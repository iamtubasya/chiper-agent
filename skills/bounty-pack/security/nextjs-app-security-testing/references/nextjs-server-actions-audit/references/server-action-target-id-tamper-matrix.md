# Server-action target-id tamper matrix — harness, wire ids, queue recipe

Session: Quarterwise (Next.js App Router, Cloudflare edge), 2026-10-01. Two tenants: the
vendor-granted **Pro firm** account (session cookie, refreshed after a login throttle window) and an
independent **free** account ("tenant D") holding a ledger of our own earlier test rows.
Hard rule honoured throughout: never invoke the HMRC submit family
(`submitQuarter|Annual|Se|Foreign*`, `finalDeclarationAction`, `checkHeld*`).

## 1. Why the naive replay fails

| id source | value | result when used in `next-action` |
|---|---|---|
| bundle `createServerReference` 5th-arg id | `608ea2447e785621cecc8e9c22d7a37d05d1c9e004` (`annualViewAction`) | **404, body `Server action not found.` (24 bytes)** |
| what the browser actually sends | `60dd7e2aca7bad3a5d61e22135457a37d95a277b88` (same page load) | works |

The wire id is a per-render encrypted value and is **not in the bundle**. Two consequences:
harvest it live, or avoid needing it (section 2).

## 2. Capture recipe (no CDP needed)

```python
pg.on("request", on_req)              # log every POST carrying a next-action header + its body
pg.on("response", on_resp)            # map wire id -> tts flight response (read the 1:{"error":…})
```

Facts worth remembering:

- **Page loads mostly do NOT fire actions.** Walking `/app`, `/app/clients`, `/app/review`,
  `/app/imports`, `/app/sources/<own>`, `/app/account*`, `/app/billing`, `/app/hmrc`, `/app/file` on
  this target produced exactly **one** action POST — `/app/year-end`'s fingerprint call
  (`_1_taxYear`, `_1_fph`). To see write actions you must drive a real write cycle.
- The captured body is multipart with `_1_<argName>` parts plus a trailing `0` = `[{}, "$K1"]`;
  parse with `re.finditer(r'name="(_1_[^"]+)"\r\n\r\n([^\r]*)', body)`.
- Wire ids seen for one action family across runs differ (`deleteTransactionAction` →
  `40320ee9…`, `406f9134…`, `40f20838…`), which is the same "re-harvest, never trust a cached id"
  rule that applies to chunk hashes.

Wire ids captured in this session:

| action | wire id |
|---|---|
| `addTransactionAction` | `60e5944b6198274889ab675e5b5ac94049936543e7` |
| `updateTransactionAction` | `60534dfc22d8a1b3943ff01b55228a8d1e7f5ed005` |
| `deleteTransactionAction` | `40320ee99326ce0c811c0dff7fb9e1a85b5559f622`, `406f91340d49a91b9f26836369f0fd669a392969b5`, `40f20838419efc3b27614a24766a58a8c12b60cce0` |
| review-queue **Confirm** | `4052414759f8cd53dd4f6cafbe0b5fb4ece234ba31` |
| `saveMappingAction` | `60f0ea719bb6aef08aa012520073906d62482c81e4` |
| listing assignment (import wizard) | `60f9563c8a1db7801b73c64ff8b015b32ff26ed8e2` |
| `commitImportAction` | `60793507a0e70cbf8ea19cf4a952747392e30ed565` |
| `uploadImportAction` | `60ce7e776f84d6833776722da51df1be1484c62080` |

## 3. The tamper harness (full shape)

```python
st = {"src": "", "dst": "", "on": False, "log": [], "resp": {}}

def handler(route):
    req = route.request
    if req.method == "POST" and "quarterwise.co.uk" in req.url and "/cdn-cgi/" not in req.url:
        wire = req.headers.get("next-action", "")
        if not wire:
            return route.continue_()
        body = req.post_data or ""                 # bytes: req.post_data_buffer
        hit = bool(st["on"] and st["src"] and st["src"] in body)
        rec = {"wire": wire, "patched": hit,
               "txn_before": re.findall(r'name="_1_txnId"\r\n\r\n([^\r]*)', body)[:1]}
        if hit:
            nb = body.replace(st["src"], st["dst"])
            rec["txn_after"] = re.findall(r'name="_1_txnId"\r\n\r\n([^\r]*)', nb)[:1]
            st["log"].append(rec)
            return route.continue_(post_data=nb)
        st["log"].append(rec)
    route.continue_()

def on_resp(r):
    w = r.request.headers.get("next-action")
    if w and r.request.method == "POST":
        st["resp"][w] = (r.status, re.sub(r"\s+", " ", r.text()))

def submit_owning_form(field="txnId"):           # bind to the FIELD's form, not "last submit"
    pg.evaluate("""(f) => { const el = document.querySelector('input[name="'+f+'"]');
        if (el && el.form) el.form.requestSubmit(); }""", field)
```

Read the verdict from the flight segment, not the status:
`re.findall(r'"error":"([^"]{3,160})"', st["resp"][wire][1])`.

## 4. Results (all with positive controls)

Every rejection below is paired with the same action succeeding on an owned target, so "the control
held" is not confused with "the harness never sent anything".

| action | foreign target | response | positive control |
|---|---|---|---|
| `addTransactionAction` | `propertyId` = tenant D property | `That property could not be found.` | own property → row appeared in the export |
| `updateTransactionAction` | `txnId` = tenant D entry | `That entry could not be found.` | own entry → amount £1.00 → £7.77 confirmed in the export |
| `deleteTransactionAction` | `txnId` = tenant D entry | no-op (own row survived; victim ledger byte-identical) | own row → deleted (used to clear the account) |
| review-queue **Confirm** | `txnId` = tenant D entry | no-op (queue item stayed) | unpatched → item confirmed, queue went to "Nothing to review" |
| `updateSourceSettingsAction` | shared client property | `Only the owner can change these settings.` | — |
| `updateOwnerShare` | shared client property | `That property could not be found.`; with a valid % → `Enter the current 6-digit code from your authenticator app.` | — |
| `deletePropertyAction` | shared client property | `Only the property owner can delete a property.` | own property + wrong `confirmName` → `The name you typed does not match this property.` → ownership gate precedes the name check |

## 5. Populate an empty review queue (the missing test)

```
/app/imports → choose a small CSV → Upload & preview
  step "mapping":  set every select[name="cat-key-<n>"] to the option whose text is "Review later"
  button "Apply mapping & continue"
  step "listing":  set select[name="listing-0"] to the target property (leaving it alone makes the
                   importer create a NEW property named after the file → "0 rows on the source I tested")
  button "Continue to preview"
  button "Import these transactions"
/app/review → each item = a form with hidden input[name=txnId], select[name=category]
              (pre-set to the AI suggestion) and a "Confirm" submit
```

Queue DOM that made the tamper test possible: the entry id is exposed as `input[name=txnId]` inside the
item's form, so `input[name=txnId].form.requestSubmit()` targets exactly that item.

## 6. Harness bugs that produced confident wrong answers

1. `patched = st["on"] and st["from"] in body` → `"" in body` is **always True**; the log said
   `patched: True` while nothing was rewritten. Guard on truthiness and log the field before → after.
2. `st.update(from_=...)` wrote a key the handler never read (`st["from"]`), so a whole pass of
   "foreign target" tests was actually unpatched. Same key on both sides, asserted.
3. `[...document.querySelectorAll('button[type=submit]')].pop().click()` hit the ownership-share
   *Update* button; the real subject form was never submitted. Use the field's own form.
4. Choosing the id by shape (`[0-9a-f-]{36}`) picked `propertyId` instead of `txnId` → wrong parameter
   rewritten → false pass. Address fields by NAME.
5. Wait for hydration before clicking anything: a click on a not-yet-hydrated button emits **no**
   request and reads as "the button is dead". `wait_for_selector` / `networkidle` first.

## 7. Ground truth + cleanup

- The ledger export (`/api/properties/{id}/export?format=pdf&taxYear=all`) is the row-level ground
  truth, but **a row regex can silently under-report**: categories containing a comma or ellipsis
  (`Rent, rates, insu...`) break `([A-Za-z ]+?)`. Print and read the raw text; treat the count as a
  convenience. This produced two wrong conclusions in one pass ("the foreign write must have failed",
  then "cleanup failed").
- Clean up by the proven per-row delete (`button[aria-label="Delete entry"]` → `Yes`) rather than an
  *Undo import* control that emitted no request. Switch the tax-year view (`?ty=all` / the
  "Choose tax year" button) and the **Entries** tab first, or rows from another year are not in the DOM
  and the delete buttons appear to be missing.
- Residue to disclose when there is no UI to remove it: import batch records created by test uploads
  (each is an empty shell once its rows are deleted).
