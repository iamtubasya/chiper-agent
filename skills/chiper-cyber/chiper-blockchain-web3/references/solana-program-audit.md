# Solana / Rust Program Audit Methodology

The base `chiper-blockchain-web3` skill is EVM/Solidity-centric (Slither, Mythril, Foundry,
reentrancy, flash loans). **None of that transfers to Solana.** Solana programs are Rust (or
Anchor Rust), compiled to the SBF/BPF target, and have a fundamentally different vulnerability
model. When the target is a Solana program (Metaplex, Anza/Agave, Serum, Jito, etc.), use this
reference instead of reaching for Slither.

---

## 1. Solana vs EVM — what actually differs

| Concern | EVM | Solana |
|---|---|---|
| Reentrancy | First-class (re-entrant external calls) | **Not the dominant bug.** CPIs (`invoke`/`invoke_signed`) are synchronous & the runtime forbids re-entering the *same* program in a cycle; the real risk is **arbitrary CPI to attacker-chosen programs** and **PDA signer abuse**. |
| Attack surface | Storage slots, fallback/receive | **Account validation** (owner, signer, writable, PDA derivation) is THE #1 bug class. |
| Static tooling | Slither/Mythril | `cargo-geiger`, `cargo audit`, clippy, manual review. No Solidity-grade analyzer. |
| Dynamic test | forge/anvil fork | `solana-program-test`, **Mollusk SVM** (`mollusk-svm`), `anchor test`, `solana-test-validator`. |
| "Private key" | EOA | Keypairs + **PDAs** (program-derived addresses) that a program can sign via `invoke_signed` with bump seeds. |
| Serialization | ABI | **Borsh** (manual, offset-sensitive). Deserialization + offset math bugs are common. |
| Memory | EVM word-sized | Account data is a flat `&mut [u8]` buffer. Programs do **manual `sol_memmove` + `realloc` + offset-bump** bookkeeping — a rich source of bugs. |

## 2. Toolchain (what to install before claiming to test)

```bash
# Core CLI + BPF toolchain
sh -c "$(curl -sSfL https://release.anza.xyz/stable/install)"
solana --version
# Rust SBF target (program build)
cargo install cargo-build-sbf   # (or via agave platform-tools)
# Anchor (if program is Anchor-based)
cargo install --git https://github.com/coral-xyz/anchor avm --locked
# Mollusk SVM — light SVF VM harness for unit-testing/fuzzing program entrypoints
cargo install mollusk-svm
# Static/lint
cargo install cargo-geiger
cargo install cargo-audit
```

Key commands:
```bash
cargo build-sbf --manifest-path programs/<pkg>/Cargo.toml
solana-test-validator --reset            # local validator
cargo test-bpf                           # run program tests on SBF
# Mollusk harness: assert specific accounts mutated / program halts without a live validator
```

## 3. Solana vulnerability classes (audit checklist)

1. **Missing account owner/signer check.** Every account that isn't a program-owned PDA must
   verify `account.owner == &expected_program::ID` and `account.is_signer`. This is the Solana
   equivalent of missing auth. Look for handlers that deserialize a passed account without
   checking who owns it.
2. **Account confusion / type substitution.** Two accounts with the same pubkey but different
   semantics (e.g. passing an `AssetV1` where a `CollectionV1` is expected, or a user account
   where a PDA is expected). Solana's account list is positional — swapping positions matters.
3. **PDA derivation & bump canonicalization.** `Pubkey::find_program_address(seeds, program_id)`
   returns a canonical bump; code that accepts a client-supplied bump without `assert_derivation`
   can let an attacker derive a *different* PDA and seize its signing authority. Always audit
   `invoke_signed` seed arrays and `create_program_address` vs `find_program_address` usage.
4. **Arbitrary CPI / `invoke_signed` privilege escalation.** If the program signs a PDA over
   attacker-supplied instruction data to an attacker-supplied `program_id`, and the PDA holds
   lamports/authority, that's the "asset signer" hazard. Trace every `invoke_signed`: what seeds,
   what accounts, who can trigger it, and whether the *signing authority* (PDA) can be made to
   approve something the caller didn't intend.
5. **Arithmetic overflow/underflow in offset & size math.** Account sizing (`data_len`),
   `resize_or_reallocate_account`, plugin-registry offset bumping. Rust `checked_add/sub` mostly
   neutralizes this in modern code, but `unsafe` blocks + raw pointer arithmetic
   (`account.data.borrow_mut().as_mut_ptr()`, `sol_memmove`) are where it breaks.
6. **`sol_memmove` / realloc bugs.** Grow/shrink ordering: shrink must memmove BEFORE truncation,
   grow must realloc BEFORE memmove (else you read freed/wrong bytes). Look for off-by-one in
   `copy_len`, `next_plugin_offset`, `new_registry_offset`.
7. **Lamport / rent accounting.** `collect`-style fee drains, `close_program_account`, and any
   place lamports are manually moved. Check recipient is a fixed constant, not a passed account.
8. **Merkle proof verification (compressed assets).** `verify_proof`-style: re-hash the leaf +
   proof, compare to stored root, reject on mismatch. Bugs = accepting wrong proofs or missing
   the `asset_hash != current_account_hash` check.
9. **Instruction data deserialization.** Borsh `try_from_slice` on `instruction_data` and on
   account buffers. Wrong offset or trusting a length field can read OOB or deserialize garbage.
10. **Missing `is_writable` checks.** A handler that mutates an account without verifying it was
    declared writable (or vice versa).

## 4. Access-control pattern to recognize (mpl-core model)

Metaplex `mpl-core` uses a reusable, well-hardened permission engine worth mirroring when reading
any modern Metaplex/plugin-style program:

- `resolve_authority(payer, authority_opt)` → if `authority` provided, `assert_signer` it; else
  fall back to `payer`.
- `resolve_pubkey_to_authorities(authority, collection, asset)` → build the set of `Authority`
  roles the signer holds (Owner / UpdateAuthority / Address / delegates).
- `validate_asset_permissions(...)` → collects `CheckResult` (None/CanApprove/CanReject/
  CanForceApprove) from asset → collection → plugins → external adapters, then **fail-closed**:
  any `Rejected` → `InvalidAuthority`; no `Approved`/`ForceApproved` → `NoApprovals`.
- `ValidationResult::{Approved, Rejected, Pass, ForceApproved}` with operator-precedence care in
  boolean gate chains (`&&` binds tighter than `||` — a real bug class, see below).

## 5. Real-world finding note (from a live Metaplex mpl-core pass)

- **UpdateDelegate `validate_revoke_plugin_authority` operator-precedence bug** (fixed in main,
  PR #253/#254): `a || b && c` was parsed as `a || (b && c)` where the intent was `(a || b) && c`,
  letting an UpdateDelegate revoke authority on owner-managed plugins (FreezeDelegate,
  TransferDelegate) it should not control. Lesson: when auditing boolean authority gates, check
  parenthesization of every `&&`/`||` chain against intent, and check whether the fix has shipped
  with a regression test.
- First-pass manual review of a heavily-audited program (716 commits, dedicated security branch)
  typically yields **no confirmed critical**. Report this honestly rather than fabricating. The
  path to a real finding is executable proof: Mollusk harness + fuzzing the offset/memmove paths,
  or patch-diffing recent security commits.

## 6. Metaplex bounty intel (self-hosted, not on Immunefi)

- Portal: `https://metaplex.foundation/bounty-program` — submission by **email** to
  `bounty@metaplex.foundation`, with exploit code + reproduction steps required.
- Scope = **on-chain programs only** (websites/domains explicitly OUT of scope). Only the latest
  mainnet-deployed versions count.
- Tiering (2026-10-29): Tier 1 = `Core` (mpl-core); Tier 2 = Token Auth Rules + Bubblegum;
  Tier 3 = Core Candy Machine + Bubblegum v2.
- Rewards (Tier 1): Critical $10k–$20k+, High $3k–$10k, Medium $400–$3k, Low $40–$400.
- Mainnet program IDs (for on-chain verification against repo source):
  - `mpl-core`: `CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d`
  - `mpl-token-metadata`: `metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s`
  - `mpl-bubblegum`: `BGUMAp9Gq7iTEuizy4pqaxsTyUCBK68MDfK752saRPUY`
  - `mpl-token-auth-rules`: `auth9SigNpDKz4sJJ1DfCTuZrZNSAgh9sFD3rboVmgg`
- Repos: `github.com/metaplex-foundation/{mpl-core, mpl-token-metadata, mpl-bubblegum,
  mpl-token-auth-rules}`. mpl-core = plugin-based digital asset standard
  (`programs/mpl-core/src/`); smallest tractable target is token-auth-rules (~37 src files).
