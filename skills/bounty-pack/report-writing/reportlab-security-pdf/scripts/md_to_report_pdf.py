#!/usr/bin/env python3
"""Reusable reportlab generator: markdown report -> triager-ready PDF.

Parses the report markdown so the PDF cannot drift from the source (no hand-transcription), and
implements the layout fixes learned the hard way:
  * no Spacer right after a heading  -> prevents the ORPHAN HEADING defect (keepWithNext trap)
  * hard-split over-long code tokens, break long inline-code spans -> prevents OVERSIZED WORD / overflow
  * escapes every string, then re-applies **bold** and `code` markup only
  * `![caption](path)` embeds an image (evidence screenshot), scaled to fit the text frame

Usage:
    python md_to_report_pdf.py report.md report.pdf [--header-left "Program - Report"] \
        [--header-right "FINDING-ID"] [--footer-right "Platform"]

Then ALWAYS verify:
    python pdf_layout_check.py report.pdf --tokens "Page 1 of" "FINDING-ID"

Requires: reportlab, pymupdf (for the page count / verification).
"""
import argparse, os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Preformatted, Table, TableStyle)

MONO, MONO_B = "Courier", "Courier-Bold"
SANS, SANS_B = "Helvetica", "Helvetica-Bold"
CODE_WRAP = 84          # Courier 9pt fits ~89 chars between 20mm margins; stay under it
INLINE_CODE_BREAK = 46  # long inline `code` spans get explicit <br/> breaks


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)

    def _code(m):
        c = m.group(1)
        if len(c) <= INLINE_CODE_BREAK:
            return '<font face="Courier">%s</font>' % c
        chunks, cur = [], ""
        for part in re.split(r"(?<=/)", c):
            if len(cur) + len(part) > INLINE_CODE_BREAK and cur:
                chunks.append(cur); cur = part
            else:
                cur += part
        if cur:
            chunks.append(cur)
        return '<font face="Courier">%s</font>' % "<br/>".join(chunks)

    return re.sub(r"`([^`]+)`", _code, s)


BODY = ParagraphStyle("bodyx", fontName=SANS, fontSize=11, leading=17, spaceAfter=8, alignment=TA_LEFT)
H1 = ParagraphStyle("h1x", fontName=SANS_B, fontSize=18, leading=22, spaceBefore=4, spaceAfter=12, keepWithNext=True)
H2 = ParagraphStyle("h2x", fontName=SANS_B, fontSize=15, leading=19, spaceBefore=22, spaceAfter=9, keepWithNext=True)
H3 = ParagraphStyle("h3x", fontName=SANS_B, fontSize=13, leading=17, spaceBefore=20, spaceAfter=8, keepWithNext=True)
BUL = ParagraphStyle("bulx", parent=BODY, leftIndent=16, bulletIndent=4, spaceAfter=6)
CAP = ParagraphStyle("capx", fontName=SANS, fontSize=9, leading=13, spaceBefore=4, spaceAfter=12,
                     alignment=TA_LEFT, textColor=colors.HexColor("#555555"))
CODE = ParagraphStyle("codex", fontName=MONO, fontSize=9, leading=13.5, spaceBefore=6, spaceAfter=8,
                      backColor=colors.HexColor("#f2f2f2"), borderPadding=6, leftIndent=6, rightIndent=6)
CELL = ParagraphStyle("cellx", fontName=SANS, fontSize=8.6, leading=11, alignment=TA_LEFT)
CELLH = ParagraphStyle("cellh", fontName=SANS_B, fontSize=8.6, leading=11, alignment=TA_LEFT)


def _split_row(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _is_sep(line):
    s = line.strip()
    if not s.startswith("|"):
        return False
    body = s.replace("|", "").replace(" ", "")
    return bool(body) and set(body) <= set("-:") and "-" in body


def build_table(header, rows):
    """Markdown table -> real reportlab Table of Paragraph cells.

    Column widths are POINTS (not mm): distributed by the longest cell with a
    floor, then normalised to the 170 mm text frame. Every cell goes through
    inline() so it is escaped and word-wraps — a raw str in a cell does not.
    """
    ncols = max([len(header)] + [len(r) for r in rows] + [1])
    all_rows = [header] + rows
    weights = []
    for c in range(ncols):
        longest = max((len(r[c]) if c < len(r) else 0) for r in all_rows)
        weights.append(max(longest, 12) + 8)
    avail = A4[0] - 40 * mm
    total = float(sum(weights))
    widths = [avail * w / total for w in weights]

    data = []
    for ri, r in enumerate(all_rows):
        style = CELLH if ri == 0 else CELL
        cells = [Paragraph(inline(r[c]) if c < len(r) else "", style)
                 for c in range(ncols)]
        data.append(cells)

    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _hard_split(tok, width):
    return [tok[i:i + width] for i in range(0, len(tok), width)] or [""]


def wrap_code(line, width=CODE_WRAP):
    if len(line) <= width:
        return [line]
    out, cur = [], ""
    for tok in re.split(r"(\s+)", line):
        if len(tok) > width:                       # unbreakable token (long path) -> hard split
            if cur.strip():
                out.append(cur.rstrip()); cur = ""
            out.extend(_hard_split(tok, width))
            continue
        if len(cur) + len(tok) > width and cur.strip():
            out.append(cur.rstrip()); cur = tok.lstrip()
        else:
            cur += tok
    if cur.strip():
        out.append(cur.rstrip())
    return out or [""]


def build_story(md):
    story, lines, i, last_heading = [], md.splitlines(), 0, False
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            wrapped = []
            for b in block:
                wrapped.extend(wrap_code(b))
            # Preformatted renders its text literally (no XML/entity pass), so code
            # must NOT be esc()'d here — escaping would print `&lt;` in the PDF.
            story.append(Preformatted("\n".join(wrapped), CODE)); story.append(Spacer(1, 2))
            last_heading = False
            continue
        # markdown table: `| a | b |` followed by a `|---|---|` separator row.
        # MUST run before the paragraph branch, which would otherwise absorb the
        # whole table into one run-on paragraph (silent mangle, no error).
        if ln.strip().startswith("|") and i + 1 < len(lines) and _is_sep(lines[i + 1]):
            header = _split_row(ln)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            story.append(build_table(header, rows))
            story.append(Spacer(1, 8))
            last_heading = False
            continue
        m_img = re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", ln.strip())
        if m_img:
            # evidence screenshot: `![caption](path/to.png)` — path may be absolute (Windows ok)
            from reportlab.platypus import Image as _RLImage
            _cap, _path = m_img.group(1), m_img.group(2)
            if os.path.exists(_path):
                _im = _RLImage(_path)
                _max = 170 * mm                      # A4 text frame is ~170mm wide at 20mm margins
                if _im.imageWidth > _max:
                    _r = _max / _im.imageWidth
                    _im.drawWidth = _max
                    _im.drawHeight = _im.imageHeight * _r
                story.append(_im)
                if _cap:
                    story.append(Paragraph(inline(_cap), CAP))
            else:
                story.append(Paragraph(inline("[missing image: %s]" % _path), BODY))
            last_heading = False
            i += 1
            continue
        if ln.startswith("# "):
            story.append(Paragraph(inline(ln[2:].strip()), H1)); last_heading = True
        elif ln.startswith("## "):
            story.append(Paragraph(inline(ln[3:].strip()), H2)); last_heading = True
        elif ln.startswith("### "):
            story.append(Paragraph(inline(ln[4:].strip()), H3)); last_heading = True
        elif re.match(r"^\s*[-*]\s+", ln):
            story.append(Paragraph(inline(re.sub(r"^\s*[-*]\s+", "", ln)), BUL, bulletText="\u2022"))
            last_heading = False
        elif re.match(r"^\s*\d+\.\s+", ln):
            story.append(Paragraph(inline(re.sub(r"^\s*(\d+)\.\s+", r"\1. ", ln)), BUL))
            last_heading = False
        elif ln.strip() == "":
            if not last_heading:       # no Spacer after a heading (orphan-heading trap)
                story.append(Spacer(1, 6))
        elif ln.strip() == "---":
            story.append(Spacer(1, 4)); last_heading = False
        else:
            para = [ln.strip()]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(
                    r"^(#|\s*[-*]\s|\s*\d+\.\s|```|---|\|)", lines[i + 1]):
                i += 1
                para.append(lines[i].strip())
            story.append(Paragraph(inline(" ".join(para)), BODY)); last_heading = False
        i += 1
    return story


def make(out, story, header_left, header_right, footer_right, title, total_pages=1):
    def _decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont(SANS, 8); canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(20 * mm, A4[1] - 13 * mm, header_left)
        canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 13 * mm, header_right)
        canvas.drawString(20 * mm, 13 * mm, "Page %d of %d" % (doc.page, total_pages))
        canvas.drawRightString(A4[0] - 20 * mm, 13 * mm, footer_right)
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.line(20 * mm, A4[1] - 15 * mm, A4[0] - 20 * mm, A4[1] - 15 * mm)
        canvas.line(20 * mm, 16 * mm, A4[0] - 20 * mm, 16 * mm)
        canvas.restoreState()

    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=20 * mm, bottomMargin=20 * mm, title=title)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=_decorate)])
    doc.build(story)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md"); ap.add_argument("pdf")
    ap.add_argument("--header-left", default="Security Report")
    ap.add_argument("--header-right", default="")
    ap.add_argument("--footer-right", default="")
    a = ap.parse_args()
    md = open(a.md, encoding="utf-8").read()
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    # pass 1: page count, then pass 2 with the true "Page X of Y" (fresh flowables each time)
    make(a.pdf + ".pass1", build_story(md), a.header_left, a.header_right, a.footer_right, "t", 1)
    n = len(pymupdf.open(a.pdf + ".pass1")); os.remove(a.pdf + ".pass1")
    make(a.pdf, build_story(md), a.header_left, a.header_right, a.footer_right, os.path.basename(a.pdf), n)
    print("PDF:", a.pdf, "pages:", len(pymupdf.open(a.pdf)))


if __name__ == "__main__":
    main()
