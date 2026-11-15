## Rewriting the target id in flight — the cross-tenant WRITE matrix, with positive controls

The strongest cheap test for entry-level write authz, and the one that finally settled every write
action on Quarterwise: **let the real UI fire the action with a valid (per-render) wire id, intercept
the POST, and rewrite the target id to another tenant's object.** The server's own flight-segment
error is the evidence, and because the id in the request came from the page you can also prove the
substitution happened (log the field *before → after*).

```python
def handler(route):
    req = route.request
    if req.method == "POST" and "quarterwise.co.uk" in req.url and "/cdn-cgi/" not in req.url:
        wire = req.headers.get("next-action", "")
        body = req.post_data or ""                      # multipart → use post_data_buffer for bytes
        if wire and st["on"] and st["src"] and st["src"] in body:
            nb = body.replace(st["src"], st["dst"])
            log(before=find_field(body, "_1_txnId"), after=find_field(nb, "_1_txnId"))
            return route.continue_(post_data=nb)
        log(wire=wire)                                   # log every action even when not patching
    route.continue_()
pg.route("**/*", handler)
```

Observed matrix (firm tenant → free tenant D / a view-only shared client property; every row has a
positive control where the SAME action on an OWNED target succeeds):

| action | foreign target | server response | control |
|---|---|---|---|
| `addTransactionAction` | `propertyId` | `That property could not be found.` | own property: row created |
| `updateTransactionAction` | `txnId` | `That entry could not be found.` | own entry: amount changed £1.00 → £7.77 |
| `deleteTransactionAction` | `txnId` | **no-op** — own row survived, victim byte-identical | own row: deleted |
| review-queue **Confirm** | `txnId` | **no-op** — the queue item stayed | unpatched: item confirmed, queue emptied |
| `updateSourceSettingsAction` | shared `propertyId` | `Only the owner can change these settings.` | — |
| `updateOwnerShare` | shared `propertyId` | `That property could not be found.` (valid % → demands the authenticator code) | — |
| `deletePropertyAction` | shared `propertyId` | `Only the property owner can delete a property.` | own property + wrong name → name-mismatch (proves the ownership gate fires first) |

**Harvesting the wire id without CDP** — a Playwright request listener is enough, and note that page
loads rarely fire actions (on this target only `/app/year-end` did, for its fingerprint call): you
must **drive a real write cycle** to capture write-action ids.

```python
pg.on("request", lambda r: log(r.headers.get("next-action", ""))
      if r.method == "POST" and r.headers.get("next-action") else None)
```

### Harness bugs that faked results (each produced a confident wrong answer)

- **`"" in body` is always True.** A patch log written as `patched = st["on"] and st["from"] in body`
  reports `patched: True` when `st["from"]` is empty, while the real rewrite never happens. Gate the
  guard on truthiness (`st["from"] and st["from"] in body`) **and** log the extracted field value
  before → after. "patched: True" with no field values is not evidence.
- **A dict-key typo silently disables the patch.** `st.update(from_=...)` (trailing underscore, from
  avoiding the Python keyword) left the handler reading `st["from"]` as `""` → every "foreign target"
  test that pass was actually an unpatched call. Read the same key you write, and assert the
  before/after differ.
- **Submit the OWNING form, not "the last submit button".** `document.querySelectorAll('button[type=submit]')[-1]`
  hit the ownership-share *Update* button (which then demanded an authenticator code) and the entry
  edit was never sent. Bind to the target field's form:
  `document.querySelector('input[name=txnId]').form.requestSubmit()`.
- **Picking the id with a loose regex grabs the wrong field.** A "first 36-char uuid on the page"
  matcher returned `propertyId` instead of `txnId`, so the patch rewrote the wrong parameter and the
  test looked like a pass. Read the field by NAME (`input[name=txnId]`), never by shape.

### Populating an empty review queue so its Confirm action can be tested

The AI-categorisation queue is fed by *low-confidence* rows, so an ordinary import (explicit category
per row) leaves it empty. Deterministic lever: upload a fresh CSV, and in the column-mapping step set
the per-row category selects to the literal **"Review later"** option
(`select[name="cat-key-<n>"]` → option text `Review later`) before pressing *Apply mapping & continue*
→ *Continue to preview* → *Import these transactions*. The queue then renders each item as a form with
a hidden `input[name=txnId]`, a `select[name=category]` pre-set to the AI's suggestion, and a
`Confirm` submit. Row counts live in the export, not the UI — a queued row may be absent from the
export until confirmed.

### Ground-truth parsers silently under-report — read the raw artifact

Twice in one pass a PDF-export row regex (`(\d{2}/\d{2}/\d{4})\s+([A-Za-z ]+?)\s+(\S+)\s+(£…)`) reported
**0 rows / "unchanged"** while the ledger actually held rows, because a category containing a comma
(`Rent, rates, insu...`) or an ellipsis breaks the `[A-Za-z ]+?` group. That produced a false
"cross-tenant write must have failed" and then a false "cleanup failed". Always print the raw export
text and READ it; treat the regex count as a convenience, and never as the only reading.

### Cleanup preference that costs fewer cycles

When clearing test rows, go straight to the proven per-row delete
(`button[aria-label="Delete entry"]`, confirm `Yes`) instead of fighting an *Undo import* control that
emits no request; and switch the tax-year view (`?ty=all` / the "Choose tax year" button) plus the
**Entries** tab first, or rows from another tax year are simply not in the DOM and the delete buttons
look absent. See `references/server-action-target-id-tamper-matrix.md` for the full harness, the
captured wire ids, and the queue recipe.

