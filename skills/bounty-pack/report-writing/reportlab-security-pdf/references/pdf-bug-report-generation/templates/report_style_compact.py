"""Compact reportlab report base — copy next to your generator as `<target>_style.py` and import.

This is the self-contained replacement for the old
`D:/data hermes/bug-bounty/_progress/fira.money_v1/submission/att_style.py` pointer (that tree gets
purged — verified 2026-10 when the path no longer existed and a 7-report engagement had to rebuild it).

It enforces the quality bar in the parent skill:
  * `esc()` is applied INSIDE `C()` and `tbl()` so a bare `&` cannot become `&...;` in the PDF
  * `keepWithNext=True` on H1/H2 so a heading is never stranded at a page bottom
  * two-pass build so the footer can print `Page N`
  * MARGIN = 42pt -> run the layout QA gate with `--margin-mm 14.8` (`42 * 25.4 / 72`)

Every report in the 2026-10-12 Vana engagement (7 findings, 3-4 pages each) was built on this and passed
`qa_pdf_layout.py --margin-mm 14.8` clean.

Usage from a per-finding generator:

    from vana_style import (P, C, B, H1, H2, BODYS, SMALL, KT, tbl, meta_table, make_docs)
    story = []
    story.append(P("Finding title here", H1))
    story.append(meta_table([("Target", "..."), ("Severity", "Low")]))
    story.append(P("Summary", H2))
    story.append(P("...", BODYS))
    story.append(C('''curl -s https://target/api   # code blocks: triple-SINGLE quotes'''))
    make_docs(str(OUT / "F1-Low-slug.pdf"), "Target - security report", "F1 Low", story)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm  # noqa: F401  (kept for generators that position things)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Table, TableStyle, KeepTogether, PageBreak)  # noqa: F401

MARGIN = 42.0                      # pt -> 42 * 25.4 / 72 = 14.8 mm for the QA gate
NAVY = colors.HexColor("#101a3a")
ACCENT = colors.HexColor("#2f4bd8")
GREY = colors.HexColor("#5a6474")
LINE = colors.HexColor("#d7dbe6")


def esc(s):
    """Escape for reportlab's mini-HTML. Use for EVERY string that reaches a Paragraph."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


ss = getSampleStyleSheet()
# 16/24 (not 18/23): a wrapped two-line H1 at a tighter leading makes the layout checker report a
# false OVERLAP between the title lines. 1.5x leading keeps wrapped headings clean.
H1 = ParagraphStyle("H1x", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=16,
                    leading=24, textColor=NAVY, spaceAfter=8, keepWithNext=True)
H2 = ParagraphStyle("H2x", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13,
                    leading=18, textColor=ACCENT, spaceBefore=12, spaceAfter=6, keepWithNext=True)
BODYS = ParagraphStyle("BODYSx", parent=ss["BodyText"], fontName="Helvetica", fontSize=11,
                       leading=17, textColor=colors.HexColor("#1c1f27"), spaceAfter=8,
                       alignment=TA_LEFT)
SMALL = ParagraphStyle("SMALLx", parent=BODYS, fontSize=9.5, leading=14, textColor=GREY)
CODE = ParagraphStyle("CODESAFE", parent=ss["Code"], fontName="Courier", fontSize=9, leading=13.5,
                      textColor=colors.HexColor("#14251a"), backColor=colors.HexColor("#f4f6fa"),
                      borderColor=LINE, borderWidth=0.6, borderPadding=6, spaceAfter=8)
CELL = ParagraphStyle("CELL", parent=BODYS, fontSize=9.5, leading=13.5, spaceAfter=0)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold", textColor=NAVY)


def P(t, st=BODYS):
    return Paragraph(t, st)


def B(t):
    return Paragraph("&bull; " + t, BODYS)


def C(block):
    """Code block. The `&`/`<`/`>` escape matters, and newlines become <br/>."""
    return Paragraph(esc(block).replace(chr(10), "<br/>"), CODE)


def KT(head, *flows):
    return KeepTogether([Paragraph(head, H2)] + list(flows))


def tbl(rows, widths=None):
    data = [[Paragraph(esc(c) if isinstance(c, str) else c, CELLB if i == 0 else CELL)
             for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, LINE),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f8")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                           ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def meta_table(pairs):
    return tbl([["Field", "Value"]] + [[k, v] for k, v in pairs], widths=[120, 373])


def make_docs(out_path, title, header_right, story):
    """Build with a running header/footer. `title` also lands in the PDF metadata."""
    def _page(canv, doc):
        canv.saveState()
        canv.setFont("Helvetica", 8)
        canv.setFillColor(GREY)
        canv.drawString(MARGIN, A4[1] - MARGIN + 14, title)
        canv.drawRightString(A4[0] - MARGIN, A4[1] - MARGIN + 14, header_right)
        canv.drawString(MARGIN, MARGIN - 15, title)
        canv.drawRightString(A4[0] - MARGIN, MARGIN - 15, "Page %d" % canv.getPageNumber())
        canv.restoreState()

    frame = Frame(MARGIN, MARGIN, A4[0] - 2 * MARGIN, A4[1] - 2 * MARGIN, id="f")
    doc = BaseDocTemplate(out_path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN, title=title,
                          author="RESEARCHER_NAME")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=_page)])
    doc.build(story)
