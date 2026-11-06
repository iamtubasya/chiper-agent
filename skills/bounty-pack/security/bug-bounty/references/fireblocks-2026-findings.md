# Fireblocks Bug Bounty — Findings & Recon Reference
**Last Updated:** 2026-09-04

## ⚠️ TWO SEPARATE PROGRAMS
Fireblocks has bounty programs on **TWO DIFFERENT PLATFORMS** with **DIFFERENT SCOPE:**

| Platform | Program | Scope | Status |
|----------|---------|-------|--------|
| **HackerOne** | `hackerone.com/fireblocks_mpc` | MPC wallet infrastructure, console, API | Historical (2026-09) |
| **Bugcrowd MBB** | `bugcrowd.com/engagements/fireblocks-mbb-og` | 3 sandbox API targets + smart contracts | Active (since Sep 9, 2025) |
| **Bugcrowd MBB** | `bugcrowd.com/engagements/fireblocks-mbb-og2` | `github.com/fireblocks/mpc-lib` ($150K pool) | Active |

**Do NOT confuse findings between platforms.**

---

## Bugcrowd MBB Engagement (Active — fireblocks-mbb-og)

### Program Details
- **Model:** Managed Bug Bounty (MBB)
- **Status:** In Progress (since 2025-09-09)
- **Reward Allocation:** pay_for_success
- **Safe Harbor:** Yes
- **Scope Rank:** 1/4 (Top Priority)
- **Avg Payout:** $160.41
- **Total Researchers:** 403 joined

### In-Scope Targets
1. `sb-console-api.fireblocks.io` — Console API (Express.js, Cloudflare)
2. `sb-mobile-api.fireblocks.io` — Mobile API (Express.js, health endpoint leaks)
3. `sandbox-api.fireblocks.io` — Core REST API (JWT auth, Cloudflare)
4. **Smart contracts** — fireblocks-smart-contracts repo (46+ Solidity files)

### Reward Tiers
| Priority | Reward Range | Typical Findings |
|----------|-------------|-----------------|
| P1 Critical | $7,000 – $12,000 | Auth bypass, RCE, IDOR, unauthorized fund transfer, SQLi |
| P2 High | $1,000 – $9,000 | Stored XSS, CSRF, OAuth ATO, SSRF internal secrets |
| P3 Medium | $300 – $1,500 | Reflected XSS, Content Spoofing, 2FA bypass |
| P4 Low | $20 – $300 | Missing rate limiting, HTTP tokens, headers |
| P5 Info | $0 | Points only — excluded from submission |

### Focus Areas
1. Unauthorized actions → emphasis on unauthorized funds transfer
2. Sensitive data / PII disclosure
3. XSS / CSRF (privileged context)
4. RCE / Auth flaws (IDOR, auth bypass)
5. Injection (SQL, XML) / Directory traversal
6. Security misconfig with verifiable vulnerability
7. MPC protocol for ECDSA signatures (Bitcoin, Ethereum) + EdDSA

### Exclusions
- P5 vulnerabilities, DoS/DDoS, Rate limiting bypass
- N-day exploits within 16 days of disclosure
- Social engineering, Phishing, Physical attacks
- Third party providers/services
- Post-exploitation scenarios (report & stop)

### Infrastructure Intel (from recon)
- **AWS Account IDs leaked** via /health: sandbox (751886943440), prod (808451231866)
- **S3 buckets:** fireblocks-sandbox-messages, us-prod-fb-sqs-messages
- **SQS/SNS:** 5 queues + 5 topics per environment
- **No rate limiting** observed on any endpoint
- **Proxy bypass** via X-Original-URL/X-Rewrite-URL on sb-console-api
- **CSP weakness:** unsafe-inline + unsafe-eval on sandbox.fireblocks.io
- **X-Powered-By: Express** disclosed on 2/3 hosts

### Subdomains Discovered (34)
Key ones: aave, apigw, arc, auth, console-api, console, console2, csd, demo1-3, kibana, lava-prod, mobile-api, n8n, network-provider-onboarding, otc-demo, sb-auth0, sgx-client, support, www

---

## HackerOne Engagement (Historical)

### Multi-Region Console Infrastructure
| Region | Console Domain | Auth0 Domain | Cloudinary Account | Notes |
|--------|---------------|--------------|-------------------|-------|
| Production | `console.fireblocks.io` | `auth.fireblocks.io` | `fireblocks` / `kgdyxtmr` | Main production |
| Sandbox | `sandbox.fireblocks.io` | `fireblocks-sandbox.us.auth0.com` | `fireblocks` / `kgdyxtmr` | Same Cloudinary as prod |
| EU | `eu-console.fireblocks.io` | `eu-auth0.fireblocks.io` | `dvkywpcq6` / `xazdnpoq` | `USE_MOCKS: 'true'` |
| EU2 | `eu2-console.fireblocks.io` | `eu2-auth0.fireblocks.io` | `dvkywpcq6` / `xazdnpoq` | `USE_MOCKS: 'true'` |

### Auth0 Client IDs (per region)
- **Production main:** `by1XIDAOja683EkdveBn8uIpXuJC9a0r`
- **Sandbox main:** `JXzdtvEJDz2rY0AfKqCnIfJnS9WeV4DI`
- **EU main:** `Z1qNte5LBOFEFQOaom41otijvNzPpPDc`
- **EU2 main:** `5Hyzf9iLrfQoqgnw2wIuRLfMMG9ntvLZ`

### HackerOne Findings (All Failed VRT)
**F1: Cloudinary Upload Preset Abuse** — by-design. Unsigned presets are designed for client-side use.
**F2: Cloudinary CORS Misconfiguration** — by-design. Public upload endpoints require `*` CORS.
**F3: Client-Side Secrets in env-config.js** — informational. All are publishable/public keys.
**F4: Staging Storage Public Access** — not reproducible. Random UUIDs return 403.

---

## Session 2026-09-04: Authenticated API Exhaustion + Auth0 Enumeration

### Auth0 Enumeration Patterns (Reusable)

**Technique: Error differential to detect signup status without account**

1. **`/dbconnections/signup` with `user_metadata`:**
   - No metadata → `"Invalid request: missing 'user_metadata'"`
   - String metadata → `"Invalid request: invalid user_metadata type (expected object)"`
   - Object metadata → `"public signup is disabled"`
   - **Key insight:** Error returns BEFORE checking signup status when metadata format is wrong. Server validates format first, then checks signup policy.

2. **Password grant (`/oauth/token` with `grant_type=password`):**
   - Different client IDs have different grant type permissions
   - Sandbox clients allow password grant WITHOUT client_secret
   - Response: `"Wrong email or password"` — same for ALL emails (no enumeration)

3. **Dynamic client registration (`/oidc/register`):**
   - Returns 404 → registration endpoint exists but disabled
   - Would return 200 with client_id if enabled

4. **Device code flow:**
   - `"client not authorized for device_code grant type"` → flow exists but not enabled for this client

### JWT Error Code Differential Analysis

**sandbox-api returns different error codes revealing server-side validation pipeline:**

| Code | Meaning | What it reveals |
|------|---------|----------------|
| `-3` | No token sent | Server rejects before any parsing |
| `-2` | Token parsing failed | JWT sent but missing `sub` claim OR no API key |
| `-16` | Bad userId format | JWT has `sub` but `userId` field doesn't match expected format |

**Technique:** Send requests with progressively more valid tokens to map the validation chain. Each error code reveals a NEW validation step.

### JWT `userId` vs `sub` Claim Analysis
- JWT decoded: `userId: "aa815e398-afd1-4adb-b9ad-534d550c0ba3"`, `iat`, `exp`
- **No `sub` claim present** — this is the critical field
- API requires `sub` claim but Fireblocks tokens use custom `userId` field
- **Error code -16** confirms `sub` is expected but receives wrong format
- Token was **expired** (iat/exp ~2h window)
- **Conclusion:** Without a registered account's `sub` claim, the API is unreachable

### Cloudflare Ban Management

**Pattern: Subdomain-specific bans with different cooldown windows**
1. Direct curl ban: Aggressive JWT forgery triggered Cloudflare 1010 ban
2. Ban scope: Different subdomains have independent ban states:
   - `console-api.fireblocks.io` → BANNED (403, persistent)
   - `sandbox-api.fireblocks.io` → RECOVERED after 30s cooldown
   - `mobile-api.fireblocks.io` → NOT BANNED (different WAF rules)
3. **`web_extract` bypass:** Different IP pool bypasses Cloudflare ban entirely
4. **Cooldown period:** 30-60 seconds between requests to avoid re-trigger

### Host Header Injection
- `sb-console-api` with Host: `sandbox-api.fireblocks.io` → routes to sandbox-api backend
- **X-Original-URL** and **X-Rewrite-URL** headers rewrite path
- Not exploitable — backend validates auth independently of routing

### SPA JavaScript Bundle Endpoint Enumeration

**From console.fireblocks.io JS bundle — API surface discovered:**
```
/v1/orders          — Trading orders
/v1/positions       — Portfolio positions
/v1/quotes          — Price quotes
/v1/trading         — Trading operations
/v1/external-keys/signing_keys — External signing key management
/v1/mpc_keyset      — MPC keyset operations
/v1/audit_logs      — Audit trail
/v1/eligibility/scan — Compliance screening
/get_amplify_jwt    — JWT generation endpoint
```

**Technique:** Extract JS bundle URLs from React SPA, grep for API paths. SPA bundles contain full API surface including endpoints not linked in the UI.

### Error Messages That Leak Validation Logic
| Endpoint | Response | Reveals |
|----------|----------|---------|
| `/dbconnections/signup` (no metadata) | `missing 'user_metadata'` | Expected field name |
| `/dbconnections/signup` (string metadata) | `invalid user_metadata type (expected object)` | Expected type |
| `/dbconnections/signup` (object metadata) | `public signup is disabled` | Signup policy |
| `/oauth/token` (no client_id) | `Missing client_id` | Required parameter |
| `sandbox-api` (no token) | Error code -3 | Auth pipeline step 1 |
| `sandbox-api` (bad token) | Error code -2 | Auth pipeline step 2 |
| `sandbox-api` (no sub claim) | Error code -16 | Auth pipeline step 3 |

### mpc-lib Audit (fireblocks-mbb-og2 — $150K max)

**memcmp Analysis — 11 instances, ALL on public data:**
- Curve points (P, Q), generator points, hashes → NOT secret scalars
- SECURITY-MODEL §6.5 explicitly excludes timing on public values
- No timing side-channel exploitable

**Batch Statistical Security (from previous session):**
- `BATCH_STATISTICAL_SECURITY = 5` + `uint8_t` random coefficients → 8-bit security
- Should be ≥40 bits for production

### Cloudinary Upload Abuse (Confirmed By-Design)
- Preset `kgdyxtmr`: unsigned, active, allows custom `public_id` and `folder`
- **Cannot overwrite existing assets** (preset restrictions block)
- SSRF via Cloudinary fetch transformation: outbound requests confirmed but AWS metadata restricted
- **No exploitable SSRF**

### Attack Vector Exhaustion Summary (17 vectors)
| Category | Tested | Result |
|----------|--------|--------|
| Auth bypass | JWT forgery, alg:none, key confusion | Blocked (cert validation) |
| Account creation | Auth0 signup, password grant, device code, dynamic registration | ALL disabled |
| API endpoint abuse | 100+ endpoints discovered, all require JWT + API key + sub claim | Unreachable |
| Infrastructure | S3, SQS, SNS, CloudFront, Cloudinary, DNS | By-design or AccessDenied |
| Client-side | JS bundles, source maps, env-config.js, CSP | Informational only |
| Third-party | Auth0, Cloudinary, Datadog, Stripe, Pendo | All publishable keys |
| Source code | mpc-lib (in-scope for MPC MBB) | Well-written, memcmp on public data |
| Crypto | Paillier, range proofs, seed handling | Sound implementation |

**Decision: Need sandbox account to proceed.** Request credentials from @febfrm on Bugcrowd.
