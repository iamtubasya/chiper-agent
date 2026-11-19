---
name: chiper-dev
description: "Full-stack engineering plus design intelligence. Use for ANY UI/UX work — building or refactoring pages and components, choosing color palettes, typography, spacing, layout, charts, icons or motion, applying shadcn/ui + Tailwind, generating design tokens, reviewing accessibility, designing logos, brand guidelines, banners, social assets or HTML slide decks. Bundles a queryable catalog: 80 styles (51 active), 194 product palettes with reasoning, 74 font pairings, 130 UX guidelines, 105 icons, 17 GSAP presets, 25 chart types, 22 stacks. Keywords: ui, ux, design, desain, tailwind, shadcn, dark mode, responsive, a11y, contrast, palette, font pairing, design token, logo, brand, banner, slide, deck, mockup."
---

# Chiper-Dev — Engineering + Design Intelligence

Router for the eight sub-skills bundled under this category. Load the narrowest skill
that answers the question; do not read all eight.

## Routing table

| Task | Load |
|---|---|
| Warna/palette, font pairing, style/pattern halaman, UX rule, chart, ikon, motion, panduan per-stack | `chiper-dev-uiux` |
| Design token 3 lapis, spesifikasi komponen, validasi token, deck/slide | `chiper-dev-design-system` |
| Implementasi UI: shadcn/ui, Tailwind, tema, dark mode, canvas visual | `chiper-dev-ui-styling` |
| Logo, ikon SVG, CIP/mockup korporat, social photo, banner | `chiper-dev-design-assets` |
| Brand guideline, voice & messaging, konsistensi aset | `chiper-dev-design-brand` |
| Banner per platform (social/ads/hero/print) | `chiper-dev-design-banner` |
| Presentasi HTML + Chart.js | `chiper-dev-design-slides` |

Backend, API, debugging, arsitektur, devops, testing → pakai skill engineering biasa
(`fastapi-backend-architecture`, `systematic-debugging`, `modern-frontend-development`, dst).

## Katalog desain ada di disk (lokal, offline, tanpa API key)

```bash
SK="${CHIPER_HOME:-$HOME/.chiper}/skills/chiper-dev/chiper-dev-uiux"

# Design system utuh: pattern + style + palette + font + efek + anti-pattern + checklist
python "$SK/scripts/search.py" "beauty spa wellness service" --design-system -p "Serenity Spa"

# Domain spesifik
python "$SK/scripts/search.py" "keyboard focus modal" --domain ux
python "$SK/scripts/search.py" "fintech dashboard" --domain color
python "$SK/scripts/search.py" "editorial serif" --domain typography
python "$SK/scripts/search.py" "revenue trend" --domain chart

# Panduan per stack (nextjs, react, vue, angular, svelte, astro, laravel, flutter,
# swiftui, jetpack-compose, react-native, javafx, wpf, winui, avalonia, uno, uwp, threejs, ...)
python "$SK/scripts/search.py" "suspense streaming bundle" --stack nextjs

# Simpan jadi token/design system proyek
python "$SK/scripts/search.py" "<query>" --design-system --persist --tokens css -p "<Project>" --output-dir .
```

Output `--design-system` selalu memuat: pattern halaman, style + keyword, palette
(primary/secondary/CTA/background/text), font pairing + link Google Fonts, efek,
**anti-pattern yang harus dihindari**, dan pre-delivery checklist.

## Aturan keras

1. **Query dulu, kode kemudian.** Hex, nama font, dan skala spacing harus berasal dari output
   katalog — bukan karangan model.
2. **Aksesibilitas CRITICAL:** kontras ≥ 4.5:1, target sentuh ≥ 44×44 px, focus ring terlihat,
   `prefers-reduced-motion`, label tidak terpotong.
3. **Uji breakpoint** 375 / 768 / 1024 / 1440 px sebelum bilang selesai.
4. **Token > hardcode.** Warna/spacing/radius/typography lewat token; buktikan dengan
   `chiper-dev-design-system/scripts/validate-tokens.cjs`.
5. **Anti-pattern dilarang:** emoji sebagai ikon fungsional, hover-only affordance, teks di
   gambar, `div` sebagai kontrol, hex liar di komponen.
6. **Bukti, bukan klaim:** screenshot `agent-browser` atau output test sebelum menyatakan UI selesai.

## Catatan operasional

- Semua script Python di bundle ini **stdlib-only** (tanpa pip install), jalan offline.
- Katalog data (`data/*.csv`, termasuk 22 tabel stack) ikut ter-commit di repo. Kalau
  `search.py` balik kosong, cek dulu `ls "$SK/data"` — data hilang = instalasi rusak,
  bukan "tidak ada hasil".
- Path di dokumen sub-skill memakai `${CHIPER_HOME:-$HOME/.chiper}` supaya portabel antar
  server dan antar profil.
