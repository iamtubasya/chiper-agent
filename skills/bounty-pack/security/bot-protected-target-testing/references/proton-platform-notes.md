# Proton platform notes (bug bounty engagement, 2026-10-20)

Program: proton.me/security/bug-bounty — report to security@proton.me (PGP key published).
Reward table (official): Critical $25k-50k, High $2.5k-25k, Medium $1k-2.5k, Low $0 default.
Adjudication weighs preconditions, impact scope, chain value, exploitability, novelty,
submission quality.

## Scope (explicit list only — anything unlisted is excluded)

In: proton.me, account.proton.me, mail.proton.me + api.protonmail.ch, calendar/drive/docs/
pass/wallet/lumo.proton.me, protonvpn.com + account.protonvpn.com + api.protonvpn.ch,
simplelogin.io + app.simplelogin.io, standardnotes.com + app.standardnotes.com, plus the
mobile/desktop apps of those products.
Out: DoS, social engineering, user phishing, WordPress bugs, shop.proton.me (Shopify),
script exec on sandboxed domains, "intended behavior" reports (ineligible for reward).

## Account provisioning under anti-abuse

- ProtonCAPTCHA (jigsaw puzzle, `account-api.proton.me/captcha/v1/assets/?purpose=signup`)
  gates signup; SimpleLogin register uses hCaptcha (checkbox, escalates to drag challenge).
  Both defeat naive automation. SN uses the same ProtonCAPTCHA.
- Disposable email domains are blocked at signup ("Email domain not allowed" inside the
  challenge iframe) and at wallet invites (422 "Invitation cannot be sent to this address").
  Use the "Get a new encrypted email address" (proton.me username) path — no external email.
- Anti-abuse is risk-based: the captcha appears intermittently, and after repeated attempts
  the form silently stops submitting (no captcha, no error). A fresh username plus a fresh
  persistent browser profile resets it.
- Working pattern: headed browser + one manual captcha solve by the operator, then poll for
  the URL change and save the session. Template: `templates/headed_captcha_handoff.py`.
- Login (as opposed to signup) needs no captcha — re-login with the password works.

## Session/auth mechanics — read BEFORE any authenticated probing

- Per-app session UID: mail/drive/wallet/calendar/docs each get their OWN `x-pm-uid`.
  Probing app B's API with app A's uid gives 422 Code 5003 "This web page is out of date"
  or 401 "Invalid access token". ALWAYS capture the target app's real request headers
  (`x-pm-appversion` + `x-pm-uid`) from its own traffic before hand-crafting fetches.
- `x-pm-appversion` format is `web-<product>@<version>` (e.g. web-mail@5.0.136.5,
  web-wallet@0.0.76.0, web-calendar@5.0.0, web-account@1.0.0). A stale version triggers
  422 Code 5003; an invalid product name triggers 422 Code 2064.
- API Accept header: `application/vnd.protonmail.v1+json`.
- Session fork flow: `POST /api/auth/v4/sessions/forks` body
  `{"ChildClientID":"web-mail","Independent":0}` (Independent is a BoolInt INTEGER, not a
  JSON bool) returns `{"Selector":"<32-char>"}`. `GET /api/auth/v4/sessions/forks/{selector}`
  from an UNAUTHENTICATED client returns full-scope AccessToken+RefreshToken — reported as a
  finding (the `sk` in the authorize URL fragment is not required for the token grant, only
  for payload decryption). Forks are single-use with a 24h expiry; the claim request path
  contains the selector (server-log surface).
- Clearing Playwright profile cookies mid-engagement destroys the HttpOnly session AND
  persists the logged-out storage_state — the next run starts logged out. Re-login requires
  the full password flow. Do not "clean up" cookies on a live test-account profile.

## API surface notes (authenticated)

- Wallet (`web-wallet@0.0.76.0`): `POST /api/wallet/v1/wallets/{id}/accounts/{aid}/transactions`
  takes TransactionID/HashedTransactionID as **valid PGP data** (E2E metadata) plus a
  client-signed SignedTransactionHex — the server never holds keys. Field casing is
  case-sensitive: `InviterAddressID` (capital ID) on the invites endpoint even though the
  error message spells `InviterAddressId`. ID format is validated before ownership checks.
- Mail (`web-mail@5.0.136.5`): /api/mail/v4/conversations, /messages, /api/core/v4/users,
  /addresses, /keys/all, /api/auth/v4/sessions (session inventory), /api/payments/v5/status
  and /methods. Observed scope enforcement: password change blocked ("password" scope
  missing), session revocation blocked ("locked" scope missing).
- Calendar: /api/calendar/v1/booking (public booking pages), /api/calendar/v1/directory?Type=2.
  Subscription-URL SSRF endpoint not confirmed — needs the app's exact session uid.
- Lumo guest session (created by visiting a dead share link `lumo.proton.me/u/0/c/{id}`):
  POST /api/ai/v1/chat/completions works with a 20-message limit, enforced (429 after);
  basic prompt-injection attempts resisted; user-data endpoints return 401.
- Standard Notes API is version-gated: send `x-application-version: Web-3.202.10` and
  `x-snjs-version: 2.212.6` or every call returns 400 "client version no longer supported".
  standardnotes.com serves a static `Access-Control-Allow-Origin: *` (not reflected, no
  credentials) — not exploitable.

## Structural takeaways

The E2E architecture blocks the classic bug classes by design: the server never sees
plaintext (no malicious file/image parsing → no parsing RCE), all object IDs are random
(no enumeration IDOR), keys stay client-side. The productive surfaces are auth/session
mechanics (the fork finding), business logic, public-link authz, and newer features
(bookings, wallet invites, Lumo). A second test account is required for cross-account
IDOR — provisioning one costs one more manual captcha solve.
