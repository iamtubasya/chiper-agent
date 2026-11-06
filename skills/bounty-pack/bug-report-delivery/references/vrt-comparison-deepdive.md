# VRT Comparison + Deep-Dive Reference

## VRT JSON Lookup Pattern

```python
import urllib.request, json

def find_vrt_entry(keywords):
    """Search VRT JSON for matching vulnerability category."""
    url = "https://raw.githubusercontent.com/bugcrowd/vulnerability-rating-taxonomy/master/vulnerability-rating-taxonomy.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    
    results = []
    def deep_search(node, path=""):
        name = node.get("name", "").lower()
        node_id = node.get("id", "")
        for kw in keywords:
            if kw in name or kw in node_id:
                results.append({
                    "name": node.get("name"),
                    "id": node_id,
                    "priority": node.get("priority"),
                    "path": path
                })
                break
        for child in node.get("children", []):
            deep_search(child, path + " > " + node.get("name", ""))
    
    for cat in data["content"]:
        deep_search(cat)
    return results
```

## CORS Deep-Dive Checklist

### Origin Matrix (test ALL combinations)
```python
origins = [
    "https://evil.com",           # Standard external
    "https://target.com.evil.com", # Subdomain spoof
    "https://evil-target.com",    # Domain spoof
    "null",                        # Sandbox iframe
    "http://localhost:3000",       # Local dev
]
```

### Endpoint Categories to Test
1. **Unauthenticated data endpoints** — topics, lists, public configs
2. **Authenticated endpoints** — profile, settings, user data (test with custom auth headers)
3. **Matrix/API server endpoints** — versions, capabilities, login
4. **Well-known endpoints** — `.well-known/matrix/server`, `robots.txt`

### CORS Response Analysis
| ACAO Value | Impact | VRT Baseline |
|------------|--------|-------------|
| `*` (no creds) | Unauthenticated data readable cross-origin | P4 |
| `*` + `ACAC: true` | Impossible (browsers reject) — server misconfigured | P3 |
| Reflects Origin | Authenticated data exfiltrable | P2 |
| `null` accepted | Sandbox iframe data theft | P4 |

### Key Questions
1. Does server reflect specific origins? (test with 4+ origins)
2. Is `Access-Control-Allow-Credentials: true` present with `*`?
3. Does preflight (OPTIONS) return permissive headers?
4. Are authenticated endpoints also CORS-enabled?
5. Does `null` origin get CORS access?
6. How many subdomains share the CORS policy?

### Subdomain CORS Scan Pattern
```python
subdomains = ["api", "chat", "sync", "media.video", "newsroom", "support"]
paths = ["/", "/health", "/util/topics/v1", "/.well-known/matrix/server"]
for sub in subdomains:
    for path in paths:
        # curl with Origin header, check for ACAO in response
```

## Viability Gate Examples

### BY DESIGN (skip these)
- PostHog write keys exposed in client JS → designed for client-side event tracking
- Algolia secured API keys → designed for client-side with filter restrictions
- OAuth open registration on public platform → by design
- CORS `*` on public read-only API endpoints → depends on data sensitivity
- **Amplitude HTTP API key + CORS * on analytics proxy** → key is public by design, CORS * required for client SDK event sending. Data poisoning via fake events = inherent in Amplitude's architecture. NOT reportable.
- **RevenueCat web key (`rcb_*`) + subscriber endpoint** → web key designed for client-side SDK to query current user's subscription. `/subscribers/{id}` is the intended client API. Using web key server-side = same access level as client SDK. NOT reportable.
- **Mux environment key in client JS** → video player config, public by design
- **Turnstile site key in HTML** → captcha widget key, public by design
- **Third-party Vercel deployment returns 200** → ALWAYS verify page content is target's app. Check canonical URL, og:site_name, app title. A `project-name.vercel.app` returning 200 may be an unrelated third-party project, not a staging deployment.

### INFORMATIONAL (skip unless chainable)
- Missing security headers (no exploit chain)
- Software version disclosure
- Internal IP disclosure (no SSRF path)
- Weak CSP (`unsafe-inline` + `unsafe-eval`) without any injection point to exploit it
- CORS `*` on subdomains with legitimate purpose (Matrix web client, video player, analytics proxy)

### REPORTABLE (include these)
- CORS `*` on authenticated API endpoints → data exfiltration
- CORS `*` with Origin reflection → credentialed data theft
- CORS `*` on endpoints with sensitive data → PII/metadata leak
- CORS misconfiguration enabling CSRF → state-changing actions
- Any finding chainable to higher severity
- **Analytics proxy with CORS * AND no rate limiting AND accepts arbitrary user_id** → if the proxy can be used to DoS the analytics pipeline or inject data that triggers automated business actions (billing, feature flags), argue for P4-P5 with concrete impact scenario

## Severity Argument Template (when VRT baseline is None)

```
VRT Category: [path from VRT JSON]
VRT Baseline: [priority or "None"]
Researcher Assessment: [P{N}]

Justification:
- Impact: [what data/action is affected]
- Attacker: [permissionless/needs user interaction/needs auth]
- Scope: [single endpoint/cross-subdomain/full platform]
- Precedent: [similar CVEs or disclosed reports]

Recommended Severity: P{N} ({Low/Medium/High/Critical})
```
