# Verifying PDF layout geometrically (no vision model needed)

`qa_pdf_layout.py` catches stranded headings / overlap / margin faults, but "does any text actually
overflow the frame" is checkable deterministically. Use this as the verification step on every
rebuild, and as the fallback when a screenshot/vision pass is unavailable or erroring.

## The overflow scan

```python
import pymupdf
d = pymupdf.open(path)
M, W, H = 54.0, 595.28, 841.89          # A4, MARGIN = 54pt  (gate: --margin-mm 19.05)
for i, p in enumerate(d):
    for b in p.get_text("blocks"):
        x0, y0, x1, y1 = b[:4]
        if x0 < M-1.5 or x1 > W-M+1.5 or y0 < M-25 or y1 > H-M+18:
            print(f"p{i+1} x0={x0:.1f} x1={x1:.1f} y0={y0:.1f} y1={y1:.1f} :: {b[4][:60]!r}")
```

### Whitelist the running footer

`report_style_structured` draws the footer at `drawString(MARGIN, MARGIN-18, title)` — deliberately
*below* the frame. It therefore always lands in the overflow list at roughly `y0≈797`, x spanning
the full frame width.

So the rule is:

- **One predictable footer block per page** = clean output.
- **Body text** at those coordinates = real defect.
- Confirm the flagged string actually matches the document title before dismissing it — don't
  whitelist by coordinate alone.

## Required-string assertions

A layout-clean file can still be missing a section. Assert content presence too:

```python
t = "".join(p.get_text() for p in d)
for k in ("What this is NOT", "On severity", cvss_string, primary_endpoint, proof_value):
    assert k in t, k
```

Pick `k` values that would only appear if the section rendered — the disclaimer headings, the
exact CVSS vector, the endpoint path, and the distinctive proof value (the leaked field, the code,
the total). A truncated table cell or a swallowed section fails this immediately.

## Why both

Geometric scan answers "did anything spill outside the frame"; string assertions answer "did the
content survive". Together they are stronger than a visual glance, and re-runnable on every
rebuild in under a second.

## Page count

```python
print("pages:", len(d))
```

Log it alongside the verdict so a rebuild that silently grows/shrinks is visible.
