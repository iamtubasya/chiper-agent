# Infrastructure Pivot Patterns — When WAF/Cloudflare Blocks You

## Core Principle
The main API is NOT the attack surface. The entire infrastructure ecosystem is. When Cloudflare/WAF blocks you, systematically find services that bypass it.

## Methodology: Non-Cloudflare Service Discovery

### Step 1: Certificate Transparency Enumeration
```bash
# Get ALL subdomains from CT logs (bypasses Cloudflare)
curl -s "https://crt.sh/?q=%.TARGET.COM&output=json" | \
  python3 -c "import sys,json; [print(d['name_value']) for d in json.loads(sys.stdin.read())]" | \
  sort -u > /tmp/subs.txt
```
**Why CT logs:** Every TLS cert issued is logged publicly. Even behind-Cloudflare services must get certs, so CT reveals them. Cloudflare doesn't proxy ALL subdomains — peripheral services often sit outside.

### Step 2: Bypass Check Per Subdomain
```bash
# For each subdomain, test if Cloudflare blocks you
while read sub; do
  status=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $sub" "https://$sub/" --max-time 5 2>/dev/null)
  if [ "$status" = "000" ]; then
    echo "TIMEOUT: $sub"
  elif [ "$status" = "1009" ] || [ "$status" = "1020" ]; then
    echo "BLOCKED: $sub (CF error $status)"
  elif [ "$status" != "000" ]; then
    echo "ACCESSIBLE: $sub (HTTP $status)"
  fi
done < /tmp/subs.txt > /tmp/results.txt

# Show accessible (non-Cloudflare) services
grep "ACCESSIBLE" /tmp/results.txt
```

### Step 3: Classify Accessible Services
Common peripheral services that bypass Cloudflare:
- **Monitoring/Analytics**: datadog-forwarder, sentry, newrelic, segment, event-router
- **Health/Status**: health, status, readiness, liveness endpoints
- **Internal Tools**: research apps, admin portals, handbooks, wikis
- **SSO/Identity**: SSO login pages (Okta, LumApps, Auth0)
- **Storage**: S3 buckets, CloudFront distributions
- **QA/Staging**: qa, staging, dev, test subdomains

### Step 4: Test Each Category

**A. Monitoring Endpoints (Datadog/Sentry/etc):**
```bash
# Test without API key
curl -s -w "\nHTTP:%{http_code}" -X POST \
  "https://TARGET-datadog-forwarder.com/api/v2/series" \
  -H "Content-Type: application/json" \
  -d '{"series":[{"metric":"test.metric","type":0,"points":[{"timestamp":UNIX,"value":1}],"tags":["test"],"source_type_name":"custom"}]}'
# 202 = success, 403 = auth required
```

**B. Health/Status Endpoints:**
```bash
curl -s "https://TARGET-health.com/health"
# Look for: container names, DB IDs, AWS regions, build info
```

**C. Event Endpoints:**
```bash
# Test with empty payload first
curl -s -X POST "https://TARGET-event-router.com/track" \
  -H "Content-Type: application/json" \
  -d '{"events":[]}'
# Check for: validation errors that reveal schema, accepted field names
```

**D. Internal Tools:**
```bash
# Check for exposed Django/Flask/FastAPI apps
curl -s "https://TARGET-internal.com/" | grep -oP '<title>[^<]+</title>'
curl -s "https://TARGET-internal.com/admin/"
curl -s "https://TARGET-internal.com/api/"
```

**E. SSO/Identity:**
```bash
# Test redirect chains
curl -s -L -o /dev/null -w "%{url_effective}\n%{redirect_url}" "https://TARGET-sso.com/"
# Look for: Okta org IDs, LumApps org IDs, login provider IDs
```

## Finding Classification

| Service Type | Typical Finding | VRT Match | Severity |
|---|---|---|---|
| Unauthenticated monitoring injection | Datadog metric pollution → corrupted dashboards | Infrastructure Misconfiguration | P2-P3 |
| Health info disclosure | AWS region, container names, DB IDs leaked | Information Disclosure | P4-P5 |
| Open event ingestion | Event stream poisoning → analytics corruption | Infrastructure Misconfiguration | P3-P4 |
| SSO config leakage | Internal identity provider IDs exposed | Information Disclosure | P4-P5 |
| Internal tool exposure | Django/Flask apps without access control | Infrastructure Misconfiguration | P3-P4 |

## Viability Gate for Infrastructure Findings

**Strong if:**
- Unauthenticated access to production monitoring (Datadog, Sentry)
- Ability to inject data that affects dashboards/alerts/metrics
- Real operational impact (alert fatigue, SOC blindness, wrong business decisions)

**Weak if:**
- Informational-only (version strings, health status without sensitive data)
- Rate-limited injection (prevents DoS but not pollution)
- Read-only access with no write capability

## Real Examples (Chime Financial 2026-09)

### F1: Datadog Forwarder — Production Metric Injection
- `datadog-forwarder.chime.com` accepted POST with NO API key
- All 4 metric types (gauge/count/rate/count) accepted
- Arbitrary metric names, tags, and resources accepted
- Metadata endpoint revealed internal enum (`origin.Origin.Product`)
- **Impact:** Corrupted dashboards → wrong operational decisions

### F2: Event Router — Open Event Ingestion
- `event-router.chime.com/track` accepted empty event arrays
- Pydantic validation errors leaked field schema
- Real event names from APK triggered HTTP 500 (no crash protection)
- **Impact:** Event stream pollution → corrupted analytics

### F3: Health Endpoint — Infrastructure Disclosure
- `nd.chime.com/health` exposed container names, DB IDs, AWS regions
- No authentication required
- **Impact:** Reconnaissance data for targeted attacks

### F4: HeyMarvin Multi-Stack Infrastructure
- `beta.heymarvin.com` = Next.js (build manifest reveals ALL routes)
- `demo.heymarvin.com` = Django (CSRF tokens, Django admin patterns)
- Both have open `/accounts/signup/` and `/accounts/password_reset/`
- **Key insight:** Different subdomains running different stacks = different attack surfaces. Next.js has build manifest leaks; Django has CSRF/admin patterns. Test BOTH independently.

### F5: CloudFront vs Cloudflare — Different Bypass Strategies
- CloudFront distributions directly accessible = no Cloudflare protection
- Cloudflare 1009 = geo-restriction (NOT bypassable with headers)
- Cloudflare 1020 = custom rule (MIGHT be bypassable with header manipulation)
- **Strategy:** CloudFront → direct IP → Host header; Cloudflare → need geo-proxy

## Pitfall: CT Logs Miss Some Services
Not all subdomains have public TLS certificates. Some use wildcard certs. Cross-reference with:
- DNS history (SecurityTrails, VirusTotal)
- Shodan/Censys queries
- Google dorking (`site:*.target.com -www`)
- Mobile app string extraction (decompiled APKs reveal internal endpoints)
