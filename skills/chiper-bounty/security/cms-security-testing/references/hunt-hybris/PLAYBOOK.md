---
name: hunt-hybris
description: Use when the target runs SAP Commerce (Hybris) — OCC v2 REST surface (/rest/v2/{site}/...), ws-api/v1 cart, /medias, /hac, /backoffice, verbose Spring validation leaks, serial-voucher endpoints, and the safe way to probe create-* endpoints behind validation-before-auth.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, hybris, sap-commerce, occ, rest, ecommerce]
    related_skills: [hunt-business-logic, hunt-idor, hunt-csrf, bot-protected-target-testing, web2-vuln-classes]
---

# SAP Commerce (Hybris) hunting

SAP Commerce — still widely called Hybris — powers a large share of retail/e-commerce estates
(observed on target.com.au, 2026-09). This skill is the platform playbook: how to confirm the
platform, where its attack surface lives, what its controls usually look like, and how to probe
the dangerous endpoints without creating real business records.

## 1. Fingerprint in one request

Send a deliberately invalid identifier and read the error envelope — Hybris answers in a
distinct JSON shape (`{"errors":[{"message":...,"type":...}]}`):

| Probe | Signature response |
|-------|--------------------|
| `GET /rest/v2/{site}/products/1` | `400 "Product with code '1' not found!"` / `UnknownIdentifierError` |
| `GET /rest/v2/{site}/stores/1` | `400 "No PointOfService with name 1, type STORE found in baseStore {site}"` |
| anything unmapped | `404 "There is no resource for path /rest/v2/..."` / `UnknownResourceError` |
| `POST /rest/v2/{site}/vouchers` (empty) | `400 ValidationError` naming `de.hybris.platform.commercewebservicescommons.dto.voucher.VoucherWsDTO` and the tenant's own OCC extension |
| `/medias` | Hybris media servlet (returns a script/Akamai page when bot-managed) |
| `/hac`, `/backoffice` | 404 / admin consoles — if they answer, that is its own finding |

The `site` segment (base store id) is the first thing to learn; it appears in every path and in
error text. Storefront JS usually reveals it plus the OCC base URL.

## 2. Surface map

```
/rest/v2/{site}/users/current                     -> 401 "Full authentication is required..." if protected
/rest/v2/{site}/users/{id}[, /orders, /addresses, /paymentdetails, /carts, /vouchers]
/rest/v2/{site}/users/anonymous[/orders, /carts, /delivery/estimates/{code}, /nudge/...]
/rest/v2/{site}/orders/{code}                     -> guest order lookup; often edge-blocked
/rest/v2/{site}/products/{code} | /products/search?query=...
/rest/v2/{site}/stores/{name} | /stores/nearest/store/{n} | /stores/location/geo/{lat}/{lng}
/rest/v2/{site}/cms/pages[?slug=]                 -> CMS payload (can be very large; check for slots
                                                     that reference unpublished/non-public content)
/rest/v2/{site}/vouchers                          -> SERIAL VOUCHER GENERATION (write) — see §4
/rest/v2/{site}/{languages,currencies,deliverycountries,titles,application/constants}
/ws-api/v1/{site}/cart/{add,remove,update}        -> second cart API (usually carries _csrf)
/medias/...                                       -> media servlet (feeds, sitemaps, assets)
/status, /actuator/*, /hac, /backoffice           -> misc; record what actually answers
```
Micro-frontends on top of OCC each expose their own `/uir-*/api/*` routes (e.g.
`/uir-pdp/api/cart/add`). Two cart write paths with *different* protections is the normal state
here — mine both from the browser's own traffic instead of guessing paths.

## 3. Controls to expect (and how to record a negative)

- `users/*` → `401 {"message":"Full authentication is required to access this resource",
  "type":"UnauthorizedError"}` — correct, no user-enumeration oracle in the response.
- `users/anonymous/*` → `401 AccessDeniedError` (different message ⇒ the route exists but is
  closed). Do not read this as a leak.
- Order paths are frequently protected twice: an edge rule on `/orders*` (Akamai answered 403 for
  every case/`//`/encoded variant) plus app-level 401. Record the double protection.
- Header/method bypass matrix (X-Original-URL, X-Rewrite-URL, X-Forwarded-*, X-Custom-IP-
  Authorization, `Origin: null`, PUT/PATCH/OPTIONS) — expect uniform 401. A uniform answer is the
  evidence; keep it.
- Cart writes accept `application/json` and **reject CORS-simple content types** (text/plain,
  x-www-form-urlencoded → 400). That single fact is what usually kills the CSRF story: verify
  with the attacker-origin harness rather than reasoning (`hunt-csrf` template).
- Quantity handling: `0` and `-1` may produce a **500** (sloppy input handling, no stack trace →
  normally INFORMATIVE), while a large quantity may be silently capped and the cap re-enforced on
  repeat adds. Always test the REPEAT case before claiming a limit bypass.

## 4. Serial-voucher endpoints — probe safely, never mint

`POST /rest/v2/{site}/vouchers` maps to a controller like
`ExtendedVouchersController.createSerialVoucherCodes(TargetSerialVoucher, String)`. Observed
behaviour worth knowing before you touch it:

1. **Validation runs BEFORE authorization.** An invalid body returns 400 with the required
   parameters named; you will not see a 401 until the payload is valid.
2. Gate the format first: the demo target required `code` to match `^[A-Z0-9]{3}$` and a
   non-null `quantity`.
3. **Then use the inert-value probe**: send a format-valid code with `quantity: 0`. Zero makes a
   "generate N codes" call a no-op, so the test is decisive and side-effect free.
   Observed result: `401 Access is denied (AccessDeniedError)` ⇒ control holds, nothing minted.
4. Only consider `quantity >= 1` against a live base record with explicit operator sign-off and a
   plan for the record you are about to create. Minting real vouchers on a production system is a
   business side effect, not a test.
5. Residual risk to note in the report (not a finding by itself): a 3-character code space is
   36³ ≈ 46k. If any unauthenticated voucher *lookup* ever appears (`/vouchers/{code}`,
   `/users/current/vouchers` answered 401 here), enumeration becomes trivial — flag it as a
   design comment.

## 5. Information leaks that recur

Hybris/Spring verbose validation messages leak internal structure, e.g.
`de.hybris.platform.commercewebservicescommons.dto.voucher.VoucherWsDTO`,
`au.com.target.tgtcommerceocc.v2.controllers.ExtendedVouchersController.createSerialVoucherCodes(...)`,
`au.com.target.tgtfacades.voucher.data.TargetSerialVoucher`, plus full
`[Field error in object 'x' on field 'y': rejected value [z]; codes [NotNull...]]` blocks. Also
`"No valid solrFacetSearchConfig found for the current context"` on a mis-parameterised search.
Classify honestly as P5/informative (verbose errors) unless a program treats framework leakage as
in-scope — check the excluded/ineligible list first.

## 6. Workflow

1. Fingerprint (§1) + get the base-store id.
2. Harvest the real surface from storefront bundles and a CDP network capture — not from a
   wordlist (see `bot-protected-target-testing` when the estate is behind Akamai/Cloudflare).
3. Sweep the `/rest/v2/{site}/...` families for: public config (fine), 401-protected (record),
   404 (record), and anything that answers 200 with per-user data (chase it).
4. Cart: capture the site's own add-to-cart call, then run quantity/coupon/custom-field probes on
   that exact payload shape (`hunt-business-logic`).
5. Voucher and any other `create*/issue*` endpoint: validation-oracle first, inert-value probe
   second, real values only with sign-off.
6. Report with the coverage matrix: what answered, what was edge-blocked, what was left untested
   and why.

## 7. Pitfalls

- Native Windows tooling needs native paths (`D:\...`, `MSYS_NO_PATHCONV=1`), and non-browser
  HTTP clients are usually refused by the edge on these estates — drive tests from a real browser
  session and keep the 403 transcripts as the reason.
- `/cms/pages` and cart payloads can be hundreds of KB; raise response slices or the JSON parse
  fails and looks like a transport error.
- Two cart APIs (OCC `/rest/v2` vs front-end `/uir-*/api` vs `/ws-api/v1`) — an inconsistency in
  CSRF/token handling between them is a lead, not automatically a finding; prove reachability from
  an attacker origin.

## Support files

- `references/target-au-2026-09-transcript.md` — copy-exact fingerprint strings, the full
  reachable/blocked endpoint inventory, cart content-type gating table, quantity behaviour, the
  voucher probe ladder, and the CSRF/CORS/headers outcome from a real engagement.

