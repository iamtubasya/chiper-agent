# Kindroid (kindroid.ai) — worked Firebase-audit example, 2026-11

Real target. VDP/bounty (self-hosted): report to hello@kindroid.ai, subject
"Security report". Scope = kindroid.ai + subdomains + iOS/Android apps. Rewards:
Critical $1,000–5,000 (cross-user chats/memories, ATO, RCE, infra), High $300–1,500
(cross-user private data, stored XSS, paid-features-without-paying), Medium $100–300,
Low = credits.

## Stack fingerprint
- Next.js SPA at kindroid.ai (`_app-db2d83cc538def75.js` holds the Firebase config).
- Express API at api.kindroid.ai (GCP Google Frontend, `x-powered-by: Express`).
- Firebase project `kindroid-ai`; storage on Cloudflare R2. Billing = Chargebee + Stripe.
- ~270 API endpoints mapped from the bundle (grep `[A-Za-z]+:"v[12]/..."`).

## Auth flow (confirmed working end-to-end)
1. `POST /v1/send-otp-code {"email":"x"}` → `200 "OTP code sent"` (always 200, anti-enumeration).
2. Email arrives "Your Kindroid Login Code" with an 8-digit code, 15-min TTL.
3. `POST /v1/verify-otp-code {"email","code"}` → `{"token":"<CUSTOM token>"}`.
4. Exchange: `identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=<webKey>`
   `{"token":"<custom>","returnSecureToken":true}` → `idToken` (iss securetoken.google.com/kindroid-ai).
5. Gmail API reads the OTP (accounts: RESEARCHER_EMAIL, mrRESEARCHER_EMAIL in
   `~/AppData/Local/hermes/gmail_accounts/*.json`; empty `account` field resolves after
   refresh + `users/me/profile`).

## What ended up LOCKED (all negative results — target is well-secured)
- Admin endpoints (~46, incl consultation/coupons/chargeback/featured-panel): all 403
  "Admin only"/"Forbidden" with complete bodies.
- API kin/message access: scoped by uid (cross-account → `400 "AI not found"`).
- Firestore: **App Check enforced** — Node client SDK `getDoc("Users/<ownUid>")` also
  `permission-denied`. So no direct DB read even authenticated.
- Firebase Storage: list denied; `storage-presign` path traversal & cross-user → 400
  "Path not allowed"; support-upload path is `support/<uid>/attachment-<uuid>.png` (scoped).
- Mass assignment `is_subscriber`/`admin_role`/`is_beta_user` → joi "… not allowed".
- Gift-code issue → paid-subscriber only; premium features (internet-query, link-browsing,
  daily-reward, text-messaging) → "Start a trial or subscribe".
- email-change flow requires a code to the new email; text-messaging subscriber-only.

## The one finding (Low)
Email enumeration via `POST /v1/user/email-change/request-code`:
- other user's email → `409 "Email is already in use"`
- unregistered email → `200 {"success":true}`
- own email → `400 "New email matches your current account email"`
Validated 3x. Rate-limited (~30s/account) but bypassable by rotating free accounts.
Reward tier = credits, not cash — went into the draft, default NOT sent.

## Rescue pattern worth re-using
The "AUTH FAILED / no fresh OTP" loop in this session had TWO non-obvious causes that are
now captured in the umbrella SKILL.md pitfalls: (a) pasting the redacted `AIzaSy...` key,
(b) stale Gmail token. Both fixed with programmatic key extraction + OAuth refresh-per-call.