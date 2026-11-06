# Rails / Devise app recon + sequential-ID IDOR semantics

Measured 2026-10-31 on ConferenceBadge (`dash.conferencebadge.com`, Rails + Devise + Cloudflare).
Two reusable pieces: minting an account on a Rails signup page whose submit control is not a
`type=submit`, and reading a sequential-ID IDOR probe correctly.

## Fingerprint a Rails/Devise app in one pass

```
/                    301 -> /events
/users/sign_in       200   (Devise)
/users/sign_up       200   (Devise)
/users/edit          200   (authenticated profile, `_method=put` on /users)
/users/sign_out      302
/password/new        404   (Devise not mounted at the default path)
```

Tells:
- `authenticity_token` hidden inputs = Rails CSRF. **Every** form on the page carries its own
  token (the currency-switcher forms, the signup form) — grab the one inside the form you are
  submitting, not `tokens[0]`.
- `_conference_badge_session` cookie = Rails session store.
- `robots.txt` `Disallow:` list is a free route map. On this target it named `/admin/`,
  `/account/`, `/settings/`, `/events/`, `/api/`, `/iframe`, `/3xc3pt10n` — most 404'd, but
  the naming pattern (`/events/<id>/<sub>`) came straight from it.
- `security.txt` on the **app** host, not just the marketing host
  (`dash.<host>/.well-known/security.txt`), is where the real contact lives.

## The submit button is not `type=submit` — three fallbacks, in order

`page.click("input[type=submit], button[type=submit]")` **timed out** (30 s) on the Devise
signup form even though the button rendered. The form's real submit is a plain
`<button>` with the label "Sign up" and no `type` attribute.

```python
# 1. click by visible text
await pg.click("text=Sign up")

# 2. if that misses (matches a heading/other node), submit the form that owns the field
await pg.evaluate("""() => {
    for (const f of document.querySelectorAll('form')) {
        if (f.querySelector("input[name='user[email]']")) {
            const b = Array.from(f.querySelectorAll('button,input[type=submit]'))
                       .find(x => (x.innerText||x.value||'').toLowerCase().includes('sign up'));
            if (b) { b.click(); return 'clicked'; }
            f.requestSubmit ? f.requestSubmit() : f.submit();
            return 'submitted';
        }
    }
    return 'noform';
}""")

# 3. last resort — enumerate every button and read its identity
await pg.evaluate("""() => Array.from(document.querySelectorAll('button'))
    .map(b => [b.id, b.className, b.textContent.trim().slice(0,30)])""")
```

**Diagnose before retrying blindly.** Enumerate the forms first — the page had FOUR
(`/currency/USD`, `/currency/GBP`, `/currency/CAD`, `/users`). The signup form is the one whose
`action` is `/users` and which contains `user[email]`. Clicking the wrong one is silent.

**Judge success by the redirect, not the page.** The signup POST returns `302` to `/events`;
the page body still shows the signup form markup for a moment after a failed attempt. Read
`page.url` after a 10 s settle — `https://dash.<host>/events` = account created.

**No email verification on this target.** Account was usable immediately after the 302. Do not
assume a verification gate exists; check by navigating to an authed route.

## Sequential IDs are a lead, not a finding — read the status semantics

Events were `/events/<id>` with **sequential** numeric ids (account A → `180015`, account B →
`180016`). That is the classic IDOR shape, and it is worth testing — but the *status code*
decides whether there is an oracle at all:

| Probe | Result | Meaning |
|---|---|---|
| my own id, `/` | `302` → `/editor` | correct |
| my own id, `/editor` | `200` | correct |
| foreign id, any sub-resource | `404` | **scoped to owner** |
| foreign id, `/` | `404` | scoped |

**`404` (not `403`) for a foreign object is the GOOD outcome** — it means the lookup is scoped
by owner in the query, so there is no existence oracle: an attacker cannot distinguish
"someone else's event" from "no such event". Record it as a verified control, and record the
`A→A = 200` control row alongside it. A `403` here would actually be *weaker* (it confirms the
object exists).

Sub-resources to sweep on a Rails dashboard app (all 404'd for the foreign id):
`/`, `/editor`, `/preview`, `/checkout`, `/copy`, `/badge_types`, `/shipping`,
`/documents/sheet_format`, `/sheet_format`.

**Do not scan a wide id range to "find other users' ids".** Probing `180010..180021` returned
`404` for everything except my own id — which is ambiguous (the ids may not be globally
sequential, or the range may simply be empty). The clean proof is always the **two-account**
test: create the record on account B, then read it with account A's session. The range scan
adds noise and no evidence.

## File-upload validation: check whether it is header-only or a real parse

The custom-font upload (`POST /api/internal/custom_fonts`, `ttf/otf/woff`, 5 MB, 50 fonts,
client-side ext check only) rejected everything — including a well-formed minimal TTF — with
`422 {"error":"That doesn't look like a font file…"}`.

Probe ladder (all returned 422 here, i.e. genuinely safe):
`wOFF` magic + padding · PHP content renamed `.woff` · SVG renamed `.woff` · HTML renamed
`.woff` · `../../../../tmp/evil.woff` · `evil.php.woff` · `evil.woff\x00.php` · `.php` with an
`application/x-php` type · a hand-built minimal sfnt TTF (30 bytes, `00010000` + one `cmap`
record).

**A minimal-but-valid file being rejected is the signal that validation is a real parse, not a
magic-byte check** — that is the strongest form of the negative. If the minimal file had been
*accepted*, the next step is a polyglot (valid font + appended payload) to test what the
storage/retrieval path does with the tail.

## Rails error pages: confirm they are generic before calling 500 "info disclosure"

`POST /api/internal/custom_fonts/dismiss_banner` (a GET-only endpoint) returned `500` for every
body. The rendered error page was the app's own branded "Your request could not be completed"
template — no backtrace, no `/app/` paths, no `NoMethodError`. Grep the response for
`/app/`, `.rb:`, `backtrace`, `ActiveRecord`, `NoMethodError` before claiming a 500 leaks
anything; a generic 500 with no differential across payloads is a hardening note at most.

## The real endpoint map lives in `window.<APP> = {…}` (Rails dashboard state), not in generic paths

Minified Rails dashboard bundles hide routes in template literals (`${t}/${e}`) and, crucially,
the EDITOR/page shell injects a server-built state object into an inline `<script>`:

```
window.CB = {}
CB.HEADER_DATA    = {"newEventPath":"/events/import/spreadsheet", …}   // route map
CB.SAVE_PATH      = '/events/180015/badge_types/:id'                    // dynamic route template
CB.ATTENDEES      = [{"id":77318528,"data":{},"full_name":"Bob Jones"}, …]
CB.ATTENDEES_DATA_KEYS = [{"key":"full_name",…},{"key":"company",…}]    // the exact JSON-column schema
CB.EVENT_ID       = 180015
CB.CURRENT_USER_ID = 135364
CB.IMG_PATH       = 'https://conference-badge.s3.us-east-1.amazonaws.com'  // object storage host
CB.LEAD_RETRIEVAL = false                                               // feature flag: gate ON/OFF
CB.PRICES         = {printed_cardboard_badges_425x370:"2.19", …}        // client-side price map
```

`grep` the shell for `window.<APP>` / `<APP>.<X> =` (not just the bundle) before probing generic
`/api/users/1` tebakan. On this target the generic probes all 404'd while the real surface was
`PATCH /events/<id>/attendees/<attendee_id>`, `POST /images.json`, `POST
/api/internal/custom_fonts`, `POST /api/internal/organization_colors`. The `CB.*` literals *are*
the route + schema + storage map — grep them, don't guess. (This is the Rails-dashboard sibling
of the `window.__NUXT__` / `window.app` / `window.__APOLLO_STATE__` config extraction in
`hunt-spa-api`.)

## Object storage: public bucket + unguessable key = by-design, NOT exposure

`POST /images.json` returned `{"filename":"<64-hex-sha256>.png"}` and the object was served from
`https://conference-badge.s3.us-east-1.amazonaws.com/images/<key>` with **`200` + NO cookie**.
That looks like unauthenticated data exposure — and it is, but it is the standard pattern:

- Bucket **root** `/` → `403 AccessDenied` (no directory listing) = correct.
- Individual object → public read, but the key is a **64-char SHA-256 hex** (192+ bits entropy),
  so it is functionally a permanent capability URL, equivalent to a signed URL.

Verdict: **by-design, not a finding.** The triage question is key entropy, not "is the object
public". Only report it if (a) the bucket lists (`/` → 200 `<ListBucketResult>`), or (b) the key
is predictable/sequential/guessable (then it's an enumeration→PII leak), or (c) the object holds
PII written by *another* tenant and you can derive its key.

## Record mass-assignment: JSON column vs top-level columns respond differently

`PATCH /events/<id>/attendees/<attendee_id>` accepted a **`data` JSON column** whose value is
fully overwritten (not merged) server-side, while **top-level scalar columns** (`attendable_id`,
`printed_at`, `fake`, `provider_id`) answered **`400`**. That split is the discrimination recipe:

- A flexible JSON/`data` column that replaces itself = by-design (the schema key names come from
  `CB.ATTENDEES_DATA_KEYS`); mutate only your own record and it is not a finding.
- A top-level ownership/state column (`attendable_id`, `printed_at`) that you can set is the real
  mass-assignment primitive — test it explicitly and record the 400 as a verified control.

## Stored-XSS negative signature: JSON `\u003c` escape + Title-Case normalize

Injecting `<img src=x onerror=alert(1)>` / `</script><script>…` into a persisted text field
returned, on re-read, a value where `<` and `>` are **JSON/JS unicode-escaped** and the whole
string is **Title-Cased** by the server:

```
"full_name":"Xss\u003c/Script\u003e\u003cScript\u003eAlert(...)\u003c/Script\u003e"
```

Two independent negative signals: (1) no literal `</script>` byte ever reaches the HTML (it is a
valid JS string literal), and (2) the server normalises case so known payloads lose their exact
shape. Grep the *raw* `CB.ATTENDEES`/state blob for `\u003c` — that is the escape proof. A
Title-Case-only (no escape) reflection is NOT safe by itself; look for both, or re-test with a
case-preserving payload before declaring XSS closed.

## CSV import is a multi-step `importer_spreadsheet_base` wizard — the 500 is generic, not a finding

The import surface is `POST /events/import/spreadsheet/validate` (multipart), field prefix
`importer_spreadsheet_base[...]` (`[file]`, `[title]`, `[lead_retrieval]`, date parts
`[start_date(1i)]`…), with a JS poll loop on `data-status-url` → `IMPORTED|FAILED`. A clean minimal
CSV still returned `500` (multi-step: the record/event must be established first), and the 500 was
the branded generic page, not a stack trace. Formula/DDE injection (`=cmd`, `@SUM`, `HYPERLINK`)
cannot be validated end-to-end until the import *commits* AND the victim *exports+opens* — a 500 at
the validate step proves nothing. Don't claim CSV-injection positive or negative without reaching
the export step.

## Lead-retrieval scan is a feature-gated public-PII QR endpoint — check the flag first

`CB.LEAD_RETRIEVAL=false` named the ticket before any request: the scan surface is
`https://<event-slug>.conferencebadge.com/scan?attendee_email=<email>` (used placeholders:
`your-event`, `sample@example.com`). It is **feature-gated per event** and a paid flow
(`/lead-retrieval/pre-purchase`), so it is untestable on a free/PURCHASED:false account. Record the
flag read (`CB.LEAD_RETRIEVAL` / `CB.PURCHASED`) as the evidence for why the PII scan surface is a
coverage *gap*, not a tested-negative.
