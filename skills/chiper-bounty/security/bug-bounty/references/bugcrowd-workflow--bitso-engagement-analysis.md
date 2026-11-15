# Bitso Engagement Analysis — Pattern Template

## Engagement Page Analysis Workflow (Reusable per Bugcrowd Program)

### Step 1: Extract Program Metadata
From the Bugcrowd engagement page (use `browser_navigate` — `web_extract` often 504s):
```
- Program type (Managed/Public/Private)
- Safe harbor status
- Testing period (Ongoing/Limited)
- Scope rating (1-4)
- Average payout & validation time
- Number of vulnerabilities rewarded
```

### Step 2: Extract Scope — In-Scope & Out-of-Scope
```
In-Scope:
- Target names, URLs, tags (tech stack)
- Known issues (if listed)
- Reward chart (P1-P4 ranges)

Out-of-Scope:
- Explicit exclusions (domains, vulnerability types)
- Focus areas (what they WANT you to find)
- Access/Traffic identification requirements (headers, email format)
- Cross-domain duplicate policy
- N-Day policy (usually 14 days)
```

### Step 3: Extract Focus Areas
Programs often list specific vulnerability classes they're most interested in. These are HIGH-VALUE targets because:
1. They're pre-authorized (no scope debates)
2. They get prioritized in triage
3. They often have bonus rewards

**Crypto/Fintech focus areas (common pattern):**
- Access control / IDOR / BOLA
- Privilege escalation (vertical & horizontal)
- Authentication weaknesses (2FA bypass, session handling, ATO)
- Business logic flaws in financial flows (balance manipulation, trade exploits)
- Race conditions (transactions, transfers, balance updates)
- KYC/onboarding bypass
- API vulnerabilities (broken auth, excessive data exposure, rate limits)

### Step 4: Extract Recent Activity (CrowdStream)
Check the CrowdStream tab for:
- Recently accepted submissions → indicates what's being rewarded
- Priority levels being accepted → shows where the bar is
- Which targets are getting hits → indicates attack surface density
- Researcher names → top hunters to study their approaches

### Step 5: Check Hall of Fame
- Top researchers and their points
- Indicates how many valid findings exist
- Higher point totals = more active program

### Step 6: Check Announcements
- Bonus reward periods
- Scope changes
- Policy updates

---

## CSP Header Analysis — Hidden Attack Surface Discovery

**When:** During initial recon of any target with a Content-Security-Policy header.

**How:** `curl -sI -H "X-Bug-Bounty: Bugcrowd-BC_USERNAME" "https://target.com" | grep -i "content-security-policy"`

**What to extract from CSP:**
```
connect-src → Internal API endpoints, third-party services
script-src  → CDN domains, analytics services
img-src     → Asset hosting, tracking pixels
frame-src   → Embedded services, widgets
font-src    → Font hosting
style-src   → Style hosting
media-src   → Media hosting
```

**High-value CSP findings:**
1. **Internal hostnames** — `*.internal.company.com`, `cgw.company.com`
2. **Dev/staging URLs** — `dev-*.company.com`, `stage-*.company.com`
3. **Third-party services** — Amplitude, Segment, Sentry, HubSpot (each is a potential data leak vector)
4. **Cloud services** — GCP Cloud Run (`*.uc.a.run.app`), AWS Lambda
5. **Analytics endpoints** — Often accept arbitrary data (potential SSRF/data injection)

**Example from Bitso:**
```
connect-src reveals:
- cgw.bitso.com → Gateway service
- amplitude.bitso.com → Analytics (potential data injection)
- segment.bitso.com → CDP (potential PII leak)
- uptok-server-production-cyxmaabxjq-uc.a.run.app → GCP Cloud Run
- dev-amplitude.bitso.com → Dev analytics (info leak?)
- dev-segment.bitso.com → Dev CDP (info leak?)
- assets-dev.bitso.com → Dev assets (source code?)
```

**Attack angles from CSP intel:**
- SSRF to internal services via user-controlled parameters
- Analytics endpoint manipulation (inject fake events/data)
- Dev/staging endpoint access (often weaker auth)
- Cloud service enumeration

---

## Cross-Domain Duplicate Policy

Some Bugcrowd programs group multiple domains as a single logical entity.

**Pattern:** "bitso.com, nvio.mx, and nvio.ar are considered a single logical entity"

**Implications:**
- Vulnerabilities on these domains from the same root cause = SINGLE finding
- First report wins (on ANY of the domains)
- Subsequent reports on sibling domains = Duplicate
- Researchers should NOTE if vulnerability affects multiple domains in ONE report

**Before submitting:**
1. Check if target has cross-domain duplicate policy
2. If yes, consolidate ALL evidence of same root cause into ONE report
3. List all affected domains in the report
4. Don't submit separate reports per domain

---

## Crypto/Fintech Bug Bounty — Attack Surface Map

### Financial Flow Attack Vectors
```
Deposit → Withdraw → Trade → Convert → Earn
   ↓          ↓         ↓        ↓        ↓
  IDOR    Race cond   Logic   Rate     Balance
  BOLA    Double-     flaw   manip    manip
          spend
```

### Race Condition Targets (Crypto-Specific)
- Simultaneous withdrawal requests (same balance)
- Concurrent trade execution on same pair
- Balance update during internal transfer
- KYC status change during transaction
- 2FA bypass via parallel code submission
- Flash crash exploitation via API

### Business Logic Targets (Crypto-Specific)
- Order manipulation (price/quantity after submission)
- Negative amount/price injection
- Decimal precision / rounding errors
- Currency mismatch (deposit USD, withdraw BTC at manipulated rate)
- Early withdrawal calculation bypass
- Conversion rate TOCTOU

### Mobile App + Web App Pattern
- Mobile apps (iOS/Android) often have SEPARATE API endpoints
- Mobile traffic may bypass WAF rules present on web
- API versioning differences between web and mobile
- Mobile app may expose endpoints not reachable from web

---

## Program Analysis Template

```markdown
# [Program Name] — Engagement Analysis

## Program Info
- Type: [Managed/Public/Private]
- Safe Harbor: [Yes/No]
- Status: [Ongoing/Limited]
- Avg Payout: $X,XXX
- Response Time: X days
- Findings Rewarded: XX

## In-Scope Targets
| Target | URL | Stack | Tags |
|--------|-----|-------|------|
| ... | ... | ... | ... |

## Reward Chart
| Priority | Range |
|----------|-------|
| P1 | $X,XXX – $X,XXX |
| P2 | $X,XXX – $X,XXX |
| P3 | $XXX – $X,XXX |
| P4 | $XX – $XXX |

## Focus Areas (What They Want)
1. ...
2. ...

## Out-of-Scope
- ...
- ...

## Cross-Domain Policy
[Single entity / Separate entities]

## CSP/Recon Findings
[Internal services, dev URLs, analytics endpoints]

## CrowdStream Analysis
- Recent accepted: [priority levels, targets]
- Top hunters: [researcher names]

## Attack Plan
[Tier 1-4 priority vectors]
```
