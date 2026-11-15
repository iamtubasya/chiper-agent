---
name: hunt-passwordless-otp-auth
description: "Hunt passwordless email-OTP / magic-code login (Better Auth & similar) — endpoint map, type-parameter gate bypass, OTP brute-force, enumeration, client-bundle role-guard fingerprinting."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, otp, better-auth, passwordless, account-takeover, auth]
    related_skills: [hunt-ato, hunt-mfa-bypass, hunt-auth-bypass, auth-api-authz-probe-ordering]
---

# Hunt passwordless email-OTP / magic-code auth

## When to use

Any target where login is **"enter email → receive 6-digit code → done"** (no password, or OTP as
the primary factor). The dominant library is **Better Auth** (`better-auth`), fingerprintable from
the SPA bundle in a few greps. This skill covers: fingerprinting the stack, mapping the full auth
endpoint surface, then the concrete bugs that pay on these systems — email-OTP brute-force → ATO,
the `type`-parameter registration-gate bypass, user enumeration via the OTP sender, and client-side
role guards. Derived from a live Critical finding (conferencebadge.com, 2026-11) plus cross-target
patterns.

## 1. Fingerprint the stack from the client bundle

Do NOT probe endpoints blind. Pull the built JS bundle and grep:

- **Better Auth marker**: `better-auth`, `BETTER_AUTH_URL`, `NEXT_PUBLIC_BETTER_A` or the error-code
  table `Invalid OTP` / `OTP expired` / `Too many attempts` in one string literal.
- **Fetch wrapper** (the API base): a line like
  `const Gw="/api"; async function Br(e,r){const t=await fetch(\`${Gw}${e}\`,{credentials:"include",...})}`
  → the whole API is same-origin under `/api` with `credentials:"include"` (cookie session).
- **Route guard / role logic**: `e.user.role ?? "exhibitor" === "organizer"` — the role is read from
  the **session user object** and defaulted. If the API does not re-check the role server-side, a
  client-side role is forgeable (see §5).
- **OTP length + input mask**: `maxLength:6` / `.slice(0,6)` / `placeholder:"000000"` → confirms a
  6-digit numeric space (10^6) — this is the number that makes brute-force feasible.
- **OTP plugin error codes** (Better Auth `email-otp` plugin): `INVALID_OTP`, `TOO_MANY_ATTEMPTS`,
  `OTP_EXPIRED`, plus core `VALIDATION_ERROR`, `UNAUTHORIZED`, `INVALID_TOKEN`,
  `INVALID_CALLBACK_URL`, `PROVIDER_NOT_FOUND`, `EMAIL_PASSWORD_SIGN_UP_DISABLED`.

## 2. The endpoint map (Better Auth)

Base prefix `/api/auth`. Standard routes, all worth probing:

| method | path | notes |
|---|---|---|
| GET | `/api/auth/ok` | always `{"ok":true}` — liveness/fingerprint |
| GET | `/api/auth/get-session` | `null` when anon, user object when authed |
| GET | `/api/auth/list-sessions` | 401 anon, session list authed |
| POST | `/api/auth/email-otp/send-verification-otp` | **enumeration + gate-bypass target** (§3, §4) |
| POST | `/api/auth/sign-in/email-otp` | `{email, otp}` → session — **brute-force target** (§6) |
| POST | `/api/auth/email-otp/verify-email` | `{email, otp}` — verifies email, does NOT create session |
| POST | `/api/auth/email-otp/check-verification-otp` | `{email, otp, type}` |
| POST | `/api/auth/sign-in/email` | `{email, password}`, `404` on OTP-only setups |
| POST | `/api/auth/sign-up/email` | may return `EMAIL_PASSWORD_SIGN_UP_DISABLED` |
| POST | `/api/auth/change-email` / `change-password` | 401 anon (auth required) |
| POST | `/api/auth/revoke-sessions` / `revoke-session` / `delete-user` / `update-user` | 401 anon |
| POST | `/api/auth/sign-in/social` | `{provider}` → `PROVIDER_NOT_FOUND` if OTP-only |
| GET | `/api/auth/callback/<google|eventbrite|...>` | 302, may exist even when social UI hidden |

Note `sign-up/email`, `sign-in/email`, `sign-in/email-otp` etc. `404` on GET — they are POST-only.

## 3. User enumeration via the OTP sender

`POST /api/auth/email-otp/send-verification-otp {"email":"X","type":"sign-in"}` differentiates
registered vs not **by design**:

- registered attendee/exhibitor → `200 {"success":true}`
- unregistered → `403 {"message":"Your email is not registered for this event. ..."}`

Confirm 3×. Feed the enumerated list into §6 (brute-force) to pick high-value targets — staff/admin
accounts are often registered on **every** event subdomain, so one takeover is cross-tenant.

## 4. The `type`-parameter registration-gate bypass

The "must be registered" gate is often enforced **only** for `type=sign-in`. Other accepted types
skip it for arbitrary emails:

| type | unregistered result |
|---|---|
| `sign-in` | `403` gate enforced |
| `email-verification` | `200 {"success":true}` |
| `forget-password` | `200 {"success":true}` |
| `change-email` | `400 {"message":"Invalid OTP type"}` (rejected) |

Impact is usually LOW (the resulting OTP does NOT itself grant a session — verify via
`verify-email` leaving `get-session → null`), but it (a) allows unsolicited OTP mail to any address
and (b) proves the gate is type-scoped. Report as an auth-gate inconsistency, but do NOT over-claim
ATO from this alone — chain it with §6.

## 5. Client-side role guard → check the API's server-side enforcement

When the bundle shows `role ?? "exhibitor" === "organizer"` gating `/organizer/*`, the router is
**client-side only**. The real question is whether `/api/...` re-checks the role. The organizer API
surfaces (`/api/scans`, `/api/scans/all`, `/api/events/:id/exhibits`, `/api/attendees`,
`/api/attendees/invite`, `/api/events/:id/send-leads`, `/api/events/:id/exhibits/promote`,
`/api/events/:id/exhibits/:id/members`) returns 401 when unauthenticated — but you need an authed
session before you can test role escalation. Do not assume "client role ⇒ forgeable"; prove it with
two accounts (organizer + attendee) or after the §6 ATO.

Also note the QR/badge flow may pass a **user-controlled identifier** directly into a data lookup:
`POST /api/scans {"attendeeEmail": <from QR>}` returns the full PII record (name, company, title,
**email, phone, LinkedIn, Twitter**). If the API trusts an arbitrary email you can iterate, that is
an IDOR/mass-PII-disclosure — the classic Lead-Retrieval bug.

## 6. OTP brute-force — the highest-value test

The core question is **whether the attempt limiter is real**. Better Auth's `email-otp` plugin
tracks failed attempts per OTP token, but two defects repeatedly appear and make it brute-forceable:

1. **Lockout fires once, then stops enforcing.** The `TOO_MANY_ATTEMPTS` 403 typically appears at a
   specific attempt index (often the 3rd or 4th) **and then subsequent attempts return normal
   `INVALID_OTP` (400)** — the counter is not actually gating.
2. **A new OTP request resets the counter.** Send OTP → 3 free guesses → send again → 3 free guesses
   … and OTP sends are themselves unlimited.

Measured signatures that prove it (conferencebadge.com):

| test | attempts | block rate |
|---|---|---|
| 200 sequential | 200 | **0.5%** (1 blocked) |
| 200 parallel, 4.6 s | 200 | 0.5% (43.5 req/s) |
| sustained 601 s | 23,900 | **0.004%** (39.7 req/s) |
| parallel-burst 3,000 / 50.7 s | 3,000 | **0.13%** (59.1 req/s) |

**⚠ Measure severity — do NOT claim "X h Critical" from the 10^6 space alone.** The naive
"6-digit / rate = X hours" math over-claims because it ignores two server-side constraints that cap
the REAL attack. This session's finding was challenged as "theoretical 4.7 h" and the corrected
measurement came out **High, not Critical**:

1. **Server-side hash cost sets the true rate ceiling.** Measure one wrong-OTP verify's round-trip
   and push concurrency in 2–3 shapes (aiohttp 500-concurrent, 200-thread `requests`). Here the
   ceiling is ~50 req/s single-IP (the verify does a deliberate slow hash, ~1.27 s round-trip), so
   more concurrency does NOT raise it — the browser's ~59 req/s was not the server's limit.
2. **OTP TTL forces repeated windows.** Send one OTP, then re-send the SAME wrong OTP every ~2 min
   and watch for `INVALID_OTP` → `OTP_EXPIRED`. The OTP stayed valid ≥10 min here (Better Auth
   default `expiresIn` ≈5 min). A short TTL means you cannot run one continuous 10^6 exhaust — you
   restart a fresh window each time.

With ceiling ≈50 req/s and TTL ≈10 min, each window ≈30,000 guesses ≈ **3% of the space**, so ~90%
success takes roughly **half a day from a single IP** (a botnet scales it linearly). State both the
proven part (lockout broken → 0 blocks in thousands of attempts) and the honest timeline (~half-day),
and OFFER to reproduce the full ATO on vendor-provided **test accounts** — that is the clean way to
close the "still theoretical" objection without touching a real account.

**Non-destructive proof (no need to actually complete a takeover):**
- Confirm OTP length is 6 from the bundle.
- Send one OTP, then issue N guesses; record `blocked` vs `invalid` count. A block rate ≤ 1% (and
  especially the re-send-resets-counter behaviour) is the finding.
- Prove the reset: 5 rounds of `send → 4 guesses` each show the block only at the 4th guess every
  round (`...B`), i.e. the counter resets on each send.
- Prove session-grant on success without guessing: read the SPA handler — `signIn.emailOtp({email,
  otp})` then `window.location.href = "/"` (authed). A valid OTP ⇒ session.

Do NOT actually take over a real staff account on production. The proof above is sufficient and
non-destructive.

**Recommended fix to cite**: per-email + per-OTP-token attempt limit that is NOT reset by a new OTP
request; invalidate the OTP after N failures with a cooldown; add CAPTCHA/PoW after a few failures;
consider 8+ digit OTPs or magic-link tokens as defence in depth.

## 7. Verification discipline (3× minimum, non-destructive)

- Enumeration and gate-bypass: repeat the exact request 3× and diff — both are deterministic.
- Brute-force: run at least two independent batch shapes (sequential + parallel) and report both
  numbers; a single run can be throttled.
- The `send`-rate-limit and the `verify`-attempt-limit are DIFFERENT controls. A program may mark
  "rate limit on login/signup/reset" out-of-scope — that is the **send** limit. The **verification
  attempt limit** is the control that protects the account; state the distinction explicitly in the
  report so triage does not bounce it as OOS.
- **But the operator may still judge the whole thing OOS — accept and pivot, don't re-argue.** When
  the operator (or a broad reading of the program's OOS list) treats "rate limit on login" as
  covering the OTP attempt-limit too, stop defending the finding and pivot to clearly in-scope
  classes: first-party stored XSS, IDOR/BOLA, CSRF, SSRF, business-logic fee/entitlement
  manipulation, open-redirect. Prove an unambiguous in-scope bug instead of re-litigating scope
  across multiple turns (this exact 2026-11 session burned several turns defending the OTP lockout
  before the operator accepted the pivot to the Lead-Retrieval IDOR/privilege-escalation leads).
- Severity discipline: registration-gate bypass alone is LOW; the brute-force is **High** (broken
  lockout → slow-but-feasible ATO), NOT Critical — the slow hash + TTL bound the rate. Separate what
  is PROVEN (lockout fires ~0.025% of the time) from what is THEORETICAL (an actual completed
  takeover), and correct the timeline to ~half-day single-IP rather than "hours". Offer the e2e proof
  on vendor test accounts instead of over-claiming.

## Support files
- `references/better-auth-otp-conferencebadge-2026-11.md` — full worked transcript: exact endpoints,
  the `type` matrix, the measured block-rate table, and the report/recommended-fix wording.