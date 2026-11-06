# Web-form report submission (CVD / vendor forms)

When the programme's channel is a **web form** rather than an email address, most of this skill's
email machinery is irrelevant and a different set of traps applies. Measured live 2026-10-31
(Zenya / Infoland CVD form) — one successful submission, but only after two near-misses that would
each have shipped a wrong report.

## 0. Decide the channel from the policy text, not from habit

Read the "How to report" section verbatim before building anything:

> "You can submit your findings through our Coordinated Vulnerability Disclosure form."

If it says form, build the form. Staging a Gmail draft "as well" is wasted work — in the Zenya
engagement the email draft was staged first and turned out to be dead weight. Get the channel right
in step 0 and skip the email pipeline entirely.

If the policy offers **both**, prefer the form (it is usually ticketed and acknowledged
automatically) and keep the email path only as a fallback.

## 1. Recon the form before you try to submit

Never POST blind. Fetch the form page and answer:

- What is the framework? (`__VIEWSTATE` → ASP.NET WebForms; `_token` → Laravel; `__NEXT_DATA__` →
  Next.js; a bare `<form method="post">` → plain POST)
- Which inputs carry a `name` attribute, and which do not?
- Is there a hidden field that a JS function populates at submit time?
- Is there a spam/CSRF service called on submit?
- What are the field IDs / allowed values for any list or dropdown?

```python
import re
t = requests.get(form_url, headers=UA, timeout=30).text
for m in re.finditer(r'<(?:input|select|textarea)[^>]*?\sname="([^"]+)"', t):
    print(m.group(1))
```

**The critical observation:** in the Zenya form, Title / URL / Description / E-mail / Type /
Severity / Consent had **no `name` attribute at all**. They are not posted as ordinary fields —
they exist only inside a hidden text input named `hidFormData`, which the page's JavaScript builds
on submit. Any attempt to hand-craft the POST from the visible inputs produces an empty report.

## 2. Find the serializer, and read its output shapes from source

The page defines a per-field-type serializer. Grep the inline JS for it:

```javascript
function collectFormData() {
    var objCollectedFormData = [];
    for (var intI = 0; intI < objFields.length; intI++) {
        var objField = objFields[intI];
        var objElement = document.querySelector(".WebFormElement[data-field-id='" + objField.FieldID + "']");
        if (objElement.getAttribute('data-conditional-disabled') != '1') {
            var objWebformResult = window.FieldTypes[objField.FieldTypeName].getValue(objField.FieldID);
            objWebformResult.FieldID = objField.FieldID;
            objWebformResult.FieldType = objField.FieldTypeName;
            objCollectedFormData.push(objWebformResult);
        }
    }
    document.getElementById('hidFormData').value = JSON.stringify(objCollectedFormData);
}
```

Then read each `FieldTypes.<Type>.getValue` to learn the exact object shape:

| Type | `getValue()` returns |
|---|---|
| `Text` | `{ TextValue: <string> }` |
| `EmailAddress` | `{ TextValue: <string> }` |
| `List` | `{ ListValues: { "i_<optionId>": "<optionText>" } }` |
| `Attachments` | `{ AttachmentValues: [ {ID, Name}, ... ] }` |

The `objFields` array (also inline) carries each field's `FieldID`, `FieldTypeName`, `required`
flag, `maxlength`, and the full `listvalues` for any List — that is your authoritative schema.

## 3. Do NOT hand-build the hidden JSON — drive a real browser and read it back

You *can* reconstruct `hidFormData` by hand from the shapes above, but the page's own serializer is
the ground truth and it is free. Fill the form in a real browser, call `collectFormData()`, and read
the value back:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b  = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page()
    pg.goto(form_url, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(2500)

    pg.fill("#MainContent_ctl00", title)
    pg.fill("#MainContent_ctl04", url_ip)
    pg.fill("#MainContent_ctl05", description)
    pg.fill("#MainContent_ctl07", email)
    pg.check("#rdoMainContent_ctl02_" + severity_id)   # radio list
    pg.check("#rdoMainContent_ctl08_" + consent_id)

    collected = pg.evaluate("""() => {
        collectFormData();
        return document.getElementById('hidFormData').value;
    }""")
    parsed = json.loads(collected)
```

This is both the fill mechanism *and* the verification mechanism — see §5.

## 4. Custom dropdowns: `_setSelectedIndex` is 1-based over the VISIBLE list, not the item array

This is the single most dangerous trap in the whole flow. The dropdown is not a `<select>`; it is a
custom widget whose real value must be set through its API.

Measured failure: the target value was `7976` ("Security misconfigurations") at index **8** in
`_objItems`. Calling `_setSelectedIndex(8)` selected **`7977` — "Cross Site Scripting (XSS)"**.

Cause: the visible list carries a leading `- Clear selection -` placeholder, so the visible index is
the array index **minus one**. Submitting would have filed the bug as an **XSS I never proved** —
exactly the overclaim the rest of this skill exists to prevent.

Correct approach — **search for the index whose resolved value matches, and verify by value, never
by index**:

```python
dd = pg.evaluate("""(wanted) => {
    const id = Object.keys(window).find(k =>
        k.startsWith('MainContent_objDropdown') && !k.endsWith('_Tooltip'));
    const o = window[id];
    const idx = (o._objItems || []).findIndex(i => String(i.Value) === String(wanted));
    if (idx < 0) return {ok:false, reason:'item not found'};
    let used = null, gv = null;
    for (let cand = Math.max(0, idx-2); cand <= idx+2; cand++) {
        try { o._setSelectedIndex(cand); } catch(e) { continue; }
        let v = null; try { v = o.getSelectedValue(); } catch(e) {}
        if (String(v) === String(wanted)) { used = cand; gv = v; break; }
    }
    return {ok: used !== null, wanted, usedIndex: used, getSelectedValue: gv,
            getSelectedText: o.getSelectedText()};
}""", type_id)
```

The window search matters: it is robust to a ±N shift without you having to reason about which
placeholder exists. **Never trust the returned index; trust `getSelectedValue()`.**

Reading the widget's API when you don't know it: `Object.keys(obj)` gives own methods,
`Object.getOwnPropertyNames(Object.getPrototypeOf(obj))` gives the prototype methods where
`_setSelectedIndex`, `getSelectedValue`, `getSelectedText`, `getSelectedData` live.

## 5. The 3× pre-submit check IS the readback — do it from the page, not by eye

Eyeballing the rendered form proves nothing; the field that actually ships is the hidden blob. The
check is: fill → `collectFormData()` → parse → assert every field against the intended value.

```
[ ] every required field present and non-empty
[ ] every List field's ListValues key == the intended option id
[ ] every List field's ListValues text == the intended option label
[ ] every Text/EmailAddress TextValue byte-identical to the intended string
[ ] Attachments present as AttachmentValues (even if empty)
[ ] consent field carries a real option id
```

Run it **3 times on a fresh page load each time** — that is the operator's 3× rule applied to the
form, and it catches viewstate/session drift as well as logic errors.

Then gate the submit mechanically. If any assertion fails, refuse to click:

```python
gate = all(checks.values())
if DO_SUBMIT and not gate:
    print("REFUSING TO SUBMIT — gate failed")
    raise SystemExit(1)
```

A scripted gate cannot talk itself into sending; a human reading the form can.

## 6. Mechanics of the POST (when you submit by HTTP instead of the browser)

If you do submit programmatically, keep the pieces together:

```python
rv = requests.get(form_url)
vs  = hidden(t, "__VIEWSTATE")          # ~7-9 KB, unique per page load
vsg = hidden(t, "__VIEWSTATEGENERATOR")
ev  = hidden(t, "__EVENTVALIDATION")
guid = requests.post(spam_url, json={"strTargetGroupID": group},
                     headers={"Content-Type": "application/json"}).json()["d"]

data = {"__EVENTTARGET":"", "__EVENTARGUMENT":"",
        "__VIEWSTATE":vs, "__VIEWSTATEGENERATOR":vsg, "__EVENTVALIDATION":ev,
        "hidValidationCode":guid, "hidFormData":hid_json,
        "ctl00$MainContent$objSubmit":"Send"}
```

- `__VIEWSTATE` is fresh per GET — never reuse a cached one.
- The spam/validation GUID is **also fresh per attempt**; request a new one immediately before posting.
- Send the same session (cookies **and** `Referer`/`Origin`).
- **Do not add an empty multipart file part.** Sending
  `files={"..._FileInput": ("", "", "application/octet-stream")}` for an optional attachment field
  makes the handler throw `"Er is een onverwachte fout opgetreden"` (unexpected error). If the
  attachment field is optional and you don't need it, post plain urlencoded JSON-only.

Prefer the browser path when the page defines a heavy serializer, as here — it removes the whole
class of "did I reconstruct the blob correctly" doubt.

## 7. Verify the submission actually landed

"HTTP 200" is not confirmation — an error page also returns 200. Read the **destination**:

| Signal | Meaning |
|---|---|
| URL becomes `<form>/ThankYou$?...&formdataid=<guid>` | accepted; the guid is your case reference — record it |
| Body contains "Thank you for reporting…" | accepted |
| Body contains "unexpected error" / `Error ID: <guid>` | rejected — nothing sent; capture the Error ID |
| Same form re-renders with fields cleared | usually validation failure; re-check the blob |

Capture `submit_result.txt` (URL + body text) and a screenshot. Record the `formdataid` in the
engagement ledger next to the finding — it is the only handle if you need to follow up.

**Watch for a display-only discrepancy.** The Zenya ThankYou URL read `email=Anonymous` even though
the EmailAddress field carried the real address. That parameter is cosmetic. Before assuming your
contact was dropped, confirm it is present in the submitted `hidFormData` — and belt-and-braces,
repeat the contact in the Description body so the triager sees it regardless of field mapping.

## 8. Pitfalls checklist

- [ ] Channel taken from the policy text, not assumed to be email
- [ ] Form recon done: framework, named vs unnamed inputs, hidden serializer, spam service
- [ ] Serializer shapes read from `FieldTypes.*.getValue` source, not guessed
- [ ] Dropdown selection verified by **resolved value**, never by index
- [ ] 3× readback from `collectFormData()` on a fresh load each time
- [ ] Hard gate that refuses to submit on any mismatch
- [ ] No empty multipart file part for an optional attachment field
- [ ] Fresh `__VIEWSTATE` + fresh validation GUID per attempt
- [ ] Post-submit: read the destination URL/body, capture `formdataid`, store it in the ledger
- [ ] Contact present in the submitted blob *and* in the Description body
- [ ] The severity/category you actually selected matches what your report body claims
