# Aghanim (DTC payments / liveops for mobile games) — 2026-10-27 engagement notes

Vendor: Aghanim Inc. Contact `bugbounty@aghanim.com`. Policy `support.aghanim.com/bounty-program`
(v2026-08-24). Rewards Critical $1250 / High $550 / Med $250 / Low $50, paid after fix.
Outcome: **no reportable finding**; the value here is the verified-negative matrix, the exclusion traps,
and the two credential gates that bound the coverage.

---

## 1. The host the operator named was OUT OF SCOPE

Operator said `support.aghanim.com`. That host is **Helpjuice SaaS** (response headers
`Server: Heroku`, `Via: heroku-router, cloudfront`, NEL `report_to: heroku-nel`, cookie
`_helpjuice_session_v4`) → policy §4.3.1 "third-party services … not owned by Aghanim".

The real scope came from **`https://<apex>/.well-known/security.txt`**, which is the first thing to fetch
on any engagement:

```
Contact: mailto:bugbounty@aghanim.com
Contact: https://support.aghanim.com/bounty-program      <- policy lives on the OOS helpdesk
Policy: https://support.aghanim.com/bounty-program
Expires: 2026-12-31T23:59:59.000Z
```

So the named host can be both *the policy host* and *out of scope*. Confirm from the policy text, and say
so in the first paragraph of the deliverable — auditing a SaaS helpdesk for 3 hours would have been wasted.

Declared in-scope hosts: `aghanim.com`, `api`, `dashboard`, `dashboard-api`, `events`, `events-web`,
`hub-api`, `hub-api-global`, `my`, `my-api`, `pay`, `pay-api`, `s2s-api`, `sdk-api`, `upload`,
`*.aghanim.app`, and `api|pay-api|my-api|hub-api.aghanim.store`, plus the Android/Unity SDKs.

## 2. Exclusion traps that kill whole classes here (read before hunting)

| policy | consequence |
|---|---|
| §4.2.14 | no findings based on **guessing/enumerating identifiers** (order IDs, user IDs) → use junk placeholders, never a guessed real id |
| §4.2.5 | client-embedded PSP keys (Adyen `live_…`, Ebanx `live_pk_…`) are explicitly **not** findings — they appear in `/ps/` responses by design |
| §4.4.2 | **test-mode payment behaviour that does not affect live mode** is out → every sandbox observation needs a live equivalent |
| §4.4.4 | self-funded transactions / self-referral / own-account manipulation out unless it hits other players or financial integrity |
| §4.4.6 | **"login by Player ID" and "composite authorization" are declared by-design** — the Hub `authorize_user_id` flow is NOT a finding no matter how loose it looks |
| §4.1.6 / §4.1.4 | no aggressive scanning; no brute force on auth |

§4.4.6 is the expensive one: it pre-kills the most obvious-looking behaviour on the whole Hub API.

## 3. Estate map (what actually answers)

| host | stack | notes |
|---|---|---|
| `pay.aghanim.com` | React Router SPA + WAF | checkout UI; robots `Disallow: /` |
| `pay-api.aghanim.com` | **Go** (chi/echo: `404 page not found`, `/health` exposes `Alloc/NumGC/TotalAlloc`) | **order + payment-session core** |
| `my-api.aghanim.com` | FastAPI (`{"detail": …}`) | player accounts, users/me, reward points |
| `api.aghanim.com` | FastAPI | `/s2s/v1/*` (179 OpenAPI ops), `/hub/v1/websites/{slug}/*` |
| `hub-api(-global).aghanim.com` | same FastAPI app | hub reads |
| `dashboard-api.aghanim.com` | FastAPI under `/dashboard` prefix | 382 admin routes |
| `dashboard.aghanim.com` | Vite SPA, **13.5 MB** `assets/index-*.js` | the route oracle |
| `upload.aghanim.com` | worker, JSON error envelope | `/upload` + `/ingest` (`{url,bucket,file_type}` = **SSRF primitive**) |
| `events(-web).aghanim.com` | Go | `events-web` answers `pong` to **every** path (health probe) |
| `*.hub.aghanim.store` | 4 live game hubs | `criticalstrike`, `skullgirls`, `polygunarena`, `daysafter`; others = Gcore 404 |

Extra doc gold: **`https://docs.aghanim.com/openapi.json`** — a full 1.1 MB OpenAPI 3.1 spec
(`Aghanim Server-to-Server API`, 97 paths / 179 operations, **every** operation `HTTPBearer`, zero
no-security operations). Docusaurus sites frequently expose the spec at the docs root like this; try it
before crawling.

## 4. Verified-negative matrix (all of these were probed, all held)

Authz:
- Tenant sweep: 352 tenant-scoped dashboard routes × victim `com_`/`gm_` ids → **240× 403**, 97× 405,
  7× 404, 3× 200. All three 200s (`email_templates`, `creators/platforms`, `creators/platforms/define`)
  were **global templates**, byte-identical to the same call on my own tenant (7 records, matching md5s).
- Every write on my own tenant with the read-only `user` role → 403 (`items`, `coupons`, `api_keys`,
  `customer_roles`, `games`, `checkout_links`, `game_settings`).
- `X-Company-Id` / `X-Game-Id` header substitution → no effect (403 either way); `X-Aghanim-API-Key`
  header → 403.
- `api_keys` list masks the id as `"id":"***"` and returns `secret_redacted: "s2s_izz...T5J"`;
  `POST …/api_keys/{***}/reveal` and `DELETE …/{***}` → 404 `APIKey not found` (no traversal on the mask).

Tokens:
- Hub JWT is HS256 with `{game_id,user_id,player_id,secure,iat,exp}`, 180-day expiry.
  `alg:none` rejected; `HS256-secret` / `HS256-jwt_secret` rejected; token is **game-bound**
  (game-A token → game-B paths = 401).
- No token confusion across services: hub→my-api, hub→pay-api, hub→dashboard-api, hub→s2s, dash→my-api
  all 401. Each plane takes its own credential only.

Order / money:
- `PATCH /order/v1/orders/{id}` → 200 echoing the object, silently ignoring items[].price,
  items[].quantity, amount, total, subtotal, currency, payment_amount, email, return_url, player_id,
  user_id. Only `country` honoured → and it re-prices **correctly** (1.99 USD SKU → IDR 29 000 / JPY 300 /
  TRY 99.99 / NGN 3 090 / BRL 10.99, `payment_amount_usd` stable at 1.61–2.31).
- `/ps/cards/calculate` and `…/submit` with injected `amount`/`total` → server recomputes; tax per
  country is correct (ID PPN 11 % included, GB VAT 20 %).
- Payment replay: re-submitting a paid order → `400 {"error":{"code":8}}`; `payments/last` → `{}`.
- `/wh/{ps}/s/{3ds_complete,capture,payment_data,otp,reestr}` → `404 page not found` or
  `422 {"error":{"code":5}}`; no unauth transition into `done`.
- `RAZORPAY` UPI `validate_vpa` is unauth but returns only `{"valid":bool}` (by-design).
- `/ps/bins/search` unauth, returns bin/scheme/bank/type/country (by-design: fires on card entry).

Hub:
- `POST /hub/v1/websites/{slug}/auth/authorize_user_id {user_id}` mints a JWT + auto-creates the player
  (documented flow, §4.4.6). `player_id` is client-chosen by design.
- `POST …/orders` requires a real `store_item_id` (`order.store_item_required`); foreign `stm_` ids → 404;
  custom items with client price → rejected. `store_item_id` discount is server-side and scoped per game
  (a pixelgun `stm_…` on a skullgirls item → 404).
- `PATCH …/user/me` persists **only** `name`; `balances`, `attributes`, `marketing_consent` ignored.
- `…/user/me?user_id=<other>` ignored (token-scoped). `…/user_communications?user_id=` ignored.
- `challenge_code` needs a real code or nonce (`404 Authorization code not found`); `b64(uid)` is not the
  format (`400 Invalid code format`).

Checkout:
- Stored XSS via `player_id` in the checkout URL → **WAF "Security Block" 403**. Do not retry endlessly,
  the whole request path is filtered on markup.

Auth:
- `my-api` signup requires `email` + `phone`; `start_login` demands `lookup_key ∈ {email,id}` and a phone
  on file; wrong code path returns `403 Invalid or expired confirmation token`; repeated `start_login` → 429.

## 5. The one unstable lead (and why it was NOT reported)

A single `POST /order/v1/orders/{id}/apply_reward_points` on a *guest* order (no auth) **zeroed the
order** (`amount/total 2900000 → 0`, `applied_reward_points: 161`). Eight subsequent fresh orders —
including the same player, the same body, and the same sequence — all returned `applied_reward_points: 0`
with `total` unchanged. `revoke_reward_points` then restored the total and re-apply produced `0` again,
i.e. **non-deterministic, not reproducible**.

Per operator rule (and §6a premature-negative discipline in reverse): **an unreproducible zero-total is a
lead, not a finding**. It was dropped. If a future run sees it again, the reproduction recipe to try:
order → `PATCH {email}` → `apply_reward_points {}` → check `total`; the successful case had
`feature_flags.reward_points_enabled: false` and `sandbox: true`, which suggests a flag-gated code path
where a race or a stale points-cache leaks the "fully redeemed" branch.

## 6. Coverage bound: two credential gates (state these, don't hide them)

Untested because of credentials, not because of difficulty:

1. **`my-api` player plane** (`/v1/users/me`, `/reward_points`, saved payment methods, subscriptions)
   → needs a **phone number + SMS OTP**. Public signup returns
   `201 {id: plusr_…, email_verified:false, phone_verified:false}` and `start_login` then answers
   `400 "User phone is required"`. This is the largest remaining surface.
2. **179 S2S operations + the dashboard write plane** → need an **S2S key**
   (`post_login → GET /companies/games` shows tenant membership), and `POST …/api_keys` is 403 for the
   auto-provisioned read-only role. Getting a write role needs an invite (`/join/{inviteId}`) or the
   creator-program path. That key would unlock `/v1/webhooks/{id}/reveal`, `/refund`, `/dispute_evidence`,
   `/players/{id}/subscriptions/{id}/transfer|upgrade`, and every cross-tenant reconciliation endpoint.

Also untested: **live-mode checkout** — the demo game (`gm_eGVcrwxCfOH`, company `com_eGwBObdcIVz`,
website `wikipedia-i2yx`) runs with `sandbox: true` and has no real items, so §4.4.2 excludes anything
observed in it anyway.

## 7. Reusable mechanics harvested from this engagement

- Helpjuice / Heroku+NEL headers = third-party SaaS helpdesk → check scope before touching.
- `docs.<t>/openapi.json` at the docs root (Docusaurus) = full spec, no crawling.
- The dashboard bundle's **backtick template literals** `/v1/companies/{company_id}/games/{game_id}/…`
  are the complete route map → `scripts/tenant_sweep_from_bundle.py`.
- `POST …/resolve` is the read oracle when `GET` on the same resource is 405 (SPA projection pattern).
- FastAPI validation errors on `my-api` (`422 {"detail":[{"loc":["body","phone"],…}]}`) hand you the
  exact required schema in one request — use them as a schema oracle instead of guessing bodies.
