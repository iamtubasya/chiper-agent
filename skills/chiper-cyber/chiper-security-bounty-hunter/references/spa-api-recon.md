# SPA / JS Bundle API Recon (endpoint & host mining)

Fast passive technique to map a JavaScript SPA's full backend API surface from its
public bundle — no auth, no fuzzing, no source repo needed. Very effective on
payment/fintech dashboards and any modern React/Vue/Angular app.

## 1. Harvest the JS bundle URL from the SPA HTML

```bash
curl -sk "https://<app-host>/" -A "Mozilla/5.0" -o app.html
python3 -c "
import re
h = open('app.html', encoding='utf-8', errors='ignore').read()
for m in re.findall(r'<script[^>]*src=[\"\x27]([^\"\x27]+)', h):
    print('JS:', m)
"
```

Look for `/assets/index-<hash>.js` (Vite/Rollup) or `/static/js/main.<hash>.js` (CRA/webpack).

## 2. Download the main bundle (often 1MB+) and mine it

```bash
curl -sk "https://<app-host>/assets/index-<hash>.js" -o bundle.js
```

Write the regex to a file and run it (do NOT inline `\`` backtick classes in a
shell heredoc — backticks trigger command substitution and break the script; the
safe pattern is `write_file` → `python3 extract.py`).

```python
# extract.py — API hosts, baseURLs, and /api/vN/ paths from a JS bundle
import re
h = open('bundle.js', encoding='utf-8', errors='ignore').read()

hosts = set(re.findall(r'https?://([a-z0-9-]+\.example\.net)', h))
print('HOSTS:', sorted(hosts))

for m in set(re.findall(r'baseURL\s*[:=]\s*["\x27`]([^"\x27`]+)', h)):
    print('baseURL:', m)

for m in set(re.findall(r'["\x27`](/api/v[0-9]+/[a-zA-Z0-9/._${}:?=-]{2,80})["\x27`]', h)):
    print('PATH:', m)
```

Bonus: route templates with `${var}` placeholders reveal **IDOR candidates** at a
glance, e.g. `wallets/${id}/addresses`, `merchant/clients/${id}`,
`referral-codes/${id}` — every `${id}`-style path is worth an authz test later.

## 3. Probe unauthenticated endpoints (non-destructive GET only)

```bash
for ep in /api/v1/env /api/v1/currencies /api/v1/rates /api/v1/features; do
  code=$(curl -sk "https://api-host$ep" -o body.txt -w "%{http_code}" --max-time 10)
  echo "$ep -> $code  $(head -c 200 body.txt)"
done
```

- `200` unauthenticated on an endpoint you'd expect guarded = potential info disclosure.
- `/api/v1/env` and similar config endpoints frequently leak `env name`,
  `identityBaseUrl`, feature flags, or internal hostnames (Low severity, but real).
- `401` with empty body on guarded routes confirms auth is enforced (document as a no-finding).

## 4. Bonus: Cloudflare `data-cfemail` email deobfuscation

Cloudflare-obfuscated emails on marketing/legal pages decode with XOR against the
first hex byte:

```python
import re
cf = re.findall(r'data-cfemail="([0-9a-fA-F]+)"', html)
for c in cf:
    r = int(c[:2], 16)
    print(''.join(chr(int(c[i:i+2], 16) ^ r) for i in range(2, len(c), 2)))
```

## Pitfalls

- **`httpx` is ambiguous** — Python `httpx` (import module) and projectdiscovery
  `httpx` (Go CLI) are different tools. A bare `httpx -silent ...` call may hit the
  wrong binary or a permission-denied shim. When in doubt, do live-host probing with
  a small Python `httpx.get` + ThreadPoolExecutor script instead.
- **Backticks in heredoc regex** cause `bad substitution`. Always `write_file` the
  Python, never inline template-literal (`\``) patterns in `<<'EOF'`.
- **Non-Cloudflare IPs** on a subdomain (e.g. nginx `server:` header, no `cf-ray`)
  are the origin IP exposed directly — flag it, but treat internal infra subdomains
  (rabbit/admin/logs) as likely out-of-scope per most VDPs until confirmed.
