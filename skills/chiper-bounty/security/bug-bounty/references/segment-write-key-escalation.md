# Segment Write Key Escalation Testing

When you find a Segment write key (32-char alphanumeric), test whether it can read data in addition to writing:

## Step 1: Verify Write Works
```bash
# Track event
curl -s -X POST "https://segment.TARGET.com/tracking/v1/track" \
  -H 'Content-Type: application/json' \
  -u '<write_key>:' \
  -d '{"userId":"test","event":"security_test","properties":{"source":"bugbounty"}}'

# Identify traits
curl -s -X POST "https://segment.TARGET.com/tracking/v1/identify" \
  -H 'Content-Type: application/json' \
  -u '<write_key>:' \
  -d '{"userId":"test","traits":{"role":"admin","isPremium":true}}'
```

## Step 2: Test Read Endpoints
```bash
# Try read endpoints (most write keys reject these)
for endpoint in "/tracking/v1/batch" "/tracking/v1/import" "/tracking/v1/identify" "/tracking/v1/groups" "/tracking/v1/track"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "https://segment.TARGET.com$endpoint" -u '<write_key>:')
  echo "$endpoint → $code"
done
```

## Step 3: Multi-Environment Extraction
Segment write keys often appear in JS bundles across MULTIPLE environments (prod, dev, staging). If ANY key is read-enabled across ANY environment, ALL environments' data is at risk.

```bash
# From build manifest, extract keys per environment
for env in assets devassets stageassets; do
  curl -s "https://$env.TARGET.com/_next/static/$BUILD_ID/_next/en-US/6._sharedentry.js" \
    | grep -oE '[a-zA-Z0-9]{32,}' | head -5
done
```

## Impact Assessment
| Write-Only (Low) | Read-Enabled (Medium-High) |
|------------------|---------------------------|
| track/identify/alias return `{"success": true}` | batch/import/identify return actual user data |
| No data can be extracted | User PII, analytics data accessible |
| Data injection only | Full data exfiltration |
| Severity: P5 | Severity: P2-P3 |
| **Write-only + no downstream consumer** | **Read-enabled + CRM sync present** |
| **→ Still P5** | **→ P2-High** |

## Bitso 2026-09-06 — Confirmed Write-Only Results (4 Environments)
- **Tested 4 JS bundles** across assets, devassets, stageassets, mobileassets
- All `track`/`identify`/`page`/`group`/`alias`/`batch` → `{"success": true}`
- ALL read endpoints (GET /batch, GET /import, GET /identify, GET /groups) → 404 or 000
- Hightouch US + EU endpoints: write-only, no downstream consumer proven
- **Conclusion:** Write-only across ALL environments = P5 informational
- **Cross-environment pattern:** Keys persist across bundle boundaries — testing 1 environment informs all, BUT always verify read capability per key per environment
