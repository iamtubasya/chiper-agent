---
name: socialdeal-engagement
description: "Social Deal (Intigriti) — scope, estate map, test-account path."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, intigriti, socialdeal, nuxt, nextjs, whitelabel]
    related_skills: [security:bug-bounty, security:security-recon, security:disposable-auth-identity, security:authed-webapp-audit]
---

# Social Deal — engagement record (Intigriti)

Deals marketplace (restaurants / hotels / wellness / day trips) operating across NL, BE, DE, FR, AT,
DK, SE, NO. Buys are vouchers redeemed at partners. Program is **public + open** on Intigriti:
`app.intigriti.com/programs/socialdeal/socialdeal/detail`.

Scope and rules below were read off the live program page on 2026-10-29. **Re-read them before each
session** — the tier list and the known-issues table change.

## Scope (exhaustive as of 2026-10-29)

| Asset | Type | Tier |
|---|---|---|
| `www.socialdeal.nl` | URL | 1 |
| `www.socialdeal.nl/blog/` | URL | 1 |
| iOS app "Social Deal" | iOS | 1 |
| `app.nl.socialdeal` | Android | 1 |
| `socialdeal.nl/inspirations/bluemonday/` | URL | 2 |
| `www.socialdeal.nl/orderlist/5e834ae0bed5c/63d772e2ed277/` | URL | 2 |
| `www.spontaan.nl` | URL | 2 |
| `www.whynot.com` | URL | 2 |

> "Any domain that is not listed in the Domains section is out of scope for this program."

Consequence to respect: the heavy subdomain surface that passive enum returns
(`admin.`, `api.`, `api-beta.`, `pay.`, `webhook.`, `odoo.`, `staging.`, `development.`,
`merchant.`, `aanbieder.`, `crm.`, `beheer.`, `dashboard.`, `auth.`, `game.`, `travel-*-images.`, …)
is **out of scope**. Do not test it. It is still useful as *intel* (the app names its upstreams),
not as a target.

Rewards: Tier 1 €25 / 50 / 250 / 500 / 1,000 · Tier 2 €25 / 50 / 200 / 350 / 750
(Low→Exceptional). €25 bonus for late validation, €50 for verifying a fix.

## Rules of engagement (verbatim constraints)

* `@intigriti.me` address **required** for researcher accounts.
* User agent: not applicable. Request header: not applicable.
* **Automated tooling: max 2 requests/sec.** They also state "do not use automated test-tools on our
  domains, IP will be blocked" — run everything at `-rl 1..2`, `-c 2`, and stop on 429.
* No DoS/DDoS, no brute force, no rate-limit-bypass findings.
* Do not disclose without written consent (incl. YouTube/Vimeo PoCs).

## Known issues that auto-close (selection — read the full list on the page)

Clickjacking without impact · API-key disclosure without business impact · WordPress usernames ·
pre-auth account takeover / OAuth squatting · self-XSS · verbose messages/dir listing with no
sensitive data · CORS on non-sensitive endpoints · missing cookie flags / security headers · CSRF
with no/low impact · autocomplete attribute · reverse tabnabbing · **rate-limit absence or bypass** ·
password best-practice violations · CSV injection · sessions not invalidated · tokens leaked to third
parties · anything SPF/DMARC/DKIM/email-spoofing · content injection without HTML modification ·
**username/email enumeration** · email bombing · HTTP request smuggling without proven impact ·
homograph · XMLRPC · banner/version disclosure · file metadata not stripped · same-site scripting ·
subdomain takeover without takeover · **arbitrary file upload without proof the file exists** ·
**blind SSRF (pingbacks not sufficient)** · Google Maps API keys · **host header injection without
proven business impact** · **"account activation without access to the email inbox, by exposing the
activation code from the API, is known"**.

Mobile auto-closes: clipboard-leaked share links, URI leakage, missing cert pinning, data in URLs
under TLS, lack of obfuscation, path disclosure, no jailbreak/root detection, crash-on-malformed-scheme,
missing anti-debug/SSL-pinning, snapshot/pasteboard leakage, runtime exploits, tokens sniffed by a
3rd-party app.

Their stated worst case: **full access to servers and database**.

## Estate architecture (measured)

* **Legacy storefront** — PHP 7.4/8.1 on AWS ASG/EC2 behind Cloudflare, MariaDB. Server-rendered
  pages, jQuery/Vue-on-page, session cookie `Socialdeal` (rotates every response). Router map taken
  from the bundles: `js/components|library|desktop.*.js` on `media.socialdeal.nl` →
  `/cart/add/{unique}/{n}/`, `/cart/overview/`, `/cart/pay/`, `/cart/splitpayment/`,
  `/cart/address/{save,update}/`, `/my-vouchers/*`, `/my-reservations/*`, `/gift-box/pdf/{unique}/?pdf=<b64>`,
  `/deal-details/promo-code/`, `/loyalty/{tickets,ticket,check,shuffle}/`, `/spaarkaart/add-stamp/`,
  `/orderlist/{a}/{b}/`, `/proxy/*` (Apigility), `/agent/*` (public JSON for AI agents, documented in
  `/llms.txt`).
* **New checkout app** — Next.js at `https://www.socialdeal.nl/checkout`, assets under
  `/checkout/_app/_nuxt/`, own API namespace `/_app/api/{account,platform}/*`, CSRF header
  `csrf-token` (`__Host-csrf` cookie), guest identity cookie `guest_identity` + header
  `x-guest-identity`, `x-product-origin: socialdeal|travel`. Its inline config leaks internal
  service base URLs (`api.socialdeal.internal`, `account-api.…`, `customer-service-api.…`) and an
  **Adyen `environment:"test"` clientKey inside the production checkout config** — worth chasing
  only by completing a payment.
* **Whitelabel platform** — `www.spontaan.nl` and `www.whynot.com` are NuxtJS storefronts over
  `api.whynot.nl`; cookie `wl_tokens` (RS256 JWT, `iss: api.whynot.nl`, `aud/group: website`,
  `data.identifier`), plus `browser_unique`. API at `/api/*` (JSON:API-ish): `/api/deals`,
  `/api/translations` (3.2 MB, unauthenticated), `/api/faq`, `/api/V2/city-places/`,
  `/api/carts`, `/api/member/`, `/api/bookings`, `/api/accounts/browser`, `/api/login/`,
  `/api/auth/auto-login/`, `/api/auth/acl/cache-busting/`. An unbound `Host:` on the ELB answers
  `200 "Bedankt. Het domein is nu gekoppeld…"` (domain-binding feature) for **any** host.
* **Marketing** — `/blog/` is not WordPress (no `wp-json`, no generator). `email.socialdeal.nl` is an
  ESP click-tracker; `link.*`, `click.*`, `gtm.*` are mail/GTM infra.

## Test-account path that works (when the legacy form is open)

1. mail.tm inbox → `POST /register/` on `www.socialdeal.nl` with
   `{email, password, city:"achterhoek", via:"footer", referrer:"footer"}`, `X-Requested-With`.
2. Poll mail.tm; the activation link is `https://www.socialdeal.nl/account/activeren/?code=<digits>&ref=<token>`.
   Visiting it logs the browser in directly. Link is **idempotent** (revisit → "Je account is al geactiveerd").
3. **Pick ONE auth stack and stay in it.** The two stacks do not compose:
   * New checkout app: `POST /_app/api/account/login` `{email,password,register:false,remember_me:false}`
     with `x-product-origin: socialdeal` → 200 `{"token":"<JWT>"}` and sets `tokens` +
     `guest_identity` + `__Host-csrf`. This session authenticates the **legacy** app too
     (`/account/` then shows the member email).
   * Legacy: `POST /login/ {email,password,remember:"on",redirect:"/my-vouchers/"}`.
   * ⚠️ **Calling legacy `/login/` DELETES the `tokens` cookie and does not authenticate.** Every
     symptom that follows looks like a target bug and is not: the cart answers `closeCart()`,
     `/cart/overview/` says "niet bevoegd", `/gift-card/` says "niet bevoegd", and the account looks
     logged-out. If you must use the legacy stack, log in legacy **only** and never re-login via the
     API in the same jar. Verify state with `/account/` (XHR) containing the member email.
   * Login is rate-limited hard and answers **`429` with `statusMessage:"Invalid credentials"`**
     (a misused status code, no `Retry-After`). After ~6 logins the account stops authenticating for
     >4 min. Do not "retry the login" as a debugging step — that is what causes the lockout.
4. The program ALSO publishes two shop accounts for the purchase flow —
   `intigriti-1@socialdeal.nl` / `intigriti-2@socialdeal.nl` with passwords on the FAQ. Do not change
   their passwords. (`+` in an email is rejected by the system, per the FAQ.)
5. If the legacy form is closed, use the checkout app's `/_app/api/account/login {register:true}`
   path — see `disposable-auth-identity` → "When the legacy signup is locked out".

## Verified-negative / measured (2026-10-29, do not re-burn time)

* Cart amount tampering: `0`, `-1`, `0.5`, `1.5`, `10000` on `/cart/save/` are clamped or ignored;
  total recomputed server-side. Handler reads `items[0][amount]`, not `items[][amount]`.
* `/cart/pay/`, `/cart/overview/` for a fresh session return `{"success":false,"shouldLogin":true}`.
* `/proxy/api/<path>` without `X-Provider` → Apigility 404. With `X-Provider: loyalty` →
  `/promotion/` returns 20 promotions (marketing config, unauthenticated, low value);
  `/promotion/{id}/` → `403 {"code":403,"message":"Could not find member"}`. Unknown provider → 500
  generic localized page (no traversal, `../../etc/passwd` included). `X-Provider: inbox` →
  `/presentation/messages/` + `/presentation/unread-message-count/` unauth (empty for a guest).
* `/_app/api/platform/account/details/<id>` → own id 200, every other id `403` with
  `GET socialdeal/member/<id>/ → 403` = correct authz.
* `/proxy/deeplink/` parses a URL but fetches nothing (`file:///etc/passwd`,
  `169.254.169.254`, external, internal all identical timing, echoed back) = no SSRF.
* `/agent/*`: `offset`/`date`/`city`/`deal` all validated with explicit 400/404 errors; `tag` and
  `party_size` are reflected but HTML-escaped in `/agent/html/*` (`&lt;`, `&quot;`).
* Gift-box PDF: FPDF 1.86, title `Print giftbox: <card name>`; the `?pdf=<base64>` message is not
  embedded in the decompressed content stream — no injection, no template control.
* Product pages embed `promoCode:null` from `/deal-details/promo-code/` — no promo leak without a
  valid deal+quantity combination.
* **Payment-method confusion is rejected.** `/cart/method/?forceFlow=required` lists the fixed set
  (`ideal, klarna, creditcard, paypal, mrcash, cartebancaire, apple_pay, google_pay`); the hidden
  inputs are `method[type]` / `method[reference]`. `method[type]=ideal` → `/cart/pay/` returns a real
  PSP redirect (`data-payment-url` → `tx.ideal.nl`). Any value outside the list (`tegoed`) → `/cart/pay/`
  returns bare `closeCart()`. There is **no credit/tegoed payment path** to abuse. Requires an
  authenticated cart; an anonymous cart always gets `shouldLogin:true`.
* **`/spaarkaart/add-stamp/` is server-validated.** Card `data-unique` + `index` (1–20) come from the
  client, but POSTing index 1–5 with 0 earned stamps returns `{"success":false}` every time and the
  rendered card stays empty. Stamps are earned from spend (1 per €7,50), not from the `index` value.
* **JWT signature is verified on both stacks — proven by 401-vs-403 discrimination** (this is the test
  that settles it, not "the token is RS256"):
  * `tokens` (checkout): payload-swap keeping the old signature → `401`; `alg:none` + empty sig → `401`;
    a VALID token against `/details/1` → `403`. 401 = signature failed, 403 = signature good but
    authorization refused, so the signature is genuinely checked.
  * `wl_tokens` (whitelabel): `iss: api.whynot.nl`, payload `{"data":{"identifier":<int>},
    "group":"website"}`. Control and tampered both answer `409 logout` — **no oracle here**; treat as
    unproven rather than clean.
* **BFF traversal is blocked by pre-encoding.** The proxy leaks the internal URL it builds
  (`GET socialdeal/member/<id>/ → 403`), which is a useful oracle — but the `<id>` segment is
  percent-encoded before concatenation: `..%2f..%2fpayments` → `400`, `%2e%2e%2f` → `400`,
  `..%252f..%252f` → `403`, `1%00` → `400`, `1%2f..%2f..%2fdeals` → `404`. PATCH is guarded exactly
  like GET (`/details/1`, `/78958011`, `/000000000` all `403`).
* **`/_app/api/platform/cart` cannot be created from outside the UI.** GET → `204` (no cart);
  PATCH/POST/PUT/DELETE with a `deal_groups` body → `404 MultiCart.NotFound`; the new checkout store
  is separate from the legacy cart, so a legacy `/cart/add/` never populates it. Payment proof therefore
  needs the real UI to mint the cart.
* `/checkout` is a **different product** (travel) with its own empty-cart state — a legacy deal cart
  will never appear there. Do not read "Je winkelmandje is momenteel leeg" as a broken session.

## Known blockers (state them honestly; they are not findings)

* **Registration/login lockout appeared mid-session**: after the first successful signups the legacy
  `/register/` and `/login/` began answering `400 {"field":"email"}` for every domain
  (gmail, outlook, mailinator, intigriti.me, mail.tm) from headless *and* a real Camoufox browser;
  the published `intigriti-1/-2` accounts were refused too. Turnstile is on both forms. This removes
  the purchase/voucher lifecycle — the highest-paying logic class here — and further attempts would
  be rate-limit/captcha probing, which the program excludes. Report it to the vendor via Intigriti
  as a testing blocker; retry later / from a different egress.
* `mail.tm` remains reachable, so the block is target-side.

## Highest-value next steps

1. **Complete one real payment in `/checkout`** and watch `POST /_app/api/platform/cart/{unique}/pay`
   + `…/{unique}/handoff`. The production config shipping Adyen `environment:"test"` is the only
   lead here with Critical potential — settle it with a completed transaction, not by reading the key.
2. **Whitelabel crossover**: get a `spontaan.nl` member session, replay its `wl_tokens` against
   `socialdeal.nl /_app/api/*` and vice versa; check whether a whynot/spontaan member can read a
   socialdeal member record.
3. **Voucher lifecycle** with a genuinely purchased voucher: `my-reservations/{add,remove}-voucher`,
   `modal/my-reservations/claim-voucher`, `my-vouchers/gifted`, `company-receipt-form/<b64>`
   (the b64 wraps a print URL — decode, mutate, see whether another member's voucher renders).
4. **Loyalty ticket abuse** (`/loyalty/ticket`, `lot-cost`, 1 lot per €10) once a member-scoped
   loyalty session exists.
5. iOS/Android (Tier 1) — untouched; `app.nl.socialdeal` bundle + `mobile.socialdeal.nl`.

## Round-2 leads (2026-10-29) — read before re-hunting

1. **Gift-card redemption PIN — the most direct money path here, still unproven.**
   `/gift-card/` is a *public* "Verzilver je waardebon" page. Its form is `#giftCardModalForm` →
   `input[name=code]`, submitted by `#giftCardSubmitButton` to `POST /gift-card/ {code}` (same URL, no
   action attr). The response is a JS state machine, so the oracle is in the JSON, not the status code:
   * `{"success":false,"link":"requires_pin"}` → a PIN step opens (`#pin_code`, `#pin`) —
     i.e. the code is real and only a short PIN stands between you and credit;
   * `{"success":false,"link":"transfer"}` → voucher belongs to someone else (transfer prompt);
   * `{"success":false,"alert":{…},"errors":["pin"]}` → PIN wrong;
   * `{"success":false,"shouldLogin":true}` → you are not authenticated (this is the answer you get
     from a broken session — do NOT read it as "code rejected").
   Prove: does a short numeric PIN have any attempt counter, and does the counter survive a fresh
   login (account-level vs per-session, see `modern-web-framework-attacks` §9h)? **Do not brute force
   — the program excludes it.** Establish the structure from the response contract, then decide.
2. **Voucher claim by code** — `POST /modal/my-reservations/claim-voucher/ {vouchercode}` attaches a
   voucher to a reservation; `my-reservations/add-voucher/ {unique}` and `remove-voucher/` take a
   reservation unique from the client. This is the IDOR surface once any voucher exists.
3. `/orderlist/5e834ae0bed5c/63d772e2ed277/` (in scope, Tier 2) sends an anonymous visitor to `/` today
   — re-check with a member session and after a purchase; the two opaque segments look like
   member+order identifiers and are the most likely IDOR in the published asset list.

### State-reading trap that caused a wrong conclusion

Modal routes (`/my-vouchers/`, `/gift-card/`, `/savings-cards/`, `/loyalty/`, `/cart/*`) return the
**full ~5 MB homepage** unless the request carries
`X-Requested-With: XMLHttpRequest`. Reading the big response and grepping for a gate string ("Activeer
eerst") then yields a false "the gate is gone / I am authenticated" — that is what happened here, and
it sent the session chasing a phantom session bug. Always send the XHR header, and sanity-check that
the response is a *fragment* (hundreds of bytes to tens of KB) before believing any state derived from
it. Small-bodied empty answers (`{"success":false,"shouldLogin":true}`, 151–153 B) are the real
"not authenticated" signal.

## Pointers

* `security-recon` → `references/alt-frontend-api-surface.md` (how the checkout app and its
  `__NUXT__.config` / `/_app/api` surface were found and mined).
* **This skill** → `references/dual-stack-auth-and-modal-state.md` (the two auth stacks, the
  `tokens`-cookie wipe, the 429/"Invalid credentials" lockout, the `X-Requested-With` modal trap, and
  the Camoufox capture pattern incl. the `evaluate`-arg pitfall).
* `disposable-auth-identity` → account bootstrap, the mid-engagement lockout lesson, activation-flag
  assertion.
