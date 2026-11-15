# RACV VDP 2026 — AEM Session Detail

Authorized engagement: Bugcrowd VDP "racv-vdp-pro" (Royal Automobile Club of Victoria). Mode VDP (points, no cash). Focus: OWASP Top 10, PII exposure, server misconfig, crypto weakness. Out of scope: *.racv.com.au (incl. my.racv.com.au), subdomain takeovers, rate limiting, contact/support forms, bulk exfil. N-Day: 45 days.

## Targets & stacks
| Target | Stack | Notes |
|---|---|---|
| racv.com.au | AEM, Java, AWS/CloudFront/ALB, Apache | `ams=Royal Automobile Club of Victoria (Enterprise)`, tier=publish |
| bourkestreetgreen.com.au | AEM (shared stack), CloudFront | Microsite — smaller dispatcher 404 size |
| arevo.com.au | Swift Digital T3 composer (PHP), Bootstrap 3, AWS Global Accelerator, New Relic | Legacy CMS, aggressive WAF + rate limit |

## Key fixed body sizes (discriminator values, racv)
- Dispatcher soft-404 (racv): **134356**
- Dispatcher soft-404 (bsg microsite): **23072**
- AEM generic soft-500 (both): **136137**
- CloudFront edge 403: ~1053 ("The request could not be satisfied")
- CloudFront edge 400: ~226 (450 for path bytes)

## Versioned-vs-legacy endpoints found (the winning pattern)
JS (clientlib-forms.min.js) called `/bin/racv/v1/validateracvmember` (captcha-enforced). Fuzzing `/bin/racv/validateracvmember` (unversioned) found a live legacy handler:

```
POST /bin/racv/validateracvmember   → 200 {"serviceDown":false,"validRACVMember":false,
    "validation-error":"...","golfMembershipFee":"242.00","cardColor":"NoMember",
    "category":"NoMember","discountMessage":""}        (no captcha required)
POST /bin/racv/v1/validateracvmember → 200 {"validation-error":"We couldn't verify
    reCAPTCHA, please try again."}                       (captcha enforced — or NOT, varies)
```

- v1 captcha enforcement consistency test: 12/12 identical full-payload requests in one session returned validation results (RAN) with NO captcha token; other sessions returned captcha-error for the same payload → server-side reCAPTCHA verification is unreliable = bypass by retry/session rotation.
- Rate limit test: 20 rapid legacy requests → 20/20 HTTP 200, no 429/403/Retry-After.
- Cross-target: identical behavior on bourkestreetgreen.com.au (shared AEM stack).

### Member-validation wire format (full rendered form payload)
```
:formResource=racvaem/components/content/form/membervalidation
:formPath=/content/racv/en/home/membership/member-discounts/member-validation-woolworths/jcr:content/root/container/membervalidation
pagePath=/content/racv/en/home/membership/member-discounts/member-validation-woolworths
urlData= (empty)
memberValidationChoice=normal  memberChoice=woolworth  MemberValidationChoice=normal
membershipNo=<9-digit>  lastname=<surname>  firstname=<first>  email=<email>  emailId=<email>
dateOfBirth=  g-recaptcha-response=  altName= (honeypot — leave empty)
```
Guessing `:formPath` (4 variants) or minimal fields → uniform 500 soft. Must copy hidden inputs from the rendered page.

### Success-path PII (from clientlib-forms.min.js)
```js
if(e.membershipNo || e.clientId && e.validRACVMember){
  var r = { clientId: e.clientId, memberId: e.membershipNo,
            firstName: encodeURI(e.firstname), lastName: encodeURI(e.lastname),
            emailId: e.emailId, memberClientTokenId: e.encryptedKey };
  // hidden form POST to e.autUrl (partner site — Ticketek/Woolworths/kynect)
}
```
Valid match → `emailId`, `clientId`, encrypted auth token disclosed to caller + auto-POST to partner `autUrl`. Form page `data-redirect="https://premier.ticketek.com.au/shows/show.aspx?sh=RACV"`.

## Dispatcher bypass variants all neutralized (40+)
Path normalization, URL-encoding matrix (%2f/%252f/%00/%0a/%0d/%3b/%23/%3f/%26/UTF-8 overlong), semicolon matrix, selector/extensions (.css/.sling.json//a.css), case tricks, header bypasses (X-Original-URL, X-Custom-IP-Authorization, X-Forwarded-*, X-Host, X-Real-IP, True-Client-IP, CF-Connecting-IP), absolute-URI raw socket, POST/OPTIONS/PUT/PATCH, wcmmode=edit. All 403/404 while gdpr oracle stayed 200.

## Other negative results (documented to avoid re-testing)
- GraphQL `/graphql/execute.json/global`: POST+GET → generic AEM 500 (136137) = servlet absent, NOT live GraphQL.
- AEM Asset HTTP API `/api/assets/*.json`: 404. Packmgr `/crx/packmgr/*`: 301→blocked. `_jcr_content` variants: 404.
- Source maps: 404. Stack-trace/error-page leaks: none.
- Host-header injection: Host-evil → 403; X-FH/X-Host ignored (body identical).
- CORS origin reflection: none on any JSON endpoint.
- Open redirect (racv 9 params, arevo 9 params): no absolute-external follow.
- Search XSS reflection (q/searchType/keyword/k/s): none.
- Funnelback index diff: 3241 harvested URLs vs 3044 sitemap → only homepage artifact + 294 public compliance PDFs (PDS/TMD/WGEA — legally public). No unpublished content.
- DAM 17,296 assets: images only; 6 "documents" benign; XMP clean (dam:sha1/dimensions only).
- Legacy WebSphere `.do` paths from gau: 301→404 dead. `/wps/*`: redirect home.
- Request smuggling TE:CL/CL:TE via raw socket: CloudFront 403 edge reject.
- CRLF via %0d%0a in 301 Location: no header injection.
- arevo.com.au (Swift Digital): `/login/` = Swift Digital Suite admin portal (CSRF pl_token validated server-side, rotating per session; reCAPTCHA enforced; no user enumeration — uniform SN05). subscribe.php GET-exact-format → 404 (auth-gated code 108 for lp.php). controller.php Base64+token → auth-gated. `/.env` 403 WAF (19 bypass variants failed). S3 prod-swiftdigital-staticassets → AccessDenied. Ports: 80/443 only.

## WAF/bot notes
- ffuf 833-word burst on /bin/racv/* → ALL 403 len=919 (even known-200 gdpr) = temporary WAF state; oracle recovered 200 after pause. Always re-verify the oracle before trusting "all paths blocked".
- arevo aggressively rate-limits (429) at >1 req/10-15s — slow sequential probing required.