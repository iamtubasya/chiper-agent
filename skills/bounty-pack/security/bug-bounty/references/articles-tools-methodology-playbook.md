# Tooling & Research Methodology — Research Articles Compendium

> Source: 6 PortSwigger Research articles on tooling/automation/attacker workflow, 2015-2025 (Kettle, Fedotkin, Heyes). Extracts: `_portswigger-extracts/articles/`.

## Article Map

| Year | Title | Contribution |
|---|---|---|
| 2019 | Turbo Intruder: embracing the billion-request attack | Racing/bruteforce engine, gate system, decorators, headless CLI |
| 2019 | Cracking reCAPTCHA, Turbo Intruder style | Last-byte sync + second-order race on token validation |
| 2025 | WebSocket Turbo Intruder: unearthing the goldmine | WS message fuzzing, HTTP adapter, server-side proto pollution |
| 2023 | How to build custom scanners for research automation | Automate smallest manual step, expect unexpected, automate triage |
| 2017 | Adapting Burp extensions for tailored pentesting | Fork/patch extension workflow (Gradle fatJar, BappManifest) |
| 2015 | Burp Clickbandit | JS clickjacking PoC generator (multi-click, blur detection) |

## Key Techniques

- **Turbo Intruder core** — hand-coded HTTP stack, flat memory for multi-day attacks, Python-configured (%s injection point). Filter junk via `handleResponse(req, interesting)` + `@MatchStatus`/`@MatchSizeRange` decorators; 'learn' requests teach baseline. Stream wordlists line-by-line (never `readlines()` — RAM). Engines: THREADED (default), BURP/BURP2 (stability+proxy), HTTP2.
- **Race/gate system** — `engine.queue(req, gate='race1')` for all, then `engine.openGate('race1')` → last-byte synchronization: send all-but-last-byte, release simultaneously. Benchmark: 5 threads 2.7ms window → full-establish 1.4ms → last-byte 0.7ms. Race conditions cluster (shared shaky libs) — one hit ⇒ probe siblings.
- **reCAPTCHA race (second-order)** — token validated server-to-Google; race the TARGET's validation not Google's: Turbo→Target→Google chain. Token reusable a few times at speed ⇒ TOCTOU on registration/vote/post + captcha cost ÷3. Fix: app-side lock/sync on g-recaptcha-response.
- **WebSocket Turbo Intruder** — thousands msgs/sec, custom Python per-message, smart filtering; HTTP adapter integrates WS probes into existing HTTP scans; CLI + debug mode. Use for WS-specific vulns: server-side proto pollution via WS payloads, WS race (connection stays open = perfect sync), ping-of-death variants. Custom engine flaky → fall back to Burp engine.
- **Custom scanner methodology (Kettle)** — (1) Identify opportunity: familiarity + novel tooling + test-bed in days. (2) Automate the SMALLEST earliest manual step (probe phase, not full exploit). (3) Don't encode expectations — report ANY unexpected status diff (avoid false negatives; FP triage later). (4) Make iteration painless (select-all-in-proxy → scan). (5) Automate triage by observing your own filters: timeouts out, 429=rate-limit out, 502/503=back-end out, cache-busters in. Found races in parsing (400 under sync = desync hint), SSO back-end URL disclosure.
- **Extension patching workflow** — BAppStore → View Source → git clone; Java: JDK+Gradle, verify `gradle fatJar` build FIRST from BappManifest.bmf; patch (e.g. Collaborator Everywhere + HUNT SSRF params), load jar via Extender→Add. Keep fork local if it upsets sites.
- **Clickbandit** — Burp menu → copy script → paste in victim-page dev console → record clicks (blur event + mouseover flag for iframe multi-click) → review mode (zoom/transparency/arrow keys) → save PoC HTML. For clickjacking reports: state state-changing action + no X-Frame-Options/frame-ancestors + recorded PoC.

## Payload / Workflow Table

| Task | Tool | Key config |
|---|---|---|
| Race condition | Turbo Intruder | race.py, gate=, openGate() |
| Captcha TOCTOU | Turbo Intruder | race on validation endpoint |
| Brute/enum millions | Turbo Intruder | streaming loop + decorators |
| Param discovery | Param Miner | 'response time' attr, bottom-quartile |
| Scoped SSRF | Param Miner | Detect/Exploit scoped SSRF scans |
| WS fuzzing | WS Turbo Intruder | per-msg python, HTTP adapter |
| Hidden routes | Param Miner | vhost wordlist + Sonar fdns |
| WAF bypass probe | nowafpls / timing | body-size threshold stacking |
| Clickjacking PoC | Clickbandit | record → review → save HTML |
| Custom extension | Gradle fatJar | BappManifest.bmf BuildCommand |

## By-Design / SKIP Filters

- reCAPTCHA race: Google declined fix (2019) — burden on site; report site-side TOCTOU impact, not "Google is vulnerable".
- Turbo Intruder CLI: basic, no auto-filtering — don't use as primary workflow, only headless/server runs.
- WS Turbo custom engine errors → switch Engine.BURP before concluding target unreachable.
- Race found without state-changing exploit (only 50X anomaly) = probe result, not finding — escalate or drop to INFO.
- Scanner FPs (429/502/503/timeout) are triage noise — never report untriaged scanner output.
- Clickbandit needs same-origin console injection during TEST — that's fine; but clickjacking finding itself needs frame-busting absence check.

## Severity Guide

- **HIGH** — reCAPTCHA race enabling protected-action abuse (vote/review/registration at scale, proven); WS race w/ state corruption.
- **MED** — captcha bypass tripling abuse capacity on secondary actions; desync-hint sync-400 confirmed as smuggling.
- **LOW** — hidden param/route enumeration without exploitable impact.
- **INFO** — scanner anomalies untriaged; timing-only race hints.
- Methodology/tooling articles = no direct findings; use them to POWER the other playbooks. Blocked chain = INFORMATIONAL.

## Reporting Checklist

- [ ] Race: gate timing evidence (server-side window ≤1ms), before/after state diff (2 accounts/resources).
- [ ] Captcha: video/screenshot of N successful validations per token + action consequence.
- [ ] WS: message sequence + server state change proof.
- [ ] Custom scanner: describe probe + triage filters applied (show FP suppression) — no raw dump reports.
- [ ] Clickjacking: saved PoC HTML + sensitive action + missing frame-ancestors/XFO header capture.
- [ ] State tool version used (Turbo Intruder release, Param Miner build) for reproducibility.
- [ ] Blocked chain (anomaly only) ⇒ INFORMATIONAL per master KB.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
