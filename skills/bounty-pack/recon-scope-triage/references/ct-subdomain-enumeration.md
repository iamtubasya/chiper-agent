# Certificate Transparency → subdomain / infra enumeration (passive)

Use to enumerate a target's hostnames WITHOUT touching the target. CT logs are public and free, and
they routinely surface the highest-value passive surface: staging environments, `-v2` stacks, internal
service hostnames, log ingesters, evidence/compliance hosts, storage buckets, and link/email trackers.

## Recipe (certspotter first — crt.sh is frequently 502/rate-limited)

```bash
D=target.com
curl -s "https://api.certspotter.com/v1/issuances?domain=$D&include_subdomains=true&expand=dns_names" \
 | python3 -c "import sys,json;d=json.load(sys.stdin);\
   s=set(n for e in d for n in e.get('dns_names',[]));\
   print('\n'.join(sorted(x for x in s if x and '*' not in x)))"
```

- No-resolve / error guard: if the reply is a dict (`{'message':...}`) it's an error, not a list.
- crt.sh fallback: `https://crt.sh/?q=%25.$D&output=json` — expect 502/429; retry later, don't hammer.
- Dates/issuer: drop `expand=dns_names` — each entry then carries `not_before`/`not_after`/`id`
  (issuer *name* is often null on the free tier; certs are ~90-day so the window is short).

## Then resolve + classify (Cloudflare vs DIRECT origin)

- Resolve each name via DoH — pure public DNS, no contact:
  `https://dns.google/resolve?name=<host>&type=A` and `&type=CNAME`.
- Classify the A record:
  - **Cloudflare** (`104.16/12`, `104.20/14`, `172.64/13`, `172.66-67/16`, `188.114.96/20`, …) = proxied,
    origin hidden.
  - **Anything else** = a DIRECT origin IP that bypasses the WAF → the interesting surface.
    Common: GCP `34/8`,`35/8`; Hetzner `157.x`,`5.9/16`,`88.99/16`; Railway `69.46.46.x`; AWS `3/8`,`52/8`.
  - A private `10.x`/`192.168.x` A record published in PUBLIC DNS = an internal-topology leak (itself reportable).

## Reading the output (what typically falls out)

`staging.*` · `*-v2` / `app-v2` / `agents-v2` · `logs(-ingestor)*` · `evidence.*` · `comp.*` /
`api.comp.*` (compliance) · `synthea.*` (synthetic-patient generator) · `uploads.*` / `static.*` /
`public-*-media.*` · `t.*` / `trackmail.*` (link/email trackers) · `carejournal.*` (may be a different owner).

Then a LIGHT single GET/HEAD per name (not a port scan) to see what is publicly reachable vs
firewalled vs behind Zero-Trust. Examples of strong signals:
- a full app returning 200 on a `staging.` host (public non-prod environment),
- `Server: cloudflare` + `302 → <team>.cloudflareaccess.com` (protected, correct),
- Railway `{"status":"error","code":404,"message":"Application not found"}` = name points at Railway
  but no app is deployed (placeholder/retired).

## Pitfalls

- crt.sh 502/429 is common — certspotter is the reliable free source; neither shows hostnames that
  never held a cert.
- A name in CT may no longer resolve (retired) — always check A/CNAME before reporting it "exposed".
- Cloudflare-proxied names hide the origin — only direct-origin IPs are WAF-bypass surface.
- Enumerating CT is inherent to public certs; report the *exposed non-prod/internal* hosts as the
  finding, not "you have lots of subdomains".
