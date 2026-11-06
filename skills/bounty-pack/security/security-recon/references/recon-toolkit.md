# Recon Toolkit — 19 Recon Repos + Tool Selection Guide

## Attacker Recon Philosophy
Recon = finding ATTACK SURFACE, not just listing domains. Every subdomain = potential entry point. Every JS file = potential API endpoint. Every error message = potential info leak.

## Tool Selection by Attack Goal

| Goal | Primary Tool | Backup | Why |
|------|-------------|--------|-----|
| Find ALL subdomains | subfinder | amass passive | Fast, accurate, community sources |
| Find hidden subdomains | amass enum -passive | crt.sh | Certificate transparency |
| Check which are alive | httpx | curl loop | Status code + title + tech detect |
| Find open ports | naabu | nmap | Fast port scan, integrates with httpx |
| Find hidden paths | katana | gau + waybackurls | JS crawl discovers API endpoints |
| Historical endpoints | gau | waybackurls | Wayback Machine + common crawl |
| Find secrets in JS | katana -jc | grep manual | JS files contain API keys, tokens |
| Tech fingerprinting | whatweb | httpx -tech-detect | Identify CMS, framework, version |
| Subdomain takeover | dnsReaper | manual CNAME check | Dangling DNS records |
| Cloud storage | AWSBucketDump | manual S3 enum | Public buckets |
| DNS records | dig + whois | nslookup | Foundation of all recon |

## Recon Pipeline (Ordered by Attack Value)

```
Step 1: SUBDOMAIN ENUMERATION (find attack surface)
  subfinder -d TARGET -silent -o subs.txt
  amass enum -passive -d TARGET -o amass_subs.txt
  cat subs.txt amass_subs.txt | sort -u > all_subs.txt

Step 2: HOST DISCOVERY (find live targets)
  cat all_subs.txt | httpx -silent -status-code -title -tech-detect > live.txt
  awk '{print $1}' live.txt > live_hosts.txt

Step 3: PORT SCANNING (find services)
  naabu -list live_hosts.txt -top-ports 1000 -o ports.txt
  # naabu output + httpx = full service map

Step 4: ENDPOINT DISCOVERY (find attack paths)
  cat live_hosts.txt | gau --threads 5 | sort -u > urls.txt
  katana -list live_hosts.txt -jc -d 3 -o crawled.txt
  cat live_hosts.txt | waybackurls >> urls.txt
  cat urls.txt crawled.txt | sort -u > all_endpoints.txt

Step 5: JS ANALYSIS (find hidden APIs)
  cat all_endpoints.txt | grep "\\.js$" | while read js; do
    curl -s "$js" | grep -oP '"https?://[^"]+' | sort -u >> api_endpoints.txt
    curl -s "$js" | grep -iE 'api_key|token|secret|password|auth' >> secrets.txt
  done

Step 6: SENSITIVE FILE DISCOVERY
  for p in /.env /.git/HEAD /robots.txt /.DS_Store /backup /config /debug; do
    echo -n "$p: "
    curl -s -o /dev/null -w "%{http_code}" "https://TARGET${p}"
  done

Step 7: SUBDOMAIN TAKEOVER CHECK
  cat all_subs.txt | httpx -silent | grep -iE "CNAME|github.io|herokuapp|amazonaws"
  dnsreaper predict --domain TARGET

Step 8: CERTIFICATE TRANSPARENCY
  curl -s "https://crt.sh/?q=%.TARGET.com&output=json" | python3 -c "
  import sys,json
  data = json.load(sys.stdin)
  names = set()
  for entry in data:
    for name in entry.get('name_value','').split('\n'):
      names.add(name.strip())
  for n in sorted(names): print(n)
  " > ct_subs.txt
```

## Attacker-Specific Recon

### JavaScript Bundle Analysis (HIGH ROI)
```bash
# Find all JS bundles
curl -s "https://TARGET" | grep -oP 'src="[^"]+\.js"' | sed 's/src="//;s/"//' > js_bundles.txt

# Extract API endpoints from JS
cat js_bundles.txt | while read js; do
  curl -s "https://TARGET${js}" | grep -oP '"/api/[^"]+' | sort -u
done > api_from_js.txt

# Find hardcoded secrets
cat js_bundles.txt | while read js; do
  curl -s "https://TARGET${js}" | grep -oP '(api[_-]?key|token|secret|password|auth)["\s:=]+["\047][^"'\'']{8,}'
done > secrets_from_js.txt
```

### Error Message Mining
```bash
# Trigger errors to find internal paths
for p in /admin /api /graphql /debug /test /staging; do
  curl -s "https://TARGET${p}" | grep -iE "error|exception|stack|trace|debug|internal"
done > error_messages.txt
```

### Source Map Discovery
```bash
# Source maps contain original source code
curl -s "https://TARGET" | grep -oP 'src="[^"]+\.js"' | sed 's/src="//;s/"//' | while read js; do
  curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://TARGET${js}.map"
done | grep "^200" > source_maps_found.txt
```

## Integrated Repos (19)

| Repo | Stars | Attack Value |
|------|-------|-------------|
| owasp-amass/amass | 15.2K | Deep subdomain enumeration |
| projectdiscovery/naabu | 6.3K | Fast port scanning |
| projectdiscovery/httpx | 11K | Host discovery + tech detection |
| projectdiscovery/subfinder | 9K | Subdomain brute force |
| projectdiscovery/katana | 9K | JS-aware web crawler |
| sensepost/gau | 5K | Historical URL collection |
| tomnomnom/waybackurls | 5K | Wayback Machine endpoints |
| projectdiscovery/nuclei | 18K | Vulnerability scanning |
|OWASP/Amass | 15K | Passive DNS enumeration |
| punk-security/dnsReaper | 3K | Subdomain takeover detection |
| leebaird/discover | 4K | Recon automation scripts |
| yogeshojha/rengine | 9K | Automated recon pipeline |
| screetsec/Sudomy | 2.5K | Subdomain analysis |
| 1N3/BlackWidow | 2K | Web scanner + OSINT |
| m3n0sd0n4ld/GooFuzz | 1.5K | OSINT fuzzing |
| AlbusSec/Penetration-List | 1.5K | Vuln-type resource index |
| pikpikcu/airecon | 1K | AI recon agent |
| gl4ssesbo1/Nebula | 600 | Cloud recon framework |
| hisxo/ReconAIzer | 900 | Burp AI recon extension |

## Anti-Defense Recon

### WAF Detection
```bash
# Check if WAF is present
curl -s -I "https://TARGET" | grep -iE "server|x-powered|x-waf|x-cdn|cloudflare|akamai|aws"
# If WAF detected, use slower rate + random headers
```

### Rate Limit Bypass
```bash
# Rotate User-Agent
for ua in "Mozilla/5.0" "Googlebot/2.1" "curl/7.68"; do
  curl -s -H "User-Agent: $ua" "https://TARGET/api" &
done
wait
```

### Cloudflare Bypass
```bash
# Find origin IP behind Cloudflare
dig TARGET +short  # → Cloudflare IPs
# Check historical DNS
curl -s "https://api.hackertarget.com/dnslookup/?q=TARGET"  # → original IP
# Test origin directly
curl -s -H "Host: TARGET" "http://ORIGIN_IP/"
```
