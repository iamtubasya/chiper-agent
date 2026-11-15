# Bitso Bug Bounty — Complete Session Archive (2026-09)

## Session Summary
- **Program:** Bitso (Bugcrowd Managed Public)
- **Scope:** bitso.com, nvio.mx, nvio.ar, mobile apps
- **Reporter:** BC_USERNAME@BC_ALIAS.com
- **Header:** `X-Bug-Bounty: Bugcrowd-BC_USERNAME`
- **Duration:** Multi-session (Aug 29 - Sep 6, 2026)

## Attack Vectors Tested (ALL EXHAUSTED)

### Phase 1: Recon & Infrastructure
- [x] Subdomain enumeration (12+ subdomains found)
- [x] CSP analysis (revealed 15+ internal services)
- [x] CDN mapping (3 CloudFront distributions: assets, devassets, stageassets)
- [x] Keycloak discovery (dev.bitso.com, master + web realms)
- [x] NVIO domain analysis (MX + AR, different infra)
- [x] S3 bucket enumeration (onchain.bitso.com, dev.nvio.ar)

### Phase 2: Auth & OIDC
- [x] OIDC well-known + JWKS
- [x] CORS testing (5 origin variations per endpoint)
- [x] Client ID enumeration (uniform error = no enumeration)
- [x] Dynamic client registration (blocked by origin)
- [x] Token Exchange / CIBA / Device Flow (invalid_client or 404)
- [x] ROPC testing (`admin-cli` enabled, zero lockout)
- [x] Rate limiting (76+ requests, no 429)

### Phase 3: Web Application
- [x] CSP header analysis (unsafe-inline, unsafe-eval)
- [x] Host header injection (blocked 403)
- [x] Open redirect (redirect_uri validated)
- [x] Subdomain takeover (all CNAMEs legit)
- [x] Geo-restriction (Indonesia blocked, LATAM VPN needed)
- [x] reCAPTCHA on NVIO (blocks automation)

### Phase 4: Third-Party API Keys (Segment, Hightouch, Amplitude)
- [x] **Segment write key extraction** — keys found across environments (values REDACTED here —
      recover from the target's own JS bundle at recon time, never store live keys in a skill):
  1. `prod` HTML → Hightouch write key (64-hex): `[REDACTED]`
  2. `devassets` bundle → format example only: `sE0dVawHc…RtYuIo` (not a real key)
  3. `stageassets` bundle → `[REDACTED]`
  4. `assets` (prod) bundle → `[REDACTED]`
- [x] **Segment write key escalation testing** — ALL write-only (read endpoints return 404/000)
- [x] **Hightouch write key injection** — both US + EU endpoints accept injections
- [x] **Amplitude keys** — only track endpoints, no read capability

### Phase 5: Internal Services (from CSP)
- [x] `amplitude.bitso.com` → 522 (Cloudflare)
- [x] `segment.bitso.com` → 522
- [x] `dev-segment.bitso.com` → 522
- [x] `dev-amplitude.bitso.com` → 522
- [x] `cgw.bitso.com` → 000 (SSRF target, connection refused)
- [x] `status.bitso.com` → 200
- [x] `uptok-server-production-cyxmaabxjq-uc.a.run.app` → 200 (Hightouch endpoint)

### Phase 6: Staging Environment
- [x] `stage.bitso.com` — Admin console 200, CORS wildcard, same realms as prod

### Phase 7: Mobile Apps
- [x] APK extraction (bitso v4.52.0, nvio v2.1.3)
- [x] Bundle analysis (React Native, no additional keys beyond web)
- [x] Deep link enumeration
- [x] Certificate pinning check

## Reportable Findings (SUBMITTED/READY)

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | CORS Misconfiguration on Keycloak OIDC (prod) | MEDIUM (6.5) | SUBMITTED |
| 2 | Stage Environment Fully Exposed (admin console + CORS) | MEDIUM (P3) | READY |
| 3 | No Rate Limiting on Auth Endpoints | MEDIUM (P3) | READY |
| 4 | Weak CSP (unsafe-inline/eval) | INFO (P5) | DOCUMENTED |
| 5 | CORS + ROPC + Zero Lockout → ATO Chain | HIGH (8.1) | SUBMITTED |

## Non-Reportable Findings (By-Design / Informational)

| Finding | Reason |
|---------|--------|
| OIDC metadata/certs exposed | Public by spec |
| Segment write key injection (4 keys) | Write-only, no downstream consumer found |
| Hightouch write key injection | Write-only, no CRM impact proven |
| CDN SPA catch-all (200 for /.git, /.env) | S3 SPA hosting returns 200 for all paths |
| Geo-restriction blocking signup | By-design (regulatory) |
| Auth0/Sentry/Datadog keys in bundles | Public by design (client-side only) |

## Key Technical Learnings

### 1. Multi-Environment Segment Key Exposure Pattern
**Finding:** Segment write keys appear in JS bundles across MULTIPLE environments (assets, devassets, stageassets) — not just production. Each environment's bundle contains the SAME or DIFFERENT keys.

**Testing Method:**
```bash
# Get build manifest from any Next.js page
curl -s "https://TARGET.com/" | grep -oP '"buildId":"[^"]+"'
# Fetch _buildManifest.js for each subdomain
for sub in assets devassets stageassets mobileassets; do
  curl -s "https://$sub.bitso.com/_next/static/$BUILD_ID/_buildManifest.js"
done
# Search for segment keys in each bundle
grep -i "segment" *.js | grep -E '[a-zA-Z0-9]{32,}'
```

**Impact:** If ANY environment has a read-enabled write key, ALL environments' analytics data is exposed. Test read capability per key.

### 2. Segment Write Key Escalation — CONFIRMED Write-Only
**Tested on 4 keys across 3 environments + Hightouch:**
- All `track`/`identify`/`page`/`group`/`alias`/`batch` → `{"success": true}`
- All read endpoints (`/batch` GET, `/import` GET, `/identify` GET) → 404 or 000
- **Conclusion:** Write-only = P5 informational. No downstream business consumer found.

**Update to segment-write-key-escalation.md:** Add Bitso results as confirmed write-only case study.

### 3. Hightouch Reverse ETL Keys — New Third-Party Class
**Finding:** Hightouch (reverse ETL) write keys exposed in HTML source, not just JS bundles.
- US endpoint: `api.hightouch.com/events`
- EU endpoint: also accepts injections
- Cloudflare Worker proxy: `uptok-server-production-cyxmaabxjq-uc.a.run.app`
- **Severity depends entirely on downstream CRM sync** (Salesforce, HubSpot, Braze)

### 4. "Exhausted All Vectors" Stopping Criteria for Hardened Targets
When ALL of these are true, STOP — target needs authenticated access:

- [x] All standard web/API vectors tested → 403/401/WAF-blocked consistently
- [x] Infrastructure pivots (S3, pre-prod, staging) → AccessDenied or not found  
- [x] Third-party service analysis (Auth0, Segment, Hightouch, Amplitude, Sentry, Datadog, Cloudflare, Zendesk, HubSpot, Smooch, Appcues, TikTok, TikTok pixels) → all by-design / write-only
- [x] Client-side JS analysis → no secret keys, no debug endpoints, no exploitable config
- [x] Source code audit (if available) → out-of-scope or no exploitable bugs
- [x] Mobile app APK → no additional API surface beyond web
- [x] Auth wall is absolute (signup disabled, no device code, no passwordless, no dynamic registration)

**Decision:** Request sandbox credentials from @maintainer OR pivot to related program with deeper scope (e.g., Fireblocks MPC MBB has source code scope).

### 5. CSP connect-src Is the Best Recon Source for Modern Apps
Revealed 15+ internal services, third-party integrations, and dev/staging endpoints that NO other recon method found.

### 6. Different TLDs = Different Infra = Different Security Posture
- `dev.nvio.ar` → AmazonS3 (no Cloudflare, no security headers)
- `nvio.mx` + `dev.nvio.mx` → Cloudflare + HSTS
- `bitso.com` + `dev.bitso.com` → Cloudflare + HSTS
- **Always test each TLD independently.**

### 7. GraphQL Returning HTML = SPA Catch-All, NOT Real GraphQL
Confirmed on nvio.mx/ar. `/graphql` returns SPA HTML (200), not GraphQL response.

## Evidence Directory Structure
```
/d/data hermes/bugbounty/bitso-2026/
├── recon/
│   ├── subdomains.txt
│   ├── csp-analysis.json
│   ├── keycloak-oidc-discovery.json
│   └── nvio-domain-comparison.md
├── keys/
│   ├── segment-keys.json        # 4 keys with environment mapping
│   ├── hightouch-key.json
│   └── amplitude-keys.json
├── poc/
│   ├── cors-keycloak.txt
│   ├── segment-escalation.txt
│   ├── hightouch-injection.txt
│   ├── ropc-chain.txt
│   └── rate-limit-test.txt
├── screenshots/
│   ├── keycloak-admin-console.png
│   ├── cors-origin-reflection.png
│   └── segment-write-success.png
└── reports/
    ├── bitso-finding-1-cors-medium.md
    ├── bitso-finding-2-stage-medium.md
    ├── bitso-finding-3-ratelimit-medium.md
    └── bitso-finding-5-cors-ropc-high.md
```

## Final Verdict
**Bitso unauth attack surface: EXHAUSTED.**
- Ceiling without test account: P3 (rate limit, stage env, weak CSP)
- Ceiling with test account: P2 (ROPC chain → ATO)
- All 20+ unauthenticated vectors tested
- No further value without sandbox credentials

**Next Action:** Request sandbox credentials via Bugcrowd @maintainer OR pivot to next target.

---

*Session closed: 2026-09-06. All data archived. Moving to next target.*