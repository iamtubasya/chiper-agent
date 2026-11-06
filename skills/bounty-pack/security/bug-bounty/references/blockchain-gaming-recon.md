# Blockchain Gaming Infrastructure Recon — Aurory 2026-08-30

## Target Profile
- **Target:** Aurory (aurory.io) — blockchain game on Solana
- **Domains:** aurory.io (frontend), aurorynet.io (backend/RPC)
- **Tech:** K8s microservices, Envoy proxy, FusionAuth OAuth, Solana RPC

## Architecture Pattern

```
[Browser] → aurory.io (CloudFront + nginx)
                ↓
[Internal K8s Cluster (*.default.svc.cluster.local)]
   ├── aurorynet-api (backend)
   ├── auth-service (FusionAuth)  
   ├── solana-rpc (node)
   └── other microservices
```

**Key insight:** All backend APIs run on Kubernetes internal DNS (`*.default.svc.cluster.local`). These are NOT reachable from external. This is proper segmentation.

## Recon Results

### JS Bundle Analysis (7.5MB)
- 75+ JS chunk files analyzed
- Internal API endpoints extracted (all .default.svc.cluster.local)
- FusionAuth config: app IDs (prod + dev), client IDs
- No hardcoded API keys found
- No Solana private keys
- No embedded wallet mnemonics

### RPC Endpoints Found
| Endpoint | Type | CORS | Notes |
|----------|------|------|-------|
| rpc.aurorynet.io | Chain-index | `Access-Control-Allow-Origin: *` | Public, info disclosure |
| rpc.aurorynet.dev.aurory.io | Dev Chain-index | `Access-Control-Allow-Origin: *` | Dev env exposed |
| rpc-legacy.aurorynet.io | Legacy Chain-index | `Access-Control-Allow-Origin: *` | Old version |
| rpc.aurorynet.dev.aurory.io | Solana RPC | `Access-Control-Allow-Origin: *` | Direct Solana RPC |

### OAuth Configuration
- **Provider:** FusionAuth
- **Prod App ID:** 82ef5024-9104-4c07-b50-ae2b0e096e95
- **Prod Client ID:** 3b2b4f0a-2a57-4c25-9e45-fafab493e5a7
- **Dev App ID:** 0832daa1-bc24-4986-96dc-f2ac3c4e71dc
- **Dev Client ID:** 85f081a8-3279-4529-863c-968f469f6e5e
- **Token lifetime:** 3600 seconds
- **Scopes:** profile, email, openid, offline_access

### Cloudflare Rules (from JS)
- Bot score ≥ 4 and not bot → `Managed Challenge`
- Bot score < 4 and not bot → `Managed Challenge`  
- URI path = `/matrix` → `Managed Challenge`

### FingerprintJS
- **API Key:** 0MN0QnMnZKHnRH2PuVQI
- Endpoint: `https://cdn.aurory.io/fingerprint/v3/...`

### Deployments
- Production: FzRouter + WebEngine
- FzRouter v3 (next-gen)
- FzEngine
- Preprod (internal only)

## Findings

1. **CORS Misconfiguration on RPC** — `Access-Control-Allow-Origin: *` allows any origin to query blockchain data cross-origin. Informational (P4-P5).
2. **Dev Environment Exposed** — `rpc.aurorynet.dev.aurory.io` resolves publicly and responds to queries. Dev = weaker security controls. Worth testing further.
3. **Internal Architecture Leak** — JS bundles reveal entire K8s service topology. Not exploitable but reveals attack surface.

## What Was NOT Vulnerable

- **Internal APIs** — All on .default.svc.cluster.local, unreachable externally. This is proper segmentation.
- **No API keys in JS** — 7.5MB of JS, no hardcoded secrets found.
- **No private keys** — Solana keys properly managed server-side.
- **CloudFront CDN** — Properly configured, security headers present.
- **FusionAuth** — OAuth flow appears standard, redirect_uri validation needs further testing.
- **Nginx** — Server headers hidden, only shows "nginx".

## Lessons Learned

1. **K8s internal APIs are not vulns** — Recognize *.default.svc.cluster.local pattern early, don't waste time.
2. **Dev environment is worth testing** — Dev RPC endpoint publicly accessible = potential weaker controls.
3. **Solana RPC CORS is informational** — Not exploitable but worth noting.
4. **JS bundle value = OAuth config + endpoint discovery** — No secrets, but architecture mapping is valuable.
5. **7.5MB JS = 75 chunks** — This is normal for complex SPAs. Focus on endpoint URLs and auth config, not individual functions.
