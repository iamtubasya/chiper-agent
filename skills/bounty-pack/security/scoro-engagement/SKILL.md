---
name: scoro-engagement
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Scoro (scoro.com) work-management SaaS — VDP engagement map. Scope, rules, surface
  estate, API auth model (v4 OAuth2+PKCE, legacy v2 apiKey), signup gate (business-email),
  and known finding (internal staging-cluster disclosure).
metadata:
  hermes:
    tags: [security, bug-bounty, vdp, scoro, saas, oauth, signup]
---

# Scoro VDP — engagement map

Work-management / PSA SaaS untuk firma profesional (proyek, CRM/pipeline, estimasi/budget,
invoicing, time & cost tracking, resource planning, report). Monetisasi: trial 14 hari +
paket per-seat + add-on. Infra AWS multi-region (Frankfurt/Toronto/Sydney).

## Scope & rules (diverifikasi dari policy)
- **Jenis:** VDP "contact only" (disclose.io), BUKAN bug bounty. Safe harbor, reward optional.
- Kontak: `security@scoro.com` (1 temuan / 1 email).
- `security.txt`: `https://scoro.com/.well-known/security.txt` → Policy `https://www.scoro.com/security/`.
- **IN scope:** SaaS app (customer site `*.scoro.com`), public API `api.scoro.com`, mobile
  apps iOS/Android, web property terkait auth/account-security (termasuk `www.scoro.com`).
- **OUT of scope:** `support.scoro.com`, `status.scoro.com` (pihak ketiga); fisikal/social
  engineering/insider; laporan tanpa impact jelas. RoE: no DDoS, no exfil, no privacy
  violation, no persist; akun uji sendiri dgn naming `vdpaccount-<id>.scoro.com`.

## Surface estate (fingerprint)
| host | tech | peran | auth |
|---|---|---|---|
| `<company>.scoro.com` | PHP, cookie `sapi_token` (JWT), `sapi_company_account` | tenant SaaS app | email+password, magic link, email-domain SSO (`email_domains_enabled`) |
| `create-site.scoro.com` | Vue/Vite SPA | signup "Try for free" | `/api/email` (email), `/id/google` + `/id/microsoft` (OAuth), reCAPTCHA v2 invisible |
| `api.scoro.com` | Cloudflare+PHP | API docs + reference | v4 OAuth2; v2 apiKey |
| `apps.scoro.com` | Node/Express (Vue SPA) | App Store / integrations | `/api/apps` publik (by design) |
| `developers.scoro.com` | Nuxt SSR | Developer Portal (register OAuth app) | Google/Microsoft SSO only; `/api/apps` 401 |
| `www.scoro.com` | WordPress | marketing (in-scope auth) | WP plugins |

## API auth model (penting — dari OpenAPI + repo publik Scoro-Software/ai)
- **v4:** OAuth 2.0 authorization code + PKCE + client secret. Base URL `https://{site}.scoro.com/api/v4`.
  Header `Scoro-Company-Account` (opsional). Scopes `{resource}:{level}` (`r`/`rw`/`rwd`) + `offline_access`.
  226 endpoint, SEMUA butuh auth (0 unauthenticated). Token per-site (tak bisa lintas site).
  - authorize: `https://{site}.scoro.com/auth/oauth/authorize`
  - token: `https://{site}.scoro.com/auth/oauth/token`
  - OpenAPI: `https://api.scoro.com/api/v4/reference/openapi` (publik, 944KB).
  - Endpoint kaya IDOR: `/api/v4/files/{id}/download`, `/invoices/{id}/pdf`, `/orders/{id}/pdf`,
    `/companies/{id}`, `/persons/{id}`, `/custom/{customModulePath}/...`.
- **v2 (legacy, masih hidup):** `POST https://api.scoro.com/api/v2/{module}/{action}` body
  `{"apiKey","lang","company_account_id","request":{}}` ATAU `{"user_token",...}`.
  Sample pakai `company_account_id:"tutorial"` (demo). Juga header `scoro-app-id` untuk app marketplace.
- **Register OAuth app** = via Developer Portal (developers.scoro.com, SSO). callback URL boleh
  `http://`, `localhost` tanpa scheme; `redirect_uri` harus match EXACT.

## Signup gate (blocker, terukur)
`POST create-site.scoro.com/api/email` (form pricing, cross-origin dari www.scoro.com, method POST,
body `userEmail` + `agreement`, cookie `pricing_create_site_config` = konfig paket id `79` dst):
- domain invalid / tak ada MX → `303 /error` (synchronous).
- **gmail/outlook (provider gratis) → `303` success + `Set-Cookie scoro_create_site__session`,
  lalu `GET /api/status` `pending` → `failed` (ASYNC reject business-email).**
- Email path ini TIDAK lewat reCAPTCHA (hanya form pricing); reCAPTCHA v2 invisible hanya di
  SPA flow (`/api/recaptcha` → 401 "Authentication required" tanpa session, alias auto-flow
  untuk SSO/manual saja).
- Kanonik: butuh email domain bisnis, ATAU SSO Google/Microsoft dgn account work.
Lihat `signup-block-ops` §1c untuk pola async business-email gate + decode cookie.

## Finding terkonfirmasi (Low/Info)
**Internal environment disclosure di production signup** — bundle publik
`https://create-site.scoro.com/assets/SetupPage-ItioMtqO.js` membocorkan:
1. Cluster "Staging" jadi opsi (dan DEFAULT) di dropdown "Server": `Y={STAGING:"staging",FRANKFURT:"frankfurt",TORONTO:"toronto",SYDNEY:"sydney"}` + `Ce=[{id:Y.STAGING,value:"Staging"},...]`, default `clusterSelection=Ce[0].id`.
2. Teks internal: "Welcome, Scorer! You're here because you signed up with a @scoro.com Google account... internal testing sites should start with the scorotesttemp prefix."
Tak terkonfirmasi apakah server menerima `clusterSelection:"staging"` (perlu akun terverifikasi).

## Coverage note
WordPress (`www.scoro.com`) hardened: xmlrpc → 301, REST user enum diblokir, plugin terbaru
(WPML 5.2.0, AIOSEO 5.0.4 — sudah lewat CVE-2026-109367 ≤5.0.3, Redirection 5.10.1, Safe SVG 2.5.2,
Custom Permalinks 3.3.3). S3/CDN (`scoroassets`/`content`/`developer-portal-cdn`.scoro.com) tertutup.
IDOR/business-logic lintas-tenant & API v4 authenticated **belum diuji** — butuh tenant terverifikasi.