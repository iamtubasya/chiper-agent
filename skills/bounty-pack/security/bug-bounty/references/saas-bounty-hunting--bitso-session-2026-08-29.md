# Bitso Bug Bounty Session (2026-08-29)

## Target
- **Program:** Bitso (Bugcrowd Managed)
- **Scope:** bitso.com, nvio.mx, nvio.ar + mobile apps
- **Header:** `X-Bug-Bounty: Bugcrowd-BC_USERNAME`
- **Reporter:** BC_USERNAME@BC_ALIAS.com

## Attack Surface Discovered

### Infrastructure
- **CDN:** Cloudflare (all production domains)
- **Auth:** Keycloak v30bg (React/Keycloakify theme) on dev.bitso.com
- **Hosting:** S3+CloudFront (onchain.bitso.com, dev.nvio.ar), Cloudflare (everything else)
- **Keycloak Realms:** `master`, `web`
- **HSTS:** `max-age=31536000; includeSubDomains; preload` (bitso.com, dev.bitso.com, api.bitso.com, nvio.mx, dev.nvio.mx)

### CSP-Based Internal Service Discovery
From bitso.com CSP `connect-src` directive:
- `amplitude.bitso.com` → 522 (Cloudflare-protected)
- `dev-amplitude.bitso.com` → 522
- `dev-segment.bitso.com` → 522
- `cgw.bitso.com` → 000 (truly internal, connection refused)
- `status.bitso.com` → 200
- `onchain.bitso.com` → 200 (S3+CloudFront SPA)
- `segment.bitso.com` → 522
- `uptok-server-production-cyxmaabxjq-uc.a.run.app` → 200 (Hightouch US endpoint)

### CSP connect-src also reveals
- Zendesk integration: `bitsohelp.zendesk.com`, `*.zendesk.com`
- Smooch (messaging): `*.smooch.io`, `api.smooch.io`
- HubSpot: `*.hubspot.com`, `api.hubapi.com`
- TikTok analytics: `analytics.tiktok.com`
- Appcues: `fast.appcues.com`
- Datadog: `logs.browser-intake-datadoghq.com`, `rum.browser-intake-datadoghq.com`
- Sentry: `*.ingest.sentry.io`
- Many ad-tech/tracking pixels

## Findings

### FINDING 1: CORS Misconfiguration on Keycloak (dev.bitso.com)
**Severity:** HIGH (P2-P3)
**Endpoint:** `dev.bitso.com/auth/realms/master/protocol/openid-connect/userinfo`
**PoC:**
```bash
curl -s -D- -H "Origin: https://evil.com" \
  "https://dev.bitso.com/auth/realms/master/protocol/openid-connect/userinfo" \
  | grep -i "access-control"
# Returns: access-control-allow-origin: https://evil.com
# Returns: access-control-allow-credentials: true
```
**Also affects:** token endpoint (POST OPTIONS), userinfo endpoint
**Impact:** Session hijacking for any authenticated user on dev.bitso.com. Attacker can read Keycloak userinfo cross-origin with credentials.
**Remediation:** Restrict CORS to specific trusted origins. Remove wildcard reflection.

### FINDING 2: Hightouch Write Key Exposed — CRM Data Poisoning
**Severity:** MEDIUM (P3)
**Location:** HTML source of `/api/trade` page
**Write Key:** `[REDACTED — 64-hex, recover from the target's HTML/JS bundle at recon time]`
**Endpoints:**
- US: `https://api.hightouch.com/events` (also via `uptok-server-production-cyxmaabxjq-uc.a.run.app`)
- EU: Also accepts injections
**PoC:**
```bash
curl -s -X POST "https://api.hightouch.com/events" \
  -H "Content-Type: application/json" \
  -d '{"writeKey":"<REDACTED>","batch":[{"type":"identify","userId":"test","traits":{"role":"admin"}}]}'
# Returns: {"success": true}
```
**Impact:** If Hightouch syncs to CRM (Salesforce/HubSpot), attacker can poison contact records, inject fake leads, modify deal stages. Marketing budget waste from triggered campaigns.
**Severity note:** Write keys are public by design. Real severity depends on downstream CRM integration. Analytics-only = informational.

### FINDING 3: Keycloak Admin Console Accessible
**Severity:** INFO (P4)
**Endpoint:** `dev.bitso.com/auth/admin/master/console/` → HTTP 200
**Keycloak version:** v30bg (React-based, Keycloakify theme)
**Client enumeration:** All tested client_ids return "invalid_client" (uniform error, good practice)
**Remediation:** Restrict admin console access to VPN/internal networks.

## Keycloak OIDC Attack Patterns (Bitso-specific)

### Error Differentiation
All tested client IDs returned `invalid_client` — Keycloak does NOT differentiate between "client doesn't exist" and "client exists but credentials wrong" on the token endpoint. This is GOOD security practice (prevents client enumeration).

### JWKS Keys
- `al2m_xeZRPvPgAsikr0QR0wBsqf0dbJs6uwsbw4kMXc` — RSA-OAEP (encryption)
- `_3A5Wz-wW0f5Gl82oPCP8hm4sbls-iobrZle8UqFTNY` — RS256 (signing)

### OIDC Endpoints Tested
| Endpoint | Method | Response |
|----------|--------|----------|
| `/auth/realms/master/.well-known/openid-configuration` | GET | 200 + full config |
| `/auth/realms/master/protocol/openid-connect/userinfo` | GET | 401 (auth required) |
| `/auth/realms/master/protocol/openid-connect/token` | POST | 401 (invalid_client) |
| `/auth/realms/master/protocol/openid-connect/certs` | GET | 200 + JWKS |
| `/auth/admin/master/console/` | GET | 200 (admin console) |
| `/auth/realms/master/clients-registrations/openid-connect` | POST | "Invalid origin" |

## NVIO Domain Analysis

### nvio.mx / nvio.ar (Production)
- React SPA (antiClickjack protection)
- Security headers: nvio.mx has HSTS; nvio.ar has NONE
- No CSP, no XFO, no XCTO on either
- GraphQL endpoint returns HTML (SPA catch-all, NOT real GraphQL)
- API endpoints: `/api/v1/clabes` (401:107), `/api/v1/clabes/settings` (401:107)

### dev.nvio.mx
- Has CSRF token preloading: `/api/v3/csrf_token`
- `noindex, nofollow` meta tag
- HSTS: max-age=31536000; includeSubDomains; preload

### dev.nvio.ar
- **AmazonS3** hosting (not Cloudflare!)
- No security headers
- Different infrastructure = potentially different security controls

### CORS on all NVIO domains
```
access-control-allow-origin: *
access-control-allow-methods: GET
access-control-max-age: 300
```
Wildcard origin but GET-only and no ACAC = LOW severity.

## Lessons Learned
1. **CSP connect-src is gold** for internal service discovery — reveals dev/staging endpoints, third-party services, internal APIs
2. **dev.bitso.com has SAME CSP as prod** — dev CSP likely copy-pasted from prod, including all third-party whitelists
3. **Keycloak CORS on dev instances** is a common misconfiguration — dev environments often have relaxed CORS
4. **Multi-domain programs** (bitso.com + nvio.mx + nvio.ar) have INDEPENDENT security postures — always test each
5. **Hightouch/Reverse ETL write keys** are a newer class of third-party exposure — beyond traditional Segment/Amplitude keys
6. **GraphQL returning HTML** = SPA catch-all routing, not a real GraphQL endpoint (confirmed on nvio.mx/ar)
7. **Different TLDs may use different infra** — dev.nvio.ar uses S3, everything else uses Cloudflare
