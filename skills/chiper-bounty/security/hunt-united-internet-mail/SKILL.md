---
name: hunt-united-internet-mail
description: "Hunt United Internet mail platforms (mail.com/web.de/GMX) incl. flexreg signup."
metadata:
  hermes:
    tags: [security, bug-bounty, mail-com, gmx, web-de, united-internet, flexreg, recon]
---

# Hunting the United Internet mail platform (mail.com / GMX / WEB.DE)

One product, three brands, one shared backend. A bug found on any brand's interface
counts once for the whole programme (program rules say so explicitly). Engage this
skill whenever the target is mail.com, gmx.net, web.de, or any `*.mail.com` /
`*.gmx.net` / `*.web.de` host.

## 0. Program facts (verified 2026-10-24)

- Policy: `https://bugbounty.mail.com/` — report to **report@bugbounty.mail.com**
  (security.txt: `https://www.mail.com/.well-known/security.txt`).
- **In scope:** web applications in the authenticated area processing customer data
  (email, calendar, file storage) **including the authentication systems**.
- **Out of scope (auto-close):** product features (sharing, SPAM), malware issues,
  "not directly exploitable" (missing headers, information leakage), self-XSS /
  physical-access issues, availability (e.g. logout CSRF).
- Eligibility: first finder across all three brands; no real customer data at risk —
  use a test account for PoC.
- Core business: free ad-supported email (100+ domains) + Premium subscription
  (shop.mail.com, ad removal / more storage) + cloud + calendar. Money flow:
  signup → optional Premium upgrade → entitlement → ad-free experience.

## 1. Attack-surface map (from a full recon, 154 subs / 64 live)

| Area | Host(s) | Notes |
|---|---|---|
| Webmail app | `navigator-lxa.mail.com` (+ `addressbook`, `oauthbridge`, `trackbar`, `cats`, `epimetheus`, `interception`, `lps`, `wusa`, `products`) | SPA "mailint" 1.484.0 on s.uicdn.com; per-client host pattern `$(clientName)-$(dataCenter).mail.com` in the login form's successURL |
| Account mgmt | `account.mail.com` / `account-lxa` / `ciss.mail.com` / `myaccount` | Apache Wicket app "ciss" 1.16.132; every path 401s without session; JSESSIONID appears in the redirect URL (`/ciss/login;jsessionid=…`) |
| Calendar | `calendar.mail.com`, `caldav.mail.com` | calendar root answers `OK` (2 bytes) on every path — health endpoint, not the app |
| Cloud/files | `cloud.mail.com`, `storage-{us,eu}`, `storage-file-{us,eu}` | `storage-file-*` = Basic realm "Online Storage" |
| Auth | `login.mail.com` (UAS), `password.mail.com` (Wicket recovery), `oauth2.mail.com` (OAuth2 — authorize endpoint IS functional), `auth.mail.com`, `mlogin`, `signup` | login form posts service/statistics(encrypted blob)/uasServiceID/successURL |
| Registration | `register.gmx.net`, `register.web.de`, `register-service.*` | flexreg 2.14.1 (see §3) |
| Attachments | `attachment-download.mail.com` | OAuth Bearer-protected; URL pattern `/mailbox/primary/Mail/{uuid}/{ts}/Attachment/{id}` — **prime IDOR candidate once you hold a token** |
| Edge | everything | "platform-mesh" (k8s); `X-App-Dc` / `X-App-Host` headers leak pod names (info only, auto-closed) |

Full recon artifacts pattern: subfinder → httpx → gau → katana → ffuf(sensitive
wordlist) → arjun → nuclei(curated, gentle). Negative results worth recording:
no user-enumeration on login (generic error, uniform ~1.6 s timing), recovery tokens
are session-bound (cross-session = 401), no CORS reflection, no GraphQL, no subdomain
takeover (67 non-resolving subs, no dangling CNAMEs), TRACE disabled.

## 2. Getting a test account (the hard part — plan around it)

- **mail.com signup is geo-blocked edge-wide**: from a non-allowed country every path
  on `signup.mail.com` answers 403 (platform-mesh), and `register-service.mail.com`
  exists but 404s. The block is IP-based; consent cookies do not help.
- **GMX/WEB.DE wizards load from anywhere** (`register.gmx.net`, `register.web.de`)
  but the final step is an **mTAN SMS verification** (6-digit, 3 attempts, 60 s
  cooldown per the `/config` response). Do not use the operator's personal phone
  without explicit approval; a paid SMS service needs budget approval.
- **Anti-automation is per-IP across all three brands**: after ~10 registration
  starts the wizard bails to `hilfe.<brand>.net/kundenservice/flexreg.html`
  ("Registrierung fehlgeschlagen") and `/aliases` starts answering
  `denial-error`. Budget **~1 usable registration flow per 30–60 min per IP** and
  schedule multi-run validations around that cooldown. Free proxy lists are ~96 %
  dead and mail.com blocks datacenter IPs anyway; a Vercel relay fleet does not
  defeat geo policy (see skill `geo-block-proxy-ops`).

## 3. flexreg registration API map (the reusable part)

Driving `register.gmx.net` (same shape on web.de) with a browser, the flow calls
`https://register-service.gmx.net` with header `x-ui-app: flexreg/2.14.1`:

| Step | Endpoint | Content-Type | Body |
|---|---|---|---|
| config | GET `/config?product=gmxnetFree&defaultCountryCode=DE` | — | returns registrationFlowId + protectiveMeasures (mTan, CAPTCHA_FOX) |
| captcha | POST `/captcha-verification` | application/json | `{"captchaFox":{"userSolution":"MAM_…"},"registrationFlowId":…}` |
| identity | POST `/personal-info` | `application/vnd.ui.mam.flexreg.user.personalinfo-v1+json` | `{registrationFlowId, firstName, lastName, birthDate}` |
| alias | POST `/aliases` | `application/vnd.ui.mam.flexreg.alias.suggestioninput-v2+json` | `{registrationFlowId, amount, wishAlias, mode:"alias"}` |
| select | POST `/alias-selection` | — | confirms the chosen address |
| address | POST `/address-details` | — | gender/postalCode/city/street/country |
| password | POST `/password-check` | — | password strength gate |
| mTan | phone step | — | SMS verification — **the wall** |

Flow state is carried by cookies `reg-flow-data0` / `reg-flow-data1` /
`chunks-flow-data`, which are **encrypted** (decoding yields binary, not JSON) and
bound to the registrationFlowId — a random flow id with a valid cookie is rejected
(`cookie-validation-error`), so the cookies are not forgeable. Fetch calls from page
context need `credentials:'include'` or they arrive cookie-less and 401.

## 4. Enumeration oracle (finding class, validated)

`POST /aliases` with `mode:"alias"` answers `{"available":true/false}` — a reliable
account-existence oracle for the whole platform:

```
postmaster@gmx.de           -> {"available":false}   registered
admin@gmx.net               -> {"available":false}   registered
abuse@gmx.de                -> {"available":false}   registered
zzq_nonexistent_8471@gmx.de  -> {"available":true}    not registered
```

Report as Low (CWE-204/CWE-200): mass-enumeration of customer addresses enables
targeted phishing/credential stuffing. The platform applies denial-error after
sustained probing, which raises attacker cost but does not remove the oracle — say
that honestly in the report.

## 5. OAuth client-secret exposure (finding class, validated 3x)

The one-connector entry page (`https://connect.gmx.net/entry?mc=…&ac=…`) embeds
`data-clientid` + `data-clientsecret` in public HTML. Prove a leaked secret is live
by the error-shape differential at the token endpoint:

```
valid secret  + grant_type=authorization_code -> {"error":"invalid_grant"}     (client AUTHENTICATED)
wrong secret  + grant_type=authorization_code -> {"error":"invalid_client"}    (client auth FAILED)
```

Per-grant client authorization is enforced (password/client_credentials/refresh_token
answer invalid_client for this client even with the valid secret), so scope the
impact claim honestly: broken public-client model + phishing material, not direct
account access.

## 6. Pitfalls that cost time

- **Wizard "Continue" needs TWO clicks** on the alias step: the first fires the
  async availability check, the second advances (`/alias-selection`). A single click
  looks like a dead form.
- **CaptchaFox smart checkbox: use a REAL click and poll for the API call.** An earlier
  version of this skill said `dispatch_event('click')` is more reliable — corrected
  2026-10-25: real sessions hit runs where dispatch_event never fired the API calls
  (only `GET /config` appeared, alias input stayed disabled). Pattern: wait for
  `.cf-checkbox` + ~4 s stabilise → real `click(timeout=10000)` → poll the network for
  captcha-verification AND personal-info (2.5 s interval, up to 4 click retries). Full
  recipe in skill `flexreg-anti-automation-bypass`.
- **Token-mismatch artifact (false-positive trap)**: in the Wicket password-recovery
  flow (`password.mail.com/passwordrecovery/`), submitting a form whose hidden
  `srttkn` does not match the session's current token renders a *clean* page 2 that
  looks like a different response class (e.g. "no error = account exists"). It is
  not. Always extract the hidden token from the freshly fetched form and re-run the
  comparison before claiming an enumeration oracle. The mail.com recovery flow showed
  uniform errors once tokens matched — do not report it.
- `fetch` from page context without `credentials:'include'` silently loses the flow
  cookies → `cookie-validation-error` that looks like a server-side block.
- oauth2 authorize validates the client before everything else — without a valid
  client_id you cannot probe redirect_uri/response_type behaviour.

## 7. Mobile / APK surface (verified 2026-10-25)

The Android app (`com.mail.mobile.android.mail`, APKMirror has it when APKPure/APKCombo are
Cloudflare-blocked — download flow + toolchain in skill `apk-redteam-pipeline`) exposes:
- **`POST https://brand-resolver.mail.com/resolution`** — LIVE, `{"username":"<email>"}` →
  `{"brand":"mailcom|gmxnet|webde"}`; strict domain mapping, no injection/enumeration value.
  Needs `Origin: https://auth.mail.com`.
- **`auth.mail.com/loginapp`** — the mobile WebSignIn React app; **full source map at
  `/assets/login-app.js.map`** (90 TS sources). Login API: `identification`,
  `authentication/password`, `authentication/token`, `authentication/webauthn-start|finish`
  (sessionId-based), captcha verifications. Mobile deep link
  `com.mail.androidmail.redirect://authorization_code_grant/close` = OAuth code grant.
- **RestFS guest-share pattern** `restfs/guest/{ownerId}/share/{shareHash}/{resourceId}` on
  `storage-file-us.mail.com` — **prime IDOR candidate once authenticated** (edge Basic-auth
  blocks anonymous probes; API keys from the APK do not bypass it).
- Dead/unreachable: `lts.*.com/logintokenserver`, `cocos-lookup` (needs params),
  `lcloud`/`bigfile`/`xps.uimserv.net`.

Full detail (endpoint table, API-key values, X-UI-* headers, RestFS operation list):
`references/apk-mobile-surface.md`.

## 7b. Third-party / adjacent surface found in round 3 (2026-10-25)

- **Cognigy AI chatbot**: the webchat wrapper (`s.uicdn.com/mampkg/@mamdev/core.frontend.libs.webchat-wrapper/webchat-wrapper.js`) leaks `chatbot-services.mail.com` (403 blanket) and live `endpoint-mam.cognigy.cloud/<64-hex>` endpoints. GET on the token returns the full widget config (title "mail.com Support Chat", colours, `disableHtmlContentSanitization:false` = sanitisation ON). POST answers `channel: 'webchat3' is invalid or unsupported` for every channel value — a broken/misconfigured chatbot (availability, not security). Config is public by design.
- **games.mail.com**: gaming CMS (cms 8.0.81, same as shop). `/login` → 301 → `/site/login` → 404 (decommissioned). No API/admin/actuator paths; robots/sitemap 404 (SPA catch-all). CSP leaks internal domain `*.server.lan`.
- **www.mail.com `/ajax/webvitals`**: POST-only (GET → 405 `Allow: POST`), 500 on any body, no stack trace in the error page. `/mail.com/welcomeback` returns a static JSON teaser payload (no reflection).
- **plus.mail.com** ("ADITIONSERVER v1.0"): `/track` → 302 to `imagesrv.adition.com/1x1.gif`, ignores url params (no open redirect).
- **caldav.mail.com**: PROPFIND/REPORT/OPTIONS all 302 → `/begenda/dav/users/…`; every user path 401 uniformly (no enumeration difference).
- **MTA-STS** (`mta-sts.mail.com/.well-known/mta-sts.txt`): `mode: testing` (not enforce) — informational only.
- **Blog** (`www.mail.com/blog/`): custom, NOT WordPress (wp-json/xmlrpc/wp-login all 404).
- **Shop/premium**: `shop.mail.com/*` → 301 → `www.mail.com/premiummail/tariffs`; the purchase flow itself lives behind login (marketing pages only when anonymous).
- **HTTP request smuggling** (raw-socket CL.TE/TE.CL/TE-obfuscated/double-CL against www/account/login): all answered fast and uniformly — no desync timing, edge hardened. **CRLF** in login successURL: not reflected. **`.well-known` sweep**: no openid-configuration anywhere; security.txt only.
- **hsp/hsp2/confix-android/chatbot-services**: OAuth Bearer-protected (401 + `oauth-protected-resource` metadata pointer) or blanket 403 once the IP is flagged.

## 7c. Operator workflow lesson (2026-10-25)

When one avenue blocks (registration wall), do NOT tunnel on it — the operator's word:
*"gkush kejar regis aja, kamu cek ulang unauth surfacenya, seluas itu, pasti ada bug"*.
Re-sweep the whole unauthenticated surface systematically (every live host × every
bug class) before concluding. Three exhaustive rounds on this target still ended with
the surface hardened and the remaining vectors account-gated — that is an honest,
reportable outcome, not a failure, and the sweep evidence (per-host × per-class) is
what makes it defensible.

## 8. References

- `references/ui-mail-platform-detail.md` — full host inventory, request/response
  transcripts, evidence-file layout, and the engagement log from the 2026-10-24
  session.
- `references/apk-mobile-surface.md` — mobile/APK surface: brand-resolver, loginapp
  source-map API map, RestFS guest-share pattern, API keys, dead hosts.
- Program policy: https://bugbounty.mail.com/ · security.txt:
  https://www.mail.com/.well-known/security.txt
- Related skills: `geo-block-proxy-ops` (signup geo-block escalation),
  `security-recon` (pipeline), `reportlab-security-pdf` (draft + PDF delivery),
  `apk-redteam-pipeline` (APK download + analysis toolchain),
  `flexreg-anti-automation-bypass` (route-abort technique for the registration API).

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/flexreg-anti-automation-bypass/PLAYBOOK.md` — the shared United Internet registration
  API family (mail.com / web.de / GMX): the flexreg endpoint shape, the anti-automation fields, and
  the bypasses that were actually verified. Load it before attacking signup on any UI family that
  resolves to flexreg.
