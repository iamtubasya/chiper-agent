# Reference: God-Eye Validation & False Positives (BBflow §6)

> JANGAN pernah bilang "finding"/"critical" sampai semua check di bawah lolos.
> Frame hasil sebagai **God-Eye Verdict**: clear pass/fail dengan reasoning.

## Checklist (setiap kali)

```
□ Exposed WITHOUT auth? (kalau auth required → state upfront)
□ Internal/private data, atau public-by-design? (client-side config = PUBLIC)
□ Exploitable oleh external attacker tanpa privileged access?
□ Documented/acknowledged behavior? (= accepted risk, bukan vuln)
□ Compensating control ada? (rate limit, server-side validation, upstream guard)
□ IMPACT match SEVERITY? (match persis, jangan inflate)
```

## Credential Exposure — Validation Protocol

Exposed credentials (AWS keys, API tokens, write keys) are the #1 source of false positives in bug bounty. Follow this protocol:

### Step 1: Does the credential work?
```
→ If NO: INFO (credential expired/invalid)
→ If YES: proceed to Step 2
```

### Step 2: What permissions does it grant?
```
→ Run the credential against ALL relevant services
→ Log every ALLOW and DENY
→ Map: what CAN it do vs what it CANNOT do
```

### Step 3: Does the permission scope enable real impact?
```
→ If restricted to read-only / analytics / logging: LOW at best
→ If allows write to business systems: MEDIUM+
→ If allows admin / fund access: HIGH+
```

### Step 4: Is there a compensating control?
```
→ Server-side validation before data reaches business logic?
→ IAM policy properly scoped (least privilege)?
→ Data cleaning pipeline between injection point and consumer?
→ If YES to any: likely NOT exploitable despite working credential
```

### Real Examples
| Credential | Works? | Permissions | Impact | Verdict |
|------------|--------|-------------|--------|---------|
| AWS Identity Pool (Cognito) | YES (STS success) | STS GetCallerIdentity ONLY — 19/20 services DENIED | Cannot access S3, Lambda, DynamoDB, Secrets Manager | **NOT A VULN** — properly scoped role |
| Segment Write Key | YES (200 OK) | track/identify/page/batch — all accepted | Only analytics pipeline — no proof data reaches financial systems | **NEEDS MORE PROOF** — trace data flow before claiming |
| Datadog Client Token | YES (202 Accepted) | Log ingestion only | Monitoring noise, no direct user/fund impact | **LOW** — monitoring bypass |
| Zendesk Widget Key | YES (widget loads) | Create fake support widget | Social engineering / phishing vector | **MEDIUM** — if phishing is in scope |

## Tabel False Positive

| Ditemukan | Realita | Verdict |
|-----------|---------|---------|
| Remote config w/ server URLs | client-side config fetch | **NOT A VULN** |
| API docs requiring auth | working access control | **NOT A VULN** |
| `__NEXT_DATA__` page props | SSG/SSR public data | cek real secrets |
| JS bundle w/ API routes | client code, always public | **NOT A VULN** |
| GraphQL "not authenticated" | working auth gate | butuh credential |
| Verbose error w/ internal codes | fingerprinting | INFO (excluded) |
| WAF bypass reaching public pages | no protected data behind | **NOT A VULN** |
| Source maps / version banners | info disclosure only | Category 7 (rejected) |
| AWS Cognito Identity Pool exposed | IAM role properly scoped, least privilege | **NOT A VULN** — see Credential Protocol above |
| Segment/Amplitude write key in JS | Write keys ARE public by design, only analytics | **TRACE FLOW** — only vuln if data reaches business logic |
| Keycloak OIDC metadata exposed | Required by OpenID Connect specification | **NOT A VULN** — public by spec |
| Keycloak admin console accessible | Login page public, strong admin password | **NOT A VULN** — by design |
| React env-config.js / _env.js / config.js with Auth0/Datadog/Cloudinary IDs | React client-side config injection — values appear in browser DevTools, CSP whitelists same domains | **NOT A VULN** — see React Config Gate below |
| Health endpoint returns AWS infra (Account ID, ARNs, bucket names) | MUST compare with sibling services — if /health on console-api returns 403 but mobile-api returns 200+dump → disclosure exceeds health-check scope | **COMPARE** — see API Health Endpoint Gate below |

## Severity Scale

| Severity | Definisi | Requires |
|----------|----------|----------|
| Critical | fund loss, consensus failure, RCE (no preconditions) | external attacker, no auth, direct impact |
| High | significant breach, auth bypass w/ material harm | clear attack path |
| Medium | specific conditions, limited scope | mungkin butuh auth/chaining |
| Low | minor bugs, non-sensitive info | low real-world impact |

## Escalation (MEDIUM → HIGH → CRITICAL)

Jangan submit LOW/INFO. Kalau MEDIUM, cari cara escalate sebelum report.

- **MEDIUM → HIGH**: chain finding (info leak → IDOR → ATO) atau buktikan read/write data sensitif user lain.
- **HIGH → CRITICAL**: buktikan **FUND LOSS** atau **RCE** tanpa preconditions. Untuk paymaster/gas/financial: gold standard = on-chain proof — submit operasi real dan tunjukkan penurunan balance protokol.
- **Escalate dengan menambah proof, bukan adjective.** Jangan pernah inflate claim untuk naikkan severity.

## Severity Classification Pitfall — "Working ≠ Exploitable"

**Exposed credentials yang WORK bukan berarti VULN.**

The "It Works!" Fallacy:
```
"I found an AWS key and it gave me credentials!" → So what? What can those credentials DO?
"I injected data and it returned success!" → So what? Where does that data GO?
"I accessed the admin console!" → So what? Can you bypass auth?
"I got CORS reflection!" → So what? Can you actually steal session data?
"Staging is accessible!" → So what? Is there exploitable content there?
```

Setiap kali menemukan sesuatu yang "works", tanya:
1. Apa yang BISA dilakukan dengan akses ini?
2. Apa yang TIDAK BISA dilakukan (compensating controls)?
3. Apakah ada dampak nyata ke dana, user, atau sistem?
4. Bisakah buktikan dengan PoC, bukan hanya teori?

**Bukti > Adjective**: "AWS credentials obtained but restricted to STS only (19/20 services denied)" > "AWS credentials exposed! HIGH severity!"

## CORS Misconfiguration — Exploitability Checklist

**CORS reflection ≠ session theft.** Before claiming MEDIUM+ for CORS, verify:

### Step 1: Cookie Analysis (CRITICAL)
```
□ What session cookies does the target set?
□ Are they HttpOnly? → If YES, JavaScript CANNOT read them → CORS NOT exploitable for session theft
□ Are they SameSite=None? → If YES, they WILL be sent cross-origin (but still can't read if HttpOnly)
□ Are they stored in localStorage/sessionStorage? → If YES, CORS CAN steal them (Bearer token scenario)
```

### Step 2: Data Exfiltration Proof
```
□ Can you actually READ sensitive data via CORS (not just get empty 401)?
□ Does the endpoint return user data on valid auth?
□ Can you demonstrate data theft with a real attack scenario (HTML page)?
```

### Step 3: Compensating Controls
```
□ Does the app use Bearer tokens in headers (vulnerable) vs HttpOnly cookies (not vulnerable)?
□ Is there CSRF protection that blocks cross-origin state changes?
□ Does the app use SameSite=Strict/Lax cookies?
```

**Bitso case study**: CORS reflection on Keycloak OIDC → `access-control-allow-origin: evil.com` + `credentials: true` → BUT all session cookies are HttpOnly → **CANNOT steal sessions via JavaScript** → Verdict: P4-P5 (informational, not exploitable).

## Staging/Dev Environment — Exploitability Checklist

**Accessible staging ≠ finding.** Before claiming severity for exposed staging:

### Step 1: Content Assessment
```
□ Is there actual application functionality (not just login page)?
□ Are there test accounts, demo data, or sample content?
□ Are there weaker security controls (no CAPTCHA, no rate limit, disabled 2FA)?
□ Are there staging-specific APIs that don't exist in production?
```

### Step 2: Exploitation Path
```
□ Can you register new accounts without restrictions?
□ Can you access internal tools (admin panels, debug endpoints)?
□ Can you escalate from staging to production (shared auth, shared DB)?
□ Can you find credentials, API keys, or secrets in staging?
```

### Step 3: Information Disclosure Value
```
□ What internal URLs/services are exposed via CSP headers?
□ Are there developer tools, version control, or CI/CD endpoints?
□ Does the staging reveal architecture details useful for production attacks?
```

**Verdict guidance**:
- Staging with full app + no auth controls = MEDIUM (attack surface expansion)
- Staging with only login page = LOW (limited attack surface)
- Staging with CSP internal URLs only = INFO (information disclosure)
- Staging with no exploitable content = NOT A VULN (reject)

**Bitso case study**: dev.bitso.com accessible → BUT all API routes redirect to /404 → No test accounts → No weaker controls → Only Keycloak OIDC endpoint works (standard spec) → Verdict: P5 (informational only).

## Keycloak OIDC — Exploitability Checklist (NEW)

**OIDC endpoints are public by spec.** Before claiming severity for Keycloak findings, verify:

### Step 1: Is it required by OpenID Connect spec?
```
□ /.well-known/openid-configuration → PUBLIC BY SPEC (informational only)
□ /protocol/openid-connect/certs → PUBLIC BY SPEC (public keys must be accessible)
□ /protocol/openid-connect/auth → PUBLIC BY SPEC (authorization endpoint)
□ /protocol/openid-connect/token → Requires client_id — check if CORS reflects
```

### Step 2: CORS on Token Endpoint (the real finding)
```
□ Does POST to /token reflect origin with credentials?
□ Does it allow Authorization header cross-origin?
□ Can you demonstrate cross-origin token refresh with stolen refresh token?
→ If YES to all: P3 (Medium) — real exploitation chain
→ If only GET endpoints reflect: P4-P5 (informational)
```

### Step 3: Dynamic Client Registration
```
□ Does registration endpoint return 200 + application/json? → Client registered
□ Does registration endpoint return 200 + text/html? → Login page redirect (NOT registered)
□ Does Trusted Hosts policy block registration? → 403 Forbidden
□ Is the registration endpoint behind auth? → Check if unauthenticated access returns 404
```

### Step 4: Advanced Grant Types
```
□ Token Exchange enabled → Check if any client can exchange tokens
□ CIBA enabled → Check if backchannel auth can be initiated
□ Device Flow enabled → Check if device code can be generated
→ If enabled + valid client found: P1-P2 (privilege escalation)
→ If enabled + all return "invalid_client": P3 (misconfiguration, not exploitable)
```

### Step 5: Staging Environment
```
□ Is staging accessible from public internet?
□ Does staging have same realms/clients as production?
□ Does staging have weaker CORS/CSP/rate limiting?
□ Can you register clients on staging that work in production?
→ If staging = production-equivalent: P3 (attack surface expansion)
→ If staging has unique test data: P2-P3 (info disclosure)
```

### Real Examples (Bitso 2026-08)
| Finding | Response | Verdict |
|---------|----------|---------|
| OIDC metadata exposed | Public by spec | **NOT A VULN** |
| CORS on GET /certs | ACAO=evil.com, ACAC=true | **P5** (public keys, no session data) |
| CORS on POST /token | ACAO=evil.com, ACAC=true | **P3** (token refresh chain) |
| Dynamic registration returns 200 HTML | Login page redirect | **NOT REGISTERED** (Content-Type=text/html) |
| Token Exchange enabled | All requests = "invalid_client" | **NOT EXPLOITABLE** (no valid client) |
| CIBA endpoint returns 404 | Endpoint doesn't exist | **NOT ENABLED** |
| Stage Keycloak exposed | Admin console + CORS + same realms | **P3** (attack surface expansion) |
| No rate limiting on /token | 30+ requests without 429 | **P3** (brute force surface) |
| Weak CSP (unsafe-inline, unsafe-eval) | Reduced XSS protection | **P5** (defense-in-depth) |

## OIDC Discovery — Informational Only Gate

**OpenID Connect SPECIFICATION requires these endpoints to be publicly accessible:**
- `/.well-known/openid-configuration` — Server metadata (MUST be public)
- `/protocol/openid-connect/certs` — Public keys (MUST be accessible for token verification)
- `/protocol/openid-connect/auth` — Authorization endpoint (MUST be accessible for login)
- `/protocol/openid-connect/userinfo` — User info (requires Bearer token, but endpoint itself is public)

**These are NOT vulnerabilities — they are by-design per OpenID Connect Core 1.0 §4.**

Before claiming ANY OIDC endpoint as a finding:
1. Check if it's in the spec-required list above
2. If yes → informational only (P5), not reportable
3. If no → proceed with normal exploitability analysis

**Bitso case:** OIDC metadata, certs, and auth endpoints were tested → all public by spec → NOT a finding. Token endpoint CORS = P3 (real finding).

## Unauthenticated JWT Minting — Validation Protocol (NEW)

When a game/SaaS API has a token creation endpoint that accepts an `ownership_id` and mints JWT without caller verification:

### Step 1: Is the endpoint truly unauthenticated?
```
□ POST to /tokens (or /ownership/{id}/token) succeeds WITHOUT Authorization header?
□ Server does NOT verify caller identity (no wallet challenge, no signature, no CAPTCHA)?
□ JWT returned contains valid player_id, account_id, and claims?
→ If all YES: proceed to Step 2
→ If any NO: NOT A VULN (server verifies caller)
```

### Step 2: Is the ownership_id discoverable?
```
□ API responses leak ownership_id (CORS reflection, stats endpoint, referral API)?
□ XSS on game domain can read ownership_id from localStorage?
□ Account creation returns ownership_id (sequential/predictable)?
□ Third-party API with permissive CORS exposes ownership_id?
□ Enumeration possible (short sequences, known format)?
→ If ANY vector exists: JWT minting is EXPLOITABLE (chain the finding)
→ If NO vector exists: JWT minting is THEORETICAL (informational, P4-P5)
```

### Step 3: What is the real impact?
```
□ Attacker can buy items in victim's account? (financial impact)
□ Attacker can read victim's personal data? (data breach)
□ Attacker can transfer victim's assets? (fund theft)
□ Multiple JWTs can be active simultaneously? (persistence)
□ Refresh token available? (persistent access beyond JWT TTL)
→ Map impact to severity:
   Fund theft / NFT theft → P1 ($3,500-$4,500)
   Account takeover + data access → P2 ($1,500-$2,500)
   Account takeover without financial impact → P2-P3
   JWT minting theoretical (no ownership_id vector) → P4-P5
```

### Step 4: Frame correctly
```
BAD:  "XSS on game domain allows stealing JWT"
      (XSS is the delivery mechanism, not the finding)

GOOD: "Broken Authentication — Unauthenticated JWT Minting via Public API"
      (the root cause is the API accepts minting without auth)

Why: The XSS is one way to get the ownership_id. The real bug is that
the server mints tokens without verifying the caller. This framing
shows the program the systemic auth flaw, not just one attack vector.
```

### Real Example (Aurory 2026-08)
| Check | Result |
|-------|--------|
| Endpoint accepts POST without auth? | ✅ YES — `POST /v1/tokens` returns JWT |
| ownership_id discoverable? | ✅ YES — via CORS, referral stats, XSS |
| Financial impact? | ✅ YES — attacker can buy items in victim's account |
| Multiple tokens active? | ✅ YES — attacker + victim both have valid JWT |
| Refresh token? | ✅ YES — persistent access |
| Verdict | **P2 ($1,500-$2,500)**, potentially P1 with fund theft proof |
| Framing | "Broken Authentication — Unauthenticated JWT Minting via Public API" |

---

## React Client-Side Config — By-Design Gate (NEW)

**React/Vue/Angular apps inject runtime config via client-side JS files.** These files contain values that LOOK like secrets but are PUBLIC BY DESIGN.

### Common file patterns:
```
/v2/env-config.js
/_env.js
/config.js
/runtime-config.js
/env.js
/env.production.js
```

### Values that are NOT reportable (always public):
```
Auth0 Client IDs (client_id)     — OAuth spec requires public client IDs
Auth0 Domain                      — discoverable via OIDC well-known
Datadog RUM token (starts "pub") — public client token, ingestion only
Cloudinary upload preset          — designed for client-side file upload
Pendo / LaunchDarkly IDs          — client-side analytics/feature flags
Google Analytics / GTM IDs        — tracking, public by design
Sentry DSN                        — client-side error reporting
Stripe publishable key (pk_*)     — designed for client-side use
Firebase config                   — Firebase client SDK reads this at runtime
```

### The test: Is it in the CSP whitelist?
If the Content-Security-Policy header explicitly allows the domain hosting the config value, it was INTENTIONALLY made public. Check:
```bash
curl -sI https://TARGET/v2/ | grep -i content-security-policy
# If CSP allows auth0 datadog cloudinary pendo launchdarkly → all values public by design
```

### Verdict
| Value | Works? | Actually Secret? | Verdict |
|-------|--------|-------------------|---------|
| Auth0 client_id | YES | No — public per OAuth 2.0 | **NOT A VULN** |
| Datadog "pub" token | YES | No — ingestion only | **NOT A VULN** |
| Cloudinary preset | YES | No — upload endpoint | **NOT A VULN** |
| Auth0 client_secret | YES | YES — must never be client-side | **P1-P2** |
| API key (not pk_*) in config | YES | YES — depends on permissions | **ALWAYS CHECK** |

**Fireblocks case (2026-09-03):** `sandbox.fireblocks.io/v2/env-config.js` contained Auth0 client_ids, Datadog RUM token, Cloudinary preset, Pendo/LaunchDarkly IDs → all values visible in browser DevTools, CSP whitelisted → **NOT REPORTABLE**.

---

## API Health Endpoint — Disclosure Gate (NEW)

**Health endpoints are common but frequently over-disclose.** The key question is NOT "does /health exist?" but "does /health disclose MORE than needed for health checking?"

### Comparison Technique (MANDATORY)

When finding an info-disclosure on `/health` or `/status`:
1. **Find ALL sibling services** with similar endpoints
2. **Compare disclosure levels** across services
3. **If one service restricts and another doesn't** → the disclosure is NOT by-design

```
Service A: /health → 403 Forbidden
Service B: /health → 200 OK + AWS Account ID + SNS/SQS ARNs + S3 bucket
→ B's disclosure exceeds A's restriction → NOT by-design
```

### What a standard /health endpoint should return:
```json
{"status": "ok", "timestamp": "..."}
```

### What is EXTRA (potentially reportable):
```
AWS Account ID             — enables targeted IAM attacks
SNS/SQS full ARNs          — enables resource enumeration + policy crafting
S3 bucket names            — enables direct bucket access attempts
Memory/RSS thresholds      — internal operational details
Redis/RabbitMQ connection  — backend technology fingerprinting
Full stack trace on error  — RCE surface (always report)
```

### Impact argument for AWS Account ID disclosure:
```
1. Targeted IAM brute-force on specific account (12-digit ID narrows attack)
2. SNS/SQS resource enumeration (publish malicious messages, subscribe to topics)
3. S3 bucket policy crafting (cross-account bucket access)
4. CloudTrail log identification (hide audit trail)
5. Cross-account trust relationship exploitation
6. Cost allocation / billing targeting
```

### Severity mapping:
| Disclosure Level | VRT Category | Priority |
|-----------------|--------------|----------|
| status: ok only | — | NOT A VULN |
| + server version (Express/Node) | Server Security > Fingerprinting | P5 |
| + AWS region | Cloud Security > Misconfigured Services | P4 |
| + AWS Account ID | Cloud Security > Insecure API Endpoints | P3-P4 |
| + full service ARNs + bucket names | Sensitive Data Exposure > Disclosure of Secrets | P3 (escalable to P2) |
| + credentials / tokens / keys | Sensitive Data Exposure > Disclosure of Secrets for Publicly Accessible | P1-P2 |

**Fireblocks case (2026-09-03):** `sb-mobile-api.fireblocks.io/health` returned full AWS infrastructure dump (Account ID `751886943440`, SNS/SQS ARNs, S3 bucket `fireblocks-sandbox-messages`, memory thresholds) while `sb-console-api.fireblocks.io/health` returned 403 → disclosure is NOT by-design, severity P3-P4.

---

## Finding Cross-Check Protocol — 5-Point Verification (NEW)

**Every finding MUST pass ALL 5 points before proceeding to report.** This is the user's explicit quality gate — skip it and the finding gets rejected by triage.

### Point 1: IS IT REAL?
```
□ Freshly reproduced (not old session data)?
□ Response captured (full body, headers, status code)?
□ No fabrication — raw tool output, not paraphrased?
□ Reproducible by anyone with curl/browser?
→ If YES: proceed
→ If NO: DROPPED — do not report
```

### Point 2: IS IT BY-DESIGN?
```
□ Compare with sibling services (same endpoint, different behavior)?
□ Check if feature is documented as public/expected?
□ Is the endpoint functioning as intended (health check, status page)?
□ Is there a SPEC-REQUIRED justification (OIDC, OAuth, etc.)?
→ If clearly by-design: DROPPED
→ If disclosure exceeds by-design scope: proceed
→ If unclear: flag as BORDERLINE, seek escalation path
```

### Point 3: IS IT INFORMATIONAL?
```
□ Does the data enable a specific attack (not just "could be useful")?
□ Would a triager accept this as a standalone finding?
□ Is there real exploitation value beyond fingerprinting?
□ Compare to known-public info (would this be in Google dork anyway?)
→ If purely informational (P5): DROPPED unless chains to higher
→ If has attack value: proceed
```

### Point 4: IS IT AN ASSUMPTION?
```
□ All data extracted from live HTTP response (not inferred)?
□ Attack path documented with actual requests + responses?
□ No "could potentially lead to" — only "does lead to"?
→ If assumption-based: DROPPED
→ If evidence-based: proceed
```

### Point 5: VRT + SCOPE COMPARISON
```
□ Mapped to specific VRT category + priority?
□ Target confirmed in-scope (check program policy)?
□ Severity matches impact (not inflated)?
□ No known program-specific exclusions?
→ If all pass: READY FOR REPORT
→ If scope conflict: DROPPED or flag for user
```

---

## GraphQL-Specific False Positive Gate (VERIFIED)

**GraphQL APIs have unique by-design patterns that look like vulnerabilities but aren't.**

### Introspection Enabled — NOT a Vulnerability
```
□ GraphQL introspection (__schema query) works without auth
□ Schema reveals all types, queries, mutations, subscriptions
□ This is INTENTIONAL for developer experience (DX)
□ Most GraphQL APIs leave introspection ON
→ Verdict: NOT A VULN (informational at best, P5)
```

**Exception**: If introspection reveals admin-only mutations that execute without auth, the finding is the MUTATION EXECUTION, not the introspection.

### Product/Category/Content Data Dump — NOT a Vulnerability
```
□ GraphQL returns product listings, categories, blog posts, pricing
□ Data is the same as what appears on the public website
□ This is a CATALOG — designed to be public
→ Verdict: NOT A VULN (by design)
```

### Error Messages Saying "Permission Denied" — IS Working Auth
```
□ GraphQL mutation returns "Permission denied" or "Not authorized"
□ This means the authorization CHECK WORKED
□ The mutation exists, executed, but was correctly blocked
→ Verdict: NOT A VULN (access control functioning)
```

### "Server Error" vs "Permission Denied" — Critical Difference
```
"Server Error" = mutation executed and FAILED at business logic (POTENTIAL VULN)
"Permission denied" = mutation executed and was BLOCKED by auth (WORKING AUTH)
"Not authenticated" = mutation exists but requires login (POTENTIAL VULN if auth bypassable)

# You need SERVER ERROR or working auth bypass to claim a finding
# "Permission denied" alone is NOT a finding
```

### Feature Flag Enumeration — Check If Security-Critical
```
□ Flags controlling UI behavior only? → NOT A VULN
□ Flags controlling security features (2FA, rate limiting)? → MEDIUM
□ Flags revealing internal roadmap? → LOW (info disclosure)
```

### What IS a GraphQL Vulnerability
| Finding | Severity | Why |
|---------|----------|-----|
| Mutation executes WITHOUT auth (Server Error) | HIGH+ | Code ran before auth check |
| reCAPTCHA bypass (null token works) | HIGH | Automated abuse possible |
| SAML/private keys in JS bundle | CRITICAL | Key theft = account takeover |
| ID enumeration via error messages | MEDIUM-HIGH | Valid IDs revealed |
| Feature flags control security features | MEDIUM | Security bypass possible |
| Password reset without email validation | MEDIUM | Email bombing / user enum |