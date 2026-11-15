# Quarterwise Pro session — tax-rule scenarios and verdicts (2026-09-30)

Account: vendor-granted Pro, own test account. No HMRC connection at any point (verified:
property settings still read "Quarterly period: not set yet"; Other income reads "Not checked
with HMRC yet"). All scenario data removed afterwards (API: 1 property, 0 transactions).

Panel used as oracle (verbatim shape, dashboard "TAX YEAR 2026-27 · YOUR SHARE"):

```
Total income | Total expenses | Net profit
Before mortgage interest of £X, which is relief, not a deduction
Est. tax 2026-27 £Y
Profit: £… | Taxable: £… | Finance costs relief (20%): −£… | Estimated tax: £… | Top rate: …%
[allowance sentence] | [estimate-only disclaimer]
```

## Verdicts

| Rule | Scenario | Product result | Verdict |
|---|---|---|---|
| §24 finance costs | UK prop, rent £60,000 + interest £20,000 (`residentialFinancialCost`) | profit stays £60,000; "Finance costs relief (20%): −£4,000.00"; label "Before mortgage interest of £20,000.00, which is relief, not a deduction" | CORRECT |
| Property allowance £1,000 | rent £30,000 + interest £2,000 + repairs £50 | "Your actual expenses (£2,050.00) beat the £1,000 property allowance" → taxable £17,380, tax £3,076 | **DEFECT** — the £2,050 includes the £2,000 of finance costs, which are not deductible expenses; with the correct comparison the allowance wins (taxable £16,380, £200 less at 20%, £400–450 at 40/45%). Product copy claims "we've used whichever saves you more" |
| Foreign Tax Credit Relief | overseas prop (Spain): foreign rent £10,000 + `foreignTaxPaidOrDeducted` £8,000 | ledger shows "Foreign tax paid on this income … not income, not in totals"; **no credit line anywhere** in the panel or the property exports (xlsx/pdf) | UNVERIFIED — cap cannot be assessed; reported as a question. Side note: the property's Excel export labels it "Tax withheld at source (paid to HMRC for you, not income)", which is wrong for foreign tax |
| Cash basis £150,000 | receipts pushed to £155,000 | no warning on dashboard, property page or properties list ("150,000"/"cash basis"/"accruals"/"threshold" absent) | promised by vendor on 29 Sep, not present |
| Ownership share 100/60/40 | rent £10,000, share changed via `#ownerPercent` | "your share £10,000 / £6,000 / £4,000"; dashboard "YOUR SHARE" block matches; `/api/v1/sources` reports sharePercent | CORRECT. One percentage, no date range → a mid-year change applies to the whole year (vendor acknowledges it is unsupported) |
| Accruals basis | — | no accruals inputs exist anywhere; all ledger categories are receipts/payments | cash-basis-only by design; nothing to falsify |
| Capital gains | residential property sale | section exists at /app/other-income → "Capital gains" but is unreachable: with no NINO "Add your National Insurance number on the HMRC page first"; after saving one, "Connect to HMRC first" | NOT TESTED (would require an HMRC link). Vendor's own public CGT calculator encodes 18/24%, £3,000 AEA, PRR pro-rata + final 9 months, 60-day reporting |

## Rules used (cite the manual id in a report)

- §24 / finance-cost restriction: interest added back, 20% basic-rate reducer — vendor's own
  /tools/section-24-calculator page states it.
- Property allowance £1,000: alternative to deducting actual expenses.
- Cash basis default for property businesses at ≤ £150,000 receipts — **PIM1092**.
- FTCR: credit limited to the lower of the foreign tax paid and the UK tax on that income —
  HS263 / FTCR working sheet.
- CGT on residential: 18%/24% by remaining basic-rate band, £3,000 annual exempt amount,
  60-day report and pay.

## Harness notes specific to this target

- Estimate block is on `/app?view=mine` when the account also has a "Clients" (adviser) view;
  a plain `/app` redirects to `/app/clients`.
- `Foreign tax paid on this income` never appears as income in the totals — but it also never
  produces a credit, which is what made the FTCR question worth raising.
- Adding a finance cost of £1 changes the panel by exactly £0.20 (the reducer), which is a
  cheap way to confirm the reducer is applied as a tax reducer.
