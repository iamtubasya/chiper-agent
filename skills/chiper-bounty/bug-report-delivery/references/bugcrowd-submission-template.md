# Bugcrowd Submission Guide Template

Use this template to create pre-filled form data for Bugcrowd submissions.
Each finding should have this filled out BEFORE opening the submission page.

## Form Fields

### Vulnerability Type (VRT)
**Category:** Broken Authentication → Authentication Bypass
(Match to Bugcrowd VRT: https://bugcrowd.com/vulnerability-rating-taxonomy)

### Priority
P1 Critical / P2 High / P3 Medium / P4 Low
(Use CVSS score to justify)

### Vulnerability Title
**Format:** [Root Cause] in [Component] Allows [Impact]
**Example:** Broken Authentication in JWT Token Minting Endpoint Allows Account Takeover

### CVSS Score
```
X.X (CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N)
```
Include full breakdown table in report body.

### Vulnerability Description
Structure:
1. Executive Summary (2-3 sentences)
2. Technical Details (endpoint, request, response)
3. Authentication Flow Analysis (how it should work vs how it does)
4. Root Cause (WHY the bug exists)
5. Proof of Concept (step by step, with curl commands)
6. Verified Evidence (actual API responses)
7. Negative Tests (what you tried that DIDN'T work)
8. Impact (numbered list of concrete impacts)
9. Remediation (numbered, actionable fixes)

### Attack Scenario Summary
Pre-requisite → Attack Chain → Outcome
Numbered steps, each with concrete action.

### Supporting Information
Program name, target scope, vulnerability class, CVSS, researcher name, date.

### Attachments
1. PDF Report (full finding with evidence)
2. PoC Scripts (reusable, clean, commented)
3. Screenshots (Pillow-generated terminal-style or browser captures)
4. Evidence files (JSON responses, terminal output)

## Checklist Before Submitting
- [ ] Title is specific (not generic "Security Vulnerability")
- [ ] CVSS matches severity claim
- [ ] Steps are copy-paste reproducible
- [ ] All endpoints are in-scope
- [ ] No real user data in evidence (use test accounts only)
- [ ] Negative tests included (shows thoroughness)
- [ ] Remediation is actionable (not "improve security")
- [ ] PDF has all sections per Gold Standard format
- [ ] Screenshots have watermark with reporter name + date
