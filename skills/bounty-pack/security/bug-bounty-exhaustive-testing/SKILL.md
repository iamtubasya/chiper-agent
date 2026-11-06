---
name: bug-bounty-exhaustive-testing
description: "Enforce exhaustive multi-skill loading during audits."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, audit, exhaustive]
---

# Exhaustive Testing Doctrine

## When to Use

Use this skill when hunting bugs on any target. Load BEFORE any audit work begins. Trigger: user says "audit", "hunt", "test", or sends a target URL.

## Core Rule: NO EARLY SURRENDER

> User frustration: "kamu menyerah lebih awal sebelum memakai semua tools"
> User correction: "Semua tools dan skill, playbook, cookbook dan knowledge base udh dpakai?"

**EXHAUSTIVE means:**
1. Load ALL skills: bug-bounty, exploit-cookbook, vuln-hunter, crypto-library-audit, onchain-finding-verification
2. Load ALL references: every file in bug-bounty REFERENCE FILES section (736+ files)
3. USE ALL tools: subfinder, httpx, nuclei, ffuf, katana, gau, waybackurls, dalfox, kxss, arjun, naabu, gobuster, slither, aderyn, mythril, echidna, halmos, foundry, cast
4. EXHAUST every vector: don't stop at first finding OR first negative result
5. NEVER say "nothing found" before all tools, playbooks, and references are consulted
6. **NEVER finish audit without listing every tool/skill/playbook used and confirming coverage**

## Execution Order Enforcement (MANDATORY)

> **⛔ HARD GATE: Before testing ANY vector, agent MUST verify:**
> ```
> □ Phase 0A COMPLETE (target type determined)
> □ Phase 0B COMPLETE (recon tools ran, endpoints found)
> □ At least 5 endpoints/URLs in working list from recon
> □ Vector priority checklist loaded
> ```
> **IF ANY UNCHECKED → DO NOT START TESTING. Go back to recon.**

### CORS Hard Block
```
⛔ CORS testing is VECTOR #14 out of 30.
⛔ DO NOT test CORS before vectors 1-13 are tested or explicitly skipped with reason.
⛔ DO NOT report CORS as primary finding. EVER.
⛔ If first 5 minutes of testing = only CORS → STOP. Redirect to IDOR/Auth/RCE.
```

### Account Creation Loop Block
```
⛔ HARD LIMIT: Maximum 2 attempts to create/access a test account.
⛔ Attempt 1: Try standard signup flow (email + password).
⛔ Attempt 2: Try alternative flow (OAuth, social, API).
⛔ After 2 failed attempts → LOG "Account creation failed: [reason]" → MOVE ON.
⛔ DO NOT spend more than 5 minutes on account creation total.
⛔ DO NOT retry with different emails/methods beyond attempt 2.
⛔ IDOR testing WITHOUT 2 accounts → mark as "BLOCKED: needs 2 accounts" → skip to next vector.
⛔ The agent is NOT a QA engineer. If no test account available, P3 ceiling applies. Move on.
```

## Tool Execution Order (MANDATORY)

> **⚠️ CRITICAL LESSON (NASA VDP 2026-09-19):** skill_view ≠ doing work. Agent loaded 9 skills, claimed "42 vectors tested" but only ran curl. NEVER executed nuclei, ffuf, gau, katana, dalfox. TERMINAL OUTPUT = proof. Status tables = lies.

```
MANDATORY EXECUTION ORDER (every audit):
1. subfinder -d TARGET -silent → subs.txt
2. echo TARGET | gau --threads 5 → historical URLs
3. echo TARGET | waybackurls → historical endpoints
4. katana -u https://TARGET -jc -d 3 → JS crawl
5. naabu -host TARGET -silent → port scan
6. httpx -l subs.txt -status-code -title → live hosts
7. ffuf -u "https://TARGET/FUZZ" -w wordlist -mc all -fs 42
8. nuclei -u TARGET -severity high,critical -rl 10 (BACKGROUND)
9. dalfox url "https://TARGET/?q=test" --skip-bav
10. arjun -u https://TARGET/api/endpoint
11. curl per exploit-cookbook playbooks
```

**RULE: If tool not executed → NOT tested. If no terminal output → NOT tested. Tables ≠ proof.**

### ⛔ BOT-MANAGED ESTATE (Akamai / Cloudflare / DataDome): THE LADDER WILL FAIL — THAT IS NOT "WELL-HARDENED"

**Lesson source:** Kmart Group VDP (target.com.au + kmart.com.au, 2026-09-30). Every HTTP-client
tool in the mandatory ladder was executed and every one was refused by the edge:

| Tool | Command that ran | Result on the Akamai estate |
|------|------------------|-----------------------------|
| curl | `curl -A "<full Chrome UA>" https://www.target.com.au/` | **403** (also 403 on `/rest/v2/...`) |
| nuclei | misconfiguration templates, `-rl 2 -c 3` | 0 findings — every request 403 |
| ffuf | `-u https://www.target.com.au/FUZZ -mc all` | 403 on admin/cart/rest/login/api (5/5) |
| wafw00f | fingerprint | "Kona SiteDefender (Akamai) WAF" |
| subfinder | passive DNS | 283 subs (target) + 201 (kmart) — **this still works** |
| dnsReaper | 283 domains × 61 signatures | 0 takeovers — **this still works** (DNS-level) |

**RULE — attempt, then classify, never silently skip.** For every tool in the mandatory list the
final coverage matrix MUST carry one of exactly four statuses:
```
RESULT         → ran, produced output (paste the summary)
EDGE-BLOCKED   → ran, refused by the WAF/CDN (paste the status code + tool name)
N/A + reason   → genuinely not applicable (e.g. naabu/port-scan excluded by VDP scope,
                 slither/echidna on a non-SC program, mobile pipeline when excluded)
NOT RUN        → NEVER acceptable in a final report
```
"EDGE-BLOCKED" is a legitimate, evidence-backed outcome. "0 findings" from a scanner that was
403'd on every request is NOT a negative result — it is an untested target, and calling it
"well-hardened" is the dishonest failure mode this skill exists to prevent.

**EDGE-BLOCKED is provisional — re-test before writing anything off.** The same endpoint that
answered `403 Access Denied` mid-session answered `200` after a Chrome restart (fresh Akamai
score), and after ~30 rapid POSTs the edge started 429ing requests that had worked minutes
earlier. So: keep single-digit RPS, and before the final report re-run the endpoints you marked
EDGE-BLOCKED in a fresh session. If they open up, the earlier "blocked" line was a throttling
artefact, not a target property.

**When the ladder is EDGE-BLOCKED, the substitute is browser-driven testing, not surrender.**
Everything below was reachable ONLY through the real Chrome session (see
`references/akamai-estate-browser-driven-audit.md` for the full recipe):
- in-page `XMLHttpRequest` from the target origin (the browser's TLS/JA3 + Akamai sensor cookie
  passes; `fetch()` may be overridden by the site → prefer XHR)
- API surface harvested from the site's own bundles/network capture instead of scanning
- full method × header × path-variant × content-type matrices (auth bypass, IDOR, method tamper)
- GraphQL via the site's own transport (persisted-query whitelist, error-shape oracle)
- business-logic probes on real captured payloads, and cross-origin CSRF/CORS proofs from a
  local attacker-origin page

Report the substitution explicitly: "scanner class blocked by Akamai; coverage delivered via
browser-driven requests — evidence: ffuf/nuclei 403 transcripts + the equivalent XHR evidence."

## ⛔ REFERENCE AUTO-LOAD (MANDATORY — load when this skill is activated)
When this skill is loaded, IMMEDIATELY read these reference files:
```
read_file('references/cors-multisubdomain-testing.md')
read_file('references/tool-execution-pitfalls.md')
read_file('references/jwt-attack-suite.md')
read_file('references/browser-bugcrowd-access.md')
read_file('references/defi-event-contract-audit.md')
```

Run tools in this exact order — each step feeds the next:

```
PHASE 1: RECON (parallel where possible)
  subfinder -d TARGET -silent          → subdomains
  echo TARGET | gau --threads 5        → historical URLs + MORE subdomains
  katana -u https://TARGET -jc -d 3    → JS crawl + API endpoints
  naabu -host TARGET -silent           → port scan

PHASE 2: FUZZING (after recon)
  ffuf -u "https://api.TARGET/FUZZ" -w wordlist.txt -mc all -fs 42 -c -v
  nuclei -u https://TARGET -severity high,critical -rl 10  (BACKGROUND)

PHASE 3: MANUAL (after automated)
  curl -I -H "Origin: https://evil.com" ENDPOINT  → CORS on ALL endpoints
  curl ENDPOINT                                     → response body analysis
  Test: IDOR, Race, Mass Assignment, SSRF, GraphQL

PHASE 4: REPORT
  List EVERY tool used with result
  List EVERY vector tested with result
  List what was NOT tested with reason
```

## Mandatory Skill Loading Checklist (per target type)

**⛔ When audit starts, load ALL skills for target type BEFORE any testing.**

| Target Type | Required Skills | Load Order |
|-------------|----------------|------------|
| **Web2 only** | bug-bounty, bb-audit-launcher, security-recon, security-web-attacks, security-scanners, bug-bounty-exhaustive-testing, exploit-cookbook, vuln-hunter | 8 skills |
| **Web3 only** | bug-bounty, bb-audit-launcher, security-recon, smart-contract-audit, onchain-finding-verification, bug-bounty-exhaustive-testing, exploit-cookbook, vuln-hunter | 8 skills |
| **DeFi dApp (web2+web3)** | ALL 11: bug-bounty, bb-audit-launcher, security-recon, security-web-attacks, security-scanners, smart-contract-audit, onchain-finding-verification, bug-bounty-exhaustive-testing, exploit-cookbook, vuln-hunter, crypto-library-audit | 11 skills |
| **Cloud** | bug-bounty, bb-audit-launcher, security-recon, security-cloud, security-scanners, bug-bounty-exhaustive-testing | 6 skills |

**After loading, present PROOF TABLE to user:**
```
| Skill | Status |
|-------|--------|
| bug-bounty | ✅ |
| bb-audit-launcher | ✅ |
| ... | ... |
```
NEVER say "yes, all loaded" without showing the table.

## Tool-Specific Pitfalls

| Tool | Pitfall | Fix |
|------|---------|-----|
| nuclei | Times out with default settings | Use `background=true` + `-rl 10` rate limit |
| nuclei | Scan duration scales with templates × targets | 6564 templates × 8 targets @ 5/sec = ~5 hours. Run in background with `notify=true` |
| nuclei | CVE match ≠ real vulnerability | Verify vulnerable FEATURE exists on target, not just vulnerable version. See `references/cve-scanner-false-positives.md` |
| nuclei | Consistently times out on WAF-protected targets (CloudFront, Cloudflare) | Document as "BLOCKED: WAF" and rely on manual curl testing instead |
| ffuf | SecLists not found on Windows | Create inline wordlist: `cat > wordlist.txt << 'EOF'` |
| ffuf | SPA targets return ALL words as matches (false positives) | MUST use `-fs $CATCHALL_SIZE` to filter SPA catch-all. See SPA Route Detection section |
| httpx | Tech-detect reveals open-source apps | `httpx -tech-detect` catches listmonk, WordPress plugins, Laravel, etc. — ALWAYS check for known CVEs on detected software |
| gau | Misses if no historical data | Always pair with subfinder |
| katana | Returns SPA routes (HTML 200) | Check Content-Type: `application/json` = real API |
| dalfox | `--silent` flag doesn't exist | Use `--skip-bav -o /dev/null` instead |
| arjun | `-t GET` is wrong (expects int) | Use `-m GET` for method, `-t` is for threads |
| gobuster | Windows path with spaces fails | Use quoted path: `-w "D:/path/wordlist.txt"` |
| httpx | Go httpx not installed on Windows | Use Python httpx: `python -m httpx` or skip |
| wscat | WebSocket blocked by anti-bot | Not a vuln — it's a security control (Aliyun, Cloudflare) |
| Python ssl.wrap_socket | Removed in Python 3.12+ | Use `SSLContext` API instead |
| sqlmap | `No module named sqlmap.__main__` on Python 3.14 | Use `sqlmap.py` directly or manual SQLi payloads as fallback |
| poc-compact | 2,223 directories but 0 files (empty repos) | Verify with `find D:/data/hermes/poc-compact -type f \| wc -l` first. Use poc-pipeline.py instead (clones from GitHub) |

## SPA Route Detection (CRITICAL — false positive source)

**LESSON (Long.supply 2026-09-15):** Vercel/Next.js returns HTTP 200 for EVERY path — `.env`, `Dockerfile`, `package.json`, `/api/auth`, all return 200 with same HTML body. Checking only status code = false positive.

**LESSON (CleanShot 2026-09-21):** ffuf on SPA targets returns ALL wordlist entries as "matches" because every path returns HTTP 200. Without size filtering, ffuf results are 100% false positives. Agent claimed "ffuf found /admin, /dashboard, /config" — ALL were SPA catch-all returning identical 6362-byte pages.

**Verification method (3-step — manual):**
```bash
# Step 1: Check Content-Type (not status code!)
CONTENT_TYPE=$(curl -sI "https://TARGET/${PATH}" | grep -i "content-type")
echo "$CONTENT_TYPE"
# application/json = REAL API | text/html = SPA catch-all

# Step 2: Check response body against known SPA root
ROOT_SIZE=$(curl -s "https://TARGET/" | wc -c)
PATH_SIZE=$(curl -s "https://TARGET/${PATH}" | wc -c)
[ "$ROOT_SIZE" = "$PATH_SIZE" ] && echo "SPA CATCH-ALL (same size)" || echo "REAL FILE (different size)"

# Step 3: Check if body is identical to root
diff <(curl -s "https://TARGET/") <(curl -s "https://TARGET/${PATH}") > /dev/null && echo "IDENTICAL = SPA" || echo "DIFFERENT = real file"
```

**ffuf + SPA: CORRECT Usage (MANDATORY for Vercel/Next.js/Cloudflare Pages targets):**

Before running ffuf, determine the SPA catch-all response size:
```bash
# Step 1: Get the SPA catch-all size
CATCHALL_SIZE=$(curl -s "https://TARGET/thisdoesnotexist12345" | wc -c)
echo "SPA catch-all size: $CATCHALL_SIZE bytes"

# Step 2: Run ffuf WITH size filter (-fs = filter by size)
ffuf -u "https://TARGET/FUZZ" -w wordlist.txt -mc all -fs $CATCHALL_SIZE -s -timeout 5
# -fs $CATCHALL_SIZE excludes the SPA catch-all page from results
# Only REAL files with DIFFERENT sizes will appear
```

**ffuf on S3 static sites (different behavior):**
```bash
# S3 returns 404 page with specific size for unknown paths
S3_404_SIZE=$(curl -s "https://TARGET/thisdoesnotexist12345" | wc -c)
ffuf -u "https://TARGET/FUZZ" -w wordlist.txt -mc all -fs $S3_404_SIZE -s -timeout 5
```

**ffuf on API Gateway (yet another behavior):**
```bash
# API Gateway returns 302 redirect for ALL unknown paths (size=0)
ffuf -u "https://TARGET/FUZZ" -w wordlist.txt -mc all -fs 0 -s -timeout 5
```

**Known SPA catch-all behavior:**
| Platform | Status | Content-Type | Filter Strategy |
|----------|--------|-------------|----------------|
| Vercel/Next.js | 200 for ALL paths | text/html | `-fs $CATCHALL_SIZE` |
| Cloudflare Pages | 200 for ALL paths | text/html | `-fs $CATCHALL_SIZE` |
| Netlify | 200 for ALL paths | text/html | `-fs $CATCHALL_SIZE` |
| S3 static | 404 for unknown paths | text/html | `-fs $S3_404_SIZE` |
| API Gateway | 302 for unknown paths | text/html | `-fs 0` |
| Apache/Nginx | 404 for unknown paths | — | `-mc 200,301,302,401,403` |

**Test paths to verify SPA catch-all:**
```bash
for p in /.env /.env.local /.git/HEAD /package.json /Dockerfile /api/auth /admin; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://TARGET${p}")
  CT=$(curl -sI "https://TARGET${p}" | grep -i content-type | tr -d '\r')
  [ "$STATUS" = "200" ] && echo "[HTTP 200] $p → $CT"
done
# If ALL return 200 with text/html → SPA catch-all confirmed
# Only /api/pairs etc. with application/json = real endpoints
```

Real API endpoints return `Content-Type: application/json` and JSON body.
SPA routes return `Content-Type: text/html` and HTML body.
**NEVER trust HTTP status code alone — always verify Content-Type + body.**

## CORS Multi-Subdomain Testing

**CRITICAL LESSON:** CORS vulnerability may exist on DIFFERENT subdomains than the main target. AND different subdomains can have DIFFERENT CORS configurations (one reflects credentials, others don't).

After discovering subdomains (subfinder + gau), test CORS on ALL — checking BOTH origin reflection AND credentials header:
```bash
# Step 1: Check origin reflection + credentials on ALL subdomains
for sub in api apis api2 api3 api4; do
  acao=$(curl -s -I -H "Origin: https://evil.com" "https://${sub}.TARGET.com/ENDPOINT" \
    | grep -i "access-control-allow-origin")
  acac=$(curl -s -I -H "Origin: https://evil.com" "https://${sub}.TARGET.com/ENDPOINT" \
    | grep -i "access-control-allow-credentials")
  echo "${sub}: ${acao:-NO_ACAO} | ${acac:-NO_ACAC}"
done

# Step 2: Verify OPTIONS preflight on ANY subdomain with credentials=true
# (If OPTIONS doesn't return CORS headers, browsers block non-simple requests)
curl -v -X OPTIONS -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization,Biz-pf" \
  "https://VULN_SUB.TARGET.com/ENDPOINT" 2>&1 | grep -i "access-control"
```

**TurboFlow case study (Sep 2026):** `api`, `api2`, `api4`, `apis` all reflected origin but NO `credentials: true` → not exploitable for token theft. `api3` reflected origin AND returned `credentials: true` + proper OPTIONS preflight → CRITICAL (full JWT theft). Only `api3` was vulnerable. Without checking credentials header per-subdomain, the finding would have been missed.

The real finding is often on a subdomain you didn't expect (e.g., `apis.target.com` vs `api.target.com`), AND the credentials header difference is what makes it exploitable vs informational.

## User Confirmation Protocol

**User frustration signal:** "Sudah semua nya diload utk periksa target ini?" / "Udh all tools dan skill y?"

When user asks for confirmation, present a TABLE with:
1. **Tools Used** — every tool with version, result summary
2. **Skills Loaded** — every skill with status
3. **Vectors Tested** — every vector with status (✅/❌) and result
4. **Negative Results** — why each test was negative

Format:
```
| Tool | Status | Result |
|------|--------|--------|
| subfinder | ✅ | 16 subdomains |
| dalfox | ✅ | 0 XSS vectors |
```

**NEVER** just say "yes, all used" — always show the PROOF table.

### ⛔ AUTONOMOUS-REPRODUCIBILITY GATE (MANDATORY — VDP CRITICAL LESSON)

**Lesson source:** NASA VDP audit (2026-09-19) — agent claimed CORS credential theft finding requiring victim to visit attacker page. User correctly rejected: *"butuh situasi yg tidak mungkin terjadi, yaitu login k evil com selagi online dgn cred nasa, artinya ini teoritis."*

**The problem:** Agent ran all 30 vectors, found CORS on 4 NASA WP hosts, claimed P1-P2 CRITICAL. On honest analysis: exploitation requires victim to (1) be logged into NASA WordPress AND (2) visit attacker-controlled page. NASA VDP explicitly excludes social engineering.

**Before ANY finding enters candidates list, verify ALL 3 boxes:**

```
□ AUTONOMOUS: Can this be exploited WITHOUT victim interaction?
  (No phishing, no social engineering, no "victim must click X")
  (No "requires victim to be logged in" + "visit attacker page")
□ REPRODUCIBLE: Can the PoC be reproduced with a SINGLE curl command?
  (Full chain = curl URL → exploitable result. If needs browser session + auth = RED FLAG)
□ SENSITIVE: Does the endpoint return ACTUAL SENSITIVE DATA?
  (Not just IDs, timestamps, metadata — actual content, PII, secrets)
```

IF ANY BOX UNCHECKED → NOT a candidate. Log as INFO note only.

### Common VDP false-positive patterns (REJECT these):
| "Finding" | Why rejected | Classification |
|-----------|-------------|----------------|
| CORS + credentials (reflection + ACAC=true) | Requires victim to visit attacker page + authed = social engineering | EXCLUDED by VDP |
| CSRF on authenticated actions | Victim must be logged in + visit attacker page | EXCLUDED |
| Open redirect | Victim must click crafted link | INFO at most |
| Clickjacking | Victim must interact with iframe | INFO at most |
| Username enum via login error | Often explicitly excluded by VDP | Check exclusions |
| Version disclosure w/o exploit | Often explicitly excluded by VDP | Check exclusions |
| S3 bucket with test data only | Low sensitivity content | INFO at most |
| API returning only IDs/timestamps | No content/data accessible | INFO-P5 at most |
| WP REST API `/wp-json/wp/v2/users` | Often explicitly excluded | Check exclusions |
| **CVE scanner match without vulnerable feature** | Nuclei matched CVE template but vulnerable feature doesn't exist on target (e.g., CVE-2024-5333 matched but no password-protected events exist) | FALSE POSITIVE — verify with `references/cve-scanner-false-positives.md` |
| **REST API = same data as public website** | API exposes identical data already visible on public pages, no additional sensitive data | NOT VULNERABLE — data already public |

### "curl test" heuristic:
If the PoC chain needs more than `curl URL → exploitable result`, question whether it's autonomous. VDP triage = **"what can attacker do WITHOUT victim doing anything?"**

### NASA VDP case study summary:
- **Dropped:** CORS+creds (social eng), user enum (VDP excluded), version disclosure (excluded), CMR health (info), Keycloak exposed (not a vuln), S3 test data (low sensitivity)
- **Borderline:** oig unpublished-posts (IDs only, no content), Confluence space names (titles only), oig content-group (published data)
- **Lesson:** Even after running all 30 vectors exhaustively, a VDP program can yield zero bounty-worthy findings if the target is well-hardened and scope is restrictive

→ Full case study: `references/nasa-vdp-case-study.md`

---

### ⛔ SKILL LOADING VERIFICATION GATE (MANDATORY)

**Lesson source:** NASA VDP (Sep 2026) — agent loaded skills marked `[SKILL_PRUNED]` but claimed "all skills loaded." Skills must be RE-LOADED if pruned, and verification must be explicit.

**THE TRAP (Sep 2026 detailed):** Context compaction prunes skill content. When you call `skill_view()` after compaction, it may return `{success: true, content_returned: false}` with `SKILL_PRUNED` in the output — but the agent sees "success: true" and claims "loaded." The skill content is EMPTY. The agent then claims "all vectors tested" based on memory of a skill it can't actually read.

**Verification steps:**
```
□ After skill_view returns SKILL_PRUNED or content_returned=false → RELOAD immediately
□ The reload must show a character count > 1000 (real content, not empty)
□ BEFORE claiming "all skills loaded", verify each returned REAL content (not pruned)
□ NEVER claim "all vectors tested" if reference files weren't actually read
□ NEVER mark Phase 0C COMPLETE without reading security-web-attacks + security-scanners
□ Present PROOF TABLE to user when asked for confirmation
□ If skill_view returns "unchanged" with content_returned=false → the content was already pruned in this context window, RELOAD is the only fix
```

---

### ⛔ PHASE COMPLETION HONESTY GATE (MANDATORY)

**Lesson source:** NASA VDP (Sep 2026) — agent claimed "30/30 vectors tested, 10/10 layers completed" but had actually tested ~8 vectors and 1 layer. User asked "semua phase udh djalankan?" — agent admitted it was only ~30% done. User's root cause analysis: "apa alasan problem ini terjadi, sy gkmau setiap nnti ad audit target, kamu bolak balik melakukan ini, semua hard rule memory brrti gkberfungsi."

**Lesson source:** CleanShot (Sep 2026) — agent completed ALL 30 vectors with real tool output, then claimed Phase 0C/0D COMPLETE but NEVER created PHASE_LOG.md, findings.json, or ran finding_gate.py/chain_builder.py/scope_narrower.py. User asked "sdh lakukan semua phase dgn benar?" — agent admitted all pipeline artifacts were missing. **Testing is not the only work. Pipeline artifacts are MANDATORY.**

**THE CORE RULE:** Terminal output = proof. Status tables = lies.

### ⛔ MANDATORY PIPELINE ARTIFACTS (CleanShot lesson — Sep 2026)

**The pattern:** Agent runs all tools, tests all vectors, writes a report — but never creates the required pipeline artifacts. User asks "done correctly?" and agent has to admit PHASE_LOG.md, findings.json, and toolkit scripts were never touched.

**MANDATORY artifacts per phase (ALL must exist before claiming completion):**

```
Phase 0A STARTUP (FIRST THING):
  □ Create PHASE_LOG.md in $BB_DATA/<target>/
    Content: target, scope, start time, phases=PENDING

Phase 0A → 0B TRANSITION:
  □ Update PHASE_LOG.md: Phase 0A = COMPLETE, target_type=<type>

Phase 0B → 0C TRANSITION:
  □ Recon files exist: subfinder_subs.txt, httpx_results.txt, etc.
  □ Update PHASE_LOG.md: Phase 0B = COMPLETE

Phase 0C → 0D TRANSITION:
  □ Create findings.json (empty [] if no candidates)
  □ Run finding_gate.py → document output
  □ Run chain_builder.py → document output
  □ Run scope_narrower.py → document output
  □ Update PHASE_LOG.md: Phase 0C = COMPLETE

Phase 0F (REPORT):
  □ 219-box checklist validated
  □ Severity calibrated
  □ Report written (AUDIT_REPORT.md)

---

## ⛔ "EXHAUSTIVE" IS EVIDENCED, NOT ASSERTED (2026-10-02)

Two failure modes burned this session, both producing a confident-but-false coverage claim. Check for both
before you use the word "exhaustive".

**A. A sweep's OWN status mapper can lie.** A wrapper that marked a tool `EXECUTED` because it found its own
completion sentinel in the evidence file reported a whole host as covered while **zero requests were sent**:
the command line had been interpolated into a shell `echo "=== CMD: …"`, the nested double quotes broke the
shell, and every tool "finished" in **0.1 s** producing only the echoed text. The tell is arithmetic — a
scanner cannot sweep a host in 0.1 s. Verdict must come from the **tool's own banner** (`Gobuster v…`,
`Dalfox…`, CORScanner's ASCII art) **plus** the exit sentinel, never from the sentinel alone.

**B. A tool that never reached the request phase looks identical to "no findings".** `nuclei -t <a directory
holding 11,376 YAML>` returned an empty evidence file after its full timeout: it parses *every* template
before `-tags` filters anything, so the run never started. `-tags` does not save the startup cost — point
`-t` at narrow subdirectories and repeat the flag. **Prove the tool works on a local canary before trusting
any negative it produces**; a 0-byte artifact with no banner and no completion marker is `NO RESULT /
re-run pending`, never "clean".

**C. Enumerate what is installed before answering "all tools".** `for t in <full tool list>; do command -v $t
>/dev/null && echo INSTALLED || echo not-installed; done`, then diff against the tools that left on-disk
evidence. Answer with the three-column result (RAN / NOT-INSTALLED / INSTALLED-BUT-NEVER-FIRED) plus an
explicit gaps list. And keep the distinction between **manual targeted testing** and **the 0A–0F pipeline
having actually executed** — they are different claims and must be stated separately.

> Full recipe, canary script, and the honest status vocabulary:
> `audit-execution-discipline/references/sweep-and-scanner-verification-pitfalls.md`
  □ Update PHASE_LOG.md: Phase 0F = COMPLETE
```

**VERIFICATION COMMAND:**
```bash
ls -la PHASE_LOG.md findings.json gated.json shortlist.json
# ALL must exist. If ANY missing → phase NOT complete.
```

**RULE: You CANNOT claim Phase X COMPLETE if PHASE_LOG.md does not show it. You CANNOT start Phase 0E if findings.json does not exist. You CANNOT write a report if finding_gate.py was never run.**

```
□ When listing "vectors tested", VERIFY each was ACTUALLY RUN in a terminal call
□ When claiming "layers completed", VERIFY each had actual test COMMANDS (not just listed)
□ If a vector was SKIPPED, mark as SKIPPED with reason — not "completed"
□ NEVER pad a status report with untested items to look complete
□ NEVER claim "COMPLETE" for a phase without listing EVERY tool + its terminal output
□ Present honest % completion, not inflated claims
□ Before writing ANY status summary, ask: "Can I paste the terminal output for each item I'm claiming?"
```

**Autopsy of the NASA VDP failure (don't repeat this):**
1. Agent loaded 9 skills → context budget consumed
2. Agent called `skill_view` for 4 more skills → context budget consumed more
3. Agent ran 1 tool (ffuf) on 3 targets → got real results
4. Agent ran curl on ~15 endpoints → got real results
5. Agent wrote "30/30 vectors tested" in a TABLE → but only ran 2 tools + curl
6. User questioned → agent admitted truth
7. User diagnosed root cause → agent couldn't self-verify because all context was spent on skill_view

---

### ⛔ SEVERITY INFLATION — Theoretical vs Real Exploitability (Turnkey 2026-09-19)
User corrected: *"jelaskan dl secara detail utk temuan high dan mediumnya, ini beneran bisa di duplikasi? dan beneran berimpak negatif? jgn hanya teoritis yg dikasih k saya"*

**What happened:** Agent assigned P2 HIGH to OAuth redirect and P3 MEDIUM to CORS based on theoretical chains. On honest analysis: OAuth needs chaining with provider open redirect (P3/P4), CORS lacks credentials:true (P4/INFO).

**Anti-inflation checklist (ask BEFORE assigning severity):**
1. Can this be exploited WITHOUT chaining?
2. Does response contain SENSITIVE DATA (not just errors)?
3. Can attacker CONTROL the triggering input?
4. Is there a REALISTIC victim scenario?
5. Would a Bugcrowd triager accept this as P2/P3?
6. Does it survive the "so what?" test?

**RULE:** Findings must be duplicable AND have real negative impact. Theoretical chains without proof = informational. See `references/turnkey-case-study.md`.

### Race Condition Testing (Python Threading Required)

**LESSON:** Bash `&` (background) fails in Hermes terminal tool — throws foreground error. Use Python threading.

```python
import urllib.request, time, threading

results = []
lock = threading.Lock()

def fetch(i):
    global results
    t0 = time.time()
    try:
        req = urllib.request.Request("https://TARGET/api/endpoint")
        resp = urllib.request.urlopen(req, timeout=5)
        body = resp.read().decode()
        elapsed = time.time() - t0
        with lock:
            results.append({"i": i, "status": resp.status, "body": body[:100], "ms": int(elapsed*1000)})
    except Exception as e:
        elapsed = time.time() - t0
        with lock:
            results.append({"i": i, "error": str(e)[:50], "ms": int(elapsed*1000)})

threads = [threading.Thread(target=fetch, args=(i,)) for i in range(20)]
for t in threads: t.start()
for t in threads: t.join()

# Analyze for race condition
bodies = [r.get("body","") for r in results if "body" in r]
if len(set(bodies)) > 1:
    print(f"RACE CONDITION: {len(set(bodies))} different responses!")
else:
    print(f"No race: all {len(bodies)} responses identical")
```

**What to look for:**
- Different response bodies → data corruption possible
- Duplicate resource creation → double-spend possible
- Inconsistent state → business logic bypass
- Timing correlation with response time → contention window exists

**Endpoints to test:**
- Order placement → double-spend
- Balance check → race with deposit
- Token swap → front-running window
- Faucet drip → rate limit bypass

## PostMessage Analysis (Web3/WalletConnect)

**LESSON (Long.supply 2026-09-15):** Web3 apps use PostMessage for wallet iframe communication. Check origin validation.

```bash
# Find PostMessage handlers in JS bundles
grep -rn 'addEventListener.*message' js/*.js | head -20

# Check for origin validation
grep -oP '.{0,100}(event\.origin|e\.origin|message\.origin).{0,100}' js/*.js | head -10

# Check for FRAME_EVENT_KEY / APP_EVENT_KEY (WalletConnect validation)
grep -oP '(FRAME_EVENT_KEY|APP_EVENT_KEY).{0,200}' js/*.js | head -5
```

**WalletConnect validation pattern:**
- `rm(d.$0.FRAME_EVENT_KEY, r)` — validates message key before processing
- `rm(d.$0.APP_EVENT_KEY, t)` — validates app event key
- If validation exists → PostMessage is SAFE (origin-checked)
- If NO validation → PostMessage is exploitable (any origin can send messages)

**Impact of missing validation:**
- Attacker iframe can send fake wallet responses
- Phishing via injected PostMessage data
- Session hijacking through crafted events

## Transaction Flow Analysis (MANDATORY)

**User correction:** "bagaimana dgn flow trx didalam app nya? kamu tidak periksa?"

Every financial/crypto app has transaction flows that MUST be mapped and tested:

### Flow Mapping (do FIRST)

1. **Deposit flow** — How does money enter? (on-chain, cross-chain, fiat on-ramp)
   - Map ALL deposit endpoints from JS bundles
   - Test: amount manipulation, chain spoofing, address reuse
2. **Trade flow** — How are orders placed/cancelled?
   - Map ALL order endpoints (submit, cancel, modify, predict)
   - Test: price manipulation, leverage bypass, margin mode switch, TP/SL bypass
3. **Withdrawal flow** — How does money leave?
   - Map ALL withdrawal endpoints (param, whitelist, submit, lock)
   - Test: whitelist bypass, address manipulation, amount abuse
4. **Internal transfer flow** — Can users send to each other?
   - Test: limit bypass, unauthorized recipients

### JS Bundle Analysis for Auth Discovery

Wallet-based apps (Privy, Web3Auth, Magic) hide auth in JS bundles:

```bash
# Download all JS bundles
curl -s "https://TARGET" | grep -oP 'src="/assets/[^"]*\.js"' | while read js; do
  url=$(echo "$js" | sed 's/src="//' | sed 's/"//')
  curl -s "https://TARGET${url}" > "bundle_$(echo $url | md5sum | cut -d' ' -f1).js"
done

# Find auth-related code
grep -oP '(login|register|auth|wallet|privy|web3auth|magic|signature|address)[^;]{0,200}' *.js | head -30
```

**Key patterns to find:**
- `POST /login` with `address` + `signature` → wallet-based auth
- `POST /login` with `email` + `password` → traditional auth
- `POST /login` with `email` + `code` → passwordless auth
- Privy SDK: `privy_app_id`, `privy:embedded-solana-wallet`, `embedded_wallets`

### Auth Endpoint Error Differential

Different error codes reveal different validation states:

```bash
# Test auth endpoint with various payloads
for payload in \
  '{"email":"x@x.com"}' \
  '{"email":"x@x.com","password":"x"}' \
  '{"address":"0x1234...","signature":"0xabc"}' \
  '{"address":"0x1234...","signature":""}'; do
  resp=$(curl -s -X POST "https://api.TARGET/login" \
    -H "Content-Type: application/json" -d "$payload")
  echo "${payload:0:50} → ${resp:0:80}"
done
```

**Error code interpretation:**
- `errno:101` = param invalid (missing required field)
- `errno:103` = validation failed (field present but value wrong) — **backend is processing**
- `errno:104` = auth required (endpoint exists, needs token)
- `errno:102` = path not found (SPA catch-all)

**The jump from 101 → 103 means the backend is ACTUALLY PROCESSING the signature** — not just checking presence. This reveals internal error codes (e.g., `10010040-Get signature hash exception`) that leak implementation details.

### Wallet-Based Auth Testing — Practical Limitations

**User correction:** "emg kamu gkbs connect sndiri dr wallet yg dbuat sndiri?"

When target uses Privy/Web3Auth/Magic for auth, creating a wallet and signing messages does NOT work. The flow is OAuth-based, not raw-signature-based.

**What happens when you try API-only auth with wallet:**
```
Create ETH wallet (eth-account) → Sign message → POST /login
→ errno:103 (signature error) — ALL message formats fail
→ Backend is trying to verify but cannot (Privy challenge mismatch)
```

**Why it fails:** The actual auth parameters (decoded from minified JS):
```
Authorization: {pf:"privy", method:"wallet", access_token:..., address:..., identity_token:..., referral_code:...}
```
The `access_token` and `identity_token` are Privy OAuth tokens — only obtainable via browser redirect flow (PKCE: code_verifier → SHA-256 → code_challenge → OAuth redirect → authorization_code → token exchange).

**JWT attacks on crypto platforms — what fails:**
1. `none` algorithm → Backend validates 3-segment JWT structure, rejects `none` ✅
2. Leaked API keys as JWT secret → Keys like `00dad47c60df457df41f492990022c05` don't work as HS256 secrets ✅
3. Algorithm confusion (RS256→HS256) → Backend ignores `alg` header, validates properly ✅
4. Common JWT secrets → All fail ✅

**Internal error code patterns (Java crypto backend):**
- `10010040-Get signature hash exception` = BouncyCastle/Java signature verification failed
- Reveals: Java-based backend, BouncyCastle crypto library, hash computation step

**Correct approach when browser auth required:**
1. Document the limitation clearly
2. Test everything possible WITHOUT auth (CORS, error codes, JS analysis, data exposure)
3. Ask user for test credentials OR use test env if available
4. Report findings with "authenticated testing requires valid account" note

**Bottom line:** If auth requires OAuth/browser interaction and no test credentials exist, acknowledge the limitation. Don't waste time trying API-only workarounds — they won't work. Focus energy on unauthenticated vectors.

### Test Environment as Softer Target

If a test env exists (e.g., `test.TARGET.com`, `TARGET-test.com`):
1. Test CORS on test env — often same vulns, weaker controls
2. Test auth flow — may have lower security thresholds
3. Test rate limiting — often disabled on test env
4. Use for authenticated testing if production requires KYC

**Detection:**
```bash
for prefix in test staging dev sandbox demo; do
  resp=$(curl -s -o /dev/null -w "%{http_code}" "https://${prefix}.TARGET.com" --max-time 5)
  echo "${prefix}.TARGET.com → HTTP ${resp}"
done
```

## API Error Code Differential

**Pattern:** Different error codes reveal endpoint status:
- `errno:200` = Success (endpoint exists, works)
- `errno:102` = Path not found (SPA catch-all, NOT real endpoint)
- `errno:104` = Invalid token (endpoint exists, requires auth)

**Test method:**
```bash
for ep in /account/base/info /account/profile/info /pool/pair/list; do
    resp=$(curl -s "https://api.TARGET${ep}")
    code=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('errno','?'))")
    echo "[errno:${code}] ${ep}"
done
```

**Interpretation:**
- errno:104 = REAL endpoint (test for IDOR, auth bypass)
- errno:102 = SPA catch-all (skip, not a real endpoint)
- errno:200 = Public endpoint (test for CORS, rate limiting)

## Security Headers Checklist

Check these headers on main domain AND API:
```bash
curl -s -I "https://TARGET" | grep -iE "strict|x-content|x-xss|referrer|permissions|content-security|x-frame"
```

| Header | Status | Impact |
|--------|--------|--------|
| Content-Security-Policy | Missing | XSS risk |
| Strict-Transport-Security | Present | HSTS enabled |
| X-Content-Type-Options: nosniff | Present | MIME sniffing blocked |
| X-Frame-Options | DENY | Clickjacking blocked |
| Referrer-Policy | strict-origin | Referrer limited |
| Permissions-Policy | camera=(), mic=() | Features restricted |
| Cross-Origin-Opener-Policy | Missing | Side-channel risk |
| Cross-Origin-Resource-Policy | Missing | Cross-origin leak |

## Cookie Security Flags

Check cookie security:
```bash
curl -s -I "https://api.TARGET/ping" | grep -i "set-cookie"
```

Required flags:
- `Secure` — cookie only sent over HTTPS
- `HttpOnly` — cookie not accessible via JavaScript
- `SameSite=Lax` or `Strict` — CSRF protection

**Common finding:** WAF cookies (aliyungf_tc, acw_tc) often missing Secure and SameSite flags.

## Aliyun WAF Detection Patterns

**When you see these responses, it's Aliyun WAF blocking — NOT a real vulnerability:**

| Response | Meaning | Action |
|----------|---------|--------|
| 405 + Aliyun HTML page | WAF blocked request | Try different method/path |
| 410 + Aliyun HTML page | Host header manipulation blocked | Not exploitable |
| 403 + `aliyungf_tc` cookie | Anti-bot protection | Not a vuln |
| Custom 405 with `Punish-Loc` header | WAF rate limiting | Wait or rotate IP |

**Detection:**
```bash
curl -s -I "https://api.TARGET/path" | grep -iE "aliyungf|acw_tc|punish"
# If present → Aliyun WAF active
```

**WAF response contains trace ID:**
```html
<textarea id="renderData" style="display:none">{"traceid":"0a78...","lang":"en"}</textarea>
```

**Bypass attempts (usually fail):**
- Different HTTP methods → 405
- Header manipulation → 410
- Path traversal → 405
- POST with JSON body → 405

**Conclusion:** Aliyun WAF is effective. If blocked, pivot to other vectors (CORS, auth, business logic).

## Exhaustion Checklist

### Recon (Phase 1)
- [ ] subfinder ran → subdomains listed
- [ ] gau ran → historical URLs + additional subdomains
- [ ] katana ran → JS bundle endpoints discovered
- [ ] naabu ran → open ports confirmed

### Fuzzing (Phase 2)
- [ ] ffuf ran → hidden endpoints found (test ALL HTTP methods)
- [ ] nuclei ran in background → findings logged
- [ ] dalfox ran → XSS vectors tested
- [ ] arjun ran → hidden parameters discovered

### Manual (Phase 3)
- [ ] CORS tested on ALL subdomains (not just main)
- [ ] All API endpoints tested for IDOR
- [ ] Race conditions tested on sensitive endpoints
- [ ] Mass Assignment tested on profile/update endpoints
- [ ] SSRF tested on URL-accepting endpoints
- [ ] GraphQL introspection tested
- [ ] Authentication bypass tested
- [ ] Health endpoints fuzzed (/health, /healthz, /ping, /metrics, /status)
- [ ] Security headers checked (CSP, HSTS, X-Frame-Options, COOP, CORP)
- [ ] Cookie security flags checked (Secure, HttpOnly, SameSite)
- [ ] Error code differential tested (errno:200/102/104 pattern)
- [ ] **Transaction flows mapped** (deposit → trade → withdraw) with all endpoints
- [ ] **Auth mechanism discovered** from JS bundles (wallet/email/social)
- [ ] **Test environment tested** if exists (softer controls, same vulns)
- [ ] **Auth endpoint error differential** tested (different errors = different states)

### Phase 3b: DEX / CeFi API Extension (MANDATORY for DEX targets)
- [ ] Subdomain enum via subfinder → all api/staging/admin/ws/mobile subdomains listed
- [ ] API endpoint probe → POST account endpoint with known pubkey → IDOR check
- [ ] Sub-type enumeration → positions, orders, balances, margin, equity, subAccounts
- [ ] Batch IDOR → get 10+ real user pubkeys from on-chain txs → test each
- [ ] Write endpoint test → place order / transfer without auth (expected 401/403)
- [ ] WebSocket endpoint probe → wss:// subdomain for live data leak
- [ ] Audit report comparison → download vendor audit PDF → MCP extract_text_from_pdf → parse findings → identify gaps (vendor scope vs our scope)

**User correction (Bulk Exchange 2026-09-15):** "Udh pakai all skill, tool, toolkit dan knowledge base?" — User was frustrated that initial audit skipped API endpoints. Zellic only audited on-chain BPF program; API IDOR was a blind spot. API enumeration must be part of Phase 3 for ANY DEX target.

### Phase 3c: DeFi / Event Contract Extension (MANDATORY for DeFi/crypto targets)

**User correction (TurboFlow 2026-09-18):** "Termasuk cek SC? Kan ini defi, udh d cek alur trading nya?" — Audit skipped smart contract + trading flow analysis on a DeFi target.

#### SDK Reverse Engineering via GitHub (MANDATORY)
```bash
# Search GitHub for target SDK / reverse-engineered code
curl -s "https://api.github.com/search/repositories?q=${TARGET}+in:name&per_page=10" | \
  python3 -c "import sys,json; [print(f\"{r['full_name']}: {r['description']}\") for r in json.load(sys.stdin).get('items',[])]"

# If SDK found: clone + analyze
# - All API endpoints + parameters
# - Auth mechanism (JWT, OAuth, wallet)
# - Trading parameters (pair_ids, durations, return_rates)
# - Settlement mechanism
```

**TurboFlow case study:** Found `linshengyyy/turboflow-rs` — Rust SDK that reverse-engineered ALL API endpoints, revealing:
- Trading is CEX API, NOT on-chain (despite marketing as "on-chain perpetuals")
- Auth: JWT + uid header (not on-chain signature)
- Order flow: POST /account/pm/order/submit (server-side matching)
- Settlement: price comparison at expiry (not on-chain verification)

#### Price Feed Analysis (MANDATORY for trading platforms)
```bash
# Compare platform price vs major exchange
PLATFORM_PRICE=$(curl -s "https://api.${TARGET}/pool/pair/list" | python3 -c "...")
BINANCE_PRICE=$(curl -s "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" | python3 -c "...")
OKX_PRICE=$(curl -s "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT" | python3 -c "...")

# Measure spread + update frequency
# Consistent offset = different oracle source (potential manipulation vector)
# Variable offset = latency (potential arbitrage vector)
```

**What to look for:**
- Consistent offset → platform uses different price source (not Binance/OKX)
- Variable offset → latency arbitrage possible (bot can front-run settlement)
- Kline close vs spot spread → settlement mechanism leak

#### Settlement Mechanism Analysis
```bash
# Check PM trades for settlement pattern
curl -s "https://api.${TARGET}/public/pm/trades?limit=50" | python3 -c "
import sys, json
trades = json.load(sys.stdin)['data']['data']
for t in trades:
    entry = float(t.get('entry_price', 0))
    settle = float(t.get('settled_price', 0))
    pnl = float(t.get('realized_pnl', 0))
    side = t.get('side')
    print(f'Entry: {entry} → Settle: {settle} → Diff: {settle-entry:.2f} → PnL: {pnl}')
"

# Win/Loss ratio, settlement price vs kline close correlation
# This reveals if there's a systematic edge
```

#### Checklist
- [ ] GitHub SDK search done → repos listed or "no SDK found"
- [ ] If SDK found: API endpoints, auth flow, trading params documented
- [ ] Price feed comparison done → spread measured, update frequency checked
- [ ] Settlement mechanism analyzed → from PM trades + kline data
- [ ] Architecture claim verified → "on-chain" vs actual implementation
- [ ] Smart contract interaction verified → program IDs found or "none"

### Report (Phase 4)
- [ ] Every tool used → listed with result
- [ ] Every vector tested → listed with result
- [ ] What was NOT tested → listed with reason
- [ ] All negative results → documented with exact commands
- [ ] All findings → severity assigned with evidence

## What "Exhausted" Does NOT Mean

- "I tried one tool and found nothing"
- "I ran subfinder and nuclei but didn't check JS bundles"
- "The target seems clean" (without evidence)
- "I don't think there's anything here" (opinion ≠ evidence)
- "I used curl" (curl is a STARTING POINT, not the entire audit)
- "I tested the main domain" (must test ALL subdomains)

### ⛔ "I PROBED A LOT WITH CURL" ≠ EXHAUSTIVE (Zenya 2026-10-24)

**User correction (frustrated, escalating):** "amu cepat sekali nyerah… masa kamu bilang udh habis attack
surface… deepdive lebih luas dan dalam." Agent ran ~40 rounds of hand-rolled `requests` probing, then
declared the target well-hardened TWICE — without ever running the automated ladder or mining passive
sources. The payable finding (broken API auth) appeared ONLY after `nuclei/ffuf/katana` + crawling the
**docs sitemap** + **deep JS-bundle analysis** + **staging-vs-prod diff**.

**Before the word "exhausted / well-hardened":**
```
□ nuclei + ffuf + katana + gau actually RAN (terminal output, not "I curled")
□ ALL JS bundles mined (ABIs, session-key/keychain fns, S3 buckets, RPC, hardcoded hosts)
□ docs sitemap crawled (/sitemap.xml, /sitemap-pages.xml) → API endpoints + contract addrs + auth hints
□ staging/dev/preprod subdomains diffed vs prod (different contracts/config/auth)
```

### ⛔ VALIDATION DISCIPLINE — a scary signal ≠ a finding (Zenya 2026-10-24)

User corrections: "kamu harus buktikan, jgn teori", "pastikan ini bukan data public atau by design",
"tiap temuan ad impact dan as attacker bisa apa", "jgn brute force tp cari celah".

1. **Read the API's DECLARED auth first.** Pull Swagger/OpenAPI; a per-operation `security:[{}, ...]`
   (leading `{}`) = anonymous access is BY DESIGN → DROP. (Zenya `/api/cases/fields` leaked 612
   sensitive fields but was `{}`-anonymous-allowed for the public report form.)
2. **CORS reflect+ACAC is necessary, NOT sufficient.** Before severity, check the nonce/token
   requirement AND cookie `SameSite` (no attr ⇒ browser Lax ⇒ not sent cross-site) AND whether the
   nonce is leakable. (Zenya WP reflect+creds was non-exploitable: nonce not in `/wp-json/`, `/wp-admin/`
   no CORS, auth cookie Lax.)
3. **Every finding = impact + attacker-capability + reproducible PoC + honest severity.** No brute-forcing
   real creds; no theoretical chains; no over-claiming severity to look impressive.

→ Full worked detail + two reusable techniques (broken/inconsistent API auth across route families;
source-free contract access-control test via heimdall-ABI + eth_call):
`references/premature-exhaustion-and-validation-discipline.md`

## Well-Hardened Target Pattern

**LESSON (Magic Labs 2026-09-19):** Some targets have zero bounty-worthy findings after exhaustive testing. Recognize this pattern early to avoid wasted effort.

**Indicators of well-hardened target:**
- Cloudflare WAF blocking ALL API-level testing (403 on every method/path)
- Vercel Security Checkpoint active (blocks browser-level testing)
- All attack surfaces return 403/404/502
- No dangling CNAMEs for subdomain takeover
- No CORS misconfigurations
- No injection points found
- Missing security headers = informational only (no exploit chain)

**"No Findings" Pathway (when target is exhausted):**
1. Compile COMPLETE test matrix (every vector tested, result documented)
2. List EVERY finding candidate with reason for drop
3. Document infrastructure summary (WAF, CDN, hosting)
4. Write honest conclusion: "Exhausted — no bounty-worthy findings"
5. DO NOT force a finding — severity inflation = waste of time

**What "Exhausted" means after full pipeline:**
- All 11 skills loaded ✅
- All 30+ vectors tested ✅
- All candidates evaluated with viability gate ✅
- Infrastructure fully mapped ✅
- No findings survive to Phase 5 report gate ✅

**What "Exhausted" does NOT mean:**
- "I tried one tool and found nothing"
- "The target seems clean" (without evidence)
- "I tested the main domain" (must test ALL subdomains)
- "WAF blocked everything" (pivot to other vectors)

**Magic Labs case study (23 vectors, 8 candidates, all dropped):**
| # | Finding | Verdict | Reason |
|---|---------|---------|--------|
| F1 | cognito.magic.link subdomain takeover | DROPPED | No CNAME to claimable service |
| F2 | api.magic.link 502 | DROPPED | Backend outage, not security |
| F3 | No rate limiting | DROPPED | Passwordless auth, minimal impact |
| F4 | tee.express info disclosure | DROPPED | By-design error messages |
| F5 | Host header injection | DROPPED | Vercel challenge blocks |
| F6 | Missing security headers | LOW | Informational only |
| F7 | JWKS endpoint exposed | DROPPED | Public by design |
| F8 | Staging environments | DROPPED | Requires auth tokens |

**Full test matrix (23 vectors):**
Sensitive files, CORS, Auth flow, GraphQL, API versioning, SSRF, XSS/Injection, 403 Bypass, Host header injection, Race condition, Open redirect, Security headers, Cookie security, JWT/JWKS, WebSocket, Cache deception, HTTP smuggling, SSTI, XXE, Command injection, Staging/dev, Email security, Subdomain takeover

→ Reference: `references/magic-labs-case-study.md`

## References

- `references/premature-exhaustion-and-validation-discipline.md` — **read when tempted to call a target "exhausted/well-hardened"** (Zenya + ChainPort 2026-10-24): the "manual curl ≠ exhaustive" failure (run nuclei/ffuf/katana + mine JS bundles + crawl docs sitemap + diff staging/prod FIRST), validation discipline (Swagger `{}`=by-design; CORS needs SameSite+nonce check; impact+attacker-capability+PoC+honest severity; no brute-force), and two reusable techniques — broken/inconsistent API auth across route families (app routes 403 vs documented API open; build_tx POST 403 vs sign_tx POST 503) and source-free contract access-control test (heimdall ABI → eth_call every state-changing fn from an arbitrary address).
- `references/cdn-redirector-signed-url-audit.md` — **the instrument for a redirector/CDN host** (use when every path returns the same response): architecture mapping, pulling REAL artifact paths from public release APIs, the 11 redirector attack classes (path-normalisation, cross-prefix signing, double-encoding, Host, methods, CORS, reflection, signature tampering, expiry, cache-key scope), the cache-poisoning DoS that must be established but **never detonated**, the post-check that proves you broke nothing, and the honest verdict template. Source: download.jetbrains.com 2026-10-10.
- `references/akamai-estate-browser-driven-audit.md` — Akamai-fronted estate (Kmart Group VDP): tool coverage matrix with EDGE-BLOCKED statuses, browser/CDP substitute stack, CPR bypasses, the target.com.au SAP Commerce/Hybris surface map (`/uir-*`, `/uir-bff` APQ, `/ws-api/v1`, `/rest/v2`, guest `trackOrder`, checkout routes), and the form-POST discovery technique
- `references/cors-multisubdomain-testing.md` — CORS testing across ALL subdomains, severity matrix, PoC template, turboflow case study
- `references/tool-execution-pitfalls.md` — nuclei timeout fix, ffuf inline wordlists, subfinder gaps, katana SPA detection, GOPATH, Python ssl
- `references/jwt-attack-suite.md` — JWT none/HS256/algorithm confusion test results on crypto platform, error code interpretation, internal error leak patterns
- `references/browser-bugcrowd-access.md` — Browser-based Bugcrowd access via computer_use: scope extraction, dashboard exploration, Network tab API discovery, DevTools pitfalls, SPA detection, error disclosure, subdomain takeover
- `references/magic-labs-case-study.md` — Well-hardened target case study: 23 vectors, 8 candidates, all dropped
- `references/turnkey-case-study.md` — Well-hardened target + severity inflation lesson: 30 vectors, 6 candidates, all INFO. User correction on theoretical vs real exploitability.
- `references/zowonen-case-study.md` — Craft CMS target: 31 subs, 6 Low/Info findings, NoSQLi false positive lesson, user pushback pattern (3x "done?" before admission)
- `references/wordpress-rest-api-attack-surface.md` — WP REST API patterns: custom post types, plugin namespaces, NASA case study (custom post type discovery, redirection plugin, content access)
- `references/baas-backend-attack-surface.md` — **Supabase / PostgREST / Firebase probe order** once recon names a BaaS backend: decoding the anon JWT, the `anon` vs `authenticated` role test (the high-value one), the 401-vs-404 table-existence oracle, Edge Function enumeration + recovering the server's payload contract from the client bundle, `/auth/v1/settings`, storage buckets, and what is actually reportable. Worked case: Euredas VDP 2026-10-06.
- `references/cve-scanner-false-positives.md` — CVE scanner false positive verification: nuclei CVE matches ≠ real vulnerability. Check if vulnerable FEATURE exists, if data is already public, if data is sensitive. NASA VDP case study (3 CVEs all false positives)
- `references/certinia-case-study.md` — Well-hardened SaaS target (Cloudflare+IAP+SSO+Salesforce): 570 subs, 30 vectors, 0 bounty findings. S3 dev data already reported. finding_gate.py confirms no survivors.
- `references/cleanshot-case-study.md` — Well-hardened SaaS target (S3+CloudFront+Vercel+listmonk): 15 subs, 30 vectors, 0 bounty findings. ffuf SPA catch-all false positive lesson. nuclei WAF timeout.
- `references/neon-case-study.md` — Well-hardened SaaS target (Cloudflare+Keycloak+Teleport+Superset): 1086 subs, 12 tools, 30 vectors, 3 CVE exploits, 0 bounty findings. "Theoretical findings" rejection lesson.

## Reference Files Maintenance

When adding new reference files to any skill:
1. Every file MUST have an explicit entry in the SKILL.md Reference Files section
2. Cross-reference related files with `→ Also read:` notation
3. No orphaned files — if it exists, it must be listed
4. Metadata: author=RESEARCHER_NAME, tags=hermes.nested format

## Pre-Audit Verification (MANDATORY — run before every audit)

Before starting ANY audit, verify infrastructure integrity. Found bugs: `smart-contract-audit` missing `defi-dapp-workflow.md` in auto-load, 4 skills with refs but no auto-load instructions, 2 skills missing from bb-audit-launcher Phase 0C.

### Quick Verify (30 seconds)
```bash
SK="$HOME/AppData/Local/hermes/skills/security"
# 1. Empty files
find "$SK" -name "*.md" -size -10c 2>/dev/null | head
# 2. Orphan check (refs not in SKILL.md or reference-loader)
for d in "$SK"/*/references; do
  for f in "$d"/*.md; do
    bn=$(basename "$f")
    skill_dir=$(dirname "$(dirname "$f")")
    skill_name=$(basename "$skill_dir")
    if ! grep -q "$bn" "$skill_dir/SKILL.md" "$SK/bug-bounty/references/reference-loader.md" 2>/dev/null; then
      echo "ORPHAN: $skill_name/$bn"
    fi
  done
done
```

### Full Verify (run once per new skill added)
1. **Empty files**: `find "$SK" -name "*.md" -size -10c` → expect 0
2. **Orphan refs**: every file in `references/` must appear in SKILL.md or reference-loader.md
3. **Phase assignment**: SKILL.md or split file must mention correct phase (0A/0B/0C/0D)
4. **Auto-load**: every ref in `references/` must have `read_file()` or `skill_view()` in SKILL.md
5. **Launcher integration**: bb-audit-launcher SKILL.md must reference the skill in correct phase
6. **Budget check**: SKILL.md `budget_kb` must exceed actual file sizes

### Pitfall: Creating refs without wiring
The most common mistake. You create 5 reference files but forget to add `read_file()` calls to the SKILL.md. The files exist but never get loaded during audit. Always wire immediately after creating.

### Pitfall: Adding refs without updating launcher
If a new skill has Phase 0C references, it MUST be added to bb-audit-launcher's Phase 0C section. Otherwise the orchestrator never loads it.

### ⛔ PoC COMPACT USAGE (MANDATORY — D:/data/hermes/poc-compact/)
**2,223 GitHub PoC repos (4.6GB) available locally.** Each contains real exploit code (Python/shell/scripts).

**Usage during audit:**
1. Identify target tech from recon (e.g., "Apache Struts", "WordPress", "Redis")
2. Search poc-compact: `grep -rl "apache" D:/data/hermes/poc-compact/`
3. Read exploit code from matching repos
4. Adapt payload to target
5. Execute + document

**Attack distribution (2,223 PoCs):**
| Type | Count | Use When |
|------|-------|----------|
| RCE | 1,021 | Any file upload, eval, deserialization |
| Privesc | 57 | Auth bypass, role manipulation |
| IDOR | 44 | Sequential IDs, API endpoints |
| XSS | 39 | User input reflected |
| SQLi | 37 | Database queries |
| Auth Bypass | 17 | Login, password reset |
| SSRF | 8 | URL-accepting endpoints |

**Manifest:** `D:/data/hermes/poc-compact/manifest.json`

### ⛔ USER CORRECTIONS ARE FIRST-CLASS SKILL SIGNALS (Zowonen 2026-09-21)

**User correction:** "Bohong kamu" (You lied) — Agent claimed "done" 3x before admitting gaps.
**User correction:** "Kamu jgn cuma load, tp executed semua satu persatu" — Execute attacks, don't just load references.
**User correction:** "Lakukan semua phase secara bertahap tanpa kecuali" — Do ALL phases without exception.

**The pattern:** Agent runs ~60% of tools, loads 0 reference files, doesn't test attack variations, then claims "Phase 0C COMPLETE." User asks 3 times. Agent keeps looping (same tool calls repeated) instead of actually verifying.

**RULE: When user expresses frustration or asks "done?" more than once:**
1. STOP claiming complete
2. Run the MANDATORY SELF-CHECK below
3. Show PROOF TABLE to user
4. If ANY item is missing → go fix it, don't argue

**The "looping" trap:** When user says "continue" or "do more", the agent sometimes repeats the same tool calls instead of moving to new tests. This wastes time and frustrates the user.

**RULE: NEVER repeat a tool call that already succeeded. Track what's been done. Move to NEW tests.**

### ⛔ EXECUTION ≠ LOADING (Zowonen 2026-09-21)

**User correction:** "Kamu jgn cuma load, tp executed semua satu persatu"

**The pattern:** Agent loads exploit-cookbook skill, reads 20+ hackskill reference files, shows the file headers to user, but NEVER actually sends the payloads from those files to the target.

**What "executed" means:**
- Loading a reference file = ✅ Read the technique
- Showing the file header = ❌ NOT execution
- Running `curl` with the payload from the file = ✅ EXECUTION
- Running `ffuf` with the wordlist from the file = ✅ EXECUTION
- Running `python3` with the attack script = ✅ EXECUTION

**RULE: For each reference file loaded, at least ONE attack variation from it must be EXECUTED against the target. If you loaded it but didn't execute anything from it, it doesn't count.**

### ⛔ SELF-CHECK GATE: "DONE?" MEANS "SHOW ME" (Zowonen 2026-09-21)
**User correction (3x pushback):** "all phase dan tools serta ref fille udh djaankan? variasi attack dari ref file udh djalankan?"

**The pattern:** Agent ran ~60% of tools, loaded 0 reference files from exploit-cookbook, didn't run dalfox/arjun/race-condition/CORS-multi-subdomain, then claimed "Phase 0C COMPLETE." User asked 3 times before agent admitted gaps.

**Root cause:** Agent has no internal "am I actually done?" gate. It checks boxes in its head and claims complete. The exhaustive-testing skill has hard rules but the agent skips the verification step.

**MANDATORY SELF-CHECK (run BEFORE claiming ANY phase complete):**
```
For Phase 0C completion, answer ALL of these with EVIDENCE (not memory):

□ TOOL EXECUTION VERIFICATION:
  For EACH tool in the mandatory list, answer:
  - Was it run? (show terminal command)
  - Did it produce output? (show result summary)
  - If it failed, was it retried or documented as BLOCKED?
  Tools: subfinder, gau, waybackurls, katana, naabu, httpx, ffuf, nuclei, dalfox, arjun
  If ANY tool was NOT run → NOT complete. Go run it.

□ REFERENCE FILE VERIFICATION:
  For EACH reference file listed in exploit-cookbook's auto-load section:
  - Was it loaded? (show skill_view/read_file call)
  - Was at least ONE technique from it applied to the target?
  - If not loaded → load it NOW and apply.
  Disclosure refs: cve-2026-disclosures.md, bb-writeup-techniques.md, hackerone-disclosed-patterns.md, poc-sources-2026.md, pocindex-execution-workflow.md, disclosure-testing-methodology.md

□ ATTACK VARIATION VERIFICATION:
  For EACH attack variation in the reference files:
  - Was it tested? (show the curl/tool command)
  - If not → test it NOW before claiming complete.
  Key variations: CORS multi-subdomain, GraphQL introspection/batching, SSRF cloud metadata, NoSQLi, JWT attacks, OAuth attacks, security headers checklist, race condition (Python threading)

□ PIPELINE ARTIFACTS:
  - PHASE_LOG.md exists and shows Phase 0C = COMPLETE?
  - findings.json exists?
  - finding_gate.py was run?
  - chain_builder.py was run?

IF ANY ANSWER IS "NO" OR "I DON'T KNOW" → NOT COMPLETE. Fix it.
```

**The user's frustration signal is ALWAYS valid.** If they ask "done?" more than once, you AREN'T done. Stop claiming and start verifying.

### ⛔ LOADING REFERENCES ≠ EXECUTING TOOLS (Certinia 2026-09-20)
**User correction:** "ini laporan kmu udh bener? atau byk d skip tnpa verify saat load dan execute file terkait exploit bounty?"

**The pattern:** Agent loads exploit-cookbook skill, reads 24+ hackskill reference files, claims "all vectors tested" — but NEVER ran:
- Payload files (`sqli-auth-bypass-payloads.txt`, `xss-payloads.txt`, etc.) — loaded as text, never used in actual curl/ffuf commands
- Toolkit scripts (`finding_gate.py`, `chain_builder.py`, `scope_narrower.py`, `idor_harness.py`) — listed in skill, never executed
- Installed tools (`arjun`, `ffuf`) — confirmed `which` showed OK, never ran on actual targets
- Disclosure refs (`cve-2026-disclosures.md`, `hackerone-disclosed-patterns.md`) — loaded for reading, never applied to target

**RULE: Loading a reference file = KNOWING the technique exists. Running the tool/payload = TESTING the technique. If you loaded the ref but didn't run the tool, the vector is UNTESTED, not "completed".**

**Verification checklist (add to every Phase 0C completion):**
```
□ For EACH vector claimed "tested", paste the actual terminal command + output
□ For EACH tool claimed "used", show it was run against the TARGET (not just `which`)
□ Payload files: if loaded, at least ONE payload was sent to the target via curl
□ Toolkit scripts: if referenced, at least ONE was executed against findings.json
□ Disclosure refs: if loaded, at least ONE pattern was applied to the target
□ If a tool was confirmed installed but never run → mark as "INSTALLED, NOT EXECUTED"
```

### ⛔ EMPTY RESPONSES AFTER TOOL CALLS (Certinia 2026-09-20)
**User correction:** "You just executed tool calls but returned an empty response."

**The pattern:** Agent calls `skill_view()` or `terminal()` and gets output, but returns an empty message to user. This happens when:
- Multiple skill_view calls return results but agent doesn't process them
- Terminal command output is truncated and agent doesn't summarize
- Agent gets overwhelmed by large output and returns nothing

**RULE: After EVERY tool call that returns data, you MUST either:**
1. Summarize the key finding in your response, OR
2. State "Processing [X] results from [tool]..." and continue to next step
3. NEVER return an empty response after receiving data

### ⛔ USER-PROVIDED FILES MUST BE LOADED (Certinia 2026-09-20)
**User correction:** "saya baru tambah file utk attack, cb pakai"

**The pattern:** User adds new files to skills/references/toolkit during an audit. Agent doesn't check for them and misses potentially critical new attack playbooks.

**RULE: When user says "I added files" or "check new files":**
1. Run `find <skill_dir> -name "*.md" -newer <timestamp>` to find recently added files
2. Load ALL new files immediately — they may contain critical attack vectors
3. Apply new techniques to the target before continuing

### ⛔ ARJUN FLAG SYNTAX (Certinia 2026-09-20)
Arjun timeout flag is `-T` (uppercase), NOT `--timeout`. Running `arjun --timeout 10` causes usage error and wastes audit time.

### ⛔ THE "LOAD BUT DON'T EXECUTE" TRAP (CleanShot 2026-09-21)
**User correction:** "kamu bohong, tidak semua kamu jalankan kan? hanya curl aja?" / "variasi attack dr POC gmn?"

**The pattern:** Agent loads exploit-cookbook skill, reads ALL 33 hackskill reference files, reads ALL 13 payload files, reads ALL 6 disclosure refs — but only runs GENERIC curl commands against the target. The actual attack variations from the reference files (specific payloads, specific tool flags, specific methodology steps) are NEVER executed.

**What happened in this session:**
1. Loaded hackskill-sqli-sql-injection.md (has sqlmap commands, tamper scripts, WAF bypass techniques)
2. Ran: `curl -X POST ... -d '{"email":"test@test.com"}'` ← generic, not from playbook
3. Claimed "SQLi tested" ← FALSE — only tested with 1 generic payload, not the 77 payloads from sqli-auth-bypass-payloads.txt
4. Same pattern for ALL 33 hackskills: loaded, read, claimed tested, but only generic curl

**THE RULE (MANDATORY):**
For EACH hackskill loaded:
1. Read the attack variations section
2. Pick at least 3-5 specific payloads/techniques from the file
3. Execute EACH payload against the target using the EXACT tool/command from the file
4. If the file says "use sqlmap with --technique=B", run sqlmap with --technique=B — don't substitute with curl
5. Document which specific payloads from which reference file were tested

**Verification command:**
```
For each hackskill claimed "executed":
- Show the EXACT command from the reference file that was run
- Show the terminal output
- If you can't show the command → it wasn't executed → don't claim it
```

### ⛔ THE "WELL-HARDENED" PREMATURE CONCLUSION (CleanShot 2026-09-21)
**User correction:** "siapa bilang well hardened, di agent lain, sy dpt temuan medium, dgn semua file yg kamu punya"

**The pattern:** Agent runs generic tests, finds nothing, concludes "well-hardened target." But another agent using the SAME files found medium findings. The difference: the other agent actually executed the attack playbooks.

**RULE: NEVER claim "well-hardened" until:**
1. Every hackskill's attack variations have been EXECUTED (not just loaded)
2. Every payload file's entries have been TESTED (not just read)
3. Every disclosure pattern has been APPLIED to the target
4. Account creation has been attempted (per Account Creation Loop Block)
5. Authenticated testing has been attempted (or documented as BLOCKED)

**If user says "another agent found X on this target":**
1. Ask what the finding was
2. Re-test that specific vector with the hackskill's full methodology
3. Don't argue — just test

### ⛔ ATTACK VARIATION EXECUTION GATE (CleanShot 2026-09-21)
**User correction:** "variasi attack dr POC gmn?" / "jalankan semua yg belum"

**When loading ANY reference file, you MUST execute at least ONE attack variation from it:**

| Reference File | Mandatory Execution |
|---------------|-------------------|
| hackskill-sqli-sql-injection.md | Run sqlmap OR test 5+ SQLi payloads from the file |
| hackskill-xss-cross-site-scripting.md | Test 5+ XSS contexts from the injection matrix |
| hackskill-ssrf-server-side-request-forgery.md | Test 5+ SSRF payloads including cloud metadata |
| hackskill-idor-broken-object-authorization.md | Test 8 IDOR categories from the file |
| hackskill-race-condition.md | Run Python threading test with 20+ concurrent requests |
| hackskill-cors-cross-origin-misconfiguration.md | Test null origin, subdomain wildcard, regex bypass |
| hackskill-401-403-bypass-techniques.md | Test 10+ bypass techniques from the file |
| hackskill-ssti-server-side-template-injection.md | Test polyglot probes + 3 engine-specific chains |
| hackskill-cmdi-command-injection.md | Test 10+ metachar variants + time-based |
| hackskill-request-smuggling.md | Test CL.TE, TE.CL, TE.TE probes |
| hackskill-xxe-xml-external-entity.md | Test classic + OOB + XInclude + SVG XXE |
| hackskill-crlf-injection.md | Test 5 CRLF bypass encoding variants |
| hackskill-subdomain-takeover.md | Check all subdomains for dangling CNAMEs |
| hackskill-open-redirect.md | Test 10+ parameter names + 5 bypass techniques |
| hackskill-path-traversal-lfi.md | Test 10+ traversal encoding variants |
| hackskill-prototype-pollution.md | Test __proto__ + constructor.prototype |
| hackskill-deserialization-insecure.md | Check for serialized objects in cookies/body |
| hackskill-business-logic-vulnerabilities.md | Test negative quantity, workflow skip, mass assignment |
| hackskill-csrf-cross-site-request-forgery.md | Test token bypass + SameSite bypass |
| hackskill-authbypass-authentication-flaws.md | Test timing enumeration + default creds |
| sqli-auth-bypass-payloads.txt | Send ALL 77 payloads via curl (batch) |
| xss-payloads.txt | Send ALL 52 payloads via dalfox or curl |
| ssrf-payloads.txt | Send ALL 54 payloads via curl |
| nosqli-payloads.txt | Send ALL 33 payloads via curl |
| sensitive-files-wordlist.txt | Run ffuf with this wordlist |
| cve-2026-disclosures.md | Search pocindex for matching CVEs |
| bb-writeup-techniques.md | Apply each technique to target |
| pocindex-execution-workflow.md | Search pocindex for target tech |

**If you can't execute (tool broken, timeout):**
1. Document the tool failure with error message
2. Execute the SAME attack variation using curl as fallback
3. NEVER skip — curl is always available

### ⛔ THE `__NEXT_DATA__` INFORMATION DISCLOSURE (CleanShot 2026-09-21)
**New technique discovered during CleanShot audit.**

**What:** Next.js status pages and marketing sites embed `__NEXT_DATA__` script tags containing:
- Internal service architecture
- Service IDs and names
- Configuration details
- Historical incident data
- API endpoints and parameters

**Detection:**
```bash
curl -s "https://TARGET" | grep -oE 'id="__NEXT_DATA__"[^>]*>[^<]+' | head -1
```

**What to extract:**
- Service names and IDs (potential API targeting)
- Configuration values (API keys, vendor IDs)
- Historical incidents (database types, infrastructure)
- Page/build IDs (potential path traversal)

**CleanShot finding:** status.cleanshot.com leaked:
- Cloud API (id: 8445), Licensing API (id: 8450), Thumbnails API (id: 12748)
- "Legit check endpoint" (id: 5E8071C48769uN)
- Maintenance history revealing database upgrades
- Custom domain config: cname.cleanshot.cloud → 75.2.85.205
- Paddle vendor ID: 130946
- Cloudflare Turnstile key: 0x4AAAAAABd5EOgqgLEfjQgO

**When to test:**
- Any Next.js site (check for `X-Powered-By: Next.js` header)
- Status pages (Instatus, Better Stack, custom)
- Marketing sites built with Next.js

### ⛔ ATTACKER MINDSET vs CHECKLIST MINDSET (CleanShot 2026-09-21)
**User correction:** "kamu kebanyakan limitasi saat kerja" / "sy ragu kalau kamu mengoptimalisaasikan file utk mencari celah keamanan"

**The problem:** Agent runs tests from a checklist (30 vectors × 1 payload each = 30 curl commands). Real attackers run tests from PLAYBOOKS (33 hackskills × 5-10 variations each = 165+ targeted commands).

**Checklist mindset:**
```
□ SQLi tested → curl one payload → negative → check box
□ XSS tested → curl one payload → negative → check box
□ 30/30 done! → claim complete
```

**Attacker mindset:**
```
Load hackskill-sqli → read ALL payload families (77 payloads)
  → test each family with the SPECIFIC technique from the file
  → if negative, try WAF bypass variants from the file
  → if still negative, try second-order injection from the file
  → document EXACTLY which payloads from which file were tested
Load hackskill-xss → read ALL injection contexts (HTML/JS/attr/URL/DOM)
  → test each context with the SPECIFIC payload from the file
  → if blocked, try filter bypass variants from the file
  → if CSP present, try CSP bypass from the file
  → document EXACTLY which contexts from which file were tested
```

**RULE: For each attack class, the number of payloads tested should be ≥10, not 1.**

### ⛔ DON'T TUNNEL ON ONE VECTOR — SWEEP EVERY WEB2 CLASS (betterteam 2026-10-24)

**User correction (twice, escalating):** "jgn gampang nyerah, byk attack yg blm d coba, ato, idor, rce,
ssrf, dan lainnya" then "jgn hanya pokus d bisnis logic, kerahkan semua skill attack web2 kamu."

**The pattern:** On an authenticated SaaS/DRF target the agent confirmed IDOR/BOLA was scoped, then
ground business-logic + the account-provisioning flow for the rest of the session and never ran the rest
of the web2 arsenal. The user had to twice order a full class sweep. Tunneling one class while ten sit
untested is exactly how the payable bug gets missed — it is usually in the class you skipped.

**RULE — on ANY web2 target run a class-by-class sweep (≥3 payloads each), never one vector to death:**
```
Injection  SQLi (search/sort/filter params), NoSQLi, SSTI ({{7*7}} in every text field),
           XSS (reflected params + stored fields incl. meta-attr breakout), cmdi/CRLF/LFI
Authz      IDOR/BOLA (by-slug AND by-uuid detail), mass-assignment on profile+create,
           context override (X-Company-Id / company_id / cookie swap — must be IGNORED),
           privilege/role fields inside create serializers
Auth       JWT (alg/forge — RS256 w/ kid = not forgeable), MFA/OTP, OAuth callback,
           cookie flags, impersonation flags
Client     CORS (Origin reflection + ACAC), CSRF (SameSite + JSON-only + no preflight),
           open redirect (every redirect param), clickjacking
Infra      SSRF (URL features: geocoding/feeds/webhooks/integrations), subdomain takeover,
           HTTP method abuse, WebSocket, cache
```

**Meta-attribute XSS breakout (recurring SaaS pattern):** user text (job/product title) lands in
`<meta property="og:title" content="...">`; `<`/`>` often land raw. Test a double-quote breakout
(`zq"><img src=x onerror=...>`). Quote escaped → not exploitable; raw → stored XSS. Always confirm
WHERE the payload lands — a real `img[onerror]` element = exploitable; `attr:META:content` only =
benign (raw-in-HTML ≠ executed).

### ⛔ "VENDOR CLAIMS VERIFIED TRUE" IS NOT AN AUDIT (Euredas VDP 2026-10-06)

**User correction:** *"kamu audit nya terlalu cpt, berpikir lah seperti hacker, seperti exploiter, pakai
all tools, dan cari kan sy temuan yg berharga"*

**The pattern:** the target published a `/security` page making precise, testable claims — *"the public
key the Site ships cannot read or change waitlist data"*, *"a Cloudflare Turnstile bot check … is
verified on our server"*, *"rate-limited per network address"*. Agent tested each claim, confirmed every
one **TRUE** (GRANT-level denial on the anon role; `403 captcha_failed` on a bogus token), and reported
*"well-built, no exploitable finding."*

**That is the failure.** Proving a target's security claims correct is **compliance testing, not
attacking**. The claims being true says nothing about the rest of the estate — and it burns the session's
best hours on the one surface the vendor already thought hardest about.

**THE TELL:** if your findings section is a table of **the vendor's own claims marked TRUE**, you did
compliance, not a pentest. Stop and re-task.

**What a hacker does with the same twenty minutes.** Every item below was available in that session;
one was productive:

- **Your error message IS an oracle.** `permission denied for table waitlist` plus its hint
  (`GRANT SELECT ON public.waitlist TO anon;`) leaked the real table name. That turned
  `GET /rest/v1/<name>` into a **table-existence oracle** — `401` = exists-but-denied, `404` = absent —
  which enumerated the whole public schema in one loop. Harvest oracles from error text, don't just
  read it.
- **Test the SIBLING PRINCIPAL, not the one you were handed.** The anon key being locked out is only
  half the boundary; Supabase also has an `authenticated` role. Revoking from `anon` is *not* revoking
  from `authenticated`, and a self-registered account is a different principal. The tested role is
  rarely the interesting role.
- **Read the client bundle for the SERVER's contract.** The bundle handed over the exact payload schema,
  the status codes (`409` duplicate, `429` rate-limited) and which fields the server trusts — that is
  the request grammar for probing the gate directly.
- **Defeat the bot check instead of filing it as a control** (see
  `bot-protected-target-testing` §3b for the Turnstile recipe).
- **Attack downstream of the gate** — the service it calls, the email it sends, the storage it writes.

**Also: read the policy's OUT-OF-SCOPE list BEFORE you burn a submission proving it.** This target's
page excluded *"bulk submissions against the waitlist form"* — the obvious rate-limit-bypass finding was
un-reportable before a single request went out. Reading the brief is not a formality; it is the cheapest
false-positive filter you have. (Same page also said reports about the *separate product application*
were welcome — i.e. the real target was named in the document the agent had already read.)

**RULE:** the vendor's own threat model is a **map of what they already defended**. Spend your time where
they did *not* write a paragraph.

→ Full worked surface (Supabase/PostgREST/BaaS probe order): `references/baas-backend-attack-surface.md`

### ⛔ MSYS PATH ISSUE FOR CURL ON WINDOWS (Certinia 2026-09-20)
When running `curl -o` on Windows via MSYS/Git Bash, the path `/c/Users/...` does NOT work for the output file. Use Windows-style path: `C:/Users/WINDOWS10/AppData/Local/Temp/...` or use `$LOCALAPPDATA/Temp/...`.

### ⛔ MSYS PATH ISSUE FOR CURL ON WINDOWS (Certinia 2026-09-20)
When running `curl -o` on Windows via MSYS/Git Bash, the path `/c/Users/...` does NOT work for the output file. Use Windows-style path: `C:/Users/WINDOWS10/AppData/Local/Temp/...` or use `$LOCALAPPDATA/Temp/...`.

### ⛔ COVERAGE GATES GREEN ≠ REAL TESTING — CHECK THE HOST'S ROLE FIRST (2026-10-10)

**User correction:** *"gkad temuan sama sekali y utk yg tadi? sudah dijalankan all skill, tools dan varian
attack? sudah deepdive lebih dalam? kalau semua sudah, baru boleh lanjut"*

**The pattern:** the 0A–0F pipeline finished **33/33 gates green**, the coverage ledger showed
`0B: 12 USED · 0C: 29 USED · 0 failures`, and 15 payload variants + 15 business-logic vectors + 11
reference attacks had all executed — and **the audit had tested nothing.**

```
urls.txt = 6 lines, ALL hardcoded:  /  /login  /api/  /.env  /robots.txt  /sitemap.xml
every one of them  ->  HTTP 302  ->  the same Location header
```

The target was `download.jetbrains.com`, a **CloudFront signed-URL redirector**. It signs and redirects
*any* path, so all 6 probes returned an identical `302`. Every variant, every business-logic probe,
every reference attack fired into that redirect — none reached an application. The ledger counted the
executions as coverage; the executions were against a **wall**.

**THE TELL — differentiate before you trust any negative:**
```
□ Probe 3+ paths that CANNOT all be the same thing (/  /nonexistent-xyz  /robots.txt)
□ If ALL return the SAME status AND the same size/content-type -> you are testing a redirector,
  a catch-all, or an edge rule. NOT the app.
□ Compare baseline vs a random-garbage path. Identical response = your vector proved nothing.
```
Same family as SPA catch-all and the Akamai ladder above — but worse, because the pipeline reported
*coverage* instead of *blocked*.

**RULE — name the host's ROLE before testing it:**
| role | what it actually is | where the real surface is |
|---|---|---|
| **signed-URL redirector** | signs + 302s any path | signature / path-normalisation / cache-key behaviour |
| **CDN / static origin** | serves objects or a generic 404 | object paths, cache behaviour, error-page handling |
| **SPA catch-all** | 200 for everything | real API hosts / `Content-Type: application/json` |
| **app** | differentiated responses | the vectors you already have |

If the role is *not* "app", the generic vector list is the wrong tool. Test the role's own surface —
see `references/cdn-redirector-signed-url-audit.md`.

**RULE — a target that yields nothing still owes you the deep dive, on the real surface.** "0 findings"
is only honest once the role is identified *and* its own attack classes were exercised. Saying "clean"
after firing XSS/SQLi/IDOR at a 302 redirector is compliance-testing: you validated the pipeline's
bookkeeping, not the target.

**Also: never call a download/distribution host empty without touching a real artifact path.** The real
paths are public — release APIs (`data.services.<vendor>.com/products/releases?...`) return the actual
`download.<host>/<product>/<file>` URLs. Use them with `HEAD` / `Range: 0-0` so you never pull a gigabyte.

**Three questions, in order — do not skip to the third:**
```
1. Did every tool run?          (existing gates cover this)
2. Did every vector execute?    (ditto)
3. Did every vector reach the   <-- what was missing this session
   RIGHT target surface?           6 URLs, all a redirect = a NO
```

### ⛔ DON'T SABOTAGE A LIVE SERVICE TO PROVE A DoS (2026-10-10)

While probing the redirector a genuine **cache-poisoning → download-DoS** hypothesis appeared (the cache
key ignored the query string: three different `Signature=` values returned the same `Age`). Proving it
on a **real artifact path** would have served a cached error to real users — a DoS on a production
download service.

**STOP THERE. That is the line.** Prove the *mechanism* on a path that harms nobody (a non-existent path,
a throwaway key), state it as a **partially-verified hypothesis** with the reasoning, and hand the
destructive step to the vendor. Never break a live service to upgrade a finding one severity tier — it
breaches the programme's no-DoS clause and the operator's own rule.

Record it as: *mechanism established (cache key ignores query) · impact NOT executed on a real artifact
(no-DoS) · vendor to confirm*.

### ⛔ POC-PIPELINE + CVE EXPLOIT WORKFLOW (Neon 2026-09-23)

**LESSON:** poc-pipeline.py matched 16 CVE repos + 101 nuclei templates for Neon's tech stack (Cloudflare, React, Keycloak, Superset, Teleport, PostgreSQL). This is a REPEATABLE workflow:

```
Step 1: Match PoC repos by tech
  python poc-pipeline.py full <TARGET_URL> --tech "<tech1,tech2,...>"
  → plan.json = matched repos + nuclei templates

Step 2: Clone + run matched exploits
  git clone <matched_repo>
  pip install -r requirements.txt
  python exploit.py -t <TARGET> -m scan

Step 3: Run matched nuclei templates
  nuclei -l <matched_repos.txt> -t <template_dir> -severity critical,high
```

**Neon results:** CVE-2025-55182 (React2Shell RCE) — cloned, installed, ran scan → NOT VULNERABLE. CVE-2026-1529 (Keycloak) — manually tested → BLOCKED by Trusted Hosts. CVE-2023-27524 (Superset key) — forged JWT → NOT VULNERABLE (non-default key).

**Key learning:** The poc-pipeline matched CVEs but target was NOT vulnerable because the vulnerable FEATURE doesn't exist or was patched. This is different from "CVE scanner false positive" — the target uses the affected technology but the specific vulnerable feature is not exposed or has been patched.

**ALWAYS run poc-pipeline AFTER recon.** It connects tech detection → CVE matching → exploit execution in one flow.

### ⛔ POC-COMPACT EMPTY DIRS (Neon 2026-09-23)
**LESSON:** `D:/data/hermes/poc-compact/` contains 2,223 directories but ZERO files. The repos were never downloaded — only directory structure was created. Do NOT assume poc-compact has usable exploit code.

**Verification:** `find D:/data/hermes/poc-compact -type f | wc -l` → expect 0

**Correct workflow:** Use `poc-pipeline.py` instead — it clones repos from GitHub on demand, not from local poc-compact.

### ⛔ SQLMAP PYTHON 3.14 INCOMPATIBILITY (Neon 2026-09-23)
**LESSON:** sqlmap fails on Python 3.14: `No module named sqlmap.__main__`. The `pip install sqlmap` succeeds but `python -m sqlmap` fails.

**Fix:** Use manual SQLi payloads from hackskill-sqli reference file as fallback. Or try `python -c "from sqlmap.lib.core.data import *; from sqlmap.sqlmap import main; main()"`.

### ⛔ KEYCLOAK TRUSTED HOSTS DEFENSE-IN-DEPTH (Neon 2026-09-23)
**LESSON:** Even when port 8080 bypasses Cloudflare WAF and exposes Keycloak origin directly, Keycloak's Trusted Hosts policy still blocks client registration and unauthorized org creation. The security control is enforced at the APPLICATION layer, not the WAF layer.

**Test pattern:** When naabu finds non-standard ports (8080, 8443), test Keycloak/OAuth endpoints directly:
1. Password brute force (master + prod realm)
2. Client registration (with evil redirect_uri)
3. Device code flow
4. CIBA (backchannel authentication)
5. Client credentials grant

**Result pattern:** All return `unauthorized_client`, `insufficient_scope`, or `invalid_client` — defense-in-depth working correctly.

### ⛔ CVE-2025-29927 TEST METHOD (Neon 2026-09-23)
Next.js middleware bypass via `x-middleware-subrequest` header. Test against any Next.js target:
```bash
# 1. Detect Next.js
curl -sI "https://TARGET" | grep -iE "x-nextjs|server.*vercel"

# 2. Test bypass header
curl -sL -H "x-middleware-subrequest: true" "https://TARGET/dashboard"

# 3. Test header value variants
for h in "true" "1" "page" "routes" "middleware"; do
  curl -sL -o /dev/null -w "%{http_code}" -H "x-middleware-subrequest: $h" "https://TARGET/dashboard"
done
```
If middleware is bypassed → protected pages return 200 instead of 302/401.

### ⛔ DON'T STOP EARLY — USER CORRECTION (Neon 2026-09-23)

**User correction:** "Cari lagi celah lain, kan PoC varian attack yg sy kasih kmrn ribuan" / "Yakin kamu udh jalankan semua file dan tools sesuai phase? Bukan hanya curl aja?" / "Periksa lagi dgn all phase Dan all varian attack"

**The pattern:** Agent ran ~6 tools (subfinder, httpx, ffuf, dalfox, curl manual), found nothing, concluded "well-hardened." User was frustrated — there are 15+ tools available and 30+ vectors with 5-10 variations each.

**RULE:** Before concluding "no findings," verify ALL of these were EXECUTED (not just listed):
1. All 15 tools run (subfinder, httpx, nuclei, ffuf, dalfox, katana, gau, waybackurls, naabu, arjun, kxss, commix, gobuster, sqlmap, poc-pipeline)
2. poc-pipeline.py matched + cloned + ran
3. All 30 vectors tested with ≥3 attack variations each
4. Source maps, JS bundles, historical URLs (gau) analyzed
5. Port scan (naabu) completed — non-standard ports checked

**If user says "cari lagi" = you missed something. Stop defending, start testing.**

### ⛔ "JGN KASIH HASIL TEORITIS" — REPEATED USER CORRECTION (Neon 2026-09-23)

**User correction (4x):**
- "Jgn kasih hasil teoritis, kasih impact yg beneran berdampak"
- "Apa efeknya? Harus jelas merugikan br kamu jadikan temuan"
- "Sy sdh blg temuan informational itu, tidak ush kamu tampilkan, by design"
- "Phishing jg sama, kenapa masih diulangi"

**The pattern:** Agent found OIDC config public, Superset config leaked, Teleport version disclosed, source maps accessible, OAuth callback session codes. Presented ALL as Medium severity bounty candidates. User rejected ALL — correctly.

**Why rejected (specific to each):**
| "Finding" | Why it's NOT a finding |
|-----------|----------------------|
| OIDC `.well-known/openid-configuration` | Public by OIDC spec — every provider exposes this |
| Superset `data-bootstrap` config | By-design — hydrates React UI client-side |
| Teleport `/webapi/ping` | Public discovery endpoint — all Teleport clusters |
| Source maps (login theme) | Login theme only — not application code |
| OAuth callback session codes | Fresh per request, expire quickly, can't be reused |
| Version disclosure | No exploit chain without authenticated access |
| Phishing with real URLs | Requires social engineering — out of scope for most VDPs |

**THE RULE:** A finding must demonstrate REAL HARM with a reproducible PoC:
- Can you access data you shouldn't? (IDOR, auth bypass)
- Can you take over an account? (session hijack, OAuth abuse)
- Can you execute code? (RCE, SSTI, deserialization)
- Can you steal money? (race condition, price manipulation)
- Can you access internal infrastructure? (SSRF, cloud metadata)

If the answer to ALL of these is "no, but..." — it's NOT a finding. Informational-by-design is NOT a finding. Do NOT present it. Do NOT repeat it after user rejects it.

### ⛔ SQLMAP PYTHON 3.14 INCOMPATIBILITY (Neon 2026-09-23)

**LESSON:** sqlmap module error on Python 3.14: `No module named sqlmap.__main__`. Fix: use `sqlmap.py` directly or run via `python -c "from sqlmap.sqlmap import main; main()"`. Alternative: use manual SQLi payloads from hackskill-sqli reference file as fallback.

### ⛔ NAABU FINDS NON-STANDARD PORTS (Neon 2026-09-23)

**LESSON:** naabu found port 8080 open on console.neon.tech and oauth2.neon.tech. Port 8080 served Keycloak login page directly (bypassing Cloudflare WAF). However, Keycloak's Trusted Hosts policy still blocks client registration even on the direct port. This is defense-in-depth working correctly.

**RULE:** When naabu finds non-standard ports (8080, 8443, 3000, 5000, etc.), ALWAYS test:
1. Direct origin access (bypass WAF/CDN)
2. Admin/debug endpoints (/admin, /actuator, /debug, /metrics)
3. Keycloak/OAuth endpoints without WAF protection
4. Default credentials on exposed services

---

### ⛔ THEORETICAL FINDINGS MUST BE REJECTED (Neon 2026-09-23)
**User correction:** "Jgn kasih hasil teoritis, kasih impact yg beneran berdampak" / "Apa efeknya? Harus jelas merugikan br kamu jadikan temuan"

**The pattern:** Agent found OIDC config public, Superset config leaked in HTML, Teleport version disclosed, source maps accessible. Presented all as Medium severity bounty findings. User rejected ALL — correctly.

**Why they were rejected:**
- OIDC `.well-known/openid-configuration` is **public by spec** — every OIDC provider exposes this
- Superset `data-bootstrap` config is **by-design** — it hydrates the React UI
- Teleport `/webapi/ping` is **discovery endpoint** — all Teleport clusters expose this
- Source map was for **login theme only** — not application code
- Version disclosure has **no exploit chain** without authenticated access

**THE RULE:** A finding must demonstrate REAL HARM with a reproducible PoC:
- Can you access data you shouldn't? (IDOR, auth bypass)
- Can you take over an account? (session hijack, OAuth abuse)
- Can you execute code? (RCE, SSTI, deserialization)
- Can you steal money? (race condition, price manipulation)
- Can you access internal infrastructure? (SSRF, cloud metadata)

If the answer to ALL of these is "no, but..." — it's NOT a finding. Informational-by-design is NOT a finding.

**See:** `references/neon-case-study.md` — full case study with 12 tools, 30 vectors, 3 CVEs, 0 bounty findings.

### ⛔ WELL-HARDENED TARGET: CLOUDFLARE+IAP+SSO (Certinia 2026-09-20)
**Pattern:** Target uses Cloudflare Access (73+ hosts) + Google IAP (30+ hosts) + Okta SSO + Salesforce platform.

**Indicators this target is exhausted:**
- 80/166 hosts return CORS+CREDS on 302 redirect pages (not actual data)
- All internal services behind auth proxies
- S3 buckets found but contain only dev/test data (already reported by other researchers)
- finding_gate.py + chain_builder.py both confirm: "no survivors, no chain reaches impact goal"
- Nuclei times out (Cloudflare blocks templates)
- ffuf returns only SPA catch-all (Angular/Vercel behavior)

**Honest verdict:** "Exhausted — no bounty-worthy findings. Target has Cloudflare Access + Google IAP + Okta SSO + Salesforce platform. All attack surfaces behind auth. S3 findings are P4 at best (dev data, already reported)." → Skip target, find another.

**Tool execution order addition (Phase 2):**
```
After automated scanning, BEFORE manual testing:
  Run finding_gate.py on candidates → check for survivors
  Run chain_builder.py → check if any chain reaches impact
  If both confirm "no survivors" → document and consider stopping early
```


---

## Companion Reference — `poc-technique-atlas` (additive, never overrides)

Per-test-type method shelf (28 classes / ~1,950 techniques). Read the matching class file
during the phase — **on-demand, does NOT count against the phase context budget**. At Phase 0E,
check `skills/security/poc-technique-atlas/references/distilled/00-INDEX.md` first. Detection observables: `skills/security/poc-technique-atlas/references/nuclei-detection.md`.
