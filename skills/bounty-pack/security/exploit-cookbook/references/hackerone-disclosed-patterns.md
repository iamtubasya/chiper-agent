# HackerOne Disclosed Report Patterns — 2026
> Source: reddelexc/hackerone-reports, ajaysenr/HackerOne-Disclosed-Reports, pwnpanda/Bug_Bounty_Reports
> Safety: ✅ All repos verified clean (data files only)

## Top Vuln Classes in 2026 HackerOne Disclosures

### 1. IDOR / BOLA (Most Common)
- **Pattern:** `/api/v1/users/{OTHER_USER_ID}` without authz check
- **Bypass:** UUID prediction, sequential IDs, encoded IDs, base64 manipulation
- **Testing:** Change user ID in request → check if other user's data returned
- **Tool:** `curl -H "Authorization: Bearer $TOKEN" https://target.com/api/v1/users/ATTACKER_ID`

### 2. SSRF (Highest Impact)
- **Pattern:** URL parameter → server fetches internal resources
- **Bypass:** IPv6, DNS rebinding, redirect chains, encoded URLs
- **Cloud pivot:** `http://169.254.169.254/latest/meta-data/` (AWS), `http://metadata.google.internal/` (GCP)
- **Tool:** `curl -x http://BurpCollab.net http://target.com/fetch?url=http://169.254.169.254/`

### 3. XSS (Most Frequent)
- **Pattern:** User input reflected without sanitization
- **Bypass:** DOMPurify bypass, SVG mXSS, event handler injection
- **Technique:** Test in HTML attributes, JS contexts, CSS, SVG, URL params
- **Tool:** `dalfox url "https://target.com/page?q=test" --skip-bav`

### 4. SQLi (High Bounty)
- **Pattern:** User input in SQL query without parameterization
- **Bypass:** WAF bypass via tamper scripts, unicode normalization, double encoding
- **Technique:** Union-based → extract data, blind → time-based confirmation
- **Tool:** `sqlmap -u "https://target.com/page?id=1" --batch --risk=3 --level=5`

### 5. Authentication Bypass
- **Pattern:** OAuth misconfiguration, JWT validation gap, session fixation
- **Technique:** Token manipulation, cookie injection, redirect URI validation bypass
- **Testing:** Test password reset flow, OAuth callback, JWT `none` algorithm

### 6. Business Logic Flaws
- **Pattern:** Price manipulation, quantity overflow, race conditions
- **Technique:** Negative quantities, decimal prices, concurrent requests
- **Testing:** Intercept → modify → replay → observe server response

### 7. Information Disclosure
- **Pattern:** Verbose error messages, debug endpoints, source code leaks
- **Technique:** `.git/config`, `.env`, `/debug`, `/actuator`, stack traces
- **Tool:** `gau target.com | grep -E '\.(git|env|debug)'`

## Bounty Ranges (2026)
| Severity | Avg Bounty | Typical Finding |
|----------|-----------|-----------------|
| Critical | $10K-$100K | RCE, SSRF→RCE, Auth Bypass |
| High | $5K-$10K | SQLi, IDOR (sensitive data), SSRF |
| Medium | $1K-$5K | XSS, CSRF, Information Disclosure |
| Low | $100-$1K | Clickjacking, Missing Headers |

## Disclosed Report Repos
| Repo | Content |
|------|---------|
| `reddelexc/hackerone-reports` | Raw data.csv with 1000+ reports, Python scraper |
| `ajaysenr/HackerOne-Disclosed-Reports` | Dashboard: filter by severity, year, bounty, CVE |
| `pwnpanda/Bug_Bounty_Reports` | Curated reports since 2020 |
| `termireum/bugpedia` | Hand-picked writeups library |
| `hack-dex.com` | Community writeup directory |
| `bugbountyhunt.com/cve` | Daily CVE+PoC for hunters |
