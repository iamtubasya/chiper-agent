# UK property / MTD tax rule bank (with sources) + scenarios that were used

Condensed while auditing a UK MTD property/self-employment product (2026-09). Sources are the
official pages; re-check the figures for the year you are testing (allowances change).

## Rules worth knowing before you test

**Section 24 — finance-cost restriction (residential property)**
Since 2020/21 finance costs are no longer deductible. Add the interest back, compute tax on
the full property profit, then apply a tax REDUCER of 20% of the finance costs. A landlord on
the basic rate is broadly unaffected; higher/additional-rate landlords lose the difference
between their marginal rate and 20%. Basic-rate taxpayers therefore cannot distinguish
"deducted" from "reducer" by the bottom line — build a scenario that crosses into the 40%
band before concluding anything.
Source: gov.uk / legislation.gov.uk (Finance Act 2015 s.24), vendor's own S24 calculator copy.

**Property allowance (£1,000)** — an alternative to deducting actual expenses, not an extra
deduction. You compare it with the actual deductible expenses and use whichever is better
(it cannot be combined with deducting those expenses). Because finance costs are no longer
deductible, they must NOT count toward that comparison.
Source: gov.uk property-allowance guidance; PIM (property income manual).

**Foreign Tax Credit Relief (FTCR)** — relief is capped at the LOWER of the foreign tax paid
and the UK tax attributable to that income; multiple sources are processed serially.
Source: gov.uk HS263 "Relief for Foreign Tax Paid" + the FTCR working sheet (FTCRWS).

**Cash basis vs accruals (property businesses)** — cash basis is the default for individuals/
partnerships with receipts of £150,000 or less for the tax year; above that it is no longer
the default (elect accruals, or fall out of the regime). Under cash basis, receipts and
expenses are recognised when money moves, so there are no debtors/creditors. Disposal receipts
for assets whose cost was deducted under cash basis are treated as INCOME receipts, not gains.
Source: gov.uk HMRC internal manual PIM1092 (cash basis overview), PIM1095/PIM1098.

**Capital gains on a residential disposal** — gain = proceeds − cost − buying/selling costs −
capital improvements; deduct the annual exempt amount (currently £3,000) then tax at 18%/24%
depending on remaining basic-rate band; private residence relief pro-rates for periods of
occupation plus the final 9 months; report and pay within 60 days of completion for UK
residential property. Applies to your share only for jointly owned property.
Source: gov.uk "Report and pay your Capital Gains Tax"; CG73550.

**Joint ownership / Form 17** — spouses/civil partners in jointly held property are taxed
50:50 by default; a different split reflecting actual beneficial shares needs a Form 17
declaration. Other joint owners generally follow their actual ownership shares.

## Scenarios used (copy the shape, keep the exact numbers for evidence)

| # | Scenario | Expected by the rules | What the app did |
|---|---|---|---|
| 1 | UK property, rent £60,000, mortgage interest £20,000 | profit £60,000 (interest added back), reducer 20% × £20,000 = £4,000 off the tax | correct: "Before mortgage interest of £20,000.00, which is relief, not a deduction", "Finance costs relief (20%): −£4,000.00" |
| 2 | UK property, rent £30,000, interest £2,000, repairs £50 | finance costs excluded from the allowance comparison → £1,000 allowance applies → profit £28,950, taxable £16,380, tax £2,876 | **defect**: "Your actual expenses (£2,050.00) beat the £1,000 property allowance" — it counted the £2,000 interest as expenses → profit £29,950, tax £3,076 (£200 high; £400–450 at 40%/45%) |
| 3 | Overseas property (Spain), foreign rent £10,000 + "foreign tax paid" £8,000 | a credit line capped by UK tax on that income | **no credit line anywhere** in the estimate → cap unverifiable (report as a question); the property's own Excel export also mislabels the foreign tax as "Tax withheld at source (paid to HMRC for you…)" |
| 4 | Receipts pushed to £155,000 | behaviour/warning above the £150,000 cash-basis threshold | no warning on dashboard, property page or list (vendor had said they would add one) |
| 5 | Rent £10,000 with ownership share 100% → 60% → 40% | share applied consistently | correct: share £10,000 / £6,000 / £4,000 in UI and in the API; a single share value applies to the WHOLE year (mid-year change not supported — vendor-acknowledged limitation) |
| 6 | Capital gains section | CGT arithmetic testable | unreachable: gated behind "add your NINO" then "Connect to HMRC first" — reported as a product gap, not tested |

## Practical notes

- The app's estimate panel is the oracle: copy lines like `Estimated tax`, `Taxable`,
  `Finance costs relief (20%)`, `Tax deducted at source`, `Top rate` verbatim into the report.
- Take a screenshot of the panel for each state (before/after) — a claim like "£11,227.77 →
  £0.00" is unanswerable with a screenshot attached.
- Build the scenario via the public API when one exists (exact amounts, no UI noise), then read
  the panel through the UI because that is where the arithmetic is displayed.
- Delete the scenario entries afterwards and verify counts; leave the account as delivered.
