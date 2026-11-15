# Quarterwise — v6 pass (2026-10): re-verification + auth/API/entitlement sweep

Fourth pass on `quarterwise.co.uk` (Malden Ltd). Earlier rounds: the Pro-account tax rules
(`quarterwise-pro-session-2026-09.md`), the public calculators (`quarterwise-public-calculators-2026-10.md`),
and a security/API pass (findings.json on the v5 workspace). This round was "re-verify everything, then
deep-dive the sides not yet covered".

## 1. Re-verification: the previously reported defects are FIXED

Harness: headless Chromium; inputs set via the native value setter + `input`/`change`/`keyup` + ~4 s settle
(a plain `.value=` does not drive these React tools and silently returns the OLD figure — that alone caused a
false "no effect" reading mid-pass).

| Tool | Input | Was (defect) | Now | Verdict |
|---|---|---|---|---|
| rental-income-tax-calculator | rent £130,000 | £44,882 (+£629) | **£44,253** | fixed |
| rental-income-tax-calculator | rent £160,000 | £58,382 | **£57,753** | fixed |
| section-24-calculator | £120k / 0 / £20k | £35,675 (+£243) | **£35,432** | fixed |
| section-24-calculator | £130k / 0 / £20k | £41,332 (+£629) | **£40,703** | fixed |
| mtd-penalty-calculator | £5,000, 40d late, 2026 | £314 | **£314** | fixed* |
| mtd-penalty-calculator | £5,000, 40d late, 2027 | £314 (wrong) | **£414** | fixed* |

\* The MTD tool is now year-aware and the footnote reads "Based on 2026/27 and 2027/28 UK tax rules".
Note `#pyear` is a `<select>` (options 2026/2027) — setting it needs the SELECT prototype's value setter,
not the INPUT one, or both runs report the default year (2027) and look identical.

## 2. Tax-engine panel — arithmetic VERIFIED CORRECT (both bands)

Baseline (Audit Flat A): income £31,001.01 − expenses £2,512.34 = £28,488.67 · §24 interest £3,000 shown as
"relief, not a deduction" · taxable £28,488.67 − £12,570 = £15,918.67 · 20%×£15,918.67 = £3,183.73 − £600
relief = **£2,583.73**, top rate 20%. All exact.

Higher-band scenario built then removed (rent £30,000 + repairs £50 + residential finance £2,000):
income £61,001.01 -> taxable £45,868.67 -> 20%×£37,700 + 40%×£8,168.67 = £10,807.47 − £1,000 relief =
**£9,807.47**, top rate 40%. The §24 add-back + reducer and the 20/40 split are correct even where a broken
taper would show.

§24 independently confirmed on the FREE tier: net profit £29,950 = £30,000 − £50 expenses with the £2,000
interest shown as relief (not deducted).

## 3. The property-allowance defect — isolated, still live (reported as a QUESTION)

Both legs, same account, **£0.00 deductible expenses**:

- no finance costs -> "Property allowance applied: −£1,000.00 (instead of £0.00 actual expenses, saves you
  £200.00)"  -> allowed.
- £3,000 residential finance -> "Claiming your expenses and the mortgage interest relief saves more tax than
  the £1,000 property allowance, so we've used those. You can't claim both." -> withheld, £200 more tax at 20%.

The only variable was the finance costs, which are not deductible. The comparison population therefore
includes finance costs. Defensible if HMRC forbids combining allowance + finance-cost reducer; the messaging
("we've used whichever saves you more") is contradicted by the £0-expenses numbers either way. Report as a
question with the numbers.

**Isolation recipe that worked** (the panel is ALL SOURCES, so the aggregate had to drop under £1,000):
1. Record the account's rows, then delete the expense rows only (inline "Delete? Yes" confirm).
2. Read `/app?view=mine` -> the allowance line appears with "instead of £X actual expenses".
3. Re-add the same rows (category/amount/date/description) and re-verify the totals match the originals.
   Watch for a duplicate (the add button can double-fire) — check the totals, delete the extra, re-verify.

## 4. API v1 — business logic all enforced

Body shape: **bare JSON array** (not `{"transactions":[...]}`), items `{type, category, amountPence, date,
externalRef?, description?}`. Pence integers (£450.00 = 45000). Getting the envelope wrong yields a misleading
`0.date: Required` for every item.

- create -> 201 `{"created":1}`; replay same `externalRef` -> 200 `{"created":0,"deduplicated":1}`; same ref,
  different amount -> also deduplicated, original kept (no overwrite). 
- 422 on: amountPence <= 0, non-integer pence, > 10,000,000,000 (£100M), unknown category, income-category on
  an expense `type` (and vice versa), impossible date, future year, description > 500 chars.
- > 500 items in one request -> 422 `too_many`. DELETE on the collection -> 405.
- BOLA: reading another tenant's source id (the second test account's) or a random uuid -> 404
  `source_not_found`, "No source with that id on this account." No cross-tenant read.

New key minting is TOTP-gated (`/app/account/api`, `#key-label` + `#apiKeyMfaCode`). The stored keys from the
prior pass were revoked; fresh keys work immediately and revoke instantly from the same page.

## 5. Plan / entitlement — enforced

- Free "Add an income source" -> "Your free plan includes 1 income source…" and no second source is created.
- Free `/app/account/api` -> "API access is part of Pro — Upgrade to create API keys", no key form.
- Free `/app/clients` -> 307 to /app (Clients view is Pro-only).
- Firm view (Pro) lists 1 client, role "Can view"; the app states filing is done from the client's own account.
  A foreign-client boundary is not testable with one client — do not claim it either way.

## 6. Auth / ATO surface

- Password reset is CODE-based: `/forgot` (email) -> `/reset` ("Enter the 6-digit code we emailed you and
  choose a new password"). The code arrives from support@quarterwise.co.uk, subject "Your Quarterwise code is
  NNNNNN". No reset LINK, so no predictable-token / host-header-injection surface.
- **Attempt cap: 5.** Attempts 0-4 -> "That code is not correct."; attempt 5 -> "Too many attempts. Request a
  new code." 10^6 space not brute-forceable. Resend cooldown shown ("Send a new code in 56s").
- `/signup` -> email verify at `/verify` with the same 6-digit code pattern.
- No open redirect (`/login?next=<evil>` -> 200, no redirect; `/auth/redirect` -> 404).
- No CORS: `OPTIONS /api/v1/sources` -> 204 with no `Access-Control-*` headers.
- API is bearer-only, so no CSRF against it; all app forms are same-origin Next.js server actions
  (`$ACTION_*` refs + `$ACTION_KEY`).

## 7. Credentials / session reuse

- Login: `https://quarterwise.co.uk/login` (email + password) -> `/login/mfa` (`#code`, 6 digits). The
  "Log in" button click does not advance — submit the form with `form.requestSubmit()`.
- The Pro `qw_session` cookie from the previous pass was still valid this round — reuse it and skip MFA.
- A separate free account (own `qw_session`) exists for tenant-boundary / entitlement tests.

## 8. Cleanup discipline that mattered

Isolation required touching the operator's account: the 3 leftover test expense rows were removed, the panel
read, then restored — and the restore produced a duplicate £500 row that had to be hunted down and the totals
re-verified against the original (Income £31,001.01 / Expenses £2,512.34 / Net £28,488.67 / finance £3,000 /
Est. tax £2,583.73). Always re-read the totals after a restore; never assume the re-add matched.
