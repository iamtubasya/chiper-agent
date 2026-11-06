# Public-calculator verification sweep — observed results, 2026-10 (Quarterwise, round 3)

Companion to `tax-estimate-coverage-checklist.md`. Same product family, later round. **Everything here
is a template for the method, not a fact about today — the vendor ships fixes, so re-run every row.**

## Fixed since the previous round (re-tested, now correct)

| Tool | Prior defect | This round |
|---|---|---|
| Rental Income Tax Calculator | personal-allowance taper overstated by up to a flat **£629 = 5% × £12,570**, from ~£117k profit | matches to the penny at every swept point |
| MTD Penalty Estimator | stored ONE late-payment rate set and applied it to every tax year (2027-28 understated) | 2026-27 → £314, 2027-28 → £414 for £5,000 paid 40 days late |
| Section 24 Calculator | "tax now" leg over by ~£629 at £130k rent | 130,000 / 0 / 20,000 → **£40,703** (= 0.2·37,700 + 0.4·87,440 + 0.45·4,860 − 20% × 20,000) |

Re-tested former bugs are a *verified-correct* row in the new report, not a repeat finding — and they
prove to the vendor you re-checked rather than re-sent.

## Verified correct this round (hand-computed from the rule, matched to the penny)

| Tool | Input | Result |
|---|---|---|
| Rental Income Tax Calculator | rent 110k / 118k / 120k / 124k / 130k / 160k | 32,832 / 37,632 / 38,832 / 41,232 / 44,253 / 57,753 |
| MTD Penalty Estimator | 2026-27, any missed updates | £0 (no points in 2026-27) |
| MTD Penalty Estimator | 2027-28, 4 / 5 / 8 missed | 200 / 400 / 1,000 |
| Section 24 Calculator | 60,000 / 0 / 20,000 | now 7,432 · old rules 5,486 · extra 1,946 |
| Section 24 Calculator | 50,000 / 5,000 / 10,000 | 4,486, extra 0 (basic rate, no S24 cost) |
| Capital Gains Tax Calculator | 400k / 250k / 20k | 28,218 |
| Capital Gains Tax Calculator | same + other income 45k | 30,164 |
| Stamp Duty Calculator | 295k single / +additional / FTB 295k / FTB 400k / FTB 500,001 | 4,750 / 19,500 / 0 / 5,000 / 15,000 |
| MTD Readiness Checker | 60k / 40k / 25k / 15k | 6 Apr 2026 / 2027 / 2028 / not mandated yet |
| MTD Qualifying Income | property 30k + self-employment 15k | 45,000 |
| Accountant vs Software | 3 properties | saving £151–£501 |

The SDLT row is the one worth copying: the calculator **defaults the "additional property" box to
ticked**, so a single-property check reads £19,500 and looks wrong until you clear it. Always print
the checkbox labels next to the result; a default-true toggle is not a bug, a *documentation* gap.

## The one new item

`MTD Penalty Estimator` — the "this is my first year using Making Tax Digital" flag changes the answer
at 16 and 30 days (£150 → £0) and has **no effect at all** at 31, 40 and 60 days (£301/£314/£341
identical with the box ticked or cleared). Reported as a hedged question with both quotes, not a
verdict, because HMRC's table is ambiguous (see the SKILL.md pitfall on terse authority tables).
Method worth reusing: **sweep every boolean input across a second axis** before believing it is wired.

## Non-tax surfaces checked in the same round (same product)

- **Import preview**: a CSV whose description column held `<img src=x onerror=…>` and
  `<script>…</script>` rendered as **text**, 0 injected elements; malformed CSV (unterminated quote,
  tabs, embedded newline, 5 KB field) parsed into the mapping step without error. Testing through the
  *preview* rather than committing avoided all ledger residue.
- **AI receipt extraction** (`POST /api/ai/extract-expense`, session-authed, JPG/PNG/WebP/PDF only):
  a generated PDF returned `1234.56 / 2026-04-15 / "TEST MERCHANT LTD - Boiler service" /
  repairsAndMaintenance / confidence 95`; a PNG returned `300 / 2026-05-02 / "ACME PLUMBING…"`. A
  prompt-injection block placed on **page 2** of the PDF had no effect. Correct extraction + injection
  resistance is a *verified-correct* line, and it is cheap to produce with reportlab + PIL.

## Delivery shape used

Correctness travels as its **own** English PDF + its own Gmail draft (subject ends
`(…, not a security report)`), never inside the security reply thread. The PDF carries: framing, meta
table, summary table with an explicit **direction-of-error** column, one section per item with a
`product says / should be` table, a **"what is correct"** table (22 rows in this round), honesty
limits, suggested fixes. Build gate: `qa_pdf_layout.py <pdf> --margin-mm 14.8` for the 42 pt style
module, plus a text-layer assert for raw entities and for the operator's Indonesian function words.
