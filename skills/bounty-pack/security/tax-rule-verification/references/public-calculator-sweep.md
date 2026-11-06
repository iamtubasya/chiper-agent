# Sweeping a vendor's public calculators (Playwright recipe + observed field map)

The public calculators are the cheapest second oracle on a tax/finance target, need no login, and on
several products they are where the real arithmetic defects live while the paid engine is correct.
They are React tools, so drive them with the native value setter — not `.value =`.

## Reusable harness

```python
from playwright.sync_api import sync_playwright

SET = """([id,v])=>{const e=document.getElementById(id)||[...document.querySelectorAll('input')].find(x=>x.name===id);
 if(!e) return 'missing:'+id;
 const p=e.tagName==='SELECT'?window.HTMLSelectElement.prototype:window.HTMLInputElement.prototype;
 Object.getOwnPropertyDescriptor(p,'value').set.call(e,String(v));
 e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));
 return 'ok';}"""

def sweep(pg, url, scenarios, reset=()):
    pg.goto(url, wait_until="domcontentloaded", timeout=70000); pg.wait_for_timeout(4500)
    # 1. map the form FIRST — never guess ids from label text
    fields = pg.evaluate("()=>[...document.querySelectorAll('input,select')].map(i=>i.id||i.name)")
    out = []
    for sc in scenarios:
        for k in reset:                       # 2. clear every field you are not setting
            pg.evaluate(SET, [k, ""])
        for k, v in sc.items():
            pg.evaluate(SET, [k, v])
        pg.wait_for_timeout(1600)
        txt = pg.evaluate("()=>document.body.innerText")
        out.append({"in": sc, "text": txt})
    return fields, out
```

- **`reset` is not optional.** React keeps prior values; a stale field invents a fake mismatch (a CGT
  case appeared wrong only because `oth` still held the previous scenario's 45,000).
- **Checkboxes:** toggle with `.click()` and assert `el.checked` before reading the result.
- **Read the whole result block**, not just the first number — relief lines sit below the fold and a
  correct total can hide two offsetting wrong steps. Capture `document.body.innerText` and grep it.
- **Quote the result verbatim** in the report (the tool prints a full block: heading, components,
  total, then its own "Based on 20xx/xx UK tax rules" footnote).

## Field map observed on one UK MTD landlord product (2026-10)

Useful because the ids are terse and unguessable from the labels:

| Tool (slug) | Input ids | Notes |
|---|---|---|
| `rental-income-tax-calculator` | `rent`, `exp`, `int`, `oth` | property allowance applied automatically |
| `section-24-calculator` | `rent`, `exp`, `int`, `oth` | prints old-rules / tax-now / extra-tax triple |
| `mtd-penalty-calculator` | `pyear` (SELECT: `2026`,`2027`), `missed`, `tax`, `days`, + 1 checkbox = "first year" | `missed` = count of missed updates |
| `capital-gains-tax-calculator` | `proc`, `buy`, `costs`, `oth` | `oth` = other income, sets the band split |
| `stamp-duty-calculator` | `price`, + 2 checkboxes: [0] "additional property", [1] "first-time buyer" | |
| `mtd-readiness-checker` | `rent`, `se` (+ 2 checkboxes) | returns a mandate date, not a number |
| `mtd-qualifying-income-calculator` | `prop`, `se` | |
| `accountant-vs-software-calculator` | `props`, `acc` | |

Other tools on that site with no numeric input (`limited-company-landlord`) are explainers — record
them as "no arithmetic to test" rather than skipped.

## Boundary sweeps that pay

- Income-tax taper: sweep rent across `110k / 118k / 120k / 124k / 130k / 160k` and diff against a
  hand-computed table built with **band widths on taxable income** (see the pitfall in SKILL.md).
  A product with the flat-allowance bug shows a constant offset that plateaus at 5% of the allowance.
- Penalty estimator: cross `pyear` × `days` (`16/30/31/40/60`) × the first-year checkbox. A flag that
  changes the answer at 30 days and not at 31 is an internal inconsistency worth reporting.
- Penalty points: sweep `missed` = 3/4/5/8 per year and check the threshold arithmetic (4 points →
  one £200, each further miss another £200) and any "no points this year" grace.
- SDLT: sweep price across the band edges **with each checkbox combination** — the first-time-buyer
  relief must vanish entirely above £500,000, and the additional-dwelling surcharge must not combine
  with FTB relief.
- CGT: run the same disposal with and without other income to pin the 18%/24% split.

## Reporting hygiene

Put the figures that matched to the penny in the report in a full table (test / input / tool /
expected / verdict). A correction report that only lists defects reads as an attack; the
verified-correct table is what makes "compliant" credible and is the reason the vendor keeps
answering.
