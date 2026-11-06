# Rapyd Bug Bounty Program (Bugcrowd) — working reference

Engagement: https://bugcrowd.com/engagements/rapyd · Public, safe harbor, scope rating 4/4.
Brief last updated 2026-06-17. Researcher handle used: `BC_USERNAME` / portal alias `RESEARCHER_BC_EMAIL`.

---

## Scope (verified from the Targets tables, 2026-09)

| Tier | Target | Notes |
|---|---|---|
| 3 (Premium) | api.rapyd.net | API Testing, NodeJS — **sandbox environment ONLY** |
| 2 | dashboard.rapyd.net, verify.rapyd.net, checkout.rapyd.net | Client Portal / KYC / Hosted Pages |
| 1 | `*.rapyd.net`, `*.korta.is`, jointhemoment.net, `*.rapyd.com`, `*.rapyd.org`, `*.kortathjonustan.is` | wildcards |

Out of scope targets: community.rapyd.net, support.rapyd.net, docs.rapyd.net, sandbox.rapyd.net,
ghost.rapyd.net, `3rd party services`, `*.neatcommerce.com`, `*.neattest.com`, `*.neat.com.hk`,
`*.neat.hk`, `*.neat.wtf`.

Out-of-scope vuln classes (read before writing anything up): DNS attacks (cache poisoning/flooding/
amplification/fast-flux/zone transfer/missing DNSSEC), UDP flood, DoS, social engineering
(phishing/vishing/smishing), **automated scanning against contact/submission forms**, clickjacking on
non-sensitive pages, CSRF on unauthenticated forms, MITM/physical-access, known-vulnerable libs
without a PoC, CSV injection without demonstrated impact, SSL/TLS best-practice misses, content
spoofing/text injection without an attack vector, **rate limiting/bruteforce on NON-auth endpoints**,
missing CSP / cookie-flag best practices, missing email best practices.

## Program rules (hard)

- **Every request must carry `X-Bugcrowd: Bugcrowd-<handle>`** (also sent `X-Bug-Bounty:` as belt-and-braces).
- Self-signup on dashboard.rapyd.net must use the Bugcrowd alias `[username]@BC_ALIAS.com`.
- **Production mode needs country = Iceland at signup**; otherwise the portal is sandbox mode
  ("all users are admins") and cross-user/role testing is limited.
- API testing: sandbox only. PCI findings min $500. Privacy findings (GDPR/CCPA) have their own track.
- "We enforce a rate limit on our entire Cloud environment… just skip this one" → **scale scanning down
  hard**. A full-template nuclei run over the live wildcard list planned ~1.27M requests; it was killed
  and replaced with a 22-host priority list at `-rl 4`. Cloudflare returned 429/1015 quickly during fast
  probes — keep request rates low and spread out.
- No automation against contact/submission forms. Only test accounts you own; stop and report if you
  reach non-public data/credentials.

## Top submitted classes (their words)

1. Input sanitization → **email template injection** (invites/notifications are the natural vector).
2. **Race conditions on critical business logic** (e.g. passing multiple refunds).
3. **Business logic that changes wallet balance with an incorrect amount**.

---

## SAML 2.0 in the Client Portal (the brief's promoted feature)

- SP details: ACS `https://dashboard.rapyd.net/v1/merchants-portal/users/login/sso/callback`,
  Entity ID `rapyd_merchants_portal`.
- Brief's vectors: assertion replay, XSW, InResponseTo enforcement, ATO via NameID/email spoofing,
  RelayState open redirect, XXE in the assertion, privilege escalation via attributes, tenant isolation.
- SAML out of scope: dummy/permissive IdPs (MockSAML), an admin attacking their own SSO config, and a
  known/still-tracked IDOR on `idp_id` (**do not submit**).
- **⛔ BLOCKER discovered 2026-09-29 — the portal refuses non-allow-listed IdPs.**
  SSO screen = Settings → Team members & Roles → SSO configuration (fields: Provider Name, Entry
  Point, Issuer, Certificate accepting `.pem,.crt,.cer`).
  - Keycloak on `https://localhost:8443` → Save stays **disabled**; submit → `Invalid parameters or
    file structure`.
  - Same Keycloak published over real HTTPS (cloudflared tunnel, correct issuer via
    `--hostname/--proxy-headers`) → Save enables, then:
    **"The Entry Point and Issuer URLs must belong to a trusted identity provider (Google, Microsoft,
    or Okta)."**
  - ⇒ For Rapyd, a self-hosted IdP is a dead end. You need **Okta / Microsoft Entra ID / Google
    Workspace** exactly as the brief says. Okta's Integrator Free Plan signup is **reCAPTCHA-gated**
    (the form has a required `recaptcha` field that blocks submit without a token) → this step needs a
    human click, so front-load it.
  - Prep that carries over: the Okta form values (`RESEARCHER_NAME` / `Susanto` / alias email / country / terms)
    can be filled programmatically, leaving only the captcha + "Sign up". Okta's domain check endpoint
    is `https://www.okta.com/free-trial/api/email-validation/?email_domain=<d>`.
  - Full lab mechanics + the pre-flight SP harness live in the `hunt-saml` skill:
    `references/self-hosted-idp-test-harness.md`.

## Getting an account (mechanics that actually worked)

1. Signup page is a React SPA at `/sign-up`; **Cloudflare Turnstile** gates it. A stealth-Firefox
   backend never rendered the widget (`window.turnstile` stayed undefined, button disabled forever).
   Real Chrome over CDP solved it automatically (token issued) — drive the real browser for auth flows.
2. Email verification: alias forwards to the registered Gmail. The mail is relayed by Bugcrowd
   (`forward-bot@BC_ALIAS.com`), and Rapyd's link is wrapped by Mandrill — pull the raw HTML,
   strip QP soft breaks (`=\r\n`, `=3D`), take the `mandrillapp.com/track/click/...` URL and
   base64-decode its `p=` payload to recover the real
   `https://dashboard.rapyd.net/branded-sign-up/<token>` link.
3. Phone step requires country + number (own number used). "Use authenticator app" is offered →
   **capture the TOTP secret** from `POST /v1/merchants-portal/users/change-mfa-type` with an
   in-page fetch/XHR hook instead of asking the user for the SMS code. Then generate codes locally —
   no further user involvement. (Persisting the hook needs `Page.addScriptToEvaluateOnNewDocument`
   so it survives SPA navigation/reloads.)
4. Re-submitting signup for the same email returns *"sign-up using this email will be available again
   in one hour"* — a 1-hour lock, not a hard block. Do not burn attempts; wait or use the TOTP path.

## Portal API surface worth testing (from the 8.8 MB entry bundle)

- `POST /v1/merchants-portal/users/change-mfa-type`, `/finish-registration`, `/edit/otp-code`
- `…/organization/api-keys`, `/api-keys/access-key`, `/rotate-with-verify`, `/rollback-with-verify`,
  `/send-sms`, `/organization/ip-whitelist`, `/organization/delete_organization_send_sms|verify_code`
- `…/users/set-organization`, `/users/active-organization`, `/users/edit/allowed-roles`,
  `/access-control/role/user`, `/list/users`, `/invites/users/verifications/activate-user`
- Korta (Iceland) integration inside the portal: `merchants-portal/korta/external/v1/…` — including
  `authorisationRequests/{id}/refund`, `merchants/{id}/acquiringContracts|terminals`,
  `reports/settlements/*`, `customers/autocomplete`, `icelandicPayments`, `outbatches`/`inbatches`.
  `…/{id}/refund` is the obvious IDOR/business-logic candidate once an account exists.
- `GET /config.json` is **public by design** (SPA config: public reCAPTCHA site keys, analytics IDs,
  feature flags, SFTP allow-list, testNumbers, `role_name`). No secrets — do **not** report it, even
  though nuclei's `config-json-exposure-fuzz` template flags it "critical".

## Adjacent surfaces found (all in-scope wildcards)

- **mcp.rapyd.org** — real MCP server + OAuth AS. Public `/.well-known/oauth-authorization-server`;
  `POST /register` (dynamic client registration) returns **201** for arbitrary `redirect_uris` and
  `token_endpoint_auth_method: none`; `POST /token` is internet-reachable (400 `invalid_grant`), while
  `GET /authorize` (any variation) 302s to `rapyd-global.cloudflareaccess.com` (Cloudflare Access).
  Open DCR + Access-gated authorize = **no proven impact** — keep as a lead, do not submit as-is.
  PKCE advertises `["plain","S256"]` and there is no `scopes_supported`.
- **finance-portal-qa.rapyd.org** (+ `api-finance-portal-qa.rapyd.org/api/v1`) — Vite SPA, Auth0;
  backoffice/GL endpoints enumerate from the bundle (`/backoffice/{merchants,tenants,wallets,
  transactions,banks,gw-accounts,reconciliations-table}`, `/bank-log-transactions/*`, `/clickhouse/query`,
  `/expanded-general-ledger`). Unauthenticated GETs all return **403 `RBAC: access denied`** (Envoy
  ext_authz) — control works; the endpoint map is the value for a future authenticated run.
- **ai-assessment.rapyd.org** — public SPA plus a **publicly served internal `README.md`** (2.4 KB,
  real markdown) describing: Cloudflare Pages Functions, KV whitelist + submission backups, BlinkOps
  webhook, `/api/start|submit|invite`, KV key schema, deployment/secret-env notes. Controls verified
  working: `/api/start` with a non-whitelisted email → `{"status":"not_invited"}`, `/api/invite`
  without token → 401, other repo files fall through to the SPA catch-all, `.env`/`.git/config` → 403.
  ⇒ honest severity **P4 info disclosure** (no candidate PII, no invite secret, no code).
- **Internal-tool hostnames** (jenkins*, argocd-k8s, grafana, security-kibana, rundeck, sentry, sensu,
  clearpass, *vpn, portal, pwm, forge, zoho, banklogs-prod.finance/finops, encryption) — enumerable via
  passive sources but **NO DNS ANSWER publicly** (verified with `dnsx`). Informational only; reporting
  bare subdomain names is noise. `discord.rapyd.com` leaked an internal EC2 hostname in the title
  (`ip-100-74-4-46.eu-west-2.compute.internal`) — LOW.
- Cloudflare Access (WARP)-gated, untestable without a Rapyd identity: attainment-dashboard,
  blink-discovery, `mcp.rapyd.org/authorize`.

## Live state (as of 2026-09-30)

- Account `RESEARCHER_BC_EMAIL` (Owner, sandbox, TOTP `VL37PYS56X35Z7JFQFDBCFY`). Its password was
  reset during testing — read the current value from `ENGAGEMENT_LOG.md`, never assume the old one.
- **Findings:** 001 (public internal README, P4) · **004** (HTML/link injection in the invite email — the
  escaping map shows only the invitee interpolation is missed, inviter + 3 other templates escape → P3
  requested) · 005 (Turnstile token replay on `/users/login`, P4/P5) · **008** (hosted checkout is
  frameable on production and its postMessage handler has no origin check, incl.
  `CHECKOUT_SUBMIT_PAYMENT`, P4) · 009 (verify.rapyd.net KYB link is a pure bearer credential: applicant
  email + entity token readable with just a `kyb_token` header).
- **Leads:** 003 internal hostnames · 007 valitor-calc-prod raw Node errors. **Closed:** 002 (mcp.rapyd.org
  DCR is now restricted — redirect_uri validated, PKCE S256 enforced, SAML-only login → not exploitable) ·
  006 (upgraded into 008).
- **Reports ready to submit:** `reports/RAPYD-2026-001|004|008_bugcrowd.md`.
- **Blockers:** real payment link needs onboarding (POST `/payment-link` and `/checkout-payment` →
  `ERROR_GENERATE_HOSTED_CATEGORY_NOT_SUPPORTED`), so the 008 visual PoC needs the program to enable
  sandbox payment categories — do **not** fabricate KYC data. SAML vectors still need an Okta/Entra tenant
  (one human captcha click). api.rapyd.net keys are valid but the account is not API-enabled (401 on every
  signed request) so signature matrices stay meaningless until KYB.
- **Techniques that mattered:** demo checkout tokens come unauthenticated from
  `GET sandboxapi.rapyd.net/v1/hosted/config/preview_tokens?type=checkout`, and the checkout UI path is
  `/hosted/preview?token=…` (`/hosted/checkout` 404s on the sandbox host). Read a cross-origin framing page
  by attaching to the OOPIF target from `/json/list` (type `iframe`) over CDP; `Page.captureScreenshot`
  hangs on that heavy page — skip `Page.enable` and don't rely on screenshots there.
- Full log + evidence: `D:/data hermes/bug-bounty/_progress/rapyd-2026-09-29/` (`ENGAGEMENT_LOG.md`,
  `findings.json`, `reports/`, `evidence/`, `checkout/`, `mcp2/`, `scans/`).
- Still open: Okta/Entra tenant for the 8 SAML vectors; portal BOLA/IDOR + Korta refund; wallet/refund
  business logic (needs KYB); role matrix for Editor/Admin (needs a second phone number).

## Operational playbook — portal automation (learned 2026-09-29, saves hours)

**Second account WITHOUT SMS — use the invite flow, not signup.**
Owner invites a member (`RESEARCHER_USERNAME+tag@gmail.com` — Gmail plus-addressing works, mail lands in the
same inbox) → open the invite link (`dashboard.rapyd.net/invite/<128 hex>`) → set password → the
set-phone step fires an SMS, but the "Use authenticator app" option on the same screen returns the
TOTP secret in `POST /users/login/generate-authenticator-app-uri` (`data.config_uri`, `secret=…`).
In practice the invited user's session came up already authenticated. Note: the invitee name is a
*separate* invite body field — `POST /v1/merchants-portal/users/user
{invitedUsersList:[{email,role,full_name}], recaptcha_token}`; role aliases: `basic`=Viewer,
`editor`, `admin`, `owner`, plus Compliance Admin.
The phone number of an existing account cannot be reused (silent `INVALID_PHONE` in
`localStorage.error_requests`).

**Login (2026-09 layout).** `/login` is a SINGLE page: email + password + Turnstile together (the old
"Continue with email" two-step is gone). Turnstile token field on the wire is **`recaptcha_token`**
(not `cf-turnstile-response`); the app also sends a `fingerprint` header (32 hex, `localStorage.fp`).
Session auth = `token` header from `localStorage.token` — cookies alone give
`MERCHANTS_PORTAL_INVALID_SESSION`. Password login helper: `rapyd_login_pw.py`
(fill email with `Input.insertText` — real key events drop the "." — and the password with key events
or `insertText`; then poll for the 768-char Turnstile token before clicking).

**react-select dropdowns (country, role, tables) via CDP.** Mouse clicks and `Input.insertText` do
NOT filter the list and opening state is lost between CDP connections — do everything in ONE process.
Reliable recipe: focus the `input[role=combobox]` (tag it with a data attribute), then dispatch
JS `KeyboardEvent` keydown/keyup (`ArrowDown`, keyCode 40 / `Enter`, 13) on it, and read progress
from the react-select `aria-live` region ("option ID +62 focused, 100 of 247") or, for short lists,
`[class*=dropdown__option]`. Scripts: `rapyd_country_pick.py`, `rapyd_invite.py`.
Capture the API call itself with `Network.enable` + `Network.requestWillBeSent` (a fetch/XHR JS hook
misses Next.js/axios calls in this app).

**RBAC ground truth (Viewer vs Owner, sandbox).** Viewer is blocked (400
`MERCHANTS_PORTAL_UNAUTHORIZED_ACTION`) on: `POST /users/update/{email} {role}` (self-escalation),
`DELETE /users/user`, `GET /organization/api-keys` (the key PAIR), sso-config, ip-whitelist,
reports-settings, allowed_user_domains, partners/settings, valitor claims. Viewer CAN read
`GET /organization/api-keys/access-key` (access key only — useless without the secret; INFO not a
finding), `POST /list/users`, `GET /access-control/role/user/{role_name}`, webhooks/notifications
settings. So portal writes are properly gated; don't burn time expecting easy escalation there.

**Turnstile token is replayable** on the same endpoint (same token accepted 3×; garbage/no token
still rejected; cross-endpoint reuse fails). An IP/device lockout (`MERCHANTS_PORTAL_ERROR_MAX_LOGIN_ATTEMPTS`)
also exists — report honestly as P4/P5, not as a full captcha bypass, and don't hammer the login form
(program rule: automating form submissions = ban).

**Sandbox API (`sandboxapi.rapyd.net`) is NOT usable from a fresh org**: every correctly-signed
`GET /v1/data/countries` returns `401 UNAUTHENTICATED_API_CALL` ("check the status of your account in
Account Details") while the portal still shows the "Don't forget to verify your account" banner →
account onboarding/KYB is incomplete, so API access is off. Signature matrices are meaningless
without a 200 control request. To unlock the API-reward category, the user must finish onboarding
(honest business data — do not fabricate). Signature itself (HMAC-SHA256 over
`method.lower()+path+salt+timestamp+access_key+secret_key+body`, hex) rejected bad sig, stale/future
timestamp, unsigned/tampered body, method confusion and unknown access key — consistent with a
consistent with a correct implementation once a control exists.

## Live state update — 2026-09-30 (later sessions)

- **Credential change:** the owner password is no longer `Bugcrowd-BC_USERNAME-2026!` — a "forgot password"
  request invalidated it. The new password is in `_progress/rapyd-2026-09-29/ENGAGEMENT_LOG.md` (TOTP
  secret unchanged). Do not fire reset flows on this account; see `browser-cdp-auth-audit` for why.
- **mcp.rapyd.org (old LEAD-2026-002) — CLOSED, not exploitable.** The host moved to Cloudflare
  Access-managed OAuth (`rapyd-global.cloudflareaccess.com/cdn-cgi/access/oauth/*`); `/register` on the
  MCP host is now a Cloudflare 404, DCR accepts **loopback redirect URIs only**, `/authorize` validates
  redirect_uri, PKCE S256 is mandatory, `resource=` is required, forged JWTs are rejected and the login
  page offers **SAML only**. Full control matrix + client-cleanup note: `web2-vuln-classes` →
  `references/cloudflare-access-oauth-mcp.md`. Four test clients were registered and cannot be deleted by
  us (create-only DCR) — listed in the engagement log for Rapyd's admin to purge.
- **RAPYD-2026-008 (hosted checkout — frameable + postMessage with no origin check).**
  `checkout.rapyd.net` and `hosted.rapyd.net` return 200 with **no** `X-Frame-Options` /
  `frame-ancestors` (an earlier SAMEORIGIN sighting was the Cloudflare 429 rate-limit page). The checkout
  bundle's receive handler applies `hideOrderDetails`, `hideSubmitButton`, `btnText`, `customStyles` and
  `CHECKOUT_SUBMIT_PAYMENT` with no `event.origin` check, and posts to its parent with `"*"`. Demo tokens
  are handed out unauthenticated by
  `GET https://sandboxapi.rapyd.net/v1/hosted/config/preview_tokens?type=checkout`; the preview URL is
  `/hosted/preview?token=…` (`/hosted/checkout` 404s on the sandbox host). Filed P4 with an explicit
  verification-status section — no visual PoC on a funded page.
- **RAPYD-2026-009 (KYB hosted link is a bearer credential).** `/onboarding` embeds
  `verify.rapyd.net/verify?token=happ_<32hex>&otk=<121>`; the SPA sends that token as a `kyb_token:`
  header, so `curl -H "kyb_token: happ_…" /v1/verify/applications/hosted/happ_…` returns 200 with the
  owner's email + `rapyd_entity_token` from a cookieless client. The bundle also exposes save/submit/
  document writes and an SMS-OTP resend on the same credential. P4/P5, honest framing (do not fire the OTP).
- **KYB blocker for payment-link creation:** `POST /v1/merchants-portal/payment-link` and
  `/checkout-payment` → `400 MERCHANTS_PORTAL_ERROR_GENERATE_HOSTED_CATEGORY_NOT_SUPPORTED`, and the
  `/collect/create-payment-link` payment-method checkboxes are rendered `disabled`. Do **not** invent
  business/identity data to get past KYB (see `browser-cdp-auth-audit`); ask the program to enable the
  sandbox capability, or complete a full visual PoC only with the operator's real entity data.
- **Nuclei sizing for this program:** `-tags exposure,disclosure,takeover,default-login,misconfig` over
  260 hosts advertises ~1.5M requests (0% progress after 32 min) — too heavy. Use a bounded sweep
  (260 hosts × ~14 paths @ ~4 rps ≈ 9 min) plus nuclei with narrow tags on ~45 hosts; both produced 0 new
  findings, which is itself the useful result (that class is exhausted except
  `ai-assessment.rapyd.org/README.md`).

## Live state update — 2026-09-30 (supersedes parts of the 2026-09-29 notes above)

**mcp.rapyd.org OAuth lead is CLOSED — do not submit.** The MCP server now sits behind Cloudflare Access
OAuth (issuer `rapyd-global.cloudflareaccess.com`); `/mcp`, `/sse`, `/authorize` return
`401 invalid_token` + `resource_metadata` (RFC 9728). DCR at `…/cdn-cgi/access/oauth/registration` accepts
**loopback redirect URIs only** (`http://localhost:3334/callback` → 201; public hosts, wildcards and
`javascript:` → `400 invalid_client_metadata "redirect_uri is not allowed by the account configuration"`).
`/authorize` validates the redirect against the registration, requires `resource=`, and requires PKCE
S256; the login page offers **SAML only** (no OTP/social), so an outsider cannot mint an Access JWT, and
forged JWTs (random / `alg=none` / HS256) are all rejected. Hygiene: DCR is create-only — the response
carries no `registration_access_token` and there is no manage/delete endpoint, so test clients you
register stay in their tenant; list them in the log for the vendor.

## Portal operational lessons (saves hours next session)

- Login page is a single form (email + password + Turnstile). The wire field is **`recaptcha_token`**, the
  app also sends a `fingerprint` header, and session auth needs the `token` header from `localStorage`
  (cookies alone → `MERCHANTS_PORTAL_INVALID_SESSION`). **One page load = one usable Turnstile token**:
  reload (`Network.setCacheDisabled` + reload) before each attempt and POST once — a retry on the same
  page load fails with `ERROR_CLOUDFLARE_CAPTCHA_VALIDATION_FAILED` even with a freshly-read token. Most
  reliable login path: read the widget token from the page and POST `/v1/merchants-portal/users/login`
  yourself; the response carries `token`, `is_otp_verified`, `is_first_login`, `user_organization_id`.
- **A password-reset request immediately invalidates the current password** (login then returns
  `MERCHANTS_PORTAL_ERROR_LOGIN` until the reset link is used), while **existing sessions stay valid**.
  Never fire a reset on an account you are actively using. Recovery: read the reset mail over IMAP (it
  arrives via `forward-bot@BC_ALIAS.com`), decode the Mandrill link, open
  `/change-password/<token>`, set a new password. Reset mails are throttled — request once and wait.
- **An invited member cannot use the portal API before finishing MFA**: login returns
  `is_otp_verified:false` / `is_first_login:true` and every protected endpoint answers
  `MERCHANTS_PORTAL_INVALID_SESSION`. A full Editor/Admin role matrix therefore needs a **second phone
  number** for the first-login step (the owner's number is taken → silent `INVALID_PHONE`).
- Role boundary already confirmed: a Viewer is blocked (400 `MERCHANTS_PORTAL_UNAUTHORIZED_ACTION`) on
  `POST /users/update/{email} {role}`, `DELETE /users/user`, `GET /organization/api-keys` (the key+secret
  pair), sso-config, ip-whitelist, reports-settings, allowed_user_domains, partners/settings; it may read
  `/organization/api-keys/access-key` (access key only, useless alone), `POST /list/users`, and role
  definitions. Don't burn time expecting easy escalation there.
- **Payment-link creation is blocked by onboarding state**: `POST /v1/merchants-portal/payment-link` and
  `POST /checkout-payment` → 400 `MERCHANTS_PORTAL_ERROR_GENERATE_HOSTED_CATEGORY_NOT_SUPPORTED`; on
  `/collect/create-payment-link` the payment-method checkboxes are rendered `disabled`, so "Create Link"
  never enables. `GET /checkout-config` is 200 but not sufficient. Consequence: no real checkout token →
  signed sandbox-API calls stay 401 and the postMessage PoC cannot be finished on a funded page (see
  `references/postmessage-iframe-channel-testing.md`).
- **Unauthenticated demo checkout tokens**: `GET https://sandboxapi.rapyd.net/v1/hosted/config/preview_tokens?type=checkout`
  → 200 with `data[].token` (one flagged `is_demo`) while every other call on that host is 401;
  production `api.rapyd.net/v1/...` returns an empty list. Usable as a PoC enabler, reportable as a
  Low/Info auth inconsistency. The preview page renders at `/hosted/preview?token=…`
  (`/hosted/checkout` 404s on the sandbox host) and stays idle without a real payment context.
- Portal react-selects: when the option list is **not** virtualized, options are plain
  `[class*=dropdown__option]` elements — open the menu and click the matching option directly (that's the
  long country list on `/collect/create-payment-link`). For virtualized lists only ~7 rows exist in the
  DOM, so use JS-dispatched `KeyboardEvent` (ArrowDown/Enter) + the `aria-live` region for feedback, all
  inside ONE CDP process (the menu closes when the connection drops).
- CDP practicalities: pages with heavy cross-origin iframes can stall `Page.captureScreenshot` — attach to
  the OOPIF target (`type:"iframe"` in `/json/list`, own `webSocketDebuggerUrl`) and read the DOM instead,
  or fall back to `PIL.ImageGrab`. Keep one Chrome profile per identity
  (`C:\temp\rapyd-chrome-profile`, `…-viewer`, `…-harness`) so two accounts can be live simultaneously.

## Sesi 9 addendum — results already obtained (do not redo)

**Concluded finding: invitation email HTML/link injection (class #1 for this program).**
Escaping map on the same stored payload — invitee name RAW in the invitation email; **inviter name
and three other templates escaped** ("User Password Changed", "Forgot Password", "Did you attempt to
login…"). Delivery verified `dkim=pass header.i=@rapyd.net` + `spf=pass` (Mandrill). Resend
(`POST /users/invitation {mpu_email}`) re-renders the stored payload. Negatives already tested and
documented: CRLF/header injection (invite form collapses CRLF), stored XSS in the member list (escaped),
role-change/member-removal notifications (**no email is sent at all**). Method:
`security/email-template-injection`.

**Operational trap — reset = self-lockout.** Requesting "forgot password" for the account you are
working in immediately invalidates its password (logins then return `…ERROR_LOGIN` / "Email or password
are incorrect") while **live sessions keep working**. If you must test the reset template: rename →
request reset → use the link immediately → revert the name. Reset/invite mail is throttled, so a second
request can send nothing and expire the previous link. Current owner credentials live in
`_progress/rapyd-2026-09-29/ENGAGEMENT_LOG.md` (they changed during testing — read the log, not memory).

**Captcha rule:** one page load = one usable Turnstile token; the invite form's reCAPTCHA token is
obtained internally (reading `grecaptcha.getResponse()` / the hidden textarea comes back empty) →
capture the app's own request with CDP `Network.enable` + `Network.requestWillBeSent`, or drive the UI.

**Hosts already swept (all auth-gated or dead — record, don't re-probe):**
- `serviceportal.rapyd.net` — full internal API mapped from its bundle (`/api/requests`, `/api/admin/stats`,
  `/api/servicedesks`, `/api/assistant/chat/stream`, `/api/auth/*`) + Atlassian OAuth client id; **every
  endpoint 401**.
- `api.rapyd-app.rapyd.net` — `/health` public `{"ok":true}`; bundle paths (`/api/user/me`,
  `/api/management/users`) → **401**.
- `api-finance-portal-qa.rapyd.org/api/v1*` → **403** at the edge (Envoy).
- `sandboxbo-preview.rapyd.net` — `/api/*` **503**; `/swagger.json`, `/actuator/health` = SPA catch-all.
- `korta.is` — only `netgreidslur.korta.is` live → 302 to `checkout.rapyd.net/500?op_id=<uuid>`.
- `valitor-calc-prod.rapyd.net` — exposed internal calc service, **always 500** with raw Node errors;
  body `null` leaks the field name `number_payments`. P5/informational → lead only.
- `automation-wh-prod.rapyd.net` — GET returns `{"status":{"status":"SUCCESS"}}` to anyone (no data).
- `gw.rapyd.net` / `globalgw` / `gw1` / `pos.rapyd.net` → 401 Envoy gateways (need API keys — blocked
  anyway by the sandbox-account API gate).

**Still untouched / blocked:** mcp.rapyd.org OAuth DCR chain (authorize behind Cloudflare Access),
the 8 SAML vectors (need an Okta/Entra/Google tenant), cross-tenant BOLA (needs a second organisation —
`POST /users/new-account` demands a Google reCAPTCHA token), race/wallet business logic (needs KYB).
