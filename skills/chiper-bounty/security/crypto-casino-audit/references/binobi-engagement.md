# Binobi (binobi.com) — worked engagement, 2026-10-27/28

Operator: Lexoria Global Ltd (Belize), Anjouan licence ALSI-202503035-F12. Programme is in-house,
reports to `support@binobi.com` (`partners@binobi.com` for affiliate issues), duplicate Critical into
Live Chat. Reward ladder: hot wallet $300k / account penetration $40k / balance manipulation $30k /
in-house game $25k / server $20k / bonus abuse $10k / aggregator game $5k / functional bug $500.

No platform, no scope PDF, no `security.txt` — the programme page is the whole policy.

## 1. Stack

| Layer | Detail |
|---|---|
| Web | Next.js (pages router), buildId `inKq_6RqFSycsRHw-haLK`, locale-prefixed routes |
| API | NestJS ("Cannot GET /x" + `{"message":…,"statusCode":…}`) |
| Edge | Cloudflare on every host; `CF-RAY …-SIN` |
| Captcha | Cloudflare Turnstile, widget on signup/login/forgot |
| Flags | LaunchDarkly (`NEXT_PUBLIC_LD_ID_PROD`) |
| Analytics | Microsoft Clarity (`t1wvstakue`), Cloudflare Insights |
| Auth | HS256 JWT `{ver:2,tokenUse:"access",sid,sub,iat,exp,aud:"binobi-api",iss:"binobi-auth"}` + `__Host-binobi-at` / `__Host-binobi-rt` cookies |
| Games | Slotegrator-class aggregator (89 providers) + in-house |
| PSPs | moneygrator, avepay, bestpay, dns-pay, expay, fxmb, paysage, repay, settle, 100hp, antrpay |

Hosts: `binobi.com`, `www`, `api.binobi.com` (real API), mirrors `binobi.casino/.io/.in/.mx`
(`api.binobi.io` fully live incl. `/metrics`). `admin.`, `affiliates.`, `affiliates-admin.`, `mail.`
all NXDOMAIN.

## 2. The rewrite discovery (how the two API paths were found)

`GET /_next/static/inKq_6RqFSycsRHw-haLK/_buildManifest.js` contained:

```js
__rewrites:{afterFiles:[
  {has:i,source:"/:locale(en|uk|…)/_binobi/api/:path*",destination:"/api/mirror/:path*"},
  {has:i,source:"/:nextInternalLocale/robots.txt",destination:"/:nextInternalLocale/api/robots"},
  …
]}
```

So `https://binobi.com/_binobi/api/games/list` == `https://api.binobi.com/games/list`. Both answer;
the API host is the cleaner target (no Next.js in the way). `sortedPages` in the same file gave all
38 web routes.

## 3. Internal API inventory (196 paths, from bundle greps)

Extracted with `re.findall(r'"/[a-zA-Z0-9][a-zA-Z0-9_./{}$: -]{1,70}"', app_js)` then filtered for
locale/asset prefixes. The interesting ones (all under the `/_binobi/api` or `api.` prefix):

```
auth:      precheck, register, login, refresh, logout, me, validate-captcha,
           confirm-email/request, forgot-password, password-recovery/{status,exchange,cancel,complete},
           2fa/{initial,disable}, mfa/complete, strategies/{metamask,google,telegram,binance,ton}
money:     balance, balance/bonus, withdraw, cashback-balance, deposit/card-method,
           deposit/expay/create_wallet, moneygrator/create{,/idr,/kzt,/rub/sbp},
           avepay/create, settle/create/processing/{inr,card/kzt,card/mxn,clabe/mxn,codi/mxn,oxxo/mxn},
           settle/create/tele2, fxmb/{banks,deposit}, ex-gateway{,/acquiring,/crypto/invoice},
           payment-rotation, accounting/rate (403)
bonus:     bonuses/v2/{available,all-user-bonuses}, bonuses/v2/issue-freespins-bonus (PATCH+qparams),
           binobi-boost/{activate,status}, airdrop candidates, promocode claim /v2/promocode/claim
loyalty:   ticket, ticket/buy, ticket/spent, ticket/lucky-wheel, tickets/transactions,
           daily-quest, users/lucky-wheel-time, ranks/{levels,next-rank,cashback,cashback-history}
referral:  referral/{overview,balance,campaigns,referrals,claim,ref},
           referral/campaigns/full?campaignId=, campaigns/stat
games:     games/{list,providers,search,history,favorite,user/stats,top/played/<x>}
kyc:       verifications (POST), verification/isActive, verification?uniqueCode=
files:     files/<uuid>  (signed URL resolver; 404 on unknown, no auth bypass)
admin-ish: banners/find (403), accounting/rate (403), partners (401), partners/login (400)
```

Front-end-only routes seen in `sortedPages`: `/account/{game-history,sessions,tickets-transactions,transactions,verification}`,
`/banned/[reason]`, `/crawl-links`, `/daily`, `/restricted-area`, `/verification`, `/wheel`, `/vip`.

`/locales/en/vault.json` exposed an unlinked **player-to-player tips** feature
("Send Tips" → `{Username, Currency, Amount}`, `min`, and a success string naming the recipient).

## 4. Account mint — three paths, ranked

### 4a. Wallet signature (works, no captcha)
```python
POST /auth/strategies/metamask/message  {"address": addr}      -> 201 {"result":{"message":"Login at <ms>. Nonce: <32hex>"}}
sig = Account.sign_message(encode_defunct(text=message))        # plain text, NOT EIP-712
POST /auth/strategies/metamask  {"address","sign":"0x…","language":"en","browserData":{…},"isLogin":true}
   -> 201 {"result":{…,"token":"eyJ…","expiresAt":…,"sessionId":"<uuid>"}}
```
`browserData` is required and nested: `browser{name,version,major}`, `cpu{architecture,logicalProcessor}`,
`device{}`, `engine{name,version}`, `os{name,version}`, `ua`, `resolution`, `timezone`,
`systemLanguage`, `canvasPrint` (a base64 data-URL string — any string passes).

Gotchas measured:
- Header `X-Binobi-CSRF: 1` required on the second call, else `403 Invalid auth origin or CSRF headers`.
- Adding `email` to the *login* call → `400 error_auth_email_is_missing` on first use, then
  `error_auth_account_already_taken`, then `409 error_auth_register_duplicate_wallet`.
- Extra `address` field on the login call → `403 error_auth_sign_not_found_or_expired` (false expiry).

### 4b. Email + Turnstile (works with a real mailbox)
```python
POST /_binobi/api/auth/register
{"email":"you+tag@gmail.com","password":"Test12345!","language":"en","browserData":{…},"captchaToken":"<turnstile>"}
  -> 201, returns the full user object WITH token + sets __Host-binobi-rt / __Host-binobi-at
```
- Turnstile token harvested headless: open `/`, click `Sign Up`, click `[data-testid=method-switcher-button]`
  (switches phone→email), wait for `input[name="cf-turnstile-response"].value`, 709 chars.
- **No email verification is required** — account + bearer token issued immediately.
  `/auth/confirm-email/request` returns `201 {"result":[],"status":"success"}` but is cosmetic.
- Disposable domains blocked: `error_auth_register_disposable_email` for mail.tm/yopmail/etc.
- `500 Internal server error` on `you+tag10@gmail.com` and `fz.susanto13@gmail.com`; `201` on
  `you@googlemail.com`. Unexplained crash path in signup — candidate.

### 4c. Login with password (also captcha-gated, issues cookies but NO bearer)
`POST /auth/login {login,password,browserData,language,captchaToken}` → 201 + `Set-Cookie:
__Host-binobi-rt` (7d, HttpOnly/Secure/Lax) and `__Host-binobi-at` (15 min). Refresh then mints a
bearer from the cookie.

## 5. Session lifecycle result (the reportable one)

```
login                       -> rt1
POST /auth/refresh (rt1)    -> 200, rt2 issued
replay rt1                  -> 200, returns a NEW token   <-- old RT never invalidated
replay rt2                  -> 200
POST /auth/logout           -> 204, clears cookies
replay rt1 / rt2 after logout -> 401  (server-side revoked at logout)
```
Nuance worth keeping: inside one session the RT was replayable and each replay returned the *same*
new RT value (idempotent), so "rotation" is cosmetic; logout does revoke the whole session family.
Conclusion recorded: **in-session refresh-token replay works; post-logout replay does not.** Do not
upgrade this to "session termination broken" — it is not, on this target.

## 6. `/metrics` (unauth, Prometheus)

`https://api.binobi.com/metrics` (24.5 KB) and `https://api.binobi.io/metrics`, plus
`https://binobi.com/api/metrics`. Nuclei confirmed as `prometheus-metrics` [medium].

Labels mined:
- `binobi_moneygrator_callback_events_total{outcome=received|authenticated|invalid_signature|
  configuration_error|status_error|duplicate|deposit_credited|deposit_failed|review}` —
  `invalid_signature` 843/901 → the callback IS signature-checked and heavily bot-hammered.
- `binobi_rate_limit_decisions_total{provider=…,rule=callback-burst|callback-minute|api-burst|
  api-minute|default,outcome=allowed|rejected|storage_error}` with `provider` naming every PSP:
  100hp, amatic, antrpay, avepay, bestpay, dns-pay, expay, fxmb, moneygrator, paysage, promotions,
  repay, settle, slotegrator-betting, slotegrator-casino, twilio.
- `binobi_auth_*` — refresh/replay/rotation counters, origin-error counts.
- `binobi_ws_*` — Socket.IO gateway rules (`ws-handshake-burst`, `origin` denials),
  `connections{kind=authenticated|guest}` → confirms a guest-allowed websocket gateway.

## 7. Business-logic probes and their answers

| Probe | Result |
|---|---|
| `POST /ticket/lucky-wheel` ×1 | `201 {"result":{"id":13}}`, sets `nextLuckyWheelSpinTime` +24h |
| same ×12 concurrent | **1×201, 11×400 error_ticket_time** → atomic gate, no race |
| `POST /ticket/buy {quantity:1}` | `404 error_ticket_balance_usdt_not_found` (needs funded balance) |
| `PATCH /bonuses/v2/issue-freespins-bonus?bonusId&gameId` | `bonusGames[].id` → `404 deposit_need_transaction_first`; slug → `404 game_does_not_exist` |
| `GET /balance/bonus` | `[{amount:1814.881, currency:"IDR", wager:0, wagerGoal:90744.05, …}]` — wheel win credited here |
| `POST /withdraw` ladder | invalid_amount → minimal_withdraw → invalid_address → not_enough_balance; FIAT → `withdraw_wrong_currency` ("allow only with USDT") |
| `POST /referral/campaigns {}` | `400 name must be a string`; `{name:"x"}` → `201` with `link:"/?r=<20char>"` |
| cross-account `campaignId` | `404 error_campaign_not_found` (correct) |
| `POST/PATCH /balance`, `/balance/bonus` | `403 Forbidden resource` / `404 Cannot …` (correct) |
| `PATCH|DELETE /users/lucky-wheel-time` | `403 Forbidden resource` (route exists, guard blocks) |
| 17 header-spoof variants (`X-Forwarded-For`, `X-Original-URL`, `X-User-Role`, `X-Admin`, …) on `POST /balance` | all `403`, one `401` when overriding `Authorization` |
| `POST /auth/google/login` / `telegram/login` with `alg:none` JWT | `401 Invalid … OIDC nonce` / `Invalid Telegram OIDC token` |
| game launch (`/all-games/game/<slug>` preloader → Play?) | no launch XHR at all — gated on balance |

## 8. Tooling notes that cost time

- **Injecting a bearer into the SPA**: patching `XMLHttpRequest`/`fetch` in an `addInitScript`
  partially failed (a typo introduced by string-replacing `window.fetch = function` produced
  `window.fetunction`, which broke silently). The reliable pattern is Playwright routing:
  ```js
  await ctx.route('**/_binobi/api/**', async route => {
    const req = route.request();
    if (req.url().includes('/auth/refresh'))
      return route.fulfill({status:200, contentType:'application/json',
        body: JSON.stringify({result:{...user, token, expiresAt:user.expiresAt}})});
    return route.continue({headers:{...req.headers(),
      authorization:'Bearer '+TOK, 'x-binobi-csrf':'1'}});
  });
  ```
  This makes the SPA fully authenticated without a real cookie.
- `ffuf` on 1,935 POST paths and 403 GET game-launch paths → 0 hits. `nuclei` (5.7k templates,
  43k requests, 22 min) → only `/metrics`. Both runs are worth recording as coverage.
- Minified 5.4 MB `_app.js`: never `grep` it line-wise (60 s timeout); use
  `d.find(needle)` + slice in Python.

## 9. Honest coverage at end of session

Tested: programme/scope, full bundle + 60 page chunks, 196-path API inventory, auth (wallet/email/
Google/Telegram/JWT), session+refresh+logout, IDOR sweep, promo/bonus/ticket/wheel, withdraw ladder,
PSP create endpoints, role/admin endpoints, header spoofing, ffuf, nuclei, subdomain/DNS, mirrors.
Blocked: PSP callback forgery (needs a real deposit), game launch / in-house RNG (needs a funded
account), bonus wager manipulation (needs a deposit). No Critical/High found; the strongest verified
items were unauth `/metrics`, email-verification-less signup, and signup 500s.
