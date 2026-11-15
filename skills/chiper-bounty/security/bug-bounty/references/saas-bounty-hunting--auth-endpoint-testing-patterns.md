# Auth Endpoint Testing Patterns — Rate Limiting & Version Disclosure

> Reference for saas-bounty-hunting Phase 1 (Auth Wall Detection).
> Derived from Arlo bug bounty session (2026-08-27).

---

## Rate Limiting Absence Testing

When login/registration endpoints exist, ALWAYS test for rate limiting. This is a standalone Medium finding if absent.

### Test Method
```bash
# Test 50 rapid login requests with varying credentials
for i in $(seq 1 50); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "TARGET/hmsweb/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"test$i@test.com\",\"password\":\"wrong$i\"}")
  echo "Req $i: [$code]"
  [ "$code" == "429" ] && echo "RATE LIMITED at request $i" && break
  [ "$code" == "403" ] && echo "IP BLOCKED at request $i" && break
done
```

### What to Check
- HTTP 429 (Too Many Requests) = rate limiting present
- HTTP 403 after N requests = IP blocking
- Increasing response delays = soft rate limiting
- CAPTCHA trigger after N requests = progressive defense
- **ALL returning same code (401/400) = NO rate limiting = finding**

### Severity Classification
- **Medium:** No rate limiting + auth endpoint exposed = brute force / credential stuffing
- **Low-Medium:** Rate limiting exists but too generous (100+ req/min)
- **Info:** Rate limiting properly enforced

### Registration Endpoint Check
```bash
# Also test registration for rate limiting
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "TARGET/hmsweb/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"newuser$i@test.com\",\"password\":\"Test12345!\"}")
  echo "Req $i: [$code]"
done
# No rate limiting = bulk account creation possible
```

---

## Version/Infrastructure Disclosure

Unauthenticated version endpoints leak internal infrastructure details.

### Test Method
```bash
for ep in /version /status /info /config /health /metrics /prometheus; do
  resp=$(curl -sk "https://TARGET$ep" 2>/dev/null)
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://TARGET$ep" 2>/dev/null)
  echo "[$code] $ep → $(echo $resp | head -c 300)"
done
```

### Common Leaks
| Field | Example | Risk |
|-------|---------|------|
| Server name | `nginx-clientapi` | Internal naming convention |
| Environment | `prod/`, `staging/`, `dev/` | Deployment target confirmed |
| Infrastructure | `EKS`, `ECS`, `CloudRun` | Cloud provider + orchestrator |
| Version | `v6.32.0` | Software version for CVE matching |
| Model | `claude-sonnet-4-20250514` | LLM model for targeted attacks |

### Arlo Example
```json
{"name":"nginx-clientapi","version":"prod/","infra":"EKS"}
```
Reveals: internal service name (`nginx-clientapi`), production environment, AWS EKS (Kubernetes).

### Severity
- **Low-Medium** standalone
- **Escalates to Medium** when combined with CNAME/K8s cluster name disclosure (full infrastructure map enables targeted container/pod attacks)

---

## S3 Bucket Region Disclosure

S3 403 responses leak the bucket's AWS region via headers.

### Test Method
```bash
curl -I "https://BUCKET.s3.us-west-2.amazonaws.com/"
# 403 Forbidden
# x-amz-bucket-region: us-west-2  ← REGION LEAKED
# x-amz-request-id: QPRQ67N4ADEVT49A  ← CONFIRMS REAL BUCKET
```

### Key Insight
The `x-amz-bucket-region` header is returned EVEN ON ACCESS DENIAL. This confirms:
1. Bucket EXISTS (not 404)
2. Bucket is in specific region
3. Bucket name is real (not honeypot)

### Combined with JS Bundle Analysis
If JS bundle contains S3 object paths (e.g., `BUCKET/path/to/object`), the region disclosure enables:
- Targeted object enumeration in correct region
- Potential object-level IDOR if auth bypass found
- SSRF via S3 signed URL generation
