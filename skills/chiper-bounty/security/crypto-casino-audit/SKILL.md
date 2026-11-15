---
name: crypto-casino-audit
description: "Use when auditing an online casino / sportsbook / crypto-gambling operator (own in-house bug-bounty program)."
version: 1.0.0
author: hermes-curator
license: MIT
sources: engagement_derived
metadata:
  hermes:
    tags: [security, bug-bounty, igaming, casino, gambling, wallet, bonus-abuse, payments, nextjs, business-logic]
    related_skills: [authed-webapp-audit, hunt-business-logic, hunt-race-condition, unauth-config-disclosure, hunt-idor, report-writing]
---

# Crypto Casino / iGaming Operator Audit

## When to Use

Load this when the target is an **online casino, sportsbook, or crypto-gambling operator** —
especially one that runs its own bug-bounty program (no HackerOne/Bugcrowd in front, submit by email).
Typical signs: `/casino`, `/slots`, `/live`, `/crash`, "provably fair", "cashback", "rakeback",
"VIP levels", "free spins", "lucky wheel", wallet with crypto deposit networks.

These targets are **not** normal SaaS. The money is not in auth bypass alone — it is in the
**bonus/wager ledger**, the **PSP callback path**, and the **in-house RNG**. The programme's own
reward table tells you exactly which of those it pays for; read it first and rank your effort by it.

## The programme's reward table IS your priority queue

Casino programmes publish a severity ladder that maps almost 1:1 to bug classes. Read it before
touching anything, then work down the list — a class that pays $300k is worth ten hours, a class
capped at $500 is worth ten minutes.

A real example (Binobi, 2026-10) — the shape repeats across operators:

| Class | Ceiling | What actually qualifies |
|---|---|---|
| Hot-wallet drain | $300k | Withdraw funds from operator hot wallets |
| Account penetration | $40k | Access someone else's account |
| Balance manipulation | $30k | Fabricate / inflate a user balance |
| In-house game exploit | $25k | House-edge bug, or win consistently |
| Server vulnerability / DDoS | $20k | Partial/total outage |
| Bonus abuse | $10k | Mining, Charge, rakeback, cashback, referral |
| Aggregator game exploit | $5k | Third-party provider games |
| Medium functional bug | $500 | Non-cosmetic functional defect |

Two consequences:

- **"Balance manipulation" is the sweet spot.** It is reachable from an account you own, needs no
  victim, and pays 30× the functional-bug tier. Spend your time on the ledger, not on XSS.
- **In-house games pay; aggregator games mostly don't.** Aggregator slots run on the *provider's*
  server (you are testing someone else's code through the operator's proxy). The operator's own
  crash/dice/mines/plinko/wheel are where the operator's own logic lives.

## Step 1 — Map the money flow before probing anything

Write this flow out for the target; every finding comes from one of the arrows.

```
signup → KYC? → deposit (PSP invoice) → PSP callback credits balance
       → wager (game launch / bet) → win/lose settles balance
       → bonus accrual (wager goal) → rakeback/cashback claim
       → withdraw (network + address) → operator payout
       + referral commission, lucky wheel, daily quests, promos/promocodes
```

Ask at each arrow: *who computes this value, and can the client influence it?*

- **Deposit credit** ← computed by the PSP callback handler. Test the callback's signature check.
- **Wager progress / bonus unlock** ← computed from bet volume. Test whether the client can post bets.
- **Cashback / rakeback** ← computed from net loss. Test the claim endpoint for amount injection.
- **Referral commission** ← computed from referee deposits. Test attribution (self-referral).
- **Wheel / quest reward** ← server picks the award. Test whether the *award id* is client-supplied.

## Step 2 — Recon: find the real API, don't wordlist

Casino front ends are almost always a marketing SPA in front of a separate API host.

### 2a. Next.js rewrite → separate API host (very common)
Read `/_next/static/<buildId>/_buildManifest.js` — it contains `__rewrites`, which names the proxy
rule. On Binobi it was:

```
/:locale/_binobi/api/:path*  ->  /api/mirror/:path*
```

meaning the SPA's `/…/_binobi/api/games/list` and the public host `api.<domain>/games/list` are the
same backend. That gives you a **second, differently-fronted path to every endpoint** — useful when
Cloudflare rules differ per hostname, and it gives you the real `api.` host for direct probing.
The same file's `sortedPages` list is a free route inventory for the web tier.

### 2b. Chunk harvest = full internal route list
`_buildManifest.js` also lists every page chunk. Download them all and grep for quoted paths — the
authenticated pages (`/account/*`, `/verification`, `/referral/*`, `/cashback`, `/wheel`) are
lazily loaded and their chunks carry API paths the landing page never mentions.

```bash
# grab chunk names from the manifest, then fetch each (URL-encode [id]/[tab] segments or use -g)
curl -sS "https://<host>/_next/static/<buildId>/_buildManifest.js" -o bm.js
grep -oE 'static/chunks/pages/[^"]+' bm.js | sort -u
```

Then grep the *app* bundle (multi-MB, minified) with **windowed Python**, never `grep` on the whole
line: `i=d.find("/referral/"); print(d[i-400:i+300])`. Extract the API helper calls — the pattern
`.Ay.post("".concat(i.C1,"/ticket/lucky-wheel"))` hands you method + path in one line.

Also localise: `/{locale}/{ns}.json` namespace files (`vault.json`, `ticket.json`, `wheel.json`,
`ranks.json`) describe features that may not be linked in the UI at all. `vault.json` on Binobi
revealed a player-to-player **tips** feature ("Send Tips", username + currency + amount) that no
menu item pointed at.

### 2c. `/metrics` on the API host is an architecture oracle
See `security/unauth-config-disclosure` §"Prometheus / exporter endpoints". On this class it is
unusually valuable because the metric labels name the operator's **PSP integrations** and the
**callback outcome taxonomy** (`invalid_signature`, `duplicate`, `deposit_credited`, `review`), i.e.
it tells you which payment callback to attack and which error strings it returns.

### 2d. The estate beyond the apex
- Mirror domains are real: `binobi.casino/.io/.in/.mx` all served the app, and `api.binobi.io`
  answered the full API + `/metrics`. **Mirrors frequently have looser WAF rules than the apex.**
- `crt.sh` gives the admin/affiliate hosts (`admin.`, `affiliates.`, `affiliates-admin.`) — usually
  NXDOMAIN or 403 from outside, which is itself a legitimate negative to record.

## Step 3 — Get an account WITHOUT the captcha loop

Casino signup is Turnstile-protected and disposable-email-blocked. Plan for it; do not brute the
widget.

- **The Turnstile token is reusable across the registered host.** Harvest it once from a headless
  browser (`input[name="cf-turnstile-response"]` gets a value after the widget self-solves), then
  POST it to the API yourself. The same token also validates against `/auth/validate-captcha`
  (`201 {"status":"success"}`) — and note that validate-captcha **accepts** a token that
  `/auth/forgot-password` **rejects** with `error_auth_captcha_failed`, so a "captcha failed" on a
  specific endpoint is not proof the token was bad; the endpoint may just be stricter or broken.
- **Disposable-domain blocklist is real and it lies about the shape.** `mail.tm`, `yopmail`,
  `guerrillamail` → `error_auth_register_disposable_email`. A real provider works. Use a Gmail
  **plus-alias** (`you+tag@gmail.com`) or a second real mailbox you control.
- **Wallet login is often the easiest account mint and skips the captcha entirely.** See Step 4.

Reference implementation of all three paths (headless token harvest, plus-alias registration,
wallet sign-in) with the exact request shapes: `references/binobi-engagement.md`.

## Step 4 — Auth surface of a crypto casino

### 4a. Wallet-signature login (MetaMask / TON / Binance)
Two-step, and the second step is where the detail lives:

```
POST /auth/strategies/metamask/message  {"address":"0x…"}   -> {"result":{"message":"Login at <ts>. Nonce: <hex>"}}
POST /auth/strategies/metamask          {"address","sign","language","browserData","isLogin"?, "email"?}
```

What actually matters when testing it (each was measured):

- **The signed message is a plain-text string, not EIP-712.** `eth_account.messages.encode_defunct(text=msg)`
  works; prepend `0x` to the signature if your library omits it.
- **Signature verification is real.** Signing account A's message with account B's key returns
  `403 error_auth_wallet_invalid_signature`. Do not report "wallet auth forgeable" — test it first,
  it usually holds.
- **Nonce is single-use and short-lived** (`403 error_auth_sign_not_found_or_expired` on replay).
- **Sending extra body fields can break the lookup.** Adding `address` to the *second* request (when
  it is already implied) returned `sign_not_found_or_expired`; the same call without it succeeded.
  When a signature "expires" instantly, retry with the minimal body before concluding anything.
- **`email` is optional on the FIRST registration but mandatory on later ones** —
  `error_auth_email_is_missing` then `error_auth_account_already_taken` / `error_auth_register_duplicate_wallet`
  are the three states. That sequence is how you learn the account exists without owning it.
- **`X-Binobi-CSRF: 1`-style header is required on state-changing calls** (403 "Invalid auth origin or
  CSRF headers" without it). It is a static value copied from the bundle, not a token — read it out of
  the app chunk (`e.set("X-Binobi-CSRF","1")`) rather than guessing.

### 4b. Email registration often skips verification — check it explicitly
On Binobi, `POST /auth/register` returned `201` **with a bearer token and both refresh/access cookies**,
while the confirmation email endpoint (`/auth/confirm-email/request`, `201 {"status":"success"}`) was
purely cosmetic: the account was fully usable and `isVerified:false` only gated withdrawals.
**That is a reportable hardening gap on this class** (bonus/referral/quest abuse needs many cheap
identities), though usually Low unless combined with a bonus that pays per account.

### 4c. Session/refresh battery — the class's most repeatable finding
These apps use a rotating refresh cookie (`__Host-<brand>-rt`, HttpOnly/Secure/SameSite=Lax) plus a
short-lived access JWT in `__Host-<brand>-at` and/or an `Authorization: Bearer` header.

Run these four, in order, and record answers as a table:

1. **Rotation:** login → `POST /auth/refresh` → is the refresh cookie value different? (should be)
2. **Replay:** put the OLD cookie value back → `POST /auth/refresh`. `200` + a new token means the
   old token was never invalidated. On Binobi this returned `200` every time, and the same RT could be
   replayed indefinitely, each use yielding a fresh RT — **refresh-token replay works**.
3. **Revocation on logout:** `POST /auth/logout` (204) → replay each previously captured RT. On
   Binobi *every* historical RT still worked **after logout** — logout only killed the newest one.
   This is a genuine "session termination is not effective" finding: a stolen RT survives the
   victim's logout/password-change remediation. Frame it with the capability test — what does the
   replaying attacker gain? (a fresh access token = full account, including the wallet UI).
4. **Cross-account:** confirm the RT from account A cannot be used against an endpoint that returns
   account B's data (it should be scoped; verify, don't assume).

Do NOT confuse #2/#3 with "JWT forgery" — the JWT itself is usually HS256 with a server-only secret
and is not forgeable. The finding is lifecycle, not crypto.

## Step 5 — The money-logic battery

Every one of these is a class the programme pays for. Test in this order (cheapest first).

### 5a. Withdraw validation (do this first — it is 20 minutes)
`POST /withdraw {amount, currency, address, network}`. Enumerate the validation ladder and record it:

```
amount=-100  -> error_withdraw_invalid_amount
amount=0     -> error_withdraw_invalid_amount
amount=1e-8  -> error_withdraw_minimal_withdraw
amount=100   -> error_withdraw_invalid_address      (address format checked per network)
valid addr   -> error_withdraw_not_enough_balance
IDR+FIAT     -> withdraw_wrong_currency ("withdraw allow only with USDT currency")
```

A clean ladder = **negative**, and it is worth recording as one, because it tells you the withdraw
path is not where the bug is. What you are hunting: an amount/currency/network combination that
*skips* the balance check (e.g. a FIAT path that debits a different ledger), a `network` that the
address validator does not actually check, or a negative amount that survives to the ledger write.
`amount` as a **string** (`"100"`) is worth trying on every numeric money field — it passes `Number()`
coercion in some stacks and breaks strict validation in others.

### 5b. Bonus / wager ledger
- `GET /bonuses/v2/available` lists bonus definitions **with their `id`, `spins_amount`, `endAt`,
  and `bonusGames[].id/gameId`** — that is the client-supplied material for the claim call.
- `PATCH /bonuses/v2/issue-freespins-bonus?bonusId=…&gameId=…` — note the **PATCH with query
  params and an empty body**. Two distinct errors to distinguish: `game_does_not_exist` (wrong id
  shape — it wants the *bonusGames[].id*, not the slug) vs `deposit_need_transaction_first` (the
  real gate: a deposit is required). Repeating the call N times to see if the gate is idempotent is
  a legitimate test; a gate that is only checked *once* is the bug.
- `GET /balance/bonus` exposes `amount`, `bonusAccruals`, `wager`, `wagerGoal`, `wagerStartDate`.
  If any of those are writable through a PATCH/POST on the same resource, that is balance
  manipulation. Test `PATCH`/`PUT`/`POST` on `/balance`, `/balance/bonus`, `/cashback-balance` —
  on Binobi all returned `403`/`404` (correct), so this is usually clean; record it.
- **Wager goal arithmetic**: `wagerGoal` should be a fixed multiple of the bonus. Check whether the
  goal is recomputed server-side after a top-up (a top-up that *reduces* the remaining wager, or a
  claim that resets `wager` to 0, is the classic bug).

### 5c. Lucky wheel / daily quest / promo claim — race + client-supplied award
- `POST /ticket/lucky-wheel` returns `{"result":{"id":13}}` — the **award id**, which the UI then
  looks up in a hardcoded client table (`{id:13, value:0.1, currency:"BTC", angle:308}` …) to render
  the win. The client table is cosmetic; the credit is server-side. What to test: whether the award id
  is *echoed* from a request field anywhere, and whether the cooldown is enforced atomically.
- Cooldown test: `GET /users/lucky-wheel-time` → `nextLuckyWheelSpinTime`. Fire 12 concurrent spins
  (ThreadPoolExecutor). Healthy result on Binobi: **1 × 201, 11 × 400 error_ticket_time** —
  atomically gated, no race. Record that explicitly as a verified negative; it is a class the
  programme pays $10k for and a clean "no" is a real result.
- `POST /ticket/buy {quantity:1}` → `error_ticket_balance_usdt_not_found` — tickets are bought with
  balance, so this path is gated behind a deposit like everything else.
- Free-spin eligibility has a *second* gate beyond the daily timer:
  `hasLuckyWheelDepositLast7Days` (deposit within 7 days) — the UI computes it client-side from
  `totalDepositsLength` and `createdAt`. **If the server trusts the client's `userCreatedAt` in that
  computation, a fresh account can mint the "deposit last 7 days" state.** The bundle literally posts
  `{userCreatedAt: t.createdAt}` to a server action to decide — chase that.

### 5d. Deposit creation + PSP callbacks (highest value, hardest to prove)
Front-end paths hand you the PSP integration names (`/moneygrator/create`, `/avepay/create`,
`/settle/create/processing/inr`, `/ex-gateway/crypto/invoice`, `/fxmb/deposit`,
`/deposit/expay/create_wallet`). Test the **create** side first — it is a read-only invoice mint:

- `POST /ex-gateway/crypto/invoice` → token enum (BNB,BTC,DOGE,ETH,USDTTRC,USDTERC…), `amount`,
  `currencyForTopUp`. Note the `currencyForTopUp must be one of: ` with an **empty** enum list — a
  validation error that leaks an empty whitelist is worth a second look (it means the config array is
  empty server-side; the field may be ignored entirely).
- `POST /ex-gateway/acquiring` → `amount` 1000–499999 + `cardDetails` — a card-acquiring invoice.
- `POST /moneygrator/create` → `amount` 100..500000.

The callback handler itself is the prize (`invalid_signature` occupies 93% of the metric's events on
Binobi, which tells you it *is* signature-checked and that bots are already hammering it). **Do not
report a callback bypass you have not demonstrated with a real, credited deposit** — you cannot
prove "balance credited without payment" from the outside without either a payment or a signature
forgery, and a claimed bypass with neither is the single most likely way to get closed as
unreproducible on this class. If you cannot prove it, write it up as an open lead with the exact
missing step.

### 5e. Referral / affiliate
- `GET/POST /referral/campaigns` — creating a campaign returns `link:"/?r=<token>"`. Test:
  **self-referral** (register through your own link), campaign-id ownership (A's `campaignId` on B's
  token → `error_campaign_not_found`, correct on Binobi), and whether commission is computed from
  the referee's *deposit* or from a client-settable field.
- `GET /referral/campaigns/full?campaignId=<uuid>` is the per-campaign stat endpoint; a
  cross-account read there is a clean IDOR if it works (it did not on Binobi — 404, correct).

## Step 6 — Game launch / in-house RNG (the gate everything hides behind)

The game-launch call is **not in the client bundle** as a normal API path — the preloader page renders
and the launch is issued only after a balance exists. Two things to do:

1. **Try the obvious launch paths anyway** (`/games/<id>/launch`, `/games/session`, `/games/url`,
   `/play/<id>`, …) with an authed token. A uniform 404 set tells you it is not a guessable path.
2. **Drive it in a browser with the token injected** (see the Playwright recipe in
   `security/authed-webapp-audit` §"Headless authenticated crawl"). Even with a valid session the
   Binobi preloader issued *no* launch call — because there was no balance. Reaching the RNG
   surface requires a funded account; say so instead of claiming the surface was tested.

If the programme pays $25k for in-house exploits, a funded account is the cost of doing business on
that class. Do not silently skip it — report it as an explicitly blocked class with the reason.

## Verified-negative library (record and reuse — do not redo)

These were each measured on Binobi and are the *expected* state for a modern operator. Knowing them
saves a whole session and makes the eventual positive credible.

| Test | Expected result | On Binobi |
|---|---|---|
| Cross-key wallet signature | 403 invalid_signature | ✅ held |
| Signed-message replay | 403 sign_not_found_or_expired | ✅ held |
| Internal header spoof (`X-Forwarded-For`, `X-Original-URL`, `X-User-Role`, `X-Admin`, …) | no effect | ✅ held (all 17 variants) |
| `POST /balance`, `PATCH /users/<field>` | 403 Forbidden resource | ✅ held |
| Cross-tenant campaign/stat read | 404 error_campaign_not_found | ✅ held |
| Withdraw amount/address/network ladder | full validation | ✅ held |
| Wheel cooldown race (12× concurrent) | 1 success, N-1 `error_ticket_time` | ✅ held |
| Google/Telegram OIDC `alg=none` | rejected (nonce checked first) | ✅ held |
| `PUT/POST` on `/files/<uuid>` | 404 File not found | ✅ held |
| Admin/affiliate subdomains | NXDOMAIN or 403 | ✅ NXDOMAIN |

## Pitfalls

- **Distinguish `Cannot GET /path` (404 route-miss) from `{"message":"Forbidden resource","error":"Forbidden","statusCode":403}`.**
  The 403 form means the route **exists** and NestJS's guard rejected you — that is a real endpoint
  you found, and it belongs in the surface map even though it is not a bug. 404 means the route is
  not there. Never collapse the two in your notes.
- **A `404` body with a `{"type":"error_…","code":400}` shape is a business error, not an HTTP 404.**
  Binobi returned `404` with `{"type":"deposit_need_transaction_first","code":400}` — the status code
  lies. Always read `type`/`code` in the body.
- **`error_auth_captcha_failed` on one endpoint may be endpoint-specific.** A token that
  `/auth/validate-captcha` accepts can still be rejected by `/auth/forgot-password`. Retest the token
  against validate-captcha before blaming your harvester.
- **Registration 500 on alias-style emails is a real signal, not noise.** `you+tag10@gmail.com` and
  `fz.susanto13@gmail.com` returned `500 Internal server error` while `you@googlemail.com` returned
  `201`. That is a crash/DB-constraint path in the signup handler — worth a second and third attempt
  with variations before writing it up (it may be a transient), but it is exactly the kind of
  unhandled-exception surface this class forgets.
- **Do not report the pre-auth `/metrics` as a high.** It leaks architecture, not customer data.
  It is Informative/low on its own — its real value is that it names the PSP integrations and
  callback outcomes you then go attack. Say so plainly.
- **A casino bonus gate is usually a deposit gate.** When every path ends in
  `deposit_need_transaction_first`, you have hit the economic gate, not a bug. The honest report is
  "classes A–E blocked behind deposit; classes F–J verified negative", never "target clean".

## Reporting

- Submit where the programme says (these operators typically use a plain `support@` mailbox, not a
  platform) and duplicate Critical findings into Live Chat when they ask for it — they do.
- Their rules are almost always: no public disclosure, do not touch other users' data, step-by-step
  repro + evidence of the result. Honour them; non-compliance forfeits the reward.
- One finding per root cause; lead with the impact in their own vocabulary (`balance manipulation`,
  `account penetration`) because that is how they tier it.
- Companion skills: `report-writing` for format, `evidence-hygiene` for redaction,
  `security/unauth-config-disclosure` for the `/metrics` write-up.

## Supporting files

- `references/binobi-engagement.md` — full worked surface map: the Next.js rewrite discovery, the
  196-route internal API inventory, the three account-mint paths (Turnstile harvest / plus-alias /
  wallet signature) with exact request bodies, the refresh-token replay + post-logout survivability
  result, the `/metrics` label dump, the wheel cooldown race, and the complete verified-negative list
  with the response strings to expect.
