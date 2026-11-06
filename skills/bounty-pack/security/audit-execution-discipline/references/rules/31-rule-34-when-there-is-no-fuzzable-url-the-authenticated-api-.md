## ⛔ RULE 34: When there is NO fuzzable URL — the authenticated API harness IS the real tool

**User reminder (Rapyd portal engagement 2026-09-29): "kerahkan semua kemampuan dan tools kamu,
jgn hanya curl"** — on a target whose surface is an auth-gated SPA + JSON API (Turnstile/reCAPTCHA on
every send endpoint, no injectable parameters). Here `sqlmap/dalfox/ffuf/nuclei` have nothing to aim
at; the honest answer is not "curl only", it is a *different toolchain*:

1. **Bundle mining** — `katana -u <host> -d 2 -jc` + fetch the JS chunks, then regex the minified
   strings for endpoint literals (`"/api/…`, template paths, hostnames). This is what produces the
   real API map (this engagement: 526 portal endpoints, plus an internal service-portal API surface
   and a finance-portal API base that no scanner would have surfaced).
2. **In-page authenticated harness** — drive the real browser over CDP and issue the app's *own*
   `fetch` from inside the page, reusing `localStorage.token` + the fingerprint header + a JSON body.
   Batch a cases file (`GET/POST/PUT/DELETE` + body + note) and print `status → error_code` per row.
   This is the tool that actually tests this class of target, and it produces reportable evidence.
3. **Role matrix** — two browser profiles (owner + an invited low-privilege member), same case list,
   diff the results. Findings come from the diff of the two matrices, not from a scanner.
4. **Evidence = the API response rows**, saved as `results_*.json` beside the cases file. Give scanners
   their turn only where the bundle exposes a parameterised or unauthenticated surface.

**Self-inflicted lockout pitfall (cost a working session):** never submit a forgot-password request for
the account you are actively using — it can invalidate the password immediately (subsequent logins
return a generic `…ERROR_LOGIN` / "Email or password is incorrect") **while live sessions keep
working**. If the reset flow must be tested: rename → request → consume the link → revert. Same class
of self-harm: deleting the low-privilege member you still need for the RBAC matrix, or firing a
"resend invite" that expires the link you were about to use.

Related: `security/email-template-injection` (mail-channel findings + escaping-map evidence), and
RULE 33 (credentials that change mid-engagement live in the engagement log, never in memory).

