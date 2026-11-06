# Evidence rendering for PoC PDFs — pitfalls + a filter-free renderer

Session detail (SendSafely Dropzone postMessage PoC, 2026-10-23). The PoC PDF
embeds two kinds of evidence: a browser screenshot and a rendered text log of the
3x-validation output. The text-log renderer is where time was lost.

## PITFALL — `scripts/make_evidence.py` silently drops non-matching lines

`make_evidence.py` keeps only "meaningful evidence lines" filtered by hardcoded
prefixes (RESULT / CONFIRMED / ok-style markers). A custom evidence log that does
not use those prefixes is mostly discarded:

- Input: a 40-line 3x-validation transcript.
- Output: `evidence_validation.png` at **1500x294**, tool printed `lines=5`.
- The `lines=N` the tool prints is NOT proof the image captured the file — it
  reports how many lines *survived the filter*, not how many you fed it.

Two fixes:
1. Prefix every evidence line so it matches the filter, or
2. For arbitrary text, skip the filter and render directly (below).

Always sanity-check the PNG: **height must scale with content.** A ~300px-tall
strip for a 40-line log means the renderer ate the input.

## Filter-free PIL renderer (copy-paste)

Consolas on Windows; wraps long lines; colour-codes result/attacker lines. No
prefix dependency, nothing silently dropped.

```python
from PIL import Image, ImageDraw, ImageFont
import os
FONT = next(p for p in ["C:/Windows/Fonts/consola.ttf","C:/Windows/Fonts/cour.ttf"]
            if os.path.exists(p))
def _wrap(s, n):
    out = []
    while len(s) > n: out.append(s[:n]); s = s[n:]
    if s: out.append(s)
    return out or [""]
def render(txt, out, width=1600, fs=17, pitch=27, wrap=120, title=None):
    font = ImageFont.truetype(FONT, fs)
    lines = []
    if title:
        for w in _wrap(title, wrap): lines.append((w, "t"))
    for raw in txt.splitlines():
        if not raw.strip(): lines.append(("", "")); continue
        k = ("ok"  if ("CONFIRMED" in raw or "RESULT:" in raw) else
             "hl"  if any(x in raw for x in ("ATTACKER","attacker","packageCode","origin=http://127")) else "")
        for w in _wrap(raw, wrap): lines.append((w, k))
    pad, bar = 18, (30 if title else 0)
    H = pad*2 + bar + pitch*len(lines)
    im = Image.new("RGB", (width, H), (20,22,28)); d = ImageDraw.Draw(im)
    col = {"":(210,215,225),"ok":(80,230,140),"hl":(255,120,120),"t":(120,200,255)}
    y = pad
    if title:
        d.rectangle([0,0,width,bar], fill=(30,40,60))
        d.text((pad,6), title, font=font, fill=(150,210,255)); y = bar+pad
    for w,k in lines:
        if w: d.text((pad,y), w, font=font, fill=col.get(k, col[""]))
        y += pitch
    im.save(out); return im.size
```

Verify before embedding: `from PIL import Image; print(Image.open(out).size)` —
a 40-line log should be ~1100-1200px tall, not ~300px.

## Browser screenshot for the PDF

`Page.captureScreenshot` (CDP) → base64 → write PNG. The screenshot is
corroborating visual evidence; the rendered text log is the primary, greppable
evidence. Embed both. Record sha256 of each artifact in the report's evidence
section (see the disclosure pipeline reference for the sha256-attachment rule).
