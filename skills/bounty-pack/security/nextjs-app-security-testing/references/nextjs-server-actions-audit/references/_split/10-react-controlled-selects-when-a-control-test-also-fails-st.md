## React controlled selects: when a control test also fails, STOP and say so

Setting a controlled `<select>`'s value (even via the native setter) does not always reach
React state, and the subsequent submit can return HTTP 200 with a page render and NO state
change. If the LEGITIMATE value also fails to apply, the harness is the problem — report
"offered in the UI, application unverified", never "bypass". This is the same rule as the
digest-only 500s: a failed control invalidates the finding, not the target.

**Duplicate ids are the usual culprit when the native setter throws `Illegal invocation`.**
Seen on Quarterwise: the NINO card was `<div id="nino" class="card">` wrapping
`<input id="nino" name="nino">`. `document.querySelector('#nino')` returns the DIV, so
`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el, v)` is
applied to a div and Chromium throws "Illegal invocation" — and Playwright's `fill('#nino')`
fails with "Element is not an <input>…". Before blaming React or the framework, dump
`[...document.querySelectorAll('[id]')]` and look for repeats, then target by attribute
(`input[name="nino"]`). The duplicate id itself is also a (minor) reportable defect.

**`Illegal invocation` has a second, more common cause: the wrong prototype.** Filling a
`<textarea>` with `HTMLInputElement.prototype`'s value setter throws it. Use the element's own
constructor so the same helper works for input/textarea/select:

```js
const setv=(sel,val)=>{ const el=document.querySelector(sel); if(!el) return false;
  const set=Object.getOwnPropertyDescriptor(el.constructor.prototype,'value').set;
  set.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true}));
  el.dispatchEvent(new Event('change',{bubbles:true})); return true; };
```

**`:has-text()` is a Playwright selector, not a CSS one.** Dropping it (or `locator("button:has-text(...)")`
text) inside `page.evaluate(...)` raises `SyntaxError: 'button:has-text("X")' is not a valid
selector` and kills the run mid-script. Inside `evaluate`, filter the NodeList yourself:
`[...document.querySelectorAll('button')].find(b=>/save/i.test(b.innerText||''))`. Keep
Playwright-only syntax for `pg.locator(...)` calls, where it belongs.

**A form that emits ZERO network requests is usually HTML5 validation, not a broken action.**
Before writing it up as "the button does nothing", dump the page's required fields:

```js
[...document.querySelectorAll('input[required]')].map(x=>({n:x.name||x.id, t:x.type, v:x.value}))
```

A `required` field that is empty (typically a sibling form's `mfaCode` / OTP box) makes the
browser refuse to submit and console shows nothing. Seen on Quarterwise: the invoice-settings
form carries a required `mfaCode` (bank details print on invoices), and the same settings page
also never submitted on click / Enter / `form.requestSubmit()`. Two silent-submit failures on the
same page = **harness limit, report the field inspection and say the server behaviour was not
verified** — do not upgrade it to "destructive action is unprotected".

