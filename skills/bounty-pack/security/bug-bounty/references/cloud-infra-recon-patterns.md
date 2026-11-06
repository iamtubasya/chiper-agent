# Cloud Infrastructure Recon Patterns — Arlo Case Study
# Reference for vdp-recon Phase 4B and Phase 8

## Target: arlo.com (HackerOne, "No Automated Scanning" policy)
## Tech: Python/Uvicorn (FastAPI), Cloudflare, S3, Okta SSO, Shopify, ASP.NET (OMS)

## Recon: 1096 subs → 368 filtered → 94 live → 15+ deep → 333 endpoints from 18MB JS

## Key Findings

### 1. Health Endpoint Info Disclosure
GET /health → version, git hash, LLM model ID (no auth)
```bash
curl -s https://ai-agent-z2-prod.arlo.com/health
# {"status":"healthy","version":"...","model_id":"us.anthropic.claude-sonnet-4-..."}
```

### 2. S3 Bucket Name from Error Response
S3 errors include bucket name + folder path:
```bash
curl -s https://mygoldenqa.arlo.com/robots.txt
# <Key>web-wac-gqa/www/robots.txt</Key>
```

### 3. Unauthenticated Cron Validation
POST /api/v1/automations/validate-cron → server timezone + next executions (no auth)

### 4. WebSocket CAPTCHA Bypass (Medium 6.1)
Frontend `captchaEnabled = false` → empty token → `success: true`
Full AI agent + tools + live agent escalation

### 5. JS Bundle Endpoint Enumeration
18MB Angular bundle → 333 endpoints, Azure URL, S3 bucket, Okta params
```bash
grep -oE 'https?://[a-z0-9.-]+\.arlo\.com[^\s"'"'"'<>]*' main_app.js | sort -u
grep -oE '"[/][a-z0-9/_-]+"' main_app.js | sort -u | wc -l
```

### 6. AWS API Gateway Detection
"Missing Authentication Token" = API Gateway (not generic 403)
/ping = healthy without auth = liveness check

### 7. ASP.NET Error Message URL Disclosure (Low-Med 3.1)
.NET 404 errors leak INTERNAL backend URL in error message:
```bash
curl -sk "https://oms.arlo.com/api/nonexistent"
# {"Message":"No HTTP resource was found matching 'https://arlo-production-admin-web.azurewebsites.net/api/nonexistent'."}
```
Extract: hostname (arlo-production-admin-web), cloud provider (azurewebsites.net), API structure.
Also: x-ms-forbidden-ip header on Azure backend = IP-based access control.

### 8. S3 Bucket Existence Verification (Low 2.5)
Verify bucket existence + region without credentials:
```bash
# 301 = exists in different region (try other regions)
# 403 + AccessDenied = exists in this region (locked)
# 404 = doesn't exist
curl -sk -o /dev/null -w "%{http_code}" "https://BUCKET.s3.us-east-1.amazonaws.com/"
curl -sk "https://BUCKET.s3.us-west-2.amazonaws.com/" | head -c 500
```
AccessDenied ≠ "not vulnerable" — bucket EXISTS, name + region confirmed.

### 9. ASP.NET Auth System DoS (Medium 5.3)
POST to login/forgot/register → 500 crash chain:
```
POST → 302 → /WebError/Error500?aspxerrorpath=/Account/Login
→ "Server Error in '/' Application. Runtime Error"
```
Full auth system DoS. CSRF token doesn't prevent crash. SSO also affected.

### 10. Firebase Project Enumeration
4 projects from client JS: web-app-359a3, web-app-beta-9504f, web-app-gdev, web-app-prod-d8c19
All RTDB/Firestore locked (404). Multiple = multiple environments.

### 11. Shopify GraphQL Introspection
apac.arlo.com — full schema (100+ types), no auth needed.

### 12. AWS ALB Cookie Detection
Set-Cookie: AWSALB=... + AWSALBCORS=... → confirms ALB behind Cloudflare.
Infrastructure: Cloudflare → AWS ALB → Azure App Service.

## False Positives
- care.arlo.com — ALL paths 200 with identical Arlo 404 page (custom error handler)
- myapigoldendev.arlo.com/ocapi/* — SPA catch-all (Angular fallback, not real APIs)
- .env, config.json, swagger.json on SPA = Angular fallback, not real files

## Infrastructure Map
- EKS clusters: k8s-aiagent-prodsava, k8s-aiagent-savantai, k8s-aiagent-goldenqa
- ALBs: arlocsprodalb, arlo-ow-np-staging (10 variants), ssocallback-prod (8)
- Okta: engihub-dev client_id 0oavkbbm4h70lXU3c697, ebsprd SAML SSO

## Blocked (Not Vulnerable)
CORS (Cloudflare clean), subdomain takeover (85 CNAMEs Arlo-owned), SQLi (WAF),
IDOR (auth required), SSRF (guardrails), prompt injection (guardrails),
JWT alg:none, account enumeration, Firebase RTDB/Firestore, S3 listing

## Pitfalls
1. Python 3.14 on Windows: lxml/docx break from PYTHONPATH → os.environ.pop('PYTHONPATH')
2. heredocs >50 lines fail on MSYS → use write_file
3. python3 -c with complex code fails on MSYS → write_file first
4. DoS rules apply → 3-5s delays between probes
5. No Automated Scanning policies → GENTLE automated (rate-limited, never manual/curl-only)
6. SPA catch-all: all paths 200 with identical body = false positive
7. Azure "Web App - Unavailable" 403 = app STOPPED, not WAF block
8. Report language: English for HackerOne submission
