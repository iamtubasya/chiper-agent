# Tax/accounting app — calculation-correctness & compliance review

Session-derived recipe for auditing a tax product (UK Making Tax Digital example) where the
question is *"is the tax logic right and up to date?"* rather than *"is it exploitable?"*.
Read this before writing any compliance claim — the whole job is separating the two.

## 0. The framing decision, made first

Compliance defects in a tax app are **product-correctness issues, not security findings.** Say so
in the opening paragraph of the report, not in a footnote. A reviewer who has to guess whether
you think you found a vulnerability will discount the rest of the report.

- Security finding: crossing a trust boundary. Needs demonstrated attacker impact.
- Correctness issue: the customer's own figure is wrong. Needs a quantified example and a fix.

Do not promote a correctness issue into a "financial impact" finding because the tax is involved.
A user who mis-reports their own income is the one who suffers; that is not an attack.

## 1. Map the gate chain before promising anything

Most interesting logic is unreachable on a free plan. Establish the chain explicitly so the
coverage gap is a fact, not a shrug.

Typical chain: `feature tier (Pro) → 2FA → provider credential (Government Gateway) → filing`.
Probe each rung by injecting the field the client would have set, and record the server's
refusal string verbatim — a quotable refusal is the evidence that the gate is real:

```
inject countryCode=ES + outsideUk=1 into the create action
  -> "Overseas property is part of Pro. Upgrade to add a property outside the UK."   ← gate holds
```

Then write: *"FTCR computation, its cap, accruals arithmetic, Section 24 restriction, 60/40 and
CGT were never exercised. I make no claim about them in either direction."* That sentence is
part of a good report, not an admission of weakness.

## 2. Model the data structure, not the UI

The scalar-vs-timeline defect is invisible from screenshots and obvious in the bundle. For any
"time-varying" control (ownership %, seats, quota, discount, tier multiplier):

1. Grep the client bundle for the field (`ownerPercent`, `shareBp`, `percent`, `effectiveFrom`,
   `fromDate`, `transfer`, `sold`, `completed`).
2. Record what is **absent**: no date input, no effective-from, no disposal date.
3. Prove it by toggle test against the authoritative output (see SKILL.md §2b-2).

Absence in the bundle is the proof — much stronger than "I didn't see a date field in the UI".

## 3. Verify what they GET RIGHT, against an external source

Half the value of a compliance review is telling the vendor which of their claims are correct.
Verify each, don't eyeball it:

| Claim in the product | Rule to check | Verdict if it matches |
|---|---|---|
| "cash basis is HMRC's default" (property income) | default since 2017/18; accruals needs an election — **not** the same as trading income | correct |
| "income over £50,000 must use MTD" | stepped thresholds: £10k Apr-2024 → £50k Apr-2026 → £30k Apr-2027 → £20k Apr-2028 | correct |
| quarterly update dates shown in-app | published HMRC dates for the year, one month after each quarter end | correct |
| tax year 6 Apr – 5 Apr | standard UK year | verify empirically, don't assume |
| "furnished holiday lettings abolished April 2025" | abolished for years commencing on/after 6 Apr 2025 | correct |
| platform reporting (Airbnb/Vrbo/Booking) | digital-platform income reporting | correct |

**Watch for category errors the vendor will also get wrong:** the accruals/cash-basis default is
different for *property income* than for *trading income*. A vendor quoting the trading-income
default for a landlord product is wrong — and so would you be if you assumed it.

Search the public marketing pages too, not just the app. A holiday-let tool that still implies
abolished relief would be a material finding; one that states the abolition clearly is a credit.

## 4. Test the thresholds the product is supposed to enforce

For every statutory limit the product knows about, push past it and look for a warning:

- drive cash receipts past the basis ceiling with one large entry
- search the page, its settings tab, the dashboard and the export for any mention of the figure
- a genuine check produces a named number, a warning, or a forced basis switch

"No warning anywhere" is the finding. Absence of the *string* in the bundle is the cheap proxy
— grep the downloaded chunks for the threshold value before ever loading the page.

## 5. Write it without overclaiming

Structure that works:

1. Scope/identity paragraph, including what you deliberately did **not** do (no DoS, no volume,
   no paid-feature acquisition).
2. One-paragraph honesty statement separating security findings from correctness issues.
3. Summary table with **separate Type and Severity columns** so the two categories never blur.
4. Per issue: what the app does → reproduction with real numbers → impact → *explicitly what it
   is not* → suggested fix.
5. A "what I tested and found sound" section. Credit where due; it is what makes the rest
   credible.
6. A "what I could not test" section.
7. Close by naming the one issue you most want their product view on.

Reusable impact sentence for a self-scoped validation gap:

> To be explicit about the limits of this: it is self-scoped. It only affects the records of the
> account that creates the entry. It does not expose another user's data, it does not grant
> access to any feature or plan, and it does not cross any account boundary.

## 6. Mechanics that cost time on Windows/Git-Bash

- **The `$ACTION_ID` trap.** The first `$ACTION_ID_*` field on a Next.js page usually belongs to
  the *log out* button. Replaying it logs you out mid-audit. Read the form whose fields match the
  action you want, and never grab "the first action id on the page".
- **Bound actions cannot be replayed out-of-band.** A form action carrying a `$K1`/`$ACTION_KEY`
  binding is tied to that page render; replaying it later returns `500 digest` and proves nothing.
  Drive these through the real browser instead of curl.
- **Session cookies rotate constantly.** Refresh the jar immediately before each assertion batch
  and re-login when it 307s. A stale jar silently produces "0 records" style false negatives that
  look exactly like a security control holding.
- **Path args get mangled by MSYS.** `/app/foo` in an argv becomes `C:\...\app\foo`. Prefix
  commands with `MSYS_NO_PATHCONV=1` (or set `MSYS2_ARG_CONV_EXCL='*'`) when passing URLs/paths.
- **Don't build JS-in-JSON through a bash heredoc.** `\n`, `\s`, `\/` and quote-doubling get
  mangled and produce `SyntaxError: Invalid regular expression: missing /`. Generate the actions
  file from Python `json.dumps`, or put the JS in a `.js` file, or just do the interaction in a
  plain Playwright script.
- **Only one Playwright sync instance per process.** For two identities use two *contexts* in one
  browser (contexts have independent cookie jars). Two `sync_playwright().start()` calls raise
  "Sync API inside the asyncio loop".
- **Race tests need real concurrency.** Open N pages in one context, put each in the required
  state, then fire the submits in a tight loop and report the elapsed ms alongside the result.
  A "0 extra rows" from sequential requests is not a race test.
