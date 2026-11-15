---
name: genians-engagement
description: Genians (Genian NAC/ZTNA/CSM) bug bounty — scope, account provisioning that actually works, console/REST map, measured negatives, closed vs still-open leads, and the Art.7.1 reversing prohibition.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, genians, nac, ztna, keycloak, saml, jsf, primefaces, wordpress]
    related_skills: [modern-webapp-auth-hunting, hunt-mfa-bypass, bb-methodology]
---

# Genians Bug Bounty Engagement

Korean NAC/ZTNA vendor. In-house programme (no HackerOne/Bugcrowd) — first in Korea's security
industry, expanded Feb 2026 to cover all products.

## When to Use
Any hunt on `genians.com` / `genians.co.kr` / `genians.net`, Genian NAC, ZTNA, EDR, Insights E,
GPI, IPAM, or the Cloud-managed NAC (CSM).

## Programme facts

| item | value |
|---|---|
| Policy | `genians.co.kr/bug-bounty/policy/en` (rev 2026-01-26) |
| FAQ | `genians.co.kr/bug-bounty/faq/en` |
| Report channel | `bugbounty@genians.com` |
| CSM account | **must** use `my.genians.com/register/?registertype=bugbounty` — a normal signup forfeits the reward |
| Scoring | CVSS 4.0 |
| Payout | Critical 9.0–10.0 → KRW 5.4–9.0M · High 7.0–8.9 → 2.52–3.6M · Medium 4.0–6.9 → 720K–1.8M · Low 0.1–3.9 → 240–480K |
| Payment | month after patch; if unpatched, 60 days after report. High+ triggers a re-test request — no reply in 2 weeks can forfeit |

### In scope
Genian NAC V4.*+ · Cloud NAC CSM (`my.genians.com`, `my.genians.co.kr`, `my.demo.genians.co.kr`,
`gov.genians.co.kr`, `*.my.*`) · PI API `pi-api.genians.com/pi/v1/` · `www.genians.com` ·
"all products/services managed by Genians".

### Out of scope — confirmed third-party, do not report
`invoice.genians.com` (Zoho Books) · `ims.genians.com`, `wiki.genians.com`, `wiki.cloud.*`
(Atlassian Cloud) · status pages (`*.betterstack`) · `survey.genians.com` (Zoho) ·
`genian-mdr-trial-2026` (Cloudflare Pages).

### Art.7.3 exclusions that kill candidates
Simple admin-page exposure · debugging response values / error-page server info · clickjacking ·
page tampering · simple version exposure · missing security headers / plain TLS · self-XSS · simple
reflected XSS · CSRF against CSM · DoS · automated-scanner-only results · 3rd-party OSS fixed by
update · known-disclosed · incomplete "possibility only" reports.

## Known issues — DUPLICATE, never report
Check the live revision against these before spending time:

| advisory | CVSS | issue | fixed at revision |
|---|---|---|---|
| GN-SA-2026-003 / CVE-2026-16520 | 8.7 High | CWP User Search → unauth admin credential disclosure | ≥ 150340 |
| GN-SA-2026-002 | 9.3 Critical | internal IPC endpoint callable externally, unauth | ≥ 148665 NAC / 148670 ZTNA |
| GN-SA-2026-001 | 5.9 Med | ZIP-Slip RCE in agent upgrade | ≥ 148817 |
| GN-SA-2024-001 | — | Blind SQLi | — |
| GN-SA-2023-001, 2021-001/002/003 | — | multi-vuln, Log4j, SQLi | — |

Read your instance version at `GET /mc2/rest/information/version/nac` →
`{"value":"NAC-CLOUD-R-154085-5.0.92.1022"}`. Build `154085` already clears all three 2026
advisories, so do not re-litigate them.

## Access path — how to actually get inside

The public site is a hardened decoy; the product lives behind trial provisioning. Full chain:

1. Register a CSM account — **use the demo Keycloak signup** (`my.demo.genians.co.kr` → Sign up),
   not `my.genians.com/register`, which dead-ends in `login_reregistration`. Verify the email and
   enrol TOTP (see "Account provisioning").
2. Log in → `/common/services` → `try-cloud-gsp`. The trial form posts to
   `POST csm.demo.genians.co.kr/wp-admin/admin-ajax.php` with
   `action=gn_cloud_start_subscribe`, plus a single-use `csrf_token` from
   `action=gn_async_create_csrf_token`.
   **`product` must be the form value `nac` / `nac6`** — `5`/`11` are `value2` lookups and yield a
   misleading "invalid access".
3. Result: `bbt<date>.demo.genians.co.kr`, licence row appears in `services-gsp`.
4. Console: `https://<site>/mc2/faces/adminlogin.xhtml` (JSF + PrimeFaces 8.0). Login with the
   **CSM email + password** created during provisioning.
5. Step 2 of login is an OTP **iframe**: `/mc2/faces/otpAuthDlg.xhtml`, field
   `form1:fldCheckAuthNumber`. The CSM TOTP secret authenticates here too.
6. First login runs EULA → `regist/initialSetup.xhtml` → `mainFrame.xhtml`
   ("<site> - Management Console").

Only 1 trial per account, global across products ("maximum number of trial versions exceeded").
Pick NAC — it is the flagship product surface. **A second account gets its own trial**, which is
how you get a second tenant for cross-account testing.

## Account provisioning — where each surface breaks

| surface | verdict |
|---|---|
| `my.demo.genians.co.kr` → **Sign up** (Keycloak) | ✅ **the only path that works end-to-end** |
| `my.genians.com/register/?registertype=bugbounty` | mails a link, then lands in `login_reregistration` — unverified |
| `csm.demo.genians.co.kr/register` | `302` → `/login`, registration closed |
| `gov.genians.co.kr/register` | creates the account, but login returns `?smcode=signin_pending` — **needs manual admin approval** |

Three traps that look like bugs and are not:

- **`+` aliases are silently invalid.** The email field rejects `RESEARCHER_USERNAME+tag@…` with
  *"입력 가능한 특수문자는 하이픈(-)과 쉼표(.)"* — so the mail never gets sent and it looks like a
  broken mailer. **Use dot-variants instead:** Gmail ignores dots, so `f.zs.us.anto@…` reaches the
  same inbox while being a distinct address to their system. That is what finally produced a
  second working account.
- **gov registration requires 2FA and consent or it silently no-ops:**
  `{"result":false,"message":"Authenticator is required."}` then
  `{"result":false,"message":"개인정보보호 정책 동의 해주세요."}`. Must send
  `authenticator=true` + `ga_secret` + `ga_otp_code` + `agree_privacy=true` + `agree_email=true`.
- **Keycloak action-token links expire fast.** Register → poll the inbox → open the link within
  ~1 minute, in one process. A link opened later returns *"작업이 만료되었습니다"* and you will
  wrongly conclude the token is malformed.

Full working recipe (poll-Gmail → decode TOTP QR from the base64 `<img>` → CONFIGURE_TOTP →
UPDATE_PASSWORD → landed session) and the credentials-file layout:
`references/account-and-action-matrix.md`.

## Console + REST map
See `references/nac-console-map.md` for the full page tree, REST endpoint list, permission model,
and the plugin AJAX surface on `csm.demo`.

## Measured negatives — do not burn time re-testing
Each was verified with a control, not assumed:

- **PI API SQLi** — `news/1e0` resolves, `news/"1 and 1=1"` does not; values are numerically cast.
  The `DEBUG` object only echoes constants (`"server_version":"DB_NAME"`) and is excluded by Art.7.3.
- **SAML** — assertion-signed/response-unsigned is accepted but is **spec-permitted** (WebSSO allows
  signing only the assertion). Strip-all, NameID swap, XSW evil-first/nested/wrapped, and replay all
  refused. Implementation is sound.
- **Keycloak** — password / client_credentials / device_code / `admin-cli` / `account` grants all
  refused; default admin creds refused; DCR endpoint live but WAF returns a branded 403 for every
  well-formed body.
- **NAC JSF resource traversal** — baseline `?ln=css` serves 4541 B CSS; `?ln=../../WEB-INF`,
  encoded variants and `web.xml` are refused. Blocked.
- **NAC REST SQLi** — `pageSize=30'` → type-validation error; `AND SLEEP(4)` 1.17 s vs 1.02 s
  baseline. Not injectable.
- **NAC REST unauth** — `/mc2/rest/nac/nodes` and `genidevices` return the error page, not JSON.
- **Licence parameter tampering** — asked `nodes=10` → got 300 (plan default); asked
  `validityperiod=3650` → got 30 days. Client values ignored at provisioning.
- **Plugin IDOR** — `/order-detail-gsp/?order=N` always "invalid access"; `/getlicense/` and
  `/authority_modify` render only for your own `subscription_id`, empty for neighbours and unauth.
- **`genians/api/v1` dispatcher** — 5,651 command names swept, only `samlauth` + `member` live;
  `member` is admin-only even authenticated.
- **WordPress on CSM hosts** — `wp-json`, `xmlrpc.php`, `readme.html` all 403.

## Ethics boundary (hold this line)
`/authority_modify?subscription_id=X&user_email=Y` can transfer a licence to another account. It is
ownership-checked for foreign ids, so proving cross-account impact would require an **existing
subscription id belonging to another demo tenant** — which means touching a third party's data.
Do not. Provision a **second account of your own** and prove it between your two tenants.
Use a **dot-variant** address (`f.zs.us.anto@…`) — not `user+gen2@…`, because the registration
form rejects `+` outright and the mail silently never arrives. Recipe in
`references/account-and-action-matrix.md` §1.

## Leads — status after the second pass

### CLOSED, measured (do not re-run)
1. **Privilege escalation inside NAC — NEGATIVE.** Built `bbauditor` (role `auditor`, perm 5) via
   the user wizard. Server honours `permLevelMap`: perm-0 pages (`genianDevMgmt`, `setup/configMgmt`,
   `softwareUpgrade`) return `302 -> error.xhtml`; perm-5 pages load read-only. Self-escalation
   attempt on the account's **own** record: `lbxAdminRole` is **not rendered** for readOnly, and
   injecting `form1:userTabView:lbxAdminRole=superAdmin` does not land — PrimeFaces posts only
   registered components, role unchanged after reload. Session-cookie cross-pairing
   (`JSESSIONID` vs `mc.sessionId`) is authoritative on `JSESSIONID` only. RBAC is sound.
2. **Cross-tenant IDOR — NEGATIVE.** With two self-owned accounts, swept 12 AJAX actions
   (`gn_license_download`, `gn_start_stopped_site`, `shop_license_reissue`, `get_acl_ajax`,
   `cloud_console_acl_modify_ajax`, `shop_card_info_modify_ajax`, `gn_deal_check_purchase_state`, …).
   Every one returns `no permission` / `invalid access` / ownership-scoped data for a foreign
   `subscription_id` or `sitename`. Matrix in `references/account-and-action-matrix.md`.
   One anomaly: `gn_deal_check_purchase_state` returns `data:true` for **any** id including
   non-existent ones — but it leaks only a boolean, so it is Art.7.3 "extremely minimal" material.
   Not reportable; do not blow it up into an IDOR.
3. **Authenticated PI API — BLOCKED by design.** `/platform/*`, `/oui/*` are 403 without a key.
   Trial ordering for `gpi`/`gdpi`/`pi`/`13` is refused (`invalid access`) — the trial form only
   accepts `nac`/`nac6`. `shop_license_detail` (which would render `restkey`) returns HTTP 500
   consistently on the demo build. No path to a key from a trial account.

### STILL OPEN (each needs a resource Genians must supply)
4. **CWP design import Tar-Slip — UNPROVEN.** `/mc2/faces/setup/cwpDesignImportDlg.xhtml` accepts
   `tgz|gz` with **client-only** `allowTypes`; the server rejects the upload before extraction
   (`hidUploadComplete` stays `false`, message `!! key mc.setup.cwpDesign.import.errorMsg not found !!`)
   and the traversal marker never lands. Needs a **valid design package** to pass validation;
   Export is unavailable (3093 templates, no row checkboxes, Tasks menu has no Export).
5. **CWP pre-auth portal** — needs a captive-portal session minted by a real network sensor.
6. **Production CSM** (`my.genians.com`) — signups land in `login_reregistration`; see provisioning.

## Policy guardrail — DO NOT reverse-engineer the agent binary

Art.7.1 prohibited acts explicitly include *"Reverse engineering, decompiling, disassembling, or
otherwise duplicating, imitating, or modifying the Service"*. Consequence is reward disqualification
**plus** possible legal liability. So "analyse the NAC agent binary" is closed **by contract**, not
by tooling. If an operator says "gas" on binary reversing, say no and cite Art.7.1 — record the
refusal in the status file so the next session does not relitigate it.

## ⚠️ RETRACTED — the "broken verification email" was my own measurement error

An earlier version of this skill claimed production registration mail was malformed: that the
link contained `…&user_idw74` because the second parameter lost its `=`, making every production
signup unverifiable. **That is false. Do not repeat it.**

What actually happened: the URL was read from **truncated terminal stdout**, where a 1058-char
`action-token` link renders as `key=eyJhbG...ZTkw`. The `...` was my console, not the email.
Reading the same message from the saved raw body showed the link **intact and functional**
(`key` param 766 chars, `client_data` 159 chars, no ellipsis).

**Rule:** never validate a long token/URL from printed output. Write it to a file, then measure
(`len()`, parse the query string, assert no `...`) before concluding anything about the sender.

Nothing was filed on the wrong conclusion, which is the only reason it cost nothing.

## Housekeeping
Policy asks testers to delete trial servers when done. Keep a cleanup list of created sites and
remove them at engagement end.

## Recon — `crt.sh` alone is not enough here

Certificate transparency missed `tech.`, `sso.`, `partner.`, `auth.my.`, `api.my.`, `dashboard.my.`,
`sase.my.` because those hosts reuse certificates and never appear as unique names. A plain label
brute across `genians.com` / `genians.co.kr` / `my.*` found six hosts that CT logs never showed —
and the single highest-value adjacency of the engagement (`auth.my.genians.co.kr`, a *second*
Keycloak) was only discovered by following an OIDC `redirect_uri` leak from `partner.genians.com`,
not by enumeration at all. Brute labels, then follow every auth redirect you see.

Note the scope split: `tech.genians.com` / `sso.genians.com` are **internal IT** (Jira + Crowd),
not product surface. Already reported to the vendor as a good-faith note — do not re-report.

## Support files
- `references/nac-console-map.md` — page tree, REST endpoints, permission map, plugin AJAX actions
  and their exact contracts.
- `references/account-and-action-matrix.md` — second-account provisioning (dot-variant email,
  poll-Gmail, TOTP-from-QR), the 12-action IDOR matrix with real responses, and the adjacent-host
  frontier with its measured negatives.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/genians-audit/PLAYBOOK.md` — the earlier pass over the same programme: scope article
  text, the revision-check query that kills the whole known-CVE list in one request, the reward
  table, and the reversing prohibition. Its `references/genians-surface-map.md` is the denser
  surface map; use it with this skill's console/REST map.
