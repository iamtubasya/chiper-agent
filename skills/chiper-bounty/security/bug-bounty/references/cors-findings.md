# CORS Misconfiguration — Finding Assessment Guide

## Overview

CORS (Cross-Origin Resource Sharing) misconfigurations are one of the most common findings in bug bounty, but also one of the most over-reported. Many CORS findings are rejected because they're either by-design or not actually exploitable.

## Common CORS Patterns

### 1. Origin Reflection (Most Common)
```
Request:  Origin: https://evil.com
Response: Access-Control-Allow-Origin: https://evil.com
          Access-Control-Allow-Credentials: true
```
**Assessment**: If session cookies are HttpOnly → NOT exploitable for session theft. But check: (a) Bearer tokens in JS memory/localStorage, (b) token endpoint CORS for refresh chains, (c) Authorization header allowed in CORS headers.

### 1c. WordPress REST API CORS — Full Attack Chain (P1-P2 CRITICAL)
**Session: NASA 2026-09 — verified across 3 live WordPress hosts.**

**Why WordPress CORS is uniquely dangerous:**
WordPress uses `application/json` content type + cookie-based auth (`X-WP-Nonce`). When CORS reflects ANY origin with credentials + write methods + nonce header allowed, the full attack chain is:
1. Attacker hosts page on evil.com
2. Victim (authenticated WordPress user) visits evil.com
3. JS reads user data (posts, pages, authors, media) cross-origin
4. JS extracts `X-WP-Nonce` from cookie (accessible in JS, not HttpOnly)
5. JS makes authenticated POST/PUT/DELETE requests (create posts, modify content, delete data)
6. Full WordPress compromise without touching the server

**Detection — REST API namespace discovery:**
```bash
# Step 1: Enumerate ALL namespaces (key for finding custom plugin endpoints)
curl -s "https://TARGET/wp-json/" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for n in d.get('namespaces', []):
    print(n)
"

# Step 2: CORS reflection test on REST API root
curl -sD- -o /dev/null "https://TARGET/wp-json/" \
  -H "Origin: https://evil.com"

# Step 3: Verify critical headers
# Access-Control-Allow-Origin: https://evil.com (reflected!)
# Access-Control-Allow-Credentials: true (cookies sent!)
# Access-Control-Allow-Methods: OPTIONS, GET, POST, PUT, PATCH, DELETE (write methods!)
# Access-Control-Allow-Headers: Authorization, X-WP-Nonce, Content-Type (nonce allowed!)
```

**Impact when ALL headers are present:**
- **GET** → Read all content (posts, pages, media, authors) cross-origin
- **X-WP-Nonce allowed** → Attacker can extract nonce from cookie and make authenticated POST/PUT/DELETE
- **POST/PUT/DELETE allowed** → Attacker can create/modify/delete content cross-origin
- **Author enumeration** → Extract user emails, display names, avatars

**CVSS escalation factors:**
| Factor | Impact on Severity |
|--------|-------------------|
| `X-WP-Nonce` in Allow-Headers | +1 level (enables write operations) |
| `POST/PUT/DELETE` in Allow-Methods | +1 level (write access, not just read) |
| WordPress cookie auth (not HttpOnly) | +1 level (nonce accessible from JS) |
| Custom plugin endpoints exposed | +0.5 level (less reviewed than core) |
| SSO/ADFS cookies (federated identity) | +2 levels (steals enterprise identity) |

**Minimum CVSS for WordPress CORS + ACAC + write methods:**
- `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N` — Score: 8.1 (HIGH)
- If SSO/ADFS (federated): +CRITICAL (identity theft, not just data)

**Testing methodology (WordPress-specific):**
```bash
# 1. Root namespace (verifies CORS on REST API)
curl -sD- -o /dev/null "https://TARGET/wp-json/" -H "Origin: https://evil.com"

# 2. Author enumeration (data leak)
curl -s "https://TARGET/wp-json/wp/v2/users" | python3 -c "
import sys, json
for u in json.load(sys.stdin):
    print(f\"{u.get('slug')} | {u.get('name')} | {u.get('link')}\")
"

# 3. Content enumeration (posts, pages, media)
for type in post page media; do
  curl -s "https://TARGET/wp-json/wp/v2/${type}?per_page=3" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'${type}: {len(d)} items')
"
done

# 4. Custom namespace enumeration (THE real finding)
curl -s "https://TARGET/wp-json/" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for ns in d.get('namespaces', []):
    if not ns.startswith('wp/v2'):
        print(f'CUSTOM: {ns}')
"

# 5. Full CORS header check on POST endpoint
curl -sD- -o /dev/null -X POST "https://TARGET/wp-json/wp/v2/posts" \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/json" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization, X-WP-Nonce"
```

**False positive check (MANDATORY):**
- Is `X-WP-Nonce` actually in `Access-Control-Allow-Headers`? If NO → attacker can't make authenticated requests → severity drops to P4-P5 (read-only data leak)
- Are write methods (POST/PUT/DELETE) actually in `Access-Control-Allow-Methods`? If NO → attacker can only read, not write
- Are custom endpoints auth-protected (401/403)? If YES → less impact (but read-only CORS still leaks data)

### 1b. Origin Reflection — Extended Testing (ALWAYS do all 5)
```bash
# Standard reflection
curl -sI -H "Origin: https://evil.com" "https://TARGET/endpoint"
# → ACAO: https://evil.com

# Test 2: null origin (sandboxed iframe — no Origin header sent)
curl -sI -H "Origin: null" "https://TARGET/endpoint"
# → ACAO: null = exploitable via <iframe sandbox="allow-scripts">

# Test 3: HTTP origin (not HTTPS — mixed content bypass)
curl -sI -H "Origin: http://evil.com" "https://TARGET/endpoint"
# → ACAO: http://evil.com = exploitable from HTTP pages

# Test 4: Random text (not a valid origin at all)
curl -sI -H "Origin: foobar123" "https://TARGET/endpoint"
# → ACAO: foobar123 = server blindly reflects ANY value

# Test 5: Subdomain of target
curl -sI -H "Origin: https://evil.TARGET.com" "https://TARGET/endpoint"
# → ACAO: https://evil.TARGET.com = subdomain takeover vector
```
**Severity escalation**: If null + HTTP + random ALL work → server has NO origin validation at all → higher confidence in exploitability.

### 2. Wildcard Origin
```
Response: Access-Control-Allow-Origin: *
          Access-Control-Allow-Credentials: true
```
**Assessment**: Browsers block `*` with credentials. This is actually SECURE (browsers ignore the wildcard). NOT a finding.

### 3. Null Origin
```
Request:  Origin: null
Response: Access-Control-Allow-Origin: null
          Access-Control-Allow-Credentials: true
```
**Assessment**: Exploitable via sandboxed iframe or local HTML file. MEDIUM if sensitive endpoints exist.

### 4. Subdomain Wildcard
```
Response: Access-Control-Allow-Origin: *.target.com
          Access-Control-Allow-Credentials: true
```
**Assessment**: Exploitable if attacker can control any subdomain (XSS, subdomain takeover). MEDIUM-HIGH depending on endpoints.

## Exploitability Checklist (MANDATORY before claiming severity)

### Step 1: Cookie Analysis
```
□ What session cookies does the target set?
□ Are they HttpOnly? → If YES, JavaScript CANNOT read them → CORS NOT exploitable for session theft
□ Are they SameSite=None? → If YES, they WILL be sent cross-origin (but still can't read if HttpOnly)
□ Are they stored in localStorage/sessionStorage? → If YES, CORS CAN steal them (Bearer token scenario)
```

### Step 2: Data Exfiltration Proof
```
□ Can you actually READ sensitive data via CORS (not just get empty 401)?
□ Does the endpoint return user data on valid auth?
□ Can you demonstrate data theft with a real attack scenario (HTML page)?
```

### Step 3: Compensating Controls
```
□ Does the app use Bearer tokens in headers (vulnerable) vs HttpOnly cookies (not vulnerable)?
□ Is there CSRF protection that blocks cross-origin state changes?
□ Does the app use SameSite=Strict/Lax cookies?
```

## Severity Classification (UPDATED)

| Scenario | Severity | Reasoning |
|----------|----------|-----------|
| CORS + HttpOnly cookies + GET endpoints only | P4-P5 | Cannot steal sessions (cookies hidden from JS) |
| CORS + HttpOnly cookies + token/POST endpoint | P3 | Enables cross-origin token refresh (attacker needs stolen refresh token) |
| CORS + localStorage tokens + sensitive endpoints | P2-P3 | Can steal Bearer tokens via XSS + CORS |
| CORS + null origin + no sensitive endpoints | P5 | Exploitable but no impact |
| CORS + null origin + token endpoint + POST | P3 | iframe can POST to refresh tokens |
| CORS + wildcard + credentials | NOT A VULN | Browsers block this by design |
| CORS + subdomain control + admin endpoints | P2-P3 | Chain with subdomain takeover/XSS |
| CORS reflects ANY value (random text, HTTP, null) | Higher confidence | Server has zero origin validation — amplify severity by 0.5-1 level |

## Real-World Case Studies

### Bitso (2026-08) — CORS on Keycloak OIDC (UPDATED)
```
Request:  Origin: https://evil.com
Response: Access-Control-Allow-Origin: https://evil.com
          Access-Control-Allow-Credentials: true
```
**Affected endpoints (ALL reflect ANY origin):**
- `/.well-known/openid-configuration` — OIDC config leak
- `/protocol/openid-connect/certs` — Public key enumeration
- `/protocol/openid-connect/userinfo` — User data theft (requires Bearer token)
- `/protocol/openid-connect/token` — **Token refresh/exchange from any origin** (POST allowed!)
- `/protocol/openid-connect/token/introspect` — Token validation
- `/protocol/openid-connect/logout` — Session hijacking

**Exploitability analysis (corrected):**
- Session cookies: `ISTIO_AUTH_SESSION_ID` (HttpOnly), `__cf_bm` (HttpOnly, SameSite=None)
- **NOT vulnerable to direct session theft** (HttpOnly cookies)
- **BUT vulnerable to:**
  1. **Cross-origin token refresh**: Attacker with refresh token can silently refresh from any website
  2. **User data theft**: Attacker with stolen Bearer token can read userinfo cross-origin
  3. **XSS amplification**: Any minor XSS becomes full account takeover via CORS
  4. **Token introspection**: Attacker can validate stolen tokens cross-origin
- Token endpoint CORS allows `Authorization` header cross-origin (via `access-control-allow-headers`)
- Origin reflection works with: HTTPS, HTTP, `null`, random text (not just valid domains)

**Corrected verdict**: **MEDIUM (P3)** — Not P1-P2 because session cookies are HttpOnly. But real exploitation chain exists: XSS → steal refresh token → CORS refresh → persistent account access.

### Typical IDOR + CORS Chain (HIGH)
```
1. CORS reflects evil.com with credentials
2. User visits attacker page
3. Attacker reads user's Bearer token from response (if stored in memory/localStorage)
4. Attacker uses token to access IDOR endpoint
5. Attacker reads other users' data
```
**Verdict**: P2-P3 (requires chaining + proof of data exfiltration).

## Testing Methodology

### ⚠️ CRITICAL PITFALLS

**1. `curl -sI` (HEAD) may miss CORS headers — always use `-sD-`:**
Keycloak and other CORS middleware may only add headers on GET/POST, not HEAD.
```bash
# ❌ WRONG — may return NO CORS headers
curl -sI -H "Origin: https://evil.com" "https://TARGET/endpoint"

# ✅ CORRECT — captures all response headers
curl -sD- -o /dev/null -H "Origin: https://evil.com" "https://TARGET/endpoint" | grep -iE "access-control"
```

**2. Browser `fetch()` CANNOT spoof Origin header — must host PoC on attacker domain:**
```html
<!-- ❌ WRONG — browser ignores your Origin, sends page's actual origin -->
<script>
fetch('https://TARGET/endpoint', { headers: {'Origin': 'evil.com'} })
</script>

<!-- ✅ CORRECT — host on evil.com, browser sends Origin: evil.com automatically -->
<script>
fetch('/endpoint').then(r => console.log(r.headers.get('Access-Control-Allow-Origin')))
</script>
```
Use curl/Python for proof-of-concept. Browser PoC only works when hosted on attacker domain.

**3. Test ALL 5 origin variations (do NOT stop at standard HTTPS):**
```bash
# Standard HTTPS
curl -sD- -o /dev/null "https://TARGET/endpoint" -H "Origin: https://evil.com"
# Null (sandboxed iframe)
curl -sD- -o /dev/null "https://TARGET/endpoint" -H "Origin: null"
# HTTP (mixed content bypass)
curl -sD- -o /dev/null "https://TARGET/endpoint" -H "Origin: http://evil.com"
# Random text (no validation = worse)
curl -sD- -o /dev/null "https://TARGET/endpoint" -H "Origin: foobar123"
# Subdomain
curl -sD- -o /dev/null "https://TARGET/endpoint" -H "Origin: https://evil.TARGET.com"
```
If ALL 5 work → server has ZERO origin validation → higher confidence.

### 1. Identify CORS Behavior
```bash
# Test basic reflection
curl -s -D- -o /dev/null "https://target.com/api/userinfo" \
  -H "Origin: https://evil.com"

# Test with credentials
curl -s -D- -o /dev/null "https://target.com/api/userinfo" \
  -H "Origin: https://evil.com" \
  -H "Cookie: session=fake_token"
```

### 2. Analyze Cookie Attributes
```bash
# Check Set-Cookie headers
curl -s -D- "https://target.com/login" \
  -d "user=test&pass=test" \
  | grep -i "set-cookie"
```

### 3. Check for Bearer Token Storage
```bash
# Search JS for localStorage/sessionStorage usage
curl -s "https://target.com" | grep -oE '(localStorage|sessionStorage)\.[a-z]+Token[^;]+'
```

## CORS on Blockchain RPC / JSON-RPC Endpoints (Non-Traditional Data)

Standard CORS analysis focuses on cookies and session tokens, but blockchain RPC endpoints expose a different data class: token balances, wallet addresses, transaction history, and protocol state. These endpoints typically use header-based auth (API keys, Bearer tokens) rather than cookies.

### Pattern: Solana RPC CORS Misconfiguration
```
Request:  Origin: https://evil.com
Response: Access-Control-Allow-Origin: https://evil.com
          Access-Control-Allow-Credentials: true
          Access-Control-Allow-Headers: Content-Type, Authorization
```

**Why this matters:**
- Solana RPC endpoints (e.g., `aurory.rpcpool.com`, `rpc.*.aurory.io`) often serve as the primary data layer for blockchain games/dApps
- They accept `Authorization` headers — which can contain wallet-signing tokens or API keys
- Reflecting any origin means any malicious website can make authenticated RPC calls
- Data exposed: wallet balances, token holdings, game state, validator info, transaction history

**Severity escalation path:**
| Scenario | Severity | Reasoning |
|----------|----------|-----------|
| RPC reflects origin, no auth required, public data only | P4-P5 | Public blockchain data — low sensitivity |
| RPC reflects origin, API key/Bearer auth, returns wallet data | P2-P3 | Attacker reads user wallet balances, game state |
| RPC reflects origin + allows Authorization header + rate-limited endpoints | P2 | Full cross-origin access to authenticated RPC calls |
| RPC reflects origin + private/permissioned endpoints | P1-P2 | Access to restricted blockchain operations |

**Testing methodology (distinct from cookie-based CORS):**
```bash
# 1. Identify RPC endpoints from CSP connect-src or JS bundles
curl -sI "https://target.com/" | grep -i content-security-policy | \
  grep -oE 'connect-src[^;]+' | grep -oE 'https?://[a-zA-Z0-9._-]+' | sort -u

# 2. Test CORS on each RPC endpoint (no cookies — test header-based auth)
curl -s -D- -o /dev/null "https://rpc.target.com/" \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"getSlot","id":1}'

# 3. If CORS reflects, test with Authorization header allowed
curl -s -D- "https://rpc.target.com/" \
  -H "Origin: https://evil.com" \
  -H "Authorization: Bearer fake_token" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"getSlot","id":1}'

# 4. Check what data is accessible without auth (getSlot, getClusterNodes, getTokenAccountBalance)
# 5. If auth works, test what additional methods become available
```

**Key insight:** Traditional CORS severity relies on "can I steal session cookies?" — for RPC endpoints, the question is "can I read sensitive blockchain state cross-origin?" The answer is often yes, because RPC endpoints are designed for programmatic access, not browser same-origin policies.

**Aurory case study (2026-08):**
- `aurory.rpcpool.com` (production): reflects ANY origin, allows Authorization header
- `rpc.aurorynet.dev.aurory.io` (dev): same issue + fully unauthenticated, exposed validator info
- Impact: any website can read Aurory's Solana game data cross-origin
- Severity: P2 (data access from unauthorized origin) to P3 (data is partially public blockchain state)

## CORS on Token/Introspection Endpoints (HIGH VALUE — distinct from session theft)

Standard CORS analysis focuses on stealing session cookies. But when the OIDC **token endpoint** or **introspection endpoint** has CORS misconfiguration, the attack chain is different and often higher severity:

### Attack Chain: Token Refresh from Any Origin
```
1. Attacker obtains refresh token (via XSS, phishing, social engineering)
2. Attacker hosts page on evil.com with JavaScript
3. Victim (Bitso user) visits evil.com while authenticated
4. JavaScript on evil.com sends POST to TARGET/token endpoint:
   - credentials: 'include' (browser sends cookies)
   - Content-Type: application/x-www-form-urlencoded
   - Body: grant_type=refresh_token&refresh_token=STOLEN
5. CORS reflects evil.com → browser allows the request
6. Attacker receives new access_token + refresh_token
7. Repeat forever → persistent account access
```

### Attack Chain: Authorization Code Exchange
```
1. Attacker intercepts authorization code (via open redirect, Referer leak, etc.)
2. JavaScript on evil.com sends POST to TARGET/token:
   - grant_type=authorization_code&code=INTERCEPTED&redirect_uri=...
3. CORS reflects origin → browser allows cross-origin POST
4. Attacker exchanges code for tokens
```

### Testing Token Endpoint CORS
```bash
# Test OPTIONS preflight
curl -sI -X OPTIONS "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization"

# Check response for:
# access-control-allow-origin: https://evil.com (reflected!)
# access-control-allow-methods: POST, OPTIONS
# access-control-allow-headers: Content-Type, Authorization  ← CRITICAL!
# access-control-allow-credentials: true

# Test actual POST
curl -sI -X POST "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=test"
# → CORS headers present + error response = endpoint processes cross-origin
```

### Severity
| Scenario | Severity | Reasoning |
|----------|----------|-----------|
| Token endpoint CORS + any origin + POST allowed | P3 | Enables token refresh from attacker page |
| Token endpoint CORS + Authorization header allowed | P2-P3 | Can use stolen Bearer tokens cross-origin |
| Introspection endpoint CORS + any origin | P3 | Token validation leak |
| Logout endpoint CORS + any origin | P4 | Force-logout CSRF (low impact) |

### Key Insight
**Token endpoint CORS is NOT about cookie theft — it's about enabling cross-origin POST requests that exchange codes/tokens.** Even with HttpOnly cookies, the attacker doesn't need to READ cookies; they need to POST with their OWN stolen credentials (refresh tokens, authorization codes). CORS misconfiguration on POST endpoints is a different vulnerability class than CORS on GET endpoints.

## Common False Positives

| Finding | Why It's False Positive |
|---------|-------------------------|
| CORS reflects origin with credentials on GET endpoints | If HttpOnly cookies + no Bearer tokens → not exploitable for session theft |
| CORS on OPTIONS preflight | OPTIONS never sends credentials, always succeeds |
| CORS on public endpoints | Public data doesn't need protection |
| CORS with wildcard | Browsers block `*` with credentials |
| CORS on Keycloak OIDC endpoints | **NOT automatically false positive!** Check: (1) does token endpoint reflect origin? (2) does userinfo accept Authorization header? (3) does introspection reflect origin? If yes to any → real finding (P3-P4). Only false positive if all endpoints are GET-only with HttpOnly cookies and no token refresh chain possible. |

## Fix Recommendations

1. **Strict origin validation**: Whitelist specific allowed origins
2. **Remove credentials support**: `Access-Control-Allow-Credentials: false` for public endpoints
3. **SameSite cookies**: Use `SameSite=Strict` or `SameSite=Lax` for session cookies
4. **HttpOnly cookies**: Always set `HttpOnly` for session tokens
5. **Avoid localStorage for tokens**: Use HttpOnly cookies instead of Bearer tokens in JS
