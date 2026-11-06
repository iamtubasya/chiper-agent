---
name: aem-attack-surface
description: Use when target runs Adobe Experience Manager (AEM) CMS.
version: 1.0.0
author: Hermes Curator
license: MIT
metadata:
  hermes:
    tags: [security, aem, bug-bounty, web, adobe, cms]
    related_skills: [bb-methodology, security-web-attacks, hunt-dispatch]
---

# Adobe Experience Manager (AEM) — Attack Surface Testing

## When to Use
- Target fingerprint shows Adobe Experience Manager / Adobe CMS (tech detect or the page markers below).
- Bug bounty / VDP / web-app pentest against enterprise sites (finance, insurance, government, retail) built on AEM.
- You've mapped a site and see `/etc.clientlibs/`, `/content/<site>/en/` URL shapes, or `/bin/` servlets.

AEM is one of the most common enterprise CMS platforms in bug bounty (finance, insurance, government, retail). Its dispatcher (Apache/CloudFront edge) is the security boundary — bypass it and the full Sling/CRX surface opens up. This skill is the proven playbook from an authorized VDP engagement (RACV, see `references/racv-vdp-2026.md`).

## 1. Fingerprint AEM
- Tech detect: `Adobe Experience Manager`, `Java`, `Apache`, AWS/CloudFront/ALB in httpx output.
- Page source markers: `/etc.clientlibs/<app>/clientlibs/*.min.js`, `ams=... (Enterprise)`, `tier=publish` in Helix RUM script, `.adm-panel`, `/content/<site>/en.html` URL shape, `/bin/` servlets.
- HTML `meta http-equiv="Last-Modified"` or `data-routing="env=prod,tier=publish"` — confirms AEM even when tech detect misses it.
- robots.txt often reveals structure: `Disallow: */content/<site>/en/*`, sitemap-index.xml.

## 2. Oracle-based dispatcher bypass testing (KEY METHOD)
The dispatcher blocks most Sling paths with uniform 403/404. Test bypasses WITHOUT guessing by using an **oracle**:

1. Find ONE endpoint that is intentionally exposed and returns 200 (e.g. `/bin/<app>/gdpr` → small JSON, or any public page).
2. Pick a BLOCKED target that would prove reach (e.g. `/bin/querybuilder.json` — dispatcher-blocked, returns 404).
3. Apply each bypass variant to BOTH paths. Oracle still 200 + target changed from 404 = bypass signal. Target still blocked while oracle 200 = variant neutralized.
4. Variant matrix to run (tested 2026-09, all neutralized on hardened RACV):
   - Path normalization: `//`, `/bin//x`, `\`, dot-segments, trailing slash
   - URL-encoding: `%2f`, `%252f`, `%00`, `%0a`, `%0d`, `%3b`, `%23`, `%3f`, `%26`, overlong UTF-8 (`%ef%bc%8f`, `%c0%ae`)
   - Semicolon matrix: `;.css`, `;a=1`, `;param=value`
   - Selector/extension tricks: `.css`, `.sling.json`, `/a.css`, `.zzz`
   - Case: `/GDPR`, `/QueryBuilder`, `/Bin/`
   - Headers: `X-Original-URL`, `X-Rewrite-URL`, `X-Custom-IP-Authorization`, `X-Forwarded-URL`, `X-Forwarded-Host`, `X-Host`, `X-Original-Host`, `X-Forwarded-For`, `X-Real-IP`, `True-Client-IP`, `CF-Connecting-IP`
   - Absolute-URI request line (raw socket, HTTP + HTTPS)
   - Verbs: POST/OPTIONS/PUT/PATCH to blocked GET paths
   - `wcmmode=edit|preview` on page URLs (author-mode trick)

## 3. Error-size differential — read the dispatcher's mind
Hardened AEM behind CloudFront returns distinctive body sizes you can use as a triage oracle:
- Dispatcher 404 soft page: **ONE fixed size** (e.g. 134356 for racv.com.au vs 23072 for a microsite — varies per site, fix it once per target).
- AEM generic soft-500 page: **DIFFERENT fixed size** (e.g. 136137) — means the request REACHED AEM and failed inside the servlet (not a dispatcher block, and NOT a live endpoint either).
- A `500` on `/graphql/execute.json/global` was NOT a GraphQL finding — it's the generic AEM error page for ANY unknown servlet path. Confirm endpoints by body size, never by status alone. `x-cache: Error from cloudfront` also distinguishes edge-level blocks.

## 4. Clientlib JS mining — find the real endpoints
AEM ships app logic in `/etc.clientlibs/<app>/clientlibs/clientlib-<name>.min.js` (+ non-min variant often exists). These bundles are the single best source of hidden endpoints:
- Download all referenced clientlibs from page source (check `clientlib-forms`, `clientlib-<feature>`, `clientlib-critical`, `clientlib-base`).
- Grep for: `"/bin/...` paths, `data-path="..."` attributes on page HTML (React mounts read `data-path` for their JSON servlet — e.g. `data-path="/car-match/search.carmatchsearch.json"`), `?API=`, `baseURL:`, `urlConfig`, `captchaParam`.
- **Wire-format recovery**: minified code shows the EXACT POST body shape (e.g. axios `bi.create({baseURL: yi...})`, request builders like `{api:"Search", order:1, requestBody:{...}}`). Copy the shape literally — guessing field names wastes time.
- Page HTML `data-` attributes (`data-memberchoice`, `data-ajax-list`, `data-submit-url`) name the live integration points.

## 5. Default endpoint checklist (probe all, expect blocks on hardened)
```
/libs/granite/security/currentuser.json
/bin/querybuilder.json (GET + POST)
/bin/wcm/search/gql.servlet.json
/crx/de, /crx/packmgr/service.jsp, /crx/explorer
/system/console, /system/console/bundles.json
/etc.json, /etc/designs.json, /etc/packages.json
/content.json, /content/<site>.json, /content/<site>/en.infinity.json
page JSON selectors: .model.json .infinity.json .0.json .1.json /jcr:content.json
_bootstrap: /content/<site>/en/_jcr_content.json
Adobe Asset API: /api/assets.json, /api/assets/<tree>.json
GraphQL: /graphql/execute.json/<persisted>, /content/graphql/global/endpoint.json
Source maps: clientlib-*.min.js.map
```

## 6. DAM asset probing
- Image-sitemap (`/image-sitemap.xml`) frequently lists EVERY DAM asset → mine it for misplaced documents (PDFs in images/ folders, employee/confidential-named files).
- Rendition servlets intended-to-work: `asset.img.jpg`, `.imgwidth.N.jpg`, `.transform/<name>/image.jpg`, `jcr:content/renditions/original`.
- Metadata leaks: request `/jcr:content/metadata.json`, `.renditions.json`, `.dam.renditions.json`; check embedded XMP for GPS/author/internal hosts (most AEM XMP is clean: only dam:sha1/size).
- `/content/dam/...` root listing: usually 403.

## 7. AEM forms & member-validation endpoints (HIGH-VALUE: PII)
- Custom forms POST to `/bin/<app>/forms/<name>` (often `sendEmail` — Salesforce `__c` field names = mass-assignment surface; verify scope before abusing, contact forms are commonly excluded).
- Member validation components use markers: `data-membervalidationchoice`, `data-memberchoice`, `data-formtype="self service"`, form inputs `membershipNo`, `lastname`, `firstname`, `email` + hidden `MemberValidationChoice`, `dateOfBirth`, `g-recaptcha-response`, honeypot `altName`.
- Find the form page by grepping candidate URLs for the clientlib, or from visible CTA hrefs (`member-validation-<partner>.html`).
- Wire format requires hidden `:formResource`, `:formPath`, `pagePath` — copy from the rendered form's hidden inputs; guessing these yields 500s.
- **The finding pattern that pays** (see #8).

## 8. Versioned-vs-legacy endpoint control drift (PROVEN FINDING)
Common AEM bug: a v1 endpoint gets hardened (reCAPTCHA/CSRF/rate-limit added), but the **unversioned legacy path is still live without the control**.
- Discover both: the JS calls `/bin/<app>/v1/validateracvmember`; fuzz `/bin/<app>/validateracvmember` (drop `/v1/`) with the same body.
- Evidence recipe: same payload to both, side-by-side; legacy returns member-status JSON (`serviceDown`, `validRACVMember`, `category`, etc.) while v1 refuses without captcha token → control gap proven.
- Also verify captcha **consistency**: n=12 identical full-payload requests, count captcha-error vs validation-ran responses. If captcha enforcement is inconsistent (sometimes skipped), that alone is a bypass (retry/session rotation).
- No rate limit is a multiplier: burst 20 rapid requests, all 200 = automation-ready enumeration → PII exposure (success handler leaks `emailId`, `clientId`, encrypted auth token and auto-POSTs to partner `autUrl`).
- Always use fabricated/nonexistent IDs for PoC (no real-member enumeration) per program exclusions.

## 9. Funnelback / site-search backend (often overlooked)
Search suggestion config on the page (`data-ajax-list`, `data-funnelback-host`) reveals the search backend (e.g. `*-search.funnelback.squiz.cloud`):
- Public query API: `/s/search.json?collection=<c>&query=*&fmt=json&num_ranks=200&start_rank=N` → paginate to harvest the full index (start_rank works; `rank=`, `page=`, `offset=` may silently no-op returning the same first page — always verify page N differs from page 1).
- Diff harvested URLs vs public sitemap → find content indexed but not in sitemap (usually compliance PDFs; occasionally unpublished pages → real finding).
- Collection enumeration: guess `<org>~<name>` variants; only the documented one returns data (others 400). Admin/panel paths: none exposed on hardened setups.
- JSONP: `callback=` param reflects — harmless if sanitized; test breakout chars for XSS signal.

## Pitfalls
- Do NOT trust status codes alone — AEM soft-404/soft-500 pages are all 200/500 with fixed body sizes; use body size as the discriminator.
- A `500` generic page ≠ live endpoint. `/graphql/execute.json/global` → 500 means "reached AEM, no such servlet", not "GraphQL is on".
- Guessing `:formPath`/`:formResource` for member validation yields uniform 500s — pull them from the rendered page hidden inputs instead.
- Minimal-field POSTs to servlets return 500 soft ("needs full field set") — always send the complete rendered form payload.
- CloudFront rejects CL.TE/TE.CL smuggling at the edge (403 "request could not be satisfied") — don't burn time there behind AWS-fronted AEM.
- Burst fuzzing (ffuf 800+ paths) can trigger a temporary WAF state where even the known-200 oracle returns 403 — wait and re-verify the oracle before trusting "all blocked".

## References
- `references/racv-vdp-2026.md` — full session detail: endpoint maps, sizes, evidence recipes (RACV VDP, racv.com.au + bourkestreetgreen.com.au + arevo.com.au).