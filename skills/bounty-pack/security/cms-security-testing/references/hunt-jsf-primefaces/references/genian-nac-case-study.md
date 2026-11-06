# Case study: Genian NAC 5.0 Cloud console (2026-10)

Concrete measurements from a real JSF/PrimeFaces appliance engagement, kept because the
*numbers* are what make the generalisations in SKILL.md checkable.

## Build under test

```
GET /mc2/rest/information/version/nac
-> {"value":"NAC-CLOUD-R-154085-5.0.92.1022"}
```

Fix revisions published by the vendor: 148665 / 148817 / 150340. Build 154085 is above all
three, so the entire published CVE set (unauth IPC, ZIP-slip RCE, CWP user search) was
**duplicate by construction**. Establish this before hunting — on this engagement it retired
three high-value targets in the first minute.

Stack: JSF + PrimeFaces 8.0, Tomcat, Apache Catalina CSRF filter
(`?org.apache.catalina.filters.CSRF_NONCE=` appears on redirects).
Sibling portals on the same host: `/mc2/` (admin console) and `/cwp2/` (captive web portal).

## Error-page markers observed

| Size | Source |
|---|---|
| 1109 | primefaces error page for `/mc2/faces/*` and `/mc2/rest/*` |
| 1056 | same error page without the PF theme block |
| 2655 | static "Not Found \| Genians" branded 404 |
| 3002 | `/cwp2/faces/sessExpired.xhtml` ("CWP Session Expired") |

Every one of these is served with **HTTP 200**. A path sweep of 25 guessed `.xhtml` names
returned 25 × `200|1109` — i.e. all absent.

## Endpoint map obtained by recording traffic (not guessing)

```
faces/management/  genianDevMgmt, port, softwareUpgrade, tree, frame
faces/monitor/     nodeMgmt, ipMgmtFrame, ipMgmtTree, tree, frame
faces/network/     swIfMgmt, tree, frame
faces/policy/      permMgmt, subjMgmt, systemMgmt, tree, frame
faces/report/      reportResult, tree, frame
faces/setup/       configMgmt, cwpDesignMgmt, genidevMgmt, tree, frame
faces/user/        userMgmt, userAppMgmt, userWizard, tree, frame
faces/ipmgmt/      tree, frame
faces/stat/        nodeSensorStat
faces/dashboard/   widgetContainer, wg*.xhtml

REST: sessions/current · information/version/nac · nac/nodes · nac/genidevices ·
      nac/menutree · nac/bpnotice · nac/commondata/servertime ·
      nac/commondata/chartData/reportResultData · nac/applications/license/page ·
      logs · reports
```

## `?ln=` traversal result

```
baseline  /javax.faces.resource/pages/adminlogin.css?ln=css  -> 200, 4541 B, text/css  (works)
?ln=../../WEB-INF                                             -> 1109 (error page)
?ln=..%2f..%2fWEB-INF                                         -> 1109
..%2F..%2FWEB-INF%2Fweb.xml                                   -> 400
%2Fetc%2Fpasswd?ln=css                                        -> 400
```

Blocked. Note the baseline was checked first — without it the 1109s are uninterpretable.

## Login flow (five gates, three by passable default)

1. `adminlogin.xhtml` — `form1:userId` / `form1:passwd` / `form1:dologin`
2. *"An account is already in use by the device with IP …"* → tick hidden
   `form1:forceLogin` ("Disconnect all previous connections")
3. iframe `allowIpDlg.xhtml` — *"Enter an IP address for the first time access. Web Console IP1/IP2"*
   → submit **empty** and continue. Not a bypass: `Number of Auth IPs/MACs/Devices = 0`, so no
   allowlist existed.
4. `signin/mfa.html` for a *newly created* account — offers
   *"Enable two-step verification"* **and** *"Continue without two-step verification"*.
   The primary admin account instead got a mandatory iframe `otpAuthDlg.xhtml`
   (`form1:fldCheckAuthNumber`, OK / Cancel, **no skip**).
   Asymmetry noted, but no instance-level "require MFA" policy page was found → treated as
   per-user opt-in, therefore not reported.
5. `mainFrame.xhtml` — shell with `mainIframe` → `dashboard/frame.xhtml`.

## RBAC differential (perm levels: 20 fullControl, 15 addEdit, 10 edit, 5 readOnly, 0 noPerm)

`GET /mc2/rest/sessions/current` for both roles; admin had 30 keys at 20, the `auditor` role
had 5 everywhere except `setup_config=0`, `genian_mgmt=0`, `mgmt_ipmapp=0`.

| Page | Admin | auditor |
|---|---|---|
| `management/genianDevMgmt.xhtml` (genian_mgmt=0) | 200 / 61 052 | **302 → error.xhtml** |
| `setup/configMgmt.xhtml` (setup_config=0) | 200 / 71 773 | **302 → error.xhtml** |
| `management/softwareUpgrade.xhtml` | 200 / 26 746 | **302 → error.xhtml** |
| `policy/permMgmt.xhtml` (5) | 200 / 28 316 | 200 / 28 083 |
| `policy/systemMgmt.xhtml` (5) | 200 / 31 748 | 200 / 31 001 |
| `monitor/nodeMgmt.xhtml` (5) | 200 / 142 783 | 200 / 142 785 |
| `user/userMgmt.xhtml` (5) | 200 / 61 262 | 200 / 60 859 |
| `report/reportResult.xhtml` | 200 / 119 119 | 200 / 25 828 (truncated) |

Enforcement is real: perm-0 pages 302 to the error page for the low-priv role.

## Write attempts as readOnly (all refused)

- `userWizard.xhtml?cmd=create&selectedTab=userSelectTab` **opens** for the auditor, but
  `form1:btnNext` is `disabled="disabled"`; force-enabling it and JS-clicking did **not** advance
  the tab server-side. Tab panels `tabLevel1` / `tabLevel2` stay disabled until step 0 validates.
- `policy/permMgmt` Tasks menu renders "Create" and "Delete", but every row checkbox is
  `disabled=True` and Create opens nothing.
- REST `POST/PUT/DELETE` on `/nac/nodes`, `/nac/bpnotice`, `/sessions/current` returned the
  1109 error page for **admin and auditor alike** — those paths take no write method at all, so
  there is no permission differential to observe. Correct method-shape matters before you
  compare roles.

## Session-cookie confusion

`JSESSIONID` + `adminLocale` + `mc.sessionId` (64-char). Cross-paired on `genianDevMgmt`:

| JSESSIONID | mc.sessionId | Result |
|---|---|---|
| admin | admin | 200 |
| auditor | auditor | 302 denied |
| **auditor** | **admin** | **302 denied** |
| admin | auditor | 200 (still admin's own) |
| auditor | *(absent)* | 302 denied |

Authoritative identity is `JSESSIONID`; `mc.sessionId` is not. No confusion.

## Edition gate — render ≠ write

License: Professional. `GET /mc2/rest/nac/applications/license/page?mode=page&query=&pageurl=/mc2/faces/setup/configMgmt.xhtml`
→ `{"pageLimitPerm":200,"licenseDetailMsgList":["This feature requires Enterprise edition or later."]}`

Yet `configMgmt.xhtml` rendered fully: 71 773 B, 77 `form1:*` inputs, **17 disabled**.
Live values: `NCTIME_IPCHANGE=3`, `WAKEONLANPORT=9`, `HTTPCWPPORTS=80,8080`,
`HTTPSCWPPORTS=443`, `SENSORLOGONTOKENIP=***`.

Write test, 3 attempts:
1. `fill()` → refused, element disabled
2. JS force-enable + real click → click intercepted by overlay
3. JS force-enable + JS `.click()` on `form1:actionBtn` → submit ran

Reload → still `3`, not `5`. **Server refused. Gate correctly enforced. Not a bug.**
This is the single most likely false positive on this stack; the reload step is what kills it.

## Trial provisioning (getting the instance)

WordPress `admin-ajax.php`, action `gn_cloud_start_subscribe`, multipart. CSRF from
`action=gn_async_create_csrf_token`, **single-use** (reuse → generic denied).

Contract learned from the page JS — `product` takes the short code (`nac`, `nac6`), while the
numeric id (`5`, `11`) is only for the separate `gn_get_plans` lookup. Sending `product=5` to
the subscribe action yields a blanket `{"result":false,"message":"invalid access"}` that reads
like a security block but is a malformed request.

Working call: `product=nac, edition=pro, nodes=10, region=ap-northeast-2` → `{"result":true,"message":"success"}`.

Differential on the client-controlled fields:

| Sent | Provisioned |
|---|---|
| `nodes=10` | 300 (plan default) |
| `validityperiod=3650` | 30 days (plan default) |
| 2nd trial, `nodes=99999` | `maximum number of trial versions exceeded (1)` |
| ZTNA trial (`product=nac6`, `nodes=99999`) | same quota message |

So: client quota fields ignored; quota is 1 per account, global across products.

## Ownership checks that held

- `/order-detail-gsp/?order={1,2,3,10,100,1000,4101,4102,4103}` → *"invalid access"* for all
- `/getlicense/?subscription_id=<mine>` renders; `<foreign>` returns empty
- `/authority_modify?subscription_id=<mine>` renders the delegation form;
  `<foreign>` empty; unauthenticated empty

**Deliberate stop:** proving IDOR here required a subscription id that genuinely belongs to
another demo customer. That was not done — it touches third-party data. The correct blocker to
raise is "needs a second account of my own", not "could not test".

## CWP pre-auth — unreachable without a sensor

```
/cwp/  -> 302 /cwp2/
/cwp2/ -> 302 /cwp2/faces/common/main.xhtml
/cwp2/faces/common/main.xhtml -> 302 /cwp2/faces/sessExpired.xhtml
all /cwp2/faces/* -> 302 sessExpired
```

The captive portal requires a session token minted when a real device is redirected by the
network sensor. Not a negative — an unreachable surface without a sensor lab. Worth flagging
because the vendor's most recent unauth CVE lived in exactly this component (CWP user search).

## What this case study is for

If a future engagement shows `/faces/*.xhtml` + `javax.faces.ViewState` + `form1:` ids, reuse this
checklist verbatim: measure the error-page size, harvest from traffic, baseline the resource
handler, build the two-role matrix, force-enable-then-reload on every gate, and cross-pair the
session cookies. Those five steps produced twelve defensible negatives and zero false reports.
