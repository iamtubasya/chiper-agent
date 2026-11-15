# Fireblocks mpc-lib — MtA Protocol Audit Case Study (2026-09)

## Target
- **Repo:** `fireblocks/mpc-lib` (GitHub)
- **Languages:** C++ (core MPC), TypeScript (coordinator), Python (bindings)
- **Protocol:** GG20-like threshold ECDSA with MtA (Multiplicative-to-Additive) share conversion
- **Bugcrowd program:** `fireblocks-mbb-og2` (MPC MBB, $150K bounty)

## Key Files
- `mpc-lib/src/common/mpc/cmp12/mta.cpp` — MtA protocol implementation (2000+ lines)
- `mpc-lib/src/common/mpc/cmp12/mpc_globals.h` — Security constants
- `mpc-lib/src/common/mpc/cmp12/gg20/mta.cpp` — GG20-specific MtA

## Vulnerability 1: Batch Statistical Security Degradation

### Root Cause
`BATCH_STATISTICAL_SECURITY = 5` (defined in `mpc_globals.h`) used as loop bound for batch verification in `mta.cpp`. Random coefficients `r_i` generated as `uint8_t` — only 8 bits of randomness (256 possible values).

### Why It Matters
- Statistical security should be ≥ 2^40 for production cryptographic systems
- 2^8 = 256 possible values → statistical security ≈ 0
- Attacker can enumerate all possible coefficient combinations
- With 2 malicious MPC parties, can forge signatures

### Code Pattern
```cpp
// In mpc_globals.h
#define BATCH_STATISTICAL_SECURITY 5

// In mta.cpp — batch verification loop
for (int i = 0; i < BATCH_STATISTICAL_SECURITY; i++) {
    uint8_t r_i;  // Only 8 bits!
    RAND_bytes(&r_i, 1);
    // ... verification using r_i ...
}
```

### Fix
```cpp
#define BATCH_STATISTICAL_SECURITY 40  // Or higher

// Use proper-sized random coefficients
uint64_t r_i;
RAND_bytes((uint8_t*)&r_i, sizeof(r_i));
```

## Vulnerability 2: Seed Buffer Over-Read

### Root Cause
Seed buffer allocated as 28 bytes but `RAND_bytes` requested 32 bytes — 4 bytes read past buffer end.

### Code Pattern
```cpp
unsigned char seed[28];
RAND_bytes(seed, 32);  // Reads 4 bytes past buffer!
```

### Impact
- Uninitialized stack memory included in seed
- Reduces entropy of generated keys
- Potentially predictable if stack layout is known

## Vulnerability 3: Arithmetic Mode Inconsistency

### Root Cause
MtA protocol requires switching between additive and multiplicative share representations. Code doesn't consistently track which domain shares are in.

### Impact
- Wrong mathematical operation applied to shares
- Incorrect signature output
- Potential key material leakage

## Statistical Security Analysis

| Parameter | Value | Should Be | Gap |
|-----------|-------|-----------|-----|
| BATCH_STATISTICAL_SECURITY | 5 | ≥40 | 8x too low |
| Random coefficient bits | 8 (uint8_t) | ≥64 (uint64_t) | 8x too narrow |
| Statistical security (achieved) | ~2^8 | ≥2^40 | Catastrophic |

## Attack Model
- **Attacker:** 2 of 5 MPC participants are malicious (colluding)
- **Expected security:** GG20 claims security with up to t-1 malicious (for t-of-n)
- **Achieved security:** Statistical verification provides negligible additional security
- **Exploit path:** Malicious parties manipulate MtA shares during batch verification → forge signature → sign arbitrary transaction → steal funds

## Lessons Learned
1. Security constants set during development/testing often remain at non-production values
2. Type choice (uint8_t vs uint64_t) for security parameters is critical
3. Batch verification shortcuts must be validated against the security proof
4. Always trace EVERY usage of a security constant — one wrong usage breaks the entire protocol
5. Performance optimization in crypto code must preserve mathematical invariants
