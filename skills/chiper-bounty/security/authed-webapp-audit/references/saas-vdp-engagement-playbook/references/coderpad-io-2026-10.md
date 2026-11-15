# coderpad.io VDP engagement — 2026-10-17 (recon/scan phase, blocked at authenticated surface)

Program: CoderPad + CodinGame VDP (updated Oct 2026). Contact `bugbounty@coderpad.io?subject=
Vulnerability Disclosure` (security.txt confirms; preferred-langs en,fr). Rewards monetary, they
set severity ("don't assess the criticality level, we do"). Accepted: coderpad.io, codingame.com,
codingame.eu, codingame-app.com + subs; EXCLUDED: trustcenter., status., metabase.* subs.

## Policy clauses that drove every triage decision (quote these when dropping candidates)

| Candidate found | Clause that kills it |
|---|---|
| Stitch webhook tokens (`window.CoderPad.STITCH_URL` / `_KEYLOGS` / `_MOUSELOGS`, hooks.stitchdata.com/v1/clients/151432/token/64hex) in the PUBLIC login/register HTML | "Data injection from clients to analytics tools" (accepted risk) + "Disclosed API keys without proven impact / Public API keys". Validity can't be shown without writing data (Stitch checks JSON parse before auth — malformed JSON and `{}` both return the same 400 from real AND bogus tokens, so there is no auth oracle). |
| `/register.json` accepts no Turnstile token (201) | "Manipulation client-side faking vulnerabilities that are not real server-side" — use as a means, never as a finding. |
| Pad session JWTs in `execute.coderpad.io/socket.io/?pad=…&initialExecSettings=…token=eyJ…` URLs (web archives via gau) | "Links/Urls found in Web Archives … except if showing a still-existing flaw that we can reasonably fix" — current-behaviour proof needs an authenticated pad; blocked. |
| GraphQL error messages allow full field enumeration (introspection disabled) | "Issues without a clear security impact". |
| Alias-overloading allowed / url-encoded POST queries (graphql-cop HIGH+MEDIUM) | "All RATE LIMITING related reports, or missing throttling" (+ no-DoS rule); "logged-out CSRF / CSRF with no or low impact". |

Other standing exclusions worth remembering for this estate: open redirect on coderpad.io SSO,
all OAuth findings, arbitrary file upload/download, org-member billing/feature abilities, trial
signup via email manipulation (BUT "unlimited interview pad creation after trial expiration"
IS explicitly reportable), server/version disclosure, missing headers/CORS, origin IP.
Hard rules: full description IN THE MESSAGE TEXT (body-in-attachment/PDF = rejected), 1 finding
= 1 message = 1 ticket, PoC must include screenshots/video, human pace only, min accounts,
90-day embargo.

## Estate map (recon artefacts under `D:/data hermes/bug-bounty/coderpad.io/recon/`)

- **Wildcard DNS catch-all**: every random subdomain resolves → the shared Rails "Login |
  CoderPad" page. So `grafana.` `kibana.` `prometheus.` `admin.` `pod-manager.` `tty.` etc. are
  NOT those products — don't chase them. (Rule: always probe a random subdomain first; it costs
  one request and kills dozens of phantom leads.)
- Real distinct services: `iscb.` (1Password SCIM bridge; `/health` → 401 JSON, `/scim/v2/*` →
  404 SCIM-error, UI at `/app/index.*.js`), `hydra-admin.` (401 Basic), `argocd.`/`dev-n8n.`/
  `release-n8n.` (Google-SSO gated), `gaston.`/`lumiere.` (Slack custom-domain sign-in),
  `api.screen.`/`api.interview.`/`developers.` (same ReadMe docs site, JS-rendered), `ats-api.`/
  `execute.`/`playback.`/`transcription.`/`excalidraw.`/`ai-chat.` (Express 404 shells;
  `execute.` is the socket.io pad-execution server), `static-screen-ide.` (403 CF),
  `integrations.` (530).
- Auth stack: Rails monolith + React SPA (webpack packs on CloudFront), AWS Cognito (new login),
  Ory Hydra legacy SSO (`login_challenge` param), Cloudflare + Bot Management in front.
  GraphQL at `POST /graphql` (introspection disabled, no CSRF needed for /graphql; Rails JSON
  routes need the csrf-token meta). Query fields: `user`, `organization`, `inviteDetails`,
  `emailDomain(domain:)`, `question(id:Int!)`, `snippet`, `quota`, `plan`, `plans`;
  `question(id)` → NotLoggedInError (correct authz). Customer REST API `/api/pads|questions/…`
  → 401 `Invalid API key` before any param processing (no SQLi surface unauth).
- Signup flow internals: step-1 Continue enables only after the `EmailDomain` GraphQL query
  resolves (canSubmit = query status Success); full recipe in
  `saas-test-account-provisioning:references/react-rails-signup-traps.md`.

## The blocker (evidence summary)

CoderPad transactional email never delivered: 3 addresses × 2 independent providers
(Gmail plus-alias, Gmail dot-alias, fresh mail.tm inbox) × 6 send attempts (register ×3 →
201 `/unconfirmed`, `/confirmation` resend ×2, `/password.json` reset ×1), ~60 min polling,
includeSpamTrash — zero mail anywhere, while the Gmail inbox received 200+ unrelated messages
(incl. other vendors' plus-alias mail). Pre-confirmation login → `/login.json` 403. Status page
"All Systems Operational". Engagement logged **BLOCKED at authenticated surface**, not "0 findings".

## Verdict & tool trace (for the coverage section of any future report)

nuclei (rl 5 / c 2, low→critical, 68 hosts) 0 hits; ffuf (800 paths, rate 8) SPA-302s only;
gau 14,684 URLs; katana 9,319; subfinder 73 subs → 71 in-scope; arjun JSON-mode no hidden params;
graphql-cop 2 hits (both clause-dropped); JS secret regex scan (packs + screen page) 0 hits;
interactsh via nuclei embedded (clean). jsluice unavailable (Go 1.24 tree-sitter build break, no
release binaries) — compensating manual scan. sqlmap/ghauri/qsreplace: no parameterised unauth
surface (401-before-params). deep-audit-mode guard = BLOCKED (orchestrator not run) → no
clean-negative claim made. Workspace STATUS.md holds the full write-up + resume plan.
