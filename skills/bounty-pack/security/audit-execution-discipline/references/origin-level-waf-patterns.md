# Origin-Level WAF Patterns — Real-World Findings

> Added from ALSCO audit (2026-09-23). These WAFs run at the origin server level, NOT CDN-level.

## Pattern 1: Secure Gateway® (ALSCO)

### Identification
- **Server header:** `Server: Secure Gateway®` or `Server: S.G WebServer`
- **Custom headers:** `X-Server-Powered-By: Secure Gateway®`, `X-Secure_Gateway_ID: <hash>`
- **Error page:** Redirects to `/msg/sg_err.php?err=<code>&SG_ID=<id>&ser=N&Rule=<rule>`
- **Block behavior:** ALL paths → 302 redirect to error page

### WAF Rules Observed
| Rule Code | Category | Triggered By |
|-----------|----------|-------------|
| G.S.13 | General sensitive path | All paths |
| G.S.930130 | Suspicious request | .env, .git/config |
| G.S.941100 | XSS detection | `<script>` tags |
| G.S.921120 | CRLF injection | `%0d%0a` payloads |

### Architecture
- Runs as nginx module or reverse proxy on origin server
- NOT CDN-level — bypassing Cloudflare does NOT help
- Blocks ALL request types: normal paths, attack payloads, file access
- Uses SG_ID (timestamp-based monotonic counter) for session tracking

### Bypass Attempts (ALL FAILED on ALSCO)
| Technique | Result |
|-----------|--------|
| Direct origin IP access | BLOCKED — same 302 |
| HTTP/2 binary framing | BLOCKED — empty response |
| Chunked transfer encoding | BLOCKED — 302 |
| Large body (>8KB) | FAILED — TLS internal error |
| Content-Type switch (JSON) | BLOCKED — 302 |
| Multipart form data | BLOCKED — 302 |
| HTTP method override | BLOCKED — 302 |
| Path normalization (12 variants) | BLOCKED — err=23 |
| Backslash/semicolon path | BLOCKED — 302 |
| Null byte injection | BLOCKED — connection reset |
| URL/double encoding | BLOCKED — 302 |
| Case variation | BLOCKED — 302 |
| Absolute URI | BLOCKED — empty |
| Host header manipulation | BLOCKED — 403 |

## Detection Method
```bash
# Step 1: Find origin IP (not Cloudflare)
nslookup target.com 8.8.8.8
# If IP is NOT 104.x/172.67.x → direct origin

# Step 2: Test direct access
curl -skI --resolve target.com:443:DIRECT_IP https://target.com/

# Step 3: Check Server header for WAF product
curl -sk --resolve target.com:443:DIRECT_IP https://target.com/ 2>/dev/null | grep -i "server:"

# Step 4: If Server shows WAF product name → origin-level WAF
```

## Signs You're Facing Origin-Level WAF
1. ALL paths return same status (302/403) regardless of content
2. DNS resolves to non-CDN IP (not Cloudflare/Akamai/Fastly)
3. Direct IP access with correct Host header STILL gets blocked
4. Server header shows custom WAF product name
5. Custom WAF-specific headers present
