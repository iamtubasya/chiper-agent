# Next.js Server-Action Cross-Tenant Replay (validated 2026-09, Quarterwise VDP)

How to test whether a second account can invoke another account's server actions
(share-percentage change, delete, invite, settings) on a Next.js App Router target.

## Why manual curl usually fails
Server-action POSTs carry state that is easy to get wrong:
- `next-action: <64-char hex>` header — the action function id.
- `next-router-state-tree: <urlencoded tree>` — the routing tree at submit time.
- urlencoded body with `_1_`-prefixed field names (React 19 action-args framing),
  including `_1_$ACTION_REF_N`, `_1_$ACTION_N:0` (JSON `{id, bound:"$@1"}`),
  `_1_$ACTION_N:1` = `[{}]`, `_1_$ACTION_KEY` = a per-render random key, and the
  visible form fields prefixed the same way.
- The `$ACTION_KEY` **rotates on every page render** — keys captured minutes ago (or in
  another tab) produce a 404 shell even for the legitimate owner.

Reconstructing this by hand almost always returns the 404 SPA shell, which is NOT an
authorization signal — it's a malformed request. So: capture the real browser POST first.

## Capture (owner's tab, CDP)
```python
# hook fetch so the action POST + response are visible
js("""(function(){
  window.__cap=[];
  const of=window.fetch;
  window.fetch=function(u,init){return of.apply(this,arguments).then(async r=>{
    try{const c=r.clone();const t=await c.text();
      window.__cap.push({u:String(u),m:init&&init.method,s:r.status,
        h:init?JSON.stringify(init.headers||{}):'',b:init?String(init.body).slice(0,400):'',
        r:t.slice(0,400)});}catch(e){}
    return r;});};
  return 'HOOK';
})()""")
# ... perform the action via a real click / form.requestSubmit ...
caps = js("JSON.stringify(window.__cap)")
# Native form submits surface in Network.requestWillBeSent too:
#   headers: Accept: text/x-component, next-action: <id>, next-router-state-tree: <tree>
#   postData: urlencoded _1_$ACTION_... fields
```
Verify the owner's own call succeeds (RSC stream with ok:true, or visible state change)
BEFORE replaying under the second account's jar — otherwise you can't distinguish
"action blocked for B" from "body malformed for everyone".

## Replay under victim B's jar
```python
import urllib.parse, subprocess
body = urllib.parse.urlencode([
  ("_1_$ACTION_REF_6",""),
  ("_1_$ACTION_6:0", '{"id":"<action-id>","bound":"$@1"}'),
  ("_1_$ACTION_6:1", "[{}]"),
  ("_1_$ACTION_KEY", "<FRESH key from the current page render>"),
  ("_1_propertyId", "<A's object id>"),
  ("_1_percent", "100"),
])
cmd = ["curl","-sk","-X","POST",
  "-H","Accept: text/x-component",
  "-H","next-action: <action-id>",
  "-H","next-router-state-tree: <captured tree>",
  "-H","Content-Type: application/x-www-form-urlencoded",
  "-b","jarB.txt","-d",body,
  "-o","out.txt","-w","%{http_code}", "<target>/app/sources/<A-id>"]
```
Read the FRESH `$ACTION_KEY` (and `$ACTION_N:0` id) from B's current page render where
possible; if the action is page-scoped, B's page simply won't contain it and the replay
404s — that itself is evidence the action surface is ownership-scoped.

## Interpretation
- Owner call succeeds (200 + state change) AND B's replay 404s / no-op => ownership-scoped
  action, no finding.
- B's replay succeeds and mutates A's object => BOLA/priv-esc — confirm by re-reading the
  object under A's jar, then report with both request bodies.
- 404 shell for BOTH A and B => malformed request, not a verdict. Re-capture.

## Pick the RIGHT wire format — there are three, and only one matches your capture

Read the DOM of the form you are about to replay and branch. Using the wrong format returns
the SPA shell (200 HTML) which masquerades as a 404/verdict.

| Form shape in DOM | It is | Request |
|---|---|---|
| `$ACTION_REF_N` + `$ACTION_N:0` + `$ACTION_N:1` + `$ACTION_KEY` | progressive-enhancement form, bound args | urlencoded POST to the **page URL**; body `0=[{}, "$K1"]` + `_1_$ACTION_REF_N` + `_1_$ACTION_N:0` + `_1_$ACTION_N:1` + `_1_$ACTION_KEY` + `_1_<fields>` |
| `$ACTION_ID_<hex>` (no key) | no-arg action, e.g. Log out / Remove | `_1_$ACTION_ID_<hex>=""` alongside the visible `_1_<fields>` |
| no hidden action fields; button has a JS handler | **client `fetch` action** | `next-action: <hex>` + `next-router-state-tree: <tree>` + `content-type: text/plain;charset=UTF-8`, body `{"0":"[\"$K1\"]","_1_<field>":"<val>"}` — **no `$ACTION_KEY` at all** |

The third row is the one that breaks hand-reconstruction: the body is JSON, `$K1` resolves to
the FormData assembled from the `_1_`-prefixed keys, and the content-type is `text/plain`, not
urlencoded and not multipart. Sending that body as urlencoded or multipart yields the HTML
shell, and a hand-built multipart with a truncated `$ACTION_N:0` yields a bare 500 — neither
is evidence about authorization.

## Preferred decisive test: attacker's OWN render, then swap the object id

Victim-side capture (above) is the expensive path and its cross-tenant replay is usually
**inconclusive**. Cheaper and stronger:

1. Attacker (B) creates their OWN object so the action is available with a valid binding.
2. B performs the action on their own object; hook `fetch` and capture the exact request.
3. Confirm the control: own object → `200` and the change is visible.
4. Re-send the **identical** request with only the object id swapped to the victim's.
5. Re-read the victim's object under the victim's jar.

Observed profile on a hardened target (Quarterwise, 2026-09):
- B deletes B's own entry → `200`, entry gone.
- Same request, `_1_txnId` = A's entry → `500` with `1:E{"digest":"<same hash>","..."}`, A's entry intact.
- Replaying an action id captured from A's render under B's jar → the SAME `500` digest.

Interpretation: a thrown server-side check (in production the flight error is a hashed digest,
so you cannot read the message — the *status transition* is the evidence). 200-with-mutation on
the control plus 500/no-mutation on the swap = data-layer authz enforced → verified negative.
Only a `200` + mutation on the swap is a finding. The digest being stable across attempts means
you are hitting one deterministic guard, not a malformed request.

## Renaming a resource is a cheaper probe than deleting one

Prefer a low-blast-radius action for the swap test. A rename/settings POST returns the guard's
plaintext message in the flight row (`1:{"error":"Only the owner can change these settings."}`,
`1:{"error":"That property could not be found."}`) — far more quotable in a report than a
hashed digest, and it leaves the victim's data untouched. Save destructive swaps for last.

## git-bash / Windows argv caveat

Passing a path argument that starts with `/` (e.g. `/app/sources/<id>`) as a Python argv gets
MSYS path-mangled into `/home/agentuser/app/...` before your script sees it, producing a bogus
hostname resolution error that looks like a network fault. Prefix the command with
`MSYS_NO_PATHCONV=1` (or pass URLs, not paths). Also note exported env vars persist across
`terminal` calls in the same session — `unset` them when a later command must behave normally.

## Notes
- RSC responses look like `0:{"a":"$@1",...}\n1:{"error":"..."}` — read row `1` for the
  server action's result/error message (e.g. `{"error":"This property is already fully
  allocated."}` is a business-logic gate, not an authz block).
- `rel=noopener` / `target=_blank` links to `/api/documents/<id>` etc. are the unauthenticated
  object-read surface: probe them cross-tenant with both jars (404 = scoped, 200 = leak).
- On targets with per-render action keys, a "wrong key" control (same body, dead key)
  returning the same 404 as the cross-tenant attempt proves the 404 comes from the
  framework, not a custom authz check — document both controls in the report.

## Getting object ids that never appear in the DOM

Server-action bodies carry object ids (`_1_txnId`, `_1_noteId`, `_1_propertyId`) that are bound
at render time and are often absent from the markup. Don't guess them and don't scrape HTML:

1. Find the row's edit affordance (`button[aria-label=Edit entry]`, `Edit note`, ...) and click it.
2. The edit form exposes the id in a hidden input — read `input[name=txnId]` / `input[name=noteId]`.
3. For a list, index the buttons (`[...document.querySelectorAll('button[aria-label=Edit entry]')][n]`)
   and then read `[...document.querySelectorAll('input[name=txnId]')].map(i => i.value)` to map
   ids back to rows by matching the adjacent description field.

This yields a victim object id for the swap test without ever needing the victim's session.

## A 200 plus a full HTML page is a NO-OP, not success

POSTing a server-action form with the wrong serialization (urlencoded or multipart when the action
expects the text/plain JSON body, or omitting `next-action`) returns `200` with the complete
rendered page. It looks like it worked; nothing happened. Never trust the status code — after every
replay, RE-READ the object or reload the page and assert the mutation is actually visible. The tell
is the response shape: an RSC flight stream (`0:{...}` / `1:{...}` rows) means the action ran; a
full `<!DOCTYPE html>` page means it did not. Several cycles in the 2026-09 Quarterwise session were
lost to reading a 200 as success on a `$ACTION_ID_` form replay.
