---
name: server-actions-auth-audit
description: Use when auditing Next.js Server Actions auth or BOLA.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [nextjs, server-actions, bola, idor, auth, bug-bounty]
    related_skills: [hunt-nextjs, hunt-idor, hunt-ato]
---

# Server Actions Auth & BOLA Audit (Next.js App Router)

## When to Use

- Target is a Next.js App Router app (Next 13/14/15) with Server Actions: forms
  POST multipart with `$ACTION_*` hidden fields / `Next-Action` header to the
  page URL itself.
- The app has authenticated multi-tenant state (properties, documents, adviser
  invites, shares) and you need to test BOLA/IDOR beyond the obvious page-level
  checks.
- You need to unlock MFA-gated flows during authorized VDP testing.

## Overview

Hands-on playbook for auditing modern Next.js App Router apps whose state-changing
logic lives in Server Actions (multipart form actions), often with MFA gates,
adviser/co-owner role models, and import/export features. Built from a full
VDP engagement on a hardened MTD fintech app.

## Core technique 1 — Capture Server Action bodies, don't hand-craft them

Hand-building Server Action multipart bodies is fragile. A wrong construction
returns a **meaningless 500** — NOT evidence of server-side security. Always
capture the exact body from a real browser action first.

Observed multipart shape (action index `N`, zero-based per page):

```
_N_$ACTION_REF_N            (empty)
_N_$ACTION_N:0              {"id":"<action-binding-id>","bound":"$@1"}
_N_$ACTION_N:1              [{}]
_N_$ACTION_KEY              k<40 hex>
_N_<realfield>              e.g. _1_propertyId, _1_amount, _4_name, _4_email
0                           [{}, "$K1"]        (trailing action-arg field)
```

Headers sent with the action: `Next-Action: <action-id>`, `Accept: text/x-component`,
`Referer` = the page URL. The id is typically **42 hex chars** (some builds emit 40 —
treat it as opaque, don't assume a length).

Reliable capture: Chrome CDP `Network.requestWillBeSent` (filter POSTs to the app
page) + `Network.getRequestPostData` for the FULL body — the event's
`request.postData` alone is truncated/unreliable. Save
`{url, headers (Content-Type + Next-Action), postData}`; replay with the same
multipart boundary.

### 1a. Static replay (no browser): DROP the `_N_` prefix

The `_N_`-prefixed names above are what **Chromium** emits. Replaying them from `requests`
returns a meaningless **500 on every single action** — a whole sweep of 500s means the
*prefix* is wrong, not that the target is safe. The names the server actually accepts in a
hand-built POST are the rendered form field names, **unprefixed**:

```
$ACTION_ID_<42hex>   ""                                  # $ACTION_ID_-style forms (nav, keyId, accessId, documentId…)
$ACTION_REF_N        ""                                  # $ACTION_REF_N-style forms (source settings/share/delete…)
$ACTION_N:0          {"id":"<42hex>","bound":"$@1"}
$ACTION_N:1          [{}]
$ACTION_KEY          k<40 hex>
<field>              value                               # propertyId, accessId, keyId, documentId, confirmName, percent, taxYear
0                    [{}, "$K1"]
```

`multipart/form-data`, `Referer` = the page URL, `Accept: text/x-component`. With bare names the
server runs the action via the progressive-enhancement path and returns the real RSC result — so the
**whole form surface can be swept without a browser** (fast, loopable, no hydration flakiness).
Verified: source-page settings/share/delete returned their genuine ownership errors, and
`keyId` revoke returned `That key could not be found.`

Note the two form styles coexist in the same page (a nav logout form carries `$ACTION_ID_`, the
business forms carry `$ACTION_REF_N`); the bare-name body works for both.

## Core technique 2 — Drive UI via CDP, not raw urllib

- Login walls / Server Actions are far easier driven in a real browser:
  `Page.navigate` → `Runtime.evaluate` to set the input value + dispatch
  `new Event('input',{bubbles:true})` → click submit → read `document.body.innerText`.
  **Use the native value setter for controlled inputs — a bare `el.value=` is
  dropped by React and submits the OLD value (see Core technique 9.1).**
- Plain urllib POST that returns 500 = **malformed request**, not proof of a
  control. Baseline with a CORRECT request first; only a differential (valid
  works, tampered fails) is evidence.
- Browser-harness drivers timeout on heavy pages; raw
  `websocket.create_connection(page.webSocketDebuggerUrl, header=["Origin: http://localhost"])`
  works once Chrome runs with `--remote-allow-origins=*`. Keep one WS per tab;
  the eval loop must skip non-matching message ids.

## Core technique 3 — Cross-tenant (BOLA) signals on Server Actions

- Replaying account A's captured POST with account B's cookie →
  `1:E{"digest":"..."}` (500) or `{error:"Server action not found."}` →
  action binding is session-scoped.
- Changing the object id (`propertyId`) inside YOUR OWN session's form →
  `"That property could not be found."` → write is re-scoped server-side.
- UI hiding a button (e.g. no "Delete entry" for a role) is NOT proof the action
  is blocked. For view-only roles, absence of the button + 0 delete-capable
  objects is the expected enforcement; confirm via account export.

## Core technique 4 — Role-confusion false-positive guard

If the tested account holds TWO roles with different privileges (e.g. 50%
co-owner share + contributor adviser), an observed privilege may come from the
OTHER role. Near-miss: combined co-owner+contributor could delete the owner's
entry; after revoking the co-owner share, the PURE contributor had no delete
buttons on owner entries → boundary enforced correctly.

Disambiguation recipe: strip the extra role (revoke share / change role) and
retest as the PURE role. Only a pure-role success is a real finding. Always note
the exact role combination in the evidence.

## Core technique 5 — TOTP self-enrollment to unlock gated flows

Legitimate VDP testing pattern for YOUR OWN test account:
1. MFA setup → authenticator app → submit password → extract base32 secret from
   page text (regex `[A-Z2-7]{20,}`) or QR.
2. RFC 6238: `base64.b32decode(secret + padding)`, `hmac.new(key, pack('>Q', t//30), sha1)`,
   dynamic truncation, `str(val % 10**6).zfill(6)`.
3. Fill the code on the SAME page (NO reload — reload rotates the secret), verify.
4. Reuse TOTP for login MFA, NINO save, role-upgrade code, share-invite code.

Enrollment requiring current password + valid TOTP = good anti-hijack; absence
of either would be a finding.

## Core technique 6 — Param echo vs server enforcement

A query param echoed into UI copy is NOT a control bypass. Observed:
`/reset?codeLimit=1&why=cooldown` changed the top message to "in about 1 seconds"
but the same page showed the server-side resend cooldown ("Send a new code in 58s")
independent of the param — display-echo only. Always verify enforcement by
attempting the disallowed action.

## Core technique 7 — Verification oracle: account export, not UI

For "did the write land / who owns what", read the account export API
(e.g. `/api/account/export` — clients/properties/transactions/NINO). UI "saved"
markers can mislead (e.g. NINO shown filled in UI but export reported
`nino=None` — confirm which is truth). Use export to check for stray/cross-tenant
writes after replay tests.

## Core technique 8 — Import/export injection output paths

Check EVERY output path, not just preview:
- XLSX: sharedStrings (`<si><t>` = literal, safe) vs a real `<f>` formula element
  (= dangerous). Grep `sharedStrings.xml` / `sheet1.xml`.
- Clients CSV: server prepending `'` to `=`-led values = mitigation present.
- Entries page: payloads rendered escaped (`&lt;img...&gt;`) with no `img[src=x]`
  in DOM = stored-XSS safe at that sink.

## Mindset (from user corrections — ignore at your peril)

- "Banyak jalan menuju Roma" — never stop at the obvious surfaces; enumerate
  every feature, every param, both directions of every toggle.
- Exploit-first, not "check what's blocked": ask "how do I make this succeed
  across tenants / without the gate?", then prove or kill the hypothesis.
- Don't declare a target clean after surface tests; document the negative
  evidence per class so a later pass doesn't re-test the same ground.
- No "batas wajar" stopping before all non-destructive surfaces in scope are
  exhausted; the one firm line is: own accounts only, no DoS, no touching other
  users' real data — crossing it invalidates every finding.

## Core technique 9 — Reliable field tampering & re-replay (the silent-no-op traps)

Server-Action forms are React-controlled. Naive `el.value = x; dispatch('input')`
often **submits the OLD value and 200-re-renders** — a silent no-op you can mistake
for "the server rejected my tampered value". Four traps, each with the fix:

1. **React value tracker ignores direct `.value` writes.** Use the native setter:
   `const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
   s.call(el,v); el.dispatchEvent(new Event('input',{bubbles:true}));
   el.dispatchEvent(new Event('change',{bubbles:true}));`
   Or, simplest, `locator.click(); press('Control+a'); type(v)` (real key events).
2. **`<select>` value not in the options becomes `""`.** To test a cross-type /
   out-of-list value you MUST inject it first:
   `if(![...el.options].some(o=>o.value===v)){const o=document.createElement('option');
   o.value=v; o.text=v; el.appendChild(o);} el.value=v; ...`
   Otherwise the action silently stores an *empty* category and you wrongly conclude
   "it accepted my arbitrary value".
3. **`$ACTION_KEY` is per-render.** Replaying a captured multipart body with a stale
   key returns 200 + a full re-render but the action does **not** run (bound args
   fail to decrypt). Always re-fetch the page fields (`$ACTION_KEY`, `$ACTION_n:0/1`)
   immediately before each replay, or drive via the live browser.
4. **Action ids churn on every redeploy.** Ids are build-derived; a mid-engagement
   deploy silently invalidates captured ids (observed: chunk hashes + ids changed
   under us). Re-read the binding from the served page each round; don't cache ids.

Driving tips: `form.evaluate("f=>f.requestSubmit()")` reliably fires
progressive-enhancement forms (bypasses disabled/hit-testing). In-app confirm
dialogs are usually **inline Yes/No buttons**, not `[role=dialog]`:
`get_by_role("button", name="Yes", exact=True)`. Bound actions
(`{"id":...,"bound":"$@1"}`) work through the real form; a hand-rolled multipart
replay of a bound action tends to 500 — drive it, don't hand-roll it.

## Core technique 10 — Two id spaces: bundle reference id ≠ wire id

There are TWO different action ids and confusing them wastes a whole session:

| id space | where it lives | use |
|---|---|---|
| **reference id** | `createServerReference("<id>", callServer, …, "<exportedName>")` in the client bundle | mapping only — posting it as `Next-Action` returns **`404 "Server action not found."`** |
| **wire id** | the value the browser actually sends in `next-action` | the only value the server accepts |

The wire id for JS-invoked actions is **produced per render**: it is NOT in the bundle, NOT in the form
HTML, and NOT in the RSC payload (`RSC: 1` header returned 0 ids of that shape). Verified by collecting
all three in the same minute — the live id matched none of them. So:

- **JS-invoked actions → harvest live.** `page.on("request")`, drive the UI once, log every POST to the
  app origin carrying a `next-action` header, parse the body for `_1_<arg>` names.
- **Form-rendered actions → ids ARE in the HTML** as `name="$ACTION_ID_<id>"` or
  `$ACTION_N:0 value="{"id":"<id>",…}"`. These also replay through the normal form path (see tech 1/9).
- Do not try to "replay by id" from a stale build; ids churn per deploy (tech 9.4).

## Core technique 11 — Inventory the whole backend surface from the bundle

Production Next.js builds keep the exported function name as the 5th argument of
`createServerReference`, so an authenticated crawl of the app pages yields a **complete, named action
inventory** even without source maps:

```python
re.finditer(r'createServerReference\)\("([0-9a-f]{30,48})",\s*[A-Za-z_$][\w$.]*,\s*void 0,'
            r'\s*[A-Za-z_$][\w$.]*,\s*"([^"]+)"\)', js)
```

That is how the audited app's 109 named actions (bsas/accruals/ladr/tla/cis/foreign-annual/loss/
invoice/note/document/attachment/adviser/share/…) were enumerated from just the pages the account can
open. Use it to find surfaces the UI never advertises — then pick the ones that take an object id.
Fetch the bundle with the **authenticated session** and walk every route your account can load.

## Core technique 12 — The definitive authz test: rewrite the id in the live action body

The strongest, least-fragile cross-tenant test does not need the wire id at all:

```
1. Let the REAL UI fire the action (valid wire id, valid $ACTION_KEY, correct arg names).
2. Intercept the request with page.route(); substitute the target object id in the body with a
   FOREIGN tenant's id; continue_ the request with the rewritten body.
3. Read the SERVER'S OWN response (RSC error string) and an independent oracle (export/other session).
4. Pair every "rejected" with a POSITIVE CONTROL: same action, own id → must succeed.
```

Observed responses that prove enforcement (all HTTP 200, error inside the RSC payload):
`That property could not be found.` · `That entry could not be found.` ·
`Only the owner can change these settings.` · `Only the property owner can delete a property.` ·
`That key could not be found.` · `Only the property owner can delete a property.`

Same pattern on the file family: `deleteDocumentAction` (`propertyId` + `documentId`) with a RANDOM
`documentId` **400/200s, re-renders, and the document SURVIVES**; the unpatched control deletes it
(200 → `/api/documents/{id}` 404). So the write is id-validated. Cross-tenant file READ:
`/api/documents/{id}` with the owner session = 200 PDF, with the other tenant's session = 404 — but
check the plan, because a free-tier tenant may not expose the "Add a document" affordance at all,
which makes the reverse direction untestable (say UNTESTED, don't infer).

Traps that silently turn this into a no-op (cost: several wasted rounds):
- **Assert the substitution landed.** Log `id_before` → `id_after` from the patched body. A dict-key
  typo (e.g. `from_` vs `from`) meant the patch never applied and every "rejected" was really an
  *unpatched* run that mutated our own data.
- **`"" in body` is always True.** Guard with `if src and src in body:` — an empty-string source made
  the log claim `patched=True` while nothing was rewritten.
- **A no-op looks like a rejection.** Confirm with an independent oracle (ledger export bytes/rows,
  the other tenant's own session). "The row is still there" proves the foreign write did not land
  *only* if the same action provably works on an owned id.
- Some actions need their own UI path to fire at all (e.g. a destructive button that opens a
  confirmation step and issues no POST from a programmatic `click()`). Treat "no POST captured" as
  UNTESTED, never as "blocked".

## Core technique 13 — Per-action binding asymmetry (same feature, two behaviours)

Within ONE feature, some actions are **bound server-side** at render while others take the id **from
the client**. You must check each action before concluding anything:

| where the id comes from | how to tell | consequence |
|---|---|---|
| **server-bound** | the modal/form carries NO id field (e.g. `Edit note` showed only `body` + `percent`) | client cannot retarget it → no tampering vector to test; the encrypted reference *is* the target |
| **client-supplied** | the fired body contains the id (`_1_noteId`, `_1_invoiceId`, `_1_documentId`, `_1_accessId`, `_1_keyId`) | testable — rewrite it (tech 12) |

Observed in one property's Notes tab: `Edit note` = bound (no id in the modal), while the `Delete note`
confirmation form DID carry `propertyId` + `noteId`. So "the feature is safe because the modal has no id
field" is wrong reasoning — read the body of the *destructive* action, which is where the id appears.

**Prerequisite for a real cross-tenant test: create the SAME object type in BOTH tenants first.** A
random/nonexistent id only proves "unknown id is a no-op" (any sane implementation no-ops) — it does NOT
prove account scoping. The strong test substitutes a *valid id that exists in the other tenant*
(upload/create a note, document, invoice, entry there first). Doing that on the Notes family produced
the cleanest result of the whole engagement: firm session deleting with tenant D's real `noteId` →
no-op, D's note survived, and the unpatched control deleted our own note.

Property-by-property results from that sweep (args + outcomes) are in
`references/notes-invoice-document-family-tests.md`.

## Pitfalls

- **Native value setter is per-prototype.** `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,
  'value').set` throws `TypeError: Illegal invocation` when applied to a `<textarea>` (note bodies,
  addresses, descriptions). Pick by tag:
  `const d = e.tagName === 'TEXTAREA' ? HTMLTextAreaElement : HTMLInputElement;` then take the setter
  from `d.prototype`. A `||`-chained fallback does NOT work — the first descriptor is always truthy, so
  the wrong setter is the one that gets called.
- **Collapsed rows hide every action.** Invoice/entry lists render each row as an accordion button
  (`aria-expanded="false"`); `Download PDF` / `Mark paid` / `Delete invoice` do not exist in the DOM
  until the row is expanded. Click the row first, then look for controls — and don't let a fuzzy
  `/delete|remove|more/i` selector grab the cookie banner's "Learn more" link instead.
- **Stale frozen "action id" in a rewritten runbook** — ids are ephemeral; see tech 9.4.
- **Parse `$ACTION_ID_*` / `$ACTION_N:0` PER `<form>`, never page-wide.** A page-wide regex matched the
  nav/logout form first, so the replay silently invoked **logout** (303 → /login; the session was dead
  and the next "survival check" read a login page). Slice each `<form>…</form>` block first, then read
  its own action fields. Keep a re-login helper in the harness and re-run any test whose session died
  mid-flight.
- **A form that never fires from a programmatic click is UNTESTED, not blocked.** Buttons that open
  their own confirmation step (`Stop advising`, `Delete document`) issue no POST on `element.click()`;
  drive them with a real `locator.click()` plus a follow-up confirm, or use the static bare-name replay
  (tech 1a).
- **The ledger export is the oracle, not the page UI.** A property page renders only the selected
  tax year, so rows written into another year are invisible ("0 entries" on screen, rows present in
  `/api/properties/{id}/export?format=pdf&taxYear=all`). Always verify writes through the export or the
  account export, and parse the PDF text with a regex tolerant of categories/descriptions that contain
  commas, dots and ellipses — a brittle row regex produced three false "0 rows" readings.
- **Pending-review rows are invisible until confirmed.** An imported row whose category is left as
  "Review later" does not appear in the ledger export; that is the mechanism for feeding an
  AI-categorisation queue on purpose (upload a tiny CSV → map `cat-key-*` to "Review later" → import).
- **Attribution rule for throttling.** After heavy volume, a login server-action can hang and return
  `504` (Cloudflare, `retry-after: 120`); a plain retry a few minutes later succeeded. Recording that
  as a finding without a clean-IP control would be a false positive — report only what the retry
  disproves nothing about.
- **Silent no-op ≠ control** — if a tampered submit 200s but the value is unchanged,
  suspect the value never reached React (tech 9.1/9.2) before concluding the server
  rejected it. Confirm the landed value via the read-back oracle (tech 7).
- **Verify the session identity matches the intended account FIRST.** A stored
  session cookie may belong to a different (older/test) account than the API key
  you were handed. Confirm via the account export / `GET /api/v1/me` accountId before
  trusting either; mismatched identity invalidates cross-account conclusions.
- **Read the account's real plan/dashboard before assuming the surface.** The
  "Pro" account here turned out to be a FIRM (multi-client) plan exposing a whole
  `/clients` surface — the single-listing assumption would have missed it.

## Support files
- `references/server-actions-audit-playbook.md` — extended field-prefix examples,
  NINO/MFA retention oracle cases, parameter-echo tables.
- `references/react-field-tampering-and-action-replay.md` — copy-paste snippets for
  the native value setter, `<select>` option injection, `requestSubmit`, inline
  confirm handling, fresh-key replay, and the observed-vs-landed comparison table.
- `references/tenant-boundary-matrix-and-ledger-oracles.md` — the full multi-tenant
  boundary matrix (read paths, export endpoints, header/param tenant overrides, unauth,
  cache-of-authenticated-response, existence-oracle check), the ledger-export oracle,
  the review-queue population recipe, and the cleanup recipe after driving the UI.
- `scripts/tenant_boundary_probe.py` — re-runnable read-only cross-tenant probe: give it
  two tenants' credentials plus a list of object ids and it prints a PASS/LEAK matrix.
- `references/static-form-action-replay.md` — the browserless (bare-name) form replay: exact field
  set per form style, per-form parsing, the 500 signature, and the sweep classification table.
- `scripts/static_form_action_sweep.py` — re-runnable sweeper: walks the app pages, slices each
  `<form>`, replays every id-carrying form unpatched (baseline) and with FOREIGN/RANDOM id values over
  the bare-name format, and prints a per-form PASS/REJECT/UNTESTED table. Skips sensitive forms
  (file/email/password/MFA) and HMRC-submission pages by default.
- `references/notes-invoice-document-family-tests.md` — per-family action/argument map (notes,
  documents, invoices), binding asymmetry (bound vs client-supplied id in the same feature), the
  real-foreign-id test results, UI mechanics (per-prototype setter, "Yes, delete", collapsed invoice
  rows) and the cleanup oracles.

## Reporting shape the owner expects (user preference)

Execute the whole sweep first, then report **findings + impact** — not a menu of options, and not a
mid-run "which one should I do?" question. When nothing exploitable exists, say so plainly and separate
three buckets: (a) exploitable findings, (b) correctness/functional defects with user-facing impact,
(c) informational observations that cannot be exploited. State explicitly what was NOT testable and why
(no second firm, free tier lacking an affordance, UI flow that never fires) instead of implying
coverage. Keep the per-family test list so a later pass doesn't re-walk the same ground.