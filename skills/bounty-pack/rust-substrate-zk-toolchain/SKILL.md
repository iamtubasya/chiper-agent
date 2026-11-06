---
name: rust-substrate-zk-toolchain
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Rust/Substrate/Polymesh + ZK audit toolchain: which tool for which job, install
  state, and how it maps to the 0A-0F pipeline. Use when auditing Rust runtimes,
  FRAME pallets, ink! contracts, or circom ZK circuits.
metadata:
  hermes:
    tags: [security, rust, substrate, polymesh, zk, circom, toolchain, web3]
---

# Rust / Substrate / ZK Toolchain

## Tool → job map

| Tool | Job | Status on this host | Where it fits |
|---|---|---|---|
| **Kani** (AWS) | formal verification / bounded model checking of Rust — proves pallet invariants | not installed (needs `kani-verifier` + CBMC) | 0C deep-dive: prove an invariant instead of testing it |
| **Miri** | undefined-behaviour detection in Rust (interprets MIR) | not installed (`rustup component add miri`) | 0C: UB in runtime code, unsafe blocks |
| **cargo-fuzz** | libFuzzer harness for Rust | installing (see below) | 0C: fuzz pallet extrinsics / parsers |
| **CodeQL** | static analysis, multi-language, dataflow queries | not installed (needs CodeQL CLI bundle) | 0B/0C: dataflow across the runtime |
| **Semgrep** | pattern static analysis, fast, multi-language | **installed** (`semgrep` on PATH) | 0B/0C: first-pass pattern sweep |
| **circomspect** | static analysis + constraint-solver for circom circuits | not installed (needs OCaml/opam) | 0C: ZK circuit audit |
| **Picus** | ZK circuit exploit/verification tooling | not installed | 0C: ZK |
| **ecne** | circom R1CS analysis | not installed | 0C: ZK |
| **cargo-audit** | RustSec advisory DB against `Cargo.lock` | installing (see below) | 0A/0B: supply-chain gate |
| **cargo-deny** | licenses, bans, duplicate deps, advisory sources | installing (see below) | 0A/0B: supply-chain gate |

## Install notes for this host (verified 2026-10-18)

- **Toolchain:** `stable-x86_64-pc-windows-msvc` is the working default. The GNU
  toolchain **fails** on `windows-sys` with `dlltool.exe: program not found` — MSYS
  does not ship `dlltool`. Switch with
  `rustup default stable-x86_64-pc-windows-msvc` and put
  `VC\Tools\MSVC\<ver>\bin\Hostx64\x64` + a Windows Kits `bin\<ver>\x64` on PATH.
- **Compile-from-source is slow** (cargo-audit + cargo-deny + cargo-fuzz took >8 min).
  Run it as a background job, never foreground.
- **`cargo install` needs the MSVC linker**, not just rustc: verify with
  `command -v link` before blaming the crate.

## Pipeline mapping (0A → 0F)

```
0A scope        → cargo-audit / cargo-deny on Cargo.lock (supply-chain gate, fail-closed)
0B recon        → semgrep (fast pattern sweep) + CodeQL dataflow when the repo is available
0C hunt         → cargo-fuzz (parsers/extrinsics) · Miri (UB) · Kani (invariants)
                   circomspect/Picus/ecne for ZK circuits
0D verify       → tool-usage JSON: every tool above must leave an artefact or an N/A reason
0E review       → ToB variant-analysis + fp-check (dedupe, false-positive kill)
0F report       → ToB spec-to-code-compliance for the "what was supposed to happen" section
```

## Substrate/Polymesh-specific (from ToB substrate scanner)

7 critical pallet patterns to check, in order:
1. **Arithmetic overflow** in dispatchables (debug builds panic → node DoS)
2. **Panic DoS** — any `unwrap()`/`expect()`/slice-index reachable from an extrinsic
3. **Incorrect weights** — under-priced extrinsic = block-fullness DoS
4. **Bad origin checks** — `ensure_signed` vs `ensure_none` vs `ensure_root` misuse
5. **Unsigned extrinsic validation** missing or forgeable
6. **Storage unbounded growth** — map/set with user-controlled keys
7. **Currency/balance logic** — non-atomic transfer, rounding, reentrancy via hooks

## Companion skills (installed under `skills/tob/`)

`rust-review` · `property-based-testing` · `variant-analysis` · `differential-review` ·
`constant-time-analysis` · `zeroize-audit` · `sharp-edges` · `supply-chain-risk-auditor` ·
`spec-to-code-compliance` · `entry-point-analyzer` · `mutation-testing` ·
`semgrep-rule-creator` · `audit-context-building` · `fp-check` ·
`vulnerability-triage-brocards` · `post-patch-validation` · `scanner-substrate` ·
`scanner-solana` · `scanner-cosmos` · `scanner-cairo` · `scanner-algorand` ·
`codeql` · `semgrep` · `sarif-parsing` · `cargo-fuzz` · `libfuzzer` ·
`fuzzing-dictionary` · `fuzzing-obstacles` · `ossfuzz`

## Provenance

Skills copied from `github.com/trailofbits/skills` (Apache-2.0). Tool map and
pipeline mapping written for this host.
