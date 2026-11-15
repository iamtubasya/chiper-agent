#!/usr/bin/env python3
"""Render a terminal-style EVIDENCE screenshot (PNG) from a raw console transcript.

Why: a PDF finding is much stronger with a picture of the actual run. This turns a captured
stdout log into a legible dark-terminal image that embeds into the report markdown with
`![caption](path)` (see md_to_report_pdf.py -- it handles that line).

Usage:
    python make_evidence.py raw/TL-01.txt out/TL-01.png --cmd "$ cargo test -p x poc_y -- --nocapture"
    python make_evidence.py raw/             # batch: every *.txt -> <raw>/../img/<stem>.png

Batch mode reads an optional sidecar `cmds.json` mapping {"TL-01": "$ command"} for the title bar.

PITFALLS learned the hard way:
  * vitest/jest console output carries ANSI colour codes ("\\x1b[33mtrue\\x1b[39m"). They are NOT
    whitespace, so `line.strip()` does not remove them and every `startswith("PoC ...")` filter
    misses. ALWAYS strip ANSI first (see ANSI below) or you get an empty screenshot.
  * keep the extract filter aligned with what your PoCs actually print; if a test prints nothing,
    the image is a title bar with no body -- add explicit print/log lines to the PoC instead of
    screenshotting the tool's default "ok" line.
  * legibility (user rejects cramped images): width ~1500, font ~17, line pitch ~31, wrap ~118.
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

W = 1500
PAD = 24
LINE_H = 31
FONT_SIZE = 17
WRAP = 118

BG = (13, 17, 23)
BAR = (22, 30, 41)
FG = (214, 226, 232)
GREEN = (126, 231, 135)
BLUE = (159, 211, 255)
DIM = (90, 106, 120)
YELL = (255, 214, 102)

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def font(size):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def extract(path):
    """Keep only the meaningful evidence lines. Adapt the prefixes to your PoC output."""
    out, seen = [], set()
    for ln in open(path, encoding="utf-8", errors="replace"):
        s = ANSI.sub("", ln).rstrip("\r\n").strip()
        if not s:
            continue
        if s.startswith("PoC ") or s.startswith("["):
            if s not in seen:
                out.append((s, "y" if "RESULT" in s else "n")); seen.add(s)
        elif s.startswith("RESULT"):
            if s not in seen:
                out.append((s, "g")); seen.add(s)
        elif s.startswith("-----"):
            out.append((s, "d"))
        elif s.startswith("test test::") and s.endswith("... ok"):
            out.append(("> " + s.split(" ... ")[0] + " ... ok", "g"))
    return out


def wrap(line, n=WRAP):
    return [line[i:i + n] for i in range(0, len(line), n)] or [""]


def render(fid, cmd, rows, dest):
    body = []
    for s, k in rows:
        body += [(w, k) for w in wrap(s)]
    title = "Terminal — " + fid + "  PoC evidence"
    cmd_lines = wrap("$ " + cmd.lstrip("$ "), WRAP + 8) if cmd else []
    bar_h = PAD * 2 + LINE_H * (1 + len(cmd_lines)) + 12
    height = bar_h + PAD + LINE_H * len(body) + PAD
    img = Image.new("RGB", (W, height), BG)
    d = ImageDraw.Draw(img)
    f = font(FONT_SIZE)
    fb = font(FONT_SIZE + 2)
    d.rectangle([0, 0, W, bar_h], fill=BAR)
    d.ellipse([PAD, PAD - 4, PAD + 14, PAD + 10], fill=(255, 95, 86))
    d.ellipse([PAD + 22, PAD - 4, PAD + 36, PAD + 10], fill=(255, 189, 46))
    d.ellipse([PAD + 44, PAD - 4, PAD + 58, PAD + 10], fill=(39, 201, 63))
    ty = PAD - 6
    d.text((PAD + 74, ty), title, font=fb, fill=FG)
    cy = ty + LINE_H + 2
    for cl in cmd_lines:
        d.text((PAD, cy), cl, font=f, fill=BLUE)
        cy += LINE_H
    y = bar_h + PAD // 2
    for s, k in body:
        d.text((PAD, y), s, font=f, fill={"g": GREEN, "y": YELL, "d": DIM, "n": FG}[k])
        y += LINE_H
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    img.save(dest)
    return dest, len(body)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    if os.path.isdir(src):
        cmds_path = os.path.join(src, "cmds.json")
        cmds = json.load(open(cmds_path, encoding="utf-8")) if os.path.exists(cmds_path) else {}
        imgdir = os.path.join(os.path.dirname(os.path.abspath(src.rstrip("/\\"))), "img")
        for name in sorted(os.listdir(src)):
            if not name.endswith(".txt"):
                continue
            fid = os.path.splitext(name)[0]
            dest, n = render(fid, cmds.get(fid, ""), extract(os.path.join(src, name)),
                             os.path.join(imgdir, fid + ".png"))
            print(f"{fid}: {dest} lines={n}")
    else:
        dest = sys.argv[2]
        cmd = ""
        if "--cmd" in sys.argv:
            cmd = sys.argv[sys.argv.index("--cmd") + 1]
        fid = os.path.splitext(os.path.basename(src))[0]
        dest, n = render(fid, cmd, extract(src), dest)
        print(f"{fid}: {dest} lines={n}")


if __name__ == "__main__":
    main()
