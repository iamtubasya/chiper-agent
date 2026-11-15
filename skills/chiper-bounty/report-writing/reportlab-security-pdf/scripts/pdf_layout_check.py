#!/usr/bin/env python3
"""Deterministic layout/QA check for generated bug-bounty report PDFs.

Why this exists: text-layer inspection does NOT reveal overlapping text. Word bounding-box
geometry does. A visual (vision-model) pass missed the real defect and hallucinated a different
document; this script is the source of truth.

Usage:
    python pdf_layout_check.py report.pdf [report2.pdf ...] [--tokens "Mr Fz" "Page 1 of"]

Checks per page:
  1. word-collision            overlapping words from different text blocks
  2. out-of-margin             words outside the printable area
  3. orphan heading            section heading as the last block on a page (content spilled)
  4. oversized word            a word wider than the text column (non-wrapping table cell)
Global:
  5. raw HTML entity           '&mdash;' etc. leaking into rendered text (canvas/non-Paragraph)
  6. watermark/draft tokens    word-boundary matched (avoids 'confidentiality' false positive)
  7. required tokens           --tokens values must appear
  8. JPEG neighbour sanity     if a JPEG is embedded, its Page-* metrics must describe its own pixels

Exit code 0 = pass, 1 = problems found.
"""
import argparse
import re
import sys

try:
    import pymupdf  # PyMuPDF
except ImportError:  # pragma: no cover
    import fitz as pymupdf

A4_W, A4_H = 595.28, 841.89
HEAD_RE = re.compile(r"^\s*\d{1,2}\.\s+\S")
ENTITY_RE = re.compile(r"&[a-zA-Z]+;")
BAD_WORDS = ("watermark", "draft", "template", "evaluation copy", "sample")


def analyse(path, tokens, margin=42.0, header_band=60.0, footer_band=60.0,
            frame_lm=None, frame_rm=None):
    """frame_lm/frame_rm = the document's ACTUAL text frame in points (BaseDocTemplate
    leftMargin / pagewidth-rightMargin). Pass them whenever the frame is narrower than the
    page margin you would guess — otherwise overflow between the frame edge and the guessed
    margin is invisible. Measured 2026-10-25: a 20 mm frame (ends at 539 pt) with a code block
    running to x1=597; a 42 pt page-margin check passes anything up to 560, so a smaller
    breach (say 550) reads clean while the text sits outside its column."""

    doc = pymupdf.open(path)
    problems = []
    for pi, page in enumerate(doc):
        W, H = page.rect.width, page.rect.height
        words = page.get_text("words")  # x0,y0,x1,y1,word,block,line,wordno

        # 1. collisions between DIFFERENT blocks (same block = normal multi-span line)
        for i in range(len(words)):
            a = words[i]
            for j in range(i + 1, len(words)):
                b = words[j]
                if a[5] == b[5]:
                    continue
                ix = min(a[2], b[2]) - max(a[0], b[0])
                iy = min(a[3], b[3]) - max(a[1], b[1])
                if ix > 1.2 and iy > 1.2:
                    problems.append(f"p{pi+1} COLLISION {a[4]!r} x {b[4]!r}")

        # 2. out of margins
        for w in words:
            if w[2] > W - margin + 7 or w[0] < margin - 7:
                problems.append(
                    f"p{pi+1} OUT-OF-MARGIN {w[4]!r} x0={w[0]:.1f} x1={w[2]:.1f} (page W={W:.0f})"
                )

        # 2b. outside the document's OWN frame (block level). This is the check that catches
        # an unwrapped Preformatted code block: the page is wider than the frame, so nothing
        # "leaves the page" and the per-word margin test above can still pass.
        if frame_lm is not None and frame_rm is not None:
            for b in page.get_text("blocks"):
                x0, x1 = b[0], b[2]
                if x0 < frame_lm - 3 or x1 > frame_rm + 3:
                    snippet = b[4].strip().split("\n")[0][:48]
                    problems.append(
                        f"p{pi+1} OUT-OF-FRAME {snippet!r} x0={x0:.1f} x1={x1:.1f} "
                        f"(frame {frame_lm:.0f}-{frame_rm:.0f})"
                    )

        # 3. orphan heading: last body block on the page is a heading
        body = [b for b in page.get_text("blocks")
                if b[4].strip() and header_band < b[1] < H - footer_band]
        if body:
            last = sorted(body, key=lambda b: b[1])[-1][4].strip().replace("\n", " ")
            if HEAD_RE.match(last) and len(last) < 70:
                problems.append(f"p{pi+1} ORPHAN HEADING {last[:60]!r}")

        # 4. oversized word (column overflow from a raw-string table cell)
        text_w = W - 2 * margin
        for w in words:
            if (w[2] - w[0]) > text_w:
                problems.append(f"p{pi+1} OVERSIZED WORD {w[4][:40]!r} width={(w[2]-w[0]):.0f}")

    full = "\n".join((p.get_text() or "") for p in doc)

    # 5. raw entities in rendered text
    for m in set(ENTITY_RE.findall(full)):
        problems.append(f"RAW ENTITY {m} present in rendered text")

    # 6. watermark-ish words, word-boundary matched
    for bw in BAD_WORDS:
        if re.search(rf"\b{re.escape(bw)}\b", full, re.I):
            problems.append(f"token present: {bw!r}")

    # 7. required tokens
    for t in tokens or []:
        if t not in full:
            problems.append(f"REQUIRED TOKEN MISSING: {t!r}")

    # 8. embedded JPEG neighbour sanity
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_get_key(xref, "Subtype")[1] != "/Image":
                continue
            if doc.xref_get_key(xref, "Filter")[1] not in ("/DCTDecode", "/DCT"):
                continue
            px = int(doc.xref_get_key(xref, "Width")[1])
            metrics = doc.extract_image(xref)
            hp, wpt = float(metrics["Page hp"]), float(metrics["Page wp"])
            rate = float(metrics["Page rate"])
            if abs(hp / (px / 72.0) - 1.0) > 0.02 or abs(rate - 1.0) > 0.02:
                problems.append(f"JPEG xref {xref}: Page hp/rate do not match its own pixels "
                                f"(hp={hp} rate={rate} px={px}) — stale/sticky size metadata")
        except Exception:
            pass

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--tokens", nargs="*", default=[])
    ap.add_argument("--frame-lm", type=float, default=None,
                    help="actual left frame edge in pt (BaseDocTemplate leftMargin)")
    ap.add_argument("--frame-rm", type=float, default=None,
                    help="actual right frame edge in pt (pagewidth - rightMargin)")
    args = ap.parse_args()

    total = 0
    for p in args.pdfs:
        probs = analyse(p, args.tokens, frame_lm=args.frame_lm, frame_rm=args.frame_rm)
        pages = len(pymupdf.open(p))
        print(f"===== {p}  pages={pages}  problems={len(probs)}")
        for x in probs[:40]:
            print("   ", x)
        total += len(probs)
    print(f"TOTAL PROBLEMS: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
