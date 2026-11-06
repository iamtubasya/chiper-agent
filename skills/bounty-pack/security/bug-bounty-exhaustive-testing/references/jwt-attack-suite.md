---
author: RESEARCHER_NAME
tags: [jwt, authentication, crypto-platform, attack-suite]
---

# JWT Attack Suite — Crypto Platform Results

**Source:** TurboFlow.xyz audit (Sept 2026)
**Target:** Crypto perpetuals trading (Privy wallet auth)

## Tests Conducted

### 1. `none` Algorithm
Craft JWT with `"alg":"none"`, empty signature.
**Result:** Backend validates 3-segment structure. Returns `errno:104` (invalid token). `none` rejected.

### 2. Leaked Keys as HS256 Secret
Test hardcoded keys from JS bundles as signing secrets.
**Result:** All fail. Keys are for external APIs, not JWT.

### 3. Algorithm Confusion (RS256→HS256)
Change `alg` header, sign with public key.
**Result:** Backend ignores `alg` header, validates against stored secret.

### 4. Common Secrets
Test 10+ common secrets (secret, password, changeme, etc.).
**Result:** All fail. Strong random secret.

## Error Code Interpretation

| Error Code | Meaning | Implication |
|-----------|---------|-------------|
| `errno:104` | Invalid token | JWT valid structure, wrong sig → endpoint EXISTS |
| `errno:101` | Param invalid | JWT not recognized → endpoint doesn't use JWT |
| `errno:102` | Path not found | SPA catch-all → NOT real endpoint |
| `errno:103` | Validation failed | Backend PROCESSING signature (not just checking presence) |

## Internal Error Leak

Malformed signatures to `/login`:
```json
{"msg":"10010040-Get signature hash exception","errno":103}
```
- `10010040` = Java-style internal error code
- `Get signature hash exception` = BouncyCastle/Java crypto library
- Leaks: Java backend, BouncyCastle, hash computation step

## Backend Behavior Summary
- Validates JWT structure (3 segments) BEFORE signature check
- Ignores `alg` header — uses configured algorithm
- No timing oracle leakage
- Same error for all JWT attacks

## Takeaway
If JWT is properly secured (none rejected, no leaked secrets, no algorithm confusion), **pivot to other vectors**: CORS, business logic, rate limiting, error disclosure. Don't waste time on JWT brute force.
