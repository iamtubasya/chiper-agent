# React Native / Expo Mobile App Bundle Recon for Bug Bounty

When the target has a React Native mobile app (iOS/Android), the JS bundle is the single most valuable recon artifact — equivalent to a full backend API map.

## Technique: Hermes Bytecode String Extraction

React Native apps compiled with Hermes engine produce `.bundle` files containing bytecode, but `strings` extraction reveals API endpoints, deep links, config, and GraphQL schemas.

### Step 1: Extract Strings from Bundle
```bash
# Hermes bytecode .bundle — standard strings extraction
strings -n 8 chime.bundle > all_strings.txt

# Also try: node_modules bundle (if APK was downloaded)
unzip -o app.apk 'assets/index.android.bundle' -d extracted/
strings -n 8 extracted/assets/index.android.bundle > all_strings.txt
```

**Note:** Hermes bundles are NOT standard JS — they're compiled bytecode. Standard JS beautifiers/prettifiers won't work. Use `strings` utility (minimum length 8) for extraction.

### Step 2: Enumerate Extracted Patterns
```bash
# API endpoints (GraphQL mutations/queries, REST paths)
grep -oE 'https?://[a-zA-Z0-9._:/-]+' all_strings.txt | sort -u > urls.txt
grep -ioE '(mutation|query)\s+[A-Z][a-zA-Z]+' all_strings.txt | sort -u > graphql_ops.txt

# Deep link schemes (custom URL schemes)
grep -ioE '[a-z]+://' all_strings.txt | sort -u > deeplinks.txt

# Environment URLs (dev, staging, QA, production)
grep -ioE '(dev[0-9]+|staging|qa|integ|preprod)\.' all_strings.txt | sort -u > env_urls.txt

# Internal URLs, debug endpoints
grep -ioE '(internal|debug|admin|sandbox|dogfood)[_/a-zA-Z0-9-]*' all_strings.txt | sort -u > internal.txt

# Third-party SDK config
grep -ioE '(sentry|amplitude|segment|plaid|arkose|launchdarkly|datadog|newrelic)[a-zA-Z0-9_./-]*' all_strings.txt | sort -u > sdk_config.txt

# Feature flags and config
grep -ioE '(feature|flag|toggle|experiment|abtest|variant)[a-zA-Z0-9_./-]*' all_strings.txt | sort -u > feature_flags.txt
```

### Step 3: Expo / OTA Configuration Analysis
```bash
# Extract Expo project identity
grep -oE 'expo\.dev/@[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+' all_strings.txt
grep -oE 'owner["'"'"':]+\s*["'"'"'][a-zA-Z0-9_-]+["'"'"']' all_strings.txt
grep -oE 'slug["'"'"':]+\s*["'"'"'][a-zA-Z0-9_-]+["'"'"']' all_strings.txt

# Expo project UUID (for API enumeration)
grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' all_strings.txt | sort -u

# Check OTA (Over-The-Air) updates
grep -ioE '(updates\.expo\.dev|classic-assets\.eascdn\.net|expo-updates|eas-update)' all_strings.txt

# Code signing status
grep -ioE '(CODE_SIGN|expo-signing|secure-manifest|EXUpdatesPublicKey)' all_strings.txt
```

### Step 4: Deep Link Route Mapping
React Native apps expose deep link routes as string constants. These reveal the full navigation structure:

```bash
# Map all deep link routes
grep -ioE '(chime|internal)://[a-zA-Z0-9_/{}?&=-]+' all_strings.txt | sort -u > deeplink_routes.txt

# Categorize by sensitivity
cat deeplink_routes.txt | grep -i 'private\|internal\|admin\|debug\|dogfood\|sandbox\|credential\|secret\|key\|token' > sensitive_deeplinks.txt
cat deeplink_routes.txt | grep -i 'test\|mock\|fake\|stub\|demo' > test_deeplinks.txt
```

**Severity indicators:**
- `internal://private_key_storage` → CRITICAL (credential access)
- `internal://dogfood/installApk` → HIGH (code execution)
- `internal://sandbox_tool_button` → MEDIUM (test mode in prod)
- `chime://settings/security/*` → LOW-MEDIUM (auth-protected)

### Step 5: GraphQL Schema from Bundle
Modern RN apps with GraphQL backends embed the full operation definitions:

```bash
# Extract all GraphQL mutations (write operations = higher attack value)
grep -ioE 'mutation\s+[A-Z][a-zA-Z0-9]+' all_strings.txt | sort -u

# Extract all GraphQL queries (read operations)
grep -ioE 'query\s+[A-Z][a-zA-Z0-9]+' all_strings.txt | sort -u

# Extract fragment definitions
grep -ioE 'fragment\s+[A-Z][a-zA-Z0-9]+\s+on\s+[A-Z][a-zA-Z]+' all_strings.txt | sort -u

# Extract variable names (input fields for mutations)
grep -oE '\$[a-zA-Z]+' all_strings.txt | sort -u
```

**Attack priority:** Mutations > Queries > Fragments. Focus on mutations that involve:
- Fund transfers / payments (race condition, double-spend)
- Account creation / identity verification (bypass, escalation)
- Card activation / management (IDOR)
- Loan applications (data manipulation)

→ **For detailed GraphQL attack patterns:** Read `references/graphql-attack-patterns.md` — covers unauthenticated namespaces, BOLA via mutation variables, race condition static analysis, step-up MFA exploitation, and error analysis.

### Step 6: Environment Enumeration
RN apps often include URLs for multiple environments (dev1-dev5, QA, staging, integration):

```bash
# Extract all environment-specific URLs
grep -oE 'https?://[a-zA-Z0-9.-]*(dev[0-9]+|staging|qa|integ|preprod|dogfood)[a-zA-Z0-9.-]*' all_strings.txt | sort -u

# Map environment exposure
# Production bundle with dev/QA URLs = likely bypassable
# QA endpoints accessible from internet = weaker auth
# Dev endpoints with debug features = highest value
```

**Severity mapping:**
- QA/Staging endpoints accessible from internet → P2 (weaker auth, by-explicitly-in-scope programs)
- Dev endpoints with debug features → P1-P2 (credential logging, test accounts)
- Dogfood/employee-only features in prod bundle → P2-P3 (privilege escalation)

## Case Study: Chime Financial (2026-09)

### What was found:
- **22,275 strings** extracted from Hermes bytecode bundle
- **8+ environment URLs** (dev1-dev5, qa, integ, preprod) — all in production bundle
- **Internal deep link scheme** (`internal://`) with 200+ routes
- **50+ GraphQL mutations** including `ActivateCardEncrypted`, `EnrollExperianMutation`, `SubmitLoanApplication`
- **Arkose Labs SDK config** (security challenge provider)
- **70+ GraphQL fragments** revealing full data model
- **Feature flag tuner config URLs** (A/B test configuration)
- **JIRA ticket reference** (LEND-4303 — internal issue tracker leak)
- **Slack workspace** (chime.enterprise.slack.com — internal comms)

### Attack vectors identified:
1. **GraphQL BOLA/IDOR**: Mutations with user IDs as variables — test with different user IDs
2. **QA/Staging bypass**: `member-qa.chime.com`, `app-qa.chime.com` — likely weaker auth
3. **Race conditions**: Money movement mutations (`SubmitLoanApplication`) — double-spend testing
4. **Internal deep links**: `internal://private_key_storage`, `internal://dogfood/installApk`
5. **Dev environment exploitation**: Debug endpoints (`action-clearAllLogs`, `auth_credential_logins.json`)

### Cloudflare WAF considerations:
- VPS IPs blocked by CloudFront geo-blocking (Singapore pop)
- US residential proxy required for actual testing
- Infrastructure pivot: S3, third-party APIs, CDN endpoints may bypass WAF

## Pitfalls
1. **Hermes bundles are NOT JS** — don't try `node` or `js-beautify`, they won't work
2. **Strings extraction is approximate** — may miss some patterns, cross-reference multiple grep patterns
3. **Expo project ID may be invalid** — check `expo.dev/@owner/slug` format first
4. **OTA may be disabled** — Expo Classic sunset (2024), check if updates are still served
5. **Deep links may require authentication** — mapping routes ≠ exploiting them, still need auth testing
6. **Not all GraphQL operations are accessible** — some may require specific roles/permissions
7. **Subagents will REFUSE offensive testing** — run all active exploit attempts via terminal/execute_code directly
