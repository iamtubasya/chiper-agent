## Destructive buttons that never POST: accept JS dialogs first

If a click on "Delete …", "Remove", "Confirm" or "Undo" produces **no network request at all**
(the URL does not change, no POST is captured), do not conclude the endpoint is broken or that
the action is unauthenticated. Playwright **auto-dismisses** native dialogs by default, so a
button whose handler is `if (!confirm(...)) return;` silently does nothing. Install the handler
before navigating:

```python
pg.on("dialog", lambda d: (log(f"[dialog] {d.type}: {d.message[:80]}"), d.accept()))
```

Observed on Quarterwise: three separate actions (property "Delete this property permanently",
adviser "Remove", import "Undo import") produced zero POSTs until the handler was added. Also
check the button's `disabled` state — on that form the delete button was `disabled=true` until
the typed property name matched, then `false`; a click while still disabled is a no-op.

After adding the handler, re-check every earlier "the control held" conclusion that rested on
"the request succeeded but nothing changed" — in this engagement the review-queue Confirm did
send the request once dialogs were accepted, which changed the finding from "unverified" to
"request delivered, state unchanged (still unexplained)". Two different outcomes; do not blend
them.

### …and the OTHER cause of "no request at all": an unfilled `required` field

If a click produces **no network activity** even with the dialog handler installed, check HTML5
validation before writing "the button is dead". A form whose write is gated on a fresh second
factor carries a required code input, and the browser silently refuses to submit while it is empty —
`click()`, `press('Enter')` and `form.requestSubmit()` all do nothing, with no console error.

```python
pg.evaluate("""() => {
  const f = document.querySelector('#confirmName')?.closest('form');
  return { required: [...f.querySelectorAll('[required]')].map(x => ({
             n: x.name || x.id, type: x.type, filled: !!x.value })),
           valid: f.checkValidity() };
}""")
```

Observed on Quarterwise: the self-employment settings form mixes `$ACTION_REF` hidden fields with
`name="mfaCode"` **required** — i.e. the vendor deliberately re-challenges the second factor for a
sensitive settings write (bank details for invoices). That is a *positive* control to report, not a
harness failure. Generalise: dump `[required]` + `checkValidity()` for the owning form before
concluding anything about a submit that never leaves the page, and state which of the two causes
(dialog gate vs validation gate) you actually proved.

