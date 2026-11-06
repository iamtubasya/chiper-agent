#!/usr/bin/env python3
"""Deterministic post-build verification for a PoC video.

Why this exists: the build log says "concat rc: 0" even when a segment silently lost half its
duration to a frame-rate mismatch, or when the address-bar overlay never landed. The only reliable
check is to sample the FINISHED file and classify the pixels.

Usage:
    python verify_video_timeline.py OUT.mp4
    python verify_video_timeline.py OUT.mp4 --segments-dir build --expect card:5,terminal:15,card:7,terminal:10,card:10,browser:15,card:12

Reports:
  1. Per-segment (of the parts directory) duration + frame rate  -> catches a dropped fps.
  2. A scan of the final file at a fixed step, classifying each sampled frame by pixel layout
     -> catches a truncated segment, a missing address bar, or pillarboxing.

Region model assumed (adjust LAYOUT below if your canvas differs):
    top strip     0   .. 74   = address bar / terminal title bar
    viewport      74  .. 930
    caption strip 930 .. 1080
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

BAR = (0, 74)
CAP = (930, 1080)


def probe(ffprobe, path):
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration:stream=r_frame_rate,width,height,codec_name,pix_fmt",
         "-of", "default=nw=1", str(path)],
        capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def grab(ffmpeg, video, t, dest):
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", str(t),
                    "-i", str(video), "-frames:v", "1", str(dest)], capture_output=True)
    return dest.exists()


def classify(arr):
    """Return (tag, metrics). 'browser' requires a bright bar AND a populated caption strip."""
    bar = arr[BAR[0]:BAR[1]]
    cap = arr[CAP[0]:CAP[1]]
    bb = (bar.sum(axis=2) > 300).mean()          # bright pixels in the bar
    cb = (cap.sum(axis=2) > 300).mean()          # bright pixels in the caption
    view = arr[BAR[1]:CAP[0]]
    light = (view.min(axis=2) > 200).mean()
    dark = (view.max(axis=2) < 90).mean()
    edges = (np.abs(np.diff(view.mean(axis=2), axis=1)) > 40).mean()
    if bb > 0.04 and cb > 0.02:
        tag = "browser"
    elif bb > 0.02:
        tag = "terminal"
    else:
        tag = "card"
    return tag, dict(bright_bar=bb, bright_cap=cb, light=light, dark=dark, edges=edges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--segments-dir", default=None,
                    help="directory of the individual mp4 parts, to table their duration/fps")
    ap.add_argument("--step", type=float, default=1.5, help="sampling step in seconds")
    ap.add_argument("--expect", default=None,
                    help="comma list name:seconds,... of expected segment lengths, for a summary")
    a = ap.parse_args()

    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    video = Path(a.video)
    if not video.exists():
        sys.exit(f"not found: {video}")

    info = probe(ffprobe, video)
    print(f"FINAL  {video.name}")
    print(f"       codec={info.get('codec_name')} {info.get('width')}x{info.get('height')} "
          f"{info.get('pix_fmt')} {info.get('r_frame_rate')} "
          f"duration={float(info.get('duration', 0)):.1f}s "
          f"size={video.stat().st_size // 1024} KB")
    if info.get("pix_fmt") != "yuv420p":
        print("  !! pix_fmt is not yuv420p - many portals reject that")
    fps = info.get("r_frame_rate", "0/1")
    if fps != "30/1":
        print(f"  !! frame rate is {fps}, segments were built at 30/1 - concat may have drifted")

    if a.segments_dir:
        d = Path(a.segments_dir)
        print("\nPARTS")
        for p in sorted(d.glob("*.mp4")):
            pi = probe(ffprobe, p)
            print(f"  {p.name:<18} {float(pi.get('duration', 0)):6.1f}s  {pi.get('r_frame_rate')}")
        if a.expect:
            want = sum(float(x.split(":")[1]) for x in a.expect.split(","))
            got = float(info.get("duration", 0))
            flag = "OK" if abs(want - got) < 1.0 else "MISMATCH"
            print(f"  expected total {want:.1f}s vs final {got:.1f}s  -> {flag}")

    print("\nTIMELINE (frame classification by pixel layout)")
    tmp = video.parent / "_verify_tmp"
    tmp.mkdir(exist_ok=True)
    prev, t, end = None, 0.0, float(info.get("duration", 0))
    while t < end:
        f = tmp / "s.png"
        if not grab(ffmpeg, video, t, f):
            print(f"  t={t:6.1f}  FRAME MISSING"); t += a.step; continue
        arr = np.asarray(Image.open(f).convert("RGB")).astype(int)
        tag, m = classify(arr)
        if tag != prev:
            print(f"  -> {tag:<8} starts ~t={t:5.1f}s   "
                  f"bar={m['bright_bar']:.1%} cap={m['bright_cap']:.1%} "
                  f"light={m['light']:.1%} dark={m['dark']:.1%} edges={m['edges']:.2%}")
            prev = tag
        t += a.step

    print("\nCHECK: a 'browser' span should exist, and its viewport should be mostly ONE colour")
    print("       (a page) with a small amount of text - not uniformly blank and not heavily")
    print("       dark at the left/right edges (that is pillarboxing from force_original_aspect_ratio=decrease).")


if __name__ == "__main__":
    main()
