---
name: dnsReaper
description: "Subdomain takeover scanner — 50+ signatures, 50 subs/sec, supports AWS/Azure/Cloudflare/GoDaddy/DigitalOcean/GCP. Use during recon phase for subdomain takeover checks."
version: 1.0.0
author: Punk Security (adapted for Hermes)
license: MIT
metadata:
  hermes:
    budget_kb: 6
    tags: [security, recon, subdomain, takeover, dns]
---

# dnsReaper — Subdomain Takeover Scanner

## When to Use

Load during Phase 0B (Recon) of any BB audit, specifically for subdomain takeover detection. Works with 50+ takeover signatures across all major cloud providers.

## Location

`D:\data hermes\dnsReaper\`

## Usage

### Single domain scan
```bash
cd "D:\data hermes\dnsReaper"
python main.py single --domain target.com
```

### File-based scan (list of domains)
```bash
python main.py file --filename domains.txt
```

### Docker (full features including Google Cloud)
```bash
docker run -it --rm -v "$(pwd):/etc/dnsreaper" punksecurity/dnsreaper file --filename /etc/dnsreaper/domains.txt
```

### Output formats
```bash
python main.py single --domain target.com --out stdout --out-format json
python main.py single --domain target.com --out results --out-format csv
```

### Cloud provider scans (need credentials)
```bash
# AWS
python main.py aws --aws-access-key-id KEY --aws-access-key-secret SECRET
# Cloudflare
python main.py cloudflare --cloudflare-api-token TOKEN
# Azure
python main.py azure --azure-subscription-id ID
```

## Integration with Audit Workflow

Add to `security-recon` Phase 0B:
1. After subdomain enumeration (subfinder/crt.sh)
2. Pipe discovered subdomains to dnsReaper
3. Check for takeover-able CNAME records
4. Report as findings if takeover is possible

## Known Issue — FIXED

Google Cloud provider was broken on Python 3.14 (missing `pkg_resources`).
**Fix applied:** upgraded `google-cloud-dns` from 0.34.1 → 0.37.1 (uses `importlib.metadata`).
All providers now work including GCP.

## Signatures

50+ takeover signatures covering:
- AWS S3/CloudFront/EB/Lambda
- Azure Blob/CDN/VM/Functions
- GitHub Pages/Shopify/Heroku
- Fastly/Netlify/Cloudflare Pages
- Many more...

## Fallback saat tool rusak — cek CNAME dangling manual

Kalau `python main.py` gagal saat import (mis. `ModuleNotFoundError: No module named
'dns.asyncresolver'` — konflik versi dnspython), **jangan berhenti**. Deteksi takeover
cuma butuh dua hal dan keduanya bisa dilakukan tanpa tool ini:

1. **CNAME yang menunjuk ke target yang tidak resolve** (NXDOMAIN) — sinyal terkuat.
2. **CNAME ke layanan pihak ketiga yang bisa diklaim** (S3, Azure, CloudFront, Shopify).

Resep manual (`nslookup`, tanpa dependensi):

```python
import subprocess, re, concurrent.futures as cf

def dig(host):
    out = subprocess.run(["nslookup","-type=CNAME",host,"8.8.8.8"],
                         capture_output=True, text=True, timeout=15).stdout
    m = re.search(r'canonical name\s*=\s*([^\s]+)', out)
    if not m: return None
    cname = m.group(1).rstrip('.')
    out2 = subprocess.run(["nslookup",cname,"8.8.8.8"],
                          capture_output=True, text=True, timeout=15).stdout
    nx = ("NXDOMAIN" in out2) or ("can't find" in out2)
    return (host, cname, nx)

with cf.ThreadPoolExecutor(max_workers=15) as ex:
    for r in ex.map(dig, subdomains):
        if r and r[2]: print("DANGLING:", r[0], "->", r[1])
```

Lalu kelompokkan CNAME per provider (regex-nya ada di § Signatures) dan periksa yang
menarik. Nuclei juga punya template siap pakai:

```bash
nuclei -l subs.txt -t "<nuclei-templates>/http/takeovers" -rl 5 -c 2 \
  -H "User-Agent: <username>@BC_ALIAS.com"
```

**Aturan FP di bawah tetap berlaku** — resolve host dulu, jangan percaya fingerprint
yang muncul di halaman error CDN.

## False positives — VERIFY BEFORE REPORTING (2026-10-21, bytefederal.com)

subzy flagged `influx/ldbapi/ldbapiglobal.bytefederal.com` as **Cargo Collective** takeovers.
All three resolved to **Cloudflare proxy IPs (104.18.x)** and the "fingerprint" was the
**generic Cloudflare 404 page** — a scanner-label match, not a finding. Verification rule:

1. **Resolve the host first.** If it lands on a CDN/proxy range (Cloudflare 104.16–104.31,
   172.64–172.67, 188.114.x; Fastly; etc.), any service-fingerprint match on an error page is
   an FP — you are fingerprinting the CDN's error page, not the origin.
2. A real takeover needs BOTH: a CNAME (or A record) pointing at a **claimable third-party
   service** AND a response that is actually that service's "unclaimed" page.
3. For bare-IP hosts that don't answer HTTP: check other ports before calling them dangling.
   `onyx/tagcase/skynyxvanta.bytefederal.com` (174.138.x / 198.199.x) answered nothing on
   80/443 but had **SSH open** — live, controlled servers, not reclaimable IPs. A dark web
   port ≠ a dead droplet.
4. Report FPs as "FP, already verified" in the ledger so the next run doesn't re-chase them.
