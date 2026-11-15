# OTP Lockout Matrix + Duplicate-Submission Race (QuarterWise VDP, 2026-09)

Verified-negative and low-severity techniques from a hardened Next.js VDP target.
All tests used own accounts (within VDP rules); numbers are the observed block points.

## 1. OTP / MFA lockout — account-level, not per-session (SAFE)

Two-round decisive test (own account):

| Vector | Round 1 | Round 2 (fresh login) | Verdict |
|---|---|---|---|
| Login wrong-password (no MFA account) | blocked at attempt 11, "wait about 15 minutes" | n/a (skipped to avoid lockout) | rate-limited |
| Login-MFA wrong OTP | blocked at attempt 6 | immediately blocked at attempt 1 | **account-level lockout** |
| MFA-recovery wrong code ("Forgot MFA?" → email code) | blocked at attempt 6 | "Too many attempts. Request a new code." persists after fresh nav | **account-level, persists cross-session** |

Recovery flow markers that make MFA-disable non-attackable even with the password:
- "takes 24 hours", "we'll email you first so you can stop it if it wasn't you",
  "remind you before it is removed", per-recovery resend cooldown ~58s.
- Recovery code arrives with subject-side leak (`Confirm turning off two-factor — code
  764264`) — minor hygiene only; email is sent to the account holder.

Method notes:
- Manual `urllib` multipart replay of login/MFA POSTs returned 500 for everything —
  broken wire format, not a server signal. Browser-driven (CDP fill + requestSubmit) is
  ground truth for OTP flows.
- Do not brute-force to full lockout on someone else's account; bounded two-round probing
  (≤14 attempts/round, own account) is enough to prove account-level persistence.

## 2. URL param echo ≠ rate-limit control

`/reset?codeLimit=1&why=cooldown` changed rendered copy to "ask for a new code in about 1
seconds", but the actual resend cooldown stayed server-side (`Send a new code in 58s`, and
early resend was still rejected). `codeLimit` / `why` are echoed into message text only.
Enforcement signal = independent (resend button cooldown, submit rejection), never the
echoed copy.

## 3. Duplicate-submission race on server actions (LOW, reproducible)

```
// one Runtime.evaluate tick on the "Add income" form:
b.click(); b.click();
```
→ export JSON showed 2 ledger entries (amountPence 7777 x2) from ONE form instance.

- 150ms-apart double-click → exactly 1 entry (form closes after first submit), so real
  users don't trigger it. Exploitability requires scripted same-tick or network replay →
  LOW / missing-idempotency, not payout-grade.
- Root cause contrast: product API v1 dedups on `externalRef`; the UI server action has no
  idempotency key/unique constraint.
- **Verify by export JSON, not page text.** Page text shows the amount twice even for one
  entry (label + entry line). Count `amountPence` in `/api/account/export`.

## 4. Business-logic amount validation (verified safe)

Same-tick double-click aside, the endpoint rejected: negative amounts, 0, huge
(>10^12 pence), fractional pence (0.001), and arbitrary category values (fallback to
default). Only proper positive whole-pence values with valid category persisted.