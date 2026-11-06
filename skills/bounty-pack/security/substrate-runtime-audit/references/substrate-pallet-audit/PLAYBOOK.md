---
name: substrate-pallet-audit
description: Use when auditing Substrate/FRAME pallets.
version: 1.0.0
author: Qwen
license: MIT
metadata:
  hermes:
    tags: [security, substrate, frame, rust, pallet, web3, weights, poc]
    related_skills: [rust-substrate-zk-toolchain, web3-audit, codebase-bounty-review, exploit-depth]
---

# Substrate / FRAME pallet audit

White-box review of a Rust runtime's `pallets/` directory, with a **runnable mock-runtime
PoC** and severity bounded by measured numbers — not by reading.

## When to Use

- A bounty/audit scope names a **Substrate chain** (Polkadot/Kusama ecosystem, or a
  standalone chain like DeeperChain) rather than an EVM contract.
- You have `pallets/*/src/lib.rs` with `#[pallet::call_index(...)]` extrinsics.
- You need to prove a pallet bug rather than assert it, and the repo pins its own
  nightly toolchain.

Not for EVM/Solidity (use `web3-audit`) and not for tool selection alone
(`rust-substrate-zk-toolchain` holds the tool→job map; this file holds the method).

## The three highest-yield classes, in order

### 1. Weight mis-declaration (cheapest to PROVE)

The declared weight is a literal in a generated `weights.rs`, so "declared N, actually N+M"
is a measured fact, not an opinion.

Signature: a dispatchable path calls `iter()` / `iter_keys()` / `iter_values()` on an
**unbounded** `StorageMap`, while `weights.rs` declares a **fixed** read count.

```
delegate_any() : Validators::<T>::iter_keys().collect()        // O(N)
weights.rs     : reads(16)                                     // constant
```

**Strongest evidence is an internal contrast in the same file** — one call site caps the
iteration, another does not:

```
elect()        : Validators::<T>::iter() ... validators.truncate(Self::validator_count())
delegate_any() : Validators::<T>::iter_keys().collect()        // no truncate
```

That proves the authors knew the pattern and missed a site. Measured live: `cap = 2,
delegate_any iterates all 503`.

Then measure the curve (~61–70 µs per entry in one real run) and compute the N that
consumes the block budget instead of estimating.

### 2. Missing `#[transactional]` on a sibling

Grep the attribute — it is explicit. Compare sibling extrinsics that move funds:

```rust
pub fn staking_delegate(...)        // NO #[transactional]
#[transactional]
pub fn usdt_staking_delegate(...)   // HAS it   (count in whole file = 1)
```

Map side-effect order against the point that can fail (transfer → bookkeeping → credit →
call that returns `Result`). **Do not claim fund loss from the asymmetry alone** — rollback
depends on the outer dispatch wrapping. Proved asymmetry + observation until you have an
attacker-reachable `Err` at that exact line.

### 3. Unbounded storage growth / permissionless registration

Check who can insert into the map backing a hot loop: `ensure_signed` with no bond-size or
count gate means any account can inflate it. Compute the capital cost from
`ExistentialDeposit` and state whether it is locked-but-recoverable.

## Severity bounding — three reads before writing a number

Inflation happens here. Run all three.

| # | Question | How to answer |
|---|---|---|
| 1 | **Who holds the gating key?** | Read the storage decl: `StorageValue<_, AccountId>` = **one global key** (internet attacker cannot sign) vs `StorageMap<_, _, AccountId, _>` = per-account |
| 2 | **Is the trigger repeatable?** | Count the state space the gate allows. `ensure!(dst > cur)` with a 9-variant enum = max 8 triggers/account |
| 3 | **Does something else already do the work?** | If era rotation already walks the same set, marginal impact < raw N |

A weight gap that is objectively wrong (625× under-declared, 700 ms measured) is still
**Medium** when a global key gates it, the trigger is capped, and the cost is already paid
on a schedule. Write those three bounds into the report — a triager's first question is
"can anyone actually send this?".

## Workflow

1. **Read `rust-toolchain` first.** Substrate repos pin a nightly; a wrong compiler yields
   edition/trait errors that look like broken source.
2. `cargo fetch` **in the background** (git dependency on polkadot-sdk, ~20 min), then
   `cargo test --offline` is fast. Never foreground the first build.
3. Add `src/dXX_poc.rs`, register `#[cfg(test)] mod dXX_poc;` after `mod tests;` — do not
   edit their 100 KB `tests.rs`.
4. Seed storage directly in the mock (`<Map<Test>>::insert(k,v)`) instead of driving extrinsics.
5. Assert the **measured** behaviour so the suite fails the day it is fixed.

Full commands, the mock-runtime API, the three harness bugs that produced false results, and
the kill-list of rejected candidates:
**`references/substrate-pallet-build-and-poc.md`**

## Pitfalls that produced FALSE results (all mine, not the target's)

- **`include_str!("lib.rs").contains("...\n...")` fails on a CRLF checkout.** Use
  `.replace('\r', "")`; verify byte-level rather than trusting the boolean.
- **`re.split(r"#\[cfg\(test\)\]")[0]` truncates a file at its header** (`mod mock; mod tests;`
  are declared at the top) — 903 bytes reported for a 138 KB file, producing a false
  "nothing here" negative. Split on the last occurrence, or scan the whole file.
- **A mock account does not hold funds because you assumed an index.** Scan for a funded
  account and assert you found one.
- **`BlockWeights::get()` needs a type annotation** in a test —
  `<<Test as frame_system::Config>::BlockWeights as Get<BlockWeights>>::get().max_block`,
  else `E0282`.

## Anti-inflation rules specific to this class

| Temptation | Reality |
|---|---|
| "unbounded iteration → chain halt" | check who can register entries and whether the gating key is global |
| "missing `#[transactional]` → stolen funds" | needs a proven attacker-reachable `Err` after the transfer |
| "`unwrap()` in a dispatchable → panic DoS" | look **upward** for `ensure!(x.is_some())`; most are guarded |
| "`mint_into` reachable" | check the origin gate: `ensure_root` / `has_privilege` / nothing. "Nothing" is the finding |
| "`len() - 1` / `[i-1]` underflow" | check `!is_empty()` and `i>0` above it |

## Related

- `rust-substrate-zk-toolchain` — which tool for which job (semgrep, cargo-fuzz, Miri, Kani,
  CodeQL, cargo-audit/deny) and this host's install state.
- `web3-audit` — EVM/Move bug classes, pre-dive kill signals, Foundry PoC discipline.
- `codebase-bounty-review` — the 0A–0F phase model for repo-only (no live host) targets.
- `exploit-depth` — L0–L5 ladder; a code-read hunch is L2 until a test executes it.
