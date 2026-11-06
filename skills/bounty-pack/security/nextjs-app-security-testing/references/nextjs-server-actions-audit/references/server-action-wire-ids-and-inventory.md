# Server-action wire ids vs bundle ids, and the full action inventory

Session: quarterwise.co.uk, 2026-10-01 (firm/Pro session, own test tenants). Everything here is
from reading the app's own served bundle and the browser's own requests.

## Two id spaces — the trap that wastes a pass

| Id | Where it lives | Can you POST with it? |
|---|---|---|
| `createServerReference("608ea244…", …)` hex | client chunks (`_next/static/chunks/**`) | **No.** `next-action: <that id>` → `404`, body `Server action not found.` (24 bytes) |
| `next-action:` header value | produced per render, seen only on the wire | Yes — but it must be harvested live |
| `$ACTION_N:0` = `{"id":"<41 hex>","bound":"$@1"}` | server-rendered HTML hidden fields | Yes — via the `_N_$ACTION_*` multipart form replay |

Verified on the same page load: `/app/year-end` fired
`next-action: 60dd7e2aca7bad3a5d61e22135457a37d95a277b88`, while the bundle's reference for that
action is `608ea2447e785621cecc8e9c22d7a37d05d1c9e004`. Posting the reference id returned
`404 "Server action not found."` for every action/shape combination tried (54 probes) — that 404 is
the wrong-id-space signature, not a dead route.

Consequence for planning: you can enumerate the surface offline (bundle), but replaying
**client-invoked** actions needs a live harvest. **Form-bound** actions (their hidden
`$ACTION_*` fields are rendered into the HTML) replay offline with `requests` — that is what makes
the HTTP-only write tests possible. Decide which kind you have by grepping the rendered HTML for
`$ACTION_` before assuming a browser is required.

## Harvest shape for a client-invoked action (captured live)

```
POST /app/year-end
next-action: 60dd7e2aca7bad3a5d61e22135457a37d95a277b88
next-router-state-tree: %5B%22%22%2C%7B%22children%22%3A%5B%22app%22%2C…%5D%7D%2Cnull%2Cnull%2Ctrue%5D
accept: text/x-component
content-type: multipart/form-data; boundary=----WebKitFormBoundary…

_1_taxYear   2026-27
_1_fph       {"deviceId":"…","timezone":"Asia/Bangkok","timezoneOffset":"UTC+07:00", …}
0            [{}, "$K1"]
```

Note the arg fields are `_1_<parameterName>`, not `_3_<param>` — the index tracks the action's
form index on that page, and for a client-invoked call it lands at `_1_`.

## Inventory scale (why this grep matters)

`createServerReference("<hex>", callServer, void 0, findSourceMapURL, "<name>")` keeps the **exported
function name in production**. Quarterwise's shipped bundle: **109 named actions + 5 unnamed**.
Names are a backend map the UI never shows. Subsystems that surfaced with no visible entry point on
the tested plan:

`bsasViewAction/TriggerAction/AdjustAction` · `accrualsSaveAction/SubmitAction` ·
`periodsOfAccountViewAction/SubmitAction` · `ladrViewAction/DisapplyAction/WithdrawAction` ·
`tlaViewAction/SubmitAction/DeleteAction` · `cisViewAction/CreateAction/DeleteAction` ·
`foreignAnnualViewAction/SubmitAction/DeleteAction`, `submitForeignQuarterAction`,
`checkForeignHeldAction` · `lossViewAction/SubmitAction/DeleteAction` ·
`aiViewAction` (the review-queue feed) · `listAccountsAction` / `listBenefitsAction` /
`listEmploymentsAction` / `listCalculationsAction` · `amendPrepareAction` / `amendReturnAction` ·
`bissSummaryAction` · `partnerIncomeViewAction` · `viewBusinessDetailsAction` ·
invoices (`create/mark paid/mark unpaid/delete/updateInvoiceSettings`) ·
notes / reminders / documents / attachments · `signOutOtherSessions`, `disableMfa`, `removeSms`,
`sendAccountSmsCode`, `cancelEmailChange`, `deleteMyAccount`, `changePassword`, `updateProfile` ·
HMRC submit family: `submitQuarterAction`, `submitAnnualAction`, `submitSeQuarterAction`,
`submitForeignQuarterAction`, `finalDeclarationAction`, `refreshHmrcStatusAction`,
`refreshObligationsAction`, `checkHeldCumulativeAction`, `checkSeHeldAction`,
`checkFinalObligationAction` — **never invoke these** (hard rule for regulated-filing targets);
state the exclusion explicitly in the write-up.

Save `{id: [name, chunk]}` as JSON evidence. It converts "I tested the buttons I could see" into a
defensible surface statement.

## What this let us test, and one honest gap

- Three write actions against a view-only shared property, with explicit error strings
  (see the "zero-risk oracles" section of SKILL.md) — all refused at the ownership gate.
- **Not tested: the review-queue `Confirm` action.** `/app/review` was empty
  ("Nothing to review — you're all caught up."). Populating it requires committing a pending import
  (the import batches sit in preview state, e.g. rows `uk / ambig / bad / 45000 serial`), which
  writes ledger rows into the vendor's live property. That was judged not worth the residue and was
  reported as a coverage gap instead. If you do take it on: `commitImportAction` then
  `undoImportAction` is the intended revert path, and `aiViewAction` is the queue's read action.
