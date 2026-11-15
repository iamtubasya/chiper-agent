---
name: tax-rule-verification
description: "Use when auditing tax/finance SaaS arithmetic (HMRC/MTD cases) or any product that computes money from user-entered figures."
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [tax, hmrc, finance, business-logic, audit, mtdaas, correctness]
    category: security
---

# Tax / Financial Rule Verification

For the class of task: *"does this product's money arithmetic match the authoritative rules?"*
Typical trigger: auditing a tax or bookkeeping SaaS (UK MTD products, landlords, VAT, payroll),
or any product that turns user-entered figures into a tax/liability number. Ask for it by name
when the user says "cek aturan pajaknya", "verify the tax rules", "is this calculation right",
or hands you a list of rule names (Section 24, foreign tax credit, cash vs accruals, capital gains…).

This is **calculation-correctness auditing**, not security. It runs alongside a security audit of
the same target and reports to the same vendor — keep the two framed separately in the write-up.

**Run it unprompted when the target is a tax/finance product.** Do not wait to be handed a rule
list: this operator routinely asks, after the security work, *"is the business logic checked, and
does it comply with the latest tax rules?"* — and expects that answer to already exist. Do the
engine sweep in the same session as the security testing, and report the verified-correct figures
alongside the gaps (see the coverage checklist below).

## Rule zero: get the authoritative rule BEFORE touching the product

Never infer the rule from the product. Pull it from the authority's own pages/manuals and write it
down as expected input → expected output before you test. For UK tax that means gov.uk
guides and the HMRC internal manuals (e.g. `gov.uk/hmrc-internal-manuals/property-income-manual/pim1092`
for the cash basis). Where the product publishes its own rule pages (free calculators, guides,
FAQ), read those too: they tell you the rule set the vendor believes it implements, and a
contradiction between their copy and their arithmetic is the strongest form of bug report.

See `references/uk-property-mtd-rules.md` for the concrete UK property/MTD rule set, formulas, and
worked expectations — including the ones used against a live product in 2026-09.

## Method

1. **Design the scenario so the wrong rule produces a DIFFERENT visible number.**
   This is the single most important step and it is easy to get wrong. Example: Section 24
   (finance costs added back + 20% reducer) and the old full-deduction treatment give
   **identical** tax for a basic-rate-only landlord — the vendor's own page says so. To tell them
   apart you must push income into the higher band. Always sanity-check that your "correct" and
   "buggy" numbers differ before running the test.
2. **Write the entries through the product's bulk path** (the public API if there is one, else the
   import flow), not by clicking forms: exact amounts, exact categories, one request, reproducible.
   Keep the raw request in your evidence.
3. **Use the product's own summary panel as the oracle.** A dashboard line like
   `Profit / Taxable / Estimated tax / <relief> / Top rate` is a per-scenario answer key. Read the
   *whole* block (do not truncate your extraction — a relief line can sit below the fold of your
   slice). Record the exact strings you saw.
4. **Hand-compute the expected result from the rule** and compare line by line, not just the final
   number. A correct total can hide two offsetting wrong steps.
5. **Isolate with a minimal delta.** When panel wording suggests a wrong basis, change exactly one
   thing: add £1 of the suspect item and see whether an unrelated relief disappears.
   Observed: £0 real expenses + £2,000 mortgage interest → the £1,000 property allowance is never
   applied because the panel compares the allowance against "actual expenses" that *include* the
   finance cost. Adding £1 of interest moved nothing; adding a £50 repair moved the profit but the
   allowance stayed suppressed. That delta pattern is what proves the comparison basis is wrong.

## Coverage checklist — test the engine, not just the rules you were handed

The user's rule list is the floor, not the ceiling. When they later ask *"does it comply with the
LATEST rules?"* the answer has to come from a sweep like this, because every item below silently
produces a wrong number and none of them was on the original list. Run them as separate scenarios
(one reset property, entries via API):

| # | Item | Why it catches bugs |
|---|---|---|
| 1 | **Personal-allowance taper** (£100k–£125,140 for UK income tax) | The 60% effective-rate zone; a product that applies the flat PA overstates/understates badly and it is invisible below £100k. Push total to ~£120k. |
| 2 | **Additional rate band** above the taper end (£125,140) | Confirms the top band boundary and that the PA is fully withdrawn. |
| 3 | **Loss carried forward** from an earlier year | Perennial gap: the estimate computes this year in isolation. A prior-year loss must reduce this year's profit. |
| 4 | **Which income SOURCES the estimate includes** | Read the panel's own disclaimer ("X is not yet included"). A "live tax estimate" that omits a whole source type is a disclosure/copy mismatch even when internally consistent. |
| 5 | **Regional / residency variants** (Scottish+Welsh rates, non-dom, non-resident) | Grep the client bundles for `scotland|scottish|welsh`: if the string count is 0, the product cannot be applying those bands, and a user who lives there sees the wrong number. |
| 6 | **Social-insurance leg** (Class 4 NI / NICs / payroll-on-cost) | Often absent from a "tax" figure. Say plainly whether the product models it, and quote the panel wording rather than assuming. |
| 7 | **Relief-vs-expense interaction** (property/trading allowance vs finance costs, RAR claim, reliefs b/f) | This is where the real arithmetic bug lives (see pitfall below). |
| 8 | **Payments on account / deadlines** | Not arithmetic, but the omission users complain about most; report as a suggestion, not a bug. |
| 9 | **The public calculator(s)** | Vendors ship free tools ("CGT calculator") that apply the same rule set — a second oracle, and cheaper to test than the app. Verify them on 2–3 scenarios with different band splits. |
| 10 | **Period allocation** (quarters 6 Apr/6 Jul/6 Oct/6 Jan) | Test the *boundaries* through whatever per-period view exists. |

Record both directions: a **verified-correct** list with exact figures is as valuable in the report
as the bug list, and it is what lets you say "compliant" with a straight face. Quote the app's own
figures against your hand-computed ones (e.g. rent £120,000 → profit £119,000, taxable £115,930,
tax £38,832 — matched exactly, including the 60%-rate "saves you £600" line).

See `references/tax-estimate-coverage-checklist.md` for this checklist with the concrete expected
figures, the scenarios that expose each item, and the observed product behaviour.

## Pitfalls

- **Estimates aggregate every source in the account.** Scenario 2 inherits scenario 1's figures and
  the numbers stop making sense (income suddenly £130,000). Either run one scenario per account, or
  delete/reset the trial data between scenarios, or design scenarios so the aggregation is
  intentional and note it. Always re-read `GET /sources` before concluding.
- **Single-percentage ownership share has no date range** → the share necessarily applies to the
  whole year, so there is no pro-rating arithmetic to test. Report it as a product limitation the
  vendor already admits, not as a bug.
- **Gate chains hide whole features.** A section can be rendered but inert behind a 2FA / external-
  authority connection gate. Confirm the gate before claiming coverage, and record it as
  NOT TESTED rather than passed or failed.
- **Never enable 2FA (or bind a real external account) on a vendor-granted test account.** The TOTP
  secret ends up in your hands and the vendor loses access to their own account. If a feature is
  behind that gate, stop and ask the vendor for a test identity where *they* hold the second factor.
- **Respect the engagement's external-system rules.** If the vendor says "do not connect to the tax
  authority / do not submit anything", that includes clicking refresh-from-authority buttons. If you
  touch one by accident, verify and disclose it (see `references/uk-property-mtd-rules.md` §
  "HMRC state disclosure").
- **Do not treat a deliberately conservative estimate as a bug without a rule check.** Check whether
  the product states the figure is an estimate and whether the relief is applied at filing stage.
- **Hand-calc the taper from TAXABLE income, not from gross — or you will manufacture a false
  positive.** Once the personal allowance is reduced, the bands apply to the *taxable* figure and the
  basic band is **£37,700 wide from zero**, NOT £12,570–£50,270. Writing
  `higher = 0.40 * (taxable - 50_270)` makes your "expected" ~£5,000 too low right at the taper start
  and a CORRECT product then looks wrong. Right shape:

  ```python
  pa  = max(0, 12570 - (profit - 100000) // 2) if profit > 100000 else 12570
  tx  = max(0, profit - pa)
  t   = min(tx, 37700) * 0.20
  t  += min(max(tx - 37700, 0), 125140 - 37700) * 0.40
  t  += max(tx - 125140, 0) * 0.45
  ```

  Sanity-check one point that has **no taper at all** before trusting the helper. Worked anchor
  (2026-10): rent £110,000 → profit £109,000, PA £8,070, taxable £100,930 → **£32,832**, which matched
  the vendor to the penny and killed a would-be false report. The vendor's real defect that round was
  +£629 = exactly 5% of the £12,570 allowance — a constant-shaped error is a useful smell test.
- **When the authority's own table is terse, report the behaviour + both quotes, not a verdict.**
  HMRC's MTD late-payment table prints the first-year carve-out (`"or no penalty if it's your first
  year"`) on the 16–30 day row and does NOT repeat it on the 31+ row, while the prose says *"After 30
  days, we'll start to apply penalties."* A tool that charges the day-15 percentage at 31+ days with
  the first-year flag set is genuinely ambiguous. Write it as *"the setting stops having any effect
  after day 30 — is that intended?"*, print both quotes, and say plainly that the other reading makes
  the number right. A hedged, well-evidenced question costs nothing; a wrong *"your number is off by
  £150"* costs the credibility of the whole report.
- **Test a flag, not just a field.** The highest-yield class of defect found on a public calculator in
  2026-10 was not a wrong rate but a **checkbox that stops mattering**: the first-year toggle changed
  the answer at 16 and 30 days (£150 → £0) and did nothing at 31, 40 or 60. Sweep a boolean input
  across a second axis (days, bands, years) before believing it is wired at all.
- **Audit the vendor's own PUBLIC calculators with the same rigour as the app — and expect the APP
  to be the correct one.** These free tools are a second oracle, but they are *not* assumed correct.
  Observed 2026-10 (Quarterwise): the in-app estimate was exact while the vendor's own
  `/tools/rental-income-tax-calculator` overstates tax through the personal-allowance-taper zone by
  up to a flat **£629 (=5% of the £12,570 PA)** above ~£117k profit, and its `/tools/mtd-penalty-calculator`
  applies the 2026-27 late-payment rates (3%/3%) to **2027-28** as well, where gov.uk says 4%/4%
  (understates £100 on £5,000 paid 40 days late). A vendor-vs-its-own-tool contradiction is the
  sharpest form of bug report — quote the tool's own headline back at them (this tool's said it
  "correctly appl[ies] the Section 24 … restriction that most buy-to-let calculators get wrong").
  Read the calculator's constants straight out of the JS bundle (`grep` the tool's chunk for the
  band/rate object), then confirm 2–3 points through the UI with the **native value setter** (React
  ignores a plain `.value=`).
- **Reset EVERY field between scenarios, or a stale value will look like a bug.** These calculators
  keep their state across a re-fill. Driving the CGT tool through successive scenarios while only
  setting the fields named in the current one left the previous scenario's `other income` (45,000) in
  place; the tool then returned 44,564 where the rule says 42,618, and the gap looked exactly like a
  defect. It was produced by my own leftover input. Before each scenario, enumerate the form's inputs
  (`[...document.querySelectorAll('input,select')].map(i=>i.id||i.name)`) and explicitly zero the ones
  the scenario does not set — then re-read the panel. A "bug" that vanishes once you clear an untouched
  field was never a bug; a real one survives a clean reset.
- **Hand-compute from BAND WIDTHS, not from band thresholds.** On UK income tax the higher-rate
  threshold (£50,270) is a TAXABLE-INCOME figure that already has the personal allowance removed; the
  arithmetic is 20% on the first £37,700 of taxable income, 40% above it. Applying 40% to
  `(taxable − 50,270)` instead yields a plausible-looking number that is wrong by about
  `(50,270 − 37,700) × 0.40`, and it will make a correct product look broken. Write the reference
  implementation as explicit band widths
  (`min(tx,37700)*0.20 + min(max(tx-37700,0),87440)*0.40 + max(tx-125140,0)*0.45`) and sanity-check it
  against a figure the vendor has already verified before accusing anyone.
- **A setting that works in one band and silently stops working in the next is a real report item —
  but check the authority's table layout before calling it a defect.** Quarterwise's MTD Penalty
  Estimator: the "this is my first year" flag correctly drives the penalty to £0 at 16–30 days late,
  then has NO effect at 31+ days (identical figure to unticked). GOV.UK prints the first-year carve-out
  ("no penalty if it's your first year") on the 16–30 row only, and the 31+ row does not repeat it, so
  the table genuinely admits two readings. Report the *observable inconsistency* (the flag silently does
  nothing after day 30, contradicting the tool's own copy — "no late-payment penalty within 15 days, or
  30 days in your first year") and say plainly that the vendor may read the 31+ row differently. Do not
  assert one "correct" number when the authority's own table is terse; the honest framing is still
  actionable.
  **Re-checked 2026-10-08: BOTH of those defects were FIXED.** The rental calculator now matches the
  hand-computed figures to the penny at every point swept (£110k→32,832 · £118k→37,632 · £120k→38,832 ·
  £124k→41,232 · £130k→44,253 · £160k→57,753) and the penalty estimator keys its rate on the selected
  tax year (2026-27 → £314, 2027-28 → £414 on £5,000 paid 40 days late). Every "observed" figure
  anywhere in this skill is a hypothesis about a past build, never a fact about today — re-run the
  scenario and report what you see this time.
- **Re-verify the previous round's bugs before repeating them; they may already be fixed.** Two items
  reported wrong in the prior round were CORRECT this round (property-allowance-vs-finance-cost
  either/or comparison; the £150k cash-basis warning). Treat last session's finding list as
  *hypotheses to re-test*, not facts; a gone bug is a verified-correct line in the new report.
- **Authenticator-gated controls need a two-step, freshly-timed code.** Changing the ownership share
  (Form 17) showed only "Update"; the click merely *revealed* a "Code from your authenticator app"
  field, and the real submit is the second step. Generate the TOTP immediately before submitting
  (30-second window) or the second attempt fails with "That code is not correct". Same gate on
  "Share this property".
- **Report the exact source/URL of any tool you flag**, and quote its own claim — the operator asks
  "which site is this calculator from?". Name it (e.g. the vendor's own `/tools/<slug>`), never
  "a public calculator".
- **Audit the vendor's OWN free calculators — they are a second oracle AND can themselves be
  wrong.** Sweep one input across the band boundaries, hand-compute the correct tax in Python, and
  diff. Observed (2026): the in-app estimate was correct everywhere, but the public "Rental Income
  Tax Calculator" over-stated tax from ~£117k rent upward, plateauing at +£629 (= 5% of the £12,570
  personal allowance) — a real customer-facing defect that the product's own engine did not have.
  Fill these React tools with the native value setter (`Object.getOwnPropertyDescriptor(
  HTMLInputElement.prototype,'value').set.call(el,v)` + `input`/`change`), not `.value=`, or the
  result never updates. State which surface is wrong when the two disagree.
- **Prior "observed" figures in this skill go STALE — re-verify, never assume.** A product ships
  fixes; a bug recorded last quarter may be gone and a "correct" item may have regressed. Two
  previously-observed bugs (property-allowance-vs-finance-cost comparison; missing £150k cash-basis
  warning) were BOTH fixed on re-test in the next round — same product, same method, correct now.
  Re-run the scenario fresh and report what you see this time; the reference's observed column is a
  template, not a fact about today.
- **Cleanup must walk every tax-year view, or leftovers accumulate silently.** The entries list
  renders ONE tax year by default, so test rows dated in the previous year survive every
  "delete until zero" loop and reappear as duplicate pairs in the next session's scenarios.
  Iterate the year parameter (`?ty=2025-26`, `?ty=2024-25`, …) and finish with a per-source API
  count, not a DOM count. Also expect more than one throwaway source: an earlier import run may
  have created `<filename>` as its own property.
- **A carried-forward-loss test needs the *prior* year's data inside the product.** Put the loss in
  the earlier tax year and the profit in the current one; the current-year estimate is the oracle.
  If the product only offers the current year in the dashboard year selector, say so and mark the
  item NOT TESTABLE rather than guessing.
- **Aggregate columns can be STATUS, not amounts.** An adviser/portfolio CSV with `Q1..Q4` headers
  looked like the per-quarter split; it is actually per-quarter *submission status*
  (`late (due 2026-08-07)`) and stays empty for unfiled quarters. Read the header row AND one
  populated example before treating a column as a figure. Where the split is only computed at
  filing time, the honest result is "period allocation not observable without connecting to the
  authority".
- **Red flag for a finding (relief displaced by a non-deductible cost):** when a panel says
  "your actual expenses (£X) beat the £1,000 allowance", check what £X is composed of. If it
  includes finance costs (which are a *relief*, not a deductible expense post-S24), the allowance
  comparison basis is wrong and the estimate overstates tax by `allowance × marginal rate`.
  Verify with a minimal delta: rent £130,000 + £50 repair + £20,001 interest reproduces
  `actual expenses £20,051 beat the £1,000 allowance` → £450 overstated at 45%.

- **Authority pages: fetch with curl, not `web_extract`.** On this host `web_extract` was
  search-only (ddgs) and refused URL fetches. `curl -s -A "Mozilla/5.0" <gov.uk url>` piped through
  a strip-tags regex gets gov.uk guidance text, and HTML tables parse cleanly with
  `re.findall(r'<tr>(.*?)</tr>', t, re.S)` → gives you the authoritative rate table to quote
  directly in the report.
- **Ownership-share / joint-split (Form 17) is second-factor gated AND needs the property not to be
  "already fully allocated".** You cannot share while your own share is 100%; the first click on
  "Update" only *reveals* the code field, and the real submit is the second step. Once satisfied the
  split applies correctly and consistently across UI + API (share 60% → estimate used 60% of rent).

- **A toggle that changes the answer at one input value but NOT at another is a finding shape — sweep
  the toggle, don't spot-check it.** Verified 2026-10-08 (Quarterwise MTD Penalty Estimator, gov.uk
  late-payment table). The "this is my first year using Making Tax Digital" checkbox returns £0 at 16
  and 30 days late (vs £150 cleared), then from day 31 onward the figure is **identical whether the box
  is ticked or not** — £301 at 31 days, £314 at 40, £341 at 60. Method:
  `for days in [16,30,31,40,60]: for first_year in (True,False): read the panel figure` and diff. A flag
  whose effect *stops changing the output* at a boundary is the signal; a single 40-day check would have
  shown "box ticked, £314" and told you nothing.
  Report it carefully: GOV.UK attaches "or no penalty if it's your first year" to the **day-15** element
  and its prose says "After 30 days, we'll start to apply penalties", so a first-year 31+ day payment
  should carry only the day-30 charge (≈£163.70 on £5,000 at 40 days) — but the table does not repeat the
  carve-out on the 31+ row. State the ambiguity and the £ difference; do not assert a wrong number you
  cannot source. Direction matters: this class overstates the charge, which is the direction that
  generates support tickets.

- **The in-app estimate may sit behind the authority connection — check that BEFORE promising an engine
  sweep.** On a product whose annual/quarterly estimate renders only after the HMRC (or equivalent)
  OAuth gate, an engagement that forbids connecting to the authority cannot reach it. Verify which
  surfaces actually render, then say so as a **limit**: the sweep collapses to (a) the account's own
  profit/relief panels (e.g. "Net profit / Residential finance / Relief, not deducted. After it:") and
  (b) the vendor's public calculators. Do not silently redefine the scope of your own coverage, and do
  not connect to the authority to unblock it.

- **When the in-app estimate sits behind the tax authority's connection, it is NOT sweepable — say
  so and sweep the public tools instead.** Some products only render the live estimate once the
  account is authorised with the authority. If the engagement forbids that connection (it usually
  does), the 10-item engine sweep below cannot run; the vendor's own free calculators and the
  account's own source/ledger panels become the observable surface. Do not silently substitute one
  for the other — write "no authority connection was made, so the in-app estimate and the filing
  path were not exercised" into the report's limits. Recipe for the public-tool sweep (field-id
  discovery, the native-setter harness, the band-boundary matrix, checkbox-flag matrices):
  `references/public-tax-calculator-sweep.md`.
- **A flag/checkbox that changes the answer in one band and is inert in another is the finding
  shape — and you only see it with a state-verified matrix.** Toggle label controls like
  "this is my first year" across the parameter's bands and read `checked` after every click; an
  unverified click makes a working flag and a dead flag look identical. Observed 2026-10: the MTD
  Penalty Estimator's first-year box gives £150 → £0 at 16–30 days late and £314 vs £314 at 31+
  days, i.e. the exemption is applied in the 16–30 band only. Report that kind of item as
  behaviour + quoted rule + both readings, never as a bare "your number is wrong".
- **Set every field for every scenario, and derive the band arithmetic from the bands.** A field
  left over from the previous scenario silently changes the next answer (a CGT sweep read 44,564
  instead of 42,618 because `oth` still held 45,000 from the run before), and a hand-calc written
  off the *gross* bands will "prove" a correct tool is broken — on taxable income the basic band is
  £0–£37,700 wide, so `higher = taxable - 37700`, not `taxable - 50270`.
- **Re-test the previous round's findings as hypotheses, and expect fixes to have landed.**
  2026-10 re-run: the public calculator's personal-allowance taper was fixed, the MTD late-payment
  year keying was fixed, and one caption/arithmetic mismatch was still present. Put every fixed
  item in the report as a verified-correct row with its exact figures.

### Hand-computation pitfalls that manufacture false "defects"

- **Tapered personal allowance → use band WIDTHS on taxable income, not the £50,270 threshold.**
  Once the allowance is withdrawn the taxable figure no longer starts at zero-with-PA, so the
  basic-rate band is £0–£37,700 of *taxable* income and higher rate runs £37,700–£125,140. Applying
  the £50,270 threshold to the taxable figure understates the tax and produces a phantom "the tool
  overstates by £X" finding. Worked miss this session: rent £110,000 → profit £109,000, PA £8,070,
  taxable £100,930. Wrong method gave £27,804; correct is 37,700×20% + 63,230×40% = **£32,832**,
  which is what the tool said. Sanity-check your own arithmetic first — a disagreement with the
  product is at least as likely to be your bug as theirs.
- **Reset EVERY input between scenarios.** React tools keep their prior value; a field you did not
  re-set carries the last scenario's number into the next one and fabricates a mismatch. Observed:
  a CGT "£44,564 vs £42,618" discrepancy was purely `oth` still holding 45,000 from the previous
  case. Read the whole form state back (all fields) before trusting a diff.

### Driving the calculators (React) — what actually takes the input

- Text inputs need the native value setter plus both events, and so does a `<select>`:
  `Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(el,v)` then
  dispatch `input` + `change`. A plain `el.value = x` is ignored by the framework.
- A checkbox is toggled with `.click()`, never a value-set — and **verify the state changed** before
  reading the result (`el.checked`), otherwise "the flag does nothing" may just be a click that
  never landed.
- Map the tool's own field ids first (`[...document.querySelectorAll('input,select')].map(i=>i.id||i.name)`)
  instead of guessing names from the label text; guessing cost a whole sweep in this session.

### A flag that works in one band and is silently inert in another is the highest-signal pattern

Observed on the MTD penalty estimator: the "this is my first year" checkbox changes the answer at
16–30 days late (£150 → £0) and has **no effect at all at 31+ days** (£314 either way). That shape —
the same setting honoured in one branch and dropped in the next — is worth chasing, because it is an
internal inconsistency rather than a rules disagreement, and the product's own copy usually backs you.

**But when the authority's text is genuinely ambiguous, frame it as a clarification, not a defect.**
HMRC's late-payment table prints the first-year carve-out on the 16–30 row and does not repeat it on
the 31+ row, so "the day-15 element should be nil at 31+ days too" is a reading, not a certainty.
Write it as: what was observed (with the 3× repeat), the two quoted passages, both candidate figures,
and "if you intend the other reading, this is a wording point only". Never let an ambiguity argument
into the defect column — it is the fastest way to burn credibility on a VDP.

### The in-app estimate may be entirely behind the authority connection

If the engagement forbids connecting to HMRC (a standing rule on some engagements), the in-app
estimate and the filing path are **NOT TESTABLE** — say so explicitly and sweep the vendor's *public*
calculators instead, which need no connection. Do not silently skip the calculation work, and do not
pretend the in-app engine was covered. Also note which panels remain reachable without the
connection: the per-source summary block (income / expenses / net profit / finance costs / "relief,
not deducted") is, and it is a real oracle for the profit-and-relief legs.

## Reporting

- Frame as *calculation correctness*: rule → what the rule requires → what the product did → the
  money difference at 20% / 40% / 45%. A number in pounds lands; "the logic is wrong" does not.
- Quote the vendor's own copy back at them when it contradicts the arithmetic
  ("We've used whichever saves you more" against a run where the allowance is suppressed).
- Separate three categories explicitly in the write-up: **verified correct**, **wrong arithmetic**,
  and **not implemented / not testable** (with the reason).
- State the limits: self-scoped to your own test account unless you proved otherwise, and whether
  the figure feeds a real submission or only a displayed estimate.

### Delivery: the correctness report travels separately from the security report

They have different audiences and different language, so stage them as **two artifacts** — both in
**English** (the operator's own notes are Indonesian, but nothing vendor-facing ever is — not the
subject line, not the PDF; see the language section in `references/product-correctness-report-shape.md`,
which also gives the programmatic language check to run before staging):

- Security items → the existing reply draft inside the vendor thread, exploit evidence attached.
- Correctness items → its own PDF (one document for the whole sweep, not one per rule) staged as a
  **separate draft with its own subject**, labelled so nobody reads it as a vulnerability report:
  subject and title both say *"… (round two, not a security report)"*, and the body opens by saying
  it is about whether the numbers are right with no claim or payment request attached.
- Put the **verified-correct figures inside that same PDF**. It is what makes "compliant" credible
  and stops the document reading as a hit-piece.
- **De-duplicate before delivery.** These items usually get appended to the security reply during the
  same session (the thread is open, it is convenient). If the separate report also goes out, strip
  the tax section from one of the two, and record in the engagement summary which draft carries
  what. The same finding arriving twice invites "we already answered that".

See `references/product-correctness-report-shape.md` for the section order and label wording that
survived review, and for how the split is written into the engagement summary.

## Hygiene

Tax scenarios create junk books with big round numbers. Delete every test entity (entries, then the
throwaway properties via the product's own delete-with-name-confirmation flow) and restore changed
settings (ownership %, account name). Verify with the product's API that the account is back to its
original state, and say so in your report. A vendor hands you a clean account; give it back clean.

## References

- `references/public-calculator-sweep-2026-10.md` — observed public-calculator sweep results for a later round (which prior defects are now FIXED, the full verified-correct table, the default-true SDLT toggle trap, the import-preview and AI-extraction verification recipes, and the correctness-report delivery gate)
- `references/uk-property-mtd-rules.md` — UK property/MTD rule set with formulas, the observed
  in-app estimate is behind an authority connection you are forbidden to make: field-id discovery,
  the React native-value-setter harness, "set every field per scenario", band-boundary sweeps,
  state-verified checkbox matrices, the MTD first-year/31+-day trap, and the 2026-10 observed results.
- `references/uk-property-mtd-rules.md` — UK property/MTD rule set with formulas, the observed
  Quarterwise behaviour per rule (2026-09), and the disclosure note about the external-authority
  state check.
- `references/tax-estimate-coverage-checklist.md` — the 10-item engine sweep with concrete
  scenarios, expected vs observed figures, the prior-year-loss / allowance-vs-finance-cost / RAR /
  regional-rate results, and the three-bucket reporting shape.
- `references/product-correctness-report-shape.md` — how to package and deliver the findings as a
  *separate non-security report* (label wording, 8-section order, "what is correct" table, and the
  de-duplication rule when the same items also sit in the security reply thread).
- `references/uk-tax-rule-bank-2026-27.md` — condensed, quotable authority bank: rUK income-tax
  bands + PA taper, MTD phases/deadlines/penalty points and late-payment rates, SDLT bands + FTB
  relief, CGT (AEA/18%/24%/PRR), each with the gov.uk URL and a one-line curl recipe. Use it as
  the "expected" in every scenario so you never infer a rule from the product.
- `references/public-calculator-sweep.md` — the Playwright harness for driving React calculators
  (native value setter on inputs AND selects, `.click()` + state-assert on checkboxes, mandatory
  per-scenario field reset), the observed input-id map for a UK MTD landlord product, and the
  boundary sweeps that actually expose defects.

## Absorbed playbooks (complete sub-packages under `references/`)
Umbrella for "verify money arithmetic against authoritative rules". The three former siblings keep
their own reference banks:

- `references/tax-calculation-audit/PLAYBOOK.md` — UK property/MTD calculator probing, the recurring
  bug shape, the two traps that manufacture false findings, re-verification rounds
  (`references/uk-property-tax-rules.md`, `scripts/totp.py`).
- `references/tax-rule-correctness-review/PLAYBOOK.md` — condensed review method plus the "let the
  product compute your test" oracle trick.
- `references/financial-logic-verification/PLAYBOOK.md` — the generic money-handling version: the
  quote/check endpoint (money testing with no payment method) and the checkout / order-object ladder
  for fees, interest and PSP fronts.
