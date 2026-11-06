"""Known-good reportlab style module for per-finding security report PDFs.

Copy next to your generator as ``<target>_style.py`` and import from it::

    from report_style import (P, C, B, KT, tbl, meta_table, make_docs,
                              H1, H2, BODYS, SMALL, Spacer, PageBreak, esc)

Enforces the pdf-bug-report-generation quality bar:
  * ``esc()`` applied inside ``C()`` and ``tbl()`` -> no bare ``&`` turning into ``&...;``
  * ``keepWithNext=True`` on H1/H2 -> no stranded headings
  * two-pass build -> footer prints "Page X of Y"
  * MARGIN = 42.0 pt (~14.8 mm) -> run QA with ``qa_pdf_layout.py <pdf> --margin-mm 14.8``
  * H1 at 16pt/24 leading -> wrapped titles do not trip the checker's OVERLAP rule

NOTE: the researcher handle lives in a constant named RESEARCHER (not "author"/"auth…"-prefixed),
because a quoted assignment to a name starting with ``auth`` can be stripped by the file-writing
secret redactor and leave the module syntactically broken. Assign RESEARCHER once, then pass it as
``author=RESEARCHER`` (no quoted value on that keyword).

Build the *generator* line-by-line (see the skill's nested-quote traps) and lint before building:
  python -c "import ast;ast.parse(open('gen.py',encoding='utf-8').read())"
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.pdfgen import canvas as _canvas

MARGIN = 42.0            # pt; margin_mm = 42.0 * 25.4 / 72 = 14.8
HEADER_LEFT = "Security report"
RESEARCHER = "Researcher handle"

NAVY = colors.HexColor("#101a3a")
ACCENT = colors.HexColor("#2f4bd8")
GREY = colors.HexColor("#5a6474")
LINE = colors.HexColor("#d7dbe6")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=_ss["Heading1"], fontName="Helvetica-Bold", fontSize=16,
                    leading=24, textColor=NAVY, spaceAfter=8, keepWithNext=True)
H2 = ParagraphStyle("H2x", parent=_ss["Heading2"], fontName="Helvetica-Bold", fontSize=13,
                    leading=18, textColor=ACCENT, spaceBefore=12, spaceAfter=6, keepWithNext=True)
BODYS = ParagraphStyle("BODYSx", parent=_ss["BodyText"], fontName="Helvetica", fontSize=11,
                       leading=17, textColor=colors.HexColor("#1c1f27"), spaceAfter=8,
                       alignment=TA_LEFT)
SMALL = ParagraphStyle("SMALLx", parent=BODYS, fontSize=9.5, leading=14, textColor=GREY)
CODE = ParagraphStyle("CODESAFE", parent=_ss["Code"], fontName="Courier", fontSize=9,
                      leading=13.5, textColor=colors.HexColor("#14251a"),
                      backColor=colors.HexColor("#f4f6fa"), borderColor=LINE,
                      borderWidth=0.6, borderPadding=6, spaceAfter=8)
CELL = ParagraphStyle("CELL", parent=BODYS, fontSize=9.5, leading=13.5, spaceAfter=0)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold", textColor=NAVY)


def P(t, st=BODYS):
    return Paragraph(t, st)


def B(t):
    return Paragraph("&bull; " + t, BODYS)


def C(block):
    """Code block. Uses ''' literals at the call site; esc() keeps & < > literal-safe."""
    return Paragraph(esc(block).replace("\n", "<br/>"), CODE)


def KT(heading, *flows):
    return KeepTogether([Paragraph(heading, H2)] + list(flows))


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
    """pairs: [(field, value), ...] -> two-column furniture table."""
    return tbl([["Field", "Value"]] + [[k, v] for k, v in pairs], widths=[120, 373])


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
        canv.setFont("Helvetica", 8)
        canv.setFillColor(GREY)
        canv.drawString(MARGIN, A4[1] - MARGIN + 14, HEADER_LEFT)
        canv.drawRightString(A4[0] - MARGIN, A4[1] - MARGIN + 14, header_right)
        canv.drawString(MARGIN, MARGIN - 15, title)
        label = "Page %d" % canv.getPageNumber()
        if total:
            label += " of %d" % total
        canv.drawRightString(A4[0] - MARGIN, MARGIN - 15, label)
        canv.restoreState()

    frame = Frame(MARGIN, MARGIN, A4[0] - 2 * MARGIN, A4[1] - 2 * MARGIN, id="f")
    doc = BaseDocTemplate(out_path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN,
                          title=title, author=RESEARCHER)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
    doc.build(story, canvasmaker=lambda *a, **kw: _CountingCanvas(*a, _counter=counter, **kw))


def make_docs(out_path, title, header_right, story, two_pass=True):
    """story: a list of flowables, OR a zero-arg callable returning a fresh list.

    Pass a callable when you want the "Page X of Y" footer (two passes consume the flowables,
    so the second build needs a fresh story).
    """
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
