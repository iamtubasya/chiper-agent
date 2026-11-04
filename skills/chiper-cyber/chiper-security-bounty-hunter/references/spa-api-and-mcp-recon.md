# SPA API Mining, CT SAN Pivoting & MCP Recon Recipes

 Condensed, reusable one-liners and scripts for Phase 1–3 bug bounty reconnaissance.

## 1. Decode Cloudflare Email Obfuscation (`data-cfemail`)
Bug bounty policy and footer pages behind Cloudflare often hide `security@...` and legal entity emails in `data-cfemail` attributes.

```python
import re, urllib.request

html = urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
).read().decode("utf-8", "ignore")

for cf in re.findall(r'data-cfemail="([0-9a-fA-F]+)"', html):
    key = int(cf[:2], 16)
    email = "".join(chr(int(cf[i:i+2], 16) ^ key) for i in range(2, len(cf), 2))
    print("Decoded email:", email)
```

## 2. CT Log Failover (`crt.sh` → `CertSpotter`) & Shared SAN Discovery
When `crt.sh` times out (`HTTP 000`) or returns truncated output, query CertSpotter with `expand=dns_names`. Always inspect non-target domains in `dns_names` — shared Let's Encrypt certificates expose sibling or shadow domains hosted on the same origin server.

```bash
for d in example.com; do
  curl -s "https://api.certspotter.com/v1/issuances?domain=$d&include_subdomains=true&expand=dns_names" \
    --max-time 20 -A "Mozilla/5.0" | python3 -c "
import sys, json
for entry in json.load(sys.stdin):
    for name in entry.get('dns_names', []):
        print(name.strip().lower())
"
done | sort -u
```

Verify shared TLS certificate SANs directly against the origin/host to prove infrastructure ownership:
```bash
echo | timeout 12 openssl s_client -connect host.example.com:443 -servername host.example.com 2>/dev/null \
  | openssl x509 -noout -subject -issuer -ext subjectAltName
```

## 3. SPA JS Bundle API Route & Host Extractor
Avoid complex inline bash quote-escaping (`bad substitution` on `${...}` template literals) by writing a small Python script or passing regex via stdin:

```python
import re

h = open("bundle.js", encoding="utf-8", errors="ignore").read()

# 1. Backend & sibling hosts
hosts = sorted(set(re.findall(r"https?://([a-z0-9.-]+\.[a-z]{2,})", h)))

# 2. Versioned API paths (both string literals and template literals with ${...})
ver_paths = sorted(set(re.findall(r"""['"`]([^'"`]*/v[0-9]+/[^'"`]{2,80})['"`]""", h)))

print("=== HOSTS ===", *hosts, sep="\n")
print("=== VERSIONED PATHS ===", *ver_paths, sep="\n")
```

Also inspect the `Content-Security-Policy` (`default-src` / `connect-src`) header on the SPA HTML response — it frequently lists every backend API host, WebSocket endpoint, and third-party payment/KYC integration before you even parse the JS bundle.

## 4. Non-Destructive Model Context Protocol (MCP) Endpoint Probing
If a host or subdomain (e.g., `mcp.*` or `/mcp`) returns `405 Not Allowed` on `GET /mcp`, test whether it is an unauthenticated JSON-RPC MCP server using read-only `initialize` and `tools/list` calls:

```bash
# 1. Handshake
curl -sk "https://target/mcp" --max-time 10 \
  -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"recon","version":"1.0"}}}'

# 2. Enumerate exposed tools & input schemas
curl -sk "https://target/mcp" --max-time 10 \
  -X POST -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python3 -m json.tool
```
