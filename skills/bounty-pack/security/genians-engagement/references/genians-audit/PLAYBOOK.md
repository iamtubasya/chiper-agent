---
name: genians-audit
description: Genians (Genian NAC / CSM) bug bounty — scope, policy traps, known CVEs, verified negatives.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, genians, nac, csm, keycloak, saml, ztna]
    related_skills: [security:bug-bounty, security:disposable-auth-identity, security:artifact-backed-claims]
---

# Genians bug bounty (Genian NAC / Cloud NAC CSM)

In-house programme (no HackerOne/Bugcrowd). Reports go to **bugbounty@genians.com**; CSM accounts
must register through `https://my.genians.com/register/?registertype=bugbounty` or the reward can be
denied. Read `references/genians-surface-map.md` for the endpoint/app map and what each one returned.

## ⛔ Policy trap that ends the engagement: reverse engineering is FORBIDDEN

Article 7.1 — prohibited acts — names verbatim: *"Reverse engineering, decompiling, disassembling, or
otherwise duplicating, imitating, or modifying the Service."* Consequence is **disqualification from
reward plus potential legal liability**.

So the NAC agent/installer binary is **out of bounds** — do not download-and-reverse it, do not run
`strings`/decompilers on it, do not describe it as "the remaining path". An operator saying "gas" is
not consent to break a written programme rule; surface the prohibition instead and pivot. Same
caution for anything that looks like patch-bypass or license-tamper.

Other Article 7.3 exclusions that kill otherwise-real findings: simple admin-page exposure,
debugging response values, error-page server info, simple version exposure, missing security
headers/simple TLS, self-XSS, simple reflected XSS, **CSRF against CSM**, DoS / automated-scanner-only
results, third-party OSS fixed by update, "extremely minimal attack value".

## Payout (CVSS 4.0, KRW reference amounts, not guaranteed)

| Score | Severity | Reward |
|---|---|---|
| 9.0–10.0 | Critical | 5.4M – 9.0M |
| 7.0–8.9 | High | 2.52M – 3.6M |
| 4.0–6.9 | Medium | 720K – 1.8M |
| 0.1–3.9 | Low | 240K – 480K |

Payment lands the month after the patch is confirmed; if never patched, 60 days after report.

## Scope (Article 3, rev 2026-01-26)

IN: **Genian NAC V4.\*+** · Cloud NAC CSM (`my.genians.com`, `my.genians.co.kr`,
`my.demo.genians.co.kr`, `gov.genians.co.kr`, `*.my.genians.co.kr`) · **PI API**
(`pi-api.genians.com/pi/v1/`) · `www.genians.com` · "all products/services managed by Genians".

OUT: third-party hosting. Confirmed OOS during recon — stop when you see these:
`invoice.genians.com` (Zoho Books), `ims./wiki./www.genians.com` behind Atlassian Cloud
(geni-works.atlassian.net), status pages (Better Stack/`incidents.betterstack.com`),
survey (Zoho).

**Grey zone — decide with the operator, not alone:** `tech.genians.com/jira` (self-hosted Jira),
`sso.genians.com` (Atlassian Crowd SSO), `partner.genians.com`. These are Genians-owned but read as
internal IT, not product, and the FAQ warns *"attempts to find bugs outside the stated products and
services and domains are not allowed by default and may be held accountable."* Send at most a
good-faith notification, worded so the vendor decides scope — do not treat them as bounty targets.

## Known issues = automatic duplicates. Check the revision FIRST.

| Advisory | CVE | CVSS | Patched at revision |
|---|---|---|---|
| GN-SA-2026-003 CWP User Search → unauth admin cred disclosure | CVE-2026-16520 | 8.7 | 150340+ |
| GN-SA-2026-002 internal IPC callable externally unauth | — | 9.3 | 148665+ |
| GN-SA-2026-001 ZIP-Slip RCE via AgentUpgrade | — | 5.9 | 148817+ |
| GN-SA-2024-001 Blind SQLi / 2023 / 2021 (incl. Log4j, SSTI RCE) | — | — | older |

```bash
# authenticated, one request, decides whether the whole CVE list is dead:
curl -sk "https://<site>/mc2/rest/information/version/nac"
# -> {"value":"NAC-CLOUD-R-154085-5.0.92.1022"}   rev 154085 > every row above = all patched
```
Do this **before** probing CWP user search or agent upgrade; on a current build they are patched by
construction and any "hit" is your misread.

## Working an engagement (order that actually produces signal)

1. **Version first** (`/mc2/rest/information/version/nac`) → kills the CVE list or focuses it.
2. **Provision a trial site** so you own a real NAC instance (see next section). Without a site the
   console is a login page; with it you get `/mc2/faces/mainFrame.xhtml`.
3. **Recon the CSM plugin** `/wp-content/plugins/genian_csm/` — `composer.json` is readable and names
   the stack: `onelogin/php-saml ^4.3`, `firebase/php-jwt ^7.2`, `phpseclib ^3.0`. `services/gsp`
   HTML carries the whole admin-ajax action list and hidden fields.
4. **Two owned accounts, then the cross-account matrix.** Use `disposable-auth-identity` for the
   account mechanics; dot-variant Gmail aliases work where `+tag` is rejected.
5. **Write negatives with their control** per `artifact-backed-claims`. This programme's build is
   genuinely hard — the deliverable is often a well-evidenced "not vulnerable".

## Owning a real NAC instance (the unlock)

Sign up on the **demo** tenant (`my.demo.genians.co.kr` → Sign up, Keycloak realm `csm`), then in
CSM → `try-cloud-gsp` submit `action=gn_cloud_start_subscribe`. Only `product=nac` or `nac6` is
accepted (`gpi`/`gdpi`/`pi`/13 all return "invalid access").

```
product=nac  edition=pro  branch=candidate  nodes=10  region=ap-northeast-2
cluster_name=kr-ap-ne2-master  customdomain_yn=N  + fresh csrf_token
-> {"result":true,"message":"success"}   site: <sitename>.demo.genians.co.kr
```

- **Quota is 1 trial per account, global across products.** Second attempt →
  `"maximum number of trial versions exceeded (1)"`. That is why a second *account* is the way to a
  second site, not a second order.
- Server **ignores** client `nodes` and `validityperiod`: ask `nodes=10` receive **300**, ask 3650
  days receive **30**. Not a bypass — the plan defaults win.
- Console login = CSM email + password → IP dialog (submit empty) → **`forceLogin` checkbox** when
  "account already in use" → TOTP dialog in iframe `otpAuthDlg.xhtml`, field
  `form1:fldCheckAuthNumber` (the **same TOTP secret as Keycloak** works) → EULA (pick radio, Finish)
  → Initial Setup (OK) → `mainFrame.xhtml`.
- Newly provisioned sites take minutes; `/mc2/` returns 404 or times out until the vhost is up. Poll,
  don't conclude "broken".

## Verified negatives — do not re-burn time

Build tested: `NAC-CLOUD-R-154085-5.0.92.1022`, two owned CSM accounts, two trial sites.

| Surface | Result |
|---|---|
| PI API `/news/*` SQLi | Values numerically cast: `news/1e0` 200, `news/"1 and 1=1"` not-found → no injection. DEBUG block only echoes constants (+ Art.7.3 excludes it) |
| PI API `/platform/*`, `/oui/*` | 403 without `X-API-key`; trial form cannot mint a PI subscription |
| SAML (`/genians/api/v1/samlauth`) | Assertion signature enforced; response-level signature not (spec-permitted, **not** a bug); 3 XSW variants rejected; replay rejected (one-time use) |
| Keycloak grants | password / client_credentials / device_code all `unauthorized_client` → no token-without-OTP path |
| Keycloak `redirect_uri` | 14 bypass variants (evil host, suffix dot, `@`, traversal, trailing slash, null byte, scheme-relative, wildcard sub, `plain` PKCE) → all 400. Exact match only |
| Keycloak DCR | `registration_endpoint` live but POST → 403 WAF |
| `genians/api/v1/` dispatcher | 5,651 command names swept → only `samlauth` + `member` (admin-only) |
| admin-ajax `gn_*` | 155 names → ~7 live; CSRF token **single-use**; no shell injection in `gdpi_api_call` (SLEEP/timing flat) |
| NAC REST | `/mc2/rest/{nodes,users}` need `?apiKey=`; **session cookie is not accepted** |
| NAC API key | `btnApiKey` disabled even for the main admin ("Synchronized & Not Editable" — cloud editions manage keys in CSM) |
| JSF resource traversal | `?ln=../../WEB-INF` → error page/400; baseline CSS 200 4541 B |
| NAC REST SQLi (`bpnotice/nodes/logs`) | type validation rejects quotes; `SLEEP(4)` no delay |
| RBAC | `permMap` enforced server-side: auditor `genian_mgmt/setup_config=0` → 302 to error; role select **not rendered** for readOnly and a spliced `lbxAdminRole` is not bound by PrimeFaces |
| Session confusion | authority bound to `JSESSIONID`; swapping `mc.sessionId` across roles changes nothing |
| Cross-site session | admin cookie from site A → site B returns the login page. Host-bound |
| IDOR (12 CSM actions) | `gn_license_download`, `get_acl_ajax`, `gn_start_stopped_site` all enforce ownership (`no permission` / `invalid access`) |
| `gn_user_profile_process` | identical `invalid access` for own email, second real account, and nonexistent → rejected **before** user lookup; ATO hypothesis unsupported (see `artifact-backed-claims`) |
| Edition gate | Enterprise-only `configMgmt` renders on Professional but writes do **not** persist (server-enforced) |
| WordPress (www / my / gov) | `wp-json`, `xmlrpc`, `wp-admin`, `wp-login`, `debug.log` all 403; Elementor 4.3.5 current |

## Open leads that need a resource you don't have

State these as **blockers**, not as negative — they are untested, not clean.

1. **CWP design import (Tar Slip)** — `/mc2/faces/setup/cwpDesignImportDlg.xhtml` accepts
   `allowTypes /(tgz|gz)$/` with **client-side-only** extension validation; server rejects the upload
   (`hidUploadComplete` stays `false`, `mc.setup.cwpDesign.import.errorMsg` i18n key missing) because
   it wants a well-formed design package. Blocked: `cwpDesignMgmt` shows 3093 templates but has **no
   per-row checkbox and no Export**, and `btnCreate` opens nothing. Need a genuine design package.
2. **CWP pre-auth** — reachable *with a cookie jar* (`/cwp2/` → `common/design/standard/main.xhtml`),
   and `user.xhtml` shows an `Invalid User Account (...)` oracle, but the name is always empty and no
   GET param is reflected (16 tested). CWP derives node identity from the network
   (`CWP_NODEID`/`CWP_SMAC` empty, `CWP_SRCIP` = CDN IP behind the demo proxy), so the auth flow never
   activates. Need a real sensor/portal or a way to look like a registered node.
3. **NAC agent** — binary reversing **prohibited** (see top). Do not pursue.
4. **PI API authenticated** — need an `X-API-key` from CSM; `shop_license_detail` (which exposes
   `restkey`) returns a consistent 500 on the demo tenant.

## Reporting notes

- One Low shipped from this engagement: `tech.genians.com/jira/rest/api/2/dashboard` returned 18
  internal dashboard names unauthenticated (3× reproduced, fresh connections). Prefix/severity honest
  as **Low**, and its scope is arguable — the draft said so in the body and let the vendor decide.
- Do not claim "no findings" without the coverage table; this programme rewards a precise negative
  with the revision evidence far more than a hopeful Low.
- Cleanup: policy asks you to delete trial servers after testing. Record what was left alive
  (sitenames, accounts) so the operator can decide.
