# SPA API envelope reverse-engineering (worked case: VeSync account SPA, 2026-10-17)

When the target is a modern SPA (Angular/React/Vue) whose real API is undocumented, the whole
private API can be reconstructed from static assets — no guessing. This is the recipe that took
`account.vesync.com` from "every endpoint says illegal argument" to a full auth-flow map in one
session. Companion to `js-bundle-recon.md` and `mobile-app-bundle-recon.md`; this file is about
the **request envelope + field-name extraction**, which is where most attempts stall.

## 1. Runtime config first — the API hosts are usually served separately

The SPA shell (`/`) references a runtime config file (`/config.js`,
`window.__CONFIG__`, `/env.js`). Fetch it before the bundle:

```js
var PAGECONF_US = {
  hostApi: 'https://accountapi.vesync.com',
  platformApi: 'https://platformapi.vesync.com',
  smartApi: 'https://smartapi.vesync.com/',
  ...
}
```

That single file gave the three real API hosts (one of which — `accountapi` — was NOT in the
subdomain enumeration). Rule: **the config file is the topology; subfinder is only the perimeter.**

## 2. Bundle grep for endpoint paths

Download the main bundle from the shell's `<script src>` and grep:

```python
paths = sorted(set(re.findall(r'["\'`](/v[0-9]/[a-zA-Z0-9/_{}-]{2,50})["\'`]', bundle)))
# and for namespaced APIs:
re.findall(r'\.post\("([^"]+)",\s*(\{[^}]{0,300})', bundle)   # path + inline payload
```

VeSync's lived under `/globalPlatform/api/<module>/v1/<action>`:
`accountAuth/v1/authByPWDOrOTM`, `accountRegister/v1/registerByPwd`,
`accountDataManage/v1/resetPassword` … The `.post("path", {...})` regex gives both the path AND
the payload shape when the call site is in the same bundle.

## 3. The envelope — why raw bodies get "illegal argument"

The axios instance had a request interceptor that WRAPS every body:

```js
at.interceptors.request.use(e => {
  const {appID: t, token: n, userInfo: i} = Qo(), {appID: a} = Xr(), {lang: s} = uc();
  let u = e.data,
      f = {...vM, acceptLanguage: s, traceId: N1(), appID: t, sourceAppID: a || t,
           token: n || "common", accountID: (i?.accountID) || "common",
           method: e.url.match(/[^/]+$/)[0]};
  e.data = {context: f, data: u};          // <<< THE ENVELOPE
  ...
});
```

So the wire format is `{"context": {...common}, "data": {...actual payload}}` — posting the bare
payload gets `-11000086 illegal argument`; posting the envelope with one wrong field gets a
DIFFERENT code (`-11000129`) — **the error code moving is your progress signal.**

Common-field object (`vM`) found nearby: `timeZone, clientType ("pc"/"mobile"), osInfo, phoneOS,
clientInfo, phoneBrand, clientVersion, appVersion`. Base-URL routing in the same interceptor:
paths starting `/cloud` → smartApi, containing `/api/legal` → platformApi, else hostApi.

## 4. The appID constant map

`Ls = {PET_APP:"psybfyca", H_APP:"hesyqzkw", CLOUD_APP:"eldodkfj", ACCOUNT_WEB:"bqkfzrwn",
VESYNC_STORE:"tyhspdml", SHOPIFY_LEVOIT_US:"eadvoakq", ...}` — grep the bundle for
`ACCOUNT_WEB` and read the surrounding object. `appID` is a required context field; the map also
leaks which client apps exist (useful surface intel by itself).

## 5. Exact field names live in the LAZY route chunks

The main bundle's wrappers take `{...e}` spreads — the real field names are in the per-route
chunks listed in the bundle's import map:

```
assets/RegisterByPassword-B_o21h3O.js, assets/LoginByPassword-abi37PlL.js,
assets/ForgotPasswordEmail-BRsE0SsE.js, assets/verify-code-*.js, ...
```

Download the interesting ones and read the component `setup()` — the login chunk showed the
whole call verbatim:

```js
const [t, e] = await W({password: ae(r.value), email: n.value,
                        authProtocolType: "generic", ...j()});
```

That is where you learn the password is **MD5-hashed client-side** (classic VeSync scheme), the
`authProtocolType` enum, and the extra-fields helper. Also read the password-field regex for the
policy (8+ chars, 3-of-4 classes) and the error-handler branches (`account_frozen`,
`account_locked`, `mfa_required`, `account_not_init`, `email_not_match`) — that is your
enumeration oracle once the call lands.

## 6. Error-code schema enumeration (introspection off)

With introspection disabled, field/type existence still leaks through validation errors:

- `{ zzz }` → `Field 'zzz' doesn't exist on type 'Query'` (confirms Query type)
- `question(id: "x")` → `Type mismatch on variable $id and argument id (ID! / Int!)` (confirms
  field + arg type)
- `organization(slug: "x")` → `doesn't accept argument 'slug'` (field exists, wrong arg)

Walk candidate names; each error is a one-bit oracle. Response interceptor also maps numeric
codes to UI states (`11247 account_locked`, `11248 account_frozen`, `11257 mfa_required`,
`11203 account_is_exist`, `11264 to_many_verification_email`) — grep the bundle for the code map.

## 7. Playwright hydration wait (the blocker that eats 30 minutes)

React/Vue SPAs hydrate slowly behind big vendor chunks. Symptom: `fill()`/`click()` "succeeds"
but nothing happens, no XHR fires, submit stays disabled. Fix:

- `wait_until='domcontentloaded'` (NOT `networkidle` — analytics/websockets keep it busy forever)
- **sleep ~20 s for hydration**, then interact
- `pg.evaluate("() => document.querySelector('#email').focus()")` + `pg.keyboard.type(...)`
  (trusted events) beats synthetic `fill()` on controlled inputs
- checkbox state: click via Playwright real click AFTER hydration, then assert `is_checked()`

## 8. Tool notes

- **graphql-cop** installs from `dolevf/graphql-cop` (GitHub) — NOT `dotw0rd`. If `pip install
  git+...` is blocked (AV), fetch the zip from `codeload.github.com/dolevf/graphql-cop/zip/refs/heads/main`
  and `pip install -r requirements.txt` in place. Run: `python graphql-cop.py -t <url>`.
- jsluice may be unbuildable on Go 1.24 (tree-sitter API break, no release binaries) — the
  compensating control is a regex secret scan over the downloaded bundles
  (`AKIA|sk_live_|ghp_|xox|AIza|BEGIN PRIVATE KEY`).

## 9. What this buys (and what it doesn't)

Full endpoint map + auth scheme + field names = you can now test enumeration, rate limits, and
auth flows precisely. It does NOT prove impact: in the VeSync case the GraphQL layer rejected the
Rails session cookie (Bearer-only auth), which killed the CSRF angle — always verify the
auth-transport assumption (cookie vs header) before claiming a cross-site primitive.
