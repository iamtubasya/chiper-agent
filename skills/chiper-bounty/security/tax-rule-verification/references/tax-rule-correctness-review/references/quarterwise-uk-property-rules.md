# UK property / MTD income-tax rules — verified in practice

Session: Quarterwise (quarterwise.co.uk, Malden Ltd, HMRC-recognised MTD software), 2026-09/10.
All scenarios run in the auditor's own Pro account; data removed afterwards.
Sources: gov.uk guides + HMRC internal manuals (PIM1092 etc.), HMRC HS263 (FTCR working sheet),
and the vendor's own public copy/calculators as the yardstick for their stated interpretation.

## Section 24 — restriction on residential finance costs
Rule: from 2020/21 finance costs (mortgage interest etc.) are NOT deducted from property
profits; the profit is computed on the full rent and a basic-rate **20% tax reducer** is applied
to the tax instead. Carried-forward unused finance costs are a separate category key.
Vendor's own page states it correctly ("you add back the full interest and instead receive a
20% tax credit on it").
Observed: **correct**. Ledger has dedicated keys `residentialFinancialCost` /
`residentialFinancialCostsCarriedForward` (UK) and `broughtFwdResidentialFinancialCost` (foreign).
Output showed `Net profit £60,000.00` (interest not deducted), the explicit line
"Before mortgage interest of £20,000.00, which is relief, not a deduction" and
`Finance costs relief (20%): −£4,000.00`.
Scenario that separates right from wrong: rent £60,000 + interest £20,000 (the S24 and the
pre-2017 full-deduction answers are equal for a basic-rate taxpayer — push the total into the
40% band so they diverge).

## £1,000 property allowance — the bug found
Rule: the £1,000 property allowance is an **alternative to deducting actual expenses**; you
compare it with the deductible expenses and (broadly) claim the better one. Finance costs are not
deductible expenses post-S24, so they must not enter that comparison.
Observed: **bug** — the app compares the allowance against "actual expenses" that INCLUDE finance
costs. With £50 of real expenses and £20,001 of mortgage interest:
`Your actual expenses (£20,051.00) beat the £1,000 property allowance, so we've used those.`
→ the allowance is never applied when a landlord has a mortgage, and `Taxable` is £1,000 too high
(£450 of extra tax at the 45% rate). Their own copy says "We've used whichever saves you more",
which the arithmetic contradicts.
Isolation recipe: property with rent only → allowance applied; add ONE penny of finance cost →
allowance disappears (that contrast is the proof).
Caveat to keep in the write-up: the precise allowance/finance-cost interaction deserves a
specialist's confirmation; the internal contradiction ("whichever saves you more") is the
unarguable part.

## Foreign Tax Credit Relief (FTCR) — and the cap
Rule (gov.uk HS263 + FTCR working sheet): credit against UK tax for foreign tax already paid,
limited to the **lower of the foreign tax paid and the UK tax on that income**; multiple sources
are processed serially. Alternative treatment: deduct the foreign tax from the foreign income.
Observed: the app records `foreignTaxPaidOrDeducted` ("Foreign tax paid on this income —
withheld, not income", correctly excluded from income) but **no credit line appears in the
estimate at all**, while the FAQ promises "you can record foreign tax you have already paid and
claim Foreign Tax Credit Relief, so you are not taxed twice".
⇒ The cap could not be verified: either the estimate omits FTCR (applied at return stage) or the
relief is unimplemented. Report as a question, not a confirmed bug.
Foreign property is treated as a **separate business** from UK property (vendor copy matches
HMRC), with its own quarterly updates; its category keys differ (`rentIncome`,
`foreignTaxPaidOrDeducted`, `specialWithholdingTaxOrUkTaxPaid`).

## £150,000 cash-basis threshold
Rule (PIM1092): the cash basis is the **default** for property businesses run by individuals or
partnerships with receipts of £150,000 or less for the tax year; above that it is no longer the
default (accruals / election territory). Under the cash basis, receipts and expenses are
recognised when money moves — no debtors, creditors or balance sheet.
Observed: receipts pushed to £155,000 → **no warning anywhere** (checked the personal dashboard,
the property page and the property list; "150,000"/"cash basis"/"accruals" absent). The vendor
had stated in writing (29 Sep) that they *would* add such a warning — quote that.
Accruals: the product accepts only receipt/payment entries (no accrual inputs, no toggle, no
ageing), i.e. cash-basis-only by design, so there is no accruals arithmetic to get wrong — but
also no route for a user above the threshold.

## Ownership share (50:50 default, 60:40, Form 17)
Rule: each owner reports their own share; married couples/civil partners in jointly-held property
are usually taxed 50:50 by default, with a different split requiring Form 17 paperwork; other
joint owners normally follow beneficial ownership.
Observed: **correct** arithmetic. Share 100% → 60% → 40% gave "your share" £10,000 / £6,000 /
£4,000 on the property page, the same figures in the dashboard's "YOUR SHARE" block, and
`sharePercent` 100/60/40 in the API. Only one share value exists (no date range), so a mid-year
change necessarily applies to the whole year — the vendor had already acknowledged this
("a share that changes part-way through a year isn't supported yet"). No pro-rata arithmetic
exists, so nothing there can silently mis-compute.

## Capital gains on disposal
Rule: CGT on UK residential property — annual exempt amount £3,000, rates 18% / 24% depending on
remaining basic-rate band, private residence relief pro-rated plus the final 9 months, report and
pay within 60 days of completion. Note PIM1092: disposal receipts are income (not a chargeable
gain) where the asset cost was deducted under the cash basis.
Observed: the product has a "Capital gains" section under Other income & reliefs but it sits
behind "Two-factor authentication is required before connecting or filing with HMRC" plus a
live "Refresh from HMRC" action → **not testable** under a no-government-gateway constraint.
Their public CGT calculator states the 18/24% + £3,000 AEA + PRR + 60-day rules correctly.

## Incidental notes worth re-using
- `GET /api/v1/categories?sourceType=<type>` returns the exact accepted ledger keys per source
  type — fetch it before inventing payloads; it also reveals S24/FTCR-specific keys.
- Role changes move the product's landing page: after accepting an adviser invite, `/app`
  served the client dashboard; `?view=mine` restored the personal (estimate) dashboard.
- Capability flags are a cheap compliance check: `/api/v1/me` returned
  `capabilities.hmrcSubmission: false`, evidencing the API cannot submit, independent of the
  engagement rule.
