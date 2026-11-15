# Telekom estate map — verified host + endpoint inventory

Recon snapshot 2026-10-29. Artefacts on disk under `D:\isplab\telekom\recon\`
(`subs.txt` 93,423 · `all-clean.txt` · `live-hosts.txt` 5,140 · `live2.jsonl` 2,345 ·
`cname-resp.txt` 730 · `secrets.jsonl` 113 · `actuator-hits.jsonl` 535).

Purpose: stop re-scanning the same hosts. Update in place when a host changes state.

---

## 1. Confirmed defects (state as of snapshot)

### 1a. `customer-rest-services.api-docs.iot.telekom.com` — unauth Spring Boot API + full schema

- `/v3/api-docs` → **200, 498 KB**, `"title":"M2M Customer API REST Service","version":"1.0.0"`,
  **`security: null`** and **`components.securitySchemes: {}`** (empty — no auth declared at all).
- 46 documented paths under `/v1/partners/{partnerId}/…`: `sims`, `pools`, `apiusage`,
  `actions/activation|block|suspend|termination|tariffchange|limitoverride|limitreset|
  simallocation|simtransfer|optionbooking|fraudreset|productivestate|restrict`,
  `sims/{iccid}/sms|session|sessionhistory|hlrcheck|hlrreset`.
- Unauthenticated probes (no `Authorization` at all) → **no 401**:
  `/v1`, `/v1/partners`, `/v1/partners/1`, `/v1/partners/1/sims`, `/v1/partners/1/pools`,
  `/v1/partners/1/apiusage` all return
  `500 {"message":"Could not initialize class at.compax.foundation.core.db.HikariDatasource$HikariDataSourceHolder"}`.
- **Reading:** security filter chain does not cover `/v1/**`; the handler is reached. Data is
  **not** reachable (datasource pool dead). Reportable as *unauthenticated handler chain +
  complete API schema disclosure of a SIM-lifecycle API*; escalation to BOLA
  (`{partnerId}` is an integer) is **conditional on the datasource recovering**.
- Re-check later: poll `/v1/partners` for a non-5xx. If it ever returns 200, stop at one
  record per RoE.

### 1b. `bitwarden.telekom.de` + `bitwarden-test.telekom.de` — internet-facing vaults

- `/api/config` → `{"version":"2026.10.0","gitHash":"8092e6a…","environment":{"cloudRegion":"EU",
  "vault":…,"identity":…},"settings":{"disableUserRegistration":true}}`.
- `/admin` → 302 (admin portal present, login-gated).
- Identity OIDC discovery leaks internal DNS: `"issuer":"http://bitwarden-self-host-identity"`,
  `"jwks_uri":"http://bitwarden-self-host-identity:5000/…"`, and `token_endpoint` is plain
  `http://` internally. Info-leak + internal-topology disclosure; no auth bypass found.

### 1c. `adminapi.dih.telekom.com` — public OpenAPI for an internal approval API

- `/` → `Admin API` (text/plain). `/api-docs` → 200, "Admin Approval API v1.0".
- Documents `organization/{onboardingOrgId}/approval-status|approve-note`,
  `organization/onboarding/merge|find`, `checkAndTrigger/{id}`, `queue_data/*`,
  `triggerAutoSetup[/group]`, `roles`, `allowed/cors`, `update/cors`.
- `servers: [{"url":"http://dih-cloud.net/api/v1"}]` (internal host leaked).
- All `/api/v1/*` → **401** (correctly gated). Schema disclosure only.
- `iam.dih.telekom.com` = Keycloak, realm `dih` public at
  `/realms/dih/.well-known/openid-configuration`; `/admin/` → 403.

### 1d. `5g-slicing.telekom.net` — full API map, correctly gated

- React/Vite SPA. Build env inline: `VITE_BACKEND_API_URL:"/backend/api"`,
  `VITE_OIDC_AUTHORITY:"https://5g-slicing.telekom.net/auth/realms/fivegslice"`,
  `VITE_OIDC_CLIENT_ID:"five-g-slice-ui"`, `VITE_TILER_API_KEY`, Mapbox `pk.` token.
- Endpoints (all `401` with the AWS-style envelope `{"errors":[],"traceId":"Root=1-…","userTraceId":"…"}`):
  `/backend/api/{whoami,products,user,user/get,customer/list,customer/data,orders,orders/export,
  simcards,simcards/get,role-booking-configs,customer-booking-configs,product-order,
  product-order/{id},map/fetch-mapbox-layer,map/is-at-layer,spiceRack/5gEventEligibility,
  pdf/generate-pdf/{id}}`. `/backend/api/whoami` → 403 (different handler than the rest).
- `/api/*` (without `/backend`) returns the **200 SPA shell** — catch-all trap.
- Keycloak `five-g-slice-ui`: **public PKCE** client (`Missing parameter: code_challenge_method`
  on authorize), **no direct access grant** (`unauthorized_client`), `redirect_uri` strictly
  validated (evil.example and `…telekom.net.evil.example` both → 400). No registration link.
- JWT forgery matrix: `alg:none`, `HS256:secret`, `HS256:empty` × `{whoami,products,customer/list}`
  → **all 401**. Skip alg-confusion on this target.

### 1e. `developer.telekom.com` — Nuxt, feature-guarded

- `/api/sitemap-handler` → 200 (public route list, 86 entries).
- `/api/account/profile`, `/api/account/name`, `/api/dashboard/invitations`,
  `/api/documents/upload`, `/api/dashboard/party-privacy/keycloak/verifyJwks` → 404 with
  `"data":{"source":"feature-guard"}` = **routes exist, gated off**.
- `/api/sms-campaign-tool/vonage-sms-send` → server-side **Vonage proxy**: accepts
  `{to,from,text,apiKey,apiSecret}` and **reflects the provider's response verbatim**
  (`"error-text":"Bad Credentials"`, `message-count`). SSRF-ish proxy + provider-error oracle;
  needs a valid Vonage key to abuse. `/api/support-form-email` → 400 `Missing emailData…`,
  then 401 on any shape tried.
- `dashboard.developer.telekom.com` → 302 to `oidc.idp.vonage.com` (client `dt-dashboard-telekom`).
- `docs.developer.telekom.com` is a **Vonage** docs mirror (title "Vonage Verify API") — the
  MagentaBusiness CPaaS is white-labelled Vonage. Not a DTAG app.

### 1f. Internal tooling exposed (all login-gated, no bypass found)

| Host | Product / version | Public surface |
|---|---|---|
| `schiff.roaming.telekom.net` | Portainer **2.45.3** | `/api/status` public (`InstanceID`); `/api/users/admin/check` → 204; `/api/endpoints` → 401 |
| `argocd.tcloudlz.telekom.net` | Argo CD | `/api/version` + `/api/v1/settings` (2.9 KB) public; `/api/v1/applications` → 401 |
| `argocd-demo.commx.bo.dih.telekom.com` | Argo CD Playground | 200, customer tenant — OUT |
| `ai.tcloudlz.telekom.net` | Open WebUI **0.12.4** | `/api/config` public; `enable_signup:false`; `/api/v1/auths/` 401 |
| `artifactory.devops.telekom.de` (+`.dev.`, `-itg.test.`) | JFrog | `/artifactory/api/system/ping` 200; `/repositories` 401 |
| `sonarqube2/3/5/6.devops.telekom.de` | SonarQube | UI 200; `/api/system/status` 403; `/api/projects/search` 401 |
| `dependencytrack.eco{,-preprod}.tsi-dev.otc-service.com` | Dependency-Track 4.8.0 / 4.13.6 | `/api/version` public (systemUuid leaked); `/api/v1/project` 401 |
| `ni22-prd-rmq.scs.iot.telekom.com` | RabbitMQ mgmt | 401; `guest:guest` rejected |
| `bwm{,-beta,-test}.sgp.telekom.de` | **Roundcube** (`rcversion:10617`) | login page; installer absent |
| `acceptance.jira.telekom.de`, `customer.jira.telekom.de` | Jira + SAML | 200 → Kantega SAML redirect; `/rest/api/2/serverInfo` 401 |
| `analytics.brand-dialog.telekom.com` | Matomo | `/index.php` 403; API requires view access |
| `countlydata.pix.telekom.net` | Countly | `/o/ping` → `{"result":"Success"}` |
| `admin.imsa{,-dev,-test}.telekom.de` | iMSA (Vue) | `/api/bff/v1/customer/stock` 401; `/env-config.js` → `AUTH_PROVIDER:"icu"`, `ENVIRONMENT_NAME:"PRODUCTION"` |
| `admin.qc-tool.telekom.net` / `admin.wats.telekom.net` | bespoke admin | `/api/v1/users/me` 401 on `auth.qc-tool…`; recovery endpoints 404 (no enum oracle) |
| `admin.winners-circle.goldclub.telekom.com` | Gold Club admin (React) | SPA 200; backend = `gold-club-tool-stage-*.herokuapp.com` (**third party — OUT**) |
| `secret-share.devops.telekom.de`, `plantuml.devops.telekom.de` | 401 `{"error":"authentication required","login":"/login"}` | |
| `auth.ms.otc.t-systems.com` | Keycloak (resources `3eke2`) | realm `master`/`otc` → 404 |

### 1g. OBS buckets (T Cloud Public)

Public read listing is **by design** for `*-public` / `*-external` names. Check ACL before reporting.

- `apig-demo.obs.eu-de.otc.t-systems.com` — `?acl` shows `AllUsers` **READ**; listing OK
  (`java/SdkDemo.zip`). Public-by-design.
- `brodos-external.obs.eu-de.otc.t-systems.com` — lists `Bedienungsanleitung/*.pdf` (product
  manuals). `?acl` → 403.
- `bgr-geoldg-public.obs.otc.t-systems.com` — 307 redirect to `eu-nl` region endpoint.
- `appdata-3dgt6-bmp-live.obs…` → `NoSuchBucket` (stale DNS entry).

---

## 2. Verified negatives — do not re-run

| Target | What was tried | Result |
|---|---|---|
| `shop.telekom.de` | `/api/shop/{order,items,coupon,confirmation,dcb_vouchers,paypal_express}` | all **404** unauth; API is session-gated upstream. `/api/downtimes`, `/api/redirects` → 200 (public by design) |
| `developer.telekom.com` | `/api/account/*`, `/api/dashboard/*`, `/api/documents/upload` | `feature-guard` 404 (gated off) |
| `5g-slicing.telekom.net` | JWT alg:none / HS256 × 3 payloads × 3 endpoints | 401 ×9 |
| `5g-slicing.telekom.net` Keycloak | `redirect_uri` evil.example, suffix trick | 400 (strict allowlist) |
| `adminapi.dih.telekom.com` | `/api/v1/roles,queue_data,allowed/cors,wikiJsRoles` | 401 |
| `auth.qc-tool.telekom.net` | `recovery/request` with 2 emails, `recovery/validate` bad token | 404 (no user-enum oracle) |
| `*.shared.dih.telekom.com`, `*.commx.bo.dih.telekom.com` | — | customer tenants → **OUT of scope, don't test** |
| ~60 hosts | `/.env`, `/.git/config`, `/actuator/*`, `/server-status`, `/debug/pprof/`, `/v3/api-docs` | 200 + **SPA shell** (body-diff verified). Noise. |
| `artifactory*`, `argocd*`, `sonarqube*`, Portainer, RabbitMQ, Open WebUI | anonymous API | 401/403 (correctly gated) |

## 3. Host-class taxonomy (for scan budgeting)

```
*.tap.telekom.de            ~49,000  ephemeral CI previews — FILTER OUT
*.caas-t41/t3413/t14/p41     ~4,500  container platform
*.aws.telekom.de             ~2,075
*.gc.telekom.de                ~679  GCP prod ingress
*.p5x.telekom.de               ~615  prod ingress (account./login.)
*.devops.telekom.de            ~609  CI/CD tooling (see 1f)
*.oasis.telekom.de             ~563
*.b2b.telekom.de               ~445
*.gigadev.telekom.de           ~426
*.das-schiff.telekom.de        ~391
*.one-erp.telekom.de           ~366
*.a4.telekom.de                ~352
*.odl.telekom.de               ~286
*.ocean.telekom.de             ~264
*.dih.telekom.com            customer tenants — OUT OF SCOPE
*.obs.*.otc.t-systems.com    object storage (mostly public-by-design)
```

CNAME map highlights (third-party SaaS → OUT of scope for attack, useful for asset inventory only):
`business.telekom.com`→netlify · `onesource.telekom.com`→ivalua · `telekomhilft.telekom.de`→sprinklr ·
`surveys.telekom.com`→qualtrics · `brand.telekom.com`→frontify · `rec.telekom.com`→jobs2web ·
`mdm.telekom.net`→mobileiron · `websso.t-systems.com`→msappproxy ·
`autoqa|playground1|prod|preprod|dev1|dev2.sdx.telekom.net`→servicenow ·
`schiff.roaming.telekom.net` + `account.roaming.telekom.net`→**myfritz.net** (home router DDNS! worth a
second look — a corporate DNS name pointing at a consumer FRITZ!Box is an anomaly) ·
`uki.cgs.telekom.net`→azurestaticapps · `modi.telekom.de`→jsctool.com.

## 4. Next actions when resuming

1. Re-run `nuclei` on `urls-scan.txt` to green (takeovers / exposures / misconfig / default-login)
   — the coverage gate is not satisfied until that lane produces output.
2. Re-poll `customer-rest-services.api-docs.iot.telekom.com/v1/partners` for a non-5xx; if it
   recovers, test `{partnerId}` integer traversal with **one** record, then stop.
3. Pull `git.orbit.otc-service.com` / `coder.orbit.otc-service.com` behind
   `pangolin.orbit.otc-service.com` — Pangolin auth-gated, `/api/v1/` says `{"message":"Healthy"}`.
4. `docs.devops.telekom.de`, `login.devops.telekom.de`, `registry.devops.telekom.de` share an ALB
   with `kroki`/`shields`/`plantuml` — one weak service there could pivot.
5. Authenticated lanes remain blocked (no self-registration anywhere). Escalate only via an
   unauthenticated surface.
