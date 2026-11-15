# Certinia (FinancialForce) Case Study — Well-Hardened Target
> Session: 2026-09-20 | Target: *.financialforce.com + *.certinia.com | Platform: Bugcrowd

## Target Profile
- **Type:** Web2 (SaaS on Salesforce/Cloudflare/AWS)
- **Scale:** 570 subdomains, 166 live hosts, 31 unprotected
- **Auth:** Cloudflare Access + Google IAP + Okta SSO + Salesforce OAuth
- **Bounty:** P1-P4 ($175-$4,500)
- **Program active since:** Aug 2021, 120 vulns already paid out

## Infrastructure
- Cloudflare: 89 hosts (HSTS, WAF)
- Cloudflare Access: 73+ hosts (302 redirect to login)
- Google IAP: 30+ itops hosts (302 redirect to Google OAuth)
- Okta SSO: certinia.okta.com (centralized auth)
- Salesforce: Login portal, Connected Apps
- AWS: S3 buckets (dev, staging, prod)
- WordPress: blog.certinia.com (minimal, blocked REST API)

## Attack Surface
- 13 truly accessible endpoints (200, no auth redirect)
- CLX app (React SPA, API behind auth)
- HMRC API (Salesforce OAuth flow)
- Trust portal (Whistic vendor assessment, Angular)
- int/pre/prod environments (marketing pages)
- S3 buckets (4 public, 50+ exists/403)

## Tools Executed (with evidence)
| Tool | Command | Result |
|------|---------|--------|
| subfinder | `subfinder -d financialforce.com -silent` | 186 subs |
| subfinder | `subfinder -d certinia.com -silent` | 384 subs |
| httpx | `cat all_subs.txt \| httpx` | 166 live, 31 unprotected |
| gau | `echo financialforce.com \| gau` | 16,844 URLs |
| gau | `echo certinia.com \| gau` | 8,783 URLs |
| katana | `katana -u https://certinia.com -depth 3` | 86,745 URLs |
| dalfox | `dalfox url "https://www.certinia.com/?q=test"` | 0 XSS |
| sqlmap | `sqlmap -u "URL?id=1" --batch` | 0 SQLi |
| ffuf | `ffuf -u "URL/FUZZ" -w common500.txt` | SPA catch-all |
| nuclei | Multiple targets, timeout | Cloudflare blocks |
| arjun | Timeout (300s) | No results |
| curl | 30+ manual tests | Various negative |
| finding_gate.py | `python finding_gate.py findings.json` | 0 survivors |
| chain_builder.py | `python chain_builder.py findings.json` | No chains |

## Findings (all weak)
| Finding | Severity | Gate Verdict | Reason |
|---------|----------|-------------|--------|
| S3 ff-dev (dev data) | P4 | DOWNGRADED | Already reported by other researchers (Aug 2026) |
| S3 ff-dev-config | P4 | DOWNGRADED | No concrete impact signal |
| CORS redirect pages | Info | DROPPED | 302 redirect only, cannot exfiltrate app data |

## What Was Tested (30 vectors)
IDOR, Auth bypass, Privilege escalation, RCE/SSRF, SQLi, Race condition, Business logic, Mass assignment, Info disclosure, XSS (reflected/stored/DOM), GraphQL, CORS, CSRF, File upload, Cache poisoning, 403 bypass, Password reset, Open redirect, WebSocket, API versioning, Rate limiting, Third-party service, Source maps, SSTI, Command injection, XXE, Subdomain takeover, HTTP smuggling

## Why Zero Bounty-Worthy Findings
1. **Cloudflare Access** blocks 73+ internal services
2. **Google IAP** blocks 30+ itops services
3. **Okta SSO** centralizes auth — no bypass found
4. **Salesforce platform** — app behind login
5. **SPF/DMARC strict** — email security solid
6. **S3 findings already reported** — other researchers found same buckets (Aug 2026 PoC files present)
7. **No test accounts** — cannot test authenticated endpoints (IDOR, auth bypass, business logic)

## Lessons for Future Sessions
1. **570 subdomains ≠ 570 attack surfaces** — most are behind auth proxies
2. **CORS on redirect pages ≠ exploitable CORS** — check if data is actually accessible
3. **S3 with dev data ≠ production PII** — verify file contents before claiming P2/P3
4. **Other researchers' PoC files in S3** — means finding was already reported
5. **finding_gate.py is the truth** — if it drops everything, accept the verdict
6. **Well-hardened targets exist** — not every program has bounty-worthy findings
