# Replaying Next.js Server Actions for real (verified 2026, Next.js 15 App Router)

The naive "POST with a `Next-Action` header" recipe (seen in most hunt-nextjs checklists) almost
never fires a real action. Modern Next.js binds **encrypted** server-bound arguments and requires
a router-state header, so a plaintext action id alone returns an error digest. This is the recipe
that actually worked.

## Required request shape

| Part | Value |
|---|---|
| Method / path | `POST` to the **page route** that owns the form (e.g. `/app/sources/<uuid>?new=1`) |
| `next-action` | the 40-hex action id (lowercase) |
| `Accept` | `text/x-component` |
| `next-router-state-tree` | URL-encoded JSON of the RSC router tree (see below) |
| `Origin` / `Referer` | target origin / current page — **Origin is enforced**: an evil origin → HTTP 500 |
| `Content-Type` | `multipart/form-data; boundary=----WebKitFormBoundary<rand>` |
| `Cookie` | the authenticated session cookie |

## Router-state-tree (URL-encode the whole JSON)

```
["",{"children":["app",{"children":["sources",{"children":[["id","<uuid>","d"],
   {"children":["__PAGE__",{},null,null]},null,null]},null,null]},null,null]},null,null,true]
```

Nesting matters: a slightly different tree returned `{"error":"That property could not be found."}`
even though the uuid was valid. Build it programmatically and `urllib.parse.quote(..., safe='')`.

## FormData field naming

- Bound args arrive as **`_1_<name>`**: e.g. `_1_propertyId`, `_1_amount`, `_1_txnDate`,
  `_1_category`, `_1_type`, `_1_submissionId`, `_1_code`, `_1_email`, `_1_password`, `_1_interval`.
- Trailing reference slot: `0=[{},"$K1"]`.
- Real apps also send fields you would never guess (e.g. `_1_fph` — a device-fingerprint blob with
  timezone, screen size, UA, public IP). **Do not guess field names** — capture the for real.

## Capture the app's own request (highest fidelity)

From a live authed page, inject a **main-world** `<script>` (via `/tabs/{id}/evaluate`) that wraps
`window.fetch` **and** XHR, serialises `FormData` to `key=value`, and writes the log to
`document.documentElement.setAttribute('data-cap', JSON.stringify(log))`. Read that attribute from
`/evaluate` (isolated world) — same DOM-attribute handshake used for captcha work. Then replay with
the exact captured shape (names + tree + headers).

## Extracting action ids + names from chunks

```bash
# createServerReference("<40hex>",callServer,void 0,findSourceMapURL,"<name>")
grep -oE 'findSourceMapURL,"[A-Za-z0-9_]+"' *.js    # names, in file order
grep -oE '[0-9a-f]{40,}' *.js                       # ids, dedupe in order → zip with names
```

Get the chunk list from the live page: `performance.getEntriesByType('resource')` filtered on
`chunks` — this reveals route chunks loaded after client-side nav (`…/app/sources/%5Bid%5D/page-<hash>.js`).

## Reading responses (do not misread)

| Response | Meaning |
|---|---|
| `303 See Other` + `Location` | action ran and redirected (usually success) |
| `200` + `{"error":"<msg>"}` | action ran; normal business validation error |
| `200` + `1:E{"digest":"…"}` | handler threw — usually **wrong shape/args**, NOT an auth block |
| `500` + empty body | malformed request (e.g. wrong Content-Type for a form action) |
| `307` → `/login` | middleware/session gate (unauth) |

Encrypted bound args mean an ERROR digest is **ambiguous** — always compare against the same
request with a valid session/shape before concluding anything about authorisation.

## FALSE-POSITIVE GUARD: RSC reflection is not XSS / LFI / SSTI

Query params are serialised into the flight payload
(`self.__next_f.push([1,"…__PAGE__?{\"ty\":\"<input>\"}…"])`), so injected strings **appear in the
response**. dalfox and friends flag this as "reflected param". It is state serialisation, not a sink.

| Claim | Disproof |
|---|---|
| XSS | payload must appear **raw**; Next serialises `<` as `\u003c` / `&lt;` → not executable |
| SSTI | use a **unique** expression (`{{1337*3}}`) and require `4011`; a literal echo is not evaluation |
| LFI | require file content (`root:x:0`), not the reflected path string |
| baseline drift | grep the **clean** page for the expected value first — a `49` already in the template made `{{7*7}}` look like a hit |

Locally, verify the DOM result in a real browser (navigate to the payload URL, read a sentinel like
`document.title`) rather than by substring presence in the flight payload.
