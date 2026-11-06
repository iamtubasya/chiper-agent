# Web Cache Poisoning — Bug Bounty Playbook

> Source: PortSwigger Web Security Academy + "Practical Web Cache Poisoning" (2018) / "Web Cache Entanglement" (2020) research.
> Core: inject a harmful response via an **unkeyed input**, get it **cached**, serve it to other users. Two phases: elicit payload from back-end → get it cached.

## Quick Detection

| Step | Action | Signal |
|---|---|---|
| 1. Identify cache | Check resp headers: `X-Cache`, `Age`, `Cache-Control`, `CDN-Cache`, `Via`, `Cf-Cache-Status` | `HIT` / `Age>0` = cacheable |
| 2. Find unkeyed inputs | Param Miner → right-click → "Guess headers" (auto cache buster ON); or manual: inject random header, diff resp (Comparer) | Reflected header or altered response = unkeyed input |
| 3. Probe reflection | Try `X-Forwarded-Host: <collab>` etc.; check body/redirects | Input shapes generated content (links, script src, redirects) |
| 4. Confirm caching | Repeat same URL **without** the header | Poisoned content served from `HIT` = exploitable |
| 5. Map cache key | Vary path/query/headers one at a time | Key usually = request line + Host; rest is unkeyed |

Cache key = request line + Host typically. Unkeyed parts are ignored by the cache but can still shape the **cached** back-end response.

## Attack Vectors

- **Unkeyed header reflection → poison**: header reflected un-sanitized (e.g. `X-Forwarded-Host` into canonical links). Poison URL, victims with matching key get it.
- **XSS via unkeyed header**: reflect payload into script context / JS var (e.g. `X-Forwarded-Host` controlling script src → attacker-hosted JS).
- **Resource import / path poisoning**: back-end builds static-import paths from unkeyed header → import attacker JS/CSS ("static" ≠ safe).
- **Feed injection / JSONP**: unkeyed param controls JSON callback / feed URL → steal content / exec callback.
- **Cookie gadgets**: unkeyed cookie reflected into client-side DOM sink → XSS despite "unexploitable" reflection.
- **Multiple headers**: combine (one injects, another restores value) to bypass middleware/cache-suppression.
- **Fat GET / parameter cloaking**: body params on GET or `;`/delimiter params — cache and back-end parse differently → hide payload from cache key, deliver to back-end.
- **Normalized cache keys**: cache decodes/dedupes key but back-end doesn't (or vice versa) → smuggle params.
- **Unkeyed port**: port excluded from key → alternate-port requests share entries; redirects built from Host header.
- **Unkeyed query string**: entire query excluded from key → poison one URL, hit all variants.
- **Cache key injection**: inject into key generation via delimiters (e.g. Fastly `;` handling) to control keying of extra params.
- **Internal cache poisoning**: chain edge-cache poison to reach back-end/internal cache tiers.
- **Vary-header abuse**: cache trusts `Vary` (e.g. `Vary: User-Agent`) but browsers/CDNs honor it inconsistently → craft colliding keys.
- **cache_def digest tricks**: abuse digest/validator headers (`cache_def`, ETag variants) to force re-keying / bypass key validation.
- **GZIP/padding abuse**: unkeyed `Accept-Encoding` → serve decompressed/deflated body (content-shift entanglement).
- **DOM chain**: poison resource feeding a DOM sink → client XSS without server reflection.
- **Web cache deception (related)**: trick victim to request private page at cacheable path (`/profile/nonexistent.css`) → cache stores private data → attacker reads it.

## Payload / Bypass Table

| Goal | Technique |
|---|---|
| Safe testing | **Cache buster**: unique param every request (`?cb=1`); Param Miner auto-buster ON — never poison real users |
| Hit same cache entry | Respect `Vary` (iterate UA/lang); check `Cache-Control`/`Set-Cookie` (kills caching on many CDNs) |
| Cache lifetime | Binary search with timed polling on unique key; watch `Age`/`X-Cache: HIT` delta |
| Get response cached | Vary file ext (`.css/.js/.ico`), content type, status code (302s often cached), route, method, headers |
| Common unkeyed headers to try | `X-Forwarded-Host`, `X-Host`, `X-Forwarded-Scheme`, `X-Forwarded-Proto`, `X-Original-URL`, `X-Rewrite-URL`, `X-HTTP-Method-Override`, `X-Forwarded-Port` |
| Backend parses, cache doesn't | Fat GET body, `;`-params, duplicated params, weird encodings (cloaking) |

## By-Design Filters (SKIP — not vulnerabilities)

- `Cache-Control: no-store`/`private` on all responses; `Set-Cookie` present on every response (most CDNs skip caching).
- CDN strips/disables unkeyed headers by default; per-user nonce in key; empty `Vary` honored correctly.
- Reflecting attacker-controlled `X-Forwarded-Host` only in non-cacheable 4xx responses.
- Testing-allowed pages only; sandbox/preview domains.

## Severity Guide

| Severity | Criteria |
|---|---|
| CRITICAL | Persistent XSS / JS-import on high-traffic page; affects all matching-key users, zero interaction; re-poisonable |
| HIGH | XSS/redirect on limited or low-traffic scope; requires uncommon header; session/token leak via deception |
| MEDIUM | Defacement-only; short cache window; niche key-collision; no script exec |
| LOW | Header reflection or key quirks without proven exploit chain |
| INFO | Blocked/unproven chain (see footer) |

## Reporting Checklist

- [ ] Cache buster used on **every** probe request (prove no real users were hit).
- [ ] PoC: minimal raw request pair — poisoning request + victim `HIT` request (show `X-Cache`/`Age`).
- [ ] Payload non-destructive (`alert(1)` / unique marker), no real-attack content.
- [ ] Cache key elements enumerated (what's keyed vs unkeyed) + CDN/vendor identified.
- [ ] Cache duration measured; note re-poison feasibility.
- [ ] Impact: who is affected, page traffic, payload capability.
- [ ] Fix guidance included: key used headers, rewrite instead of excluding, disable fat GET, cache only true statics, disable unused CDN headers.

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
