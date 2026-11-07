---
name: aghanim-engagement
description: "Aghanim (support.aghanim.com / *.aghanim.com API estate) bug-bounty engagement map — scope rules, exclusion traps, endpoint inventory, test-account access path, and verified dead ends. Load before hunting aghanim.com."
tags: [bug-bounty, security, aghanim, scope, engagement, dead-ends]
---

# Aghanim Engagement Map

DTC commerce / liveops / payments platform for mobile games. Everything below was verified live.

## 0. CHAIN GRAPH FIRST

`CHAINS.md` (13 chains) and `CHAINS_v2.md` (~40 links, HOLDS/DIES with verbatim server strings)
live in `D:\data hermes\poc-plans\aghanim\`. Read v2 before proposing any vector — it records the
exact string that kills each lead. Method: `chain-to-impact` + `exploit-chain-graph`.

### The one asymmetry worth remembering: sibling API generation
`api.aghanim.com/checkout/v1/*` is the sibling of `pay-api.aghanim.com/order/v1/*` (both bases exist
in the SPA: `Ew=new Tb({baseUrl: x1?PAY_API/order:HUB_API/checkout})`).
`GET /checkout/v1/orders/{id}` -> **200 full order JSON unauth**, including the creator's
`/ip_address` and `/user_agent`; the current-gen `pay-api/order/v1/orders/{id}` -> **405**.
Capped: order ids are 15-char base62, no listing route exists, archived ids return
`410 {"code":"order.expired"}` (24h TTL), and policy 4.2.14 excludes id-guessing. UNPROVEN/OOS.

## 1. Scope reality check (do this first)

`support.aghanim.com` is the public help center = **Helpjuice SaaS** (Server: Heroku, CloudFront,
cookie `_helpjuice_session_v4`). It is **NOT in scope** — §4.3.1 excludes third-party services.
The policy PDF/doc lives there but the host itself is OOS. Do not spend time on it.

Real in-scope hosts (policy v2026-08-24, from `aghanim.com/.well-known/security.txt`):

```
aghanim.com            api.aghanim.com          dashboard.aghanim.com
dashboard-api.aghanim.com    events.aghanim.com  events-web.aghanim.com
hub-api.aghanim.com    hub-api-global.aghanim.com
my.aghanim.com         my-api.aghanim.com       pay.aghanim.com
pay-api.aghanim.com    s2s-api.aghanim.com      sdk-api.aghanim.com
upload.aghanim.com     *.aghanim.app
pay-api.aghanim.store  my-api.aghanim.store  api.aghanim.store  hub-api.aghanim.store
+ Aghanim Android SDK, Aghanim Unity SDK
```

**No wildcard `*.aghanim.com`.** subfinder returns 190+ subs (admin-api, account-api, buy-api,
api-dev, api.staging, datahouse, cpanel, ...) — all OUT of scope unless explicitly listed.
Testing them = engagement risk.

Rewards: Critical $1250 / High $550 / Med $250 / Low $50. Contact bugbounty@aghanim.com.
Payout after fix. CVSS v4 as starting point but business logic judged individually.

## 2. Exclusion traps (kill leads before you burn hours)

| Exclusion | Practical meaning |
|---|---|
| 4.2.5 | Adyen/Ebanx/PayPal client keys in checkout responses = by design. `/ps/?order_id=` leaks `credentials.adyen.client_api_key live_...` and `ebanx.public_integration_key live_pk_...` → **do not report** |
| 4.2.14 | Anything keyed on guessing `ord_`, `itm_`, `usr_`, `lnk_`, player_id → excluded even if unauthenticated |
| 4.2.4 | version/banner/stack-trace only → excluded |
| 4.2.10 | `/v1/users/lookup` `{exists,email_verified,has_passkey}` enumeration → excluded without more |
| 4.4.2 | test-mode/sandbox payment behaviour → excluded |
| 4.4.4 | self-funded, self-referral, own-account economy manipulation → excluded unless other players/games affected |
| 4.4.6 | "login by Player ID" and "composite authorization" are **documented integration patterns** → not vulns |
| 4.1.3/4.1.5 | DoS, email/SMS flooding incl. password-reset abuse → excluded |

## 3. Architecture (what talks to what)

```
game server --(S2S Bearer key)--> api.aghanim.com/s2s/v1/orders  (price supplied by game)
player --> pay.aghanim.com / <slug>.hub.aghanim.app  (SPA, Vite)
           --> pay-api.aghanim.com (Go) : /order/v1/*, /ps/*, /wh/{ps}/s/*
           --> api.aghanim.com/hub/v1/websites/{slug}/* (FastAPI, game hub)
           --> my-api.aghanim.com/api/v1/* (player account, requires phone+OTP)
dashboard (Auth0 PKCE) --> dashboard-api.aghanim.com/dashboard/v1/* (FastAPI, RBAC)
upload.aghanim.com : /upload, /ingest (multipart, needs dashboard JWT + X-Company-Id)
events.aghanim.com / events-web.aghanim.com : analytics ingestion (events-web answers "pong" to everything)
```

Auth0 tenant: `auth0.aghanim.com`, client id `FqpBNJhXOxenE0RqoCvRTnFnrwecLV80`,
audience `https://aghanim.com`, passwordless email OTP.

## 4. Test-account access path (works, reproducible)

1. **Dashboard account** — passwordless, no phone needed:
   - `https://dashboard.aghanim.com/` → Sign up → email → OTP arrives from `notifications@aghanim.com`
     (subject "<6 digits> is your Aghanim verification code").
   - Decode OTP from Gmail API (script: `gmail_otp.py` pattern — refresh token at
     `~/.chiper/skills/bounty-pack/google_token.json`, search `from:aghanim`).
   - After login: onboarding page needs `POST /dashboard/v1/customers/accept_agreements` (204) —
     the React checkbox UI is flaky, just call the API.
   - Result: auto-provisioned company `com_...` + game `gm_...`, role **"user" = read-only**
     (`campaign:read`, `sku_item:read`, `transaction:read`, ...).
   - Bearer token lives in dashboard localStorage key `@@auth0spajs@@::<clientid>::https://aghanim.com::openid profile email offline_access` → `.body.access_token`.
2. **Guest checkout order** — no account at all:
   `POST https://pay-api.aghanim.com/order/v1/links/lnk_eHriLMNNvUxvbFHm?player_id=<anything>`
   → 201 with full order object (demo game "Wikipedia", sandbox). Public doc example link.
3. **Sandbox payment** (to reach paid/delivered state, webhook, receipt):
   - `PATCH /order/v1/orders/{id}` `{"country":"GB"}` first — testcards are geo-blocked in ID.
   - `POST /ps/cards/calculate` `{order_id, billing_address:{iso_code:"GB"}, skip_address_validation:true}`
   - `POST /ps/cards/submit` with `4242424242424242`, exp 12/2030, cvc 123, `save:false`.
   - Result: order → `paid`, `delivered_at` set, receipt email, receipt_number.
4. **Hub player token** — `POST https://api.aghanim.com/hub/v1/websites/<slug>/auth/authorize_user_id`
   `{"user_id":"<any string>"}` → 200 + HS256 JWT (1 year) for the **demo** game only.
   For real games (e.g. `hub.pixelgun3d.com`) the same call returns **401** because the game's
   `player.verify` webhook gates it — so this is NOT an auth bypass (and 4.4.6 covers it).

## 4b. SELF-PROVISION a full integrator tenant (no invite needed)

Never ask the operator for an invite or a phone. A read-only account can create its own tenant
and become **owner**, which mints a real S2S key:

```
POST /dashboard/v1/companies        {"name":"...","size":3,"url":"https://example.com"}   -> 201 {id:com_...}
GET  /dashboard/v1/companies/{com}/profiles/me                                           -> "role":"owner","mode":1
POST /dashboard/v1/companies/{com}/games  {"name","locale_default","url","logo_url",
     "description","social_medias":[],"game_stores":[],"login_methods":["user_id"]}       -> 201 {id:gm_...}
POST /dashboard/v1/companies/{com}/games/{gm}/api_keys {"type":"secret"}                 -> 201 {secret:"s2s_..."}
```
`POST /v1/companies` only needs name/size/url; games need the three empty lists (`social_medias`,
`game_stores`, `login_methods`) — validation errors enumerate every missing field, so loop on
`detail[].loc[-1]` until 201. Websites additionally require a client-supplied `share_token`.

Then `Authorization: Bearer s2s_...` against `https://api.aghanim.com/s2s/v1/*` — all 179 ops.

**Verified isolation with that key** (all correct, do not redo): foreign order read/patch/refund/expire
-> 403; `/v1/payments?order_id|user_id|search_string=<foreign>` -> `[]`; foreign player
-> `404 User not found`; `/v1/items?game_id=<foreign>` -> `[]`; requested website slug colliding with
another tenant is silently **auto-deduplicated** (`wikipedia-i2yx` -> `bb-site-tvee`) so no hub hijack.
NOTE `PUT /v1/players/{pid}` returning 200 is an **upsert into your own game**, not cross-tenant.

## 4c. events-web.aghanim.com — unauthenticated event ingestion (UNPROVEN impact)

Catch-all: `POST https://events-web.aghanim.com/<any-path>` with any JSON (including `{}`, junk,
claims of purchases for other companies) -> `200 "Event with ID: <n> accepted successfully."`
No auth, no schema, no rate limit, `access-control-allow-origin: *`; origin is GCP with
`x-origin-mtls: present=true`. GET any path -> `pong`. IDs are random (not snowflake-ordered).
Cannot prove persistence: there is no read-back, and forged markers never appear in
`reports/load_cube_data` / `general_analytics` / `audit_trails`. Record as UNPROVEN, not a finding.

## 4d. Webhook forgery chain — fully tested, chain does NOT complete

Signing contract (from docs): `X-Aghanim-Signature = HMAC-SHA256(whsec_secret, "{X-Aghanim-Signature-Timestamp}.{raw_body}")`,
case-insensitive hex, plus payload fields `event_type,event_data,event_time,event_id,idempotency_key,sandbox,trigger,request_id`.

Verified with **two tenants I own** (A=`com_eLmGVLbDpXD`/`gm_eLmGWvAlcrc`, B=`com_eLmHgAMOSGh`/`gm_eLmHgVDBqyr`):

| Test | Result |
|---|---|
| create webhook + `reveal` own secret | 201 / 200, secret `whsec_` + 32 chars |
| secret shared across tenants? | **NO** — A≠B, unique per webhook, ~256-bit |
| webhook secret == S2S key? | NO |
| A's S2S key -> B's webhook `reveal`/`GET`/`PUT`/`expire_secret` | **404 all** (correct isolation) |
| B's own key -> same ops | 200 (control passes) |
=> The Critical form (forge `item.add` into another game's backend) needs a foreign `whsec_`.
   There is no path to it: reveal is tenant-scoped, secrets are unique and unguessable, and
   webhook ids are `wh_` + base62 (guessing = OOS 4.2.14). **Chain DIES at secret acquisition.**

### SSRF via webhook URL — well defended at creation
| URL | Result |
|---|---|
| `https://localhost/`, `https://metadata.google.internal/` | 422 `URL points at a local network name: <host>` |
| `https://169.254.169.254/`, `127.0.0.1`, `10.0.0.1`, `[::1]`, `[::ffff:127.0.0.1]` | 400 `The webhook URL must point at a public address.` |
| `127.0.0.1.nip.io`, `169.254.169.254.nip.io`, `localtest.me`, `127.0.0.1.sslip.io`, `7f000001.0a000001.rbndr.us` | 400 (resolution-based check catches rebinding hosts) |
| `0x7f000001`, `0177.0.0.1`, `2130706433` | 403 WAF "Security Block" |
| `file:///etc/passwd` | 403 |
| `http://<oob>/hook` (plaintext, docs require HTTPS) | **201 ACCEPTED** — minor hardening gap |
| `https://hub-api.aghanim.com/hook` | **201 ACCEPTED** — webhook may target Aghanim's own API host (unproven impact) |
| `https://<oob>` at creation | triggers a **DNS lookup from Google infra** (validated OOB, `remote-address 192.178.118.215`) |

**Cannot be completed without KYC or a real payment.** A live delivery needs an event:
- `player.verify` needs a published hub -> `check_publish_readiness` returns
  `{"can_publish":false,"blockers":[{"code":"account_not_verified"}]}` (KYC — never fake it)
- `item.add` needs a paid order -> `POST /v1/orders` and the checkout link both return
  **500 Internal server error** for a game with no website; sandbox game via
  `POST /v1/companies/{c}/games/{g}/sandbox` (creates `sandbox:true` game, 201) has the same 500.
- No `/webhooks/{id}/test|ping` route exists; no delivery-log route exists.
=> result: only DNS (validation) hits, **zero HTTP deliveries**. Delivery-time redirect SSRF UNPROVEN.

## 4f. RETRACTED (was F1) — "unauth order read" is BY DESIGN. Do not re-report.

`GET api.aghanim.com/checkout/v1/orders/{id}` returns the full order unauthenticated. That LOOKS like
an authz gap against `pay-api/order/v1/orders/{id}` (405). **It is not.** The comparison is invalid:

**The order URL is a bearer capability by design (guest checkout).** The legitimate checkout page
(`pay.aghanim.com/en/order/{id}`, loaded in a headless browser with zero auth) calls
`POST https://pay-api.aghanim.com/order/v1/orders/{id}/resolve` — unauthenticated — and that route
returns the SAME fields: `ip_address`, `user_agent`, `player_id`, `player_info{name,avatar_url,
attributes}`, `user_id`, `datahouse_user_id`. The page renders only item/price/total, but the data is
reachable by anyone holding the link. Docs confirm it: "treat the resulting URL as opaque — do not
modify the path", i.e. the URL *is* the capability. Policy 4.2.14 also excludes id-based access.

**The trap I fell into:** I benchmarked the legacy sibling against `GET` on pay-api, a method that
does not exist there (405). The correct baseline is *the route the legitimate client actually calls*
(`POST /resolve`), which returns the same data. Comparing to a non-existent route turns a design
property into a fake authorization gap.

**Detection rule for this class:** before reporting an unauthenticated read, (1) find which route the
official front-end calls, (2) call it yourself with no credentials, (3) if it returns the same data,
the data is public by design — stop. Full writeup: `_RETRACTED/RETRACTION.txt`.

Same failure as the relay.link `x-api-key required:false` lesson. It is the single most expensive
mistake in this engagement; check it FIRST, not after building a PDF.

## 4g. Sibling write-path sweep (#1) — NEGATIVE, do not redo

Tested every write on `api.aghanim.com/checkout/v1` against an order I created (demo game, sandbox).

**PATCH /v1/orders/{id} is a full no-op on money state.** All of these return 200 and change nothing:
`status`, `paid_at`, `delivered_at`, `handled_by_client`, `receipt_number`, `payment_method`, and
(previously) `amount`, `total`, `subtotal`, `currency`, `items[].price/quantity/price_after_discount/
store_item_id/discount_percent/is_free_item`, `coupon_code`, `promo_code`. Only `country` applies.

**`apply_reward_points` — the sibling LIES without persisting.** Body schema is
`{reward_points:int, reward_points_balance:int}` (both required). `reward_points_balance` is IGNORED;
`reward_points` is client-controlled and believed. Matrix on a player with **zero** real points:

| reward_points | balance | sibling reports | pay-api (authoritative) |
|---|---|---|---|
| 0 | 1000000 | total 2900000, applied 0 | unchanged |
| 1 | 0 | total 2881975, applied 1 | unchanged |
| 161 | 0 | **total 0, applied 161** | **total 2900000, applied 0** |
| 999999 | 0 | total 0, applied 161 | unchanged |

**It does not persist and cannot be completed.** `POST pay-api/order/v1/orders/{id}/resolve` still shows
`total=2900000, applied_reward_points=0`; `POST /ps/cards/calculate` charges the **full 2900000**; and the
sibling has **no `/ps/*` payment path at all** (404 on `/ps/`, `/ps/cards/calculate`, `/ps/cards/submit`).
=> cosmetic response divergence in a legacy API. **No financial impact. Not reportable.**

Also dead: `pay_link` → blind `204` for any subscription id (garbage included, current gen 404s);
`activity/{type}` enum is only `tab_closed` (analytics); `select_subscription_plan` unreachable
(needs a subscription order, which cannot be created); coupons need a real coupon in that game.

## 4h. Two-way cross-tenant isolation (#2) — NEGATIVE, isolation is correct

Method: two tenants I own, **real object ids, zero guessing** (strongest form of the test).
A = `com_eLmGVLbDpXD`/`gm_eLmGWvAlcrc`, B = `com_eLmHgAMOSGh`/`gm_eLmHgVDBqyr`.

| A-key against B's object | result |
|---|---|
| `GET/PUT/PATCH/DELETE /v1/items/{B_item}` | 404 / 404 / 405 / 404 |
| `GET/PUT/DELETE /v1/leaderboards/{B_board}` | 404 / 404 / 404 |
| `GET /v1/players/{B_player}`, `POST` | 404 |
| `PUT /v1/players/{B_player}` | 200 — but writes **A's own namespace** (distinct `usr_` id); B's record untouched |
| `GET /v1/orders/{B_order}` + PATCH/refund/expire | 403 |
| `/v1/payments?order_id=` `?user_id=` `?search_string=` (B values) | `[]` |
| `/v1/webhooks/{B_wh}` GET/PUT/reveal/expire_secret | 404 (B's own key: 200) |
| `/v1/coupons/user/{B_uid}`, `/store_promotions/user/{B_uid}` | `[]` (identical to B's own key) |
| `?game_id={B_game}` on items/orders/payments/leaderboards | 200 but returns **A's own rows** |

**Two detector traps that produced false positives** — both now in the lessons list:
1. `?game_id=<B>` returning 200 looked like a read leak; it actually **ignores the param** and lists your
   own tenant. Always assert the returned **ids** contain the foreign object, never just check status 200.
2. `PUT /v1/players/{B_player_id}` returning 200 looked like a cross-tenant write; `player_id` is
   **per-game**, so it created A's own player with the same string. Verify by comparing the returned
   `usr_` id to B's.

## 5. Endpoint inventory (harvested, keep for reference)

- S2S OpenAPI: `https://docs.aghanim.com/openapi.json` → **179 ops / 97 paths, all `HTTPBearer`**.
  Includes `/v1/orders`, `/v1/orders/{id}/refund`, `/v1/payments`, `dispute_evidence`,
  `/v1/players/{id}/subscriptions/{sid}/transfer|upgrade`, `/v1/webhooks/{id}/reveal`,
  `/v1/users/authenticate`, `/v1/users/authorize`, `/v1/coupons`, `/v1/items`.
- Dashboard: 382 paths from `dashboard.aghanim.com/assets/index-*.js` (13.5 MB, grep
  `` `/v1/...` ``). Pattern `/dashboard/v1/companies/{company_id}/games/{game_id}/...`.
- Hub: 97 paths from `gau hub-api.aghanim.com` — `items`, `items/{itm}?store_item_id=`,
  `item_categories`, `daily_rewards`, `leaderboards`, `achievements`, `news`, `pages/{pg}/children`,
  `sections`, `loyalty`, `user/me`, `user/reward_points`, `user/virtual_currencies`,
  `user_communications`, `activities/visit_page`, `auth/authorize_user_id`, `auth/challenge_code`,
  `orders`, `range_offers/{rof}`, `rolling_offers/{rgo}`, `progression_programs/{pgp}`,
  `user_banners/daily-rewards`.
- Checkout: `/order/v1/links/{lnk}` POST, `/order/v1/orders/{id}` PATCH|POST resolve,
  `apply_coupon|revoke_coupon|apply_reward_points|revoke_reward_points|select_subscription_plan`,
  `/ps/` list, `/ps/bins/search`, `/ps/bins/search/profile`, `/ps/cards/calculate`,
  `/ps/cards/submit`, `/ps/payment_options`, `/ps/payments/{pmt}`, `/ps/subscriptions/*`,
  `/ps/orders/{id}/payments/last`, `/wh/{ps}/s/{capture|3ds_complete|otp|otp_confirmation|payment_data|reestr|cancel}`.
- Upload: `POST /upload` (multipart: file, bucket, file_type, file_hash, thumbnail),
  `POST /ingest` `{url, bucket, file_type}` → **SSRF primitive**, but 403 for read-only role.

## 6. Verified dead ends (don't redo)

| Vector | Result |
|---|---|
| Price/currency/qty tampering (PATCH order, resolve body, calculate, submit) | server recomputes; only `country` honoured, re-prices correctly across ID/JP/BR/TR/NG/US |
| Cross-tenant dashboard (240 GETs vs other company/game) | 403 all; `email_templates` + `creators/platforms` = global templates, byte-identical across tenants |
| RBAC escalation as read-only "user" | items/coupons/api_keys/roles/game_settings writes → 403 |
| `api_keys/{id}/reveal` | id is masked `***`; 404 |
| Hub JWT forgery | HS256, `alg:none` rejected, common secrets rejected, token bound to game_id |
| Token confusion hub↔my-api↔pay-api↔dashboard↔s2s | every combo 401 |
| Payment replay / idempotency | resubmit paid order → 400 code 8; `/wh/*` 404 or NOT_FOUND |
| Hub order creation | `store_item_id` mandatory, cross-game store_item_id → 404, custom price ignored |
| Hub mass assignment (`balances`, `attributes`, `marketing_consent`) | silently dropped; only `name` persists |
| IDOR `user/me`, `user_communications?user_id=` | token-scoped |
| Stored XSS via `player_id` in checkout URL | WAF "Security Block" 403 (note: `PATCH user/me` name DOES store raw HTML `<img src=x onerror=...>` — renderer not yet proven, hub app needs dashboard session) |
| secrets in client bundles | none (s2s_/whsec_/sk_live_/AIza all absent) |
| nuclei (cve,exposure,misconfig,panels,default-login,takeover,tech @rl6) | only `dns-waf-detect:cloudflare` info |
| ffuf 272-path wordlist × 6 API hosts | no new routes |
| `apply_reward_points` with no auth zeroing an order | 1× anomaly, unreproducible on 8 fresh orders → do not report |

## 6b. Tool results + two Windows traps

All runs produced artifacts in `artifacts/` (see `artifacts/TOOL_EVIDENCE.txt`):
nuclei (tech/cve/exposure/misconfig/panels) 6 hosts → **0 findings** (only `dns-waf-detect:cloudflare`
info from the DNS pass); ffuf 272-path × 6 hosts → 0 new routes; dalfox ×2 → 0 XSS;
sqlmap ×2 → not injectable + WAF detected; katana/httpx/subfinder → no new surface.

**Trap 1 — sqlmap "host does not exist" on Cloudflare hosts.** `getaddrinfo()` returns **IPv6 first**
for e.g. `pay-api.aghanim.com` and there is no IPv6 route, so sqlmap dies on DNS. `nslookup` also
returns IPv6 only. Fix (no admin rights needed): monkeypatch `socket.getaddrinfo` to force AF_INET
then call `sqlmap.main()` — see `run_sqlmap_ipv4.py` in the poc-plans dir.
Editing `C:\Windows\System32\drivers\etc\hosts` needs admin and is denied in this shell.
A local CONNECT proxy did NOT help (sqlmap "can't establish SSL connection" through it).

**Trap 2 — arjun "Skipped due to errors".** It silently drops the target unless you pass an explicit
User-Agent and cap the rate: `-t 1 --rate-limit 2 --headers "User-Agent: ..."`.
Rerun result on `/hub/v1/websites/{slug}/items`: **hidden params `country` and `type`**.
`country` re-localises prices (ZZ falls back to USD, no error); `type` enum `item|lootbox|subscription`.
Both are product features, not bugs — but they are the right place to look for price/entitlement logic.

## 6c. Do not re-test these (verified benign)

- `PATCH /hub/v1/websites/{slug}/user/me` stores `name` **raw** (`<img src=x onerror=...>` round-trips),
  but the `.aghanim.app` hub front-end needs a dashboard `__ssid` session to render, so XSS is unproven.
- `?country=` on hub items and `PATCH order {country}` both re-price consistently; ID/JP/BR/TR/NG/US/ZZ
  all sane (differences are the game's own regional price points).
- `billing/payment_methods` = 250-entry **global platform catalogue**; other tenants get 403, so no leak.

## 6d. Stored-XSS lead — FULLY CLOSED (do not redo)

Chain investigated end-to-end:
1. `PATCH /hub/v1/websites/{slug}/user/me {"name":"<img src=x onerror=...>"}` → **stores raw HTML**
   and returns it raw. Also works on your *own* tenant (slug `demo`, hub `manabuff.com`).
2. Downloaded all 132 hub chunks from `manabuff.com/assets/*.js` (Next.js + React Compiler) and
   enumerated every `dangerouslySetInnerHTML` in **app** code (excluding the React runtime):
   - `Linkify` (Ci0lKHjb.js): `children.toString().replaceAll(URL_RE, '<a href="$&">$&</a>')` then
     `dangerouslySetInnerHTML` — non-URL text is injected **unescaped**. Real bug pattern, BUT it is
     wired only to `n.description` (item/news description) = integrator content → OOS per 4.4.3.
   - `LexicalContent` (DKsmdTTr.js) — rich-text editor content, integrator-controlled.
   - GA/GTM/MetaPixel/Termly/custom_code_js script injections — integrator-configured.
   - **No sink consumes the player `name`.**
3. Empirical: set payload name, opened `manabuff.com/go/login?token=<hub_jwt>` + `manabuff.com/`,
   checked `document.querySelectorAll('img[src=x]')`, `<b>BBXSS</b>`, and `onerror=` in the DOM →
   **0 hits, 0 dialogs**. Leaderboard components (`B__phrsb.js`) contain **0** `dangerouslySetInnerHTML`.

Verdict: raw storage + safe text render = **data hygiene, not XSS**. Do not report.

## 6e. Hub session mint (how the dashboard→hub SSO works, for future runs)

Route `/api/auth/hub/:slug` on the dashboard SPA:
`POST /dashboard/v1/websites/search_website {search_string: slug}` → then
`POST /dashboard/v1/companies/{c}/games/{g}/websites/{w}/create_exchange_token` → `{token}` →
appends `?preview_token=<token>` to the hub URL.
Both are **correctly tenant-scoped**: `search_website` returns 404 for slugs/sites you don't own
(tested `wikipedia-i2yx`, `hub.pixelgun3d.com`, `sale`, `manabuff`) and `create_exchange_token`
returns 404 for read-only role. No cross-tenant pivot here.

## 7. Remaining surface (needs identity you probably don't have)

1. **Player surface `my-api.aghanim.com/api/v1/*`** — gated by **phone number + SMS OTP**.
   `signup` requires `{email, phone}`; `start_login` returns `400 User phone is required`;
   `verification_type: phone` returns `400 Email verification required`.
   This blocks: saved payment options, subscriptions, reward/loyalty, full `/v1/users/me`.
2. **All 179 S2S ops** — need a game S2S key. Creating one requires dashboard write role
   (`POST .../api_keys` → 403 for "user"). Path to write role probably via company invite
   (`/join/:inviteId`, `/v1/invites/{id}/accept`) or creator-program approval.
3. **Live-mode checkout** — demo game is production but has no store items.
4. **upload `/ingest` SSRF** — only reachable with a write-role dashboard JWT.

## 8. Working scripts (in D:\data hermes\poc-plans\aghanim\)

`api.py` (call()), `gmail_otp.py` (Gmail OTP fetch), `bola_sweep.py` (cross-tenant sweep),
`pw_login_otp.py`, `pw_pay4.py` (full sandbox payment), `pw_xss.py`, `pw_hub.py`,
`docs/*.html` (9 integration docs), `openapi.json`, `js/dash.js`, `js/index-*.js`.

## Pitfalls

- Curl against `aghanim.com` apex returns Vercel Security Checkpoint 403; use `www.` or the API hosts.
- `PATCH /order/v1/orders/{id}` returns 200 even when it ignores your fields — always re-`resolve` to read state.
- `GET /order/v1/orders/{id}` is 405; use `POST .../resolve` to read an order.
- Dashboard onboarding React page needs agreement API call, not UI clicks.
- Hub front-end for `.aghanim.app` redirects to Auth0 dashboard session; you cannot render it from a
  player JWT alone (needs `__ssid` from `dashboard.aghanim.com/api/auth/hub/<slug>`).
- Send `X-Bug-Bounty: <email>` on every request (policy §7.2).
