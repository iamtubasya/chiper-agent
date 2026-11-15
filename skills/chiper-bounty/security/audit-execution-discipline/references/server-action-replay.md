# Next.js Server Action Replay + RSC Reflection Guard

Source: quarterwise.co.uk audit, 2026-09-28 (Next.js App Router, RSC, Server Actions).
Companion to **RULE 2b/2c** (use the right tool; read the evidence body). This file is the
**reproduction recipe** for testing Server Actions, plus the false-positive guard that stops
you reporting RSC state-echo as LFI/SSTI/XSS.

---

## 1. Why the naive recipe fails (and what it looks like)

The common advice — POST to the page with `Next-Action: <id>` and a body of `[]` — **does not
work** on a real app:

```bash
# ❌ this shape 500s with an opaque digest
curl -X POST https://target/ -H "Next-Action: <40hex>" \
     -H "Content-Type: multipart/form-data; boundary=----" \
     --data-raw $'------\r\nContent-Disposition: form-data; name="1"\r\n\r\n[]\r\n------\r\n'
# → 0:{"a":"$@1",...}  1:E{"digest":"3099188954"}
```

Two reasons:
1. **Bound args are encrypted** on real submissions (`encryptActionBoundArgs`) — you cannot
   synthesise the payload from an ID alone.
2. The request needs a **router-state-tree** header, and the FormData field names are
   prefixed (`_1_<name>`), which you can only learn by watching the app's own request.

**A `digest` error is a SHAPE error, not a security control.** Never report "action blocked"
from a digest — it means your request was malformed.

## 2. Enumerate the actions (bundles + server-rendered HTML)

```bash
# 1) From JS chunks — id + exported name (name is the last string arg)
grep -rho 'createServerReference([^)]*' js/ | sed 's/.*("//' | head -40
# pattern: createServerReference("<40-hex>",callServer,void 0,findSourceMapURL,"saveNino")

# 2) Pair ids↔names by ORDER (robust when quotes are escaped in the chunk):
#    names = re.findall(r'findSourceMapURL,"([A-Za-z0-9_]+)"', src)
#    ids   = dedupe-in-order(re.findall(r'([a-f0-9]{40,})', src))
#    list(zip(names, ids))

# 3) Server-rendered forms reveal the LIVE action id + field names directly:
grep -oE '\$ACTION_ID_[a-f0-9]+' page.html
grep -oE '<input[^>]*name="[^"]+"' page.html      # e.g. name="interval" value="annual"
```

Beware: some bundles store escaped content (`"` not `"`). Python `re.findall` on the raw
text handles both; a shell grep for `name:"x"` will silently return nothing.

## 3. Capture the real request (the only reliable path)

`evaluate` runs in an **isolated world** and cannot see the page's `fetch`. Inject a
main-world `<script>` that wraps `fetch` + XHR and hands results back via a DOM attribute:

```js
// injected via: <script>textContent = <this code>; appendChild; remove()</script>
window.__cap=[];
const save=()=>document.documentElement.setAttribute('data-cap',JSON.stringify(window.__cap.slice(-20)));
const of=window.fetch;
window.fetch=function(a,b){try{var o=b||{};var h={};
  if(o.headers){o.headers.forEach?o.headers.forEach((v,k)=>h[k]=v):Object.assign(h,o.headers);}
  var bd=o.body;
  if(bd&&typeof bd!=='string'){try{ if(bd instanceof FormData){var p=[];bd.forEach((v,k)=>p.push(k+'='+v));bd='FD{'+p.join('&')+'}';} else bd=JSON.stringify(bd);}catch(e){}}
  window.__cap.push({u:typeof a==='string'?a:a.url,m:o.method||'GET',h:h,b:String(bd).slice(0,2500)});save();
}catch(e){}
return of.apply(this,arguments);};
```

Drive the real UI action once (click/type), then read `document.documentElement[data-cap]`.
You now have the exact URL, headers, and FormData field names.

## 4. Replay — required headers + body

```http
POST /app/sources/<uuid>?new=1
next-action: <40-hex id>
accept: text/x-component
next-router-state-tree: <see builder below, URL-encoded>
content-type: multipart/form-data; boundary=----WebKitFormBoundary…
origin: https://<target>
referer: https://<target>/app/sources/<uuid>
cookie: qw_session=<...>
```
```
FormData (field names prefixed _1_):
  _1_submissionId=092174f3-…        <-- idempotency key (server dedupes duplicates)
  _1_propertyId=<uuid>
  _1_type=income
  _1_category=turnover
  _1_amount=1000.00
  _1_txnDate=2026-09-01
  0=[{},"$K1"]                      <-- client-reference tail
```

**Router-state-tree builder** (must mirror a real tree or the action 404s "could not be
found" even for your own object):

```python
import json, urllib.parse
def rst(*segs):                       # e.g. rst('app','sources',('id',SRC_UUID))
    cur = ["__PAGE__", {}, None, None]
    for s in reversed(segs):
        cur = {"children":[[s[0], s[1], "d"], cur, None, None]} if isinstance(s,tuple) \
              else {"children":[s, cur, None, None]}
    return urllib.parse.quote(json.dumps(["", cur, None, None, True]), safe='')
```

## 5. Reading the result

| Response | Meaning |
|---|---|
| `1:E{"digest":"…"}` | **shape error** — wrong tree/fields/id; fix, don't conclude anything |
| `200` + `{"error":"Only the owner can change these settings."}` | action RAN; **authz enforced server-side** |
| `200` + real data/redirect | action ran; inspect for the actual impact |

Server Actions in a well-built app are plain server functions that re-check ownership. The
"Server Action auth bypass" hypothesis (crown-jewel in `hunt-nextjs`) only pays when the
action **lacks its own guard** — test the guard, never assume client-side-only enforcement.

## 6. RSC reflection guard — `?param=` echo is NOT LFI/SSTI/XSS

RSC serialises query params into the flight payload, so your input is echoed back and looks
alarming (`?ty=<payload>` appears in the HTML). It is state serialisation, not a sink.

```bash
# baseline FIRST — does the marker already exist on the clean page?
#   (a bare "49" hit on a page that already contains 49 = artefact, not SSTI)
?ty={{1337*3}}               → response contains 4011?      NO  = literal echo, not evaluated
?ty=../../../../etc/passwd   → response contains root:x:0?  NO  = path echoed only
?ty=<script>alert(1)</script>→ contains RAW <script>alert(1)? NO = serialised \u003cscript\u003e, inert
?ty=x%0d%0aX-Injected:yes    → response header X-Injected present? NO = no CRLF injection
```

Values reflected into RSC JSON with `\u003c` / `\u003e` escaping are inert. A size delta in
the response is expected (your string is longer) and proves **nothing** — always
body-diff content, never infer from status/size alone.

## 7. Tool-targeting corollary (ties to RULE 2b/2c)

Real tools must be aimed at the **parameterised, authenticated** surface, not the root:

- `sqlmap -u https://target/` → "no parameter(s) found" = a no-op. Use a real param URL
  (`/app/other-income?ty=2026-27`) **plus** `--cookie` for the session.
- Same for ffuf/dalfox/arjun on the app surface: pass `-H "Cookie: …"` and a param URL.
- Static root pages have no state to race/mutate — a green verdict there is meaningless.
- If a whole run reports "not injectable / 0 results", retry once with the session cookie and
  a parameterised URL before recording a NEGATIVE — otherwise you've tested nothing.
