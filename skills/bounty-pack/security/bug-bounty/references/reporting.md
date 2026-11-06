# Reference: Reporting, Severity & Triage (v2)

> The report is the final product. A great bug with a weak report = rejected/underpaid.
> A clear report with credible impact = accepted and paid properly.

## Standard Report Structure
1. **Title** — concise & specific: `[Class] in [component] allowing [impact]`.
   Example: "IDOR in /api/v2/invoices allows cross-tenant invoice access".
2. **Summary** — 2–3 sentences: what the bug is, where, why it matters.
3. **Severity** — rating + CVSS vector + impact argument (see below).
4. **Steps to Reproduce** — numbered, precise, reproducible without guessing.
5. **Proof of Concept** — request/response, screenshots, or script (Web3 fork test).
6. **Impact** — real business/user impact. Explain realistic attack scenario.
   If there's chained impact not executed, explain narratively.
7. **Remediation** — actionable fix recommendation for dev team.
8. **Supporting material** — references, notes, environment.

### Traits of Accepted Reports
- 100% reproducible from written steps.
- Impact explained from business perspective, not just technical.
- Neutral & professional — no hype, no threats, no "give big bounty pls".
- One bug per report (unless interdependent chain).
- Sensitive data redacted.

### ⚠️ Informational → Valid Finding: Chaining is Mandatory
Triagers reject "information-only" reports. Before writing, ask:
1. Can the data exposure lead to phishing/social engineering → ATO?
2. Can the read-only IDOR be chained with another vuln for write/execute?
3. Can the info leak enable targeted attacks on specific high-value users?
4. Is there an economic impact chain? (e.g., data leak → targeted manipulation)

**Example chain (Aurory):**
- IDOR on wallet holdings (info) → attacker profiles target's rare items →
  sends phishing trade offer → steals NFT = HIGH finding
- Unauthenticated account creation (info) → free items per account →
  mass-create 1000 accounts → economy inflation = CRITICAL finding

**If no chain exists, DO NOT submit as-is.** Pivot to another finding.

---

## Severity & CVSS (v3.1 / v4.0)
CVSS provides a number; **impact argument** provides credibility. Include both.

**Base metrics (v3.1) quick reference:**
- **AV** Attack Vector: Network (N) / Adjacent (A) / Local (L) / Physical (P)
- **AC** Attack Complexity: Low (L) / High (H)
- **PR** Privileges Required: None (N) / Low (L) / High (H)
- **UI** User Interaction: None (N) / Required (R)
- **S** Scope: Unchanged (U) / Changed (C) — impact jumps to another component
- **C/I/A** Confidentiality/Integrity/Availability impact: None (N) / Low (L) / High (H)

**Score ranges:** 0.0 None · 0.1–3.9 Low · 4.0–6.9 Medium · 7.0–8.9 High · 9.0–10.0 Critical

**Honest scoring:**
- Choose metrics based on actual evidence, not worst-case imagination.
- If PR/UI makes attack more or less realistic, reflect that.
- For Web3: many platforms (Immunefi) use their own impact scale (Critical/High/...)
  based on **funds at risk / protocol damage** — follow program rubrics.
- Always include full **vector string** for triager verification.

**Example argument (not just numbers):**
> "High (CVSS 8.1 / AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N). An attacker with a basic account
> can read and modify invoice data of other tenants without victim interaction, impacting
> confidentiality and integrity of financial data for all customers."

---

## Deduplication (before submitting)

Duplicates = no payout. Check first:
- Is this already documented? (changelogs, public security advisories).
- Is this a variant of your old report or known pattern for this asset?
- For contests (Code4rena/Sherlock): assume "obvious" bugs will have many reports —
  winners usually have the most precise root cause + best write-up.
If unsure about uniqueness: report anyway with clear angle/impact — let triager judge.

---

## Triage & Follow-up

After submission, you interact with the triager. Approach: cooperative, data-driven.

- **Request for more info** → provide clearer steps/artifacts, don't get defensive.
- **Severity dispute** → argue with concrete impact scenarios + CVSS vector, not emotion.
  If they're right, accept. If you're right, show proof.
- **Marked duplicate/informative** → ask for clarification politely; present new impact
  angles if uncovered.
- **Need deeper PoC** → coordinate; offer controlled demo/safe environment.
- **Timeline & disclosure**: follow coordinated disclosure. Don't publish before authorized/patched.

---

## Template Report

```
# [Class] in [component] — [impact summary]

## Summary
[2–3 sentences]

## Severity
[Rating] — CVSS:3.1/AV:_/AC:_/PR:_/UI:_/S:_/C:_/I:_/A:_ (score _)
[1–2 sentence impact argument]

## Steps to Reproduce
Prerequisites: [setup details]
1. ...
2. ...
3. ...

## Proof of Concept
[request/response/screenshot/script output]

## Impact
[realistic attack scenario + business impact; chaining = narrative description]

## Remediation
[actionable fix suggestion]

## Notes
[environment, timestamp, references]
```

---

## ⚠️ MANDATORY OUTPUT PATH — D: DRIVE (GLOBAL RULE)

**ALL bug bounty output MUST go to `D:\data hermes\bugbounty\` — NEVER C:\.**

Windows path (bash/MSYS): `"/d/data hermes/bugbounty/<target>/"`

### Directory structure (per target)
```
D:\data hermes\bugbounty\<target>\
├── <target>-F<number>-<short-name>/
│   ├── <Finding_Title>.pdf          # Main report (evidence embedded)
│   ├── gen_*.py                     # Generation scripts (screenshots, PDF)
│   └── evidence/
│       ├── ss1_*.png
│       └── (raw curl output)
└── recon/                           # Recon data (subdomains, JS bundles, endpoints)
```

### Rules
1. **PDF output path:** ALWAYS `D:/data hermes/bugbounty/<target>/<name>.pdf` — never relative path, never cwd, never `C:\Users\WINDOWS10\`.
2. **Recon data:** subdomain lists, endpoint dumps, JS analysis → `D:/data hermes/bugbounty/<target>/recon/`.
3. **Before generating ANY file:** `mkdir -p "/d/data hermes/bugbounty/<target>"` first.
4. **reportlab call:** `SimpleDocTemplate("D:/data hermes/bugbounty/<target>/<report>.pdf", ...)` — pass ABSOLUTE D: path.
5. **MEDIA delivery still works from D:** — Telegram can attach `MEDIA:/d/data hermes/bugbounty/...` normally.
6. **Exception:** skill/knowledge files stay on C: drive. Only DATA (PDF, evidence, recon, reports) goes to D:.

**Why:** C: drive is OS drive — user's global rule stores all bug bounty & Kebersihan Sumatra data on D:. PDFs landing in `C:\Users\WINDOWS10\` or `%APPDATA%` = RULE VIOLATION.

### Self-check before finishing any session
- [ ] `find "/d/data hermes/bugbounty/<target>" -type f` shows the PDF
- [ ] No PDF/evidence files created in `C:\Users\WINDOWS10\` root or cwd
- [ ] If any file landed on C: → move it to D: immediately (`mv`), then relink MEDIA path

---

## PDF Report Generation Pipeline (reportlab)

When user requests PDF reports (default for bug bounty findings), use `reportlab` to generate professional PDFs. Do NOT use wkhtmltopdf or external converters — reportlab is always available. **Output path: ALWAYS `D:/data hermes/bugbounty/<target>/` — see MANDATORY OUTPUT PATH section above.**

### Dependencies (always available on this system)
```python
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, HRFlowable
```

### Recommended PDF Structure (5-page format)
1. **Page 1 — Title Page:** Finding title, severity badge (colored Table), metadata table (target, endpoint, reporter, date, program, status)
2. **Page 2 — Vulnerability Details:** Classification table, impact analysis with bullet points
3. **Page 3 — PoC:** Step-by-step with `Preformatted` code blocks showing exact HTTP requests/responses
4. **Page 4 — Data Fields / Evidence:** Tables showing exposed data, statistics, rate limit test results
5. **Page 5 — Remediation + CVSS:** Numbered fix recommendations, CVSS metrics table with vector string

### Key Patterns
- **Severity badge:** Use a colored `Table` with white text, centered. Colors: CRITICAL=#c0392b, HIGH=#e74c3c, MEDIUM=#e67e22, LOW=#f39c12, INFO=#3498db
- **Metadata table:** 2-column, bold labels, gray text values, subtle borders
- **Code blocks:** `Preformatted` with `code_style` (fontSize=8, backColor=#f4f4f4, borderPadding=6)
- **Data tables:** Alternating row colors (#ffffff/#f9f9f9), grid lines (#ddd), bold headers with colored backgrounds
- **CVSS table:** Purple theme (#8e44ad), bold score row at bottom

### Evidence Embedding Rule (MANDATORY)
**ALL screenshots and evidence MUST be embedded inside the PDF.** Do not generate separate screenshot files that require the reviewer to open multiple documents. The PDF must be a single self-contained report.

For generating terminal-style evidence screenshots (curl output, tool results):
1. Use Pillow to render terminal-style images from real command output (black bg, colored text)
2. Force convert to RGB before saving as PNG (handles mode mismatch)
3. Embed in PDF via `reportlab.platypus.Image` with calculated aspect ratio
4. Use `KeepTogether([image, caption])` to prevent page-break splits

If separate evidence files are needed (raw data, full API responses), they are supplementary only — not the primary evidence.

### Universal Report Rule (MANDATORY)
**Reports must be platform-agnostic.** Do NOT include any platform-specific branding, watermarks, or identifiers:
- ❌ "HackerOne", "Bugcrowd", "Immunefi" — anywhere in text, headers, or metadata
- ❌ Platform-specific submission portals or IDs in the report body
- ❌ Platform watermarks on screenshots or PDFs
- ✅ Generic disclosure statement: "submitted for security review purposes"
- ✅ Researcher name + date only — no platform account IDs

This allows the same report to be submitted to ANY platform (HackerOne, Bugcrowd, Immunefi, direct disclosure, etc.).

### Severity Honesty — Mitigating Factors
**Severity must reflect real-world exploitability, not theoretical worst-case.** When the target has active security controls that constrain the attack chain, this MUST be reflected in CVSS metrics:

- **Endpoint controls** (e.g., NASA managed workstations restrict external browsing while authenticated): Impact Attack Complexity from Low → High if the attack requires victim to browse attacker-controlled content.
- **Network restrictions** (e.g., DNS filtering, proxy blocks): If the victim network blocks the attack vector, AC:H is appropriate.
- **Authentication gating**: If the sensitive endpoint requires authentication that the victim doesn't have in the attack scenario, this limits impact.
- **Defense-in-depth**: If the organization has controls that make exploitation harder (even if not impossible), note them in the report.

**Key principle:** A misconfiguration is still a valid finding even if severity is MEDIUM/Low due to mitigating factors. Don't inflate to HIGH/CRITICAL when the chain has real-world blockers. Reviewers respect honesty — they reject inflated claims.

### ⚠️ Pitfalls
- **No Unicode subscripts/superscripts** — built-in fonts render them as black boxes. Use `<sub>`/`<super>` markup in Paragraphs.
- **Watermarks:** NEVER add watermarks to evidence screenshots or PDFs — user explicitly prohibits them.
- **Fake evidence:** ALL evidence must be real curl output, actual tool results, verifiable data. No fabricated responses.
- **Consistency:** PDF text, code blocks, and screenshot evidence must describe the SAME request/response. Cross-verify before generating.
- **`pymupdf` (fitz) for verification** — after generating PDF, load it with pymupdf to verify page count and content rendering.
- **Severity inflation is worse than honest MEDIUM:** When endpoint controls or network restrictions make exploitation harder, AC:H + UI:R is appropriate. A well-argued MEDIUM beats a rejected HIGH.

### Evidence Directory Structure (per finding)
```
<target>-F<number>-<short-name>/
├── <Finding_Title>.pdf              # Main report (evidence embedded)
├── gen_*.py                         # Generation scripts (screenshots, PDF)
└── evidence/                        # Raw evidence + generated screenshots
    ├── ss1_*.png                    # Terminal-style evidence (rendered)
    ├── ss2_*.png
    └── (raw curl output as supplementary data)
```

**Naming convention:** `F<number>` = finding sequence number within the target. Files named with `01_`, `02_` etc. for ordered evidence narrative.

### Terminal-Style Evidence Screenshots (Pillow)
For generating clean, professional evidence screenshots from real curl/tool output:

```python
from PIL import Image, ImageDraw, ImageFont

W, BG = 1180, '#1e1e1e'
F = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 15)

img = Image.new('RGB', (W, h), BG)
d = ImageDraw.Draw(img)
d.text((16, y), line, fill='#d4d4d4', font=F)
# Colors: GREEN=#50fa7b, RED=#ff5555, YELLOW=#f1fa8c, CYAN=#8be9fd, WHITE=#d4d4d4
```

**Critical:** Always `img.convert('RGB')` before saving as PNG — PIL images may be in palette mode which breaks ReportLab embedding. Also force RGB conversion when loading existing screenshots for embedding:
```python
pil = PILImg.open(filepath)
if pil.mode != 'RGB':
    pil = pil.convert('RGB')
    pil.save(filepath, 'PNG')
```
