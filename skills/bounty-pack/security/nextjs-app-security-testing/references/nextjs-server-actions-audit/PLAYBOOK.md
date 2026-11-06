---
name: nextjs-server-actions-audit
description: "Use when auditing Next.js Server Actions authed flows."
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [nextjs, server-actions, rsc, bug-bounty, authz, csrf, race]
---

## ⛔ KONTRAK INTEGRASI (WAJIB DIBACA SEBELUM PAKAI SKILL INI)

Isi skill ini **dipecah**: core ada di file ini (auto-load), sisanya di `references/_split/`.
File di `references/` **TIDAK ikut ter-load otomatis** — hanya ter-LIST saat skill dibuka.
**Karena itu: buka file di tabel bawah ini lewat `skill_view(name=..., file_path=...)`
sebelum mengerjakan bagian yang relevan. Jangan menebak dari judulnya.**

Aturan pakai:
- Bagian CORE di bawah = aturan wajib, selalu berlaku, jangan dilewati.
- Bagian yang dipisah = kedalaman per-topik. **Panggil saat pemicunya muncul, jangan dibiarkan tak terpakai.**
- Kalau ragu bagian mana yang relevan, baca `references/_split/_INDEX.md` dulu (satu file, murah).

### Tabel pemicu → file (WAJIB dipanggil saat kondisi terpenuhi)

| kapan dipanggil | file |
|---|---|
| saat mengerjakan: **Testing a destructive write WITHOUT changing anything — three or** | `references/_split/01-testing-a-destructive-write-without-changing-anything-thre.md` |
| saat mengerjakan: **OTP / MFA lockout matrix (account-level vs session-level)** | `references/_split/02-otp-mfa-lockout-matrix-account-level-vs-session-level.md` |
| saat mengerjakan: **Two-factor / TOTP surface — the full matrix worth running** | `references/_split/03-two-factor-totp-surface-the-full-matrix-worth-running.md` |
| saat mengerjakan: **Missing-idempotency race (duplicate submit)** | `references/_split/04-missing-idempotency-race-duplicate-submit.md` |
| saat mengerjakan: **Verifying a vendor's fix — and where fixes leak** | `references/_split/05-verifying-a-vendors-fix-and-where-fixes-leak.md` |
| saat mengerjakan: **Shared-book authz: co-owner vs view-only adviser (API surface)** | `references/_split/06-shared-book-authz-co-owner-vs-view-only-adviser-api-surfac.md` |
| saat mengerjakan: **Rewriting the target id in flight — the cross-tenant WRITE matri** | `references/_split/07-rewriting-the-target-id-in-flight-the-cross-tenant-write-m.md` |
| saat mengerjakan: **Cross-tenant data-access pass — "can I read someone else's ledge** | `references/_split/08-cross-tenant-data-access-pass-can-i-read-someone-elses-led.md` |
| saat mengerjakan: **Rate-limit headers that are not enforced** | `references/_split/09-rate-limit-headers-that-are-not-enforced.md` |
| saat mengerjakan: **React controlled selects: when a control test also fails, STOP a** | `references/_split/10-react-controlled-selects-when-a-control-test-also-fails-st.md` |
| saat mengerjakan: **Route handlers hidden behind a feature flag — create the entity ** | `references/_split/11-route-handlers-hidden-behind-a-feature-flag-create-the-ent.md` |
| saat mengerjakan: **Sweep a parameter over boundaries, not just one bad value** | `references/_split/12-sweep-a-parameter-over-boundaries-not-just-one-bad-value.md` |
| saat mengerjakan: **Authenticated crawl → route-handler inventory (cheapest source o** | `references/_split/13-authenticated-crawl-route-handler-inventory-cheapest-sourc.md` |
| saat mengerjakan: **AI/extraction endpoints: mass-assignment first, injection second** | `references/_split/14-aiextraction-endpoints-mass-assignment-first-injection-sec.md` |
| saat mengerjakan: **Deleting leftover test rows: the tax-year filter hides half of t** | `references/_split/15-deleting-leftover-test-rows-the-tax-year-filter-hides-half.md` |
| saat mengerjakan: **App navigation and side effects that burn a session** | `references/_split/16-app-navigation-and-side-effects-that-burn-a-session.md` |
| saat mengerjakan: **JS-in-Python string pitfalls (each one costs a debug cycle)** | `references/_split/17-js-in-python-string-pitfalls-each-one-costs-a-debug-cycle.md` |
| saat mengerjakan: **Second-factor (MFA) surface — the matrix that mostly finds contr** | `references/_split/18-second-factor-mfa-surface-the-matrix-that-mostly-finds-con.md` |
| saat mengerjakan: **Reading TOTP secrets in a harness (avoid the masking trap)** | `references/_split/19-reading-totp-secrets-in-a-harness-avoid-the-masking-trap.md` |
| saat mengerjakan: **Destructive buttons that never POST: accept JS dialogs first** | `references/_split/20-destructive-buttons-that-never-post-accept-js-dialogs-firs.md` |
| saat mengerjakan: **Verification discipline** | `references/_split/21-verification-discipline.md` |
| saat mengerjakan: **Email / disclosure delivery (user rules)** | `references/_split/22-email-disclosure-delivery-user-rules.md` |
| saat mengerjakan: **References** | `references/_split/23-references.md` |
| butuh daftar lengkap split / arsip | `references/_split/_INDEX.md`, `references/_split/_full-archive.md` |


# Next.js Server Actions — AuthZ / CSRF / Business-Logic Audit

Working methodology for testing Next.js apps (App Router + Server Actions) where the
"signed-in app" is the scope. Built from a full VDP engagement against an MTD/tax
app (quarterwise.co.uk, 2026-09). All testing on own accounts.



## Why this class needs its own playbook

Server Actions are NOT normal REST endpoints. Requests are multipart/form-data POSTs to
the *page* URL with hidden `$ACTION_*` fields, an `next-action` header, `Accept:
text/x-component`, and RSC flight responses. Classical curl testing gives 500s that are
construction failures, not server authz. Replays, CSRF tests, and cross-role tests all
need the exact captured body.



## Setup that makes this work

- **Two Chrome profiles via CDP** for cross-tenant cookie isolation:
  `chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=...`
  (and :9223 with a second profile). Plain `websocket-client` connects with
  `header=["Origin: http://localhost"]`. Account A in profile 1, account B in profile 2.
  Only profile-redirection (not tabs) isolates cookies.
- **Camofox equivalent (no CDP):** `POST localhost:9377/tabs/open` with a DIFFERENT
  `userId` per account (`{"userId":"hermes"}` = account A, `{"userId":"hermes2"}` =
  account B) → each userId gets its own browser profile and **isolated cookies**.
  Verify before trusting it: log in as A, then check B's snapshot still shows the
  logged-OUT header. **`sessionKey` does NOT isolate** — tabs opened with different
  `sessionKey` values shared one cookie jar in testing (justify `userId` instead).
  Tabs are reaped after 300s idle, so chain open → sleep → act in one call. File upload
  requires an ABSOLUTE path inside `~/.camofox/uploads` (relative → `invalid_upload_path`,
  outside root → `upload_path_outside_root`).
- **mail.tm** as disposable inbox (own addresses): create account, poll
  `GET /api/mail.tm/messages` with bearer token; regex the 6-digit codes / invite token
  out of `text`. Needed for signup OTP, reset OTP, adviser/co-owner invite tokens,
  and reset-link host-poisoning checks (email to SELF — allowed under most VDPs).
- **TOTP**: if the app lets you enroll an authenticator app, extract the base32 secret
  from the DOM and generate codes with RFC 6238 in Python (never paste from phone).



## Capturing a real Server Action

**Finding the action IDs in the first place (App Router).** IDs are not in the HTML — no
`"action":"<hex>"` exists. They live in the client chunks as
`createServerReference("<40+ hex>", callServer, void 0, findSourceMapURL, "<name>")`, and
chunk files carry backslash-escaped quotes, so `grep -o '\"hash\"'` misses them. Use
character-class regexes and zip names↔ids **in file order**:

```bash
grep -oE 'createServerReference\(\\?"([0-9a-f]{40,})' chunk.js   # ids, in order
grep -oE 'findSourceMapURL,\\?"([A-Za-z0-9_]+)\\?"' chunk.js     # names, in order
```

Dedupe ids preserving order, then zip with the name list — positional pairing is how you
recover "which action does what" (`cancelMfaDisable`, `finalDeclarationAction`, …).

**The names survive into PRODUCTION, so this grep is a full surface map — treat it as a
deliverable, not just a lookup.** On Quarterwise the shipped bundle yielded **109 named actions
+ 5 unnamed**, revealing whole subsystems the UI never showed that account: `bsas*` (3),
`accruals*` (2), `periodsOfAccount*` (2), `ladr*` (3), `tla*` (3), `cis*` (3), foreign
annual/quarter (5), `loss*`, `aiViewAction`, `list*`, `amend*`, invoices, reminders, notes,
documents, attachments, sessions/MFA/SMS/profile, and the HMRC-submit family
(`submitQuarter|Annual|Se|Foreign*`, `finalDeclarationAction` — never invoke these; state the
exclusion). Save the id→name JSON as evidence; it turns "I tested the buttons I could see" into
"here is the whole backend surface and which parts were exercised".

Prioritise by name family when you cannot test 109 actions: `delete*` · `update*` ·
`commitImportAction` / `saveMappingAction` / `undoImportAction` · `inviteShare` /
`updateSharePercent` / `removeShareAction` / `updateOwnerShare` · `inviteAdviserAction` /
`setAdviserRoleAction` / `revokeAdviserAction` · `*View*` / `aiViewAction` (read-side leaks) ·
anything with `toggle`, `mark`, `confirm`. Full inventory + subsystem table:
`references/server-action-wire-ids-and-inventory.md`.

**The per-route chunk is not in `document.querySelectorAll('script[src]')`** after
client-side navigation. Ask the Resource Timing API instead:

```js
performance.getEntriesByType('resource').map(r=>r.name)
  .filter(n=>n.includes('/_next/static/chunks'))
// → .../_next/static/chunks/app/app/sources/[id]/page-<hash>.js   ← the action owner
```

**Raw-HTTP replay (no browser) — all four required, or you get a shape error:**
`next-action: <hex>` · `Accept: text/x-component` · `next-router-state-tree:
<URL-encoded JSON>` · multipart FormData with `_<index>_<argName>` fields + `0=["$K1"]`.
Route tree = `["",{children:[ "<seg>", {children:[["id","<uuid>","d"],{children:["__PAGE__",{},null,null]},null,null]},null,null]},null,null,true]`
(append one `{children:[...]}` wrapper per path segment). Hook format without the
`$ACTION_REF` hidden fields works for many actions — but see the shape-error rule below
before reading any 500.

**CORRECTION (verified 2026-10-01): there are TWO id spaces, and the wrong one 404s.**
The bundle's `createServerReference` hex and the id the browser puts in the `next-action`
header are **not the same value**.

```
bundle:   createServerReference("608ea2447e785621cecc8e9c22d7a37d05d1c9e004", …, "annualViewAction")
wire:     next-action: 60dd7e2aca7bad3a5d61e22135457a37d95a277b88   (captured on the same page load)
POST with the bundle id  -> 404, body = "Server action not found."  (24 bytes), for EVERY action tried
```

So the safe statement is narrower than "you can replay any action from the chunk id":

| Action kind | How to replay |
|---|---|
| **Form-bound** — the page HTML carries `$ACTION_REF_N` / `$ACTION_N:0` / `$ACTION_KEY` | fetch the page, rebuild `_N_$ACTION_*` + real fields as multipart, POST. **Works, no browser.** |
| **Client-invoked** — `createServerReference` (buttons, `useActionState`, on-load calls) | the wire id is a **per-render encrypted value**; harvest it live (CDP `Network.requestWillBeSent`, or monkey-patch `window.fetch` and read the `next-action` header) and replay that, OR drive the real UI |

Do not burn a pass enumerating action ids from chunks and POSTing them with `next-action:` —
every one returns `404 "Server action not found."`, which reads like a dead endpoint and is
actually the wrong id space. Confirm which kind you have first: grep the rendered HTML for
`$ACTION_` (form-bound) before assuming a browser capture is needed.

**Static harvesting is a dead end — proven, so don't re-test it.** For a JS-invoked action the
per-render wire id is absent from all three places you would look, checked in the same minute on the
same build: not in the client bundle (grep of every downloaded chunk), not in the page HTML, and **not
in the RSC flight payload** (`GET <page>` with header `RSC: 1` returned 0 ids of that shape while the
plain HTML returned the form ids). Only the live capture (request listener while driving the UI) or
the real UI itself produces it. Corollary: for JS-invoked actions, budget for *one UI path per
action*; for form-rendered actions you can enumerate everything statically from the HTML.

**Hand-rolled multipart replay of a form-bound action returned a constant HTML 500 (2,140 B) for every
form and every substitution** on this target — with and without the `%ACTION_*` fields, with and
without `next-router-state-tree`. Same rule as the digest-only body: a constant, structureless error
across all variants is a harness-shape failure, not a server signal. When that happens, stop
hand-building and drive the owning form instead (`el.form.requestSubmit()` after setting fields, or
Playwright `locator.click()`), which executed correctly every time. A runnable, credential-driven
cross-tenant probe (rows 1–14 of the boundary matrix, no browser) lives at
`server-actions-auth-audit/scripts/tenant_boundary_probe.py`.

Captured wire shape for a client-invoked action (POST to the page path):

```
next-action: <42 hex, per-render>
next-router-state-tree: <url-encoded RSC tree, ends ...,null,null,true] for __PAGE__>
accept: text/x-component
content-type: multipart/form-data; boundary=----WebKitFormBoundary…
body parts:  _1_<argName>        (arg names come from the action's parameters: _1_taxYear, _1_fph)
             0                   [{}, "$K1"]
```

Chrome truncates `postData` in `Network.requestWillBeSent`. Use POST capture + full body:

```
Network.enable  → collect requestWillBeSent for POST to the page URL
Network.getRequestPostData { requestId }  → FULL multipart body (save to disk)
also save headers: next-action, Content-Type (boundary), Referer, Accept: text/x-component
```

Multipart field naming pattern (action index `N`):
`_N_$ACTION_REF_N`, `_N_$ACTION_N:0`, `_N_$ACTION_N:1`, `_N_$ACTION_KEY`,
then real fields `_N_email`, `_N_role`, `_N_propertyId`, … and a trailing
`0` part containing `[{},$K1]`.

**Pitfall:** hand-building POSTs that omit the exact prefixed fields returns a full HTML
500 page — that is a *construction failure*, not an authz signal. Always replay the exact
captured body and only change one thing (cookie, Origin, one field) per test.

### Replay pitfalls that silently NO-OP (each returns 200 with no change)

These look like "the control held" but are harness failures. Rule the cause out before scoring.

- **Stale `$ACTION_KEY` = silent no-op.** `$ACTION_KEY` and the `$ACTION_N:0` binding are
  minted **per render**. Replaying a body captured from an EARLIER page load returns HTTP 200
  with a fresh HTML render but the action does **not** execute — no error, no state change.
  Symptom seen: a rename POST echoed 200 yet the property name was unchanged. Fix: fetch a
  fresh page immediately before the replay and rebuild the body from THAT render, or drive the
  real form (`form.requestSubmit()` after overriding fields) so the live key is used.
- **Progressive forms need multipart, not urlencoded.** For a plain `$ACTION_ID_<hex>` action
  (Remove/Logout style, no bound args), posting the fields as
  `application/x-www-form-urlencoded` returned 200 but did nothing; the SAME fields as
  `multipart/form-data` (`$ACTION_ID_<hex>=""` plus the real field) executed and took effect
  (verified: the target row disappeared). If a POST 200s with no state change, re-send as
  multipart before concluding a control held.
- **Forged enum value on a select the UI never offers.** Setting a controlled `<select>` to a
  key with no matching `<option>` silently yields `""` → you get an "uncategorised" row and a
  bogus result. Append the option first, then select, then submit:
  `el.evaluate((e,v)=>{ if(e.tagName==='SELECT' && ![...e.options].some(o=>o.value===v)){const o=document.createElement('option');o.value=v;o.text=v;e.appendChild(o);} e.value=v; e.dispatchEvent(new Event('change',{bubbles:true})); }, v)`.
  Outcome that time: the server still refused the forged cross-type category ("Choose a
  valid…") → validation holds — but only because the forged value was actually submitted.
- **The app redeploys mid-engagement.** Chunk hashes AND 42-hex action ids change between
  sessions (source-page chunk `734c188c…` → `608c8e2f…`; action `60b40f67…` → `6081b945…`).
  Never trust an id captured minutes ago — re-enumerate from the current page/chunk, and
  re-confirm any "control held" whose evidence was a captured id.

### Verify WHO the saved session is before trusting it

A stored session cookie can belong to a **different account** than the API key you hold. Seen
this session: the saved `qw_session` drove a stale FREE test account while the API key was the
vendor's PRO account — different tenants, different surfaces. The app you see depends on which
it is: the Pro account was a FIRM/accountant plan whose `/app` lands on a `/app/clients`
multi-client dashboard (`?view=mine` restores the personal book), with each client a separate
tenant uuid whose shared source is reachable as an adviser. Before any authed test, resolve
identity from an authoritative endpoint — `/api/v1/me` (key's `accountId`+`plan`) and
`/api/account/export` (session's `users[].email`+`plan`) — and confirm they agree; if not,
re-login instead of testing the wrong role.

### Deriving a full action replay from the rendered HTML (no capture needed)

You do not need a browser to get the fields. Any server-rendered page containing the form carries
the hidden action state inline; fetch it with your session cookie and parse it:

```python
html = S.get(BASE + "/app/sources/" + SRC).text          # session cookie attached
# hidden fields are $ACTION_REF_N / $ACTION_N:0 / $ACTION_N:1 / $ACTION_KEY where N is the
# form's index ON THAT PAGE — it changes per page and per render (seen: _1_ settings,
# _4_ , _5_ delete, _6_ ownership share on one source page)
data = {"_1_$ACTION_REF_1": "", "_1_$ACTION_1:0": <hidden>, "_1_$ACTION_1:1": <hidden>,
        "_1_$ACTION_KEY": <hidden>, "0": '[{},"$K1"]',
        **{"_1_" + k: v for k, v in overrides.items()}}
r = S.post(BASE + PAGE_PATH, files={k: (None, v) for k, v in data.items()},
           headers={"Accept": "text/x-component", "Origin": BASE, "Referer": BASE + PAGE_PATH})
re.findall(r'"(?:error|message)":"([^"]{4,160})"', r.text)   # the flight segment
```

Verified live this pass — three action families returned **explicit** strings, not digests, which
is what makes the HTTP-only route usable as evidence:

```
updateSourceSettings + foreign propertyId -> "Only the owner can change these settings."
updateOwnerShare     + foreign propertyId -> "That property could not be found."
deleteProperty       + random  propertyId -> "Only the property owner can delete a property."
```

Pitfalls that cost a cycle each:

- **The field-name prefix is mandatory and silent when missing.** Posting `email`/`password`
  instead of `_1_email`/`_1_password` returns the page's own HTML with HTTP 200 and **runs
  nothing** — no error, no Set-Cookie. Prove the action ran before reading any response: submit
  once with a CORRECT credential and once with a deliberately WRONG one. If both responses are
  byte-identical in length and headers the action never executed (observed: both 49,625 bytes,
  no Set-Cookie) → fix the field names; do not conclude "the login flow changed".
- **Do not send the form-payload id as a `Next-Action` header.** The `$ACTION_N:0` value
  (`{"id":"<41 hex>","bound":"$@1"}`) is the *form-action* envelope; its id in a `Next-Action`
  header returns **404**, because the header path expects the `createServerReference` hex from the
  chunk. Pick one style, never a mix.
- **Parse hidden fields with either attribute order.** `name="X"[^>]*value="…"` alone silently
  yields `""` when the markup puts `value` first; the POST then 500s and looks like a server
  error. Print every extracted value (and the resolved action id) before submitting, so a
  construction failure shows up as a blank rather than as a 500 "from the server".

### Login / action POSTs that hang ~60s and return 504 — that is your own footprint

After a high-volume pass from one IP, `POST /login` (the action POST, browser or curl) can sit for
exactly ~60s and return **Cloudflare 504 with `retry-after: 120`**. Two wrong readings to avoid:
"the app's login changed" and "login is DoS-able → finding". It is the edge throttling your
egress and it clears on its own. Practical consequences:

- Check what you already hold before re-authenticating. `GET /app` with a stored cookie:
  **200 = still valid, 307 = expired, 500 = ambiguous** (one account returned 500 while another
  account's cookie returned 200, so 500 is not proof of expiry). A valid pre-existing session is
  enough to run a whole cross-tenant matrix — don't spend the session budget on a fresh login.
- Never loop login attempts to "get it working"; each attempt extends the window. Use the API key
  for anything the API covers, and state honestly which session-dependent paths you could not
  re-run this pass.



## Architecture split: reads on a REST API, writes as Server Actions (+ the minted Bearer JWT)

Not every Next.js app puts everything behind actions. A common and very testable shape is a
**split plane**: the UI's mutations are Server Actions, but its *reads* go to a separate data API
on another host, authenticated by a short-lived Bearer JWT that a Server Action mints per page.

Find it by recording XHR while the authed UI loads — the app's own calls name the backend:

```
GET  api.example.com/api/auth/get-session                      (cookie session - control plane)
GET  api.example.com/api/auth/organization/list-members?organizationId=<id>
GET  data.example.com/api/trials                               (Authorization: Bearer eyJ… - data plane)
GET  data.example.com/api/trial-protocols/pro-tokens
```

Why this matters: the REST data API is far easier to drive than the actions.

- **Capture the JWT** by listening while any authed page loads:
  `pg.on("request", lambda r: JWT.__setitem__(0, r.headers["authorization"]) if "data.example.com" in r.url and r.headers.get("authorization","").startswith("Bearer") else None)`
  The action that mints it is usually literally named `getAuthToken` in the bundle inventory.
- **Decode it** (base64url the middle segment) to read the claims that *are* the tenant boundary:
  `activeOrganizationId`, `activeMemberRole`, `aud`, `exp`. A 5-minute TTL and a pinned
  `activeOrganizationId` are normal hardening — record them, they are not bugs.
- **Reads are GET; writes 404.** `POST` to a data-API path returns `404 Not Found` even when `GET`
  on the same path is `200`. That is the signal that creation lives in Server Actions — not that the
  endpoint is missing. Create the entity through the UI, then read it back over the REST API.
- **IDOR probe that fits this shape:** swap the tenant id in a read query
  (`?organizationId=<other>` / `?userIds=[…]`) with your own cookie. An explicit
  `403 {"code":"YOU_ARE_NOT_A_MEMBER_OF_THIS_ORGANIZATION"}` vs your own org's `200` is the control
  that proves the boundary holds — capture both readings.
- **Session vs JWT are two credentials for two planes.** The control-plane host takes the
  better-auth session cookie (`__Secure-better-auth.session_token` on the parent domain); the data
  host takes the Bearer JWT. A request to the wrong host with the wrong one 404s/401s; match them.

### Two automation pitfalls that silently block entity setup

- **Python slicing is not JavaScript.** Inside `page.evaluate("""…""")` a trim written as
  `e.textContent.trim()[:28]` throws `SyntaxError: Unexpected token ':'` and the whole evaluate dies.
  Use `.slice(0,28)`. (Same family as the `" ".join` / `len()` traps above.)
- **A required base-ui / Radix combobox left unset blocks the submit CLIENT-SIDE — with no POST.**
  Clicking create/submit then produces **zero network requests** plus an inline message naming the
  missing field (e.g. "Say which CTCAE publication this trial grades to"). The native value setter
  does NOT drive these components. Drive them like a user: click the trigger (`[role=combobox]`),
  then click the option in the **portal** (`[role=option]`); re-query the combobox list after each
  pick because indices shift, and press `Escape` if a listbox lingers (a stale open overlay makes the
  next `.click()` time out with "element is not visible"). Keyboard fallback (`ArrowDown` then
  `Enter`) also works. Verify the trigger's own text changed, then watch for the first POST as proof
  the form fired.
- **Reading your own OTP to get in.** If the app uses email-OTP signup and you own the inbox, the
  `google-workspace` skill's `google_api.py gmail search "from:<domain> newer_than:5m"` returns the
  code; regex the 6–8 digits and type them. Only ever use your OWN inbox (VDPs forbid mailing third
  parties), and create accounts under the program's policy.



## Testing the Origin control on a Server Action (capture → replay, one change at a time)

CSRF on a Next.js app is a question about **Server Actions**, not about `<form>`s: a cross-site
HTML form cannot set the `next-action` header, so the only real question is whether the server
enforces `Origin` on the action POST. Answer it by capturing one genuine action call and replaying
it with a foreign `Origin`. Works for any client-invoked action — no id enumeration needed:

```python
cap = {}
pg.on("request", lambda rq: cap.update({"url": rq.url, "headers": dict(rq.headers), "body": rq.post_data})
      if rq.method == "POST" and "<host>" in rq.url and "/cdn-cgi/" not in rq.url else None)
pg.goto(BASE + "/app/account", wait_until="domcontentloaded"); pg.wait_for_timeout(6000)
pg.evaluate("""()=>{const b=[...document.querySelectorAll('button')].find(x=>/save details/i.test(x.innerText||'')); b&&b.click();}""")
pg.wait_for_timeout(7000)
# replay: same next-action + multipart body + session cookie, ONLY Origin changes
for origin in ["https://<host>", "https://evil.example", None]:
    hh = {k: v for k, v in cap["headers"].items()
          if k.lower() in ("next-action", "content-type", "accept", "user-agent", "next-router-state-tree")}
    hh["Cookie"] = "qw_session=" + SESSION; 
    if origin: hh["Origin"] = origin
    r = requests.post(cap["url"], headers=hh, data=cap["body"].encode(), timeout=30)
```

Read the verdict from **state**, never from the status line:

- same-Origin → 200 and the field changed; foreign Origin → rejected **and the field unchanged**
  ⇒ the control holds. Confirm the "unchanged" by re-reading the value from the page or a `GET`,
  not by trusting the absence of an error.
- **A foreign `Origin` returning HTTP 500 (RSC `{"digest":"…"}` body) is the protection working,
  not a finding.** Next.js aborts the flight stream; the error is delivered inside the
  `text/x-component` body rather than as a clean 403. Do not report "500 on Origin mismatch" as a
  bug — record it at most as a one-line robustness note, and only if the same request with a
  same-site Origin returns 200 (that pair is the whole proof).
- **An absent `Origin` header being accepted is not CSRF either.** A cross-site browser form
  cannot set `next-action`, and a cross-origin `fetch` that could would first have to pass CORS
  preflight. Say which of the two conditions you actually tested.
- One request, one variable. Changing cookie *and* Origin in the same replay tells you nothing
  about either.

## Next.js quirks (verified, reusable)

1. **POST + multipart/form-data to an UNKNOWN /api path → 500 "Internal Server Error"
   text/plain**; POST with no body / `{}` / `[]` / text/plain → 404; GET/PUT/OPTIONS →
   404. Cause: body parser runs before route match for multipart. Not a security finding —
   a status-code inconsistency. Vendors will ask for exact path+method+body; table this.
2. **RSC flight data escapes reflected URL params as `\u003c`** — grepping the raw HTML for
   your marker misses this and produces XSS false positives. Always confirm in the DOM:
   query for real `<img>/<script>/<svg>` elements, check `element.innerHTML` for `&lt;`
   vs raw `<`, and check the marker's location (flight string inside
   `self.__next_f.push` ≠ rendered HTML).
   **Inverse trap (bit me twice):** a detector that scans `outerHTML` of every `img/script/svg`
   for `src="x"` or `onerror` also matches the `<script>self.__next_f.push([1,"…<img src=x
   onerror=…>…"])</script>` flight element and reports a phantom "injected element". Exclude
   scripts whose text starts with `self.__next_f` before reporting, and require a real element
   (`document.querySelectorAll('img[src="x"]').length`). Then confirm *execution*, not just
   presence — install hooks **before** navigation (Playwright `add_init_script`) and read them
   after:
   ```js
   window.__fired = [];
   const a = window.alert; window.alert = (m) => { window.__fired.push('alert:'+m); return a.apply(this, arguments); };
   window.addEventListener('error', e => { if (e?.target?.tagName === 'IMG') window.__fired.push('img:'+e.target.getAttribute('src')); }, true);
   ```
   Verdict shape: payload appears as **text** in a leaf node + no real element + empty
   `__fired` = escaped/not exploitable. Report all three readings so the negative is credible.
3. **CVE-2025-29927 middleware bypass**: send `x-middleware-subrequest: middleware` (and
   variants) to authed routes; if every probe returns 307→login, middleware auth still runs.
4. **`/reset?codeLimit=N&why=cooldown`-style params are display echoes.** Manipulating the
   value only changes the hint text ("about N seconds"); the real gate is server-side
   cooldown ("Send a new code in 58s") and attempt counters. Don't report as a bug.
5. **OPTIONS on an existing route returns `Allow: GET, HEAD, OPTIONS`** — it reveals the
   method set; good for spotting upload/document routes that only accept GET (no upload
   handler at all → dead end).



## Upload/document-store checklist that actually finds things

- Filename traversal: `set_input_files({"name": "../../..//evil.png", ...})` → check the
  served `filename=` (expected: basename only).
- Content-type spoof: HTML bytes declared `image/png` → stored, but served as `image/png`
  with `X-Content-Type-Options: nosniff`, so no render. **Inline + nosniff is the reason
  this is safe — verify both headers before calling it clean.**
- Size: send ~11MB when the copy claims 10MB (expect rejection).
- Re-open the upload form for EVERY case — it closes after a successful upload and the next
  `set_input_files` then times out, which reads as "rejected" when it is just a stale form.
- Does the receipt/AI scan endpoint retain the image? Count documents before/after.
- Delete affordance: check for `button[aria-label="Delete document"]` so you can restore the
  account.



## Feature-gated surface: create the entity, don't declare a coverage gap

A route handler can exist in the bundle with nothing to point it at, because the tab that uses it
renders only for a particular entity type. Read the component's props to learn the gate, then create
the entity that satisfies it — that is usually 5 minutes, versus an honest-but-empty "not tested".

Worked example: `InvoicesTab` took `{propertyId, businessRowId, isSe, invoicing}` and only rendered
under a self-employment source. Creating one (dashboard → "Add an income source" →
"Self-employment"; a `name` and an optional CIS checkbox) immediately added the `Invoices` tab, and
`/api/invoices/{id}/pdf` could then get a real id in front of a second session. Two mechanics worth
remembering:

- The artifact id is **not** in the list markup — the row is a disclosure button
  (`button[aria-expanded]` whose text contains `INV-`); click it, then grep the DOM for
  `/api/invoices/<uuid>`. Looking for the link before expanding yields a false "no object exists".
- Tab panels are directly addressable in this app style (`?tab=invoices`, `?tab=settings`), which
  removes a click-dependency from every scripted run.
- BOLA shape that came out of it (report it as a control when it holds):
  owner session `200 application/pdf` → second account `404` → no session `307` → random uuid `404`,
  plus `/api/invoices` (list) `404` for the second account and the foreign-source UI page rendering
  the not-found shell.

**Escalate through three submit paths before declaring it broken, then stop.** Observed on a
`Delete this property permanently` form (name typed, button enabled, `disabled=false`): a
Playwright `locator.click()`, pressing Enter in the confirm field, and calling
`form.requestSubmit(button)` from `Runtime.evaluate` **each produced zero network requests** —
no POST, no RSC fetch, no console error. So "the button is enabled" does not mean the submit is
wired. After all three, record it as *unverified through automation* and say so in the report;
do not score it as a working control and do not claim the destructive action is unprotected.

**A sibling form with a required code field will block submission silently.** On the same page the
invoice-settings form carried `mfaCode` with `required=true`; an empty required field blocks HTML
form submission with **no network request at all**, which looks identical to a dead button. Before
concluding "the action never fires", dump `[...document.querySelectorAll('input[required]')]` on
the page — if one of them is the MFA/code field, the real finding is "sensitive settings are
code-gated", which is a *positive* control, not a bug.
