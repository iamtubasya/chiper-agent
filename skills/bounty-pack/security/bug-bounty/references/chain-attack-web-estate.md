# Chain-attack hunting on web/SSO estates

Sequence that produced a real finding on the FIRST.org engagement (2026-10-26): tracing the
hub.first.org SSO redirect chain revealed the portal is itself an OAuth 2.0 provider, and its
/oauth/authorize endpoint validated client_id but not redirect_uri (arbitrary external 302,
validated 3x, reported as a separate issue from the captcha bypass found earlier).

## Order of operations (cheap kills first, expensive chains last)

1. **Map the SSO topology before touching anything else.** Unauthenticated, follow every redirect
   chain by hand (manual loop with urljoin — relative Locations are common). A host that redirects
   to `<portal>/oauth/authorize?...` means the portal is an OAuth provider: that endpoint is a
   trust boundary and gets tested like one.
2. **Pull `/.well-known/openid-configuration` from every in-scope host.** Free recon: issuer,
   authorization/token/userinfo endpoints, response_types_supported, grant_types_supported
   (check whether `user_credentials`/password grant is advertised AND actually enabled — they often
   differ), and scopes_supported (scope values like `service:jsm` leak internal service names).
3. **Harvest a real client_id** by starting a legitimate SSO flow and reading the authorize redirect
   (e.g. `app-jupyterhub-<22-char-suffix>`). Do not guess client ids — invalid ones return
   `invalid_client` 400 and tell you nothing.
4. **Test redirect_uri validation across ALL response types.** The error path often redirects to an
   arbitrary URI even when the success path is gated. With an unentitled test account the code flow
   may 401 before any redirect — prove the flaw with `response_type=token` / `id_token` (which
   redirect with `error=unsupported_response_type` to the supplied URI) and report the code-theft
   impact as ARGUED, not proven. Variant matrix to run: arbitrary domain, userinfo trick
   (`https://legit@evil.com`), protocol-relative (`//evil.com`), path suffix on the real callback,
   plain-HTTP downgrade, `javascript:`, encoded traversal. Record which return 302 vs 406 — a 406
   on malformed schemes proves *some* parsing exists, which makes the missing domain check more
   credible, not less.
5. **CSRF token session-binding test.** Mint a `__req`-style token in session A, submit a
   state-changing POST in session B. If accepted, tokens are not session-bound — then check the
   session cookie's SameSite attribute (missing attribute = browser Lax-by-default = cross-site
   POST CSRF is mitigated; the finding is defense-in-depth only, NOT reportable on its own). Look
   for state-changing GETs (favorite add/delete via GET link): Lax cookies ARE sent on top-level
   GET navigation, so those are CSRF-able — usually low impact, note and move on.
6. **Identity-store sharing test (do this early, it kills chains cheaply).** Try the portal
   credentials on the central IdP's universal login (`/u/login/identifier` → password page). A
   generic "account or password is incorrect" means separate stores — the portal→IdP→other-services
   chain is dead and you stop investing in it.
7. **Hidden-field mass assignment on join/apply forms.** Join/application forms often carry
   `user` (uid) and `Membership`/status hidden fields. Submitting another uid or `Membership=member`
   usually just re-renders the form — verify by checking the RESULTING STATE (group page, pending
   flag), not the response page, and note that server-side validation errors (e.g. a mandatory
   questionnaire field) mean the POST never reached the interesting code path.
8. **Subscribe-others via list/bulk checkboxes.** Profile forms with `_lists[N][]` whose value is
   an email address: try setting another address. Expect validation against the session user; a
   block here is the norm, a pass is a spam finding.

## Reporting shape

Each finding = its own PDF + its own draft email, even when found in the same hour on the same
host — the captcha bypass and the redirect_uri flaw are different root causes and triage merges
same-subject bundles. In the redirect_uri report, the honesty table is what makes it credible:
proved = arbitrary external redirect (N runs, M variants); argued = authorization code interception
and ATO on SSO-linked services for entitled victims (untestable with an unentitled account).
