# UK landlord / property-income tax rules — worked expectations for testing

Compiled from authoritative sources (HMRC internal manuals, gov.uk helpsheets) plus the
vendor's own public calculators, during a UK landlord-tax SaaS engagement in Sept 2026.
Assumptions used throughout unless stated: **tax year 2026-27**, property income is the
person's only income, personal allowance £12,570, basic-rate band £37,700, property allowance
£1,000, no National Insurance on property income.

## 1. Section 24 — restriction of finance-cost relief

- Finance costs (mortgage/loan interest on residential property) are **no longer deducted** from
  property profit. Since 2020/21 they are added back and relieved as a **tax reducer of 20% of
  the finance costs**.
- Consequence: a basic-rate taxpayer gets the same result either way; a 40%/45% taxpayer loses
  the difference between their marginal rate and 20%.
- Excess finance costs that cannot be used are carried forward and used in later years.
- Expected output shape: profit unchanged by the interest, plus a separate line for the
  reducer, e.g. `Finance costs relief (20%): −£4,000.00` on £20,000 of interest.

**Worked test (used to confirm the arithmetic was right):** rent £60,000 + interest £20,000 →
profit £60,000; taxable £47,430 (= 60,000 − 12,570); tax 20% × 37,700 + 40% × 9,730 = £11,432;
minus the £4,000 reducer = **£7,432**.

**The bug this exposed (property allowance, see below):** if the allowance were applied
correctly the taxable figure would have been £46,430 and the tax £7,032.

## 2. Property allowance (£1,000) — and why finance costs must not displace it

- The £1,000 property allowance is an **alternative to deducting actual expenses**, chosen
  whichever is more favourable. It does not require any claim paperwork.
- Because finance costs are **not deductible expenses** post-Section 24 (they are relieved as a
  tax reducer), they must not take part in the allowance-versus-expenses comparison. Only
  genuinely deductible expenses count.
- Expected behaviour: with £0–£1,000 of real deductible expenses, the £1,000 allowance wins and
  profit is £1,000 lower.
- **Observed defect:** the product compared "actual expenses" *including* mortgage interest
  against the allowance, so any landlord with >£1,000 of interest never received the allowance.

**Worked test:** rent £30,000 + interest £2,000 + repairs £50.
```
app output:  Total income £30,000.00 | Total expenses £50.00 | Net profit £29,950.00
             "Your actual expenses (£2,050.00) beat the £1,000 property allowance"
             Taxable: £17,380.00 | Finance costs relief (20%): −£400.00 | Estimated tax: £3,076.00
correct:     profit £28,950 (allowance applied) → taxable £16,380 → tax £3,276 − £400 = £2,876
delta:       £200 at 20%; £400–£450 at 40%/45%
```

## 3. Cash basis vs accruals — the £150,000 threshold

- From 2024/25 the **cash basis is the default** for unincorporated property businesses with
  receipts of **£150,000 or less** in the tax year (PIM1092). Above that it is no longer the
  default, and a business elects in/out.
- Cash basis recognises receipts and expenses when money moves — no debtors, creditors, or
  accrued income. Accruals (GAAP) requires the opposite, with transitional adjustments on
  entering/leaving (PIM1098).
- Test shape: confirm whether the product has **any** accruals input at all; if it is
  cash-basis-only, that is a documented limitation, not a bug — but a product that warns
  nothing as receipts pass £150,000 leaves the landlord unaware they are outside the default.
- Watch for the vendor's own promise: "we'll warn landlords whose receipts pass £150,000" is a
  commitment you can check later and report as not-yet-present (we did; nothing at £155,000).

## 4. Foreign Tax Credit Relief (FTCR) — the cap matters

- Where foreign income is taxed in the UK and abroad, the credit is limited to the **lower of**
  the foreign tax paid and the **UK tax attributable to that income** (gov.uk HS263 and the
  FTCR working sheet). Multiple sources are processed serially.
- So a £8,000 foreign tax on £10,000 of overseas rent does **not** produce an £8,000 credit; it
  produces roughly the UK tax on that slice.
- Test shape: record overseas rent plus foreign tax, then look for a credit line and compare it
  with your hand-computed cap. If **no credit line appears at all**, the cap is unobservable —
  report that the relief is not visible rather than claiming the cap is wrong.
- Also check the export labels: we found foreign tax labelled "Tax withheld at source (paid to
  HMRC for you, not income)", which misstates who was paid.

## 5. Ownership share and jointly-owned property

- Married couples / civil partners: jointly held property income is taxed **50:50 by default**
  (s.836 ITA 2007), unless actual beneficial shares differ and a **Form 17 declaration** is
  made (only available to spouses/civil partners, and only for unequal *beneficial* shares).
- Other joint owners (friends, siblings, business partners) are taxed on their actual shares.
- Non-50/50 splits are common and legitimate — a 60:40 example appears in the vendor's own
  blog. Test the multiplication, not the policy: income × share, expenses × share, profit ×
  share, and that the same figure reaches the API and the estimate.
- A single percentage with no date range means a mid-year change silently applies to the whole
  year. That is a real limitation for a first year or a change of shares, and vendors often
  acknowledge it — check before reporting it as a bug.

**Worked test:** rent £10,000 at 100/60/40% → "your share" £10,000 / £6,000 / £4,000, matching
in the UI card, the estimate block, and `sharePercent` from the API.

## 6. Capital gains on disposal (often gated, know the rules anyway)

- UK residential property gains are reported and paid within **60 days of completion**,
  separately from the return.
- Rates for residential property are **18%** up to the remaining basic-rate band and **24%**
  above it — the split depends on other income in the year of sale.
- The **annual exempt amount is £3,000** (was £6,000 in 2023/24, £12,300 before).
- **Private Residence Relief** exempts the period of actual residence plus the **final 9
  months** of ownership.
- Losses brought forward, lettings relief edge cases and joint-ownership splits are commonly
  out of scope in vendor calculators — read their own disclaimer before treating a gap as a bug.

## 7. Reporting deadlines (context for the "not tested" section)

- Quarterly MTD updates are due roughly one month after each quarter ends; the tax return by
  31 January following the tax year. A product that shows the next deadline is worth verifying
  against the tax year's actual quarter dates when you are in there anyway.

## Source notes

- PIM1092 / PIM1094 / PIM1098 — cash basis for landlords (default, receipts & expenses,
  transitional adjustments).
- HS263 + FTCR working sheet — foreign tax credit relief and its cap.
- gov.uk: property allowance; report and pay Capital Gains Tax; Section 24 overview.
- Vendor-published pages are useful as *their* stated understanding — quote them verbatim when
  the product contradicts them, and check them against the authority rather than trusting them.
