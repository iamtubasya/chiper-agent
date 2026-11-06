# CDN / Static Subdomain WAF Bypass

## Pattern
When main domain (e.g. `www.target.com`) returns 403 via WAF, check static/CDN subdomains
for the same content served WITHOUT WAF. CDN origin often pulls from the same backend
but routes through a different CDN provider (ImageKit, CloudFront, Fastly) without WAF.

## Discovery
1. **Certificate transparency**: crt.sh for `*.target.com` → find static/image/cdn subdomains
2. **Subfinder/Amass**: enumerate all subdomains, filter for static/image/cdn patterns
3. **Common naming**: `images-static.*`, `static.*`, `cdn.*`, `assets.*`, `media.*`, `img.*`

## Verification
```bash
# Compare WAF response vs CDN response
curl -sL -o /dev/null -w "%{http_code}" "https://www.target.com/path"     # 403 (WAF)
curl -sL -o /dev/null -w "%{http_code}" "https://images-static.target.com/path"  # 200 (bypass)
```

## What to test through the bypass
1. **robots.txt** — reveals allowed/disallowed paths, hidden endpoints
2. **gateway-api/** — backend API endpoints proxied through CDN
3. **test.html / test** — SPA entry points with full app config
4. **Any path** that returns 403 on main domain

## Data extraction via bypass
- `window.__PRELOADED_STATE__` — React state with Firebase config, feature flags, API keys
- `window.__NYKAA_CONFIG__` / `window.__APP_DATA__` — app configuration
- CSP policy — reveals all third-party integrations
- Feature flags — security controls (captcha enabled/disabled, auth requirements)
- Internal API structure — endpoints, query params, data models

## Case Study: Nykaa (2025-09)
- **Main domain**: `www.nykaa.com` → all paths return 403 (WAF)
- **CDN bypass**: `images-static.nykaa.com` (ImageKit.io behind CloudFront)
- **Evidence**:
  - `/robots.txt` → 200 (main: 403)
  - `/gateway-api/omsApis/helpCenter?domain=NYKAA` → 200 (main: 403)
  - `/test.html` → 200, 634KB full Nykaa SPA
  - `/test` → 200, canonical `http://www.nykaa.com/test`
- **Extracted**:
  - Firebase: `nykaa-android-1224`, API key, storage bucket, messagingSenderId
  - Feature flags: `signupCaptcha: false`, `loginCaptcha: false`
  - Kong API proxy config
  - All A/B test configs
  - Internal domain list: `api.nykaa.com`, `prod-events.nykaa.com`

## Severity mapping
| Finding | Severity | Notes |
|---------|----------|-------|
| WAF bypass via CDN | Medium-High | Bypasses all WAF protections (rate limit, IP block, geo) |
| Config/credential leak via bypass | Low-Medium | Firebase keys, feature flags, API structure |
| Captcha disabled in feature flags | Low | May enable automated abuse |
| Firebase rules_version="1" | Low | Old security rules format |

## Pitfalls
- CDN may cache aggressively — stale content, not live backend
- Some CDN paths are rewrite rules (e.g. `test` → `test.html`) — check both
- API endpoints through CDN may return HTML fallback (SPA routing) not JSON
- Firebase keys in client-side code are EXPECTED to be public — severity depends on what they unlock
- Always compare response sizes: CDN serving 634KB vs main domain 403 is clear evidence
- Canonical URL in `<link rel="canonical">` confirms CDN serves same origin as main domain
