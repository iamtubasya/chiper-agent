# MPC Version Downgrade Analysis — Fireblocks mpc-lib

## The Pattern
```cpp
// cmp_setup_service.cpp:150
if (version > MPC_PROTOCOL_VERSION) {  // BUG: should be != or >=
    throw_cosigner_exception(INVALID_PARAMETERS);
}
temp_data.version = version;  // Stores lower version
```

## Why It Seems Exploitable
- Attacker claims version=10 (old), real version=13
- `use_extended_seed` flag: `(temp_data.version >= MPC_EXTENDED_MTA) ? 1 : 0`
- Version 10 → `use_extended_seed=0` → weaker seed derivation in ZKP range proofs
- Old seed: `SHA256(SALT, aad, message, commitment, proof.A, proof.Bx, proof.By, proof.E, proof.F, proof.S, proof.T)` — less parameter binding

## Why It's NOT Exploitable (2-Party)
1. **Both parties use same `metadata.version`** during signing
2. Honest party's `metadata.version` = 10 (stored during keygen with attacker)
3. Attacker can't send version > 10 during signing (`version > metadata.version` rejected)
4. Honest party generates MtA proofs using version 10 (old seed) — **same as attacker**
5. No prover/verifier mismatch → ZKPs verify correctly
6. Result: Both sides use weaker but **consistent** proof system

## When It WOULD Be Exploitable
- **Multi-party (3+):** If parties A and B agree on version 10 but party C uses version 13
- **Independent version tracking:** If each party stores their own version independently
- **Version negotiation per-round:** If signing allows per-round version changes

## Key Files
- `cmp_setup_service.cpp:130-175` — `store_setup_commitments` (version acceptance)
- `cmp_setup_service.cpp:241,292` — `use_extended_seed` decision
- `cmp_ecdsa_online_signing_service.cpp:148-160` — signing version check
- `mta.cpp:988,1596` — `_version >= MPC_EXTENDED_MTA` in batch verifier
- `mta.cpp:83-113` — `generate_mta_range_zkp_extended_seed` (stronger)
- `mta.cpp:115-132` — `generate_mta_range_zkp_seed` (weaker)
