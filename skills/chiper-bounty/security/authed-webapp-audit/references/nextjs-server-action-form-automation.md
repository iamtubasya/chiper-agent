# Driving Next.js (React) Server-Action forms from Playwright

Use when the audit needs to **create** state through the app UI — building a controlled scenario,
seeding a ledger, entering a tax figure — rather than replaying a captured action. Hand-built urllib
POSTs to `/app/...` return 500 (Next action binding), so the browser form is the only reliable writer.

Distilled 2026-10-09 on a Next.js + Cloudflare MTD SaaS (server actions, `$ACTION_REF_*` +
`$ACTION_KEY` hidden inputs, `multipart/form-data`).

## 1. Set values the React way

```python
def setv(pg, sel, v):
    pg.eval_on_selector(sel, """(el,v)=>{
      const p = (el.tagName==='SELECT' ? window.HTMLSelectElement
                : el.tagName==='TEXTAREA' ? window.HTMLTextAreaElement
                : window.HTMLInputElement);
      Object.getOwnPropertyDescriptor(p.prototype,'value').set.call(el, String(v));
      el.dispatchEvent(new Event('input',{bubbles:true}));
      el.dispatchEvent(new Event('change',{bubbles:true}));
      el.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true}));
    }""", str(v))
```

- **Plain `el.value = x` does nothing.** React never sees the change, the result panel keeps its static
  help text, and a public calculator looks "broken" when the harness is at fault. This produced a
  false "the tool returns the wrong number" reading for a full round.
- Selects need the `HTMLSelectElement` prototype — reusing the input setter on a `<select>` throws.
- **Settle 3.5–4 s** before reading results; these panels recompute on a debounce.
- Read the result as `" ".join(page.inner_text("body").split())` and pull `£[\d,]+` — but also keep the
  surrounding sentence, because the *copy* ("Property allowance applied … instead of £0.00 actual
  expenses") is often the finding itself.

## 2. Submit with `requestSubmit()`

```python
pg.eval_on_selector("form", "f => f.requestSubmit ? f.requestSubmit() : f.submit()")
```

- `pg.get_by_role("button", name="...")` timed out repeatedly on these pages (the handlers are client
  components; the accessible name drifts). `requestSubmit()` worked for every step.
- **Read the BODY, not the URL.** A multi-step flow (login → MFA) left `page.url` unchanged while the
  body switched from the password form to the 6-digit code prompt. Asserting on the URL alone reports a
  failed login that actually succeeded.

## 3. Open the right sub-form

The identical "Record expense" button behaved differently per tier:

| tier | click behaviour |
|---|---|
| Pro | modal → *Scan with AI* / *Enter manually* → then `#category #amount #txnDate` |
| free | straight to `#category #amount #txnDate` (no modal) |

Probe after opening:

```python
pg.evaluate("""()=>{const b=[...document.querySelectorAll('button')]
  .filter(x=>/Enter manually/i.test(x.innerText||''));
  if(b.length){b[0].click(); return 'modal';} return 'direct';}""")
```

Then set `#category` (the value must be one of the API's category keys, e.g. `repairsAndMaintenance`,
`residentialFinancialCost`) + `#amount` + `#txnDate`, and click `Add income` / `Add expense`.

## 4. Delete rows: inline confirm, index not text

- The confirmation is **inline** (`Delete? Yes No`), so `page.on("dialog", ...)` never fires. A bare
  `.click()` on the delete button does nothing observable — the row stays and the ledger is unchanged.
  Always follow with:
  ```python
  pg.get_by_role("button", name="Yes", exact=True).click()
  ```
- Row-*targeted* selectors ("the row whose innerText contains Repairs") failed repeatedly. The
  dependable pattern is: find the first `button[aria-label='Delete entry']`, click, click "Yes",
  re-read the ledger, repeat until clean — then **re-add** anything you removed that must be restored.
- Verify by reading the source's own summary line (`Income · 2026-27 £… Expenses · … Net profit · …`),
  not by counting rows in the DOM.

## 5. Cleanup discipline (this is not optional)

Seeding a scenario mutates the operator's account. Before finishing:

1. Re-add every removed row with its original amount/date/category (keep the dump you took before you
   started — you will need the exact values, including any deliberately odd ones like a prior XSS test
   row at `-£12.34`).
2. Re-read the summary and assert it equals the pre-test values
   (`Income £31,001.01 / Expenses £2,512.34 / Net £28,488.67 / finance £3,000 / Est. tax £2,583.73`).
3. Delete any API key you minted and any invite you sent; re-check the page shows them gone.
4. Duplicate-add is easy (a retry adds a second identical row) — check the totals and drop the spare.

## 6. Session reuse beats a fresh login

Before asking for credentials/MFA, try a session cookie stored from a previous pass:

```bash
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" -H "Cookie: qw_session=<val>" https://target/app
# 307 -> /app/...   = authenticated, proceed
# 307 -> /login    = expired, then build the TOTP flow
```

When you do need the TOTP: `pyotp.TOTP(secret).now()` (and a 20-line HMAC-SHA1 fallback if pyotp is
absent) — verify both agree before using the code, and read the code *immediately* before submitting
(30 s window).
