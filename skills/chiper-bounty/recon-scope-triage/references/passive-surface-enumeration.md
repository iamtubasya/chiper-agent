# Passive public-surface enumeration (no active scanning)

Builds the ownership anchor + attack-surface map **without touching the target**. Nothing here sends a payload or generates load — safe to run against any third party when authorization is unverified or absent.

## 1. Certificate Transparency — highest-value passive source
CT logs leak internal/ops hostnames because internal services still get public certs (or get pulled in via multi-SAN issuance). This is where `gitlab.`, `gitea.`, `matrix.`, `element.`, `ovpn.`, `mon.`, `stg-forms.` type hosts surface.

- Primary: `curl -s "https://crt.sh/?q=%25.<domain>&output=json"`
- **crt.sh frequently returns 502 / rate-limits and serves an HTML error page** → the JSON parse fails. Do not conclude "no subdomains". On failure, fall back immediately:
- **Fallback (reliable): certspotter API**
  ```bash
  curl -s "https://api.certspotter.com/v1/issuances?domain=<domain>&include_subdomains=true&expand=dns_names"
  ```
- Parse unique `dns_names` (strip `*`), then resolve each (below).

## 2. Passive DNS resolution + hosting classification (DoH)
`curl -s "https://dns.google/resolve?name=<host>&type=A"` — also `CNAME`, `TXT`, `MX`, `NS`, `SOA`, `CAA`. Queries go to Google's resolver, **never the target's authoritative NS** (no footprint on them).

Classify each resolved IP against provider CIDRs (Cloudflare, GCP, AWS, Hetzner, DigitalOcean, OVH):
- IP inside Cloudflare ranges = asset is proxied/shielded.
- IP on a **raw GCP / Hetzner / AWS origin** = directly exposed → WAF-bypass surface, priority target.
- **RFC1918 addresses (`10.x`, `172.16–31.x`, `192.168.x`) published in PUBLIC DNS = internal VPC topology leak** — a real, reportable hygiene finding on its own.

## 3. Harvest extra hosts from public CSP + page source
The `Content-Security-Policy` of a public app enumerates the entire third-party stack **and more of the org's own hosts** (`frame-src`, `connect-src`, `img-src`, `script-src`). Grep it for names — expect `forms`, `stg`/`stg2`/`stg3` (staging!), `static`, `api`, CDN buckets, and third parties.
```bash
curl -sI https://app.<domain>/ | tr -d '\r' | grep -i content-security-policy
grep -oiE 'href="[^"]*"' home.html | sort -u      # all nav/footer links
```

## 4. Single-request reachability (NOT scanning)
ONE `curl -sI -m 6 https://<host>/` per host — no paths, no fuzzing, no concurrency. Result tells you:
- reachable → `HTTP/1.1 200|302|401|403` plus a `Server:` banner (nginx/x, etc.)
- not reachable → empty (firewalled / private-IP-only)

One HEAD per host stays "one request", not a port scan. Never brute a path or loop an endpoint list.

## 5. Header posture snapshot
From the same HEAD output, grep: `strict-transport-security`, `x-frame-options`, `content-security-policy`, `referrer-policy`, `permissions-policy`, `server`, `www-authenticate`, `cf-ray`. Also read `CSP connect-src` for live API/WebSocket backends.

## 6. Passive complements
- **Wayback CDX** (historical params/endpoints):
  `curl -s "http://web.archive.org/cdx/search/cdx?url=<domain>*&output=text&fl=original&collapse=urlkey&limit=400"`
- **Public code:** GitHub API `users/<org>/repos`, `search/repositories?q=<name>`; raw SDK files often reveal the API base URL.
- **Email/DNS posture:** SPF (`~all` softfail vs `-all`), DMARC (`p=none|quarantine|reject`), CAA (which CAs allowed), TXT verification tokens. Extract `mailto:` addresses from CAA `iodef` / DMARC `rua`/`ruf` — a good source of the real security/devops contact.

## Boundary — what stays passive
Passive = data someone else already published (CT, DNS, archives, public code) + at most a **single GET/HEAD of a page that is intentionally public**.

**Stop before:** port scans, path/dir brute force, auth/login attempts, staging-environment probes, cloud-bucket enumeration, or anything that generates load on the target. Those require a verified authorization artifact (see SKILL.md Step 0).
