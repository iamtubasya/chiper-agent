# RACV VDP — Membership Entitlement Trust Case (2026-09-26)

Worked example of the client-state trust class on an AEM travel/membership portal.
All values reproduced live against racv.com.au. Times/dates set to the original session.

## Target surface
- Portal: https://www.racv.com.au (Adobe Experience Manager + CloudFront; shared backend
  with bourkestreetgreen.com.au).
- Resort booking widget: /travel-experiences/resorts/search.html
- Search API: `/bin/racv/v1/resortSearch` (GET, JSON)
- Member validation APIs (legacy + v1): `/bin/racv/validateracvmember` and
  `/bin/racv/resortMemberValidation` (unversioned); `/bin/racv/v1/...` (versioned, reCAPTCHA).

## Finding A — client-cookie member pricing (P3 Medium, reproducible)

Wire format from clientlib-resorts.js (recovered from page script tags):
```js
r = { resortIds: h.where_param, membershipNo: h.membership_id, lastName: h.member_lastname } // member validation POST
l = { keyResorts, startDate, endDate, adults, kids, promo, memberType, submember, timestamp } // resortSearch GET params
```
Actual working GET (dates MUST be ISO `YYYY-MM-DD`; other formats 500):
```
/bin/racv/v1/resortSearch?resortIds=72447,72448,72450&startDate=2026-10-01&endDate=2026-10-05&adults=2&kids=0&type=s
```

### Differential (resort 72447 Cobram, 2 adults 01-05 Oct):
| Cookie state | minPrice | rate plans | booking URL fragment |
|---|---|---|---|
| none (guest) | 357.0 | 3 (non-member) | — |
| `memberType=RACV_CLUB_MEMBER; membershipId=1` | 201.0 (-44%) | 6 incl. "Room Only - RACV Club Member" (RATEPLANID 2334498) | `identifier=RACVCLUB&RATEPLANID=2334498` |
| `memberType=RACV_MEMBER; membershipId=1` | 268.0 (-25%) | 7 incl. "Long Stay Saver - RACV Member" | `identifier=RACV&RATEPLANID=10939647` |

Membership number or lastname are NOT checked: 2 fabricated cookies are sufficient.
Param `memberType=` alone is ignored; server reads the COOKIE.
Only `RACV_CLUB_MEMBER` and `RACV_MEMBER` trigger member rates (not AUTO_CLUB_MEMBER etc).

### Honest scope (kept in report, avoided overclaim)
- Final checkout is a third party: `https://reservations.travelclick.com/...`
- RACV disclaimer: "member card required at check-in"
- => Reported as P3 access-control/pricing-disclosure, NOT free/discounted booking.

## Finding B — legacy endpoint reCAPTCHA gap (P4 Low, cross-target)

Identical POST body (woolworths flow):
```
membershipNo=1234567890&lastname=Test&firstname=Test&email=test@example.invalid
&memberValidationChoice=normal&memberChoice=woolworth&g-recaptcha-response=&altName=
```
- `POST /bin/racv/validateracvmember` -> HTTP 200 member-lookup JSON, NO captcha check
- `POST /bin/racv/v1/validateracvmember` -> `{"validation-error":"We couldn't verify reCAPTCHA, please try again."}`
- Same gap on `resortMemberValidation` (legacy 200 empty body; v1 captcha-blocked)
- Same gap on `https://www.bourkestreetgreen.com.au/bin/racv/validateracvmember` (shared backend)

### Honest scope (kept in report)
- Only fabricated member numbers used; no real enumeration, no PII retrieved.
- PII leak on a valid match (clientId/emailId/encryptedKey via success handler) is
  INFERENTIAL — that premise kept severity at P4.
- Program excludes rate limiting; framed as reCAPTCHA control gap instead.

## Tool-chain notes that found these
1. `katana -d 2 -jc -kf all` surfaced `/bin/racv/hotelbooking.data.json`,
   `resortMemberValidation`, `promoCode`, `getOfferLink` — endpoints absent from sitemaps.
2. Page HTML script tags pointed to `clientlib-bau/clientlib-resorts.<hash>.js` — that
   bundle contained the true wire formats AND the success handler that sets
   `membershipId=1`/`memberLastname`/`memberType`/`memberTypeDiscount` cookies.
3. `resortSearch` param is `resortIds` (JS), NOT `keyResorts`; wrong param -> `Invalid
   input parameters` with `resortIds:[]` echo.
4. Curl-only guessing had failed for hours; the differential cookie test + JS wire
   format took minutes.

## Delivered artifacts (reference for format)
- report/F1-* PDF: 4 pages, 3 embedded POC screenshots, no watermark
- report/F2-* PDF: 4 pages, 3 embedded POC screenshots, no watermark
- report/SUBMISSION_GUIDE.md: Bugcrowd VRT mapping + paste-ready workflow
- POC screenshots generated with Pillow terminal-style (dark bg, no watermark).