---
name: yarbo-audit
description: Yarbo (yarbo.com) bug-bounty engagement — cloud API map, RSA password scheme, registration flaw, endpoint authz matrix, next leads.
metadata:
  hermes:
    tags: [bug-bounty, yarbo, iot, api-gateway, auth0]
---

# Yarbo engagement (yarbo.com) — state of knowledge

Self-hosted BBP: policy at /pages/vulnerability-disclosure-policy, terms at
/pages/bug-submission-process. Payout table v1.0 (07/24/2026): Critical $11k-15k web,
High $3.5k-4k, Medium $200-800, Low $100. Bounty bonus for chained exploits (+30-50%).
Intake: **security@yarbo.com** (no platform). NDA + W-8BEN before payout.

In scope: all *.yarbo.com, mobile apps (com.hanyang.yarbo), device firmware, cloud/IoT
backend APIs (includes the identity service). Out of scope: third-party hosted subdomains
(Shopify storefronts au/uk/de/fr/se/ca/eu/mx, Zoho support, Discourse forum, Auth0 platform
itself, Bitly, Klaviyo, CDN), dev/staging/test stages, DoS, social engineering, physical
disassembly, missing security headers, missing TLS pinning.

## Asset map (production, as of 2026-10)

| Host | What it is |
|---|---|
| 4zx17x5q7l.execute-api.us-east-1.amazonaws.com/Stage | **main app API** (robot-service, message-service, data-service, msg) |
| 26akbclmo9.../Stage | mqtt-migration service (unauth `?sn=` query, returns `migrated`) |
| 26akbclmo9.../test, /test/yarbo/sim-service/query | TEST stage — out of scope |
| gu7e5n9ef4.../Stage | other API, all paths 403 (unknown routes) |
| oczkojjxh5.../dev/iotL | DEV IoT API — out of scope |
| ms0frm2hkf.../dev/app | returns 502; app.yarbo.com CNAMEs here (TLS name mismatch, Host not accepted) |
| wiki.yarbo.com | Wiki.js 2.x on EC2 54.198.93.49 (GraphQL anon: pages.list only; users/system forbidden) |
| go.yarbo.com / launch.yarbo.com / dealer.yarbo.com | AWS 34.205.214.208, nginx+PHP. go = utm redirector; launch+dealer = 403 on every path (vhost exists, dealer not in public DNS) |
| robot.yarbo.com | Fly.io app, TLS handshake always EOF (no cert for SNI) |
| auth.yarbo.com → dev-6ubfuqym1d3m0mq1.us.auth0.com | Auth0 **dev** tenant in production; client_id SL1GSNy3VmCLTML01qPkwqjgY4xm66i0; all redirect_uri values rejected (custom scheme only) |
| MQTT | c4750009.ala.dedicated.aws.emqxcloud.com:8883 (CONNACK 5 for every credential guess, incl. token-as-password); Tencent TDMQ host is dead |

S3: yarbo-commonuser (maps, private), yarbo-common-file (public firmware), dc-ota-version
(private; unauth getDcVersion mints presigned URL — currently points at
`research-owned-security-marker-20260808.txt`, a PRIOR researcher's marker → that OTA write
primitive is already known, do not re-report).

## Auth mechanics (needed for any authenticated test)

- Login: `POST /Stage/yarbo/robot-service/robot/commonUser/login`
  `{"username": email, "password": base64(RSA_PKCS1v15(password))}`.
  RSA key = `assets/flutter_assets/assets/rsa_key/rsa_public_key.pem` inside the XAPK
  (raw base64, wrap with PEM headers; 2048-bit). Response: accessToken (Auth0 RS256 JWT,
  30 days), refreshToken, userId, snList. Token claims carry `https://auth0.yarbo.com/roles`.
- Register: `POST .../robot/commonUser/register` `{"username": email, "password": enc}`
  → 00000 + accessToken, **no verification code, no captcha** (finding F1). Re-registering a
  known address → "This email is already registered." Register limiter → code 4290 after ~6.
- Wrong RSA key or plaintext password still "reaches" the service but every call fails with
  a generic "Incorrect password." / "An unexpected error occurred" — the *correct* key is what
  unlocks the JSON-schema error messages ("Payload validation error ... on property email"),
  which is the cheapest way to learn field names. Login itself always answers
  "Login failed, please check your account." so it is useless as an oracle.
- Param-name oracle: send `{}` and read the message ("sn cannot be empty",
  "coreSn is empty!", "SN is empty.", "Please set the nickname"). Examples found:
  - getWarrantyInfo → `sn`; findUserExist → **`username`** (GET); updateSnowbotName →
    `serialNum` + `snowbotName`; reportDcOta → `coreSn`.

## Endpoint authz matrix (tested with a real unverified account)

ENFORCED (A0230 without token / ownership checked): getUserRobotBindVos, getUesrInfo,
downloadUserAvatar, userWhiteList/*, rasterBackground/get|add|delete (denies other SNs),
getAgoraToken (denies other SNs), reportDcOta ("not authorized to manage this device"),
bindUserRobot (returns "invalid user!" for a synthetic SN), updateSnowbotName, notification/*,
msg/*.

**NOT ENFORCED (findings):**
- `POST getWarrantyInfo {"sn": "<any>"}` — no token at all; returns unit + sibling module
  serials, regist_ts, regied_ts, in_warranty. (F2)
- `GET findUserExist?username=<email>` — no token; `{"exist":0|1}`. (related observation)

By design / no impact: login, register, resetPw, getDcVersion (known), mqtt-migration/query,
questionnaire, getLatestPubVersion, getMapUploadSetting.

Dead ends already burned: SQLi/NoSQLi probes on sn + login, JWT alg=none/null tokens,
username change via updateUserInfo, presign path traversal, MQTT anon/weak creds, Auth0
redirect_uri, S3 bucket listing, vhost fuzz on 34.205.214.208 (only launch/dealer found),
mail captcha + checkCaptcha (every body → "unexpected error", flow appears dead/unused).

## Open leads

1. How the app obtains EMQX/TDMQ credentials — not in the APK strings, not our token, not
   the email. If they are derived per-device, the issuance call is the next target.
2. Agora App Certificate: APK contains 32-hex candidates (e87579c1…, d6031998…, affc62d6…,
   5eeefca3…) — App ID is public by design; a *certificate* in the binary would allow minting
   tokens for any channel (channel name is client-chosen in getAgoraToken). Verify before
   claiming; joining a real unit's stream is off-limits.
3. DC firmware bundled in the APK (v1.1.8/v1.1.11) + `/greengrass/v2` strings — local attack
   surface; the 2026-05 Makris disclosure covers remote diagnostics/creds, so treat as known.

## Open leads / deep-dive status (2026-10-27, 2nd pass)

1. **MQTT credentials: CLOSED as a remote lead.** The full route list was extracted from the
   AOT snapshot (grep `/yarbo/`, `robot-service`, `message-service`, `data-service`, `sim-service`
   in `libapp.so`) — there are exactly 44 routes and *none* issues broker credentials. Two
   fuzz sweeps (716 + 1185 probes over APK-derived camelCase ops × `/yarbo/robot/`,
   `/yarbo/msg/`, `/yarbo/commonUser/`, `/yarbo/robot-service/robot/commonUser/`) found no
   hidden route beyond the known three. Broker CONNACK is 5 for every pair tried (email+token,
   token+token, `hytech`+token, anon). Provisioning therefore happens device-side, not via API.
2. **Agora: App ID identified, certificate NOT shipped.** Only ONE of the four 32-hex
   candidates is a real App ID: `affc62d646c840ceba4d374500fc7f92` (Web SDK answers
   `dynamic use static key` instead of `invalid vendor key, can not find appid`). The project is
   in certificate mode. Tokens minted with the official AccessToken2 builder over the other
   three candidates fail with `invalid token, authorized failed` → none is the certificate.
   So no token minting. Method (reusable): build token with AgoraIO/Tools
   `AccessToken2.py` + `RtcTokenBuilder2.py` (2-step HMAC: HMAC(issueTs, cert) then
   HMAC(salt, ·), and `'007' + b64(zlib.compress(pack_string(sig)+signing_info))` — a
   naive single-HMAC implementation parses as `invalid vendor key`, which is easy to mistake
   for a bad App ID), then join a self-chosen channel from headless Chrome with
   `AgoraRTC_N-4.20.0.js`. `channel_name` is client-supplied in `getAgoraToken`, so a leaked
   certificate would mean tokens for any channel; ownership check on `sn` blocks the shortcut.
3. **Device binding is properly gated.** `bindUserRobot` answers `"invalid user!"` for *every*
   body shape (empty, sn, sn+code, sn+pairCode, snList, sn+userId/userName/masterUsername/email/
   account/targetUser/bindUser/owner) with a valid token from an unverified account — a
   caller-side pre-check, not a body-shape problem. The APK `bindUserRobotb` string is an AOT
   artifact suffix, not a different route. Real binding goes through the DC QR flow.
4. **Accounts created by the unverified `/register` ARE real backend users**: `updateUserInfo`
   fields (nickName, firstName, lastName, region, sex) persist and read back through
   `getUesrInfo`, and the account keeps logging in. Mass-assignment on
   `permissionGroup`/`roles`/`status`/`isAdmin` is filtered (B0001) and the JWT claims never
   change, so no vertical escalation from there.
5. DC firmware v1.1.11 (769 KB, from the unauth `getDcVersion` presigned URL) has no plaintext
   MQTT/broker credentials — only ESP-IDF wifi/`halow_ssid` plumbing. The
   `research-owned-security-marker-20260808.txt` object at the OTA path is a real firmware
   blob, i.e. the earlier researcher's write primitive — treat OTA tampering as KNOWN.

### Negative matrix (all executed, not assumed)

SQLi (time-based `SLEEP(3)`, `||`, `WAITFOR`) on `getWarrantyInfo.sn`, `login`, and
`go.yarbo.com/<code>` path → no delay, no error delta. NoSQL operator injection on login →
same "Login failed". JWT: `alg:none`, empty sig, HS256 signed with the JWKS public key (PEM and
raw DER) → A00023. Auth0: `redirect_uri` rejected for 6 values incl. suffix trick;
`dbconnections/signup` → `public signup is disabled`; email format strictly validated so no
case/space/NBSP/NUL normalization gap. Account enumeration via case-flip → blocked
("This email is already registered" for `BIND-TEST-1@EXAMPLE.COM`). Cross-account
`commonUserDeregister` with `username=<other>` → refused, target still logs in.
`getUserRobotBindVos` / `getUserWhiteList` ignore `?userId=` / `?sn=` (identical body AND
identical `sign` ⇒ same self-scoped response). Map endpoints (`rasterBackground/get|delete`)
deny unbound serials. Anonymous `PUT` to `dc-ota-version` and `yarbo-common-file` → 403.
`go.yarbo.com` vhost fuzz + `launch`/`dealer` (.env, .git, admin, phpinfo…) → all 403/404.
Serial numbers are NOT sequential (`…HO5226/5228/5230/6000` all "Record not found"), so
the unauth warranty endpoint cannot be turned into bulk enumeration.

**Conclusion of the 2nd pass:** the device plane (bind, maps, OTA report, Agora token,
whitelist) enforces serial ownership correctly; the account plane has the three real gaps
(F1 register-without-verification, F2 unauth warranty, F3 unauth `findUserExist`). Reaching
Critical needs either a vendor-designated demo serial/device, or firmware deep-dive on the
rover (not the DC) — both require something we do not have remotely.

## Submission compliance (verified 2026-10-27)

**There is a mandatory FORM, not just an e-mail.** VDP §5 says "Complete the Vulnerability Disclosure
Request and send it to security@yarbo.com" — that is a ~30-field `.docx` linked from the policy:

```
https://www.yarbo.com/cdn/shop/files/Vulnerability_Disclosure_Request.docx      <- works
https://www.yarbo.com/cdn/shop/files/1/0604/5394/5441/files/...docx?v=...      <- 404s
```
Sections: 1 Report Information · 2 Disclosure Content · 3 Disclosure Timing · 4 Disclosure Channels ·
5 Coordinator Information (incl. govt ID type) · 6 Other Notes · Technical Reproduction A-D
(Required) · 8-checkbox Agreement. Submit to `security@yarbo.com`. Fill and attach it — e-mail + PDF
alone is an incomplete submission.

Terms §1.4 also mandates eight report elements, three of which the form only partly covers and which
were missing from the PDF until asserted: **testing environment configuration**, **PoC artefact**,
**exact hardware model + firmware version** (answer "not applicable, no device involved").

Impact needs a real user count. Google Play for `com.hanyang.yarbo` shows **10,000+ installs** (read
from the listing HTML as `info 10K+ Downloads`).

### Two scope risks that must be argued in the report, not assumed

1. **Host is not `*.yarbo.com`.** `4zx17x5q7l.execute-api.us-east-1.amazonaws.com` — policy §1.2 says
   "under the yarbo.com root domain". Defence: Terms list "Cloud & IoT Backend APIs ... end-user
   identity authentication and authorization services" as in scope, the published app calls this host,
   and AWS is hosting not ownership. Offer to re-run through a `yarbo.com` front door if one is named.
2. **`/Stage` reads as staging.** §1.2 excludes dev/staging/test/UAT. Proofs that it is production:
   the store build calls this exact host **and** stage; it holds real units/warranty records; the real
   non-prod stages are `/test` on gateway `26akbclmo9` and `/dev` on `oczkojjxh5` (left untouched).
3. Proactively explain `dev-6ubfuqym1d3m0mq1`: Auth0 tenant IDs are immutable at creation and this is the
   tenant the published app authenticates against and that issues real customer tokens.

Residual risk to expect on triage: F2 can be argued down to **Low** under their row "Read-Only
Unauthorized API Endpoint — exposes only publicly available or negligible-sensitivity data", because the
example serial is public. The counter is that the two unpublished module serials plus the warranty dates
are not public. F1 can be argued up to **High I** if the address alone is accepted for a support or
warranty action.

## Report artefacts (this engagement)

**SUBMITTED 2026-10-27** to security@yarbo.com, two separate threads:
- F1 `1a17ecd8de0990f9` / thread `1a17eb1396263488` — "[Security] Yarbo cloud API - account created without e-mail verification"
- F2 `1a17ecd98cd766f0` / thread `1a17eb140193e63d` — "[Security] Yarbo cloud API - warranty and serial data readable without authentication"

Receipts in `D:/yarbo/evidence/sent_receipts.json`. Each mail carried 4 attachments (report PDF, completed
Vulnerability Disclosure Request .docx, PoC script, raw JSON capture), all sha256-verified against local copies.

### Submission mechanics that are MANDATORY here (learned the hard way)
The VDP §5 sentence "Complete the Vulnerability Disclosure Request and send it to security@yarbo.com" points at a
**separate .docx form**, not just an e-mail. Live URL (the one embedded in the policy page 404s):
`https://www.yarbo.com/cdn/shop/files/Vulnerability_Disclosure_Request.docx` (17,551 B, python-docx readable).
It demands: Report Information / Disclosure Content / Timing / Channels / Coordinator Info, then Technical
Reproduction A–D (Product+version, Steps+reproducibility+expected-vs-actual, Evidence attachments, Impact+remote
Y/N), then Supplementary (CWE, CVSS, prereqs, environment, tools, fix, availability), then 8 agreement checkboxes.
Fill it even when you request NO public disclosure — state that explicitly in §2/§3/§4.

### Scope pitfalls specific to this target (pre-empt both in every report)
1. **Host is not `*.yarbo.com`.** Endpoints live on `4zx17x5q7l.execute-api...amazonaws.com`, but §1.2 excludes
   "third-party hosted subdomains". Answer: it is Yarbo's own deployment for its published app; §1.2 also lists
   "Cloud & IoT Backend APIs ... end-user identity services" as in scope; AWS is the hoster, not the owner.
2. **Path segment `/Stage` looks like staging**, and §1.2 excludes "development, staging, test, UAT". Answer with
   evidence: the Play-Store build calls that exact host+stage; the estate holds real units/warranty rows; the actual
   non-prod stages are named differently on different gateway IDs (`/test` on 26akbclmo9, `/dev` on oczkojjxh5).
3. Bonus: Auth0 tenant is `dev-6ubfuqym1d3m0mq1`. Tenant IDs are immutable and it is what the released app uses —
   state this before a triager reads "dev-" as a tell.

Impact number for §1.4 ("number of potentially affected end users"): Google Play lists com.hanyang.yarbo at
**10,000+ installs**.


`D:/yarbo/poc/` — per finding: `gen_f<n>.py` (generator), `body_F<n>.txt` (e-mail body),
`blocks_F<n>.json` (typed blocks for the renderer), `VDR_F<n>_*.docx` (completed form),
`yarbo_poc_F<n>_*.py` (PoC, read-only except the one route), plus `yarbo_style.py`, `vdr_builder.py`,
`mkfig.py`, `rsa_public_key.pem` (extracted from the APK, needed by the PoC).
PDFs: `F1_registration_without_email_verification.pdf` (7 pp), `F2_warranty_data_without_auth.pdf` (6 pp).
Evidence + `poc_capture_F<n>.json` in `D:/yarbo/evidence/`. Both PDFs pass
`qa_pdf_layout.py --margin-mm 19.05` (layout: clean).
Drafts staged to security@yarbo.com with 4 attachments each, sha256 verified — **draft only, operator
sends**. Rebuild invalidates the staged PDF: delete the superseded draft, then append.
