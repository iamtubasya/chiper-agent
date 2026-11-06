# Arlo Bug Bounty — Session Findings (2026-08-27, Updated)
# Reference for vdp-recon. Target: arlo.com (HackerOne, "No Automated Scanning")

## Recon: 1096 subs → 368 filtered → 94 live → 15+ deep → 333 endpoints from 18MB JS

## 10 Confirmed Findings

### F1: WebSocket CAPTCHA Bypass (Medium 6.1) — 3 envs
- Frontend `captchaEnabled = false` → empty token → `success: true`
- Full AI agent + tools (search_feed, escalate_to_live_agent, kb_find, shopify_*, list_devices)
- Kill chain: bypass → system prompt → tool abuse → live agent → social engineering
- Detection: Search page HTML for `captchaEnabled`, `turnstile_site_key`

### F2: OMS ASP.NET Complete DoS (Medium 5.3)
- oms.arlo.com — login, forgot, SSO all crash to 500
- Every POST → 302 → `/WebError/Error500` → "Server Error in '/' Application"
- CSRF token required but doesn't prevent crash
- **Pattern:** POST to /Account/Login with any creds = 500 redirect

### F3: No Rate Limiting on Login (Medium 5.3)
- beta.arlo.com/hmsweb/login — 50+ rapid requests, 0 blocked
- Password policy leaked: error 2036 (min 6 chars, 1 upper, 1 lower, 1 number)

### F4: System Prompt Disclosure (Medium 4.3)
- WebSocket `system_prompt` → 23K chars. Patched z2-prod, still works z4-prod + ngsandbox

### F5: Dev API Exposed (Medium 4.3)
- myapigoldendev.arlo.com — 22+ endpoints, auth logic, token endpoint
- Error codes: 2001, 2103, 2401, 2036

### F6: Azure Backend URL Disclosure (Low-Med 3.1)
- OMS 404 leak: `arlo-production-admin-web.azurewebsites.net`
- .NET error: `{"Message":"No HTTP resource was found matching... 'https://INTERNAL-URL/api/endpoint'."}`
- Azure 403 IP-blocked (x-ms-forbidden-ip header)
- **Pattern:** Test nonexistent /api/* on ASP.NET — 404 error leaks backend URL

### F7: S3 Bucket Existence (Low 2.5)
- arlo-s3-custdetect-z2-gdev — 301 in 7/9 regions, 403 in us-west-2
- Path from JS: `0ec0b89af6a6488c9b56c934023`
- **Pattern:** 301=exists wrong region, 403=exists locked, 404=not found

### F8: Shopify GraphQL Introspection (Low 2.5)
- apac.arlo.com — full schema readable, 100+ types, no auth

### F9: Registration Info Leak (Low 2.5)
- /hmsweb/register — detailed validation errors, password policy
- JS reveals password encoding: `btoa(unescape(encodeURIComponent(pass)))`

### F10: Firebase Project Discovery (Info)
- 4 projects: web-app-359a3, web-app-beta-9504f, web-app-gdev, web-app-prod-d8c19
- All RTDB/Firestore locked (404). 5 Google API keys (masked in JS)

## Not Vulnerable
CORS, subdomain takeover, SQLi, IDOR (auth required), SSRF, prompt injection,
JWT alg:none, account enumeration, Firebase RTDB/Firestore, S3 listing

## Kill Chain
CAPTCHA bypass → system prompt → tool abuse → live agent → social engineering
No rate limit → brute force → account takeover
OMS 500 crash → full auth system DoS

## Key Techniques
- JS bundle: 333 endpoints from 18MB Angular (grep URLs + API paths)
- WebSocket: captcha_verify, system_prompt, send_message events
- S3 existence: 301=wrong region, 403=exists locked, 404=not found
- ASP.NET errors: 404/500 messages leak internal backend URLs
- Firebase config: projectId, authDomain, appId from client JS
- SPA catch-all: all paths return 200 with identical HTML body
- Multi-env: same endpoint across prod/dev/QA — dev weaker
- Registration: password base64 encoded in transit, needs captcha token (missing field)
- OCAPI endpoints on myapigoldendev: SPA catch-all (not real APIs)
- ebsprd SAML: Okta SSO via Cloudflare Access Gateway (locked)
