# Extracting the API contract from a production SPA bundle (worked recipe, VeSync 2026-10-17)

When the SPA is a Vite/Vue/Angular production build and the API host is not guessable from
subdomain enumeration, the bundle hands you the whole contract. Order that worked on
`account.vesync.com` (VeSync account SPA):

## 1. Runtime config script first
`/config.js` (also `/gen-cfg.js`, `/env.js`) is server-rendered and usually unauthenticated.
VeSync's declared the entire API topology:

```js
var PAGECONF_US = {
  hostApi: 'https://accountapi.vesync.com',
  platformApi: 'https://platformapi.vesync.com',
  smartApi: 'https://smartapi.vesync.com/',
  sensorsServerUrl: 'https://analysis.vesync.com/analysis/v1/uploadTrackingData4JS',
  opsEnv: 'prdDeploy'
}
```

`accountapi.vesync.com` appeared in NO subdomain list — the config was the only source.

## 2. Grep the bundle for call shapes, not URLs
```python
re.finditer(r'\.post\("([^"]+)"', js)      # every endpoint path
re.finditer(r'(query|mutation|subscription)\s+([A-Z]\w+)', js)   # GraphQL operation names
```
Surfaced e.g. `/globalPlatform/api/accountAuth/v1/authByPWDOrOTM`, `.../sendVerifyEmailCodeNoAuth`,
`/globalPlatform/api/accountRegister/v1/registerByPwd`, `.../accountDataManage/v1/resetPassword`.

## 3. Read the HTTP client's request interceptor — it defines the envelope
VeSync's axios instance wrapped EVERY body and routed by path prefix:

```js
at.interceptors.request.use(e => {
  const {appID: t, token: n, userInfo: i} = Qo(), {appID: a} = Xr(), {lang: s} = uc()
  let u = e.data, f = {...vM, acceptLanguage: s, traceId: N1(), appID: t,
                       sourceAppID: a || t, token: n || "common",
                       accountID: (i?.accountID) || "common",
                       method: e.url.match(/[^/]+$/)[0]}
  e.data = {context: f, data: u}
  e.url.startsWith("/cloud") ? e.baseURL = smartApi
    : e.url.includes("/api/legal") && (e.baseURL = platformApi)
})
```

Probing with a bare JSON body gets a generic `illegal argument`; the `{context, data}` envelope is
the difference between a working call and a wall. Replicate `context` exactly (timezone, clientType,
osInfo, clientInfo, phoneBrand, clientVersion, appVersion, acceptLanguage, traceId, appID,
sourceAppID, token:"common", accountID:"common", method).

## 4. Constant maps live in the bundle
- appID per surface: `Ls = {ACCOUNT_WEB:"bqkfzrwn", CLOUD_APP:"eldodkfj", VESYNC_STORE:"tyhspdml",
  SHOPIFY_LEVOIT_US:"eadvoakq", …}`
- server error-code maps: `11203 account_is_exist`, `11247 account_locked`, `11248 account_frozen`,
  `11257 mfa_required`, `11252/3 bizToken_invalid`, `11264 to_many_verification_email` — these tell
  you the auth surface's vocabulary before you touch it.
- client-side validation regexes (password policy: 8+ chars, 3-of-4 classes).

## 5. Lazy route chunks carry the form fields
Main-bundle wrappers take `{...e}` spreads; the real field names are in per-route chunks.
Enumerate `assets/[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8}\.js` from the bundle, download the relevant ones
(`LoginByPassword-*`, `RegisterByPassword-*`, `ForgotPasswordEmail-*`), and read the submit
handlers. VeSync login call site:

```js
const [t, e] = await W({password: ae(r.value), email: n.value,
                        authProtocolType: "generic", ...j()})
```

## 6. Rate-limit / policy UI chunks confirm server behaviour
A `SendCodeFrequently-*.js` chunk ("tooManyVerification … thirtyMinutes") revealed the email-code
endpoint is capped at 1 per 30 min BEFORE spending a single request testing it.

## 7. Hash functions imported by the login chunk are part of the contract
`import{m as ae} from "./md5-*.js"` + `password: ae(value)` = client-side MD5 before transit.
Replicate the exact hash the bundle computes, not a guess.

## Pitfall: structured error bodies are progress signals, not results
A `200 {"traceId":…,"code":-11102086,"msg":"internal error"}` is NOT a working call. Treat any
`code != 0` as "shape wrong" and diff your body against the bundle's construction until the code
changes. Error-code deltas are the signal: `-11000086` (bad shape) → `-11000129` (envelope landed,
one field still wrong) → real auth errors. Also check content-type acceptance explicitly
(application/json vs application/x-www-form-urlencoded vs text/plain) — an endpoint that executes
urlencoded but rejects text/plain is a CSRF-relevant asymmetry worth noting.
