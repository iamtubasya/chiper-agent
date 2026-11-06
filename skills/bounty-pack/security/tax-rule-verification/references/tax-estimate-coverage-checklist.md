# Tax-estimate coverage checklist — scenarios, expected figures, observed behaviour

Worked from a UK MTD landlord/self-employment product (Quarterwise, 2026-09, vendor-granted Pro
account). Reusable as a template: swap the rate table, keep the scenario shapes. All scenarios were
driven through the product's REST API into ONE throwaway source, reading the dashboard estimate
panel (`/app?view=mine`) as the oracle, then cleaning every tax-year view.

## Expected figures used (UK 2026-27, rUK bands: PA 12,570 / basic 37,700 @20% / higher to 125,140 @40% / 45% above)

| Scenario | Entries | Expected | Observed |
|---|---|---|---|
| PA taper | rent £120,000, no expenses | allowance £1,000 applied → profit 119,000; PA = 12,570 − (119,000−100,000)/2 = 3,070 → taxable 115,930 → tax 38,832 | **38,832 exact** (and "saves you £600" = £1,000 × 60% — taper-aware) |
| Additional rate | rent £130,000 | profit 129,000 → taxable 129,000 → 7,540 + 34,976 + 1,737 = 44,253 | **44,253 exact** |
| Property loss | 2025-26: rent 10,000 − repair 25,000 = −15,000; 2026-27: rent 40,000 | loss b/f → 2026-27 profit 25,000 − 1,000 allowance = 24,000 → taxable 11,430 → tax ~2,286 | **5,286** — loss ignored, no "loss brought forward" field anywhere, year-end pages never mention losses |
| Allowance vs finance cost | rent 130,000 + repair 50 + mortgage interest 20,001 | compare allowance with the £50 of real expenses → profit 128,950 | **129,950** — panel says "actual expenses (£20,051) beat the £1,000 allowance"; £450 overstated at 45% |
| Rent-a-Room | receipts 7,000 + claim 7,000 | relief is claimed via the "amount claimed" field → net 0 | **0** — model is entry-driven; the £7,500 exemption is NOT auto-applied. Not a bug, document the model |
| £150k cash-basis warning | receipts/turnover 155,000 | warning per the vendor's own statement | **none** (property or SE) |
| Self-employment in the estimate | turnover 60,000 − costs 5,000 | should affect the estimate (and Class 4 NI) | **excluded**; the panel says "Self-employment is not yet included in the estimate" — pricing page advertises "Live tax estimate" |
| Scottish/Welsh bands | grep bundles for `scotland\|scottish\|welsh` | — | **0 hits** → regional rates not modelled |
| CGT public calculator | sale 400k / buy 250k / costs 20k; other income 0 then 45k; and 300k/100k/10k | gain 130,000 − AEA 3,000 → 28,218 ; with other income 45k → 30,164 ; gain 190,000 → 42,618 | **all three exact** (AEA £3,000, 18%/24% split by remaining basic band) |
| Rental-income public calculator (2026-10) | sweep rent 50k→160k, no expenses/interest; hand-compute in Python | correct for rent ≤ ~£115k; above that the tool over-states | **BUG in the tool** — wrong from ~£117k, grows through the £100k–£125,140 taper, plateaus at +£629 (= 5% × £12,570). e.g. rent 130k → tool 44,882 vs correct 44,253; rent 120k → 39,000 vs 38,832. The IN-APP estimate was correct for the same inputs — so audit the calculators independently, they can be the buggy surface |
| Tax-year boundary | expenses dated 5 Apr 2026 vs 6 Apr 2026 etc. | 5 Apr belongs to 2025-26 | **correct** — adviser CSV YTD summed only the 8 in-year rows (£80.36 of £80.36+£10.09) |
| MTD quarter allocation | 9 expenses on 5/6 Apr, 5/6 Jul, 5/6 Oct, 5/6 Jan, 5 Apr 2027 | Q1..Q4 splits | **not observable** — `Q1..Q4` columns in `/app/clients/export.csv` are submission STATUS (`late (due 2026-08-07)`) and stay blank pre-filing |

## Scenario shapes worth copying

- **Two-source isolation**: run each arithmetic scenario, then delete every entry before the next —
  the estimate aggregates ALL sources in the account, so a leftover from scenario N poisons N+1.
  Re-read `GET /sources` before each run and after cleanup.
- **Minimal-delta probes** for relief interactions: add £1 of the suspect item and watch whether an
  unrelated relief disappears (that is how the allowance-suppression basis was nailed).
- **Prior-year data**: to test carry-forward you must be allowed to write into the *previous* tax
  year. Entries dated inside the prior year are accepted by the API even when the dashboard's year
  selector only renders the current year.
- **Boundary sweep for periods**: one entry per boundary day with a unique amount, then read a
  per-period view. Unique amounts make the mapping unambiguous.
- **The public calculator is a free second oracle — and a target in its own right**: fill it by
  element id (`#proc`, `#buy`, `#costs`, `#oth`, `#rent`, `#exp`, `#int`, `#oth`) with the native
  value setter, then read the result string. Don't stop at one input: **sweep** a range across the
  band boundaries (e.g. rent 50k→160k), hand-compute the correct figure in Python for each, and
  print calc / correct / error. That is how the rental-income taper bug (+£629 plateau) surfaced —
  a single point looked plausible. Confirm which surface is wrong when calculator and product
  disagree.

## Round-two results (2026-10) — prior bugs fixed, two NEW defects in the public calculators

Re-ran the sweep a month later. The app estimate was exact everywhere; the two prior "wrong
arithmetic" items were now correct, and two fresh defects turned up in the vendor's own free tools.

| Scenario | Expected | Observed |
|---|---|---|
| PA taper, rent £120,000 | profit 119,000 / taxable 115,930 / tax 38,832 | **38,832 exact** ("saves you £600") |
| Additional rate, rent £130,000 | tax 44,253 | **44,253 exact**, top 45% |
| Section 24, rent £60,000 + interest £20,000 | taxable 47,430, reducer 4,000, tax 7,432 | **7,432 exact** |
| Allowance vs finance cost (rent 130k + £50 + £2,000 int) | allowance wins → profit 129,000, tax 44,253 | **FIXED** — "saves you £27.50", 44,253 |
| £150k cash basis (rent 155,000) | warning | **FIXED** — "over £150,000, so HMRC doesn't allow the cash basis…" |
| Tax-year boundary (5 vs 6 Apr 2027) | 5 Apr in 2026-27 | **correct** |
| Form 17 share 60% / 40% (rent 10,000) | your share 6,000 / 4,000 | **correct**, API tracks it |
| Loss c/f (2025-26 −15,000 → 2026-27 rent 40,000) | tax 2,286 | **5,286** — ignored, but DISCLOSED on the dashboard |
| Rent-a-Room | entry-driven | net 0 via "amount claimed" (model) |
| **Vendor's /tools/rental-income-tax-calculator** | see rule | **WRONG** — overstates by up to £629 (5% of PA); taper applied incorrectly, error 0 ≤£115k, grows through £100k–£125,140, plateaus |
| **Vendor's /tools/mtd-penalty-calculator** | 2027-28 late pay = 4% at day 15 + 4% at day 30 + 10%/yr | **£314 for both years** (uses 3%/3%) → understates 2027-28 by ~£100 on £5,000/40 days |
| /tools/stamp-duty-calculator | 295k single→4,750; +5% surcharge; FTB 0/5,000/none>500k | **all exact** |
| /tools/mtd-deadline-calculator | 7 Aug / 7 Nov / 7 Feb / 7 May | **exact** |
| /tools/capital-gains-tax-calculator | 28,218 / 30,164 / 42,618 | **exact** |
| /tools/mtd-penalty points | 4 points, £200, first-year grace 2026-27, +£200 each further miss | **exact** |
| /tools/limited-company-landlord | — | explainer, deliberately NO number (nothing to test) |

MTD late-payment constants (2026-27 vs 2027-28, from gov.uk): ≤15 days no penalty; 16–30 days
3%→**4%**; 31+ days 3%+3%→**4%+4%**, plus 10%/yr charged daily from day 31. Points: threshold 4,
£200 per point-triggered miss; **no penalty points for quarterly updates in 2026-27** (grace).
SDLT (E&NI): 0%≤125k; 2% to 250k; 5% to 925k; 10% to 1.5m; 12% above; +5% additional-dwelling
surcharge (applies >£40k); FTB relief 0%≤300k, 5% 300–500k, none >500k.

Ownership-share / Form 17 procedure: the "Your ownership share % → Update" control is TOTP-gated —
click Update, a "Code from your authenticator app" field appears, then submit with a FRESH code.
A property that is 100% allocated can't be shared ("already fully allocated — reduce another share
first"). Verified 60%→estimate £6,000, 40%→£4,000, restored to 100%.

AI receipt scan + import robustness (2026-10): image-embedded prompt injection had no effect;
JavaScript / external-URI / 40-page / truncated PDFs → graceful nulls, no SSRF/OOB; import handled
provider formats (Airbnb/Vrbo/Booking), BOM, £ and thousands separators, 5k rows, merged-cell xlsx
and multi-sheet xlsx (data sheet only); formula cells stored as text. Only gap: semicolon-delimited
CSV is not parsed.

Authority-state disclosure (do this before closing any tax engagement): prove no HMRC connection
and no submission — dashboard "Connect to HMRC" step still outstanding, /app/hmrc still shows the
connect flow, property "Quarterly period: not set yet", other-income "Not checked with HMRC yet",
`/api/account/export` `"submissions": []`, and API `hmrcSubmission:false`. Note the only POST the
year-end page makes on load is its own fingerprint action (`Next-Action` + `_1_fph` device blob) —
telemetry, not a submission; say so explicitly.

## Reporting shape that worked

Three explicit buckets, in this order: **verified correct** (with exact figures), **wrong
arithmetic** (pounds of difference at 20/40/45%), **not implemented / not testable** (with the
reason — e.g. needs an authority connection the engagement forbids). Then a one-line suggestion
list (payments on account, coverage statement in the estimate). State that the account was left
clean: N sources, 0 entries, verified through the product's own API.
