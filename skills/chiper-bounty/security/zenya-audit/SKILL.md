---
name: zenya-audit
description: Zenya (formerly Infoland) bug-bounty/CVD engagement — scope, rules, API map, auth model, test tenant access, submission flow, and tracked (hardened vs auth-gated) attack surface. Load before/during any Zenya audit.
---

# Zenya (Infoland) — Bug Bounty / CVD engagement

Healthcare quality & risk management SaaS. Was "iProva". CVD program (no fixed tiers; reward by severity+quality), SLA 5 business days.

## Scope & Rules (read first — they void findings)
- Program: https://www.zenya-software.com/coordinated-vulnerability-disclosure
- security.txt: `https://www.zenya-software.com/.well-known/security.txt` (Expires 2027-07-02)
- Submission FORM: `https://forms.zenya.work/psbr6j9omo/1325` (their own form, not H1/BC/YWH). Email needed.
- Languages nl/en. Reward only for "serious, unknown, directly exploitable" issues.

OOS (report will be rejected): fingerprinting/version, public IPs, SPF/DKIM/DMARC, outdated w/o PoC, breach emails, cosmetic, public files, missing headers, URL redirect to valid page, TLS w/o PoC, HTTP 404 & non-200 pages + content spoofing, clickjacking, DoS/resource exhaustion, non-reproducible / not-validated-with-2nd-tool, rate-limit w/o impact, third-party services.
- **"Exploits not validated with a second tool/method" = OOS** → every finding needs 2 independent methods (matches the 3x validation + second-tool rule).
- **FORBIDDEN**: brute-force, malware, copy/edit/delete data, repeated access, social engineering.

Known accepted-risks (NOT reportable): anonymous API access by-design (login/SSO/support-access/public report forms/card-file/portal content), seeing IdP, public OpenAPI + feature flags + version info, tenant-level data exposure (→ report to that customer, not Zenya).

## Product / core business (business-logic targets)
Modules: DOC (DMS), FLOW (workflow+incident/complaint), AUDIT, CHECK, RISK, BOOST, Kaartenbak (card-file), portals.
AI features (NEW, least-hardened → prime targets): AI Chat, AI Search (RAG "answers from the org's own documents"), AI FLOW Prompt, AI summary/translate/compare documents, AI analyze findings, AI risk bowtie, AI image gen (campaigns).
Money/revenue: subscription SaaS, healthcare tenants. No e-commerce/payment surface. High-value bugs = cross-tenant isolation, document/case IDOR (PHI), AI RAG leakage.

## Attack surface & keys
- Tenant host pattern: `<tenant>.zenya.work` (e.g. `imres.zenya.work`, `test.zenya.work`). Each tenant = own host. `m.zenya.io` / `zenyai.io` are UNRELATED companies (OOS, careful).
- Zenya-owned infra: developer.zenya-software.com, my.zenya-software.com, community.zenya-software.com, update.infoland.eu / update.zenya-software.com, forms.zenya.work (Formdesk), webshare.zenya.work. Marketing site zenya-software.com = WordPress 6.8 (plugins: Rank Math, WPML, UberMenu, GoodLayers gdlr-core, GTM4WP, Leadinfo).
- **Zenya's own TEST tenant = `test.zenya.work`** (safe to test, "Test omgeving Infoland"). Version 7.8.0.11, API v5. Sparse data (no cases/docs, 1 inactive reporter form id=1508, 1 case_type id=280 "michel-emergis", ~7807 card-file objects).

### REST API (Swagger, public)
- `https://test.zenya.work/api/swagger/v4/swagger.json` (522 paths / 702 ops; v1 also exists). Front-end generated client: `vueprojects/portal/dist/assets/services.gen-*.js` + `api-*.js` (lists all endpoints incl AI settings)
- Auth schemes: `basic` (Basic auth) + `bearer` (JWT). Global security = basic|bearer.
- OIDC: `/.well-known/openid-configuration` + `jwks.json` (ES256, EC P-256, kid `user_bearer`). issuer=tenant host.

### Auth flow endpoints
- `POST /tokens` {api_key, username} → API token. `POST /bearer_tokens` (basic) → bearer. `POST /oauth/token` (client_credentials/password/etc; needs valid client_id else 401). `GET /tokens/token` (auth). `POST /tokens/sharing_content_api` (auth) — webshare token.
- `POST /tokens/support_access_token` {access_token, justification} → support-access login (anonymous-reachable).
- `GET /zenya_url_tokens` (anonymous) → RS256 JWT {Zenya_domain_url, tenant_id, exp 30min, aud ZenyaUrlToken}. NOTE: RS256 while JWKS exposes ES256 (different key). Used for "is this a real Zenya call" webhook validation.
- IMPERSONATION feature exists (client sends `authorization: bearer <ImpersonationBearerToken>`) — hunt the impersonation endpoint.

### ID model (IDOR planning)
- `object_id`, `case_id`, `report_id`, `media_folder_id`, `collection_id`, `portal_id` = INTEGER (enumerable). `document_id`, `media_item_id`, `attachment_id`, `glossary_item_id`, `case_secret`, `external_user_unique_key` = UUID (unguessable).

### Anonymous model (by design)
API request w/o creds = built-in anonymous account, no permissions. Restricted routes → 403 `Anonymous user not allowed`; invalid creds → 401. Endpoints marked `security:[{}]` in swagger = anonymous-reachable (109 of them), but app-level check still gates writes (POST /objects → 403). Anonymous CAN read: card-file (/objects, /objects/{id}), portals (roots/collections/content_items/news), case_types/reporter_forms, glossary, license, features, versions, settings/{name} (GET, but setting_name enum restricted), zenya_url_tokens.

## Verified hardened (do NOT re-report) on test tenant
- Writes anonymous → 403: POST /objects, POST /cases, PUT/PATCH settings, GET /objects/{id}/permissions, GET /organization_units, GET /objects/{id}/cases, POST /cases/safer_causes/{id}/cases, GET /tokens/token.
- `$filter` (OData-like) on /objects & /documents = safe parser (clean OData "Syntax error"/"unknown function" messages; `$expand`/`$select` ignored) → NOT SQLi.
- `POST /sanitizer` {input} = robust HTML sanitizer (strips scripts/handlers/js:/data: URLs; returns result_code ok_after_changes).
- document content/download IDOR blocked by UUID ids (no enumerable path).
- POST /tokens/support_access_token needs a valid server-issued access_token (not guessable).

## Auth-bypass attempts — ALL FAILED (verified 3x, don't re-try)
- `X-Api-Version` header downgrade (1..5, 0, 999, empty) on `POST /objects` + `GET /organization_units` → still 403. No versioned weak-auth.
- JWT alg confusion on `Authorization: bearer <jwt>`: alg=none, HS256 (empty-secret AND EC-pub-key-as-secret), ES256-empty → all 401 `invalid_token`. Signing is correctly pinned (ES256, EC P-256). No alg=none bypass.
- `POST /tokens` api_key guessing (empty/admin/test/0/1/api) → 400 `Invalid api_key passed`. Not enumerable/guessable.
- SQLi in login `Authorization: credentials u:<x> pwd:<y>` (single/double quotes, `OR 1=1`) → all 401 (parameterized, no injection). Login user-enum = uniform 401, no timing oracle.
- `PATCH /users/password_requests/{uuid}` null/guessed uuid → 404. Reset token unguessable.
- Tenant-isolation header spoof (Host/X-Forwarded-Host/X-Original-Host) → ignored, Host is routing key (prior round).

## NEW leads (this round, unproven/retracted)
- ~~SAML `redirect_url` scheme validation gap~~ RETRACTED. Trial/demo tenant returns `null` for ALL redirect_url (no SAML), which masked the real behavior. On a SAML tenant (infoland/mumc/*.zenya.work via Azure AD or radboudumc via SURFconext): `redirect_url` is NOT reflected in the AuthnRequest (no RelayState in `post_data`), and the Azure Application Gateway WAF blocks `javascript:`/`https://evil.com` with 403 (and `//evil.com` → 400 server-side). No sink, no bypass. SAML tenants found: `GET /bearer_tokens/saml2/data` returns `{url:<IdP SSO url>, method:POST, post_data:<bg64 AuthnRequest>}`; `null` = SAML not configured.
- **Malformed login header → unhandled 500** (still valid, Low): `Authorization: credentials u:admin` (missing `pwd:`) or `credentials u:admin;pwd:x` (semicolon in username) → HTTP 500 unhandled (stable 3x). Same class as prior F5 (unhandled 500). No info leak, not exploitable.
- **OAuth docs client_id/secret** (in Infoland/iProva-REST-API-examples `Authentication.md`) is a DEAD placeholder → 401 `app registration not found` on all tenants. BUT the error reveals a client_id oracle (valid id = different error). client_id is UUID → not enumerable. OAuth client_credentials grants a machine-to-machine token (600s), supports `client_id+client_secret` OR `client_id+client_assertion` (RFC 7523). App registrations created via "Application Management".

## LEGACY SOAP/WCF API (STILL LIVE — the attack surface the REST docs deprecate)
The deprecation doc "List of API functions with support ending Q2 2022" lives at
`webshare.zenya.work/lmg7hpgbqrmp2n4o/DocumentResource/40c47d63-7b82-4961-9c06-f62d9d35515b/Document.html`
(public). It lists SOAP + WCF services "planned for removal Q2 2022" — ALL STILL LIVE in production (verified trial+test):

- `POST /Management/Webservices/UserManagementAPI.asmx` (SOAP, ns `http://www.infoland.nl/suite/core/`, WSDL 96KB public). 30 methods: **AddUser, AddUserGroup, AddUserToUserGroup, RemoveUser, RemoveUserGroup, UpdateUser, UpdateUserGroup, GetUserInfo, GetAllUserLoginCodes, GetAllUserGroupNames, GetUserGroupMembers, GetUserMemberships, GetUserStartCategoryID, GetTokenForUser(strTrustedApplicationID,strLoginCode), LogonByCredentials, LogonByToken, Logoff, GetIProvaVersion, GetLicenseInfo**, + org-unit CRUD (Add/Update/Move/DeleteOrganisationUnit_ByID/ByExternalID/ByParentID).
- `POST /iDocument/Webservices/ExternalInfo.asmx` (ns `http://www.infoland.nl/suite/idocument/`): GetDocumentList, GetDocumentInfo(guid[]), GetDocumentParagraphList(guid,state), GetDocumentBookmarkList, GetFilteredDocumentList, GetFilterFieldValues, GetFolderInfoXML, GetFolderTreeBranchXML, GetMetaFields, GetMultiFolderDocumentList, GetTokenForUser, LogonByCredentials/Token.
- `POST /iPortal/Webservices/External/PortalExternalAccess.asmx`: GetMyTaskList, GetNumberOfReadAndUnreadTasks, GetMyTasksURL.
- WCF `ExternalAPI/*/*.svc` (6): Portals, Documents, News, MyTasks, MyFavorites, MyRecentlyViewedItems.

SOAP envelope: Content-Type text/xml, SOAPAction `"<ns><Method>"`, method element must carry `xmlns="<ns>"` (else params bind null → "Value cannot be null"). ASMX = .NET WebForms (look for ViewState/WebResource.axd on webshare host too).

**Auth model (SOAP = SAME as REST, verified):** anonymous "current user" no-perms. GetAllUserLoginCodes/GetUserInfo/GetLicenseInfo → SOAP fault "current user not allowed"/SecurityException. GetIProvaVersion → 200 (public). GetDocumentList/GetDocumentInfo/GetFolderInfoXML → 200 but `<list rowcount="0"/>` (permission-filtered empty, no IDOR on test). LogonByCredentials/LogonByToken → false for all (parameterized, NO SQLi — 9 payloads all `false`). GetTokenForUser needs valid TrustedApplicationID (else null-ref). NOT a working auth-bypass — but the surface is a reportable Low/Medium "deprecated endpoints not removed" finding (WSDL public, exposes AddUser/GetTokenForUser/GetAllUserLoginCodes/org-unit-CRUD).

## Lead to chase NEXT (needs auth — AI RAG is the money bug)
1. **AI RAG cross-doc leakage / prompt injection**: `/search`, `/search/answer`, `/search/chunks`, `/agents/chat`, `/agents/{id}/chat`, `/documents/{id}/v{v}/generate_summary_requests`. Test: low-priv user asks AI to reveal docs they lack access to (ACL not enforced by embedding index), indirect prompt injection via a malicious doc.
2. **Impersonation endpoint** (find it; test if non-admin can impersonate). Client sends `authorization: bearer <ImpersonationBearerToken>`; login route has `asdifferentuser` type.
3. **Cross-tenant isolation** (tenant_id in tokens; same infra).
4. **Authenticated IDOR** on integer-id resources (cases, objects, reports) between two users.
5. **`POST /users` (v5) creates user** — security=None (needs basic/bearer); if ANY auth-bypass lands, this is self-provisioning → full auth'd surface.

## Account
NO self-service registration (enterprise SaaS, provisioned by tenant admin). No signup form. Brute-force forbidden by policy. To get auth: request a demo/account from sales (infoland/zenya) or use a customer-tenant with permission — otherwise most AI/IDOR testing is blocked. Per operator rule: 5 failed account attempts → stop, move target.

## Report prep
Submit via their form (forms.zenya.work/psbr6j9omo/1325), email field required. Validate every finding with a 2nd independent tool/method (OOS otherwise) + 3x reproduction. Language: en. Severity must show directly-exploitable impact (chain Lo→Critical). Keep PoC alive until verified.