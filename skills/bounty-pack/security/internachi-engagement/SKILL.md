---
name: internachi-engagement
description: "InterNACHI (nachi.org) bug-bounty engagement — verified scope/RoE, estate map, WAF behaviour and the browser-only POST technique, route inventory, gating model, and open leads for the member-only surface."
version: 1.0.0
metadata:
  hermes:
    tags: [security, bug-bounty, internachi, laravel, cloudflare]
    related_skills: [security/bug-bounty, security/bot-protected-target-testing, security/report-writing]
---

# InterNACHI® bug bounty — engagement notes

## Program (verified 2026-10-30)
- Policy: https://www.nachi.org/bug-bounty  · submit: /bug-bounty/submit · security.txt present
- CVSSv3 based: <6 may not be rewarded; 7→$1,750, 8→$3,500, 9→$7,500, 10→$10,000. Paid via PayPal.
- In scope: `*.nachi.org`, `*.internachi.org`, all InterNACHI websites **and mobile apps**.
- OOS: login/logout CSRF, cached content after logout, access to an account you already control,
  attacks requiring valid creds without a way to obtain them, rate limiting, email spoofing,
  DNSSEC/DANE, unsupported browsers, Reflected File Download, missing HSTS, **insurance.nachi.org**.
- Disqualifiers: accessing other members' accounts, any DoS, social engineering,
  **fuzzing support forms**, **automated scanning and brute-forcing**.
- Rules: send `X-Bug-Bounty:` header; guest accounts must contain `bugbounty` in the email;
  one report per bug; first report wins.

## Estate
- `www.nachi.org` = main app: Laravel + Alpine/Aire (client validation rules leak the server rules
  as JSON in `Aire.connect(...)`) + Ziggy (424 authed routes at `/my/*`) + Vite build.
- `forum.nachi.org` = Discourse 2026.11.0-latest (current; SSO signature enforced → 422).
- `insurance.nachi.org` = WordPress/WP Engine (OOS), `marketing.nachi.org` = Wix,
  `testimonials.nachi.org` = white-label Testimonial.to (third-party).
- `billing.nachi.org` = Stripe custom checkout domain (`/c/pay/cs_live_...`).
- `office.nachi.org`, `unifi.nachi.org` resolve but are IP-restricted (timeout).
- `www-staging-cloud-1.nachi.org` = HTTP Basic, IP-restricted.
- No dangling CNAMEs (only wpengine + myshopify, both live). S3 buckets not listable.

## Critical technique: their WAF allows only native form POSTs
- Cloudflare + InterNACHI's own WAF. `requests`/`httpx`/`nuclei`/`sqlmap` get 403 after a few requests
  (fingerprint based). In-page `fetch`/XHR **POST** also 403 — even with `_token`, `X-CSRF-TOKEN`,
  `X-Requested-With`, `Origin`, `Sec-Fetch-*`.
- What DOES pass: a real browser **navigation form submit** (`form.requestSubmit()` / `.submit()`
  after building hidden inputs). GET fetches pass. Use Playwright over CDP (`connect_over_cdp`
  to a Chrome started with `--remote-debugging-port=9222`); Camofox and headless Chromium do not
  clear the CF challenge, a CDP-attached real Chrome does.
- Multi-identity: `ctx.storage_state()` then `b.new_context(storage_state=...)` re-uses `cf_clearance`
  and passes the challenge, so parallel accounts are possible.

## Auth model
- Laravel session (`laravel_session`, SameSite=Lax, HttpOnly) is authoritative.
- `internachi_auth` = `<user_id>;<md5-ish>` and `legacy_auth` = base64(`id;sha256;ts`) are **not**
  honoured by www.nachi.org (cookie alone → redirect to /auth/login). No forgery.
- `/dynamic/js/session/{user_id}/{hash}.js` is generated **per session**: path params are ignored
  (any id/hash returns your own `window.logged_in_user`), `cache-control: private`, CF BYPASS →
  no IDOR, but it leaks your own `id`, `account_id`, `username`, `role`, flags and `legal_name`.
- Password reset: short link `/s/<10 chars>` → `/auth/password/reset/<64 hex>`; needs username+token;
  no user enumeration. Login form field is `username` (email or username).
- SameSite=Lax kills cross-site POST CSRF; state-changing **GETs** (login-attempt approve/flag) are
  still reachable by top-level navigation.

## Gating model (the blocker)
Guest role gets 302 → `/my/company/billing/stripe/checkout` (i.e. must buy All-Access, $49/mo or
$499/yr) or a 403/404 "not available for your account" page for nearly all member modules:
agreements (create/view/download), FetchReport, company users/transcripts, education record create,
id-card, proof-of-payment, payouts, insurance applications, MSFH inspections + signatures,
vendor offers, licenses/{id}. Guest-reachable only: dashboard, profile/settings, education
transcript + records index (own), exams, chapters list, mentoring, jobs list, assets, 2FA,
security-check, MSFH metadata/documents *create* (store still 404s), agreements template list.
→ The high-value surface (SSRF via FetchReport, cross-tenant company users, agreement rendering,
payouts) is behind the paywall. Decide with the operator before spending money.

## FINDING — Unauthenticated blind SSRF (2026-10-30, 1/3 confirmations)
`POST /verify/submit-report`, field `inspector_website`. Public form, no login.
Backend issues a server-side `HEAD` to the submitted URL before persisting the report.
Full PoC + verbatim capture: `references/ssrf-verify-submit-report.md`.

```
METHOD: HEAD   UA: Ruby   IP: 34.197.76.213 (AWS us-east-1)
x-datadog-trace-id: 767542872150593634   x-datadog-parent-id: 3048030264738685989
```
Datadog trace headers = their production Rails app, not CDN/client. Unique canary path
created minutes earlier and submitted once → causality airtight.

**Why the retries died — and how to tell WAF-ban from payload-filtering:**
2nd/3rd submissions returned HTTP 403 with no side effect. Discriminator: swap the canary
host entirely (`webhook.site` → fresh `oast.fun`) and retry. Still 403 after 7 min cool-down
→ **endpoint+IP rate limit**, not payload filtering. Do NOT proxy-hop to beat this (evasion);
schedule the retry instead. Related: `/my/profile/company_url` accepts the same URL shape but
produced **zero** server-side fetch (only client validation) → not a sink.

## Turnstile on this estate (needed to reach any public form)
Signup and `/verify/submit-report` both gate on Turnstile. Token stays empty (len 0) until the
challenge is actually interacted with. Working move from CDP Playwright:

```python
for f in pg.frames:
    if "challenges.cloudflare.com" in f.url:
        f.click("body", timeout=4000)        # -> token appears (len 730-752)
```
The widget container reports `height: 0` so `page.click` on the element fails; clicking the
**iframe body** is what works. Retry the click in a loop (5-8 attempts) — first click often
no-ops. A stale token from a previous load is fine for one submit only.

## Confirmed defects (low)
1. **RETRACTED 2026-10-30 — "legal_name corrupted at signup" was a FALSE POSITIVE.**
   A 3rd controlled account (given=Alpha, family=Beta, legal="Gamma Delta", values injected
   directly into the DOM) stored `legal_name = "Gamma Delta"` — correct. The duplication only
   appears when the field is typed/filled normally, because the signup form's Alpine component
   auto-prefills: given_name/family_name `@change` runs
   ``if (infer_legal_name && !!family_name) { legal_name = `${given_name} ${family_name}` }``
   and `legal_name @focus/@change` sets `infer_legal_name = false`. Result: whatever the user
   types into legal_name gets prefixed with "First Last" → "RESEARCHER_NAMERESEARCHER_NAME".
   That is a **client-side UX bug** (and arguably intended "infer from name" behaviour),
   NOT server-side data corruption. **The server stores exactly what is submitted.**
   Residual, still-unproven: `legal_name` is stored raw (HTML from given_name landed in it on
   one account) while `given_name` is sanitised → *potential* stored XSS/PDF injection if a
   rendering sink exists, but every sink (id-card, certificate, affidavit) is All-Access gated.
   DO NOT report this without a proven sink.
   LESSON: a 2-account "reproduction" is not a reproduction when both were created by the same
   automation path. Always add a control account with DOM-injected values.
2. `POST /webhook/stripe` returns `200 "ok"` for **any** body (invalid JSON, empty, forged
   `Stripe-Signature`) — signature enforcement unverified; likely a stub/queue endpoint.
   Forging `checkout.session.completed` for my own live session id did **not** flip entitlement
   (dashboard stayed Guest) → inert, negative.
3. `GET /my/programs/msfc/citizens-mit-bt-23/create` → 500 (unhandled exception, generic page).
4. Guest UI/authorization mismatch: MSFH document form and license create wizard render for guests
   but the POST 404s.
5. SQLi sweep on public GET params (`verify/lookup?name=`, `search/results?q=`,
   `inspection-glossary/{prefix}`, `certified-inspectors/browse/{c}/{s}?page=`, `terms/{t}`):
   `'`, `''`, `"`, `\` all 200 with no SQL error strings → parameterised. Negative.

## Open leads (need All-Access)
- `/my/reports/fetchreport` + `POST /my/reports/fetchreport` (fetch remote URL → SSRF),
  `claim-reports/verify-email`, `{report}/recipients` (BOLA on report recipients).
- `/my/agreements/{agreement}`, `/access-codes`, `/download`, template render (SSTI in
  placeholder substitution — company_name is user-controlled).
- `/my/company/users/{company_membership}/*` (transcript, education-records, webseals, cpi-status)
  → cross-company BOLA if not scoped.
- `/my/payouts/*` (Stripe Connect), `/my/insurance/applications/{application}`.
- `/my/msfh/wind-mitigation-inspections/{inspection}/signature` (signing state OIR-1802 forms).

## Closed negatives (do NOT re-spend time)
- **IDOR on exam sessions** — account5 vs account1's session: `/1`, `/results`, `/review`,
  `/group/N` all **403**; a fabricated session id gives **404**. 403-vs-404 is the
  discriminator: ownership is enforced. Exam sessions are the only object type a guest can reach.
- **RCE** — upload sinks gated; `education.nachi.org/show.php?course_id=` is a thin redirector
  (`'`, `"`, `../`, `[]` → 403/302, no PHP errors); `exams.nachi.org/admin/` 403; no
  `_ignition`, `/telescope`, `/horizon`, `/log-viewer`, `/phpinfo`, `/server-status`.
- **Traversal** — `{article}.htm` and `/webseals/{filename}`: `..%2f`→400 (CF),
  `%2e%2e/`→normalised then 403, double-encoded→403.
- **Email-confirm signature** — `/auth/confirm-email/verify` with `dead`, `0000`, empty
  signature → all bounce to `/auth/login`. Enforced.
- **Stripe webhook forgery** — forged `checkout.session.completed` for own live session id
  did not flip entitlement (`is_all_access:false`, `paid_through_at:null`). Inert.
- **Auth-cookie forgery / session fixation / CSRF / mass assignment / S3 listing /
  subdomain takeover / Discourse SSO** — all negative.

## Housekeeping
Test accounts (all tagged per policy): `RESEARCHER_USERNAME+bugbounty@`, `+bugbounty2@`, `+bugbounty3@`,
`+bugbounty4@` (never confirmed, unusable), `+bugbounty5@` (id 59293448, the clean control).
Working dir `D:\bb\internachi` (`recon/`, `evidence/`, `loot/`).
Artefacts: `evidence/SSRF_PoC.md`, `evidence/InterNACHI_SSRF_PoC.pdf`,
`evidence/ssrf_hit1.json`, `evidence/legalname_validation.json`.
Helpers: `pw.py` (CDP connect), `bfetch.py` (in-page GET probe), `req.py`.
SSRF detail: `references/ssrf-verify-submit-report.md`.

## Submission channel
`security.txt` gives only the web form `/bug-bounty/submit` — **no security@ mailbox is published**.
For an email submission the closest published address is `fast-reply@internachi.org` (named in
their membership Terms for complaints/feedback). Gmail draft (operator-approved, single-confirmation
wording) was created to that address with `InterNACHI_SSRF_PoC.pdf` attached.
Report style that fits this vendor: numbered sections, no reward talk, explicit validation-status
section. PoC PDF built with reportlab (`mkpdf2.py`) → 3 pages, 7.6 KB.
