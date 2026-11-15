# Pitfalls Library — Bug Bounty

Extracted from `SKILL.md` §Known Pitfalls to keep the skill under the loader cap.
**Read this before Phase 3 (Analyze) and again before declaring a target exhausted.**
Each entry is a real, dated lesson — the failure it caused and the rule it produced.

## ⛔ EXHAUSTED ALL VECTORS — When to Stop and Move On
**Session: Bitso 2026-09-06.** After 20+ unauthenticated attack vectors, ALL returned negative or by-design. The ceiling without a test account is P3 (rate limit, stage env, weak CSP). User said: "udah ada angka yg cukup utk move ke next target" — MOVE ON.

**When ALL of these are true, the unauth surface is EXHAUSTED:**

- [ ] All standard web/API vectors tested → 403/401/WAF-blocked consistently
- [ ] Infrastructure pivots (S3, pre-prod, staging) → AccessDenied or not found
- [ ] Third-party services (Segment, Hightouch, Amplitude, Sentry, Datadog, Auth0, Cloudflare, Zendesk, HubSpot) → all by-design or write-only
- [ ] Client-side JS analysis across ALL environments (prod/dev/staging/mobile) → no exploitable keys or config
- [ ] Mobile app APK → no additional API surface beyond web
- [ ] Auth wall absolute (signup disabled, no device code, no passwordless)
- [ ] Source code audit (if applicable) → out-of-scope or clean

**Decision tree when exhausted:**
```
1. Can you request sandbox/test credentials (Bugcrowd @maintainer)?
   → YES: Document 20+ vectors tested + auth enumeration evidence → request credentials
   → NO: Continue to step 2

2. Is there a related program with deeper scope (source code, MPC, etc.)?
   → YES: Pivot to that program
   → NO: Continue to step 3

3. Have you documented ALL testing + the exhaustion verdict?
   → YES: Present to user as "exhausted — ceiling is X, no further value"
   → NO: Document now (screenshots, endpoint list, by-design analysis)

4. User decides: request credentials, pivot, or move to next target
   → USER DECIDES. Never unilaterally declare "done" — present evidence, let them choose.
```

**Key rule:** Present the exhaustion verdict WITH evidence (full attack vector list, by-design analysis table, severity ceiling). User gets to decide next step — request creds, pivot, or move on. Never keep hammering the same target fruitlessly.

## ⛔ NEVER STOP AT FIRST FINDING — Exhaustive Multi-Finding Rule
**Session: Self-Hosted Bounty Audit 2026-09-04.** User gave 24h per project. Agent found 1 finding (CVSS 5.3), then immediately stopped and tried to generate PDF. User corrected:

> *"Sy kasih waktu temukan Exploit sebanyak mungkin dalam waktu 24 jam. tp kamu baru ketemu 1 yg mana itu jg informational, udh berhenti. Lanjut kan terus, kalau temuan udh mentok kamu deepdive, kl udh juga kamu crosschek ulang, sampai waktu 24 jam tsb tercapai baru kamu generate pdf dgn lengkap."*

**RULE:** When user specifies a time budget per target:
1. **NEVER stop after first finding** — keep testing ALL attack vectors
2. **When stuck** → deepdive on untested endpoints/techniques
3. **When deepdive exhausted** → cross-check all previous findings for variations
4. **Only when time budget is nearly exhausted** → generate ONE comprehensive PDF
5. **ONE PDF per project** containing ALL findings — NOT separate PDFs per finding

**Apply the exhaustive vector checklist** (Phase 4, Step 0 of autonomous-vuln-researcher — 17-vector SPA checklist). All vectors must reach terminal state before report generation.

**Before moving to next project:** ALL attack surfaces documented as tested or explicitly cancelled with blocker reason. No shortcuts.

## ⛔ NEVER Declare "READY TO SUBMIT" Without User Confirmation
**Session: Fireblocks 2026-09-03.** Agent declared F1 "READY TO SUBMIT" after 7-stage pipeline. User challenged: *"Yakin? Kamu udh cek inscopenya udh sesuai dgn yg dicantumkan di bugcrowd utk fireblock? Data disclosed AWS dll sptnya mmg disengaja?"*

**Two critical questions were NOT addressed:**
1. **Scope alignment** — Was the specific endpoint actually in the Bugcrowd program scope? (Yes, confirmed via bountyindex.in aggregator)
2. **By-design analysis** — Is the AWS info disclosure intentional for sandbox environments? (Likely yes — sandbox health endpoints commonly expose infra details for debugging)

**RULE:** After Stage 7 checklist, present findings to user with:
- Scope verification evidence (which source, exact match)
- By-design analysis (arguments for AND against)
- Severity with sandbox-context adjustment
- **Explicitly ask user to approve before generating report**

Never say "READY TO SUBMIT" — say "FINDING READY FOR REVIEW" and let user decide.

## python3 Not Found on Windows
Use `"~/.local/share/Python/bin/python.exe"` or `execute_code` tool.

## Cloudflare WARP VPN DNS Interception — Use Python for True Resolution
**Problem:** When Cloudflare WARP VPN is active, `curl`, `host`, `dig`, and system DNS all return WARP's virtual IPs (`127.0.2.x`) instead of the actual IP. This makes staging domains APPEAR unreachable when they might actually be accessible, and vice versa.

**Fix:** Always use Python's `socket.gethostbyname()` for DNS resolution behind WARP:
```python
import socket
real_ip = socket.gethostbyname("stageui.example.com")
# Returns ACTUAL IP, bypassing WARP DNS interception
```
**Why it works:** Python's socket library uses the system resolver at a lower level than WARP's DNS hook, returning the true DNS record.

## JWT from Browser ≠ API Bearer Token
Browser session tokens (localStorage/cookies) are NOT Fireblocks API keys + JWT pairs.

## By-Design Analysis Framework (MANDATORY for Info Disclosure)
Before declaring any info disclosure finding valid, run this checklist:

**Arguments FOR by-design (weakens finding):**
- [ ] Sandbox/staging environment (testing infra intentionally exposed)
- [ ] Health/readiness endpoint (dev teams need infra visibility)
- [ ] Same data publicly documented (AWS docs, architecture blog posts)
- [ ] Industry-standard practice (Cloudflare health endpoints expose similar data)
- [ ] No authentication required AND endpoint explicitly designed for monitoring
- [ ] Data doesn't enable further attack (AWS Account ID alone ≠ exploitable without additional misconfiguration)

**Arguments AGAINST by-design (strengthens finding):**
- [ ] Production environment with real user data
- [ ] Non-standard endpoint (not /health, /ready, /status)
- [ ] Leaks credentials, tokens, or PII (not just infra metadata)
- [ ] Enables attack chain (AWS Account ID → targeted resource policy attacks)
- [ ] Cross-service comparison shows inconsistency (sandbox leaks, production doesn't)
- [ ] Vendor guidance recommends against (CWE-200 recommendations)

**Severity adjustment for sandbox findings:**
- Sandbox info disclosure: P4 Low ($20-$300) unless it chains to something bigger
- Production info disclosure: P3 Medium ($300-$1,500)
- Sandbox + production comparison revealing pattern: P3 Medium (methodology value)
- AWS Account ID alone: P4 Low (needs additional misconfiguration to exploit)

## ⛔ VERIFY BEFORE CLAIMING — Don't Assume Exploitability
**Session: Kinsta 2026-09-04.** Agent found SAML private key in JS bundle, assumed full account takeover without verifying the complete exploitation chain. User corrected:
> "cek satu persatu apakah benar exploit yg menimbulkan kerugian, bukan sekedar asumsi"

**The trap:** Finding a component (key, endpoint, mutation) ≠ proving it causes harm. Agent assumed:
- "Key in bundle" → assumed it signs production SAML assertions (actually unclear if used for all customers or mock IDP only)
- "Mutation executes" → assumed it returns useful data (actually returns null/perm denied with no data exposure)
- "CAPTCHA bypass" → assumed unlimited bypass (actually rate-limited after ~5 attempts)
- "Feature flag endpoint" → assumed flags can be modified (actually returns 0 flags, read-only)

**RULE: After finding something that LOOKS exploitable, verify the ACTUAL damage path:**

```
STEP 1: Does the endpoint/mutation/feature actually RETURN useful data?
  → Mutation executes ≠ mutation leaks data
  → Key exists in bundle ≠ key is used for signing production assertions
  → Endpoint accessible ≠ endpoint has exploitable behavior

STEP 2: What is the ACTUAL chain from finding to damage?
  → Write each intermediate step
  → Test each step — don't assume any step works
  → If ANY step fails, the chain is broken

STEP 3: What BLOCKS the exploitation chain?
  → Rate limiting, relay state, server-side validation, auth requirements
  → Document blockers explicitly — don't hand-wave past them

STEP 4: Honest severity assessment based on PROVEN chain
  → Proven full chain → severity based on actual impact
  → Partial chain → severity based on the furthest proven step
  → Broken chain → informational or low (document what you DID prove)
```

## ⛔ SOURCE MAP OVERCLAIM — What Is NOT Sensitive (Don't Report Public Keys as Findings)
**Session: TeamViewer 2026-09-07.** Agent extracted source maps from `mv-frontend-react-v5`, found reCAPTCHA site keys, RSA public keys, SRP configuration, and staging URLs. Reported these as "sensitive information disclosure." User corrected: *"Dalam report ini tidak ada sensitive information disclosure — semuanya public keys dan information."*

**The trap:** Source maps reveal EVERYTHING about the client-side code — including things that are intentionally public. The researcher sees "key exposed" and assumes it's a finding, when the key is public by design.

**MANDATORY SELF-FILTER before including any "sensitive data" in a source map finding:**

| Looks like a finding | Actually | Verdict |
|---|---|---|
| reCAPTCHA site key (`6Le...`) | Embedded in every client-side `<script>` tag by Google's design | **SKIP — by-design** |
| RSA/EC public key (PEM) | Public keys are PUBLIC. Only private keys are sensitive. | **SKIP — by-design** |
| SRP configuration (params, group, salt) | Server-side SRP validation makes client params harmless | **SKIP without proof** |
| Feature flags / config | Informational — no security impact | **SKIP** |
| Unpkg CDN URLs | Public package registry links | **SKIP** |
| `webpackChunkName` labels | Development metadata, no security value | **SKIP** |
| Staging URLs in source | Must PROVE reachability first (see below) | **CONDITIONAL** |

**What IS a finding from source maps:**
- ✅ **Private keys** (RSA/ECDSA/EdDSA PRIVATE keys, not public)
- ✅ **API tokens / bearer secrets** (not public publishable keys)
- ✅ **Database credentials** (connection strings, passwords)
- ✅ **Internal API endpoints** that reveal business logic or PII access patterns
- ✅ **Hardcoded secrets** (JWT signing keys, encryption keys, admin credentials)
- ✅ **Pre-production data** with real PII (not test data)

**Staging URL Reachability Gate:**
When source maps reveal staging/dev URLs (`stageui.*`, `ui-test.*`, `preprod.*`):
1. **DNS resolution check:** `socket.gethostbyname(hostname)` — if resolves to `127.x.x.x`, it's an internal-only domain (NOT publicly reachable)
2. **HTTP probe:** `curl -sk -o /dev/null -w '%{http_code}' --max-time 5 <url>` — 000/timeout = unreachable
3. **Only if BOTH pass:** staging URL is a valid attack surface. If DNS returns loopback, the staging system is on an internal network and CANNOT be tested remotely.
4. **DO NOT claim** "staging environments likely have weaker security controls" without proving the staging URL is actually accessible.

**Impact reframing — what to highlight instead:**
The real value of source map recon is the **API endpoint catalog** — complete list of routes, parameters, auth modes, and request structure. This is the reconnaissance payload, not the "leaked keys."

**Presentation format when source map findings are mixed:**
```
SENSITIVE (truly exploitable):
- [private keys, credentials, internal PII endpoints]

NOT SENSITIVE (by-design, public, informational):
- reCAPTCHA site keys — public by Google's design
- RSA public keys — public keys are not secrets
- Feature flags — informational
- Staging URLs — [DNS resolves to 127.0.2.2, NOT reachable]

RECON VALUE (attack surface intelligence):
- 20+ internal API endpoints with auth modes
- Request/response structure for each endpoint
- Internal naming conventions (versioned APIs, admin routes)
```

## ⛔ SEVERITY INFLATION KILL — The #1 Credibility Killer
**Session: Kinsta 2026-09-05.** Agent extracted SAML private key from client bundle, attempted multiple relay state bypasses, ALL FAILED (20+ approaches). Agent then presented the finding as "HIGH — Key Exposure" with a chain that was architecturally dead. User's exact response:

> *"Omong kosong brrti temuan diatas, karna take over akunnya d block, kamu harus belaja lebih baik lagi saat Exploit, jgn kasih sy nonsense, temuan high, critical padahal omong kosong belaka"*

**The core mistake:** Presenting extracted artifacts (keys, endpoints, mutations) as HIGH/CRITICAL findings when the exploit chain is BLOCKED at a server-side control that cannot be bypassed.

**THE RULE — SEVERITY MUST MATCH PROVEN CHAIN, NOT ASSUMED CHAIN:**

```
SEVERITY MATRIX (only based on PROVEN, UNBLOCKED chain):

Chain FULLY proven → actual impact determines severity:
  - Account takeover → HIGH/CRITICAL
  - Data exfiltration → HIGH
  - Financial impact → CRITICAL

Chain PARTIALLY proven (blocked at step N) → severity of step N-1:
  - Key extracted but can't be used for signing → INFORMATIONAL
  - Endpoint accessible but returns null/permission denied → INFORMATIONAL
  - Bypass attempted but blocked by server-side control → INFORMATIONAL
  - Mutation exists but doesn't leak data → INFORMATIONAL

Chain BROKEN (no path from finding to damage):
  - Private key in client bundle + can't sign valid tokens → LOW/INFO
  - Public API endpoint + auth required → NOT A FINDING
  - Feature flag enumeration + returns 0 flags → NOT A FINDING
```

**ABSOLUTE RULES:**
1. **NEVER claim HIGH/CRITICAL if ANY step in the chain is blocked** — blocked chain = INFORMATIONAL at best
2. **"Key exposed in client bundle" is NEVER a finding on its own** — it's only a finding if you can USE the key to cause damage
3. **"Endpoint/mutation accessible without auth" is NEVER a finding** — it's only a finding if it returns useful data or performs privileged actions
4. **If you need to say "with valid SAML domain this would be CRITICAL" → it's NOT CRITICAL** — the domain verification IS the security control, and it WORKS
5. **Present FACTS first, then hypothetical chain** — "Key extracted ✓ → Signing tested ✓ → BLOCKED by relay state ✓ → Chain broken ✗ → Severity: INFORMATIONAL"

**Self-check before presenting any finding:**
- [ ] Can I demonstrate the FINAL impact (account takeover, data leak, financial loss) WITHOUT assuming any server-side behavior?
- [ ] Is every step in my chain PROVEN with evidence?
- [ ] If I remove all assumptions, what's left? THAT'S my severity.
- [ ] Would I feel embarrassed presenting this to a senior pentester? If yes, it's probably inflated.

**Presentation format when verification is partial:**
```
CONFIRMED (what you proved):
- [specific finding with evidence]

NOT CONFIRMED (what you assumed but couldn't prove):
- [assumption] — BLOCKED BY: [specific blocker]

ATTACK CHAIN: [step 1] → [step 2] → BLOCKED AT [step 3]
```

**Why this matters:** Presenting a finding as "CRITICAL account takeover" when the chain breaks at step 3 wastes user time and erodes credibility. Honest partial findings are MORE valuable than inflated claims.

---

## ⛔ FINDING QUALITY GATE — "Informational" ≠ Exploitable Bug
**Session: Fireblocks 2026-09-03 + Adafruit 2026-09-04.** User repeatedly rejected findings:
> *"Yg kamu tunjukkan itu semua informational, bukan bukti valid bug yg bs diexploit, cari lbh dalam lagi yg berimpak pada data, sistem, user, dan dana nasabah"*
> *"temuan yg kamu sebut itu hanya informational, y wajar product n dan kategori itu nampak, cari dr sisi lain"*

**RULE: Before presenting ANY finding to user, run this gate:**

```
IMPACT CHECKLIST (ALL must be YES for at least one):
□ Can this directly compromise user data (PII, credentials, financial)?
□ Can this directly affect system integrity (modify config, inject code)?
□ Can this directly cause financial loss (unauthorized transfer, fund theft)?
□ Can this chain to a higher-impact vulnerability with proof?

IF ALL NO → It's INFORMATIONAL. Do NOT present as "finding ready for review."
Do NOT generate PDF. Do NOT waste time on severity scoring.
INSTEAD: Keep digging. Pivot to infrastructure, JS bundles, third-party services.
```

**Common false positives to self-filter:**
- AWS Account ID disclosure (sandbox) → informational unless chained to resource policy attack
- Health endpoint metadata → informational unless enables lateral movement
- env-config.js client IDs → informational (public by design) unless chained
- Server crash (500) on /signup → low unless causes DoS or data corruption
- Auth0 OIDC config exposed → informational (standard OIDC discovery)
- CORS on auth endpoints → informational (Auth0 default behavior)
- API endpoints behind auth returning 401 → expected behavior, not a finding
- **Public product/category/price API on e-commerce sites** → by-design (competitors scrape this daily)
- **CORS wildcard without credentials** → informational (no cookie theft possible)
- **User enumeration via API error messages** → informational (standard behavior)
- **Missing security headers** → informational/low (Cloudflare handles most anyway)
- **Public Sentry DSNs in JS bundles** → informational (DSN ≠ auth, only sends errors)
- **Open ports requiring auth (MQTT, Redis, etc.)** → informational unless auth bypass works
- **Session cookie named "admin_session"** → informational (naming != privilege)
- **Cloudinary unsigned upload presets in env-config.js** → ALWAYS by-design. Unsigned presets are designed for client-side use; their presence is intentional. Submitting this = wasted time (H1 finding F1, failed VRT: "Cloudinary Upload Preset Abuse — by-design")
- **Cloudinary CORS `*` on public upload endpoints** → by-design. Public upload requires `*` CORS to work from browser (H1 finding F2, failed VRT)
- **env-config.js with public/publishable keys only** → informational. Auth0 client IDs, Stripe publishable keys, Datadog tokens are public by design (H1 finding F3, failed VRT)
- **Staging bucket access with random UUIDs** → by-design if requires valid UUID. If UUID is guessable, escalate (H1 finding F4, not reproducible)

**Self-filtering rule:** If you need to explain WHY it's a finding instead of it being obvious from the PoC → it's probably informational. Real bugs speak for themselves. If a triager would say "and?" after reading your finding, it's informational.

---

**Privy SIWS Auth — Bypass Authentication Wall on Web3 Apps (No Real Wallet Needed)**
→ `references/privy-siws-auth-bypass.md`

If the target uses Privy (auth.privy.io) for wallet-based login, you don't need a real wallet or any browser. The full SIWS flow can be completed from Python in 3 requests with a locally-generated Ed25519 keypair (PyNaCl). This gives you a valid JWT for every authenticated endpoint — matches, wallet, profile, trading, withdrawals. See the reference for the exact recipe, message format (varies per app), and common failure modes. Works on any Privy-protected dApp: just extract the `privy-app-id` and `SIWS message template` from the JS bundle.

## Sandbox/Staging Environment Attack Surface Patterns**
**Key lesson: Sandbox environments are designed to be hardened against external researchers.**

**What sandbox environments typically have:**
- No public signup (account creation blocked)
- Robust auth (API key + JWT dual auth, certificate pinning)
- Active WAF (Cloudflare, Akamai) blocking all injection attempts
- Debug endpoints behind auth (not public)
- Same infrastructure as production BUT with stronger restrictions

**What sandbox environments typically leak (informational only):**
- Health endpoint metadata (AWS account IDs, queue names, bucket names)
- env-config.js (Auth0 client IDs, feature flags, monitoring tokens)
- Auth0 OIDC discovery (well-known endpoints, client IDs)
- X-Powered-By headers, CSP policies

**Where REAL bugs hide in sandbox environments:**
1. **Config bugs** — env-config.js with wrong values (double-equals, typos) that break auth flows
2. **Crash bugs** — 500 errors on specific input patterns (potential for DoS or info leak)
3. **Inconsistency** — sibling endpoints with different behavior (one leaks, others don't)
4. **Third-party services** — Auth0, Cloudinary, Stripe integration bugs
5. **Infrastructure** — S3 bucket policies, SQS/SNS ACLs, CloudFront configs
6. **Client-side** — React app JS bundles, source maps, debug flags

**Self-filtering for sandbox findings:**
- AWS Account ID alone → P4 Low (sandbox-specific, needs chaining)
- Health endpoint metadata → P4 Low (standard in sandbox envs)
- env-config.js with public keys → Informational (by design)
- env-config.js with internal URLs → P3 Medium (information disclosure)
- env-config.js with config bugs → P3 Medium (potential auth bypass)
- Server crash without rate limit → P3-P4 (DoS potential)

**Presentation rule:** When presenting sandbox findings, ALWAYS:
1. Acknowledge the sandbox context upfront
2. State explicitly whether it chains to production impact
3. Compare with production (if accessible) for severity adjustment
4. Be honest about by-design likelihood

## ⛔ WELL-DEFENDED SITE AUDIT — The "Nothing Works" Trap
**Session: Adafruit 2026-09-04.** Cloudflare + proper auth + minimal external attack surface. 20+ phases of testing all returned negative. User said to keep going.

**Characteristics of well-defended sites:**
- Cloudflare WAF blocking SQLi, SSTI, CRLF, XXE, path traversal
- Session cookies properly configured (Secure=True, HttpOnly=True)
- CSRF protection present
- Rate limiting active (per-session, not per-IP)
- Auth required for all sensitive endpoints
- WebSocket requires API key
- Origin IP blocked (403) for common paths

**What NOT to report on these sites (ALL informational):**
- Public API dumps (product catalog, categories, pricing)
- CORS wildcard without credentials
- User enumeration via error messages
- Sentry DSNs in JS bundles
- Missing security headers
- Open auth-protected ports
- Session cookies named "admin" something

**What TO test when standard vectors fail (ordered by likelihood):**
1. **Business logic** — checkout flow, pricing, coupon/gift card abuse, quantity manipulation
2. **IDOR** — user-specific data (orders, invoices, addresses, API keys) with sequential/predictable IDs
3. **Race conditions** — double-spend, price update during checkout, TOCTOU on gift card redemption
4. **Account takeover** — password reset flow weaknesses, OAuth misconfiguration, email verification bypass
5. **Stored XSS** — user profile fields, product reviews, support tickets, feedback forms
6. **Privilege escalation** — normal user → admin via API parameter manipulation
7. **SSRF via app features** — webhook URLs, image import, RSS feed parser, preview functionality
8. **Third-party integration abuse** — payment processor test mode, email service, analytics proxy
9. **Infrastructure pivots** — staging/dev subdomains, non-Cloudflare origins, S3 bucket policies
10. **Client-side** — source maps, debug flags, hidden admin routes in JS bundles, localStorage sensitive data, `__NEXT_DATA__` script tag (emails, config, internal URLs)

**Decision rule:** If you've tested 10+ standard vectors and ALL are negative, stop repeating the same tests. The vuln is either (a) in business logic you haven't traced, (b) in infrastructure you haven't found, or (c) genuinely not there. Switch to manual code review of JS bundles and trace every user-controlled input through the full processing pipeline.

## ⛔ SLITHER PROXY FALSE POSITIVES — Don't Chase Ghosts in Upgradeable Contracts
**Session: Paxos Cantina 2026-09.** Slither scan on proxy/upgradeable contracts produces hundreds of findings that are ALL false positives. Presenting them wastes user time and destroys credibility.

**Universal false positives on upgradeable/proxy contracts:**

| Detector | Why it's false positive | Pattern |
|---|---|---|
| `uninitialized-state` | Storage initialized via `initialize()` not constructor — standard proxy pattern (EIP-1967, OpenZeppelin Transparent/UUPS) | Any contract with `initialize()` function |
| `external-function` | Proxy admin/implementation split creates "unprotected" external calls that are actually admin-only via proxy routing | Any TransparentUpgradeableProxy |
| `constable-states` | Implementation contract states look "mutable" but are actually proxy storage slots (immutable in practice) | Proxy + implementation pair |
| `arbitrary-send-eth` on TimelockController | TimelockController's `executeBatch` sends ETH — that's its purpose, not a vulnerability | OZ TimelockController |
| `incorrect-exp` on OZ Math library | XOR used in Math.sol intentionally for gas-efficient swap, Slither misinterprets as exponentiation | OpenZeppelin Math.sol |

**RULE:** When scanning upgradeable contracts with Slither:
1. **Filter proxy patterns first** — check for `initialize()`, `proxyAdmin`, `implementation` slots
2. **Suppress known false positives** in config rather than reporting them
3. **Focus on LOGIC bugs** in business logic (reward calculations, access control modifiers, share math)
4. If >50% of findings are `uninitialized-state` or `external-function` → the scan is dominated by proxy noise, not real bugs

**Hardhat Compilation Failure Taxonomy (multi-repo audits):**
When scanning multiple repos and some fail to compile:
- `YOUR_PAXOS_API_KEY is not set` → repo needs API key in env for deployment scripts (not needed for Slither if you can isolate Solidity-only config)
- `Cannot find module 'hardhat'` → Hardhat not installed locally (`npm install --legacy-peer-deps`)
- `ENOTEMPTY` / corrupted `node_modules` → `rm -rf node_modules && npm install --legacy-peer-deps`
- Missing import paths → repo uses workspace/monorepo deps not present in standalone clone

**Fix strategy:** Patch `hardhat.config.js` to remove API key requirements for compilation-only (comment out the deployer config), or use a minimal Solidity-only config for Slither.

## Cloudflare 1009 = Geo-Restriction (Not WAF Block)
**Session: Chime 2026-09-04.** HTTP error 1009 from Cloudflare means **geo-restriction**, NOT a standard WAF block. All `*.chime.com` subdomains returned 1009 from a non-US VPS, completely blocking access to QA/staging environments.

**Key distinction:**
- 1009 = `Access denied` (geo-blocked by Cloudflare firewall rule) — need US-based proxy/VPN
- 1020 = `Access denied` (custom firewall rule triggered) — might be bypassable
- 403 = Standard Cloudflare block — might be bypassable with headers

**What 1009 blocks:** Everything. No response body, no headers, no way to test any endpoint. The ENTIRE attack surface behind Cloudflare is invisible.

**Pivot options when geo-blocked:**
1. US-based VPS or VPN (essential for geo-blocked targets)
2. CloudFront direct distributions (bypass Cloudflare)
3. Non-Cloudflare subdomains (event-router, nd, research, attachments)
4. Third-party services (HeyMarvin, SendSafely, status pages)
5. Mobile app API endpoints (may use different CDN/path)
6. DNS resolution → direct IP → Host header (bypass Cloudflare DNS)

**Don't waste time:** If ALL subdomains return 1009, stop testing and get a US proxy. No amount of header manipulation bypasses geo-restriction.

## ⛔ SOURCE CODE ANALYSIS BEFORE SCOPE VERIFICATION
**Session: Fireblocks 2026-09-03.** Agent did deep source code analysis across 5 repos (ncw-backend-demo, plugin-based-callback-handler, ts-sdk, py-sdk, btc_tx_validation), finding real vulnerabilities — then discovered NONE were in scope. Hours of work wasted.

**Root cause:** Bypassed Stage 1 (Scope) to jump to technical analysis. User corrected: *"Cek inscopenya dl, kl masuk, br dkerjakan"* (Check scope first, if in-scope, then do the work).

**RULE:** Source code analysis, smart contract audits, and API testing are ALL blocked until scope is verified. No exceptions. The bounty-targets-data.json method (below) takes 30 seconds. Always run it first.

**Pattern to watch for:** When repos/tools/SDKs are publicly available but NOT listed in program scope, findings in them are NOT payable. Demo repos, reference implementations, and example code are commonly excluded.

## Bounty-Targets-Data Scope Extraction (Bugcrowd — RELIABLE METHOD)
**Problem:** Bugcrowd program pages are React SPA — `web_extract` returns login wall, `curl` returns empty `<div id="root">`. Scope data is NOT in static HTML.

**Working pattern (proven):** The `arkadiyt/bounty-targets-data` repo dumps scope to `data/bugcrowd_data.json` hourly.

```bash
# Extract scope for a specific program
curl -s "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/bugcrowd_data.json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for eng in data:
    if 'PROGRAM_NAME' in eng.get('name','').lower():
        print(json.dumps(eng, indent=2))
"
```

Returns: `targets.in_scope[]` with `type`, `target`, `uri`, `name`. Verified working for Fireblocks (`fireblocks-mbb-og` + `fireblocks-mbb-og2`).

**Also works for Immunefi:** `data/immunefi_data.json` has same structure.

**Fallback (if bounty-targets-data fails):**
1. **bountyindex.in** — Server-rendered, has extracted scope data
2. **Direct Bugcrowd extraction** — Last resort, usually fails for React SPAs

## ⛔ bounty-targets-data Mixed-Type Array — String Entries Cause AttributeError
The `targets.in_scope[]` array in `arkadiyt/bounty-targets-data` can contain **raw strings** mixed with dicts. Example: `"targets": [{"type":"URL", "target":"*.chime.com"}, "*.chimebank.com"]`. Calling `.get()` on a string entry crashes with `AttributeError: 'str' object has no attribute 'get'`.

**Fix:** Always guard with `isinstance(t, dict)` before calling `.get()`:
```python
for t in eng.get('targets', {}).get('in_scope', []):
    if not isinstance(t, dict):
        print(f"[SKIP non-dict] {t}")
        continue
    # ... normal .get() calls
```
**Also:** Target names may have trailing whitespace/tabs (e.g., `"*.chimebank.com\t"`). Always `.strip()` before matching.

## Aggregator Scope Extraction (Bugcrowd React-Rendered Pages)
**Problem:** Bugcrowd program pages are React SPA — `web_extract` returns login wall (503 chars), `curl` returns empty `<div id="root">`. Scope data is NOT in static HTML.

**Working pattern:**
1. **bountyindex.in** (PRIMARY) — Server-rendered, has extracted scope data
   ```
   web_search("bountyindex.in PROGRAM_NAME") → find cached page
   web_extract([url]) → returns scope data with target URIs
   ```
   - Search for: `target_path` or `asset_identifier` in output
   - If no JSON structure, grep for domain patterns in raw HTML
   
2. **Alternative aggregators** (if bountyindex fails):
   - `strike.fyi` — Usually empty/loading (SPA)
   - `bountyhunte.rs` — May have limited data
   - `bbradar.io` — None found

3. **Direct Bugcrowd extraction** (last resort):
   ```bash
   curl -sL "https://bugcrowd.com/engagements/PROGRAM_ID" > page.html
   # Search for scope data in HTML — often empty for React SPAs
   grep -oP '"target_url":"[^\"]+' page.html
   ```

**Verification:** After extraction, always confirm the exact URLs match what you're testing. A scope mismatch = wasted findings.

## PortSwigger JS-Rendered Pages
CURL returns 503 for lab URLs. Use `browser_navigate` + JS extraction.

## Tool Installation Audit Workflow
When tools are missing or status unclear: (1) run audit script from `references/tool-installation-windows.md`, (2) install Go runtime first if missing, (3) `go install` for Go tools with `timeout=300`, (4) use PowerShell `Invoke-WebRequest` for GitHub downloads (curl fails on redirects), (5) for tools needing admin/special deps (nmap, aderyn, mythril), document the blocker and find Go-based alternatives (naabu replaces nmap, slither replaces aderyn). Full guide + pitfalls: `references/tool-installation-windows.md`.

## VRT JSON Programmatic Lookup (Bugcrowd — Correct Structure)
The VRT taxonomy at `bugcrowd-vrt/src/data/vrt.json` has CHANGED. `content` is now a **list** of top-level categories (not a dict with `children`). Each entry has `id`, `name`, and `children[]` for sub-entries.

**Working lookup code:**
```python
import json, urllib.request
url = "https://raw.githubusercontent.com/Bugcrowd/vrt/master/src/data/vrt.json"
data = json.loads(urllib.request.urlopen(url).read())
# content is a LIST, not dict — iterate with for, not .get()
for category in data['content']:
    for entry in category.get('children', []):
        if 'social_engineering' in entry.get('id', ''):
            print(entry)  # 'name': 'Social Engineering', 'id': 'P4.social_engineering'
            break
```
**Common error:** `data['content']['children']` raises `TypeError: list indices cannot be slices or ints` because `content` is a list of dicts, each with `children`. Always `for category in data['content']`.

## Decision Gate — When Pivoting Is Futile
After exhausting all attack vectors on a hardened sandbox/target, before continuing to dig fruitlessly:

**STOP digging when ALL of these are true:**
1. All standard web/API vectors tested → 403/401/WAF-blocked consistently
3. Infrastructure pivots (S3, pre-prod, staging) → AccessDenied or not found
4. Third-party service analysis (Auth0, Cloudinary, Stripe) → all by-design
5. Client-side JS analysis → no secret keys, no debug endpoints, no exploitable config
6. Source code audit → out-of-scope or no exploitable findings

**When pivoting IS still worth doing (DON'T stop):**
- You haven't tested business logic flows (checkout, payment, account creation)
- You haven't checked for race conditions on any endpoint
- You haven't tried IDOR on user-specific data (orders, invoices, API keys)
- You haven't checked mobile app APK for different API surface
- You haven't tested GraphQL introspection (even if REST returned 401)
- You haven't enumerated staging/dev subdomains from CT logs

**User decision tree:** *"先验证scope → outscope则op2 → inscope则PDF+SS+PoC → 然后op2"*

## Skill Delivery to Other Agents
To share this mega-skill externally: `powershell Compress-Archive -Path "<skill_dir>\*" -DestinationPath "bug-bounty-mega-skill.zip"`. Include all of SKILL.md + references/ directory. Zip is ~334KB. Note: target agent must extract and load as a skill — content is self-contained.

## ⛔ AUTHENTICATION BLOCKER — When All In-Scope APIs Are Locked and Signup Is Disabled
**Session: Fireblocks 2026-09-04.** All 3 in-scope sandbox API endpoints require JWT + API key + `sub` claim. Auth0 signup is administratively disabled. 17 attack vectors exhausted — ALL blocked by the authentication wall.

**⚠️ SPECIAL CASE: Privy-protected web3 apps — authentication is BYPASSED via SIWS.** If the target uses Privy wallet auth, you do NOT need signup or real credentials. See `references/privy-siws-auth-bypass.md` — 3 requests from Python with an Ed25519 keypair gives you a valid JWT in 10 seconds.

**Characteristics of this blocker:**
- All in-scope API endpoints return 401/403 without valid auth token
- Auth0/OAuth signup endpoint returns `"public signup is disabled"`
- No alternative account creation path (no device code, no passwordless, no dynamic registration)
- Password grant exists but requires valid credentials (can't enumerate)

**Decision tree when facing this blocker:**

```
1. Can you get sandbox/test credentials?
   → YES: Request from bounty program (@maintainer on Bugcrowd)
   → NO: Continue to step 2

2. Is there a related program with deeper scope?
   → YES: Pivot (e.g., Fireblocks MPC MBB has source code scope)
   → NO: Continue to step 3

3. Are there unauthenticated attack surfaces NOT yet tested?
   → YES: Test them (see list below)
   → NO: Continue to step 4

4. Has infrastructure pivoting been exhausted?
   → YES: Conclude — target needs authenticated access
   → NO: Pivot to infrastructure (see pivot list)
```

**Unauthenticated surfaces to test BEFORE requesting credentials:**
- env-config.js / feature flags (config bugs, double-equals, typos)
- JS bundle API endpoint enumeration (full API surface from SPA)
- Third-party service abuse (Cloudinary, Auth0 OIDC, Sentry, analytics)
- Health/info endpoints (info disclosure, version leakage)
- Cloudflare ban behavior (different subdomains = different rules)
- Host header injection (routing manipulation)
- JS source maps (internal code structure)
- GraphQL introspection (even if REST returned 401)
- Error message differential analysis (reveals validation pipeline)

**Auth0 enumeration patterns (detect signup status without account):**
- `/dbconnections/signup` with different `user_metadata` types → reveals format validation order
- `/oauth/token` with different `grant_type` → reveals enabled grant types per client
- `/oidc/register` → 404 = disabled, 200 = enabled
- Password grant error: same error for all emails → no enumeration possible

**JWT error code differential analysis (map auth validation pipeline):**
- Send requests with progressively more valid tokens
- Different error codes reveal each validation step (no token → bad format → missing claim → bad claim format)
- Use this to understand exact auth requirements without source code

**When to STOP and request credentials:**
- All unauthenticated surfaces tested → informational/low only
- Infrastructure pivots exhausted → by-design or AccessDenied
- Source code (if in-scope for separate program) → well-written, no exploitable bugs
- Time investment exceeds 50% of budget without finding

**Presentation rule:** When concluding with "need sandbox account," present:
1. Complete list of 17+ vectors tested (exhaustive evidence)
2. Auth0 enumeration results (signup is disabled, not just untested)
3. Error code differential analysis (auth pipeline mapped)
4. Remaining attack surfaces that WOULD be tested with auth (justify the request)
5. Explicitly ask user to approve requesting credentials before messaging @maintainer

## Crypto Library Audit (MPC, Threshold Signatures, Custom Crypto)
When target is a cryptographic library (not smart contract), load `crypto-library-audit` skill. Covers C/C++/Rust/JS MPC implementations, Paillier, batch verification, seed/entropy analysis. Distinct from `smart-contract-audit` (on-chain Solidity).

**Key pivot:** When sandbox API is hardened and web surface exhausted, clone the target's source code repos for crypto implementation audit. Real bugs hide in parameter sizing (uint8_t vs uint64_t), seed buffer over-reads, and arithmetic mode switches.

**STOP rule for crypto audits:** After 3+ disproved findings in a crypto library, the implementation is likely sound. Don't keep digging — pivot back to web/API/infrastructure. Well-audited crypto (Fireblocks, OpenZeppelin, etc.) is genuinely hard to break. The version downgrade path, batch verification bypass, and buffer over-read are common rabbit holes that all lead to "not exploitable." See `crypto-library-audit` skill for detailed disproof patterns.

## Next.js Build Manifest — Full Route Enumeration
**Session: Chime/HeyMarvin 2026-09-04.** Every Next.js app exposes its complete route structure via build manifest files. This is one of the most powerful recon techniques for modern web apps.

**Step 1: Get __NEXT_DATA__ from any page**
```bash
curl -s "https://TARGET.com/any-page/" | grep -oP '"buildId":"[^"]+"'
# Returns: "buildId":"BhOKF_7n48o5yJueL6FiG"
```

**Step 2: Fetch build manifest**
```bash
curl -s "https://TARGET.com/_next/static/BhOKF_7n48o5yJueL6FiG/_buildManifest.js" | \
  grep -oP '/[a-zA-Z0-9/_-]+' | sort -u
# Returns EVERY route in the application, including:
# - /accounts/signup, /accounts/login, /accounts/password_reset
# - /integrations, /projects, /settings, /admin
# - /api/* routes
# - /onboarding/* flows
# - /_next/data/{buildId}/*.json (data routes for SSR pages)
```

**Step 3: Test data routes (SSR page data)**
```bash
curl -s "https://TARGET.com/_next/data/{buildId}/accounts/signup.json"
# Returns page props — may leak server-side data
```

**Why this matters:** Build manifest reveals routes that robots.txt hides, auth walls protect, and sitemaps don't list. It's the APPLICATION MAP that developers assume attackers can't see.

**Also extract `__NEXT_DATA__` from the same page** — it contains staff emails, internal URLs, password policy, lockout config, and MongoDB IDs. See `references/nextjs-nextdata-disclosure.md` for full extraction methodology and severity assessment.

**Cross-platform check:** Same site may run different stacks on different subdomains (e.g., beta = Next.js, demo = Django). Test build manifest on each.

## CSP Header — Third-Party Integration Stack Discovery
**Session: Chime 2026-09-04.** Content-Security-Policy headers reveal the COMPLETE technology stack including internal third-party integrations that are never mentioned in marketing or docs.

```bash
curl -sI "https://TARGET.com/login" | grep -i 'content-security-policy'
```

**Parse CSP directives to find:**
- `script-src` → Analytics (Plausible, Segment), monitoring (Sentry, New Relic), chat (Intercom), feature flags (Pendo, LaunchDarkly)
- `connect-src` → API endpoints, WebSocket URLs, analytics proxies
- `frame-src` → Embedded services (CloudflareStream, YouTube, Calendly)
- `style-src` → CSS frameworks (Chakra UI, Tailwind)
- `img-src` → CDN hosts, S3 buckets
- `font-src` → Font services

**Impact:** Each third-party service is a potential attack surface — a misconfigured Sentry DSN, an over-permissive Intercom integration, or a public Segment write key.

**Also check:** `x-source-version` or `x-git-sha` headers for git commit hash leakage (gives exact code version).

## Subagent Refusal on Offensive Tasks
Subagents REFUSE active attack payloads. **Run ALL offensive tests directly via terminal/execute_code.** Do NOT delegate SQLi, XSS, SSRF, or active exploitation to subagents — they will refuse or timeout. Use `execute_code` from main thread for all attack-phase testing.

## ⛔ GRAPHQL ACCOUNT LOCKOUT BYPASS — Portal Locks, GraphQL Doesn't
**Session: Origin Energy / MyConnect 2026-09-04.** Portal login form enforces 3-attempt lockout (30-min), but GraphQL `loginUser` mutation processes unlimited attempts with zero lockout.

**The trap:** Researchers test the portal form, hit lockout after 3 attempts, and conclude "brute force blocked." They don't test the GraphQL endpoint separately.

**Detection pattern:**
```
1. Send 3 wrong passwords via portal form → "Your account has been locked"
2. Send 30 rapid requests via GraphQL loginUser mutation → ALL return "email or password incorrect"
3. Portal lockout = ENFORCED. GraphQL lockout = BYPASSED.
```

**Why this happens:** Payload CMS has separate auth pipelines for the portal form (Next.js middleware) and the GraphQL API (direct database access). Lockout is enforced at the middleware layer, not the database layer.

**Severity:** P3 Medium (brute force amplification) → P1 Critical if brute force succeeds

**Rule:** When testing any target with account lockout, ALWAYS test GraphQL/REST endpoints SEPARATELY from the main login form. The lockout may only be enforced on one endpoint.

## Subagent Timeout on Sequential API Workflows
Subagents TIMEOUT on sequential API workflows (create account → get token → test endpoints) because they require shared state across steps. **Use `execute_code` from main thread** for API testing that needs token lifecycle management. The 300s timeout is a hard limit.

## TARGET DRIFT — Multi-Program Session Amnesia
Re-read original user instruction at session start AND after context compaction. Verify target name/domain.

## Computer Use — ALWAYS Available
`computer_use` tool IS configured. Don't check if installed — use it directly.

## Mega-Skill Merge — Stale Content Pitfalls
When absorbing skills into this unified SKILL.md:
1. **Update the absorbed list in the header** — every skill name must appear in the `> ⚠️ NO NEED TO LOAD OTHER SKILL.` line, or agents will try to load deleted skills
2. **Update REFERENCE FILES count** in the section header — the actual count, not a guess
3. **Remove phantom file pointers** from "Absorbed from Other Skills" — if the source skill directories are deleted, replace `skillname--*.md` pointers with a prose description of what was absorbed and what inline section covers it
4. **Bump version** on every major merge (e.g. 2.0.0 → 2.1.0 for adding skills, 2.1.0 → 3.0.0 for major restructure)
5. **Verify with `skill_view()`** after patching — load the skill and confirm all linked_files resolve and the absorbed list is accurate