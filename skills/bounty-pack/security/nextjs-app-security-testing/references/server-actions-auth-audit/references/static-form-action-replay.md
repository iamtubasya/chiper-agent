# Static (browserless) Server-Action form replay

Why: driving every form through a headless browser is slow and flaky (hydration timing, hidden
confirm steps, `locator` misses). Any action that is **rendered as a `<form>`** in the
server-sent HTML can be replayed with plain `requests` — once you use the right field names.

## The one thing that matters: no `_N_` prefix

Chromium sends field names prefixed with the action index (`_1_propertyId`, `_1_$ACTION_KEY`, …).
Replaying those names from `requests` returns **500 "Internal Server Error"** for EVERY action —
identical 2140-byte Next.js error page. A sweep of uniform 500s is a *format* error, never a
"hardened target".

The names the server accepts statically are the **unprefixed** rendered field names.

## Field set per form style

Two styles coexist on the same page (a nav logout form uses one, the business forms the other):

| style | action fields in the `<form>` block | how the wire id appears |
|---|---|---|
| `$ACTION_ID_` | `name="$ACTION_ID_<42hex>"` (no value) | id is in the field name |
| `$ACTION_REF_N` | `$ACTION_REF_N` (empty) + `$ACTION_N:0` = `{"id":"<42hex>","bound":"$@1"}` + `$ACTION_N:1` = `[{}]` + `$ACTION_KEY` = `k<40hex>` | id is inside `$ACTION_N:0` |

Body to POST (multipart/form-data) to **the page path the form lives on**:

```
$ACTION_ID_<42hex>   ""                    # $ACTION_ID_ style only
$ACTION_REF_N        ""                    # $ACTION_REF_N style only
$ACTION_N:0          {"id":"<42hex>","bound":"$@1"}
$ACTION_N:1          [{}]
$ACTION_KEY          k<40hex>
<business field>     value                 # propertyId | accessId | keyId | documentId | confirmName | percent | taxYear
0                    [{}, "$K1"]
```

Headers: `Referer: <page url>`, `Accept: text/x-component`, `Origin: <origin>`.
A successful run answers **200** with a full RSC re-render (60–70 KB) that embeds
`1:{"error":"…"}` when the action refused. `303` + `Location` is also a valid action result
(e.g. after "remove access" → back to the list).

## Parse PER `<form>`, never page-wide

```python
for block in re.findall(r"<form\b.*?</form>", html, re.S | re.I):
    aid  = re.search(r'name="\$ACTION_ID_([0-9a-f]{42})"', block)
    ref  = re.search(r'name="(\$ACTION_REF_\d+)"', block)
    n0   = re.search(r'name="(\$ACTION_\d+:0)"\s+value="([^"]*)"', block)
    key  = re.search(r'name="\$ACTION_KEY"\s+value="([^"]*)"', block)
    fields = {m.group(1): m.group(2) for m in
              re.finditer(r'<input[^>]*name="([^"$][^"]*)"[^>]*value="([^"]*)"', block)}
    # ...classes/selects: take the first <option value=...> as the current value
```

A page-wide regex over all forms matched the **nav/logout** form first; the replay then invoked
logout (303 → /login) and invalidated the session mid-sweep. Slice the form blocks first.

## Classification of results

| observation | reading |
|---|---|
| `1:{"error":"That property could not be found."}` etc. | object-id lookup is account-scoped → **REJECT** |
| `1:{"error":"That key could not be found."}` | same, for revocation-style actions → **REJECT** |
| 200 re-render, no error, and an independent oracle shows the object untouched | **REJECT** (no-op) — confirm with the oracle, and with a positive control on an owned id |
| 303 + Location, no visible state change | action ran, nothing matched the substituted id → REJECT, but note it as a weaker signal (a random id would no-op even on an unscoped action too) |
| 500 (2140-byte Next.js page) | **format error** — check the `_N_` prefix and that the action id came from the right form |
| status 0 / no response | UNTESTED |

Random ids cannot distinguish "scoped" from "unscoped-but-absent" — a *valid foreign* id can. If the
only foreign object you can reach is one you own in a second tenant, use that; if the second tenant
cannot even hold the object type (e.g. a free plan with no "Add a document" affordance), record the
direction as **UNTESTED** rather than inferring.

## Session hygiene

* Re-fetch the page immediately before each replay (`$ACTION_KEY` and `$ACTION_N:*` are per-render).
* Action ids churn on redeploy — never cache them in a runbook.
* Since static replay can hit a logout/id-collision, keep credentials handy and re-login; re-run any
  test whose session died mid-flight.
