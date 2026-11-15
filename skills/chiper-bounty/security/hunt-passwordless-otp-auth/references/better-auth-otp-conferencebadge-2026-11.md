# Better Auth OTP — conferencebadge.com worked transcript (2026-11)

Target: `*.conferencebadge.com` — event subdomains (`cas2026`, `convention-2026`, …) serve a
React/Vite **Lead Retrieval** SPA backed by Better Auth email-OTP login on the same origin.

## Exact endpoint surface (all POST unless noted)

```
GET  /api/auth/get-session          -> 200 "null" (anon)
GET  /api/auth/list-sessions        -> 401 UNAUTHORIZED
GET  /api/auth/ok                    -> 200 {"ok":true}
POST /api/auth/sign-up/email         -> 400 body.name/email/password required; then
                                        400 EMAIL_PASSWORD_SIGN_UP_DISABLED
POST /api/auth/sign-in/email         -> 400 (email/password OTP-only)
POST /api/auth/email-otp/send-verification-otp   -> {email,type}
POST /api/auth/sign-in/email-otp     -> {email,otp} -> session
POST /api/auth/email-otp/verify-email        -> {email,otp}
POST /api/auth/email-otp/check-verification-otp -> {email,otp,type}
GET  /api/auth/verify-email?token=x  -> 401 INVALID_TOKEN (no token given)
POST /api/auth/verify-email          -> 404
POST /api/auth/change-email          -> 401 (auth) / 403 INVALID_CALLBACK_URL
POST /api/auth/change-password       -> 401 (auth)
POST /api/auth/revoke-session        -> 400 [body.token] required (interesting: validates body first)
POST /api/auth/sign-in/social        -> 404 PROVIDER_NOT_FOUND (google/eventbrite)
GET  /api/auth/callback/google|eventbrite -> 302 (exist even though social UI absent)
GET  /api/health                     -> 200 {"data":{"ok":true,"release":"<git-sha>","schemaLevel":5}}
```

## `type` gate-bypass matrix (unregistered email)

| type | result |
|---|---|
| `sign-in` | `403 {"message":"Your email is not registered for this event. Contact the organizer."}` |
| `email-verification` | `200 {"success":true}` |
| `forget-password` | `200 {"success":true}` |
| `change-email` | `400 {"message":"Invalid OTP type"}` |

`email-verification`/`forget-password` returns `success:true` but no mail arrives for unregistered
users — a false-positive success, not a real send. The gate is enforced only on `sign-in`.

## Enumeration result

`admin@conferencebadge.com` → 200 on ALL six event subdomains (a staff account registered on every
event). Other probe addresses → 403. This is the takeover target.

## OTP brute-force — measured block rates

| test | attempts | blocked | rate |
|---|---|---|---|
| 200 sequential | 200 | 1 | 0.5% |
| 200 parallel (4.6 s) | 200 | 1 | 43.5 req/s |
| sustained 601 s | 23,900 | 1 | 39.7 req/s |
| parallel-burst 3,000 / 50.7 s | 3,000 | 4 | 59.1 req/s |

Lockout reset proof: 5 rounds of `send OTP → 4 guesses` produced `...B` each round (block only at
the 4th guess) — the counter resets on each new OTP request.

OTP length confirmed from the bundle: `onChange: F => h(F.target.value.replace(/\D/g,"").slice(0,6))`,
`maxLength: 6`, `placeholder: "000000"`.

## Route guard (client-side role)

```js
function _5(){const{data:e}=Wc();
  return (e.user.role ?? "exhibitor") === "organizer"
    ? <organizer routes /organizer /organizer/exhibits/:id>
    : <attendee routes / /scan> }
```

`Wc()` = Better Auth `useSession()`. Role comes from the session user object; absent role defaults to
`"exhibitor"`. Organizer API: `/api/scans`, `/api/scans/all`, `/api/attendees`,
`/api/attendees/invite`, `/api/events/:id/exhibits`, `/api/events/:id/exhibits/:id/members`,
`/api/events/:id/exhibits/promote`, `/api/events/:id/send-leads`. All 401 anon (server does check
auth). Scan flow: `POST /api/scans {"attendeeEmail": <QR value>}` returns full PII
(firstName,lastName,title,company,email,phone,linkedin) — the QR simply encodes the attendee email.

## Report wording (rejected-by-triage avoidance)

The program's OOS list included "rate limit on signup/login/password reset". The finding is NOT that
send limit — it is the **verification** attempt limit being absent. Wording used:

> "Rate limiting on login/signup/password-reset endpoints is listed as out-of-scope in the policy;
> **Finding 1 is not about the send rate limit** — it is about the *verification* attempt limit being
> absent, which is the control that protects the account."

Severity split: OTP brute-force = **High** (broken lockout → slow-but-feasible ATO, NOT Critical);
enumeration = Medium; `type`-gate bypass = Low/Medium (false-positive "success", no session granted);
`/api/health` commit-hash + schemaLevel leak = Low.

## Honest severity correction (measured 2026-11, after operator challenge)

The naive "59 req/s → 4.7 h" was over-claimed. Measurement showed:
- the server does a **slow hash** on each wrong-OTP verify (~1.27 s round-trip) → true ceiling
  ≈ **50 req/s single-IP** regardless of concurrency (aiohttp 500-concurrent and 200-thread
  `requests` both plateau ~50).
- the OTP stays `INVALID_OTP` (not `OTP_EXPIRED`) ≥10 min after issue → TTL ≥ 10 min.

So each window ≈30,000 guesses (~3% of 10^6); ~90% success ≈ **half a day single-IP**, botnet scales
it linearly. Net: **High** — the lockout is genuinely broken (0 blocks in 4,000 attempts), but the
slow hash + TTL bound the rate. Close the "still theoretical" objection by offering an e2e brute on
vendor-provided test accounts.