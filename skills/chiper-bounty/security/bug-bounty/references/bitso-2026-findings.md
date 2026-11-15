# Bitso Bug Bounty — Findings Reference (2026-08)

## Scope
- bitso.com (production)
- nvio.mx (NVIO payment system — Mexico)
- nvio.ar (NVIO payment system — Argentina)
- stage.bitso.com (staging environment)
- Program: Bugcrowd Managed (Public)

## Reportable Findings

### 1. CORS Misconfiguration on Keycloak OIDC Endpoints (SUBMITTED)
- **Endpoint:** `bitso.com/auth/realms/master/protocol/openid-connect/*`
- **CVSS:** 6.5 (MEDIUM)
- **Status:** SUBMITTED to Bugcrowd
- **Evidence:** Origin reflection + credentials on all OIDC endpoints
- **Affected endpoints:** `/.well-known/openid-configuration`, `/certs`, `/userinfo`, `/token`, `/token/introspect`, `/logout`

### 2. Stage Environment Fully Exposed (P3)
- **Endpoint:** `stage.bitso.com`
- **Evidence:** Admin console accessible (200 HTML), CORS reflects ANY origin, same realms as production

### 3. No Rate Limiting on Auth Endpoints (P3)
- **Endpoint:** `bitso.com/auth/realms/master/protocol/openid-connect/token`
- **Evidence:** 76+ requests without 429 response

### 4. Weak CSP (P5 Informational)
- **Evidence:** `unsafe-inline`, `unsafe-eval` in Content-Security-Policy

### 5. CORS → ROPC → Account Takeover Chain (P2)
- **Chain:** CORS reflection + `admin-cli` ROPC enabled + zero lockout
- **CVSS:** 8.1 (HIGH)
- **VRT:** Authentication > Weak Password Policy > Account Takeover
- **Key lesson:** CORS alone is P3. Chain with ROPC + no lockout → P2.

### 6. CDN Cross-Environment Access (P4-P5 Informational)
- **Evidence:** Production CDN serves files from dev deployment ID. All 3 CDNs serve same SPA HTML — no sensitive data.
- **Internal subdomains from CDN analysis:** `amplitude.bitso.com` (522), `segment.bitso.com` (522), `dev-segment.bitso.com` (522), `dev-amplitude.bitso.com` (522), `mobileassets.bitso.com` (200), `devassets.bitso.com` (200), `stageassets.bitso.com` (200), `cgw.bitso.com` (000 — SSRF target)

## Non-Reportable Findings (By-Design)

| Finding | Why Not Reportable |
|---------|-------------------|
| OIDC metadata/certs exposed | Public by spec |
| Token Exchange/CIBA/Device Flow | Returns "invalid_client" or 404 |
| Open redirect | Server validates redirect_uri |
| Host header injection | Blocked (403) |
| Subdomain takeover | CNAMEs point to legit infra |
| Segment write key injection | Write-only, no downstream impact |
| CDN SPA catch-all | S3 returns 200 for all paths |

## Testing Methodology
1. OIDC discovery + realm enumeration
2. Client ID enumeration via error messages
3. CORS testing (5 origin variations)
4. Dynamic client registration
5. Token Exchange / CIBA / Device Flow
6. Staging environment analysis
7. Rate limiting testing
8. CSP analysis
9. Subdomain takeover
10. Segment write key extraction + injection
11. CDN cross-environment access testing
12. Internal subdomain enumeration from CSP + JS bundles

### Key Lessons
- **Verify before claiming.** Check Content-Type headers. Check response body for actual data.
- **SPA catch-all false positive.** S3 configured for SPA hosting returns 200 for ALL paths including `/.git/HEAD`, `/.env`. Verify response body.
- **Geo-restriction blocks account creation.** Bitso blocks Indonesia (302 → /404). NVIO has reCAPTCHA. LATAM VPN required.
- **Unauth attack surface is very limited.** After 20+ vectors, P3 is the ceiling without test account.
