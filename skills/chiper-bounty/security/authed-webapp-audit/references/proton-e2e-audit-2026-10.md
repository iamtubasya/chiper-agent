# Proton E2E-suite audit (2026-10-20/21) — per-app sessions, surface map, verified negatives

Engagement: public bug bounty (proton.me/security/bug-bounty, report to security@proton.me).
One valid finding (session-fork token issuance, disclosed). This file captures the **reusable
technique** (auditing a multi-app E2E-encrypted suite with one test account) and the **surface map
with verified negatives** so a future session does not re-derive it.

## Multi-app suite sessions: each app = own forked session (UID + appversion)

Proton web apps (mail/drive/pass/wallet/calendar/docs/lumo) do NOT share one API session. Each app
boots by creating a **session fork** (`POST /api/auth/v4/sessions/forks` on the account host) and
claiming it (`GET <app>/api/auth/v4/sessions/forks/{selector}`). Consequences for auditing:

- **API calls need the per-app `x-pm-uid` + `x-pm-appversion`.** Using the mail UID against the wallet
  API returns 401; a stale appversion returns `422 Code 5003 "This web page is out of date"`.
  Appversions seen: `web-mail@5.0.136.5`, `web-wallet@0.0.76.0`, `web-pass@1.42.0`,
  `web-calendar@5.0.136.4`, `web-account@1.0.0`.
- **Capture, don't guess.** The reliable way to get a valid pair is Playwright
  `page.on("request")` filtered on the app's `/api/` traffic, reading `r.headers['x-pm-uid']` /
  `r.headers['x-pm-appversion']`. Then replay probes with `fetch()` from inside the loaded page
  (credentials ride along). Loading the app fresh each round is required — the UID is per session,
  and an already-open app makes no new API calls to capture.
- **Account-host rate limiting is real.** After ~1 account creation + heavy multi-app testing,
  account.proton.me began timing out (curl 000/20s) while app hosts stayed up. Temporary; retry
  later. Do not read it as a target outage.
- **Pass has an extra unlock layer:** after the fork, Pass requires the account password to decrypt
  E2E keys (`Unlock Pass with your Proton password`, input is `input[name=password]`, dynamic id).
  The fork alone does not unlock vault data — correct design.

## Error-message casing does NOT match the accepted field casing

Proton's API validation messages name fields in one casing while the accepted JSON uses another.
Observed: error `"Missing required attribute InviterAddressId"` while the body only registered
**`InviterAddressID`** (capital ID). Rule: when a field is reported missing although you sent it,
retry with case variants (`Id`→`ID`, `Url`→`URL`) before concluding the body isn't read. Also:
`POST /api/wallet/v1/transactions` only exists as
`POST /api/wallet/v1/wallets/{WID}/accounts/{AID}/transactions` — the flat path answers with a
different required-attribute list that misleads.

## What is structurally closed in an E2E-encrypted suite (verified negatives)

Testing 9 angles; all but the fork finding were defended. Recorded so future sessions start from
the map, not from zero:

| Angle | Result | Evidence |
|---|---|---|
| Server-side RCE via uploads/image parsing | No surface | Server never processes plaintext; all content E2E-encrypted client-side |
| SSRF via calendar subscription | Negative | `POST /api/calendar/v1` ignores `Type` (always personal calendar); `Url` accepted but zero OAST hits — subscriptions fetched client-side |
| Enumeration IDOR | Blocked | All object IDs are random base64; modified/random IDs → `400 Invalid ID` **before** lookup (no exists/forbidden oracle) |
| Mail HTML XSS | Closed, 2 layers | (1) custom sanitizer strips handlers/script/iframe/object/math/video/meta-refresh/`javascript:`/CSS `@import`, neutralizes `<base>` to a plain link; (2) message iframe `sandbox` **without `allow-scripts`** — residual scripts cannot execute. Orphaned `<input>` survive (form stripped) but inert. Remote content blocked by default |
| AI indirect prompt injection (Lumo) | Guarded | No URL-fetch tool (web search is query-based); model explicitly recognizes injection patterns and refuses embedded instructions |
| Wallet transaction tampering | Solid | Tx signed client-side (`SignedTransactionHex`); metadata (`TransactionID`/`HashedTransactionID`) must be valid PGP; ID format validated pre-authz; password change & session revoke blocked by missing token scopes |
| Cross-account IDOR | Untested | Requires 2nd account — anti-abuse silently blocked repeat signups (see below) |

## The finding that DID land: session-fork claim without the secret key

`GET https://mail.proton.me/api/auth/v4/sessions/forks/{selector}` — an **unauthenticated**
request knowing only the 32-char selector receives a full-scope `AccessToken` + `RefreshToken`
(scope: mail calendar drive pass wallet payments settings …). The `sk` transmitted in the authorize
URL fragment is only used to decrypt the optional payload (keyPassword), never required for the
token grant. Fork is single-use, 24 h expiry. Impact measured by capability probe (see below).

## Capability probe — prove what a stolen token CANNOT do (severity honesty)

Before writing impact claims, probe the boundaries with the claimed token. This turned a
"full account takeover" guess into an accurate Medium:

- `GET /api/core/v4/users`, `/settings`, `/payments/v5/status`, `/addresses`, `/auth/v4/sessions` → **allowed** (PII + session inventory readable)
- `PUT /api/core/v4/users/password` → `9102 MissingScopes:["password"]` — **blocked**
- `DELETE /api/auth/v4/sessions/{id}` → `9101 MissingScopes:["locked"]` — **blocked**
- E2E content → not readable (keyPassword in sk-encrypted payload)

So: sensitive-data disclosure, not account takeover. Report the table; triage trusts it more.

## Mail-XSS battery methodology (reusable for any webmail target)

1. Send an HTML email with N payloads from a mailbox you control (Gmail API works) to the test
   account on the target webmail.
2. Open it in the target client with Playwright `page.on("dialog")` capturing alerts + a console
   listener. Zero dialogs = nothing executed.
3. Extract the **rendered** DOM from the message iframe (`about:blank` frame whose body text matches
   your payload markers) and diff surviving tags/attrs vs what you sent — that shows the sanitizer's
   exact policy, not just pass/fail.
4. Check the iframe's `sandbox` attribute: no `allow-scripts` means script execution is impossible
   regardless of sanitizer gaps — architectural closure.

## Anti-abuse escalation after the first account

Second test-account creation from the same IP/browser profile was **silently blocked** (form simply
stops submitting; no captcha, no error) after: 1 account + repeated signup attempts + authenticated
testing across 5 apps. Automated (synthetic-event) submissions stopped registering in the React
wizard entirely. The path that works: **headed browser + trusted manual input by the user** for the
first account of a fresh IP. Plan engagements that need 2+ accounts to mint them early, or expect
this wall.

## Gmail-side staging notes (see also pdf-bug-report-generation skill)

- Gmail access token expires hourly; refresh with the stored refresh_token via
  `POST https://oauth2.googleapis.com/token`. The refresh token itself can be revoked mid-engagement
  (`invalid_grant`) — recovery is the setup.py `--auth-url` flow: user approves in browser, copies the
  full `http://localhost:1/?code=...` redirect URL, agent exchanges code+verifier (pending state in
  `google_oauth_pending.json`) and saves the new token.
- Draft verification: walk `payload.parts` for `mimeType == "application/pdf"`, fetch via
  `attachments/{attachmentId}`, base64url-decode, compare sha256 to the local PDF. `body.data` is
  absent on attachment parts — attachmentId is the only route.
