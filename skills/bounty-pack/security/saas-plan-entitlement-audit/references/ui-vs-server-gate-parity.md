# UI-hides-it / server-allows-it — gate & allow-list PARITY testing

Class: the client renders a *filtered* view of an enum or hides a field, and you assume the
server enforces the same rule. Sometimes it does. Sometimes it enforces it for 3 of 4 values.
**The tell is inconsistency across the whole enum, not a single accepted value.**

Two distinct parity surfaces, both cheap to test, both real bug classes:

| Surface | Client hides… | Server must… | Failure = |
|---|---|---|---|
| **Feature gate** | a whole capability/field behind a plan/flag prop | reject the gated *field* in the action | free user reaches a paid feature |
| **Enum allow-list** | some values of a select (role, category, status) | keep its own allow-list of values | writes a value the product says you can't |

Verified on a freemium UK tax SaaS, 2026-09. One surface held, the other leaked.

---

## Surface A — feature gate: find the client prop, then inject the gated FIELD

Do not stop at "the page wants me to upgrade". The gate is frequently a **prop on the client
component**, which tells you the exact server field to try.

```js
// bundle (minified) — the give-away:
function v(){ let {thenSe=!1, allowForeign:t=!1, onCancel:n} = ... }
//                                    ^^^^^^^^^^^^ the gate
// ...and inside: t ? (<checkbox> This property is outside the UK
//                     <select name="countryCode" required>…</select>) : null
```

So the server action that creates the object very likely accepts `countryCode`. Inject it:

1. Open the create form on a **fresh account with 0 resources** (on an account already at a cap
   the control is not rendered at all and the test silently does nothing).
2. Append hidden inputs to the real form and submit via the form's own submit button — keeps the
   React/Next binding valid:
   ```js
   const f = [...document.querySelectorAll('form')].find(x => x.querySelector('#name'));
   for (const [k,v] of Object.entries({countryCode:'ES', outsideUk:'1', isOverseas:'true'})) {
     const i = document.createElement('input'); i.type='hidden'; i.name=k; i.value=v; f.appendChild(i);
   }
   f.querySelector('button[type=submit]').click();
   ```
3. Read the server's own refusal string — that is the evidence.

**Known-good result (record it, it is a valid outcome):**
`"Overseas property is part of Pro. Upgrade to add a property outside the UK."` and the object is
not created. Also test the **update** action, not just create: injecting `countryCode` into the
property-settings action returned a success toast ("Settings saved.") while the object did **not**
become overseas — a success message is not proof the field was honoured. Always re-read the
object's state (and its export) afterwards.

---

## Surface B — enum allow-list parity (the one that leaked)

Client-side filtering of an enum is a *rendering* decision. It is not a control.

```js
v = ("income"===t ? y.Tl(i) : y.Od(i)).filter(e => !e.nrlOnly)
//                                       ^ four categories flagged nrlOnly are removed for EVERY user
```

There was **no toggle anywhere** that could ever satisfy `nrlOnly` (grep the whole bundle:
the flag appeared only in the category definitions and that one filter). So the UI hid those
values from every human, which makes the server's own allow-list the only real control.

Recipe — test the **entire** flagged set plus two controls:

1. Fresh page → open the create form.
2. Read what the UI actually offers and log it (proves the value is hidden):
   ```js
   [...document.querySelectorAll('#category option')].map(o => o.value)
   ```
3. For each candidate, inject an `<option>` if absent, set it, fill the rest, submit:
   ```js
   if (![...sel.options].some(o => o.value === cat)) {
     const o = document.createElement('option'); o.value = cat; o.text = 'INJ'; sel.appendChild(o);
   }
   sel.value = cat; sel.dispatchEvent(new Event('change', {bubbles:true}));
   ```
4. **Compare every server response side by side.**

Observed matrix (the inconsistency is the finding):

```
foreignTaxPaidOrDeducted          -> REJECTED  "Choose a valid category."
specialWithholdingTaxOrUkTaxPaid  -> REJECTED  "Choose a valid category."
seTaxDeducted                     -> REJECTED  "Choose a valid category."
totallyBogusKey                   -> REJECTED  "Choose a valid category."   (control: not real)
taxDeducted                       -> ACCEPTED  <-- 1 of 4 flagged values
periodAmount                      -> ACCEPTED                              (control: allowed)
```

Three of four flagged values are refused with one message; the fourth is written. That asymmetry
is what makes it *unintended* rather than a deliberate carve-out — say exactly that in the report.

### Verify with ground truth, never the toast
Confirm the write landed and how it is carried, from the export:
```
row  8  21/08/2026 | Tax withheld | Tax withheld from rent (not income, not in totals) | | 234.56
row 10  20/08/2026 | Tax withheld | Tax withheld from rent (not income, not in totals) | |  12.34
row 26  Tax withheld at source (paid to HMRC for you, not income) | 246.9   (12.34+234.56 ✓)
```
Reproduce it twice with different amounts before writing it up.

### Severity honesty for this class
The product's own copy matters: this value was labelled *"tax sent to HMRC out of your rent
(non-resident landlords)"* with the hint *"net it off your tax estimate"*. So a non-qualifying
user can write a figure the product treats as tax already paid, and it reaches the official
export / submission payload.

**Still P4/P5 LOW.** It is client/server validation inconsistency (CWE-20, improper input
validation) with a filing consequence, but it is **self-scoped**: the actor only alters their own
records. No other user's data, no entitlement gained, no boundary crossed. Do NOT inflate it to
P2/P3 — and do say plainly that the inconsistency is the strongest argument it is unintended.
The correct framing: *"client hides it, server accepts 1 of 4 flagged values, entry becomes a
first-class line in the official export"* + an explicit statement of what it does NOT grant.

---

## Rules of thumb

- Client-side `.filter()`, `v-if`, plan props, `featureFlag &&` are **hints**, never controls.
- Always run the **whole** enum, with one known-bogus control and one known-allowed control. A
  lone accepted value means nothing; the pattern across siblings is the evidence.
- A success toast ("Saved.") proves the request was accepted, **not** that the field was honoured.
  Re-read the object.
- Confirm the served allow-list from the *server's* refusals, not from the dropdown.
- Feature gates are commonly enforced server-side (this target held) — that is a **negative**
  worth recording with the exact refusal string, not a reason to stop testing the enum surface.
