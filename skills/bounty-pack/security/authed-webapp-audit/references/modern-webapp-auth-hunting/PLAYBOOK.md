---
name: modern-webapp-auth-hunting
description: Use when auditing authenticated web apps in bug bounty.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, web, auth, idor, bola, server-actions, nextjs, cdp, csrf]
    related_skills: [hunt-idor, hunt-auth-bypass, hunt-oauth, bb-methodology]
---

# Modern Web App Auth Hunting (browser-CDP + server actions)

## When to Use
Trigger when the target is a modern JS-framework web app with:
- Next.js/React/SPA pages and `_next/static/chunks` in HTML
- `Vary: rsc, next-router-state-tree` or `next-action` POST headers (Server Actions / RSC)
- any authenticated `/app/*` or dashboard surface requiring a session cookie
- Disposable-account flows (signup OTP, invites) needing repeatable test identities

Class-level playbook for authenticated testing of modern JS-framework web apps where the UI is a
Next.js/React SPA and state-changing ops run through **Server Actions / RSC** (multipart POST to
the page URL with `next-action` header). curl-only testing fails on these apps; you drive a real
browser via Chrome CDP.

## Mindset (user-mandated — non-negotiable)
- **Exploiter, not defender.** "Apakah ini ke-block?" is the wrong question. The right question:
  "Gimana caranya nembus?" Every surface gets an attack matrix, not a single check.
- **Real tools per class, not just curl.** sqlmap for SQLi, dalfox for XSS, nuclei `-tags` for
  class sweeps, ffuf for discovery, interactsh for OOB. Curl is for verification/headers only.
  The user will call you out ("kamu gunakan semua tools? bukan sekadar curls?") if you lean on curl.
- **Never stop at "bersih".** A clean first pass is an invitation to deep-dive: child-object IDOR,
  file upload, Pro-gate bypass, share/co-owner flows, MFA-gated flows, server-action replay.
- **Prior audit results are reference, not skip permission** (user-mandated). When re-engaging a
  target, re-run the examination on untouched or surface-only-touched areas — "deepdive lagi
  perlahan, maksimalkan tools yang ada" — even where an earlier pass recorded a negative.
  Old findings tell you where to look deeper, not where to stop.
- **Server-side enforcement is the only truth.** UI hiding a button proves nothing. Replay the
  server action directly with tampered values / another account's cookie / evil Origin.
- **Honest negatives are still deliverables.** When a target genuinely holds (all vectors blocked),
  document the evidence trail — future sessions use it to avoid re-testing and to justify "no finding".

## Setup
### Two isolated browser profiles (account isolation)
Same Chrome profile shares one cookie jar — a second tab just redirects /signup to the logged-in
dashboard. Use separate profiles + ports per test account:
```bash
"C:/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="$LOCALAPPDATA/Temp/qw-chrome-debug" --no-first-run --no-default-browser-check about:blank &
# second account: port 9223 + qw-chrome-debug2
```
**`--remote-allow-origins=*` is mandatory.** Without it, Python `websocket-client` gets
`403 Rejected an incoming WebSocket connection` on the CDP WS handshake. If the port was already
held by an older Chrome without the flag, kill the exact PID (`netstat -ano | grep :9222`).

### Disposable accounts + OTP (mail.tm)
`scripts/mailtm_helper.py` creates inboxes, fetches 6-digit OTPs, and extracts invite/share links.
Use ONE mailbox per test identity, plus a fresh one per tamper test (mail.tm rate-limits creates).

### TOTP enrollment (when MFA gates a valuable flow)
MFA setup pages show a base32 secret (grab `[A-Z2-7]{20,}` from body) + a confirm code field.
Generate the code in Python (RFC 6238, SHA1, 30s period) and submit — no phone needed. Secret
rotates on page reload: read the CURRENT secret from the live page, don't reuse an earlier one.

### When the user hands you their own authenticator QR
A client-supplied QR is usually the **export** format (`otpauth-migration://offline?data=...`), not
a plain `otpauth://totp/...` URI — the secret sits inside a base64'd protobuf. Decode, don't ask
the user to retype anything. Working parser + iframe recipe:
`references/owned-second-factor-and-grant-matrix.md`.
- `cv2.imread` + `zxingcpp.read_barcodes(img)` → `.text`. On a phone photo of a screen, retry at
  2–6x upscale, then `threshold`, `adaptiveThreshold`, `bitwise_not`, and Otsu before giving up.
- **Prove a QR is present before grinding decoders.** Downscale to ~76 cols and print an ASCII
  preview (`" .:-=+*#%@"`). A QR shows three high-contrast finder squares; a dark UI screenshot
  reads as noisy text blocks. This avoids 30 futile decode attempts on the wrong file.
- Protobuf layout: field 1 = repeated `otp_parameters`; inside it field 1 = secret (bytes),
  2 = name, 3 = issuer, 4 = algo, 5 = digits, 6 = type, 7 = counter.
  Secret = `base64.b32encode(raw).decode().rstrip("=")`.
- Verify before use: `pyotp.TOTP(secret).now()` plus remaining window `30 - int(time.time()) % 30`.
- **One secret often covers several systems.** Here the same TOTP opened both the SaaS IdP and the
  on-prem appliance management console — enumerate every login offering "authenticator" before
  assuming a second enrolment is needed.

## Workflow
1. **Fingerprint**: headers (`Vary: rsc, next-router-state-tree`, `_next/static/chunks`,
   `next-action` header on POST) = Next.js server actions.
2. **Map authenticated surface**: nav each `/app/*` route in CDP, collect `performance resource`
   + `Network.requestWillBeSent` URLs, download per-route chunks, grep `"/api/...`, `/app/...`,
   `fetch("/api/...")`, action IDs. Also probe `/developers` → OpenAPI spec + docs (richest surface).
3. **Build account 2 (and 3) in isolated profiles** (see Setup). Create an object (property/
   business) in account 1 to get a target UUID.
4. **Cross-tenant matrix** (per state-changing action):
   - page-level: acc2 → acc1 object URL (expect 404/403 baseline)
   - server-action replay: acc1 action body + acc2 cookie → expect `Server action not found`/500
   - propertyId/BOLA swap: acc2 opens form on THEIR object, swaps id to acc1's → expect "not found"
   - role tamper: change hidden/radio values (`viewer`→`owner`) before submit → server falls back
   - accept-token binding: try accepting acc3's invite while logged in as acc2 → must be rejected
5. **Business logic**: over-allocation (invite sharePercent that pushes total >100%), negative/0
   sharePercent, invite-then-replay with tampered percent.
6. **CSRF (server actions)**: capture legit POST body via `Network.getRequestPostData`, replay
   SAME body + SAME cookie but `Origin: https://evil.example.com` → 500/digest error = enforced;
   2xx + double-write = vulnerable. Confirm via a count/export endpoint, never just status code.
7. **Export/injection**: XLSX formula injection — inspect `xl/sharedStrings.xml` (`<si><t>`) vs
   `<f>` elements; real formula = `<f>`. CSV — check for `'` prefix mitigation.

## Verify server-side, always
- After any write attempt, confirm via the app's export/JSON endpoint (count rows, list values).
- Password state after change attempts: actually log in with old vs new password in a clean profile.
- One 500 from a hand-built urllib POST ≠ vuln — repeat via browser (missing headers cause 500s).
- **A business-logic bypass needs a SUCCEEDING baseline in the same harness.** Run the legitimate
  request first with the values the UI itself would send; only a working baseline makes the
  manipulated result readable as "server trusted my value". If the baseline is also rejected you
  cannot distinguish server validation from "this account isn't eligible", and the honest verdict
  is *unproven* — not a finding. (Cost here: a parameter-tamper claim that was really a wrong
  parameter.)
- **Take the request body from the page's own `FormData.append(...)` / fetch call, not from the
  option element.** HTML `<option>` attributes often carry several ids — `value` (what is
  submitted) and `value2` (a lookup id used only by JavaScript). Submitting the lookup id gives a
  generic "invalid access" that looks exactly like an authorisation check. Grep the inline script
  for the real field values before concluding anything.
- **Compare what you asked for against what you got.** Requesting `nodes=10` and receiving a
  300-node licence is the proof that a parameter is ignored server-side; requesting `3650` days
  and receiving 30 is the same proof for duration. Measure the created object, don't infer from
  the HTTP status.

## MFA / 2FA surface — audit the controls, not just the bypass

If the app lets you enroll 2FA (your own test account), enroll it and then verify each control.
Every one of these is reportable positive evidence when it holds, and a headline finding when it
does not:

1. **Half-authenticated session** (password accepted, code not yet entered) must not reach
   `/app`, `/app/account` — expect 307 → `/login`.
2. **Sensitive actions enforce the code server-side.** Watch for the form *revealing* extra
   fields only after the first submit (observed: changing the account email added
   `currentPassword` + `mfaCode`, and the copy said a code also goes to the NEW address before the
   change lands). Wrong code + "turn off 2FA" must fail and leave 2FA on. Saving a tax/NINO-style
   identifier must not change the stored value.
3. **Attempt cap**: count wrong codes until lockout (observed: 5 → "wait about 15 minutes"), then
   prove it is **account-level** (fresh login + CORRECT code still refused during the window) and
   that it **expires** (log in again ~15 min later). Note WHERE the cap lives: a device-level
   lockout ("This device is blocked until …") with no HTTP-level 429 on the MFA endpoint is still
   a working control — do the feasibility math (observed ~15 attempts per 15-min block vs a 10^6
   keyspace = infeasible) and log it as a negative, not a finding. A cap that is only HTTP-level
   (429s, no device state) is weaker: the mfa_token often stays valid across the window.
4. **Code replay** — the clean test is ONE TOTP code driving TWO logins inside the same 30s
   window; the second must be refused. Do NOT judge replay by reusing a code for a data-entry
   action: that action's own value validation can reject you for an unrelated reason and you will
   draw the wrong conclusion (this session: a NINO ending in "E" failed the *checksum*, not the
   replay check — read the raw RSC error segment `1:{"error":"..."}` to tell them apart).
5. **Recovery path**: read `/login/mfa/recover` style copy (24h delay + "we'll email you first so
   you can stop it" = sound design). Do not press it on a borrowed account — it starts a real 24h
   disable timer.
6. **Expectation gap worth reporting**: MFA covers interactive login only. An API key keeps
   working while the login is locked out — say so, because "2FA is on" reads to a customer as
   "the data is protected".
7. **ATO chain to test explicitly**: stolen session → change email → password reset. It must
   require password + TOTP + a code to the new address. Any missing leg is the finding.
8. **Calibrate before claiming a missing leg (user-corrected, 2026-10)**: an email change that
   applies immediately without verifying the new address is NOT a finding when the endpoint
   already requires the account password. The bar is *"can an attacker do something they
   couldn't before?"* — with the password they can already log in and do everything, so the
   missing verification grants no new capability (immediate change is normal authenticated
   self-service UX; a typo-lockout is a support issue, not a security bug). Only claim it when
   the change is reachable WITHOUT the password (session-only), or on ANOTHER user's record.
   The user will retract these on sight — test the capability delta, not the control checklist.

## Is MFA actually bypassable? (credential oracle + grant matrix)

**Use the login response as a credential oracle.** Two-step logins answer differently for "wrong
password" versus "password right, code next": observed `Login failed.` vs `Please enter your
Authentication Code.` That single differential confirms a credential without guessing, tells you
when to stop password work and start OTP work, and is the fastest way to validate a
user-supplied password. Read the step-2 message before declaring a login failed — a naive script
prints the same "login failed" for both branches and you draw the wrong conclusion.

**When the browser flow enforces a code, test the non-browser grants.** For Keycloak, read
`/realms/<realm>/.well-known/openid-configuration`: `grant_types_supported` advertising `password`
does NOT mean a given client may use it. Each rejection below is a **control that holds** — record
it, don't treat it as a dead end:

| attempt | client | expected control response |
|---|---|---|
| password grant | app's public client (from `VITE_OIDC_CLIENT_ID` etc.) | `unauthorized_client` |
| password grant | `admin-cli` | `Client not allowed for direct access grants` |
| password grant | `account` | same |
| client_credentials | app client | `unauthorized_client` |
| device_code (`/auth/device`) | app client | `unauthorized_client` |

**Dynamic Client Registration is the sharp edge.** `POST /realms/<r>/clients-registrations/default`
returning `400 Invalid json representation for ClientRepresentation` proves the endpoint is live and
parsing (a `401`/`404` would mean closed). The prize is registering a client with
`directAccessGrantsEnabled:true`, then using the password grant to mint a token that never sees the
OTP step. In practice an edge WAF often answers a **static branded "Not Found" HTML page with 403**
for well-formed bodies — if every field variant returns that page, record WAF-blocked / unproven.
Never report without a created `client_id` and a token actually obtained through it.

**SAML assertion tampering — fire the whole matrix, one FRESH token per test** (assertions are
single-use; reusing one makes the control fail and you misread it as "everything blocked"):

`control` (must succeed) · `strip all signatures` · `strip RESPONSE-level signature only` ·
`NameID swap` · `XSW evil-first` · `XSW nested` · `XSW signature-wrapped` · `strip Conditions`.

Reading the results:
- **control fails** → replay protection / addressee binding. Fix the harness before concluding.
- **`strip_response_only` succeeds** → usually **spec-permitted**: SAML WebSSO allows signing only
  the assertion, and assertion-signed + response-unsigned is a legal configuration. Confirming this
  is what lets you *stop* instead of filing a spec violation as a vulnerability (dropped here, zero
  report).
- **any tampered `NameID` accepted** → real authentication bypass. That is the finding.

## Privilege escalation — the RBAC matrix (build the low-priv account yourself)

When the target is an admin console/appliance and you hold superadmin on **your own instance**, the
highest-value next move is to create a **read-only admin** and prove whether the server honours the
permission model. This is the test that separates "RBAC enforced" from "buttons are hidden".

Sequence (measured on Genian NAC 5.0.92, 2026-10):

1. **Create the low-priv account via the product's own UI**, not by editing a DB. Capture the exact
   field contract first — role dropdown, purpose, status, password/confirm, email. Wizard entry points
   are often iframe-scoped: the Tasks menu item does nothing visible because it opens
   `?cmd=create&selectedTab=<tab>` inside an iframe; drive that URL directly.
2. **Log in as the low-priv account and read the permission map** if the app exposes one
   (`GET /rest/sessions/current` → `permLevelMap` {fullControl:20, edit:10, addEdit:15,
   readOnly:5, noPerm:0} plus a 30-key `adminPermMap`). Diff it against superadmin programmatically;
   that diff *is* your test plan.
3. **Page-access matrix** — one request per page as each role, record status **and byte size**:

   | page | superadmin | read-only |
   |---|---|---|
   | pages gated by a `0` permission | 200 / 61 KB | **302 → error** |
   | pages with `5` readOnly | 200 / 61 KB | 200 / 61 KB (read is correct) |

   A `302 → /faces/error.xhtml` for a `perm=0` page and a `200` for a `perm=5` page is the proof the
   server enforces the map rather than the sidebar.
4. **Then attempt the writes the low-priv role should not have** — this is the part everyone skips.
   For each: force-enable the disabled control, submit via the page's own function/JS click, then
   **reload and re-read the value**. Persistence is the only proof.
5. **Session-cookie confusion** — when the app sets two session cookies, determine which one carries
   authority by crossing them:
   `lowpriv JSESSIONID + admin secondaryCookie` → must stay low-priv. If it escalates, that's the
   finding. (Here it did not: authority was bound to `JSESSIONID`; the second cookie was inert.)

Honest-negative framing that makes this deliverable: "server-side RBAC enforced on build X — 3 gated
pages 302'd, 3 write attempts did not persist, cookie-cross produced no escalation". Full worked
matrix, the JSF/PrimeFaces control quirks, and the two anomalies to record (see below):
`references/rbac-escalation-matrix.md`.

### UI-gated vs server-gated — the persistence test

A page rendering a form whose fields are `disabled` proves **nothing**; it is often the licence/edition
gate implemented in the template only. Decisive procedure:

```text
1. read the field's current value          (e.g. NCTIME_IPCHANGE = 3)
2. force-enable  -> el.removeAttribute('disabled'); el.disabled=false; el.readOnly=false
3. set a new value                          (5)
4. submit via the page's own handler        (el.click() on the Update button, or its JS function)
5. RELOAD the page and re-read the field
   -> still 3  = server rejected/ignored  = NOT a finding
   -> 5        = server honoured it       = licence/edition bypass, real
```
Two traps: a modal/overlay silently swallows a real `.click()` (dismiss `.ui-dialog` then JS-click the
button), and `fill()` refuses on a disabled input, so the force-enable must happen first. Report a
gated-page *render* only after a write proves; otherwise it is an info-disclosure at best and often
lands squarely in an "UI/feature exposure" exclusion clause.

## File upload — read the accept-list from the WIDGET config, not the form

`accept="…"` on the `<input>` is advisory and often absent, while the framework widget carries the
real client-side filter. For PrimeFaces read the initialiser in the page source:

```text
PrimeFaces.cw("FileUpload","widget_form1_fileUpload1",{... fileLimit:1,
  invalidFileMessage:"The file format is not valid.",
  allowTypes:/(\.|\/)(tgz|TGZ|gz|GZ)$/});
```

An archive accept-list (`tgz|gz|zip|tar`) on an *import* dialog is the highest-value upload shape:
the server must extract it, which is the classic **Tar/ZIP-slip → arbitrary file write → RCE**
family. Notes that make the test efficient and honest:

- **Try the rejected extension first anyway.** `.txt`/`.zip` being refused proves the filter is
  client-side; the accepted extension then tells you which parser to attack.
- **Build a benign slip archive and mark it.** One normal member plus
  `../../bbtest_traversal.txt` and a deep `../../../../../../tmp/bbtest_deep.txt`, each containing a
  unique marker string. Never a webshell, never an executable.
- **Hunt the marker across every web root** before concluding anything:
  `/`, `/mc2/`, `/mc2/upload/`, `/mc2/faces/`, `/mc2/resources/`, `/cwp2/`, `/upload/`. Even a
  404/error page is a data point; a 200 whose body contains the marker is the finding.
- **Distinguish "filter refused" from "extraction reached but failed".** A refusal leaves the file
  out of the queue; a real attempt returns a *server* message. Here the import returned a missing
  i18n key (`!! key mc.setup.cwpDesign.import.errorMsg not found !!`) — i.e. the handler ran and
  errored, but the marker never landed, so extraction either validated paths or failed before
  writing. That is **UNPROVEN, not a vulnerability** — say exactly that.
- **You usually need a valid package to reach the sink.** If the feature ships an Export, get a
  real artifact and inject one member into it; if Export is unavailable (no row checkboxes, Tasks
  menu has only Create/Delete), the honest status is *blocked — could not obtain a valid package*,
  and you do **not** claim the bug. Do not substitute a handcrafted archive for the real one and
  call the resulting rejection a negative either: both are "test not completed".
- Check the advisory history first: if the vendor already published a ZIP-slip RCE, your target is
  only interesting in a **different component**, and you must say which component you tested.

## Session lifecycle — the finding class nobody tests

**Sessions surviving password change** (verified Medium, djangoeurope 2026-10): the password
endpoint updates the credential but does not revoke existing auth tokens. Full recipe:

1. Log in, capture the session token (cookie value or Authorization key).
2. Change the password through the documented endpoint (e.g. `PATCH /user/{id}` with
   `{current_password, password: new}`).
3. Prove the change is real: old password → 400, new password → 200.
4. Replay the PRE-change token against any authenticated endpoint. **200 = finding.**

Impact framing that survives triage: an attacker holding a stolen token keeps access for the
token's full lifetime (check the expiry the API reports — observed 7 days) even after the victim
changes their password, so the victim's standard remediation fails; eviction requires manually
deleting tokens, which is not part the password-change flow. Fix: revoke all tokens on password
change (or all but the one performing it). Not an auth bypass — say so; the finding is that the
token survives the credential rotation meant to cut off exactly this access.

Companion checks on the same surface:
- **Reset-token reuse**: replay an already-consumed reset UUID → must fail ("expired").
- **Logout**: does it revoke server-side or only clear the cookie?
- **Token budget**: some APIs invalidate a token after ~10 rapid requests (401 mid-sequence) —
  space requests ~500ms or re-login; this is a rate mechanism, not a finding.

## Laravel + Livewire 3 targets (magic-link / QR / webhook components)

Livewire apps (Laravel Breeze + `wire:` directives, `/livewire/livewire.min.js` on the page)
expose server-side component logic through `POST /livewire/update`. Driving it correctly:

- **Discover components from the HTML**: every `wire:snapshot="..."` attribute is a component.
  JSON-decode it — `memo.name` is the component class (`magic-link-login`, `q-r-login`, …) and
  `data` is its public state. That is your action map without reading any server code.
- **The update format** (Livewire 3):
  ```json
  {"_token": "<plain token from <meta name=\"csrf-token\">",
   "components": [{"snapshot": "<exact wire:snapshot string, HTML-escaped as in the page>",
                   "updates": {"email": "a@b.c"},
                   "calls": [{"path": "", "method": "sendMagicLink", "params": []}]}]}
  ```
- **CSRF gotcha**: `X-CSRF-TOKEN` wants the PLAIN token (meta tag); `X-XSRF-TOKEN` wants the
  encrypted cookie value. Omitting `_token` from the body → `419 CSRF token mismatch`.
- **Stale snapshot → 404**: replaying the initial snapshot after the component's checksum has
  rotated (e.g. after a poll regenerated state) returns a route-not-found page. Browser-driven
  calls work because Livewire sends the CURRENT snapshot. So: drive actions in the browser, or
  re-fetch the page for a fresh snapshot before each scripted call.
- **`fill()` does not sync `wire:model` reliably** — Playwright's fill sets the value without
  the event sequence Livewire listens for, and the server sees an empty model. Use real
  keystrokes (`pg.keyboard.type(..., delay=50)`) and verify the snapshot's `data.email` updates
  before invoking the action.
- **Rate-limit oracle**: component error strings are returned verbatim in the response
  (`{"sent":false,"error":"Too many requests. Please try again in 57 minutes."}`) — a free
  read of the per-email/per-IP throttling policy, and a differential between known and unknown
  accounts if the copy differs.
- **Registration-moved-to-mobile check**: read the signup modal copy before assuming a web
  register route is live. "Create your account in the app" + a 500 on every `/register` POST =
  registration is app-only by design (fail-closed, a functionality note, NOT a security finding).

## DRF + Angular SPA targets (token-auth pattern)

Django REST Framework backends behind an Angular SPA use `Authorization: Token <40-hex>` plus
cross-origin session cookies. Header-only clients get `Invalid API token` / `API token has
expired` even with a valid token — the missing piece is `credentials: 'include'` (withCredentials).
Test from inside the page origin:
`fetch(api, {credentials:'include', headers:{'Authorization':'Token '+<token from document.cookie>}})`.
Angular redirects unknown routes to /login: enumerate real routes from the bundle
(`path:"..."` regex over main.js) before navigating. Lazy chunks carry the feature API surface —
visit each route, capture the `.js` responses, grep `\.(get|post|put|patch|delete)\("..."` for the
full call map including endpoints the root listing doesn't show.

## When the app computes money (calculation-engine correctness)

- **The product's own itemised panel is the oracle.** Drive one controlled scenario and read the
  breakdown (income / expenses / profit / taxable / credit lines), not the headline number.
- **Isolate one variable at a time.** Add a £1 restricted cost versus £0 and watch whether the
  allowance/disregard comparison flips — a 1-unit delta proves the operator bug cleanly (this
  session: a £1 finance cost moved a £1,000 allowance the wrong way).
- **Enumerate EVERY write path to the same data** before declaring an invariant enforced: form
  add, form edit, delete, bulk import (CSV *and* XLSX), public API, and any AI-suggest / review
  queue path. Invariants are commonly enforced on the add form and nowhere else — that gap is the
  finding, and it is worth listing the paths you checked.
- **Prove the impact on the number that matters** (tax/amount due), with before/after values, then
  remove the test data and re-read to show it reverses.
- Verify the rule against the authoritative source before claiming (HMRC manual, gov.uk, RFC) and
  quote the rule in the report. Keep severity honest: a self-scoped bookkeeping error is not a
  cross-tenant break.

## Tool sweeps worth running (and their expected noise)

Order that fits one session: `ffuf` route discovery on both `/api/v1` and `/app` (`-ac` is
required — SPA catch-alls otherwise match everything) → `arjun` with the auth header for hidden
params → `nuclei` with LOCAL template dirs by tag (misconfiguration/exposures/technologies; a
whole-directory run can blow past 10 minutes per target, so run it in the background) → `sqlmap`
(`--level 3 --risk 2 --technique=BEUST`) on the parameter that actually reaches a query →
`dalfox` with the session cookie → `trufflehog` on the client bundles → `wafw00f`/`naabu` for the
edge.

Expected noise, so you don't over-read it:
- nuclei returns INFO header/CSP findings only on a hardened target.
- dalfox flags `Reflected ... param` for RSC flight echoes (escaped text in
  `self.__next_f.push`, not a sink) — confirm in the DOM before believing it.
- sqlmap can self-disprove its own verdict (`parameter ... does not seem to be injectable` after
  an initial "appears to be injectable") and may report thousands of 403s from the WAF — read the
  final `[CRITICAL] all tested parameters do not appear to be injectable` line and quote the
  403 count as a coverage caveat.
- A tool that misbehaves is an environment issue, not a target finding: check `-h` when flags act
  oddly (a stub binary can shadow the real one) and log it in your own notes, not the report.
- Long scans: background + explicit `timeout`, keep the raw output files — the verdict line is
  usually all you need later.

## Auth artifacts — read the client factory before calling it a bug

A token/selector/blob that works without a secret looks like Broken Access Control until you find
the factory that mints it. Checked live on Proton (`mail.proton.me`): `GET /api/auth/v4/sessions/
forks/<selector>` with no cookies, no `Authorization` and no fork secret returned a **full-scope**
AccessToken+RefreshToken → looked like a High. The drive/wallet/pass bundles then showed the call as
`{method:"get", url:`auth/v4/sessions/forks/${selector}`, unauthenticated:!0}` — the selector *is*
the intended bearer credential for the app hand-off (it is handed to the child client in the URL
fragment). **By-design ⇒ dropped, zero report written.**

Procedure, in this order:
1. Grep the bundles for the path fragment plus `unauthenticated:!0`, `silence:!0`, `skipAuth`,
   `ignoreHandler`, `pullFork`. If the call is declared unauthenticated, the artifact is a credential.
2. **Scope-differential the token** instead: `GET /api/core/v4/auth/scopes` on both tokens. Proton's
   fork token lacked `password`, `locked`, `vpn`, `docs`, `lumo` vs the SRP-login token — that gap is
   the real attack surface.
3. Then test the privileged actions, not the claim:
   | action | fork token | login token |
   |---|---|---|
   | `PUT /core/v4/settings/email` | 403 `MissingScopes:["password"]` | sudo-gated |
   | `DELETE /auth/v4/sessions/{uid}` | 403 `MissingScopes:["locked"]` | 200 |
   | `PUT /core/v4/keys/user` | 403 `MissingScopes:["locked"]` | — |
4. **Revocation reach is a real finding class** (see Session lifecycle): after `DELETE /api/auth/v4/
   sessions` (revoke-all) both fork-derived tokens died *and* their refresh tokens returned
   `422 Invalid refresh token`. Capture that as a proven negative — it is what shows the design holds
   rather than "we didn't get to it".

Rule of thumb: an auth oddity is a candidate, a *capability delta* is a finding. Find the extra
capability, or write the negative down and move on.

## Pitfalls
- **Playwright auto-dismisses native dialogs.** Buttons whose handler is
  `if (!confirm(...)) return;` never POST: no network request, page unchanged. Install
  `pg.on("dialog", lambda d: d.accept())` BEFORE concluding an endpoint is broken or unauthenticated.
  Also check `button.disabled` — a confirm-name field can gate the button until it matches.
- **Duplicate `id` attributes** (a wrapper div and the input inside it sharing `id="x"`) make
  `#x` resolve to the div: the native value setter throws `Illegal invocation` and Playwright's
  `fill()` refuses with "Element is not an <input>". Target by attribute (`input[name="x"]`).
- **Borrowed/vendor-granted accounts**: 2FA you enable locks the OWNER out (they don't hold the
  secret); never fill a documented daily write cap (it locks their quota for ~24h); keep a
  cleanup list and re-verify the account state (entries, properties, shares, MFA) at the end.
- curl/urllib multipart to Next.js Server Action endpoints → 500 (needs browser-generated
  `$ACTION_REF/_KEY` state + `next-action` header). Do signup/login in the browser.
- `requestWillBeSent.postData` is TRUNCATED — always `Network.getRequestPostData` for full bodies.
- HttpOnly session cookies are invisible to `document.cookie`; use `Network.getAllCookies`.
- mail.tm: poll inbox (3s x N); OTP subject is `Your <site> code is NNNNNN`; invite/share emails
  contain the accept link in text body.
- Cloudflare will 403 raw Python/urllib bursts; browser + cookie context works. `wafw00f`-style
  checks: treat 403 storms during tool scans as rate limiting, not WAF-block on a single request.

## Support files
- `scripts/cdp_helper.py` — minimal Chrome CDP driver: connect, navigate, js(), cookies, full
  post-body capture via getRequestPostData.
- `scripts/mailtm_helper.py` — mail.tm inbox create/OTP/link extraction.
- `references/rbac-escalation-matrix.md` — build-your-own read-only admin, read the permission map and
  diff it, the page-access matrix (status **and** size), the three write attempts as low-priv, the
  session-cookie confusion test, and the JSF/PrimeFaces control quirks (iframe wizard entry, hidden
  `forceLogin`, error-page size fingerprints, disabled-input force-enable + reload-persistence). Use
  when you hold superadmin on your own instance and need to prove or disprove privilege escalation.
- `references/quarterwise-vdp-case-2026-09.md` — full case study: surface map, every tested
  vector, and the exact mitigations that held (evidence for "hardened target" conclusions).
- `references/mfa-business-logic-and-tool-sweep.md` — MFA/2FA control matrix with observed
  numbers, calculation-engine oracle recipes, and the concrete tool sweep results
  (ffuf/arjun/nuclei/sqlmap/dalfox/trufflehog) from a Pro-plan follow-up engagement.
- `references/owned-second-factor-and-grant-matrix.md` — decode an
  `otpauth-migration://` export QR into a base32 secret (protobuf parser + ASCII present-check),
  fresh-window TOTP submission, OTP prompts hidden in JSF/PrimeFaces iframes, the Keycloak grant
  + DCR probe set, and the SAML tamper harness that keeps one fresh assertion per variant.