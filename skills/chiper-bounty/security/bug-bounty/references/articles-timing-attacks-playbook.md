# Timing Attacks & XS-Leak Timing — Research Articles Compendium

> Source: 2 PortSwigger Research articles, 2019-2024 (Kettle, Saftnes/Heyes). Extracts: `_portswigger-extracts/articles/`. Complements: `articles-css-exfil-xsleak-playbook.md`, `race-conditions-playbook.md`.

## Article Map

| Year | Title | Contribution |
|---|---|---|
| 2024 | Listen to the whispers: web timing attacks that actually work | Single-packet timing, scoped SSRF detection, blind injection probes, Param Miner integration |
| 2019 | Abusing jQuery for CSS powered timing attacks | `$(location.hash)` + `:has`/`:contains` selector → binary-search data exfil |

## Key Techniques

- **Signal vs noise doctrine** — signal = timing difference to detect; noise = network jitter + server jitter. Repeated measurements scale poorly (billions needed once noise dominates). Maximize signal (slow code path, delay amplification: nested XML entities, ReDoS, ORM/GraphQL workload multiplication, 256 headers w/ fixed prefix `X-Uaa: a...`) + minimize noise (shortest code path, caching, connection reuse).
- **Single-packet attack (timing variant)** — HTTP/2: send request headers, withhold empty DATA frame, ping frame forces OS coalescing of header frames, then send final frames together → both requests processed simultaneously; compare response ARRIVAL ORDER not absolute time (eliminates network jitter entirely). Detectable differential: 200μs. Built into Burp; OSS: h2spacex.
- **Hidden attack surface via timing** — Param Miner + 'response time' attribute: compare bottom quartile of 2×30 measurements; distinct = valid hidden param/header/cookie. Findings class: cache-keyed params (`?id=` slow = keyed → parameter-based cache poisoning exposure), JSON-parsing headers (`commonconfig: {}` fast), even connection-reset servers leak via reset delay.
- **IP spoofing detection** — `True-Client-IP: xyz.example.com` slower than random header = in-band DNS lookup = spoofable header (rate-limit bypass, forged logs, access control). DNS caching: 3rd request faster. ~170/375 found domains had NO pingback — invalid IP (x.psres.net) threw exception → skipped slow geo-lookup: timing detects EXCEPTIONS too.
- **Blind injection underclass** — timing shines when WAF blocks sleep/classic payloads: JSON escape `\` differential (200μs faster = parser hit), blind server-side parameter pollution (encoded `%23` vs `%21` timing diff = SSPF probe), error-triggered fast paths. Fully blind SQLi w/ sleep available = DON'T use timing (detection worse than OAST).
- **Scoped SSRF detection (kill feature)** — reverse proxy routes Host header but scoped to own subdomains → no pingback possible. Detect: same-host twice → 2nd response faster = DNS cache hit = server DID try to resolve. DNS-nocache variant: 64-octet DNS label (`aaa{63}.example.com`) → client refuses lookup → faster = negative proof.
- **Reverse proxy exploitation chain** — Detect scoped SSRF (Param Miner) → 'Exploit scoped SSRF' find alternate routes (vhost brute via Sonar fdns reversed+sorted+`look` binary search) → firewall bypass (route to internal-only sonarqube), front-end rule bypass, front-end impersonation (trusted headers via alternate route skip overwrite: New Relic `Service-Gateway-Is-Newrelic-Admin` full internal API compromise) → chain w/ subdomain takeover DNS→IP = full SSRF.
- **CSS/jQuery timing (client-side)** — `$(location.hash)` in hashchange event + `:has(*:has(*):parent...)` slow selector chain + `:contains('char')` → binary search per-char via JS timing → extract non-input text (displayed full name). Space URL-encoded on Firefox → CSS hex escape `\000020` padding. End-of-string detection: 6 backtracks. Needs: hashchange firing + URL decode of hash.

## Payload / Bypass Table

| Probe | Fast (baseline) | Slow (signal) |
|---|---|---|
| Hidden param | `?foo=x` 22ms | `?id=x` 310ms (keyed/processed) |
| Header JSON | `commonconfig: x` 55ms | `commonconfig: {}` 50ms |
| IP spoof DNS | `random-header: x` 65ms | `True-Client-IP: xyz.example.com` 70ms |
| Scoped SSRF | `abc.example.com` 1st 25ms | same host 2nd 20ms (DNS cache) |
| DNS refuse | `aaa{62}.example.com` 25ms | `aaa{63}.example.com` 20ms |
| Blind JSONi | `key=a\"bb` 24.3ms | `key=a"\bb` 24.1ms |
| SSPF probe | `%21` 430ms | `%23` 180ms |
| WAF timing | small body | repeat `exec` param stacks delay → nowafpls bypass |
| jQuery exfil | `:contains('a')` miss | `:contains('d')` + slow `:has` chain |

## By-Design / SKIP Filters

- Sleep-capable injection (classic blind SQLi): timing-based detection inferior → use `||sleep(5)||`/OAST, don't report timing as the finding.
- Timing differential without identified mechanism: carry assumptions lightly — WAF processing ≠ RCE (the 'exec' param case). Misidentified = false positive.
- Absolute-time claims are meaningless across targets — never benchmark a lab differential and port the number.
- reCAPTCHA-token constant-time comparison: real-world exploit requires PoC; theory-only = don't claim.
- jQuery selector attack: needs hashchange handler + `$()` + interesting data — one missing = dead chain. Modern jQuery patched hash XSS but selector-timing pattern persists.
- DoS-adjacent amplification (CPDoS, resource consumption): only with program permission; unauthorized DoS = out of scope.

## Severity Guide

- **HIGH** — scoped SSRF → front-end impersonation (auth header injection → internal API compromise); firewall bypass to internal/pre-prod systems.
- **MED/HIGH** — spoofable IP header w/ proven impact (rate-limit bypass, access-control bypass w/ evidence); blind JSON/SSPF injection w/ exploitable structure manipulation.
- **MED** — scoped SSRF confirmed but alternate routes benign; hidden keyed param enabling cache poisoning setup.
- **LOW** — timing differential confirmed, mechanism identified, no exploit path.
- **INFO** — differential without mechanism understanding; DNS-cache-only signal.
- Unproven differential (no bottom-quartile separation) = not a finding. Blocked chain = INFORMATIONAL per master KB.

## Reporting Checklist

- [ ] Show probe pairs w/ timings (min 30 measurements, bottom-quartile comparison) — table in report.
- [ ] Identify the mechanism: DNS lookup / parser hit / exception path / WAF processing — state evidence for each.
- [ ] Single-packet: confirm HTTP/2 + response-order bias ≥80% over ≤50 pairs (Param Miner methodology).
- [ ] Scoped SSRF: DNS-cache pair + 64-octet negative control + alternate route table (direct vs proxied).
- [ ] Exploit chain: screenshot final impact (internal system access, spoofed session).
- [ ] jQuery: PoC video/screenshot showing extracted chars + selector used + hashchange handler source.
- [ ] Rate-limit: confirm no per-IP 1-5ms rate limit defeated the attack (defence check).
- [ ] Blocked chain (differential only) ⇒ INFORMATIONAL per master KB.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
