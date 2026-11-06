# app-link files as a route oracle, and `.internal` hosts leaking through redirects

Two recon techniques that both cost one request and both pay on modern SPA estates. Measured on
Social Deal (www.socialdeal.nl, 2026-10-29), both in-scope, both reproducible.

## 1. `apple-app-site-association` / `assetlinks.json` is a self-declared sensitive-route map

```
GET /.well-known/apple-app-site-association      # 200 application/json
GET /.well-known/assetlinks.json                 # 200 application/json
```

Why bother: the AASA `components` list is the vendor telling Apple which paths the app should
**NOT** handle. That list is, by construction, the set of routes the company considers sensitive
or non-deep-linkable. It is an oracle for route names the JS bundle never contains.

Verbatim from the target:

```json
{"applinks":{"details":[{"appIDs":["9U84DV26B2.nl.socialdeal.app"],"components":[
  {"/":"/deal/preview/*","exclude":true},
  {"/":"/app/","exclude":true},
  {"/":"/samenwerking/*","exclude":true},
  {"/":"/samen/*","exclude":true},
  {"/":"/partners/mailing-list/*","exclude":true},
  {"/":"/onelogin-saml/","exclude":true},
  {"/":"/orderlist/*","exclude":true},
  {"/":"/cart/handleThreeD/*","exclude":true},
  {"/":"/account/auth/*","exclude":true},
  {"/":"/theme/*","exclude":true},
  {"/":"/*","comment":"Allow all other urls"}]}]}}
```

Read it for three things:

1. **Named routes to probe.** `/onelogin-saml/` (an SSO entry point), `/account/auth/*`,
   `/cart/handleThreeD/*` (3DS callback — payment state machine), `/deal/preview/*` (unpublished
   deal preview), `/theme/*`. All of these were absent from the SPA bundles.
2. **`"/*"` allow-all.** If the catch-all is present, every path on the domain is handed to the
   app. That converts a generic web bug (open redirect, host-header reflection, `.internal`
   redirect) into a **mobile-reachable** one, which is the difference between Low and Medium.
   Always state this when the program's scope includes iOS/Android — it is the amplifier.
3. **A route may be a different application.** `/theme/*` returned a 741 KB Nuxt app whose
   `_nuxt/` chunks resolved under **`/inspirations/`** — i.e. one URL prefix silently serves the
   inspirations app. Re-parse `_nuxt/` paths from the HTML rather than assuming they are
   `/theme/_nuxt/`.

`assetlinks.json` gives the Android package + cert fingerprints:
`app.nl.socialdeal` with two SHA-256 fingerprints (a live one and a second, typically upload-key).
Compare the package against the program's published Android asset name.

## 2. `.internal` hostnames leaked in `Location` headers

Detection is two requests. Any path that 301s to a hostname you cannot resolve is worth capturing:

```
curl -sS -D - -o /dev/null https://<host>/<app>/api-socialdeal
-> HTTP/1.1 301
   location: http://api.socialdeal.internal/inspirations/api-socialdeal/

curl -sS -D - -o /dev/null https://<host>/<app>/api-availability
-> HTTP/1.1 301
   location: http://availability.socialdeal.internal/inspirations/api-availability/
```

### The discriminator that makes it a misconfig, not app routing

Re-request the same path **with a trailing slash**:

| request | response | meaning |
|---|---|---|
| `/inspirations/api-socialdeal` | `301 → http://api.socialdeal.internal/...` | upstream mapping emits the internal target |
| `/inspirations/api-socialdeal/` | `302 → https://www.socialdeal.nl` | the app itself redirects, and it redirects to the PUBLIC host |

Opposite schemes and opposite hosts across the two variants proves the 301 is produced by the
proxy/upstream rule and not by application code. Without this pair, the finding is arguable;
with it, it is mechanical.

### Header-injection tests you must run before claiming anything bigger

- `X-Forwarded-Host: evil.test` → still the same `.internal` target (not attacker-controlled)
- `Host: evil.test` → **403** (vhost allowlist) — so no host-header poisoning here
- `X-Original-Host: evil.test` → same `.internal` target

Record all three. The 403 on `Host:` is itself the honest bound on the finding.

Note the separate, unrelated response worth knowing: sending `Host: <anything>` to a *whitelabel*
front end returned `200 "Bedankt. Het domein is nu gekoppeld."` from `awselb/2.0` — a domain-binding
feature answering success for every unknown host. Impactless alone, but it means a bare 200 there
is not evidence of anything.

## 3. Public framework config blocks name internal services too

The Nuxt/Next hydration payload is a config dump delivered to every anonymous visitor:

```bash
curl -s https://<host>/checkout | python -c "import sys;h=sys.stdin.read();i=h.find('window.__NUXT__.config')
print(h[i:h.find('</script>',i)])"
```

Verbatim excerpt:

```js
window.__NUXT__.config={public:{
  identity:{cookieName:"guest_identity",headerName:"x-guest-identity"},
  adyen:{clientKey:"test_XYHG...",environment:"test",applePayMerchantId:"merchant.nl.adyen.socialdeal.test"},
  sentry:{enabled:true,dsn:"https://...@o4510856491106304.ingest.de.sentry.io/...",release:"7cdd78082fa",dist:"39"},
  csurf:{headerName:"csurf-token"},
  openFetch:{ socialdeal:{baseURL:"http://api.socialdeal.internal"},
              customerService:{baseURL:"http://customer-service-api.socialdeal.internal"},
              account:{baseURL:"http://account-api.socialdeal.internal"} }
}}
```

Triage it correctly — this is where overclaiming happens:

| value | verdict |
|---|---|
| `api.*.internal`, `account-api.*.internal`, `customer-service-api.*.internal` | internal topology disclosure (same class as the `.internal` Location leak) |
| Sentry `dsn`, `release`, `dist` | **public by design** — DSNs ship to browsers. Not a finding. |
| Adyen/Stripe *publishable* `clientKey` / `pk_` | public by design on its own |
| `environment:"test"` on a **live** checkout | worth a look, but only a finding if you show a test-mode payment settling a real order — do not report the string alone |

Also expect a build fingerprint (`release:"7cdd78082fa", dist:"39"`) — usable to confirm the same
build across hosts, and to date a deployment.

## 4. Reporting this class honestly

Programs almost universally exclude "banner grabbing / version disclosure" and "verbose messages
without sensitive information". A `.internal` hostname in a header will be read as that unless you
argue the difference:

- it is not passive metadata but an **instruction to the client** (the client is told to fetch it);
- the scheme is `http://` on a host the public cannot resolve → a logged **downgrade / failed fetch**
  for any client that follows redirects, including the in-scope mobile apps that claim the path;
- it hands over the internal **service layout** (`api.`, `availability.`, `account-api.`,
  `customer-service-api.`) mapped per public path.

And state the bound in the report body, unprompted: no internal body, no credential, no customer
data, no SSRF achieved. Shipping this as "Low / informational, here is the recon value and the
downgrade" is defensible; inflating it to High because the word "internal" appears is how the
report gets closed as invalid.

Remediation wording that actually maps to the defect: answer the no-slash request internally or
with a same-host `https://` redirect; never place an intermediary hostname in a `Location`;
if an internal hop is required, proxy it server-side instead of redirecting.
