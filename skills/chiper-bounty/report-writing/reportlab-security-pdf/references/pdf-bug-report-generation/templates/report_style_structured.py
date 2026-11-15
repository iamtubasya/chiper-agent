"""Structured security-report style module (vendor-proofread layout).

Skeleton follows the format Deeper Network asked for after rejecting dense text:
  Title / Summary / Affected component / Steps to reproduce / Expected result /
  Actual result / Attack scenario / Result / Impact / Recommended remediation.

Typography rules enforced here:
  * numbered steps and bullets are real list flowables with hanging indents, not prose
  * one idea per paragraph; generous leading and spaceAfter
  * headings keepWithNext so a section label never strands at a page bottom
  * two-pass build for "Page X of Y"
  * MARGIN = 54 pt = 19.05 mm  ->  run qa_pdf_layout.py --margin-mm 19.05
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.pdfgen import canvas as _canvas

MARGIN = 54.0
FRAME_W = A4[0] - 2 * MARGIN
HEADER_LEFT = "Security report"
RESEARCHER = "Mr Fz"
BULLET = chr(8226)

NAVY = colors.HexColor("#101a3a")
ACCENT = colors.HexColor("#2f4bd8")
GREY = colors.HexColor("#5a6474")
LINE = colors.HexColor("#d7dbe6")
SOFT = colors.HexColor("#f2f5fb")

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1s", parent=_ss["Heading1"], fontName="Helvetica-Bold", fontSize=16,
                    leading=24, textColor=NAVY, spaceAfter=4, keepWithNext=True)
SUB = ParagraphStyle("SUBs", parent=_ss["BodyText"], fontName="Helvetica", fontSize=10,
                     leading=15, textColor=GREY, spaceAfter=14, alignment=TA_LEFT)
H2 = ParagraphStyle("H2s", parent=_ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5,
                    leading=18, textColor=ACCENT, spaceBefore=15, spaceAfter=7, keepWithNext=True)
H3 = ParagraphStyle("H3s", parent=_ss["Heading3"], fontName="Helvetica-Bold", fontSize=10.8,
                    leading=15.5, textColor=NAVY, spaceBefore=10, spaceAfter=4, keepWithNext=True)
BODYS = ParagraphStyle("BODYSs", parent=_ss["BodyText"], fontName="Helvetica", fontSize=10.6,
                       leading=16.4, textColor=colors.HexColor("#1c1f27"), spaceAfter=9,
                       alignment=TA_LEFT)
SMALL = ParagraphStyle("SMALLs", parent=BODYS, fontSize=9.3, leading=13.8, textColor=GREY)
BUL1 = ParagraphStyle("BUL1s", parent=BODYS, leftIndent=17, bulletIndent=3, spaceAfter=5,
                       bulletFontName="Helvetica", bulletFontSize=10.6)
BUL2 = ParagraphStyle("BUL2s", parent=BODYS, leftIndent=36, bulletIndent=22, spaceAfter=4,
                       bulletFontName="Helvetica", bulletFontSize=9.6, fontSize=10.0, leading=15.5)
NUM = ParagraphStyle("NUMs", parent=BODYS, leftIndent=24, bulletIndent=2, spaceAfter=6,
                      bulletFontName="Helvetica-Bold", bulletFontSize=10.6)
STEPB = ParagraphStyle("STEPBs", parent=BODYS, leftIndent=24, spaceAfter=8)
CODE = ParagraphStyle("CODEs", parent=_ss["Code"], fontName="Courier", fontSize=8.5,
                       leading=12.6, textColor=colors.HexColor("#14251a"),
                       backColor=colors.HexColor("#f4f6fa"), borderColor=LINE,
                       borderWidth=0.6, borderPadding=7, leftIndent=6, spaceBefore=4,
                       spaceAfter=10)
CODE_I = ParagraphStyle("CODE_Is", parent=CODE, leftIndent=30, spaceBefore=3, spaceAfter=9)
CELL = ParagraphStyle("CELLs", parent=BODYS, fontSize=9.2, leading=13.2, spaceAfter=0)
CELLB = ParagraphStyle("CELLBs", parent=CELL, fontName="Helvetica-Bold", textColor=NAVY)
CELLH = ParagraphStyle("CELLHs", parent=CELLB, textColor=colors.white)

def P(t, st=BODYS):
    return Paragraph(t, st)

def H2P(t):
    return Paragraph(esc(t), H2)

def H3P(t):
    return Paragraph(esc(t), H3)

def BUL(t, lvl=0):
    st = BUL1 if lvl == 0 else BUL2
    return Paragraph(esc(t), st, bulletText=BULLET)

def NUMB(n, t):
    return Paragraph(esc(t), NUM, bulletText="%d." % n)

def STEPBODY(t):
    return Paragraph(esc(t), STEPB)

def CODE_BLOCK(block):
    return Paragraph(esc(block).replace(chr(10), "<br/>"), CODE)

def CODE_IN(block):
    return Paragraph(esc(block).replace(chr(10), "<br/>"), CODE_I)


def SP(n=8):
    return Spacer(1, n)

def dt(rows, widths):
    data = [[Paragraph(esc(c) if isinstance(c, str) else c, CELLH if i == 0 else CELL)
             for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY),
                           ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                           ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t

def kv(pairs, widths=(120, 367)):
    data = [[Paragraph(esc(k), CELLB), Paragraph(esc(v), CELL)] for k, v in pairs]
    t = Table(data, colWidths=list(widths), hAlign="LEFT")
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, LINE),
                           ("BACKGROUND", (0, 0), (0, -1), SOFT),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                           ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t

def note(label, text):
    body = Paragraph("<b>" + esc(label) + "</b> " + esc(text), CELL)
    t = Table([[body]], colWidths=[FRAME_W], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT),
                           ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t

class _CountingCanvas(_canvas.Canvas):
    def __init__(self, *a, **kw):
        self._counter = kw.pop("_counter", None)
        super().__init__(*a, **kw)

    def showPage(self):
        if self._counter is not None:
            self._counter["n"] += 1
        super().showPage()

def _build(out_path, title, header_right, story, total, counter):
    def on_page(canv, doc):
        canv.saveState()
        canv.setFont("Helvetica", 7.8)
        canv.setFillColor(GREY)
        canv.drawString(MARGIN, A4[1] - MARGIN + 16, HEADER_LEFT)
        canv.drawRightString(A4[0] - MARGIN, A4[1] - MARGIN + 16, header_right)
        canv.setStrokeColor(LINE)
        canv.setLineWidth(0.6)
        canv.line(MARGIN, A4[1] - MARGIN + 10, A4[0] - MARGIN, A4[1] - MARGIN + 10)
        canv.drawString(MARGIN, MARGIN - 18, title)
        label = "Page %d" % canv.getPageNumber()
        if total:
            label += " of %d" % total
        canv.drawRightString(A4[0] - MARGIN, MARGIN - 18, label)
        canv.restoreState()

    frame = Frame(MARGIN, MARGIN, FRAME_W, A4[1] - 2 * MARGIN, id="f")
    doc = BaseDocTemplate(out_path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN, title=title, author=RESEARCHER)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
    doc.build(story, canvasmaker=lambda *a, **kw: _CountingCanvas(*a, _counter=counter, **kw))

def make_docs(out_path, title, header_right, story, two_pass=True):
    if two_pass and callable(story):
        tmp = str(out_path) + ".pass1"
        counter = {"n": 0}
        _build(tmp, title, header_right, story(), None, counter)
        _build(out_path, title, header_right, story(), counter["n"] or None, None)
        try:
            import os
            os.remove(tmp)
        except OSError:
            pass
    else:
        _build(out_path, title, header_right, story() if callable(story) else story, None, None)