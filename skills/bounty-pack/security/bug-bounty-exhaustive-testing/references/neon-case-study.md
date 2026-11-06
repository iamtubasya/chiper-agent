# Neon (neon.tech) — Well-Hardened SaaS Case Study (Sep 2026)

## Target
- **Company:** Neon (neon.tech) — Cloud-native PostgreSQL
- **Program:** HackerOne neon_bbp ($150-$5,000 bounty range)
- **Type:** Web SaaS + API (Keycloak auth, Cloudflare WAF)

## Attack Surface
- 1,086 subdomains (subfinder)
- 548 live hosts (httpx)
- 11 in-scope assets: console, API v2, staging, preview, extensions

## Tools Executed (15 tools, real terminal output)
| Tool | Result |
|------|--------|
| subfinder | 1,086 subdomains |
| httpx | 548 live hosts |
| nuclei | 6 findings: TLS 1.0/1.1 weak ciphers on superset, track, static |
| ffuf | .git/.env=403, /admin=CF Access, /healthz=200 |
| dalfox | 0 XSS (CSP strict-dynamic) |
| katana | 19K+ neon.com URLs, WebAuthn JS endpoints |
| gau | 98,193 historical URLs (internal Azure endpoints unreachable) |
| waybackurls | URLs collected |
| **naabu** | **Port 8080 OPEN on console.neon.tech + oauth2.neon.tech** |
| arjun | 0 hidden params |
| kxss | 0 XSS reflections |
| commix | No injectable params |
| gobuster | /admin=CF Access, /healthz=200, /login=307 |
| poc-pipeline | 16 repos matched + 101 nuclei templates |
| CVE exploits | 6 tested, all not vulnerable |

### New Tools From This Session
- **naabu** — Critical discovery: port 8080 open on console + oauth2 (Keycloak origin direct access, bypasses Cloudflare WAF)
- **gobuster** — Confirmed /admin behind Cloudflare Access with `kid` token
- **poc-compact** — Searched 2,223 repos (see POC-COMPACT section below)
- **CVE-2025-29927** — Next.js middleware bypass via `x-middleware-subrequest` header (test method below)

## CVE Exploits Tested (6 total, Real Tools)
1. **CVE-2025-55182 (React2Shell RCE CVSS 10.0)** — Cloned exploit repo, installed deps, ran scan → NOT VULNERABLE (React patched)
2. **CVE-2026-1529 (Keycloak org registration)** — Tested client registration + device code + CIBA + client credentials → BLOCKED by Trusted Hosts policy + unauthorized_client
3. **CVE-2023-27524 (Superset default key)** — Python HMAC forging of 12 default keys → NOT VULNERABLE (non-default key)
4. **CVE-2025-29927 (Next.js middleware bypass)** — `x-middleware-subrequest: true` header test → NOT VULNERABLE (neon.com on Vercel, patched)
5. **CVE-2025-59470 (PostgreSQL cmd inject)** — POC-COMPACT dir empty (no exploit code) → NOT APPLICABLE
6. **CVE-2026-11102 (OAuth2 implicit grant hijack)** — POC-COMPACT dir empty → NOT APPLICABLE

## CVE-2025-29927 Test Method (Next.js Middleware Bypass)
```bash
# Detection: check for Next.js + middleware headers
curl -sI "https://TARGET" | grep -iE "x-nextjs|x-middleware|server"
# neon.com: Server: Vercel (Next.js confirmed)

# Exploit: send x-middleware-subrequest header to skip middleware
curl -sL -H "x-middleware-subrequest: true" "https://TARGET/admin" 
# Result: 404 (patched or no middleware auth)

# Also test with bypass header value variants
for h in "true" "1" "page" "routes" "middleware"; do
  curl -sL -o /dev/null -w "%{http_code}" -H "x-middleware-subrequest: $h" "https://TARGET/dashboard"
done
```

## Port 8080 Direct Access (Defense-in-Depth Working)
naabu found port 8080 open on console.neon.tech and oauth2.neon.tech.
- Port 8080 serves Keycloak login page directly (no Cloudflare WAF)
- Password brute force: FAILED (10 common passwords, both master + prod-realm)
- Client registration: BLOCKED by Trusted Hosts policy (same as via Cloudflare)
- Lesson: Keycloak's Trusted Hosts policy is enforced at application layer, not WAF layer

## POC-COMPACT: 2,223 Dirs, 0 Files
```
D:/data/hermes/poc-compact/
├── manifest.json (empty or missing)
├── 007bsd_ml-kem-key-recovery/  (empty)
├── 0xlyvio_CVE-2026-1529-.../  (empty)
├── ... (2,223 empty directories)
└── 0 Total files found
```
**The poc-compact directories exist but contain NO exploit code.** The repos were not actually downloaded. poc-pipeline.py matched repos separately (16 repos), which is the correct workflow — it clones from GitHub directly, not from poc-compact.

**Lesson:** Do NOT assume poc-compact has content. Verify with `find D:/data/hermes/poc-compact -type f | wc -l` before relying on it.

## User Correction: "Jgn kasih hasil teoritis"
The agent initially presented 5 "findings" (Superset config leak, Keycloak OIDC config, Teleport version, etc.) as Medium severity bounty candidates. User correctly rejected ALL of them:

**"Jgn kasih hasil teoritis, kasih impact yg beneran berdampak"** — Don't give theoretical results, give impact that actually damages.

**"Apa efeknya? Harus jelas merugikan br kamu jadikan temuan"** — What's the effect? Must clearly harm before you call it a finding.

**The truth:** Every "finding" was either:
- By-design (OIDC config is public per spec, Superset config hydrates UI)
- Informational (version disclosure, no exploit chain)
- Blocked by security controls (Cloudflare Access, auth enforcement)

**The rule:** If you can't demonstrate REAL HARM (data access, account takeover, financial loss, RCE) with a reproducible PoC, it's NOT a finding. Period.

## What "Exhausted" Looks Like on a Well-Hardened SaaS
Indicators observed:
- Cloudflare WAF + Access blocks all admin/internal paths
- Keycloak properly validates redirect_uri (15 bypass techniques failed)
- All API endpoints require auth (401 on every HTTP method)
- CVE exploits fail (patched/mitigated)
- No dangling CNAMEs for subdomain takeover
- No CORS misconfigurations
- Rate limiting in place
- 98K historical URLs from gau → zero exploitable

**Honest conclusion:** "Exhausted — zero bounty-worthy findings."

## Key Lesson
Some targets are genuinely well-hardened. After 12 tools, 30 vectors, 3 CVEs, 98K URLs, and 7 skills loaded — zero findings is a valid outcome. Do NOT force findings to look productive. Severity inflation wastes everyone's time.

## Neon-Specific Infrastructure Notes
- Auth: Keycloak (prod-realm) with GitHub/Google/Microsoft/Hasura SSO
- WAF: Cloudflare on all domains
- Teleport: v18.7.4 Enterprise (K8s proxy, SSH, MySQL proxy)
- Superset: v5.0.0 (config leak by design)
- API: v2 with proper auth (401 on all endpoints)
- MCP Server: v1.0.0 on Vercel
