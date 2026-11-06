#!/usr/bin/env python3
"""Deterministic layout QA for a generated PDF report.

Run as the last gate before delivery:

    python qa_pdf_layout.py report.pdf [--margin-mm 18]

Checks, per page:
  * STRANDED heading  - a bold, heading-sized line with no text after it on the page
                        (the classic "heading at the page bottom, table on the next page")
  * heading too close to the page bottom (< 40pt of room left under it)
  * margin overflow   - any text line whose bbox crosses the page margins
  * OVERLAP           - two text lines whose bboxes intersect

Exit code 0 = clean, 1 = issues found (so it can gate a build script).

Why: a vision model asked to review a rendered page can return a fluent answer describing a
DIFFERENT document, without ever reporting that it never got the image. This script cannot
hallucinate. Use it as the authoritative layout check and keep vision for human-facing "does
this look right" on a screenshot you have confirmed renders.

Requires: pymupdf  (pip install pymupdf)
"""
import argparse
import pathlib
import sys

try:
    import pymupdf
except ImportError:  # older name
    import fitz as pymupdf


MM = 72.0 / 25.4  # points per millimetre


def load_lines(page):
    """Flatten a page into text lines with font size / weight / bbox."""
    out = []
    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") != 0:
            continue
        for ln in blk["lines"]:
            txt = "".join(s["text"] for s in ln["spans"]).strip()
            if not txt:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            out.append({
                "t": txt,
                "size": round(max(s["size"] for s in ln["spans"]), 1),
                "bold": any("Bold" in s["font"] for s in ln["spans"]),
                "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            })
    out.sort(key=lambda l: l["y0"])
    return out


def check(pdf_path, margin_mm=18.0, heading_size=12.5, bottom_gap=40.0):
    doc = pymupdf.open(str(pdf_path))
    issues = []
    for pno, page in enumerate(doc, 1):
        w, h = page.rect.width, page.rect.height
        left, right = margin_mm * MM - 2, w - margin_mm * MM + 2
        bottom = h - margin_mm * MM
        lines = load_lines(page)

        for ln in lines:
            if ln["x0"] < left or ln["x1"] > right:
                issues.append(
                    f"p{pno}: overflows margins x0={ln['x0']:.1f} x1={ln['x1']:.1f} "
                    f":: {ln['t'][:60]}")

        for ln in lines:
            if not (ln["bold"] and ln["size"] >= heading_size):
                continue
            after = [l for l in lines if l["y0"] > ln["y0"] + 12]
            if not after:
                issues.append(f"p{pno}: STRANDED heading at y={ln['y0']:.0f} "
                              f":: {ln['t'][:70]}")
            elif bottom - ln["y0"] < bottom_gap:
                issues.append(f"p{pno}: heading only {bottom - ln['y0']:.0f}pt from page "
                              f"bottom :: {ln['t'][:70]}")

        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                a, b = lines[i], lines[j]
                if (a["y1"] - 1 > b["y0"] and b["y1"] - 1 > a["y0"]
                        and a["x1"] - 1 > b["x0"] and b["x1"] - 1 > a["x0"]):
                    issues.append(f"p{pno}: OVERLAP '{a['t'][:30]}' <-> '{b['t'][:30]}'")
    return doc.page_count, issues


def main():
    ap = argparse.ArgumentParser(description="Deterministic PDF report layout QA")
    ap.add_argument("pdf")
    ap.add_argument("--margin-mm", type=float, default=18.0,
                    help="page margin used by the generator (default 18)")
    ap.add_argument("--heading-size", type=float, default=12.5,
                    help="minimum pt size treated as a heading (default 12.5)")
    args = ap.parse_args()

    path = pathlib.Path(args.pdf)
    if not path.exists():
        print(f"NOT FOUND: {path}")
        return 2

    pages, issues = check(path, margin_mm=args.margin_mm, heading_size=args.heading_size)
    print(f"file : {path}")
    print(f"pages: {pages}")
    if issues:
        print("ISSUES:")
        for s in issues:
            print("  -", s)
        return 1
    print("layout: clean (no stranded headings, no margin overflow, no overlap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
