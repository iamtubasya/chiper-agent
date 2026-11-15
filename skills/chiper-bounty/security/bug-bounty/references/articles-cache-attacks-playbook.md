# Web Cache Attacks — Research Articles Compendium

> Source: 5 PortSwigger Research articles (2018–2024) — Kettle (cache poisoning, countermeasures, DoS, entanglement) + Doyhenard (parser discrepancy poisoning/deception). Distilled for bug bounty hunting.

## Article Map

| Year | Short title | Core contribution |
|---|---|---|
| 2018 | Practical WCP | Unkeyed-header poisoning methodology; Param Miner; XSS/redirect/OG gadgets on real sites |
| 2018 | Bypass Countermeasures | Defeats Cloudflare WAF + cache-key mitigations (duplicate headers); dangerous patches |
| 2019 | Responsible DoS | Single-request persistent DoS via poisoning; real bounty value of cache DoS |
| 2020 | Cache Entanglement | Cache-key gaps: normalization, delimiters, fat GET, unkeyed query/method, gadgets |
| 2024 | Gotta Cache 'Em All | URL parser discrepancies → arbitrary cache poisoning AND cache deception at CDNs |

## Key Techniques

- **Cache key identification**: Run Param Miner to guess unkeyed headers/cookies (it watches for response changes). Always add a cache buster (`$randomplz` / `fcbz` param) so probes never poison real users. Default key ≈ method+path+query+Host; any input that changes the response but is unkeyed is poisonable.
- **Classic poisoning flow**: (1) find unkeyed input (X-Forwarded-Host, X-Original-URL, X-Forwarded-Scheme...); (2) make it land somewhere harmful — script src, og:image/og:url, canonical, Set-Cookie domain, Location; (3) prove the response is cached (CF-Cache-Status/X-Cache: HIT, or fetch clean from another machine); (4) escalate via gadgets (XSS, open redirect, JSONP, CSS/JS resource injection). `Age`/`max-age` reveal exact expiry timing; `Vary` enables selective (UA-targeted) poisoning.
- **Cache entanglement**: Attack keyed parts via parsing gaps — Host port stripped from key (redirect DoS); query string excluded from key (reflected XSS → site-wide stored); cache parameter cloaking (utm_ regex quirks, Rails `;` param delimiter); unkeyed method (POST stored under GET key); fat GET (body params not keyed — GitHub $10k); key normalization (nginx URL-decode → poison arbitrary paths, e.g. Firefox update takedown); key injection via unescaped delimiters (Akamai X-True-Cache-Key); internal fragment caches (WP Rocket) poison whole sites and allow blind intranet poisoning.
- **Countermeasure bypasses**: Duplicate headers (first benign, second payload) defeat Cloudflare's key-based mitigation; X-Forwarded-Host port override → persistent DoS; cacheable WAF block pages → single-request DoS; URL-encoding (`%6c`) evades "don't cache reflected-redirects"; discriminate caches via Cache-Control (private vs public), session-cookie presence, and per-region CDN nodes (target cache IP directly).
- **Web cache deception**: Instead of poisoning, trick the cache into storing a dynamic/sensitive response under a static-looking key. Origin delimiters (`;` Spring, `.` Rails, `%00` OpenLiteSpeed, `%0a` nginx rewrite) vs cache rules (static extensions .js/.css, static dirs /static,/assets,/wp-content, static files robots.txt/favicon.ico) — victim visits crafted link, their data gets cached under that key, attacker fetches tokens → account takeover.

## Payload / Bypass Table

| Technique | Unkeyed input | Impact |
|---|---|---|
| Header reflection | X-Forwarded-Host | Stored XSS via og:image/script src for all visitors |
| Route poisoning | X-Original-URL | Cache key ≠ backend path → wrong page / redirect hijack |
| Chained inputs | X-Forwarded-Host + X-Forwarded-Scheme | Arbitrary open redirect → CSRF token theft |
| Host port strip | Host: target:1337 | Persistent redirect-to-dead-port DoS |
| Unkeyed query | query excluded from key | Reflected XSS becomes site-wide stored |
| Fat GET | GET body params (Varnish/CF/Rack) | Parameter override → XSS / abuse flows |
| Unkeyed method | POST body on GET key | Persistent XSS on every page |
| Key normalization | `%3f`, dot-segments in key | Poison arbitrary high-traffic paths |
| Key injection | Origin w/ delimiter chars | Exploits "unexploitable" keyed-header XSS |
| Deception: static ext | `;`/`%23` + `.css` suffix | Victim's account data cached → token theft |
| Deception: static dir | `/static/..%2f/myAccount` | Arbitrary dynamic response cached |
| Cacheable WAF block | Any-Header: burpcollaborator.net | Cached 403 → single-request DoS |

## By-Design / SKIP Filters

- Reflection via unkeyed input with NO cached-response proof (no HIT to others) = INFO.
- DoS on purpose-built test pages only, or DoS with no path to core routes = SKIP.
- Cache-buster collisions, self-poisoning (own fcbz/proxy artifacts) = not a finding.

## Severity Guide

- Poisoned response provably served to other users (XSS/redirect/resource hijack) = MED/HIGH; homepage or script-src takeover = HIGH.
- Cache deception storing another user's tokens/PII = HIGH.
- Persistent single-request DoS on core functionality = MED (reception varies $0–$10k).
- Self-poisoning only / no third-party delivery = INFO.
- Blocked or unproven chain (no HIT evidence, no gadget) = INFORMATIONAL.

## Reporting Checklist

1. Cache oracle chosen (HIT/MISS header, timing, or dynamic-content tells).
2. Unkeyed input confirmed manually (Param Miner hit + resend), cache buster on every probe.
3. Reflection documented: request/response pair showing payload injected.
4. Cache proof: clean replay returns poisoned content (X-Cache: HIT).
5. Victim delivery proven from different IP/machine/browser with no special headers.
6. Safety: buster/PURGE used; no live-user poisoning; test paths marked (`dontpoisoneveryone`).
7. Gadget chain explained (why a normal visitor executes/redirects).
8. Severity per guide; unproven chains filed INFORMATIONAL.
9. Fix advice: disable/key unkeyed inputs, no fat GET, align cache+origin URL parsers, `Cache-Control: no-store` on dynamic responses.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
