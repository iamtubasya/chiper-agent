# VeSync IoT Bug Bounty — protocol map & verified-negative ledger

Engagement notes, 2026-10-28. Target: `security.vesync.com/bug-bounty` (active, updated 2026-08-26).
Submit: `datasecurity@vesync.com`, PGP fp `4F2A 7C1E 9B3D 5F8A 2E4C 1D6B 8A3F 9E2C 7B5D 1A4F`.

Read this before re-hunting: the auth protocol below took most of the session to reverse, and the
negatives list exists so nobody re-tests disproved paths.

## Scope (Art. 5, verbatim)

> "(i) Vesync Application; (ii) IoT devices supported by Vesync Application, including outlets,
> switches, lighting, kitchen appliances, air purifiers, scales, trackers, etc."

**Art. 8(g) is the trap that kills most IoT leads here:** *"Vulnerabilities that require the user to
operate the Application or device to cooperate and interact (such as triggering the network
distribution, authorized login, etc.) will not be regarded as a Vulnerability."* Pairing-flow,
network-distribution and BLE-proximity findings are therefore unpayable on this program no matter
how real. Do not spend the session there.

Also: Art. 4(f) "will not exfiltrate any data under any circumstances"; VDP §7 no large-scale
automated scanning → gentle rate only. Bands: Critical $3–10k / High $1–3k / Medium $500–1k / Low $100–500.

## Target shape

Not subscription-monetised. Value = hardware + account + device pairing. So impact concentrates in
**account takeover** and **cross-tenant device control**, not pricing logic. The one untested
monetised surface is the store/mall estate (appID `tyhspdml`).

AppID map (from the web bundle):

| appID | app |
|---|---|
| `bqkfzrwn` | ACCOUNT_WEB (account.vesync.com auth SPA) |
| `eldodkfj` | CLOUD — **required for the mobile/cloud token** |
| `psybfyca` | PET_APP |
| `hesyqzkw` | H_APP (health) |
| `tyhspdml` | VESYNC_STORE |
| `eadvoakq` / `rxrovonj` / `tpzqlaeu` | Shopify: Levoit / Cosori / Etekcity US |

## Auth protocol — the part worth memorising

### Web API envelope (accountapi / platformapi)

Every call is `POST` with a `context` wrapper. `token` and `accountID` default to the **literal
string `"common"`** when unauthenticated.

```json
{"context": {
   "timeZone":"Asia/Jakarta","clientType":"pc","osInfo":"Windows","phoneOS":"Windows",
   "clientInfo":"Chrome 130","phoneBrand":"pc","clientVersion":"V1.0.1","appVersion":"Chrome 130",
   "terminalId":"MallWeb-<uuid4>",        // format wajib — plain uuid => -11000129
   "debugMode":false,"bizSystemId":"28005ad6-fca3-4634-9b43-ac47129c3b70",
   "acceptLanguage":"en","traceId":"WEB<14digits>-<5digits>",
   "appID":"bqkfzrwn","sourceAppID":"bqkfzrwn",
   "token":"common","accountID":"common",
   "method":"<last path segment>"},
 "data": {...}}
```

Routing: `/cloud/*` → `smartapi.vesync.com`; `/api/legal*` → `platformapi.vesync.com`; everything
else → `accountapi.vesync.com`.

### Web token — two steps

```
1  POST accountapi /globalPlatform/api/accountAuth/v1/authByPWDOrOTM
   {"email":"<e>","password":"<md5-hex>","authProtocolType":"generic"}   -> authorizeCode + accountID
2  POST accountapi /globalPlatform/api/accountAuth/v1/loginByAuthorizeCode4AccountWeb
   {"protocolList":[],"authorizeCode":"<ac>","redirectUri":null}          -> token
```

**MD5 of the password**, hex — not plaintext.

### Mobile/cloud token — the step everything hinges on

Step 1 is identical but with `appID: "eldodkfj"` + mobile context (`clientType:"mobile"`,
`phoneOS:"ios"`, `appVersion`). Step 2 must be the **Vesync** exchange, not the AccountWeb one:

```
POST smartapi /user/api/accountManage/v1/loginByAuthorizeCode4Vesync
{"method":"loginByAuthorizeCode4Vesync","authorizeCode":"<ac>",
 "userCountryCode":"US","regionChange":null,"bizToken":null}
```

Wrong exchange with a stale code returns `-11265129 "login temporary auth code expired"` — that is
an expiry signal, not a validation error; mint a **fresh** authorizeCode (TTL is short) and retry.
AuthorizeCodes are mode-bound: an `AccountWeb` code (`bizType: appId:bqkfzrwn`) is rejected by the
Vesync exchange. The pair must match.

### Cloud API body is FLAT, not the context wrapper

```json
{"acceptLanguage":"en","accountID":"<id>","appVersion":"5.6.60","debugMode":false,
 "method":"getHomeList","phoneBrand":"iPhone15,2","phoneOS":"ios",
 "timeZone":"Asia/Jakarta","token":"<app token>","traceId":"<ms>","userCountryCode":"US",
 "pageNo":1,"pageSize":50}
```

`bypassV2` adds `cid`, `configModule`, `configModel`, `deviceId`, and
`payload: {"method":"<act>","source":"APP","data":{}}`.

### Token shape

HS256 JWT, signature enforced. Bare token has an 8-digit **prefix**: `50010011` = session,
`30410011` = authorizeCode, `30110011` = MFA bizToken, `30010011` = setting bizToken,
`10010111` = cloud/app token. Claims: `aud` = accountID, `iss` = vesync.com, `jti`, `exp`, `terminalId`.

## Register an account yourself (working recipe)

Live page: `https://account.vesync.com/register-by-password`. Playwright + capture is faster than
guessing (see `disposable-auth-identity` → "Berhenti menebak payload"). Two steps:

```
1 sendVerifyEmailCodeNoAuth {email, password:<md5>, bizType:"register"}   -> mails a 6-digit code
2 registerByPwd {authProtocolType:"generic", password:<md5>,
   protocolList:[{protocolCode:"PRIVACY_POLICY",version:"20260831",url:...},
                 {protocolCode:"TERMS_OF_USE",version:"20261027",url:...}],
   emailCode, oneTimeCode, code, bizType:"register", email, newAccountEmail,
   registerSource:2}                                                   -> {accountID}
```

Get the protocol versions first from `platformapi /globalPlatform/api/legal/v2/globalGetLegalProtocolV2`
with `protocolCodeList:["PRIVACY_POLICY","TERMS_OF_USE"]`.

mail.tm works for the inbox; one domain only (`maxxspace.com`); 429s a second account per IP — see
the mail.tm pitfalls in `disposable-auth-identity`.

Account IDs are **sequential** (`23335362`, `23336789`, `23336790`, …) → trivially enumerable as an
ID space, but every authz check held (below).

## VERIFIED NEGATIVES — do not re-test

| vector | result |
|---|---|
| Cross-tenant home read (`getHomeDetail`/`getHomeInfo` w/ foreign `homeId`) | `-11002002 the user does not have permission` |
| `homeSharedInvitation` foreign `homeId` | `code 0` but membership lands on **caller's own** home — server ignores client `homeId`. Not a bug |
| Token↔accountID confusion (C's token + A's accountID) | rejected web + cloud |
| JWT forgery: `alg:none`, HS256 foreign sig, `aud` swap | all `the token has expired` |
| Pre-MFA `bizToken` used as session token | rejected |
| 2FA enforcement | enforced (`-11257129`); `authBy2fa` throttles at 5 |
| Reset-code brute | throttles at 5, then `requests are too frequent` |
| Reset code bound to its account | B's code → A = `email verification code invalid`; same code → B = `0` |
| Lockout | 5 bad logins → `-11247129`, 300 s, persisted even with correct password |
| Mass assignment `editAccountDataInfo` | `illegal argument`, state unchanged |
| Register on existing email | blocked at sendCode (`-11203129 the account is already exist`) |
| `authProtocolType:"oauth2"` to skip MFA | `illegal argument` |
| EU cluster `accountapi.vesync.eu` | identical validation + oracles |
| Unauth read-only sweep, 34 of 172 `/cloud/*` routes | only `getAppConfigurationV2` answered unauth, `configList: null` |
| APK embedded RSA private key | **false positive** — BouncyCastle test fixture in `classes20.dex`, not a VeSync secret |
| `discover.vesync.com` `.env`/`.git`/`_ignition`/`telescope`/`horizon` | all identical 301 meta-refresh to `/discover` = SPA catch-all, not a leak |
| `operationstatic.pawsync.com` | first-party S3+CloudFront, no dangling CNAME |

## REPORTED — Low

**Unauthenticated account enumeration**, 3 oracles, each 3 registered vs 3 unregistered
(9/9 + 9/9), CVSS 5.3:

| endpoint | exists | doesn't |
|---|---|---|
| `checkAppActivated` | `0 {"activated":true}` | `-11202129 the account does not exist` |
| `authByPWDOrOTM` (wrong pw) | `-11201129 account or password incorrect` | `-11202129` |
| `sendVerifyEmailCodeNoAuth {bizType:register}` | `-11203129 the account is already exist` | `0 request success` |

`checkAppActivated` is **not** rate limited (10/10 in a burst). Only the third one throttles
(~25 s per address).

## STILL UNTESTED — resume here

1. **Store/mall estate** — `us.` / `store.` / `store-pc.` / `store-pc-jp.`, Nuxt/Vue, appID `tyhspdml`. The only monetised surface. Untouched.
2. **`discover.vesync.com` `/api/*`** — Laravel + PHP 7.2.24; `/api/user` returns `401 {"message":"Unauthenticated."}` with `laravel_session` lacking `Secure`/`SameSite`. Route enum not done.
3. **`bypassV2` / `appRegister` / `loginByTourist`** — need a physical device; likely excluded by Art. 8(g) anyway.
4. **`cs.vesync.com`** — default "Welcome to nginx!" page, unprobed.
5. `test-*` / `uat-*` / `*.webdev.*` staging estate — live but scope eligibility unverified.

## Recon snapshot

117 resolved subdomains, 90 live (`httpx -threads 5 -rl 20`). Full API surface extracted from the
301 MB APK: 434 `/cloud/*` + 11 `/user/api/*` paths — grep the APK, not the docs
(`docs.vesync.com` has a broken cert).
