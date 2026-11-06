# Quarterwise — public calculators round (2026-10)

> **STATUS 2026-10-08 — ALL THREE DEFECTS IN THIS FILE ARE FIXED.** Re-verified end-to-end with a correct
> harness: rental £130,000 → **£44,253** and £160,000 → **£57,753** (the +£629 plateau is gone);
> section-24 £120k/£20k → **£35,432** and £130k/£20k → **£40,703**; MTD penalty tax £5,000/40 days →
> **£314** for 2026 and **£414** for 2027, footnote now reads "2026/27 and 2027/28". **Do NOT re-report
> these.** Keep the file as the record of the original defects and the method that proved them; a future
> round should start from "what has NOT been covered", not from this list.
>
> **The harness trap that nearly faked the result:** a plain `el.value = v` (and even a naive
> `eval_on_selector` setter) does NOT drive these React calculators — the result panel never updates, so
> every input looks like it was rejected and every defect looks "fixed". A working setter dispatches all
> three events on the native value setter and then waits ~3.5–4 s:
>
> ```js
> (el,v)=>{var d=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
>          d.call(el,v);
>          el.dispatchEvent(new Event('input',{bubbles:true}));
>          el.dispatchEvent(new Event('change',{bubbles:true}));
>          el.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true}));}
> ```
> `<select>` needs the same dance against `HTMLSelectElement` (`#pyear` defaults to **2027**, so a
> forgotten year switch reads as "2026 shows the 2027 figure" — a fabricated finding).
> Always sanity-check the harness against a KNOWN-GOOD tool/value before trusting a "no change" result.

Round three on `quarterwise.co.uk` (Malden Ltd). Rounds one and two were the Pro-account pass and
the tax-engine notes (see `quarterwise-pro-session-2026-09.md` and `uk-property-tax-rules.md`).
This round covered the one surface the earlier rounds never touched: **the free public calculators**.
The vendor had already fixed the earlier items and paid a discretionary reward, so this round was
purely "what did the account-based sweep miss".

## Why this surface gets missed

Everything in rounds one and two was reached through a logged-in Pro account and graded against the
product's own itemised estimate panel. The public tools have neither: no session, no panel. So the
only oracle is the rule. That makes them easy to drop from a plan built around "log in, drive the
panel, compare" — and they are customer-facing marketing surface, which is exactly where a wrong
figure costs the vendor trust.

## The tool index (enumerate, don't guess)

Crawled from the tools page + URL history (`gau`), the full public set:

```
/tools/rental-income-tax-calculator      <- DEFECT (see below)
/tools/section-24-calculator             <- DEFECT (same root cause)
/tools/mtd-penalty-calculator            <- DEFECT (rate, see below)
/tools/mtd-readiness-checker             correct
/tools/mtd-deadline-calculator           correct
/tools/mtd-qualifying-income-calculator  correct
/tools/accountant-vs-software-calculator correct
/tools/allowable-expenses-checker        verdicts correct; content gap (no "mortgage interest"
                                         / "furniture" / "cleaning" entries -> "No matches")
/tools/capital-gains-tax-calculator      correct
/tools/stamp-duty-calculator             correct
/tools/limited-company-landlord          explainer, no numbers -> nothing to verify (say so)
```

Handy property of most of these tools: the four inputs are consistently `#rent #exp #int #oth`
(the S24 tool reuses the same ids), and `#pyear #missed #tax #days` on the MTD penalty tool. Setting
them is the same native-setter dance as the app (see the recipe at the end).

## Defect 1 — personal-allowance taper (two tools, one root cause)

`/tools/rental-income-tax-calculator`, rent only, expenses/interest/other left blank:

| Annual rent | Tool | Correct | Error |
|---|---|---|---|
| £110,000 | £32,832 | £32,832 | 0 |
| £118,000 | £37,650 | £37,632 | +£18 |
| £120,000 | £39,000 | £38,832 | +£168 |
| £124,000 | £41,700 | £41,232 | +£468 |
| £130,000 | £44,882 | £44,253 | +£629 |
| £160,000 | £58,382 | £57,753 | +£629 |

`/tools/section-24-calculator` returns the *identical* figures for the same inputs:

| Inputs (rent / expenses / interest) | Both tools | Correct | Error |
|---|---|---|---|
| £120,000 / 0 / £20,000 | £35,675 | £35,432 | +£243 |
| £130,000 / 0 / £20,000 | £41,332 | £40,703 | +£629 |

**Signature analysis** (the part that makes the report). Exact below ~£115,000; error starts as soon
as adjusted net income passes £100,000; grows through the taper; then **plateaus at exactly +£629**.
£629 is 5% of the £12,570 personal allowance. Above £125,140 the allowance is nil in *both* the
correct and the incorrect case, so the taper cannot produce that flat addition — there is a second,
wrong calculation in the tools. The app's engine returns £44,253 for rent £130,000 (verified in the
product), so the correct logic already exists in the codebase; that is the fix instruction.

Below the taper everything agrees: rent £60,000 + £20,000 interest → £7,432 in both the tool and the
app; rent £130,000 with £50,000 expenses → £19,432 (correct).

## Defect 2 — MTD Penalty Estimator uses 2026-27 rates for 2027-28

`/tools/mtd-penalty-calculator`, tax £5,000 paid 40 days late → **£314 for both** "2026 to 2027
(first year)" and "2027 to 2028 onwards". GOV.UK has 3% (day 15) + 3% (day 30) for 2026-27, rising to
**4% + 4%** from 2027-28, so the correct 2027-28 figure is 4%×5,000 + 4%×5,000 + 10%×5,000×(10/365)
= **£413.70** — understated by ~£100, and worse on a bigger bill. Corroborating detail worth quoting:
the footnote under the result still reads *"Based on 2026/27 UK tax rules"* even with 2027-28
selected, which supports the single-constant-set explanation.

Everything else on that tool is right: the 4-point threshold, the £200 penalty, the 2026-27 "no
penalty points in the first year" grace, the £200-per-further-miss rule, and the 2026-27 figure.

## Defect 3 (minor) — S24 caption vs its own "old rules" leg

Rent £60,000, expenses 0, interest £20,000 → "old rules" £5,486, "now" £7,432 (correct), "Section 24
costs you £1,946". The caption says *"Both figures use the £1,000 property allowance"*; the old-rules
leg does not use it (£5,286 with it, making the headline cost £2,146). The "now" leg is correct, and
correctly refuses the allowance alongside the interest credit. Reported as wording/consistency with
the caveat that the allowance treatment in a hypothetical pre-2017 regime is arguably either way.

## Verified-correct list (always ship this half)

MTD Readiness Checker phase-in (£60k→6 Apr 2026, £40k→2027, £25k→2028, £15k→not yet); Accountant vs
Software (£250–600 vs Pro £99 → saving £151–501); Allowable Expenses verdicts; CGT calculator;
SDLT; MTD deadlines and thresholds; both affected tools whenever income stays below the taper.

## Re-verification recipe (run it on the day you write the report)

```python
from playwright.sync_api import sync_playwright
import re
SET = """(e,val)=>{const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,
        'value').set;s.call(e,val);e.dispatchEvent(new Event('input',{bubbles:true}));
        e.dispatchEvent(new Event('change',{bubbles:true}));e.blur();}"""
# launch headless, goto the tool, wait ~2.5s for hydration, then per scenario:
#   pg.locator("#rent").first.evaluate(SET, "130000")
#   pg.wait_for_timeout(1400)
#   t = re.sub(r"\s+", " ", pg.inner_text("body"))      # collapse whitespace before searching
#   i = t.find("Estimated tax on your rental income")
```

Gotchas that cost time here:
- Read the whole flattened body and `find()` the label; do not try to regex the number out of the
  page (several figures repeat — the headline and the breakdown line both carry the same value).
- `#pyear` is a `<select>` — use `select_option(label=...)`, and read `option` texts first because
  they change wording between builds.
- Dump controls with `[...document.querySelectorAll('input,select')].map(e=>[e.id||e.name,e.type])`
  before assuming ids; the S24 tool silently reuses `#rent #exp #int #oth`.
- These pages hydrate; 2–3s before the first interaction, then ~1.4s after each input change.

## Vendor-thread notes

The mailbox, not the workspace, held the actual pending task: the reporter had written "I will do
another run and let you know if I find something else", and the vendor had already replied with the
full fix list and a paid reward. Recovering that thread first (Message-IDs included, for threading
the reply) is what made this round a coherent follow-up rather than a restart. See the
"Resuming a paused engagement" section in the `bug-report-delivery` skill.
