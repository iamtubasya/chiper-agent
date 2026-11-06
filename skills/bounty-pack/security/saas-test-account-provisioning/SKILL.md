---
name: saas-test-account-provisioning
description: "Provision a verified SaaS test account pre-audit."
version: 1.0.0
author: "RESEARCHER_NAME"
license: "MIT"
metadata:
  hermes:
    tags: [security, bug-bounty, signup, recaptcha, automation, playwright, email, authenticated-testing]
    related_skills: [bug-bounty, security-recon, security-arsenal, exploit-cookbook, waf-stateful-bypass]
---

# SaaS Test-Account Provisioning (verified account → authenticated testing)

## When to Use
- A bug-bounty/SaaS engagement needs the **authenticated** app tested (IDOR/BOLA, business logic, realtime) and there is **no account**.
- The signup flow has **reCAPTCHA** (v2 checkbox or v3) and/or an **email-verification** step.
- The operator **authorises** creating a test account (many programs require it and ask you to tag it).
- **Or you need to prove that no account can be self-created at all** (vendor-provisioned enterprise B2B
  SaaS) — see Step 0b. That proof is a deliverable, not a dead end: it justifies pivoting off the authed
  plane instead of leaving it as an unexamined gap.
Load it during **0C** (authenticated testing prep) when the engagement plan reaches the authed plane.

**Proven end-to-end on ably.com (2026-10):** account created, email verified, dashboard reached, API keys
extracted, capability tokens round-tripped.

**Also covers fully headless OIDC/Cognito provisioning** (no browser at all): unsigned Cognito
`SignUp`/`ConfirmSignUp` via `X-Amz-Target` (email-alias pools need a non-email Username), Gmail
plus-alias code read by context, the app-BFF login chain (RSA-OAEP-SHA256 credential envelope ->
`/api/oauth2/authenticate` -> `/auth/oidc/callback` -> session cookies), the SRP fallback with
pycognito when `USER_PASSWORD_AUTH` is off, the reusable `login(meta)` session-helper pattern for
cross-account harnesses, the German/English error-language map that saves retries, and the
delete-or-disclose account hygiene step: `references/headless-oidc-cognito-provisioning.md`.

**Also covers wallet-based / embedded-IdP logins** (Para/Capsule style: email OTP → MPC wallet → app
session, where the field is in a shadow root and the OTP step is in a cross-origin iframe). That flow has
its own recipe + traps: `references/para-capsule-wallet-login.md` (read it before touching any
`cpsl-*` / Capsule / "Sign Up or Login" widget — the DOM looks empty and the state lives in localStorage).

**Also covers mobile-first wallet/fintech signup** (Galoy/Blink lineage: Ory Hydra + Oathkeeper + Kratos
auth microservice, phone+OTP only, Firebase AppCheck attestation, GeeTest slide). Mapped surface, the
captcha-free-but-attestation-gated endpoints, the GeeTest dead-end, and the escalation path when a
**hand-solved** slide is still rejected (un-instrumented Chrome on a debug port + solve-captcha-only /
mint-session-over-REST split): `references/attestation-gated-auth-surface.md`. **Read it before spending a
single attempt on a captcha.**

**Also covers services where the ACCOUNT itself is the finding** — an internal collaboration instance
(Mattermost / Rocket.Chat / Zulip / GitLab / Grafana) that is publicly reachable and allows self-registration
with an open-join workspace. The three-claim ladder (registration open → team joinable → internal content
reachable), the API-only create/verify/login path, and the "join, read channel NAMES only, leave, disclose"
discipline are in `references/self-registration-impact-proof.md`. **Read it before reporting "open
registration" as informational** — the join-201 is what turns it into a real finding (measurably escalated
medium → high on chat.blink.sv, 2026-10-12).

**Sweep the siblings in the same pass** — one public internal tool means the estate has more, and the
sweep is what produces either the next finding or the credible "controls held" table. Per-service-class
verdict probes (Mattermost / Forgejo / Matrix / Grafana / Specter / Concourse / Next.js apps), the
certspotter enumeration step for the *second* corporate domain, and the brand-name-collision rule for
buckets: `references/internal-tool-exposure-sweep.md` (verified on the blink.sv + blinkbtc.com estate,
2026-10-13: 10 new hosts, every one a held control — registration disabled on Git and Matrix,
password-gated Specter, auth-gated Grafana/Concourse).

**Also covers Rails + React (MUI / react-hook-form) signup flows** — the "typing does nothing"
hydration trap on pack-heavy SPAs (15–25 s settle, `domcontentloaded` not `networkidle`, focus +
trusted `keyboard.type` + `Tab` blur for `mode:"onTouched"`), Turnstile invisible-mode dead-ends in
headless (hidden input, no iframe, token never issued), the Rails direct-endpoint fallback
(`csrf-token` meta → `/check-email` + `register.json` accepted **without** any Turnstile token),
and the hard lesson that a 201 signup ≠ provisioned account — the confirmation-email side effect
can silently never fire while the inbox works fine for everyone else. Full recipe + evidence
checklist: `references/react-rails-signup-traps.md` (verified on coderpad.io, 2026-10-17).

**Also covers classic server-rendered multi-step wizards** (PHP/LAMP style: one inline script
posting `action=<step>` to a single endpoint, email-PIN → signed-link → ABN/ABR lookup → SMS-PIN
gates): mapping the state machine from the inline JS before sending anything, plus-alias vs
dot-variant mailbox traps, capturing the exact request format by hooking `XMLHttpRequest` in
the page when curl archaeology fails, diagnosing which step's server-side gate a misleading
error actually names, and the SMS-PIN wall (never fire SMS at arbitrary numbers):
`references/multi-step-wizard-registration.md` (verified on microkeeper.com.au, 2026-10-17).

**Also covers Auth0 Universal Login (classic + new UL, DB connection)** — the two forms use
*different* field names (`input[name=username]` on login vs `input[name=email]` on signup),
`wait_for_selector("input")` hangs on the hidden `state` field, the consent screen is a second
gate, a "Something went wrong" banner on signup does **not** mean registration failed, and the API
token is captured from the `/oauth/token` network response rather than the SPA's in-memory client:
`references/auth0-universal-login-provisioning.md` (verified on console.hivecompute.ai, 2026-10-26).

**Also covers Auth0 PASSWORDLESS (email-code) tenants** — no password exists at all, and the selectors
differ from the DB-connection form in a way that silently burns 30 s per guess: the email input is
`input[name="email"]` with **`type="text"`**, so `input[type="email"]` / `input[type="text"][name=…]`
combinations time out even though the field is visibly there, and the page carries **9+ hidden
`state`/`connection` inputs** that defeat any `wait_for_selector("input")` strategy. The two-step shape is
`sigup|login/identifier` (fill `email` → submit) → `login/passwordless-email-challenge` (fill `code` →
submit). Read the OTP with the Gmail API refresh-token flow, then poll *before* typing: on this tenant the
code mail landed in ~4 s but the challenge page took ~6 s to accept input. Full recipe, including the
`451` consent gate that blocks the API *after* a successful login:
`references/auth0-passwordless-otp-and-consent-gate.md` (verified on dashboard.aghanim.com, 2026-10-27).

**Also covers Privy-backed web3 / embedded-wallet apps** (the IdP behind most crypto, agent and
trading products): the whole account — including the app-side cross-chain wallet — is created with
curl in ~6 calls, no browser. Two traps dominate: the app authenticates with **`x-access-token` +
`privy-id-token`**, NOT `Authorization: Bearer` (wrong header = flat `401 Authentication required`
on a perfectly good token), and `+tag` / dot aliases of one mailbox collapse to **one** app account,
so the alias family cannot give you a second identity for cross-tenant tests. Disposable mailboxes
pass OTP at the IdP and then get `500 Failed to set up your wallet` at app bootstrap — that is a
provisioning refusal, not a transient error. Recipe, tenant-config discovery, guest/SIWE switches
and mailbox polling: `references/privy-headless-wallet-provisioning.md`.

**Also covers JSON:API backends** (Laminas/API-Platform style, `application/vnd.api+json`): three separate
calls — signup `POST /users` with a **caller-chosen `data.id` ULID**, activation via a **short-link** whose
`302 Location` carries `confirmToken` (extract from the redirect, not the email body), and a **`GET`
`/users/signin` with HTTP Basic auth** returning an RS256 JWT. Then the post-provisioning IDOR check that
paid off: a `/v4/users/{ulid}/id` resolver that returns the **sequential internal id with no ownership
check** (BOLA). Recipe + the weak-ID and no-scanner-eligibility notes:
`references/jsonapi-signup-and-basic-auth-signin.md` (verified on wallbox.com, 2026-11).

## Step 0 — Map the auth surface into a GATE MATRIX before automating anything
The expensive failure mode is spending an hour on the captcha when the real gate is something else. Do
this first; it takes ~10 minutes with introspection + source and it tells you which paths are even reachable.

1. **Enumerate the private auth API, not just GraphQL.** Mobile-first apps put signup on a REST auth
   service behind the same reverse proxy: `/auth/create/device-account`, `/auth/email/code`,
   `/auth/email/login`, `/auth/phone/captcha`, `/auth/phone/code`, `/auth/phone/code-appcheck`,
   `/auth/phone/login`, `/auth/totp/validate`, `/auth/telegram-passport/*`. Find the base from the client
   source (`CORE_AUTH_URL` default in the repo's `env.ts`, e.g. `http://localhost:4455/auth` → prod
   `https://api.<target>/auth`) and probe **route existence** with GET vs POST (`401` vs `404` tells you a
   route exists but is gated).
2. **Introspect the GraphQL `Mutation` type** and read each candidate resolver's *context type* in the
   public source. **Mutation names lie** — a name containing `Registration`/`Signup` is often the
   *authenticated* "add a credential to my account" flow. Tell: the resolver reads `user.id` from the
   context (`GraphQLPublicContextAuth`), so without a token it answers `NOT_AUTHORIZED`.
   `AuthorizationError` → `"Not authorized"` (`NOT_AUTHORIZED`) is a **scope/identity** failure;
   `AuthenticationError` → `"Not authenticated"` (`NOT_AUTHENTICATED`) is a **missing token**. Do not
   confuse them, and do not report "signup is disabled" until you know which one you got.
3. **Classify every route into one of four buckets** and write it down before acting:

   | Bucket | How to prove it | What it buys you |
   |---|---|---|
   | unauthenticated + uncaptcha'd | real `200` with a payload (`/auth/email/code` → `{"result":"<uuid>"}`) | free recon; may or may not be a bug |
   | captcha-gated | omitted params → `missing inputs`; junk params → `CaptchaUserFailToPassError` | the gate you must actually beat |
   | **attestation-gated** | `401` unless the proxy injects proof (`x-appcheck-jti`) | **dead end — stop, see below** |
   | auth-required | `NOT_AUTHORIZED` / `NOT_AUTHENTICATED` | needs the account you don't have yet |

4. **Attestation gates are not beatable from a script — recognise and walk away.** When the route needs a
   Firebase AppCheck / Play Integrity / App Attest JWT, remember *who* verifies it: the edge proxy
   (Oathkeeper `jwt` authenticator with a **pinned** `trusted_issuers` + `jwks_urls` + `target_audience`),
   injecting `X-Appcheck-Jti` into the upstream. You cannot mint that token without an app registered in
   the vendor's own Firebase project. Confirm the shape once (send `Appcheck: undefined` / junk / omit →
   `401`), record it, and move to the human path. Do not grind on it.
5. **Prefer the path with the fewest unmovable gates.** Rank: email-only signup > web captcha (solvable
   by a human in 20 s) > phone OTP via a channel the operator actually owns > mobile attestation (never).
   Then automate every step *except* the human one, and make the human step a single screen interaction.

## ⛔ Rules first
- **Identity is the operator's call.** (A) operator's real email, (B) operator mailbox via IMAP,
  (C) disposable inbox — **only with explicit operator approval**. Ask, don't assume.
- **Tag the account** exactly as the program asks (Ably: `bugbountyably` in the company field) and never
  submit an **AI-written** report where the policy forbids it (Ably does).
- Stay inside scope/ToS; do not fabricate KYC/KYB or regulated-entity data.

## Step 1 — Disposable inbox (option C): mail.tm
```python
d    = requests.get("https://api.mail.tm/domains").json()          # -> a LIST, use x["domain"]
r    = requests.post("https://api.mail.tm/accounts", json={"address": f"{local}@{dom}", "password": pw})
addr = r.json()["address"]                                         # USE THE RETURNED ADDRESS (dots stripped!)
tok  = requests.post("https://api.mail.tm/token", json={"address": addr, "password": pw}).json()["token"]
msgs = requests.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {tok}"}).json()
```
**Pitfalls:** `/domains` is a list (not `hydra:member`); the API **strips dots** so token with the
*returned* address or you get `401 Invalid credentials`; message `html` can be a **list** — join it.

## Step 2 — Read the signup contract from the front end (before automating)
Client-rendered forms hide the endpoint. Get it from **source maps** (often public):
`/assets/*.js` → fetch `<file>.js.map` → JSON `sourcesContent` (full TS source). Grep for
`registrationPath`, `fetchWrapper(`, `POST`, `JSON.stringify`, `/users`, `sessionPath`.
On Ably this gave the exact contract:
`POST /users.json` body `{"user":{"name","company_name","email","accepts_terms":"1","marketing_opt_in":"1","password"},"g-recaptcha-response":"<token>"}`
and the React props block `data-...-props-value="{...registrationPath:"/users.json"...}"`.

## Step 3 — Drive signup in a REAL browser (live Chrome)
```python
ctx = p.chromium.launch_persistent_context(PROFILE, channel="chrome", headless=False,
      args=["--disable-blink-features=AutomationControlled","--no-first-run"])
```
- Dismiss the OneTrust banner first (`#onetrust-accept-btn-handler`).
- Click "Or continue with email" to reveal the email form; fill `input[name="user[...]"]`.
- **reCAPTCHA v2 (checkbox)** — click inside the anchor iframe, no challenge on a real browser:
  ```python
  pg.frame_locator("iframe[src*='recaptcha/api2/anchor']").locator("#recaptcha-anchor").click(force=True)
  # wait until textarea[name=g-recaptcha-response].value length > 20; a VISIBLE bframe = human needed
  ```
- **reCAPTCHA v3** — needs the **sitekey** (grep `6L[0-9A-Za-z_\-]{20,}` in JS or the iframe `k=`), then
  `grecaptcha.render(div,{sitekey,size:'invisible'})` + `grecaptcha.execute(wid,{action:'signup'})`.
- A real navigation to `/onboarding` or `/dashboard` = account created + logged in.

## Step 4 — Direct POST fallback (bypass React validation)
POST the contract **from inside the page session**:
```python
pg.evaluate("""async ({body}) => (await fetch('/users.json',{method:'POST',credentials:'same-origin',
  headers:{'Content-Type':'application/json','Accept':'application/json'},
  body:JSON.stringify(body)})).text()""", {"body": body})
```
Need the **CSRF token** (`csrf-token` meta / `authenticity_token`) for state-changing posts, else `401`.

## Step 5 — Email verification
- Poll the inbox, fetch message body.
- **Extract the code by CONTEXT, not by value.** CSS colours like `#292831` look exactly like a 6-digit
  code. On Ably the real code was `821245`; `292831` was a text colour. Prefer text near "verify"/"code".
- Type into the `maxlength=6` input; it auto-submits on the last digit (also try Enter).

## Step 6 — Onboarding wizards
Products gate the dashboard behind onboarding (Ably: "what are you building?" → AI chat → create first
app → verify email). Automate: fill textarea, click Continue/Send, **wait ~9 s** for the AI, repeat until
the URL leaves `/onboarding`. `GET /accounts/<id>.json` → `403 onboarding_incomplete` = not done;
`email_not_verified` = only the code is left.

## Step 6b — When the LOGIN page won't drive, call the API directly
Modern React/Vite apps (especially with an IdP) often have an **un-drivable login** (2-step, customer
buttons or a "Continue" that silently routes the primary action to **"Continue with Google"**, encrypted
request bodies like `sgbody:v2`, JS-set cookies). Do NOT burn 40 minutes on the DOM — authorise via API:
```bash
POST https://api.<target>/auth/api/v1/user/login   {"email":"...","password":"..."}
# -> 200 {access_token, refresh_token, id_token, tenant_id, scope, ...}
```
- Find the base by watching the **Network** tab during signup (e.g. `api.safeguard.sh/auth/api/v1/user/signup`).
- Decode the **access_token JWT** — claims reveal `sub`, `iss`, `realm_access`, `resource_access`, tenant.
- Use it as `Authorization: Bearer <access_token>` for the whole authed plane; also try the MCP tool
  endpoints (`/api/tools/<name>`) which a UI may hide.
- `iss: http://localhost:8083/idp/realms/<x>` in a **production** token = an internal-issuer info leak
  (CWE-200) — note it, but it is usually informational, not reward-worthy on its own.

## Step 6c — A `451` after a successful login is a CONSENT wall, not a broken session

Verified on dashboard.aghanim.com (2026-10-27). Auth0 passwordless login succeeded, cookies +
`localStorage` access_token were captured, and then **most of the API answered
`451 {"detail":"Terms of service has changed"}`** while a handful of endpoints kept working
(`/companies/games`, `/invites/me`, `/customers/outdated_agreements` returned 200). The SPA parks you on
`/onboarding` and asks you to tick two checkboxes.

The UI would not submit for me — the page's own "Accept" button was a **cookie-banner** Accept, and
`input[name=privacy]` / `input[name=terms]` clicked `checked` without firing React's handler (the classic
§3f tell). Do not fight it: **call the consent endpoint the SPA calls.**

```python
GET  /dashboard/v1/customers/outdated_agreements
  -> {"terms": true, "privacy": true, "terms_version": null, "privacy_version": null}
POST /dashboard/v1/customers/accept_agreements   {}        -> 204      # tenant-MEMBER variant
POST /dashboard/v1/companies/{company_id}/profiles/accept_agreements    # per-company variant
GET  /dashboard/v1/profiles/me                   -> 200 {"id":"cmr_…","email":"…"}   # gate gone
```

Rules:

1. **A 451 is a gate, not an error to retry.** Grep the bundle for `accept_agreements` /
   `outdated_agreements` — the pair tells you the exact contract, and it is usually a bare `POST []`
   (204 on success).
2. **Two variants exist, and which one you need depends on whether you are a tenant member.** A fresh
   self-signup is provisioned as a *company-less customer* (`cmr_…`, `mode: 1`) inside an auto-created
   "Demo Corp" — the customers/* variant is the one that clears it. An invited teammate needs the
   companies/* one.
3. **Gate-awareness first, discovery second.** Before crawling an authenticated API, hit `/profiles/me`
   (or `/me`) once and treat any 451/403-on-everything-else as "onboarding incomplete", then check
   `/onboarding` in the UI text. Otherwise you record a dozen endpoints as "gated by auth" when the real
   cause was an unaccepted ToS — a false negative across the entire plane.
4. Related: some tenants return `403 "Terms of service has changed"` only on **write** endpoints while
   reads stay open. Same fix; do not report it as broken access control.

## Step 7 — Extract material, pivot to the authed plane- **API keys** on `/accounts/<slug>/apps/<api_id>/app_keys`: regex `APPID\.[A-Za-z0-9_\-]{6,}:[A-Za-z0-9_\-]{6,}`
  (match the real app id, e.g. `TUmWSA.*:*` — not CSS tokens like `ion-layout.ot-cat-item`).
- Persist `ctx.storage_state(path=...)` after every step — the session is the asset.
- Then run authed checks: **IDOR/BOLA** (`/accounts/<other-id>`, cross-slug), business logic
  (billing/plan/entitlement), realtime authz, **capability-token enforcement**, outbound **webhook SSRF**
  (`interactsh-client` as the URL target).

## Step 3c — Wallet / embedded-IdP logins (Para, Capsule, "Sign Up or Login" widgets)

Full recipe: `references/para-capsule-wallet-login.md`. The shape that generalises to any
wallet-as-a-service login (and to custom-element auth widgets generally):

1. **The DOM will look empty.** The email field lives in a **shadow root** (`cpsl-*` custom elements), so
   `document.querySelectorAll('input')` returns only the terms checkbox. Walk shadow roots; fill with the
   **native value setter** + `input`/`change` events (React-controlled inputs ignore `el.value = x`).
2. **Submit by coordinate.** There is no `<form>` and no button inside the field's root — enumerate visible
   buttons with `getBoundingClientRect()` and click the small icon button just right of the field via
   `Input.dispatchMouseEvent`. `Enter` sometimes works, sometimes silently does nothing; one failed Enter
   is not a broken flow.
3. **The OTP step is a cross-origin OOPIF** (`app.usecapsule.com/auth/otp`). Route CDP calls to it by
   passing the **iframe targetId as `target_id`** in `browser_cdp` (the `frame_id` route needs the CDP
   supervisor, i.e. `browser_navigate`, which a hand-launched Chrome does not have). Its body can be empty
   on first attach and render seconds later — poll before concluding failure; when the target disappears,
   the code was accepted.
4. **Read state from localStorage, not the UI** (`@PARA/modalState` → `step`; `@CAPSULE/userId`,
   `@CAPSULE/sessionCookie`, `@CAPSULE/wallets`). `step:"AWAITING_ACCOUNT"` + `wallets:{}` means verified
   but no wallet → no app session yet. **But never conclude "wallet stalled" from localStorage alone** —
   see step 8: a minted JWT + a real EVM address still produces no app session when the app gates entry.
8. **STALLED AFTER OTP? CHECK FOR AN APPLICATION GATE BEFORE BLAMING THE WALLET.** This is the #1
   misdiagnosis. Verified live on app.vana.com (2026-10): the flow looked stuck at
   `step:"AWAITING_ACCOUNT"` for ~3 minutes, and I reported a "wallet creation blocker" — wrong. The
   evidence that the identity was fully provisioned was in the SDK's own network traffic:
   - `POST https://api.getpara.com/assets/balances {"wallets":[{"type":"EVM","address":"0x…"}]}` → a wallet existed,
   - `POST https://api.getpara.com/auth/jwt {"keyIndex":0}` → a JWT was minted,
   - `GET  https://api.getpara.com/users/supported-auth-methods/v2?email=<e>` → identity recognised.
   What actually blocked was the **application's own gate**: the app page rendered
   *"Vana is invite only (for now) — Enter your code or join the waitlist"*, and the app issued **no
   session cookie at all** (`Network.getAllCookies` → only `cf_clearance`). The vendor's blog confirmed
   invite-only onboarding with codes distributed via their community.
   **Diagnostic order when a post-OTP flow stalls:** (a) capture the SDK's requests and look for balance /
   JWT / auth-methods calls — if they succeed, provisioning is *done*; (b) read `document.body.innerText`
   on the app's post-login URL — invite-only / waitlist / referral-code gates are plain text, not errors;
   (c) dump cookies — **no app session cookie = a gate, not a crypto bug**; (d) only then consider
   passkey/MPC. State the gate plainly to the operator and name what you need (a legitimately obtained
   invite code) instead of burning an hour on the wrong layer.
   **Map the gate as its own surface while you are there** (it is in scope and cheap): the invite
   validation endpoint answered a **uniform** `404 {"valid":false,"reason":"not_found"}` for random,
   empty and missing codes → no validity oracle (good design, nothing to report); no rate-limit headers
   were observed in 5 gentle probes, which is **not** proof of absence — testing that needs a bounded
   burst and must be labelled as a rate-limit test, never as code guessing.
   **Size the keyspace from the DOM before scoring it.** The same page's code input carried
   `maxlength=6` and `pattern="^[a-zA-Z0-9]+$"` → 62^6 ≈ 5.7e10, and *that* is what turns "no rate limit"
   from a style nit into a brute-force question. Read the attributes
   (`document.querySelectorAll('input')` → `maxLength`, `pattern`, `placeholder`), quote the keyspace in
   the write-up, and keep the probe honest and bounded with
   `scripts/ratelimit_probe.py "<url-with-{code}>" --steady 30 --burst 10 --out evidence/rl.json`
   (random codes only, self-labelled "rate-limit testing", JSON with status set / 429+Retry-After count /
   per-phase median+p95 latency as attachable evidence). Verdict on the Vana run: 40 requests, all uniform
   `404`, no 429/Retry-After, median 0.46 s → reported as **low (hardening)**, explicitly NOT as a
   demonstrated bypass, because no valid code was ever found.
5. **Passkey steps need a virtual authenticator in ONE persistent session** —
   `WebAuthn.enable` + `WebAuthn.addVirtualAuthenticator` must share a CDP session (per-call stateless CDP
   loses the virtual environment: *"The Virtual Authenticator Environment has not been enabled for this
   session"*). Hold a WebSocket to the target's `webSocketDebuggerUrl` (also lets you log the SDK's calls).
6. **Do not finish via the IdP's API.** Direct calls to the vendor's verify endpoints return **403** without
   portal-scoped flow headers, and the IdP is a **third party, not the target** — stay on the app's own
   client flow, record the public client config as intel, and never as a finding.
7. **Know when to hand off.** If the wallet/MPC creation step stalls, hand that 30-second step to the
   operator **in the Chrome you launched** so the resulting session cookie is still in a profile you can
   read (`Network.getAllCookies`) — then run the authed suite. A human handoff is the right call at a UX
   wall; say so plainly instead of burning an hour or filing it as a finding.

## Capability-token enforcement (Ably-style, reusable pattern)
```python
# POST /keys/<FULL_KEYNAME>/requestToken   body needs ALL of:
{"keyName": "<APPID>.<keyid>", "capability": json.dumps({"*":["*"]}), "clientId": "x", "timestamp": ms}
```
- `400 no keyName/timestamp` = malformed request (include them).
- **A 201 does NOT mean escalation.** Round-trip the token: the grant must be the **intersection** with
  the key. Prove it — publish-present-only channel → 401; presence → 200. Test a *limited* key
  (publish=401) and a *full* key (publish=201) separately.

## Step 3d — OAuth "continue with X" opens a POPUP, not a redirect (headless fails silently)

Verified on CodeRabbit (2026-10-21): clicking "GitHub Cloud" on the login page calls `window.open`,
so `pg.url` **never leaves the app origin** and the click looks like a no-op. Two consequences:

- **Headless is a dead end for this flow.** Run it **headed** (`headless=False`, `bring_to_front()`)
  and catch the popup with `ctx.on("page", lambda pg: popups.append(pg))` — the GitHub authorize page
  lives in that popup, and the operator completes it there. Poll BOTH `pg.url` and every popup's url;
  success is the MAIN page leaving `/login` (the popup closes itself on callback).
- After the operator authorizes once, the GitHub app remembers the grant, so a later automated
  re-run (headless is fine) only needs the click → instant redirect back with `?code=…`. If a
  headless re-run still does not redirect, the popup was blocked — the fix is popup handling, not
  more retries. Full walkthrough: `references/oauth-popup-signup-flow.md`.

## Step 3e — Invisible reCAPTCHA on submit: the zero-request tell

Verified on Cloudsmith (2026-10-21): the signup form carried **no visible captcha widget**; the
reCAPTCHA (v3-style invisible, sitekey in the anchor iframe `k=`) only executed on Continue. The
diagnostic that distinguishes it from a React-state failure: **filter every network request during
the Continue click** (exclude datadogh/sentry/assets). A React-state failure still fires the app's
own XHR; an invisible-captcha block fires **only** `google.com/recaptcha/api2/anchor` + `bframe`
and nothing else. Headless fails silently, headed-automated fails, and a human drag can also fail
(reCAPTCHA v3 scores the whole session, not just the widget). When you see the anchor/bframe pair
and zero app requests: stop, log BLOCKED at the authenticated surface, and pivot to the
unauthenticated plane (public API endpoints, OpenAPI schema, package feeds) — Cloudsmith's
`/v1/packages/{org}/{repo}/`, `/v1/formats/`, `/v1/openapi/` were all reachable without an account
and the WAF only blocked the bare API apex from datacenter IPs.

## Step 3f — Terms checkbox: click the LABEL; and the zero-request React diagnostic

Verified on Cloudsmith (2026-10-21), same family as the hydration trap but a distinct tell:

- `input[name=acceptTerms].click()` (JS or real mouse at its coordinates) sets `checked=true` in the
  DOM while React's `onChange` never fires — the form still submits as "terms required". Clicking
  the **`<label>` text** (`pg.locator("label:has-text('service terms')").click()`) fires the real
  change event. Always assert `cb.checked` AND re-read the error text after the click.
- **Zero app-request diagnostic:** if a real mouse click on Continue produces no app XHR at all,
  React state never received the field values — synthetic `value` setters lie (`el.value` reads
  back correct while the component state is empty). Re-fill with **trusted keyboard typing**
  (`locator.click()` then `pg.keyboard.type(val, delay=40)` per field), which is the only input
  path that reliably registers in these wizards.

## Step 3g — Signup anti-abuse blocked? The email is often ALREADY REGISTERED — finish via LOGIN magic-code
Verified on Betterteam (2026-10-24): repeated signups from one IP escalate to a hard
"Access blocked, please contact support" (the email+name step still advances to the password step,
but the password submit is blocked). BUT the login plane is NOT blocked, and the address you typed
during the blocked signup is already registered as a PENDING user. Recovery that works:
1. Go to the LOGIN page, enter the same `+bugbounty` alias, Continue.
2. Choose the **"Email sign-in code" / magic-code** option (not password — none was ever set).
3. Read the 6-digit code from the operator mailbox (Gmail IMAP, plus-alias), type into `input[name=code]`.
4. You land authenticated; save `ctx.cookies()` / storage_state immediately.
Tell: the login recognises the address (advances past the email step) = the pending account exists.
This turns a "signup blocked" dead-end into a provisioned session without beating the anti-abuse gate.
If login ALSO blocks or the address isn't recognised, it's a genuine wall — say so, don't grind.
(Contrast with the Proton silent-drop case in Pitfalls: there the block is IP-level and hits every path;
here the login plane stays open, which is the discriminator.)

## Step 3h — OAuth-only SaaS (no email signup): provision a GitLab account as the OAuth enabler
Verified shape on CodeRabbit (2026-10-24): login is GitHub/GitLab/Bitbucket/Azure/SSO only — no
email/password signup, so the plus-alias trick does not apply. GitLab signup is OPEN (email + verify,
no SMS / geo-wall observed) → create a GitLab account on the operator plus-alias → use "GitLab Cloud"
to OAuth into the target. Watch for the OAuth POPUP (Step 3d): `window.open`, so `pg.url` never leaves
the app origin — run headed, catch the popup with `ctx.on("page", …)`, poll BOTH urls. Rank the forge
the operator already has an account on before creating a new one.

## Step 3i — TOTP/2FA enrolment: recover the SECRET from the QR, don't relay codes

The moment a login shows an OTP field, you have a scheduling problem: codes live
30 s, the flow has several stages, and an audit needs many re-logins plus a
second identity for IDOR differentials. Do **not** set up a request-a-code loop
with the operator.

**Ask once for the enrolment/export QR image**, decode it, and generate codes
locally forever:

```bash
python scripts/decode_totp_qr.py <qr.jpg> --json ./totp.json
# -> secret (base32), issuer, algorithm, digits, type, and a live code
```

Then feed the harness from JSON, never from a literal (see the char-codes
pitfall below), and **wait for a fresh 30 s window before submitting** — a code
submitted with <10 s left renders "invalid authenticator code" and burns an
attempt on a rate-limited IdP.

Handles both `otpauth-migration://` (Google Authenticator export, protobuf — the
common case) and plain `otpauth://totp/…`. Full recipe, the protobuf field map,
the QR-decode failure ladder, the Keycloak two-stage login form map, and the
"find the QR on the operator's disk" step:
`references/totp-2fa-enrollment.md`.

**Having the secret does not make the target's 2FA off-limits** — use it to test
whether the *direct-grant* path (password / client_credentials / device-code)
skips the second factor, whether an accepted code replays, and whether the
post-auth redirect works with pre-OTP cookies only. All three were clean
negatives on Genians/Keycloak (2026-10-27); record those as evidence, not
findings.

## Step 3j — Cloudflare Turnstile: the widget must be CLICKED, it does not auto-solve

Verified on scribblemaps.com (2026-10-31) on **both** the register form and the reporter-portal form.
This is the single most common reason a signup/report automation "hangs at the captcha" when every
other gate is already beaten.

**The tell.** The widget container has a real bounding box, yet:

```python
d = page.evaluate("""()=>{const el=document.getElementById('registerTurnstile');
  const r=el?el.getBoundingClientRect():null;
  return {rect:r?[r.x,r.y,r.width,r.height]:null,
          iframes:[...document.querySelectorAll('iframe')].length,      # -> 0
          resp:(()=>{try{return window.turnstile.getResponse()}catch(e){return 'err'}})()}}""")
# rect = [550,439,300,69]  iframes = 0  resp = null
```

`iframes: 0` is **not** proof the widget failed — the iframe lives inside the widget div and is not
reachable with `document.querySelectorAll('iframe')`. `resp: null` after 90 s of polling is the real
signal: **no token was ever issued.**

**The fix — click the checkbox inside the widget:**

```python
rect = page.evaluate("()=>{const el=document.getElementById('registerTurnstile');"
                     "if(!el)return null;const r=el.getBoundingClientRect();"
                     "return [r.x,r.y,r.width,r.height]}")
page.mouse.click(rect[0] + 32, rect[1] + rect[3]/2)     # checkbox sits left, vertically centred
# token appears ~4 s later
for i in range(45):
    time.sleep(1)
    if page.evaluate("()=>{try{return window.turnstile.getResponse()}catch(e){return null}}"):
        break
```

Notes that save a re-run:
- Click x-offset `+32` (register widget) and `+36` (portal widget) both worked; the checkbox is on
  the **left**, vertically centred — do not click the centre of the box.
- `turnstile.reset(sel)` + `turnstile.execute(sel)` as a fallback did **not** help when the click had
  already failed; the click is the operative action.
- **It is flaky, not deterministic.** On the same profile the click produced a token in 4 s during a
  diagnostic run, then failed on three consecutive attempts in the next run. Treat one failure as
  "retry later", not "impossible" — and have the captcha-free fallback ready (see
  `bug-report-delivery` → `references/_split/10-portal-submission-discipline.md` §7).
- Sitekeys differ per form (register vs portal) — read `data-sitekey` from the HTML, never hardcode.
- A **headed** real Chrome is required; headless never produced a token here.

## Step 0b — Prove there is NO self-service signup before calling the authed plane blocked

Every section above assumes a signup exists and the problem is beating its gates. Enterprise B2B SaaS
(healthcare, compliance, ERP, on-prem-lineage products sold per-tenant) frequently provisions **every**
account through the vendor or the customer's own admin. There is no signup route, no free tier, no
self-serve trial.

Verified on Zenya/Infoland (2026-10-31): the Vue login router accepted only
`credentials|saml2|nosaml|asdifferentuser`; 7 registration paths × 12 hosts all 404; the support portal
SSO'd to a *different corporate domain*; the form host had no reporter portal.

The failure this prevents is not wasted time — it is reporting "authenticated surface unreachable" in a
way that reads as giving up. Produce the matrix, then state it as a proven blocker:

1. **Read the login router's accepted types out of the bundle** instead of guessing paths. Vue/React
   routers carry `path:'/:type?/:step?'` plus a `beforeEnter` that whitelists values, e.g.
   `['credentials','saml2','nosaml','asdifferentuser'].includes(type) ? next() : redirect({name:'login'})`.
   That whitelist **is** the answer: if `register`/`signup` is not in it, no URL reaches a signup view.
   Grep the bundle for `path:` and `beforeEnter` before sweeping anything.
2. **Sweep registration paths across MANY hosts, not one.**
   `/register /signup /registreer /aanmelden /Registratie /registration /account/register` against the
   trial host, the demo host, AND a sample of real customer tenants. One host 404ing is weak evidence;
   twelve agreeing is the matrix that justifies the conclusion.
3. **Check every other auth door before concluding.** The OTP route (`POST /api/tokens`) needs an
   `api_key` you cannot mint; the password route needs real credentials; the support/DevRev portal may
   SSO to a **different corporate domain** (Zenya's redirected to `my.infoland.eu` — outside the written
   scope, and SSO is not signup anywhere).
4. **Check whether the submission channel itself minted an identity you can use.** Usually it did not —
   Zenya's CVD form host answered the same error template for `/Case.aspx`, `/Status.aspx` and
   `/Track.aspx` with a random GUID as with a real one, so there was no reporter portal to log into.
5. **⛔ Never fabricate an organisation on a demo/sales form** to obtain a tenant. Registrable-entity data
   belongs to the operator. Ask them, or request a test account through an already-open disclosure thread
   — that request is normal practice and it can ride on a report you already filed.

Then pair the blocker with the next-best surface, which is what the reachability gate asks for anyway.

### A login route that 404s may just be missing its version header

**404 is not proof a route is absent on a versioned API.** Zenya's documented
`POST /api/bearer_tokens` returned `404 Not Found` for every request — anonymous, with credentials, with
junk — until `X-Api-Version: 5` was added, at which point it answered
`401 {"title":"invalid_login_or_password"}`. The vendor's own API doc curl example omits the header and
fails identically.

Two consequences:

- An anonymous sweep that omits the version header will silently mark real routes as 404, and you will
  record them as non-existent. **Re-probe every auth-ish 404 with the version header** (and with
  `?api-version=N` / a versioned `Accept`) before writing it off.
- The `404`-vs-`401` distinction you *did* observe may be an artifact of your own request shape, not of
  the server's routing — the same class of error as concluding from a truncated string: the instrument
  reporting on itself.

### A uniform 401 across existent and non-existent users is a held control

Once the route answers, run the enumeration test properly and record the negative: 3 runs ×
{nonexistent, admin, beheerder, test} × 2 hosts, one fixed dummy password → 24/24
`401 invalid_login_or_password`, **one** distinct body, latency 1.0–3.4 s. Verdict: hardened, no
user-existence oracle, no timing oracle — worth stating as a property, not filing as a finding. Do not
scale the request count into a real brute-force; that is a different, unauthorised test.

## Payable-surface-gated triage (do this BEFORE committing an engagement)
Recurring wall (2026-10-24, three targets in a row): the bug-bearing surface is gated behind
(a) a **subscription/paywall** — djangoeurope & Betterteam both require a paid plan to *publish* a job,
which is what stands up the career site / resume-upload / applicant surface the rewards pay for;
(b) **OAuth-only registration** (Step 3h); (c) a **platform store** — tinyseo.com is a Shopify app whose
real backend only exists once installed on a store. Before investing, answer: is the payable surface
reachable on the FREE tier (open registration + a feature usable without paying)? If not, label the
engagement "paywalled / unauth-surface-only" up front instead of discovering it at the authed plane —
and confirm a program exists at all (tinyseo had no security.txt / VDP / safe harbor).

## Pitfalls (all hit for real)
- Disposable domains are sometimes **blocked** — page accepts signup but no mail arrives; empty inbox = rejected.
- Native tools here do **not** get MSYS path translation: use `D:/path` in Python, never `/d/path`.
- `/accounts/<id>/x.json` can answer `406` under `Accept: application/json` — retry with `Accept: text/html`.
- State-changing POST answered `401 "requires you to be logged in"` = **missing CSRF token**.
- "confirm/verify" on a page may be the **cookie banner** ("Confirm My Choices") — confirm by URL change, not substring.
- Keep `interactsh-client -json -o <file>` running; only interactions that arrive are logged.
- **Plus-alias beats a disposable inbox when the operator offers their mailbox** (`user+<target>@gmail.com`):
  it tags the account, arrives in their real inbox, and needs no domain that might be blocklisted. Read it
  with the Gmail API token at `%LOCALAPPDATA%\hermes\google_token.json` (`refresh_token` grant →
  `messages?q=from:<sender> newer_than:30m`). Still extract the code **by context** — the first 6-digit run
  in an HTML email is often a colour/size.
- **If the signup form rejects the `+` alias, fall back to a Gmail DOT-VARIANT — and probe it with the API,
  not the form.** Some vendors reject plus-addressing outright and the failure is silent. Verified on
  amboss.com (2026-10): `createUser` returned `CreateUserInputValidationError` for `user+tag@gmail.com`,
  `@mailinator.com` and `@yopmail.com`, but `AuthToken` for `RESEARCHER_NAMEsusanto.amboss@gmail.com` and for the
  dot-variant `f.z.susanto@gmail.com` — dots are ignored by Gmail, so the mail still lands in the
  operator's real inbox and the variant reads as a distinct address to the target. **Sweep the shape, not
  one guess:** send the same mutation with (a) a `+` alias, (b) a dot-variant, (c) a disposable domain and
  read which one returns the success type — the differential tells you the vendor's email policy in three
  requests instead of ten minutes of form-filling.
- **Some vendors canonicalize the `+` tag away — the whole alias family collides, go straight to a
  disposable inbox.** Verified on Adafruit (2026-10-21): account #1 registered as
  `user+tag1@gmail.com`, then every subsequent `+tag` attempt failed with *"The canonical form of
  your email is already taken"* — the server strips the plus-suffix (and dots) before the uniqueness
  check, so tag1/tag2/tag3 are one address to it. The tell is that exact error string; when you see
  it, stop sweeping aliases and dot-variants (both collide) and provision account #2 on a
  disposable inbox — the mail.tm recipe in Step 1 worked first try (`201`, `maxxspace.com` domain).
  Corollary for IDOR testing: you need two genuinely independent identities, and a temp-mail
  account is the reliable second one on any vendor with strict canonicalization.
- **When the SPA's own signup route 500s, register through the UNDERLYING MUTATION/API.** A Next.js BFF
  route (`POST /us/register`) answered `HTTP 500` with body `default`, and a CDP-driven form fill produced
  the app's generic "Something went wrong" — while the backing GraphQL mutation
  `createUser(data:{channel:passwordSignup,email,password})` succeeded directly and returned an
  `AuthToken`. Capture the real request once in a CDP-driven browser to learn the mutation + argument
  names, then script the API for every subsequent account. Do not conclude "signup is broken / the target
  is untestable" from a broken BFF route.
- **Log every account you create, including the incidental ones.** Probing the email policy above created
  three accounts on addresses that were not the operator's (`RESEARCHER_NAMEsusanto.amboss@…`,
  `amboss.research2026@…`, `RESEARCHER_USERNAMEamboss@…`). They are unverified (no email confirmation completed) but
  they exist and some may route to third parties. Write them into `ENGAGEMENT_LOG.md` next to the intended
  test account and disclose them for vendor cleanup — an account you created while probing is still a
  state change on the target.
- **A hand-launched Chrome must keep its `--user-data-dir`.** If the operator finishes a step manually in
  that window, the session is only harvestable because you launched it — never point them at their own
  everyday profile, and never delete the profile until the authed suite has run.
- **Verified ≠ provisioned.** The gate is an authenticated call succeeding (`/api/me` 200), not an email
  code being accepted. A flow that verifies the address and then stalls before issuing a session is a
  GAP to report as such, not a partial success to build tests on.
- **A signup `201` from a bypassed client-side gate is NOT a provisioned account until the
  confirmation mail is seen.** On Rails+React apps the direct `/register.json` path (no Turnstile)
  can return `201 {"urlRedirect":"/unconfirmed"}` while the transactional-email job never runs;
  login pre-confirmation then answers a generic `403` and `/check-email` gives no existence
  oracle. Poll the operator's inbox via Gmail API (`includeSpamTrash`, both `+` and dot aliases,
  ≥30 min) before you declare either "account ready" or "target untestable" — and if mail never
  arrives while unrelated mail flows, log the engagement as BLOCKED at the authenticated surface
  with the evidence trail, never as "0 findings".
- **On pack-heavy React SPAs, form input before hydration silently no-ops** — the DOM value
  updates (so `el.value` lies), no XHR fires, MUI `check()` reports "did not change its state",
  and `click()` fails with "element is not stable". Wait 15–25 s after `domcontentloaded`
  (assert by an app XHR appearing, not a fixed guess — `networkidle` never fires on
  analytics-heavy pages), then JS-`focus()` + trusted `keyboard.type` + `Tab` to blur
  (`mode:"onTouched"`), and poll `button.disabled` via `evaluate`. Details in
  `references/react-rails-signup-traps.md`.
- **CDP target ids come in two shapes.** `http://127.0.0.1:9222/json` returns `id`; `Target.getTargets`
  returns `targetId`. A script that reads `/json` and then calls `Target.attachToTarget` with
  `t["targetId"]` dies with `KeyError: 'targetId'` before doing any work — use
  `t.get("targetId") or t.get("id")`. Attach with `flatten: true` and pass the returned `sessionId` on
  every later `Runtime.*` / `Input.*` call so they land inside the cross-origin iframe.
- **Register through the program-specific URL if the policy names one.** Bounty
  programs often publish a dedicated registration link (`…/register/?registertype=bugbounty`)
  and state that registering through the normal customer form disqualifies the
  reward. Read the policy's reporting article before filling any form.
- **⛔ Before you call anything in an email "malformed/truncated", prove the
  `...` is in the DATA and not your own tool-output truncation.** Verified the
  hard way on Genians (2026-10-27): a verification link printed as
  `…/login?loginuse_mailkey=eyJhbG...k89A&user_idw74` looked like the template
  had lost the `=` in `&user_id=<val>`, and a whole chain of variants (`=w74`,
  `=74`, `=1`, key-only) all failed — which appeared to confirm a permanent
  functional break affecting every new registration. It was false. The link was
  intact (1056 chars, `key` param 766 chars) and the `...` was my shell
  head/buffer cutting the string. Two failed submits then produced "expired" and
  reinforced the wrong story. **The check that settles it in one line:** read the
  link from a FILE (or `len(link)`, `"..." in link`) instead of from console
  output, and parse the query params — if `user_id` is present with a value, the
  template is fine. A real link also decays fast (Keycloak action tokens expired
  in <20 min), so "expired" proves nothing about the format either.
- **A `+`-alias rejected by the email validator is the real reason no mail
  arrives — not a broken template.** On Genians gov the form returned
  `Invalid : Email 형식이 올바르지 않습니다. 입력 가능한 특수문자는 하이픈(-)과
  쉼표(.)입니다` → only `-` and `.` allowed, so every `user+tag@gmail.com`
  attempt was refused *client-side* and registration was never submitted at all.
  Call the vendor's own validator directly to see the verdict instead of
  inferring it from a missing mail:
  `page.evaluate("\n  (em)=>{try{return gn_check_email_valid(em)}catch(e){return 'ERR:'+e.message}}", email)`
  — `''` means valid, anything else is the exact rejection text. Then use a
  Gmail **dot-variant** (`f.z.sus.anto@gmail.com`), which Gmail normalises to the
  same inbox while the target sees a distinct address.
- **Read the AJAX response, never the rendered page, when a signup silently does
  nothing.** Same engagement: the page looked unchanged after submit because a
  client-side gate returned before the POST. Calling the action directly showed
  the real sequence of blocking requirements —
  `{"result":false,"message":"Authenticator is required."}` then
  `{"result":false,"message":"개인정보보호 정책 동의 해주세요."}` — i.e. 2FA
  enrolment + explicit consent params were mandatory. The final accepted payload
  needed `authenticator=true&ga_secret=<b32>&ga_otp_code=<code>&agree_privacy=true&agree_email=true`,
  and the two consent params were invisible in the form (added by the button's JS
  handler). **Capture the real POST body** by hooking `page.on("request", ...)`
  during one genuine UI submit, then replay it in `page.evaluate(fetch(...))` with
  only the field you want to vary.
- **"Registration succeeded but login is refused" can simply be an approval
  queue.** Genians gov answered `?smcode=signin_pending` →
  *"관리자의 회원가입 승인 후 이용할 수 있습니다"* = manual admin approval, so the
  account exists yet no amount of retrying will authenticate it. Check the
  post-login redirect code before provisioning further accounts, and prefer a
  plane with self-service activation (the demo/staging Keycloak plane here:
  register → email verify → `CONFIGURE_TOTP` → `UPDATE_PASSWORD` → session, all
  automatable in one process).
- **The same TOTP seed often works on more than one door.** The seed enrolled for
  the account portal also satisfied the product console's OTP step (Step 3i), so
  decode once and reuse. Conversely, a *changed* error string after
  password-only submit ("Please enter your Authentication Code") is proof the
  credential is valid — do not report an OTP wall as "login blocked".
- **Credentials hygiene in the evidence dir.** After this class of work, delete the third-party SDK
  bundles you downloaded (a single `assets/index-*.js` was 2.5 MB of the IdP's code, not target evidence)
  and keep only a small extract of endpoints + header names. Never write the IdP's key material from
  `localStorage` (mpc key-share / recovery-secret blobs) to disk — it is the IdP's design, not a finding,
  and it is live key material; if a log captured a long base64 run, redact it
  (`re.sub(r'[A-Za-z0-9+/]{120,}={0,2}', '[REDACTED-BLOB]', text)`).
- **Do not rotate egress to "fix" a captcha.** A GeeTest slide rejected server-side
  (`ERR:服务端forbidden`, surfaced via the widget's `onError`) failed identically on a residential IP and on
  a fresh Cloudflare WARP IP — that is behavioural/attestation detection, not IP reputation. Rotating IPs,
  profiles or user-agents burns the operator's time and their phone's OTP attempts. Verify the gate's shape
  (two probes), then go to the human handoff.
- **If the HUMAN's own drag also fails, the browser is the problem, not the mouse.** A hand-solved slide
  inside a Playwright/CDP-driven window can be rejected for the same reason your synthetic one was. Switch
  the human step to a detached, un-instrumented `chrome.exe --remote-debugging-port=9222
  --user-data-dir=<fresh>` (never a profile the operator uses daily) and attach CDP only *after* the captcha
  is done. Then split the work: operator drags the slider and pastes the OTP into chat; **you** mint the
  session over REST (`POST /auth/phone/login {phone,code}` → `authToken`) instead of driving the browser
  form. One drag + one paste for them, everything else scripted.
- **Build PII identifiers (phone numbers, device ids) from char codes, not literals.** Tool-call arguments
  can mask them, so a plaintext `+62822…807` arrives at the target as `+628****807` and comes back as
  `InvalidPhoneNumber`. `PHONE = "+" + "".join(chr(c) for c in [54,50,56,…])`, and log only
  `PHONE[:4] + "****" + PHONE[-3:]`. This was already the reason an existing solver looked obfuscated —
  it is a harness constraint, not paranoia.
- **The same masking hits PASSWORDS and TOTP secrets written into generated source** — and it fails
  *silently in a confusing way*: a line like `PASSWORD = "<secret>"` can land on disk as
  `PASSWORD = ***`, and the script then dies with `SyntaxError: unterminated string literal` at a line
  that looks fine in your tool call. Hit twice on Genians (2026-10-27). Do not debug the syntax error —
  it is the masking. Keep credentials in a JSON file beside the session state and read them
  (`json.load(open("creds.json"))["secret"]`), or build from `chr()` codes. Never inline a real secret
  as a quoted literal in code you author or rewrite.
- **A `Not authorized` on a `…Registration…` mutation is a name trap, not evidence that signup is off.**
  Read the resolver's context type first: `GraphQLPublicContextAuth` + `user.id` = "add credential to my
  existing account". Drawn from the wrong conclusion, you report a missing feature instead of looking for
  the real signup route on the REST auth service.
- **A verified login is also a CONTROL test — record the negative with its histogram.** Once you hold a
  login id, an unbounded wrong-code loop on the same endpoint is the cheapest real protection check:
  `POST /auth/email/code {"email":<your own mailbox>}` → `{result:<loginId>}`, then N wrong codes and
  histogram the statuses. Measured on Blink (2026-10-12): first 5 attempts `401 {"error":"invalid code"}`,
  then **sticky `429 {"error":"too many requests"}` for the remaining 35** — limiter holds, so the honest
  output is a *negative with evidence*, not a finding. The discriminator that makes it a control and not a
  429-fluke: the limiter must persist across the rest of the run (ephemeral `429` after 1–2 hits is a
  rate-limit *observation* worth reporting as hardening at most). Save the row-per-request JSON as evidence.
- **Collaboration-service account APIs: the session token lives in a response HEADER, not the body.**
  Mattermost `POST /api/v4/users/login` returns the user object in the body and `Token: <session>` in the
  headers; a script that reads `json["token"]` silently gets `None` and "loses" a working session. Read
  `dict(resp.headers).get("Token")`. Same family of traps: the join call needs **both** `team_id` and
  `user_id` (`400 invalid_body_param` otherwise), and the verification secret comes out of the mail as
  `?token=<T>&email=<E>` → `POST /api/v4/users/email/verify {"token":"<T>"}`.
- **Raw CDP to a hand-launched Chrome 403s on the WebSocket upgrade until you pass `suppress_origin=True`.**
  Chrome rejects the default `Origin: http://127.0.0.1:9222` (`Handshake status 403 Forbidden … Rejected an
  incoming WebSocket connection from the http://127.0.0.1:9222 origin`) even though the browser is yours —
  `websocket.create_connection(ws_url, suppress_origin=True)`, or launch with `--remote-allow-origins=*`.
  Without this the un-instrumented-Chrome path looks broken and you fall back to Playwright, which is the
  thing that trips the captcha in the first place.
- **Read the operator's progress from `/json/list`, not from an attached session.** The HTTP endpoints
  (`/json/version`, `/json/list`) expose the live tab `url` with no CDP session, so polling them to see the
  human reach `/login/verification` cannot be detected. Attach CDP only to pre-fill the form (native value
  setter + `input`/`change` + click submit), assert the captcha widget rendered, then close the socket — the
  human then does exactly one drag in an un-instrumented window. Details in
  `references/attestation-gated-auth-surface.md` (raw-CDP section), alongside the pre-auth Hydra
  scope/credential-header matrix and the "OSS source = hypothesis generator, verify edge reachability
  before reporting" lesson (Telegram-passport webhook, 403 on every variant).
- **Risk-scored anti-abuse ESCALATES from challenge to silent drop after the first account (verified on
  Proton, 2026-10-21).** The first automated signup from a clean IP shows the captcha (user solves once →
  account created). Every subsequent signup attempt from the same IP — after account creation plus
  authenticated testing traffic — is **silently blocked**: no captcha iframe appears, no error renders, the
  React wizard just never submits (`POST .../users` never fires). This is NOT the captcha-gated bucket and
  NOT a disposable-domain block (those show a visible rejection like "Email domain not allowed"); the tell
  is the *absence* of any challenge or error. The block is IP-level, not host-level: the alternate signup
  path (`account.<vendor>.com` vs `account.<vendor>.com/signup`) fails identically. Recovery options, in
  order: (a) **manual handoff** — headed browser, the operator types the credentials themselves (trusted
  input + human interaction pattern passes what synthetic events do not; proven on Proton account #1);
  (b) wait for the rate window to reset (hours); (c) provision the second identity on a different surface
  entirely. Do not burn attempts re-running the same automation — each failed attempt deepens the flag.
- **Detect signup success by URL polling + a state file, never by "the click happened".** The React wizard
  advances asynchronously and its submit is flaky under synthetic input even when NOT blocked. Pattern that
  worked: drive the flow, then poll `pg.url` every 3 s for up to 8 min, write
  `{"user":…,"captcha":<bool>,"url":…}` to a state file the moment the flow starts and again on any URL
  change, and keep the headed window open for a manual finish. A `final_url` still on `/signup` after the
  poll window = blocked or failed, not "probably fine".
- **"No mail found" is usually a search-window problem, not a negative.** Fetching the N most
  recent messages misses vendor mail whenever the mailbox is busy (verification codes, other
  engagements). Search by sender instead — `MailBox.fetch(AND(from_="vendor.com"), reverse=True,
  limit=40)` — before concluding a flow did not send. A validation script that reports
  `successful trials: 0 of N` because of an 8-message window is a *false negative*: re-verify with a
  second method, and if a stale log survives on disk leave a `<log>_NOTE.txt` naming the artefact
  that supersedes it so the next session cannot quote it as a negative.
- **⛔ Never `ctx.clear_cookies()` on a persistent profile mid-engagement.** Clearing cookies logs the
  session out, and the `storage_state(path=...)` save that follows then **persists the logged-out state**,
  silently killing the session you were building (hit twice on Proton — once exploring the fork flow, once
  re-checking Calendar; each cost a full re-login). To force a fresh app-level session, delete only that
  app's cookies by domain, or use a separate profile — then re-verify login before saving state.

## Verification checklist
- [ ] Signup POST 200/201 and navigates to onboarding/dashboard
- [ ] Email code verified (left `/users/verify_email`)
- [ ] `GET /api/me` (or equivalent) returns 200 with the account
- [ ] At least one API key captured and round-tripped against the live API
- [ ] IDOR probe across adjacent IDs returns 404/401 (documented SOLID, not assumed)
