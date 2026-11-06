# Gated route handlers, collapsed rows, and forms that never fire

Worked material from a Next.js App Router tax SaaS (Quarterwise, 2026-09-30), written as a
checklist because every item here cost a debug cycle in the session it came from.

## 1. Inventory the handlers the UI actually uses

```bash
# authenticated crawl first — the anonymous one only sees the landing pages
katana.exe -u https://target -H "Cookie: <session>" -jc -kf all -d 3 -c 5 -rl 6 \
           -timeout 15 -silent -o authed.txt -fs rdn
# then pull the page chunks it revealed and grep route literals (plain strings, unlike action ids)
grep -ohE '"/api/[A-Za-z0-9_./{}$?=&-]+"' chunks/* | sort -u
grep -ohE '.{160}type:"file".{200}' chunks/*          # upload inputs and their accept-lists
grep -ohE '\{\s*id:"(\w+)",label:"([^"]+)"\}' chunks/* # tab definitions
grep -ohE '.{120}invoicing.{140}' chunks/*             # the flag that gates the interesting tab
```

Handlers found this way and testable afterwards: `/api/attachments/{id}` (receipt files on
ledger entries), `/api/invoices/{id}/pdf` (customer-facing PDFs), `/api/properties/{id}/export`.

## 2. BOLA matrix and the statuses that mean "control holds"

| Identity | `/api/attachments/{id}` | `/api/invoices/{id}/pdf` |
|---|---|---|
| owner session | 200 `image/png` | 200 `application/pdf`, `content-disposition: inline; filename="invoice-INV-0001.pdf"` |
| second account (own) | 404 | 404 `text/plain` "not found" |
| no session | 307 → /login | 307 |
| random uuid | 404 | 404 |
| list endpoint cross-account | — | `/api/invoices` → 404 |

Cross-account on the *page* route also 404s (foreign source id → marketing/not-found shell;
`/api/properties/{foreign}/export` → `{"error":"not found"}`). Keep the owner's 200 body: for
invoices it contains the customer name and address, which is the reason the check matters.

## 3. Unlocking a flag-gated feature

`InvoicesTab` props were `{propertyId, businessRowId, isSe, invoicing, isOwner, …}` → the tab
renders only for a **self-employment** business. Creating one through the app's own flow
(dashboard → Add an income source → Self-employment, name only) made the tab appear, exposed
`businessRowId`, and produced a real object to test. Fields of the invoice form, in order:
`customerName`, `issueDate`, `customerAddress`, `lineDesc0`, `lineQty0`, `linePrice0`.

Same page carried a positive control worth reporting: the invoice-settings form (address, bank
details, number prefix) has a **required `mfaCode`** field — bank data is step-up gated even
though the account already has 2FA on.

## 4. Reading an id out of a collapsed row

Rows render as `button[aria-expanded="false"]` whose innerText contains the human reference
(`INV-0001`). Click it, *then* grep:

```js
const h = document.documentElement.outerHTML;
[...new Set(h.match(/\/api\/invoices\/[0-9a-f-]{36}/g) || [])]   // -> ['/api/invoices/cf025564-…']
```

Grepping before the expand finds nothing and reads as "the object has no id in the DOM".

## 5. Forms that emit zero network requests

Three submit paths all produced nothing on the settings page: Playwright `locator.click()`,
`press("#confirmName","Enter")`, and `form.requestSubmit(button)` — while the sibling
entry-delete buttons (`button[aria-label="Delete entry"]`) worked fine. Check, in order:

1. `[...document.querySelectorAll('input[required]')]` — an empty required field (here the
   sibling form's `mfaCode`) blocks submit with no console output.
2. the button's `disabled` state — it can be gated on React state, and a native-setter fill
   without resetting the value tracker may not move that state.
3. whether the parent form's hidden `$ACTION_*` fields are present at all.

Two failures = stop and record it as a harness limit ("fields inspected, server behaviour not
verified"). Do not convert it into "the destructive action is unprotected".

## 6. Playwright/JS snippets that fail loudly

```js
// WRONG inside page.evaluate: " ".join(...) is Python, and this raises TypeError
txt: " ".join(document.body.innerText.split())
// RIGHT
txt: document.body.innerText.split(/\s+/).join(' ')

// WRONG inside page.evaluate: :has-text() is Playwright-only -> SyntaxError, kills the script
document.querySelector('button:has-text("Delete")')
// RIGHT
[...document.querySelectorAll('button')].find(b=>/Delete/.test(b.innerText||''))

// WRONG for a <textarea> -> "Illegal invocation"
Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(textarea, v)
// RIGHT: use the element's own prototype
Object.getOwnPropertyDescriptor(el.constructor.prototype,'value').set.call(el, v)
```

## 7. Boundary sweep that found the one real (P5) defect

```
/app/sources/{id}?ty=abc | -1 | 0 | 2026.5 | 99999 | 20261   -> 200 (graceful fallback)
/app/sources/{id}?ty=1900 | 9999                             -> 500 (Next.js error page)
/app/sources/{id}?ty=1900%00                                 -> 200
anonymous visitor, any ty                                    -> 307 → /login (so: session required)
```

No stack trace, no data, no state change → P5 robustness note, reported as such. It only exists
because the parameter was swept instead of probed once.
