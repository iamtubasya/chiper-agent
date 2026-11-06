# Source Map Reverse Engineering — Recover Full API Surface

> Proven on Chipotle catering web (Vue.js SPA + ASP.NET API gateway).
> When direct path probing hits a wall (404 on API gateway, 401 everywhere), the frontend bundle is the map to the whole backend.

## When to Use
- SPA target (Vue/React/Angular) dengan API gateway terpisah yang return 404 untuk root & generic paths
- Path probing menghasilkan 401 (auth-gated) tanpa tahu endpoint apa yang valid
- Mau mapping endpoint lengkap + request headers + parameter structure tanpa akun dulu

## Workflow

### 1. Find the JS bundle(s)
```bash
curl -s "https://target.com" -o home.html
grep -oE 'src="[^"]*\.js[^"]*"' home.html | head -40
```
Cari bundle app (bukan vendor/chunk). Kadang di CDN terpisah (`orderweb-cdn.chipotle.com`).

### 2. Extract base URLs & env config dari bundle
```bash
grep -oE 'https?://[a-zA-Z0-9._/-]+' app.js | sort -u | head -40
grep -oE 'VUE_APP_[A-Z_]+' app.js | sort -u
```
Ini mengungkap: API base URL, env var names (`VUE_APP_BASE_URL`, `VUE_APP_SUBSCRIPTION_KEY`, dll).

### 3. Download & parse source map
```bash
# Cek kalau sourceMappingURL ada di akhir bundle
grep -oE 'sourceMappingURL=[^ ]*' app.js
# Download map (sering 200 walau bundle besar)
curl -sk "https://target.com/js/app.HASH.js.map" -o app.js.map
```

**NOTE:** `.js.map` sering LEBIH BESAR dari bundle-nya. Jangan `grep` file map mentah (JSON satu baris raksasa — bikin terminal timeout). Parse dengan Python:

```python
import json, re
with open('app.js.map', 'r', encoding='utf-8', errors='replace') as f:
    sm = json.loads(f.read())
content_map = {}
for s, c in zip(sm.get('sources', []), sm.get('sourcesContent') or []):
    if c:
        content_map[s] = c
# sources = daftar file asli, sourcesContent = full source code
```

### 4. Extract API surface dari source files
- Cari file `*Client.js` / `*Service.js` di daftar sources → berisi SEMUA endpoint calls
- Grep pattern: `get(`, `post(`, `put(`, `delete(` dengan path
- Cari `createClient.js` → header structure (API keys, correlation IDs, auth mode)
- Cari `process.env.VUE_APP_*` → nama-nama config yang mungkin bocor di bundle production

### 5. Status-code differential probing (tanpa akun)
Setelah tahu base URL + path structure, probe untuk bedain endpoint valid vs tidak:

| HTTP Code | Arti |
|---|---|
| 404 | Path tidak ada / salah prefix |
| 401 | Path ADA, butuh auth — valid endpoint |
| 429 | Endpoint auth aktif + rate-limited (login/register) |
| 200 | Public endpoint — test langsung |

```bash
for p in "/api/v1/health" "/api/v1/order" "/api/v1/login"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 10 "https://target.com$p")
  echo "$p -> $code"
done
```

## Chipotle Example (working case)
- Base: `https://services.chipotle.com/cateringorder/v1` (dari `VUE_APP_BASE_URL` + `VUE_APP_VERSION`)
- EPOPS: `https://services.chipotle.com/epops/v2`
- Headers (dari `createClient.js`): `Ocp-Apim-Subscription-Key`, `Chipotle-CorrelationId: COO-{uuid}`, `x-cmg-ff-user`, `withCredentials: true` (cookie auth)
- 42 endpoint API berhasil di-recover termasuk `/order/{id}/validate`, `/order/{id}/transfer`, `/order/{id}/promotions/{code}`, `/transaction/tokenize/{providerId}/{clientToken}`
- Auth endpoints (login/register) → 429 rate-limited

## Pitfalls
- Jangan grep file .map mentah di terminal — JSON satu baris raksasa → timeout (exit 124). Selalu parse via Python.
- `orderweb-cdn.chipotle.com` reject curl biasa (exit 35 SSL) — coba `curl -sk` atau ambil dari browser.
- Endpoint 429 ≠ broken — itu rate limiter aktif; jangan brute, delay 3-5 detik.
- Beberapa path butuh prefix version (`/v1`) yang beda dari yang terlihat di bundle minified — cek `VUE_APP_VERSION` env.
- Route-level code splitting = bundle terpisah per halaman (`webpackChunkName`). Endpoint untuk fitur tertentu bisa di chunk lain, bukan app.js utama.

## Staging Domain Reachability Testing
When source maps reveal staging/dev URLs (`stageui.*`, `ui-test.*`, `preprod.*`), PROVE they're reachable before claiming weaker security.

### Step 1: DNS Resolution Check
```python
import socket
hostname = "stageui.teamviewer.com"  # from source map
try:
    ip = socket.gethostbyname(hostname)
    print(f"Resolves to: {ip}")
    if ip.startswith("127."):
        print("BLOCKED: Loopback — internal-only, NOT publicly reachable")
    else:
        print(f" reachable at {ip}")
except socket.gaierror as e:
    print(f"BLOCKED: DNS failure — {e}")
```

**Key insight:** Cloudflare WARP VPN intercepts DNS and returns its own virtual IPs (127.0.2.x). Python's `socket.gethostbyname()` bypasses WARP DNS interception and returns the ACTUAL resolution. Always use Python DNS, never trust curl/host/dig behind WARP.

### Step 2: HTTP Probe (only if DNS resolves to public IP)
```bash
curl -sk -o /dev/null -w "HTTP %{http_code} | %{time_total}s" \
  --max-time 5 "https://stageui.teamviewer.com/"
# 000 = unreachable (timeout/connection refused)
# 200 = accessible — now test auth, endpoints, etc.
# 403/401 = behind auth — still a valid attack surface
```

### Step 3: Interpret Results
| DNS Result | HTTP Result | Verdict |
|---|---|---|
| `127.x.x.x` | N/A | **Internal-only** — cannot test remotely. Do NOT claim staging has weaker security. |
| `127.x.x.x` | N/A (WARP) | **WARP intercept** — use `socket.gethostbyname()` to get real IP |
| Public IP | `000`/timeout | **Firewalled** — not reachable from external network |
| Public IP | `200`/`401`/`403` | **Reachable** — valid attack surface, test normally |
| DNS failure | N/A | **Does not exist** — source map artifact, not a real endpoint |

**⚠️ CRITICAL RULE:** Do NOT write "staging environments likely have weaker security controls" in a report when you CANNOT prove the staging URL is accessible. This is an assumption, not evidence. If DNS returns loopback, state: "The staging domain resolves to an internal network address (127.0.2.2) and is not externally accessible."
