# UK property / MTD-ITSA rule set — formulas and observed behaviour

Sources for the rules below: gov.uk guidance, HMRC internal manuals (PIM = Property Income Manual),
HS263 (Foreign Tax Credit Relief) incl. the FTCR working sheet. Observed column = results from a live
audit of a UK MTD-recognised tax SaaS ("Quarterwise", 2026-09/10), tested on the auditor's own
account, all test data removed afterwards. Use the "observed" column as a template for what to look
for, not as an assumption about another product. **The observed column is a date stamp, not a fact
about today — re-run the scenario and report what you see now.** A 2026-10 re-test of the SAME
product found the §2 and §4 items below had been FIXED since the 2026-09 pass (see the
"re-test" notes); treat every "BUG" here as "was a bug as of this date".

## 1. Section 24 — restriction on residential finance costs

| | |
|---|---|
| Rule | From 2020/21 the full finance cost is **added back** (not deducted from profit). Relief is given as a **basic-rate tax reducer of 20%** of the finance cost, subject to limits, with excess carried forward. |
| Categories seen in the product's API | `residentialFinancialCost` (residential mortgage interest), `residentialFinancialCostsCarriedForward` / `broughtFwdResidentialFinancialCost`, `financialCosts` (other finance costs) |
| Expected panel signature | profit unchanged by the interest; a separate line `Finance costs relief (20%): −£X`; wording like "Before mortgage interest of £X, which is relief, not a deduction" |
| **Trap when designing the test** | For a basic-rate-only landlord, add-back + 20% reducer gives the **same tax** as the pre-2017 full deduction. Push income into the 40% band before you can prove which one the product implements. |
| Observed | **Correct.** Rent £60,000 + interest £20,000 → profit £60,000, taxable £47,430, reducer −£4,000, est. tax £7,432, top rate 40%. |

## 2. Property allowance (£1,000) — the comparison basis matters

| | |
|---|---|
| Rule | A flat **£1,000** deduction can be claimed **instead of** deducting actual property expenses (all-or-nothing: you cannot claim both). It is compared against *deductible* expenses. Finance costs are no longer deductible expenses (see §1), so they cannot be what displaces the allowance. Partial-relief restrictions exist for certain other reliefs; when in doubt quote the rule and let the vendor confirm. |
| How to test | Property with rent R and only finance costs F (no real expenses): expected = allowance applied (£1,000 deducted) whenever real deductible expenses < £1,000. Then add £1–£50 of a genuine expense and watch the panel wording. |
| Observed | **Was a BUG, FIXED by 2026-10.** (Historical: the panel compared the allowance against "actual expenses" totalling *real expenses + finance costs*, so with £50 repairs and £2,000 interest it printed "Your actual expenses (£2,050.00) beat the £1,000 property allowance", suppressing the allowance → ~£200–£450 overstated.) Re-tested 2026-10: correct. Rent £130,000 + £50 + £2,000 interest → allowance applied ("instead of £2,050.00 actual expenses, saves you £27.50"), profit £129,000, tax £44,253 — the £27.50 matched the hand-computed either/or difference. With £20,001 interest the panel correctly chooses expenses+relief instead. Re-verify, don't re-report. |
| Re-test (2026-10) | **FIXED — now correct.** The tool now performs the true either/or election. rent £130,000 + £50 repairs + £20,001 interest → uses expenses+relief (reducer £4,000.20). rent £130,000 + £50 repairs + £2,000 interest → applies the allowance and prints "Property allowance applied: −£1,000.00 (instead of £2,050.00 actual expenses, saves you £27.50)"; profit £129,000, tax £44,253. The £27.50 matched the hand-computed difference exactly. Rule anchor: GOV.UK "You cannot use the property allowance if you … claim the tax reducer for finance costs." |

## 3. Foreign Tax Credit Relief (FTCR) and its cap

| | |
|---|---|
| Rule | Credit for foreign tax paid on income also taxed in the UK, **capped at the lower of** the foreign tax paid and the **UK tax attributable to that income**. Multiple sources are processed serially (see the HMRC FTCR working sheet, HS263). |
| Product-side expectation | Withholding is recorded as *not income* and a credit line appears against the UK tax on that income. |
| How to test | Overseas property + rent £10,000 + foreign tax £8,000. Grep the whole estimate block **and** the product's own exports for a credit line. |
| Observed | **No credit line anywhere** — the £8,000 sat in the ledger correctly ("Foreign tax paid on this income … withheld, not income") but the estimate taxed the foreign rent in full, so the cap could not be evaluated at all. Reported as a question (applied only at return stage, or not implemented in the estimate?), not as a proven bug. |
| Extra defect | The property's own Excel export labelled the foreign tax as **"Tax withheld at source (paid to HMRC for you, not income)"** — for a foreign tax that is factually wrong; it is not paid to HMRC. Worth flagging separately: landlords read these exports as their records. |

## 4. Cash basis vs accruals basis, and the £150,000 threshold

| | |
|---|---|
| Rule | Under PIM1092 the cash basis is the **default** for property businesses run by individuals/partnerships with receipts of **£150,000 or less** for the tax year; receipts and expenses are recognised when money moves (no debtors/creditors). Above the threshold the default changes, so a cash-basis-only product should warn or route the user to accruals. |
| How to test | (a) Check whether any accruals input exists at all — if the ledger only accepts receipts/payments, there is no accruals arithmetic to be wrong (report as by-design, not as a pass or a fail). (b) Push receipts past £150,000 and look for a warning on every surface: dashboard, property page, properties list. |
| Observed | No accruals inputs exist anywhere (by design). **Was a gap, FIXED by 2026-10**: at £155,000 receipts the dashboard now shows "Your property income this tax year is over £150,000, so HMRC doesn't allow the cash basis. Quarterwise works on the cash basis only, so talk to an accountant before you file." |
| Re-test (2026-10) | **FIXED — warning now present.** Rent £155,000 → panel: "Your property income this tax year is over £150,000, so HMRC doesn't allow the cash basis. Quarterwise works on the cash basis only, so talk to an accountant before you file." Matches PIM1092 (cash basis default ≤ £150,000). |

## 5. Ownership shares (the "60:40" class) and Form 17

| | |
|---|---|
| Rule | Each owner reports **their share**. Jointly held property between spouses/civil partners defaults to 50:50, with the option to declare actual beneficial shares (Form 17 route) — hence 60:40 and other splits are legitimate. Non-spouse joint owners generally follow ownership shares. |
| How to test | Drive the share control 100% → 60% → 40% and read three things: the property page's "your share" line, the dashboard's "YOUR SHARE" totals, and the API's `sharePercent`. |
| Observed | **Correct** at all three percentages, consistent across UI and API (rent £10,000 → £10,000 / £6,000 / £4,000). A single percentage field with no date range means a share change necessarily applies to the whole year: no pro-rating exists, so a mid-year change cannot be represented — the limitation the vendor had already admitted. |

## 6. Capital gains on disposal

| | |
|---|---|
| Rule | Residential property gains: annual exempt amount **£3,000**, taxed at **18%** to the extent of remaining basic-rate band and **24%** above; Private Residence Relief covers the period lived in plus the final **9 months**; UK residential disposals must be reported and paid within **60 days** of completion, separately from the return. Note also PIM1092: disposal receipts of an asset whose cost was deducted under the cash basis are treated as **income**, not a chargeable gain. |
| How to test | Only if the product has a capital-gains input that is reachable. Check whether the entered figure is taxed at CGT rates (not income rates) and whether the £3,000 AEA is applied. |
| Observed | **Not testable within the engagement's rules.** The product's Capital gains section sat behind a 2FA + external-authority connection gate; enabling 2FA on the vendor-granted account would have locked the vendor out. Recorded as NOT TESTED with the reason, and the rule was compared against the vendor's own public CGT calculator instead (which uses the correct rule set above). |

## HMRC state disclosure (do this when the platform has an external-authority integration)

If any script of yours may have pressed a "Refresh from <authority>" control while hunting for a form,
verify the integration state afterwards and disclose it in the report in one sentence — the vendor
cares, and proactive disclosure is protected. When the operator asks you to *prove* nothing was
connected or submitted, run the whole read-only battery and report each line:

- property settings panel: "Quarterly period: not set yet" → nothing connected;
- other-income page: "Not checked with HMRC yet" → no pull has occurred;
- dashboard setup checklist: the "Connect to HMRC" / filing step is still outstanding;
- `/app/hmrc` renders the **connect** flow ("Connect to HMRC — Authorise …"), not a connected state;
- account data export: `GET /api/account/export` → `"submissions": []` (an empty list is the
  strongest single proof of "nothing filed");
- API: `GET /api/v1/me` → `capabilities.hmrcSubmission == false` (the API has no filing path at all);
- firm/portfolio export: each client row carries `Set-up: Not connected to HMRC`.

**An on-load fingerprint POST is not a submission.** Opening `/app/year-end` fires a server action by
itself (`Next-Action: <hex>`, body `taxYear` + an `fph` device-fingerprint blob) — telemetry the page
sends on mount, not a filing. Grep your captured POSTs for the authority routes and read the body
before worrying; only a body carrying return/quarterly figures (or a pressed Connect/Refresh control)
would be a submission.

Also flag genuinely misleading UI strings when you see them: a page rendered
"Checked with HMRC 30 Sept, 09:01" on first load although no authority account had ever been
connected. Ask whether it is a static string or real state.

## Testing-hygiene reminders specific to tax scenarios

- Bulk-write entries via the API when one exists (`POST /api/v1/sources/{id}/transactions`), including
  category keys taken from the product's own categories endpoint, so the scenario is exact and
  reproducible; keep the raw request as evidence.
- The estimate panel aggregates the whole account — re-read `GET /sources` and account for every
  source before interpreting a number.
- Delete trial entities and throwaway properties at the end (delete flows often require typing the
  entity name into a confirmation field), restore ownership share and account name, then verify with
  the API that the account is back to its original state.
