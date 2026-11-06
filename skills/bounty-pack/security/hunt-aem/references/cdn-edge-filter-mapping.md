# Mapping what survives a CDN edge filter in front of AEM

Companion to `hunt-aem` §0/§1. Use when the AEM site sits behind **Fastly / Akamai / Cloudflare**
and the whole `.json` surface appears dead — because a blocked-path probe alone cannot tell
"dispatcher denied it" from "the edge never forwarded it".

Session that produced this: a Swiss bank's AEM publish tier behind Fastly. 55-path probe →
32× bare edge-404, 5× edge page, 14× Apache-404, **4× AEM origin**. The 4 were the whole finding.

## 1. Which CDN, before anything else

Read the headers on any 200 response:

```
X-Served-By: cache-fra-eddf8230198-FRA, cache-iad-kiad7000105-IAD
X-Cache: MISS, MISS, MISS, HIT
X-Timer: S1791838858.507503,VS0,VS0,VE21
```
`X-Served-By` + `X-Cache` + `X-Timer` = **Fastly**. Fastly's own VCL error page is identifiable by
the body string **`Error 54113`** — a ~398-byte XHTML page titled `Error 404` that is *not* an
AEM 404 and *not* an Apache 404. Seeing `54113` means Fastly answered, so nothing behind it ran.

Akamai uses `X-Akamai-Transformed` / `Server: AkamaiGHost`; Cloudflare uses `CF-Cache-Status`
and `cf-ray`. Identify the layer first — the fix for each is a different config file.

## 2. Classify by byte-stable response shape, not by status code

Status codes are useless here: the edge, the dispatcher and AEM all emit 404. Classify on
`(status, content-type, body-length, body-snippet)`:

| class | signature | meaning |
|---|---|---|
| `EDGE-EMPTY` | `404` + `text/plain; charset=utf-8` + **0 bytes** | edge dropped it; origin never saw the request |
| `EDGE-404` | `404` + `text/html` + a fixed size (here 4000 / 59962 / 4447) | edge custom 404 page — body is byte-constant, measure it once |
| `AEM-JSON` | `application/json` + body contains `"errors"` with `errorType` | **ORIGIN REACHED** |
| `OTHER` | `text/plain` + 13 bytes `404 Not Found`, or Apache `iso-8859-1` 236-byte 404 | dispatcher/Apache reached — a different layer again |

Print the class counts at the end; a table of 55 identical rows proves nothing, but
`Counter({'EDGE-EMPTY': 32, 'EDGE-404': 5, 'OTHER': 14, 'AEM-JSON': 4})` shows where the hole is.

## 3. `/graphql/execute.json` is the path that is usually NOT filtered

Observed on hardened AEM installs: the edge deny-list covers `/content/*`, `/etc*`, `/apps`,
`/var`, `/home`, `/tmp`, `/libs/*`, `/bin/*`, `/crx/*`, `/system/*`, `.infinity.json`,
`.model.json`, `jcr:content*` — and misses the GraphQL servlet, because it was added to the product
later than the filter rule.

Four unauthenticated probe shapes establish the servlet is live and what it discloses:

```
GET  /graphql/execute.json            -> 204, 0 bytes      (servlet present, no suffix)
GET  /graphql/execute.json/gkb        -> 400 ServletError "Suffix: '/gkb' does not contain a path"
GET  /graphql/execute.json/gkb/global -> 404 PersistenceError
       {"details":"Configuration: 'gkb' and Query Name: 'global' does not resolve to an
        existing Persisted Query"}
POST /graphql/execute.json            -> 403                (write path blocked at edge — good)
```

**What that discloses with zero data returned:** the internal GraphQL **configuration name**
(`gkb` here — the AEM content-structure root), the confirmation that a publish tier sits behind the
edge, and the servlet's error taxonomy. Enumerate persisted-query names against that configuration
(`global home site navigation footer search page article product content main default all pages`
is a useful starter set). 16 names, all unresolved on this target → no content leaked, and the
report said exactly that.

**Always check CORS on the surviving path** — it is the one path where an origin misconfiguration
would turn an info-leak into a cross-origin data read. Four hostile origins returned no
`Access-Control-Allow-Origin` here. Also check `OPTIONS`: some builds advertise `TRACE` in the
`Allow` header, which is worth recording even without a working TRACE-XST.

## 4. Confirm it is the AEM publish tier with one header

`x-vhost: publish` in the surviving path's response names the vhost, i.e. the tier. Its siblings
`x-sky-isauth: 0` (auth gate off) and `set-cookie: affinity="..."; HttpOnly; secure`
(sticky-session affinity) confirm the request landed on a load-balanced publish node rather than
an edge cache of a static asset.

## 5. Hybrid AEM + Edge Delivery Services — check for EDS before assuming classic AEM Sites

If marketing pages are served from `/de/...` with `/scripts/aem.js` + `/styles/*.css` and there is
**no** `/.content.xml`, the site is AEM **Edge Delivery Services** (formerly Franklin). Then these
work where the classic surface does not:

```
GET /robots.txt           -> "Sitemap: https://host/sitemap-de.xml"
GET /de/query-index.json  -> 200, ~776 KB, {"columns":[...],"data":[1505 rows],"total":...}
```
The query index is the whole published content inventory — `path`, `title`, `description`,
`lastModified`, `robots`, `cq-tags`, `contenttype`. It is **intended to be public**, so it is not a
leak; but it is the fastest estate map available, and entries whose `robots` field is non-empty or
whose `path` names an unpublished branch are worth chasing individually.

## 6. What to do with a surviving path

- **No data returned → hardening, not a finding.** Report it as informational with the exact
  deny-list fix, and state plainly that persisted-query enumeration resolved nothing.
- **Data returned → that is the finding.** Impact statement: "arbitrary published-content read
  without authentication, via a path family the edge filter forgot."
- **Do not claim GraphQL is "exposed" from a 500 or a 404** — the skill's §0 pitfall still applies.
  Only the small JSON envelope carrying an `errorType` proves the servlet actually ran.
