# Next.js server-action REPLAY & AUTHZ testing (verified on a live App-Router SaaS)

Companion to `nextjs-server-actions-and-session-identity.md` (that one covers identity/driving an
authenticated session; this one covers *replaying* actions headlessly and using them to test
authorization). All of the below was proven on a Cloudflare-fronted Next.js App Router app.

## 1. Two different ids — know which one you need

| id | where it lives | used for |
|---|---|---|
| **reference id** | `createServerReference("<42-hex>", …, "<Name>")` in the client bundle | reading the app's action inventory (the name is often still present in prod!) |
| **wire id** | the `next-action:` request header at call time | actually invoking the action |

They are NOT the same string. Posting the bundle's reference id as `next-action` returns
`404 Server action not found.` The wire id is produced per render and is **not** in the bundle and
**not** in the RSC payload (verified: `RSC: 1` fetch of the page returned 0 hex-42 ids; greps of every
loaded chunk found nothing).

⇒ For **JS-invoked** actions you must harvest the wire id live: run a Playwright
`page.on("request")` listener, drive the real UI, and log every POST to the target host that carries a
`next-action` header (parse the multipart body for `_1_<arg>` field names). One UI path per action.
⇒ For **server-rendered form** actions you do NOT need the wire id at all — see §2.

Useful side-effect of the inventory: production bundles often keep the exported function name as the
5th argument, so you can enumerate the whole backend surface by name
(`deleteTransactionAction`, `commitImportAction`, `revokeAdviserAction`, …). That is a map, not an
exploit — you still need the wire id to call them.

## 2. The static replay format that actually works (bare field names)

Replaying a server-action form with plain HTTP requests:

```
POST https://target/<page-path>
Content-Type: multipart/form-data; boundary=…
Accept: text/x-component
(optional) next-action: <wire id if you have it>

fields = every name="…" from the form's <input>/<select> AS-IS, i.e. NO prefix:
  $ACTION_ID_<42hex>            (empty value)      # $ACTION_ID_*-style forms
  $ACTION_REF_4 / $ACTION_4:0 / $ACTION_4:1 / $ACTION_KEY   # $ACTION_REF_N-style forms
  <payload fields: propertyId, confirmName, percent, accessId, keyId, documentId, email, mfaCode…>
  0 = '[{},"$K1"]'
```

**PITFALL (cost hours):** the names Chromium sends from a hydrated client are prefixed `_1_`
(`_1_propertyId`). Sending those from `requests` makes the server throw **HTTP 500 (2 140-byte error
page)** every single time — which looks like "the target rejects this action". It does not. Send BOTH
flavours when unsure; bare names are the ones that work headlessly. Recognising this instantly
separates "action executed" (200 + RSC error string, or 303) from "my replay is malformed" (500).

**PITFALL 2:** parse `$ACTION*` **per `<form>` block**, never with one page-wide regex. A page-wide
match grabbed the nav logout form's `$ACTION_ID` and the replay silently **logged the session out**.

## 3. Authz testing pattern (body rewrite + positive control)

Do not hand-craft payloads for client-invoked actions — let the UI produce a valid call and rewrite
the target id in flight:

```python
def handler(route):
    rq = route.request
    if rq.method == "POST" and TARGET in rq.url and rq.headers.get("next-action"):
        body = rq.post_data
        if OWN_ID in body:                       # rewrite to the foreign/random id
            return route.continue_(post_data=body.replace(OWN_ID, FOREIGN_ID))
    route.continue_()
page.route("**/*", handler)
```

Then read the server's own message out of the RSC payload (`"error":"…"`) and **always pair it with a
positive control**: the same action with your own id must SUCCEED (create/rename/delete visibly).
Without the control a "no-op" is indistinguishable from "my request was malformed".

Rejections observed and worth recognising as healthy:
`That entry/property could not be found.` · `Only the owner can change these settings.` ·
`Only the property owner can delete a property.` · `That key could not be found.` ·
`The name you typed does not match this property.` (name-check, so the foreign id was stopped at the
ownership gate, not the name gate) · silent no-op for delete/confirm paths (verify by re-reading the
object, and confirm the same action *did* work on an own object).

## 4. Destructive actions are usually MFA-gated (and how to test through it)

Property delete / ownership-share update / adviser invite require a CURRENT authenticator code at
submit time. A replay without `mfaCode` is refused with
`Enter the current 6-digit code from your authenticator app.` Add `mfaCode = pyotp.TOTP(secret).now()`
to the SAME POST and it completes (observed 303). Consequences:
- cleanup of a harvested scratch object may silently need a TOTP — a "cleanup printed success but the
  object is still there" is almost always this;
- verify cleanup by re-reading state (API listing), never by trusting the flow's own message.

## 5. Free-tier / entitlement bypass recipe (server-side enforcement check)

UI-only caps are common. To test whether the server enforces them:
1. harvest the create-action's wire id from an account that is NOT capped (e.g. a paid/firm account's
   personal view — on one target the chooser only rendered at `/app?view=mine`);
2. replay it from the CAPPED account's session with a fresh name;
3. read the server's own reply. Capped ⇒ it answers with its own cap message
   (`Your free plan includes 1 property you own. Upgrade to Pro…`) and the account's source count is
   unchanged = control holds. No message + a new object = real bypass (report it).

## 6. UI-path map (what fires an action and what does not)

- Tabs/panels (Entries / Documents / Notes / Reminders / Settings) are **server-rendered** — clicking
  them fires nothing. Read them with plain HTTP.
- Modals/wizards are **client-invoked**: record income/expense, share/invite dialog, review-queue
  Confirm, document delete-confirm, import wizard (3 hops: upload → saveMappingAction → listing
  assignment → commitImportAction). These need §3's interception.
- Buttons labelled `type="submit"` inside those modals often do nothing under `element.click()` from
  an automated context — prefer `form.requestSubmit()` or the static replay of §2.
