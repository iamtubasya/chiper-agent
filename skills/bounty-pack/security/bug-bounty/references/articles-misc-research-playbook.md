# Misc Research & Researcher Craft — Research Articles Compendium

> Source: 3 PortSwigger Research articles — fuzzing (2018-2019) + research methodology (2018). Extracts: `_portswigger-extracts/articles/`. Catches remaining research topics + top-10 craft takeaways.

## Article Map

| Year | Title | Contribution |
|---|---|---|
| 2019 | Provoking browser quirks with behavioural fuzzing | Charset fuzz → parser quirks → XSS filter/sandbox escapes |
| 2018 | Unearthing ZalgoScript with visual fuzzing | Puppeteer screenshot diff → unicode combining chars = valid JS |
| 2018 | So you want to be a web security researcher? | Research methodology: breadcrumbs, iterate/invent/share |

## Key Techniques

- **Behavioural fuzzing (browser quirks)** — goal ≠ crash (memory corruption); goal = interesting BEHAVIOUR: chars that open/close tags abnormally, chars ignored by JS parser. Each quirk = XSS filter bypass / JS sandbox escape primitive. Workflow: generate char combos → render → detect behavioural diff (screenshot/pixel region diff) → classify (tag-opener, whitespace, quote).
- **ZalgoScript (visual fuzzing)** — Edge treated unicode combining chars (U+0300-034F) as whitespace (ChakraCore bug). Fuzzer: HTML page renders `String.fromCharCode(c).repeat(100)` (or pairs), extreme-wide CSS so legit chars overflow right; Puppeteer screenshots; node png.js checks non-white pixels in top/left/bottom regions = visual defect logged. Combining-pair loop 768-879, excluding 31 single-effect codepoints (834,1425,1430,1442-1447,1450,1453,1557,1623,1626,3633,3636-3642,3655-3662). Pair 837+any(768-858)×5 = Zalgo-wrapped but VALID JS: `combine(837,i)×5` → whitespace → `a[10]+='alert(';a[15]+='1';a[20]+=')';eval(join)` = filter-evading exec (WAFs don't flag zalgo).
- **Visual defect generation** — single chars w/ repeat: combining chars (see list); pairs: 311+844 → upward defects. Output = payload, e.g. zalgo + alert(1) executing on Edge.
- **Researcher craft (Kettle's methodology)** — (1) Hunt forgotten knowledge: read archives/old docs. (2) Collect diversity: docs as exploit manuals (FreeMarker), colleagues, white-box + pentest + bounty mix. (3) No idea too stupid (MySQL auth bypass CVE-2012-2122 = retry same password; Google admin via phone not laptop). (4) Abandon comfort: difficult/scary topics = low competition (request smuggling from 2005 doc → $70k in 2019). (5) Iterate: take someone's research + mix techniques + apply to live targets (CORS research → bounties). (6) Invent via breadcrumbs: chase everything that makes you say "this makes no sense" — Piwik PHP path handling → X-Forwarded-Host → Host header attacks lineage. (7) Share early: community catches prior art; blog not just X; always include one real-app exploit example.

## Payload / Bypass Table

| Technique | Condition | Payload |
|---|---|---|
| ZalgoScript | Edge/ChakraCore whitespace bug | `c(837,i).repeat(5)` strings + eval |
| Zalgo chars | filter visual-insensitive | fromCharCode(834).repeat(20) etc |
| Pair defects | visual mapping | 311+844 = upward drift |
| Quirk chars | HTML parser | fuzz tag openers/closers per charset |
| Whitespace bugs | JS parser | chars ignored → break token filters |

## By-Design / SKIP Filters

- ZalgoScript: ChakraCore/Edge-specific — Edge is Chromium now = historical only; treat as WAF-evasion DESIGN pattern (unicode-as-whitespace), test modern engines for equivalents.
- Browser quirk findings with no sink at target = research material, not a finding — quirk must connect to real filter/sanitizer bypass at a bounty target.
- Visual fuzzer needs wide-CSS rendering; chars rendering normally (right side) are not defects — don't report rendering-only oddities.
- Combining chars in user-input filters: if target normalizes unicode (NFKC) before filtering = dead chain → test normalization first.
- Methodology article = no exploit content — never cite as vulnerability evidence.

## Severity Guide

- **HIGH** — quirk-derived filter bypass → proven XSS at a target (chain: quirk + sink + exec).
- **MED** — filter/WAF evasion primitive proven against target's sanitizer (bypass shown, no exec chain yet).
- **LOW** — quirk reproduces at target but only affects display/parsing cosmetics.
- **INFO** — engine-level quirk with no target application; fuzzer artifacts without target context.
- Escalate quirk→bypass→exec chain before claiming; quirk alone = INFO. Blocked chain = INFORMATIONAL per master KB.

## Reporting Checklist

- [ ] State engine+version tested (legacy Edge/ChakraCore vs current Chromium/Firefox/WebKit) + retest on modern engines.
- [ ] Unicode normalization check at target (NFKC/NFC) — show payload survives pre-filter.
- [ ] Filter bypass: original filter source/policy + payload passing through + output evidence.
- [ ] Exec chain: alert(document.domain) screenshot at the actual target origin.
- [ ] Fuzzer setup (for custom research): render page + region check + codepoint ranges covered.
- [ ] Context: cite this as evasion TECHNIQUE, pair with the target finding it enables — not standalone.
- [ ] Blocked chain (quirk without sink) ⇒ INFORMATIONAL per master KB.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
