# API Security Reconnaissance — Proven Techniques

> Extracted from Fireblocks bounty (2026-09-03). Systematic techniques for API-only targets where you can't see frontend JS bundles.

---

## 1. Error Differential Analysis (The Master Technique)

**Core insight:** Different HTTP status codes and error message patterns reveal what exists, what's blocked, and what's protected differently.

### Status Code Legend
| Code | Meaning | What to Do |
|------|---------|------------|
| 200 | Open endpoint — likely public | **TEST EVERYTHING on this** |
| 401 | Auth required — endpoint EXISTS | Try auth bypass, error message leak |
| 403 | Forbidden — usually WAF/Cloudflare | Try WAF bypass, check if origin returns different code |
| 404 | Doesn't exist — NOT a target | Skip |
| 405 | Method not allowed — TRACE disabled | Confirms method filtering exists |
| 500 | Server crash — BUG | **High priority** — broken endpoint, potential DoS/RCE |
| 502/503 | Backend down | May be intermittently exploitable |

### Sibling Comparison Method
When you find an interesting response on one service, immediately test the SAME path on ALL sibling services. Different backend teams configure things differently — one sibling may leak what another hides.

```
For each endpoint pattern discovered:
  Test on sb-console-api
  Test on sb-mobile-api
  Test on sandbox-api
  Compare: 200 vs 401 vs 403 vs 404 — the anomaly is the finding
```

### WAF Detection Pattern
Cloudflare WAF returns HTML error pages with `cf-cache-status: DYNAMIC` and `Server: cloudflare`. Origin errors return JSON or plain text. If you see HTML with `<!DOCTYPE`, it's Cloudflare, not the app.

```
# Test if blocked by WAF vs origin
curl -s -o /dev/null -w "%{content_type}" https://TARGET/payload
# text/html = Cloudflare block
# application/json = origin response (real error)
# text/plain = origin response (real error)
```

---

## 2. Health Endpoint Fuzzing

Health endpoints are often the single highest-ROI API reconnaissance target.

### Standard Probing
```bash
curl -s https://TARGET/health
curl -s https://TARGET/healthz
curl -s https://TARGET/health?verbose=1
curl -s https://TARGET/health?debug=true
curl -s https://TARGET/health?detailed=true
curl -s https://TARGET/health?check=all
curl -s -X POST https://TARGET/health  # Some accept POST
```

### What Verbose Health Endpoints Typically Leak
- **AWS Account ID** — enables resource-based policy attacks
- **SNS Topic ARNs** — message injection potential
- **SQS Queue Names/URLs** — message send/receive potential
- **S3 Bucket Names** — bucket enumeration, misconfiguration check
- **Memory Usage** — heap/RSS with thresholds (not sensitive, but confirms runtime)
- **Database Status** — type, connection health
- **Cache Status** — Redis/Memcached connection details
- **Message Queue Status** — RabbitMQ, Kafka connection details
- **Service Names** — internal service mesh topology

### Impact Escalation Path
```
Health endpoint (no auth)
  → AWS Account ID
    → Resource-based policy attacks
  → SNS/SQS Names
    → If combined with auth bypass → message injection
  → S3 Bucket Name
    → AccessDenied = bucket exists (confirmation)
    → Public = data leak (critical)
  → Memory/Runtime Info
    → Helps craft exploits for specific runtime versions
```

---

## 3. Auth Error Code Enumeration

**Core insight:** Custom auth systems often return DIFFERENT error codes for different validation stages. Each code reveals a step in the auth flow.

### Systematic Approach
1. **No auth** → What code? (-3 "JWT is missing")
2. **Malformed auth** → What code? (-2 "No API key, nor 'sub' property")
3. **alg:none JWT with fake payload** → What code? (-7 "Error getting User certificate")
4. **alg:none JWT with valid-format UUID as sub** → What code? (same -7, deeper validation)
5. **Invalid UUID format** → What code? (-16 "Invalid user id format")

### Reconstructed Auth Flow
```
Request arrives
  → Check for Authorization header
    → No header? → code -3 "JWT is missing"
    → Has header but not Bearer? → code -3
    → Has Bearer but invalid JWT? → code -2 "No API key..."
    → Valid JWT but no 'sub' claim? → code -2
    → Valid JWT with 'sub' claim?
      → Validate UUID format
        → Invalid UUID? → code -16 "Invalid user id format"
        → Valid UUID?
          → Lookup user certificate
            → Not found? → code -7 "Error getting User certificate"
            → Found? → Authorize request
```

### Value for Attackers
- Error codes tell you exactly what format the auth expects
- Code -7 means forging a JWT with valid UUID sub WILL reach certificate lookup
- If you can find valid UUIDs (from /health, error messages, etc.), you can test the cert lookup
- Different error messages = different validation stages = different bypass points

---

## 4. JWT Analysis Framework

### Decode First
```python
import base64, json
header = json.loads(base64.urlsafe_b64decode(jwt.split(".")[0] + "=="))
payload = json.loads(base64.urlsafe_b64decode(jwt.split(".")[1] + "=="))
print(f"Algorithm: {header['alg']}")
print(f"Payload keys: {list(payload.keys())}")
print(f"Has 'sub': {'sub' in payload}")
print(f"Has 'iss': {'iss' in payload}")
print(f"Has 'aud': {'aud' in payload}")
```

### Key Questions
| Question | Why It Matters |
|----------|---------------|
| Is `sub` claim present? | Some APIs require `sub`, not `userId` |
| Is `iss` (issuer) present? | Custom JWT vs Auth0/OIDC |
| Is `aud` (audience) present? | Token scope/audience validation |
| What's the algorithm? | RS256 = asymmetric, HS256 = symmetric (confusion potential) |
| What's the expiry? | Time window for exploitation |

### Algorithm Confusion Attack
Test if server accepts different algorithms with the SAME payload:
```python
for alg in ["HS256", "RS256", "ES256", "PS256", "none"]:
    forged = base64url({"alg": alg, "typ": "JWT"}) + "." + original_payload + "." + signature
    # Send with Authorization: Bearer {forged}
```

If server returns different error for different algorithms = custom validation logic (more attack surface).

---

## 5. CORS Matrix Testing

### Test Matrix
For each origin, test ALL endpoints:
```
Origins to test:
  https://evil.com          → Should be blocked
  https://fireblocks.io     → Is it whitelisted?
  https://sandbox.fireblocks.io → Staging origin
  null                      → Null origin (iframes)
  https://localhost:3000    → Dev origin

Headers to check:
  Access-Control-Allow-Origin
  Access-Control-Allow-Credentials
  Access-Control-Allow-Methods
  Access-Control-Allow-Headers
```

### Key Pattern
`Access-Control-Allow-Origin: https://sandbox.fireblocks.io` + `Access-Control-Allow-Credentials: true` = you can make cross-origin authenticated requests FROM sandbox.fireblocks.io. If you can find XSS on sandbox.fireblocks.io, you can steal tokens via this CORS config.

---

## 6. HTTP Method Enumeration

For every discovered endpoint, test ALL methods:
```
GET     → Read data
POST    → Create/modify
PUT     → Full replace
PATCH   → Partial update
DELETE  → Remove
OPTIONS → CORS preflight (reveals allowed methods)
HEAD    → Same as GET but no body
TRACE   → Should be disabled (returns request)
```

**Key finding**: If OPTIONS returns 200 with `Allow: POST` on an endpoint that normally returns 401, the endpoint exists and supports that method — it's just behind auth.

---

## 7. Information Disclosure → Exploitation Chain

### Concrete Example (Fireblocks)
```
1. /health?verbose=1 → AWS Account ID 751886943440
2. /health?verbose=1 → SNS topic "sandboxAggregator"
3. Forge JWT with UUID sub → code -7 (cert lookup)
4. If cert lookup bypassed → access /debug/pprof
5. /debug/pprof/heap → memory dump
6. Memory dump → API keys/secrets
7. API keys → access all endpoints
```

### Second Example
```
1. POST /signup → 500 (crash)
2. X-Powered-By: Express → Node.js backend
3. CSP allows *.auth0.com → Auth0-based auth
4. Auth0 staging tenant discovered → fireblocks-staging.auth0.com
5. Staging Auth0 JWKS keys → 2 RSA keys with expiry dates
6. Auth flow: Auth0 → Custom JWT → User certificate → Endpoint access
```

---

## 8. Debug Endpoint Discovery

### Standard Paths (Go/Java/Node.js)
```
# Go (pprof)
/debug/pprof
/debug/pprof/heap
/debug/pprof/goroutine
/debug/pprof/trace
/debug/pprof/profile
/debug/vars
/debug/requests
/debug/events

# Java (Spring Actuator)
/actuator
/actuator/env
/actuator/health
/actuator/info
/actuator/mappings
/actuator/beans
/actuator/configprops
/actuator/heapdump

# Monitoring
/metrics
/prometheus
/debug/vars

# Node.js
/debug/
/__debug__
/_debug
/console
```

### Key Insight: 401 ≠ 404
If `/debug/pprof` returns 401 (not 404), the endpoint EXISTS and is behind auth. This is different from a 404 (doesn't exist). A 401 means: if you bypass auth, you get the debug data.

---

## 9. Host Header Injection via Cloudflare

Cloudflare typically blocks Host header manipulation:
```
curl -H "Host: 169.254.169.254" https://TARGET/ → 403 from Cloudflare
curl -H "Host: localhost" https://TARGET/ → 403 from Cloudflare
```

BUT Cloudflare only blocks the Host header. Other injection vectors may work:
- `X-Forwarded-Host`
- `X-Real-IP`
- `X-Original-URL`
- `X-Rewrite-URL`

---

## 10. Auth0 Discovery Checklist

When CSP or config mentions Auth0:
```bash
# Find tenant domains
curl -s https://fireblocks.auth0.com/.well-known/openid-configuration
curl -s https://fireblocks-staging.auth0.com/.well-known/openid-configuration
curl -s https://fireblocks.us.auth0.com/.well-known/openid-configuration

# JWKS keys (may reveal key rotation, expiry)
curl -s https://fireblocks-staging.auth0.com/.well-known/jwks.json

# Registration endpoint
curl -X POST https://fireblocks-staging.auth0.com/oidc/register \
  -H "Content-Type: application/json" \
  -d '{"client_name":"test","redirect_uris":["https://evil.com"],"grant_types":["authorization_code"],"token_endpoint_auth_method":"none"}'

# Token endpoint
curl -X POST https://fireblocks-staging.auth0.com/oauth/token \
  -d "grant_type=client_credentials&client_id=test"

# Common client IDs to enumerate
for cid in fireblocks console mobile sdk api sandbox; do
  curl -s -X POST "https://fireblocks.auth0.com/oauth/token" \
    -d "grant_type=client_credentials&client_id=$cid"
done
```

---

*Last updated: 2026-09-03 | Source: Fireblocks bounty recon (deep_probe1-6.py)*
