---
name: formdesk-engagement
description: Formdesk (formdesk.com) bug-bounty engagement — scope, stack, auth/session model, working curl login+2FA recipe, discovered API surface, account/form state, findings and validated negatives. Load when resuming or auditing the Formdesk / Innovero Software form-builder SaaS.
sources: authorized-engagement
report_count: 1
---

# Formdesk Bug-Bounty Engagement

Form-builder SaaS (Classic ASP on IIS) by Innovero Software Solutions B.V. (Netherlands).
Program: https://formdesk.com/en/security-exploit-bounty-program/ — report to info@formdesk.com (one bug per email thread, PayPal, discretionary amount).

## Scope & rules (read this first)

- **In-scope = the product**, at `www.formdesk.com` → which 302/JS-redirects to sharded app servers `fdN.admin.formdesk.com` (fd1..fd26; fd1=77.87.163.50, fd2..26=77.87.163.32).
- **Qualifying** (only these): auth flaws, circumvention of Platform/Privacy permissions model, XSS, CSRF/XSRF (NOT logout CSRF), server-side RCE. Core bar: *"successfully used … to access user data that is not yours."*
- **NON-qualifying**: best-practices/headers, DoS, sending malicious links, third-party (payment/SMS) bugs, "requires victim to install software", spam/social-eng, **issues on the public marketing site `formdesk.com/en|nl|de`**, SPF/DKIM/DMARC.
- The marketing site is WordPress — OOS. The product is the ONLY bounty surface.

## Architecture / stack

- Classic ASP (`.asp` handlers) on IIS (`meta name="handled-by" content="WAS8"`), `X-Powered-By` blanked (version hidden).
- Custom router using `!` as route separator (e.g. `!login/try`, `!account/register`, `!forms/<id>/<tab>/`) plus legacy `action`/`step` query params.
- Data API: `GET/POST /<tenant>/data/<object>/<id>/?task=<op>&single=false&silent=false&lang=2&random=<6ch>&sidn=<sidn>`.
- Sharded per **whitelabel tenant**: each account gets a tenant path `/sectestco1/` (the `domain` field auto-generated from company name during signup, de-duplicated by numeric suffix). `label` = white-label brand (main = "Formdesk" id 2).

## Auth / session model (the hard part — already reverse-engineered)

- **sidn**: 32-hex session nonce, ROTATES on every page load. Present in the URL query AND in cookies `backend.<sidn>` / `rvtoken.<sidn>`. Two sidns can coexist (login sidn + post-navigation sidn).
- **rvtoken**: rotating CSRF/anti-replay token, format `BASE64{epoch_seconds}`. In `<meta application-info>` AND hidden input `__rvtoken` AND a per-sidn cookie. Required on POST; GET writes are no-ops without it.
- **session.backend.secure**: the real auth cookie (`<n>::<base64token>`, HttpOnly+Secure+SameSite=Lax). `<n>` is a per-session record id (NOT the account id — it changes every login: 252/6969/7400/7821 all seen).
- `application-info` meta/header leaks `auth.id` (`<n>::<token>`) + `auth.rvtoken` + `auth.sidn` on EVERY response (JS-readable; minor design note, not a finding by itself).
- **Login = email+password → MANDATORY email 2FA (6-digit code) → session.** 2FA flow:
  - `POST /!login/try/?lang=en&sidn=<sidn>` body `txtUsername=<email>&txtPassword=<pw>&ts=<ms>&__rvtoken=<rvt>` → 2FA page.
  - `GET /<tenant>/data/twofactor/0/?task=check&single=false&silent=false&lang=2&type=backend&value=email&random=x&sidn=<sidn>` → sends code.
  - `POST /<tenant>/!login/twofactor/?lang=en&sidn=<sidn>` body `code=<6d>&__rvtoken=<rvt>` → 302 → summary.
- **Signup** = email-verify 6-digit code via `data/verification/0/?task=check&todo=send|code`.

## Working session helper

Re-runnable login + `data()` helper: `scripts/fd_session.py`. It logs in (handles 2FA + mail.tm code fetch) and exposes `f.data(obj, id, task, ...)`. Save/loads cookies+pkl and state json.

Key gotcha: **page-level navigation loses the session** (sidn rotates and the URL must carry the fresh sidn + `2v<version>=`). Did NOT reliably drive the JS SPA form builder headless. **What works perfectly: the `data/<obj>/<id>/?task=<op>` API via `requests`** — use it to enumerate/test authorization directly.

## API objects discovered (valid, `task=get`)

`summary_forms` (form list + permissions), `labels_forms` (whitelabels), `settings/<formid>` (form settings XML), `view/<formid>` (form field/mergecode XML with uuids), `message/<formid>` (JSON), `users/<id>`, `mergecodes`, `logout` (GET!), `ping`, `verification`, `twofactor`. Unknown-object = HTTP 500; valid-but-no-context often 401.

## State (account/form created)

- Trial account: `fdauditx9k2m7p4@fldubai.com` / `Str0ngPw123!`, tenant `sectestco1`, form created id **920499** ("form1").
- Permissions: `{editaccount:true, editprofile:false, statistics:true, managelabels:true, createform:true, copyformsto:false}`, roles `["supervisor"]`, subscription 0 (90-day trial).

## Findings & validated negatives

**LOW (validated 3x) — form-ID existence enumeration oracle.** Form IDs are sequential integers (920498/920499/920500 consecutive). `data/settings/<id>/?task=get` returns 200+data for your own form, **403** for an existing form of another tenant, **200 empty** for a non-existent id (same on `view`, `message`). Lets you enumerate ~920k forms; does NOT expose contents → likely informational, non-qualifying under "access user data" bar.

Negatives (all tested, solid security): no SQLi (login/get.asp/data), no user enum (login + forgot-password return byte-identical bodies), IDOR/BOLA blocked (403 on cross-tenant reads AND `task=save/set` writes — server authorizes from session context, not the URL id), CSRF protected (rotating rvtoken; GET `task=save` is a no-op). HSTS, HttpOnly+Secure+SameSite=Lax cookies, X-Content-Type-Options, hidden ASP version.

**Not yet tested** (blocked by JS SPA + headless): stored XSS in form-builder fields (client loads DOMPurify), published-form result exposure, whitelabel "labels" management, registration `domain` mass-assignment collision. These are the likely path to a *qualifying* finding on a revisit.