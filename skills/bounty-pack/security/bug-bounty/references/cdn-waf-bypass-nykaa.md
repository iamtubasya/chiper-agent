# CDN WAF Bypass — Nykaa Case Study

## Summary
CloudFront CDN endpoint (`images-static.nykaa.com`) mengembalikan 200 OK untuk file yang di-WAF-blocked di origin (`www.nykaa.com` → 403). Alternate domain (`images-static.naikaa.com`) juga bypass — same ImageKit infra.

## Technique

### Step 1: Confirm WAF Block di Origin
```bash
curl -sI https://www.nykaa.com/ReactConfig.php
# → 403 Forbidden (WAF blocked)
```

### Step 2: Cari CDN Endpoint
Dari JS bundle atau HTTP headers, cari CDN domain:
- `images-static.nykaa.com` (dari JS bundle analysis)
- Pattern: `images-static.*`, `cdn.*`, `static.*`, `media.*`, `assets.*`

### Step 3: Test Bypass via CDN
```bash
curl -s https://images-static.nykaa.com/ReactConfig.php
# → 200 OK + JSON response
```

### Step 4: Test Alternate Domains
```bash
curl -s https://images-static.naikaa.com/ReactConfig.php
# → 200 OK (same infra, same bypass)
```

## Key Indicators
- **Different WAF rules per endpoint**: Origin WAF rules ≠ CDN WAF rules
- **Same origin server**: CDN proxies to same backend, but WAF layer differs
- **ImageKit infrastructure**: `images-static.*` domains often use ImageKit CDN which has its own WAF rules

## Cache Headers Analysis
```
Cache-Control: public, s-maxage=31536000  (1 year!)
Vary: Accept-Encoding                     (NO Vary: Cookie!)
```
- `s-maxage=1yr` = CDN caches aggressively
- Missing `Vary: Cookie` = CDN ignores cookies when caching
- **Risk**: If origin returns personalized data → could be cached and leaked to other users (cache poisoning)
- **Mitigation already in place**: Origin strips session data → always returns empty `customerData`

## What We Found via Bypass
1. **CSRF token**: `form_key: Crz5tLmNXorejkkV`
2. **Customer data structure**: `customerData` with id, email, mobile, loyalty fields (empty values)
3. **Feature flags**: `signupCaptcha: false`, `loginCaptcha: false`
4. **Internal API structure**: `gateway-api/omsApis/*` endpoints
5. **A/B test configs**: 28+ experiment variants

## Severity Assessment
- **WAF Bypass alone**: MEDIUM — blocked endpoints accessible, but only metadata/structure exposed
- **Cache poisoning**: NOT EXPLOITABLE — origin strips session data
- **Combined with other findings**: Could escalate if more sensitive endpoints are also WAF-blocked

## Generalized Checklist (apply to ANY target)
1. [ ] Identify CDN domain from JS bundles/headers
2. [ ] Test WAF-blocked URLs on CDN domain
3. [ ] Test alternate CDN domains (naikaa.com variant)
4. [ ] Analyze Cache-Control + Vary headers
5. [ ] Test for cache poisoning (authenticated request → check if cached for unauthenticated)
6. [ ] Enumerate exposed data structure
7. [ ] Check if CDN bypass applies to more sensitive endpoints
