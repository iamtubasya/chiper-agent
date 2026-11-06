# Submitting a CVD report through an ASP.NET WebForms form (Infoland WebControls3)

Hit live 2026-10-31 on Zenya/Infoland (`forms.zenya.work/psbr6j9omo/1325`). This stack
rebuilds its control IDs on every page load, so a hard-coded selector set does not survive
and a hand-built POST fails silently. The working method is to drive a real browser and let
the page's own JavaScript serialise the payload, then read the payload back before submitting.

## Why a hand-built POST fails

The text fields, the description and the custom dropdown carry **no `name` attribute**. They
never travel as normal form inputs — everything is serialised into a single hidden field,
`hidFormData`, by the page's own `collectFormData()`:

```js
document.getElementById('hidFormData').value = JSON.stringify(objCollectedFormData);
```

A POST assembled from the visible inputs therefore reaches the server with `hidFormData`
empty, and the response is a generic error page:

```
HTTP 200 (not a redirect)
Er is een onverwachte fout opgetreden
Error ID: <guid>
```

That page is the signature of *"the server accepted the request and thrown inside the
handler"*, not of a rejected submission. Nothing was sent. Confirm by checking that the
response is the error template rather than a Thank You redirect.

## Correct flow

1. **Fetch the form, parse the field metadata.** The page embeds the field definitions as JSON:

   ```python
   m = re.search(r'var objFields\s*=\s*(\[.*?\]);', html, re.S)
   spec = json.loads(m.group(1))          # FieldTypeName, FieldID, Options.listvalues, maxlength
   ```

2. **Verify required fields and option IDs against a FRESHLY fetched form each time.** Option
   IDs (e.g. `7976` = "Security misconfigurations") are stable, but validating against the live
   page each run catches a changed form before you submit into it.

3. **Drive a real browser** (Playwright) and fill by the control's DOM id:
   - text inputs / textareas: `pg.fill("#MainContent_ctl00", value)`
   - radio-backed lists: `pg.check("#rdoMainContent_ctl08_" + option_id)`
   - custom dropdown: call the prototype method, **not** by setting internal fields

4. **Build the payload by invoking the page's own serialiser**, then read it back:

   ```python
   collected = pg.evaluate("() => { collectFormData(); return document.getElementById('hidFormData').value; }")
   parsed = json.loads(collected)
   ```

5. **Gate on the parsed payload**, not on what you typed. Refuse to click Submit unless every
   field reads back with the expected value.

## The `getValue()` shapes (per FieldTypeName)

From `window.FieldTypes.<type>.getValue(intFieldID)`. Build the JSON in these shapes if you
must construct it by hand; prefer letting the page do it.

| FieldTypeName | shape |
|---|---|
| `Text` | `{"TextValue": "<string>"}` |
| `EmailAddress` | `{"TextValue": "<string>"}` |
| `List` | `{"ListValues": {"i_<optionID>": "<optionText>"}}` |
| `Attachments` | `{"AttachmentValues": []}` |

Each entry also carries `FieldID` (int) and `FieldType` (string).

## ⛔ The custom dropdown is offset by one — verify by VALUE, never by index

The single most dangerous trap on this stack. The dropdown object's `_objItems` array includes
a leading `- Clear selection -` placeholder that the *rendered list* does not, so the index you
pass to `_setSelectedIndex()` is **not** the `_objItems` index.

Measured: asking for `7976` (Security misconfigurations) and passing the `_objItems` index `8`
silently selected **`7977` — "Cross Site Scripting (XSS)"**. A report would have been filed
under a vulnerability class the researcher never demonstrated.

The fix is to search candidate indices and keep the one whose getter agrees:

```python
dd = pg.evaluate("""(wanted) => {
    const id = Object.keys(window).find(k => k.startsWith('MainContent_objDropdown') && !k.endsWith('_Tooltip'));
    const o = window[id];
    const idx = (o._objItems||[]).findIndex(i => String(i.Value) === String(wanted));
    let used = null, gv = null;
    for (let cand = Math.max(0, idx-2); cand <= idx+2; cand++) {
        try { o._setSelectedIndex(cand); } catch(e) { continue; }
        let v = null; try { v = o.getSelectedValue(); } catch(e) {}
        if (String(v) === String(wanted)) { used = cand; gv = v; break; }
    }
    return {ok: used !== null, usedIndex: used, getSelectedValue: gv,
            getSelectedText: o.getSelectedText()};
}""", wanted_id)
```

Then assert the ID appears in the serialised payload, e.g.
`any(str(e["FieldID"]) == "3429" and "i_7976" in json.dumps(e) for e in parsed)`.

Useful prototype methods on that object: `_setSelectedIndex`, `getSelectedValue`,
`getSelectedText`, `getSelectedData`, `getItemElementID`, `showDropDown`, `closeDropDown`.
Setting `_intSelectedIndex` / `_strSelectedText` / `_strSelectedData` directly does **not**
work — `getSelectedValue()` still returns null and the field serialises as `ListValues: {}`.

## Control IDs rotate every load

`MainContent_objDropdown<32-hex>` and `MainContent_objFileUploader<32-hex>_FileInput` are
regenerated per request. Never hard-code them — discover them:

```python
dd_id = pg.evaluate("() => Object.keys(window).find(k => k.startsWith('MainContent_objDropdown') && !k.endsWith('_Tooltip'))")
```

## Spam-protection gate

The submit handler first posts to a validation service and puts the returned GUID into
`hidValidationCode`. Replicate it, or the page's own submit path already does it for you:

```
POST https://forms.zenya.work//Webservices/SpamProtectionService.svc/ValidateForSubmit
Content-Type: application/json
{"strTargetGroupID": "<target group id>"}
-> {"d": "<guid>"}          # '00000000-0000-0000-0000-000000000000' means blocked
```

`strJSTargetGroupID` and `strSpamProtectionServiceURL` are declared near the bottom of the page.

## Success signal

A successful submission redirects to a Thank You URL carrying an opaque submission id:

```
https://forms.zenya.work/<group>/<formid>/ThankYou$?formdataid=<guid>
```

Capture that id — it is the only receipt the vendor gives you before the acknowledgement
email. A `ThankYou` URL whose `email=` shows `Anonymous` is **not** proof the contact address
was dropped; that parameter is cosmetic. Verify the real value by reading `hidFormData` before
submit, and by repeating the address inside the Description body.

## Verification checklist before clicking Send

- [ ] 3 independent runs, fresh page each, all fields read back identical
- [ ] dropdown asserted by **value** (`i_<id>` present in parsed payload), not by index
- [ ] every required live field covered by the payload
- [ ] text lengths under each `maxlength`
- [ ] contact address present in **both** the Email field and the Description body
- [ ] gate coded to `raise SystemExit(1)` when any check fails — no silent path to submit
- [ ] after submit: Thank You URL + `formdataid` captured to a file, page screenshot saved
