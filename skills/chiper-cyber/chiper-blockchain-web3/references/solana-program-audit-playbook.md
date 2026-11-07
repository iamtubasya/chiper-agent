# Solana On-Chain Program Audit Playbook

Companion to the EVM-focused `guides/smart-contract-audit-playbook.md`. Solana
programs are Rust/Anchor, compiled to SBF (Solana BPF) bytecode, and validated
with a different toolchain than Slither/Mythril/Foundry. This is the
battle-tested workflow for auditing deployed Solana programs (e.g. Metaplex).

## Toolchain (install from scratch, in order)

```bash
# 1. Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
source $HOME/.cargo/env

# 2. Agave CLI (bundles cargo-build-sbf + solana-test-validator)
curl -sSfL https://release.anza.xyz/stable/install -o /tmp/solana-install.sh && sh /tmp/solana-install.sh
export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"
solana --version          # e.g. 4.3.2
cargo-build-sbf --version # e.g. 4.4.0 (platform-tools v1.57)
```

## Recon: map the surface

1. Read the bounty page → scope is usually **on-chain programs only** (web/domain
   excluded). Note tiers + reward table + program IDs.
2. `git clone --depth 1` each in-scope repo, then `git fetch --unshallow` and
   `git log --oneline -i --grep="secur\|vuln\|exploit\|drain\|bypass\|unauth"` —
   Metaplex-style repos keep a `security-*` branch and land fixes as discrete
   commits with regression tests. Reading those commits tells you what was
   ALREADY found and the *pattern* of bug the team chases.
3. Find mainnet program IDs: `grep -rh "declare_id!" programs --include=*.rs`.
4. Map instruction dispatch (`src/lib.rs` / `processor/mod.rs`) and the
   `assert_owned_by` / `assert_derivation` / `resolve_authority` helpers — these
   are the access-control gates.

## Key architectural facts (Metaplex + most SPL programs)

- **Every state mutation is written LAST**, after all validation
  (`clean_write_metadata`, `increment/decrement_collection_size`), and Solana
  transactions are atomic — a failing instruction reverts all writes. So
  "state mutated before the authority check" is a smell, NOT a bug.
- **One authority gate**: `AuthorityType::get_authority_type(AuthorityRequest)`
  evaluates a precedence-ordered list (TokenDelegate → MetadataDelegate →
  Holder → Metadata) and returns the first match. Audit this single function
  first; it is the whole access-control model.
- **Optional accounts are detected by remaining count** (`account_info_iter.len()
  == 1`), NOT by key. Pattern is error-prone but guarded by `assert_derivation`.
- Hand-rolled account memory manipulation (`sol_memmove` + registry offset
  bumping in plugin systems) is THE classic corruption surface. Guarded by
  checked arithmetic + SAFETY comments, but this is what invariant fuzzing
  targets.

## Invariant fuzzing with Mollusk (the high-value technique)

Metaplex's own test harness uses **Mollusk** (`mollusk-svm`) to run the program
against an in-memory account store. Two modes:

| Mode | Command | Notes |
|------|---------|-------|
| Native (fast) | `MPL_CORE_NATIVE_PROGRAM=1 cargo test` | Host-compiled program; authoritative for Rust logic bugs |
| SBF (on-chain-accurate) | `cargo test` after `cargo build-sbf` | Loads the real ELF |

The winning pattern — which `adversarial.rs` invites — is:

1. The repo ships an invariant checker (`assert_registry_consistent`) that
   verifies: header/registry offsets, every record deserializes to its declared
   type, byte ranges are contiguous with no gap/overlap, registry ends exactly
   at account end.
2. Write a **deterministic xorshift64\*** fuzzer (no dev-dep) that drives long
   random sequences of REAL instructions (add/update/remove plugin, group
   membership, authority approve/revoke) through `Fixture::run()`, and calls
   `assert_registry_consistent` + bidirectional-consistency asserts after every
   step.
3. **Prove the fuzzer actually mutates state**: track an `accepted` counter and
   `assert!(accepted > 0)` per round. A fuzzer where every op is rejected tests
   nothing.
4. `adversarial.rs` documents panic/abort paths ("cannot be produced by any
   instruction") — the finding is to prove the offset-manipulation code CAN
   produce a corrupt registry record (freeze-bypass / permanent asset DoS).

A passing fuzz run + the repo's own test suite (hundreds of tests) is strong
negative evidence that the manual memory code is correct.

## Toolchain gotchas (fixes, not "tool is broken")

- **`time 0.3.34` fails to compile under rustc 1.99** (E0282 in the `time` crate).
  Fix: `cargo update -p time --precise 0.3.36`.
- **SBF-vs-Mollusk ELF mismatch**: `cargo-build-sbf 4.4.0` (platform-tools
  v1.57) builds **SBPFv3** (`e_machine = 0xf7`); `mollusk-svm 0.11.0` parses
  **SBF v0** (`0xf3`) → `FailedToParse("invalid file header")`. Forcing older
  platform-tools (`--tools-version v1.43 --arch v0`) then fails because that
  cargo (1.79) can't parse `edition2024` deps. Native mode is authoritative for
  the logic bugs this targets, so don't block on SBF mode.

## Where bugs actually live (priority order)

1. **Cross-program trust**: `auth_rules_validate` / program-config rule
   enforcement — a bypass here is a direct auth failure.
2. **Print / edition supply accounting** — unauthorized minting = value theft.
3. **Escrow / delegate lifecycle** — newest, least-audited features.
4. **Hand-rolled memory manipulation** (plugin/registry offset bumping).

## Honesty discipline

These programs (Metaplex core, token-metadata) are among the most-audited on
Solana — OtterSec, Neodyme, Halborn. A single-pass source skim will NOT find a
zero-day. The evidence-backed path is: deep source trace of the authority gate +
deterministic invariant fuzzing. Report "no confirmed vuln" with the evidence
rather than fabricating a finding — a fake report burns researcher credibility.
