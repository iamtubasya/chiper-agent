# Turnkey.com — Well-Hardened Target Case Study + Severity Inflation Lesson

**Target:** Turnkey (crypto wallet infrastructure)
**URL:** https://bugcrowd.com/engagements/turnkey (up to $50K)
**Auditor:** RESEARCHER_NAME
**Date:** 2026-09-19
**Result:** 0 bounty-worthy findings after exhaustive 30-vector + 10-layer audit

---

## Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| WAF | Cloudflare | All subdomains behind CF |
| Frontend | Next.js (Vercel) | app.turnkey.com SPA |
| API | Custom gateway | api.turnkey.com, P-256 stamp auth |
| Auth | OAuth + Email OTP + Passkey | Multiple auth factors |
| Hosting | Vercel (wallets, docs, whitepaper) | Standard Vercel deployment |
| Trust Center | Vanta | trust.turnkey.com |
| Backend | nginx/1.24.0 (leaked on app) | OpenResty on www |

## Test Matrix (30 Vectors — All Completed)

| # | Vector | Result | Verdict |
|---|--------|--------|---------|
| 1 | Sensitive Files | 404/403 on all domains | Clean |
| 2 | CORS (all subdomains) | api: no credentials; trust/wallets: * (no creds) | Clean |
| 3 | Auth Flow | P-256 stamp required; structured errors | Clean |
| 4 | GraphQL | Not found on API; not allowed on www | Clean |
| 5 | API Versioning | v1 only; v2 returns Not Found | Clean |
| 6 | SSRF | All endpoints require stamp auth | Clean |
| 7 | XSS/Injection | UUID validated; strict CSP on redirect | Clean |
| 8 | 403 Bypass (app.turnkey.com) | All paths → 302 (SPA catch-all) | Clean |
| 9 | Host Header Injection | api/www return 403 (CF blocks) | Clean |
| 10 | Race Condition | 20 parallel requests: all identical | Clean |
| 11 | Open Redirect | None on www.turnkey.com | Clean |
| 12 | Security Headers | api/app missing X-Frame-Options | INFO |
| 13 | Cookie Security | All CF cookies: HttpOnly; SameSite=None; Secure | Clean |
| 14 | JWT/JWKS | api: Not Found; www: "Invalid .well-known" | Clean |
| 15 | WebSocket | Not found on API; redirect on app | Clean |
| 16 | Cache Deception | All paths 404/403; no-store on most | Clean |
| 17 | HTTP Smuggling | 403 on all methods | Clean |
| 18 | SSTI | UUID format validated; no template syntax | Clean |
| 19 | XXE | POST endpoints; JSON only | Clean |
| 20 | Command Injection | No command-executing endpoints found | Clean |
| 21 | Staging/Dev | engineering domains: DNS resolved, not accessible | INFO |
| 22 | Email Security | No SPF/DKIM/DMARC on turnkey.com | INFO |
| 23 | Subdomain Takeover | No dangling CNAMEs | Clean |
| 24 | IDOR | No auth = no data access | N/A |
| 25 | Mass Assignment | No writable endpoints without auth | N/A |
| 26 | Business Logic | Requires authenticated session | Blocked |
| 27 | Token Handling | OAuth redirect: needs chaining | INFO |
| 28 | Rate Limiting | 50 rapid requests: all 200, 0 blocked | INFO |
| 29 | API Error Disclosure | Structured errors; no stack traces | Clean |
| 30 | Infrastructure | x-lambda-id, x-wf-region, nginx version leaked | INFO |

## Candidates Evaluated (6 — All Dropped or INFO)

| # | Finding | Initial Severity | Honest Severity | Reason for Drop |
|---|---------|-----------------|----------------|-----------------|
| F1 | OAuth redirect unvalidated scheme | P2 HIGH | P3/P4 | Needs chaining with open redirect at OAuth provider. Attacker cannot inject tokens — must come from provider. Standalone: informational. |
| F2 | API CORS origin reflection | P3 MEDIUM | P4/INFO | No `Access-Control-Allow-Credentials: true`. Without credentials, browser cannot read authenticated responses. All endpoints need P-256 stamp. |
| F3 | Org ID enumeration | P4 | P4/INFO | 3 error states reveal existence. No rate limiting. Low impact — UUID format, no sequential IDs. |
| F4 | No rate limiting | P4 | P4/INFO | 50 requests, all succeeded. But: no sensitive endpoint to brute-force without auth. |
| F5 | Infrastructure disclosure | INFO | INFO | x-lambda-id, x-wf-region, nginx version. Standard cloud metadata. |
| F6 | Missing security headers | INFO | INFO | api/app missing X-Frame-Options. No injection point to leverage clickjacking. |

## Key Lesson: Severity Inflation

**User correction:** "jelaskan dl secara detail utk temuan high dan mediumnya, ini beneran bisa di duplikasi? dan beneran berimpak negatif? jgn hanya teoritis yg dikasih k saya"

**What happened:** Agent initially assigned P2 HIGH to OAuth redirect and P3 MEDIUM to CORS based on theoretical exploit chains. On honest analysis:

1. **OAuth redirect (P2→P3/P4):** The `scheme` parameter IS unvalidated, but tokens must come from the OAuth provider. Attacker cannot inject arbitrary tokens. Exploit requires chaining with an open redirect at Google/Apple — not a standalone vulnerability.

2. **CORS (P3→P4/INFO):** Origin IS reflected, but `Access-Control-Allow-Credentials: true` is NOT present. Without credentials, browsers cannot read cross-origin authenticated responses. All API endpoints require P-256 stamp auth. Amplifier only — not standalone.

**Anti-inflation checklist (ask BEFORE assigning severity):**
```
□ Can this be exploited WITHOUT chaining with another vulnerability?
□ Does the response contain SENSITIVE DATA (not just error messages)?
□ Can an attacker CONTROL the input that triggers the vulnerability?
□ Is there a REALISTIC victim scenario (not just theoretical)?
□ Would a Bugcrowd triager accept this as P2/P3?
□ Does the finding survive the "so what?" test?
```

**Rule from user:** Findings must be duplicable AND have real negative impact. Theoretical chains without proof = informational.

## Well-Hardened Target Pattern

Turnkey shares characteristics with Magic Labs (case study in this skill):

| Factor | Turnkey | Magic Labs |
|--------|---------|------------|
| WAF | Cloudflare (blocks host header, injection) | Cloudflare (403 on all API) |
| Auth | P-256 stamp + OAuth + passkey | Passwordless Magic Link |
| API | Structured errors; no stack traces | Structured errors; auth-gated |
| CORS | No credentials on reflections | No CORS headers at all |
| Frontend | Next.js SPA (Vercel) | Next.js SPA (Vercel) |
| Infrastructure | Minimal disclosure (lambda ID, region) | Minimal disclosure |
| Result | 0 bounty findings | 0 bounty findings |

**Pattern indicators (detect early):**
- Cloudflare WAF on all subdomains
- P-256/stamp-based auth (not just JWT)
- Structured error messages (no stack traces)
- SPA catch-all on frontend
- No dangling CNAMEs
- CORS without credentials
- Missing headers without injection points

**Time budget:** ~2-3 hours for full 30-vector audit. If all vectors return clean/INFO after thorough testing → honest conclusion: "no bounty-worthy findings."
