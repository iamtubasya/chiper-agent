# Evidence Image Rendering

## make_evidence.py prefix-filter pitfall (2026-10-23)
`scripts/make_evidence.py` keeps ONLY lines matching its hard-coded PoC-output prefixes
(see its filter fn) and silently drops everything else. Feeding it arbitrary/custom
evidence text (a validation log you wrote by hand) yields a near-empty image — a 40-line
log rendered as ~5 lines / 294px tall. Always check the rendered PNG dimensions before
embedding; if the height is tiny, the filter ate your lines.

## Custom Pillow renderer for arbitrary evidence text
When the evidence is NOT tool output carrying the expected prefixes, render it directly:

```python
from PIL import Image, ImageDraw, ImageFont
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
def wrap(s, n=118):
    out = []
    while len(s) > n: out.append(s[:n]); s = s[n:]
    return (out + [s]) if s else out
lines = []
for raw in txt.splitlines():
    k = "ok" if ("CONFIRMED" in raw or "RESULT" in raw) else \
        ("hl" if ("attacker" in raw.lower() or "payload" in raw.lower() or "pwn" in raw) else "")
    for w in wrap(raw): lines.append((w, k))
pad, bar, pitch = 16, 28, 25
H = pad*2 + bar + pitch*len(lines)
im = Image.new("RGB", (1600, H), (18, 20, 26)); d = ImageDraw.Draw(im)
d.rectangle([0, 0, 1600, bar], fill=(28, 38, 58))
d.text((pad, 5), title, font=font, fill=(150, 210, 255))
colors = {"": (205, 212, 224), "ok": (70, 235, 130), "hl": (255, 110, 110)}
y = bar + pad
for w, k in lines:
    if w: d.text((pad, y), w, font=font, fill=colors.get(k, colors[""]))
    y += pitch
im.save(out)
```

Legibility bar (user rejects cramped images): width ~1600, font ~16, pitch ~25, wrap ~118,
dark background, colour-code RESULT/CONFIRMED green and payload/attacker red. Keep the
browser screenshot as separate visual corroboration and embed both.

## SKILL.md is at the 100k-char limit
As of 2026-10-23 this skill's SKILL.md is ~100.4k chars (limit 100k) — patches that ADD
text are refused. Capture new lessons as `references/` files (like this one) until the
SKILL.md is split. A future curator task: split SKILL.md so it drops back under limit.
