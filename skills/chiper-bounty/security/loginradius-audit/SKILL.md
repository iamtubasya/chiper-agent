---
name: loginradius-audit
description: "LoginRadius (loginradius.com) bug bounty — scope, API map, auth model, account provisioning, and validated findings. Use when auditing loginradius.com or any *.loginradius.com asset."
metadata:
  hermes:
    tags: [bug-bounty, security, ciam, saas, loginradius, api, idor, multi-tenant]
---

# LoginRadius Bug Bounty — engagement

CIAM (Customer Identity & Access Management) SaaS. Customers (enterprises) create a tenant in
the admin console, then provision their end-users on `api.loginradius.com`. Money = subscription
+ MAU. **Highest-value bug class = cross-tenant BOLA/IDOR on api.loginradius.com** (accessing
another tenant's user data = "significant number of users at risk" per their rewards line).

## Scope & rules (verified 2026-11; bug-bounty page soft-404s, use Oct-2026 archive)
- IN SCOPE: `*.loginradius.com`, `adminconsole.loginradius.com`, `api.loginradius.com`
- Report to: `security@loginradius.com` (email ONLY — no form, no other channels)
- Min reward $50 USD; InfoSec discretion, significantly more for serious issues
- OOS: DoS, Spamming, **Automated Scan Report** (raw scanner dump ineligible; manual PoC required),
  social engineering, deprecated browsers, physical, fingerprinting/banner disclosure, weak/no
  captcha / captcha bypass, missing security headers
- Must include clear PoC steps; no disclosure without written permission; interact only with
  accounts you own; expected response ~5 business days

## Core assets (map)
- `api.loginradius.com` — CIAM identity API (`/identity/v2/auth/*`, `/identity/v2/manage/*`).
  Root returns a JSON descriptor `{Name, Website, Documents, Status}`.
- `adminconsole-api.loginradius.com` — admin-console BACKEND. NOT in subfinder; discovered by
  mining `console.loginradius.com` JS bundles. Probed 405 endpoints; only `/auth/config` and
  `/auth/checksaml` answer WITHOUT an auth token (see finding below).
- `console.loginradius.com` (+ `adminconsole.loginradius.com` 301→it) — admin console SPA (Cloudflare Bot Management + challenge).
- `accounts.loginradius.com` — LoginRadius's own IdP for the console (OIDC authorize). App name
  "lr", public apiKey `83952b6c-61de-43fd-93bf-b88d90c76489`, OIDC client_id
  `d07669fe-a006-4e2b-9a01-526504e3d282`.
- `authdebug.loginradius.com` — client-side auth playground/debugger (Next.js); routes
  `/flows/*`, `/tools/*`; calls `api.loginradius.com` directly from browser (no SSRF backend).
- `*.hub.loginradius.com` (`hub`, `lr`, `passwordless`, `postmedia`, `dairyfarm`,
  `internal-*.hub`) — hosted login/registration pages; `internal-<name>.hub` are per-CS demo tenants.
- RAAS hosted pages expose `raasoption.apiKey` + `raasoption.sott` (Secure One-Time Token,
  base64-binary + `*<32-hex>`, encrypted/time-limited) + `registrationFormSchema` inline in the
  HTML — this is **BY-DESIGN** for the RAAS flow (server mints the SOTT for client-side
  registration; it is NOT the apiSecret and is scoped/time-limited). Do not re-raise as a finding.
  It does leak the customer's real apiKey (UUID, e.g. postmedia = `1a9a7ccf-c3f1-4ec9-a65f-2c3e8d9510a5`)
  and custom-field schema (`zephr_id` etc.), which is info-level recon only.

## Auth model (api.loginradius.com)
- Header: `X-LoginRadius-ApiKey` + `X-LoginRadius-ApiSecret`, or query `?apiKey=&apiSecret=`
- M2M Bearer (client-credentials) recommended for management APIs
- Secret is STRICTLY validated server-side: empty → `ErrorCode 923 "API secret is missing"`,
  wrong → `ErrorCode 921 "API secret is invalid"`. No secret-less manage access.
- Public/registration endpoints use only `?apiKey=` (secret not needed for client auth flows),
  gated by reCAPTCHA (site key `6LciWZ4UAAAAAN2KlBER1up2gR3d3SSsFsE6blYx`).

## Account provisioning (free trial via console) — pitfalls
- Flow: `console.loginradius.com/login?action=register` → OIDC to accounts.loginradius.com →
  register → email OTP → appName (tenant). "21 days free trial, no credit card".
- **Email is domain-gated**: gmail → `ErrorCode 1056 "Email is not allowed to register"`;
  `+` sign → client-side reject; a business-looking disposable (`@fldubai.com` via mail.tm) works.
- OTP is 6 separate inputs `#loginradius-otp1..6` (not one field). `EmailVerificationFlow:
  required`. OTP expires in 20 min; the verify link (SendGrid `url5757.loginradius.co` tracking)
  expires/redirects to `www.loginradius.com` once consumed.
- Rate limit: `ErrorCode 1122 "You have reached a limit for sending emails"` after ~5 OTP sends;
  blocks login of unverified accounts (login re-triggers verify email). Wait for reset.
- reCAPTCHA is invisible (`size=invisible`), site key `6LciWZ4UAAAAAN2KlBER1up2gR3d3SSsFsE6blYx`.
  After repeated Playwright automation it enters CHALLENGE mode: `g-recaptcha-response` (hidden
  textarea) stays empty, so "Continue" silently does nothing. Diagnostic = read `#g-recaptcha-response`
  value; empty means bot-challenged, no token. Persistent Chrome profile does NOT reliably clear it —
  this is a hard wall for automated account creation; stop after ~5 failures and pivot to unauth surface.
- Login API: `POST /identity/v2/auth/login?apiKey=...&loginUrl=&verificationUrl=...` — note the
  console passes an EMPTY `loginUrl` (`loginUrl=&&`).

## Validated finding (3x) — unauthenticated SAML tenant enumeration
`GET https://adminconsole-api.loginradius.com/auth/checksaml?sitename=saml_{slug}` returns
`{"isFound":true|false}` with only two client-controlled headers — no token/cookie:

```
Origin: https://console.loginradius.com
X-Is-LoginRadius-Ajax: true
```

Without those headers the server returns `{"ErrorCode":500,"Message":"Not allowed by CORS"}` in
the body (not a browser-enforced CORS block — a spoofable server-side gate). Verified true:
`saml_postmedia`, `saml_ultabeauty`, `saml_northumbrianwater` (real customers); false for
`saml_dairyfarm` / random slugs. Severity: Medium (info-disclosure / weak access control).
Escalation dead-ends: `/auth/config` always returns the console's OWN "lr" config (ignores
tenant params); all other probed endpoints return 401. Full report + PoC:
`finding_checksaml_saml_enumeration.txt`.

## Generalizable technique (not LoginRadius-specific)
"Not allowed by CORS" returned in a JSON BODY (HTTP 200) is a **server-side Origin-header
allowlist**, not a hardening layer — Origin and companion headers like `X-Is-LoginRadius-Ajax`
are client-controlled and trivially set in curl/Burp/scripts. When you see this, re-issue the
request with `Origin: <the-app's-own-origin>` + any `X-<App>-Ajax`-style flag and re-check for a
200/data response. This is the cheapest access-control-bypass probe on SPA admin backends.

## Recon notes
- Console is a Vite/React SPA. Mine `console.loginradius.com/assets/js/*.js`; the API client is
  `hK(e,t)` (builds `base + path + query`) + `mK` (GET) / `CK` (POST); API base
  `adminconsole-api.loginradius.com` is in `EK={prod:"https://adminconsole-api.loginradius.com"}`.
  grep `/".../..."` string literals yields the endpoint list (406 paths).
- `config.lrcontent.com/ciam/appinfo?apikey={key}&d={domain}` leaks a tenant's full IDX config
  (social providers, recaptcha key, registration schema, OTP settings) — but `lrcontent.com` is a
  third-party domain (OOS).
- Leaked internal hostnames in config: `auth-dev.lrinternal.com`, `devio-console.lrinternal.com`
  (`lrinternal.com` = OOS domain).