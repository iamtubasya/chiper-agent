# Fireblocks Bug Bounty — Findings (2026-09-01)

**Target**: Fireblocks (fireblocks.com)
**Platform**: HackerOne (`hackerone.com/fireblocks_mpc`)
**Researcher**: BC_USERNAME

## Finding 1: Cloudinary Unauthenticated Upload (HIGH)

### Vulnerability
Fireblocks Cloudinary accounts accept unsigned file uploads without authentication.

### Affected Accounts
- **US**: `fireblocks` (upload preset: `kgdyxtmr`)
- **EU**: `dvkywpcq6` (upload preset: `gz7mvatc`)

### PoC
```bash
# US account — upload HTML (no auth required)
curl -X POST "https://api.cloudinary.com/v1_1/fireblocks/image/upload" \
  -F "upload_preset=kgdyxtmr" \
  -F "file=@malicious.html"

# EU account — upload raw HTML (served as text/html)
curl -X POST "https://api.cloudinary.com/v1_1/dvkywpcq6/raw/upload" \
  -F "upload_preset=gz7mvatc" \
  -F "file=@phishing.html"
```

### Impact
- Uploaded HTML/JS served with correct Content-Type on *.cloudinary.com
- Phishing pages on trusted domain
- SVG files with embedded JS execute in victim browsers
- Bypasses CSP (raw uploads served as text/html, not image/*)

### Source
Unsigned upload presets extracted from `env-config.js` in SPA bundle.

---

## Finding 2: Auth0 CORS Wildcard Reflection (MEDIUM)

### Vulnerability
All 3 Auth0 regional endpoints return `Access-Control-Allow-Origin: *` for ANY origin, including `evil.com`, `null`, and `fireblocks.io.evil.com`.

### Affected Endpoints
- `https://fireblocks-prod.eu.auth0.com/userinfo`
- `https://fireblocks-prod.us.auth0.com/userinfo`
- `https://fireblocks-prod.au.auth0.com/userinfo`

### PoC
```bash
curl -sD- -o /dev/null -X OPTIONS \
  "https://fireblocks-prod.eu.auth0.com/userinfo" \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: GET"
# Returns: Access-Control-Allow-Origin: *
```

### Impact
- Cross-origin token refresh if session cookies are present
- Amplifies XSS impact (attacker can read Auth0 responses cross-origin)

---

## Finding 3: env-config.js Secret Leakage (MEDIUM)

### Vulnerability
`env-config.js` exposes internal configuration including:
- Auth0 client IDs (production + native signup)
- Cloudinary upload presets (unsigned)
- Datadog RUM application tokens
- LaunchDarkly client ID
- Stripe LIVE publishable key
- Pendo application ID
- Build version (`2.0.2289`)

### Source
`https://console.fireblocks.io/v2/2.0.2289/env-config.js`

### Impact
- Internal tooling configuration exposed
- Enables unauthenticated Cloudinary upload (Finding 1)
- Auth0 client IDs enable OAuth flow testing
- Build version reveals deployment timeline

---

## Finding 4: Staging Storage Public Access (LOW-MEDIUM)

### Vulnerability
CloudFront-hosted staging storage objects are publicly accessible without authentication.

### Source
Storage UUIDs extracted from JS bundle. Two SVG files confirmed accessible:
- `staging-assets-....cloudfront.net/....svg` (1,498 bytes)
- `staging-assets-....cloudfront.net/....svg` (2,688 bytes)

### Impact
- Pre-production assets accessible to external researchers
- May contain internal design assets, API docs, or staging configs
- x-amz-server-side-encryption header reveals AWS infrastructure details

---

## Key Technical Details

### JWT from Sandbox Console
- JWT valid for ~115 minutes from decode
- `userId`: `aa815e398-afd1-4adb-b9ad-534d550c0ba3`
- **Does NOT work as Bearer token for console-api** — Cloudflare blocks with error 1010
- Console-api uses separate API key auth, not web session tokens

### Cloudflare Protection
- All direct API calls from server IPs blocked (error 1010)
- Only browser-based requests (real IP, JS challenge) work
- Cannot bypass with headers, User-Agent, or proxy

### Auth0 Configuration
- Password grant enabled on production client
- Signup disabled (`/dbconnections/signup` returns 403)
- Token endpoint auth methods: `['none']` (public clients)
- No rate limiting observed on password grant
