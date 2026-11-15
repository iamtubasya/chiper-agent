# BAM ECDSA Protocol Audit Notes — Fireblocks mpc-lib

## Protocol Overview
BAM = Ballot-based AMF (Asymmetric Multi-Party) protocol for ECDSA signing.
Files: `bam_ecdsa_cosigner_server.cpp` (974 lines), `bam_ecdsa_cosigner_client.cpp` (789 lines), `bam_ecdsa_cosigner.cpp`, `bam_well_formed_proof.cpp` (491 lines)

## Key Innovation: r Correction Mechanism
BAM uses a unique `POSITIVE_R` flag to ensure the signature's `r` value is positive (low-S normalization).

### Client-side r Correction (lines 716-736)
```
1. Compute corrected_R = R_com + R_client^{H(X||R_client||R_com||m)}
2. r = x(corrected_R)
3. If r not positive:
   - Save original corrected_R as tmp
   - Loop: corrected_R += tmp (add original R), increment counter
   - After loop: k_client' = k_client * r_correction_cycles
4. Compute v = k_client'^{-1} * r
5. Compute u = (r * derived_private_share + hash) * k_client'^{-1}
6. Generate well-formedness ZKP for (u, v)
```

### Server-side r Correction (lines 847-866)
```
1. Recompute corrected_R from public data (same as client)
2. r = x(corrected_R)
3. If r not positive:
   - Same loop as client (add original R, increment counter)
   - NO k adjustment needed (server uses original k_server for decryption)
4. Verify client's well-formedness ZKP against ORIGINAL R_server
5. Decrypt partial signature, compute s
```

### Cross-Party Invariant
- Both parties compute SAME correction factor (r_correction_cycles)
- Client scales k_client by factor -> maintains consistency with corrected R
- Server does NOT scale k_server -> uses original for well-formedness verification
- Server's verification uses original R_server (line 884: generator_mul(k_server))
- Well-formedness proof binds to original R, not corrected R

### Why Sound
1. Client can't use different r_correction_cycles than server - both compute from same public data
2. Server verifies against original R -> client's proof must be consistent with original R
3. Scaling k_client by factor maintains mathematical consistency: R_new = g^{k*t} = (g^k)^t = R_original^t
4. POSITIVE_R is deterministic - same input -> same output on both sides

## Well-Formedness Proof (ZKP)
### Structure
- EC equation: g^z1 * f^z2 * f^w0 == V * U^e (Pedersen commitment)
- Paillier equation: Enc(z1, rho^w2) * E^z2 == D * S^e mod n^2 (Paillier commitment)
- Range proofs: z1, z2 bounded by security parameters

### Serialization
- assert() calls in serialize/deserialize (lines 100, 159, 188, 197, 204)
- Compile out in release builds (NDEBUG)
- NOT exploitable: cryptographic verification runs after deserialization
- Extra trailing bytes silently ignored during deserialization
- But PowSumProof/ProductProof verification catches invalid data

### Verification Flow (verify_signature_proof)
1. Check encrypted_signature is coprime with Paillier N
2. Deserialize proof
3. Range checks on z1, z2 (BN_cmp against bounds)
4. Compute e = H(encrypted_signature, encrypted_share, signature_aad, ec_base, paillier, r_server)
5. EC equation check: g^z1 * f^z2 * f^w0 == V * U^e
6. Paillier equation check: Enc(z1, rho^w2) * E^z2 == D * S^e mod n^2
7. Both checks must pass -> proof is valid

## Key Files
- `bam_ecdsa_cosigner_server.cpp:830-866` - r correction (server)
- `bam_ecdsa_cosigner_client.cpp:670-780` - r correction (client) + proof generation
- `bam_well_formed_proof.cpp:372-486` - verify_signature_proof
- `bam_well_formed_proof.cpp:57-101` - serialize_well_formed_proof
- `bam_well_formed_proof.cpp:103-160` - deserialize_well_formed_proof
