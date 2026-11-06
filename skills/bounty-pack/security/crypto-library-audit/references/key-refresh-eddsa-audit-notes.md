# Key Refresh & EdDSA Audit Notes — Fireblocks mpc-lib

## CMP Key Refresh (cmp_offline_refresh_service.cpp)
### Protocol Flow
1. Each player generates random seeds, encrypts for other players
2. Receive encrypted seeds from other players, decrypt
3. Compute PRF(seed, "x" || index) for each seed pair
4. Add other's PRF to own private key, subtract own PRF
5. Result: new_private_key = old_private_key + sum(other_prfs) - sum(own_prfs)
6. Sum of all new shares = same joint public key (refresh without changing pubkey)

### Preprocessing Data Refresh
- k and chi values also refreshed using same PRF mechanism
- chi adjusted for key change: chi_new = chi_old + (k_old * x_old) - (k_new * x_new)
- Ensures signing correctness with new key shares

### Security Properties
- Each player's PRF output is deterministic (same seed -> same PRF)
- Other players can't predict PRF output (seed encrypted under their Paillier key)
- Joint public key unchanged after refresh
- Old key shares securely deleted after refresh

### Verified Sound
- Seed encryption uses Paillier (additive homomorphic) -> properly encrypted
- PRF uses SHA256-based construction -> deterministic, no entropy issues
- Key material cleansed with OPENSSL_cleanse after use

## Ed25519 Algebra (ed25519_algebra.c, 1135 lines)
### Signing Nonce Generation (deterministic)
- k = SHA512(private_key || message) mod l
- Standard EdDSA pattern (RFC 8032)
- private_key is the raw scalar (32 bytes)
- Hash output reduced mod l (curve order)

### Verification
- Standard: s*G == R + H(R, A, msg)*A
- Point validation: on-curve check, non-infinity check
- s < L check (public, variable-time comparison OK)

### Scalar Operations
- Modular arithmetic over l (curve order)
- clamping applied during key generation
- Little-endian representation internally

## Key Files
- `cmp_offline_refresh_service.cpp:29-205` - key refresh flow
- `ed25519_algebra.c:624-669` - ed25519 signing
- `ed25519_algebra.c:671-760` - ed25519 verification
