# ATS / HR-SaaS attack checklist (reusable across any recruiting/applicant-tracking target)

Derived from the operator's 18-vector brief (2026-10-24). Applies to Betterteam, Greenhouse,
Lever, Workable, Breezy, etc. Ordered by typical payout. Confirm each is in-scope for the
specific program first (career sites + resume/file links usually are; the vendor's auth/SSO
provider usually is NOT).

## Gate first: can you reach the application flow?
The highest-value surface (applicants/resumes) only exists once a job is PUBLISHED. If the
panel has no publish/activate action and jobs sit "Pending", the application flow is behind
vendor approval — recognize this wall in the first 10 min and say so, don't grind it.

## Object-level authz (High/Critical — the money class)
1. Cross-account BOLA/IDOR on jobs / applicants / resumes / applications. Provision TWO trial
   accounts; from B try to reach A's objects by slug AND by UUID. Test both the list
   (/applications) and the detail (/applications/{uuid}).
2. Resume FILE LINKS ("the file links it serves"): guessable token? accessible without auth?
   not scoped to the owning company? A readable cross-account resume = Critical.
3. Multi-tenant context is often server-derived — still TEST it: X-Company-Id/X-Company-Uuid
   headers, company_id/company_uuid params, and swapping the user-id cookie are all commonly
   ignored (good) — verify, don't assume.

## Team / roles / invites (High)
4. Role & privilege escalation: invite a low-role member, then drive admin actions (billing,
   delete job, view others' applicants) via direct API even when the UI hides the buttons.
5. Invite/undangan tokens: expiry, single-use, bound to the target email? Predictable or
   reusable invite token = account-entry path (prove, don't actually join a real customer).

## State-changing / CSRF / export / billing (Medium)
6. CSRF on actions that matter (publish job, change billing, delete applicant) — check for a
   real CSRF token; login/logout CSRF is usually excluded, other state changes may not be.
7. Export/download (CSV/PDF applicant list): can you swap job_id/company_id to export another
   company's data? Also probe the PDF generator for path traversal / command injection.
8. Billing/Stripe integration on the vendor side (Stripe itself is OOS): webhook signature
   verification (often IP-whitelisted — check), and manual (not automated, no spend) plan
   upgrade/downgrade race conditions.

## Content injection (High when public-facing)
9. Company logo/branding upload: if it accepts SVG, that's stored XSS rendered publicly on the
   career site (no login needed to trigger) — high impact.
10. Job description rich-text (public job page): unsanitized HTML = stored XSS hitting
    applicants (public), distinct from the apply-form XSS that hits the employer.
11. Application-form stored XSS: payload in name/cover-letter/custom fields that executes when
    the employer views the application.

## Parsing / SSRF / domains (High)
12. Resume parsing (DOCX/XLSX/PDF auto-fill): XXE if the parser reads XML without disabling
    external entities; PDF with external resource → SSRF (ask the server to fetch an internal
    URL / 169.254.169.254).
13. Custom-domain / CNAME verification for career sites: claim an unverified domain belonging to
    another company via race condition or a predictable verification token.
14. Webhook / integration (outbound): point the "new applicant" webhook at an internal IP or
    cloud-metadata URL and watch for a callback (classic SSRF).

## Auth / SSO / redirect / search / race / tokens / email
15. SSO/OAuth config on the in-scope host (the IdP itself may be OOS): redirect_uri validation,
    state parameter, token handling, open redirect in the callback.
16. App-host redirect logic (e.g. app.example.com -> dashboard): can a redirect param be turned
    into an open redirect to an external domain, or does it only preserve params to the dashboard?
17. Search/filter (applicant name, job status): quick SQLi/NoSQLi probes (quote, operators) even
    on an ORM stack — 1-2 manual tries.
18. Race condition on limits (free job-post count, credits, trial caps): fire parallel requests
    under the allowed rate to test a TOCTOU. Also: JWT/token alg (alg:none), signature, and
    claim-tampering (company_id/role) on applicant/invite/reset tokens; and CRLF/header injection
    in email-notification fields (applicant name, custom subject -> Bcc).

## Reminders
- Report least-intrusive proof; never touch other customers' data to prove impact.
- If a vector is "by design or bug?" — frame it as a question to the vendor, not a claimed vuln.
- Clean up every test resource (jobs, applications, uploads) when done.
