# Scope Validation Gate — Pre-Submission Checklist

Mandatory step BEFORE writing any report. Prevents wasted time on out-of-scope or by-design findings.

## Why This Exists

User corrected: "Cek dulu syarat dan vrtnya, ap boleh submit ini d bugcrowd" — the agent was about to generate a report without verifying the finding was in-scope for the program. This gate prevents that.

## Step 1: Extract Program Details

### Bugcrowd Program Pages
- `web_extract` often fails (504/timeout) — use `browser_navigate` instead
- Pages require search navigation: go to bugcrowd.com → search program name → click result
- Program content requires JavaScript rendering — use `browser_console(expression=...)` for extraction

### Aggregator Scope Extraction (FALLBACK — often more reliable)
Bugcrowd pages are React SPAs — scope data is NOT in static HTML. `curl` returns empty `<div id="root">`.

**Pattern (ordered by reliability):**
1. **bountyindex.in** (PRIMARY) — Server-rendered, has extracted scope data
   ```
   web_search("bountyindex.in PROGRAM_NAME") → find cached page
   web_extract([url]) → returns HTML with scope data
   ```
   - Search output for: `target_path`, `asset_identifier`, domain patterns
   - If no JSON, grep raw HTML: `grep -oP 'https?://[a-z0-9.-]+fireblocks[a-z0-9./-]*'`
   
2. **Alternative aggregators** (if bountyindex fails):
   - `strike.fyi` — Usually empty/loading (SPA, same problem as Bugcrowd)
   - `bountyhunte.rs` — May have limited data
   - `bbradar.io` — None found

3. **Direct Bugcrowd extraction** (last resort):
   ```bash
   curl -sL "https://bugcrowd.com/engagements/PROGRAM_ID" > page.html
   grep -oP '"target_url":"[^"]+' page.html  # Usually empty for React SPAs
   ```

**Verification:** After extraction, confirm exact URLs match what you're testing. Scope mismatch = wasted findings.

```python
# Extract program page via JS (reliable):
page_text = browser_console(expression="""
    document.querySelector('main')?.innerText?.substring(0, 8000) || 
    document.body.innerText.substring(0, 8000)
""")
```

### Key Data to Extract
| Field | What to Look For |
|-------|-----------------|
| **Targets** | Exact domains, IPs, assets in scope |
| **Focus Areas** | What the program explicitly wants found (hints for framing) |
| **Rewards** | P1-P4 cash ranges, any active increases |
| **Known Issues** | Bugs already reported — DO NOT submit duplicates |
| **Exclusions** | Assets or bug classes explicitly out-of-scope |
| **Safe Harbor** | Legal protection status |
| **Submission Rules** | Required headers, email, format |

## Step 2: Map Finding to Scope

### Checklist per Finding
```
□ Finding targets an asset in the in-scope list?
□ Finding matches at least one focus area?
□ Finding is NOT in the known issues list?
□ Finding is NOT an explicitly excluded bug class?
□ Finding reproduces consistently (not a one-off)?
```

### Common Mapping Patterns
| Finding Type | Best Focus Area Match | Report Framing |
|-------------|----------------------|----------------|
| JWT/auth bypass | "Access", "Authentication" | Broken Authentication → [specific vector] |
| IDOR/BOLA | "Access", "Data" | Insecure Direct Object Reference → [data exposed] |
| XSS with auth theft | "Access", "API" | Stored XSS → Session Hijacking → Account Takeover |
| API data leak | "Insecure API endpoints" | Unauthenticated API → [data class] Exposure |
| Race condition | "Transaction manipulation" | Race Condition → [double-spend/double-action] |
| CORS misconfiguration | "API", "Configuration" | Unsafe CORS → [specific exploit chain] |

### Anti-Patterns (DO NOT frame like this)
- ❌ "I found XSS" → What's the impact? Steal token? Account takeover? Fund theft?
- ❌ "CORS reflects origin" → So what? Can attacker steal real session?
- ❌ "Missing security headers" → Alone this is informational. Chain it.
- ❌ Leading with delivery mechanism instead of root cause

## Step 3: Reward Tier Assessment

### Match Impact to Program's Reward Chart
| Finding | Typical Tier | Justification |
|---------|-------------|---------------|
| Unauthenticated account takeover | P1-P2 | Direct impact on user accounts |
| JWT minting without auth | P1-P2 | Attacker controls victim's account |
| Stored XSS → token theft | P2 | Chains to account takeover |
| Unauthenticated API data access | P2-P3 | Data exposure, scope-dependent |
| CORS misconfiguration (alone) | P3-P4 | Needs chain to demonstrate impact |
| Missing headers (alone) | P4-P5 | Informational without exploit |

### Consider Program-Specific Adjustments
- Some programs have active reward increases (e.g., +$1000 for P1-P2)
- Some programs cap rewards regardless of severity
- Some programs only pay for P1-P2, everything else gets kudos only

## Step 4: Report Framing

### Rule: Lead with ROOT CAUSE, not delivery mechanism
```
BAD:  "Stored XSS in profile page"
GOOD: "Broken Authentication — Unauthenticated JWT Minting via Public API"
      (XSS is just one way to exploit it; the real bug is the API accepts it)

BAD:  "CORS misconfiguration on API"
GOOD: "Insecure API Endpoint — Unauthenticated Account Creation with 
       Full Profile Data Access"
      (CORS is just one attack vector; the real bug is no auth on the API)

BAD:  "IDOR on user endpoint"
GOOD: "Broken Access Control — BOLA on User Profile API Exposing 
       Personal Data + JWT Tokens"
      (IDOR is the mechanism; the finding is access control failure)
```

### Frame to Program's Language
- If program says "transaction manipulation" → frame as "business logic flaw leading to fund theft"
- If program says "insecure auth" → frame as "broken authentication allowing [specific attack]"
- If program says "account takeover" → frame as "account takeover via [vector]"

## Step 4.5: By-Design Analysis (MANDATORY for Info Disclosure)

Before finalizing any info disclosure finding, run this analysis:

### The Question
*"Data disclosed AWS dll sptnya mmg disengaja?"* — Is the disclosed data intentionally exposed?

### Decision Framework

**Sandbox Environment Context:**
- Health endpoints in sandbox/staging often intentionally expose infra details for debugging
- Developers need to verify queue connectivity, memory usage, cloud config
- AWS Account IDs in sandbox ≠ same severity as production (different resource policies)
- Industry norm: `/health` returns readiness + dependency status (CloudWatch, SQS, S3 connectivity)

**Production vs Sandbox Severity Matrix:**
| Finding | Sandbox | Production | Notes |
|---------|---------|------------|-------|
| AWS Account ID | P4 Low | P3 Medium | Sandbox accounts rarely hold real funds |
| S3 Bucket Name | P4 Low | P3-P2 | Sandbox buckets = test data, prod = user data |
| SQS/SNS ARNs | P4 Low | P3 Medium | Sandbox queues = dev traffic |
| Memory/Heap Thresholds | P5 Info | P4 Low | Operational info, not exploitable alone |
| Tech Stack Fingerprint | P5 Info | P5 Info | Standard info disclosure |
| Database Credentials | P2-P1 | P1-P2 | Always critical regardless of env |

**Sibling Comparison (CRITICAL technique):**
Compare the same endpoint across sibling services to determine if it's standard:
```
sb-mobile-api.fireblocks.io/health → 200 + full AWS disclosure
sb-console-api.fireblocks.io/health → 403 (blocked)
sandbox-api.fireblocks.io/health → 404 (no endpoint)
mobile-api.fireblocks.io/health → 404 (no endpoint)
api.fireblocks.io/health → 404 (no endpoint)
```
- If only ONE endpoint exposes data while siblings block it → likely misconfiguration
- If ALL endpoints expose it → likely by-design
- If sandbox exposes but production blocks → likely intentional sandbox configuration

**When a finding IS likely by-design:**
1. Sandbox health endpoint with infra metadata (debugging purpose)
2. Readiness probe returning dependency connectivity (standard K8s pattern)
3. Public documentation mentions the architecture (no secret)
4. Same data available via other means (AWS account ID from DNS TXT records)

**When a finding is NOT by-design (even in sandbox):**
1. Non-health endpoint exposing same data (misconfiguration)
2. Credentials/tokens in response (never intentional)
3. PII or user data leaked (sandbox shouldn't have real user data)
4. Production-equivalent data in sandbox (shared infra = real risk)
5. Inconsistency across similar endpoints (one leaks, others don't)

## Step 5: Decision Gate

| Verdict | When | Action |
|---------|------|--------|
| **SUBMIT** | In-scope, reproducible, real impact, by-design analysis PASSED | Write report, generate PDF, submit |
| **DOWNGRADE** | In-scope but informational only / by-design likely | Convert to context for other findings |
| **SKIP** | Out-of-scope, known issue, clearly by-design | Document but do not submit |
| **CHAIN** | Finding alone is low impact | Combine with other findings for higher impact |
| **PENDING_REVIEW** | In-scope, reproducible, but by-design analysis ambiguous | Present to user with arguments for/against — NEVER auto-submit |

## Case Study: Aurory Scope Validation (2026-08)

**Finding:** Unauthenticated JWT minting via `POST /v1/tokens` public API

**Scope extraction:**
- Program: "Aurory MBB" on Bugcrowd
- In-scope: `*.aurory.io`, `aurory.io`, `amikoarena.com`, `amikolegends.com`
- Focus areas: "Transaction manipulation, access, insecure API endpoints"
- Rewards (with increase): P1 $3,500-$4,500, P2 $1,500-$2,500, P3 $400-$650

**Mapping:**
- ✅ JWT minting is an "insecure API endpoint" (focus area match)
- ✅ Leads to account takeover (matches "access" focus area)
- ✅ Can be used to purchase items in victim's account (matches "transaction manipulation")
- ✅ NOT in known issues or exclusions

**Framing:** "Broken Authentication — Unauthenticated JWT Minting via Public API"
- NOT "XSS on game domain" (that's just one delivery mechanism)
- The real finding is the API accepts `POST /v1/tokens` without verifying caller identity

**Decision:** SUBMIT as P2 ($1,500-$2,500 range, potentially P1 if fund theft proven)

## Case Study: Fireblocks Scope Validation (2026-09)

**Finding:** Health endpoint AWS infrastructure disclosure on `sb-mobile-api.fireblocks.io`

**Scope extraction (via bountyindex.in aggregator):**
- Program: "fireblocks-mbb-og" on Bugcrowd
- In-scope: 3 sandbox API targets (`sb-console-api`, `sb-mobile-api`, `sandbox-api`)
- Smart contracts: OUT OF SCOPE (confusion with HackerOne program)
- Bugcrowd React SPA blocks direct extraction — needed aggregator fallback

**Mapping:**
- ✅ `sb-mobile-api.fireblocks.io` is in the target list
- ✅ `/health` endpoint is a real endpoint returning real data
- ⚠️ By-design analysis: ambiguous (sandbox, standard health endpoint pattern)
- ⚠️ Severity: P4 Low (sandbox context reduces impact)

**Key lesson:** NEVER declare "READY TO SUBMIT" without presenting by-design analysis to user. The user's challenge ("Data disclosed AWS dll sptnya mmg disengaja?") revealed a gap in the workflow.

**Decision:** PENDING_REVIEW — present to user with arguments for/against by-design

## Parked/For-Sale Domain Detection (Stage 1 Gate)

When a target domain redirects to a domain marketplace, the domain is NOT owned by the bounty program. This is a hard scope gate — stop immediately.

### Indicators
- **HugeDomains** — redirect to `hugedomains.com/domain/pvpbattle.com`
- **Sedo** — redirect to `sedo.com/` with domain sale listing
- **GoDaddy Auctions** — redirect to `auctions.godaddy.com/`
- **Afternic** — redirect to `afternic.com/` with domain price
- **Dan.com** — redirect with "This domain is for sale" page

### How to detect
```bash
# Check redirect chain
curl -sI -L "https://TARGET.com" | grep -i "location:"
# If Location header points to a marketplace domain → PARKED

# Also check HTTP response body for marketplace keywords
curl -sL "https://TARGET.com" | grep -iE "(hugeDomains|sedo|afternic|dan\.com|for sale|buy this domain|domain expired)"
```

### Pre-check shortcut (before full recon)
```bash
# Quick domain status check
whois TARGET.com | grep -iE "(registrar|status|expir)"
# If registrar says "Domain For Sale" or status is "redemptionPeriod" → PARKED

# DNS check
dig TARGET.com A +short
# If A record is a CNAME to a marketplace CDN → PARKED
```

### Decision
| Verdict | Action |
|---------|--------|
| Domain redirects to marketplace | **ABORT** — no live app to test |
| Domain expired/redemption period | **ABORT** — not controlled by program |
| Domain points to parking page (ads) | **ABORT** — not a real application |
| Domain has live app but marketplace info exists | Proceed with caution — may be new acquisition |

### Case Study: pvpbattle (2026-09)
- **Announcement:** @PVPBATTLE on X posted bounty program (Sep 4, 2026)
- **Domain:** pvpbattle.com → redirects to HugeDomains (for sale, $4,150)
- **Result:** Domain is parked/for sale. No live application exists.
- **Lesson:** X announcements from crypto projects often reference domains that aren't deployed yet. Always verify the domain is live and owned by the project before starting recon.

## Code-Level Findings in API-Focused MBB Programs (PITFALL)

**Session 2026-09 (Fireblocks):** MBB program page lists only API endpoints as targets, but agent found smart contract vulnerabilities in open-source repos. Key question: **Are code-level findings in scope for API-focused MBB?**

### The Scope Ambiguity Pattern

```
Program page shows:
- Target: api.sandbox.example.com (API)
- Target: sandbox.example.com (Web App)

Agent finds:
- Smart contract code on GitHub (open source)
- Vulnerability in contract code (missing access control)
- Is this in scope?
```

### Resolution Checklist

```
1. Check program page for EXPLICIT scope language:
   - "All assets" / "All domains" = code-level included
   - "Only listed targets" = API-only
   - "Including source code" = code explicitly included
   - Ambiguous = assume NOT in scope (safe harbor)

2. Check if contract is DEPLOYED on target chains:
   - GitHub repo only = code exists but not necessarily target
   - Verified contract on Etherscan = potentially in scope
   - Used by target application = strongest argument for inclusion

3. Check program FOCUS AREAS for matching:
   - "Smart contract security" = code-level included
   - "API security" = code-level excluded (implied)
   - "Blockchain" = code-level included
   - "Infrastructure" = code-level ambiguous

4. Ask triager if ambiguous:
   - Use Bugcrowd support channel
   - Frame: "I found a vulnerability in contract code on your GitHub. Is this in scope?"
   - Wait for confirmation before submitting
```

### Severity Implications

When code-level findings ARE in scope for MBB:
- Smart contract vulnerabilities often map to P1-P2 (high bounty)
- Code-level findings have clearer root cause than API-only findings
- PoC is often more complex (requires fork testing, state manipulation)
- May need Foundry/Hardhat setup for proper reproduction

When code-level findings are NOT in scope:
- Document but do NOT submit
- May be in scope for separate Smart Contract audit program
- Check if company has Immunefi or Code4rena for contract-specific findings
- Inform user: "This finding is valid but may not be in this program's scope"
