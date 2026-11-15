---
name: nextjs-app-security-testing
description: "Audit Next.js App Router apps: Server Actions replay, BOLA, RSC data, MFA-gated flows."
metadata:
  hermes:
    tags: [bug-bounty, nextjs, security, web2, server-actions, cdp, mfa, vdp]
---

# Next.js App Security Testing (VDP/bug-bounty)

Proven workflow for authorized audits of Next.js server-rendered apps with:
- Cloudflare in front (curl largely works, browser-harness/headless often gets blocked)
- Next.js App Router + RSC + Server Actions (multipart POST to page URL, not /api)
- MFA/OTP sign-in, adviser/co-owner/contributor role models, email-based invites

## When to use
- VDP or bug-bounty target is a Next.js app (detect via `/_next/static/chunks/` paths, `vary: rsc, next-router-state-tree` headers, `_next` build id).
- You need to test authenticated flows and need a reliable way to drive a real browser from code.

## Workflow (condensed)

1. **Scope + policy first.** Read `/.well-known/security.txt` and `/security/disclosure` — confirm in-scope assets and rules (own-account-only, no volume/DoS). Skip out-of-scope subdomains entirely.
2. **Recon + fingerprint.** subfinder/httpx/naabu/nuclei/gau/katana/dalfox/sqlmap/ffuf per normal pipeline. Note: nuclei on Next.js targets reports TLS 1.0/1.1 low findings (usually N/A).
3. **Map the app surface via JS chunks.** Fetched chunks (`_next/static/chunks/app/...`) reveal routes (`/app/...`) and API endpoints (e.g. `/api/ai/extract-expense`, `/api/properties/{id}/export?format=xlsx`). OpenAPI at `/api/v1/openapi.json` and `/developers/docs.md` are common. Also mine (a) the server-rendered **inline `window.<app> = {config:{…}}` blob** (site keys, redirect URIs, API base — public-by-design vs license strings), and (b) a **prefix constant** for the auth API — the real mount may be `/cp-api/auth` (better-auth) not `/api/auth`; a **404 vs 307** distinguishes wrong-path from middleware-gated. Full recipe + framework fingerprints (better-auth, Mastra agent API, ts-rest client) + `/health` runtime-config leak pattern in `references/spa-surface-extraction.md`.
4. **Drive the real browser for auth.** Signup/login flows need the browser (see `references/nextjs-cdp-chrome-automation.md`). Then test authenticated surfaces from inside the session.
5. **Test server-action state-changing ops** by capturing the action POST and replaying (see rules below).
6. **Verify every "blocked" at the server, not the UI.** Hide-not-enforce is the #1 false-positive trap and the #1 missed finding (see Role confusion).

## Vendor-run (self-hosted) programs on the Next.js + Keycloak stack

Some targets have no bounty platform at all: the policy lives in the product's own docs and reports go to
`security@…`. Worked example **Mamentis** (2026-10): `app.mamentis.ai` (Next.js App Router + Auth.js) behind
Envoy, `auth.mamentis.ai` (**Keycloak**), `ws.mamentis.ai` (realtime), `api.mamentis.ai` (404s everything).

- **The scope gate is the docs page, not a platform.** It yielded channel / PoC-required / 24h-response and the
  reward bands ($50–$5,000) but **no** scope IN/OUT table, no safe-harbour clause, no testing rules — and
  `/.well-known/security.txt`, `/robots.txt`, `/security`, `/legal/security` were all 404 while the docs'
  own "GitHub: org/repo/issues" pointed at a repo that does not exist publicly. Record the absence: scope
  judgement falls to you, and the report must state which assets you assumed in scope.
- **The app can live on a different TLD than the docs.** `mamentis.com` is a static Docusaurus site whose
  "Log in" / "Start for Free" nav buttons are **dead** (`href="#"`), while the real product is
  `app.mamentis.ai`. A subdomain sweep of the *docs* apex therefore finds nothing. Locate the true host via web
  search plus the docs' own product language, then DNS-check the sibling TLDs explicitly (`.ai`/`.io`/`.app`
  resolve; the marketing `.com` does not host the app).
- **Mine the API surface from `_next/static/chunks/**`.** 11 bundles gave `/api/login`,
  `/api/auth/{providers,csrf,signin,callback/<idp>,session}`, `/api/account/credentials`,
  `/api/library/{,folder,upload}` and `/api/ws-ticket`. Pattern: fetch `/login`, collect every
  `/_next/static/**/*.js`, then regex `["'`](/api/…)["'`]`.
- **Re-probe every enumerated endpoint with ALL verbs.** A path that 307s to `/login` on GET can behave
  differently on POST/PUT/DELETE/PATCH. On Mamentis all verbs 307'd — that is a *verified negative* worth
  writing down; a GET-only matrix would not have proved it.
- **The IdP host is a first-class surface.** With Keycloak in front, `auth.<domain>` deserves its own pass —
  full probe battery with commands and interpretation in `references/keycloak-backend-recon.md`.
- **Compare security headers across sibling hosts of the same product.** `auth.mamentis.ai` sent HSTS + CSP +
  nosniff + X-Frame-Options + referrer-policy; `app.mamentis.ai` sent **none** of them and advertised
  `x-powered-by: Next.js`. The intra-product inconsistency *is* the finding — a single-host check reads as
  "no headers, low priority" instead of "they know how, this host was skipped".
- **Spoofable disclosure address.** `mamentis.com` had DMARC `p=none` with no `rua`/`ruf` and SPF `~all`;
  `mamentis.ai` had **no DMARC at all**. The spoofable mailbox was the programme's own `security@…` report
  address — a phishing vector aimed at the researchers about to report. DNS-check DMARC/SPF/DKIM for every
  apex the programme uses and quote the records as the PoC.
- **CSP is an information-disclosure channel.** Keycloak's CSP whitelisted
  `form-action … https://*.internal.mamentis.ai http://127.0.0.1:*`, leaking a non-public internal zone and
  advertising a **localhost desktop gateway**. Treat a `127.0.0.1:*` allowance as a lead to the desktop client
  (Origin/CSRF checks on that gateway), not a cosmetic CSP nit.
- **Do not create accounts with the operator's identity on your own initiative.** Mamentis had *no* public
  signup (dead CTAs, Keycloak registration disabled, `/contact` formless), so the entire authenticated surface
  was unreachable; the only provisioning path was three social IdPs (GitHub/Google/Microsoft). Testing a
  self-provisioning or e-mail-linking ATO there requires a real IdP login — that is the operator's identity and
  it creates real state on the target. **Stop, state the blocked surface, and ask**, offering a throwaway IdP
  account as the default. A blocked surface reported as a first-class result is a good outcome, not a failure.
- **Regex hits need context.** The marketing bundle matched `firestore`, which read like an exposed Firebase
  backend — it was a Prism.js language definition. Open the surrounding ~300 chars before writing any
  secret/backend-exposure line.

## Server Action replay — the mechanics that matter

Next.js Server Actions post multipart to the **same page URL** with:
- `next-action: <action-id>` header
- fields prefixed `_N_` where N = form index (e.g. `_4_$ACTION_4:0`, `_4_email`, `_4_propertyId`)
- a trailing `0: [{}, "$K1"]` field

Rules learned the hard way (all verified on VDP targets):
- Action IDs are **session-bound**. Replaying a captured body with a different user's session cookie → `500` + RSC error digest. That 500 is CSRF/binding working, NOT a bug.
- A body reused in the SAME session with wrong/missing action fields → `500`. Manual urllib-form POSTs to login/actions fail with 500 because they skip the action binding — always drive these via the browser, not urllib.
- The only meaningful cross-user test is: **authenticated as user B, submit a form rendered in B's own session but with the object id of A** (e.g. swap `propertyId`). That's where real BOLA/priv-esc lives.
- The `Accept: text/x-component` + `next-action` + `next-router-state-tree` headers are required on replays.

### Harvesting action IDs statically — no browser, no capture needed

You do not need to intercept a request to get an action ID. The client bundle carries it in plaintext,
next to the function's own name:

```bash
grep -oE 'createServerReference\)?\("[0-9a-f]{40,}"[^)]*"[A-Za-z0-9_]+"' _next/static/chunks/*.js
# -> "402cb809…588","submitDataDeletion"      "403ac75a…bf1","subscribeToNewsletter"
```

Collect chunks across every interesting page first (fetch each page → regex
`/_next/static/chunks/*.js` → download → grep), because a route's actions are only referenced by the
chunks that page loads. One pass over ~10 page loads gave the complete action inventory of the site
(NGRAVE, 2026-10-29) in under a minute, with zero requests to the action endpoints.

### Invoking an action as plain JSON (the shape that actually works)

The multipart form replay above is the *browser's* shape. For a programmatic call the JSON shape is
shorter and equally valid on current Next.js:

```bash
curl -s -X POST "https://target/en/some-page" \
  -H "Next-Action: 402cb809ecdaf6dcc30e006d6151b34aba49c2b588" \
  -H "Content-Type: text/plain;charset=UTF-8" \
  -H "Accept: text/x-component" \
  --data '[{"email":"a@b.c","order":"X1"}]'      # JSON ARRAY of the action's arguments
```

Read the reply as **line-oriented RSC**, not JSON: line `0:` is the RSC preamble
(`{"a":"$@1","f":"","q":"","i":false,"b":"…"}`), and the action's **return value is the `1:` line**
(`1:{"ok":false,"reason":"robot"}`). Parsing the whole body as JSON fails and makes a working action
look broken — this cost several wrong conclusions before the shape was identified.

- **Wrong page → `308` to `/`** with an empty body. The action ID is bound to the route that renders
  it. A 308 means "posted to a page that does not use this action", not "the action is gone".
- **Action IDs are per-deployment.** Re-derive after any redeploy; a stale ID 308s or 404s.
- **Cheap pre-auth recon win.** An action that is unauthenticated by design (newsletter, contact,
  data-deletion) still (a) confirms which server-side integrations exist and (b) hands you a
  validation oracle: a malformed field returns a distinct error string, and the *ordering* of those
  strings reveals the pipeline. `"Enter a valid email address."` → `"Something went wrong."` →
  `{"ok":true}` told us validation ran, then a third-party API call ran, then the abuse control ran —
  before any token was checked.

## OTP / MFA lockout discipline (statistical, own-account)

To test brute-force without DoS and without false claims:
- Wrong-code attempts: 6 attempts at most in round 1. Observe at what attempt a "too many attempts" message appears (typical: 6).
- Session rotation: after lockout, do a FRESH login session and try again. If blocked immediately / on first attempt → **account-level lockout** (safe). If a fresh session resets the counter → session-scoped counter → brute-forceable via rotation (finding).
- MFA-recovery flows ("Forgot MFA?", reset authenticator): same test. A 24h delay + email confirm + "too many attempts persists across fresh session" ⇒ solid.
- TOTP generation: if you enroll your own authenticator, extract the base32 secret from the page and generate codes client-side (RFC 6238, SHA1, 30s, 6 digits). This unlocks MFA-protected flows for testing.
- Query params like `codeLimit` / `why` that appear in the reset URL are **echo-only**; verify server enforcement separately (resend cooldown is server-side).

## Role confusion — the disambiguation rule

When a user holds multiple roles (e.g. contributor adviser AND co-owner), a successful action proves ONLY that one of the roles allows it. Before reporting "contributor can delete owner entries", remove the co-owner relationship and retest as PURE contributor. In one real VDP, co-owner removal changed delete-buttons from present to absent — the "finding" was the co-owner right, not the contributor boundary. Keep the promise text from the UI/invite email and verify it exactly (e.g. "can remove only entries they added" → delete buttons appear only on own entries).

## Pitfalls

- **UI ≠ server enforcement.** Hidden buttons, disabled fields, and "Only the owner can..." messages in the DOM are UI hints, not proof. Always: change the client value (e.g. role radio `viewer`→`owner`), capture the POST, and read what the SERVER returns (fallback-to-viewer, "over 100% owned", 500 with explicit error body).
- **Import/CSV preview reflects payloads as text.** Payloads (`=SUM`, `<img onerror>`, `{{7*7}}`) appearing in a preview table is not XSS/formula injection — check the rendered DOM / export internals (xlsx sharedStrings `<si>` vs formula `<f>`, CSV `'` prefixing) before claiming.
- **OG-image / id-guessing endpoints** often 404 for every guess; a valid id from a known page still 404s when text differs — not enumerable.
- **CVE-2025-29927 (Next middleware bypass)**: probe with `x-middleware-subrequest` variants, but expect 307-to-login on well-built apps — that's a clean negative, not a finding.
- **VDP scope gates**: Pro-plan features (AI scan, document upload, API keys) and HMRC/Government-Gateway OAuth are usually OUT of reach with free test accounts — note as untested surface, don't fake progress.
- **User preference**: when the operator says "keep hunting, no limits" they want breadth + adversarial creativity, not premature "target is clean" conclusions. Report dry negative results with the full matrix of what was tried, and be explicit about which surfaces need extra access (paid plan / real OAuth accounts) to continue.

## Support files
- `references/spa-surface-extraction.md` — extract API surface + inline config from public assets: `window.<app>` config blob, chunk grep, better-auth / Mastra / ts-rest fingerprints, `/health` runtime-config leak, source-map + reflection checks, and policy-driven out-of-scope discipline.
- `references/nextjs-cdp-chrome-automation.md` — full CDP wiring (multi-profile, cookie extraction, network capture, TOTP login) for Next.js apps behind Cloudflare.
- `references/keycloak-backend-recon.md` — Keycloak-as-IdP probe battery for a vendor-run Next.js target: OIDC discovery reading, grant allow-list via unauthenticated token calls, anonymous Dynamic Client Registration + the `Trusted Hosts` policy and why a Host-header bypass is usually unreachable, redirect_uri strictness matrix, registration/admin-console checks, and the account-provisioning decision gate.

## Related
- `bb-methodology`, `security-recon`, `hunt-oauth`, `security-arsenal` (owned skills — load for payloads/checklists).
## Absorbed playbooks (complete sub-packages under `references/`)
The Server Actions deep-dives live here as full packages; this SKILL.md stays the entry point.

- `references/nextjs-server-actions-audit/PLAYBOOK.md` — capturing a real action, the replay
  pitfalls that silently NO-OP, deriving a replay from rendered HTML (`$ACTION_REF_N`,
  `$ACTION_N:0|1`, `$ACTION_KEY`), Origin-control testing, the REST-reads plus action-writes plus
  minted-Bearer-JWT split, upload/document-store checklist.
- `references/server-actions-auth-audit/PLAYBOOK.md` — authz/BOLA core techniques 1-13: static
  replay without a browser, CDP-driven UI, cross-tenant signals, wire-id vs bundle-id, per-action
  binding asymmetry; `scripts/static_form_action_sweep.py`, `scripts/tenant_boundary_probe.py`.
