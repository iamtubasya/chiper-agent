# Generic submission-form fields — fill guide (VDP forms that are NOT email)

Some programmes (or the same programme via a portal) ask for the report in fixed form fields.
Keep the email-body rules of rule 0c in mind — the same honesty constraints apply field by field.
Copy this skeleton per finding and fill every `<>` slot; leave a field only if it is truly optional.

## Field map

| Field | What goes in | Watch out |
|---|---|---|
| Vulnerable System* | host + exact endpoint (+ note it is an in-scope entry of the policy list) | name the endpoint, not just the domain |
| Vulnerability Type* | the class name (e.g. Open Redirect, CSRF, Server Security Misconfiguration / CORS, Business Logic); "Other" plus a CWE if the list lacks it | match their dropdown wording first, CWE as fallback |
| CVE-ID | `none - application logic issue, not a known CVE` unless a real CVE applies | never invent one |
| Title* | one line: unauthenticated/authenticated + endpoint + what is exposed/possible | no marketing words, no severity inflation in the title |
| IP used for testing | the operator's egress IP at test time (optional field) | operator fills their own current IP |
| Summary* | 3-5 sentences: where, what the code does wrong, who can trigger it, the honest boundary | state what it does NOT give (no token theft etc.) |
| Steps to reproduce* | numbered, copy-paste runnable: exact URL/command, exact payload, expected vs observed; include the proxy/devtools chain when the bug is client-side | a reader must reproduce without guessing |
| Impact of Vulnerability* | CIA triad lines (Confidentiality / Integrity / Availability, each "none directly" or the real effect) + the attacker playbook (numbered: what the attacker sends, what the victim/system does, what the attacker gains) | impact adjusted after triage — do not oversell; Low stays Low |
| Remediation | the concrete fix (allowlist X before Y, verify token server-side via Z, POST+CSRF token instead of GET) | actionable, one short paragraph |

## Worked example shape (open redirect, finanzen.net F5, 2026-10-16)

    Vulnerable System*: login.finanzen.net - https://login.finanzen.net/federated-signin (in-scope: Web-App Finanzen.net -> login.finanzen.net)
    Vulnerability Type*: Open Redirect (CWE-601; "Other" if the list lacks it)
    CVE-ID: none - application logic issue, not a known CVE
    Title*: Unauthenticated open redirect on login.finanzen.net/federated-signin accepts any http(s) URL in base64 uri parameter and navigates the browser there
    Summary*: The route takes a uri query parameter, base64-decodes it and assigns it to location.href; the only check is that the URL protocol is http/https, the host is never compared to an allowlist.
    Steps to reproduce*: (1) base64("https://example-target.example/") -> link; (2) open in browser; (3) through a proxy observe GET <login host>/federated-signin?uri=... followed by GET <attacker host>/. Repeat with any https URL.
    Impact of Vulnerability*: Confidentiality: none directly. Integrity: none. Availability: none. Attacker playbook: phishing link that shows the trusted login domain then lands on a credential-harvesting page; bypass of allowlisted domains in mail/chat filters; chains with the vendor's own sign-out flow. Boundary: no code/token attached to the redirect.
    Remediation*: allowlist the decoded host against your own identity-service hosts before location.href, or use opaque server-issued redirect ids.

## Mechanical checks before submitting through a form

- Attachments: same trio as email drafts (PDF with embedded screenshot, evidence txt, screenshot png).
- Every claim in Summary/Steps/Impact must exist verbatim in the attached PDF (cross-artifact agreement).
- No reward/compensation wording anywhere (the operator forbids it even where the programme allows it).
- Disclose tool/AI assistance + manual verification in Summary or a dedicated sentence (mandatory on programmes that require it, harmless elsewhere).
