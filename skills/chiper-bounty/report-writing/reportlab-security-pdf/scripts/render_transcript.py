"""Render a raw shell/test transcript to a legible dark-terminal evidence PNG.

WHY THIS EXISTS ALONGSIDE `make_evidence.py`
--------------------------------------------
`make_evidence.py`'s `extract()` keeps only lines matching
`^PoC |^\[|^RESULT|^-----`, which is correct for a test runner's stdout but silently guts
anything else. Measured on a real engagement: a 35-line `forge test` transcript rendered
as 11 lines, and a 35-line shell/diff transcript rendered as **1 line** — a title bar over
an empty image, still reported as a successful render. A shell transcript's commands and
their raw output ARE the evidence, so for those, render verbatim with this script.

Usage
-----
    python render_transcript.py <raw.txt> <out.png> ["Optional Title"]

Verified: 35 lines -> 1500x1207px / 138 KB; 32 lines -> 1500x1114px / 82 KB.
Sanity-check a batch by size spread — uniform sizes mean blank renders.
"""
import re
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, FONT_SZ, PITCH, PAD, WRAP = 1500, 17, 31, 26, 118
BG, FG = (18, 18, 20), (226, 226, 226)
C_CMD, C_OK, C_FAIL, C_NOTE = (126, 200, 255), (126, 231, 135), (255, 122, 122), (150, 150, 160)

_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
)


def _font(size):
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def colour_for(line):
    s = line.strip()
    if s.startswith("$") or s.startswith(">"):
        return C_CMD
    if "[PASS]" in line or "RESULT:" in line or s.startswith("==="):
        return C_OK
    if "[FAIL" in line or "ERROR" in line or "MISMATCH" in line:
        return C_FAIL
    if s.startswith("#") or s.startswith("---"):
        return C_NOTE
    return FG


def render(src, dest, title=None):
    """Render src -> dest. Returns the number of rendered lines."""
    raw = Path(src).read_text(encoding="utf-8", errors="replace")
    # Strip ANSI FIRST: escape sequences are not whitespace, so a filter or a
    # startswith() test run before this silently matches nothing.
    raw = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw)

    lines = []
    for ln in raw.splitlines():
        ln = ln.rstrip()
        if not ln:
            lines.append(("", FG))
            continue
        # WRAP rather than clip — a clipped value is worthless as evidence.
        for segment in textwrap.wrap(ln, WRAP) or [""]:
            lines.append((segment, colour_for(ln)))

    head = 58 if title else 0
    height = max(140, head + PAD * 2 + len(lines) * PITCH + 12)
    img = Image.new("RGB", (W, height), BG)
    draw = ImageDraw.Draw(img)
    if title:
        draw.rectangle([0, 0, W, head], fill=(30, 30, 34))
        draw.text((PAD, 16), title, font=_font(21), fill=(240, 240, 240))
    y = head + PAD
    for segment, colour in lines:
        draw.text((PAD, y), segment, font=_font(FONT_SZ), fill=colour)
        y += PITCH
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    print(f"  {Path(dest).name}: {len(lines)} lines -> {W}x{height}px")
    return len(lines)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
