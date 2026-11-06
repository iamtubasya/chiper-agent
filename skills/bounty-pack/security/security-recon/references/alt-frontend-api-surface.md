# The newer frontend is a second, weaker API surface

Verified 2026-10-29 on Social Deal (Intigriti). The legacy PHP storefront refused every
registration/login (`{"field":"email"}` for gmail.com, outlook.com, mailinator, maxxspace.com,
intigriti.me — with Cloudflare Turnstile present), while a **completely separate Next.js app on the
same host** exposed its own auth API that issued a valid session with **no Turnstile at all**.

Generalise this: when the marketing/legacy app is locked down, the migration target is usually
still reachable and less defended. Find it, do not fight the wall.

## 1. Spot the second app, then read its runtime config

Look for a path that is *not* the legacy router: `/checkout`, `/app`, `/account-next`, `/portal`,
`/_app`, `/dashboard`, `/[locale]`— a 200 whose HTML has a different `data-*` root attribute,
different asset prefix, or `<script type="module" src="/…/_app/_nuxt/…">` is a separate deployment.

Both Nuxt and Next ship their server-side config in the HTML. Grep it before any probing:

```bash
curl -s "https://<host>/checkout" | grep -o 'window.__NUXT__.config=[^<]*' | head -c 4000
# Next: __NEXT_DATA__ / self.__next_f.push / process.env inlined
```

Real yield from one Nuxt config block:

* `openFetch.socialdeal.baseURL: "http://api.<brand>.internal"` — **internal DNS names for the whole
  service mesh** (`account-api.*.internal`, `customer-service-api.*.internal`). Recon intel, not a
  finding by itself, but it tells you which upstream owns which route, and it is the map for
  host-header / SSRF work.
* `csurf.headerName: "csrf-token"` — the CSRF header the API actually checks. Take it from
  `<meta name="csrf-token">` in the live DOM.
* `identity.cookieName: "guest_identity"`, `identity.headerName: "x-guest-identity"` — guest identity
  is a *cookie*, so a guest cart/identity is replayable without login.
* `adyen.clientKey` + `adyen.environment` — publishable key = public by design (**not a finding**),
  but `environment: "test"` inside a production config is a money-logic lead that can only be
  settled by completing a payment. Record the pair; do not report the key.

## 2. Mine the bundle for the API client, and the API client for the whole surface

Both frameworks keep one generated client object per upstream. Finding it hands you every endpoint
offline — no fuzzing:

```javascript
// Nuxt: {key:"getMember", value:… this.get("/member/") …}
{key:"loginRequest",value:… this.post("/login/",t)…}
{key:"activateMember",… this.post("/member/activate/",t)}
{key:"resendMemberActivation",… this.patch("/member/resend-activation/",t)}
{key:"patchMember",… this.patch("/member/",t)}
{key:"getAccount",… this.get("/accounts/".concat(e))}
{key:"patchAccountsBrowser",… this.patch("/accounts/browser",data)}
{key:"authLogin",… this.get("/auth/auto-login/",{params:data})}
{key:"getAcl",… this.get("/auth/acl/cache-busting/")}
```

Extract with a regex over `key:"<name>",value:` → next `this.(get|post|patch|put|delete)(` and the
literal path. That is the route table, the method, and the auth shape, in one pass.

**Then crawl the whole lazy-chunk graph** — entry scripts only cover the landing page:

```python
# Nuxt/rolldown: the runtime chunk holds the id → hash map
m = re.search(r'\{0:"21513df",.*?\}\[e\]\|\|e\)\+"\.js"', runtime_js, re.S)
pairs = re.findall(r'(\d+):"([0-9a-f]{7})"', m.group(0))     # 67 chunks on the sample
# fetch /_nuxt/<hash>.js for each; the auth page lived in chunk 21, not in any <script src>
```

Next.js App Router: same idea with `/checkout/_app/_nuxt/*.js` (or `/_next/static/chunks/*`)
breadth-first over `import("./X.js")` / `"./X.js"` edges, capped at ~120 chunks.

## 3. Register/login through the new app's API, not the old form

The Next app exposed a single JSON endpoint for both login and signup:

```
POST /_app/api/account/login
{"email":"<addr>","password":"<pw>","register":true,"remember_me":false}
-> 200 {"token":"eyJ…", …}          # + Set-Cookie session; no Turnstile, no captcha field
```

That answered 200 on the **first** attempt for an address the legacy form had just rejected, and the
resulting cookie jar was accepted by the legacy app (`/account/` rendered logged-in). Sequence that
works:

1. `GET /checkout` first (seeds `guest_identity` + `__Host-csrf`).
2. `POST /_app/api/account/login {…, "register": true}` → bearer `token` + cookies.
3. Send both `cookie:` **and** `Authorization: Bearer <token>`; add `csrf-token: <__Host-csrf>`.
4. Verify with a logged-in marker, then activate from mail (`/account/activeren/?code=…&ref=…` —
   the link is idempotent, a second visit answers "already activated").

`x-product-origin: socialdeal|travel` selects the storefront flavour; a wrong/absent value is often
tolerated, so probe both.

## 4. Apigility / Zend-style proxy with a header router

`/proxy/api/<path>` fronted an Apigility service whose upstream is chosen by **`X-Provider`**:

| provider value | answer |
|---|---|
| `inbox` | `200` JSON (`/presentation/messages/`, `…/unread-message-count/`, `/messages/`) |
| `loyalty` | `404 {"error":404,…}` for unknown routes, `200` for `/promotion/` |
| unknown (`admin`, `../../etc/passwd`, …) | **`500` generic HTML page** — no traversal, no leak |
| route needing a member | `403 {"code":403,"message":"Could not find member"}` |

So the provider list is enumerable (500 vs 200/404 is the discriminator), and each provider is a
separate route space to sweep. A 403 "Could not find member" means the route is real and gated —
that is a *route confirmed*, not a bypass.

## 5. Verdict rules that stop false positives here

* `/_app/api/platform/account/details/<id>` returning a **full record for your own id and `403`
  with `GET socialdeal/member/<id>/ → 403` for everyone else's** is *correct authz*. Do not report;
  record it as verified-negative with the denial string.
* `204 No Content` on `GET /_app/api/platform/cart` is "no cart yet", not an authz gap.
* A `checkout` config that leaks `*.internal` hostnames is infra/version disclosure — excluded by
  most policies as its own finding. Its value is as a map.
* Cart amount tampering on the legacy endpoint is clamped server-side (`0`, `-1`, `0.5` → silently
  reset to 1). Note that `items[0][amount]` is the shape the handler reads; `items[][amount]` alone
  is ignored.
* A `POST`-capable proxy that only *parses* a URL (`/proxy/deeplink/`) is not SSRF. Confirm by
  feeding `http://169.254.169.254/…`, `file:///etc/passwd` and reading whether anything is fetched
  (timing identical to the external case = pure parsing).
