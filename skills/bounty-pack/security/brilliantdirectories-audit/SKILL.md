---
name: brilliantdirectories-audit
description: Hunt Brilliant Directories (BD) platform software — public bounty scope, /wapi/widget unauth widget router, REST API v2 auth model, trial-site provisioning, MCP repo docs. Use when the target is brilliantdirectories.com, a directoryup.com / managemydirectory.com trial site, or any BD-powered directory site.
---

# Brilliant Directories (BD) — engagement notes

Money page: https://www.brilliantdirectories.com/security-bounty ($25–$500 per bounty).
Submit by EMAIL to security@brilliantdirectories.com (no platform, no tracker).

## Scope (read carefully — inverted vs normal programs)
IN scope: the **software product** (any BD-powered site / instance), i.e. the platform code that
customers buy. Reward examples listed by the vendor:
- IDOR on the **frontend** of a website      <- the highest-value, most reachable class
- SQLi that affects **other** websites/databases (NOT the local site DB)
- admin permission escalations that impact **other** websites

OUT of scope:
- Anything about the www.brilliantdirectories.com marketing website itself
- Exploits that only need the admin's own code/DB access (Widgets system, direct DB)
- XSS (admin or frontend), CSRF in admin, admin role escalation **inside one site**
- SQLi against the site's own local DB, SPF/DKIM/DMARC, TLS/CSP best practice, tabnabbing,
  clickjacking без sensitive action, rate-limit/brute force on non-auth endpoints, 3rd-party modules

Implication: **cross-tenant / platform-level** impact is what pays. Anything an admin of one site
can already do to their own site is a non-finding.

## Getting a target to test (fast)
```bash
# public trial provisioning widget on BD's own directory install (no auth)
curl -s -X POST https://directory.brilliantdirectories.com/api/widget/json/post/free-trial-hubspot-submit-complete \
  -H "X-Requested-With: XMLHttpRequest" -H "Referer: https://directory.brilliantdirectories.com/trial" \
  -F action=launch_trial -F theme_template_id=3579 -F devmode=1 -F editmode=1 \
  -F website_name=qa-001 -F yourname=QA -F inquiry_email=you+bd1@example.com -F phone= -F bd_hpc=
# -> {"admin_id":..,"admin_token":"..","website_id":"68216","login_url":"https://ww2.managemydirectory.com/admin/login.php"}
```
- Site URL: `https://launch<website_id>.directoryup.com` (same IP 66.147.238.90 for all trials).
- Admin console: `https://ww2.managemydirectory.com/admin/` — login by POSTing
  `admin_token=<tok>&newsite=<id>&website_id=<id>&sessionPassedTransfer=1&action=login&session_page=setupWizard.php?fill=1&newsite=<id>` to `/admin/login.php`.
  Run `GET /admin/setupWizard.php?fill=1&newsite=<id>` to flip the site from Suspended to Active.
- API key: `POST /admin/apiSettings/create/save` with `apikey[name]=x` (+ `X-Requested-With`,
  `Referer: .../admin/apiSettings`). Token is returned once (32 hex). Baseline key = members
  read/write only; everything else is "Advanced Endpoints" → 403.
- `POST /admin/apiSettings/generateSuperKey` → 400 "Only super admins can generate super API keys" (correctly gated).
- Trial sites get auto-**Suspended** if you trip the WAF; the whole `*.directoryup.com` vhost can
  firewall-block your egress IP (CSF page "Unauthorized Access … blocked IP" or plain LiteSpeed 403 1242).

## REST API v2 (per site)
- Docs: `git clone https://github.com/brilliantdirectories/brilliant-directories-mcp` → `docs/api-*.md`
  (30 resources, exact paths/fields; also the official MCP server at brilliantmcp.com).
- Auth headers: `X-Api-Key` + `X-BD-Site-URL: https://<host>`.
- Keys are **per-site**: our key on another install → `401 API Key is invalid` (verified negative).
  The `X-BD-Site-URL` header does not switch tenants (ignored).
- Filtering: `property[]` / `property_value[]` / `property_operator[]`; sorting `order_column` +
  `order_type` — classic SQLi surface (column/operator not enforced by PHP, only by the WAF).
- `POST /api/v2/user/login` with email+password returns `{"message":"credentials are valid"}` —
  a password oracle behind the API key (rate limit 100/60s).
- `auto_image_import=1` with `logo`/`profile_photo`/`cover_photo` = **server-side fetch (blind SSRF)**:
  the platform server (66.147.238.90) performs a GET to the attacker URL. Confirmed 3/3 via interactsh.
  The fetched body is NOT stored when it is not a valid image, so it stays blind.

## The best surface: the widget router (unauth)Two unauthenticated entry points on every BD site:
- `GET /wapi/widget?widget_name=<name>&request_type=GET&header_type=json&<params>` — executes the
  widget's server-side PHP
- `GET|POST /api/data/html/get/data_widgets/widget_name?name=<name>&<params>` — renders by name
  (`/api/widget/json/get|post/<name>` is the older form variant used by theme forms)

Widget inventory with full PHP source: `GET /api/v2/data_widgets/get?limit=100&page=N` (520 rows on a
default install; 415 contain `<?php`). Save them and grep — this is effectively the product's source.

### Confirmed weakness #1 — unauth RCE (CRITICAL, separate submission)
`Bootstrap Theme - Text Labels - Save Actions` has **no auth check at all** — only `isset($_GET['save'])`.
It writes any POST field into `website_labels_translation`, and `Website - Main Footer Scripts` runs
`eval("?>".$label[widget_javascript]."<?")` on every page. One unauth POST → **persistent PHP RCE**.
Write routes: `POST /api/widget/json/post/<widget>?save=1` or
`POST /api/data/html/get/data_widgets/widget_name?name=<widget>&save=1`.
Verified 6/6 on 2 installs. Full detail + pitfalls (page cache masks the proof; `$key` is SQLi) in
`references/confirmed-label-widget-rce.md`.

### Confirmed weakness #2 — frontend IDOR (reported as its own finding)
Full repro, evidence hashes, widget table and the companion SSRF:
`skill_view("brilliantdirectories-audit", file_path="references/confirmed-frontend-idor.md")`.
Default **account** widgets derive the acting member from request data, not from a session:
- `Bootstrap Theme - Account - Reviews Datatable`: `if (!isset($_COOKIE['userid'])) $_COOKIE['userid'] = $_GET['user'];` then `WHERE user_id='$_COOKIE[userid]'`
- `Bootstrap Theme - Account - Invited Contacts Table`: `WHERE user_id='$_COOKIE['userid']'` and prints
  `$invite['email']` (invitees' e-mail addresses)
- `Bootstrap Theme - Account - Leads - New Lead System DataTables`: `WHERE lm.user_id='$_COOKIE[userid]'`,
  returns lead_name / lead_location / lead_email / lead_message
- `Bootstrap Theme - Account - Manage Digital Products`: `$_COOKIE['userid']` + `$_GET['data_id']`
- `Bootstrap Theme - Billing - Invoice Purchase Confirmation`: `$_REQUEST['invoiceid']` → WHMCS
  `getinvoice` with no ownership check (returns line items/amounts) + reflects `itemdescription1`/`itemamount1`
- `showquery=1` on several datatables echoes the generated SQL (free SQLi confirmation + info disclosure)

PoC (no cookies at all):
```
GET https://<any-bd-site>/wapi/widget?widget_name=Bootstrap%20Theme%20-%20Account%20-%20Reviews%20Datatable
 &request_type=GET&header_type=json&action=data_table&user=4242&start=0&length=3&showquery=1
-> 200 + "SELECT * FROM `users_reviews` WHERE `user_id`='4242' ..."
```
Contrast: `/account` unauthenticated → `302 /login?login_direct_url=/account` (the gate the router skips).

Widgets that DO check properly: `Bootstrap Theme - Function - Comment Handling` (HTTP_ORIGIN +
validateCSRFToken + `user::isUserLogged`), `Bootstrap Theme - Account - Feature Edit` (owner compare).

## Pitfalls learned the hard way
0. **Prove the gate, then the bypass.** A 200 from an AJAX/renderer endpoint alone is not a finding — it can
   be public-by-design. The finding is the *contrast*: the page that serves the data is 302/403 without a
   session, while the renderer that feeds it answers 200 and honours a client-supplied member id. Capture
   both, 3x, with body hashes. Then add a differential (id A vs id B → different body) so "empty shell"
   is ruled out.
1. **WAF**: LiteSpeed + ModSecurity. Short/generic UA (`Mozilla/5.0 Chrome/131.0`) → 403 1242 on many
   paths; send a full Chrome UA. Many AJAX paths additionally need `X-Requested-With: XMLHttpRequest`
   (+ `Referer`). `ffuf -t 8` → everything 403; use `-t 1 -rate 20`.
2. **SQLi payloads get you blocked**: `AND 1=1`, `extractvalue(...)`, `SLEEP()` → 403, then the whole
   trial vhost/IP is firewalled ("Unauthorized Access … blocked IP"). Prove injection with `showquery=1`
   and source review, not with payloads.
3. Front-end member login needs reCAPTCHA ("Invalid recaptcha response or setup") — you cannot simply
   POST credentials. Set the Google **test** keys in Admin → General Settings (`recaptcha_site_key`
   `6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI`, secret `6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe`) on
   your own trial site if you need a member session.
4. Fresh trial sites are created **Suspended**; `setupWizard.php?fill=1&newsite=<id>` activates them.
5. `admin_token` is bound to its own website_id (passing another site's id logs you into your own site),
   and the `newmanage` session cookie is site-bound — no cross-tenant there (verified negatives).
6. Trial signup with an e-mail that already has a trial returns `has_trial` (no token leak). Passing
   `website_id` is ignored.
7. The Gmail API token in this environment expires weekly (OAuth app in Testing) — plan draft delivery
   around that; produce a `.eml` fallback with the PDF attached.

## Reporting shape that fits this program
Lead with the **in-scope category verbatim** ("IDOR on the frontend"), then the router-bypass one-liner,
then a numbered repro with raw curl, the `showquery` SQL echo as the smoking gun, the PII fields the
widget set returns, 3-host x 3-run evidence table with hashes, and an explicit "what this is NOT"
(not admin-area, not XSS/CSRF, not local-DB SQLi) because those are the vendor's OOS buckets.

Deliverable that was built and staged for this engagement (`~/bounty/bd/`):
`make_report.py` (reportlab, uses the pdf-bug-report-generation structured template) → 4-page PDF;
`email_draft.txt` → `draft_brilliantdirectories.eml` (PDF attached) → Gmail Draft via API.
Draft, never sent, until the operator says "kirim".

**Separate submission:** the API blind SSRF (`auto_image_import=1` + `logo`) is a *different* finding
from the widget IDOR — one finding per email, do not merge.

Full technique — how to mine a component-render surface, the auth-smell table, evidence discipline,
and the verified negatives — is in `references/widget-surface-mining.md`. Read it for any BD re-hunt
or for any other widget/block/shortcode platform.

Full mining procedure, the high-value widget shortlist with the exact code smells, the five-part proof
set, and the verified-negative table (per-site API keys, site-bound tokens, super-key gate, trial
provisioning quirks): **`references/widget-surface-mining.md`** — read it before re-hunting this product.

## Delivery discipline (this program is email-only)
- One finding = one email. F1 (frontend IDOR) and F2 (API `auto_image_import` blind SSRF) are separate
  submissions; never bundle them.
- Default = DRAFT in Gmail, never `.send()` without the user's explicit "kirim". The vendor's own
  guidance ("we strongly recommend a working exploit") rewards detail, not speed.
- Prove draft state instead of assuming it: `q='in:sent to:security@brilliantdirectories.com'` must be 0
  (a plain `q='to:...'` also counts the draft and reads as "already sent").
- Attach the structured PDF (see skill `pdf-bug-report-generation`, template
  `report_style_structured.py`) plus the raw response bodies; include the sha256 prefixes in the
  evidence table so the vendor can diff runs.
