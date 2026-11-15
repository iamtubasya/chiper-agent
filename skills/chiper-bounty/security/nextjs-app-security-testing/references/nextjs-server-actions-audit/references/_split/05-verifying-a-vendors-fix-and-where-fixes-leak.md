## Verifying a vendor's fix — and where fixes leak

When a vendor replies "confirmed and fixed", the follow-up is often worth more than the
original report (and gets credited). Test the SAME invariant on every path that reaches
the same data — **create, edit, delete, import** — not just the path they named.

Observed on Quarterwise (2026-09), after the vendor fixed a category/amount coupling on
create: the *category* check held on add AND edit (`Choose a valid category.`), and the
amount relation held on create even against a tampered body — but the relation was not
re-enforced on edit, and deleting the parent record orphaned the dependent one.

```
add     : withheld > rent            -> REFUSED (client + server)
tamper  : rewrite body mid-flight    -> REFUSED (server authoritative)
edit cat: ordinary entry -> hidden key-> REFUSED (server)
edit amt: withheld 10 -> 500 (rent 200)-> ACCEPTED  <-- leak
edit amt: rent 200 -> 5 (withheld 500)-> ACCEPTED  <-- leak
delete  : delete rent entry          -> withheld SURVIVES (orphan)  <-- leak
```

Method notes that made this fast and defensible:

- **Tamper a Server Action in flight with Playwright `page.route`.** `request.post_data` is
  often `None` for multipart — use `request.post_data_buffer` (bytes) and
  `route.continue_(post_data=<bytes>)`. The multipart line separator nested in a body is
  NOT plain `\r\n` once decoded; a strict string replace silently no-ops. Use a bytes
  regex and REFUSE to continue quietly, e.g.
  `re.compile(rb'(name="_?1?_?taxDeducted"\r*\n\r*\n)([^\r\n]*)')` and log
  `repr(raw[i-20:i+90])` when it does not match. Always assert the substitution count and
  print it — "tamper applied: False" is a result, not a failure to hide.
- **A re-rendered form with the error message after a tampered submit = server-side
  check.** If the client value was the benign one (100 < 500) and the tampered value
  (5000 > 500) produces the relation error, the client cannot have produced it.
- **Ground truth = the app's own export, fetched with the session cookie** (`curl -H
  "Cookie: qw_session=..." .../export?format=xlsx` then `openpyxl`). Faster and more
  reliable than clicking an export button with `expect_download`, and immune to
  pagination — the UI listed only the 7 newest entries while the books held 27.
- **Entry lists are often paginated/truncated** (only N newest rows rendered). Do not
  conclude "the row does not exist" from the DOM; check the export. Use a RECENT date for
  injected test rows so the UI still shows them for click-driven tests.
- Edit forms re-expose fields the create form hides: the withheld entry's edit form
  carried `category=taxDeducted` in a `<select>` plus a plain `amount` input, and the
  hidden `txnId`. Enumerate `input[name]`/`select[name]` on the edit form before assuming
  a value is immutable.
- Delete affordances are usually `button[aria-label="Delete entry"]` with the id bound in
  encrypted React props (not readable from the DOM) — click-based targeting works: walk up
  from the button until the ancestor's `innerText` matches and contains exactly ONE delete
  button, then click that (avoids hitting the first row of a month group).

### Enumerate EVERY write path before believing "it's fixed"

The vendor's sentence "now refused when adding or editing an entry" describes two paths.
On a later pass the same invariant leaked through five:

| Path | Where to look |
|---|---|
| create (form) | the Record-income action |
| edit | the per-row **edit form** — it re-exposes fields the create form hides; dump `input[name]`/`select[name]` and you may find the forbidden value sitting in a `<select>` |
| delete | delete the parent and check whether the child row survives (orphan) |
| **file import** | the column-mapping screen renders one `<select name="cat-key-<row>">` per CSV row whose options are the full category list — a forbidden value offered as a dropdown is a finding, and import is often a FREE feature |
| **REST API** | the public write endpoint takes the same field as a plain string; a whitelist that *runs* (`422 invalid_category` for genuinely bad values) can still contain the forbidden key |

Test the control that proves the validator is alive (`premisesRunningCosts`, a bogus key →
`422`) so "it accepted ours" is not mistaken for "validation is off".

### UI-automation pitfalls that cost real time

- **Destructive confirmations may not exist.** After clicking "Revoke", a loose confirm
  matcher `/^(yes|confirm|revoke)$/i` matched the *next row's* Revoke button and revoked two
  API keys at once. Scope destructive clicks to the row (match the row's own text, require
  the ancestor to contain exactly one action button) and treat "no confirm dialog" as the
  normal case. Record the accidental action if it happens; it may even prove a control works.
- **Typed-name confirmations**: `Delete this property permanently` needs the name typed into
  `#confirmName` first — read the target name from that input's `placeholder` rather than hard-coding it.
- **A required dropdown built from base-ui / Radix is NOT a native `<select>` — setting `.value` does
  nothing.** These render as `button[role=combobox]` + a portalled `[role=option]` list, so filling the
  text fields and assigning `.value` to the "select" leaves it unset; the app's own client validation then
  blocks submit **silently** — zero POST, no console error, the form looks complete. Symptom seen on a
  Next.js "Add a trial" dialog: name/protocol fields set fine, but the required "Which CTCAE publication it
  grades to" combo stayed empty → validation text appeared and no request fired. Fix: `click()` the
  combobox, wait ~1s, then `click()` the desired `[role=option]`; **re-query `[role=combobox]` on every
  iteration** because the node list shifts as each selection lands (indexing a stale handle picks the wrong
  control). Before concluding a create/edit form "doesn't work", dump
  `[...document.querySelectorAll('[role=combobox]')]`, click one, and print the `[role=option]` texts that
  appear — that separates a harness gap from a server-side refusal. A form that emits ZERO network requests
  is a harness/validation problem, never a finding.
- **VDP that allows self-serve signup: read the OTP from the operator's OWN Gmail, not a disposable inbox.**
  When the in-scope app's `/auth/sign-up` is open and the host has the operator's `google_token.json` wired
  (the google-workspace skill), register with the operator's real address and pull the emailed code with
  `google_api.py gmail search "from:<vendor> newer_than:5m"` — the operator authorises this and it avoids a
  throwaway mailbox the vendor may flag. Poll in a loop (the mail can take 10–40 s) and regex the numeric
  code out of the search output. The sign-up form may ship an 8-cell segmented OTP input: **type the code
  with `keyboard.type(code, delay=90)` after focusing the first box** (assigning the full string to one box
  stores only its first char), then submit via `form.requestSubmit()` — a plain button `.click()` was
  intercepted by the field label on this stack.
  hard-coding it.
- **Tolerant label matching** for buttons that change with account state:
  `/add\s+(an?\s+)?(your first\s+)?income source/i` matched both "Add an income source" and
  "Add your first income source"; exact-string matching failed after the first object existed.
- **Multi-stage flows**: the import wizard is mapping → listing (which property) → preview →
  commit, with buttons `Apply mapping & continue`, `Continue to preview`,
  `Import these transactions`. Drive it as a loop that clicks whichever of those is present
  (max ~4 rounds); stopping after the first click silently leaves the import uncommitted and
  produces a "no data written" false negative.
- **Import defaults create resources**: if the "listing" select is left alone, the importer
  creates a NEW property (named after the file) instead of using the one you targeted —
  hence "0 new entries on the source I tested" when the rows landed elsewhere. Always set the
  listing select explicitly and verify with the API/export afterwards.
- **Run volume and destructive tests in a throwaway resource** you can delete (a second
  property/tenant), then delete it — especially on a vendor-granted account. See
  `saas-vdp-engagement-playbook` §4h.
- **Destructive UI actions usually have NO confirm dialog.** Revoking an API key, deleting
  an entry, etc. can fire on the first click. A generic "click the confirm/yes/revoke button"
  step therefore lands on the NEXT row's button after the list re-renders, and you silently
  destroy a second object. Scope every destructive click to a single row container
  (find the ancestor whose text matches the target AND that contains exactly one such
  button) and assert the row text you clicked. Symptom seen: after "revoking one key",
  every key in the account returned `401 invalid_key` — the harness had revoked both.
  Treat this as a harness bug and verify afterwards with an explicit before/after list.

### Enumerate EVERY write path before believing an invariant holds

A UI-level guard is not a system invariant. When a vendor says "X is now refused", find all
the ways the same data can be written, and test the invariant on each:

```
form add  | form edit | form delete | bulk file import | public/REST API
```

Observed on the same target, for one rule ("this category must be tied to a parent entry"):

- form add / form edit -> correctly refused (server-side, `Choose a valid category.`)
- form delete -> parent removed, dependent row ORPHANED and still counted in totals
- **CSV import mapping UI** -> the excluded category is present in the per-row dropdown
  (`select[name="cat-key-<n>"]`, options like `taxDeducted | Income: Tax withheld from rent`),
  no parent linkage, no equivalent of the "field beside the entry" → wrote a standalone row
  **on the FREE plan** (imports are often free-by-design, so the bypass is not Pro-gated)
- **REST API** -> a category the UI forbids is still in the server's whitelist for that
  source type: `POST /api/v1/...` returned `201 created`, and the canonical export carried it

Then confirm the validator is genuinely running with negative controls (`premisesRunningCosts`,
`seTotallyFake` → `422 invalid_category`). "422 for junk keys" + "201 for the hidden key"
is far stronger evidence than the 201 alone: it shows a whitelist exists and the hidden key
is *in* it, i.e. the UI is stricter than the API — an inconsistency, not a design choice.

### Reporting hygiene specific to this class

- **Do not report bearer-token whitespace trimming.** `" <key> "` returning 200 is header
  normalisation, not a vulnerability. Log it as INFO and move on.
- **Do not report "no rate limit" from a bot-UA burst alone.** A high-volume burst from a
  script gets a blunt CDN-level block (Cloudflare `Error 1010 Access denied`) that then hits
  *all* API traffic from that IP — including the account holder's legitimate use — and
  expires on its own. Re-test with a browser-like User-Agent and pacing, and describe the
  distinction honestly: documented per-key `429` not enforced *and* a blunt edge block
  instead. If a request starts failing with an HTML/JSON CDN error page after a burst,
  that is your own footprint, not a finding.
- **XSS payloads stored via API are usually escaped, not rendered.** Confirm by DOM
  inspection (look for a real injected element and hook `alert`/`error`), never by grepping
  page HTML — RSC flight data embeds payload strings inside `<script>self.__next_f.push(...)`
  and produces false positives. Check the export paths separately: text-typed XLSX cells and
  PDF that drops the description are fine; only an executable sink counts.

