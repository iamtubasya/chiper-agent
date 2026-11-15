---
name: tax-calculation-audit
description: "Use when auditing tax-calculation correctness in tax/bookkeeping software (UK MTD, property, self-assessment first). Verifies arithmetic against published rules, not against vibes."
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [tax, uk, hmrc, mtd, property, business-logic, correctness, bug-bounty]
---

# Tax-Calculation Correctness Audit

For when the target is tax software and the question is "does it compute the right number",
not "does it let me in". Distinct from the security playbooks: the artefacts are arithmetic
scenarios and the vendor's own estimate panels, the findings are money-affecting, and the
authority is the published rule (HMRC/gov.uk), not an OWASP category.

This user asks for this class repeatedly on UK tax/accounting SaaS products, and expects the
rule cited to the official source, not to a blog.

## Method

1. **Read the product's own claims first.** Its public calculators, FAQ and guides encode the
   rules the vendor *thinks* it implements — that becomes your oracle and your "expected"
   column. A vendor calculator that is right next to a bookkeeping engine that is wrong is
   the strongest possible framing.
2. **Build controlled scenarios in your own test account.** Round numbers, one variable at a
   time, entered through the real UI *and* the public API where one exists (API is faster and
   exact).
3. **Read the product's own breakdown as the oracle.** Tax apps usually itemise: income,
   expenses, allowance applied, taxable, tax, credits, top rate. Copy that block verbatim —
   it is both the evidence and the arithmetic trace.
4. **Isolate with add/remove, not with argument.** Add one entry, read the block, remove it,
   read again. The delta is the finding, and it doubles as the cleanup.
5. **Compare to the rule and compute the correct number by hand.** State the delta in money
   ("£200 too much at 20%, £450 at 45%"), not just "wrong".
6. **Never connect to the tax authority's live system** unless the engagement explicitly
   authorises it. Many tax apps gate whole sections behind an authority link — that is a
   finding about the product ("a landlord can't record a 60-day return figure without
   linking"), not a reason to cross the line. Report the gate; don't breach it.
7. **Clean up:** delete the scenario entries, restore any shares/settings you changed, and
   verify the account is back to its delivered state (counts via the API).

## What to probe (UK property/MTD shape)

- Finance-cost restriction (§24): interest must be ADDED BACK, not deducted, with a 20%
  basic-rate reducer. Check the profit line AND the reducer line.
- Property allowance (£1,000): "whichever saves you more" is a claim you can falsify by
  checking what it compares against. **The decisive isolation: hold DEDUCTIBLE expenses at £0
  while a residential finance cost is present, and read the panel twice (finance vs no finance).**
  If the allowance is withheld when finance costs exist, the comparison is including finance costs —
  which are not deductible expenses. Two-leg recipe + exact panel sentences:
  `references/quarterwise-round-2026-10.md`.
  Report a confirmed allowance/finance-cost interaction as a QUESTION with the numbers, not a
  claimed wrong figure: the copy itself may say the allowance cannot be claimed "as well as
  mortgage interest relief", which makes withholding defensible and leaves only the wording wrong.
  Ask the vendor for the statutory basis and to confirm the intended comparison.
- Foreign tax credit: recorded vs credited; and the cap (lower of foreign tax paid and UK tax
  on that income). If no credit line exists at all, the cap is unverifiable — say that.
- Basis: cash vs accruals; the £150,000 receipts threshold; any promised warning.
- Ownership shares: the share arithmetic, and what happens when a share changes mid-year.
- Capital gains on disposal: rates, annual exempt amount, reporting-adjacent gates.
- Edge arithmetic: band boundaries, personal-allowance taper, allowance vs actual expenses,
  carried-forward amounts, and any line the estimate labels as "estimate only".

## The recurring bug shape (look here first)

**A rule enforced on one write path and not the others.** Tax apps grow multiple ingest paths
(entry form, import mapping, public API, review queue). Fixes get shipped on the form and the
rule stays missing on the rest. Test the SAME invariant on every path that reaches the ledger
— create, edit, delete, import, API — and again for a shared/co-owned book, where the same gap
lands in somebody else's records.

Second most common: **a comparison uses the wrong population** — e.g. an allowance compared
against a total that includes amounts which are not deductible expenses, silently denying the
allowance (see `references/uk-property-tax-rules.md`, property allowance vs finance costs).

## Two traps that manufacture false findings (both hit in one session)

**1. A scenario where the correct rule and the broken rule produce the same number.**
For a basic-rate landlord, deducting mortgage interest and applying the §24 20% reducer give
the *identical* tax figure — the vendor's own help page says so. Any scenario that stays in
the basic band therefore "passes" whether or not the product is right. Push income into the
higher band (rent £60k + interest £20k already separates the two paths by ~£1,746) and compare
the intermediate lines (`Taxable`, `Finance costs relief`) rather than the headline total.
Before running anything, ask: *if the code were wrong, would this scenario look different?*
If not, redesign the scenario.

**2. The control failed too — so the harness is wrong, not the product.**
Two near-misses in the same engagement, both of which would have become fabricated findings:

- A value the validator *correctly* rejected was blamed on replay protection. The NINO
  `AB123456E` is invalid (suffix must be A–D) and the server said so —
  `1:{"error":"Enter a valid National Insurance number, e.g. QQ123456C."}`. The lesson: read the
  raw server response before attributing a refusal to the control you are testing.
- A "Confirm" button that produced no POST at all was blamed on the server until the real
  cause surfaced: the handler opens a native `confirm()`, and Playwright auto-dismisses native
  dialogs, so the submit never fired. See `nextjs-server-actions-audit` for the fix.

Rule: whenever a "control" path (legitimate value, legitimate category, legitimate click)
also fails, stop and repair the harness. Only after the control passes does a failure on the
suspect path mean anything. Write "unverified" rather than a finding.

**3. The read-back raced the write — the change WAS real, the measurement was early.**
Quarterwise 2026-10: favourite buttons were clicked via the DOM, the list was read back ~immediately,
it read unchanged, and a "the writes don't persist" note started forming. It was wrong — the list had
gone 2 → 7. UI writes are async (server action + refetch); reading state in the same breath measures
the *pre-write* snapshot. When the question is "did the write take?":

- re-read after the network settles (the mutation response / `networkidle`), not a fixed sleep, and
  read **twice** before concluding "unchanged";
- prefer a server-truth read (fresh GET of the resource) over the in-page DOM the write just touched;
- a single "unchanged" observation is never enough to declare a control dead — it is the default
  shape of a timing artifact.

Mirror of trap 2: there the CONTROL failed and the harness was at fault; here the SUSPECT path
"failed" and the harness was at fault. Same reflex — a surprising negative means suspect the
measurement first, the product second.

## Adjacent finds worth logging while you are in there

- **Mis-labelled relief lines in exports.** A foreign property's foreign tax was exported as
  "Tax withheld at source (paid to HMRC for you, not income)" — it is not paid to HMRC at all.
  Export wording is part of the arithmetic story a landlord files, so note it.
- **Fixed cost of a report panel that never appears.** If a feature is visible in the UI but
  the panel never shows a value (e.g. no credit line anywhere for FTCR), that absence is the
  finding, and the cap becomes "unverifiable" rather than "wrong".



## Reporting rules

- A tax-correctness finding is a PRODUCT DEFECT, not a security vulnerability. Say so in the
  title and rate it honestly (usually Low) — this user prefers an honest Low over an inflated
  Medium, and vendors accept arithmetic bugs readily when the evidence is exact.
- Where the rule interaction is genuinely arguable (e.g. whether an allowance can coexist with
  a relief), report it as a QUESTION with the numbers, not as a claimed bug.
- Always include a "verified working" list. Finance-cost arithmetic, share arithmetic and
  validation matrices that pass are what make the failures credible.
- Never send the report yourself — stage it as a draft and let the reporter send it.

## The public calculators are a separate surface — sweep them LAST, and sweep siblings

Account-based rounds systematically miss the free public tools: no session, no itemised panel, so
the only oracle is the rule itself. Make them an explicit phase instead of an afterthought. They are
also cheap (Playwright, no login, read-only) and are one of the few surfaces you can re-verify on the
day you write the report — so they are the natural home for a "confirmed still live on <date>" claim.

- **Enumerate first.** The tool index (`/tools/*` links on the tools page, plus the URL history) is
  the list; check every tool that takes numbers, including the ones with no result panel (a pure
  explainer has nothing to verify — say that rather than skipping silently).
- **When one tool is wrong, drive its siblings with the same inputs.** These tools usually share a
  core. Finding the allowance-taper defect in the Rental Income Tax Calculator and then feeding the
  same rent/interest into the Section 24 Calculator produced the identical wrong figure — one root
  cause, two customer-facing tools, and a far stronger report than either alone. Also re-check the
  same tool *below* the suspect threshold: "exact at £110,000, wrong at £118,000" bounds the cause.
- **Read the error SIGNATURE, not just the error.** Ladder the inputs, log tool-figure vs
  hand-computed figure, then look at the shape: exact below a threshold → error appears → grows →
  plateaus at a constant. A plateau proves a second cause. +£629 flat, for example, is 5% of the
  £12,570 personal allowance and is *impossible* from the statutory taper once the allowance is
  already nil — so something else is charging. Write "this points at a second, wrong taper
  calculation"; do not claim the exact line without having read the code.
- **Then go get the actual line — from the served chunk, not from your reading of it.** The tool is
  client-side, so the arithmetic is in a `_next/static/chunks/*.js` the page loads. Escalate:
  (1) capture the chunk the browser really loads (response listener + `performance.getEntriesByType('resource')`,
  and re-fetch it *inside the page context* so a CDN/bot variant can't mislead you);
  (2) **re-implement the suspect function in-page and assert it reproduces the live figure across your
  whole ladder** — 20/20 points is the bar; (3) only then quote the verbatim minified source and the fix.
  Trap that cost a full round: hand-tracing minified JS by eye gave a *confident wrong* cause (blamed the
  personal-allowance taper) which was already written into a PDF and an email draft. Executing the same
  code revealed the real defect (the band widths were being measured down from a fixed £12,570 offset, so
  45% started at taxable £112,570 instead of £125,140 → error = 5% × (taxable − 112,570), capped at
  5% × 12,570 = the £629 plateau the ladder showed). A black-box fit can predict every number and still
  name the wrong mechanism; a re-implementation that reproduces the output cannot.
- **Corroborate with the vendor's own other surfaces.** The strongest possible evidence is the product
  disagreeing with itself: the app engine returning the statutory figure for the same input while the
  public tool returns the wrong one; or the page printing "at your 60% marginal rate" while the code
  charges 67.5p. Cite those before any external authority.
- **Re-verify on the day you write, and if a deliverable already shipped the wrong explanation,
  regenerate it and replace the draft.** These apps redeploy mid-engagement; a cause read from a chunk
  is build-specific. If an earlier draft/PDF carries a superseded cause, pull it — a stale explanation in
  the vendor's inbox is worse than a late send.
- **The product contradicting its own public tool is the headline.** If the app's engine returns the
  correct figure and the marketing calculator does not, the correct logic already exists in the
  codebase — say so explicitly. It converts the finding into a one-line fix and vendors act on it.
- **Comparison legs are a real defect class, but label them minor.** A tool showing "old rules vs
  now" can disagree with its own caption (caption claimed both figures took the £1,000 allowance; the
  old-rules leg did not — £5,486 shown vs £5,286, so the headline "Section 24 costs you" was £200
  out). Report the caption/arithmetic mismatch as wording/consistency, note that it is a comparison
  leg rather than a filing figure, and flag that the allowance treatment in a hypothetical regime is
  arguable on both sides.
- **Third-party calculators are usually not usable as the authority.** Their result panes are
  JS-gated and do not read reliably. The authority is the published rule text plus the arithmetic you
  show in the report; state that you tried the third-party cross-check and why you fell back, rather
  than silently substituting.

Deterministic re-verification recipe (one script, ~60s, no account): Playwright → `goto` the tool →
set inputs via the native value setter + dispatch `input` **and** `change` **and** `keyup` → wait
**≈3–4 s** (a plain `el.value = x` does nothing; a short settle reads the static help text and looks
like a pass) → read `inner_text("body")`. Record each run to `logs/<tool>.log` so the report's
"confirmed still live" line has an artefact behind it. If the control is a `<select>` (e.g. a tax-year
picker) drive it with `HTMLSelectElement.prototype`, not the input setter — with the wrong setter the
value silently never changes and every option returns the same figure (a manufactured finding).

**Before designing a rule-isolation scenario, check the panel's scope.** If the estimate panel is an
ALL-SOURCES aggregate, a per-property rule (property allowance, FTCR) cannot be isolated while any other
source holds conflicting data — the message will be correct for the aggregate and prove nothing. Run such
scenarios on a clean account, or clear the specific rows with the operator's consent; otherwise write
"unverified", never "wrong". Note the tier: a free plan may render income/expenses/net but no tax lines
at all, in which case it cannot decide anything the itemised panel would.

**Harness false-negative (bit me on a re-verification round):** these tools are React — a plain
`el.value = v` updates the DOM but not the component state, so the result panel never recalculates and
**every earlier defect silently looks "fixed"**. Use the native setter (`Object.getOwnPropertyDescriptor(
window.HTMLInputElement.prototype,'value').set`), dispatch `input` + `change` + `keyup`, then wait
**3.5–4 s** (2 s is often too early). `<select>` needs the same against `HTMLSelectElement` — and check
its default: `#pyear` defaults to 2027, so skipping the year switch makes 2026 appear to use 2027 rates,
which is a fabricated finding. Before believing any "no change" result, prove the harness on a
known-good tool/value pair. Never record "defect fixed" from a harness you have not validated.

## When the same target comes round again (re-verification rounds)

These products redeploy between passes, so the first job on a repeat round is **re-verify, don't re-report**:

- **Re-run the previously-reported defects FIRST.** On a later Quarterwise round all three public-tool defects
  (rental taper, section-24, MTD-penalty 2027-28 rates) were already FIXED. Reporting them again would have been
  three false reports. Ladder the inputs and compare against the hand-computed correct figure before writing
  anything; say "fixed" where fixed.
- **Reuse the stored session before logging in.** The Pro account's `qw_session` cookie from a previous pass was
  still valid weeks later (`GET /app` -> 307 to /app/clients, not /login). Only do the full login when a
  GATED page bounces to /login. A saved cookie beats re-doing MFA; check it first.
- **The itemised panel is per-ACCOUNT, not per-property.** The estimate block is "ALL SOURCES": it aggregates
  every source, so a per-property rule (the £1,000 allowance) CANNOT be isolated by adding a clean property
  while old test rows exist. Isolate by removing the other rows (and RESTORE them after), or use a truly
  single-source account. Do not conclude anything from an aggregate.
- **The free tier may not show the arithmetic at all.** Quarterwise's free panel shows income/expenses/net + the
  §24 note but NO tax lines and no allowance message (the estimate is Pro-only). A clean free account is useless
  as an oracle for tax-line rules — confirm the panel renders the lines before planning an isolation on it.

### The allowance-vs-finance-cost interaction (live as of the last round)

Isolated on one Pro account, both legs with **£0.00 deductible expenses**:
- no finance costs -> panel APPLIES the allowance: "Property allowance applied: -£1,000.00 (instead of £0.00
  actual expenses, saves you £200.00)".
- £3,000 residential finance -> panel WITHHOLDS it: "Claiming your expenses and the mortgage interest relief
  saves more tax than the £1,000 property allowance... You can't claim both." -> £200 more tax at 20%.
The comparison population includes finance costs (which are not deductible expenses). The rule interaction is
arguable, so it is reported as a QUESTION with the numbers, not a claimed wrong figure (see Reporting rules).

### Harness quirks (Next.js server-action apps)

- Login: clicking "Log in" does NOT advance. Submit the real form with `form.requestSubmit()`.
  credentials -> `/login/mfa`, field `#code` (6 digits), then `requestSubmit()` again.
- Ledger entry: "Record expense" opens a modal -> click "Enter manually" (the modal also offers an AI scan).
  On a free tier there may be no modal; the form is direct. Fields: `#category` (select), `#amount`, `#txnDate`.
- Delete is an INLINE confirm ("Delete? Yes / No"), not a native dialog — a Playwright dialog handler does
  nothing. Click the `Yes` button; only some rows expose `button[aria-label="Delete entry"]` (scroll/hover first).
- React inputs need the native value setter + `input`/`change` (+ a ~3.5-4s settle) or the calculator silently
  keeps the old figure. A plain `.value=` gives a false "input had no effect" reading — do not trust it.
- Password reset on such apps is often CODE-based (/forgot -> /reset, 6-digit). Test the attempt cap, not just
  the token: Quarterwise caps wrong codes at 5 ("Too many attempts. Request a new code.") -> good control.

## References
- `references/quarterwise-v6-pass-2026-10.md` — re-verification round: three fixed public-tool defects, the
  session-cookie reuse, the aggregate-panel isolation of the allowance defect, API/entitlement verdicts.
- `references/quarterwise-round-2026-10.md` — round four on the same target: the property-allowance
  defect ISOLATED (two-leg recipe, exact panel sentences, £200 impact, why it is a question not a
  claim), the engine verified exact at 20/40/60% (incl. the PA-taper band), and the pitfalls that
  cost time (panel is "ALL SOURCES"; free tier has no tax lines; two-step expense modal; inline
  Delete?Yes/No rather than a native confirm; restore-then-re-read).
- `references/quarterwise-public-calculators-2026-10.md` — round three on the same target: the
  public-calculator surface, the sibling-tool sweep, the taper defect's error ladder and +£629
  plateau, the MTD 2027-28 rate defect, the comparison-leg caption mismatch, and the re-verification
  recipe. **STATUS SUPERSEDED — see the reverify file before citing the defects in this one.**
- `references/quarterwise-reverify-2026-10-08.md` — round four: **all three public-tool defects from
  round three are FIXED** (taper, section-24, MTD 2027-28) — re-verify before re-reporting anything
  from the round-three file. Also: the native-setter + `input`/`change`/`keyup` + ~4 s settle harness
  that separates a false negative from a true result (a plain `.value=` reads the page's help text and
  looks like "no change"); the Pro `qw_session` cookie still valid across runs (try it before asking
  for a TOTP); why the `/app?view=mine` panel aggregates ALL SOURCES and cannot isolate a
  single-property invariant; and the Record-expense 2-step modal + inline "Delete? Yes No" prompt.
- `references/uk-property-tax-rules.md` — the UK rule bank with official sources, the exact
  scenarios used, and the two defects this method found (property allowance displaced by
  finance costs; a fix that held on the entry form only).
- `references/quarterwise-pro-session-2026-09.md` — the Pro-account pass: verbatim panel shape,
  the seven rule verdicts (CORRECT / DEFECT / UNVERIFIED), the manual ids to cite, and the
  harness quirks of that target.
- `references/quarterwise-v6-2026-10.md` — round four: re-verification (every previously reported
  defect is now FIXED, with the correct figures tabulated), the aggregate-panel trap that keeps the
  property-allowance rule unverified, §24 cross-confirmed on the free tier, and the full API
  business-logic matrix (bare-array write shape, externalRef idempotency, validation edges, batch cap,
  cross-tenant 404) plus the free-tier entitlement checks.
- `scripts/totp.py` — dependency-free RFC-6238 TOTP from a base32 secret, for accounts that gate login,
  API-key minting or password change behind an authenticator code. Reproduces `pyotp`; verify once
  before relying on it.
