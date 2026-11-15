---
name: hunt-aem
description: "Use when hunting Adobe Experience Manager sites."
metadata:
  hermes:
    tags: [aem, adobe, sling, dispatcher, cms, bug-bounty, security]
---

# AEM (Adobe Experience Manager) Hunting

Use when the target runs AEM — Adobe Experience Manager (Sling/JCR/OSGi, AEM Sites, AEM Forms, AEM Assets). Fingerprint signals: `https://rum.hlx.page/.rum/@adobe/helix-rum-js`, `/etc.clientlibs/<app>/clientlibs/*.min.js`, `granite/csrf` clientlib, `aem-Grid` CSS classes, `adobeDataLayer`, `assets.adobedtm.com/launch-*.min.js`, `content/dam/` paths, `ams=... (Enterprise)` helix data attr, `data-routing="env=prod,tier=publish"`.

## 0. Calibrate the error-page oracle FIRST (before any bypass work)

A hardened dispatcher returns a **custom soft-404 HTML** for blocked paths; a request that REACHES AEM but fails returns a **different generic AEM error page**. These are byte-constant per site — measure them:

```
GET /bin/querybuilder.json          → dispatcher soft-404 (e.g. lens 134356, ct text/html)
POST /graphql/execute.json/global   → AEM soft-500 (e.g. lens 136137)  # servlet ABSENT, not "live GraphQL"
GET /bin/<app>/gdpr (known benign servlet) → 200 JSON  # use as ORACLE
```
- A 200-JSON endpoint under `/bin/<app>/` is your **oracle**: it proves a request variant reached AEM.
- **Pitfall:** a `500` with the generic AEM error page ≠ the endpoint exists. Only a small JSON body (or a body-length that differs from both constants) is a signal. Don't claim GraphQL from `execute.json` 500s.

## 1. Dispatcher bypass — ORACLE METHOD

The dispatcher (Apache/mod_rewrite in front) blocks `/libs`, `/crx`, `/system/console`, `querybuilder` etc. Don't test blind — use the oracle:

1. Baseline both endpoints: oracle (200 JSON) and target (404 soft).
2. Send the SAME normalization variant to both; bypass signal = oracle stays 200 **AND** target status/length changes from baseline.
3. Variant matrix (test all):
   - Path: `//x`, `/x//y`, backslash, `/./x`, `/x/../y`, trailing slash, semicolon matrix (`;.css`, `;a=1`...)
   - Encoding: `%2f`, `%252f`, `%00`, `%0a`, `%0d`, `%3b`, `%23`, `%3f`, `%26`, overlong UTF-8 (`%ef%bc%8f`), `%c0%ae`
   - Selector/extension: `.json.css`, `.sling.json`, `.zzz`, `/a.css` on the blocked path
   - Case: `/QUERYBUILDER`, `/QueryBuilder`
   - Headers: `X-Original-URL`, `X-Rewrite-URL`, `X-Custom-IP-Authorization`, `X-Forwarded-URL`, `X-Forwarded-Host`, `X-Host`, `X-Original-Host`
   - Methods: POST/OPTIONS/PUT/PATCH to querybuilder, absolute-URI request line (raw socket)
   - IP-spoof headers on 403 admin paths: `X-Forwarded-For: 127.0.0.1`, `X-Real-IP`, `Client-IP`, `True-Client-IP`, `CF-Connecting-IP`
4. `?disableCaptcha=true` on servlet URLs often 301-strips before AEM — don't treat the 301 as a bypass.

## 2. Endpoint inventory (default AEM attack surface)

Probe these — all should be blocked on a hardened target; any 200/small-body is finding material:
`/bin/querybuilder.json`, `/libs/granite/security/currentuser.json`, `/crx/de`, `/crx/explorer/browser/index.jsp`, `/crx/packmgr/service.jsp?cmd=ls`, `/system/console`, `/system/console/bundles.json`, `/etc.json`, `/etc/designs.json`, `/content.json`, `/content/<app>.json`, `<page>.infinity.json`, `<page>.tidy.infinity.json`, `<page>.model.json`, `/content/<page>/_jcr_content.json`, `/api/assets/*.json`, `/etc/packages.json`, `/graphql/execute.json/<persisted-query>`, `/content/graphql/global/endpoint.json`, `/libs/granite/csrf/token.json`, `/content/dam.json`, `/var.json`, `/home.json`, `/apps.json`.

**Content pages are vanity-rewritten** (`/insurance` → `/insurance.html`); `/content/<app>/en.json` is dispatcher-blocked. Test `wcmmode=edit/preview` (should render normal page — no author mode) and `?debug=1`.

## 3. Clientlib JS mining — hidden servlets & wire formats (HIGH VALUE)

Download `/etc.clientlibs/<app>/clientlibs/*.min.js` (non-min `*.js` exists too — fetch both, they differ):
- grep for `"/bin/..."`, `data-path`, `data-ajax-list`, `data-ajax-list-suggestion`, `API=` params, `.ajax({`, `fetch(`, `axios`
- **`data-path` attrs in page HTML** point at Sling JSON servlets (e.g. `<div id="filtersearchresult" data-path="/car-match/search.carmatchsearch.json">`) — always grep page HTML for `data-path`!
- **Minified axios wiring**: find `baseURL:` + `.interceptors.request/response.use` to reconstruct exact request format; `?_a=function...` / `vi(si,...)` builders reveal JSON body shape (`{"g-recaptcha-response":"","requestPayload":[{api:"Search",order:1,...}]}`).
- **`?disableCaptcha` is read by JS from the PAGE URL** (`new URL(window.location.href).searchParams.get("disableCaptcha")`) — sending the page's own URL with `?disableCaptcha=true` and a valid captcha token can bypass client-side gating; server-side must still be checked independently.

## 4. AEM Forms / member-validation endpoints (PII surface — priority)

AEM Forms with "self service" forms expose validation servlets. React pattern:
- Mine `clientlib-forms.min.js` for endpoint paths (`/bin/<app>/v1/validate...`, `/bin/<app>/forms/sendEmail`...) and the **exact POST body** (`:formResource`, `:formPath`, `pagePath`, form fields, `g-recaptcha-response`, honeypot `altName`).
- `:formPath` is a JCR path under the page (`.../jcr:content/root/container/<component>`); fuzz the component node name if unknown — servlet runs regardless.
- **LEGACY vs VERSIONED ENDPOINT DRIFT — the money bug.** Test the SAME endpoint with and without version prefixes (`/bin/<app>/validatemember` vs `/bin/<app>/v1/validatemember`). Security controls (reCAPTCHA, rate limit, auth) are frequently added to the new path only and the old unversioned path keeps working without them.
- **Control-gap proof template:** same POST body to both paths; one returns the full result object (`serviceDown`,`validRACVMember`,`cardColor`,...), the other returns `{"validation-error":"...reCAPTCHA..."}`. Then burst 20 requests to the legacy path to prove no rate limit (20/20 200).
- On valid members the frontend JS builds identity data (`clientId`, `emailId`, `encryptedKey` token) and auto-POSTs it to partner `autUrl` — quote the minified success handler as impact evidence. Use only fake numbers for PoC (no real-member brute force).

## 5. DAM / Assets

- Known asset + `.img.png` / `.imgwidth.N.png` / `.transform/<name>/image.jpg` = intended rendition servlets (not a bug).
- `.<ext>.json`, `/jcr:content/renditions.json`, `/jcr:content/metadata.json`, `assetdownload.html`, `/api/assets/*.json` — usually blocked; test anyway.
- Mine `image-sitemap.xml` (`<image:loc>` — often millions of bytes, includes PDFs/documents tucked in odd folders like `images/.../legacy-imagery/`).

## 6. Search backend as recon surface (Funnelback / Algolia style)

Page JS exposes the search engine: `data-ajax-list="https://<x>-search.funnelback.squiz.cloud/s/suggest.json?collection=<coll>"` + `data-funnelback-host`.
- `s/search.json?collection=<coll>&query=*&fmt=json&num_ranks=200&start_rank=N` — **`start_rank` paginates** (rank/offset/page often silently return page 1; verify page 2 differs!).
- **Single-request full index dump**: `num_ranks=9999` returns ALL matching results in one response (3–6MB for a site-scale index) — harvest `liveUrl` fields and diff against the public sitemap. Any indexed-but-not-sitemapped HTML page = hidden/unpublished content lead. PDFs are usually compliance docs (PDS/TMD/annual reports) — not findings by themselves.
- Enumerate collection names (`<x>~cms`, `~staging`, `~intranet`...) — invalid returns 400, valid returns 200 JSON. **403 on a leaked collection name = protected/internal** (name alone is intel, access is not).
- **JSONP callback grammar**: `callback=` reflects only grammar-valid JS identifier chains (`cb`, `$`, `a.b`, `jQuery` → 200, content-type `application/javascript`, body prefixed `/**/`); anything with parens/braces/backticks (`alert(1)`, `a['b']`) → 400/403 at the WAF. Query strings reflect into JSON `originalQuery` (string context) and HTML error views — test encoding orders there, not the callback.
- **DEBUG LEAK (high-value recon on Funnelback)**: `debug=1` on `search.json` can turn a request into HTTP 500 with a ~127KB JSON body containing full Java stack traces (Spring/Log4j versions), env vars (`REMOTE_ADDR`, `REQUEST_URL`), internal paths (`/opt/funnelback/data/<coll>/live/log/queries-qp01-*.log`, `/opt/funnelback/bin/padre-sw`), query-processor options, AND **undocumented collection names** (`racv~ds-web`). Vendor-domain leak usually OUT of scope for the bounty — but mine it for collection names + backend version, then probe those collections. `debug=true` (not `=1`) is benign (adds only `additionalParameters.debug`).
- `/s/redirect?url=` open-redirect probes usually 400.

## Pitfalls
- Aggressive rate limiting (429 on >1 req/10s) is a target config, not a finding — slow down, single-thread, use the browser for JS-locked surfaces.
- Don't stop at "verify negatives" — after dispatcher/paths die, mine JS, fuzz `/bin/<app>/` with a real wordlist (ffuf 800+ words, watch for WAF switching everything to 403 — re-check the oracle), and diff versioned vs unversioned endpoints.
- `*.racv.com.au`-style wildcards and `my.` subdomains are usually OUT of scope on VDPs — read scope before chasing auth portals.

## References
- `references/racv-vdp-session.md` — full RACV VDP case study: endpoints discovered, error-page byte constants, oracle-byte-tables, the control-drift finding PoC, Funnelback harvest commands.
- `references/funnelback-search-backend.md` — reusable Funnelback/Squiz recipes: single-request full index dump (`num_ranks=9999`), debug-leak technique (`debug=1` → internal paths + protected collection names), JSONP callback grammar (identifier-chains only → no XSS), valid param matrix.
- `references/cdn-edge-filter-mapping.md` — AEM behind **Fastly/Akamai/Cloudflare**: identify the CDN from headers, classify paths by byte-stable response shape (`EDGE-EMPTY` / `EDGE-404` / `AEM-JSON` / `OTHER`) instead of status code, and the `/graphql/execute.json` family that the edge deny-list almost always misses (`x-vhost: publish` as the origin signal). Read this when the whole `.json` surface looks dead — it is usually the edge, not the origin. Covers the hybrid AEM + Edge Delivery Services layout (`/de/query-index.json`).
## Absorbed playbooks (complete sub-packages under `references/`)
- `references/aem-attack-surface/PLAYBOOK.md` — the second pass over AEM: fingerprinting, the
  error-size differential reading of the dispatcher, clientlib JS mining, default endpoint
  checklist, DAM probing, forms/member-validation PII surface, and the proven
  versioned-vs-legacy endpoint drift finding (`references/racv-vdp-2026.md`).
