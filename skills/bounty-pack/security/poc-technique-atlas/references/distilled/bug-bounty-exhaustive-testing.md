# Distilled techniques — security/bug-bounty-exhaustive-testing

Source: `~/.chiper/skills/bounty-pack/skills/security/bug-bounty-exhaustive-testing/references`  (20 files)

One card per file: title, section headings, technique bullets.

## Akamai-fronted estate: browser-driven audit recipe (Kmart Group VDP, 2026-09-29/30)
- file: `akamai-estate-browser-driven-audit.md`  (10960 bytes)
- sections: 1. Tool coverage matrix (the honest report shape) | 2. Why the browser is the only transport | 3. Technique stack that produced all real coverage | 4. Results (both targets) — for calibrating expectations | 5. Pitfalls that cost time | 6. target.com.au surface map (SAP Commerce / Hybris) — the part that took longest to learn | 7. Discovery techniques that produced the map above | 8. Form POST / document-navigation endpoints are invisible to XHR capture
  - `curl` with a full Chrome header set → 403; the block is TLS/JA3 + IP reputation, not headers.
  - Bundle mining** for endpoint paths and GraphQL documents (`/uir-*/api/*`, `/rest/v2/...`,
  - Persisted-query (APQ) whitelist**: `/uir-bff/graphql?operationName=Product&extensions=
  - Auth-bypass matrix**: 6 methods × 8 headers (X-Original-URL, X-Rewrite-URL, X-Forwarded-For,
  - Cross-origin proof harness** from a local attacker origin (CSRF + CORS): see
  - kmart.com.au: GraphQL reachable after the CPR bypass; introspection disabled; `me` resolves

## Browser-Based Bugcrowd Access via computer_use
- file: `browser-bugcrowd-access.md`  (3860 bytes)
- sections: When to Use | Workflow (Phase 0A Alternative) | Step 1: Verify Browser Session | Step 2: Navigate to Engagement | Step 3: Extract Scope | Step 4: Explore Target Dashboard | Step 5: Extract API Endpoints via Network Tab | Step 6: Check Application Tab for Tokens | Pitfalls | SPA Catch-All Detection | Error Disclosure Pattern | Subdomain Takeover Detection

## Certinia (FinancialForce) Case Study — Well-Hardened Target
- file: `certinia-case-study.md`  (3842 bytes)
- sections: Target Profile | Infrastructure | Attack Surface | Tools Executed (with evidence) | Findings (all weak) | What Was Tested (30 vectors) | Why Zero Bounty-Worthy Findings | Lessons for Future Sessions
  - Auth:** Cloudflare Access + Google IAP + Okta SSO + Salesforce OAuth
  - Cloudflare Access: 73+ hosts (302 redirect to login)
  - Google IAP: 30+ itops hosts (302 redirect to Google OAuth)
  - truly accessible endpoints (200, no auth redirect)
  - HMRC API (Salesforce OAuth flow)
  - Okta SSO** centralizes auth — no bypass found
  - No test accounts** — cannot test authenticated endpoints (IDOR, auth bypass, business logic)
  - CORS on redirect pages ≠ exploitable CORS** — check if data is actually accessible

## CleanShot Case Study (Sep 2026)
- file: `cleanshot-case-study.md`  (4481 bytes)
- sections: Infrastructure | Key Recon Findings | Critical Information Disclosure: `__NEXT_DATA__` | docs.cleanshot.com Cookies Exposed | Lessons Learned | Defense Mechanisms Observed | SPA Catch-All Behavior (per platform) | Well-Hardened Target Indicators (present on CleanShot)
  - subfinder discovered 15 subdomains including 4 staging/dev/sandbox (all 403)
  - "Legit check endpoint" (id: 5E8071C48769uN) — separate internal service
  - Attacker mindset vs checklist** — Agent ran 1 payload per attack class (30 total). Real attackers run 10+ payloads per class (300+ total). User: "kamu kebanyakan limitasi saat kerja"
  - CloudFront WAF blocks staging/dev/sandbox (403)
  - Apple OAuth only (no email/password signup)
  - [x] CloudFront WAF on staging/dev/sandbox
  - [x] No GraphQL, no WebSocket, no debug tools
  - [x] Apple OAuth only (no email signup = no account enumeration)

## CORS Multi-Subdomain Testing — Lessons Learned
- file: `cors-multisubdomain-testing.md`  (5148 bytes)
- sections: The Rule | Discovery → Testing Flow | Real-World Findings | turboflow.xyz (2026-09) — Updated Sep 18 | SPA vs Real API Detection | Auth Header Reflection | Severity Matrix | PoC Template | Fix Recommendation
  - `api`, `api2`, `api4`, `apis` → CORS reflect origin but **NO credentials header** → NOT exploitable for token theft
  - `api3` → CORS reflect origin + `credentials: true` + proper OPTIONS preflight** → CRITICAL (full JWT theft)

## CVE Scanner False Positive Verification
- file: `cve-scanner-false-positives.md`  (5075 bytes)
- sections: The Pattern | NASA VDP Case Study (2026-09-20) | Findings from nuclei scan (4h58m, 6564 templates, 8 targets): | Why Each Was False Positive: | Verification Checklist (USE FOR EVERY CVE MATCH): | Rule: CVE Match ≠ Vulnerability | SPA Catch-All Routing (Additional False Positive Source) | Nuclei Scan Timing Expectations | Common VDP False Positive Patterns (Add to List) | References
  - No password-protected content to exploit → impact = NUL
  - Not a leak — data is already public → impact = NUL
  - `images.nasa.gov/debug` → HTTP 200 (SPA catch-all, not exposed debug endpoint)

## DeFi Event Contract / Binary Option Audit Guide
- file: `defi-event-contract-audit.md`  (2464 bytes)
- sections: Architecture Discovery | Step 1: Verify On-Chain vs Off-Chain | Step 2: Map Trading Flow | Step 3: Price Feed Analysis | Step 4: Settlement Mechanism Analysis | Step 5: Return Rate Analysis | Common Vulnerability Classes | References
  - Markets as "on-chain perpetuals"
  - SDK reveals: REST API + JWT auth + server-side matching
  - API Abuse — from leaked SDK (bots, enumeration, rate limit bypass)
  - Business Logic — negative/zero amounts, leverage bypass
  - Also read: `jwt-attack-suite.md`

## JWT Attack Suite — Crypto Platform Results
- file: `jwt-attack-suite.md`  (2036 bytes)
- sections: Tests Conducted | 1. `none` Algorithm | 2. Leaked Keys as HS256 Secret | 3. Algorithm Confusion (RS256→HS256) | 4. Common Secrets | Error Code Interpretation | Internal Error Leak | Backend Behavior Summary | Takeaway
  - Validates JWT structure (3 segments) BEFORE signature check
  - Ignores `alg` header — uses configured algorithm
  - Same error for all JWT attacks

## Magic Labs (magiclabs-mbb-og) — Well-Hardened Target Case Study
- file: `magic-labs-case-study.md`  (4526 bytes)
- sections: Infrastructure | Scope | Recon Results | Test Matrix (23 Vectors) | Candidates Evaluated (8) | Key Lessons | Comparison: Well-Hardened vs Exploitable
  - Cloudflare WAF is effective.** All API-level testing blocked. Cannot test IDOR, injection, auth bypass without authenticated session.
  - Missing security headers without injection point = informational.** Cannot leverage CSP missing without XSS vector.
  - Status page infrastructure leak is expected.** Atlassian Statuspage CORS: * is standard behavior.

## NASA VDP Case Study — Exhaustive Testing, Zero Bounty Findings
- file: `nasa-vdp-case-study.md`  (4776 bytes)
- sections: Recon Scale | Tools Executed (with terminal output proof) | Infrastructure | Candidates Evaluated & Dropped | Honest Conclusion | Lessons for Future VDP Audits

## NASA VDP Audit — Tool Execution vs Curl Illusion
- file: `nasa-vdp-tool-execution-lesson.md`  (4714 bytes)
- sections: The Core Problem | What "Exhaustive" Actually Requires | Tool Execution (MANDATORY — not optional) | curl ≠ Vector Testing | Scope Coverage | What Should Have Been Done | Phase 1: Recon (actual) | Phase 2: Fuzzing (actual) | Phase 3: Targeted (actual) | The "Zero Findings" Illusion | NASA VDP Specific Lessons | Quick Exhaustion Verification
  - dalfox XSS scans

## Neon (neon.tech) — Well-Hardened SaaS Case Study (Sep 2026)
- file: `neon-case-study.md`  (6132 bytes)
- sections: Target | Attack Surface | Tools Executed (15 tools, real terminal output) | New Tools From This Session | CVE Exploits Tested (6 total, Real Tools) | CVE-2025-29927 Test Method (Next.js Middleware Bypass) | Port 8080 Direct Access (Defense-in-Depth Working) | POC-COMPACT: 2,223 Dirs, 0 Files | User Correction: "Jgn kasih hasil teoritis" | What "Exhausted" Looks Like on a Well-Hardened SaaS | Key Lesson | Neon-Specific Infrastructure Notes
  - CVE-2025-29927** — Next.js middleware bypass via `x-middleware-subrequest` header (test method below)
  - CVE-2025-55182 (React2Shell RCE CVSS 10.0)** — Cloned exploit repo, installed deps, ran scan → NOT VULNERABLE (React patched)
  - CVE-2025-29927 (Next.js middleware bypass)** — `x-middleware-subrequest: true` header test → NOT VULNERABLE (neon.com on Vercel, patched)
  - CVE-2025-59470 (PostgreSQL cmd inject)** — POC-COMPACT dir empty (no exploit code) → NOT APPLICABLE
  - CVE-2026-11102 (OAuth2 implicit grant hijack)** — POC-COMPACT dir empty → NOT APPLICABLE
  - Informational (version disclosure, no exploit chain)
  - Keycloak properly validates redirect_uri (15 bypass techniques failed)
  - No dangling CNAMEs for subdomain takeover
  - Superset: v5.0.0 (config leak by design)

## Reference Loader — On-Demand Reference File Loading
- file: `reference-loader.md`  (2705 bytes)
- sections: Purpose | Loading Rules | Per-Vector Reference Map | Loading Pattern
  - After reading, apply the technique to the target
  - NEVER reload a reference "to check" — use read_file instead

## SQL Injection - Authentication Bypass Payloads
- file: `sqli-payloads.txt`  (2132 bytes)

## SSRF Payloads - Curated from exploit-cookbook + security-arsenal
- file: `ssrf-payloads.txt`  (1860 bytes)

## Tool Execution Pitfalls — Windows + Hermes
- file: `tool-execution-pitfalls.md`  (5390 bytes)
- sections: nuclei | ffuf | subfinder | katana | wscat / WebSocket | Python ssl.wrap_socket | GOPATH on Windows | Context Budget Exhaustion During Audits | Process Polling Anti-Pattern
  - If still running, set a reminder and do MORE other work

## Turnkey.com — Well-Hardened Target Case Study + Severity Inflation Lesson
- file: `turnkey-case-study.md`  (6623 bytes)
- sections: Infrastructure | Test Matrix (30 Vectors — All Completed) | Candidates Evaluated (6 — All Dropped or INFO) | Key Lesson: Severity Inflation | Well-Hardened Target Pattern
  - P-256/stamp-based auth (not just JWT)

## WordPress REST API Attack Surface — NASA VDP Patterns
- file: `wordpress-rest-api-attack-surface.md`  (6029 bytes)
- sections: WordPress Custom Post Types via REST API | Discovery | NASA Findings (oig.nasa.gov) | Severity Assessment | Custom Plugin Namespaces | Redirection Plugin Testing | GravityForms Endpoints | Key WordPress Endpoints to Test | WordPress VIP POST Route Enumeration | Systematic Enumeration | NASA Route Findings | NASA Custom Namespace Inventory
  - nccs.nasa.gov:** 83 POST routes — `/redirection/v1/redirect` (create redirects), `/create-block-theme/v1/*` (theme management), `/batch/v1` (batch operations)

## XSS Payloads - Curated from exploit-cookbook + security-arsenal
- file: `xss-payloads.txt`  (2089 bytes)

## Zowonen Case Study (2026-09-21)
- file: `zowonen-case-study.md`  (2925 bytes)
- sections: Target | What Happened | Findings (7 total, 2 Low, 5 Info) | User Corrections (3x pushback) | False Positive Lesson | Key Takeaways
  - Race condition: NOT TESTED until user pushed back (Python threading)
  - Exploit-cookbook reference files: NOT LOADED until user pushed back
  - CSS Source Map Leak (Info) - cp.css.map accessible, 701KB, 22 SCSS files
  - Run ALL tools in the mandatory list.** dalfox, arjun, race-condition are not optional.
  - Load exploit-cookbook reference files.** The 6 disclosure refs contain real-world patterns.
  - NoSQLi false positive:** Always check if page SIZE changes with payload. Same size = not vulnerable.

