# djangoeurope engagement (2026-10-19) — Django hosting provider, DRF API + Angular panel

Target: djangoeurope.com (wservices GmbH, Niederwangen CH) — Django hosting control panel.
- Marketing: `djangoeurope.com` (Next.js + Cloudflare) · API: `api.djangoeurope.com` (Django REST Framework) · Panel: `panel.djangoeurope.com` (Angular SPA, nginx)
- Subdomains (DoH sweep): `staging` (HTTP-only, same IP), `dev` (138.201.50.7, Django app, SSH+443 open, self-signed cert), `docs` (untouched Sphinx default), `mail`/`webmail` (136.243.84.123, full mail suite)
- Program: **none published** (no security.txt — SPA fallback serves index.html for every path). Proceeded per operator mandate. Disclosure contact confirmed live: `security@wservices.ch` (via SMTP RCPT probe).
- Workspace: `$BB_DATA/_progress/djangoeurope_v1/`

## Recon path
1. DRF root `GET https://api.djangoeurope.com/` **enumerates the full endpoint map unauthenticated** (55 endpoints: user, profile, token, otpdevice, domain, sshkey, website, stripe/*, invoice, …) — DE-01 (info).
2. Panel bundle (`panel.djangoeurope.com/main.*.js`, 1 MB) + **17 lazy chunks** (1.1 MB, harvested by driving every route in a browser session and capturing chunk responses) — the lazy chunks hold the payload structures for features the main bundle doesn't (systemuser creation, productinfo, stripe, websitemonitoring). Always harvest lazy chunks before concluding a feature is untestable.
3. Unauth endpoint sweep: 13 open (reference data: language/country/timezone/imprint/server/ca/plan/doc*/faq*), 42 auth-gated. `/server/` leaks infra detail (server names, hardware, OS/package versions, provider) — DE-02 (Low). `/imprint/` exposes bank details + Stripe pk_live + the PayPal IPN URL (mostly public-by-design).
4. ALTCHA PoW reverse-engineered and solved programmatically (see `references/altcha-antifraud-and-token-rotation-testing.md`); registration still blocked by fingerprint anti-fraud → real-browser registration succeeded.

## Findings
- **DE-05 (Low): SMTP user enumeration** — `mail.wservices.ch:587` (STARTTLS) answers VRFY and distinguishes RCPT results: existing → 252/250, nonexistent → 550 "User unknown". Enumerated 6 mailboxes (info@djangoeurope.com, info@/admin@/support@/abuse@/security@wservices.ch) before the connection rate-limit closed (~30 probes). Relay itself correctly denied without auth.
- **DE-08 (Medium): email change without verification → persistent ATO** — `PATCH /email/{id}/` with `{address, password}` changes the login identity immediately; new record `is_valid: false` (never verified); login with the new address → 200 + token, old address → 400. Chain: password knowledge → change email to attacker's address → victim locked out → password-reset flow delivers to attacker → permanent takeover, no victim recovery. Missing control: confirmation link to the new address before activation. Tested on own account and restored (the restore also skipped verification — consistent).
- DE-01 (info): unauthenticated DRF endpoint-map enumeration.
- DE-02 (Low): `/server/` infrastructure disclosure.
- DE-04 (info): `dev.djangoeurope.com` publicly exposed (no DEBUG, no admin leak).
- DE-03 (unconfirmed): contact-form response includes `is_registered` — potential enumeration oracle, flip not demonstrated (no known-registered email available).
- DE-06 (unconfirmed): ticket title/description stored verbatim incl. HTML — potential stored XSS in the staff dashboard, not verifiable from a customer account.
- DE-07 (info): `POST /systemuser/` → HTTP 500 with a complete payload on an account without a subscription (unhandled exception; no security impact).

## Authenticated surface — tested clean (IDOR/RCE focused hunt)
- **IDOR**: all 30 detail endpoints (GET) with random vs foreign UUIDs → uniform 404; admin-only endpoints (expense, finance/transaction, message, backup) → consistent 403; list filter tampering (`?user=1`) ignored; nested parent-override on creation (domainrecord/mailuser/dbuser/port/usock with foreign parent UUIDs) rejected with existence+ownership validation; `/user/{id}` + `/profile/{id}` across 14 IDs → only own data; SSH-key creation with `user:1` override → ownership enforced server-side; mass assignment on profile → only cosmetic fields (fee fields, user-link, is_staff protected); `PATCH /user/` requires `current_password` and ignores privileged fields.
- **RCE**: SSH-key option injection (`command=`/`environment=`/`from=`) → options STRIPPED server-side; systemuser name injection → blocked at server validation (and the endpoint 500s before name processing anyway); rabbitmq vhost/user names → character whitelist (`a-z0-9 _ -`); webuser name → 16-char limit; mailtransport destination → hostname validation; profile company/vat_id/street → serializer validation.
- **Payments**: PayPal IPN (`/payment/paypal/notify/`) properly verifies with PayPal ("VERIFIED failed: INVALID" on forged IPN — destination must be the PayPal account email `info@wservices.ch`, discoverable from `/imprint/`); `/stripe/card|pm` PATCH = set-default only; productinfo planprice change is ownership-filtered and paywalled (manipulation untestable).
- **Auth architecture**: rotating tokens (~10 requests), cross-origin cookie binding, login/password-reset uniform errors (no enumeration), MFA endpoints validate the server-issued mfa_token before device/OTP processing, email-validation endpoint uniform errors.

## Pitfalls hit
- Playwright headless_shell missing → executable_path to the full chromium (version dir drifts; check ms-playwright/).
- Backtick payloads inside `page.evaluate` template literals break eval — pass as args.
- Gmail API token file: after a refresh the `expiry` can serialize as an int → `Credentials.from_authorized_user_file` raises `AttributeError: 'int' object has no attribute 'rstrip'`. Fix: read the JSON, convert int expiry to ISO string, write back.
- Response bodies sliced too small break `json.loads` (plan/server objects are 20 KB+) — parse in-page or slice ≥ 30 KB.
- Registration throttle is per-IP 24 h (`429 Retry-After: 86399`) and covers /user/ and /test/ but NOT /login/, /password_reset/, /contact/ — check scope of the throttle before assuming a dead end.
