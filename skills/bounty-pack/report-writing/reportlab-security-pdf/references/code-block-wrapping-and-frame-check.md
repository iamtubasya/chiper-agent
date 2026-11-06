# Code blocks don't wrap: `Preformatted` overflows the frame, and the page-margin check misses it

Measured 2026-10-25 (bWallet b-Aware F1 disclosure PDF).

Embedding PoC source with `Preformatted(src, code_style)` put every code block past the right edge.
PyMuPDF block boxes reported `x1 = 597` against a document frame ending at `539` (20 mm margins on
A4, `frame_rm = 595.28 - 56.7`). The page still *looked* plausible in a viewer — nothing overlaps,
nothing is truncated on screen; it is the page that ends, not the line.

## Rule 1 — wrap the code yourself, in one helper

`Preformatted` does not soft-wrap. Route every code block through a wrapper:

```python
CODE_W = 84  # Courier 9pt inside a 482pt frame, minus padding

def wrap_code(text, width=CODE_W):
    # Courier cannot render these; they come out blank or as a box.
    text = (text.replace(chr(0x2014), "-").replace(chr(0x2019), "'")
                .replace(chr(0x201c), '"').replace(chr(0x201d), '"')
                .replace(chr(0x2026), "..."))
    out = []
    for line in text.split(chr(10)):
        line = line.replace(chr(9), "  ")
        if len(line) <= width:
            out.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        hang = " " * min(indent + 2, width - 8)      # continuation lines stay visually nested
        rest, first = line, True
        while len(rest) > width:
            cut = rest.rfind(" ", 0, width)
            if cut <= (0 if first else len(hang)):
                cut = width                          # no space to break on: hard cut
            out.append(rest[:cut] if first else hang + rest[:cut])
            rest = rest[cut:][1:] if rest[cut:].startswith(" ") else rest[cut:]
            first = False
        out.append(rest if first else hang + rest)
    return chr(10).join(out)

def C(t):
    return Preformatted(wrap_code(t), CODE)
```

Character width: Courier is ~0.6 em, so at 9 pt ≈ **5.4 pt per character**.
`width ≈ (frame_width_pt - 2*borderPadding) / 5.4`. A 482 pt frame → 84 chars.

Sanitise inside the wrapper, never per call site — one forgotten string reintroduces the box glyph.
Verify afterwards that the extracted text has no unexpected non-ASCII:
`{ch for ch in full if ord(ch) > 127}` should hold only the glyphs you deliberately used
(`·`, `“`, `”`, `•` came from Paragraph text, not code).

## Rule 2 — check against the FRAME, not the page

```python
import pymupdf
d = pymupdf.open(path)
W = d[0].rect.width
LM = 20 * 2.8346                 # 20 mm, in points
RM = W - 20 * 2.8346             # must equal BaseDocTemplate: pagewidth - rightMargin
for i, pg in enumerate(d, 1):
    for b in pg.get_text("blocks"):
        if b[0] < LM - 3 or b[2] > RM + 3:
            print("OUT-OF-FRAME", i, round(b[0]), round(b[2]), b[4][:50])
```

`scripts/pdf_layout_check.py` now does this too — pass the real edges:

```bash
python pdf_layout_check.py report.pdf --frame-lm 57 --frame-rm 539 \
    --tokens "RESEARCHER_NAME" "Page 1" "bAware-F1"
```

A page-margin heuristic is NOT enough: it allows everything up to `page_width - margin`, so a
breach that stops short of that renders outside its column and reads as clean. Measured case: frame
ends 539, page-margin rule allows 560 — a 550 breach would pass the old check.

## Rule 3 — a vision/screenshot pass is not the gate

The vision backend was unavailable during this session (connection error, twice). Even when it is
available, a screenshot review can miss horizontal overflow entirely because nothing overlaps and
nothing is visibly cut. Geometry is the source of truth; `problems=0` from the checker, with the
frame edges supplied, is the only pass.

## Order that worked

1. Build the story with all code blocks through `C()`.
2. `doc.build()`.
3. `pdf_layout_check.py --frame-lm … --frame-rm … --tokens …` → must be `problems=0`.
4. Assert presence of the markers a triager needs (the run's `RESULT:` line, the file/line citation,
   the test verdict) via whitespace-normalised text:
   `n = re.sub(r"\s+", " ", full)`; `"1 pass, 2 fail" in n`.
5. Only then attach to the draft.
