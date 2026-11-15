=== PoC: Paillier Blum Modulus ZKP — 80-round asymmetry ===
Target: mpc-lib/src/common/crypto/paillier/paillier_zkp.c
Code version: 2026-09 (Fireblocks mpc-lib)

CLAIM (confirmed via PoC):
- Generator `paillier_generate_paillier_blum_zkp` emits **80 rounds** 
  (`PAILLIER_BLUM_STATISTICAL_SECURITY = 80`)
- Verifier `paillier_verify_paillier_blum_zkp` checks **64 rounds**
  (`PAILLIER_BLUM_STATISTICAL_SECURITY_MINIMAL_REQUIRED = 64`)
- Rounds 64–79 are **deserialized but never verified**: `a[64..79]` and `b[64..79]`
  can be mutated to arbitrary values and the proof still passes verification.

Proof wire format (use_all_nth_roots = 0):
  [0..3]    n_len  (uint32, bytes-of-modulus)  e.g. 128 for 1024-bit key
  [4..4+n_len-1]  w  (PRF seed/entropy)
  For each round i = 0..79:
    x[i]     : n_len bytes  (commitment randomizer)
    z[i]     : n_len bytes  (only for i < 8 = MIN_NTH_ROOTS)
    a[i]     : 1 byte         (challenge/auxiliary value)
    b[i]     : 1 byte         (auxiliary value)

Per-round size = n_len + (i < 8 ? n_len : 0) + 2  bytes

Verify loop:
  for (i = 0; i < MINIMAL_REQUIRED; i++) {
    // 1. deterministic_rand(seed) -> y[i]
    // 2. check y[i] == x[i]^4 mod n
    // 3. check y[i] != 1 and y[i] != n-1
    // 4. compute x[i]^4 mod n via repeated squaring
  }
  // i iterates only 0..63. Rounds 64..79 not iterated.
  // No check of z[64..79], a[64..79], b[64..79].

Confirmed via PoC (4 test cases):
  - Flip a[79]  -> passes verification (unchecked round)
  - Flip a[63] -> rejected (last verified round)
  - Flip ALL a[64..79]+b[64..79] -> passes verification
  - Zero  a[64..79]+b[64..79] -> passes verification

Effective soundness: 2^-64 (not 2^-80). The 16 extra rounds are *redundancy* in the
generator but *unverified* in the verifier. Code comment explicitly states this
was decided during 2-out-of-2 MPC development.

Fuzzer pitfalls:
- `paillier_public_key_size(pub)` returns key SIZE IN BITS (1024) -- NOT the proof's n_len (128).
  Always read n_len from proof header: `*(uint32_t *)proof`
- Size-probe with NULL buffer + proof_len=0 returns PAILLIER_BUFFER_TOO_SMALL error
  -- use scratch buffer of generous size (65536) or allocate from proof_len first
- Verify total serialized size: calc = 4 + n_len + sum(round_size(i) for i=0..79)
  Must equal actual proof_len before doing in-place mutations.

PoC repo: ~/mpc-lib/fuzz/poc_blum_unverified.c