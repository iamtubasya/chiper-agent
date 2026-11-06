---
name: entitlement-trust-testing
author: Hermes Curator
description: "Use when client-set state unlocks member entitlements."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [security, web, access-control, business-logic, bug-bounty]
    related_skills: [security-arsenal, triage-validation, hunt-business-logic]
sources: operator_experience
---

# Entitlement / Client-State Trust Testing

Class of web bug where the server decides entitlements (member pricing, discounts,
roles, partner flows) from **client-set state** (cookies, params, localStorage)
instead of a server-side session/identity check. Typical on membership/insurance/travel
portals and any flow that does a "validate member" step then stores the result as a cookie.

## When to use
- Target has member/guest pricing, discounts, rate plans, "partner" flows, role/feature flags.
- You see JS that sets cookies AFTER a validation step (e.g. `membershipId=1`,
  `memberType=...`, `memberTypeDiscount=...`) then redirects into a buying/search flow.
- Guessed API payloads return `Invalid input parameters` — the wire format is wrong;
  recover it from the JS bundle (below) instead of guessing further.

## Core playbook (differential client-state testing)

1. **Baseline**: replay the request in the default/guest state. Record size, status,
   and key fields (prices, rate plans, URLs, result counts). Save JSON for diffing.
2. **Find privileged client-state values**: grep the page's own JS/HTML for cookie names
   and param names the app sets after validation (`memberType`, `membershipId`,
   `memberLastname`, `discount`, `role`, `isAdmin`, `token`).
3. **Inject fabricated values**: repeat baseline with `Cookie: memberType=X; membershipId=1`.
   Compare responses — look for NEW fields (memberLabel, memberUrl, ihotelierMemberRatePlan),
   changed prices, extra rate plans, different booking URLs, larger response size.
4. **Minimize the trigger set**: remove cookies/params one at a time to find the MINIMAL
   set that flips the response. (`memberType` alone may not work; `memberType`+`membershipId` may.)
   This proves the control gap is client-state-only, not a hidden server check.
5. **Scope across sibling endpoints**: repeat with the privileged state on every related
   endpoint (getOfferLink, promoCode, benefits, search) — usually only ONE endpoint honors it.
6. **Check other auth levels**: same request with param vs cookie vs no state — which wins?
   (In the RACV case: param was ignored, cookies were honored — server reads cookies only.)

## Wire-format recovery from SPA bundles (when payloads are rejected)

Guessing param names wastes hours. Recover the EXACT request shape:

1. Crawl for undiscovered endpoints and page assets:
   `katana -u https://target -d 2 -jc -kf all -silent` → grep `/bin/`, `*.json`, `api`, `search`, `booking`.
   - `-jc` = crawl/parse JS, `-kf all` = keep all forms/inputs — this surfaces endpoints not in any sitemap.
2. On the page that references the endpoint, extract script tags:
   `grep -oE '<script[^>]*src="[^"]+\.js"' page.html` → find the WIDGET bundle
   (often `clientlib-bau/clientlib-<feature>.<hash>.js` on AEM, or a feature-named bundle).
3. Download the bundle, then extract the request builder:
   - endpoint strings: `re.findall(r'["\'](/bin/[a-zA-Z0-9_\-./{}]+)["\']', js)`
   - call context: find `$.ajax({url:...` / `fetch(` / param object construction near the endpoint
     (e.g. `r={resortIds:h.where_param,membershipNo:h.membership_id,lastName:h.member_lastname}`).
   - The JS reveals the REAL param names and date formats — e.g. `resortIds` not `keyResorts`,
     ISO `2026-10-01` dates (other formats 500).
4. Re-test with the exact wire format. `Invalid input parameters` with an empty
   `resortIds:[]` echo = wrong param name; success + data = format confirmed.

## Server-side entitlement legs: when there is no client state to poison

Not every tiered SaaS lets the client set anything. Before concluding "the tier is safe",
run the three legs that live entirely on the server. Each is cheap; each is a real bypass when
it fails. Report the result even when it is all negative — "verified, held" is evidence.

### Leg 1 — find and break the payment webhook
Enumerate provider webhook paths rather than guessing one:
`/api/<provider>/webhook`, `/api/webhooks/<provider>`, `/api/<provider>/events`,
`/api/billing/webhook`, `/api/checkout/webhook`, `/api/subscription/webhook`, and check
`Allow` on a GET (`405` + `Allow: POST` means the handler exists).

Then hammer the signature check with a **matrix**, not one payload — header-shape parsers are
where the bugs live:

    garbage | t= only | v1= only | t=+v1=deadbeef | v1=64x0 | v1=64xf
    t=0     | v0= scheme | duplicate t= | space-separated
    sha256= prefix | t in the future

Correct behaviour: every variant → `400 invalid signature`; no signature → `400 missing
signature`. A single `2xx`, or a `200` that changes the account's plan, is a **critical
unauthenticated privilege grant** — report it immediately and stop.

Do not complete a real payment and do not forge a *valid* signature: that is fraud against
the merchant. Testing the check with a wrong-secret signature is in scope; acquiring the
service is not.

### Leg 2 — fabricated return URLs
The success URL is cosmetic; entitlement must come from the verified webhook. Probe the
return side with a rendered plan-state read (not a status code), because a 200 page is
meaningless:

    ?success=1  ?checkout=success  ?upgraded=true  ?plan=pro
    ?session_id=<provider_session_format>  ?subscription=active
    /<area>/success  /<area>/pro  ?success=true&plan=pro&tier=pro

Read the account's actual tier after each. Everything staying on the free tier = pass.

### Leg 3 — mass assignment on account/profile actions
Inject privileged field names into a *real* profile-update form (it gets a valid action
binding, which curl replay does not):

    plan, isPro, is_pro, tier, planTier, subscription, subscriptionStatus,
    role, isAdmin, entitlements, stripeSubscriptionId, paid, priceCents

A `200 "your details have been saved"` with the tier unchanged is a pass. Any tier change is a
bypass. Include `role` even on non-RBAC products — mis-set admin flags are still worth a line.

### Leg 4 — prove the plan is server-rendered, not client-held
A product that gates by a cookie, `localStorage` flag, or a `?tier=` param is a finding even
if every page looks right. Set the flag by hand and diff the response for NEW fields, changed
prices, or extra plan rows. Remove fields one at a time to find the minimal trigger set.

### Also worth one request each
A typed numeric cap boundary (the "free plan allows N" message from the *server*, not the UI),
and a direct call to a paid *capability* rather than a paid page — a Pro-only screen can hide
the button while the JSON endpoint behind it still answers.

## Legacy vs versioned endpoint control gaps

Same servlet often exists in `/bin/<svc>` (unversioned) and `/bin/v1/<svc>` (current).
Controls (reCAPTCHA, rate limit, auth) are frequently added to v1 and the legacy path
is left live and unguarded (incomplete migration).

- Probe BOTH paths with the identical request.
- Expect: v1 blocks with captcha/auth error; legacy runs the lookup and returns data.
- This pattern is a finding itself (server security misconfiguration / incomplete migration).
- Check it across ALL in-scope assets sharing a backend (cross-target proves systemic).

## Severity honesty rules (VRT / bug-bounty)

The most important part — do not overclaim:

- PROVEN (client-state → member pricing/rate plans/booking URLs exposed) = access-control /
  business-logic finding. VRT: Broken Access Control or Business Logic, **P3 Medium** max,
  CVSS around `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N` (6.5).
- NOT PROVEN until demonstrated (final checkout at member price, discounted payment) —
  usually gated by a THIRD-PARTY booking engine and/or "show member card at check-in".
  Say this explicitly in the report; do not claim free/discounted booking.
- Rate-limit angle: many VDP/Bugcrowd programs **exclude rate limiting** — frame findings
  on the control gap (missing captcha/auth), not on "no throttle".
- PII from a valid match (emailId/encryptedKey) that you did NOT reproduce with a real
  account = inferential — downgrade to P4 and state that no real data was used.
- Run findings through the 7-Question Gate + VRT comparison BEFORE generating PDFs.
  User pattern: "cek dl dgn severity bugcrowd, apa benar bisa submit ini" — verify
  submittability first; a shiny-but-overclaimed P2 will come back N/A.

## Pitfalls
- **A quota counter in the UI is the REMAINING allowance, not the plan limit.** Measured 2026-10-25 on
  SimpleLogin: the page read *"Currently you can create up to 4 subdomains"* right after the first one
  was created, and *"up to 0"* when five existed — the number was `limit − used`. Reading it as "the
  limit is 4" produced a false "quota bypass" claim that had to be retracted. Never derive a quota
  finding from displayed text: keep creating until the button/handler actually refuses, then **count the
  real rows**, and record `limit = count_when_refused`. A bypass needs
  `count_when_refused > limit`, or a second tenant exceeding its own cap — not a misread label.
- **"Verify" buttons on ownership gates are usually a no-op that re-reads DNS — that is a PASS, not a
  bypass.** Claiming a domain you do not own should leave it `unverified`, show the TXT/MX records, and
  produce **no** state-changing POST when Verify is clicked (capture the requests: only the login POST
  appeared). A 200 page that looks unchanged is the correct behaviour. Only escalate if the state flips,
  or if a feature behind verification (catch-all, sending) starts working before verification.
- **Check the reserved-name list before declaring a claim/hijack.** On shared-root subdomain products,
  `admin`/`test`/`mail`/`support`/`api` being rejected is the control working. A random name succeeding
  while `admin` fails means a blocklist exists — the interesting follow-up is a *victim-brand* name, not
  `admin`.
- **Trials granted at signup are the entitlement baseline, not a finding.** Note remaining-days text
  ("Premium trial expires in a week") and test whether re-registration, a second plan or a coupon
  extends it — that needs a second identity. Do not claim trial abuse from a single account.
- **JS bundle name discovery**: endpoints found by katana may NOT be in the bundle you first
  grabbed. Search page HTML for the script that references them; the AEM widget bundle is
  `etc.clientlibs/racvaem/clientlibs/clientlib-bau/clientlib-<feature>.*.js`.
- Cookie trust is often endpoint-specific — one endpoint (resortSearch) honored the member
  cookie while getOfferLink/promoCode/member-benefits.json did not. Always scope and report
  the ACTUAL scope; don't imply global unlock.
- Keep evidence real: capture actual responses (curl/requests output), never fabricate.
- When the app stores entitlement in a cookie after validation, the finding is stronger if
  you show the JS that sets it (cite the bundle + handler snippet).

## Support files
- `scripts/cookie_diff.py` — differential tester skeleton: define base request + cookie
  variants, run, diff JSON responses, print changed fields.
- `references/racv-member-entitlement-case.md` — worked RACV VDP case: endpoints, cookie
  values, before/after prices, legacy-vs-v1 gap, wire-format recovery steps.

## Related skills
- `security-arsenal` — payload library for the injection angle once entitlement is proven.
- `triage-validation` — 7-Question Gate + never-submit list (run BEFORE reporting).
- `hunt-business-logic` / `hunt-session` — adjacent vuln classes (business logic, session flags).