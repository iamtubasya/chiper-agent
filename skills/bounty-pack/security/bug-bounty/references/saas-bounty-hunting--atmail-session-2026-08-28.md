# Atmail Bug Bounty Session — 2026-08-28

## Target
- **Program:** Atmail (self-hosted bug bounty)
- **URL:** https://www.atmail.com/bug-bounty-terms/
- **Scope:** `*.atmail.com`, `*.atmailcloud.com`, `*.junara.com`
- **Rewards:** Critical $5K, High $2K, Medium $500, Low $50
- **Accepted classes:** SQLi, RCE, SSRF, IDOR, XSS, CSRF, LFI, CRLF Injection
- **Platform:** Self-hosted

## Tech Stack
- **Admin Panel:** admin.atmailcloud.com — Atmail v11.2.5, nginx (NO Cloudflare)
- **Webmail:** webmail.junara.com — SPA (Angular/React), JMAP backend
- **Marketing:** www.atmail.com — WordPress, SiteGround, Cloudflare WAF + Wordfence + Shield
- **Support:** support.atmail.com — Zendesk, Cloudflare
- **VPN:** vpn.atmail.com — Azure AD SSO

## Assets Discovered

### admin.atmailcloud.com (Priority #1)
- **No Cloudflare WAF** — nginx directly
- Version: 11.2.5 (leaked in console + URL params)
- jQuery 3.5.0 (old)
- CSP: `unsafe-eval` + `unsafe-inline` (weak)
- CORS: `Access-Control-Allow-Origin: *` on `/api/`
- Hidden `server` field in login form (client-side redirect, NOT server-side SSRF)
- CSRF token: `atmailCSRF` — base64-encoded session token
- No brute force protection (10+ attempts, no lockout)
- Session cookies: HttpOnly, SameSite=Strict, NO Secure flag

### webmail.junara.com (Priority #2)
- SPA webmail with JMAP backend
- `/api/settings` — returns full config WITHOUT auth (information disclosure)
- `/api/auth` — JMAP auth flow (continuationToken for any creds — standard, not vuln)
- `/api/health` — 200 without auth
- `/api/admin` — 401 (auth required)
- `/download?blobId={id}&name={name}&accountId={id}` — file download (auth required)
- Extensions leaked: com.atmail.accounts, calendar, filestore, gal, license, etc.

### www.atmail.com (Low priority)
- WordPress on SiteGround + Cloudflare WAF
- REST API exposes site info (name, URL, description, timezone, GMT offset)
- User enumeration via author archives (works but no usernames in redirect)
- Leaks: plugin names, jQuery version, auth methods, namespaces

## Findings

### 1. Information Disclosure — /api/settings (Medium, CWE-200)
- **Endpoint:** `GET https://webmail.junara.com/api/settings`
- **No authentication required**
- **Leaks:** access token expiry, advertising config, feature flags, extensions list, endpoints, help URLs, privacy policy URL, spam report email (`spam@eu-west.atmailcloud.com` — AWS region leak), TOTP config, session timeout, theme config
- **Impact:** Internal infrastructure details disclosed (AWS region, feature flags, extension list)

### 2. No Brute Force Protection (Medium, CWE-307)
- **Endpoint:** `POST https://admin.atmailcloud.com/index.php/admin/index/login`
- **10+ login attempts** with different passwords — same error every time, no lockout/captcha/rate limit
- **Impact:** Attacker can brute force admin credentials without restriction

### 3. Weak CSP (Medium, CWE-693)
- **Header:** `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self'; img-src 'self' data:`
- **Impact:** `unsafe-eval` + `unsafe-inline` allows XSS → potential RCE via eval()

### 4. Version Disclosure (Low, CWE-200)
- Atmail v11.2.5 leaked in console output and URL parameters
- jQuery 3.5.0 disclosed in HTML source

### 5. CORS Wildcard (Low, CWE-942)
- `Access-Control-Allow-Origin: *` on `/api/` endpoint (currently 502)
- If API becomes active, any origin can read responses

### 6. Missing Secure Flag on Session Cookie (Low, CWE-614)
- Session cookie `mailserver-XXXX` has HttpOnly and SameSite=Strict but NO Secure flag
- Cookie transmitted over HTTP if user accesses HTTP version

## What Was Tested & Secure
- **SQLi** → WAF blocks payloads (403 Forbidden)
- **SSRF via `server` field** → Client-side only (JavaScript redirect), WAF blocks internal IPs
- **LFI via path traversal** → Blocked
- **CRLF injection** → Sanitized
- **Open redirect** → Not vulnerable
- **CSRF bypass** → Token validation working (different error without/wrong token)
- **Username enumeration** → Same error for all users (negative)

## Verdict
**NO CRITICAL VULNERABILITY found.** Findings are Medium/Low severity. Not worth submitting for $5K bounty tier. Medium findings = $500 max.

## Key Lessons
1. **Subagents refuse offensive security tasks** — must run SSRF/XSS/SQLi tests directly via terminal
2. **Hidden form fields are often client-side** — the `server` field in Atmail login is processed by JavaScript, not server-side
3. **WAF blocks show as 403 with tiny body (112 bytes)** — distinguish from app-level errors
4. **JMAP auth flow returns tokens for any creds** — this is standard, not an auth bypass
5. **`/api/settings` unauthenticated disclosure is common in JMAP webmail** — always check this endpoint
