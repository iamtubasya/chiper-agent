# Citronus (citronus.com) — worked CEX surface map (2026-11)

Target: crypto exchange (spot + futures), native token CITRO, own EVM chain id 50000
(Blockscout explorer). Submit `info@citronus.com` (RU/EN). reCAPTCHA v3 threshold 0.5.

## API base URLs (from `super("https://…")` in index-*.js)

| Base | Purpose |
|---|---|
| `https://api.citronus.com/sso/` | auth, user/info, KYC, refcodes, mfa/subscription |
| `https://api.citronus.com/wallets/` | balances, limits, transactions, ws token, bonus transfer |
| `https://api.citronus.com/crypto/` | deposits, withdrawals |
| `https://api.citronus.com/spot/api/` | spot orders |
| `https://api.citronus.com/futures/` | futures orders, positions, balance |
| `https://api.citronus.com/staking/` | staking orders |
| `https://api.citronus.com/referrals/` | inviter/invitees/incomes/levels |
| `https://api.citronus.com/public/` | API keys |
| `https://api.citronus.com/notifications/` | notification list + ws token |
| `https://api.citronus.com/admin/api/` | contest-config, feature-flags, live-panel |
| `https://api.citronus.com/user-deletions/` | aggregated-info, users/delete |
| `https://api.citronus.com/maintenance/` | v1/configurations, v1/status |
| `https://api.citronus.com/` (root base) | address-validator/validate |
| `https://explorer.citronus.com/api/v2/` | explorer |

WebSocket: `wss://api.citronus.com/{wallets|notifications|coins}/ws/…/subscribe/?access_token=<43-char
opaque>`. WS tokens are 256-bit random (not JWT), scope resolved server-side from the token.

## Auth flow (OAuth PKCE + email OTP)

1. `POST /sso/registration/email/` JSON `{email,password,marketing_consent,token,referrer_code,
   language_code}` → `{code_uid, expire_after:60}` (60s = resend cooldown, code itself ~10min/1h).
2. `POST /sso/registration/email/confirm/` multipart `{code_uid,code}` → `{token}` (SSO bearer,
   40-hex, single-use).
3. Login: `POST /sso/authentication/login/email/` `{email,password,token}` → `{code_uid,…}`;
   `POST /sso/authentication/login/code/` `{code_uid,code}` → `{token}`.
4. Frontend: `GET /sso/oauth/authorize/` (Authorization: Bearer token, PKCE code_challenge) →
   `redirect_uri` → `/redirect?code=…` → `POST /web/sso/login/callback/?code=…` →
   `{access_token, refresh_token}` stored as cookies `access` (JWT) + `refresh`.
5. Refresh: `POST /web/sso/login/refresh/` multipart `{refresh_token}`.

JWT (access): `{alg:RS256, kid:…}`; payload `{exp, uid:<uuid>, sub:<numeric id>, client_type:"user",
username, roles:["common"], permissions:[]}`.

## Account mint (Playwright, reCAPTCHA v3)

- Register page: `/auth/register?response_type=code&code_challenge=…&client_id=z2GjXLkp…&redirect_uri=https://citronus.com/redirect`.
- Step 1: `#auth_email` + check the first `input[type=checkbox]` (terms — button stays disabled
  without it) → Continue (`data-testid=formSignInSingUpButton`).
- Step 2: `#auth_password` + `#auth_repeatPassword` (min 8, upper/lower/digit/special `.,-^$?*+()[]{}@<>`).
- Step 3: 6 boxes `input[inputmode=numeric][maxlength=1]`, fill one digit each → `otpFormVerifyButton`.
- OTP via Gmail API on the plus-alias inbox; take newest 6-digit code not already seen.

Password rule: special chars are a limited set (no `!`, has `@`, `.`, `-`).

## Order schemas + ladders (validated)

- Spot `POST /spot/api/orders/` `{symbol, action:buy|sell, type:market|limit, amount|total, price}`.
  `BTC_USDT` (underscore) → `500 internal_server_error`. `BTC/USDT` correct.
  negative/zero amount → `amount_lower_minimum`; price 0/neg → `total_lower_minimum`;
  valid → `not_enough_amount`.
- Futures `POST /futures/orders/` `{pair:{base,quote}, amount, leverage, side:bid|ask, type, price}`.
  amount<=0 → `invalid_order_amount_zero`; leverage<=0 → 422 `greater than 0`;
  leverage=999999999 → `500 internal_server_error`; valid → `not_enough_amount`.

## Business-logic endpoints observed

- `GET /wallets/v1/limits/rules/` → KYC 0/1/2 caps (e.g. KYC0 daily 1000/5000/15000).
- `GET /sso/kyc/status/all-levels/` → KYC 0 (personal_information), KYC 1 (document_id, photo).
- `POST /sso/kyc/mark-form-filled/ {level_name}` → only flips `form_filled`, NOT a bypass.
- `POST /sso/kyc/access-token/ {level_name}` → 403 before KYC starts (Sumsub).
- `GET /referrals/v1/{inviter,incomes/max,levels/consolidations,invitees}`; income max 70%;
  `refcodes/{generate,parse,set}` under `/sso/`; `set` self → 409 `referrer_already_setted`.
- `POST /wallets/v1/assets/transfers/bonuses/` (no body) → `amount_too_low` when 0.
- `POST /user-deletions/v1/users/delete/` → needs `{code_uid, code}` OTP.
- `GET /user-deletions/v1/aggregated-info/` → per-service order/position counts + allow_deletion.

## Confirmed findings (reported, all Low/Medium)

1. Django admin exposed at `https://api.citronus.com/admin/` (login page, no IP allowlist).
2. `/admin/api/*` served without admin role — `feature-flags/` leaks `smtp4dev_enabled`,
   `prometheus_metric`, `apple_store_app`, `google_store_app`; `contest-config/` leaks
   `contest_run_id`; `live-panel/` leaks token supply split.
3. `POST /sso/reset/password/email/` returns 204 with **no reCAPTCHA** (asymmetric vs login/register).
4. `vault.citronus.com` exposed + unsealed (`/v1/sys/health`, `/v1/sys/seal-status` public;
   secret mounts 403).

## Verified negatives (do not redo)

mass-assign whitelisted · XSS escaped (bio `&lt;…&gt;`, username charset-locked, telegram not set)
· JWT RS256 · SQLi param'd + Cloudflare WAF (`--` → 403) · OAuth redirect whitelisted · IDOR
scoped (notification `?user_id=` ignored) · RPC `personal/admin/debug` = -32601 · OTP 5-wrong →
429 throttle 3599s · Django DEBUG off · Vault mounts 403 · request-signing N/A.

## Robustness notes (not findings)

`POST /address-validator/validate/` returns `{"code":"internal_server_error"}` for ALL inputs
(broken endpoint, not SSRF). Futures `leverage=999999999` → 500 (no upper bound).