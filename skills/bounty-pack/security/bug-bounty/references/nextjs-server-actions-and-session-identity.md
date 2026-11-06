# Session identity + driving Next.js App Router server actions

Two pitfalls that cost time on the Quarterwise engagement (2026-09/10) and generalise to any
authed Next.js App-Router SaaS where you hold a stored browser session.

## 1. Verify WHAT ACCOUNT your session actually is, before testing anything

A stored `browser_state_<label>.json` / cookie jar can silently belong to a different account than
you think (an old throwaway test account from a previous session, or a free account while your API
key is the paid one). Everything you conclude is wrong if the session isn't the target identity.

- Symptom seen: a cookie labelled `browser_state_pro.json` returned plan `free`, user name
  "Audit Account E", while the separate API key returned `plan: pro`, accountId 0cf6748e — two
  different accounts. The dashboard rendered the free account's single-property view; the Pro
  account was a FIRM plan with a totally different surface (`/app/clients`).
- Check it first: call an account-scoped endpoint from BOTH credentials and compare identity —
  e.g. `/api/v1/me` (plan + accountId) for the key, and an account-scoped page/export for the
  cookie (`/api/account/export`, or a page that prints the signed-in name). If they differ, re-login
  the session as the intended user before proceeding.
- Re-login is cheap: fetch `/login`, submit email+password, handle the TOTP step with the stored
  secret, capture the fresh `qw_session`-style cookie back into the state file.

## 2. Next.js App Router server actions — how to enumerate, replay and drive them

- Action ids are **42-char hex**. They appear in the served HTML/RSC as
  `name="$ACTION_ID_<id>"` (plain form) or `name="$ACTION_<n>:0" value='{"id":"<id>","bound":"$@1"}'`
  (client-bound). They are NOT reliably in the client chunk files — harvest from the page HTML
  (`grep -oE '[0-9a-f]{42}'`), and note they CHANGE on every redeploy (chunk hashes too), so
  re-harvest after any "the button stopped working" moment.
- A submitted action is a `POST` to the SAME page path with header `Next-Action: <id>`. The
  progressive-enhancement (no-JS) body is `multipart/form-data` with fields prefixed `_1_`
  (`_1_<fieldname>`), the hidden `$ACTION_x:0`, `$ACTION_x:1`, `$ACTION_KEY`, plus a trailing
  field named `0` whose value is `[{}, "$K1"]`.
- `$ACTION_KEY` is **per-render**. Replaying a captured key from an earlier page load silently
  no-ops (200 + re-render, no state change). Either re-fetch the page and use the fresh key, or
  don't replay at all.
- Most reliable: drive the real rendered form with Playwright. For React-controlled inputs, a plain
  `el.value = v` does NOT update React state — use the native setter:
  `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,v)` then dispatch
  `input` + `change`. Submit with `form.requestSubmit()` (bypasses disabled/hit-test issues) or click
  the button.
- Client-bound actions (`$ACTION_REF_n`) can't be resumed from a captured key/body — drive the UI.
- Some controls are **two-step gates**: clicking "Update" merely reveals an MFA-code field; the real
  action is the second submit. Generate the TOTP immediately before submitting (30s window) or you
  get "code is not correct". Same for "Share this property".
- Capture action responses with `page.on("response")` and regex `(?:error|message)"?\s*:\s*"..."` —
  the human-readable result ("Only the owner can change these settings.", "That property could not
  be found.", "This property is already fully allocated.") lives in the flight payload, not the DOM.

## 3. Don't assume the stored cookie is live either

Sessions expire. Cheap liveness check: `curl -o /dev/null -w '%{http_code}'` an authed page with the
cookie (200 = live, 307→/login = dead) before a long run.

## 4. MSYS/git-bash path mangling (Windows)

On Windows git-bash, a bare argument starting with `/` (e.g. a `$p` holding `/api/v1/me`, or a
`-w "label"` string) gets converted to a `C:/...` path. Symptoms: curl says "no URL specified" or
the output label shows `C:/Users/.../git/api/...`. Fix: `MSYS_NO_PATHCONV=1` on the command, or
always pass full `https://host` URLs. Also: Hermes redacts secrets in tool output, so a command that
echoes a token can look corrupted (`Bearer ***`) — pass secrets via a file/variable read inside the
script (python `pathlib.read_text()`), not inline.

## 5. CORRECTION (2026-10, second pass): replay server actions from `requests` with BARE field names

Section 2 above is right about what the BROWSER sends (`_1_`-prefixed multipart). But when replaying
from Python `requests`, the `_1_` prefix is rejected: every attempt returned **HTTP 500** (2,140-byte
Next error page). The working format is the field names **as they appear in the form, unprefixed**:

```python
fields = {"$ACTION_ID_<42hex>": "", "<field>": "<value>", "0": '[{"$K1":1}]'}   # $ACTION_ID style
# or, for $ACTION_REF_n forms:
fields = {"$ACTION_REF_n": "", "$ACTION_n:0": '<json>', "$ACTION_n:1": "[{}]",
          "$ACTION_KEY": "<fresh>", "<field>": "<value>", "0": '[{},"$K1"]'}
r = s.post(page_url, files={k: (None, v) for k, v in fields.items()},
           headers={"Origin": base, "Referer": base + page, "Accept": "text/x-component",
                    "next-action": wire_id}, allow_redirects=False)
```
Payoff: with this format you get real answers with no browser — `200` + `{"error":"Only the owner can
change these settings."}`, `200` + `{"error":"That key could not be found."}`, or `303` on the
logout-style redirect. This makes it cheap to sweep EVERY id-carrying form on every page with a foreign
id substituted.

### PITFALL — parse `$ACTION_*` PER `<form>`, never page-wide
A page-wide regex picks the FIRST `$ACTION_ID_<hex>` on the page, which is usually the **nav "Log out"**
form. Replaying that with an extra field silently **logs your session out** (and the next sanity check
then misreads the page as logged-out). Always split the HTML on `</form>` and pick the chunk that also
contains the field you are targeting (e.g. `name="accessId"`); verify the captured id belongs to that
form before firing.

### PITFALL — entries hidden by the page's tax-year filter
Per-row controls (e.g. `button[aria-label="Delete entry"]`) only render for rows inside the selected tax
year. Cleanup loops that "find no rows" are usually looking at the wrong year: load the source page and
switch the year control to **All time** (`?ty=all`) before concluding there is nothing there.

## 6. Testing object-level authz on actions that take an id FROM THE CLIENT

Two techniques, both proven on this target:

**(a) Rewrite the outgoing body with `page.route`.** Let the real UI fire the action (so the wire id and
key are valid), intercept the POST, substitute the target id, and read the server's own response:

```python
def handler(route):
    rq = route.request
    if rq.method == "POST" and rq.headers.get("next-action"):
        body = rq.post_data or ""
        if SRC and SRC in body:                      # SRC = our own object id
            log.append(...)                          # prove the substitution: before/after values
            return route.continue_(post_data=body.replace(SRC, DST))   # DST = foreign/random id
    route.continue_()
page.route("**/*", handler)
```
Log `_1_<idfield>` BEFORE and AFTER the replace — that captured pair is the evidence that the request
carried a foreign id. Then pair every rejection with a **positive control** (same action, own id) so the
negative is meaningful: e.g. `deleteTransaction` with a foreign `txnId` = no-op while the same action on
the own id really deletes; `updateTransaction` foreign = "That entry could not be found." vs own = value
changed; the review-queue **Confirm** foreign = item stays queued vs unpatched = queue empties.

**(b) A working wire id is NOT the id in the client bundle.** For JS-invoked actions the id sent in
`next-action` is issued per render; it is absent from the chunk files, from the RSC payload (even with
`RSC: 1`), and is not the `createServerReference("<hex>")` value (using that value returns
`404 "Server action not found."`). Harvest it live by driving the UI once with
`page.on("request")` and recording `headers["next-action"]` per action, then reuse that captured value
for the route-rewrite or `requests` replay.

**Selector notes that saved time:** row controls are `button[aria-label="Edit entry" | "Delete entry" |
"Delete note" | "Delete document"]`; destructive flows use a separate confirm button whose text is often
`"Yes, delete"` (not `"Yes"`); create/edit modals carry hidden `input[name=txnId]`,
`input[name=documentId]`, `input[name=noteId]`, `input[name=invoiceId]` and are submitted with
`form.requestSubmit()` on the form that owns that hidden field. Safe patched-targets: a random UUID (no
object can match) and our own second tenant's real ids.
