## Workflow

### ⛔ HARD STOP — PRE-GENERATION SEQUENCE

**DO NOT generate PDF, screenshots, or ANY deliverable until Phase 0-2 ALL pass.**

The mandatory sequence is:
```
Phase 0: DEEPDIVE GATE (exhaust all attack surfaces)
    ↓ PASS
Phase 1: VRT COMPARISON (map each finding to VRT category)
    ↓ PASS
Phase 2: VIABILITY GATE (filter out by-design / informational)
    ↓ PASS
Phase 3: DEEP-DIVE EXPANSION (expand reportable findings)
    ↓
Phase 4: PER-FINDING ISOLATION (directory structure)
    ↓
Phase 5: GENERATE & DELIVER (PDF + screenshots + evidence)
```

**User correction (enforced):** "Cek dl temuan tsb, kompare dgn vrt bugcrowd, jgn lupa cek by design atau informasi aja itu" — agent generated 4 PDFs before checking VRT viability, ALL 4 turned out by-design/informational. Wasted full report generation cycle.

**If you catch yourself writing gen_pdfs.py or gen_poc.py BEFORE completing Phase 2, STOP IMMEDIATELY and run the viability gate first.**

### Phase 0: DEEPDIVE GATE (MANDATORY)
Before asking user which findings to include, or generating any report:
1. Complete FULL recon + analysis + verification across ALL attack angles
2. Use ALL tools: curl, browser, browser_console, execute_code, vision_analyze
3. Test: CORS, auth, IDOR, injection, SSRF, subdomain takeover, S3, GraphQL, XSS, SSTI, open redirect, email security, 3rd-party service enumeration
4. Investigate infrastructure: pre-prod, staging, third-party APIs, JS bundles, CDN/WAF
5. **Infrastructure Pivot Checklist** (when web-app attacks hit walls — MANDATORY before concluding clean):
   - Staging/dev subdomains: `staging`, `dev`, `test`, `qa`, `preprod`, `pre-production`, `beta`, `alpha`, `demo`, `sandbox`, `staging-api`, `dev-api`, `test-api`
   - Cloud storage: S3 bucket enumeration (`upscrolled`, `upscrolled-prod`, `upscrolled-media`, `upscrolled-assets`, `upscrolled-uploads`, `upscrolled-images`, `upscrolled-cdn`, `upscrolled-files`, `upscrolled-static`, `dna-media`, `dna-content`)
   - Email security: SPF (`dig TXT upscrolled.com`), DMARC (`dig TXT _dmarc.upscrolled.com`), DKIM (selectors: default, google, dkim, mail, s1, s2, selector1, selector2)
   - Pre-production deployments: Vercel (`*.vercel.app`), Netlify (`*.netlify.app`), Cloudflare Pages
   - GitHub: organization repos, leaked secrets, config files
   - PaaS: Supabase (`*.supabase.co`), Firebase (`*.firebaseapp.com`)
   - API versioning: `/v1/`, `/v2/`, `/api/v1/`, `/api/v2/`
   - GraphQL: introspection on all API endpoints
   - **⚠️ FALSE POSITIVE PITFALL:** When checking Vercel deployments (`project-name.vercel.app`), always verify the page content is actually the TARGET's application, not a different project with a similar name. Check: canonical URL, og:site_name, app title, tech stack mismatch. A 200 on `X.vercel.app` does NOT mean X is a staging deployment — it could be an unrelated third-party project.
6. ONLY THEN present findings list and ask user which to include in report
7. User preference (hard rule): "Cari dl lebih deepdive pakai semua tools dan skill, baru tanya sy sblm generate laporan"

### Phase 1: VRT COMPARISON + PROGRAM SCOPE (MANDATORY before report)
For EACH finding, perform TWO checks:

**1A. VRT Mapping:**

**Programmatic lookup (preferred — faster than manual search):**
```python
import json, urllib.request
url = "https://raw.githubusercontent.com/bugcrowd/vulnerability-rating-taxonomy/master/vulnerability-rating-taxonomy.json"
data = json.loads(urllib.request.urlopen(url).read())

def deep_search(node, keywords, path=""):
    results = []
    name = node.get("name", "").lower()
    nid = node.get("id", "")
    priority = node.get("priority")
    if any(kw.lower() in name for kw in keywords):
        results.append({"id": nid, "name": node["name"], "path": path, "priority": priority})
    for child in node.get("children", []):
        results.extend(deep_search(child, keywords, path=f"{path} > {node['name']}"))
    return results

# Example: search for API, injection, misconfiguration keywords
matches = deep_search(data["image"], ["API", "Injection", "Misconfiguration", "Exposed", "Disclosure"])
for m in sorted(matches, key=lambda x: x["priority"] or 99):
    print(f"{m['id']}: {m['path']} > {m['name']} (P{m['priority']})")
```

Key VRT categories to search for (sorted by frequency in web bug bounty):
- **Server Security Misconfiguration** → exposed admin, debug interfaces, misconfig (P3-P5)
- **Cloud Security > Misconfigured Services** → insecure API endpoints (P4)
- **Sensitive Data Exposure** → internal IP, secrets disclosure (P4-P5)
- **Injection** → SQL, NoSQL, command injection (P1-P3)
- **Broken Access Control** → IDOR, BOLA, privilege escalation (P1-P3)
- **Cryptographic Failures** → weak algorithms, exposed keys (P2-P4)

**Manual fallback:** Search by `name`, `id`, and keywords. Extract VRT ID, priority baseline, and variant path. If VRT priority is `None` (no baseline) — researcher argues severity with evidence.

**1B. Program Scope Alignment (CRITICAL — often missed!):**
Programs have their OWN scope definitions that go beyond generic VRT. You MUST check the actual program page.

1. **Extract program page** — use `web_extract(urls=['https://bugcrowd.com/engagements/<program>'])`. The HTML embeds a JSON blob with full program config (scope, severity guidelines, focus areas, out-of-scope exclusions).
2. **Check HIGH-VALUE FOCUS AREAS** — many programs list specific areas they want tested (e.g., "GraphQL: BOLA/IDOR", "Money Movement: race conditions"). If a finding matches a listed focus area, it's STRONGER than generic VRT.
3. **Check PROGRAM-SPECIFIC SEVERITY** — programs often define their own P1/P2/P3 examples that may differ from VRT baseline. Use the PROGRAM's severity (not just VRT) for the report.
4. **Check OUT-OF-SCOPE exclusions** — programs explicitly list what's excluded (e.g., "social engineering", "MITM positioning", "missing cert pinning"). If a finding requires an out-of-scope technique, it WILL be rejected.
5. **Verdict table** — produce a mapping table per finding: VRT Match | VRT Priority | In Scope? | Program Match | Verdict (SUBMIT/WEAK/REJECT)

#### ⛔ Read the brief ONCE and save it to disk BEFORE planning tests (scope drifts)

Scope is not just the target list — it is a set of *exclusions* you will otherwise plan straight into.
Do this at session start, not at report time:

```bash
# dump the brief to <workspace>/recon/brief_rules.md and grep it before every plan
grep -inE 'out of scope|strictly forbidden|temporarily|do not|must use|test propert' recon/brief_rules.md
```

Four traps that cost a whole planning cycle (Tripadvisor 2026-10 — every one of these was in the brief):

- **OOS can list BRANDS/subsidiaries, not just paths.** The brief's "brands owned by the parent but
  operating independently" clause put **Viator, TheFork/LaFourchette, CruiseCritic, Jetsetter, SeatGuru,
  HelloReco** entirely out of scope while `*.tripadvisor.com` stayed in — i.e. the apex domain being in
  scope tells you nothing about a subsidiary brand. Before adding a brand's domain to your plan, search
  the brief for it. Generally: enumerate the company's brands, then check each one's MAIN domain against
  the OOS list (also check minority-investment domains, e.g. `traxo.com`).
- **A whole *class* can be temporarily OOS.** "IDOR in property-owner features is temporarily out of
  scope" removes an entire test family — so does "no testing that causes disruption". Re-read the brief
  each session; "temporarily" means it can come back.
- **Content/entity rules are a gate, not advice.** "Interacting with legitimate live properties/customers
  is strictly forbidden (even marking a review helpful)" + "use test properties only" means many authed
  features are **untestable without the program's test-entity list**. Get that list EARLY (it lives in the
  brief, and text-extraction can drop the links — capture the raw HTML, not just the markdown). If you
  cannot get it, say the feature is blocked and ask the operator — never exercise the flow against a live
  entity "just to see", and never label an account/artifact with anything other than the program's
  required marker (e.g. the string `bugcrowd` in the name and User-Agent).
- **Enumeration/rate-limit/version-disclosure findings are usually $0** in self-hosted and VDP programs —
  the brief will say so. Don't spend a cycle proving them.

Note where the exclusion bites: it is checked AFTER VRT mapping (step 1A) and BEFORE deep-dive expansion
(Phase 3), so a finding can map to a valid VRT category and still be rejected.

**Pitfall (learned from Chime):** VRT says "Race Condition" has no fixed priority (N/A). But the PROGRAM explicitly lists "race conditions leading to double spending" as P1 Critical. **Program-specific severity overrides generic VRT baseline** when arguing for classification.

**Pitfall (learned from Chime):** "Dev/QA environments in scope" sounds good, but if the program says "testing permitted in QA/dev environments", then exposed dev portals are BY DESIGN for that program — not reportable.

#### ⛔ EXCLUSION CROSS-REFERENCE (MANDATORY — HARD STOP before Phase 3)

**This is SEPARATE from VRT mapping and MUST be done as a dedicated step.** A finding can map to a valid VRT category AND still be excluded by the program.

**Concrete example (Chime 2026-09):**
- Program page explicitly lists: "Publicly exposed API keys meant for public use (e.g., DataDog client tokens, Google Maps keys)"
- Datadog injection findings mapped to valid VRT categories (P3-P4)
- But DataDog client tokens are EXPLICITLY named in exclusions → REJECT
- Social engineering impact also excluded → findings relying on "aids phishing" → REJECT
- Result: 5 of 6 generated PDFs would have been instantly rejected by triage

**Mandatory cross-reference table (produce this for EVERY candidate finding):**

| Finding | VRT Match | VRT Priority | Matches Exclusion? | Exclusion Text | Verdict |
|---------|-----------|-------------|-------------------|----------------|---------|
| F1 | Cloud Sec > Misconfig | P4 | **YES** | "DataDog client tokens" | REJECT |
| F2 | Sensitive Data > Debug | P5 | **YES** | "debug info disclosures" | REJECT |
| F3 | Server Misconfig | P3 | **NO** | — | SUBMIT |

**If you catch yourself writing gen_pdfs.py before this table is complete with at least one SUBMIT finding, STOP IMMEDIATELY.**

#### ⚠️ GEO-BLOCKED / WAF-BLOCKED PATHWAY (when live testing impossible)
When WAF/geo-restriction blocks all live API testing (e.g., Cloudflare Error 1009, geo-restriction, IP blacklisting):

**STEP 0 (BEFORE falling back to static analysis): Enumerate Non-Cloudflare Infrastructure Endpoints**

Cloudflare usually protects the main app domain, but infrastructure microservices often sit OUTSIDE the WAF. These are gold — they have real production data but weaker protections.

**Enumeration technique (3 parallel approaches):**
1. **Certificate Transparency** — `curl -s "https://crt.sh/?q=%.chime.com&output=json" | jq -r '.[].name_value' | sort -u` — reveals ALL subdomains from public CT logs, including internal services that don't appear in DNS brute-force
2. **Decompiled app strings** — Extract URLs from Hermes bundle: `grep -oE 'https?://[a-zA-Z0-9._-]+\.chime\.[a-z]+' all_strings.txt | sort -u`
3. **HTTP probe ALL subdomains** — For each discovered subdomain, check HTTP status + Cloudflare presence:
```bash
# Quick probe — check if Cloudflare-protected
for sub in $(cat subdomains.txt); do
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$sub/" 2>/dev/null)
  cf=$(curl -sI --max-time 5 "https://$sub/" 2>/dev/null | grep -i "cf-ray")
  echo "$sub → $status | CF=$([ -n "$cf" ] && echo YES || echo NO)"
done
```

**High-value non-Cloudflare endpoint categories:**
- **Health/readiness endpoints**: `*.chime.com/health`, `/readiness`, `/healthcheck` — leak DB names, AWS regions, container names, deployment state
- **Monitoring forwarders**: `datadog-forwarder*.chime.com`, `statsd*.chime.com`, `newrelic*.chime.com` — metrics ingestion APIs often accept unauthenticated POSTs
- **Event routers**: `event-router*.chime.com/track`, `analytics*.chime.com/ingest` — event ingestion with Pydantic/FastAPI validation errors that reveal internal schema
- **SSO redirect chains**: `enterprise*.chime.com`, `sso*.chime.com`, `idp*.chime.com` — 302 redirect chains leak OAuth provider IDs, Okta app IDs, LumApps org IDs
- **Developer tools**: `research*.chime.com`, `jupyter*.chime.com`, `grafana*.chime.com` — exposed internal tools
- **Mobile config**: `mobile-state*.chime.com` (S3 buckets), `config*.chime.com`, `features*.chime.com` — feature flags, app config

**Pitfall (Chime 2026-09):** Cloudflare blocked ALL main app requests (error 1009 geo-restriction). But discovered `datadog-forwarder.chime.com` (no Cloudflare), `event-router.chime.com` (no Cloudflare), `nd.chime.com` (no Cloudflare), `interchange.chime.com` (no Cloudflare), `research.chime.com` (no Cloudflare) — all returning real production data.

**Specific findings from non-Cloudflare endpoints:**
- `datadog-forwarder.chime.com` → accepts POST to `/api/v2/series` without auth (400, not 401) — metrics injection
- `event-router.chime.com/track` → accepts empty events (200 OK), Pydantic validation errors reveal schema (`event_context`, `event_id`, `fully_qualified_schema_name`, `json_payload`, `sent_at` required)
- `nd.chime.com/health` → returns DB name `ndwcdb-*`, region `us-east-1`, container `ndsprod`
- `interchange.chime.com` → 302 to LumApps SSO with Okta, leaks IDs: LumApps Org `8729011317770419`, Login Provider `[REDACTED]`, Okta App `chime_lumapps_2`
- `research.chime.com` → exposed Django debug page with stack trace

**THEN, if non-Cloudflare endpoints also fail:**
1. **Do NOT skip** — static analysis of decompiled bundles/code can still produce valid findings
2. **Compile report with caveat**: "Based on static code analysis. Requires live verification from unrestricted IP."
3. **Evidence**: decompiled source code snippets, schema definitions, code-level proof
4. **Impact justification**: conservative — argue based on what the CODE allows, not what's been tested live
5. **Vetting quality**: static findings are weaker than live PoC — flag this honestly in the report
6. **User may choose** to submit as-is or defer until live testing is possible

**Pattern (Chime case):**
- Cloudflare Error 1009 blocked all API requests from non-US IP
- Decompile React Native Hermes bundle → extract GraphQL schema (985 operations)
- Found 11 mutations without idempotency keys vs 3 with → race condition vulnerability
- Found Float! type on financial mutations vs CurrencyAmountInput! → negative amount injection
- Submitted report with "requires live verification" caveat

### Phase 2: VIABILITY GATE (MANDATORY before report)
Filter findings through viability check:
- **BY DESIGN**: OAuth open registration on open platform, PostHog write keys (designed for client-side), Algolia secured API keys (designed for client-side with filter restrictions), SDK API keys (Amplitude, RevenueCat, Mixpanel, Segment, Mux — all designed for client-side), dev/QA environments EXPLICITLY listed as "testing permitted" → SKIP
- **INFORMATIONAL ONLY**: Missing security headers without exploit chain, software version disclosure, weak CSP without injection point → SKIP
- **REPORTABLE**: Real misconfiguration with demonstrable impact from EXTERNAL perspective → INCLUDE
- User hard rule: "pastikan bukan by design, ataupun informational"

#### ⚠️ ZERO FINDINGS PATHWAY (when all findings fail viability gate)
If Phase 2 yields ZERO reportable findings:
1. **Do NOT generate reports** — stop immediately, no PDFs
2. **Infrastructure pivot** (if not already done) — run Phase 0 step 5 checklist
3. **Re-evaluate borderline findings** — check if any P4/P5 findings can be chained:
   - Weak CSP + any reflected input = P3 (chainable)
   - CORS * on analytics proxy + no rate limiting = P4 (injectable)
   - API keys in JS + SSRF endpoint = P2 (chainable)
4. **Present honest assessment to user** with options:
   - Submit info-only reports (P5, low bounty but documentation)
   - Pivot to a different Bugcrowd VDP target
   - Push harder on 1-2 specific angles (deeper auth bypass, account takeover, etc.)
   - Generate security summary (not bounty submission, just documentation)
5. **Never force a finding** — if it's by-design, it's by-design. Submitting false positives damages researcher reputation.
6. Record the target as "exhausted — no reportable findings" in session notes for future reference.

### Phase 3: DEEP-DIVE EXPANSION (per finding)
For each reportable finding, expand attack surface:
- **CORS**: Origin reflection test, null origin, credentialed requests, preflight behavior, cross-subdomain scan
- **Auth**: Session fixation, token leakage, OAuth flow, password reset
- **IDOR**: Enumerable IDs, cross-user access, privilege boundaries
- **SSRF**: Internal IP ranges, cloud metadata endpoints, protocol smuggling
- **Injection**: All injection types, encoding bypasses, WAF evasion
- Document: what was tested, what worked, what was blocked, why

### Phase 4: PER-FINDING ISOLATION (User hard rule)
Each finding gets its OWN:
- Directory: `~/report-dir/F1-finding-name/`, `~/report-dir/F2-finding-name/`
- POC screenshots: `01-*.png`, `02-*.png`, etc. in finding directory
- PDF report: Self-contained, embeds its own screenshots
- Filename: `{Program}-{F{N}}-{ShortTitle}.pdf`
- **NEVER combine findings into single PDF** — user explicitly rejected this

### Phase 5: GENERATE & DELIVER

**⚠️ MANDATORY PRE-CHECK before generating ANY output:**
1. Define ALL PoC data constants ONCE at the top of the generation script (target-specific: endpoints, IDs, tokens, field names)
2. These SAME constants MUST drive: PDF text, screenshot text, submission.md, code blocks
3. Verify: every endpoint, ID, field name, and request body appears IDENTICALLY in all 3 outputs

Steps:
1. Reload skill: skill_view(name='bug-bounty', file_path='references/reporting.md')
2. Load writeup examples: read_file('references/writeup-index.md')  → benchmark report quality
3. Capture evidence: browser screenshots OR terminal curl output
3. Generate per-finding POC screenshots (Pillow, terminal-style) — **use TARGET-SPECIFIC constants, NOT hardcoded values from previous targets**
4. Generate per-finding PDF with embedded evidence (reportlab) — **full format: Executive Summary → CVSS Table → Technical Details → Code Evidence → Steps to Reproduce → POC Screenshots → Impact Analysis → Negative Tests → Remediation → Disclosure Statement**
5. Save all to per-finding directories
6. Send via MEDIA:<path> to the requesting chat/topic
7. Send evidence files via MEDIA:<path>

**⚠️ "Already done?" check before telling user PDFs are ready:**
- Are screenshots EMBEDDED in the PDF (reportlab Image flowable), not just saved separately?
- Does the PDF include: CVSS vector table, Negative Tests, Remediation, Disclosure Statement?
- Is every ID/endpoint/field name in screenshots the SAME as in PDF text and submission guide?
- If any answer is NO → regenerate before delivering.

