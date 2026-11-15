# M365 / Teams-app SaaS vendor — unauth surface playbook (Witivio worked example)

Target class: a company that sells Microsoft Teams apps + an "AI agent in Teams" SaaS.
Estate shape (all Azure App Service, ASP.NET Core/Kestrel):

- `admin.<product>.com`      AdminCenter — custom licence/subscription management (SSO via login.microsoftonline.com)
- `admin.<otherproduct>.com` the second product's admin (Entra SSO, OIDC redirect to a signed `signin-oidc`)
- N app subdomains           one React SPA each, embedded in Teams (`<title>App</title>` shell, `/static/js/main.<hash>.js`)
- `graph.<product>.com`      Azure-Function-style proxy (JSON `{"statusCode":404,"message":"Resource not found"}`)

## What to do, in order

### 1. `GET /api/settings` on every app host (unauth, one request each)

Witivio returned per app:

```json
{
  "apiVersion": "v1",
  "clientId": "b2380441-bb33-439e-bf4a-8cd277dcebc8",
  "graphScopes": "email offline_access openid profile User.Read Files.ReadWrite.All Sites.ReadWrite.All",
  "appInsightConnectionString": "InstrumentationKey=...;IngestionEndpoint=...;LiveEndpoint=...;ApplicationId=...",
  "manifestId": "dc00c22b-b7ad-4db8-bf35-c2660104d622",
  "adminCenterBaseUrl": "https://admin.teams-pro.com",
  "adminCenterAppId": "25b0b774-47b8-4a91-abbc-e0398b7b37a9",
  "apiSubscription": "https://subscriptions.witivio.com",
  "trackingBaseUrl": "https://teamspro-tracking-integration.azurewebsites.net",
  "appSourceOfferId": "witivio.keepass-pro"
}
```

Read the fields as an attack map:
- `graphScopes` — the privilege ceiling of that app in the victim's tenant. `Files.ReadWrite.All Sites.ReadWrite.All` on the KeePass/password-vault app means a BOLA there = read/write of another tenant's vault = Critical. This is the ranking key for which app to spend authenticated effort on if an account ever appears.
- `clientId` / `manifestId` / `adminCenterAppId` — Azure AD app ids and the product id, all public-by-design but needed to construct probes.
- `trackingBaseUrl`, `appInsightConnectionString` — internal host name + telemetry identifiers. Info-disclosure at most; the hostname is recon intel.
- `googleMapApiKey` often appears but is public-by-design (client-side, referrer-restricted). Not a finding.

### 2. CSP `frame-ancestors` = the full subdomain + backing-App-Service inventory

`curl -D - https://admin.<product>.com/` → read the `Content-Security-Policy: frame-ancestors 'self' https://teams.microsoft.com ... <app1>.<product>.com <app2>... <tp-app1-prd-preprod.azurewebsites.net> ...`.

This one header hands you (a) every app subdomain, (b) the Azure Web App backing names (`tp-<app>-prd-preprod.azurewebsites.net`). Passive/CT enum finds none of these — they share one App Service IP on a wildcard cert and never request their own cert. `connect-src`/`frame-ancestors`/`form-action` on the admin login page beats subfinder here.

### 3. The entitlement endpoint — the auth-split oracle (this is the finding shape)

`POST https://admin.<product>.com/teams-app/data` with `Content-Type: application/x-www-form-urlencoded` and body `tenantId=<tid>&userId=<uid>&appId=<adminCenterAppId>` returns 200 with NO auth:

```json
{"isUserStarter":false,"isUserPremium":false,"isUserPlatinum":false,"isUserAdmin":false,
 "isAccessRequestPending":false,"isTenantLicenceAvailable":false,"subscriptionLicenceId":null,
 "productName":"Contacts Pro","admins":[],"subscriptionCardExpiring":false,"paymentDue":false,
 "subscriptionOwner":null,"isAppLicenceAvailable":false,"tenantSuperAdmins":[],"subscriptionId":null}
```

Prove it is a *defect* and not "public by design" in one line — the siblings enforce auth while this one does not:

| endpoint | unauth result |
|---|---|
| `POST /teams-app/data` | **200** full entitlement JSON |
| `POST /teams-app/users/licences` | `authentication_required` (plain-text) |
| `POST /teams-app/access-request` | 401 `authentication_required` |

The one open endpoint in a family whose siblings are gated is the control gap. Report it as Broken Access Control / BOLA (Medium). The honest impact: unauthenticated disclosure of tenant subscription state + administrator/subscription-owner object IDs keyed on an attacker-chosen tenantId, where the tenantId is discoverable from the victim's domain via OIDC realm discovery (`login.microsoftonline.com/<domain>/.well-known/openid-configuration`). Do NOT overclaim to Critical unless you are willing to demonstrate a real customer tenant's populated `admins`/`subscriptionOwner` — and if you decide to do that, you are now handling a third party's PII, which the data-handling clause of most policies forbids. The schema + the auth-split is sufficient and safe.

`appId → productName` is a free DB-lookup oracle that proves the endpoint is a real server-side lookup, not a canned response: submitting the same `tenantId`/`userId` with `appId 008f10ab…` → "Contacts Pro", `2affb476…` → "Calendar Pro", `25b0b774…` → "Keepass Pro".

### 4. `graphtoken?scopesStr=` — the scope-escalation lead (Bearer-gated)

`GET /api/v1/graphtoken?scopesStr=<scopes>` (via the app's own axios client with the Teams SSO token) returns a Microsoft Graph access token for the *requested* scope. If the backend mints any scope verbatim instead of intersecting with the app's registered `graphScopes`, an authenticated free user can obtain `Mail.Read` / `Files.ReadWrite.All` they never consented to. Unauth it 401s (`WWW-Authenticate: Bearer`) — record as a lead requiring an account, and note it in the report as "authenticated follow-up".

### 5. jsluice for the bundle endpoint table (don't hand-grep a 4 MB minified bundle)

```bash
jsluice urls main.<hash>.js 2>/dev/null | sort -u
# -> {"url":"/graphtoken?scopesStr=EXPR","queryParams":["scopesStr"],...,"method":"","type":"fq.instance.get"}
# -> {"url":"/teams-app/data",...,"type":"stringLiteral"}
# -> {"url":"/feedback",...,"type":"fq.instance.post"}
jsluice secrets main.<hash>.js 2>/dev/null
```

`type` tells you which client (`sq.get` = settings service, `fq.instance.post` = the auth-carrying axios, `fetch` = raw no-auth) — the same classifier the hand-rolled `bundle_apimap.py` gives, plus body/query params, and it runs offline in one command. Note: no `--version` flag on this build; the `urls`/`secrets` subcommands are the interface.

## What did NOT pay / traps hit on Witivio

- `graph.<product>.com` — Azure-Function JSON 404 on every path (`/v1.0/me`, `/me`, `/health`, `/swagger`...). Legacy proxy with no reachable handler; don't burn probes.
- `apiSubscription` host (`subscriptions.witivio.com`) just 302s to the apex — no surface.
- The SPA routes `/api/shared/v1/tabs`, `/api/campaigns/user/`, `/api/directline/token` all fall through to the SPA shell (200 text/html `<!doctype html>`) — those are CLIENT-side routes, not server endpoints. Do not read a 200 shell as "endpoint exists"; the app's real server API is `/api/v1/*` and answers `401 WWW-Authenticate: Bearer`.
- MSAL/IDWeb OIDC flow (signed `state`, `nonce`, PKCE `S256`, `form_post`) on both admin hosts — standard, no open redirect via `redirectUrl` (the server normalised external values back to `/`, storing them in a cookie rather than redirecting to them).
- Non-resolving subdomains from subfinder (`app.`, `api.`, `app-dev.`, `botmeta.`, `webchat.`, `milo.` …) = internal-only hosts. Internal hostname disclosure at most.
- Account creation: signup is `POST /licence/create-user` behind "Continue with Microsoft" SSO — requires a Microsoft 365 **work/school (Azure AD)** account. A **personal** Microsoft account (outlook.com/hotmail.com) is rejected even though the OAuth URL reads `/common`: after email+password you get *"You can't sign in here with a personal account. Use your work or school account instead."* (the app's `signInAudience` is work-only). That error string is a fingerprint for the whole target class — read it and pivot, don't fight it.
- **The work-account self-provision bridge is the Microsoft 365 Developer Program**, not a direct signup. Path: personal MSA → `developer.microsoft.com/microsoft-365/dev-program` (accepts personal accounts) → `Join now` (href resolves to `/microsoft-365/profile`) → sign in → instant sandbox = free renewable E5 tenant, which hands you a work account `admin@<yourdomain>.onmicrosoft.com`. Use THAT to sign into the work-gated product. Note: joining fires a device-trust challenge — *"Verify your email — We'll send a code to <recovery-email>"*. That is actually the cheapest credential channel when the recovery email is one you control (read the code via Gmail API / IMAP rather than hand-typing); the fallback link *"Use your password"* skips the email round-trip.
- **Microsoft sign-in automation pitfalls (login.live.com / login.microsoftonline.com flows):** (1) on the live.com password page the field is `input[name=passwd]` and it submits with `Enter` — `#idSIButton9` is only reliable on the login.onmicrosoft.com pages; (2) prefer "Use your password" over the email-code path when you cannot read the recovery inbox; (3) repeated headless attempts from a datacenter/IP flagged IP trip a TEMPORARY account lock — *"You've used an incorrect account or password too many times"* — it clears in ~15-30 min and does NOT mean the password is wrong (confirm the password worked once on a prior step before concluding it is invalid). Slow the loop down: one attempt → read the response → decide, instead of re-submitting in a loop.

## Report framing

- One vuln per email, English, to the policy's contact (here `dpo@witivio.com`, discretionary reward capped €500).
- Lead with the auth-split (open `/teams-app/data` vs gated siblings) — it is the sentence that defeats "public by design".
- State the data-handling discipline explicitly: "created no data, enumerated/exfiltrated no real tenant data, stopped once the control gap was proven".