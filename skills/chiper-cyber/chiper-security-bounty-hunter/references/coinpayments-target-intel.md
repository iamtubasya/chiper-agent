# CoinPayments Bug Bounty — Target Intel (session-specific)

Self-hosted VDP/bounty. Scope `*.coinpayments.net` `*.gocps.net` `*.coinpayment.net`
`*.coinpayments.com`. Report: security@coinpayments.net. Payout USDT/USDC (Very Low $50+
→ Critical $1000+, incl. "unauthorized access to user wallets"). Policy page:
https://www.coinpayments.net/vulnerability-disclosure-bug-bounty-program

## Auth / OIDC
- authority: `https://auth.coinpayments.net` (Duende/IdentityServer)
- client_id: `coinpayments-aphrodite-pkce`
- scope: `openid profile orion offline_access`
- redirect_uri: `https://a-dashboard.coinpayments.net/callback`
- password = HMAC-SHA256(email.toUpperCase(), password) → submitted as `Input.PasswordHash`
- 2FA via email (Amazon SES). Single-use, 15-min window.

## Backends / environments (from dashboard bundle env→host map)
- `a-api.coinpayments.net` = `Production-NEBVEN`  (real prod)
- `api.coinpayments.net`   = `Production-SANDBOX` (publicly exposed sandbox)
- `b-api.coinpayments.net` = `"b"`  — NOT yet enumerated → probe it
- `c-api.coinpayments.net` = `"c"`  — NOT yet enumerated → probe it

## API surface (110 routes, mined from docs.coinpayments.net lazy chunks)
Mining technique: fetch `docs.coinpayments.net/assets/index-*.js`, extract the ~149
lazy chunk names, download each, grep `path:"/api/..."` + nearby `method:`/`version:`.
- Public (no auth): `/api/v1/currencies`, `/rates`, `/conversions`,
  `/fees/blockchain/:id`, `/env` (returns env name + identityBaseUrl)
- Merchant (Bearer auth; all correctly 401 unauth): `/api/v1|v2|v3/merchant/wallets*`,
  `/merchant/invoices*`, `/merchant/clients*`, `/merchant/currencies`
- User: `/api/v1/user/profile|teams|2fa|kyc`, `/settings`, `/referral-codes`
- Partners: `/api/v1/partners/{osl,ramfi,phaze,banxa}/*`
- Refund status (public): `/api/v1/refunds/{refundid}/{tag}`, `/api/v2/refunds/{emailSecret}`
- Wallet vault: `/api/v1/wallets/lock-vault`, `schedule-unlock-vault`, `two-fa-unlock-vault`
- Invoice ID = 32-hex GUID (no dashes). Buyer-facing:
  `/api/v1/invoices/{id}/payment-currencies/{currency}[/status]`

## Validated as NOT vulnerable (don't re-test / re-spend iterations)
- All merchant routes → 401 unauth (auth solid)
- 405 vs 401 on `/settings`, `/esims`, `/partners/osl/counterparties` = method binding,
  not bypass (tested all 8 HTTP methods)
- `legacy.coinpayments.net/api.php` → HMAC→API-key check order correct
- `userfiles.coinpayments.net` → no public service, path traversal blocked
- `influx-rabbit.coinpayments.net` → 503 nginx (no origin)
- WordPress `blog`/`signup` → REST locked (401 / CF challenge)
- `gocps.net` shortener → no open redirect/reflection (ID format = path segment)
- OIDC `redirect_uri=evil.com` → 302 to `/Error` (NOT confirmed injection; needs a live
  auth session to verify whether a code is actually issued)

## Test accounts (both send email to the SAME Gmail inbox)
- A: `chiperflux15@gmail.com` (walletId `873194a2-93f5-452f-8446-c0c25dacaf0a`, Solana)
- B: `chiperflux.15@gmail.com` (Gmail dot-alias → separate CoinPayments account)

## Next (high-value, needs TWO live sessions simultaneously)
IDOR/BOLA matrix: token A → resource B across `/merchant/wallets/:id`, `/settings/all`,
`/referral-codes/:id`, `/invoices/:id`. Crown jewels: spend/consolidation/vault/2FA flows.
Refund IDOR: test whether `/api/v1/refunds/{refundid}/{tag}` and `/api/v2/refunds/{emailSecret}`
leak cross-tenant status (tag/secret entropy assessment).
