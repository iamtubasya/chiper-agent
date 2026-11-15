# Subdomain Enumeration — crt.sh + DNS Fallback

## crt.sh Certificate Transparency

```bash
# Basic query
curl -s "https://crt.sh/?q=%.DOMAIN.com&output=json" | python3 -c "
import sys,json
data=json.load(sys.stdin)
names=set()
for e in data:
    names.update(e.get('name_value','').split('\n'))
for n in sorted(names):
    if 'DOMAIN' in n.lower():
        print(n)
"
```

**Timeout issue on Windows/MSYS:** crt.sh can be slow. Set generous timeout (60s) or run in background.

## DNS Fallback (when crt.sh fails)

```bash
# Check common subdomains
for sub in mail webmail login app portal admin demo test dev staging api docs help support vpn ftp mx smtp imap pop3; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://${sub}.DOMAIN.com" 2>/dev/null)
  if [ "$code" != "000" ]; then
    echo "${sub}.DOMAIN.com → $code"
  fi
done
```

## Response Code Interpretation

| Code | Meaning | Priority |
|------|---------|----------|
| 200 | Live service | HIGH — investigate |
| 301/302 | Redirect | MEDIUM — follow redirect |
| 403 | Forbidden (exists, blocked) | HIGH — file exists but protected |
| 404 | Not found | LOW — doesn't exist |
| 502/503 | Backend error | MEDIUM — service exists but broken |
| 000 | Connection failed | SKIP — no service |

## Admin Panel Detection Pattern

When you find an admin panel (200 on /admin, /wp-admin, etc.):

1. **Check server header** — nginx without Cloudflare = direct access, fewer protections
2. **Check CSP header** — `unsafe-eval` or `unsafe-inline` = XSS→RCE possible
3. **Check CORS** — `Access-Control-Allow-Origin: *` = cross-origin data theft
4. **Check login form** — hidden fields may be exploitable (SSRF via server param)
5. **Check for brute force protection** — multiple failed logins = rate limiting?
6. **Check version disclosure** — in console, URL params, headers

### Proven Pattern: Atmail Admin Panel
- `admin.atmailcloud.com` = nginx, no Cloudflare
- CSP: `unsafe-eval` + `unsafe-inline`
- Hidden `server` field in login form (potential SSRF)
- jQuery 3.5.0 (old, potential XSS)
- Version 11.2.5 leaked in console + URL params
- Password recovery form exposed (no username enumeration though)

## Batch Subdomain Check Script

```bash
#!/bin/bash
DOMAIN=$1
for sub in $(cat subdomains.txt); do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://${sub}.${DOMAIN}" 2>/dev/null)
  [ "$code" != "000" ] && echo "${sub}.${DOMAIN} → $code"
  sleep 0.3  # Rate limit compliance
done
```
