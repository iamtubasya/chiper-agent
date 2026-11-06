# Cache Poisoning / Deception — Exhaustive Matrix

Companion to `hunt-cache-poison`. That file covers the two attacks + 7 disclosed citations. This
file is the **atlas** of every lever: unkeyed-input list, WCD extension list, cache-key oracle, and
CDN-specific quirks — so a CDN-fronted target gets walked field-by-field.

## 1. Unkeyed-input atlas (fire each, check reflection into body/cache-key)

```
X-Forwarded-Host        X-Host        X-Forwarded-Server
X-Forwarded-Scheme      X-Forwarded-Proto     X-Original-URL
X-Rewrite-URL           X-HTTP-Method-Override
Forwarded: host=evil.com
Origin                  X-Forwarded-Port
True-Client-IP          X-Real-IP
Range: bytes=0-
```
For each: add a distinct canary + cache-busting `?cb=<rand>`, then fetch WITHOUT the header from a
second client. Reflection + cache hit = poison. The second-client check is the whole finding.

## 2. Web Cache Deception — extension & delimiter list

```
/profile.css  .js  .jpg  .jpeg  .png  .gif  .ico  .svg  .avif  .webp  .txt  .pdf
/profile/.css        (trailing delimiter + static ext)
/profile%0a.css      (encoded newline — some origins split)
/profile%2f.css      (encoded slash)
/profile%2e%2ecss    (encoded dot-dot)
/profile;.css        (semi-colon path param)
/profile?x=.css      (query-with-ext)
```
Origin serves the dynamic page (name-normalization), CDN caches it as "static" — then fetch with
no auth. Proof = victim's authenticated data in an unauthenticated response.

## 3. Cache-key oracle (learn what the CDN keys on)

```
1. GET /path           -> note response, Age
2. GET /path?cb=RAND   -> different body? (query in key?)  Age resets?
3. GET /path  -H "X-Forwarded-Host: canary"  -> canary in body + cached under clean /path?
4. GET /path with a header the app reflects -> does the clean fetch see it?
```
Any input that CHANGES the response but does NOT change which cache entry is returned = a
poisoning surface. Enumerate query params, headers, and cookies separately.

## 4. CDN-specific quirks (what breaks a naive test)

| CDN | quirk to account for |
|---|---|
| Cloudflare | strips `/Vary/` on some asset types; Cache Deception Armor allowslist only covers known ext (`.avif`/`.webp` were the historical holes) |
| Fastly | keys on `Surrogate-Key`/`Surrogate-Control`; respects `Vary` more strictly → test Surrogate headers |
| Akamai | hop-by-hop smuggling across proxy tiers (Content-Length desync) → server-side edge poison |
| GCP | `X-HTTP-Method-Override: HEAD` can store an empty body under a GET key |
| Varnish | `hash_data()` is config-defined — default keys on Host+URL only, everything else unkeyed |
| nginx proxy_cache | `proxy_cache_key` default = scheme+host+URI+args; custom keys often omit args |

## 5. Poisons by effect (what the poisoned entry does)

```
body reflection (no escape)  → mass stored XSS
Location / redirect          → mass open redirect  / redirect-to-attacker
Set-Cookie                  → session fixation at scale
4xx/5xx error body          → mass DoS (poison a legit asset with 404)
CORS ACAO permissive        → credentialed cross-origin read for victims
```

## 6. Escalation rung

```
rung 1  unkeyed input reflected, not cached      → not a finding (no shared cache)
rung 2  reflected + cached + 2nd client confirms  → Medium-High
rung 3  cached response carries auth data (WCD)   → High (data exposure / ATO)
rung 4  cached response executes as code (XSS)    → Critical (mass stored XSS)
```
"Only my own browser sees it" = self-cache = never report. The second-client (or incognito/IP)
fetch is the gate.