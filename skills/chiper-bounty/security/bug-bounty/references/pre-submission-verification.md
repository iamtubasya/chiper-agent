# Pre-Submission Verification Checklist

> Run ALL checks before generating PDF or submitting. Any failure = DO NOT SUBMIT.

---

## 1. WATERMARK / PII VERIFICATION

### Why
Bugcrowd triagers auto-reject screenshots with watermarks, researcher names, email addresses, or any identifying markers that aren't the submitter. NASA VDP follows the same rule.

### Checklist
- [ ] **Screenshot corners** — no Bugcrowd/HackerOne/Immunefi logos, badges, or platform watermarks in any corner
- [ ] **Terminal output** — no researcher email (`BC_USERNAME@...`), no Bugcrowd username, no platform account IDs in curl output or command history
- [ ] **PDF metadata** — no platform names in title, author, subject, or keywords
- [ ] **Email in PoC** — if PoC includes email fields, use `[REDACTED]` or a throwaway, never your Bugcrowd/HackerOne email
- [ ] **Browser screenshots** — check bookmarks bar, browser extensions, logged-in profile indicators
- [ ] **Terminal prompt** — PS1 showing username is OK (not PII), but email in prompt is NOT

### Pixel-Level Check (automated)
```python
from PIL import Image
import numpy as np

def check_watermarks(screenshot_path):
    img = Image.open(screenshot_path).convert('RGB')
    pixels = np.array(img)
    h, w = pixels.shape[:2]
    
    # Check corners for non-background pixels (watermarks)
    regions = {
        'top-left': pixels[0:50, 0:200],
        'top-right': pixels[0:50, w-200:w],
        'bottom-left': pixels[h-50:h, 0:200],
        'bottom-right': pixels[h-50:h, w-200:w],
    }
    
    for name, region in regions.items():
        # Count unique colors — too many = watermark/logo
        unique_colors = len(np.unique(region.reshape(-1, 3), axis=0))
        if unique_colors > 20:  # threshold: mostly uniform = clean
            print(f"⚠️  {name}: {unique_colors} unique colors — possible watermark")
    
    print("✅ Corner check complete — review flagged regions manually")
```

### Text-Level Check (automated)
```python
import re

def check_text_pii(text_content):
    patterns = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'bugcrowd_id': r'(BC_USERNAME|BC_ALIAS|hackerone|immunefi)',
        'platform_ref': r'(Bugcrowd|HackerOne|Immunefi|Intigriti)',
        'phone': r'\+?\d{10,15}',
    }
    
    findings = []
    for name, pattern in patterns.items():
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        if matches:
            findings.append(f"⚠️  {name}: {matches}")
    
    if findings:
        print("❌ PII/PLATFORM REFERENCES FOUND:")
        for f in findings:
            print(f"  {f}")
        return False
    print("✅ No PII or platform references found")
    return True
```

---

## 2. VRT CLASSIFICATION VERIFICATION

### Why
Bugcrowd uses VRT (Vulnerability Rating Taxonomy) to classify findings. Wrong VRT = triage confusion = delayed payout or rejection. For NASA VDP, the VRT path determines how the finding is routed.

### Workflow
1. **Load the VRT JSON** from Bugcrowd's GitHub:
   ```bash
   curl -s "https://raw.githubusercontent.com/Bugcrowd/vrt/master/src/data/vrt.json" -o vrt.json
   ```

2. **Parse and map** each finding to a VRT entry:
   ```python
   import json
   with open('vrt.json') as f:
       vrt = json.load(f)
   
   # content is a LIST of categories, not a dict
   for category in vrt['content']:
       for entry in category.get('children', []):
           if 'cors' in entry.get('id', '').lower():
               print(f"ID: {entry['id']}")
               print(f"Name: {entry['name']}")
               print(f"Priority: {entry.get('priority', 'Varies')}")
               print(f"Children: {entry.get('children', [])}")
   ```

3. **Common CORS mapping:**
   - `unsafe_cross_origin_resource_sharing` → P3 (if with credentials) / Informational (if without credentials)
   - VRT may show "Varies" for priority — you must justify severity based on actual exploitability

4. **Verify severity matches VRT:**
   - If VRT says P3 Medium but you claim P2 High → provide escalation justification
   - If VRT says "Varies" → you choose based on impact, document your reasoning
   - If VRT says P4 Low → don't inflate to P2 without strong justification

### Escalation Justification Template
When VRT classification underrates your finding:
```
VRT Path: [category] → [sub-category]
VRT Priority: [P-level]
Recommended Escalation: [your level]
Justification: [why the default VRT priority is too low — e.g., "VRT default assumes 
informational CORS misconfiguration, but this finding demonstrates credential theft 
via cookies/headers on authenticated endpoints, which elevates to data compromise"]
```

---

## 3. SUBMISSION GUIDE (Platform-Specific)

### Bugcrowd Submission
**Endpoint:** `POST https://bugcrowd.com/submissions.json`
**Headers:**
```
Content-Type: application/json
X-Bugcrowd-Version: 2024-01-01
Cookie: _bc_cfr_session=...
```
**Body structure:**
```json
{
  "submission": {
    "title": "[Class] in [component] — [impact summary]",
    "vulnerability_references": [
      {"id": "A05:2021", "name": "Security Misconfiguration"}
    ],
    "severity": "P2",
    "description": "## Summary\n...",
    "researcher_notes": "Internal notes...",
    "attacker_machine": {"os": "Linux"},
    "vrt_paths": [
      {"path": "P1 - Insecure Data Transmission > unsafe_cross_origin_resource_sharing"}
    ],
    "bug_priority": "P2"
  },
  "engagement_id": "PROGRAM_ID"
}
```

**Steps:**
1. Login to Bugcrowd → copy cookies + CSRF token from DevTools
2. Get `engagement_id` from the program page URL
3. Fill submission body with findings
4. POST to submissions.json
5. Verify response: `{"id": "...", "state": "new"}`

**OR use the UI:**
1. Navigate to program page → "Submit Report"
2. Fill form: Title, Description, Severity, VRT Path, PoC
3. Upload screenshots/PDF
4. Submit

### NASA VDP Submission
**Portal:** https://hackerone.com/nasa (or Bugcrowd, depending on current program)
- Follow platform-specific submission flow
- Include: VRT path, CVSS vector, PoC steps, screenshots (watermark-free)
- **One report per finding** (or all in one if same vulnerability class)
- Response SLA: typically 3-5 business days for initial triage

---

## 4. PRE-SUBMISSION FINAL GATE

Run this checklist AFTER watermarks cleared AND VRT verified:

- [ ] **Scope confirmed** — target is in-scope per program policy
- [ ] **Watermarks cleared** — all screenshots/PDFs clean (Step 1)
- [ ] **VRT mapped** — correct VRT path + severity (Step 2)
- [ ] **CVSS scored** — vector string + impact argument match VRT
- [ ] **PoC reproducible** — steps clear, someone else can follow
- [ ] **Impact stated** — business impact, not just technical
- [ ] **Remediation included** — actionable fix recommendation
- [ ] **No platform branding** — report is platform-agnostic
- [ ] **Evidence embedded** — screenshots in PDF, not separate files
- [ ] **One report per finding** (or consolidated if same class)
- [ ] **PDF on D: drive** — `D:/data hermes/bugbounty/<target>/`
- [ ] **MEDIA path ready** — can deliver via Telegram

**If ANY check fails → fix before submitting.**

---

## 5. COMMON REJECTION REASONS (AVOID THESE)

| Rejection Reason | How to Avoid |
|---|---|
| "Watermark detected" | Run Step 1 pixel + text check |
| "Out of scope" | Verify scope BEFORE any testing (Stage 0) |
| "Duplicate" | Check existing reports before submitting |
| "Informational / no impact" | Run Finding Quality Gate from main skill |
| "Wrong severity" | Map to VRT, justify escalation if needed |
| "Cannot reproduce" | Include exact curl output, full request/response |
| "Missing steps" | Number every step, include prerequisites |
| "By-design behavior" | Research if the feature is intentional before reporting |
| "No CVSS vector" | Always include full CVSS:3.1/AV:N/... string |
| "Platform branding in report" | Remove all HackerOne/Bugcrowd/Immunefi references |
