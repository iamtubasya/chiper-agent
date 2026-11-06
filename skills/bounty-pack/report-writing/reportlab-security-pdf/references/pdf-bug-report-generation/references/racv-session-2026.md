# RACV VDP session (2026-09) — findings, wire formats, patterns

Authorized VDP engagement (bugcrowd.com/engagements/racv-vdp-pro). Two reportable
findings discovered; PDF reports generated with this umbrella skill.

## Scope (recap for future RACV work)
- In scope: racv.com.au, bourkestreetgreen.com.au, arevo.com.au (each with www).
- Out of scope: `*.racv.com.au` (incl. my.racv.com.au), subdomain takeovers,
  rate limiting, contact/support forms, bulk exfil.
- N-Day: 45 days. Points-based VDP (no cash bounties).

## Finding F1 (P3) — client-side membership cookies → member-rate pricing
- Endpoint: `GET /bin/racv/v1/resortSearch?resortIds=72447,72448,72450&startDate=2026-10-01&endDate=2026-10-05&adults=2&kids=0&type=s&memberType=book-as-guest`
- With cookies `memberType=RACV_CLUB_MEMBER; membershipId=1` → `minPrice` drops
  357 → 201 (-44%), 6 rate plans incl. member plan `RATEPLANID=2334498`,
  member booking URL `reservations.travelclick.com/72447?...identifier=RACVCLUB...`.
- With `memberType=RACV_MEMBER` → 268 (-25%).
- Root cause: resort booking widget JS (clientlib-resorts bundle) stores
  membership cookies client-side after validation; search API trusts them with
  NO server-side re-validation. VRT: Broken Access Control > Privilege Escalation.
- Honest boundary: final checkout on TravelClick + member card at check-in not
  proven → P3 not P2.

## Finding F2 (P4) — legacy validation endpoints bypass reCAPTCHA
- Unversioned endpoints perform member lookup with NO captcha:
  - `POST /bin/racv/validateracvmember` → JSON member status
  - `POST /bin/racv/resortMemberValidation` → HTTP 200 (empty)
- Versioned equivalents enforce captcha:
  - `POST /bin/racv/v1/validateracvmember` → `{"validation-error":"We couldn't verify reCAPTCHA..."}`
- Same on racv.com.au + bourkestreetgreen.com.au (shared AEM). Classic
  incomplete-migration control gap.

## AEM clientlib wire-format extraction pattern (reusable)
- Page HTML carries `data-*` attributes naming services:
  `data-validation-service`, `data-membership-validation-service`,
  `data-result-url`, `data-inventory`, `data-getdatefromserver`, `data-flexi-result-url`.
- Download the page-specific bundle (`/etc.clientlibs/racvaem/clientlibs/clientlib-bau/<hash>.js`
  referenced by the page) and grep for the endpoint + `$.ajax({url, data})` to get
  the REAL wire format — guessing params wastes hours (e.g. `keyResorts` is wrong,
  real param is `resortIds`).
- `clientlib-forms.min.js` contains the member-validation success handler that
  builds `clientId / emailId / encryptedKey (memberClientTokenId)` and auto-POSTs
  to partner `autUrl`.
- Member-validation pages found: member-validation-woolworths.html,
  member-validation-kynect.html, member-validation-klook.html
  (all under /membership/member-discounts/).

## Funnelback search backend (racv-search.funnelback.squiz.cloud)
- `data-ajax-list` / `data-ajax-list-suggestion` on every page → suggest.json/search.json.
- Full index dump: `search.json?collection=racv~sp-search&query=a&fmt=json&num_ranks=9999`
  (3186 URLs, all public). Pagination via `start_rank`.
- `debug=1` leaks 127KB stack trace (paths /opt/funnelback/...; vendor-owned domain).
- Hidden protected collection name leaked: `racv~ds-web` (403).
- Callback validator only allows identifier-chains → JSONP XSS not exploitable.

## arevo.com.au (Swift Digital)
- `/login/` = Swift Digital Suite portal; CSRF pl_token server-validated; rotating
  per session; no user enumeration (uniform SN05). Not a finding.
- `/.env` 403 WAF with no bypass (19 variants tested).
- Heavy rate limiting (~1 req/15s) → batch tools time out.

## Reporting meta used in the PDFs
- Researcher: Mr Fz (user's preferred alias).
- Date/time found + IP used are mandatory on this program's submission form.
- Evidence: real curl responses only; fabricated member numbers; note
  "fabricated data only" in disclosure.