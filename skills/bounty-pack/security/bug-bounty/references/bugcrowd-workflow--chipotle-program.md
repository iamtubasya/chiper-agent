# Chipotle Bug Bounty Program — Program Details

Source: https://bugcrowd.com/engagements/chipotle-mbb-og (diakses 2026-08-23)

## Program Overview
- **Type:** Bug Bounty (managed), **Status:** In progress (sejak Aug 13 2024)
- **Scope rating:** 3/4, **Avg payout:** $308 (3 bulan terakhir)
- **Validated findings:** 61, **Triage:** 9 hari (75% dalam 3 bulan)
- **Safe Harbor:** ✅ CFAA/DMCA exempt, good-faith research lawful

## Rewards
| Priority | Bounty |
|---|---|
| P1 | $3,500 – $4,500 |
| P2 | $1,500 – $2,500 |
| P3 | $500 – $750 |
| P4 | $175 – $225 |
| P5 | Informational only (tidak di-reward) |

**Bonus $250** untuk finding P4+ yang disertai **Nuclei template UNIK** (bukan community template). Chipotle punya perpetual right atas template yang disubmit.

## In-Scope Targets
1. **Web:** `www.chipotle.com`, `www.chipotle.co.uk`, `catering.chipotle.com` (AEM + Vue.js)
2. **API:** `services.chipotle.com` (ASP.NET/C# — api gateway varnish)
3. **Mobile:** iOS `com.chipotle.Chipotle` (US) / `com.chipotle.Chipotle.eu` (UK); Android `com.chipotle.ordering` (US) / `com.chipotle.ordering.eu` (UK)

## Out of Scope (ringkas)
- In-store tech, international sites (chipotle.fr/de/ca), subdomain non-ordering-app
- Third-party software vulns, physical testing, rate-limit/DoS testing
- Missing cookie flags non-sensitive, public key exposure

## Rules
- **Header WAJIB:** `X-Bug-Bounty: Bugcrowd-<username>` (bukan X-Bugcrowd!)
- **Akun:** self-signup, WAJIB pakai email `@BC_ALIAS.com`
- Checkout: BOLEH test redeem rewards/points, add to cart, add card to wallet, redeem promo codes. **TIDAK support cancel order — jangan place order kalau tidak lapar.**
- Larangan: brute force, DoS, shell/backdoor, social engineering, target employee/customer/vendor, exfil PII, ganti password akun orang, public disclosure sebelum fix + approval
- Eligibility: first reporter, 18+, ex-employee 90-day cooldown, zero-day 30 hari setelah fix

## API Architecture (dari source map, 2026-08)
- **Base:** `https://services.chipotle.com/cateringorder/v1` (`VUE_APP_BASE_URL` + `VUE_APP_VERSION=/v1`)
- **EPOPS:** `https://services.chipotle.com/epops/v2`
- **Auth:** cookie-based (`withCredentials: true`), header `invalid-token` menandakan session expired
- **Headers (createClient.js):** `Ocp-Apim-Subscription-Key` (Azure APIM), `Content-Type: application/json`, `Chipotle-CorrelationId: COO-{uuid4}`, `Accept: application/json`, `Cache-Control: no-cache`, `x-cmg-ff-user: {customerIdHash}` (feature flag traffic key, default `-`)
- **Stack:** Azure API Management + ASP.NET backend, varnish cache, rate limiter aktif (login/register → 429)

## Key Endpoints (dari cateringOrderClient)
- Auth: `/customerauth/getstarted|login|register|upgrade|logout|changepassword|verify/initialize|verify/finalize`
- Order: `/order`, `/order/cart`, `/order/{id}`, `/order/{id}/validate|transfer|submit|favorite|isChangeable|markforupdate`, `/order/{id}/item`, `/order/{id}/reorder/{reorderId}`, `/order/{id}/promotions/{code}` (POST/DELETE), `/order/{id}/promotions/validate`, `/order/userhistory`, `/order/undoforupdate`
- Customer: `/customer`, `/customer/delivery` (+ `/{addressId}`)
- Menu: `/menu/tiered`, `/menu/tiered/{restaurantNumber}`, `/menu/geocode?latitude=&longitude=`
- Restaurant: `/restaurant/search` (POST), `/restaurant/{num}/realhours`, `/capacity`, `/restaurant/delivery`
- Payment: `/transaction/provider`, `/transaction/provider/{id}`, `/transaction/tokenize/{providerId}/{clientToken}`, `/transaction/wallet` (+ `/{tokenId}`)
- Lain: `/health`, `/promotions`, `/loyalty/points`, `/popularbuild`, `/enum/eventtypes`, `/delivery/quote`

## Suggested Attack Priorities
1. `services.chipotle.com` API (IDOR pada order/customer/delivery — cookie auth + numeric/GUID IDs)
2. Promo/reward logic (`/promotions`, `/loyalty/points`, apply promo ke order)
3. Order flow: `transfer`, `reorder`, `validate`, `isChangeable` — state manipulation
4. Payment: tokenize flow, wallet CRUD
5. Mobile apps: deep links, token storage

## Files
- `references/sourcemap-recon.md` — teknik recover API surface dari source map (dipakai di program ini)
