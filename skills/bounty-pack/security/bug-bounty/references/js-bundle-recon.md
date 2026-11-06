# JS Bundle Recon (SPA endpoint mapping)

Proven on Luno staging (Bugcrowd `luno-og`), 2026-09-10. Generalizes to any SPA target. This is how you map an entire API surface without an account.

## Workflow

1. **Fetch main page** with real browser UA + any mandatory bounty header from the brief; save HTML. Follow redirects (staging often 301s to www.).
2. **Extract bundle URLs:** `grep -oE 'src="[^"]*\.js[^"]*"'` — filter analytics (amplitude/gtag/googletag). Bundles often live on a separate CDN host (e.g. `prod.<brand>static.com`), NOT on the target domain. Fetch `main.js` + `vendor.js` (+ runtime/scripts) into `_progress/<target>/js/`.
3. **Mine bundles** with regex (write a small python script — escaping `$`/quotes in bash inline is fragile):
   - Full URLs: `https?://[a-z0-9.-]*(staging|<brand>)[a-z0-9./_-]*` → hidden hosts (ajax.*, ws.*, static.*, legacy domains)
   - API paths: `["'](/(ajax|api)/[0-9]+/[a-zA-Z0-9_/{}$-]+)["']` → endpoint map (yielded 33 paths on Luno)
   - WS endpoints: `wss?://` occurrences + `*WebSocketUrl` config keys → stream gateways
   - CSRF: grep `csrfToken` → find which endpoint issues it and which header carries it (Luno: issued in `/ajax/1/init` `userInfo.csrfToken`, sent as `X-Xsrf-Token` on POST/PUT/PATCH/DELETE)
4. **Probe each path unauthenticated** and classify by response:
   - `401 {"error":"authentication failure, type mismatch"}` → **multiple auth types exist** (session cookie vs API key) → auth-confusion / type-confusion vector candidates once you have any valid session
   - `405` on GET → POST-only endpoints (trade/order/move) → CSRF enforced; map now, test after account creation
   - `400` with param-specific error (e.g. "invalid duration: must be a number") → live parser behind it, fuzz candidate
   - `404` on documented prod paths → staging has different path layout; trust the bundle, not prod docs

## Runtime config file = the API topology subfinder never sees (Vesync, 2026-10-17)

Modern SPAs fetch a **runtime config** before the bundle — and it names the API hosts outright.
On `account.vesync.com` the page loaded `/config.js` (plus a third-party
`operationstatic.<brand>.com/static/lib/env-params/env-params.global.js`) containing:

```js
var PAGECONF_US = {
  hostApi: 'https://accountapi.vesync.com',       // ← NOT in subfinder output
  platformApi: 'https://platformapi.vesync.com',
  smartApi: 'https://smartapi.vesync.com/',
  sensorsServerUrl: 'https://analysis.vesync.com/...', opsEnv: 'prdDeploy'
}
var PAGECONF_EU = { hostApi: 'https://accountapi.vesync.eu', smartApi: 'https://smartapi.vesync.eu', ... }
```

**Add as workflow step 2b:** after extracting bundle URLs, fetch every `<script src>` that is
same-origin and small (`/config.js`, `/env.js`, `/settings.json`) — the API host map is usually
there before you grep a single bundle. Regional variants (`PAGECONF_EU` etc.) often expose a
second, less-hardened environment of the same API.

## Wrapper-function pattern → plain-JSON bodies + lazy chunks hold the field names

Minified bundles wrap every call as `at.post("<path>", {...e})` where `at` is an axios-like
instance with `baseURL = hostApi`. Grep for `post("` / `\.post\(` and you get the **full endpoint
map in one pass** (Vesync yielded `/globalPlatform/api/accountAuth/v1/authByPWDOrOTM`,
`sendVerifyEmailCodeNoAuth` (sent with a `version: 'v2'` header), `verifyEmailByCodeNoAuth`,
`authBy2fa`, `refreshAuth`, `/accountRegister/v1/registerByPwd`,
`/accountDataManage/v1/{getAccountDataInfo,resetPassword,setPassword,changeAccountEmail,trustOrRevokeDevice}`,
`/accountDsrr/v1/confirmDsrrVesyncAccount`). The `{...e}` spread means **plain JSON bodies** —
no signing, no envelope. The wrapper functions live in the main bundle, but the **actual form
field names live in the lazy route chunks** (`assets/RegisterByPassword-*.js`,
`assets/verify-code-*.js` — listed in the main bundle's dynamic-import table). When every probe
answers `illegal argument`, you are guessing field names: pull the route chunk for that screen.

Structured error envelopes are the oracle: `{"traceId":...,"code":-11102086,"msg":"internal error"}`
on an unknown path vs `{"code":-11000086,"msg":"illegal argument"}` (path exists, body wrong) vs
a business code (`Invalid or expired invite token`) — three distinct states that let you map
path-vs-params without introspection. `stacktrace: null` = no leak; a populated stacktrace field
would be its own finding.

## Signals worth chasing

- **Config endpoints that return WS URLs** (`POST /ajax/exchange/1/tradeconfig` → `marketWebSocketUrl`/`userWebSocketUrl`): locked behind login+CSRF unauthenticated, but the path is now mapped for the post-account phase.
- **Dev-mode branching in bundle** (`isDev()` rewrites URLs to `window.location.host`) → dev builds expose a different surface; check if source maps or dev builds are fetchable from the static CDN.
- **Static CDN directory listing** (`/static/` → 403) → enumerate known-prefix assets instead of listing.
- **Staging mirrors prod behavior exactly** (clean 401s, Cloudflare everywhere, no origin leaks via DNS) → the win is behind authentication. Get an account; do NOT grind unauth brute-force.

## Anti-patterns (QUALITY GATE)

- A 401/405/403 is the wall working, not a finding. Never report "missing auth check" from an unauth probe that returned 401.
- No severity claims from recon alone. Recon output = asset map + candidate list for the authenticated phase.
- Checkpoint findings to `_progress/<target>/RECON-STATUS.md` (asset map, API behavior table, artifacts) so the next session resumes cold without re-probing.