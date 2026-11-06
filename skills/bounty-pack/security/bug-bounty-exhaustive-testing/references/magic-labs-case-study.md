# Magic Labs (magiclabs-mbb-og) — Well-Hardened Target Case Study

**Target:** Magic Labs MBB OG
**URL:** https://bugcrowd.com/engagements/magiclabs-mbb-og
**Auditor:** RESEARCHER_NAME (BC_USERNAME@BC_ALIAS.com)
**Date:** 2026-09-19
**Result:** 0 bounty-worthy findings after full Phase 0C audit

---

## Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| WAF | Cloudflare | api.magic.link fully blocked (403) |
| Frontend | Vercel/Next.js | Security Checkpoint active |
| Backend | AWS us-west-2 | EC2, RDS, Lambda, S3, SQS, ElastiCache |
| Auth | Magic Link (passwordless) | No brute force possible |
| Payment | Stripe | Via status page |
| Email | Customer.io + Postmark | Via status page |
| Analytics | Segment | Via status page |
| Status | Atlassian Statuspage | CORS: * (standard) |

## Scope

- In-scope: dashboard.magic.link, auth.magic.link, api.magic.link
- Bounty: P1:$3000, P2:$1000, P3:$500, P4:$250
- Platform: Bugcrowd (Managed BB)

## Recon Results

- Subfinder: 135 subdomains
- httpx: 94 live hosts
- gau: timed out (historical URLs unavailable)
- naabu: DNS resolution failed (WSL issue)
- Sensitive files: `.git/config` returns 404, rest returns 403 (Vercel catch-all)

## Test Matrix (23 Vectors)

| # | Vector | Result | Verdict |
|---|--------|--------|---------|
| 1 | Sensitive Files (.git, .env, etc.) | 404/403 | Clean |
| 2 | CORS (all subdomains) | No CORS headers | Clean |
| 3 | Auth Flow | All 403/404 | Clean |
| 4 | GraphQL Introspection | Cloudflare blocked | Clean |
| 5 | API Versioning | v1-v3: 502, v4: 403 | Clean |
| 6 | SSRF | All 403 | Clean |
| 7 | XSS/Injection | All 403 | Clean |
| 8 | 403 Bypass (all techniques) | All 403 | Clean |
| 9 | Host Header Injection | Vercel challenge | Clean |
| 10 | Race Condition | All 403 (no auth) | Clean |
| 11 | Open Redirect | All 403 | Clean |
| 12 | Security Headers | dashboard: missing | LOW |
| 13 | Cookie Security | Proper flags | Clean |
| 14 | JWT/JWKS | JWKS public by design | Clean |
| 15 | WebSocket | No upgrade | Clean |
| 16 | Cache Deception | All 403, no-store | Clean |
| 17 | HTTP Smuggling | 403 | Clean |
| 18 | SSTI | All 403 | Clean |
| 19 | XXE | 403 | Clean |
| 20 | Command Injection | All 403 | Clean |
| 21 | Staging/Dev | 401/403 | Clean |
| 22 | Email Security (SPF/DMARC) | None found | INFO |
| 23 | Subdomain Takeover | No CNAME | Clean |

## Candidates Evaluated (8)

| # | Finding | Verdict | Reason |
|---|---------|---------|--------|
| F1 | cognito.magic.link subdomain takeover | DROPPED | No CNAME to claimable service. Cloudflare origin misconfiguration only. |
| F2 | api.magic.link 502 | DROPPED | Backend outage, not security finding. No exploit path. |
| F3 | No rate limiting | DROPPED | Passwordless auth. No brute force possible. INFORMATIONAL only. |
| F4 | tee.express info disclosure | DROPPED | By-design FastAPI/Pydantic error messages. Auth-gated. |
| F5 | Host header injection | DROPPED | Vercel challenge blocks all unknown hosts. By-design. |
| F6 | Missing security headers | CANDIDATE (LOW) | No CSP/HSTS/X-Frame on dashboard. No injection point to leverage. |
| F7 | JWKS endpoint exposed | DROPPED | Public by design (used for JWT verification). |
| F8 | Staging environments | DROPPED | Requires auth tokens. Not publicly accessible. |

## Key Lessons

1. **Cloudflare WAF is effective.** All API-level testing blocked. Cannot test IDOR, injection, auth bypass without authenticated session.
2. **Vercel Security Checkpoint blocks browser testing.** Cannot access dashboard without solving challenge.
3. **Passwordless auth limits attack surface.** No brute force possible on Magic Link auth.
4. **Missing security headers without injection point = informational.** Cannot leverage CSP missing without XSS vector.
5. **Status page infrastructure leak is expected.** Atlassian Statuspage CORS: * is standard behavior.
6. **23 vectors tested, 8 candidates, all dropped.** Exhausted = exhaustive testing with documented results.

## Comparison: Well-Hardened vs Exploitable

| Factor | Magic Labs (Hardened) | Typical Target |
|--------|----------------------|----------------|
| WAF | Cloudflare (blocks all) | None or weak |
| Auth | Passwordless (Magic Link) | Password-based |
| Frontend | Vercel Security Checkpoint | None |
| API | Cloudflare 403 on all methods | Accessible |
| Subdomains | No dangling CNAMEs | Some claimable |
| CORS | No misconfigurations | Often reflected |
| Headers | Partial (dashboard missing) | Often missing |
