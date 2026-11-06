# Reference: Viability Gate & Policy Fetch (BBflow §2-3)

> Jalankan SEBELUM deep recon. Max 5 menit. Kalau target buntu di sini, drop & pivot.

## Quick Viability Gate

### 1. CDN/WAF check — curl main domain + API
- 403 "Just a moment..." / "Access Denied" → Cloudflare/Akamai block.
- Empty body / redirect / HTML shell → SPA atau framework.
- Both main + API blocked → skip unless browser bypass works.

### 2. API pulse — probe `/api/v1/ /api/ /graphql /rest/v2/ /occ/v2/`
- All 404 → API di host/path lain.
- All 403 → auth-gated, butuh credentials.
- All 401 → butuh API key.
- All 200/404 dengan data asli → full recon.

## Decision Matrix

| Skenario | Keputusan |
|----------|-----------|
| CF/Akamai on all + browser blocked | **DROP** |
| Geo-blocked | **DROP** |
| API accessible | focus di sana |
| All 401 | butuh key — cari di JS/source/leaks |
| Full data | **recon deep** |

## Policy Fetching (programmatic)

**HackerOne:**
```bash
curl -sk "https://hackerone.com/<handle>?type=team" -H "Accept: application/json"
```
→ JSON berisi full `policy` markdown + flags (`only_cleared_hackers`, `rejecting_submissions`).

**YesWeHack:**
```bash
curl -sk "https://api.yeswehack.com/programs" -H "Authorization: Bearer $TOKEN"
# scope per-program: https://api.yeswehack.com/programs/<slug> (tanpa /api/v1/)
```
→ `{pagination, items}`; parse policy untuk: "bypasses" sections, OOS list, reward ranges, gates yang block submission.

**Wajib dibaca sebelum recon:**
- OOS list — "information disclosure without exploit" kill semua source-map/version/error-message angles.
- Bypass section — security-product programs sering mark "bypasses" sebagai Informative.

## ⛔ Common By-Design / Informational False Positives (DO NOT REPORT)

These patterns REPEATEDLY get rejected by triagers. If your finding matches ANY of these, it is NOT reportable:

### 1. Third-Party Service Defaults
- **Cloudinary unsigned upload presets** — designed for public use. Not a misconfig unless preset exposes RESTRICTED data.
- **Cloudinary CORS `Access-Control-Allow-Origin: *`** — Cloudinary default. Not a target misconfig.
- **Firebase open rules, Algolia search-only keys** — service design defaults.

### 2. Client-Side SDK Keys (ANY key in JS bundles)
- Auth0 client IDs (RFC-mandated public endpoint)
- Stripe `pk_live_*` / `pk_test_*` (designed to be public)
- Datadog RUM tokens, Pendo app IDs, LaunchDarkly client IDs
- Segment write keys, Amplitude API keys
- **VRT explicitly states:** "SDK/API Keys in Client JS ≠ Disclosure of Secrets"

### 3. OIDC / Auth0 Public Endpoints
- `.well-known/openid-configuration` — RFC 8414 mandated public endpoint
- JWKS endpoints (`/oauth2/certs`) — public by design
- Client IDs in authorization URLs — public

### 4. Static Assets on CDN
- SVG/PNG files on CloudFront/Cloudflare CDN without sensitive data
- Build version numbers in JS bundle filenames (`/v2/2.0.2289/index.js`)
- Source maps (if they don't contain secrets)

### 5. CORS on Public Auth Endpoints
- Auth0 `Access-Control-Allow-Origin: *` on `/oauth/token`, `/userinfo` — expected for public auth endpoints
- CORS reflecting origin on endpoints that don't set credentials — no credential leakage possible

## VRT Comparison Pitfalls

### Downloading VRT JSON
`execute_code` sandbox CANNOT access `/tmp/` — use home dir instead:
```bash
curl -sL "https://raw.githubusercontent.com/bugcrowd/vulnerability-rating-taxonomy/master/vulnerability-rating-taxonomy.json" -o ~/vrt.json
```
Then in Python: `open(os.path.expanduser("~/vrt.json"))`

### VRT Priority = None
If a VRT category has no baseline priority (`priority: null`), researcher argues severity with evidence. This is expected — not all findings map to pre-defined priorities.

### Common VRT Mappings for Web/API
| Finding Type | VRT Category | Typical Priority |
|-------------|-------------|-----------------|
| CORS misconfig | `unsafe-cors` | None (argue) |
| Information disclosure | `sensitive-data-exposure` | P4-P5 |
| Missing security headers | `missing-security-header` | P5 (informational) |
| Open redirect | `open-redirect` | P3-P4 |
| IDOR | `idor` | P2-P3 |
| SQL injection | `sql-injection` | P1 |
| Auth bypass | `authentication-bypass` | P1-P2 |