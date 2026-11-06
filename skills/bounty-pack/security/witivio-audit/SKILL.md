---
name: witivio-audit
description: "Witivio (witivio.com / aidesk-pro.com / teams-pro.com) bug-bounty engagement — scope, auth model, estate map, the WIT-1 unauth BOLA finding, and the auth-gated leads. Load to resume or re-run this target."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, engagement, witivio, teams, microsoft-365, saas, bola, business-logic]
---

# Witivio Bug Bounty Engagement

## Target name gotcha (cost a false start)
Operator wrote `wivitio.com` — that is **NXDOMAIN** (a transposition typo). The real target is
**witivio.com** (Witivio, a French Microsoft 365 / Teams AI-agent SaaS vendor). Before committing to
ANY operator-named domain: `nslookup` / `socket.gethostbyname` it and confirm it resolves, and for a
typo-shaped name, grep known programs for a near-match. `security.txt` on `www.witivio.com` confirmed
the program and pointed at the policy.

## Scope, contact, rules (captured 2026-11-02)
- **In scope:** `witivio.com` + all subdomains, `aidesk-pro.com` + subs, `teams-pro.com` + subs.
- **OOS:** third-party SaaS (Freshdesk support, HubSpot forms/info, OVH mail, Lovable workshop, Atlassian statuspage), customer/partner systems.
- **Contact:** `dpo@witivio.com` — one vuln per email, EN or FR. Not a form.
- **Reward:** discretionary, **max €500/report**, CVSS-guided, IBAN invoice to Witivio (Colmar, FR).
- **Not rewarded (avoid):** TLS config, missing headers/DNS, network DoS, self-XSS, scanner-only reports w/o PoC, login/logout/unauth/low-value CSRF, MITM, non-exploitable, rate-limit.
- **Data handling:** only own/test accounts; stop once proven; no exfiltration/persistence; redact PII; use recognisable UA marker (I used `BC_USERNAME-security-research`).

## Core business & money path
Teams Pro = a suite of **freemium Teams apps** (Starter / Premium / Platinum, per-tenant licence):
Calendar Pro, Contact Pro, KeePass Pro, Gantt Chart Pro, Map Pro, Remind Pro, Parking Pro, Booking
Room Pro, AI Shared Calendar Pro. Separate product = **AI Desk Pro** (`admin.aidesk-pro.com`, Entra SSO).
Money path = per-user annual subscription managed in the AdminCenter; licence assignment is
org → admin → member. The entitlement flags (`isUserPremium/isUserPlatinum/isUserAdmin`) gate
Premium features in the SPA client.

## Estate map (47 hosts enumerated via subfinder + DNS brute + CSP)
- **Core:** `admin.teams-pro.com` (AdminCenter, ASP.NET Core / Kestrel, Azure ARRAffinity), `admin.aidesk-pro.com` (AI Desk Pro, Entra SSO), the 9 app SPAs (`<app>.teams-pro.com`, React + `/api/v1/*` sensitive).
- Azure backing apps leaked via CSP `frame-ancestors`: `tp-{calendar,ai-calendar,contact,remind,map,parking,booking,keepass,gantt,home}-prd-preprod.azurewebsites.net`.
- `graph.teams-pro.com` = Azure-Function-style JSON `404` on every path (dead/placeholder).
- `subscriptions.witivio.com` → 302 to witivio.com. `docs.witivio.com` (+`docs.teams-pro.com`) = VuePress.
- Internal-only hosts from subfinder (do NOT resolve publicly): `app.witivio.com`, `app-dev`, `api`, `botmeta`, `webchat`, `milo`, `support`, `contact-pro`, `bootcamp-ms`, `dynameet-dev`. Azure Web Apps `tp-*` also not routable direct.

## Auth model
- **AdminCenter** (`admin.teams-pro.com`): custom licence auth → SSO via `login.microsoftonline.com/common` (client_id `df3f7b0b-4265-46c5-946f-cabad2d0981c`, scope `email User.Read User.ReadBasic.All`). `/licence/check-user` (GET→OAuth), `/licence/signup`, `/licence/create-user` (POST, `agree` checkbox only, everything is M365 SSO).
- **App SPAs**: Team SSO token (`getAuthToken`) → `Authorization: Bearer` on `/api/v1/*`. Entitlement looked up client-side from `admin.teams-pro.com/teams-app/data`.
- **AI Desk Pro** (`admin.aidesk-pro.com`): Entra SSO, client_id `b2c0dc10-7931-4437-8e5b-21aeb264b648`, CSP references `*.gpt-pro.com` (OOS) + `directline.botframework.com`.

## Key endpoints & config
- `GET /api/settings` on every app host (UNAUTH) → `clientId`, `tenantId`, `graphScopes`, `appInsightConnectionString` (+ApplicationId), `adminCenterAppId`, `appSourceOfferId`, `trackingBaseUrl` (`teamspro-tracking-integration.azurewebsites.net`), `apiCalendar`, `directLineTokenUrl`. Publishable keys are public-by-design; reportable item is the **internal hostname map + tenant id**.
- `POST admin.teams-pro.com/teams-app/data` (UNAUTH, form body `tenantId&userId&appId`) → full entitlement JSON. **THIS IS WIT-1 (see below).**
- `POST /teams-app/users/licences` (`{appId,userIds}` + Bearer) → `authentication_required` (gated).
- `POST /teams-app/access-request` (`user,appId,reason,locale`) → 401 (gated).
- `GET /teams-app/more-apps?appId=&userMail=` → public app catalog (200, by design).
- `GET /teams-app/{tid}/{aad}/show-plans/{appId}` → 302 to `/licence/signup?userName=…` (userName reflected, HTML-encoded → no XSS).
- App API (Bearer): `/api/v1/feedback`, `/api/v1/graphtoken?scopesStr=`, KeePass `/vault` `/vault/shared/` `/vault/user/` `/permissions/:keepassId`.

## Confirmed identifiers
- Witivio AAD tenant: `9188040d-6c67-4c5b-b112-36a304b66dad`.
- adminCenterAppId → product: `008f10ab...`=Contacts Pro, `2affb476...`=Calendar Pro, `25b0b774...`=Keepass Pro, `b31dd6f0...`=AI Shared Calendar.
- Per-app graphScopes: keepass `Files.ReadWrite.All Sites.ReadWrite.All` (password vault in OneDrive/SharePoint), maps `Sites.ReadWrite.All`, remind `TeamsActivity.Send.* TeamMember.Read.Group`, gantt `User.ReadBasic.All`.

## Findings / leads
### WIT-1 — submitted (draft staged in RESEARCHER_EMAIL → dpo@witivio.com, draftId r9158106228841571245)
Unauth Broken Access Control / BOLA on `POST admin.teams-pro.com/teams-app/data`: no auth, trusts
client-supplied `tenantId/userId/appId`, returns `isUserPremium/isUserAdmin/isUserPlatinum`,
`isTenantLicenceAvailable`, `subscriptionId`, `subscriptionLicenceId`, `admins[]`,
`tenantSuperAdmins[]`, `subscriptionOwner`. Product mapping proves a real server-side lookup
(appId→productName). Severity ~Medium (CVSS 5.3). Verified 3x, stable. Read-only (no mass assignment).
PoC/evidence: `WIT-1_PoC_evidence.txt` + `WIT-1_poc.sh` (attached to the draft).

### WIT-2 — LEAD (needs Teams SSO token, NOT proven)
`GET /api/v1/graphtoken?scopesStr=<scope>` on each app may return a Microsoft Graph token with
client-controlled scopes. If scopes aren't validated against the app's consented set, an authed user
could escalate (e.g. request `Files.ReadWrite.All` on a `User.Read`-only app).

### WIT-3 — LEAD (needs account, NOT proven)
KeePass shared vault BOLA: `/vault/shared/`, `/vault/user/`, `/permissions/:keepassId` + Graph
`/groups/*/drive/items/*`. Crypto is stock `kdbxweb` (AES-CBC + Argon2/PBKDF2/AES-KDF) — no weakness found.

## Verified negatives (do not re-test these cold)
- Mass assignment on `/teams-app/data` (`isUserPremium=true` etc. injected) → ignored, read-only.
- `userName` reflection on signup page → HTML-encoded (`&quot;&gt;&lt;script&gt;`), not XSS.
- `redirectUrl` on `/licence/login` + `/licence/signup` → normalized to `/`, no open redirect.
- `graph.teams-pro.com` → 404 JSON on every path (dead).
- KeePass crypto → standard, no weakness.
- nuclei (exposures/misconfig/panels/cves, high+critical, 47 hosts) → 0 findings.
- `userId` accepts email / `tenantId` accepts domain but returns the same empty record (no clear enumeration oracle).

## Blocker
All authenticated surface is Microsoft 365 work-account SSO (B2B Teams apps) — not self-provisionable
from an Indonesian egress without a business tenant + admin consent. The engagement is effectively
unauth-surface-only; WIT-1 is the maximum provable-from-outside finding.