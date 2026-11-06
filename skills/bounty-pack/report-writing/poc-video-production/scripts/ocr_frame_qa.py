#!/usr/bin/env python3
"""OCR-based money-shot QA for recorded PoC segments (Route E, pitfall 6).

Why this exists: pixel stats prove a frame is *populated*, not that the disclosure string is
*legible in it*. A take whose screen froze after Enter, or whose interpreter never printed,
looks structurally healthy and still fails the whole point of the segment. Tesseract (local,
no vision model) answers the text question deterministically.

Usage:
    python ocr_frame_qa.py <video> --at 16.0,25.0,40.0 --needles names,storeType,GET
    python ocr_frame_qa.py <video> --check "16.0:names,de2-leader" --check "40.0:HTTP 200"

Exit code 0 = every needle found in at least one requested frame; 1 = at least one miss.

Notes that cost real time (keep them):
  * Invert light-on-dark terminal text before OCR (threshold ~90 on luminance). Dark-theme
    frames OCR'd as empty until inverted, which reads as "the command never ran".
  * Use accurate seek: `-i <video> -ss T -frames:v 1`. The fast form (`-ss T -i`) returns the
    neighbouring segment's content at concat boundaries (pitfall 22).
  * OCR garbles glyphs (`AttesterTs store`, `flowerypt.com`). Match on short, distinctive
    needles and treat a fuzzy hit as present; only a clean absence is a real miss.
  * Crop the caption band out (it carries your own overlay text) so the assertion can only
    pass on real captured output.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow required: pip install pillow")

DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
INK_THRESHOLD = 90     # monokai/Dracula foreground luminance is 150-200; bg is ~30


def find_ffmpeg():
    return shutil.which("ffmpeg") or "ffmpeg"


def find_tesseract():
    if os.path.exists(DEFAULT_TESSERACT):
        return DEFAULT_TESSERACT
    on_path = shutil.which("tesseract")
    if on_path:
        return on_path
    sys.exit("tesseract not found — install UB-Mannheim.TesseractOCR (winget) or set PATH")


def grab(ffmpeg, video, t, dest):
    """Accurate-seek frame extraction (see pitfall 22)."""
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", video,
                        "-ss", f"{t:.3f}", "-frames:v", "1", dest],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dest):
        raise RuntimeError(f"frame grab failed at t={t}: {r.stderr[:200]}")
    return dest


def ocr_frame(tesseract, png, crop=None, threshold=INK_THRESHOLD, workdir=None):
    """OCR a (usually dark) frame. Returns the whitespace-collapsed recognised text."""
    workdir = workdir or tempfile.mkdtemp(prefix="ocrqa_")
    im = Image.open(png).convert("L")
    if crop:
        im = im.crop(crop)
    inv = Image.eval(im, lambda v: 0 if v > threshold else 255)
    inv_png = os.path.join(workdir, os.path.basename(png).replace(".png", "_inv.png"))
    inv.save(inv_png)
    base = os.path.join(workdir, os.path.basename(png).replace(".png", ""))
    subprocess.run([tesseract, inv_png, base, "--psm", "6", "-l", "eng"],
                   capture_output=True)
    txt_path = base + ".txt"
    if not os.path.exists(txt_path):
        raise RuntimeError("tesseract produced no output")
    with open(txt_path, encoding="utf-8", errors="replace") as fh:
        return " ".join(fh.read().split())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--at", default="",
                    help="comma-separated timestamps; each is checked against --needles")
    ap.add_argument("--needles", default="",
                    help="comma-separated strings that must appear in every --at frame")
    ap.add_argument("--check", action="append", default=[],
                    help="'T:needle,needle' — frame time and its own needles (repeatable)")
    ap.add_argument("--crop", default="0,40,1920,965",
                    help="x0,y0,x1,y1 crop before OCR; default drops the caption band. "
                         "Pass 'none' to disable.")
    ap.add_argument("--tesseract", default=None)
    a = ap.parse_args()

    ffmpeg = find_ffmpeg()
    tesseract = a.tesseract or find_tesseract()
    crop = None if a.crop.lower() == "none" else tuple(int(x) for x in a.crop.split(","))

    checks = []
    if a.at and a.needles:
        needles = [n.strip() for n in a.needles.split(",") if n.strip()]
        for t in a.at.split(","):
            checks.append((float(t.strip()), needles))
    for spec in a.check:
        t_s, _, needles_s = spec.partition(":")
        checks.append((float(t_s), [n.strip() for n in needles_s.split(",") if n.strip()]))
    if not checks:
        ap.error("give --at/--needles or at least one --check")

    workdir = tempfile.mkdtemp(prefix="ocrqa_")
    failures = 0
    for t, needles in checks:
        png = grab(ffmpeg, a.video, t, os.path.join(workdir, f"f{t:.1f}.png"))
        text = ocr_frame(tesseract, png, crop=crop, workdir=workdir)
        results = [(n, n.lower() in text.lower()) for n in needles]
        missing = [n for n, ok in results if not ok]
        status = "OK  " if not missing else "MISS"
        print(f"[{status}] t={t:6.2f}  " +
              "  ".join(f"{n}={'Y' if ok else 'N'}" for n, ok in results))
        if missing:
            failures += 1
            print(f"        recognised: {text[:220]}")
    shutil.rmtree(workdir, ignore_errors=True)
    print(f"\n{len(checks) - failures}/{len(checks)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
