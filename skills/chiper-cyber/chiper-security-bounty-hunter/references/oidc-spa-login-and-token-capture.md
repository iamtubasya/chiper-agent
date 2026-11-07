# OIDC / Duende IdentityServer SPA Login Automation (for authenticated API testing)

Use when a bounty target's API is OAuth2/OIDC-secured (Duende / IdentityServer4)
and you need an authenticated bearer token to test IDOR/BOLA/2FA/business-logic.
Applies to any SPA (React/Vue/Vite) whose login redirects through a
`/connect/authorize` flow.

## 1. Recover the OIDC client config from the SPA bundle
The SPA hardcodes its OAuth client. Grep the main JS bundle:
- `grep -oE 'client_id[=:"]{1,2}[^,"]{2,60}' bundle.js`  → public client_id
- `grep -oE '(authority|di)="https://[^"]+"' bundle.js`  → authority / issuer
- `grep -oE 'scope:[^,}]+' bundle.js`                     → scopes (look for `offline_access`)
- `grep -oE 'redirect_uri:[`"'"'][^`"'"']+` bundle.js     → registered redirect

Also fetch `GET <authority>/.well-known/openid-configuration` for token_endpoint,
jwks_uri, and PKCE support (`code_challenge_methods_supported`).

## 2. Client-side password hashing (CRITICAL, easy to miss)
Many IdPs hash the password in JS before POST. Look for a `PasswordHash` hidden field
or an `hmacSha256Async` helper in `site.js`. Common scheme:

    passwordHash = HMAC-SHA256(email.toUpperCase(), password)   # hex

Submit `Input.PasswordHash=<hash>` and leave `Input.Password` EMPTY. Submitting the
plaintext password is rejected with "The PasswordHash field is required."

## 3. Email-based 2FA
The 2FA code is single-use and emailed. Read it from the mailbox (himalaya:
`himalaya envelope list | grep -i 2fa`, then `himalaya message read <id> --raw`).
Submit `Input.TwoFactorCode=<6digits>`. Each login attempt mints a NEW code — use the
newest matching email, and don't reuse a stale code from a prior attempt.

## 4. PKCE authorization code → token
```
verifier  = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
```
Exchange: `POST /connect/token` with `grant_type=authorization_code` + `code` +
`code_verifier` + `redirect_uri` + `client_id`.

## PITFALLS (these cost real iterations)
- **Capture the refresh_token immediately.** Access tokens are short-lived (~15-30 min).
  The refresh_token is long-lived; persist it, then mint fresh access tokens via
  `grant_type=refresh_token` + `client_id` + `refresh_token` (no verifier needed).
- **Browser sessionStorage / idsrv.session resets on navigation.** Cloudflare challenge
  or cross-origin navigation can clear the SPA session between steps. Read the token out
  in the SAME tool call as login success — do not navigate away first.
- **A new login invalidates prior tokens.** Logging in again revokes the previous
  access+refresh tokens. One clean login → immediately persist the refresh token.
- **Manual PKCE vs the SPA's own challenge.** If you hand-craft the `/connect/authorize`
  URL with your own `code_challenge`, the SPA's JS will try to exchange the resulting
  code with ITS OWN verifier → `invalid_grant`. Either let the SPA drive end-to-end, or
  do the whole flow yourself and exchange the code with YOUR verifier before the SPA
  consumes it (authorization codes are single-use).
- **Bearer header format is usually `Authorization: Bearer <access_token>`**, but some
  APIs use `X-Api-Key` / `X-Token`. Probe cheaply: hit a known 200 endpoint with each.

## Verification loop
Once you have an access token, confirm against a known-authenticated endpoint
(e.g. `/api/v1/wallets`) → expect 200. Then start the IDOR/BOLA matrix.

## Operational shortcut
Anti-bot friction (Cloudflare session reset, single-use 2FA, short-lived tokens) makes
scripting the full login flow expensive. For a user who already has the target open in
a browser, asking them to paste `oidc_token` + `oidc_refreshtoken` from DevTools →
Application → Session Storage is 10 minutes of their time vs. many agent iterations.
