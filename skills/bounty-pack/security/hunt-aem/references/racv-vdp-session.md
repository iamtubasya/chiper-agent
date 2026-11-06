# RACV VDP Session — AEM Hunting Case Study (2026-09)

Engagement: Bugcrowd VDP, in scope = racv.com.au/www, bourkestreetgreen.com.au/www, arevo.com.au/www. Out of scope = *.racv.com.au (incl. my.racv.com.au), subdomain takeover, rate limiting, contact/support forms. Focus = PII exposure, OWASP, misconfig, crypto.

## Error-page byte constants (oracle calibration — racv.com.au)

| Probe | Status | Len | Meaning |
|---|---|---|---|
| `/bin/querybuilder.json` | 404 | 134356 | dispatcher soft-404 |
| POST `/graphql/execute.json/global` | 500 | 136137 | reached AEM, servlet absent (generic fail page) |
| `/bin/racv/gdpr`, `/bin/racv/v1/gdpr` | 200 | 39 | benign JSON servlet = ORACLE |
| `/bin/racv/admin` | 403 | 919 | exists but blocked |
| bsg equivalents | 404 | 23072 | different site constant, same role |

Key: any response length diverging from these constants = real signal. The 136137 "soft-500" is NOT GraphQL presence.

## Dispatcher bypass outcome (exhaustive, all negative on this target)

Path norm, encoding matrix (%2f %252f %00 %0a %0d %3b %23 %3f %26, overlong UTF-8, %c0%ae), semicolon matrix, selector/extension, case, header-based (X-Original-URL, X-Rewrite-URL, X-Custom-IP-Authorization, X-Forwarded-*, X-Host), methods (POST/OPTIONS/PUT/PATCH), absolute-URI request line, IP-spoof headers → all 403/404. WAF note: after ~800 ffuf requests EVERYTHING went 403 (len 919 incl. the oracle) — re-check oracle after volume fuzz.

## Clientlib mining finds (reusable)

- `data-path="/car-match/search.carmatchsearch.json"` in page HTML → config-dump Sling servlet (leaks reCAPTCHA sitekey, `captchaParam=disableCaptcha`, urlConfig, shortlist/compare structure).
- Minified axios wiring: `baseURL` = `<origin>/bin/racv/caradvisory/`; body shape = `{"g-recaptcha-response":"","requestPayload":[{api:"Search",order:1,requestBody:{...}}]}`; `?disableCaptcha=true` on URL makes server 301-strip (not a bypass).
- 136137 response to `vehicleSearch` = backend NOT deployed (browser also NetworkError; JS build had `"MISSING_ENV_VAR".API_ENV` = pending deploy surface worth re-testing later).

## THE FINDING — legacy vs versioned endpoint drift

Form page: `/membership/member-discounts/member-validation-woolworths.html`
(also `-kynect.html`, `data-redirect="https://premier.ticketek.com.au/shows/show.aspx?sh=RACV"`)

Same POST body (form fields + `g-recaptcha-response=`) to:

```
POST /bin/racv/validateracvmember        # LEGACY unversioned
→ 200 {"serviceDown":false,"validRACVMember":false,"validation-error":"The member number or family name were unable to be validated. Please try again.","golfMembershipFee":"242.00","cardColor":"NoMember","category":"NoMember","discountMessage":""}
   → NO captcha check, performs real lookup

POST /bin/racv/v1/validateracvmember      # CURRENT versioned (used by live form)
→ 200 {"validation-error":"We couldn't verify reCAPTCHA, please try again."}
   → captcha enforced
```

Proof extras:
- 20 rapid legacy POSTs → 20/20 HTTP 200 (no rate limit / throttle headers).
- Same on bsg (`www.bourkestreetgreen.com.au`) — shared AEM stack.
- Clean-session repro on racv (fresh cookie jar) — same behavior.
- Empty/missing fields → `serviceDown:true` variant; garbage-but-present fields → `serviceDown:false` + validation-error → content oracle works.
- Impact path from clientlib-forms.min.js success handler: valid match returns `clientId`, `emailId`, `encryptedKey` (memberClientTokenId) then auto-POSTs hidden form to partner `autUrl` (Ticketek/Woolworths/kynect).

## Funnelback search-backend recon (reusable)

- Exposed on all pages via `data-ajax-list` + `data-funnelback-host` → `https://racv-search.funnelback.squiz.cloud`.
- Harvest: `s/search.json?collection=racv~sp-search&query=a&fmt=json&num_ranks=200&start_rank=N` — **start_rank works**; `rank`/`page`/`offset` silently return page 1 (verify page 2 differs before trusting pagination).
- 26 single + 137 two-letter queries → 3,241 unique URLs; diff vs sitemap (3,044) → only homepage HTML extra; 294 PDFs = compliance docs (WGEA/PDS/TMD/annual reports) — not findings.
- Collection enum (`racv~cms`, `~staging`, `~intranet`, `~dev`...) → 400 invalid, only real collection 200.
- JSONP `callback=` reflects (`/**/cb(...)`); dangerous callbacks (`alert(1)`, `;`, `}`) → WAF 403; `x]});` returned JSON (no JS context) — no exploitable XSS.
- `/s/redirect?url=` → 400 (no open redirect).

## Other dead ends (one line each)

- Salesforce Experience Cloud shell on racv (`/membership/account/login.html`) → 302 to my.racv.com.au (out of scope); SF endpoints 404 at dispatcher.
- `/content-test/...` orphan page = byte-identical copy of prod page (only missing gscope-title) — no leak.
- DAM image-sitemap (17,296 assets) — only images + map PDFs; rendition servlets = intended; no metadata leak.
- arevo.com.au = Swift Digital CMS: `/login/` (Swift Digital Suite admin) CSRF-protected (rotating pl_token), reCAPTCHA, uniform SN05 (no user enum); `/.env` WAF 403 (all bypasses fail); subscribe/controller endpoints auth-gated; naabu top-1000 = only 80/443.
- Legacy `.do`/`wps` WebSphere paths → 301→404 dead.
- CRLF in 301 `Location` — sanitized. TE:CL / CL:TE smuggling — CloudFront 403. WCD `/page/foo.css` 200 but public page + cache Hit — no body diff, not a finding.
- Nuclei CVE/default-login/aem/adobe — 0 hits.

## Workflow lesson from this session

Three full rounds of "verify negatives" produced zero; the finding came only from (a) mining clientlib-forms JS for the exact POST wire format, (b) finding the live form page by following its vanity link, (c) testing BOTH version prefixes on the discovered validation servlet. Order: fingerprint oracle → dispatcher matrix → clientlib mining → form servlet wire-format reverse → versioned-drift check → rate-limit burst. That sequence is now the `hunt-aem` skill body.