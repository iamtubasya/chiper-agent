# Batch Self-Hosted Bounty Workflow (Excel-Driven)

> When user provides an Excel/CSV tracking sheet of bounty targets and asks to "start from #1" or "go through all active".

## Trigger Conditions
- User says "mulai dr no urut pertama" / "start from #1" / "go through all active"
- User provides a tracking spreadsheet (XLSX/CSV) with bounty programs
- User specifies time budget per target (e.g., "24 jam per project")
- User wants findings compiled in per-finding folders with PDF

## Workflow Steps

### 1. Parse the Tracking Sheet
```python
import openpyxl
wb = openpyxl.load_workbook(path)
ws = wb['Sheet 2']  # User specifies which sheet
# Filter by status column = "ACTIVE" (skip LIKELY, UNKNOWN, INACTIVE)
active_targets = [row for row in ws.iter_rows(min_row=2) if row[status_col].value == 'ACTIVE']
```

**Key:** Ask user which sheet to use. Parse ALL columns — program name, platform, max bounty, scope, status.

### 2. Sort by Complexity (Simplest → Deepest)
User specified order: start from simplest targets, progress to deep-dive.
**Heuristic sorting (simplest first):**
1. Static websites / brochure sites (minimal attack surface)
2. E-commerce / SaaS with standard auth
3. API-heavy platforms
4. Financial / crypto / multi-service platforms (most complex)

Or follow user's explicit numbering from the spreadsheet.

### 3. Per-Target Audit Cycle (24h budget — EXHAUSTIVE)

**⛔ HARD RULE: Find as MANY exploits as possible per target. Do NOT stop at first finding.**

User explicitly corrected: *"Sy kasih waktu temukan exploit sebanyak mungkin dalam waktu 24 jam. Kalau temuan udh mentok, kamu deepdive, kl udh juga, kamu crosschek ulang, sampai waktu 24 jam tsb tercapai baru kamu generate pdf."*

```
Hour 0-1:   Scope verification + VDP policy check
Hour 1-3:   Recon (subdomains, tech stack, API discovery)
Hour 3-6:   Low-hanging fruit (unauth endpoints, info disclosure, misconfigs)
Hour 6-12:  Auth/IDOR/race condition testing
Hour 12-18: Deep-dive (SSRF, injection, business logic, chain attacks)
Hour 18-22: Cross-check ALL previous findings + re-verify
Hour 22-24: Generate ONE comprehensive PDF covering ALL findings
```

**Exhaustion Protocol (when stuck):**
1. **Deepdive** — new attack vectors, lesser-tested endpoints, edge cases
2. **Cross-check** — re-verify all previous findings, test variations, chain combinations
3. **Infrastructure pivot** — S3, pre-prod, staging, third-party APIs, JS bundles, non-Cloudflare services
4. **Only then** — generate single consolidated PDF with ALL findings

**CRITICAL: One PDF per project, NOT per finding.** PDF must include:
- ALL findings (not just the first one)
- PoC for each finding
- Screenshots/evidence for each
- Impact assessment for each
- Consistent data across all sections (IDs, endpoints, request bodies, CVSS)
- Separate per-finding sections but in ONE document

**Do NOT:**
- ❌ Stop after first finding
- ❌ Generate PDF before time budget is exhausted
- ❌ Create separate PDFs per finding
- ❌ Declare "no finding" without exhausting infrastructure + JS bundles + third-party

### 4. Finding Quality Gate (per-finding, BEFORE including in PDF)
Apply the bug-bounty skill's Finding Quality Gate. For each candidate finding:
- ✅ Impact data, systems, accounts, users, or funds
- ✅ Reproducible from clean state
- ✅ NOT by-design, informational, or standard practice
- ✅ Can be verified by a triager

**Self-filter aggressively.** If you need to explain WHY it's a finding → it's probably informational. Real bugs speak for themselves.
Skip anything that doesn't pass ALL gates. Don't pad with weak findings.

### 5. Per-Project Output Structure
```
D:\data hermes\bugbounty\self-hosted-bounty\
├── <target-name>/
│   ├── <Target>_Full_Report.pdf          ← ONE comprehensive PDF, ALL findings
│   ├── evidence/                         ← raw evidence files
│   │   ├── f1_<name>.json                ← API response / curl output
│   │   ├── f1_cors.txt
│   │   ├── f2_<name>.json
│   │   └── ...
│   └── screenshots/                      ← HTML-rendered evidence screenshots
│       ├── f1_01_*.html                  ← reproducible evidence pages
│       ├── f1_02_*.html
│       └── ...
```

**NOT per-finding folders.** One folder per project, one PDF per project containing ALL findings.

### 6. Evidence Rules
- **ALL evidence must be real** — actual curl responses, tool output, screenshot captures
- **NO watermarks** on screenshots or PDFs
- **NO fake data** — no fabricated API responses, no mock JSON
- **Consistency required** — PDF code blocks must exactly match the evidence files
- **Reproducible** — a triager should be able to follow PoC steps and get the same result
- **Screenshot capture** — use `browser_vision` for web UI evidence, `execute_code` with curl for API evidence

### 7. Progress Tracking
After each target, update the user with:
- Number of findings found / total targets completed
- Skip reasons for targets with zero findings
- Next target name + estimated time remaining

### 8. Session Continuity
If session context is compacted or interrupted:
- Re-read the tracking spreadsheet to get target list
- Check output directory for completed folders
- Resume from next uncompleted target

## Directory Conventions
- **Windows paths:** `D:\data hermes\bugbounty\self-hosted-bounty\` (backslash in local paths)
- **Terminal paths:** `/d/data hermes/bugbounty/self-hosted-bounty/` (forward slash in bash)
- **PDF generation:** Always via `execute_code` + reportlab (terminal lacks wkhtmltopdf)
- **Evidence capture:** `execute_code` with subprocess curl (reliable, verifiable)
- **PDF verification:** Load with pymupdf after generation to verify page count and content

## Common Pitfalls
- **Don't accept "clean" after WAF blocks** — pivot to infrastructure, JS bundles, third-party APIs
- **Don't pad findings** — if a target is genuinely clean, say so and move on
- **Don't rush PDF** — verify all evidence first, generate PDF last
- **Excel parsing** — `python` not `python3` on this Windows system; use `execute_code`
- **Missing terminal commands** — `head`, `grep`, `ls` not in bash; use `execute_code` with Python
- **⚠️ E-commerce/IoT sites are "informational traps"** — Product APIs, category dumps, pricing data, public catalog endpoints are ALL by-design. These sites exist to sell products; their catalog IS the public product. Reporting this as a finding WILL be rejected. Focus on: auth bypass, IDOR on user data, business logic (checkout/gift card/coupon), stored XSS, race conditions. See `references/adafruit-2026-findings.md` for detailed case study.
- **24-hour rule is NON-NEGOTIABLE** — User explicitly said "jgn pindah project sebelum genap 24 jam audit nya." Even if all standard vectors are negative, continue with infrastructure pivots, JS bundle deep analysis, business logic tracing, and cross-checking. Only exception: user explicitly releases you early.
