# CrowdProof Bug Bounty — Session 2026-08-27

## Target
- **Program:** CrowdProof (self-hosted bug bounty)
- **URL:** https://www.crowdproof.id/security
- **Scope:** Smart contracts, web app, API, ZK circuits
- **Rewards:** Critical $5K-$25K, High $2K-$5K, Medium $500-$2K, Low $100-$500
- **Contact:** security@crowdproof.id
- **Platform:** Self-hosted (not Bugcrowd/Immunefi)

## Tech Stack
- **Web App:** Next.js SPA (www.crowdproof.id), dark theme
- **API:** api.crowdproof.id (Azure App Service), api-testnet.crowdproof.id
- **Auth:** SIWE (Sign-In with Ethereum) + API key (X-API-Key header, `did_live_*` prefix)
- **DB:** SQL Server (Azure)
- **Infra:** Azure App Service + Cloudflare CDN
- **Smart Contracts:** Solidity 0.8.24, UUPS proxy, OpenZeppelin
- **ZK:** Circom 2.1.6, Groth16, Poseidon hash, EdDSA-Poseidon

## Smart Contracts Analyzed
1. **PaymentEscrow.sol** (408 lines) — Query fee management, revenue split (70/20/10), subscriptions, timelock
2. **ReputationOracle.sol** (346 lines) — On-chain score registry, ZK proof anchoring, challenge system
3. **DIDRegistry.sol** (266 lines) — EIP-1056 DID registry, meta-transaction support
4. **CredentialVerifier.sol** (289 lines) — Groth16 ZK proof verification, credential registry
5. **GovernanceToken.sol** (250 lines) — ERC20 + voting + staking + anti-whale + slashing

## ZK Circuits Analyzed
1. **AgeProof.circom** (~600 constraints) — Prove age >= threshold without revealing DOB
2. **KYCProof.circom** (~5000 constraints) — Prove KYC completion via EdDSA signature
3. **ReputationProof.circom** (~500 constraints) — Prove score >= threshold without revealing score

## Recon Results

### Web App
- Next.js SPA with catch-all routing (ALL paths return 200 with same HTML)
- CSP: `upgrade-insecure-requests` only (minimal)
- Security headers: HSTS, X-Frame-Options: DENY, X-XSS-Protection, X-Content-Type-Options
- No server/X-Powered-By headers leaked
- robots.txt: Disallow /portal/, /api/
- GitHub repo: `crowdpay/crowdproof-protocol` (public)

### API (api.crowdproof.id)
- All paths return 403 "Web App - Unavailable" (Azure App Service default page)
- Testnet (api-testnet.crowdproof.id) — DNS doesn't resolve
- SDK found API endpoints via GitHub repo

### SDK Discovered Endpoints
From `sdk/csharp/DecentraID.SDK/`:
- `/api/v1/scores` — GET reputation scores
- `/api/v1/scores/{address}` — GET score for address
- `/api/v1/proof/verify` — POST verify ZK proof
- `/api/v1/proof/generate` — POST generate ZK proof
- `/api/v1/identity/register` — POST register DID
- `/api/v1/credentials/verify-age` — POST age verification
- `/api/v1/dispute` — POST create dispute
- `/api/v1/dispute/{id}` — GET dispute details
- `/api/v1/dispute/wallet/{address}` — GET disputes by wallet
- `/api/v1/dispute/{id}/escalate` — POST escalate dispute
- `/api/v1/dispute/{id}/withdraw` — POST withdraw dispute

### GitHub Repo
- 166 files, 17 Solidity files, 3 Circom circuits
- Default branch: master
- Language: Solidity
- Stars: 0, Forks: 1

## Assessment

### Smart Contract Quality: HIGH ✅
- Solidity 0.8.24 (overflow protection built-in)
- UUPS proxy pattern (upgradeable)
- OpenZeppelin libraries (ERC20, AccessControl, Pausable, ReentrancyGuard)
- Proper role-based access control (GOVERNANCE_ROLE, ORACLE_ROLE, ISSUER_ROLE, etc.)
- ReentrancyGuard on all state-changing external functions
- Input validation on all parameters
- No obvious vulnerabilities found

### ZK Circuit Quality: HIGH ✅
- Standard circomlib components (Poseidon, EdDSA, comparators, Num2Bits)
- Proper range checks on all inputs
- Identity commitment verification
- No circuit-level vulnerabilities found

### Web App: LOW RISK
- Minimal CSP (only upgrade-insecure-requests)
- Standard security headers present
- No API endpoints accessible (Azure firewall)

### Verdict: ❌ NO REPORTABLE FINDINGS
- All contracts well-written with standard patterns
- API not yet deployed (403 on all paths)
- No exploitable attack surface discovered
- Smart contracts haven't been deployed to mainnet (no external audit mentioned)

## Key Learnings

### 1. SDK Reverse-Engineering for API Discovery
When API docs are inaccessible (403/WAF), clone the project's SDK repo to find:
- Base URLs (mainnet/testnet)
- Auth patterns (API key header name, token format)
- Endpoint paths (from module/service files)
- Module structure (reveals functional areas)

**This technique turned "nothing accessible" into full API map in 5 minutes.**

### 2. Azure App Service "Web App - Unavailable"
When you see this HTML response with 403 status:
```html
<!DOCTYPE html><html><head><title>Web App - Unavailable</title>
```
It means the Azure App Service is configured but the app is stopped/not deployed. NOT a WAF block. NOT a firewall. The app literally isn't running.

### 3. Next.js Catch-All Routing
Next.js SPA returns 200 for ALL routes including `/api/*`, `/graphql`, `/.env`, `/api/internal/debug`. They all serve the same catch-all HTML page. Don't mistake this for actual API endpoints.

**Test:** Check Content-Type — if it's `text/html` for an API path, it's just the SPA catch-all.

### 4. Smart Contract Quick Triage
For Web3 bug bounty, check BEFORE deep analysis:
1. Repo for KNOWN_ISSUES.md / SECURITY.md / audit reports
2. Contract count + total lines of code
3. Library usage (OpenZeppelin = good sign)
4. Standard patterns (UUPS, AccessControl, ReentrancyGuard)
5. If all standard + well-written → pivot early

### 5. ZK Circuit Quick Check
For ZK circuits, check:
1. Standard circomlib includes (Poseidon, EdDSA, comparators)
2. Proper range checks on all inputs
3. Commitment verification (identity/score commitments)
4. If all standard → no novel findings likely
