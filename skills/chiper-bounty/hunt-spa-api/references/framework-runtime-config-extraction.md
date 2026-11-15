# Framework runtime-config extraction — per-framework recipes

Companion to `hunt-spa-api` §2e. Verified on a large telco estate (2026-10), 5 different frameworks
across ~20 hosts. Every recipe below is one or two GETs and replaces blind wordlist fuzzing.

Order of operations: **shell → config endpoint → bundle grep → interceptor → control probe.**

---

## Nuxt 3

The shell carries a full server-rendered config blob inline:

```bash
curl -s https://TARGET/ -o shell.html
grep -oE 'window\.__NUXT__=\{\};window\.__NUXT__\.config=\{[^<]{0,4000}' shell.html
```

Real output shape:

```
window.__NUXT__.config={public:{buildDate:"2026-10-29T10:34:19.481Z",applicationEnv:"production",
baseUrl:"https://shop.target.de",paypalExpressDetailPage:{disabled:true},
performanceMode:{enabled:true,disableFilter:false,…},…}}
```

What it gives you:
- `baseUrl` — the canonical origin (compare with the host you hit; a mismatch means a CDN/origin split)
- `applicationEnv` — `production` vs `staging` (a staging value on a prod host is a finding)
- feature flags — `{disabled:true}` on a payment/express path is a **business-logic lead**, not just config
- the rest of the `__NUXT__` payload (outside `.config`) is the serialised Pinia/Vuex state — grep it for
  `csrfToken`, `cart`, `initialized` keys to learn the session model

Nuxt 3 bundle chunks are flat and hash-named. No chunk map needed:

```bash
grep -oE '/_nuxt/[A-Za-z0-9_.\-]+\.js' shell.html | sort -u > chunks.txt
# pull them all in parallel, then:
grep -ohE '["\x27`](/api/[^"'\x27`]{1,60})["\x27`]' *.js | sort -u
```

**Nuxt server routes live under `/api/*` on the same origin.** They can exist and be routed while a
middleware feature-guard answers 404 for the gated subset — always test the `/api/*` paths the bundle
names directly rather than trusting the shell.

---

## Nuxt 2 / Vue CLI (`/_nuxt/`)

Same flat-chunk trick. Config usually arrives via `axios.create({baseURL: process.env.VUE_APP_…})`
which the build replaces with a literal:

```bash
grep -ohE 'VUE_APP_[A-Z0-9_]+:"[^"]*"' *.js
grep -ohE 'baseURL:"[^"]*"' *.js | sort -u
```

---

## Vite (`import.meta.env` → inlined literals)

`import.meta.env.*` is **replaced at build time**, so every value is a plain string literal in the
bundle. One grep dumps the entire build environment:

```bash
grep -ohE 'VITE_[A-Z0-9_]+:"[^"]*"' *.js | sort -u
```

Real output from a telco React SPA:

```
VITE_BACKEND_API_URL:"/backend/api"
VITE_BACKEND_URL:"/backend"
VITE_COMMIT_ID:"251adff3"
VITE_COMMIT_TIMESTAMP:"2026-10-12T10:32:53+02:00"
VITE_DEV_TOOLS_ENABLED:"false"
VITE_OIDC_AUTHORITY:"https://TARGET/auth/realms/<realm>"
VITE_OIDC_CLIENT_ID:"<client>"
VITE_OIDC_REDIRECT_URL:"https://TARGET"
VITE_MAPBOX_ACCESS_TOKEN:"pk.eyJ1Ij…"
VITE_TILER_API_KEY:"<16 chars>"
VITE_REVERSE_GEOCODING_URL:"https://nominatim.openstreetmap.org/reverse"
```

Notes:
- `VITE_BACKEND_API_URL` is the **real** prefix. In this case `/backend/api/*` answered `401`, while the
  naive `/api/*` prefix answered `200` with the SPA shell — the catch-all trap. Always try both and
  compare bodies, not status codes.
- `VITE_OIDC_AUTHORITY` + `VITE_OIDC_CLIENT_ID` hand you the Keycloak realm and client name without any
  discovery guessing.
- **Third-party keys need scope triage before you write them up.** A Mapbox `pk.` token is public by
  design; only a *secret* key (`sk.`) or an unrestricted `AIza` with a payable API enabled is a finding.
  Verify against the provider's own scope endpoint first.

---

## Angular

### Config endpoint

Grep the bundle for the loader to find the path:

```bash
grep -ohE '.{200}(loadEnvConfig|getEnvConfig).{200}' *.js
```

Typical result: the app fetches `/assets/config/app-config.json?t=<Date.now()>` at bootstrap.

```bash
curl -s "https://TARGET/assets/config/app-config.json" | jq .
```

Real output (note the values — this is a *production* host):

```json
{ "version":"local-dev",
  "apiBasePath":"http://localhost:4200/api",
  "callbackTrackingEnabled":true,
  "maxAgeSeconds":1800,
  "maxAllowedPasskeys":10,
  "applicationLinks":{ "telekomStartpage":{...}, "mfaHelpLink":{...}, ... },
  "authenticators":{ "google":{...}, "apple":{...} } }
```

Two takeaways:
1. **`version: local-dev` + a `localhost` API base on prod = deploy hygiene finding** (Low/Info on its
   own, but it is real and it's yours).
2. The config is **useless for finding the API** in this state. Get the base from the interceptor:

```bash
grep -ohE 'beforeIntercept\([^)]*\)\{[^}]{0,300}' main-*.js
# → o=t.clone({url:u.startsWith(c)?u:Us(c,u)})  where c = envConfig.apiBasePath
```

### `feature-guard` 404 envelope

Angular apps behind a feature-gate middleware return HTTP **404** for routes that exist but are
disabled. The envelope is the tell:

```json
{"error":true,
 "url":"https://TARGET/api/account/profile",
 "statusCode":404,"statusMessage":"Not Found","message":"Not Found",
 "data":{"source":"feature-guard"}}
```

Interpretation ladder:
- `data.source == "feature-guard"` → **route exists, gate off**. Treat the path as discovered. Try the
  enabled sibling (`/api/account/name` vs `/api/account/profile`) — sibling-gate differential is a real
  finding class.
- plain 404, `text/html`, no JSON → path does not exist.
- `404` + `{"error":…}` without `feature-guard` → different middleware, keep going.

### Angular route table

Angular ships its router config as `{path:"…",component:…}` objects in the main bundle:

```bash
grep -ohE '\{path:"[^"]*",(canActivate:\[[A-Za-z0-9_,]+\],)?component:[A-Za-z0-9_]+\}' main-*.js | sort -u
```

`canActivate:[…]` on a route names the guard; a route **without** a guard in a guarded block is the
one to probe. Also grep for `authClassHighProtectedRoutes` / `authClass` — that's the app declaring
which routes need a higher ACR, i.e. the sensitive half of the map.

---

## Next.js

Covered in `hunt-spa-api` §2c. Additions from this estate:

- `/env-config.js` on a Vue-CLI app returned
  `window.__ENV__ = { ENVIRONMENT_NAME:"PRODUCTION", AUTH_PROVIDER:"icu", … }` — one request names the
  IdP integration and confirms prod.
- `_next/static/chunks/*` on a Next 15 app returned **9 chunks, zero `/api/` literals** — the routes
  were server-side only. When a Next bundle yields nothing, stop grepping and go to the BFF:
  probe `/api/health`, `/api/jobs`, `/api/v1` and read the 404 body (Next's own 404 page vs the app's
  JSON envelope tells you whether a route handler exists).

---

## Spring Boot (backend, not SPA — but you meet it here)

Fingerprint from the 404 body, then pick the docs endpoint:

| Response | Meaning |
|---|---|
| `{"timestamp":…,"status":404,"error":"Not Found","message":"No static resource swagger-ui.","path":…}` | Spring Boot 3.x, springdoc UI absent → try `/v3/api-docs` |
| `{"timestamp":…,"status":500,"message":"Could not initialize class …HikariDatasource$HikariDataSourceHolder"}` | Boot 3 + Hikari; **DB pool dead** → endpoints exist, data unreachable |
| `{"error":"unauthorized","message":"Authentication required"}` | custom BFF auth filter, working correctly |
| `{"errors":[],"traceId":"Root=1-…","userTraceId":"<uuid>"}` | AWS-style edge + custom error envelope |

`/v3/api-docs` is the highest-yield single request against any Boot service — 46–72 paths in one shot.

---

## Control probe (always, before claiming a gap)

Pick a route you *know* should be gated, call it bare, capture the rejection. Then call the target
route bare. The differential is the finding.

```
control  GET /api/v1/roles                 -> 401 (empty body)
target   GET /api/v1/partners              -> 500 (Hikari dead)   ← auth filter ABSENT
target   GET /api/v1/partners/1/sims       -> 500 (Hikari dead)   ← same
```

The 500s are *not* a working unauth endpoint, but they prove the request traversed past where the
security chain would have rejected it. That is the reportable defect. Say both things plainly.
