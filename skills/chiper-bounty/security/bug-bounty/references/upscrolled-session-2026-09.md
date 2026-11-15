# UpScrolled VDP15 Session Findings (2026-09)

## Target
- **Platform**: UpScrolled (upscrolled.com) — content/creator platform
- **Program**: Bugcrowd VDP15
- **Scope**: [*.]upscrolled.com, *.upscrolled.com

## Infrastructure
- **CDN/WAF**: CloudFront (d2ztp9yajiqtd1.cloudfront.net) — blocks GraphQL POST, host header injection, HTTP smuggling
- **Subdomains**: api, sync, newsroom, support, chat, media.video
- **Auth**: Cloudflare Turnstile on registration/login
- **Matrix**: chat.upscrolled.com runs Tuwunel v1.9.0 (CORS *)
- **CMS**: DNA CMS on newsroom.upscrolled.com (Next.js)

## Confirmed Findings

### F1: Amplitude Analytics Proxy Injection (MEDIUM)
- **Endpoint**: `sync.upscrolled.com/2/httpapi`
- **Key**: `8b54609e6ee48c53584284b4ed4192d2`
- **Impact**: Revenue data corruption, user growth inflation, attribution pollution
- **Confirmed**: 100 events ingested in single batch, no auth, no rate limit
- **Severity**: P3-P4 (analytics-only, limited downstream impact proof)

### F2: PostHog Event Injection (LOW)
- **Key**: Extracted from newsroom HTML
- **Impact**: Arbitrary events, user properties, feature flags
- **Confirmed**: All 6 injection types return `{"status":"Ok"}`
- **Severity**: P4 (analytics-only)

### F3: RevenueCat API Key Exposure (LOW-MEDIUM)
- **Key**: `rcb_XBWplVnHCqakochgVQWuXlqkhQjb` (from `window.__UPSCROLLED_PUBLIC_CONFIG__`)
- **Impact**: Subscriber enumeration, auto-creation, identify endpoint accessible
- **Severity**: P4 (limited by no entitlements on existing subscribers)

### F4: CORS * on 4 Subdomains (LOW)
- **Affected**: api, chat, sync, media.video.upscrolled.com
- **Impact**: Cross-origin requests accepted, but no credential reflection
- **Severity**: P4

### F5: Permissions-Policy camera=* + microphone=* (LOW-MEDIUM)
- **Impact**: Embedded content gets camera/mic access
- **Severity**: P3-P4 (needs injection vector)

### F6: Newsroom Drive Enumeration (LOW)
- **Endpoint**: `https://newsroom.upscrolled.com/shared/drives`
- **Impact**: Enumerate internal drive structure without auth
- **Severity**: P4

### F7: Config Leak in window.__UPSCROLLED_PUBLIC_CONFIG__ (LOW)
- **Leaked**: Amplitude key, Mux env key, Turnstile site key, RevenueCat key
- **Severity**: P4

## Key Lessons

### 1. Server-Side Proxy Injection Pattern
The strongest finding was the Amplitude proxy at `sync.upscrolled.com/2/httpapi`. This is distinct from direct API key abuse:
- Proxy bypasses Amplitude rate limits
- Events appear to come from real users (server adds context)
- No filtering on event content or volume
- Affects business intelligence and financial reporting

### 2. Global Config Object = Goldmine
`window.__UPSCROLLED_PUBLIC_CONFIG__` contained ALL third-party API keys in one place. Always check for `window.__*__CONFIG__` patterns first — they're higher ROI than grepping individual JS bundles.

### 3. WAF Blocking = Pivot Signal
CloudFront WAF blocked: GraphQL POST, host header injection, HTTP smuggling, API endpoint fuzzing (all returned 403). Instead of retrying, pivoted to: infrastructure analysis, JS bundle extraction, third-party service enumeration, analytics proxy testing.

### 4. Matrix Federation = Limited Attack Surface
chat.upscrolled.com runs Tuwunel with CORS *, but:
- Registration is properly disabled
- Federation endpoints return 404/401
- No credential exposure via CORS
- Limited exploitability without authenticated session

### 5. Deepdive Persistence
User corrected: "Kamu terlalu gampang menyerah pdhl blm memakai semua skill dan tools yg kamu punya" — the agent gave up after initial 403s without exhausting all angles. The attack surface extends beyond the main API to analytics proxies, third-party SDKs, config objects, and subdomain services.

### F8: Account Enumeration via Sign-up Error Differential (MEDIUM)
- **Endpoint**: `POST https://newsroom.upscrolled.com/api/users/sign-up`
- **Request format**: `{"user":{"first_name":"P","last_name":"T","email":"admin@upscrolled.com","phone":"","type_id":2,"subscribed":0}}`
- **Existing user response**: `{"title":"Welcome back!","message":"You're already registered...","id_code":"43c29d20d0ed8c8a"}`
- **New user response**: `{"title":"Registration successful","message":"Welcome! We've sent a login code...","id_code":"03771601f1130ae7"}`
- **Enumerated accounts**: admin@upscrolled.com ✅, dev@upscrolled.com ✅, all others ❌
- **No rate limiting**: 10 rapid sign-ups + 20 token verification attempts, zero 429 responses
- **Severity**: P4 (User Enumeration per VRT)

### F9: Type ID Accepts All Values Without Validation (LOW-MEDIUM)
- **Endpoint**: Same sign-up endpoint as F8
- **Finding**: type_id 0,1,2,3,4,5,10,99 all accepted — no server-side validation
- **Risk**: If type_id=1 = admin, attacker could escalate privileges during registration
- **Unverified**: Cannot complete magic link flow to confirm escalation
- **Severity**: P4 (potential P2-P3 if verified)

### F10: id_code Information Disclosure (LOW)
- **Endpoint**: Sign-up endpoint returns 16-char hex `id_code` for every user
- **Impact**: Internal identifier exposed to unauthenticated callers
- **Severity**: P5 (informational)

### F11: Dashboard Endpoint Exists (INFO)
- **Endpoint**: `GET /dashboard` returns 403 "No permission to access this action"
- **Impact**: Confirms admin panel exists, proper access control in place
- **Severity**: Informational

### F12: AWS SigV4 Auth Mechanism Leak (INFO)
- **Endpoint**: `api.upscrolled.com` returns progressive error messages revealing AWS Signature V4 requirements
- **Impact**: Backend architecture information disclosure
- **Severity**: Informational

## Key Lessons

### 6. SPA API Format Extraction is Critical
When curl returns "Please provide your email address" despite including the email, the API expects a DIFFERENT JSON shape. The newsroom API wraps fields under a `user:` namespace. Always extract the actual request format from the JS bundle before testing. See `references/api-webapp-testing.md` for the full technique.

### 7. Auth Bypass Requires Complete Flow
Account enumeration via sign-up is confirmed, but privilege escalation via type_id cannot be verified without completing the magic link flow. The 6-digit verification code requires access to the email inbox. This is a common limitation in passwordless auth testing.

## VRT Mapping
- F1: unsafe_cross_origin_resource_sharing (P4, limited exploitability)
- F3: sensitive_data_exposure (P4, API key in client JS)
- F5: risky_resource (P3-P4, camera/mic access)
- F8: sensitive_data_exposure > user_enumeration (P4)
- F9: broken_access_control > privilege_escalation (P4, unverified)
- F10: sensitive_data_exposure > information_exposure (P5)
- Others: informational/low
