# Next.js `__NEXT_DATA__` Information Disclosure

**Origin session:** Origin Energy / MyConnect 2026-09-04  
**Applicable to:** Any Next.js application (Payload CMS, standalone Next.js, Vercel deployments)

---

## What is `__NEXT_DATA__`?

Every Next.js page includes a `<script id="__NEXT_DATA__" type="application/json">` tag containing the page's server-side rendered data. This is a **design feature** — Next.js needs this data to hydrate the React app on the client side.

**The problem:** Developers often include sensitive data in this payload without realizing it's fully visible in the page source.

---

## Extraction Method

```bash
# Method 1: grep from curl
curl -s "https://TARGET.com/any-page/" | grep -oP '(?<=__NEXT_DATA__" type="application/json">).*?(?=</script>)' | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(json.dumps(data, indent=2))
" > nextdata.json

# Method 2: Direct extraction of buildId (useful for build manifest)
curl -s "https://TARGET.com/any-page/" | grep -oP '"buildId":"[^"]+"'
```

---

## What to Look For

### High-Value Data (Reporting Worthy)

| Field | Location | Impact |
|-------|----------|--------|
| Staff emails | `props.pageProps.user.email`, `props.pageProps.staff[]` | Account enumeration for brute force |
| MongoDB/ObjectId document IDs | `props.pageProps.user._id`, `props.pageProps.item.id` | IDOR testing, internal data correlation |
| Internal URLs | `props.pageProps.config.*`, `props.pageProps.urls.*` | Infrastructure mapping (AWS, GCP, Atlassian) |
| Password policy | `props.pageProps.config.passwordPolicy` | Lockout/brute force planning |
| Lockout settings | `props.pageProps.config.lockout.*` | Bypass planning (see lockout bypass pattern) |
| Build ID | `props.buildId` | Build manifest route enumeration |
| Auth tokens | `props.pageProps.token`, `props.pageProps.session` | Session hijacking (if valid) |
| Feature flags | `props.pageProps.flags.*` | Feature enumeration, hidden functionality |
| API keys (client-side) | `props.pageProps.config.apiKey` | Third-party service abuse |

### Low-Value Data (Usually Informational)

| Field | Location | Impact |
|-------|----------|--------|
| Page title/description | `props.pageProps.title` | None (SEO content) |
| CSS/theme config | `props.pageProps.theme` | None |
| Navigation structure | `props.pageProps.nav` | Low (site structure) |
| Analytics IDs | `props.pageProps.analytics.*` | Informational (public by design) |

---

## MyConnect Case Study

**URL:** `https://portal.myconnect.com.au/auth/login-as`

**Data extracted from `__NEXT_DATA__`:**
```json
{
  "staff": [
    {"email": "jess@myconnect.com.au"},
    {"email": "lisa@myconnect.com.au"},
    {"email": "tanika@myconnect.com.au"},
    // ... 21 total staff emails
  ],
  "config": {
    "passwordPolicy": {"minLength": 8},
    "lockout": {"maxAttempts": 3, "lockDuration": 1800000},
    "mongodb": {"uri": "mongodb+srv://..."},
    "s3": {"bucket": "myconnect-uploads", "region": "ap-southeast-2"},
    "auth0": {"domain": "myconnect.au.auth0.com", "clientId": "..."}
  },
  "urls": {
    "aws": "https://console.aws.amazon.com/...",
    "google": "https://admin.google.com/...",
    "atlassian": "https://myconnect.atlassian.net/...",
    "newrelic": "https://one.newrelic.com/..."
  }
}
```

**Impact:** 21 staff emails + password policy + lockout config = brute force attack planning.

---

## Attack Chain

```
1. Extract __NEXT_DATA__ from any page
2. Parse JSON for emails, config, internal URLs
3. Use emails for GraphQL brute force (if loginUser mutation exists)
4. Use lockout config to plan bypass (if portal has lockout but GraphQL doesn't)
5. Use buildId to fetch build manifest (full route enumeration)
6. Use internal URLs for infrastructure attacks (if accessible)
```

---

## Severity Assessment

| Finding | Severity | VRT Mapping |
|---------|----------|-------------|
| Staff emails leaked in __NEXT_DATA__ | P3 Medium | A07: Identity & Auth Failures |
| Internal URLs leaked (AWS, Atlassian) | P3 Medium | A05: Security Misconfiguration |
| Password policy + lockout config leaked | P4 Low | A05: Security Misconfiguration |
| MongoDB connection string leaked | P1 Critical | A02: Cryptographic Failures |
| Auth token leaked in __NEXT_DATA__ | P1-P2 | A07: Identity & Auth Failures |
| Build ID only (no sensitive data) | P5 Informational | None (expected Next.js behavior) |

**Key:** The buildId itself is informational — it's required for Next.js to function. The FINDING is what you can DO with it (fetch build manifest, enumerate routes).

---

## Complementary Techniques

### Build Manifest Route Enumeration
```bash
# After extracting buildId
curl -s "https://TARGET.com/_next/static/{buildId}/_buildManifest.js" | \
  grep -oP '/[a-zA-Z0-9/_-]+' | sort -u
# Returns EVERY route including hidden admin, API, onboarding flows
```

### SSR Data Routes
```bash
# Fetch page-specific data (may leak server-side content)
curl -s "https://TARGET.com/_next/data/{buildId}/admin.json"
curl -s "https://TARGET.com/_next/data/{buildId}/api/users.json"
```

### Source Map Extraction
```bash
# Check for exposed source maps
curl -s "https://TARGET.com/_next/static/{buildId}/_ssgManifest.js" | head -c 200
curl -s "https://TARGET.com/_next/static/chunks/main.{hash}.js.map"
# Source maps contain original TypeScript, variable names, comments
```

---

## By-Design Considerations

**Arguments FOR by-design:**
- `__NEXT_DATA__` is a core Next.js feature — all SSR data must be client-side accessible
- BuildId is required for client-side navigation
- Analytics IDs are public by design

**Arguments AGAINST by-design (strengthens finding):**
- Staff emails are NOT required for client-side rendering
- Internal URLs (AWS console, Atlassian) are NOT required for client-side rendering
- Password policy and lockout config are NOT required for client-side rendering
- MongoDB connection strings are NEVER acceptable in client-side code
- Auth tokens should NEVER be in `__NEXT_DATA__` (use httpOnly cookies instead)

**Recommended approach:** Don't report `__NEXT_DATA__` as a standalone finding unless it contains sensitive data (emails, tokens, credentials, internal URLs). The buildId and public config are expected behavior.
