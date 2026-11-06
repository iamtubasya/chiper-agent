---
name: scoro-audit
description: >-
  Scoro (scoro.com) work-management/PSA SaaS — vulnerability disclosure engagement.
  Scope, contacts, estate map (tenant app, API v4/v2, signup flow, developer portal,
  WordPress plugins) and the known low-severity stite finding.
author: RESEARCHER_NAME
metadata:
  hermes:
    tags: [security, scoro, vdp, saas, oauth, api, bug-bounty]
---

# Scoro — VDP engagement notes

Program: **contact-only VDP** (disclose.io), BUKAN bug bounty berbayar. No monetary guarantee.
- Kontak: security@scoro.com
- Policy: https://www.scoro.com/security/
- security.txt: https://scoro.com/.well-known/security.txt (Canonical www, contact mailto:security@scoro.com)
- Ngopenai: VDP = "token of appreciation" discretionary, bukan bounty.

## Scope (teks persis, ketat)
IN scope:
- Scoro SaaS app (customer tenants di *.scoro.com)
- Public API api.scoro.com
- Official mobile apps (iOS/Android)
- Web property terkait auth/account security (termasuk www.scoro.com)

OUT of scope:
- Third-party (support.scoro.com, status.scoro.com = Zendesk/status tooling)
- Physical/social-engineering/insider
- Laporan tanpa impact jelas (mis. rekomendasi header best-practice)

Rules: no DDoS, no exfil data/bulk/scrape, no akses data customer lain, no credential
harvest/session-hijack user asli, no persist (backdoor/admin-user/long-lived token).
Hanya akun/tenant sendiri; konvensi nama tenant `vdpaccount-<id>.scoro.com`.

## Estate map (subfinder 63 subdomain + fingerprint)
- **Tenant app** `<company>.scoro.com` — PHP + JWT. Cookies: `__Host-PHPSESSID`,
  `sapi_token` (JWT `eyJ...`), `sapi_language`, `sapi_company_account` (tenant scope).
  Login `/login`: email+password, magic link, email-domain SSO (`email_domains_enabled`).
  Tenant aktif → 302 `/login`; tenant kosong → 404 "Scoro" (wildcard catch-all).
- **Signup** create-site.scoro.com — Vue SPA. Endpoint `/api/*`: `email`, `status`,
  `datasets`, `check-site-url`, `setup`, `recaptcha`. SSO `/id/google`, `/id/microsoft`.
  reCAPTCHA v2 invisible (sitekey `6LdOrZgp...`).
- **API v4** api.scoro.com → `/api/v4/reference` (Scalar docs). Real base =
  `https://{site}.scoro.com/api/v4`. OAuth2 authz-code + PKCE + client_secret.
  Authz endpoint `/auth/oauth/authorize`, token `/auth/oauth/token`.
  Header `Scoro-Company-Account`. Scopes `{resource}:{r|rw|rwd}` + `offline_access`.
  226 path, SEMUA wajib OAuth (0 endpoint unauth; OpenAPI di `/api/v4/reference/openapi`).
- **API v2 (legacy)** api.scoro.com/api/v2 — POST JSON `{apiKey|user_token, lang,
  company_account_id, request}`. Docs ada akun demo `company_account_id:"tutorial"`
  tapi tanpa key real.
- **App store** apps.scoro.com — Node.js/Express (Vue SPA). `/api/apps` = publik (by design).
- **Dev portal** developers.scoro.com — Nuxt. Google/Microsoft SSO ONLY (no password).
  Buat OAuth app → client_id/secret (secret tampil sekali). `/api/apps`, `/api/apps/me` 401.
- **Marketing** www.scoro.com — WordPress 7.1.4. Plugin (nuclei version-detect):
  AIOSEO 5.0.4, WPML 5.2.0, Redirection 5.10.1, Safe SVG 2.5.2, Custom Permalinks 3.3.3,
  leadin 11.3.75, w3-total-cache 2.11.0, user-role-editor 4.66.3, duplicate-page 4.5.9,
  enable-media-replace 4.2.3, limit-login-attempts 1.7.2, wp-file-manager 8.0.7.
  Hardening: xmlrpc 301 (off), REST /users rest_no_route, ?author=1 → 301, dir 403,
  debug.log off, w3tc-config execute sbg PHP (no leak). wp-file-manager
  `connector.minimal.php` di-WAF-block Cloudflare (managed rule CVE-2020-25213).
- **CDN/S3** scoroassets.scoro.com (200 empty, no listing), content.scoro.com &
  developer-portal-cdn.scoro.com (403 AccessDenied). Tidak ada bucket terbuka.
- Internal clue di subdomain: jenkins.scoro.com, csp-report.scoro.com (Envoy 204),
  datahub.scoro.com, pdapikey.scoro.com, 2fscorocom-staging.scoro.com, sl.scoro.com (nginx 204).

## Signup flow (dipelajari penuh)
1. Marketing form (www.scoro.com/pricing) POST → create-site.scoro.com/api/email dengan
   `userEmail`+`agreement`+cookie `pricing_create_site_config` (data-cookie-payload di
   tombol; `package_id:79`). **Jalur email ini LEWATI reCAPTCHA** (beda dari SPA flow
   yang reCAPTCHA-gated).
2. Balas: 303 root + Set-Cookie `scoro_create_site__session` (payload base64url =
   `{email, firstName, lastName, provider:"email", createSiteHash, expiresAt, issuedAt}`)
   + HMAC signature. `createSiteHash` = token magic-link verifikasi (tertanam di cookie
   sendiri — bisa dibaca tanpa inbox, lihat `signup-block-ops` §1c).
3. `GET /api/status` → `{"status":"pending"}` → `"failed"` (rejected) atau `"ready"`+siteUrl.
4. `GET /api/datasets` → `{"error":"manual_flow_required"}` utk sesi email.

## Blocker akun (business-email gate)
Trial signup menolak email domain gratis (gmail/outlook) secara ASYNC: 303 success lalu
`pending`→`failed`. Domain invalid (non-MX) → 303 /error seketika. Butuh email
business-domain ATAU SSO Google/Microsoft work. Detil + teknik decode cookie state:
`signup-block-ops` §1c. Akibatnya IDOR/business-logic/API-v4 authenticated belom diuji.

## Temuan (terverifikasi)
F1 (Low/Info) — Internal env disclosure di production signup: bundle
`create-site.scoro.com/assets/SetupPage-ItioMtqO.js` menampilkan cluster **"Staging"**
di dropdown "Server" (dan jadi DEFAULT `clusterSelection=Ce[0].id="staging"`), plus teks
internal `"Welcome, Scorer! ... @scoro.com Google account ... scorotesttemp prefix"`.
Evidence + PoC: `C:/Users/WINDOWS10/scoro_work/FINDINGS.md`. Belum dipastikan server
menerima "staging" (perlu akun terverifikasi).

## Lanjut bila akun tersedia
- IDOR/BOLA lintas-tenant (tenant app + API v4 `files/{id}/download`, `invoices/{id}/pdf`,
  `companies/{id}`, `custom/{customModulePath}`).
- Business-logic: plan/trial bypass, proration, webhook forgery (`/api/v4/webhooks` scope).
- apps.scoro.com `settings/package` (plan perubahan).
- developers.scoro.com OAuth app secret exposure / redirect_uri validation.