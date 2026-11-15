# Chime Financial — Comprehensive Intel & Exploitation Plan 2026-09-05

## Target Overview
- **Company:** Chime Financial (US neobank/fintech, Sutton Bank / Stride Bank partnership)
- **Platform:** Bugcrowd (Managed Bug Bounty)
- **Engagement:** `https://bugcrowd.com/engagements/chime`
- **Status:** 🟢 In Progress (started May 6, 2025, no end date)
- **Type:** Pay-for-Success (bounty per accepted vuln)
- **Max Payout:** $20,000
- **Average Payout:** $1,180 (27 rewarded vulns so far)
- **Triage SLA:** 15 days validation
- **Reporter:** BC_USERNAME (@BC_ALIAS.com)

---

## Program Scope (IN-SCOPE)

### Domains (all subdomains IN-SCOPE, including QA/Dev)
- `*.chime.com` — 50+ subdomains discovered
- `*.chimepayments.com` — 20+ subdomains
- `*.chimecard.com`
- `*.chmfin.com`
- `*.chimebank.com`
- `*.saltlabs.com` (acquisition)
- `*.1debit.com` (payment processor)

### Mobile Apps
- Chime iOS App (App Store)
- Chime Android App (Play Store)

### Key Point
**QA/Dev environments are explicitly IN-SCOPE** — permission to test production AND dev/qa

---

## OUT-OF-SCOPE (AVOID — WASTE OF TIME)

- `chime.financial`, `chimescholars.org` (wrong org)
- Debug info disclosure (no sensitive data)
- Missing CSP, HttpOnly/Secure flags on non-sensitive cookies
- Missing SPF/DKIM/DMARC
- Clickjacking on unauth pages without state-changing actions
- CSRF on login/logout
- Open redirects WITHOUT chained exploit
- DoS/DDoS, rate limiting on non-auth endpoints
- Physical access, MITM, unlikely user interaction
- **Social engineering (phishing, vishing, smishing)** ← explicitly excluded
- Missing root/jailbreak detection, cert pinning, obfuscation
- Public API keys (DataDog, Google Maps, Stripe publishable, Auth0 client IDs)
- Cloudinary unsigned upload presets (by-design for client-side use)
- env-config.js with public/publishable keys only

---

## Smart Contract Note
**The attached `DesolexContract` files (exvul.sol + abi.json) are a LayerZero OFT token — NOT Chime-related.**
Chime is a US fintech neobank with NO blockchain tokens. These contracts are **OUT OF SCOPE**. Do not waste time analyzing them for this bounty.

---

## Severity & Payout Framework (Bugcrowd VRT v1.19)

| Severity | Criteria | Examples | Est. Payout |
|---|---|---|---|
| **Critical (P1)** | Multi-user/systemic financial/data impact | Fund theft, double-spend, RCE, SSN leak, SQLi, AWS SSRF | $5K-$20K |
| **High (P2)** | Single-user ATO, PII exposure | Account takeover, single-user fund access | $1K-$5K |
| **Medium (P3)** | Limited non-sensitive info | Email enumeration, non-financial account details | $200-$1K |
| **Low (P4)** | Minimal exploitability | Subdomain takeover (no escalation) | Under $200 |

**Key rule:** Impact × Exploitability. Theoretical bugs with mitigations = Low/Info.

---

## Chime's High-Value Focus Areas (from program guidance)

### A. GraphQL Implementations ⭐
- Query complexity abuse (nested queries for bulk data extraction)
- BOLA/IDOR on GraphQL object access
- Field-level permission bypass (accessing restricted fields)
- Introspection enabled in production?

### B. Mobile Applications (iOS & Android) ⭐
- Native endpoint security flaws
- Session storage vulnerabilities (keychain/keystore vs plaintext)
- IPC mechanism abuse (deep links, app links, intent handling)
- API token extraction from mobile app

### C. Money Movement & Ledger Integrity ⭐⭐⭐ (HIGHEST VALUE)
- Transfer limit bypass (daily/monthly)
- Race conditions in payment/retry logic → double spend
- UI vs backend balance desynchronization
- Transaction replay or duplicate submission
- Negative amount transfers

### D. Identity & Account Lifecycle
- KYC/activation step skipping → funded account without verification
- Referral/rewards abuse loops
- Account state manipulation

---

## Subdomain Attack Map (Recon Results - crt.sh)

### 🔴 HIGH-PRIORITY (likely expose internal APIs/apps)

| Subdomain | Notes |
|---|---|
| `dev.chime.com` | Development environment |
| `agora-dev1-5.chime.com` | 5 dev instances + `agora-qa`, `agora-integ` |
| `employers.wp-dev1-5.chime.com` | 5 employer portal dev instances + `employers.wp-qa` |
| `qa-wp.chime.com` | QA WordPress |
| `stage-wp.chime.com` | Staging WordPress |
| `secure.chime.com` | Authentication gateway |
| `m.chime.com` | Mobile web interface |
| `enterprise.chime.com` | Enterprise portal |
| `interchange.chime.com` | Payment interchange? |
| `mobile-state.chime.com` | Mobile state management |

### 🟠 MEDIUM-PRIORITY (payment processor infra)

| Subdomain | Notes |
|---|---|
| `prod.chimepayments.com` / `dev.chimepayments.com` / `qa.chimepayments.com` | Payment environments |
| `cert.chimepayments.com` / `certification.chimepayments.com` | Certification envs |
| `vcas.prod.chimepayments.com` / `vcas.cert.chimepayments.com` | Visa VCS |
| `incomm.prod.chimepayments.com` / `incomm.integ.chimepayments.com` | InComm integration |
| `processor.1debit.com` | Payment processor endpoint |
| `op-scim.1debit.com` | SCIM provisioning (user management) |
| `schemas.1debit.com` | Schema definitions |

### 🟡 LOW-PRIORITY (likely static/low-risk)
`careers.chime.com`, `investors.chime.com`, `status.chime.com`, `help.chime.com`, `research.chime.com`, email subdomains (marketing, Mailgun)

### 🟢 SALTLABS (acquisition)
- `app.saltlabs.com` + `app.staging.saltlabs.com`
- `cent-api.saltlabs.com` + `cent-api.staging.saltlabs.com`
- `help.saltlabs.com`

---

## Tech Stack Diversity (Multi-Stack Subdomain Testing)

| Subdomain | Stack | Notes |
|---|---|---|
| `*.chime.com` (main) | React/Node.js | Cloudflare protected (1009 geo-block) |
| `nd.chime.com` | AWS ELB | 403, HSTS, all methods blocked |
| `event-router.chime.com` | OpenResty | `/track` + `/v2/track` accessible |
| `research.chime.com` | Django | 301→login, CSP reveals full stack |
| `attachments.chime.com` | SendSafely | `/dropzone/` redirects |
| `beta.heymarvin.com` | Next.js | **Open signup**, build manifest leaked |
| `demo.heymarvin.com` | Django | **Open signup**, CSRF tokens exposed |
| `status.heymarvin.com` | UptimeRobot | Sentry DSN leaked |

---

## Previous Session Findings (Honest Assessment - 2026-09-04)

| Finding | Severity | Impact | Status |
|---|---|---|---|
| F1: S3 Bucket `chime` — Public READ_ACP ACL | P5 (Info) | ACL read-only, no data access | Low-value, not reportable |
| F2: Event Router — Unauthenticated Ingest | P4 (Low) | Schema/validation logic disclosure | User_id from session, rate-limited |
| F3: HeyMarvin Open Registration | P3-P4 | Staging env access → Chime data leak? | Scope issue: `*.heymarvin.com` ≠ `*.chime.com` |
| F4: CSP/Integration Stack Disclosure | P5 (Info) | Third-party integrations revealed | Not reportable alone |
| F5: HeyMarvin Sentry DSN Leak | P5 (Info) | DSN properly secured | Sentry DSNs designed to be public |

### Key Blockers from Previous Session
1. **Cloudflare 1009 geo-restriction** — ALL main Chime endpoints blocked from non-US IP
2. **AWS ELB 403** — `nd.chime.com` blocks all HTTP methods
3. **Event Router session validation** — reads user_id from session, not request body
4. **No source code access** — no .git, config, or Docker files exposed

---

## Key Techniques Validated (from previous session)

1. **Next.js Build Manifest Analysis** — Full route enumeration via `/_next/static/{buildId}/_buildManifest.js`
2. **CSP Header Analysis** — Third-party integration stack discovery
3. **Event Schema Discovery via Validation Errors** — Incomplete payloads reveal required fields
4. **Multi-Stack Subdomain Testing** — Different tech stacks on different subdomains (Next.js vs Django)

---

## Exploitation Hypotheses (PRIORITY ORDER)

### PRIORITY 1 — GraphQL BOLA/Broken Auth (HIGH PAY potential)
```
Target: api.chime.com/graphql or similar
Hypothesis: 
  - Introspection enabled → map all types/queries
  - Access other user's data by changing user_id in queries
  - Field-level bypass (access admin fields as regular user)
Tools: curl, graphql-playground, inql Burp extension
Approach:
  1. Discover GraphQL endpoint (/graphql, /api/graphql, /v1/graphql)
  2. Run introspection query
  3. Map all queries/mutations with authorization requirements
  4. Test each query with two accounts → cross-account access
  5. Test nested queries for data extraction amplification
```

### PRIORITY 2 — QA/Dev Environment Access (HIGH PAY potential)
```
Target: agora-dev*.chime.com, employers.wp-dev*.chime.com
Hypothesis:
  - Dev environments have weaker auth or default credentials
  - Debug endpoints exposed
  - API keys/tokens in dev responses
  - No rate limiting on dev environments
Tools: httpx, nuclei, curl
Approach:
  1. HTTP probe all dev subdomains (NEEDS US PROXY for Cloudflare)
  2. Check for exposed admin panels, debug endpoints
  3. Test for default creds on any auth forms
  4. Check for verbose error messages leaking internals
  5. Look for staging API keys that work in production
```

### PRIORITY 3 — Money Movement Race Condition (CRITICAL PAY potential)
```
Target: Chime mobile app + web API
Hypothesis:
  - Concurrent transfer requests bypass daily limits
  - Transfer retry logic allows double-spend
  - Balance check and debit are not atomic
Tools: Burp Suite, two sessions, Python script
Approach:
  1. Create two Chime accounts
  2. Set up concurrent transfer requests via API interception
  3. Send multiple simultaneous transfers exceeding limit
  4. Monitor if any succeed despite limit
  5. Test P2P transfers with rapid retry
```

### PRIORITY 4 — Session/Token Abuse (HIGH PAY potential)
```
Target: m.chime.com, app Chime APIs
Hypothesis:
  - Session tokens don't rotate after password change
  - JWT with weak signing or alg=none possible
  - Account takeover via session fixation
Tools: Burp Suite, jwt_tool, Python
Approach:
  1. Capture auth flow from mobile app
  2. Analyze JWT/token structure
  3. Test token rotation on sensitive operations
  4. Test for token leakage in deep links
```

### PRIORITY 5 — Salt Labs API Testing (MEDIUM-HIGH)
```
Target: cent-api.saltlabs.com, cent-api.staging.saltlabs.com
Hypothesis:
  - Staging API has weaker auth than prod
  - IDOR on user/employer data
  - API rate limiting bypass
Tools: curl, Burp Suite
Approach:
  1. Map API endpoints (common paths, OpenAPI spec discovery)
  2. Test auth on staging vs prod
  3. Test IDOR on user IDs, employer IDs
  4. Check for CORS misconfig
```

### PRIORITY 6 — 1debit Processor Abuse (HIGH PAY potential)
```
Target: processor.1debit.com, op-scim.1debit.com
Hypothesis:
  - Payment processor API has insufficient auth
  - SCIM endpoint allows unauthorized user provisioning
  - Schema endpoint leaks internal data structures
Tools: Burp Suite, curl
Approach:
  1. Test SCIM without auth → user listing/creation
  2. Test processor API for transaction manipulation
  3. Check schemas for sensitive data model exposure
```

---

## Tools Needed

### Recon
- `httpx` — HTTP probing subdomains
- `nuclei` — vulnerability scanning templates
- `subfinder` — additional subdomain discovery
- `waybackurls` — historical endpoints

### Active Testing
- Burp Suite Professional — interception, repeater, intruder
- `inql` — Burp GraphQL extension
- `jwt_tool` — JWT analysis
- `ffuf` — fuzzing directories/parameters

### Mobile
- Frida — runtime instrumentation
- Objection — mobile app exploration
- Jadx — APK decompilation
- MITMproxy — mobile traffic interception

### Automation
- Python + requests — custom PoC scripts
- curl — quick API testing

---

## Findings to AVOID (Instant Rejection)

1. **By-design behavior** — Chime's products intentionally work certain ways
2. **No financial loss** — Must show potential for actual fund/data loss
3. **Social engineering / phishing** — Explicitly excluded
4. **Theoretical bugs without PoC** — Must be reproducible
5. **Single-parameter IDOR without impact** — Need to show what data/financial action is exposed
6. **Informational findings** — Debug headers, missing headers, version disclosure

---

## Strategy Summary

```
PHASE 1 (Day 1-2): Recon & Enumeration
├── Probe all dev/qa/staging subdomains (US proxy required)
├── Discover GraphQL endpoints + introspection
├── Map mobile app API surface
└── Test 1debit/SaltLabs API for auth gaps

PHASE 2 (Day 3-5): Targeted Exploitation  
├── GraphQL BOLA across user accounts
├── Dev environment access (default creds, debug)
├── Rate limit bypass on money movement
└── Session/token analysis

PHASE 3 (Day 6-8): Deep Dive
├── Race condition testing (double-spend)
├── SCIM endpoint abuse
├── QA environment lateral movement
└── Mobile app deep link / IPC testing

PHASE 4 (Day 9-10): Validate & Report
├── Duplicate all findings with clean PoC
├── Document step-by-step reproduction
├── Generate PDF report
└── Submit via Bugcrowd (Reporter: BC_USERNAME)
```

**Highest probability of bounty:**
1. GraphQL BOLA → $2K-$10K
2. QA/Dev env access → $1K-$5K
3. Money movement race condition → $5K-$20K
4. Session takeover → $1K-$5K

---

## Session Metadata
- **Date:** 2026-09-05
- **Agent:** BREACH v3.0 UNRESTRICTED
- **Context:** Follow-up to 2026-09-04 session (chime-2026-findings.md v1)
- **Next Action:** Phase 1 execution with US-based proxy