# Sweeping a vendor's PUBLIC tax calculators (the second oracle)

Why this file exists: on a tax/finance SaaS the *in-app* estimate is often gated behind a
connection to the tax authority, and a well-run VDP forbids making that connection. When the
engagement says "do not connect to HMRC / do not submit anything", the in-app engine sweep from
`tax-estimate-coverage-checklist.md` is **not runnable** and the vendor's own free public
calculators become the only observable arithmetic surface. That is not a downgrade — it is where
customer-facing defects actually live, and a vendor-vs-its-own-tool contradiction is the sharpest
report you can write.

State the substitution explicitly in the report ("no authority connection was made, so the in-app
estimate and the filing path were not exercised; the public tools and the account's own panels
are what is covered"): the reader must not mistake the silence for a clean bill of health.

## 1. Discover the field ids before writing a scenario

The tools are React, the ids are stable per tool, and guessing them silently writes nothing.
One call gets the map:

```js
[...document.querySelectorAll('input,select')].map(i => [i.tagName, i.id || i.name, i.type])
```

Observed on the Quarterwise family (2026-10) — useful as a template, re-verify if a tool changes:

| tool | fields |
|---|---|
| `/tools/rental-income-tax-calculator` | `rent`, `exp`, `int`, `oth` |
| `/tools/section-24-calculator` | `rent`, `exp`, `int`, `oth` |
| `/tools/mtd-penalty-calculator` | `pyear` (select: `2026` / `2027`), `missed`, `tax`, `days`, + one checkbox (first year) |
| `/tools/capital-gains-tax-calculator` | `proc`, `buy`, `costs`, `oth` |
| `/tools/stamp-duty-calculator` | `price` + checkbox[0] "additional property", checkbox[1] "first-time buyer" |
| `/tools/mtd-readiness-checker` | `rent`, `se`, + two owned-company checkboxes |
| `/tools/mtd-qualifying-income-calculator` | `prop`, `se` |
| `/tools/accountant-vs-software-calculator` | `props`, `acc` |

Note the name collision: several tools share `rent`/`int`/`oth`, so a page-scoped selector is
mandatory — `document.getElementById(id)` plus a name fallback, never a bare `input[0]`.

## 2. Fill React inputs with the native value setter

`.value = x` does nothing (React's synthetic state never sees it) and the result pane does not
recompute. Use the prototype setter and dispatch both events:

```python
SET = ("([id,v])=>{const e=document.getElementById(id); if(!e) return 'missing:'+id;"
       " const p=e.tagName==='SELECT'?window.HTMLSelectElement.prototype:window.HTMLInputElement.prototype;"
       " Object.getOwnPropertyDescriptor(p,'value').set.call(e,String(v));"
       " e.dispatchEvent(new Event('input',{bubbles:true}));"
       " e.dispatchEvent(new Event('change',{bubbles:true})); return 'ok';}")
```

`SELECT` needs `HTMLSelectElement.prototype`, not `HTMLInputElement.prototype` — using the input
prototype on a `<select>` silently leaves the default option in place (this is how a "the 2027-28
rate is wrong" reading can actually be a reading of the 2026-27 default).

## 3. Set EVERY field for EVERY scenario

A field left over from the previous scenario silently changes the next answer. Hit live: a CGT
sweep returned 44,564 where the expected was 42,618 — the `oth` box still held 45,000 from the
run before, which consumed the basic-rate band. The tool was right; the harness was wrong.

Rule: build each scenario as a complete dict covering every field on the page (blank = `0`), apply
all of them, then read. Never rely on a field's previous value, and never compare a scenario you
ran with the field set against one you ran without.

## 4. Read the result, then diff against a hand-computed value — not against the tool

`re.findall(r"£([\d,]+(?:\.\d{2})?)", body_innerText)` gives the numbers in render order, so the
first hit is usually the headline. Hand-compute from the authority rule (see
`uk-tax-rule-bank-2026-27.md`) **and write the hand-calc into the harness** so the diff is
mechanical.

Derive the band arithmetic from the bands, not from memory. The trap that cost a cycle: on
*taxable* income the basic band is £0–£37,700 wide (the allowance is already removed), so
`higher = taxable - 37700`, **not** `taxable - 50270`. Hand-calcs written off the gross-income
bands will "prove" a correct tool is broken.

## 5. Checkbox/flag controls need a STATE-VERIFIED matrix, not a single toggle

A flag can work in one band and be inert in another. That is the finding shape, and you only see
it with a matrix. Verify the checkbox's own state after every click (`c.checked`) — an unverified
click makes an inert flag and a working flag look identical.

Worked example (MTD Penalty Estimator, 2026-10, £5,000 paid late, tax year 2026-27):

| days late | first-year ticked | first-year cleared |
|---|---|---|
| 16 | £0 | £150 |
| 30 | £0 | £150 |
| 31 | £301 | £301 |
| 40 | £314 | £314 |
| 60 | £341 | £341 |

The flag is honoured in the 16–30 day band and ignored at 31+. GOV.UK attaches "no penalty if it's
your first year" to the day-15 element, which puts the first-year 31+ figure at ~£163.70.
Report it with the ambiguity stated (HMRC's table prints the carve-out on the 16–30 row only) —
a rule-reading dispute is survivable; an unstated one is not.

## 6. Sweep the parameter across the band boundaries

One bad value proves nothing. Sweep the input that moves the answer across each boundary — for a
personal-allowance taper that is roughly £100k → £125,140 of profit, so rent values around
110/118/120/124/130/160k. A defect that plateaus (the historical +£629 = 5% × £12,570) is visible
only when you have points on both sides of the plateau.

## 7. Re-test the previous round's defects first — two of three were already fixed

Prior findings are **hypotheses**, not facts. Observed 2026-10:

- personal-allowance taper in the public rental calculator → **FIXED** (matched to the penny at
  110k/118k/120k/124k/130k/160k → 32,832 / 37,632 / 38,832 / 41,232 / 44,253 / 57,753)
- late-payment rate keying on the MTD Penalty Estimator → **FIXED** (2026-27 → £314, 2027-28 → £414)
- Section 24 caption ("both figures use the £1,000 property allowance") vs the "old rules" leg
  which does not → **still present**

Every fixed item is a *verified-correct* row in the new report; that table is what makes
"compliant" credible and stops the document reading as a hit-piece.

## 8. Do not let an ambiguous rule become a confident claim

When the authority's table is terse (a carve-out printed on one row and not the next), write the
item as a behaviour + the quoted rule + the two readings, and say which one you assumed. Pair it
with a suggested fix that is correct under either reading ("apply the exemption in the 31+ branch
too, or print which treatment is being applied"). A defect report that survives its own caveat is
worth more than a louder one that does not.
