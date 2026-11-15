# Genians surface map (observed 2026-10-27)

Everything below was enumerated from a bug-bounty account on the demo tenant plus two trial sites.
Values are what the target actually returned, so this is a starting map, not a guess list.

## Hosts

| Host | What it is | Note |
|---|---|---|
| `my.genians.com` / `my.genians.co.kr` | legacy CSM (WordPress + `genian_csm` plugin) | no BFF `/api/*`; registers → email-verify |
| `my.demo.genians.co.kr` | **new CSM shell** — React + Module Federation, BFF at `/api` | the one with real API surface |
| `csmauth.demo.genians.co.kr` | Keycloak, realm `csm`, client `nexus-proxy`, PKCE S256, forward-auth BFF | TOTP enforced on browser flow |
| `csm.demo.genians.co.kr` | WordPress + Elementor 4.2.3 / Pro 3.32.3 + `genian_csm`; SAML SP | also hosts `/services-gsp/`, `/profile/`, `/try-cloud-gsp` |
| `gov.genians.co.kr` | WordPress CSM | signup exists but **login requires admin approval** (`?smcode=signin_pending`) |
| `<site>.demo.genians.co.kr` | **the actual NAC policy server** (JSF + PrimeFaces 8.0) | console `/mc2/`, captive portal `/cwp2/` |
| `pi-api.genians.com/pi/v1/` | PI API, Swagger at `/apidocs/`, spec `Pi_openapi.json` | `/news/*` open, `/platform/*` `/oui/*` need key |
| `auth.my.genians.co.kr` | **separate** Keycloak; realms `ztna-sase`, `partner`, `master` | found only via a leaked `redirect_uri`, not by DNS |

Not in scope / do not touch: `invoice.genians.com` (Zoho), `ims./wiki.genians.com` (Atlassian
Cloud), `status*` (Better Stack), `survey.genians.com` (Zoho).

## PI API (6 endpoints, spec-verified)

```
POST /platform/detect          needs X-API-key
GET  /platform/{platform_id}   needs key
GET  /platform/search          needs key
GET  /oui/search               needs key
GET  /news/search              OPEN  (locale, page_number_of_result, number_of_result)
GET  /news/{news_id}           OPEN  (numeric cast; DEBUG block echoes constants only)
```

## New CSM BFF (`my.demo.genians.co.kr/api`)

```
GET /api/health                   200 no auth
GET /api/auth/me                  200 no auth  -> {"authenticated":false} when anonymous
GET /api/public/menus             OPEN  -> leaks tenantId + iframeUrl app paths
GET /api/public/common-menu-routes OPEN -> /common/* route list
GET /api/tenants                  auth  -> tenant "default" (ownerUserId null)
GET /api/common-menus             auth  -> full menu tree incl. every iframeUrl
GET /api/menus                    auth  + REQUIRES header `X-Tenant-ID` (400 without it)
GET /api/platform/capabilities    auth
```
`X-Tenant-ID` is **not authorised** — `admin`, `system`, `genians`, `0`, `1` all return
`{"success":true,"data":[]}`; but every reply is empty, so no data exposure was provable. Treat as
unproven, not as an IDOR.

Runtime config leaks the auth design: `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM=csm`,
`VITE_OIDC_CLIENT_ID=nexus-proxy`, `VITE_AUTH_MODE=forward-auth`, `VITE_DEV_BYPASS_AUTH=false`.

## `genian_csm` plugin (WordPress on every CSM host)

```
/wp-content/plugins/genian_csm/composer.json           200  -> onelogin/php-saml ^4.3, firebase/php-jwt ^7.2, phpseclib ^3.0
/wp-content/plugins/genian_csm/shop/gsp-theme-override.css  200
/wp-content/plugins/genian_csm/genians/                200 on my./gov. hosts
POST /genians/api/v1/samlauth                          the SAML SP; returns {"result":true}
     /genians/api/v1/member                            admin-only (`no permission to view this page`)
```
Dispatcher behaviour: unknown command → `{"error":"unknown command <name>"}` (HTTP 400) — that is the
fingerprint to sweep against.

## `services-gsp` admin-ajax actions (the real inventory)

Extracted from the page's own JS; each with its actual parameters:

```
gn_async_create_csrf_token                                        single-use token
gn_get_plans                 product, productname                 plan catalogue
gn_get_branches              product                             current|beta|candidate|release
gn_get_regions               product, csrf_token                 ap-northeast-2
gn_cloud_start_subscribe     sitename,region,cluster_name,email,company,
                             firstname,lastname,password,edition,branch,
                             nodes,sra_count,language,customeremail,product,
                             product_name,customdomain_yn,customdomain,
                             extend_content,validityperiod,csrf_token
gdpi_api_call                subscription_id,startdate,enddate      "GDPI REST API CURL"
gn_gdpi_reissuance           subscription_id,restid,plan_code
gn_site_publicip_check       subscription_id,sitefullname,sitename
search_company_name_by_siteid siteid,sitename
gn_license_download          subscription_id                     -> license + serverid
gn_deal_check_purchase_state subscription_id                     -> boolean only
gn_start_stopped_site        subscription_id
shop_license_detail          subscription_id                     -> product_values incl. restkey (500 on demo)
shop_license_reissue         subscription_id,new_serverid
shop_license_change_maintenance   subscription_id,edition,maintenance_date,product_type
shop_license_extend_maintenance   subscription_id
shop_license_cancel_subscription
shop_license_add_billing_addr / _del_billing_addr
shop_card_info_modify_ajax   card_number,cvv,expiry_month,expiry_year,name,nickname,
                             target_id,street,city,zip,state,country
get_acl_ajax                 sitename,ec2_ip                     -> console ACL
cloud_console_acl_modify_ajax acl,sitename,sitefullname,ec2_ip,userpassword
gn_bizportal_siteid_change   bizportal_site_id,company_name,customer_id,deal_id
```

Profile/registration action (also used by `/profile/`):

```
gn_user_profile_process  email,company,registertype,firstname,lastname,oldpassword,
                         newpassword,newpassword2,timezone,authenticator,iam_authenticator,
                         ga_otp_code,ga_secret,referralcode,csrf_token,d_mac,d_version,
                         d_urlversion,d_license,d_return,d_option,
                         agree_privacy,agree_email
```
Required extras discovered the hard way: `authenticator=true` → `"Authenticator is required."`;
`agree_privacy=true` → `"개인정보보호 정책 동의 해주세요."`

## NAC console (`<site>/mc2/`)

```
faces/adminlogin.xhtml          login: form1:userId, form1:passwd, form1:forceLogin
faces/allowIpDlg.xhtml          iframe: "Enter IP1/IP2"; OK with empty fields proceeds
faces/otpAuthDlg.xhtml          iframe: form1:fldCheckAuthNumber  (TOTP)
faces/signin/mfa.html           enrollment: "Continue without two-step verification" available
faces/regist/userAgreement.xhtml, regist/initialSetup.xhtml   first-login wizard
faces/mainFrame.xhtml           dashboard shell (menu: Dashboard/Management/Log/Policy/Preferences/System/Community)
faces/user/userMgmt.xhtml       + userWizard.xhtml?cmd=create&selectedTab=userSelectTab
                                tabs: Select(0) General(1) Administrator(2)
                                fields: fldId,fldName,lbxAdminRole,fldPasswd,fldConfirmPasswd,USER_EMAIL
                                roles: <Not Selected> | auditor | ipAppManager | superAdmin
faces/user/user.xhtml?id=<email>&selectedTab=userTab&view=userMgmt   profile editor
faces/user/setIpMacAuthLimit.xhtml  auth IP/MAC/device limits (0 = unlimited)
faces/setup/configMgmt.xhtml    System Config (Enterprise-gated; renders on Pro, writes rejected)
faces/setup/cwpDesignMgmt.xhtml, cwpDesignImportDlg.xhtml
faces/management/{genianDevMgmt,port,softwareUpgrade}.xhtml
faces/policy/{permMgmt,subjMgmt,systemMgmt}.xhtml
faces/monitor/nodeMgmt.xhtml, network/swIfMgmt.xhtml, report/reportResult.xhtml
```

REST (`/mc2/rest/`) — all need `?apiKey={uuid}`; a session cookie is not accepted:

```
/sessions/current                 -> myLocale, permLevelMap, adminPermMap, defaultPermMap
/information/version/nac          -> NAC-CLOUD-R-<rev>-<version>   <-- START HERE
/nac/nodes, /nac/genidevices, /nac/menutree, /nac/bpnotice
/nac/commondata/servertime, /nac/commondata/chartData/reportResultData/
/nac/applications/license/page    mode,query,pageurl -> pageLimitPerm + edition message
/logs, /reports
```

`permLevelMap` = `fullControl:20, addEdit:15, edit:10, readOnly:5, noPerm:0`.

## Captive portal (`<site>/cwp2/`)

```
/cwp2/                                  302 -> faces/common/design/standard/main.xhtml  (200)
main.xhtml      meta: CWP_NODEID, CWP_SMAC, CWP_SENSORNID, CWP_SRCIP, CWP_ROLEID,
                      CWP_ENABLEAUTH, CWP_ISUSERAUTHED, CWP_AUTHUSERID, CWP_EVERYTHINGOK
notice.xhtml / download.xhtml           200
user.xhtml                              200 -> "Invalid User Account () account information does not exist."
saml2/saml2Logout.xhtml
```

Identity comes from the **network** (server-observed IP/MAC), not from the client. Behind the demo
CDN proxy `CWP_SRCIP` is the CDN address, so a client can never present itself as a registered node —
that, not "needs a sensor session", is the real blocker.
