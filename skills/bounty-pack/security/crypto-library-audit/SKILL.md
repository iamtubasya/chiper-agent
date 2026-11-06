---
name: crypto-library-audit
author: RESEARCHER_NAME
description: "Audit cryptographic libraries and MPC protocol implementations (C/C++/Rust/JS). Find crypto weaknesses: undersized parameters, broken invariants, seed/entropy flaws, arithmetic mode switches. Distinct from smart-contract-audit (on-chain) and smart-contract-audit-lab (Foundry toolchain)."
metadata:
  hermes:
    tags: [cryptography, mpc, multi-party-computation, paillier, secure-multiparty, cryptanalysis, library-audit, fireblocks, ncw, threshold-signature]
---

# Crypto Library Audit — Cryptographic Implementation Security

## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

## ⛔ REFERENCE AUTO-LOAD (MANDATORY — load when this skill is activated)
When this skill is loaded, IMMEDIATELY read these reference files:
```
read_file('references/blum-zkp-80-round-asymmetry.md')
read_file('references/fireblocks-mpc-lib-mta-analysis.md')
read_file('references/frost-protocol-audit-notes.md')
read_file('references/mpc-version-downgrade-analysis.md')
read_file('references/bam-protocol-audit-notes.md')
read_file('references/key-refresh-eddsa-audit-notes.md')
```

**Audit C/C++/Rust/JS cryptographic libraries for implementation weaknesses** — distinct from smart contract audits (Solidity/Foundry) and web/API pentesting. Focus: parameter sizing, primitive correctness, protocol invariants, entropy handling.

## Triggers
- Cloning a crypto library for audit (mpc-lib, libsecp256k1, blst, circl, etc.)
- Multi-party computation protocol review
- Threshold signature scheme analysis
- Paillier / additive homomorphic encryption audit
- MPC coordinator or key management system audit
- MtA (multiplicative-to-additive) protocol verification
- Batch verification parameter analysis
- Seed/entropy generation in cryptographic contexts

## Inputs
- **target** — repo URL or local path to crypto library
- **protocol** — specific protocol to audit (MtA, GG20, CGGMP, Frost, etc.)
- **focus** — parameter sizing, primitive correctness, entropy, or all

## Methodology — 5-Phase Crypto Audit

### Phase 1: REPO RECON (5 min)
```
1. Clone repo + identify languages (C++, Rust, JS, Python)
2. Find protocol implementation files:
   - grep -rn "verify\|mta\|paillier\|batch\|seed\|entropy\|random" --include="*.cpp" --include="*.h" --include="*.c"
3. Locate security constants:
   - grep -rn "BATCH_STATISTICAL_SECURITY\|SECURITY_PARAMETER\|STATISTICAL\|Kappa\|Lambda\|Sigma" --include="*.h" --include="*.hpp"
4. Identify cryptographic primitives used:
   - Paillier (additive homomorphic), ECDSA, Schnorr, Pedersen commitments
   - Hash functions (SHA256, Blake2, etc.)
   - Random number generation (OpenSSL RAND, /dev/urandom, CTR-DRBG)
5. Map code structure: which files implement which protocol phases
```

### Phase 2: PARAMETER TRACING (15 min) — HIGHEST ROI
**This is where most crypto implementation bugs hide.**

For each security parameter found:
1. **Read its value** (e.g., `BATCH_STATISTICAL_SECURITY = 5`)
2. **Trace every usage** — where is it used as a loop bound, bit width, or security level?
3. **Verify sufficiency** against cryptographic literature:
   - Paillier batch verification: security parameter should match statistical security parameter (typically 40-128 bits)
   - If `uint8_t` is used for security parameter → MAX 255, but also means only 8 bits of randomness
   - If random coefficients are 8-bit → only 256 possible values → negligible statistical security
4. **Check for type truncation** — is the parameter cast from a larger type?
5. **Cross-reference with protocol papers** — compare against GG20, CGGMP, or original paper specifications

**Critical pattern (Fireblocks mpc-lib 2026):**
- `BATCH_STATISTICAL_SECURITY = 5` in `mpc_globals.h`
- Used as loop bound in `mta.cpp` batch verification
- Random coefficients `r_i` generated as `uint8_t` — only 8 bits of randomness
- 2^8 = 256 possible values → statistical security ≈ 0 (should be 2^40+)
- Root cause: parameter was set for testing performance, never increased for production

### Phase 3: CRYPTO PRIMITIVE ANALYSIS (20 min)

#### 3a. Randomness & Entropy
- How are random numbers generated? (OpenSSL RAND, OS entropy, deterministic PRNG?)
- Are seeds passed correctly? Is there buffer over-read?
- Is the random oracle model correctly instantiated?
- **Seed generation pitfall:** Buffer size mismatch with requested random bytes → over-read returns garbage from adjacent memory

```cpp
// VULNERABLE pattern — over-read
unsigned char seed[28];
RAND_bytes(seed, 32);  // Reads 4 bytes past buffer!
```

#### 3b. Arithmetic Mode Correctness
- Does the code correctly switch between additive/multiplicative domains?
- Are Paillier operations (Enc, Dec, Add, Mul) correctly implemented?
- Does batch verification agree with single verification?
- **Critical:** Batch verification must be mathematically equivalent to iterating single verification. Any shortcut must preserve the security proof.

#### 3c. Zero-Knowledge Proofs
- Are ZK proofs (Range proofs, Sigma protocols) correctly implemented?
- Do verification equations match the prover's computation?
- Are challenge elements properly derived (Fiat-Shamir)?
- Is statistical security parameter consistent across all ZK components?

#### 3d. Commitment Schemes
- Pedersen commitment: are generators correctly chosen?
- Is the hiding/binding property preserved in batch operations?
- Cross-check: verify that `Commit(m, r) = g^m * h^r` matches implementation

### Phase 4: PROTOCOL FLOW ANALYSIS (15 min)
- Map the full protocol flow (e.g., GG20 signing rounds)
- For each round: what is sent, what is verified, what state is maintained?
- Check: does any party learn more than intended?
- Check: can a malicious party deviate from protocol without detection?
- Check: are abort/failure modes handled safely?

### Phase 5: EXPLOITABILITY ASSESSMENT (10 min)

**For each finding, answer:**
1. Can an external attacker exploit this? (or only a malicious MPC participant?)
2. What is the concrete impact? (key extraction, signature forgery, fund theft?)
3. What is the financial impact? (tokens at risk × price)
4. Is there a clean PoC? (attacker model: honest-but-curious vs malicious)

**Severity mapping:**
- CRITICAL: Key extraction, signature forgery, fund theft (direct financial loss)
- HIGH: Protocol deviation undetected, partial key material leak
- MEDIUM: Statistical security degradation (weaker than claimed)
- LOW: Performance parameter not security-relevant
- INFORMATIONAL: Code quality, documentation gaps

**Then run the mechanical severity gate** (same tool the web/contract side uses — one doctrine everywhere):
```bash
python $TOOLKIT/shared/finding_gate.py findings.json --report REPORT-survivors.md
```
It drops any finding that is info-only, by-design, or has a **dead exploit chain — even at high score**.
Crypto audit is the easiest place to inflate: "this parameter looks weak" without a key-extraction PoC
is documentation, not a vulnerability. If the gate drops it, it does not go in the report.
For multi-step crypto attacks (param weakness → proof forgery → signature malleability), use
`python $TOOLKIT/shared/chain_builder.py findings.json --goal key_extraction` to test whether the steps
actually compose — a chain requires adjacent findings to share a capability, not just to look related.

---

## Known Vulnerability Classes in Crypto Libraries

### 1. Batch Verification Parameter Sizing
- **Pattern:** Security constant too small, or wrong type (uint8_t vs uint64_t)
- **Impact:** Batch verification provides negligible statistical security
- **Fix:** Use cryptographically appropriate bit widths (≥40 bits for statistical security)

### 2. Seed/Entropy Buffer Over-Read
- **Pattern:** Buffer smaller than requested random bytes
- **Impact:** Uninitialized memory included in seed → predictable randomness
- **Fix:** Buffer size ≥ requested bytes, validate return values

### 3. Arithmetic Mode Switch Errors
- **Pattern:** Multiplicative shares treated as additive (or vice versa)
- **Impact:** Wrong mathematical operation → incorrect result → potential key leak
- **Fix:** Explicit domain labels, type-safe arithmetic wrappers

### 4. Challenge Derivation Weakness
- **Pattern:** Fiat-Shamir hash doesn't include all public parameters
- **Impact:** Malleable proofs, ability to create valid proof for different statement
- **Fix:** Hash all public inputs + transcript

### 5. Version Downgrade in MPC Protocol Negotiation
- **Pattern:** `if (version > MAX_VERSION)` allows lower versions without taking the minimum
- **Check:** `temp_data.version = version;` instead of `temp_data.version = min(temp_data.version, version);`
- **Impact:** Downgraded security parameters (weaker ZKP seeds, smaller random masking, different proof systems)
- **Exploitability:** Only exploitable in multi-party protocols where parties track versions independently. In 2-party protocols, both sides use the same stored version → no mismatch → no exploit.
- **Fix:** `if (version != MPC_PROTOCOL_VERSION)` or take `min()` on each party's side
- **Severity:** MEDIUM in 3+ party, LOW/INFORMATIONAL in 2-party

### 6. Statistical Security vs Computational Security Confusion
- **Pattern:** Using 128-bit computational security but only 8-bit statistical security
- **Impact:** Information-theoretic attacks become feasible
- **Fix:** Statistical security parameter ≥ 40 bits, computational ≥ 128 bits

### 7. assert() Compiled Out in ZKP Deserialization (DISPROVED)
- **Pattern:** `assert()` calls in proof serialization/deserialization functions compile out with `NDEBUG` in release builds. Example: `assert(ptr == serialized.data() + serialized.size())` — extra trailing bytes silently accepted.
- **Why it SEEMS exploitable:** Malformed proofs with extra/missing data could bypass length checks.
- **Why it's NOT exploitable:** Cryptographic verification (PowSumProof, ProductProof, Paillier equation check) runs AFTER deserialization and validates actual proof properties. Serialization assert is defense-in-depth, not a security boundary.
- **General principle:** If the cryptographic verification catches invalid data, serialization-level assert()s are informational only.
- **Severity:** INFORMATIONAL (disproved)
- **Verified in:** Fireblocks mpc-lib `bam_well_formed_proof.cpp:100,159` — 8+ assert calls in deserialization, but `verify_signature_proof()` validates EC equation (`g^z1·f^z2·f^w0 == V·U^e`) and Paillier equation (`Enc(z1,ρ^w2)·E^z2 == D·S^e mod n²`) regardless of serialization length.

### 8. ZKP Round-Count Asymmetry (Generator > Verifier) — USUALLY BY DESIGN
- **Pattern:** ZKP generator emits N rounds, verifier checks only K < N rounds.
  e.g. `PAILLIER_BLUM_STATISTICAL_SECURITY = 80` generator vs `MINIMAL_REQUIRED = 64` verifier (Fireblocks mpc-lib Paillier Blum modulus ZKP).
- **Why it SEEMS exploitable:** Rounds K..N-1 are deserialized but never verified — flipping/zeroing their bytes (a[i], b[i], z[i]) still passes verification. A fuzzer reports a high "bypass" rate on mutated proofs.
- **Why it's usually BY DESIGN:** The code comment typically says the lower bound was deliberately decided (e.g. "during development of 2-out-of-2 MPC it was decided that MINIMAL_REQUIRED is enough"). Effective soundness is 2^-K (intended), the extra rounds are generator redundancy, not a defect.
- **Decisive check BEFORE building a PoC:** (a) grep for the constant names + a code comment explaining the bound; (b) read SECURITY-MODEL.md — if 2^-K is the documented level, it's INFORMATIONAL, not a soundness break.
- **When it IS a finding:** only if 2^-K is below the documented/claimed level, OR the unchecked rounds feed a downstream value (then it's a real malleability). Otherwise it's the "attacker self-harm / redundancy" class.
- **Severity:** INFORMATIONAL (Fireblocks: confirmed by-design, not bounty-worthy)
- **Verified in:** `paillier_zkp.c` — see `references/blum-zkp-80-round-asymmetry.md`

## Wire-Format Mutation Pitfalls (for ZKP/proof PoCs)

### ⛔ `_size()` may return BITS, not BYTES — read length from the serialized header
When writing a PoC that flips specific fields of a serialized proof, do NOT use a `_size()` / `_key_size()` API to compute offsets — these frequently return bit-widths (e.g. `paillier_public_key_size()` → 1024) while the wire format stores byte-lengths (→ 128). Using 1024 in the offset math makes your PoC read/write far past the buffer → **your PoC SEGVs**, not the library. Always:
1. Read the actual length field from the serialized output: `n_len = *(uint32_t *)proof;`
2. Compute expected total size from the documented layout and assert `calc == actual_len` BEFORE any in-place mutation (guards against an OOB in your own PoC).
3. If the PoC crashes at an address far beyond the heap, suspect your offset arithmetic first — re-derive from the proof header.

### ⛔ Size-probe with NULL buffer returns BUFFER_TOO_SMALL, not a size
ZKP `generate_*` functions often refuse to return the required length when called with `buf=NULL, len=0` (they return a buffer-too-small error). To discover the needed size, pass a generously-sized scratch buffer (e.g. 65536) and read the output `len` param. Don't treat the NULL-probe error as a fuzzer crash.

---
- **Pattern:** `memcmp()` used instead of `CRYPTO_memcmp()` for comparing signature components (R points, s scalars) or public points.
- **Why it SEEMS exploitable:** Timing oracle on security-critical comparison.
- **Why it's NOT exploitable:** Compared values are PUBLIC (published as part of the signature or sent over the wire). Attacker already knows the expected values — timing leakage provides no new information.
- **Check:** Is the compared data secret? If no → not exploitable.
- **Severity:** INFORMATIONAL (disproved)
- **Verified in:** Fireblocks mpc-lib — `cmp_ecdsa_offline_signing_service.cpp:467` (r value comparison), `asymmetric_eddsa_cosigner_server.cpp:476` (R point comparison), `eddsa_online_signing_service.cpp:356` (s value comparison) — all compare public signature components.

---

## Tooling

```bash
# Clone and initial scan
git clone https://github.com/ORG/REPO && cd REPO
find . -name "*.cpp" -o -name "*.h" -o -name "*.c" | head -50

# Find security constants
grep -rn "SECURITY\|PARAMETER\|BATCH\|STATISTICAL\|KAPPA\|LAMBDA" --include="*.h" --include="*.hpp" --include="*.cpp"

# Find random/entropy usage
grep -rn "RAND_bytes\|random\|seed\|entropy\|urandom" --include="*.cpp" --include="*.h" --include="*.c"

# Find verify functions
grep -rn "void.*verify\|bool.*verify\|int.*verify" --include="*.cpp" --include="*.c"

# Find cryptographic primitives
grep -rn "paillier\|pedersen\|schnorr\|ecdsa\|threshold\|mta\|multiplicative" --include="*.cpp" --include="*.h" --include="*.c"

# Static analysis (if available)
cppcheck --enable=all --std=c++17 src/
```

---

## Known Pitfalls

### ⛔ Do NOT confuse cryptographic library audit with smart contract audit
- Smart contract audit = Solidity/Vyper + Foundry + on-chain
- Crypto library audit = C/C++/Rust + source code analysis + protocol-level
- Different tools, different methodology, different severity scales
- Use `smart-contract-audit` for on-chain, `crypto-library-audit` for off-chain

### ⛔ Informational crypto findings are NOT bounty-worthy
- "The code uses uint8_t instead of uint32_t" → INFORMATIONAL unless it enables an attack
- "The statistical security is only 8 bits" → CRITICAL if it enables signature forgery
- **Always ask:** "What can an attacker DO with this?" before claiming a finding

### ⛔ Batch verification shortcuts are the #1 bug class
- Developers optimize batch verification for performance
- Optimization often silently drops security proofs
- Always compare batch verification against iterated single verification

### ⛔ Library dependencies may contain their own bugs
- Check: what crypto library is used for primitives? (OpenSSL, libgcrypt, custom?)
- OpenSSL version matters — check for known CVEs
- Custom implementations are higher risk than well-audited libraries

### ⛔ Know when to STOP digging and PIVOT
- After 3+ disproved findings, the library is likely sound
- Continuing to dig deeper in the same codebase yields diminishing returns
- **Pivot decision tree:** Disproved crypto finding → try web/API/infrastructure attack surface → check scope boundaries → if everything in-scope is solid, write honest "no finding" report
- Don't chase version downgrades, buffer over-reads, or parameter weaknesses past the 3rd disproof
- Well-audited crypto (Fireblocks, OpenZeppelin, etc.) is genuinely hard — respect the engineering

### ⛔ Version downgrade ≠ version mismatch
- `version > CURRENT_VERSION` allowing lower versions is a code smell, not necessarily a vulnerability
- In 2-party protocols, both parties store the same min-version → use same code paths → no mismatch
- Only exploitable if parties independently track versions or if there are 3+ parties with divergent versions
- Always trace: "does the attacker end up on a DIFFERENT code path than the honest party?"

### ⛔ Don't claim findings without exploitability proof
- User explicitly requires: "Pastikan F1 bs diduplikasi" — verify findings are reproducible before reporting
- For crypto findings: write the mathematical proof that the attack works
- For protocol findings: write the step-by-step attack scenario showing the victim's loss
- Informational findings (coding style, unused variables, minor optimizations) = waste of time for bounty hunters

### ⛔ Python Fuzzing of C/C++ Crypto Code = Testing YOUR Code, Not Theirs
**Session: Fireblocks mpc-lib 2026-09-04.** WSL compilation failed (missing libgmp-dev, libssl-dev). Pivoted to Python struct-based fuzzer to simulate byte deserialization. Fuzzer "found" 15+ edge cases (empty bytes, 1-byte, 256-byte payloads). ALL findings were about the Python fuzzer's own logic — the actual C++ library was never executed.

**Root cause:** Python's struct.unpack and bytes handling are COMPLETELY different from C++'s memcpy, pointer arithmetic, and type casting. A Python fuzzer testing "what happens when I send 1 byte to a struct that expects 4" tells you nothing about what the C++ code does with that input.

**When WSL/Linux compilation fails:**
1. Fix the build (install missing deps: `apt install libgmp-dev libssl-dev`)
2. If deps are too heavy (Docker, kernel modules), use Docker: `docker run -v $(pwd):/src ubuntu bash -c "apt update && apt install -y build-essential && cd /src && make"`
3. If Docker fails, cross-compile on a different machine
4. **NEVER fall back to Python simulation** — it gives false confidence without actual code execution
5. If you truly can't compile, do STATIC ANALYSIS ONLY (read the code, trace the logic, no fuzzing)

**The trap:** Python fuzzing produces impressive-looking output (15 edge cases, coverage reports, crash logs) that LOOKS like real testing. But none of it exercises the actual C++ code paths, type conversions, or memory operations.

---

## Reference Files
- `references/blum-zkp-80-round-asymmetry.md` — Paillier Blum ZKP 80-vs-64 round asymmetry PoC + wire format layout + fuzzer pitfalls
- `references/fireblocks-mpc-lib-mta-analysis.md` — MtA batch verification deep dive
- `references/frost-protocol-audit-notes.md` — FROST Schnorr protocol structure and verification
- `references/mpc-version-downgrade-analysis.md` — Version downgrade analysis (disproved)
- `references/bam-protocol-audit-notes.md` — BAM ECDSA r_correction mechanism and well-formedness ZKP
- `references/key-refresh-eddsa-audit-notes.md` — CMP key refresh and Ed25519 algebra audit

## Case Studies

### Fireblocks mpc-lib (2026-09) — UPDATED after deep analysis
- **Target:** `fireblocks/mpc-lib` — MPC threshold signature library (~28K LOC)
- **Protocol:** CMP (ECDSA) + FROST (EdDSA) + BAM (ECDSA) + MtA with Paillier + Ring Pedersen
- **Protocols audited:** FROST Schnorr keygen/signing, BAM ECDSA signing with r_correction, CMP ECDSA online/offline, EdDSA asymmetric signing, key refresh (PRF-based), well-formedness ZKPs, DRNG, GFp/Ed25519/Stark algebra layers
- **146 source files** (.cpp/.h/.c) reviewed across all protocol implementations
- **Investigated findings (ALL disproved as non-exploitable):**
  1. ~~`BATCH_STATISTICAL_SECURITY = 5` + `uint8_t` random~~ → **SOUND.** Verifier generates random γ_i (prover doesn't know), so 8-bit randomness is sufficient. Even if prover knew, individual verification provides security fallback.
  2. ~~Seed generation buffer over-read~~ → **NOT EXPLOITABLE.** Buffer is ~512 bytes, proof.S max ~256 bytes. No actual over-read.
  3. ~~Version downgrade (store_setup_commitments `version > MPC_PROTOCOL_VERSION` allows lower)~~ → **NOT EXPLOITABLE in 2-party.** Both parties store `temp_data.version = min(version)` during keygen, then both use same `metadata.version` during signing. No prover/verifier mismatch. `use_extended_seed=0` path used by both sides.
  4. ~~MtA batch verification bypass~~ → **SOUND.** Mathematical proof: batch verification is equivalent to iterated single verification with verifier-chosen randomness.
  5. ~~FROST missing binding factor~~ → **CORRECTLY IMPLEMENTED.** Fiat-Shamir transform includes all required parameters.
  6. 40-bit Ring Pedersen masking → **SOUND.** Individual verification (non-batch) provides security regardless.
  7. ~~FROST "Shnorr" typo in AAD salt strings~~ → **COSMETIC.** Both client and server use same misspelled strings → no cross-implementation attack possible.
  8. ~~assert() compiled out in well-formedness proof deserialization~~ → **NOT EXPLOITABLE.** Cryptographic verification (PowSumProof, ProductProof, Paillier equation) runs AFTER deserialization and catches invalid data regardless of serialization length.
  9. ~~Non-constant-time memcmp on R points, s values~~ → **NOT EXPLOITABLE.** Compared values are public signature components — attacker already knows them, timing leakage provides no advantage.
  10. ~~POSITIVE_R uint8_t counter overflow~~ → **CORRECTLY HANDLED.** Counter wraps from 255→0, explicit `if (!counter)` check throws exception. assert is redundant in debug builds.
  11. BAM r_correction mechanism → **SOUND.** Both client and server independently compute same correction factor. Client scales k_client by r_correction_cycles, server uses original k_server for decryption. Cross-party invariant maintained.
  12. Key refresh (PRF-based) → **SOUND.** Uses PRF with Paillier encryption, proper seed cleanup, temporary key storage with versioning.
  13. ~~Paillier Blum modulus ZKP 80/64 round asymmetry~~ → **BY DESIGN.** Generator emits `PAILLIER_BLUM_STATISTICAL_SECURITY = 80` rounds, verifier checks only `MINIMAL_REQUIRED = 64`. PoC proved rounds 64-79 (a[i], b[i]) are deserialized but NEVER verified — flipping/zeroing all 16 unchecked rounds still passes verification. Code comment explicitly states 2^-64 was decided sufficient for 2-of-2 MPC. Effective soundness 2^-64, not 2^-80 — intentional, INFORMATIONAL only.
  14. Paillier ZKP verifiers (Blum, factorization, coprime) ASan+UBSan fuzzed (C harness, 20k+ iterations, mutated proofs) → **NO CRASHES.** All three verifiers clean under sanitizers; only "bypasses" were mutations landing in the unchecked rounds 64-79 region (fuzzer artifact of #13, not soundness break). Curve algebra (Ed25519/GFp) = thin OpenSSL BN wrappers, low attack surface.
- **Root cause of false positives:** Earlier analysis confused "code uses weaker parameter" with "attacker can exploit the weaker parameter". The key question is always: **does the attacker control the inputs to the verification equation?**
- **Impact:** No exploitable vulnerability found in 28K LOC of cryptographic code
- **Lessons:**
  1. **Version downgrade trap in MPC:** `version > CURRENT_VERSION` allows downgrades, but in 2-party protocols both sides use the same stored version → no mismatch. Only exploitable if parties independently track versions.
  2. **Statistical security parameter doesn't matter if verifier generates randomness.** Batch γ_i is verifier-side → prover can't bias it → 8-bit is fine.
  3. **Always ask "can the attacker control the verification input?"** before claiming a parameter weakness is exploitable.
  4. **Well-audited crypto libraries are genuinely hard to break.** Don't keep digging after 5 disproved paths — pivot to web/API/infra attack surface instead.
