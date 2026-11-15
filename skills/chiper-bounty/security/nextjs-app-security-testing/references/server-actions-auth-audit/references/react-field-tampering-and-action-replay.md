# Driving & replaying Next.js Server-Action forms (Playwright/CDP) — snippets

Session-derived (2026): hardened UK tax SaaS, Next.js App Router, React-controlled
`<form action=$ACTION_* enctype=multipart/form-data>`. These are the exact ops that
worked after the naive ones silently no-opped.

## 1. Set a controlled input so React actually registers it

Naive (SILENT NO-OP — React value tracker drops it):
```python
el.evaluate("(e,v)=>{e.value=v;}", v)          # action submits the OLD value
```

Reliable (native setter + input/change):
```python
SET = """(e,v)=>{
  const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
  s.call(e,v);
  e.dispatchEvent(new Event('input',{bubbles:true}));
  e.dispatchEvent(new Event('change',{bubbles:true}));
}"""
pg.locator("[name='amount']").first.evaluate(SET, "60")
```

Or with real key events (also updates React, and is what a user does):
```python
el = pg.locator("[name='percent']").first
el.click(); el.press("Control+a"); el.type("60", delay=40)
```

## 2. Test a value NOT in a <select>'s options

Setting `select.value = "expenseKey"` on an option-less value yields `""` →
the action stores an EMPTY category, and you wrongly record "it accepted my
arbitrary category". Inject the option first:

```python
SET_SEL = """(e,v)=>{
  if(e.tagName==='SELECT' && ![...e.options].some(o=>o.value===v)){
    const o=document.createElement('option'); o.value=v; o.text=v; e.appendChild(o);
  }
  e.value=v;
  e.dispatchEvent(new Event('input',{bubbles:true}));
  e.dispatchEvent(new Event('change',{bubbles:true}));
}"""
```
Observed outcome once done correctly: an income form given an expense category key
was REJECTED ("Choose a valid…") — i.e. cross-type validation held. Without the
option-injection you get a false positive (an uncategorised row gets created).

## 3. Fire a progressive-enhancement form without fiddling with buttons

```python
form = pg.locator("[name='propertyId']").first.locator("xpath=ancestor::form[1]")
form.evaluate("f=>f.requestSubmit()")
```
Bypasses disabled/hit-testing problems. Works for bound actions too.

## 4. Handle the in-app confirm (inline buttons, not a dialog)

```python
dels = pg.locator("[aria-label='Delete entry']")
if dels.count():
    dels.first.click(); pg.wait_for_timeout(700)
    y = pg.get_by_role("button", name="Yes", exact=True)   # inline Yes/No
    if y.count() and y.first.is_visible(): y.first.click()
```
A cleanup loop must iterate the year selector (`?ty=2024..2027`) and verify via the
API count — a DOM count only sees the current tax year.

## 5. Progressive-enhancement multipart shape (unbound action)

```
POST /app/sources/<id>
Content-Type: multipart/form-data; boundary=...
_1_$ACTION_REF_4        (empty)
_1_$ACTION_4:0          {"id":"<42-hex>","bound":"$@1"}
_1_$ACTION_4:1          [{}]
_1_$ACTION_KEY          k<40 hex>
_1_propertyId           <uuid>
_1_name / _1_amount ... (the real fields, prefixed _1_)
0                       [{}, "$K1"]
```

## 6. Replay rule that costs the most time if missed

`$ACTION_KEY` is generated **per render**. Replaying your saved body later returns
`200` with a full HTML re-render but the action DOES NOT EXECUTE (bound args fail to
decrypt) — indistinguishable from success unless you read the value back. Either
re-fetch page fields immediately before each POST, or drive the live browser. Same
for action ids: they change on redeploy, so re-read them each round.

## 7. Observed-vs-landed table pattern (prove the write landed)

| Case | Submitted | Action response | Landed value (read-back) | Conclusion |
|---|---|---|---|---|
| own id, valid | propertyId=own, name=A | 200 re-render | name=A | action runs |
| foreign id | propertyId=random | `{"error":"Only the owner can change these settings."}` | unchanged | owner-scoped ✓ |
| stale key replay | — | 200 re-render | unchanged | key staleness, NOT a control |
| select value not in list | category=hacked (no option) | 200 | category=NULL | false positive avoided by option injection |

Always confirm the landed value through the product's own read path (API/export),
never from a "saved" toast.
