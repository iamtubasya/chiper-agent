---
name: porkbun-audit
author: RESEARCHER_NAME
description: "Porkbun (porkbun.com) bug bounty — scope, API v3 map, hardened surfaces, PoW-captcha bypass, account-creation flow, ID-verify blocker."
metadata:
  hermes:
    tags: [bug-bounty, security, porkbun, web, api, captcha-bypass, registrar]
version: 1.0.0
---

# Porkbun Bug Bounty — engagement dossier

Domain registrar + hosting. Run the API on **api.porkbun.com**; the website on **porkbun.com**.

## Scope / rules / payout
- **In scope:** `porkbun.com` (website) and `api.porkbun.com` (API). Everything else (including `mcp.porkbun.com`) is a "other subdomain" → **out of scope**.
- **Uber challenges:** `bugbounty.design` ($1000) and `bugbounty.ink` ($500) — "deface the website". Checked 2026-11: both are **NXDOMAIN** (unregistered), so the challenges are inactive. Re-check DNS (doh/dig) before chasing.
- **Payout:** P1 $750 / P2 $500 / P3 $250 / P4 $0-100.
- **Submit:** email to `bug-bounty@porkbun.com`, subject `Bug Bounty: P{n}` (or `PR☐ LEVEL<n>`). Each finding = separate email. Must include: OWASP Top 10 + Bugcrowd VRT name + variant/affected function, full PoC, and a **PayPal address**. No scraping / no DoS / no stressing the site.
- **Invalid:** self-XSS, descriptive error messages/stack traces, clickjacking, CSRF on public/anonymous forms, CSRF cookie not-httponly (known by-design).

## API v3 — fast map
- OpenAPI spec: `https://porkbun.com/api/json/v3/spec` (151 paths). Every response sends `Link: rel="describedby"`.
- Auth: `X-API-Key` + `X-Secret-API-Key` headers (also `Authorization: Bearer` on some). Public/no-auth: `/ping`, `/ip`, `/pricing/get`, `/domain/checkDomain`, `/apikey/request`, `/apikey/retrieve`, `/mock/*`.
- **Sandbox (free keys, no approval, $1000 fake credit):** `POST /apikey/request {"sandbox":true}` returns `pk1_sb_…`/`sk1_sb_…`. Run the whole API against an isolated datastore. `hosting`, `email`, `closeout`, `cloudflare` endpoints return `SANDBOX_UNSUPPORTED`.
- Key groups: `domain/*` (reg/renew/transfer/contacts/glue/url-forward), `dns/*` (CRUD, DNSSEC, scan/import/restore/history), `hosting/*` (static + WordPress, deploy/files/makeDir/createWpCredentials), `ssl/*`, `email/*`, `account/*` (balance/invoices/invoicePdf/topup/topupCrypto-x402/topupMpp/verifyPhone/verifyEmail/apiSettings/invite), `webhook/*` (signed, delivered in sandbox), `cloudflare/*` (move domains to customer CF), `marketplace/*`, `aftermarket/*`, `closeout/*`, `apikey/*` (OAuth/PKCE flow).
- Scopes (per-endpoint via `x-porkbun-scope`): `read` is always included and covers balance/invoices/apiSettings BY DESIGN. `purchase` = register, `funding` = topup, `account` = webhook CRUD, `dns`, `domains`, `email`, `hosting`.

## HARDENED (validated 2026-11 — do not re-test these as "bug hunts")
- Auth is enforced everywhere (`API_KEY_REQUIRED`, HTTP 400).
- **IDOR/BOLA is solid:** `/domain/get/{d}`, `/dns/retrieve/{d}`, `/account/invoice/{orderId}` all check account ownership and return `DOMAIN_NOT_FOUND`/`INVOICE_NOT_FOUND` w/ helpful hint. Error messages happily name the account (your own — not a leak).
- **Scope enforcement works:** restricted key (`read`+`dns`) → `INSUFFICIENT_SCOPE` on purchase/funding/account/webhook, but reads balance/invoices freely because those are `x-porkbun-scope: read`.
- **SSRF webhook hardened:** webhook URL must be HTTPS, resolves to public internet; private/loopback/link-local/reserved refused.
- **Price manipulation blocked:** `cost` must equal server-side price (`COST_MISMATCH` names expected cents). `dryRun:true,cost:0` for a quote.

## The PoW-captcha bypass (the gold — non-obvious, saves ~30 min)
Signup and login are gated by a CUSTOM "Pork Captcha V1.3.1" — NOT Cloudflare Turnstile. It is a client-side **SHA-256 proof-of-work** with a fixed 12-bit target (`minDifficulty:12, maxDifficulty:14`). ~4096 hashes, solvable 6-23 ms in Python.

Flow (also see `scripts/porkbun_pow_solver.py`):
1. `POST /tools/porkCaptchaIssue {"sitekey":"805d2807-7ec4-44f5-84c0-f5cb5187d587"}` → `{challenge:<uuid>, challengeToken:<jwt>, difficulty:12}`.
2. Mine nonce N: `sha256("<challenge>"+str(N)).hexdigest()` starts with `"000"` (12 zero bits; for 14 bits the 4th nibble < 4).
3. `POST /tools/porkCaptchaChallenge {challengeToken, nonce, fingerprint, sitekey, difficulty, elapsed, action:"accountCreate", interactionEntropy, botHints, clickTimestamp, clickX, clickY, clickDelay}` → `{token:<jwt>}`.

A real Turnstile DOES exist but only as an escalation modal ("forceCcaptcha", sitekey `0x4AAAAAAA6GKaAgDPcUgP1q`) triggered on suspicious signals — not the default path.

### Automated account creation (pure HTTP, no browser)
- CSRF is **double-submit cookie**: GET `/account/create` sets `csrf_pb` cookie; every non-GET AJAX appends `isajax=true&csrf_pb=<cookie>`.
- `POST /api/user/accountCreateCheck {username,password,email,country,ccaptcharesponse:"",pcaptcharesponse:<pow-token>,emailBackup:"",isajax:true,csrf_pb}` → `{error:0,code:"CODESENT"}` (email sent to ARBITRARY address — this is the email-bomb vector).
- Read the code (e.g. via Gmail API `gmail_ops.py read` on the `RESEARCHER_USERNAME` account), then `POST /api/user/checkEmailSessionVerificationCode {email,code}` → `{error:0,message:"SUCCESS!"}`.
- Final `POST /account/create` with all form fields + fresh csrf + fresh pow-token + `addressValidationConfirmed=1`.
- Email validation: `support@porkbun.com` → `EMAILERRORS "Email address is not allowed"` (own domain blocked); no enumeration (fresh + pending both return CODESENT).

### BLOCKER — ID verification
New accounts get flagged "**This Account Will Require ID Verification**" (photograph of government ID) before they can register/manage domains — likely risk-based (datacenter/Cloudflare egress IP). This is a hard stop for automated signup. **Do NOT fabricate KYC/ID** (memory rule: fake KYC to a regulated entity = ban). Pivot to the sandbox API + unauthenticated surface instead.

## Auth-adjacent surface still worth probing
- `POST /apikey/request` (no creds) — OAuth/PKCE key flow. `returnUrl` is documented "must be a Universal Link/App Link you claim" but only the **scheme is checked**: arbitrary `https://evil.com` / `https://porkbun.com.evil.com` accepted → **open redirect (reported P4)**. `javascript:` rejected. Only S256 codeChallenge supported; rate limit 20/IP/hr.
- Support AI-assistant backend (`porkbun.com/js/support-widget.js`) exposes `/tools/chat_*` and `/tools/chatbot_*` (nounce → `chatbot_execute_action`, `chatbot_2fa_enable/disable`) — all **auth-gated (302)**; needs a logged-in session.

## Reported findings (avoid dup)
- P4: Pork Captcha PoW trivially bypassable → unauthenticated email bombing via `/api/user/accountCreateCheck`.
- P4: `returnUrl` open redirect in `/apikey/request`.
- P4 (2026-11-04): JSON type-confusion → HTTP 500 — `/domain/create` (dryRun, agreeToTerms), `/account/autoTopup` (enabled), `/apikey/request` (scopes), `/webhook/create` (url).
- P4 (2026-11-04): `returnUrl` open redirect in `/account/invite` (distinct endpoint).

## 2026-11-02 re-audit — NEW validated notes (don't re-derive)

- **Account creation = 3-layer wall, all legitimate controls (NOT a bug).** (1) Fingerprint2.js + `prb` cookie from `/api/user/init`; (2) Pork Captcha PoW (client-side, solvable); (3) the FINAL hurdle = server-side anti-fraud `("We are unable to create your account ... (001) ()")` which fires AFTER email verification passes. Confirmed via Playwright (real Chrome, valid fingerprint + PoW + email code KSCIZSUCIS/IAWGWMTDIA accepted) — the account is still rejected with `(001) ()` regardless of address. Root cause = IPQS flags the datacenter/VPN egress (fraud-score 84, `ipqs-ip-vpn=1`, `ipqs-ip-proxy=1`). 5 total attempts (3 curl + 2 Playwright) all walled. Stop here — do NOT try browser/account creation again without a residential IP; it is anti-fraud working as intended.
- **Account creation is blocked by browser fingerprint, not just ID verify.** `/account/create` POST fails SILENTLY (re-renders form, HTTP 200, no error) unless the request carries a valid `prb` cookie set by `POST /api/user/init` (returns `{"init":1,"prb":"<hex>"}` + sets `PRB` HttpOnly cookie). The real gate is Fingerprint2.js (`clientFingerprint`/`fingersha`) + IPQS (`ipqs-ip-fraud-score`, `ipqs-ip-vpn=1`, `ipqs-ip-proxy=1` on datacenter egress) → `FORCEIDVERIFY` (government ID). Email verification itself WORKS over pure HTTP: `POST /api/user/accountCreateCheck` (needs `isajax=true&csrf_pb=` + `pcaptcharesponse` PoW, NOT just the JSON) → `CODESENT`; read code via Gmail (`gmail_ops.py read` on `RESEARCHER_USERNAME`); `POST /api/user/checkEmailSessionVerificationCode {email,code}` → `SUCCESS`; next `accountCreateCheck` → `EMAILVERIFIED`. All AJAX non-GET must append `isajax=true&csrf_pb=<cookie>` + `X-Requested-With: XMLHttpRequest`, else 302-redirect loop (empty body = dropped data). Account creation itself does NOT need the address to be valid — set `addressValidationConfirmed=1` to skip `/api/user/validateAddress`.
- **Login rate-limit gap (weak P4 lead).** Legacy `POST /api/user/login` accepts 30+ rapid attempts with NO rate limit, NO lockout, NO captcha (all HTTP 200 "Invalid username or password (001)", same for bad-user vs bad-pass = no username enumeration). The versioned `POST /api/user/login_20230305_1` (`lep = base64('/api/user/login_20230305_1')`) IS protected (`passedCaptcha:1`, "security credentials look weird"). Login uses Cloudflare Turnstile only as an ESCALATION modal (`modal_forceCcaptcha`, sitekey `0x4AAAAAAA6GKaAgDPcUgP1q`) — not on the default path. `bypassTwoFactor(ecode)` = 2FA recovery via `POST /api/user/sendPhoneCode` (phone code) — the `ecode` is a 10-char alphanumeric code emailed on account recovery (`/account/login#ecode=XXXX&user=...`).
- **Confirmed hardened (re-verified independently):** IDOR/BOLA solid on domain/contacts/dns/invoice/invoicePdf/webhook-endpoint(`/webhook/get/{id}` integer id)/webhook-delivery — cross-account all return NOT_FOUND. Scope enforcement real (`INSUFFICIENT_SCOPE` lists requiredScope). Price/cost server-checked (`COST_MISMATCH` names expected cents); `dryRun:true,cost:0` = free quote oracle. SQLi absent (params validated/param'd; special chars in `{domain}` just → DOMAIN_NOT_FOUND). Sandbox keys `pk1_sb_`/`sk1_sb_` give `scopes:["full"]` + $1000 fake credit, fully isolated (account ids `sbx_…`); `/closeout`, `/account/topupCrypto/x402`, `/hosting`, `/email`, `/cloudflare` = `SANDBOX_UNSUPPORTED`.
- **Support chat RAG** `POST /tools/support_chat_api {query, session_id}` is UNAUTHENTICATED (returns `sources` = kb.porkbun.com articles + `response` + leaks `cost`/`usage` token metrics). No account data access ("RAG cannot see account data"). System prompt PROTECTED (refuses verbatim; only points to `https://mcp.porkbun.com/mcp`). Action endpoints (`/tools/chatbot_*`, `/tools/chat_*` reports) are auth-gated (401). Low-value LLM surface.
- **Webhook eventTypes** include `account.verification.code_sent` / `account.verification.completed` — webhook can receive account verification codes (owner-only, by design).
- **DNS record content** (TXT etc.) is stored + returned UNSANITIZED verbatim in API JSON (potential stored XSS only IF rendered unsafely in the authenticated domain-mgmt UI — unverified, and self-XSS is OOS anyway).
- Curtailment: no P1/P2/P3 confirmed; target is exceptionally well-hardened. Only lead = legacy-login rate-limit (P4, needs e2e account-test to prove lockout absence on a REAL user before reporting).

## 2026-11-04 re-audit — NEW validated notes (do not re-derive)

Spec is now **151 paths** (was 123). Two new P4s found (reports in `~/porkbun-audit/REPORT.md` + `draft_email_*.txt`):

- **JSON type-confusion → HTTP 500 (unhandled exception), P4 REPORTED.** Object-typed value where a primitive is expected crashes the handler (500, EMPTY body, `text/html`, `Server: openresty` — no Go stack trace leaks, regardless of `Accept` header). CONFIRMED crashing fields: `POST /domain/create/{d}` → `dryRun`, `agreeToTerms`; `POST /account/autoTopup` → `enabled`; `POST /apikey/request` → `scopes`; `POST /webhook/create` → `url`. NOT crashing (clean 400/200, coerced): `amount`, `cost`, `threshold`, `sandbox`; and `dryRun`/`enabled` when given array/null/string — only OBJECT (`{}`/nested) → 500. The bug = inconsistent validation: sibling fields coerce, these panic. Low value, no escalation found (empty body, per-request only).
- **`/account/invite` `returnUrl` open redirect, P4 REPORTED.** Only scheme-checked ("returnUrl must be a valid HTTPS URL"). Accepts `https://evil.com`, `https://porkbun.com.evil.com`, `https://evil.com/porkbun.com`, `https://porkbun.com@evil.com`, `https://127.0.0.1`, `https://porkbun.com/../../evil.com`. Rejects `http://`, `javascript:`, `//evil.com`. Distinct endpoint from the already-reported `/apikey/request` returnUrl. `/account/invite` also returns `inviteToken` (64-hex, random) + `inviteUrl` = `https://porkbun.com/account/create?invite=<token>` (returnUrl is stored server-side, NOT reflected in inviteUrl).
- **`/ip` & `/ping` trust client `X-Forwarded-For` for `yourIp`** (returns the spoofed IP and pushes real IP onto `xForwardedFor`). BUT the rate limiter (1 create/1s; 20 sandbox keys/hr) does NOT honour XFF — still keyed on real/account identity. Informational only, NOT a bypass, not submitted.
- **`/domain/create` double-charge (sandbox-only, not submitted).** Re-registering a domain already in the account returns SUCCESS + debits again (no-op; listAll still shows 1). `/domain/transfer` correctly returns `DOMAIN_ALREADY_IN_ACCOUNT`. Likely sandbox artifact (no real registry to reject a duplicate) — cannot confirm production, so noted only.
- **Sandbox limitations (important for future test planning):** `/domain/transfer` simulates completion INSTANTLY (`status: DONE` even with `holdForDnsSetup:true`) → the PENDING/refund `cancelTransfer` state machine is UNTESTABLE in sandbox. `payWith:"usdc"|"card"` → `SANDBOX_UNSUPPORTED` → x402/MPP payment completion + checkout-id forgery UNTESTABLE. `/sandbox/topup` negative/0/overflow/non-int amounts are CLAMPED (default 100000 or max 1000000; `True`→1) not exploitable. `/account/topup` amount strictly 500–50000 cents (string coerced, negative/overflow → 400 INVALID_INPUT).
- **Re-verified solid this round:** cross-account IDOR/BOLA (2nd sandbox account) on `/domain/get`, `/dns/retrieve`, `/domain/getContacts`, `/ssl/retrieve`, `/account/invoice`, `/account/invoicePdf` all NOT_FOUND. Mass-assignment extra fields silently ignored. Non-JSON content-type → `INVALID_OR_EMPTY_JSON`. HPP duplicate `cost` (JSON last-wins) still validated → COST_MISMATCH. OAuth `requestToken` 10/10 unique random 64-hex. Mock server no path traversal/SSRF. Webhook HMAC-SHA256 + `rotateSecret` valid (deliveries readable via `/webhook/deliveries` + `/webhook/delivery/{id}`, which include the payload but not the signature header).
- **`POST /tools/support_chat_api` now returns 405 Method Not Allowed** (2026-11-04) — previously unauth POST (per 2026-11-02 note). Endpoint still exists but rejects POST; try GET or treat as deprecated.

## 2026-11-04 re-audit — NEW validated findings (don't re-derive / don't re-report as fresh)
Two P4 submitted (draft gunakan email RESEARCHER_EMAIL, PayPal RESEARCHER_EMAIL, subject "Bug Bounty: P4"):
1. **P4 — JSON type-confusion → HTTP 500 (unhandled exception)**. Object-typed value where primitive expected panics the validation path → 500 empty body (text/html, openresty). Reproduced 3/3. Affected fields: `/domain/create` `dryRun`, `agreeToTerms`; `/account/autoTopup` `enabled`; `/apikey/request` `scopes`; `/webhook/create` `url`. Contrast: `amount`/`cost`/`threshold`/`sandbox` return clean 400 INVALID_INPUT — so it's an INCONSISTENT validation path, not by-design. No stack trace/leak. P4 only.
2. **P4 — open redirect in `/account/invite` `returnUrl`** (scheme-only, "must be valid HTTPS URL"). Accepts `https://evil.com`, `https://porkbun.com.evil.com`, `https://porkbun.com@evil.com`, `https://127.0.0.1`, `https://porkbun.com/../../evil.com`. Rejects http/javascript/scheme-relative. NEW endpoint (prior one was `/apikey/request` returnUrl). POST /account/invite → 200 SUCCESS inviteToken+inviteUrl; returnUrl stored & used post-registration.

Informational (NOT submitted, no bypass proven): `/ip` & `/ping` reflect client `X-Forwarded-For` as `yourIp` (spoofable), BUT the account/IP rate limiter (1 create/sec, 20 sandbox-keys/hr) does NOT honour XFF — verified by 8-thread create burst with distinct XFF still rate-limited to 1 success. Any downstream that trusts `/ip` for security decisions is spoofable, but no in-scope control is bypassed.

Sandbox-only (NOT submitted): `/domain/create` re-charges a domain already in the caller's account (returns SUCCESS + new orderId + debits again; no counterpart check since `/domain/transfer` does return DOMAIN_ALREADY_IN_ACCOUNT). Likely sandbox artifact (simulates registry completion, no real "already registered" rejection) — can't confirm production. Noted only.

Re-validated SOLID this round (do not retest): IDOR/BOLA cross-account via a SECOND sandbox account (domain/dns/contacts/ssl/invoice/invoicePdf all NOT_FOUND; error names caller's own account only). cost/amount type+range validation (neg/overflow/string/float/bool/HPP-dup all blocked). dryRun only truthy-int/"true"/1. mass-assignment extra fields ignored. non-JSON content-type rejected. webhook HMAC-SHA256 + rotateSecret correct; GET webhook 503 was transient. OAuth requestToken 64-hex random (10/10 unique). mock server no path traversal/SSRF. `/sandbox/topup` clamps invalid → default/max, not exploitable.

## Reusable script
- `scripts/porkbun_pow_solver.py` — issue→mine→challenge→token, prints the JWT captcha token. Reproduce with `python scripts/porkbun_pow_solver.py` (stdlib only).