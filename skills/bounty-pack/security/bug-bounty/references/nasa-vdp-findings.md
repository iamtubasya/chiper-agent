# NASA VDP Recon Findings Summary

**Engagement:** NASA VDP (Bugcrowd, ongoing, LOR only)
**Scope:** *.nasa.gov, *.usgeo.gov, *.globe.gov
**Date:** August 2026
**Reporter:** BC_USERNAME

## Confirmed Findings (Reportable)

### 0. oig + nccs + mcdc.nasa.gov — CORS Origin Reflection + Credentials (P2-P3 CRITICAL) ⭐ NEW
- **Pattern:** Server reflects ANY attacker-controlled origin in `Access-Control-Allow-Origin` + `Access-Control-Allow-Credentials: true` on `/wp-json/*` endpoints
- **Affected hosts:** oig.nasa.gov, nccs.nasa.gov, mcdc.msfc.nasa.gov
- **ACAO:** Reflects `https://evil.com`, `https://attacker.com` — any origin
- **ACAC:** true — cookies sent cross-origin
- **Methods:** OPTIONS, GET, POST, PUT, PATCH, DELETE — ALL allowed cross-origin
- **Preflight:** OPTIONS returns same permissive CORS headers
- **Vary: Origin** present — server intentionally processes Origin header
- **nccs.nasa.gov (MOST SEVERE):**
  - `/wp-json/wp/v2/users` = **200 WITHOUT auth** — leaks 3 users cross-origin: Admin/nccsadmin (ID:2), Douglas Carl/dacarl1 (ID:16), Edel Presno/epresno (ID:17) + Gravatar hashes
  - `/wp-json/wp/v2/posts` = 200 — 95 posts readable cross-origin (29KB)
  - `/wp-json/wp/v2/pages` = 200 — 68 pages readable cross-origin (11KB)
- **oig.nasa.gov (INSPECTOR GENERAL):**
  - `/wp-json/wp/v2/users` = 401 (needs auth) BUT CORS allows credentialed requests → session hijack
  - `/wp-json/wp/v2/posts` = 200 — 1130 posts cross-origin readable (72KB)
  - `/wp-json/wp/v2/pages` = 200 — 90KB cross-origin
  - 31 custom REST API namespaces exposed
- **mcdc.msfc.nasa.gov:**
  - `/wp-json/wp/v2/users` = 401 + CORS with credentials
  - `/wp-json/wp/v2/posts` = 401 + CORS with credentials
  - Root `/` = ACAO=* + ACAC=true
- **Attack chain:** evil.com JS → `fetch(target/wp-json/..., {credentials:'include'})` → reads data with victim's cookies → exfiltrates to attacker server
- **Cross-origin state change:** PUT/PATCH/DELETE allowed = CSRF+CSWSH = modify/delete posts as authenticated user
- **Mass scan:** 415 hosts tested — ONLY these 3 affected (not widespread)
- **Evidence:** `poc_cors_evidence.txt`, `poc_*.json`, `cors_verify.py`, `FINDING_CORS_CREDENTIAL_THEFT.pdf`
- **CWE:** CWE-942 (Permissive Cross-domain Policy with Credentials)
- **CVSS:** 7.5-8.1 (High)

### 1. oig.nasa.gov — Custom API Unpublished Content Leak (P3-P4)
- **Endpoint:** `GET /wp-json/nasa-external-content/v1/unpublished-posts`
- **Result:** 200 JSON, 18 unpublished items across 12 content types
- **Standard API:** `/wp-json/wp/v2/posts?status=unpublish` returns 400
- **33 custom namespaces** exposed via `/wp-json/`
- **CWE:** CWE-862 (Missing Authorization)
- **Why it works:** Custom plugin namespaces bypass core WP permission checks
- **⚠️ TEMPORAL:** As of 2026-08-24 re-test, `unpublished-posts` now returns 0 items. Namespace and route still exist (2 routes in namespace). May have been patched during testing window. Custom plugin: google-analytics-for-wordpress, nasa-blocks, nasa-hds-core-setup.

### 2. mcdc.msfc.nasa.gov — CORS with Credentials (P3-P4)
- **Headers:** `Access-Control-Allow-Origin: *` + `Access-Control-Allow-Credentials: true`
- **Impact:** Any website can make authenticated cross-origin requests with cookies
- **Context:** Marshall Child Development Center (childcare site)
- **CWE:** CWE-942 (Permissive Cross-domain Policy)

### 3. mast.stsci.edu — CORS Wildcard (P4-P5)
- **Headers:** `Access-Control-Allow-Origin: *`
- **Context:** Space Telescope Science Institute API (public science data)
- **Impact:** Limited — data is public, but wildcard allows unrestricted cross-origin access

### 4. ames-test S3 Bucket — Public Data (P4-P5)
- **Bucket:** `ames-test` (S3)
- **Contents:** 2 objects including 11MB `.rds` file
- **Access:** Public without auth (listing accessible, 731 bytes)
- **Write test:** PUT returns 403 AccessDenied — bucket is READ-ONLY, not writable
- **CWE:** CWE-538 (Insertion of Sensitive Information into Externally-Accessible File)

### 5. nccs.nasa.gov — Login Enumeration + Content Exposure (P4-P5, SUPERSEDED by Finding #0)
- **Now covered by CORS critical finding (#0)** — the CORS reflection makes the user enum much worse
- **Legacy detail:** 3 valid usernames via login error differentiation, 95 posts/68 pages via WP REST API
- **Registration:** Shows form but blocked server-side ("registration currently not allowed")

### 6. Drupal install.php Accessible (P5)
- **Hosts:** standards.nasa.gov, esdpubs.nasa.gov, disasters.nasa.gov, airbornescience.nasa.gov
- **Result:** All return HTTP 200 with "Drupal already installed"
- **Impact:** Information disclosure only — no re-installation possible

### 7. images.nasa.gov — CORS Wildcard (P5, by-design)
- **Hosted:** S3 + CloudFront
- **Headers:** `Access-Control-Allow-Origin: *`
- **Impact:** Minimal — public image gallery

### 8. images-admin.nasa.gov — S3 CORS Wildcard (P5)
- **Headers:** `Access-Control-Allow-Origin: *`
- **Context:** S3 bucket with admin prefix (misleading name)

## Dismissed Findings (Not Reportable)

| Finding | Reason |
|---------|--------|
| ciencia.nasa.gov XMLRPC | Multicall broken (500), pingback disabled, rate limiting active |
| standards.nasa.gov Drupal 9 EOL | Excluded per VDP scope exclusions |
| espoarchive.nasa.gov Drupal 7 EOL | Flagged but no active exploit |
| solarsystem.nasa.gov /modules/contrib/ | FALSE POSITIVE — SPA catch-all, not real directory listing |
| images.nasa.gov CORS | By-design for public image gallery |
| swehb OGNL injection | FALSE POSITIVE — 500 is normal Confluence error |
| esdpubs JSONAPI | FALSE POSITIVE — returns HTML (text/html), not JSON |

## API Infrastructure Findings (Info Only)

| Target | Finding |
|--------|---------|
| cmr.earthdata.nasa.gov /search/health | Exposes internal infra: Oracle DB, Elasticsearch cluster |
| cmr.uat.earthdata.nasa.gov | Staging/UAT environment accessible without auth |
| gpm1.gesdisc.eosdis.nasa.gov | Data directory listing accessible |
| goldsmr5.gesdisc.eosdis.nasa.gov | Server accessible without auth |
| api.nasa.gov | CORS * on public API (by-design) |
| DEMO_KEY | Works on APOD, NEO, EPIC, FIRMS (by-design) |

## Testing Patterns Used

1. **CMR API:** Search without auth, granule search, health endpoint, UAT access
2. **CORS sweep:** Origin: evil.com on all data hosts
3. **S3 enumeration:** Guess bucket names, check public listing + PUT test
4. **Drupal install.php:** Test /core/install.php on all Drupal hosts
5. **WP REST API:** Namespace discovery, custom endpoint testing, author enum
6. **SPA detection:** Test random nonexistent path first → compare byte size for all subsequent paths
7. **Subdomain takeover:** DNS-over-HTTPS via `dns.google/resolve?name=X&type=CNAME`
8. **Focused deepdive:** 9-section structured approach (IDOR, sensitive files, S3 write, open redirect, author enum, CORS, subdomain takeover, GraphQL, plugins)

## CNAME Mapping (Subdomain Takeover Assessment)

| Host | CNAME | Provider | Takeover Risk |
|------|-------|----------|---------------|
| oig.nasa.gov | oig-nasa.go-vip.net | Pantheon | None (managed) |
| mcdc.msfc.nasa.gov | mcdcwp-prod.nasawestprime.com | NASA West Prime | None (internal) |
| disasters.nasa.gov | appliedsciences.nasa.gov | NASA internal | None |
| standards.nasa.gov | standards.nasawestprime.com | NASA West Prime | None (internal) |
| solarsystem.nasa.gov | solarsystem.jpl.nasa.gov | JPL internal | None |
| mars.nasa.gov | d2cj35nmzi9erd.cloudfront.net | AWS CloudFront | None |
| exoplanets.nasa.gov | exoplanets.jpl.nasa.gov | JPL internal | None |
| earthdata.nasa.gov | d3vpnmsr9g81nw.cloudfront.net | AWS CloudFront | None |
| www.nasa.gov | nasa-gov.go-vip.net | Pantheon | None (managed) |
| cmr.earthdata.nasa.gov | dgw1djqk2leao.cloudfront.net | AWS CloudFront | None |
| images.nasa.gov | images.nasawestprime.com | NASA West Prime | None (internal) |
| images-admin.nasa.gov | images-admin.nasawestprime.com | NASA West Prime | None (internal) |
| mast.stsci.edu | mast-cluster.stsci.edu | STScI internal | None |

**Result:** No subdomain takeover candidates — all CNAMEs point to managed infrastructure.

## Author Enum Results (2026-08-24)

All 6 NASA WP hosts tested (`?author=1` through `?author=5`): **zero redirects, zero results.** Gov sites have author archives disabled. This vector is not viable on NASA WP sites.

## Key False Positive Patterns

1. **SPA catch-all:** All paths return HTTP 200 with identical body size → not real file exposure
2. **Drupal JSONAPI:** Returns 200 but Content-Type is text/html → catch-all routing, not data leak
3. **Confluence .action:** ALL .action paths return 500 → action mapper error, not OGNL injection
4. **Confluence 500:** Normal error handling, not exploitation indicator
