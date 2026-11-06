# Case: Kmart Australia (Bugcrowd VDP) — four independent block layers

Target: `https://kmart.com.au` / `https://target.com.au` (Bugcrowd VDP Pro, production only).
Edge: Akamai (AkamaiGHost). The audit stalled for environmental reasons, not tooling ones.
This file records the *measurements*, because the matrix is what made the blocker legible.

## The egress matrix (each cell measured more than once)

| egress path | www.kmart.com.au | api.kmart.com.au/gateway/graphql |
|---|---|---|
| Cloudflare WARP (104.28.194.248, ID) | 200 | `429 {"cpr_chlge":"true"}` |
| WARP off, ISP IP (103.129.150.89) | `403 Access Denied` | `403 Access Denied` |
| Vercel relay (`x-relay-target`) | 200 | `403 Access Denied` |
| headless chromium / python-urllib | 403 | 403 |
| camoufox (fingerprint-spoofed Firefox) | 200 | `429 {"cpr_chlge":"true"}` |
| visible real Chrome over WARP | 200 | `429 {"cpr_chlge":"true"}` |

## Layer 1 — geo/edge policy (403)
`403` with body from `errors.edgesuite.net` and a `Reference #18.xxxx.yyyy` id. The Indonesian
ISP IP was refused outright on both hosts. No header trick changed this.

## Layer 2 — bot challenge (429 cpr_chlge)
The Cloudflare WARP exit *passes* the geo policy but is classified datacenter/VPN, so it gets
Akamai Client Protection instead of content: `{"cpr_chlge":"true","t":"<int>"}`.
**Decisive evidence that this is IP-keyed, not fingerprint-keyed:** camoufox (spoofed Firefox
fingerprint, spoofed TLS/canvas) received the *identical* response as clean real Chrome. If
stealth fingerprinting were the answer, camoufox would have differed. It did not.
Conclusion recorded: stop investing in stealth browsers; the fix is a better IP.

## Layer 3 — client fingerprinting (curl 200 vs urllib 403)
Through the *same relay*, to the *same path* (`/api/health`), in the same second:
```
curl   -> 200
urllib -> 403
```
Attempted fixes that did NOT work: adding `Accept: */*`, `Accept-Encoding: gzip, deflate, br`,
`Accept-Language: en-AU,en;q=0.9`, `Sec-Fetch-Dest/Mode/Site`. All still 403.
Working fix: rewrite the enumerator to `subprocess.run(["curl", ...])`.
Symptom this avoids: a Python enumerator reports 100% 403 while manual curls return 200, and
you wrongly conclude the target is a fortress.

## Layer 4 — rate threshold (sticky, minutes)
Burst of ~20 requests → 403 for everything, including paths that returned 200 moments earlier.
The block then **sticks for several minutes**. Pacing at 3 s was still too fast; 6 s spacing
gave 8/8 × 200. Practical rule for this target: **≥6 s between requests, and never a burst**,
or the next run (even a correctly-paced one started too soon) inherits the block.

## Consequence: which surfaces were reachable
Reachable (200): `/`, `/api/health`, `/api/customer/visitor_id/`, `/robots.txt`,
`/sitemap-index.xml` + `/sitemap/au/*`, `/careers`, `/help`, `/about`, `/blog`,
`/store-locator`, `/checkout` (separate CRA SPA, 67 KB shell).
Path-blocked (403): `/account`, `/account/my-orders`, `/search/`.
Renders shell but unusable: `/login/`, `/register/` — **0 credential inputs, 0 captcha
widgets**, because the auth UI is GraphQL-driven and the API host is blocked.

Storefront page size is a reliable signal: the Next.js shell is ~1.61 MB, so anything in
1.60–1.70 MB is a catch-all, and unknown `/api/*` paths return **HTTP 200 + that 1.6 MB
error page** (soft-404) — status-code triage alone will mislead you.

## What NOT to conclude from this case
Do not write "Kmart's account/cart/checkout surface is secure". It was never reached. The
correct output is a coverage statement plus the access matrix.

## Useful extraction despite the block (zero requests)
- GraphQL operation names + argument signatures + returned PII fields: harvested from the
  `/track-order/` micro-frontend bundle (3.4 MB) and the checkout CRA bundle. See
  `references/api-surface-from-bundles.md`.
- Route inventory: the published sitemaps gave 2260 category routes, 122 marketplace sellers,
  309 store-detail pages, 57 collections, 132 content pages.
- robots.txt named the interesting paths: `/bag`, `/delivery/*`, `/checkout`, `/payment`,
  `/user/`, `/track-my-order*?*`, `*/undefined*`.
