# Bug Bounty Writeup Techniques — 2026 Real-World Methods
> Source: securitycipher/daily-bugbounty-writeups, kh4sh3i/bug-bounty-writeups, devanshbatham/Awesome-Bugbounty-Writeups
> Safety: ✅ All repos verified clean (markdown/content only)

## Proven Testing Techniques from 2026 Disclosures

### 1. DOMPurify Fingerprinting (Sep 2026)
- **What:** Identify which sanitizer version is running before crafting bypass
- **How:** Check DOM behavior differences between versions
- **Technique:** Use known bypasses per version (DOMPurify <3.0.0 has mXSS via SVG)
- **Ref:** securitycipher/daily-bugbounty-writeups

### 2. OAuth Token Refresh Chain (2026)
- **What:** Exploit race condition in token refresh
- **How:** Send concurrent refresh requests → get multiple valid tokens → use stale token for unauthorized actions
- **Technique:** Token refresh endpoint often lacks proper revocation

### 3. GraphQL Introspection Bypass (2026)
- **What:** Disable introspection check but still expose via error messages
- **How:** Send malformed query → error reveals type names and fields
- **Technique:** Error-based disclosure when introspection is "disabled"

### 4. Prototype Pollution → RCE (2026)
- **What:** JSON merge/pollution in template engines
- **How:** `{"__proto__":{"isAdmin":true}}` → template renders as admin
- **Advanced:** `__proto__.constructor.prototype` → prototype chain pollution
- **Technique:** Test all JSON merge endpoints, query param parsers

### 5. SSRF via DNS Rebinding (2026)
- **What:** Bypass SSRF filters by rebinding DNS
- **How:** Host DNS that returns public IP first, then internal IP on second resolve
- **Technique:** `0.0.0.0` → `169.254.169.254` (cloud metadata)

### 6. Race Condition on File Upload (2026)
- **What:** Upload + delete race → access deleted file
- **How:** Upload file, then immediately delete while processing is still happening
- **Technique:** TOCTOU in file processing pipelines

### 7. GraphQL Batch Query Abuse (2026)
- **What:** Rate limit bypass via batch queries
- **How:** Send `[{query: "..."}, {query: "..."}]` → 1 request, N operations
- **Technique:** Test if rate limiter counts operations or HTTP requests

### 8. JWT `kid` Parameter Injection (2026)
- **What:** SQLi/RCE via JWT key ID parameter
- **How:** Set `kid: "/dev/null"` or `kid: "key' OR 1=1--"` in JWT header
- **Technique:** Test all JWT header parameters as injection points

### 9. CORS Misconfiguration → Account Takeover (2026)
- **What:** Trusted origin reflection → steal tokens
- **How:** Origin `evil.com.trusted.com` reflected as `Access-Control-Allow-Origin`
- **Technique:** Test subdomain reflection, null origin, special chars

### 10. HTTP Request Smuggling via Content-Length/Transfer-Encoding (2026)
- **What:** CL.TE smuggling bypass modern WAFs
- **How:** Craft request with conflicting CL and TE headers
- **Technique:** Use Transfer-Encoding: chunked with Content-Length to bypass WAF

## Additional Sources
| Source | Content |
|--------|---------|
| `fatim-ezzahra12/bug-bounty-writeups` | Self-taught researcher writeups, web security focus |
| `nrshafi/idor-guide` | IDOR/BOLA zero-to-advanced, OWASP 2025 aligned, GraphQL + chaining |

## Tool Selection for Each Technique
| Technique | Tool |
|-----------|------|
| DOMPurify bypass | Manual + dalfox |
| OAuth race | curl parallel + Python |
| GraphQL introspection | arjun + manual |
| Prototype pollution | nuclei templates |
| SSRF DNS rebind | custom DNS + curl |
| Race condition | Turbo Intruder |
| JWT injection | jwt_tool + sqlmap |
| CORS | custom script |
| Smuggling | smuggler.py |
