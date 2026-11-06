# WordPress VIP Testing Quick Reference

## Detection
Look for `vip/v1` namespace in `/wp-json/` response. VIP sites are hosted by Automattic.

## Key Endpoints
| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/wp-json/vip/v1/search/dev-tools` | POST | URL allowlist | SSRF potential — needs `query` + `url` params |
| `/wp-json/vip/v1/sites` | GET | 401 | Site info |
| `/wp-json/vip/v1/plugins` | GET | 401 | Plugin list |
| `/wp-json/vip/v1/jetpack` | GET | 401 | Jetpack status |

## SSRF Test (dev-tools)
```python
import json
payload = json.dumps({"query":"test","url":"http://169.254.169.254/latest/meta-data/"}).encode()
# "url is not a valid allowed URL" → allowlist active (not exploitable)
# Returns internal content → SSRF CONFIRMED
```
**Pitfall:** VIP has URL allowlist — internal IPs always rejected. Allowed = same domain only.

## NASA Custom Namespaces
- `nasa-external-content/v1/unpublished-posts` — **KEY**: leaks unpublished content WITHOUT auth
- `nasa-hds/v1`, `nasa-apps/v1`, `smd/v1` — content endpoints (usually 401/empty)
- `gwiz/v1` — product management (install/activate — always 401)
- `newspack-content-converter` — returns 500 for all IDs (broken, not exploitable)
- `elasticpress/v1/indexing_status` — returns indexing info (usually 0 items)

## Pitfalls
- Most VIP endpoints return 401 — well-configured by Automattic
- `nasa-external-content/v1/unpublished-posts` is the ONE exception (no auth)
- dev-tools SSRF blocked by URL allowlist
- `gwiz/v1` endpoints look scary but always 401
- `newspack-content-converter` broken (500) — not exploitable

## WordPress CORS Exploitation Checklist
When testing WordPress sites for CORS misconfiguration, follow this systematic approach:

### Endpoint Priority Order
1. `/wp-json/wp/v2/users` — User enumeration (highest value if 200 without auth)
2. `/wp-json/wp/v2/posts` — Post content (always 200 on public sites)
3. `/wp-json/wp/v2/pages` — Page content
4. Root `/` — Check if CMS-level CORS is present

### Test Pattern
```bash
# For each endpoint:
curl -sk -v -H "Origin: https://attacker.com" "https://target/wp-json/wp/v2/users"
# Check response headers for:
# Access-Control-Allow-Origin: https://attacker.com (REFLECTION = CRITICAL)
# Access-Control-Allow-Credentials: true (cookies will be sent)
# Access-Control-Allow-Methods: ... PUT, PATCH, DELETE (state-changing allowed)
```

### Severity Classification
| ACAO Pattern | ACAC | Severity | Impact |
|-------------|------|----------|--------|
| Reflected attacker origin | true | **CRITICAL** | Full credential theft + data read + state change |
| `*` (wildcard) | true | HIGH | Spec-compliant browsers block cookies with *, but reportable |
| `*` (wildcard) | absent | LOW | Public data, often by-design |
| Specific trusted domain | true | MEDIUM | Whitelist misconfiguration |

### WordPress-Specific Risk Amplifiers
- `/wp-json/wp/v2/users` without auth + CORS reflection = unauthenticated cross-origin user enum (worst case)
- PUT/PATCH/DELETE in `Access-Control-Allow-Methods` = cross-origin CSRF+CSWSH
- OPTIONS preflight returning same CORS headers = browser will allow the request
- Mass scan: test 4 endpoints × 15 parallel workers for full scope coverage
