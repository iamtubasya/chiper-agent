# Embedded PoC layout: the traps that survived every other check

Measured 2026-10 on a bWallet / b-Aware finding PDF. The report built cleanly, reported 6 pages, and passed
the entity scan and the BAD_WORDS scan — while every code block ran past the right margin.

## `Preformatted` does NOT wrap

`Preformatted(poc_src, CODE)` renders each line verbatim. Long PoC lines are simply clipped or overhang; the
frame boundary is not enforced and **nothing is raised**. Block bounding boxes came back at `x1 = 597pt`
against a right frame edge of `539pt`.

A geometry checker that only inspects prose paragraphs will not catch it, because the offender is the code
block — and long lines are exactly what a PoC contains.

Fix: wrap the source yourself before handing it to `Preformatted`, with a hanging indent so a continuation
still reads as one statement. `scripts/wrap_code.py` in this skill is the working helper; copy it in.

```python
CODE_W = 84          # Courier 9pt inside a 482pt frame, minus padding

def C(t):
    return Preformatted(wrap_code(t), CODE)
```

## Normalise the non-ASCII the source always carries

Code copied out of a repo contains em dashes in comments, curly quotes in strings, ellipses and bullets.
Some encode in Courier/Helvetica and some do not; all of them read badly and vary by viewer. Map to ASCII
before rendering:

```python
text = (text.replace("\u2014", "-").replace("\u2019", "'")
            .replace("\u201c", '"').replace("\u201d", '"').replace("\u2026", "..."))
```

Body prose is fine with `\u00b7`, `\u2019`, `\u201c`, `\u201d` and `\u2022` — the standard fonts carry those.
The problem is inside monospace blocks.

## Verify with block bounding boxes

After `doc.build`, reopen with pymupdf and compare **every text block's** bbox against the frame. This is the
cheap gate that catches overhanging code, and it is the check to run FIRST:

```python
import pymupdf
d = pymupdf.open(path)
W = d[0].rect.width
LM, RM = 20*2.8346, W - 20*2.8346          # margins in points (20 mm)
probs = [(i, round(b[0]), round(b[2]), b[4][:50])
         for i, pg in enumerate(d, 1)
         for b in pg.get_text("blocks")
         if b[0] < LM - 3 or b[2] > RM + 3]
assert not probs, probs
```

Order the whole gate:

1. **block bboxes vs frame** — overflow means body text may be clipped, so every later content assertion is
   untrustworthy until this passes.
2. entity scan `&[a-zA-Z]+;` → must be empty.
3. `BAD_WORDS` (watermark / draft / template / evaluation copy / sample) → must be empty. Fix the prose, never
   relax the checker.
4. marker strings present (finding id, revision, the PoC's distinctive identifier, `RESULT:` line, page
   footer).
5. table label integrity — assert multi-word labels survive intact (`"safety.nodecap.test.ts (embedded in
   section 9)" in normalised_text`), which catches a too-narrow `colWidths` that breaks labels mid-word.

Normalise whitespace before the string asserts (`re.sub(r"\s+", " ", text)`) — extracted text wraps at
arbitrary points, so a bare `in` test on a long label fails for layout reasons, not content reasons.

## When image inspection is unavailable

If the screenshot/vision path fails, that is not a blocker for the PDF itself. The bbox gate plus the
entity / BAD_WORDS / marker asserts are a complete programmatic verdict on layout and content. Report the PDF
as verified on those and name the one check you could not run. Never call a PDF "looks fine" without the bbox
pass — it is the only check that sees overhang.

## Generating generator source from inside a heredoc

When you patch or generate a reportlab script *from inside a shell heredoc*, a literal `\n` or `\t` in the
Python you are writing gets consumed by the outer layer and the file lands broken:

```
for line in text.split("
                       ^
SyntaxError: unterminated string literal
```

Build those characters with codes so nothing has to survive the shell:

```python
'    for line in text.split(chr(10)):'
'        line = line.replace(chr(9), "  ")'
'    return chr(10).join(out)'
```

Then `ast.parse` the file immediately, and only then run it. A mangled generator can appear to succeed while
writing a truncated PDF — always re-open the built file and run the gate.

## Skeleton that worked

```python
import os, re, html
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Preformatted, Table, TableStyle)

BODY   = ParagraphStyle("BODY", fontName="Helvetica", fontSize=11, leading=17, spaceAfter=8)
CODE   = ParagraphStyle("CODE", fontName="Courier", fontSize=9, leading=13.5,
                        spaceBefore=6, spaceAfter=8, backColor=colors.HexColor("#f2f2f2"),
                        borderPadding=6)

def esc(s):                     # escape ONLY for Paragraph text, never for Preformatted
    return html.escape(str(s), quote=False)

def T(rows, widths):            # widths in MILLIMETRES -> convert, or labels wrap mid-word
    data = [[Paragraph(esc(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    ...
```

Two reminders that already live in SKILL.md but bite here again: `colWidths` are **points** so a
millimetre list must be multiplied; and escape only `Paragraph` input — `Preformatted` takes raw text, so
`html.escape` there would print `&lt;` into the code block.
