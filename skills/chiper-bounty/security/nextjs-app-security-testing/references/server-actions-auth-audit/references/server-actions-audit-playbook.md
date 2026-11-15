# Server Actions Audit Playbook — Extended Field Cases & Oracles

Session-derived detail for auditing Next.js App Router apps with Server Actions.
Companion to SKILL.md; this file holds the fuller raw examples.

## 1. Field-prefix examples observed in the wild

**Add-income action (page = property detail, action index 1):**

```
_1_propertyId   1f1dae0a-...
_1_type         income
_1_category     periodAmount
_1_amount       424.24
_1_txnDate      2026-09-25
0               [{}, "$K1"]
```
Headers: `next-action: 607c1542...`, `Accept: text/x-component`,
`Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...`,
`Referer: https://TARGET/app/sources/<id>`.

**Save-account-details action (action index 4):**

```
_4_$ACTION_REF_4   (empty)
_4_$ACTION_4:0     {"id":"...","bound":"$@1"}
_4_$ACTION_4:1     [{}]
_4_$ACTION_KEY     k03bd56df...
_4_name            Audit Tester
_4_email           test@example.com
0                  [{}, "$K1"]
```

**NINO save on /app/hmrc (action index 3):** same shape with `_3_nino`,
`_3_mfaCode`. Omitting `_3_mfaCode` entirely OR sending a wrong code both failed
server-side (500 + NINO not persisted; reload oracle showed empty input) →
MFA enforced at the action.

**Invite adviser (action index 8):** `_8_email`, `_8_role`. Role values seen:
`viewer`, `contributor`. Sending `owner` via DOM tamper → server fell back to
viewer (response re-rendered invite row as CAN VIEW). Role is enum-validated
server-side.

**Share co-owner invite:** fields `shareEmail`, `sharePercent` (plus owner
percent input `ownerPercent`). Over-allocation rejected server-side:
`{error:"That would take the property over 100% owned. There is 40% left to allocate."}`.

## 2. Cross-tenant replay response signatures

| Test | Signal observed | Meaning |
|---|---|---|
| A-body + B-cookie | `1:E{"digest":"..."}` 500 | action binding session-scoped |
| A-body + B-cookie (older) | `{error:"Server action not found."}` | action unknown to session |
| B-session + A `propertyId` | `"That property could not be found."` | write re-scoped server-side |
| B-session, owner-only action | `{error:"Only the owner can change these settings."}` | owner check at action level |
| CSRF: same body, evil Origin | 500 digest (same as wrong-session) | Origin/action-key validation |

Rule: 500 by itself proves nothing; pair it with a valid-baseline differential
and an export/state oracle.

## 3. UI fill via Runtime.evaluate — gotchas

```js
// set value + notify React
i.value='x'; i.dispatchEvent(new Event('input',{bubbles:true}));
// checkboxes/radios
r.checked=true; r.dispatchEvent(new Event('change',{bubbles:true}));
// submit
document.querySelector('form').requestSubmit();
// read state
document.body.innerText.slice(0,N)
```

- Hidden fields like `$ACTION_REF_N` are populated by React; do NOT blank them.
- If the modal didn't open, the clicked element's text may include nested
  description text — match `startsWith('Rental property')` not `===`.
- After a mutation, verify with a fresh `Page.navigate` + export API, not the
  in-page DOM (client state may be stale).

## 4. TOTP self-enrollment details

- Secret regex on the setup page: `[A-Z2-7]{20,}` (base32, 32 chars typical).
- QR is a `data:image/png;base64,...` — decode if needed, but page text usually
  prints the key too.
- Reload between showing secret and submitting code ROTATES the secret — submit
  on the same page instance.
- After enabling, the login flow gains a `/login/mfa` step; TOTP from the same
  secret satisfies it.

## 5. NINO / MFA retention oracle

- `/app/hmrc` NINO save requires TOTP. Wrong code → error stays on page, input
  empty after reload, export clients[].nino=None.
- Correct code → UI may show a success marker, but export can still say
  `nino=None` if HMRC validation deferred — trust the EXPORT for "persisted"
  claims; a UI "saved" banner is weak evidence.

## 6. Role model & disambiguation (the near-miss)

Property has: owner, co-owners (share %), advisers (viewer / contributor).
- Co-owner shares = write access to the shared books by design.
- Contributor promise text: "They can remove only entries they added".
- Combined co-owner+contributor could delete owner entries → falsely looked like
  a broken contributor boundary. After revoking the co-owner share, pure
  contributor had 0 delete buttons on owner entries (only Edit) and 1 delete
  button on their OWN entry.
- Lesson: any cross-role test must be repeated with the surplus role stripped.

## 7. Param echo vs enforcement table

| URL | Page showed | Enforcement |
|---|---|---|
| /reset?codeLimit=1&why=cooldown | "in about 1 seconds" | server resend cooldown "58s" unchanged |
| /reset?codeLimit=77 | "about 77 seconds" | unchanged |
| /reset?why=<svg> | flight data `\u003csvg...\u003e` escaped; not in visible text | no DOM sink |
| /api/properties/{id}/export?format=csv | returned XLSX regardless (format param ignored/normalized) | — |

Display echo of a param is not enforcement. Attempt the action itself.

## 8. Import pipeline injection checks

Crafted CSV rows: `=SUM(A1:A2)`, `<img src=x onerror=alert(1)>`, `@@cmd|'/C calc'!A0`,
`{{7*7}} ${7*7}`. Preview parsed and displayed them as text. After (attempted)
import: entries page had no `img[src=x]`, no `onerror` in HTML; XLSX export had
payloads only in sharedStrings (no `<f>` elements); clients CSV prefix `'=...`
for `=`-led values. All sinks safe.