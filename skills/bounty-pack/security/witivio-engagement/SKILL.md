---
name: witivio-engagement
description: "Witivio (witivio.com) bug-bounty engagement — scope, rules, core business, estate map, auth model, API surface, and finding state (WIT-1 sent; WIT-2/WIT-3 leads needing a M365 account). Load to resume or re-hunt this Microsoft 365 / Teams app-suite SaaS."
metadata:
  hermes:
    tags: [bug-bounty, security, witivio, teams, microsoft-365, saas, entitlement]
---

# Witivio — Microsoft 365 / Teams app-suite bug bounty

## When to use
- User says "wivitio.com" / "witivio" / resumes this bounty
- Hunting a Microsoft-365/Teams AI-agent SaaS (Teams Pro app suite + AI Desk Pro)

## Target typo trap (cost a recon restart)
User wrote "wivitio.com" but that is **NXDOMAIN** (typo). Real domain is
**witivio.com** (transposed letters). Always `nslookup`/resolve the apex first
and chase `security.txt` → `Policy:` to confirm the real estate before committing.

## Scope, contact, rewards (from https://www.witivio.com/en/bug-bounty/)
- IN SCOPE: `witivio.com`, `aidesk-pro.com`, `teams-pro.com` + all subdomains
- Contact: `dpo@witivio.com` (email submission, ONE vuln per email, EN/FR)
- Reward: discretionary, **MAX €500 / report** (CVSS-guided). Invoice to Witivio, 16A Rue de Selestat, 68000 Colmar, France.
- OUT OF SCOPE (won't pay): TLS/missing-header/DNS best-practice, network DoS, self-XSS, scanner-only reports without PoC, login/logout/low-value CSRF, MITM, non-exploitable, rate-limit vulns.
- DATA RULES: only own/test accounts, minimal interaction, no exfiltration/persistence/pivot, redact PII, use recognisable UA marker (used `BC_USERNAME-security-research`).

## Core business (what the money is about)
Witivio = Microsoft 365 / Teams AI-agent SaaS vendor. "Teams Pro" = a suite of 9
Teams apps (Calendar Pro, Contacts Pro, KeePass Pro, Gantt Chart Pro, Map Pro,
Remind Pro, Parking Pro, Booking Room Pro, AI Shared Calendar Pro). Freemium with
Starter/Premium/Platinum tiers; licence is per-tenant, assigned by an admin.
The entitlement logic is the business core → where BOLA/entitlement bugs pay.

## Estate map (47 hosts — brief)
- **admin.teams-pro.com** = AdminCenter (ASP.NET Core/Kestrel + Razor, Metronic). Custom licence SSO. CORE.
- **admin.aidesk-pro.com** = AI Desk Pro admin (Entra SSO, client_id `b2c0dc10-7931-4437-8e5b-21aeb264b648`, IDWeb). Minimal unauth (`/api/settings` mostly-empty, `/health`).
- 9 app SPAs: `contact|calendar|ai-calendar|remind|maps|parking|bookingroom|keepass|gantt.teams-pro.com` → React SPA + `/api/v1/*` Bearer API.
- graph.teams-pro.com = dead (JSON 404 all paths), subscriptions.witivio.com = redirect to witivio.com.
- Low value: docs/trust/status(Atlassian)/ideas/searchcenter/csm-center(maintenance)/www.
- OUT OF SCOPE third-party: `support.aidesk-pro.com` (Freshdesk), `info|forms.witivio.com` (HubSpot), `mail|smtp|imap.teams-pro.com` (OVH), `lpgsystems-copilot-workshop.witivio.com` (Lovable).

## Recon technique that paid off (Teams / M365 SaaS)
1. `curl -D -` on any host and READ the CSP `frame-ancestors` + `connect-src`: on
   this target it leaked the whole app suite + backing Azure Web Apps
   (`tp-<app>-prd-preprod.azurewebsites.net`) + a third domain (`gpt-pro.com`, OOS).
2. Every app serves unauth `GET /api/settings` → JSON: `clientId`, `tenantId`,
   `graphScopes`, `appInsightConnectionString`, `adminCenterAppId`,
   `adminCenterBaseUrl`, `appSourceOfferId`, sometimes `directLineTokenUrl`.
   Publishable keys are public-by-design; the useful signal is `adminCenterAppId`
   (the entitlement lookup key) and `graphScopes` (keepass = `Files.ReadWrite.All
   Sites.ReadWrite.All` → vault in OneDrive/SharePoint).
3. Extract API surface with `jsluice urls <bundle>.js — not context-grep on minified JS.

## API surface + auth model
- admin.teams-pro.com: `/licence/login|signup|create-user|check-user` (check-user →
  OIDC `login.microsoftonline.com/common`, client_id `df3f7b0b-4265-46c5-946f-cabad2d0981c`,
  scope `openid profile offline_access email User.Read User.ReadBasic.All`).
- Entitlement endpoints on admin.teams-pro.com:
  - `POST /teams-app/data` (form: tenantId,userId,appId) → **NO AUTH** (WIT-1)
  - `POST /teams-app/users/licences` (appId,userIds + Bearer) → 401
  - `POST /teams-app/access-request` (user,appId,reason,locale) → 401
  - `GET /teams-app/more-apps?appId=&userMail=` → public catalog (200, by-design)
- App APIs (`/api/v1/*`, Bearer-gated): `/api/v1/feedback`, `/api/v1/graphtoken?scopesStr=<scopes>`,
  keepass: `/vault`, `/vault/shared/`, `/vault/user/`, `/permissions/:keepassId` (+ Graph `/me/drive/items`, `/groups/<id>/drive/items`).

## adminCenterAppId → product map (confirmed, drives /teams-app/data lookup)
- `008f10ab-e5cd-4344-b972-a44978e10109` → Contacts Pro
- `2affb476-6802-4790-a576-ff02c6c5e263` → Calendar Pro
- `25b0b774-47b8-4a91-abbc-e0398b7b37a9` → Keepass Pro

## Finding state
- **WIT-1 (SENT, validated 3x): unauthenticated BOLA on `POST /teams-app/data`.**
  No auth, trusts client-supplied tenantId/userId/appId, returns
  `isUserStarter/isUserPremium/isUserPlatinum/isUserAdmin` + tenant-level
  `admins[]`, `tenantSuperAdmins[]`, `subscriptionOwner`, `subscriptionId`.
  Contrast: sibling endpoints 401. Read-only; mass-assignment (isUserPremium=true)
  is ignored. Severity filed Medium (CVSS ~5.3). Email drafted+staged in Gmail
  (RESEARCHER_EMAIL), user sent it. Artifacts in `C:/Users/WINDOWS10/witivio/`.
- **WIT-2 (LEAD, needs auth): `/api/v1/graphtoken?scopesStr=` scope escalation** —
  client-controlled Graph token scope; if not validated server-side → request
  `Files.ReadWrite.All` on a User.Read-only app = privesc. Untested (no token).
- **WIT-3 (LEAD, needs auth): KeePass shared-vault BOLA** — `/vault/shared/`,
  `/permissions/:keepassId`. Untested.

## Blocker (account provisioning)
Auth is Microsoft 365 **work-account SSO** (Entra). Self-provisioning a M365 dev
tenant is blocked by CAPTCHA (Arkose) + phone/SMS at `signup.live.com`; Camofox
stealth browser was down this host. A personal outlook account won't reach the
tenant-scoped Teams SSO surface. Leads WIT-2/WIT-3 stayed unaudited; only the
unauth perimeter was testable. To finish them: user supplies a Microsoft account
or receives the phone verify, then install a Teams app + capture the SSO Bearer.