#!/usr/bin/env python3
"""Deterministic frame-level verification for a rendered PoC video (no vision model needed).

Samples a video at a fixed interval and reports, per sample:
  * caption/commentary band text presence (bright pixels in the bottom strip)
  * body "ink" (is the segment rendering at all? climbs during a typed animation)
  * letterbox/pillarbox detection on the left and right edges of the content area
and then prints where the segment type changes, plus the real duration of every input part.

Why this exists: vision_analyze is unreliable on rendered frames (it can return a generic
apology instead of reading the image), and a mixed-fps concat silently truncates one segment
while the TOTAL duration still looks correct. Both failures are invisible without sampling.

Usage
-----
  python video_frame_verify.py FINAL.mp4
  python video_frame_verify.py FINAL.mp4 --band 935:1075 --body 60:925 --step 1.0
  python video_frame_verify.py FINAL.mp4 --parts build/          # also probe each input segment

Exit code 0 if every sampled frame has content, 1 if any sample looks blank.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("needs pillow + numpy:  pip install pillow numpy")

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or FFMPEG.replace("ffmpeg", "ffprobe")


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def duration(path: Path) -> float:
    """Real duration in seconds, or 0.0 when ffprobe cannot say."""
    out = _run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(path)])
    try:
        return float(out.splitlines()[0])
    except (IndexError, ValueError):
        return 0.0


def fps(path: Path) -> str:
    return _run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(path)]) or "?"


def frame_at(video: Path, t: float, out: Path) -> bool:
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(t),
                    "-i", str(video), "-frames:v", "1", str(out)], capture_output=True)
    return out.exists() and out.stat().st_size > 0


def parse_range(spec: str) -> tuple[int, int]:
    lo, _, hi = spec.partition(":")
    return int(lo), int(hi) if hi else 10 ** 9


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a rendered PoC video frame-by-frame.")
    ap.add_argument("video", type=Path)
    ap.add_argument("--band", default="935:1075",
                    help="caption/commentary strip as top:bottom (px). Default 935:1075.")
    ap.add_argument("--body", default="60:925",
                    help="content area as top:bottom (px). Default 60:925.")
    ap.add_argument("--step", type=float, default=1.5, help="sample interval in seconds.")
    ap.add_argument("--parts", type=Path, default=None,
                    help="directory of input segment MP4s to probe for duration/fps drift.")
    ap.add_argument("--edge", type=int, default=120, help="edge strip width for letterbox check.")
    ap.add_argument("--tmp", type=Path, default=None, help="scratch dir for extracted frames.")
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"not found: {video}")
    tmp = (args.tmp or video.parent / "_verify_frames")
    tmp.mkdir(parents=True, exist_ok=True)

    bt, bb = parse_range(args.band)
    ct, cb = parse_range(args.body)
    total = duration(video)
    print(f"=== {video.name}   duration={total:.2f}s   fps={fps(video)}")

    if args.parts and args.parts.is_dir():
        print("\n--- input segments (duration / fps) ---")
        for p in sorted(args.parts.glob("*.mp4")):
            print(f"  {p.name:<24} {duration(p):6.2f}s  {fps(p)}")

    print("\n--- sampled frames ---")
    print(f"{'t':>7}  {'caption':>8}  {'body_ink':>8}  {'L_bar':>6}  {'R_bar':>6}  segment")
    sample = tmp / "_sample.png"
    rows: list[tuple[float, float, float, float, float]] = []
    t = args.step / 2
    while t < total:
        if not frame_at(video, t, sample):
            print(f"{t:7.1f}  FRAME MISSING")
            t += args.step
            continue
        a = np.asarray(Image.open(sample).convert("RGB")).astype(int)
        band = a[bt:bb]
        body = a[ct:cb]
        caption = (band.sum(axis=2) > 330).mean() if band.size else 0.0
        ink = (body.sum(axis=2) > 120).mean() if body.size else 0.0
        lbar = (a[ct:cb, :args.edge].max(axis=2) < 90).mean()
        rbar = (a[ct:cb, -args.edge:].max(axis=2) < 90).mean()
        rows.append((t, caption, ink, lbar, rbar))
        t += args.step

    prev = None
    for (t, caption, ink, lbar, rbar) in rows:
        if ink < 0.02:
            kind = "CARD"
        elif lbar > 0.4 and rbar > 0.4:
            kind = "PILLARBOXED?"          # bars on BOTH edges -> improper fit
        else:
            kind = "CONTENT"
        mark = "  <-- transition" if kind != prev else ""
        print(f"{t:7.1f}  {caption:7.2%}  {ink:8.2%}  {lbar:6.2%}  {rbar:6.2%}  {kind}{mark}")
        prev = kind

    blank = [t for (t, _c, ink, _l, _r) in rows if ink < 0.001]
    pillarboxed = [t for (t, _c, _i, lbar, rbar) in rows if lbar > 0.4 and rbar > 0.4]
    print()
    if blank:
        print(f"FAIL: {len(blank)} blank sample(s), first at t={blank[0]:.1f}s")
    if pillarboxed:
        print(f"WARN: {len(pillarboxed)} sample(s) pillarboxed (both edges dark) - "
              f"use scale=...:force_original_aspect_ratio=increase,crop=W:H")
    if not blank and not pillarboxed:
        print("OK: every sample has content and the frame is filled.")
    return 1 if blank else 0


if __name__ == "__main__":
    raise SystemExit(main())
