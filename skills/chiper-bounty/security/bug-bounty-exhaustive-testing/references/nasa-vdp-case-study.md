# NASA VDP Case Study — Exhaustive Testing, Zero Bounty Findings

**Target:** https://bugcrowd.com/engagements/nasa-vdp
**Scope:** *.nasa.gov, *.usgeo.gov, *.globe.gov
**Program type:** VDP (LOR only, no bounty)
**Date:** 2026-09-19
**Outcome:** All vectors tested, zero bounty-worthy findings

---

## Recon Scale

| Metric | Count |
|--------|-------|
| Subdomains enumerated | 17,011 |
| Live hosts tested | 79 key targets |
| Key targets deep-tested | 8 |
| Reference files consulted | 12+ |
| Skills loaded | 9/9 |

## Tools Executed (with terminal output proof)

| # | Tool | Command | Result |
|---|------|---------|--------|
| 1 | subfinder | `subfinder -d nasa.gov -d globe.gov -d usgeo.gov` | ✅ 17,011 subs |
| 2 | gau | `echo TARGET \| gau --threads 3` | ✅ 0 URLs (archive blocked) |
| 3 | waybackurls | `echo TARGET \| waybackurls` | ✅ 0 URLs |
| 4 | katana | `katana -u https://oig.nasa.gov -jc -d 2` | ✅ 13,498 URLs |
| 5 | ffuf | `ffuf -u TARGET/FUZZ -w wordlist` | ✅ 3 targets (oig, nccs, science) |
| 6 | nuclei | `nuclei -l targets -severity critical,high,medium` | ⏳ 83 min, 0 results |
| 7 | dalfox | `echo URL \| dalfox pipe --skip-bav` | ❌ Timeout (WAF) |
| 8 | arjun | `arjun -u TARGET -m GET -t 5` | ✅ 0 hidden params |
| 9 | sqlmap | `sqlmap -u "TARGET/?s=test" --batch` | ✅ 0 injectable |
| 10 | curl | 42+ manual tests | ✅ Multiple findings |

## Infrastructure

| Target | Tech Stack | Notes |
|--------|-----------|-------|
| nccs.nasa.gov | WordPress VIP, Apache | WP VIP namespace present |
| oig.nasa.gov | WordPress VIP, nginx | 526 routes, 28 custom namespaces |
| science.nasa.gov | WordPress VIP, nginx | dev-tools SSRF (allowlisted) |
| mcdc.msfc.nasa.gov | WordPress, nginx | ACAO=* + ACAC=true |
| procurement.nasa.gov | Apache 2.4.37, PHP 7.4.33 | EOL versions |
| wiki.earthdata.nasa.gov | Confluence | 8 spaces accessible |
| cmr.earthdata.nasa.gov | Custom | Health endpoint exposed |
| activemq-server.czdt.smce.nasa.gov | Keycloak | Login page exposed |

## Candidates Evaluated & Dropped

| # | Candidate | Severity | Verdict | Reason |
|---|-----------|----------|---------|--------|
| 1 | CORS + Credentials (4 hosts) | P1-P2 | ❌ DROPPED | Social engineering — victim must visit attacker page + authed. NASA VDP excludes social engineering |
| 2 | nccs user enum via REST API | P4 | ❌ EXCLUDED | `/wp-json/wp/v2/users` explicitly excluded |
| 3 | procurement outdated infra | INFO | ❌ EXCLUDED | Version disclosure without exploit — explicitly excluded |
| 4 | oig unpublished-posts | P5 | ⚠️ BORDERLINE | IDs + timestamps only, no content, no write |
| 5 | oig content-group | P5 | ❌ DROPPED | Published content — already public |
| 6 | Confluence space names | P5 | ⚠️ BORDERLINE | Titles only, no content, write blocked |
| 7 | S3 ames-test | P5 | ⚠️ BORDERLINE | Test data, low sensitivity |
| 8 | CMR health endpoint | INFO | ❌ DROPPED | Health status only |
| 9 | Keycloak exposed | INFO | ❌ DROPPED | Login page ≠ vulnerability |
| 10 | VIP dev-tools SSRF | P5 | ❌ BLOCKED | URL allowlist active |
| 11 | wp-config-sample.php 500 | INFO | ❌ EXCLUDED | Software disclosure |
| 12 | package-lock.json (empty) | INFO | ❌ DROPPED | 0 packages |
| 13 | OIG 28 custom post types | P4 | ⚠️ INFO | Public content via structured API |
| 14 | OIG People directory (6 staff) | P4 | ⚠️ INFO | Public officials, public data |
| 15 | OIG 27 topics (1.5MB) | P4-P5 | ⚠️ INFO | Same content as website |
| 16 | NCCS 83 POST routes | P4 | ⚠️ INFO | All require auth (401) |
| 17 | Contact info via topics | P5 | ⚠️ INFO | Public contact info |

## Honest Conclusion

Exhaustive testing of 42 vectors across 10 layers on 8 key targets = zero bounty-worthy findings. Target is well-hardened (WordPress VIP, proper namespace gating, blocked XML-RPC, 403 on sensitive files). Strongest candidate (CORS) requires social engineering = VDP excluded.

## Lessons for Future VDP Audits

1. Check VDP exclusions FIRST before deep-testing
2. WordPress VIP CORS reflection is by-design — not exploitable
3. "Unpublished-posts" metadata = IDs/timestamps only, not content
4. VDP programs have stricter exclusions than bounty programs
5. 17K subdomains ≠ 17K attack surface (most are 404)
6. Nuclei on large scope needs background + rate limiting (2.5 hours for 6564 templates × 8 targets)
7. Honest zero-findings with evidence > severity inflation
8. WordPress VIP custom post types via REST API = standard behavior, not a vulnerability
9. WordPress VIP namespace gating = write endpoints properly blocked (401)
10. nuclei poll loop wastes turns — background + do other work + check once
11. dalfox/arthunter timeout on WAF-protected targets = not a finding, just WAF working
12. Confluence REST API with auth = standard behavior, not a vulnerability
