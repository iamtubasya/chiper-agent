---
name: scribblemaps-audit
description: >-
  Scribble Maps (scribblemaps.com) bug-bounty engagement — scope, program rules,
  API route inventory, the three validated findings, test assets, and the
  submission state. Read before any re-hunt of this target.
metadata:
  hermes:
    tags: [security, bug-bounty, target, scribblemaps, saas, gis]
---

# Scribble Maps — engagement notes

**Program (policy live, updated 2026-10-04):** https://help.scribblemaps.com/help/a/vulnerabilities-and-bounties
Bounty $25–$2,000. Submit: `https://api.scribblemaps.com/vulnerabilities` (**login wajib**).
Payment via Wise/PayPal only.

**In-scope hosts (named by the program):** `www` · `team` · `manage` · `widgets` · `api` · `data`
`.scribblemaps.com`. Pool entry also lists `*.scribblemaps.com` / `*.help.scribblemaps.com`.

**Program asks:** do NOT scan `/maps/` (scanner rabbit hole); prefers no heavy automated scanning.
→ gentle automation only (`-rl` low, `-c` 1–2), and treat `/maps/` as excluded.

**Explicitly OUT of scope:** anonymous community maps · unlisted (URL-as-credential) maps without
LockView · third-party stacks (GeoServer/Tomcat) · missing security headers without an exploit ·
rate limiting in isolation.

---

## Money model (where the bugs are)

Free / Pro / Pro Business plans · API keys · team seats · **Sell Access (paid maps)** ·
**Secure map (view password)** · Encrypted map (client-side AES-256 + PBKDF2, Pro-only).
Selling maps is the revenue path; Secure/paid map access control is the security boundary.

## API route inventory (extracted from JS, not guessed)

| surface | where | notes |
|---|---|---|
| map data | `www/api/maps/{code}/raw` · `/smjson` · `/smjsonbase64` · `/lzsbase64` · `/kml` · `/geojson` · `/format` · `/history` · `/isPro` · `/lastModified` · `/users` · `/users/authority` · `/settings` · `/listing` · `/tags` · `/stream/new` · `/stream/` | unlock via `?password=<urlencoded>` |
| image render | `www/api/maps/images/{w}/{h}/{code}.png[/metadata]` | **enforces authz** (401) |
| map meta | `www/api/maps/{code}` → `inUse, format, isPaid, isPaidFree, hasPassword, isEditor, agentMode, teamCode` | public oracle |
| market | `api/api/market/defaultPlans/{code}` · `/is-seller` · `/add-paid-map` · `/create-account` · `/create-link` · `/contact-support` | lives on **api** host, not www |
| subscription | `api/api/subscribe/plan-status?type=` · `/checkout?type=` · `/validateSession?sessionId=` · `/paypal/status` | planKeys: monthly, yearly, proBusinessMonthly/Yearly, monthlyTrial, yearlyTrial, proBusinessMonthlyTrial, proBusinessYearlyTrial, weekPass, proBusinessPass |
| account | `www/api/account` · `/email` · `/password` · `/passwordReset` · `/settings` · `/card` · `/maps` · `/recentMaps` · `/toggleSubscribe` · `/connectors` · `/overlays` · `/getGoogleToken` | |
| vuln portal | `api/api/vulnerability/submit` · `/list` · `/{id}` · `/{id}/notes` · `/aisubmit?userId=` · `api/api/admin/vulnerabilities` | admin = 403 for normal user |
| team app | SPA hash-routes: `#/users #/maps #/mapLabels #/mapSecurity #/teamMarkers #/migrateMaps #/slack #/s3 #/dataConnections #/googleAddon #/sso #/scim #/audit-log #/welcomePage #/billing #/teamSettings`. **SSO/SCIM/S3/Slack live on the `api` host, not `team`** — direct probes to `team/api/saml` etc. 404: `api/api/saml/settings` · `/saml/domains` · `/saml/import-metadata` · `/saml/toggle` · `api/api/oidc/settings` · `/oidc/import-metadata` · `/oidc/toggle` · `/oidc/providers` · `/saml/providers` · `api/api/scim/settings` · `/scim/token` · `/scim/default-product` · `api/api/s3/settings|toggle|test` · `api/api/slack/*` · `api/api/security/*`. Team host keeps `team/api/users?teamCode=` · `/user` (POST = edit user) · `/users/bulk` · `/maps` (→ 402 on free team) | discover routes by driving the SPA, not by guessing paths |
| MCP | real endpoint `api.scribblemaps.com/mcp` → 401 (auth required). `www|api/api/maps/mcp` is **not** MCP — it is the map-data route matching map code `mcp` (a real map) | don't chase it as an AI surface |
| SDK | `cdn.scribblemaps.com/api/js/1.613/scripts/main.js` (6.4 MB) | best route source; editor at `www/create/` |

Turnstile sitekeys: register `0x4AAAAAADCl3kOJjZHJ_uoz` · portal form `0x4AAAAAACwfY3Um6fHIjKSd`
(they differ — read from HTML, never hardcode).
**Turnstile behaviour on this target:** the widget renders with a normal bounding box but
`document.querySelectorAll('iframe')` returns `[]` (iframe is inside the widget div) and
`window.turnstile.getResponse()` stays `null` until the checkbox is **clicked** at
`rect.x+32..36, rect.y+height/2` — token then appears in ~4 s. It is flaky: it worked once in a
diagnostic run and then failed three consecutive times. Headed real Chrome only.

---

## Findings (validated 3×, reported)

1. **HIGH 7.5 — paid-map content disclosed unauthenticated.**
   `paidsample` is `listType:"paid"`, `free:false`, plans $199 / $19.99mo / $99.99yr, `allowCopy:false`,
   yet `/raw` `/smjson` `/smjsonbase64` `/lzsbase64` `/kml` `/geojson` on **www** return the full map
   (16,908 B, sha256 `REDACTED_********`) to anonymous
   clients. Four control signals prove intent: same path on **api** host → 401; image API → 401;
   password-protected Secure map → 401 on all six; SDK stores paid maps as `secure=true`
   (`"paid"==d&&(a.listed=!1,a.secure=!0)`). Root cause: data endpoints check only `hasPassword`,
   never `isPaid`.
2. **MEDIUM 5.4 — `POST /api/vulnerability/aisubmit?userId=` accepts a foreign userId.**
   Existence is checked, ownership is not. Full submission under another account's id returned
   `success:true`, ref `6F50F5`, and the approval e-mail went to the **victim's** address.
   Impact: report impersonation + burning the victim's 1-report/day quota.

PoC PDFs + evidence live in `/home/agentuser/bounty/scribblemaps\` (`COVERAGE.md`, `evidence/`).

3. **LOW-MEDIUM — SSRF via SSO metadata import** (found 2026-10-31, round 6).
   `POST api/api/saml/import-metadata` and `POST api/api/oidc/import-metadata` take
   `{teamCode, metadataUrl}` and the **server fetches the URL**. Confirmed out-of-band 3×
   (DNS from `20.42.77.69`, HTTP from `13.72.78.248` — Azure, one interaction per run).
   Oracle: `"Failed to parse metadata XML"` = fetched 200 vs `"Could not fetch the metadata"` =
   failed/401. Controls verified in place and stated in the PoC so it is not overclaimed:
   HTTPS-only; private/loopback/link-local/zero blocked **after DNS resolution** (15 variants
   tested incl. `[::1]`, `[::ffff:127.0.0.1]`, `2130706433`, `0x7f000001`, `017700000001`,
   `127.1`, `0.0.0.0`, `localtest.me`, `*.nip.io`); no redirects; 5 s / 512 KB caps; and the
   fetch carries **no cookies** (auth-required scribblemaps.com endpoints return 401 to it).
   ⇒ public-only SSRF, rated Low-Medium. Impact argument that lifts it: the fetched document
   becomes the team's trusted IdP. PoC:
   `ScribbleMaps_PoC_SSRF_SAML_Metadata_Import.pdf`, payload `submit/finding3_payload.json`.
   Method + reusable checklist: `hunt-ssrf` § Trigger surfaces S-C.

## Negatives already proven (do not redo)

Secure-map gate: 16 path/method/param/header bypass variants all 401; correct password → 200,
wrong/empty → 401. BOLA on `/api/maps/{code}/users` (non-owner) → 401. Team cross-tenant
`/users?teamCode=` and `POST /api/user` → HTML guard, record unchanged (owner control returns JSON).
Subscription `validateSession` on unpaid Stripe session → no entitlement. Account email change and
`/account/settings` mass-assignment → no effect. oembed SSRF (interactsh + internal IPs) → no fetch.
Stored XSS in map title → escaped. Widget rendering of Secure/Paid maps → placeholder only.
IIS tilde → 302. nuclei (105 templates × 6 hosts, completed) → 1 info-only match (aspnet-version).
ffuf 90 words → only known paths. sqlmap (after WAF retry) → not injectable.

**Round-6 additions (all with a working owner control, so not false negatives):**
- **Team SSO/SCIM/S3 cross-tenant WRITE → 403 on every one**: `saml/settings`, `saml/toggle`,
  `saml/domains`, `oidc/settings`, `oidc/toggle`, `scim/toggle`, `scim/token`,
  `security/block-personal-saving`, `s3/settings` with a foreign `teamCode`. Reads of foreign
  `saml/oidc/scim/settings` → 403 too. Owner calls on the own team return 200 JSON.
- SAML/OIDC/SCIM protocol surface: `POST /saml/acs` with garbage → 401 generic;
  `GET /oidc/callback?code&state` → 401 `Invalid or expired state`; `/scim/v2/Users` → 401;
  `/scim/v2/ServiceProviderConfig` → 200 (normal SCIM discovery). No signature/state bypass at
  this depth. **Round 7 closed this thread: it is BLOCKED, not open** — see round-7 additions below.
- `encrypted:true` on `stream/new` is **accepted by a FREE account** (200), but behaviour is
  identical to a Secure map (`/raw` 401, `/raw?password=` 200 plaintext) — no demonstrated bypass
  of the encryption control, so recorded as an entitlement question, not a finding.
- SSRF private-range filter: see finding 3 — every encoding variant blocked.

**Round-7 additions (2026-10-31, SSO deepdive — the "still open" thread is now CLOSED as blocked):**
- SAML was configured on the reporter's own team (`POST /api/saml/settings` with entityId, ssoUrl,
  self-signed cert, SHA256 → `200 {"success":true}`, `configured:true`), but **enabling requires a
  verified e-mail domain**: `POST /api/saml/toggle` and `/api/oidc/toggle` both →
  `400 "At least one verified email domain is required before enabling SAML/OIDC"`.
- Domain verification is properly built: only methods `dns` and `file` are accepted
  (`html`/`email`/`meta` → `400 Invalid verification method`); `domainId` is scoped to the caller's
  team (foreign ids → 404); the code is random and must be published as a DNS TXT record or served
  at `https://<domain>/.well-known/scribblemaps-verify.txt`. Without control of a domain's DNS or
  web root the flow cannot be completed ⇒ **SAML/OIDC cannot be enabled, so signature-wrapping /
  unsigned-assertion / replay testing on `/saml/acs` is UNREACHABLE** — state it as blocked, never
  as a negative.
- `POST /saml/acs` with a **correctly signed** assertion (signxml, enveloped RSA-SHA256, own key,
  matching Issuer/Audience/Recipient/NameID) → `401 "SAML configuration not found for this
  Identity Provider."` The ACS resolves the IdP from the assertion Issuer and only honours
  **enabled** configurations — that is why the signed assertion was rejected.
- INPUT-VALIDATION INCONSISTENCY (recorded, not a finding): `POST /api/saml/domains` accepts **raw
  IP addresses** as "domains" — `127.0.0.1`, `169.254.169.254`, `10.0.0.1`, `192.168.1.1`,
  `0.0.0.0`, `240.0.0.1` all stored (only `localhost`, decimal and `[::1]` rejected by the format
  check). The verification fetch then rejects IP literals with `"The domain is not a valid host
  name"`, so no internal request is made.
- Hostnames that resolve to private addresses (`localtest.me`, `127.0.0.1.nip.io`,
  `10.0.0.1.nip.io`, `192.168.0.1.nip.io`) are accepted and return the **same**
  `"Could not fetch verification file"` message as a non-resolving domain ⇒ internal reachability
  through this path is **UNPROVEN**. Timing (0.30–0.53 s) does not separate blocked from
  connection-refused. Do not claim it either way.
- Cleanup performed after testing: `/api/saml/toggle` and `/api/oidc/toggle` → `false`; all 13 test
  domains deleted via `DELETE /api/saml/domains/{id}` (returns `200 {"success":true}`); verified
  the domains list is empty and both SSO features are disabled.
- Draft for finding #3 created: `r518573298858966182` (SSRF PoC attached, 6,829 B).

## Coverage gaps (state as gaps, never as negatives)

Encrypted maps (Pro-only, cannot create on free) · paid team surfaces (S3 presign/list, Data
Connections, SSO OIDC/SAML, SCIM, Audit Log, billing → 402) · file upload (paid-gated) ·
blanket CVE sweep (deliberately bounded; program asks not to hammer).

## Test assets (operator-owned)

Accounts: `RESEARCHER_USERNAME+sm1@gmail.com` (userId XSyji7Gk2z), `RESEARCHER_USERNAME+sm2@gmail.com` (NoYTCa83iV),
`RESEARCHER_EMAIL` (**main**, userId dbVZ4Wz9LP, password held by operator — registered through
the vendor's own signup flow; the login page then shows a "logged in elsewhere" dialog when an older
browser session is still alive, click YES to force it).
Teams: `T2EJGi91j7` (PENTEST-TEAM-PROBE), `QHI3RR1tnc` (PENTEST-TEAM-B),
`DeklfcweMl` (PENTEST-TEAM-MAIN, owned by the **main** account — the one used for the SSO/SSRF
work; use this one, the other two belong to the +sm1/+sm2 aliases).
Maps: `N83YhqimzG` (Secure, password held by operator), `cs0F5As9vD` (saved with
`encrypted:true` on a free account), `IOcW4UQM0a`, `5wcX13Ojb5`, `hNEJ3M1c6j`
(XSS canary), `PmZmbNzHxw`. Browser profiles: `chrome-profile`, `chrome-profile2`,
`chrome-profile-main`.
OOB domain used for the SSRF proof (round 6): `dbisssq75lihdt7p8lo0cm93f35fxppcd.oast.site`
(log `oob2.txt`, interactions from `13.72.78.248`).

## Side effect to disclose

Probing `POST /api/market/create-account` created a real Stripe Connect Express account
(`acct_1UWMdARqX1zwTzSp`) for `RESEARCHER_USERNAME+sm1@gmail.com` — unverified, not activated, no balance.
Onboarding/KYC was NOT completed. Mention this when submitting.

## Submission state

- **Finding #1 SUBMITTED via the portal — referenceId `FF3179`** (2026-10-31), status
  `pendingConfirmation`: an approval link was e-mailed to `fz*******@gmail.com`
  (= `RESEARCHER_EMAIL`) and **expires in 48 h**; the report is not in review until it is
  clicked. `GET /api/vulnerability/list` still returns `[]` while pending.
  **OPEN ITEM:** the approval e-mail had not arrived in the mailbox ~12 min after submission
  (Gmail API checked with `in:anywhere`, `from:scribblemaps`, `FF3179`, `"approve this
  submission"` and a raw last-3-hours sweep — no match). Operator must click the link once it
  lands, or check spam. Saved response: `submit/submission_result.json`.
- **How it was sent:** the human form (`POST /api/vulnerability/submit`) was unusable — Cloudflare
  Turnstile stopped issuing tokens (widget rendered, `getResponse()` stayed `null` after 90 s and
  after 3 widget clicks). The portal page itself documents a captcha-free path,
  `POST /api/vulnerability/aisubmit?userId=<own userId>`, which was used with the session's own
  userId (`dbVZ4Wz9LP`, verified against `GET /api/account` first) and the exact 3×-verified
  payload. Full discipline: `bug-report-delivery` →
  `references/_split/10-portal-submission-discipline.md` (§1 throttle, §7 captcha-free fallback).
- **Finding #2 NOT sent** — the portal allows one report per account per day and `FF3179` consumed
  it. Payload ready at `submit/finding2_payload.json` (title 104 ch, description 4,389 ch, 7
  sections, attachment 8,467 B); email draft `r1850442480756029124` also carries it.
- Gmail drafts (unsent) to `support@scribblemaps.com`, one per finding, corrected PDFs attached:
  `r-5650808210828374501` (finding 1, 10,050 B), `r1850442480756029124` (finding 2, 8,467 B) and
  `r518573298858966182` (finding 3 SSRF, 6,829 B). All three bodies carry a SUBMISSION DETAILS
  block so the same text can be pasted into the portal. Stale drafts carrying older PDFs were
  deleted and recreated — when a PoC PDF is regenerated, **rebuild the draft** or it ships the
  old attachment.
- The operator was given a headed browser with the finding-#1 portal form pre-filled and verified
  3× (title 75 ch, description 4,214 ch, date, PDF attached, PayPal `RESEARCHER_EMAIL`,
  Turnstile solved by clicking the widget). `GET /api/vulnerability/list` stayed `[]` throughout,
  i.e. the manual click never landed; the report that exists is the `aisubmit` one (`FF3179`).
  Re-open the form with `portal_final.py` if a manual attempt is still wanted.
- ⛔ **Never dry-run probe `/api/vulnerability/submit`** — 6 deliberately-incomplete payloads
  tripped a per-IP `429` that blocked the real submission for ~40 min. Learn field names from the
  form HTML + page JS instead.
- Login on this target shows a **"You are logged in elsewhere. Logout other location?"** dialog
  when a previous browser session is still alive; click **YES** (the orange/primary button) to
  force the new session, then re-verify with `GET /api/account`.
