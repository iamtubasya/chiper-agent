---
name: formdesk-audit
description: Formdesk (formdesk.com) bug-bounty engagement — scope, app architecture (Classic ASP `!` router + /data/<obj>/<id>/?task=<op> API, sharded fdN.admin.formdesk.com, tenant-per-white-label-domain, sidn/rvtoken rotating session + email 2FA), working account + form, findings, and the curl→browser session bridge. Use when auditing formdesk.com or re-visiting this target.
sources: authorized-engagement
report_count: 1
---

# Formdesk — bug bounty engagement

## Scope & channel (read FIRST)

- Program: `https://formdesk.com/en/security-exploit-bounty-program/`
- Contact / submit: `info@formdesk.com` — **one bug per email thread**. PayPal reward, discretionary (no min/max).
- Qualifying: auth flaws · circumvention of Platform/Privacy permissions model · XSS · CSRF (NOT logout CSRF) · server-side code execution.
- NON-qualifying: best-practices/headers (incl. weak CSP) · DoS · "send malicious links" · 3rd-party sites · issues on the marketing site itself (`formdesk.com /en|/nl|/de`) · SPF/DKIM/DMARC.
- In-scope product: `www.formdesk.com` → shards `fdN.admin.formdesk.com` (fd1..fd26). The WordPress marketing pages are OOS; the app/product is in scope.
- Core business: form-builder SaaS (subscription tier). Alur nilai: signup/email-verify → trial → build form → publish → respondents fill → results/export.

## Architecture (reverse-engineered, non-obvious)

- **Stack:** Classic ASP on Windows IIS (`meta name="handled-by" content="WAS8"`). Custom `!` route separator + `/data/<obj>/<id>/?task=<op>` JSON/XML API. `X-Powered-By` is emptied (version hidden).
- **Sharding:** entry `www.formdesk.com` fronts `fd1..fd26.admin.formdesk.com` (fd1=77.87.163.50, fd2-26=77.87.163.32). Browser routes to a shard via redirect; curl hits www and follows.
- **Tenant model:** every account = a "white-label domain" path segment (`/sectestco1/`). Registration `domain` field is auto-derived from company name and server-uniquified by appending `1` (company "SecTestCo" → domain "sectestco1") — collision IS prevented.
- **Auth/session (the hard part):**
  - Registration: email → 6-digit code (`POST /data/verification/0/?task=check&...&type=account&todo=send|code|pending`).
  - Login: `POST /!login/try/` (txtUsername+txtPassword+ts+__rvtoken) → MANDATORY email 2FA → `POST /<tenant>/!login/twofactor/` with `code`. 2FA code endpoint: `GET /<tenant>/data/twofactor/0/?task=check&...&type=backend&value=email`.
  - Session tokens: `sidn` (rotating per-request nonce, in URL + `backend.<sidn>` + `rvtoken.<sidn>` cookies) · `rvtoken` (rotating CSRF/anti-replay, format `BASE64{epoch}`) · `session.backend.secure` cookie (`<n>::<token>`, HttpOnly+Secure+SameSite=Lax) · `id_session=<n>::<token>` appears in post-2FA redirect URL.
- **API pattern:** `/data/<object>/<id>/?task=<op>&single=false&silent=false&lang=2&random=<6>&sidn=<sidn>`. Objects found: `summary_forms`, `labels_forms`, `settings`, `view` (form field mergecodes), `message`, `users`, `mergescodes`, `ping`, `logout`, `verification`, `twofactor`. `task` ops: `get`/`check`/`save`/`set`/`delete`/`combine`/`getvalue`.
- **Form content model:** `view/<formid>` = mergecodes (system fields have negative IDs `_fd_*`); settings; multi-view layout. Form content (title/questions) is SAVED via `silentSubmit` → POST `document.builder.action + '&xml=true'` with `collectFormData(builder)` — requires the SPİA form builder; cannot be replicated by curl. Renderer: `GET /<tenant>/?action=7&step=20&nextstep=30&prevaction=7&type=1&id_form=<id>&xml=true` returns the whole rendered form HTML.
- **Public form (respondent, NO auth):** `https://www.formdesk.com/<tenant>/<form-name>` → renders title into `<title>` AND `<h1 class="Title">`. Submit: `POST /<tenant>/<form-name>/~new/?sidn=...` (has anti-bot: double-click "re-click" + bot-detection `_fd_events/_fd_duration/_fd_started` + submission key `_fd_rid/_fd_guid`). `_fd_asc` hidden field = `base64("<formid><formname>")` → leaks form id/name to the public.

## Working test account (created 2026-11-01)

- email `fdauditx9k2m7p4@fldubai.com` (mail.tm) / `Str0ngPw123!` / tenant `sectestco1` / form **id 920499** (name `form1`, title "This is the form title", state published-but-inactive).
- Login is email+password → email 2FA code; read the code from mail.tm API.

## Findings & coverage (validated 3x)

- **LOW (likely non-qualifying): form-ID sequential enumeration.** Form ids are sequential integers (920498/920499/920500 consecutive). `data/settings|view|message/<id>/?task=get` returns `200+data` (own) vs **403** (exists, other tenant) vs `200 empty template` (non-existent). The 403-vs-200-empty differential + sequential ids = enumerate every form on the platform (~920k). No content exposed → informational, NOT the bounty's "access user data" bar.
- **Verified-null (strong security):** IDOR protected (read AND write/save/set → 403 cross-tenant) · no SQLi in login/get.asp/data · no user enum (login + forgot-password `?action=3&step=1` return byte-identical 200) · CSRF via rotating rvtoken (`task=save` GET is a no-op) · `data/logout` GET = logout-CSRF only (excluded).
- **UNPROVEN lead (needs headed browser):** stored XSS in form title/field label — title renders raw into `<h1>`/`<title>` on the public form; DOMPurify (`purify.min.js`) is client-side only, Classic ASP backend may render raw. BLOCKED on injecting: content save requires the form-builder SPİA drag-drop, open the existing form via `a[title="Edit form..."]` (the Modified-date link in the summary row) — NOT the name/title/row themselves (`.click()`/`.evaluate().click()` no-op on the draggable row). **Headed Playwright (headless=False) + fd.py storage_state + sidn URL reaches the builder** where headless looped. **STYLE-only save endpoint found:** `POST /!forms/<id>/layout/builder.asp?lang=2&sidn=<sidn>&next=summary` (triggered by `FD.Backend.Save({'route':'#'})`), body = `<=<key<=>value>=>` serialization of 33 style fields (theme, title_properties, border_properties, …; the `forms` field is EMPTY). **Title TEXT lives only in `summary_forms.list[].title`** (NOT in settings/view/builder fields) and is edited inside a custom WYSIWYG editor (`body.window-wysiwyg`, iframe `empty.htm`, `#formtitle` is a plain non-contenteditable div) → no curl-able field carries the title, so content injection still needs driving the WYSIWYG editor.

## Session/automation notes (reusable)

- curl login works (`fd.py` session helper: GET /login → extract sidn/rvt from `application-info` meta → POST !login/try → POST /data/twofactor (read code from mail.tm) → POST !login/twofactor). **The session cookie is short-lived; re-login fresh each run** (saved pickle 401s within minutes).
- **Bridge curl session → browser SPA:** convert `requests` cookie jar to Playwright `storage_state` (dict with name/value/domain/path/expires/secure/sameSite) AND include `sidn=<sidn>` in the navigated URL. Direct URL nav WITHOUT sidn → "session lost". This is how the summary page (JS-rendered form list) was reached.
- Playwright: `page.evaluate("()=>JSON.stringify(<expr>)")` + `json.loads` on return avoids null serialization from `el.className`/complex DOM objects. SPA navigation to `!forms/<id>/<tab>/` via raw URL redirects to summary — must go through the JS click flow.

State files live under `~/formdesk/` (fd.py session helper, ENGAGEMENT_NOTES.md, draft_email.txt, playwright_state.json, fd_state.json).