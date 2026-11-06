# Fireblocks Bug Bounty — Session 2 (2026-09-02)

**Target**: Fireblocks (fireblocks.com)
**Platform**: Bugcrowd (`fireblocks-mbb-og`)
**Scope**: Web App, API, Smart Contracts (ETH + BNB)
**Researcher**: BC_USERNAME

## Findings Verified (6 total)

### FINDING 1: env-config.js Information Disclosure (MEDIUM)
- **URL**: `https://console.fireblocks.io/v2/env-config.js`
- **Auth**: None (HTTP 200, 1800 bytes)
- **Leaked**: Auth0 client IDs, Cloudinary preset, Stripe live key, Datadog RUM, LaunchDarkly, Pendo, build version

### FINDING 2: JS Bundle Hardcoded Test Secret (MEDIUM)
- **File**: `index-8iOyoAr8-bundle.js`
- **Secret**: `SLDJSADLALSKDJASLDK`
- **Impact**: Hardcoded secret in production bundle

### FINDING 3: GaslessFactory No Access Control (HIGH — by design)
- **Contract**: `GaslessFactory.sol`
- **Issue**: `deploy()` and `deployDeterministic()` have zero access control
- **Note**: Comments indicate this is intentional ("anyone can deploy"), but still exploitable if factory is used in production

### FINDING 4: Console JWT Missing Security Claims (LOW)
- **JWT Claims**: Only `userId`, `iat`, `exp`
- **Missing**: `iss`, `aud`, `sub`, `jti`, `scope`, `azp`
- **Impact**: Token replay, no issuer/audience validation

### FINDING 5: Cloudinary Unrestricted Upload (LOW)
- **URL**: `https://api.cloudinary.com/v1_1/fireblocks/raw/upload`
- **Preset**: `kgdyxtmr`
- **Response**: HTTP 200 (accepts files without auth)

### FINDING 6: Auth0 Configuration Disclosure (LOW)
- **Endpoint**: `https://auth.fireblocks.io/.well-known/openid-configuration`
- **Notable**: `password` grant enabled, `plain` PKCE, `token_endpoint_auth_methods: ["none"]`

## Attack Vectors Tested (Negative Results)

| Vector | Result | Notes |
|--------|--------|-------|
| JWT 'none' algorithm | 403 ✅ | Blocked |
| JWT RSA→HS256 key confusion | 403 ✅ | Blocked |
| JWT IDOR (modified userId) | 403 ✅ | Blocked |
| LFI/SSI via paths | SPA catch-all ✅ | 200 with text/html |
| CORS misconfiguration | No CORS headers ✅ | Safe |
| GraphQL introspection | CloudFront 403 ✅ | POST blocked |
| Email enumeration | Generic error ✅ | "Wrong email or password" |
| Auth0 device code grant | `unauthorized_client` ✅ | Grant disabled |

## Smart Contract Analysis

**Contracts analyzed**: GaslessFactory, GaslessToken, GaslessForwarder, GaslessRegistry, TrustedForwarder, ERC20F, ERC721F, ERC1155F, FungibleLayerZeroAdapter

**Key observations**:
- All ERC20/721/1155 contracts use role-based access control (MINTER_ROLE, BURNER_ROLE, UPGRADER_ROLE)
- UUPS upgradeable pattern used throughout
- ReentrancyGuard present on external call functions
- SalvageCapable pattern for stuck ETH recovery
- TrustedForwarder extends OpenZeppelin ERC2771Forwarder (standard)
- GaslessFactory is the ONLY contract without access control

**CloudFront GraphQL**: All POST requests to GraphQL endpoint blocked by CloudFront (returns 403). This prevents API-level testing via curl/Python. Browser tools would be needed for GraphQL testing.
