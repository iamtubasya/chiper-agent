---
name: municipal-web-estate-audit
version: 1.0.0
author: RESEARCHER_NAME
description: "Audit Dutch municipality / government web estates. Shared SaaS vendor fingerprints (Signalen/Aether, Djuma, Sigmax CityPermit, Centric, OpenStad), NL gemeente CVD scope/rules (NCSC leidraad), and the exposed non-production-environment detection technique."
metadata:
  hermes:
    tags: [bug-bounty, security, government, municipality, gemeente, cvd, vendor-fingerprint, exposed-env]
---

# Municipal / Government Web Estate Audit

Gemeentes (NL municipalities) and comparable public bodies all run the SAME handful of
third-party vendor platforms. Almost everything you'll hit is a known product, not bespoke
code. Fingerprint the vendor, then audit against that vendor's known API/design instead of
guessing. This bank was built against apeldoorn.nl (2026-11) and generalizes to any NL
gemeente / *.gemeente.nl / *.overheid target.

## When to use
- Target is a municipality, province, or government body (NL: *.apeldoorn.nl, any gemeente,
  `.overheid.nl`, gov SaaS tenants).
- The estate is a sprawling set of subdomains (hundreds), each a different vendor product.
- CVD/disclosure policy is the standard NCSC "leidraad" template (see Scope section).

## Vendor fingerprint map (the core value)

### Signalen / Aether — public reports ("meldingen", "meldpunt")
- React SPA (webpack + redux-saga + redux-first-history + `npm.keycloak-js`).
- Config is inlined as `window.CONFIG={...}` in index.html (also served on `/config.json`).
  Key fields: `apiBaseUrl`, `oidc.authEndpoint` (→ Dex), `featureFlags`, `map`, `head`, `links`.
- API base is usually a SEPARATE host `api.<subdomain>.<domain>` (nginx front).
  `GET {apiBase}/signals/v1/` returns the full endpoint map:
  `public/signals`, `public/areas`, `public/terms/categories` (public) and
  `private/signals`, `private/users`, `private/roles`, `private/me/filters`, `private/csv`, ... (private).
- Private endpoints → `401 {"detail":"invalid token"}` (Dex OIDC). Auth: Dex with municipal
  AD/Entra + a hosting vendor connector (e.g. "Log in with Delta10 account").
- Signals keyed by UUID (`signal_id` string required on POST); DB integer `id` is read-only/private → no easy IDOR.
- Media in object storage (`signalen-aether` on Scaleway s3.nl-ams.scw.cloud) behind signed URLs; listing → 403.
- Well-secured by design. Real bugs here are usually CORS/config, not auth bypass.

### Djuma — citizen portal / forms / WOO OpenInfo ("e-loket")
- Angular SPA. Vendors: Circle Software / Nieuwland (`circle.webgis.nl`, workspace `circle-software-djuma`),
  Visma analytics (`snowplow.visma.com`), Ingenico/Worldline + iDEAL payments.
- Internal SaaS host leaks in 404 bodies: `{"message":"No HTTP resource was found that matches the request URI 'https://eloket.djuma.nl/...'"}` — this is the shared tenant host.
- Public (no-auth) endpoints:
  - `/api/assets/tenantSettings` — leaks full config (fonts, colors, geo apiUrl+workspace, features, metrics.finishUrl, signicatEnabled).
  - `/api/assets/customerPortalSettings` — loginTypes: digid/digidsignicat/eherkenning/eidas/eid/handmatig.
  - `/api/openInfo/filters` — WOO request facet counts `{years:[{value,count}],categories:[],themes:[]}`.
  - `/api/openInfo/search` — POST. Body: `{"searchQuery":"","pageSize":10,"pageNumber":1,"dossierNumber":null,"yearsFilter":[],"categoriesFilter":[],"themesFilter":[]}`.
    Returns `{documentSearchHits, info:{total}, yearsFiltered, categoriesFiltered, themesFiltered}`.
- Three portal types: `p`=customer, `f`=form, `o`=openinfo (Angular enum `zn`/`O`).
- Reverse-engineer search/docs service: grep chunks for `SEARCH_API_URL`, `DocumentsApiUrl="/api/openinfo/documents"`, `dossierNumber`, `yearsFilter`.

### Sigmax CityPermit — parking permits / vergunningen ("parkeren")
- Blazor WebAssembly (`/_framework/blazor.webassembly.js`, `Sigmax.CityPermit.Portal.*` assemblies).
- CSP leaks integrations: `worldline-solutions.com`, `digid.nl`/`was.digid.nl`, `kpn-eid`/`eherkenning.nl` (eID), `brk.eid.kpn.com`.
- Dynatrace (`X-ruxit-JS-Agent`, `X-OneAgent-JS-Injection`, `dtCookien*`, `ruxitagentjs_*`).
- Auth = DigiD (citizen) / eHerkenning (business) — can't self-provision; needs account from operator.

### Centric — legacy eDiensten ("snelbalie", burgerzaken)
- ASP.NET WebForms + AjaxControlToolkit (old .NET). Cookie `CentricEBBASPXAUTH2` is the Centric sign.
- Login: `.../Public/Login.aspx?rolcode=<code>&app=<code>&PS=<n>`, `ReturnUrl` param.
- ViewState encrypted (`__VIEWSTATEENCRYPTED`), `__EVENTVALIDATION` present.

### OpenStad — citizen participation
- Node.js Express + ApostropheCMS (`apos-frontend/releases/<hash>/default/public-module-bundle.js`).
- API: `api.<sub>.<domain>/api/project/{int}` (integer project id). `GET /api/project/{id}/widgets` → `[]` when empty.
  `auth.<sub>` (login), `admin.<sub>` (admin UI, "Welkom bij OpenStad ... inloggen"), `img.<sub>` (images, 401 unauth).

### WordPress main sites (gemeente.nl root)
- Almost always: Wordfence (WAF + Login Security/passkey → `wordfence/v1`, `wordfence-login-security/v1`),
  AAM `advanced-access-manager` (`aam/v2`, `aam/v2` REST map), TranslatePress, ElasticPress
  (`*.clients.hosted-elasticpress.io`), Yoast Premium, Redirection, All-in-One WP Migration (`ai1wm/v1`).
- Ai1wm backups dir is protected: `/wp-content/ai1wm-backups/` returns literal `Kangaroos cannot jump here`.
- `wp/v2/users` → 401 (user enum blocked). xmlrpc → 405 on POST.

## Technique: exposed non-production environment detection (fast, high-yield)
1. Enumerate subdomains (crt.sh `?q=%25.<domain>&output=json` is enough to start), then httpx.
2. Grep for environment suffixes: `-acc`, `-acceptatie`, `-tst`, `-test`, `-staging`, `-dev`, `-prod`.
3. Probe each. The tell is INCONSISTENT protection, not just availability:
   - `X-dev` → 403 (protected) while `X-test`/`X-staging` → 200 = mixed ACL gap.
   - `meldingen-acc` → 403 Google IAP "Sign In" while `test-e-loket` → 200 = same.
4. Prove it's a REAL distinct test env (not an alias) by diffing config/data vs prod:
   - `/api/assets/tenantSettings`: test branding (`"Djuma Formulieren"` vs prod `"Gemeente Apeldoorn Formulieren"`).
   - `/api/openInfo/filters`: test dataset (e.g. `{years:[{value:"2025",count:14}]}`) vs prod (7578 items).
5. Frame impact: same app code as prod, weaker patch/monitoring, test data, free sandbox to develop
   exploits against prod (DigiD/permit/WOO flows).

## NL gemeente CVD scope/rules pattern (NCSC leidraad)
- Contact `cvd@<gemeente>.nl`; encrypted channel often `crypt.<gemeente>.nl` (Zivver/SmartLockr).
- `security.txt` at `/.well-known/security.txt` → Contact, Policy, Expires, Preferred-Languages: nl,en.
- Reward typically a token `€0–300`; report shared with IBD (Informatiebeveiligingsdienst voor gemeenten).
- FORBIDDEN: brute-force access, DoS, malware, social engineering, **download/modify/delete data** (screenshot or directory listing is the acceptable evidence), publishing before fix.
- Long EXCLUSION list (don't report): version banners, missing security headers (HSTS/CSP/XFO/…), CSRF on anon forms, clickjacking w/o login, host-header injection, SPF/DKIM/DMARC, old software WITHOUT working PoC, content spoofing/text injection on error pages, expired domains, missing DNSSEC/HPKP, account-lockout / forgot-password brute-force.
- Consequence: only real, PoC-backed findings (XSS w/ impact, SQLi, RCE, IDOR/BOLA, auth bypass, sensitive data exposure, business logic) are rewarded.

## Pitfalls
- The estate is usually well-secured: nuclei CVE sweep (wordpress/elementor 2024/2025 tags), panels,
  default-logins, and exposures all return ~0 because Wordfence + Dex/AD + DigiD + patched plugins are in place.
  Don't burn a full sweep here — go straight to vendor fingerprinting + env-exposure + business logic.
- Signalen/Djuma/Sigmax are commercial/open-source products with public API docs — read the product,
  don't fuzz blind. IDs are UUID (Signalen) or SaaS-tenant-scoped (Djuma), so IDOR is hard by design.
- `getent hosts` doesn't work under MSYS/git-bash on Windows — use `nslookup`/`dig` or httpx for IPs.
- All SVG/icons served from the media bucket are signed URLs; unsigned access 403 by design (not a bug).

## Workdir scratch (apeldoorn run, for reference)
- `subs.txt` (crt.sh subdomains), `httpx_live.txt`, `public_targets.txt`, per-app HTML/JS bundles,
  `FINDINGS.md`, `DRAFT_email.txt`. Technique above is the reusable part; those files are session artifacts.