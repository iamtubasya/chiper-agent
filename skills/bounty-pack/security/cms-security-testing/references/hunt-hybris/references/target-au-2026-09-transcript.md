# Observed transcript — target.com.au (Kmart Group VDP), 2026-09-30

Raw evidence behind `hunt-hybris` §1–§5. All requests came from a real Chrome session (the estate
is Akamai-fronted; curl/nuclei/ffuf were 403 — see
`bug-bounty-exhaustive-testing/references/akamai-estate-browser-driven-audit.md`).

## Fingerprint strings (copy-exact)

```
GET /rest/v2/target/products/1
 -> 400 {"errors":[{"message":"Product with code '1' not found!","type":"UnknownIdentifierError"}]}

GET /rest/v2/target/stores/1
 -> 400 {"errors":[{"message":"No PointOfService with name 1, type STORE found in baseStore target",
                    "type":"UnknownIdentifierError"}]}

GET /rest/v2/target/products/search?query=*&pageSize=1
 -> 400 {"errors":[{"message":"No valid solrFacetSearchConfig found for the current context",
                    "type":"..."}]}

GET /rest/v2/target/basesites
 -> 404 {"errors":[{"message":"There is no resource for path /rest/v2/target/basesites",
                    "type":"UnknownResourceError"}]}
```
base store id = `target`; OCC path prefix = `/rest/v2/target/`.

## Endpoint inventory actually reachable (guest)

```
200  /rest/v2/target/languages | currencies | deliverycountries | titles
200  /rest/v2/target/application/constants            (5 UI keys, nothing sensitive)
200  /rest/v2/target/cms/pages                         (727 KB CMS JSON, uid "homepage")
200  /status                                           ("OK")
200  /uir-plp/api/isLoggedIn | /uir-pdp/api/isLoggedIn ({"isLoggedIn":false})
200  /uir-plp|uir-pdp/api/cart/get                     ({}) and cartWsDTO after an add
200  /advantage/customer/getinfo                       (guest state; leaks resend URL only)
200  api.target.com.au/lz3inventory/stockStatus/{code}?modes=HD&postcode=2020&storeNumber=5121
200  /ws-api/v1/target/cart/add                        (only from the site's own XHR; carries _csrf)
401  /rest/v2/target/users/current{,/orders,/addresses,/paymentdetails,/carts,/cart}
401  /rest/v2/target/users/anonymous{,/orders,/carts}  ("Access is denied", AccessDeniedError)
401  /rest/v2/target/vouchers/{code}                   ("Access is denied")
403  every /rest/v2/target/orders* variant (edge: /orders/, /orders, /orders/X, /ORDERS/, //orders/,
     /orders/%54EST) — case-insensitive, path-normalised, not bypassable
404  /hac, /backoffice, /actuator{,/env,/health}, /server-status, /deployments,
     /v2/swagger-ui.html, /rest/v2/target/swagger-ui.html, /rest/v2/target/cart{,/entries}
405  /rest/v2/target/vouchers (GET) → "Request method 'GET' not supported" (endpoint exists)
```

## Cart write path (captured from the storefront itself)

```
POST /uir-pdp/api/cart/add
     {"productCode":"62835534","quantity":1,"postCode":2020,"storeCode":"5121"}   -> 200
POST /ws-api/v1/target/cart/add
     {"products":[{"productCode":"65618479","quantity":1}],"_csrf":"<uuid-in-body>"} -> 200
```
Content-type gating on `/uir-pdp/api/cart/add` (asserted by the app, not the edge):
```
application/json (+;charset=UTF-8)  -> 200
application/json                    -> 200
text/plain + JSON body              -> 400
application/x-www-form-urlencoded   -> 400
application/xml (+XML body)         -> 403 (edge)
```
Quantity behaviour: `0` → 500 "Hmm... That's not supposed to happen" (no stack trace in the body);
`-1` → 500; `999` → 200 and the cart settles at 99; adding 99 again does NOT exceed 99.
Foreign cart UUID via the front-end mutation → 404 / scoped to `/me`.

## Voucher endpoint ladder (the safe-probe shape)

```
POST /rest/v2/target/vouchers {"code":"ZZ-AUDIT-NO-SUCH-BASE","quantity":0}
 -> 400 ValidationError, code must match ^[A-Z0-9]{3}$
    (+ leaked controller: au.com.target.tgtcommerceocc.v2.controllers.ExtendedVouchersController
     .createSerialVoucherCodes(TargetSerialVoucher, String))
POST {"voucherId":...} / {"voucherCode":...}      -> 400 code must not be null  (field is `code`)
POST {"code":"ZZ9","quantity":0}                  -> 401 Access is denied  ← control holds
POST {"code":"000","quantity":0}                  -> 401 Access is denied
POST {"code":"ZZ9"}                               -> 400 only `quantity` missing
```
No voucher was ever created (quantity 0 throughout).

## CSRF / CORS outcome on this target

- `targetAnonymousToken` cookie: `Secure + HttpOnly + SameSite=None` ⇒ would travel cross-site.
- From a real attacker origin: JSON fetch → `TypeError: Failed to fetch` (preflight denied);
  no-cors text/plain → sent but the app 400s that content type; form `enctype=text/plain` → same.
- Cart quantity 105 before → 105 after ⇒ no state change.
- CORS probe against 4 endpoints from the attacker origin → all blocked (no ACAO reflection).
- Open redirect: 7 candidates from robots.txt + auth entry points → none left the origin.

## Header posture

`X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`,
`Strict-Transport-Security: max-age=31536000; includeSubDomains` present;
`Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy` absent (P5).
