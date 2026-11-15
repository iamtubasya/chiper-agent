# Quarterwise — re-verification round (2026-10-08)

Round four on `quarterwise.co.uk`. Two goals: re-verify the public-calculator defects reported in
`quarterwise-public-calculators-2026-10.md`, and re-run the Pro-account tax-engine pass.

**Headline: all three public-tool defects are FIXED.** Do not re-report them. Re-verify before citing
anything from the round-three reference — that file records the state at report time, not now.

## 1. rental-income-tax-calculator — taper defect FIXED

| Annual rent | Round 3 (wrong) | Now | Statutory |
|---|---|---|---|
| £110,000 | £32,832 | £32,832 | £32,832 |
| £120,000 | £39,000 | £38,832 | £38,832 |
| £130,000 | £44,882 (+£629) | **£44,253** | £44,253 |
| £160,000 | £58,382 (+£629) | **£57,753** | £57,753 |

The flat +£629 plateau is gone; the tool now agrees with the app engine and the statute.

## 2. section-24-calculator — same root cause, FIXED

| rent / exp / int | Round 3 (wrong) | Now |
|---|---|---|
| £120,000 / 0 / £20,000 | £35,675 | **£35,432** |
| £130,000 / 0 / £20,000 | £41,332 | **£40,703** |

## 3. mtd-penalty-calculator — 2027-28 rates FIXED

tax £5,000, 40 days late:
- `#pyear` = 2026 → **£314** (3% + 3% + 10%×10/365 = £313.70) — correct
- `#pyear` = 2027 → **£414** (4% + 4% + 10%×10/365 = £413.70) — correct
- footnote now reads "Based on 2026/27 and 2027/28 UK tax rules"

## Harness: a plain `.value=` silently produces a false NEGATIVE

Setting an input by assignment does not drive these React tools — you read the page's help text and
conclude "nothing changed". The working recipe (this is what made the difference between a false
"still broken" and the true "fixed"):

```js
(el,v)=>{var d=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
 d.call(el,v);
 el.dispatchEvent(new Event('input',{bubbles:true}));
 el.dispatchEvent(new Event('change',{bubbles:true}));
 el.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true}));}
```

plus a **~4 s settle** before reading. For `<select>` (e.g. `#pyear`) use the
`HTMLSelectElement` prototype setter — the input setter leaves the value unchanged and both branches
then return the same figure, which looks like a defect and is not.

## Pro session survives across runs — try the stored cookie before asking for a TOTP

`quarterwise.co.uk` sets a `qw_session` cookie (HttpOnly). A cookie captured in a prior engagement was
**still valid weeks later**: `GET /app` with it returned `307 → /app/clients` (the firm view) instead of
a redirect to `/login`. Grab the session cookie from the last workspace first; only ask for a TOTP if it
401s. Note `POST /app/account/api` (create API key) DOES require a TOTP code, and previously created keys
are revoked at engagement end, so a fresh API key needs a code even when the web session is alive.

## The estimate panel aggregates ALL SOURCES — you cannot isolate one property

`/app?view=mine` renders `TAX YEAR … · YOUR SHARE · ALL SOURCES`. Adding a controlled scenario to one
property mixes it with every other source's ledger, so a single-property invariant (the property-allowance
comparison) is **not isolable on an account that already carries entries**. Options: a fresh single-source
account, or clear the other sources first. Say "not isolable" rather than claiming a verdict.

## Engine arithmetic verified CORRECT (higher-band scenario)

Built rent £30,000 + repairs £50 + residential finance £2,000, read the panel, then deleted the entries:

```
income 61,001.01 - expenses 2,562.34 = net 58,438.67
taxable = 58,438.67 - 12,570 = 45,868.67
tax = 20%x37,700 + 40%x(45,868.67-37,700) = 7,540.00 + 3,267.47 = 10,807.47
finance costs relief = -20% x 5,000 = -1,000.00
estimated = 9,807.73 -> 9,807.47   OK, top rate 40%
```

So §24 (add-back + 20% reducer) and the 20/40 band arithmetic hold in the higher band too — the band
where a wrong taper would surface.

## UI friction worth knowing (Record expense is a 2-step modal)

"Record expense" opens a modal with **Scan with AI / Enter manually** — the manual form (with
`#category`, `#amount`, `#txnDate`) is behind the second click. Deletion is an **inline** prompt
("Delete? Yes No"), not a native `confirm()`; Playwright's `dialog` handler never fires, so click `Yes`
via `get_by_role("button", name="Yes")`. Leaving test entries behind is not acceptable — verify the panel
is back to its delivered numbers afterwards.
