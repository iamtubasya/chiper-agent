# FROST Protocol Audit Notes — Fireblocks mpc-lib

## Protocol Structure (2-of-2 EdDSA)
Files: `frost_cosigner_client.cpp`, `frost_cosigner_server.cpp`, `frost.h` (~1454 LOC total)

### Key Generation Flow
1. Client generates random secret → commitment, Schnorr proof → sends to server
2. Server validates, generates own share → commitment, Schnorr proof → sends to client
3. Both verify each other's Schnorr proofs → compute combined public key
4. Both verify combined public key matches

### Signing Flow
1. Server generates nonces (d, e) → D=d*G, E=e*G
2. Client generates nonces (d', e') → D'=d'*G, E'=e'*G
3. Common nonce R = D + D' + E + E'
4. Challenge c = H(X, msg, R)
5. Client: z2 = c*x2 + d' + e'*r2
6. Server verifies client's partial sig, computes z1 = c*x1 + d + e*r1
7. Final signature: s = z1 + z2

### Verified Correct
- Fiat-Shamir binding: challenge includes all public values (X, msg, R)
- Schnorr verification: g^z2 = X2^c · D2 · E2^r2 — equation correct
- Nonce contribution: R combines both parties' nonces — neither party controls R alone
- Commitment verification: server checks g^s2 == X2^c · D2 · E2^r2 before outputting
- Key verification: combined pubkey = sum of individual pubkeys, both sides verify

### Why Not Exploitable
1. Client can't choose D' to make R predictable — server's D,E unknown to client
2. Client can't manipulate r2 to bypass c*x2 — verification equation constrains all inputs
3. Server's private key x1 never transmitted — even with malicious client, x1 is safe
4. Both parties contribute to R → single party can't bias the nonce

### Version Constants
```
MPC_2PC = 1
MPC_CMP = 2  
MPC_CGGMP = 3
MPC_EXTENDED_MTA = 11
MPC_BAM_ECDSA = 13 (current)
```
