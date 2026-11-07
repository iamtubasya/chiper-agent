# Metaplex mpl-core — Invariant Fuzzing Harness (reusable)

Deterministic xorshift64* fuzzer that drives random sequences of REAL
mpl-core instructions through the Mollusk harness and asserts the plugin-layout
invariant (`assert_registry_consistent`) + group bidirectional-consistency after
every step.

## Files (drop into `programs/mpl-core/tests/it/`, then register in `main.rs`)

1. `fuzz_layout.rs` — internal plugin add/update/remove + authority
   approve/revoke + external adapter data grow/shrink. Asserts layout invariant
   after every mutation, and `accepted > 0` per round (proves the fuzzer
   actually mutates state, not no-op).
2. `fuzz_groups.rs` — group asset/collection membership + group nesting.
   Asserts: (a) `assert_registry_consistent` on members, (b) bidirectional
   membership (group.assets[i] ⟺ asset.Groups plugin lists group), (c) no
   self-parenting/cycle.

## Run

```bash
export PATH="$HOME/.local/share/solana/install/active_release/bin:$HOME/.cargo/bin:$PATH"
cd ~/workspace/metaplex/mpl-core/programs/mpl-core

# Fast iteration (host-compiled program; authoritative for the Rust logic bugs
# in sol_memmove/offset arithmetic this targets):
MPL_CORE_NATIVE_PROGRAM=1 cargo test --test it fuzz

# On-chain-accurate (SBF ELF) — requires matching toolchain, see gotcha below:
cargo test --test it fuzz
```

## Result (2026-11-05)

6/6 fuzz tests PASS over ~thousands of random mutations (rounds × steps). Plus
the repo's own 455-test suite passes. **No layout corruption or group desync
produced by any reachable instruction sequence.** This is strong negative
evidence that the hand-rolled `sol_memmove` + offset-bump code is correct.

## SBF-mode toolchain gotcha (important)

The SBF ELF path hits a version mismatch on a fresh toolchain:

- `mollusk-svm 0.11.0` (repo dev-dep) parses **SBF v0** (`e_machine = 0xf3`).
- `cargo-build-sbf 4.4.0` (bundled with agave CLI 4.3.2) → platform-tools
  v1.57 builds **SBPFv3** (`e_machine = 0xf7`) → Mollusk panics
  `FailedToParse("invalid file header")`.
- Forcing `--tools-version v1.43 --arch v0` fails: v1.43's cargo (1.79) can't
  parse `edition2024` deps (`wincode-0.5.2`).
- Repo CI pins `sbf_tools_version: 4.0.0` (`.github/workflows/main.yml`).

To get a Mollusk-parsable ELF you need a platform-tools version that (a)
builds SBF v0 (i.e. pre-SBPFv3, `< v1.51`) AND (b) has cargo ≥ 1.85 for
edition2024 — around platform-tools v1.44–v1.50. Native mode is authoritative
for the logic bugs this fuzzer targets, so this is a convenience, not a
correctness gap.
