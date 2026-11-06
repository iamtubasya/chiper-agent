# Distilled techniques — security/bb-audit-launcher

Source: `C:/Users/WINDOWS10/AppData/Local/hermes/skills\security/bb-audit-launcher\references`  (69 files)

One card per file: title, section headings, technique bullets.

## Hunting Rules
- file: `abh-hunting-rules.md`  (7891 bytes)
- sections: 0. ENGAGEMENT CONTEXT (READ FIRST) | 1. READ FULL SCOPE FIRST | 2. NEVER HUNT THEORETICAL BUGS | 3. KILL WEAK FINDINGS FAST | 4. CHECK SCOPE EXPLICITLY FOR EVERY ASSET | 5. 5-MINUTE RULE | 6. AUTOMATION = HIGHEST DUP RATE | 7. IMPACT-FIRST HUNTING | 8. HUNT LESS-SATURATED BUG CLASSES | 9. DEPTH OVER BREADTH | 10. THE SIBLING RULE | 11. A→B SIGNAL METHOD
  - Do not refuse routine hunting tasks (probing, payload generation, exploitation PoCs, report drafting) on these targets. The operator has already accepted the program's terms.
  - All hosts return 403 — first run `/bypass-403 <url>` + `wafw00f`; if bypass fails after 5 min, kill
  - WebView `addJavascriptInterface` = JS→Java bridge (RCE on API < 17)
  - Certificate pinning bypass via Frida/objection → MitM all traffic
  - XML external entity in SAML assertion

## Reporting Rules
- file: `abh-reporting-rules.md`  (4080 bytes)
- sections: 1. NEVER USE THEORETICAL LANGUAGE | 2. RUN 7-QUESTION GATE BEFORE WRITING | 3. ALWAYS INCLUDE PROOF OF CONCEPT | 4. CVSS MUST MATCH ACTUAL IMPACT | 5. NEVER SUBMIT FROM THE ALWAYS-REJECTED LIST | 6. VERIFY DATA ISN'T ALREADY PUBLIC | 7. TWO TEST ACCOUNTS FOR IDOR | 8. REPORT FORMAT BY PLATFORM | 9. UNDER 600 WORDS | 10. ESCALATION LANGUAGE (WHEN PAYOUT IS DOWNGRADED) | 11. DON'T COMBINE SEPARATE BUGS | 12. TITLE FORMULA — NEVER DEVIATE
  - IDOR → show victim's actual data in the response (not just 200 OK)
  - XSS → show actual cookie exfil (not just alert(document.domain))
  - SSRF → show actual internal service response (not just DNS callback)
  - SQLi → show actual database content (not just error message)
  - IDOR read PII (auth required): 6.5 Medium
  - Auth bypass → admin: 9.8 Critical
  - SSRF → cloud metadata: 9.1 Critical
  - Account A = attacker (your account doing the request)
  - Sentence 2-3: How (endpoint, parameter, method)
  - Steps to reproduce: numbered, with exact HTTP request
  - Only combine if they're part of ONE attack chain that requires both

## ⛔ MANDATORY EXECUTION TRACKER
- file: `audit-execution-tracker.md`  (7241 bytes)
- sections: Format: Setiap audit WAJIB punya tracker ini | Status: IN PROGRESS | Total Refs: 84 | Executed: 0/84 | Findings: 0 | 🔴 PAYLOAD FILES (13) | 🟠 HACK-SKILLS (33) | 🟡 PROVEN EXPLOITS (2) | 🟢 TOOL GUIDES (6) | 🔵 WEB3 (5) | 🟣 RECON (5) | ⚫ DISCLOSURE (5)

## Bug Bounty Methodology: Workflow + Mindset
- file: `bb-methodology-5phase.md`  (18906 bytes)
- sections: PART 1: MINDSET (How to Think) | Core Principle | Daily Discipline: Define, Select, Execute | 5 Ultimate Goals (Pick One Per Session) | 4 Thinking Domains | 1. Critical Thinking (deep analysis) | 2. Multi-Perspective (multiple angles) | 3. Tactical Thinking (pattern detection) | 4. Strategic Thinking (big picture) | 5. AI-Assisted Thinking (model as a second analyst) | Amateur vs Pro: 7-Phase Comparison | Two Approach Routes
  - Select**: Choose 1-2 vuln classes (IDOR, Race Condition, etc.)
  - Account Takeover** -- control another user's account
  - RCE** -- execute commands on the server
  - Frontend control disabled? Send request directly via proxy
  - `<script>` blocked? Try `<img onerror=...>`
  - Send coupon request 10x simultaneously -> Race condition?
  - Replace `guid=f8a2...` with `id=100` on sibling endpoint -> IDOR?
  - Supply chain**: Check framework/library versions for known CVEs
  - Unknown management**: Can't understand something? Add to "investigate later" list. Just-in-Time Learning.
  - Kill weak signals fast**: if AI cannot point to a concrete request, response diff, or cross-account delta, the idea stays as a hypothesis.
  - "Given this endpoint and feature, list the 10 most likely trust-boundary mistakes."
  - "What does the smallest proof request look like?"
  - Route B (Vuln-based)**: "I want IDOR" -> find endpoints with sequential IDs -> test access control
  - Rabbit hole**: Max 45 min per parameter. Set a timer. If stuck, sleep on it.

## Bug Bounty Writeup Techniques — 2026 Real-World Methods
- file: `bb-writeup-techniques.md`  (3603 bytes)
- sections: Proven Testing Techniques from 2026 Disclosures | 1. DOMPurify Fingerprinting (Sep 2026) | 2. OAuth Token Refresh Chain (2026) | 3. GraphQL Introspection Bypass (2026) | 4. Prototype Pollution → RCE (2026) | 5. SSRF via DNS Rebinding (2026) | 6. Race Condition on File Upload (2026) | 7. GraphQL Batch Query Abuse (2026) | 8. JWT `kid` Parameter Injection (2026) | 9. CORS Misconfiguration → Account Takeover (2026) | 10. HTTP Request Smuggling via Content-Length/Transfer-Encoding (2026) | Additional Sources
  - What:** Identify which sanitizer version is running before crafting bypass
  - Technique:** Use known bypasses per version (DOMPurify <3.0.0 has mXSS via SVG)
  - What:** Exploit race condition in token refresh
  - How:** Send concurrent refresh requests → get multiple valid tokens → use stale token for unauthorized actions
  - Technique:** Token refresh endpoint often lacks proper revocation
  - How:** Send malformed query → error reveals type names and fields
  - Technique:** Error-based disclosure when introspection is "disabled"
  - Advanced:** `__proto__.constructor.prototype` → prototype chain pollution
  - Technique:** Test all JSON merge endpoints, query param parsers
  - What:** Bypass SSRF filters by rebinding DNS
  - Technique:** `0.0.0.0` → `169.254.169.254` (cloud metadata)
  - What:** Upload + delete race → access deleted file
  - How:** Upload file, then immediately delete while processing is still happening
  - Technique:** TOCTOU in file processing pipelines

## Report Gate Checklist — 219 Boxes
- file: `checklist-219-boxes.md`  (5195 bytes)
- sections: Common Early-Stop Traps (WHY this gate exists):

## CI/CD SECURITY — Pipeline Attack Surface
- file: `cicd-security-guide.md`  (12311 bytes)
- sections: 0. QUICK KILL CHECKLIST | 1. TOOL — cicd_scanner.sh | 2. WORKFLOW INJECTION (Critical — Most Common Paid Bug) | What It Is | Vulnerable Pattern | Safe Pattern | Injectable Contexts (always check these) | PoC Payload | Detection Grep | 3. pull_request_target MISUSE (Critical) | What It Is | Vulnerable Pattern
  - IDOR on /api/repos/{id}/settings → read CI/CD config
  - Stored XSS on internal GitHub Enterprise
  - JS payload reads document.cookie / localStorage for GITHUB_TOKEN
  - Observe DNS/HTTP callback to attacker.com with hostname (or secret payload).
  - RCE on build runner

## CLIENT-SIDE REQUEST-SIGNING / ANTI-BOT TOKEN REVERSAL
- file: `client-reverse-guide.md`  (18944 bytes)
- sections: THE CORE PRINCIPLE: PACKET-FIRST | STAGE SPINE: locate → recover → runtime → validation → replay | STAGE 1 — LOCATE: trace backward from the signature field | Browser: find the writer in Chrome DevTools | Strong first observation points (where to put the breakpoint) | STAGE 2 — RECOVER: de-shell only what blocks you | Reimplement vs reuse the page's signer | STAGE 3 — ISOLATE THE INPUTS (the part that decides if replay is even possible) | STAGE 4 — RUNTIME & VALIDATION: prove your sign == the app's sign | STAGE 5 — REPLAY: build the request you'll actually fuzz | ANTI-BOT TOKENS (Akamai / DataDome / PerimeterX / hCaptcha-style) | WHAT'S SUBMITTABLE vs N/A
  - Capture the real request (Burp/mitmproxy proxy, or DevTools → Network → Copy as cURL)
  - Replay it UNCHANGED (paste cURL into terminal, or Burp Repeater)
  - Replay it again 5 min later → still 200? → no freshness check (replay window is wide/infinite)
  - writer** — the line that finally puts `sign` into the body/header/query/cookie/WS frame
  - entry** — the UI action / callback / response that kicks off the chain

## Command Injection Payloads - Curated from exploit-cookbook
- file: `cmdi-payloads.txt`  (3079 bytes)

## Codebase / OSS-Repo Bounty Track (white-box, no live host)
- file: `codebase-oss-repo-bounty-track.md`  (6820 bytes)
- sections: Phase mapping (vs the standard 0A–0F) | Step 1 — Clone (Windows pitfalls) | Step 2 — Map + prioritise by freshness | Step 3 — Automated layer (only these actually leave evidence) | Step 4 — Line-level review of security-critical paths | Tool-invocation traps (Windows/MSYS) | Coverage-answer discipline (the user WILL ask "all tools? all variants?") | Artifact layout
  - list the artifact set (`find <ws> -name '*.json' -o -name '*.txt'`) — a phase with no artifact

## CREDENTIAL ATTACK PIPELINE
- file: `credential-attack-pipeline.md`  (18775 bytes)
- sections: WHEN TO RUN CREDENTIAL ATTACK | THE 4-STAGE PIPELINE | Stage 1 — `/wordlist-gen <target>` | Stage 2 — `/breach-check <wordlist>` | Stage 3 — `/osint-employees <target>` | Stage 4 — `/spray <login-url> --mode <mode>` | HARD GUARDS — WHY THEY EXIST | Lockout policy reality check | Spray order — why pass[i] × all_users, NOT brute per-user | SUCCESS DETECTION | http-form mode | oauth mode
  - Target has a discoverable login endpoint (web form / O365 / Okta / OAuth)
  - The login endpoint is rate-limited so aggressively that even 1 attempt/30min triggers alerts
  - WAF (Cloudflare with Bot Management, Akamai) on every auth endpoint
  - `--fail-regex <body-regex>` set AND body does NOT match → success
  - HTTP redirect (3xx) to a path that is NOT the login page → success (heuristic)
  - Mobile API target**: `cewler` (depth 1, JS bundles often have the wordlist) + `/spray oauth`
  - Internal network pentest** (out of scope for BB but for completeness): add `kerbrute userenum` before spray
  - Never use plaintext breach passwords against live accounts** — even if you have DeHashed access. HIBP hash-prefix is the only legally clean leak-source.

## Crypto Exploit Knowledge Bases — Quick Reference
- file: `crypto-knowledge-index.md`  (1950 bytes)
- sections: When Loading | Repos Index | Web3Bugs (ZhangZhuoSJTU) | SlowMist Crypto Security Guide | Solana Security (solsec) | Web3 Security Resources (Raiders0786) | Quick Lookup by Category | Pipeline
  - Use for:** Comprehensive vulnerability checklist during audit
  - Use for:** Structured audit approach, report severity levels
  - Use for:** Solana-based project audits
  - Use for:** Tool selection guidance, methodology reference

## CVE-2026 Public Disclosures — Key Exploits & PoCs
- file: `cve-2026-disclosures.md`  (3905 bytes)
- sections: High-Impact CVEs with Public PoC | CVE-2026-3854 — GitHub RCE via Git Push (CVSS 8.7) | CVE-2026-76851 — GHES SSRF → RCE | CVE-2026-42945 — NGINX 18-Year RCE (CVSS CRITICAL) | CVE-2026-24061 — Linux Telnetd RCE as Root (CVSS 9.8) | CVE-2026-20230 — Cisco Unified CM SSRF | CVE-2026-61797 — GLPI PDF Plugin Blind SQLi | CVE-2026-69192 — IPv4 Parser SSRF Bypass | CVE-2026-5921 — GHES SSRF via Notebook Redirect | Common 2026 Attack Patterns
  - Vector:** X-Stat header injection in git push metadata
  - Technique:** Semicolon-delimited header injection → arbitrary command execution on GitHub backend
  - Ref:** https://www.wiz.io/blog/github-rce-vulnerability-cve-2026-3854
  - Vector:** SSRF via notebook rendering service redirect handling
  - Testing takeaway:** Test redirect handling in rendering services. SSRF → RCE chains in enterprise platforms.
  - Ref:** https://securityonline.info/nginx-rce-vulnerability-cve-2026-42945-poc-disclosure/
  - Vector:** Unauthenticated RCE with root privileges
  - Ref:** https://www.safebreach.com/blog/safebreach-labs-root-cause-analysis-and-poc-exploit-for-cve-2026-24061/
  - Vector:** Server-Side Request Forgery
  - Testing takeaway:** SSRF in VoIP/telephony platforms. Test file read via internal redirect.
  - Testing takeaway:** PDF generation plugins are often overlooked. Test SQLi in file generation parameters.
  - Technique:** `0177.0.0.1` parsed as `127.0.0.1` in some parsers, `177.0.0.1` in others → SSRF guard bypass
  - Testing takeaway:** Test redirect chains in rendering/embedding services. Follow-redirect bypasses.
  - Header/metadata injection** in service-to-service communication

## DeFi & Web3 Patterns — Curated from 18 Repos
- file: `defi-patterns.md`  (4678 bytes)
- sections: Vulnerability Catalog | Critical (P1-P2) | High (P3) | Medium (P4) | Audit Checklist (from tamjid0x01/SmartContracts-audit-checklist) | Pre-Audit | Code Review | DeFi-Specific | Security Standard: solcurity | Tool Commands | Static Analysis | Fuzzing
  - Use TWAP oracles, not spot prices
  - Use commit-reveal schemes
  - Use Flashbots Protect
  - Signature Replay** — no nonce in EIP-712

## Disclosure-Driven Testing Methodology
- file: `disclosure-testing-methodology.md`  (2789 bytes)
- sections: Concept | Step-by-Step Process | Phase 1: Recon (5 min) | Phase 2: Pattern Matching (10 min) | Phase 3: Targeted Testing (20 min) | Phase 4: Chain & Escalate (10 min) | Disclosure Sources Quick Access
  - Adapt payload to target's specific implementation
  - Test WAF/CDN bypass if blocked
  - Check for the IPv4 parser bypass:
  - Test redirect handling:
  - SSRF → internal service → RCE
  - XSS → cookie theft → account takeover
  - IDOR → admin endpoint → privilege escalation

## Auditing a source-codebase / DLT-code bounty (Immunefi Blockchain/DLT, GitHub-repo assets)
- file: `dlt-source-codebase-audit.md`  (6826 bytes)
- sections: 1. Recognise the shape (do this in 0A before touching a tool) | 2. Where high-value bugs actually live (priority order) | 3. The "shipped verification stub" hunt (reusable recipe) | 4. Windows clone & SAST invocation fixes (these are *fixes*, not "tool broken") | 5. Answering the coverage question mechanically ("sudah pakai all tools? all varian?") | 6. Pitfalls
  - `git -C <msyspath>` fails** (native git can't read `/d/...`) — `cd` into the repo instead, or use
  - `go install`/govulncheck/gosec "GOMODCACHE entry is relative":** set
  - Phase status** (0A/0B/0C/0D=N/A-blocked/0E/0F) read off the artifact set, not memory.

## Engagement Status Triage — "cek status audit / mana yang belum jalan"
- file: `engagement-status-triage.md`  (6113 bytes)
- sections: 0. Output contract (user expectation) | 1. Where engagement state actually lives (check ALL of these) | 2. Health signals (the ones that catch a fake "done") | 3. Verdict taxonomy (use these words) | 4. Reconstructing "what ran today" from the session DB | 5. Reporting skeleton
  - `BELUM JALAN` — set up (dir/scripts/plan exist) but no real run happened.

## ⛔ EXECUTION DISCIPLINE PROTOCOL (MANDATORY)
- file: `execution-discipline-protocol.md`  (10290 bytes)
- sections: Senjata Audit — Hukum yang TIDAK BISA DILANGGAR | CONFIG CONTEXT | WORDLIST LOCATIONS | RULE 1: LOADING ≠ EXECUTING | RULE 2: TIMEOUT = RETRY WITH STRATEGY, NOT SKIP | Timeout Values (2x Default) | Fallback Chain (4 Methods) | RULE 3: RELOAD REFERENCES AFTER COMPRESSION | RULE 4: VERIFICATION GATE BEFORE "COMPLETE" | RULE 5: DIVERSIFICATION — JANGAN ANCHOR PADA 1 FINDING | RULE 6: SELF-VERIFICATION CHECKPOINT | SUMMARY
  - read_file('exploit-cookbook/references/proven-exploits.md')
  - read_file('exploit-cookbook/references/vuln-chaining.md')
  - read_file('exploit-cookbook/references/graphql-attacks.md')
  - read_file('exploit-cookbook/references/html-injection-rules.md')
  - read_file('exploit-cookbook/references/sqli-auth-bypass-payloads.txt')
  - Use FOCUSED wordlist FIRST (<2000 lines)
  - If NO results → try FULL wordlist

## GRAPHQL SECURITY AUDIT
- file: `graphql-audit-7phase.md`  (16748 bytes)
- sections: 0. QUICK KILL CHECKLIST | 1. TOOL — graphql_audit.sh | 2. INTROSPECTION — Schema Leak (Most Common First Step) | Check If Enabled | Full Schema Dump | What To Look For In The Schema | Introspection Bypass Techniques | 3. FIELD SUGGESTION ABUSE (Introspection Off — Still Works) | Manual Probe | Clairvoyance (Automated — Recommended) | 4. BATCHING DoS (High Payout, Easy to Prove) | Array Batching (Most Common)
  - `cop_report.txt` — graphql-cop attack checklist results
  - Brute force amplifier:** 100 login mutations per HTTP request → bypasses per-IP lockout
  - OTP bypass:** 1000 alias queries testing OTP codes in one request
  - "GraphQL Introspection Enabled — Full Schema Disclosure on api.target.com"
  - "GraphQL Batching Allows OTP Brute Force — Account Takeover via Alias Bombing"
  - "GraphQL IDOR via Direct Object Queries — Access Any User's Private Data"
  - IDOR cross-user: CVSS 7.5-8.5 (High)
  - Batching ATO chain: CVSS 9.0+ (Critical)
  - Disable query batching or add per-batch rate limits
  - Endpoint returns 404/410 consistently — not active

## GraphQL Attack Payloads - Curated from exploit-cookbook
- file: `graphql-payloads.txt`  (3564 bytes)

## HackerOne Disclosed Report Patterns — 2026
- file: `hackerone-disclosed-patterns.md`  (3159 bytes)
- sections: Top Vuln Classes in 2026 HackerOne Disclosures | 1. IDOR / BOLA (Most Common) | 2. SSRF (Highest Impact) | 3. XSS (Most Frequent) | 4. SQLi (High Bounty) | 5. Authentication Bypass | 6. Business Logic Flaws | 7. Information Disclosure | Bounty Ranges (2026) | Disclosed Report Repos
  - Bypass:** UUID prediction, sequential IDs, encoded IDs, base64 manipulation
  - Testing:** Change user ID in request → check if other user's data returned
  - Bypass:** IPv6, DNS rebinding, redirect chains, encoded URLs
  - Bypass:** DOMPurify bypass, SVG mXSS, event handler injection
  - Technique:** Test in HTML attributes, JS contexts, CSS, SVG, URL params
  - Bypass:** WAF bypass via tamper scripts, unicode normalization, double encoding
  - Technique:** Union-based → extract data, blind → time-based confirmation
  - Pattern:** OAuth misconfiguration, JWT validation gap, session fixation
  - Technique:** Token manipulation, cookie injection, redirect URI validation bypass
  - Testing:** Test password reset flow, OAuth callback, JWT `none` algorithm
  - Pattern:** Price manipulation, quantity overflow, race conditions
  - Technique:** Negative quantities, decimal prices, concurrent requests
  - Testing:** Intercept → modify → replay → observe server response
  - Technique:** `.git/config`, `.env`, `/debug`, `/actuator`, stack traces

## SKILL: 401/403 Bypass Techniques — Expert Attack Playbook
- file: `hackskill-401-403-bypass-techniques.md`  (9833 bytes)
- sections: 0. RELATED ROUTING | 1. PATH MANIPULATION BYPASSES | 1.1 Trailing Slash / Missing Slash | 1.2 Case Sensitivity | 1.3 URL Encoding | 1.4 Double URL Encoding | 1.5 Unicode / UTF-8 Encoding | 1.6 Dot-Segment / Path Traversal | 1.7 Null Byte | 1.8 Path Parameter Injection | 1.9 Trailing Special Characters | 1.10 Backslash (Windows/IIS)
  - [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) — broader auth bypass (login flaws, session handling)
  - [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) — when bypass is WAF-specific rather than access control
  - [http-host-header-attacks](../http-host-header-attacks/SKILL.md) — Host header manipulation for routing bypass
  - [request-smuggling](../request-smuggling/SKILL.md) — smuggle past access controls entirely
  - [http2-specific-attacks](../http2-specific-attacks/SKILL.md) — h2c smuggling to bypass proxy ACLs

## SKILL: Authentication Bypass — Expert Attack Playbook
- file: `hackskill-authbypass-authentication-flaws.md`  (14963 bytes)
- sections: 0. AUTHORIZED CREDENTIAL TEST PLANNING | Service-first tiny sets | Username classes | Wordlist sizing and port focus | 1. SQL INJECTION LOGIN BYPASS | 2. PASSWORD RESET VULNERABILITIES | Guessable / Predictable Reset Tokens | Reset Token Not Expiring | Reset Token Reuse | Host Header Injection in Reset Email | Password Reset Token in Referer | Password Change Without Current Password
  - Request password reset → get token via email
  - Use old token → does it work?
  - Request reset → get token T1
  - Use T1 again → does it work again?
  - Request reset → go to reset URL with token
  - Create account at attacker-controlled OAuth provider
  - Set email claim = victim@target.com
  - User forgets password (account has no password set after SSO only)
  - Replay captured session cookie → still valid?

## SKILL: Business Logic Vulnerabilities — Expert Attack Playbook
- file: `hackskill-business-logic-vulnerabilities.md`  (30755 bytes)
- sections: Companion files | Extended Scenarios | 1. PRICE AND VALUE MANIPULATION | Negative Quantity / Price | Decimal Quantity — "0元购" Case | Drop a Required Field — Free Tier Coercion | Integer Overflow | Rounding Manipulation | Currency Exchange Rate Lag | Free Upgrade via Promo Stacking | 2. RACE CONDITIONS | Double-Spend / Double-Redeem
  - Condition race practical patterns — parallel coupon application, gift card double-spend with Burp group send
  - Captcha bypass techniques — drop verification request, remove parameter, clear cookies to reset counter, OCR with tesseract
  - Frontend restriction bypass — array parameters for multiple coupons (`couponid[0]`/`couponid[1]`), remove `disabled`/`readonly` attributes
  - Application-layer DoS patterns — regex backtracking, WebSocket abuse
  - Capture request
  - Send to Repeater → duplicate 20+ times
  - "Send group in parallel" (Burp 2023+)
  - Add to cart
  - Set new password (requires valid token from step 3)
  - Add item to cart
  - Use account as verified — does server enforce re-verification?
  - Request password reset for your account → get token
  - Link OAuth (Google/GitHub) to your account
  - Login as super-admin → capture request, copy Cookie (JSESSIONID/Token)

## SKILL: OS Command Injection — Expert Attack Playbook
- file: `hackskill-cmdi-command-injection.md`  (19780 bytes)
- sections: 0. RELATED ROUTING | First-pass payload families | 1. SHELL METACHARACTERS (INJECTION OPERATORS) | 2. COMMON VULNERABLE CODE PATTERNS | Python | Node.js | Perl | ASP (Classic) | 3. BLIND COMMAND INJECTION — DETECTION | Time-Based Detection | OOB via DNS | OOB via HTTP
  - [upload insecure files](../upload-insecure-files/SKILL.md) when the shell sink is part of a broader upload, import, or conversion workflow

## SKILL: CORS Misconfiguration — Credentialed Origins, Reflection, and Trust Boundary Errors
- file: `hackskill-cors-cross-origin-misconfiguration.md`  (9559 bytes)
- sections: Extended Scenarios | 1. WHEN TO LOAD THIS SKILL | 2. HIGH-VALUE MISCONFIGURATION CHECKS | 3. QUICK TRIAGE | 4. RELATED ROUTES | 5. NULL ORIGIN EXPLOITATION | How `Origin: null` is sent | Exploitation | 6. SUBDOMAIN XSS → CORS BYPASS CHAIN | Attack flow | PoC (injected via XSS on blog.target.com) | Why this works
  - Honeypot de-anonymization via JSONP — use social platform JSONP endpoints to identify anonymous visitors
  - JSON endpoints appear protected from CSRF but are readable cross-origin
  - Send crafted `Origin` headers and inspect reflection.
  - If readable data is sensitive, chain to account or tenant impact.
  - Session or JSON action abuse: [csrf cross site request forgery](../csrf-cross-site-request-forgery/SKILL.md)
  - OAuth token leakage and callback binding: [oauth oidc misconfiguration](../oauth-oidc-misconfiguration/SKILL.md)
  - API auth context: [api auth and jwt abuse](../api-auth-and-jwt-abuse/SKILL.md)
  - Find XSS on any subdomain: blog.target.com, dev.target.com, etc.
  - Exploit XSS to make credentialed requests to api.target.com
  - CORS allows the request → attacker reads sensitive API responses
  - Combined: SameSite bypass + CORS read = full API access from XSS on any subdomain
  - Warm the cache: send request with Origin: https://attacker.com
  - Cached ACAO header allows attacker.com to read the response

## SKILL: CSRF — Cross-Site Request Forgery — Expert Attack Playbook
- file: `hackskill-csrf-cross-site-request-forgery.md`  (16621 bytes)
- sections: 0. RELATED ROUTING | 1. CORE CONCEPT | 2. FINDING CSRF TARGETS | 3. TOKEN BYPASS TECHNIQUES | No Token Present | Token Not Validated (most common finding!) | Token Tied to Session but Not to User | Token in Cookie Only | Static or Predictable Token | Double Submit Cookie Pattern (broken if subdomain trusted) | 4. SAMESITE BYPASS SCENARIOS | 5. CSRF PROOF OF CONCEPT TEMPLATES
  - [oauth oidc misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) when login, account linking, or callback binding relies on OAuth state
  - Attacker can predict/construct the valid request
  - Password change ← account takeover
  - Email change ← account takeover
  - Add admin / change role ← privilege escalation
  - OAuth app authorization ← hijack oauth flow
  - Attacker initiates OAuth flow, gets authorization code
  - Before exchanging code, stops the flow (captures the redirect URL with code)
  - Sends victim the crafted URL: `https://target.com/oauth/callback?code=ATTACKER_CODE`
  - Victim's browser exchanges the attacker's code → victim's account linked to attacker's OAuth provider
  - Attacker page → 302 redirect to https://target.com/transfer?to=attacker&amount=1000
  - Browser follows redirect as top-level navigation → Lax cookies sent
  - If target accepts GET for state-changing operations → CSRF succeeds
  - Response is readable → CSRF token extracted from response

## SKILL: GraphQL and Hidden Parameters — Introspection, Batching, and Undocumented Fields
- file: `hackskill-graphql-and-hidden-parameters.md`  (1761 bytes)
- sections: 1. GRAPHQL FIRST PASS | 2. HIGH-VALUE GRAPHQL TESTS | 3. HIDDEN PARAMETER DISCOVERY | 4. NEXT ROUTING
  - frontend code using richer request bodies than visible UI controls
  - If hidden fields affect privilege: [api authorization and bola](../api-authorization-and-bola/SKILL.md)
  - If GraphQL batching changes auth or rate behavior: [api auth and jwt abuse](../api-auth-and-jwt-abuse/SKILL.md)
  - If endpoint discovery is incomplete: [api recon and docs](../api-recon-and-docs/SKILL.md)

## SKILL: IDOR / Broken Object Level Authorization — Expert Attack Playbook
- file: `hackskill-idor-broken-object-authorization.md`  (10543 bytes)
- sections: 1. IDOR vs BOLA vs BFLA | 2. WHERE TO FIND OBJECT IDs (ALL LOCATIONS) | 3. A-B TESTING METHODOLOGY | 4. ID TYPE ITS IMPLICATIONS | 5. HORIZONTAL vs VERTICAL PRIVILEGE ESCALATION | 6. HTTP METHOD ESCALATION | 7. PARAMETER POLLUTION & TYPE CONFUSION | 8. BFLA (FUNCTION LEVEL) ATTACKS | Common BFLA Endpoints to Test | How to Find Hidden Admin Endpoints | 9. INDIRECT IDOR (REFERENCE CHAIN) | 10. MASS ASSIGNMENT → PRIVILEGE ESCALATION
  - BOLA = accessing **object** you shouldn't own (data belonging to other users)
  - BFLA = accessing **function** you shouldn't be authorized for (admin CRUD operations, bulk actions, user management)
  - Fuzz with Burp: add common property names and check for `200` vs `400`
  - Perform all CRUD operations as A, capture all request IDs
  - Replay each request replacing A's IDs with B's IDs

## SKILL: OAuth and OIDC Misconfiguration — Redirects, PKCE, Scopes, and Token Binding
- file: `hackskill-oauth-oidc-misconfiguration.md`  (2320 bytes)
- sections: 1. WHEN TO LOAD THIS SKILL | 2. HIGH-VALUE MISCONFIGURATION CHECKS | 3. QUICK TRIAGE | 4. RELATED ROUTES
  - Mobile or SPA clients rely on OAuth or OIDC flows
  - [jwt oauth token attacks](../jwt-oauth-token-attacks/SKILL.md)
  - Replay callback flows with altered `state`, `nonce`, and `redirect_uri`.
  - XML federation or enterprise SSO: [saml sso assertion attacks](../saml-sso-assertion-attacks/SKILL.md)
  - CSRF-heavy login or binding bugs: [csrf cross site request forgery](../csrf-cross-site-request-forgery/SKILL.md)

## SKILL: Open Redirect — Expert Attack Playbook
- file: `hackskill-open-redirect.md`  (11388 bytes)
- sections: 1. CORE CONCEPT | 2. FINDING REDIRECT PARAMETERS | Common Parameter Names | Server-Side Sinks | Client-Side (JavaScript) Sinks | 3. FILTER BYPASS TECHNIQUES | 4. EXPLOITATION CHAINS | Phishing Amplification | OAuth Token Theft | CSRF Referer Bypass | SSRF via Redirect | 5. TESTING CHECKLIST
  - Attacker page links to: https://trusted.com/redirect?url=https://trusted.com/change-email
  - Redirect preserves Referer from trusted.com
  - CSRF protection passes because Referer = trusted.com
  - It can redirect the ORIGINAL page: `window.opener.location = "https://phishing.com/login"`
  - Open redirect fires → browser navigates to:
  - Redirects to: https://target.com/redirect?url=https://evil.com&code=AUTH_CODE
  - Open redirect sends victim to: https://evil.com?code=AUTH_CODE
  - Submit URL to server-side fetcher: http://attacker.com/redirect
  - Server follows redirect → SSRF to cloud metadata endpoint
  - Server resolves attacker.com → public IP → passes SSRF filter
  - Connection established, but HTTP redirect points to attacker.com again
  - Server follows redirect to internal address

## SKILL: Race Conditions — Testing & Exploitation Playbook
- file: `hackskill-race-condition.md`  (21470 bytes)
- sections: 0. QUICK START — What to Test First | 1. CORE CONCEPT | 1.1 TOCTOU (Time-of-check to time-of-use) | 1.2 Non-atomic read-then-write | 1.3 Database-level vs application-level locking gaps | 2. ATTACK PATTERNS | 2.1 Limit-overrun (double redeem / double claim) | 2.2 Rate-limit bypass via simultaneity | 2.3 Multi-step exploitation (beat the pipeline) | 3. HTTP/1.1 LAST-BYTE SYNCHRONIZATION | 4. HTTP/2 SINGLE-PACKET ATTACK | 5. TURBO INTRUDER TEMPLATES
  - Capture the **state-changing** request in a proxy.
  - Send **20–100** copies **as simultaneously as your tooling allows**.
  - Use **Send group (parallel)** / **single-packet attack** where available.
  - Correlate** with `x-request` (or similar) markers or unique body fields in logs (authorized environments).
  - If `TCP_NODELAY` is set, the client must use `writev()` / gather-write syscall to batch frames
  - business-logic-vulnerabilities** — workflow, coupon abuse, and logic-first checklists (`../business-logic-vulnerabilities/SKILL.md`).

## SKILL: HTTP Request Smuggling — Expert Attack Playbook
- file: `hackskill-request-smuggling.md`  (14738 bytes)
- sections: 0. RELATED ROUTING | 1. QUICK START | CL.TE first probe (front-end trusts CL, back-end trusts chunked) | TE.CL first probe (front-end trusts chunked, back-end trusts CL) | Safety note | 1. CORE CONCEPT | 2. CL.TE VULNERABILITIES | 3. TE.CL VULNERABILITIES | 4. TE.TE VULNERABILITIES | 5. HTTP/2 REQUEST SMUGGLING | H2 -> H1 Downgrade | Pseudo-header / header-injection smuggling (concept payload)
  - Front end reads only 13 bytes based on `Content-Length: 13` (that is, `0\r\n\r\nSMUGGLED`, 13 bytes total) and considers the request complete.
  - Back end parses as chunked: after the `0` end chunk, it treats **`SMUGGLED` and onward** as the start byte stream of the **next request**.
  - incorrect pseudo-header to regular-header mapping order;
  - duplicate-header merge rules inconsistent with the origin.
  - H2.CL and H2.TE variants with byte-level payload examples
  - CL.0 (connection close desync) — technique and detection
  - Fat GET request smuggling (body in GET request)
  - Request smuggling → cache poisoning chain (response queue misalignment)
  - Input enters interpreter/query language/template** (not HTTP framing) -> [Injection Testing Router](../injection-checking/SKILL.md) (then drill down into XSS, SQLi, SSTI, etc.).
  - Response header splitting / Location CRLF** -> [CRLF Injection](../crlf-injection/SKILL.md).

## SKILL: SQL Injection — Expert Attack Playbook
- file: `hackskill-sqli-sql-injection.md`  (15383 bytes)
- sections: 0. RELATED ROUTING | 1. QUICK START | Extended Scenarios | Advanced Reference | First-pass payload families | Small, stable first-pass set | DBMS routing hints | 1. DETECTION — SUBTLE INDICATORS | 2. DATABASE FINGERPRINTING | 3. UNION-BASED DATA EXTRACTION | 4. BLIND INJECTION — INFERENCE TECHNIQUES | Boolean Blind (conditional response difference)
  - SQLMap tamper scripts matrix and WAF bypass tamper chain recipes (space2comment, between, charencode, etc.)
  - `--technique`, `--risk`/`--level` combinations and `--second-url` for second-order injection
  - GraphQL + SQL injection (batched queries, nested field injection, mutation injection)
  - Routed injection: `1' UNION SELECT 0x(inner_payload_hex)-- -` where inner payload is another full query hex-encoded
  - Second Order: inject into storage, trigger when data is used in another query later

## SKILL: Server-Side Request Forgery (SSRF) — Expert Attack Playbook
- file: `hackskill-ssrf-server-side-request-forgery.md`  (11105 bytes)
- sections: 0. QUICK START | Extended Scenarios | Advanced Reference | First-pass payloads | Host validation bypass families | Protocol routing | 1. FINDING SSRF SURFACE | 2. BASIC CONFIRMATION METHODOLOGY | 3. CLOUD METADATA ENDPOINTS — MUST-TRY | AWS EC2 IMDSv1 (no auth required — critical) | AWS IMDSv2 (token required — but check if SSRF can GET the token) | Google Cloud
  - WebLogic SSRF (CVE-2014-4210) — `uddiexplorer/SearchPublicRegistries.jsp` + `operator` parameter + `%0D%0A` CRLF to inject Redis commands
  - SSRF → internal Redis → write crontab reverse shell complete payload chain
  - DNS Rebinding deep dive — TTL=0 trick, initial-legit→second-internal resolution, `rbndr.us` service
  - Kubernetes SSRF (CVE-2020-8555) and bypass (CVE-2020-8562) via DNS rebinding
  - SSRF through PDF/screenshot generators — `<iframe>` and `<img>` in HTML-to-PDF
  - URL parser confusion for filter bypass — `#@`, `\@`, `%00@`, IPv6-mapped IPv4
  - Full cloud metadata endpoint catalog (AWS IMDSv1/v2, GCP, Azure, DigitalOcean, Alibaba Cloud, Oracle Cloud, Kubernetes, Hetzner, OpenStack)
  - gopher:// payload recipes for Redis, MySQL, SMTP, FastCGI, Memcached (with encoding rules)
  - DNS Rebinding detailed attack flow with TTL manipulation and TOCTOU analysis
  - PDF/wkhtmltopdf/WeasyPrint/Chrome headless/PhantomJS SSRF patterns and exfiltration techniques
  - OAuth redirect URI (sometimes triggers server-side fetch)
  - GraphQL `@link` directive (federation)
  - Burp Collaborator / interact.sh**: check for DNS + HTTP request from server
  - Pingback/webhook abuse**: configure application's own webhook to your URL

## SKILL: Server-Side Template Injection (SSTI) — Expert Attack Playbook
- file: `hackskill-ssti-server-side-template-injection.md`  (11504 bytes)
- sections: 0. RELATED ROUTING | Extended Scenarios | Engine Payloads Reference | Universal detection & blind SSTI (pointer) | 1. DETECTION — POLYGLOT PROBE SEQUENCE | 2. ENGINE-TO-LANGUAGE MAPPING | 3. JINJA2 (PYTHON FLASK) — RCE CHAINS | Chain 1: `os` module via `__globals__` | Chain 2: MRO subclass traversal (sandbox escape) | Chain 3: `request` object globals (works when `config` blocked) | Chain 4: `lipsum` function globals (Flask built-in) | Chain 5: `cycler` object
  - First use the polyglot probe sequence at the top of this file for low-noise fingerprinting
  - Maccms 8.x PHP template `eval` — `{if-A:phpinfo()}{endif-A}` in `vod-search`, base64 bypass for webshell write
  - Struts2 OGNL S2-045 (CVE-2017-5638) — Content-Type header OGNL injection with `_memberAccess` / `OgnlUtil` blacklist clear
  - Confluence OGNL CVE-2021-26084 — `createpage-entervariables.action` with `\u0027` unicode bypass
  - SSTI vs EL injection disambiguation guide
  - Additional template engines: ASP.NET Razor, Elixir EEx, PHP Smarty/Latte/Blade, JS Pug/Handlebars/Nunjucks/EJS/Lodash + universal detection + blind SSTI + Flask PIN calculation
  - Error pages: `404 Not Found: /PAYLOAD`
  - Compute PIN** — use established open-source PIN calculators that implement the same algorithm from these values

## SKILL: Subdomain Takeover — Detection & Exploitation Playbook
- file: `hackskill-subdomain-takeover.md`  (10461 bytes)
- sections: 0. RELATED ROUTING | 1. CORE CONCEPT | 2. DETECTION METHODOLOGY | 2.1 CNAME Enumeration | 2.2 Key Signals | 2.3 Automated Tools | 3. SERVICE PROVIDER FINGERPRINT TABLE | 4. TAKEOVER PROCEDURE — COMMON PROVIDERS | 4.1 AWS S3 | 4.2 GitHub Pages | 4.3 Heroku | 5. NS TAKEOVER — HIGH SEVERITY
  - [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) when a subdomain takeover is used to bypass SSRF allowlists trusting `*.target.com`
  - [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) when CORS trusts `*.target.com` — takeover → full cross-origin read
  - [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) takeover gives you script execution under target origin (cookie theft, OAuth redirect abuse)
  - [http-host-header-attacks](../http-host-header-attacks/SKILL.md) when Host routing leads to subdomain-scoped cache or auth issues
  - Upload index.html proving control
  - Add CNAME file containing "sub.target.com"
  - heroku domains:add sub.target.com
  - Full domain takeover (serve any content, intercept email, issue TLS certs via DNS-01)
  - Modify SPF/DKIM/DMARC → send authenticated email as target
  - Potentially reset accounts that use email-based auth
  - CNAME ≠ takeover**: A CNAME to S3 that returns 403 (bucket exists, private) is NOT vulnerable. Only `NoSuchBucket` (404) is.
  - Region matters for S3**: Bucket names are global, but website endpoints are regional. Try matching the region from the CNAME.
  - Second-order takeover**: `sub.target.com CNAME → other.target.com CNAME → dead-service.com` — the chain must be followed fully.
  - SPF subdomain takeover**: If SPF includes `include:sub.target.com` and you take over `sub.target.com`, you can modify its SPF TXT record to authorize your mail server → send spoofed email as `target.c

## SKILL: Web Cache Deception — Expert Attack Playbook
- file: `hackskill-web-cache-deception.md`  (6633 bytes)
- sections: Advanced Reference | 1. CORE CONCEPTS | Web Cache Deception (steal authenticated data) | Web Cache Poisoning (serve malicious content) | 2. CACHE DECEPTION — ATTACK METHODOLOGY | Step 1: Identify Cacheable Path Patterns | Step 2: Test Path Confusion | Step 3: Verify Caching | Step 4: Deliver to Victim | 3. CACHE POISONING — ATTACK METHODOLOGY | Unkeyed Input Discovery | Common Unkeyed Headers
  - Unkeyed header poisoning (X-Forwarded-Host, X-Forwarded-Scheme, X-Original-URL, multiple Host headers)
  - Vary header manipulation, cache partitioning attacks, and missing Vary vulnerabilities
  - Set `Cache-Control: no-store, private` on authenticated endpoints
  - Use `Vary: Cookie` to prevent cross-user cache hits
  - Use `Cache-Control: no-cache` for dynamic content

## SKILL: Cross-Site Scripting (XSS) — Expert Attack Playbook
- file: `hackskill-xss-cross-site-scripting.md`  (13232 bytes)
- sections: 0. RELATED ROUTING | Extended Scenarios | Advanced Tricks | Quick context picks | 1. INJECTION CONTEXT MATRIX | 2. MULTI-REFLECTION ATTACKS | 3. ADVANCED INJECTION VECTORS | DOM Insert Injection (when reflection is in DOM not source) | PHP_SELF Path Injection | File Upload XSS | postMessage XSS (no origin check) | postMessage Origin Bypass
  - Django debug page XSS (CVE-2017-12794) — duplicate key error → unescaped exception → XSS
  - UTF-7 XSS for legacy IE environments (`+ADw-script+AD4-`)
  - HttpOnly bypass methodology — proxy-the-browser, session riding, CSRF-via-XSS
  - Session fixation via XSS — pre-set session ID before victim login
  - mXSS / DOMPurify bypass — namespace confusion, `<noscript>` parsing differential, form/table restructuring
  - Modern framework XSS — React `dangerouslySetInnerHTML`, Vue `v-html`, Angular `bypassSecurityTrust*`, Next.js SSR
  - Trusted Types bypass — default policy abuse, non-TT sinks, policy passthrough
  - Service Worker XSS persistence — malicious SW registration, fetch interception, post-patch survival
  - PDF/SVG/MathML XSS vectors, polyglot payloads, browser-specific tricks
  - [upload insecure files](../upload-insecure-files/SKILL.md) when you need the full upload path: validation, storage, preview, and sharing behavior
  - Note: **the same filter likely exists elsewhere** — if they filter `<script>` in search, do they filter it in file upload filename? In profile bio?

## SKILL: XML External Entity Injection (XXE) — Expert Attack Playbook
- file: `hackskill-xxe-xml-external-entity.md`  (16139 bytes)
- sections: 0. RELATED ROUTING | Extended Scenarios | 1. CLASSIC XXE PAYLOAD | 2. ATTACK SURFACE DISCOVERY | Direct XML Inputs | Non-Obvious XML Processing | PDF Generators | 3. OOB (OUT-OF-BAND) XXE — CRITICAL | Step 1: Blind detection | Step 2: OOB file exfiltration via attacker-hosted DTD | Step 3: Error-based OOB (alternative when HTTP blocked) | 4. XXE FILE READ TARGETS
  - [upload insecure files](../upload-insecure-files/SKILL.md) when XXE is reachable through SVG, OOXML, import, or preview pipelines
  - Apache Solr XXE + RCE chain (CVE-2017-12629) — XXE to read config, then VelocityResponseWriter for RCE
  - Office docx XXE step-by-step — unzip → inject DOCTYPE into `word/document.xml` or `[Content_Types].xml` → repackage → upload
  - DOCTYPE-based blind SSRF — `PUBLIC` external DTD reference triggers HTTP callback without entity reflection
  - PHP `expect://` protocol via XXE — direct command execution when expect extension is installed
  - Blind XXE via error messages — force file path error that leaks content in exception text
  - XXE in SOAP web services — inject entities into SOAP Envelope/Body elements
  - File upload: `.xlsx`, `.docx`, `.pptx` (Office Open XML)
  - Local DTD is trusted → entity overrides inject attacker-controlled definitions

## Harness evidence integrity — how a scanner sweep fabricates coverage
- file: `harness-evidence-integrity.md`  (7287 bytes)
- sections: 0. The user challenge that started it | 1. Answer "did you use ALL tools?" by diffing two lists — never from memory | 2. Bug: the shell-quoted command header breaks the shell, so nothing runs | 3. Bug: `capture_output=True` + `shell=True` defeats your own timeout | 4. Bug: status derived from "the command returned" — false EXECUTED | 5. Bug: the sweep used the wrong wordlist and the scanner's default UA | 6. Bug: output buffering hid the whole run | 7. What a correct sweep costs, and what it is actually worth
  - Print the end sentinel from Python**, so "the file has a header but no END" unambiguously means

## JWT Attack Payloads - Curated from exploit-cookbook
- file: `jwt-attack-payloads.txt`  (3816 bytes)

## Layer Checklists (10 Layers) — Deep Audit Doctrine
- file: `layer-checklists.md`  (9350 bytes)
- sections: LAYER 1: SURFACE | LAYER 2: INFRASTRUCTURE DEEP | LAYER 3: AUTHENTICATION DEEP | LAYER 4: AUTHORIZATION DEEP | LAYER 5: BUSINESS LOGIC DEEP | LAYER 6: THIRD-PARTY INTEGRATION DEEP | LAYER 7: CLIENT-SIDE DEEP | LAYER 8: CRYPTO/WEB3 DEEP (if applicable) | LAYER 9: ADVANCED TECHNIQUES | LAYER 10: EXOTIC / RARE VECTORS | Deep-Dive Decision Tree | Deep-Dive Anti-Patterns (NEVER DO THESE):

## Manual multi-tenant / authz testing (no-scanner engagements)
- file: `manual-multitenant-authz-testing.md`  (7975 bytes)
- sections: 1. Build the test assets (operator-owned, required by most programs) | 2. Intercept the OAuth code without a reachable callback host | 3. `redirect_uri` validation: test at the real decision point | 4. BOLA/IDOR matrix (API **and** web session) | 5. BFLA / permission levels | ⛔ The false-positive trap (cost this engagement a full re-check) | 6. Invitation / activation token binding | 7. Quick supplementary checks | 8. Pitfalls that wasted time | 9. Evidence & closing
  - Decisive test:** submit with `user=<id of a disposable own account>`, then try logging in as
  - Env isolation:** production token against the sandbox host → expect `401 Access token not recognised`.
  - Subdomain takeover triage:** resolve a random name first. Wildcard DNS means every enumerated
  - One JSON per vector under `evidence/<vector>/`, each storing the **exact request, status and body**

## Methodology Index — Curated from 5 Repos
- file: `methodology-index.md`  (1896 bytes)
- sections: 1. vavkamil/awesome-bugbounty-tools ⭐6.3K | 2. devanshbatham/Awesome-Bugbounty-Writeups ⭐6.1K | 3. KingOfBugbounty/KingOfBugbountyTips ⭐5.5K | 4. HolyBugx/HolyTips ⭐2K | 5. xalgord/Massive-Web-App-Pentest-Notes ⭐1.9K | Extracted Playbooks | Recon Methodology (from KingOfBugbountyTips) | Testing Methodology (from Massive-Pentest-Notes) | Reporting Tips (from Awesome-Bugbounty-Writeups)
  - Writeups organized by bug type (SSRF, IDOR, XSS, SQLi, etc)
  - Recon methodology, subdomain discovery, endpoint analysis
  - Covers full lifecycle: recon → test → exploit → report
  - Endpoint discovery (gau/katana/waybackurls)
  - Authorization testing (IDOR/BOLA)
  - Input validation (XSS, SQLi, SSTI)
  - File upload testing
  - API testing (REST, GraphQL)

## MOBILE APP PENTEST (ANDROID / iOS)
- file: `mobile-pentest-guide.md`  (18620 bytes)
- sections: RUNTIME-FIRST — THE ONE RULE THAT MATTERS | 0. SCOPE CHECK FIRST | 1. SETUP (one-time) | 2. STATIC SWEEP — SECRETS + ENDPOINTS WEB RECON MISSES 🔑 | 3. NETWORK-LAYER TESTING — TREAT IT LIKE A WEB TARGET 📡 | 4. SSL PINNING BYPASS — WHEN TRAFFIC IS BLANK 🔓 | 5. EXPORTED ACTIVITIES + DEEPLINK INJECTION 📲 | 6. WEBVIEW `addJavascriptInterface` BRIDGE 🌉 | 7. RECOVERING THE REQUEST SIGNER (OkHttp interceptor chain) | NEVER SUBMIT (mobile N/A list — kill these fast) | REAL PAID EXAMPLES | TOOL ORDER (compress it, but keep the logic)
  - Capture one clean baseline request, replay it **unchanged** to prove it's stable.
  - Auth / session** — strip or swap the bearer token, device-id, and tenant/user-id; replay across two accounts. Mobile apps love `X-User-Id` / `deviceId` headers that the server trusts → horizontal IDOR
  - Business logic** — change object IDs, amounts, prices, coupon state; skip workflow steps; replay payment requests (race / double-spend). Follow the money.
  - Injection** — fields reaching search, filter, file metadata, XML, or server-side fetch. SSRF/SSTI/SQLi same as web.
  - GraphQL / WebSocket** — introspection, field overreach, channel auth, stale-token reuse.
  - Deeplink sets an auth token / deep-links into a logged-in flow → **account takeover** if the URL is attacker-supplied (per Oversecured's disclosed deeplink→ATO chain).
  - On **API < 17**, `addJavascriptInterface` exposes `getClass()` → reflection → arbitrary Java → effectively RCE. Rare now but still paid on legacy apps.
  - On modern API, impact = whatever the bridge methods leak/do: auth token exfil, PII read, file read (`setAllowFileAccess`), privileged native action triggered by web JS.
  - Deep link → WebView redirect → token theft / account takeover — pattern documented across multiple disclosed Android reports (Oversecured research, seen on H1/Bugcrowd programs).
  - frida / objection — runtime hooks, pinning bypass, signer dump

## ⛔ PHASE EXECUTION ENFORCEMENT — ZERO SKIP PROTOCOL
- file: `phase-execution-enforcement.md`  (5530 bytes)
- sections: PERATURAN UTAMA | PER-FILE ENFORCEMENT RULE | TIMEOUT HANDLING — TIDAK BOLEH SKIP | CONTEXT OVERFLOW HANDLING — TIDAK BOLEH PRUNE | VERIFICATION GATE PER PHASE | SELF-CHECK PROTOCOL | CONSEQUENCE TABLE
  - Cek: 84/84 exploit-cookbook refs executed?
  - Cek: 13/13 payload files executed?

## The audit phase model is 0A → 0F (authoritative)
- file: `phase-framework-0A-0F.md`  (3791 bytes)
- sections: Phase → artifact map | Drift sweep — run this before claiming the framework is aligned | Verify, don't assume
  - `bb-audit-launcher/references/*` (a second, top-level copy of the same reference set exists — sweep both)
  - `security/exploit-cookbook/references/{execution-discipline-protocol,redteam-playbook,phase-execution-enforcement,slowmist-vulns,sqlmap-advanced,sqli-exfiltration-lab}.md`

## PoC Sources & Exploit Databases — 2026
- file: `poc-sources-2026.md`  (3074 bytes)
- sections: Primary PoC Aggregators | Advisory Databases | How to Find PoC for a CVE | BB Automation Tools | How to Execute PoCs During Audit | Program Lists | Key 2026 CVEs with PoC

## PoC Index Execution Workflow — How to Use 82K+ PoCs During Audit
- file: `pocindex-execution-workflow.md`  (6105 bytes)
- sections: Quick Reference — 3 Methods | Method 1: Direct CVE Lookup (fastest) | Method 2: Website Search (best for discovery) | Method 3: GitHub Code Search (for keyword discovery) | Audit Workflow — Step by Step | Step 1: Identify Target Tech Stack | Step 2: Search pocindex for Matching CVEs | Step 3: Read CVE File → Get PoC Links | Step 4: Study PoC → Understand Attack Pattern | Step 5: Adapt to Your Target | Practical Example — Full Workflow | Scenario: Target runs WordPress 6.4
  - Report as your own finding** — PoC is reference, not your exploit
  - Execute adapted payload

## Proven Exploitation Playbooks
- file: `proven-exploits.md`  (18173 bytes)
- sections: 1. SSRF → Cloud Metadata → RCE | Deteksi | Validasi | Eksekusi (AWS IMDSv1) | Eksekusi (GCP) | Escalation | Script | 2. IDOR → Horizontal Privilege Escalation | Deteksi | Validasi | Eksekusi | Escalation
  - Response time beda (200 vs timeout) = endpoint hidup
  - `Server` header beda = internal service
  - Error message detail = verbose error (info leak)
  - Internal Redis: `gopher://127.0.0.1:6379/_*3%0d%0aset%20...` → RCE via EVAL
  - Response 200 + data user lain = **CONFIRMED IDOR**
  - Response 403 = authorization bypass needed (vertical escalation)
  - Response 404 = ID not sequential, try enumeration
  - IDOR on DELETE → Data destruction (higher severity)
  - IDOR on PUT → Account takeover (change email/password)
  - IDOR on payment → Free stuff
  - Balance check** → deduct → (race window) → deduct again = double-spend
  - Coupon check** → apply → (race window) → apply again = multiple use
  - Permission check** → grant → (race window) → grant again = privilege escalation
  - Rate limit** → check → (race window) → bypass

## Red Team Playbook — Curated from 17 Repos
- file: `redteam-playbook.md`  (3771 bytes)
- sections: C2 Frameworks (Methodology) | 1. pupy ⭐9K — Python C2 | 2. Covenant ⭐4.7K — .NET C2 | 3. Villain ⭐4.5K — Stage 0/1 C2 | 4. PoshC2 ⭐2.1K — PowerShell C2 | 5. phpsploit ⭐2.5K — Webshell C2 | Post-Exploitation Methodology | Privilege Escalation (Linux) | Privilege Escalation (Windows) | Lateral Movement | Persistence | Offense Frameworks
  - Features: payload generation, session management
  - Features: file upload, cmd exec, reverse shell
  - Red team, exploit dev, AD attacks, EDR bypass
  - Exploit playbooks → `exploit-cookbook`

## Reference Files Loader — Phase 0C
- file: `reference-loader.md`  (17516 bytes)
- sections: Load Procedure | XSS Testing | SQL Injection | SSRF Testing | CORS Testing | Authentication Testing | GraphQL Testing | API Testing | Access Control | File Upload / Path Traversal | Request Smuggling | Race Conditions

## REPORT WRITING
- file: `report-writing-advanced.md`  (15547 bytes)
- sections: THE MOST IMPORTANT RULE | PERSISTENCE RULE | TITLE FORMULA | HACKERONE REPORT TEMPLATE | Summary | Vulnerability Details | Steps to Reproduce | Impact | Recommended Fix | Supporting Materials | BUGCROWD REPORT TEMPLATE | Description
  - Send the following request:
  - [Login as attacker / visit URL / send request]
  - Send the following HTTP request:
  - Severity is set by you: Critical/High/Medium/Low/Exceptional
  - Full account takeover of any user without interaction
  - SQLi with ability to dump/modify entire DB
  - Auth bypass to admin panel
  - SSRF to cloud metadata → IAM credentials exfil
  - SSRF reaching internal services (data returned)
  - Stored XSS executing for all users of sensitive feature
  - Payment bypass / financial loss without limit
  - IDOR on specific user's non-critical data
  - XSS on low-sensitivity page requiring victim interaction
  - CSRF on important but non-critical action

## Guarded scanner volley · path traps · orphan-process cleanup
- file: `scanner-volley-guard-and-hardening.md`  (4864 bytes)
- sections: 1. The guarded script shape | 2. Block detection + what to expect | 3. The MSYS path trap (silent fake coverage) | 4. Kill verification (killing the wrapper is not enough) | 5. Reporting the incident honestly

## SECURITY ARSENAL
- file: `security-arsenal-argus.md`  (62411 bytes)
- sections: XSS PAYLOADS | Basic Probes | Cookie Theft (proof of impact) | CSP Bypass Techniques | DOM XSS Sources and Sinks | SSRF PAYLOADS | Cloud Metadata | Internal Service Fingerprinting | SSRF IP Bypass Payloads | SQL INJECTION PAYLOADS | Detection | Union-Based (determine column count)
  - Install HTTP Request Smuggler extension
  - Right-click request → Extensions → HTTP Request Smuggler → Smuggle probe
  - Custom enterprise WAFs: `200 OK` + "Your request has been blocked. Log ID: WAF-..."
  - `500 Internal Server Error` = payload triggered backend exception (SQLi/SSTI lead)
  - `502/503` = you reached origin (WAF forwarded the request)
  - Request OTP → receive "123456"
  - Try OTP from previous session at new login

## Sensitive Files Wordlist - Curated from exploit-cookbook
- file: `sensitive-files-wordlist.txt`  (1960 bytes)

## Severity Rules & Finding Quality
- file: `severity-rules.md`  (8110 bytes)
- sections: Hard Rule: NO SEVERITY INFLATION | Hard Rule: NO OVERCLAIMING | Rule 7: SOCIAL ENGINEERING / PHISHING ≠ BOUNTY FINDING | Rule 8: FINDING QUALITY CHECKLIST | Rule 9: JANGAN BERHENTI SETELAH DAPAT 1-2 TEMUAN LOW/INFO | Rule 10: REPORT HARUS BERISI FINDINGS YANG BOUNTY-WORTHY | Finding Priority Order (HARUS diurutkan):
  - "Critical RCE" padahal hanya command injection yang ter-block
  - "Account Takeover" padahal hanya bisa akses data, tidak bisa login
  - "SSRF" padahal hanya bisa internal scan, tidak bisa akses cloud metadata
  - "Authentication bypass" padahal hanya bisa bypass rate limit
  - "Low severity information disclosure" untuk info leak
  - "High severity authentication bypass" untuk real auth bypass
  - "Critical severity account takeover" untuk full ATO chain
  - Coba exploit TANPA phishing** — bisa direct request dari attacker machine?
  - Check if endpoint returns sensitive data tanpa auth** — kalau iya, itu IDOR, bukan CORS
  - Check if endpoint accessible tanpa origin check** — itu BAC, bukan CORS
  - Jika memang butuh victim interaction** — mark sebagai "potential chain enabler" saja, JANGAN jadi finding utama
  - IDOR/BOLA testing (direct exploit, no interaction)
  - Auth bypass testing (token/cookie manipulation)
  - RCE/SSRF testing (server-side)

## SQL Injection - Authentication Bypass Payloads
- file: `sqli-auth-bypass-payloads.txt`  (2132 bytes)

## SSRF Payloads - Curated from exploit-cookbook + security-arsenal
- file: `ssrf-payloads.txt`  (1860 bytes)

## Toolkit & Shortcuts
- file: `toolkit.md`  (3460 bytes)
- sections: Web2 Tools (installed ✅) | SQLi Tools (installed ✅) | Crypto/Node Exploit Tools (installed ✅) | Web3 Tools (updated 2026-09-18) | Manual Testing | Hermes Platform Triggers | Shortcut Reference | Wordlists & Payloads
  - sqlmap (38465★) — automatic SQLi + database takeover
  - bbqsql (832★) — fast blind SQLi exploitation
  - nosqlmap (3350★) — NoSQL injection (MongoDB/CouchDB)
  - theo (349★) — Ethereum recon + exploit via RPC
  - quimera (96★) — LLM-driven exploit generation
  - rpc-fingerprint — RPC endpoint fingerprinting
  - Native Foundry:** forge, cast
  - WSL Note:** aderyn/mythril route through WSL. ~10-20% slower than native. Use `wsl -d Ubuntu --` prefix if wrapper fails.
  - curl with full payload lists
  - GraphQL queries from graphql-attacks.md
  - bypass techniques from 403-bypass.md

## TRIAGE & VALIDATION
- file: `triage-validation-7qgate.md`  (13427 bytes)
- sections: THE 7-QUESTION GATE | Q1: Can an attacker use this RIGHT NOW, step by step? | Q2: Is the impact on the program's accepted impact list? | Q3: Is the root cause in an in-scope asset? | Q4: Does it require privileged access that an attacker can't realistically get? | Q5: Is this already known or accepted behavior? | Q6: Can you prove impact beyond "technically possible"? | Q7: Is this a known-invalid bug class? | Q8: Identity check — which session found this, and does it survive? | 4 PRE-SUBMISSION GATES | Gate 0: Reality Check (30 seconds) | Gate 1: Impact Validation (2 minutes)
  - Request: [exact HTTP method, URL, headers, body — copy-paste ready]
  - Impact: The real-world consequence is [account takeover / PII read / money stolen]
  - Critical**: Any-user ATO without interaction, RCE, SQLi with data exfil, admin auth bypass
  - High**: Mass PII exfil, privilege escalation, internal SSRF with data, stored XSS all users
  - Medium**: IDOR on specific user non-critical data, XSS on sensitive page requiring click
  - Program's HackerOne/Bugcrowd disclosed reports: Ctrl+F endpoint name + bug class
  - XSS → show actual cookie theft or session hijack, not just `alert(1)` or `alert(document.domain)`
  - SSRF → hit an internal endpoint that returns data, not just DNS ping
  - SQLi → show actual data exfil from a real table, not just error message
  - IDOR → show actual other-user's data in response, not just a 200 status code
  - Anonymous repro: Does the same request work with NO auth header?
  - IDOR / BOLA**: must work with session A reading session B's data — if it
  - Auth bypass**: must work *without* a valid session — if it stops working
  - Admin bypass**: "Admin can do X" is NEVER a bug → kill it immediately

## Vendor scanner prohibition → the guarded-volley pattern
- file: `vendor-scanner-prohibition-and-guarded-volley.md`  (5107 bytes)
- sections: When this applies | The pattern | 1. Build the volley, don't fire it | 2. Validate the whole toolchain on a LOCAL target first | 3. Record the coverage claim from disk | Block signature — define it BEFORE firing | Kill-switch (Windows / MSYS) | Recovery — do not evade | Honest post-mortem line to leave in the engagement log
  - Gate artefact**: append one JSON line per tool to `tool-evidence/_usage.jsonl` and assemble
  - Send one message on the vendor's disclosure channel covering both: (a) the block on this IP,

## WEB2 RECON PIPELINE
- file: `web2-recon-extended.md`  (25602 bytes)
- sections: SETUP (one-time) | THE 5-MINUTE RULE | STANDARD RECON PIPELINE | Pre-Hunt: Always Run First | Output to Organized Directory | ATTACK SURFACE TRIAGE | Find Interesting Targets in URL List | gf Patterns (Quick Classification) | JS ANALYSIS | SecretFinder (API keys, tokens in JS bundles) | LinkFinder (Endpoints hidden in JS) | DIRECTORY FUZZING
  - No JavaScript bundles with interesting endpoint paths

## WEB2 BUG CLASSES — 26 Classes
- file: `web2-vuln-classes-26.md`  (97066 bytes)
- sections: 1. IDOR — INSECURE DIRECT OBJECT REFERENCE 🔐 | Root Cause | Variants | Testing Checklist | IDOR Chain Escalation | 2. BROKEN AUTH / ACCESS CONTROL 🔐 | The Sibling Rule | Patterns | Real Paid Examples | 3. XSS — CROSS-SITE SCRIPTING | Stored XSS (highest impact) | DOM XSS Sinks (grep for these)
  - V2:** UUID swap — enumerate UUID via email invite or other endpoint
  - V3:** Indirect IDOR — `POST /api/export?report_id=456` exports another user's report
  - V4:** Parameter add — `?user_id=other` makes backend use it
  - V7:** GraphQL node — `{ node(id: "base64(User:456)") { email } }`
  - IDOR + Read PII = Medium
  - IDOR + Write (modify other's data) = High
  - IDOR + Admin endpoint = Critical (privilege escalation)
  - IDOR + Account takeover path = Critical
  - IDOR + Chatbot reads other user's data = High
  - HackerOne TrustHub**: `POST /graphql` with `TrustHubQuery` — no auth, regular user reads all vendors (CVSS 8.7 High)
  - XSS + sensitive page (banking/admin) = High
  - XSS + CSRF token theft = CSRF bypass on critical action
  - XSS + service worker = persistent XSS across pages
  - XSS + credential theft via fake login form = ATO

## WEB3 SMART CONTRACT AUDIT
- file: `web3-audit-abh.md`  (17935 bytes)
- sections: PRE-DIVE KILL SIGNALS (check BEFORE any code review) | THE ONE RULE | 1. ACCOUNTING STATE DESYNCHRONIZATION | What It Is | Root Cause Patterns | Grep Patterns | 2. ACCESS CONTROL | Variant 1: Missing Modifier on Sibling Function | Variant 2: Wrong Check (Existence vs Ownership) | Variant 3: Silent Modifier (if vs require) | Variant 4: Uninitialized Proxy | Grep Patterns

## Windows/MSYS tool-invocation + toolchain validation recipe
- file: `windows-toolchain-validation-and-msys.md`  (6113 bytes)
- sections: 1. The two MSYS path-conversion traps | (a) HTTP paths passed as CLI args → bogus hostname | (b) File paths inside scripts → "file not found" for real files | 2. Local-target validation harness (do this before any "tools work" claim) | 3. Reporting the validation result

## Writeup Index — Bug Bounty Case Studies
- file: `writeup-index.md`  (1212 bytes)
- sections: Web2 Writeups | Web3/DeFi Writeups | Smart Contract Patterns | Attack Chains (Cross-Vector)
  - Bitso 2026: auth bypass + IDOR chain → $5K
  - Kinsta 2026: SSRF → cloud metadata → RCE
  - NASA VDP: info disclosure → credential leak
  - Neony Exchange: race condition → double-spend
  - Adafruit 2026: API key leak → account takeover
  - Fireblocks 2026: session hijack → fund access
  - Crowdstrike: OAuth misconfig → token theft
  - LayerZero OFT: message replay → cross-chain attack
  - Paxos Cantina: oracle manipulation → price exploit
  - Flash loan + oracle manipulation chain
  - SSRF → cloud metadata → IAM role → S3 access
  - XSS → session steal → privilege escalation → admin
  - Race condition → balance manipulation → fund extraction
  - GraphQL introspection → hidden mutation → mass assignment

## XSS Payloads - Curated from exploit-cookbook + security-arsenal
- file: `xss-payloads.txt`  (2089 bytes)

