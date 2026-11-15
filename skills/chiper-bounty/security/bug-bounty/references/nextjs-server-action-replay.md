# Next.js App Router: server-action replay + wire-id harvesting (verified live, 2026-10)

For Next.js App Router targets (RSC + server actions). Every point below is something that actually
worked against a production build behind Cloudflare; the failed approaches are listed too, so they don't
get retried.

## 1. The wire id is NOT the id in the client bundle

- `createServerReference("<42-hex>", …, "<actionName>")` in the bundle is a *reference* id. The value the
  browser sends in the `next-action` header is a different, per-build id.
- It is absent from the bundle AND from the RSC-1 flight payload (`curl -H 'RSC: 1' <page>` → 0 hex ids).
  Posting the reference id yields `404 "Server action not found."`.
- Working harvest: Playwright `page.on("request")` while driving the REAL UI — record
  `r.headers["next-action"]` + `r.post_data_buffer`. Gives the wire id and the exact argument names.
  (Overriding `window.fetch` via `add_init_script` captured nothing; the request listener did.)

## 2. Static replay of server-rendered forms: BARE field names

```
POST <page path that rendered the form>        (multipart/form-data)
  $ACTION_ID_<42hex> = ""                      # or the $ACTION_REF_N / $ACTION_N:0 / $ACTION_N:1 / $ACTION_KEY quartet
  <payload fields>   = <values>                # propertyId, noteId, accessId, confirmName, percent, …
  0                  = [{},"$K1"]
```

- `_1_`-prefixed names are what the browser sends when IT fires the action. Replaying `_1_` names from
  requests returns **HTTP 500** (Next's 2,140-byte error page) every time. Bare names return the real
  action result (200 with the RSC payload, or 303 on success).
- Parse `$ACTION_*` **per `<form>` block**, never with a page-wide regex. A page-wide match once picked
  the nav LOGOUT action and silently signed the session out.
- `GET /app` returning 307 is often normal (firm vs personal landing), not an expired session. Check the
  session against an authenticated page that definitely renders (e.g. `/app/account`).

## 3. Authz test pattern (deterministic, no guessing)

Let the real UI fire the action with a valid wire id, intercept with `page.route("**/*", handler)` and
rewrite the outgoing body so the object id points at a FOREIGN tenant's object; then read the server's own
message. Always pair it with a positive control on an owned object, otherwise "no error" means nothing.

Results seen on one target (all correctly scoped): add/update/delete transaction, delete document,
delete invoice, delete note, review-queue Confirm, updateSourceSettings, updateOwnerShare, deleteProperty,
revoke API key, "stop advising" — each returned a specific refusal (`That entry could not be found.`,
`Only the owner can change these settings.`, `That key could not be found.`) or was a silent no-op while
the owned-object control succeeded.

## 4. Cross-account replay also works → use it for entitlement tests

A wire id harvested in account A can be POSTed with account B's cookie. That answers "is the plan cap
enforced server-side or only in the UI?": the create-source action replayed from a capped free account
returned `{"error":"Your free plan includes 1 property you own. Upgrade to Pro for unlimited
properties. …"}` while the positive control created one. (Use your own two accounts only.)

## 5. Privileged actions are TOTP-gated

delete property / change ownership share / create API key / invite adviser are refused with
`Enter the current 6-digit code from your authenticator app.` until an `mfaCode` field carries a live
code. Add `mfaCode=pyotp.TOTP(secret).now()` to the bare replay — the delete then returns 303.
Note: a password change signs the account out on other devices, so refresh the stored session afterwards.

## 6. Other gotchas

- Wire ids are per-build: after a redeploy they change — re-harvest, don't reuse.
- Buttons clicked via `evaluate`/`requestSubmit()` sometimes produce no POST (pre-hydration). When that
  happens, fall back to the static bare-name replay (§2) instead of fighting the UI.
- Emails the vendor sends are worth auditing when the programme scopes them: profile-name text does reach
  transactional emails, but at least one vendor stripped HTML tags at render time — test tag rendering
  explicitly (set a name containing `<b>`/`<a href>`, trigger a name-bearing template such as the
  adviser-invite, and read your own mailbox) before claiming an email-injection finding.
