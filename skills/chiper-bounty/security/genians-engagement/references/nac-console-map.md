# Genian NAC console + CSM plugin — surface map

Collected from a live 5.0.92.1022 instance (`NAC-CLOUD-R-154085`). Paths are relative to the trial
site `https://<site>.demo.genians.co.kr`.

---

## 1. NAC management console (`/mc2/faces/`)

JSF + PrimeFaces 8.0. Session cookies after login: `JSESSIONID`, `adminLocale`, `mc.sessionId`.

### Login chain
```
/mc2/                       -> 302 -> /mc2/faces/adminlogin.xhtml
adminlogin.xhtml            form1:userId / form1:passwd / form1:dologin
   (correct password)       -> "Please enter your Authentication Code"
OTP iframe                  /mc2/faces/otpAuthDlg.xhtml
                            form1:fldCheckAuthNumber / form1:actionBtn
regist/userAgreement.xhtml  radio form1:j_idt21:0 .. :1 + form1:btnConfirm (Finish)
regist/initialSetup.xhtml   form1:btnConfirm (OK)
mainFrame.xhtml             <site> - Management Console   (menu + iframe mainIframe)
```
`wait_until="networkidle"` times out — the console long-polls. Use `domcontentloaded`.

### Page tree (real paths, harvested from request capture)
```
dashboard/frame.xhtml  widgetContainer.xhtml
  wgNodePlatform.xhtml  wgNodePolicy.xhtml  wgNodeType.xhtml
  wgRolePolicy.xhtml    wgUpNodeChart.xhtml
management/  frame tree  genianDevMgmt  port  softwareUpgrade
monitor/     frame tree  nodeMgmt  ipMgmtFrame  ipMgmtTree
network/     frame tree  swIfMgmt
policy/      frame tree  permMgmt  subjMgmt  systemMgmt
report/      frame tree  reportResult
setup/       frame tree  configMgmt  cwpDesignMgmt  genidevMgmt
user/        frame tree  userMgmt  userAppMgmt
ipmgmt/      frame tree
stat/        nodeSensorStat
```
Guessing page names returns a **generic 1109-byte error page** — if you see 1109 on an authenticated
request, the path does not exist (or the request was rejected). That size is the cheap sentinel for
this product.

### REST (`/mc2/rest/…`) — JSON when authenticated
| endpoint | notes |
|---|---|
| `sessions/current` | `myLocale`, `permLevelMap` (0 noPerm, 5 readOnly, 10 edit, 15 addEdit, 20 fullControl), `adminPermMap` per module |
| `information/version/nac` | `{"value":"NAC-CLOUD-R-154085-5.0.92.1022"}` |
| `nac/nodes` | node list JSON (~2.9 KB) |
| `nac/genidevices` | JSON (~860 B) |
| `nac/menutree` | requires params else error page |
| `nac/bpnotice` | paging: `page`, `pageSize` |
| `nac/commondata/servertime` | epoch ms |
| `nac/commondata/chartData/reportResultData/` | chart data |
| `nac/applications/license/page` | licensed-feature gate; params `mode`, `query`, `pageurl`; returns `pageLimitPerm` + edition warnings |
| `logs`, `reports` | `logs` needs filters; `reports` returns `{"result":[],"total":0,...}` |

Unauthenticated → the 1109 error page, **not** JSON. Use content-type as the auth oracle.

### Permission model
`permLevelMap`: `{fullControl:20, addEdit:15, edit:10, readOnly:5, noPerm:0}`.
A freshly provisioned site makes you full admin: every `adminPermMap` value is `20`.
Privilege-escalation test = create a read-only admin and check whether the server enforces 5.

---

## 2. CSM plugin (`csm.demo.genians.co.kr`)

WordPress + Elementor 4.2.3 / Elementor Pro 3.32.3 / Astra, plus custom plugin **`genian_csm`**
(composer: `onelogin/php-saml ^4.3`, `firebase/php-jwt ^7.2`, `phpseclib ^3.0`).
Caveat: WP here is a real plugin; the console-adjacent product front end.

### `wp-admin/admin-ajax.php` — live `gn_*` actions
Full sweep of ~155 names found exactly these registered. Any other name returns a literal `0`
(the "not registered" sentinel — cheap discovery oracle).

| action | contract |
|---|---|
| `gn_async_create_csrf_token` | `{"result":true,"csrf_token":"<114 hex>"}` — **single-use**; reuse returns "invalid access" |
| `gn_get_plans` | `product` = `value2` (5 NAC, 6 NAC server, 8 EDR, 11 ZTNA/NAC6, 12, 13 GPI, 14 KEYCLOAK, 15). Returns plan catalogue: `plan_code`, `trial_period:"30"`, `addons`, prices, `def_edition`. All `account_id:null` = public catalogue, no tenant leak |
| `gn_get_branches` | `product` = display name; returns `["current","beta","candidate","release"]` |
| `gn_get_regions` | with csrf; returns regions e.g. `ap-northeast-2` / `kr-ap-ne2-master` |
| `gn_cloud_start_subscribe` | trial creation (see engagement SKILL.md); multipart; `product` = `nac`/`nac6` |
| `gdpi_api_call` | server-side curl to "GDPI REST API"; needs a real `subscription_id`; injection probes (`;sleep`,`$(sleep)`,backtick,pipe,curl flags) showed **no** timing delta |
| `gn_site_publicip_check` | `subscription_id` + `sitefullname`/`sitename` |
| `authority_modify` | licence ownership delegation: `subscription_id`, `user_email`, `modify_authority_email` |

### Page-level endpoints
```
/services-gsp/                 licence table, Service ACL, SSL cert/key upload, password change
/billing-history-gsp/?type=profile   billing iframe; `type` values other than `profile` render empty
/try-cloud-gsp                 trial form (product/edition/nodes/sra_count/customdomain/validityperiod)
/order-detail-gsp/?order=N     ownership-checked; foreign N -> "invalid access"
/getlicense/?subscription_id=N licence page; only own id renders, foreign -> empty
/authority_modify?subscription_id=X&user_email=Y   delegation form; own only
/delete-cloud-site-gsp/?sitename=   destructive — GET must not be fired casually
/create-account/?id=N
```

### Leaked in page JS
`var customer_id = '4102';` and the licence row exposes `subscription_id` (numeric, sequential-ish)
plus `plan_code` (e.g. `NAC-CLOUD-PRO-M`).

### SAML SSO hop
`POST csm.demo.genians.co.kr/genians/api/v1/samlauth` ← form field `SAMLResponse` (b64) +
`RelayState`. Response is `<script>var redirectUrl='…/services-gsp/'</script>{"result":true}`.
Assertion is signed; the response signature is optional per spec. Configured via
`csmauth.demo.genians.co.kr/realms/csm/protocol/saml`.

---

## 3. Discovery notes
- Subdomain enumeration via `crt.sh?q=%.genians.com&output=json` yielded the infra names that
  matter (`*.gsp`, `*.infra`, `status-*`, `ims`, `wiki`) — but most resolve to third-party hosting.
- `infra.genians.com` = Apache blanket 403 on every path.
- `my.genians.com` / `gov.genians.co.kr` / `csm.demo` are all WordPress; only `csm.demo` exposes the
  `genian_csm` plugin JS that maps the GSP flow.
- BFF on `my.demo.genians.co.kr` (`/api/*`): `auth/me`, `platform/capabilities`, `public/menus`,
  `public/common-menu-routes`, `tenants`, `menus` (needs `X-Tenant-ID`), `common-menus` (reveals
  every `iframeUrl`, i.e. the app catalogue). `X-Tenant-ID` is **not** authorised — `admin`,
  `system`, `0`, non-existent tenants all return 200 — but every reply was empty, so no data
  exposure. Re-check only with a second tenant that actually has menu rows.
