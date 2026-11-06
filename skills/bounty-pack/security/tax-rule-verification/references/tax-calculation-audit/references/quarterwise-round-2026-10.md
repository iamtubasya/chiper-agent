# Quarterwise — round four (2026-10): the property-allowance defect ISOLATED, and the engine verified

Same target as `quarterwise-pro-session-2026-09.md` (where the allowance defect was first *observed*).
This round *isolated* it with a controlled two-leg experiment, re-verified the engine across all bands,
and re-checked the previously-reported public tools. Operator's Pro account + a free account.

## THE ISOLATION RECIPE (the decisive experiment — copy this)

The defect lives in **what the allowance is compared against**. To isolate it you must hold
DEDUCTIBLE EXPENSES below £1,000 while FINANCE COSTS are present, and read the panel twice.

1. Note the account's existing expense rows (they confound the aggregate — see pitfall below).
2. Delete the expense rows so `Total expenses = £0.00`. Read `/app?view=mine`.
3. Re-add ONLY a residential finance cost (category `residentialFinancialCost`). Read the panel again.
4. Restore the deleted rows exactly; verify the panel returns to its starting figures.

Observed (same account, same tax year, both legs with **£0.00 deductible expenses**):

| leg | panel sentence | allowance applied? |
|---|---|---|
| £0 expenses, £0 finance | `Property allowance applied: −£1,000.00 (instead of £0.00 actual expenses, saves you £200.00)` | YES |
| £0 expenses, £3,000 finance | `Claiming your expenses and the mortgage interest relief saves more tax than the £1,000 property allowance, so we've used those. You can't claim both.` | NO |

The only variable was the finance cost — which is NOT a deductible expense (it is added back with a
20% reducer). So the comparison population includes finance costs. Money effect: **£200 more tax at
20%**, £400–£450 at 40/45%. Still the same defect the 2026-09 session observed with £2,050 vs £1,000.

**Report it as a QUESTION, not a claimed wrong figure.** The panel itself says the allowance cannot be
claimed "as well as mortgage interest relief"; if HMRC forbids combining them the outcome is defensible
and only the wording ("we've used whichever saves you more") is contradicted by the numbers. Ask the
vendor (1) on what statutory basis the allowance is denied when residential finance costs exist, and
(2) to confirm the intended comparison. This is what keeps the report honest.

## Engine verification (all bands) — the negatives that make the finding credible

| scenario (added to the Pro account, then removed) | panel | hand-check | verdict |
|---|---|---|---|
| baseline (income £31,001.01, exp £2,512.34, finance £3,000) | Est. tax £2,583.73 | 20%×(28,488.67−12,570)=3,183.73 − £600 | CORRECT |
| + rent £30,000 (ANI £58,438.67) | Est. tax £9,807.47 | 20%×37,700 + 40%×8,168.67 − £1,000 | CORRECT |
| + rent £89,000 (ANI £117,488.67, taper band) | Est. tax £37,325.20, top rate 60% | PA = 12,570 − (117,488.67−100,000)/2 = 3,825.67 → taxable 113,663.00; 20%×37,700 + 40%×75,963 − £600 | CORRECT (exact) |

So the engine returns the statutory figure at 20%, 40% and the 60% taper boundary. **The allowance
interaction is the only tax-engine defect.** A full write-up of the pass lives beside this skill's
target notes in the engagement workspace (`quarterwise_v6/`).

## Pitfalls that cost time (target-specific, worth knowing before you start)

- **The panel is `· ALL SOURCES`.** Every per-property rule (allowance, §24) is decided on the
  AGGREGATE across all income sources. A per-property scenario CANNOT be isolated while any other
  source carries data — clear the other rows first (then restore), or use an account with one source.
- **The FREE tier has no tax lines.** The panel shows only income/expenses/net + the §24 "relief, not
  a deduction" sentence; there is no Profit/Taxable/Estimated-tax block and no allowance sentence
  ("Your free plan includes 1 income source"). Do not try to use a free account as the oracle — it
  cannot decide an arithmetic question. (It CAN still confirm the §24 add-back: net profit stayed
  £29,950 = £30,000 − £50 with £2,000 interest, i.e. interest not deducted.)
- **Use the native value setter + input/change (and a ~3.5–4s settle)** for every field, and prefer a
  JS `button.click()` found by exact `innerText` over Playwright role locators — the entry modal's
  buttons move, and a role locator intermittently times out mid-flow.
- **Expense entry is a two-step modal** ("Record expense" → "Enter manually") on the Pro UI, but a
  single direct form on the free UI. Deleting an entry is an *inline* "Delete? Yes/No", NOT a native
  `confirm()` — Playwright's auto-dismiss will silently leave the row in place.
- **Restore exactly, then re-read the panel.** One run added a duplicate £500 repairs row (the
  amount appeared twice); catching it meant diffing the panel figures (£3,012.34 vs the original
  £2,512.34) rather than trusting the ledger text.

## Adjacent surfaces checked the same round (no tax impact, recorded for completeness)

- Public calculators: the three defects in `quarterwise-public-calculators-2026-10.md` are now FIXED
  (rental taper £44,253/£57,753; section-24 £35,432/£40,703; MTD penalty year-aware £314/£414).
- API v1: idempotency on `externalRef` (dedup, no overwrite), amount/category/date validation, 500-char
  description cap, 500-item batch cap, DELETE 405, cross-tenant 404 — all correct.
- Plan/entitlement: free 1-source limit blocks; API access gated to Pro; `/app/clients` Pro-only.
- Auth: password reset is code-based and rate-limited (5 tries → "Too many attempts"); adviser invite
  is MFA-gated, 192-bit token, acceptance email-bound (wrong user rejected, address masked).
- `direct.<target>` was the origin IP (DigitalOcean) behind Cloudflare but a pure redirect vhost — no
  WAF bypass. Next.js CVE-2025-29927 (`x-middleware-subrequest`) not vulnerable.
