# Akamai-fronted estate: browser-driven audit recipe (Kmart Group VDP, 2026-09-29/30)

Scope: `kmart.com.au` + `target.com.au` (Bugcrowd VDP Pro "Kmart Group"). Both sit behind
Akamai Kona SiteDefender. This is the empirical record of what was blocked, what worked, and the
coverage-matrix format that satisfied the user's "sudah pakai semua tools?" challenge.

## 1. Tool coverage matrix (the honest report shape)

| Tool | Status | Evidence |
|------|--------|----------|
| curl | EDGE-BLOCKED | 403 on `/` and on every `/rest/v2/target/*` |
| nuclei | EDGE-BLOCKED | misconfiguration set, rate 2 → 0 findings, all requests 403 |
| ffuf | EDGE-BLOCKED | `-mc all` → 403 on admin/cart/rest/login/api (5/5) |
| dalfox | EDGE-BLOCKED | no output within timeout (edge refuses non-browser client) |
| wafw00f | RESULT | "Kona SiteDefender (Akamai) WAF" |
| subfinder | RESULT | 283 subdomains target.com.au, 201 kmart.com.au |
| dnsReaper | RESULT | 0 takeovers (283 domains × 61 signatures, 14 s) |
| gau | RESULT | 4228 historical URLs → surfaced `/track-order`, `/help/order-tracking`, `/delivery-postcode-tracker`, `/spc/order*`, `/p/*` |
| waybackurls | NO OUTPUT | 0 URLs (CDX unreachable from this host) — gau is the working historical source here |
| katana | NO OUTPUT | `-headless` downloads its own Chromium then yields 0 URLs behind the edge; the bundle-mining + CDP capture path replaced it |
| naabu/nmap | N/A | port scanning outside VDP scope (web-only program) |
| sqlmap/ghauri/commix/kxss/arjun/CORScanner/graphqlmap | EDGE-BLOCKED | same client class as the above |
| interactsh | N/A | no server-side-fetch candidate existed on either target |
| slither/echidna/medusa/mythril | N/A | no smart contracts in program |
| mitmproxy / ZAP | N/A | intercepting proxy = non-browser TLS → would be 403'd |
| browser + raw CDP | RESULT | all manual coverage below |

**EDGE-BLOCKED is provisional, not permanent.** The same `/ws-api/v1/...` POST that returned
`403 Access Denied` mid-session answered `200` after a Chrome restart (fresh Akamai score), and
after ~30 rapid POSTs the edge began 429ing requests that had worked minutes earlier. Re-test any
EDGE-BLOCKED endpoint in a fresh session before writing it off, and pace bursts.

## 2. Why the browser is the only transport

- `curl` with a full Chrome header set → 403; the block is TLS/JA3 + IP reputation, not headers.
- ISP IP (Indonesia) → 403 outright (geo/edge policy) on both hosts; Cloudflare WARP egress
  (104.28.x) → 200 on the storefront.
- The storefront's OWN XHRs to a challenged API also get `429 {"cpr_chlge":"true"}` — proof the
  block is egress/session level, not "our client is bad".
- Akamai CPR countermeasures that worked: `content-type: application/json;charset=UTF-8` for
  POST, and switching the operation to GET with a non-simple content-type header.
- After a burst (~30 POSTs) the edge starts 429ing requests that returned 200 minutes earlier.
  Restarting Chrome with the same profile cleared it; the control request went back to 200.
- XML content-type to the same API → 403 (the rule is content-type sensitive in both directions).

## 3. Technique stack that produced all real coverage

1. **In-page XHR over raw CDP** (Playwright's `connect_over_cdp` dies on this site's
   `blob:` shared worker; `cdp.py`-style websocket client is immune). Add an in-page `setTimeout`
   so a hanging resolver can never wedge the driver.
2. **Network capture** of the site's own traffic (CDP `Network.*`) → real endpoints, real
   payloads, real headers, plus the Akamai sensor POST (201 = our session is trusted).
3. **Bundle mining** for endpoint paths and GraphQL documents (`/uir-*/api/*`, `/rest/v2/...`,
   `/ws-api/v1/...`, operation names, `sha256Hash` persisted queries).
4. **Persisted-query (APQ) whitelist**: `/uir-bff/graphql?operationName=Product&extensions=
   {"persistedQuery":{"sha256Hash":...}}` — arbitrary documents return the app's 400 page, so
   only whitelisted operations are reachable.
5. **Error-shape oracle** (introspection off): required-argument messages, token format
   (`Hash must be exactly 64 characters`), `^[A-Z0-9]{3}$` on a voucher code, and verbose Spring
   validation leaks naming internal controllers/facades.
6. **Auth-bypass matrix**: 6 methods × 8 headers (X-Original-URL, X-Rewrite-URL, X-Forwarded-For,
   X-Custom-IP-Authorization, X-Forwarded-Host, X-Originating-IP, admin Referer, `Origin: null`)
   × path variants (trailing slash, `//`, `;x=1`, `%54`, dot-segment, case).
7. **Cross-origin proof harness** from a local attacker origin (CSRF + CORS): see
   `hunt-csrf/templates/attacker-origin-harness.html`.

## 4. Results (both targets) — for calibrating expectations

- kmart.com.au: GraphQL reachable after the CPR bypass; introspection disabled; `me` resolves
  unauthenticated; ~8 unauthenticated root fields mapped (incl. `address` → AddressLookup);
  cart negative/zero quantity rejected server-side; `setCustomField` allowlisted; foreign cart id
  → not found (`/me`-scoped). Login (Auth0 `/u/login/password`) refused by the edge for this
  egress even with human-like input → authenticated coverage = BLOCKED (needs AU residential
  egress or an operator-provided session).
- target.com.au (SAP Commerce): `users/*` 401, `orders*` 403 at the edge *and* 401 in-app,
  header/method bypass all 401, cart qty 0/-1 → 500 (no leak), cap 99 enforced (repeat-add does
  not exceed), CSRF not exploitable (endpoint accepts only `application/json`; cross-origin
  proof from a real attacker origin changed nothing), CORS not reflective, no open redirect on
  7 candidates, serial-voucher creation endpoint 401 after validation (tested safely with
  quantity 0). Zero reportable findings; P5 candidates only (verbose Hybris errors, missing
  CSP/Referrer-Policy/Permissions-Policy, a public `/status`, 500 on qty 0/-1).

## 5. Pitfalls that cost time

- MSYS paths: native Windows binaries (dnsReaper, ffuf, sqlmap) need `D:\...` paths, not
  `/d/...` — and `MSYS_NO_PATHCONV=1` for anything passed through bash.
- Port collisions: another agent session owned `127.0.0.1:8899`; the attacker-origin page
  loaded THEIR harness. Always curl the local page and confirm the title before trusting it.
- One shared debug Chrome gets hijacked: a tab being driven for target A ended up on target B's
  app mid-flow. One profile + one port per engagement, and verify the port is yours.
- Cart/JSON responses >75 KB truncated mid-parse look like transport failures; raise the slice
  or regex the field you need.

## 6. target.com.au surface map (SAP Commerce / Hybris) — the part that took longest to learn

Fingerprint (no scanner needed — the app tells you):
```
"no PointOfService with name 1, type STORE found in baseStore target"   <- Hybris OCC
"Product with code '1' not found!" (UnknownIdentifierError)
"No valid solrFacetSearchConfig found for the current context"
verbose Spring validation: de.hybris.platform...dto.voucher.VoucherWsDTO
   au.com.target.tgtcommerceocc.v2.controllers.ExtendedVouchersController.createSerialVoucherCodes(...)
```
Front-end families (each micro-frontend ships its own API — sweep them all):
```
/uir-pdp/api/{isLoggedIn, cart/get, cart/add}          product-detail micro-frontend (Next.js)
/uir-plp/api/{isLoggedIn, cart/get}                    product-list micro-frontend
/uir-bff/graphql?operationName=...&extensions=APQ      BFF; persisted-query whitelist only
/ws-api/v1/<site>/{cart, cart/add, session, trackOrder, env, json-cms/spc-content}
/rest/v2/<site>/{users/current, users/anonymous/*, products/<code>, stores/<id>, cms/pages,
                 languages, currencies, titles, deliverycountries, application/constants, vouchers}
/_ui/_assets/js/*.chunk.js   and   /static/<hash>/e/*.js     where the endpoint strings live
/spc/order                    the real checkout SPA route (robots.txt disallows /checkout/)
/medias/...                   Hybris media endpoint (public) · /status returns "OK"
```
Behaviour worth reusing as calibration:
- `/ws-api/v1/<site>/session` hands a guest a `csrfToken`; `/ws-api/v1/<site>/cart` (GET) returns
  the anonymous cart (subtotal included). Both 200 without login.
- Guest order lookup = `POST /ws-api/v1/<site>/trackOrder` with JSON `{orderId, email}`
  (form-encoded → **415**). Non-existent/mismatched order → generic failure message, i.e. NO
  enumeration oracle. Malformed email → field errors leaking the form object name
  (`orderSearchForm`) and validation keys. Empty body → 500.
- `/checkout` renders for a guest and calls `/ws-api/v1/<site>/{env, session, json-cms/spc-content}`;
  the 117 KB CMS payload contained no keys/secrets.
- Method matrix on guessed cart routes: PUT/PATCH → `405 {}` (route absent), DELETE → edge
  "Unsupported Request". The only real cart verbs are `GET /cart` and `POST /cart/add`.
- Voucher/promo code paths found in bundles (`/checkout/promotions/apply-voucher`, `apply-flybuys`,
  `redeem-flybuys`, `/cart/delivery/advantage-promo`) are SPA page routes, not APIs → direct
  fetch = 404/blocked.

## 7. Discovery techniques that produced the map above

1. **gau first** on a Hybris storefront: it surfaces the order-tracking / checkout / help routes
   that robots.txt hides (`/track-order`, `/help/order-tracking`, `/delivery-postcode-tracker`).
2. **Mine every same-origin chunk** for `"/[a-z-]+/api/..."`-shaped strings; that is how the
   `/uir-*/api/*` and `/ws-api/v1/*` families were found.
3. **Watch what a page calls on load** (CDP Network, all types) rather than guessing endpoints;
   the checkout page alone revealed `env`, `session`, `json-cms/spc-content`.
4. **Form-POST endpoints need special handling** — see §8.

## 8. Form POST / document-navigation endpoints are invisible to XHR capture

`/track-order` submits as a **document navigation**, so:
- an in-page `window.fetch`/`XHR` hook captures nothing,
- a CDP `Network.requestWillBeSent` listener filtered to `type in (XHR, Fetch)` captures nothing
  (look at `type == "Document"` instead),
- `Network.getResponseBody` for the navigation returns nothing useful (the HTML is already gone),
and the earlier run's only clue was a stray `200` for the endpoint URL with no matching request.

Workaround that works: **replicate the POST yourself** and read the body.
```
POST <endpoint>            # form-urlencoded first
  → 415 Unsupported Media Type  = the route exists and wants JSON
POST <endpoint>  application/json  {"orderId":"0000000000","email":"<test>"}
  → 200 {"success":false,"data":{"error":{"code":"ERROR_ORDER_TRACKING","message":"<generic>"}}}
```
Then vary ONE field at a time (unknown id / malformed email / empty body) to read the oracle and
the error-handling quality. Generic message for every unknown id = no enumeration oracle (a
control that works); 200-with-field-errors + object name = low-grade info disclosure; 500 on an
empty body = sloppy input handling. All three are calibration, not findings.
