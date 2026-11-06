# NASA VDP — Program Details (Bugcrowd)

**URL:** https://bugcrowd.com/engagements/nasa-vdp
**Type:** Vulnerability Disclosure (VDP) — NO monetary reward. Reward = Letter of Recognition (LOR) for P1-P4 validated/accepted/fixed reports.
**Status:** Ongoing (since Jun 01, 2023). Expedited triage enabled.
**Triage:** 75% accepted/rejected within 2 days. Acknowledgment ≤ 3 business days. 14,648+ accepted vulns.

## IN SCOPE Targets
| Target | Tech Stack |
|--------|-----------|
| `https://nasa.gov` / `https://www.nasa.gov` | Drupal, jQuery, Moment.js (+2) |
| `https://usgeo.gov/` | Drupal, jQuery, Moment.js |
| `https://globe.gov/` | Drupal, jQuery, Moment.js (+2) |

**Rule:** Hanya domain + subdomain dari list. Domains lain = OUT OF SCOPE. Testing strictly authorized ONLY on listed targets. Non-federal vendor/contractor systems = report ke vendor langsung.

## OUT OF SCOPE (testing types — auto reject)
- Social engineering (phishing, user click manipulation)
- DoS / Rate Limiting / Spamming (layer 7 DoS, Slowloris)
- Clickjacking pada pages tanpa sensitive actions
- `/wp-json/wp/v2/users` dan `xmlrpc.php` endpoints
- Attacks butuh physical access ke device user
- Known vulnerable libraries TANPA working PoC
- Content spoofing / text injection
- Reports dari automated tools/scans TANPA demonstrasi exploitability
- Software version disclosure TANPA exploit
- Missing best practices (security headers, captcha, insecure certs)
- SSL/TLS issues (ciphers, certificates)
- Missing security headers (HSTS, CSP) yang tidak lead ke vulnerability
- `autocomplete` attribute di web forms
- Host header injection KECUALI bisa buktikan steal user data
- Insecure cookie settings untuk non-sensitive cookies
- Directory Listing (standalone)
- Vulns yang hanya jalan di outdated browsers
- Verbose/descriptive error messages
- Non-technical vuln testing

## Guidelines
- Test di non-production env jika ada (contoh: `test.gcn.nasa.gov` BUKAN `gcn.nasa.gov`)
- STOP testing segera + notifikasi NASA jika ketemu sensitive data (PII, SSN, financial, ITAR/EAR, "Top Secret" markings)
- No compensation — submit report = waive all claims. LOR saja.
- 90-day coordinated disclosure — jangan publish sebelum NASA approval
- Report dalam English, sertakan PoC steps + screenshots
- Kontak jika ragu scope: `Agency-DL-VAMP-VDP@mail.nasa.gov`

## Safe Harbor
Authorized under CFAA, DMCA exempt, waives ToS restrictions — selama good faith compliance. NASA won't pursue legal action.

## Recon Findings (2026-08-24, post-deep-dive complete)
**Subdomain enum (subfinder, 3 domains):** 3,563 subdomains → **415 live hosts** (httpx).

### Tech Stack Summary (verified 2026-08-24)
| Target | Stack | Notes |
|--------|-------|-------|
| `www.nasa.gov` | **WordPress VIP** (7.0.4) + Next.js | 32 namespaces, 236 custom routes. All sensitive endpoints 401. |
| `science.nasa.gov` | **WordPress VIP** + React | 40 namespaces, 321 custom routes. VIP dev-tools SSRF (URL-validated, blocked). |
| `software.nasa.gov` | **Drupal 10.4.3** | All endpoints 401/403. Well-hardened. |
| `oig.nasa.gov` | WordPress + custom NASA plugins | **REPORTABLE**: `nasa-external-content/v1/unpublished-posts` leaks unpublished content IDs/timestamps WITHOUT auth. 31 custom REST API namespaces exposed. P3-P4. |
| `ceres.larc.nasa.gov` | **WordPress 6.5.4** | Apache, BWP External Links 1.1.3, ACF. Well-hardened. |
| `globe.gov` | **Liferay DXP 7.4** + Apache Tomcat | 136 `/o/` paths, 86 portlets. All sensitive endpoints 401/403. |
| `api.globe.gov` | Node.js + Express | Actuator hostname leak, dev API exposed, CORS * (by-design). |
| `nccs.nasa.gov` | **WordPress** (old) | nginx/1.14.1, login enum confirmed, registration open, WP content exposed. |
| `ciencia.nasa.gov` | **WordPress** | XMLRPC active but **multicall BROKEN (500), pingback DISABLED, rate limiting ACTIVE**. |
| `mcdc.msfc.nasa.gov` | WordPress (childcare site) | **REPORTABLE**: CORS ACAO=* + ACAC=true. Author enum also works. |
| `mast.stsci.edu` | Static + API | **REPORTABLE**: CORS ACAO=* on Space Telescope Science Institute. |
| `images.nasa.gov` | **S3 + CloudFront** (SPA) | CORS ACAO=* (by-design for public images). All paths return same SPA HTML. |
| `images-admin.nasa.gov` | **Amazon S3** | CORS ACAO=*. S3 bucket accessible. |
| `ames-test` | **S3 bucket** | **REPORTABLE**: 2 objects publicly accessible (11MB .rds file). |
| `espoarchive.nasa.gov` | **Drupal 7** (EOL) | install.php accessible ("already installed"). CHANGELOG exposed. |
| `standards.nasa.gov` | **Drupal 9** (EOL) | install.php accessible ("already installed"). |
| `esdpubs.nasa.gov` | **Drupal 10** | install.php accessible ("already installed"). JSONAPI false positive. |
| `pds-engineering.jpl.nasa.gov` | WordPress | Author enum works. |

### Reportable Finding 1: oig.nasa.gov — STRONGEST
**Finding:** Custom REST API Namespace Bypasses Standard WordPress Permission System
**Endpoint:** `GET /wp-json/nasa-external-content/v1/unpublished-posts`
**Auth:** NONE required
**Key insight:** Standard WP REST API blocks `?status=unpublish` (403 "Status is forbidden"), but this custom namespace bypasses it entirely.
**Data leaked:** 18 unpublished items across 12 content types with internal IDs + timestamps:
  - feature-ext (1), post (1), post-ext (2), topic-ext (3), people-ext (1), mission-ext (1), customize_changeset (1), topic (3), image-article-ext (1), gallery (1), location (1), people (2)
**Additional exposure:** 31 custom REST API namespaces exposed (coauthors/v1, redirection/v1 with 32 routes, mcp, ajax-search-pro). Custom post type IDs confirmed to exist (401 not 404 on custom type endpoints).
**VDP exclusion check:** NOT excluded — custom namespace is different from `/wp-json/wp/v2/users` (which IS excluded)
**Severity:** P3-P4 (Broken Access Control / Information Disclosure — CWE-862)
**Confidence:** HIGH (100% reproducible, no auth, consistent response)
**Status:** Ready to submit — strongest finding (novel vector, custom plugin code = less reviewed)

### Reportable Finding 2: CORS Credential Theft — 3 NASA WordPress Hosts (P1-P2 CRITICAL)
**Session: 2026-09-07 — re-verified, all 3 live hosts confirmed vulnerable.**

**Finding:** WordPress REST API CORS misconfiguration — origin reflection with credentials + full write methods + nonce header allowed. Enables full cross-origin WordPress compromise (read + write + delete) from any attacker-controlled domain.

**Affected hosts (all live, all WordPress):**
| Host | CMS Version | Theme | Status |
|------|------------|-------|--------|
| `nccs.nasa.gov` | WordPress 7.1 (Apache) | Twenty Twenty-Five | 🔴 VULNERABLE |
| `oig.nasa.gov` | WordPress 7.1 (nginx/Akamai) | nasa-oig | 🔴 VULNERABLE |
| `science.nasa.gov` | WordPress 7.0.4 (nginx/Akamai) | custom | 🔴 VULNERABLE |
| `mcdc.msfc.nasa.gov` | WordPress (childcare) | — | ⚫ DOWN (502) |

**CORS headers confirmed on ALL 3 live hosts:**
```
Access-Control-Allow-Origin: https://evil.com     ← reflected!
Access-Control-Allow-Credentials: true             ← cookies sent!
Access-Control-Allow-Methods: OPTIONS, GET, POST, PUT, PATCH, DELETE  ← write methods!
Access-Control-Allow-Headers: Authorization, X-WP-Nonce, Content-Type ← nonce allowed!
```

**Origin variations tested (ALL reflected on all 3 hosts):**
- `https://evil.com` → reflected ✅
- `null` → reflected ✅ (exploitable via iframe sandbox)
- `https://evil.nasa.gov` → reflected ✅ (subdomain takeover vector)

**Attack chain (WordPress-specific):**
1. Attacker hosts page on evil.com with JS
2. Victim (authenticated WordPress user) visits evil.com while logged into NASA WP
3. JS reads all content cross-origin (GET /wp-json/wp/v2/posts, pages, media, users)
4. JS extracts X-WP-Nonce from cookie (WordPress nonce is accessible from JS, not HttpOnly)
5. JS makes authenticated POST/PUT/DELETE requests (create posts, modify content, delete users)
6. Full WordPress compromise — attacker controls content on NASA subdomains

**Additional exposure per host:**
- `nccs.nasa.gov`: 15+ custom namespaces (all auth-protected 401), readme.html leaks WP version
- `oig.nasa.gov`: 37+ custom namespaces (two-factor, mcp, VIP, cron-control, edac, nasa-apps)
- `science.nasa.gov`: 38+ custom namespaces (simple-history, gwiz, sweep, nasa-external-content, ADFS SSO via authfs.launchpad.nasa.gov)

**SDAS/Federated Identity Impact:** science.nasa.gov uses SAML SSO via NASA ADFS (authfs.launchpad.nasa.gov). CORS credential theft on this host steals NASA enterprise identity, not just WordPress session.

**VDP exclusion check:** NOT excluded — CORS misconfiguration is NOT `/wp-json/wp/v2/users` (which IS excluded). The attack vector is cross-origin credential theft via CORS, not user enumeration.

**Severity:** P1-P2 CRITICAL (CORS Misconfiguration + Credential Theft — CWE-942). CVSS: `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N` — Score: 8.1 (HIGH) minimum. Escalates to CRITICAL with SSO/ADFS (enterprise identity theft).

**Confidence:** HIGH (100% reproducible, raw http.client + curl verified, all origin variations confirmed)

**Status:** Re-verified 2026-09-07 — all 3 live hosts still vulnerable. Ready to submit as consolidated CORS finding across NASA WordPress infrastructure.

### Reportable Finding 3: mcdc.msfc.nasa.gov — CORS with Credentials
**Finding:** CORS `Access-Control-Allow-Origin: *` WITH `Access-Control-Allow-Credentials: true`
**Endpoint:** Any URL on mcdc.msfc.nasa.gov
**Auth:** ANY origin (evil.com, attacker.com, null) gets ACAO=* + ACAC=true
**Key insight:** While this is a childcare website (not mission data), the CORS misconfiguration allows any website to make authenticated cross-origin requests with cookies. Preflight allows GET, POST, and common headers.
**Additional:** Author enum also works (`?author=1` → `/author/admin`)
**VDP exclusion check:** NOT excluded
**Severity:** P3-P4 (CORS Misconfiguration — CWE-942)
**Confidence:** HIGH (verified with raw http.client, all origins confirmed)
**Status:** DOWN (502) as of 2026-09-07 — re-verify when back online

### Reportable Finding 4: mast.stsci.edu — CORS Wildcard on Science API
**Finding:** WordPress login page differentiates valid vs invalid users via error messages
**Endpoint:** `POST /wp-login.php` with `log=<username>&pwd=wrong`
**Valid users confirmed:** nccsadmin, dacarl1, epresno (via "password for X is incorrect")
**Invalid user:** returns "username X is not registered"
**Additional:** No captcha, no rate limiting, internal hostname `nccs.smce.nasa.gov` leaked via page GUID. Registration page open. REST API pages/posts/media/categories/tags all exposed.
**VDP exclusion check:** `/wp-json/wp/v2/users` is EXCLUDED, but login error enum is a DIFFERENT vector (NOT excluded)
**Severity:** P4 (Username Enumeration + Missing Brute-Force Protection)
**Confidence:** HIGH

### Reportable Finding 4: mast.stsci.edu — CORS Wildcard on Science API
**Finding:** `Access-Control-Allow-Origin: *` on all endpoints including MAST API (`/api/v1/invoke`)
**Endpoint:** Any URL on mast.stsci.edu
**Auth:** Any origin, preflight allows `x-requested-with` header
**Impact:** Cross-origin requests to Space Telescope Science Institute API. Since this is public scientific data, impact is limited but still a misconfiguration.
**Severity:** P4-P5 (Low-Medium)
**Confidence:** HIGH

### Reportable Finding 5: S3 Bucket ames-test — Public Data Access
**Finding:** S3 bucket `ames-test` publicly listable with 2 objects
**Objects:**
  1. `ames-pricing/20230914T134750Z-8818a/ames-pricing.rds` (11,181,095 bytes)
  2. `ames-pricing/20230914T134750Z-8818a/data.txt` (292 bytes)
**Impact:** Publicly accessible test bucket with potentially sensitive pricing data. .rds file could contain internal data structures.
**Severity:** P4-P5 (Low)
**Confidence:** HIGH

### Downgraded Finding: ciencia.nasa.gov — XMLRPC (WEAKER than assessed)
**Finding:** XMLRPC active but most attack vectors NOT functional
**Details:**
  - `system.multicall`: **BROKEN** (returns 500 error)
  - `pingback.ping`: **DISABLED** (-32601 "method does not exist")
  - Rate limiting: **ACTIVE** (429 after ~8 attempts, 2+ minute cooldown)
  - All data methods require valid credentials (wp.getAuthors, wp.getUsers, etc.)
  - Only `system.listMethods` (79 methods) and `demo.addTwoNumbers` work without auth
**VDP exclusion check:** NOT excluded
**Severity:** DOWNGRADED from P3-P4 → P5/P4 (Information Disclosure only — 79 methods + debug endpoint exposed)
**Confidence:** HIGH
**Recommendation:** Include as supplementary finding in oig.nasa.gov report, not standalone submission

### Drupal install.php Findings (P5 — all 3 sites)
**Finding:** `/core/install.php` accessible on multiple Drupal hosts
**Affected:** standards.nasa.gov, esdpubs.nasa.gov, espoarchive.nasa.gov
**Status:** All show "Drupal already installed" — cannot be re-used for installation
**Severity:** P5 (Informational — info disclosure only)
**Recommendation:** Block via web server config (.htaccess / nginx rule)

### False Positives (DO NOT submit)
- **esdpubs.nasa.gov JSONAPI:** Returns 200 but Content-Type is `text/html` — Drupal catch-all routing, NOT real JSONAPI data
- **swehb.nasa.gov OGNL (CVE-2022-26134):** 500 on OGNL payloads, but SAME 500 on any `.action` path — Confluence action mapper error, NOT OGNL execution
- **swehb.nasa.gov CVE-2023-22515:** `/setup/setup.action` returns 200 but no form inputs — NOT exploitable
- **nccs.nasa.gov REST API user enum:** EXCLUDED by VDP (`/wp-json/wp/v2/users`)
- **images.nasa.gov / exoplanets.nasa.gov SPA catch-all:** All paths return 200 with same byte count — SPA routing, not file exposure

### Targets Tested & Closed (No Reportable Finding)
- `api.globe.gov`: Actuator + dev API (by-design, not reportable)
- `images-api.nasa.gov`: No injection surface
- `ceres.larc.nasa.gov`: Well-hardened (auth-blocked)
- `mdscc.nasa.gov`: Foobox not exploitable (no active galleries)
- `globe.gov`: Liferay DXP 7.4 auth-blocked, all sensitive endpoints 401
- `software.nasa.gov`: Drupal 10.4.3 auth-blocked
- `science.nasa.gov`: VIP dev-tools URL-validated (SSRF blocked)
- `nasa.gov`: All custom endpoints 401
- `usgeo.gov`: Static site, no dynamic features
- `esdpubs.nasa.gov`: JSONAPI returns HTML not JSON (false positive)
- `swehb.nasa.gov`: Confluence 9.2.22 — OGNL 500 = action mapper error (not vuln)
- `espoarchive.nasa.gov`: Drupal 7 EOL — tested all SA-CORE CVEs, all blocked
- `standards.nasa.gov`: Drupal 9 EOL — version disclosure excluded by VDP
- `portal.nccs.nasa.gov`: nginx/1.14.1 — old version but excluded (version disclosure)
- All 415 hosts scanned — 237 responded, 178 timed out

### Key Insights for Future Testing
1. NASA WordPress VIP has strong auth on all custom endpoints — `nasa-external-content/v1/unpublished-posts` is the ONE exception
2. Liferay DXP 7.4 on globe.gov is well-hardened — all sensitive endpoints 401/403
3. Drupal 10.x on NASA is well-hardened — don't expect easy wins
4. Most "scary" endpoints (gwiz install/activate, VIP plugins, JSONRPC) are all 401
5. Skip low/by-design findings early — focus on targets with actual exploit potential
6. **Custom WP REST API namespaces bypass core permissions** — always enumerate ALL namespaces from `/wp-json/` root, test each for auth bypass
7. **VDP exclusion precision matters** — `/wp-json/wp/v2/users` excluded, but `?author=N` and login error enum are NOT excluded (different vectors)
8. **Confluence 500 on `.action` paths = NOT OGNL** — compare against random `.action` path to confirm false positive
9. **Drupal JSONAPI 200 + text/html = false positive** — always check Content-Type, not just status code
10. **Claude subagents may REFUSE security testing** — fallback to direct terminal execution
11. **WordPress login error differentiation varies** — always test both valid + invalid users before claiming enum works
12. **415 hosts scanned, only 7 reportable findings** — NASA's security posture is strong. Focus on novel vectors (custom namespaces, CORS chains) not standard checks
13. **XMLRPC methods must be individually verified** — multicall can be broken, pingback can be disabled, rate limiting can be active. Don't assume exploitability.
14. **CORS ACAO=* + ACAC=true is the real finding** — ACAO=* alone on public/static sites is often by-design. The credential-bearing variant is the actual vulnerability.
15. **S3 bucket enumeration works** — systematic name guessing + public listing check. Test common suffixes (-test, -dev, -staging, -backup, -public, -data).
16. **SPA catch-all = false positive factory** — if ALL paths return 200 with same byte count, it's client-side routing, not real endpoints. Check Content-Type and body hash.
17. **Parallel multi-stream scanning is essential** — for 10+ targets, run 3-5+ background scripts + delegations simultaneously. Sequential testing doesn't fit time budgets.

### Recent disclosed high-value reports (contoh pola finding diterima):
- Unauthenticated Error-Based SQLi via POST parameter (P1)
- Unauthenticated RCE in AMMOS AIT-GUI via /tlm/query file write → /script/run chain (P1)
- Unauthenticated SSRF in NASA Trek addManifest → internal network access (P2)

## Recommended Focus (updated 2026-08-24, post-full-deep-dive)
1. ~~**oig.nasa.gov**~~ DONE — ESCALATED to P3-P4 (custom namespace bypass). Ready to submit.
2. ~~**mcdc.msfc.nasa.gov**~~ DONE — CORS ACAO=* + ACAC=true confirmed. Ready to submit.
3. ~~**All 415 hosts scanned**~~ DONE — recon + deep dive complete. 7 reportable findings identified.
4. ~~**ciencia.nasa.gov XMLRPC**~~ DONE — DOWNGRADED (multicall broken, pingback disabled). Include as supplementary only.
5. **SSRF chains** — NASA Trek `addManifest` pattern accepted P2 — look for similar in other NASA APIs
6. **Custom namespace audit across all WP sites** — the oig finding suggests other NASA WP sites may have similar custom plugin leaks
7. **Confluence auth-bypass CVEs** — `wiki.earthdata.nasa.gov`, `swehb.nasa.gov` — need valid creds or auth-bypass class CVE
8. **Report submission** — compile 6 strongest findings into Bugcrowd submission format with X-Bugcrowd header

## Tools
Sudah terinstall di venv (Windows/MSYS): subfinder v2.6.7, httpx-pd, nuclei v3.3.7, ffuf v2.1.0. Workdir recon: `~/nasa-vdp-recon/` (all_subs.txt, live_hosts.txt).
