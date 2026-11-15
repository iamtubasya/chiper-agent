# Quarterwise — round four (2026-10-08): re-verification, the aggregate-panel trap, the API matrix

Same target as `quarterwise-pro-session-2026-09.md` and `quarterwise-public-calculators-2026-10.md`
(`quarterwise.co.uk`, Malden Ltd, public VDP). This round: re-verified every previously reported
defect, tried to isolate the one rule the earlier rounds left open, and ran the API business logic.

## Outcome first — the previous findings are all FIXED

Public tools now return the correct figures (hand-computed against the rules):

| Tool | Input | Was (defect) | Now |
|---|---|---|---|
| rental-income-tax-calculator | rent £130,000 | £44,882 (+£629) | **£44,253** |
| rental-income-tax-calculator | rent £160,000 | £58,382 (+£629) | **£57,753** |
| section-24-calculator | £120,000 / 0 / £20,000 | £35,675 | **£35,432** |
| section-24-calculator | £130,000 / 0 / £20,000 | £41,332 | **£40,703** |
| mtd-penalty-calculator | tax £5,000, 40 days | £314 for both years | **£314 (2026) / £414 (2027)** |

The MTD tool is now year-aware and its footnote reads "Based on 2026/27 and 2027/28 UK tax rules".
So a re-verification round on this target is worth running before writing anything new — the vendor
ships fixes between rounds.

## Harness detail that decides pass/fail (the earlier recipe was under-specified)

A plain `el.value = x` does NOT drive these tools. Neither does the native setter alone at a short
wait — an early run read the static help text (`£100,000` / `£125,140`) and looked like a pass.

Working recipe:
1. native setter: `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,v)`
2. dispatch `input` **and** `change` **and** `keyup` (bubbling)
3. wait **≈3–4 s** before reading (React re-render + result panel)
4. `#pyear` on the MTD tool is a **`<select>`** — use `HTMLSelectElement.prototype`, not the input one.
   With the input setter the year never changes and both years show the same figure (a false finding).

## The aggregate-panel trap (why the allowance rule stayed unverified)

The Pro tax panel is headed `TAX YEAR · YOUR SHARE · **ALL SOURCES**`. It compares the £1,000 property
allowance against the **aggregate** across every source. If the account already holds leftover test
data whose expenses exceed £1,000, the panel prints "claiming your expenses … saves more tax than the
£1,000 property allowance" and that message is *correct for that data* — it never exercises the
sub-£1,000 case where the earlier defect lived. Two dead ends:

- Building a clean scenario on the **free** account: the free panel shows income/expenses/net and the
  §24 note but **no tax lines and no allowance message** — the itemised estimate is Pro-only. The free
  tier cannot decide a rule that only the Pro panel renders.
- Dropping the aggregate by deleting the existing expense rows: a destructive state change on the
  operator's account. Stop and get explicit sign-off; do not do it unilaterally.

Lesson: before designing a rule-isolation scenario, confirm the panel is **per-source**. If it is an
ALL-SOURCES aggregate, the scenario must be run on an account with no conflicting data, or the specific
row set must be cleared with the operator's consent — otherwise report "unverified", never "wrong".

## §24 confirmed independently on the free tier

Free panel, rent £30,000 + repairs £50 + residential finance £2,000 → **Net profit £29,950** with
"Before mortgage interest of £2,000.00, which is relief, not a deduction". So interest is added back on
every tier, not just Pro — a cheap cross-tier corroboration of the same rule.

## Pro-account arithmetic re-verified (both bands)

`£31,001.01 − £2,512.34 = £28,488.67` · `− £12,570 = £15,918.67` taxable · `20% = £3,183.73 − £600
relief = £2,583.73`. Higher-band scenario: `£61,001.01 − £2,562.34 = £58,438.67` → taxable `£45,868.67`
→ `20%×37,700 + 40%×8,168.67 = £10,807.47 − £1,000 = £9,807.47`, top rate 40%. The §24 reducer and the
20/40 split are right in the higher band too.

## Session/API handling for this target

- The account's `qw_session` cookie was still valid rounds later: `GET /app` → **307 to /app/clients**
  (an authenticated redirect) is the liveness test; a bounce to `/login` means re-auth. Reusing a stored
  session cookie avoids the MFA round-trip entirely.
- When a fresh login is needed: `POST`-style form at `/login` (email + password) → lands on the MFA step
  (`#code`, 6 digits) → submit. Submitting the credential form with `form.requestSubmit()` worked where a
  button click did not. TOTP from the base32 secret reproduces `pyotp` exactly (see `scripts/totp.py`).
- Minting an API key (and changing the password) needs a **current TOTP** — plan for it; revoked keys are
  dead, so a stored key from a previous round is usually useless.
- API write body is a **bare JSON array**, not `{"transactions":[...]}`. Fields:
  `{type, category, amountPence, date, externalRef?, description?}`; £450.00 = `45000`. Sending the
  wrapped object yields a misleading `0.date/0.type/0.amountPence: Required` (it parses the wrapper as
  element 0), which looks like a schema error but is your shape.

## API v1 business-logic matrix (all controls held)

| Probe | Result |
|---|---|
| create | 201 `{"created":1}` |
| replay identical externalRef | 200 `{"created":0,"deduplicated":1,"existing":[…]}` |
| same ref, **different** amount | deduplicated — original kept, no overwrite |
| amountPence −1 / 0 | 422 "Number must be greater than 0" |
| amountPence 12.34 | 422 "must be a whole number of pence" |
| amountPence 10000000001 | 422 "at most … (£100,000,000)" |
| unknown category | 422 `invalid_category` + `validCategories` |
| income category on `type:expense` (and inverse) | 422 `invalid_category` |
| impossible date / future 2099 | 422 "real date between 2000 and next year" |
| description 600 chars | 422 "at most 500 character(s)" |
| 501 items | 422 `too_many` "Send at most 500 transactions per request" |
| property category on a self-employment source | 422 `invalid_category` |
| `DELETE /sources/{id}/transactions` | 405 |
| cross-tenant read (foreign/random source id) | 404 `source_not_found` |

The idempotency-on-externalRef contract is real and safe: a replay with a changed amount does **not**
mutate the stored row. Worth testing on any target that advertises idempotent bulk ingest.

## Plan/entitlement (free tier) — enforced

- `Add an income source` → "Your free plan includes 1 income source…" and **no second source is created**.
- `/app/account/api` → "API access is part of Pro" with no key form.
- `/app/clients` → 307 to `/app` (Clients view is Pro-only).
- Core pages (`/app/file`, `/app/year-end`, `/app/account`) stay 200 — entitlement is scoped to the
  Pro features, not the whole app.
