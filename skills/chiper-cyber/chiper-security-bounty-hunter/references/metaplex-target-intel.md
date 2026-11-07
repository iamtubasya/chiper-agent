# Metaplex Bug Bounty — Target Intel (Solana on-chain programs)

## Scope & Rules (verified 2026-11-05, https://metaplex.foundation/bounty-program)

- **Scope = on-chain programs ONLY.** Websites/domains explicitly OUT of scope.
- Only **latest mainnet-deployed versions** of the listed programs are in scope.
- Submission: email `bounty@metaplex.foundation` with **exploit code + repro steps** (mandatory, else ineligible).
- No publication until fix confirmed. Duplicates → first reporter only.
- Program libraries index: https://developers.metaplex.com/official-links#programs

## Tiering (2026/10/29) + Rewards

| Tier | Programs | Critical | High | Medium | Low |
|------|----------|----------|------|--------|-----|
| 1 | **Core** (mpl-core) | $10k–$20k+ | $3k–$10k | $400–$3k | $40–$400 |
| 2 | Token Auth Rules, Bubblegum | $4k–$10k+ | $2k–$4k | $400–$2k | $40–$400 |
| 3 | Core Candy Machine, Bubblegum v2 | $800–$2k | $400–$800 | $200–$400 | $40–$200 |

## Mainnet Program IDs (from `declare_id!`)

| Repo | Program ID | Version |
|------|-----------|---------|
| mpl-core | `CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d` | 0.2.0 (crate) |
| mpl-token-metadata | `metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s` | — |
| mpl-bubblegum | `BGUMAp9Gq7iTEuizy4pqaxsTyUCBK68MDfK752saRPUY` | — |
| mpl-token-auth-rules | `auth9SigNpDKz4sJJ1DfCTuZrZNSAgh9sFD3rboVmgg` | 1.5.1 |

## Repo layout (cloned at ~/workspace/metaplex)

- `mpl-core/` — 225 rust files. Plugin-based asset standard. `programs/mpl-core/src/`
- `mpl-token-metadata/` — 283 files. `programs/token-metadata/program/src/`
- `mpl-bubblegum/` — 100 files, compressed NFT. `programs/bubblegum/program/src/`
- `mpl-token-auth-rules/` — 37 files. Rule engine. `programs/token-auth-rules/src/`

## Audit status (2026-11-05, deep manual pass)

**mpl-core (Tier 1) — reviewed, NO confirmed vuln:**
- Access control core: `resolve_authority`, `resolve_pubkey_to_authorities`, `is_valid_asset_authority`, `validate_asset_permissions` (utils/mod.rs) — fail-closed, solid.
- `transfer.rs`, `approve/revoke/update/remove_plugin`, `collect.rs` (hard-locked recipients), `decompress` (disabled → `NotAvailable`).
- Recent fix confirmed: UpdateDelegate revoke authority operator-precedence bug (commit e021ca4, PR #253/254) — already in main + regression test.
- **Leads for fuzz (NOT confirmed):** `update_plugin`/`delete_plugin`/`save_updated_groups_plugin` use manual `sol_memmove` + offset bumping; `execute.rs` arbitrary CPI signed by asset PDA `[mpl-core-execute, asset_key, bump]` (intentional agentic feature, guardrail = `validate_execute` + fee).

**mpl-token-auth-rules (Tier 2) — reviewed, NO confirmed vuln:**
- All 18 V2 constraints audited: `additional_signer`, `all`, `amount`, `any`, `frequency` (NotImplemented, fail-closed), `is_wallet` (NotImplemented, fail-closed), `namespace`, `not`, `pass`, `pda_match` (find_program_address + exact match), `program_owned`, `program_owned_list`, `program_owned_tree`, `pubkey_list_match`, `pubkey_match`, `pubkey_tree_match`.
- Merkle root = keccak hashv with 0x01 domain separator (correct).
- Unit tests: 7/7 pass.
- Note: empty `All` constraint evaluates to `Success` (vacuous pass) — footgun only, rule set is authority-owned so not directly attacker-reachable.

**Open issue (non-vuln):** mpl-core #299 — SBF stack overflow in *client crate* `registry_records_to_plugin_list` (build-time, Rust 1.89), not a deployed-program runtime vuln.

## Toolchain (installed 2026-11-05, working)

- Rust/cargo 1.99.1 (via rustup), Solana/Agave CLI 4.3.2, cargo-build-sbf 4.4.0 (platform-tools v1.57).
- `solana-test-validator` 4.3.2 available.
- Gotcha: pin `time` to >=0.3.36 (`cargo update -p time --precise 0.3.36`) — older 0.3.34 fails to compile under rustc 1.99 (E0282 in time crate).
- Build cmd: `cd programs/<prog> && cargo build --features no-entrypoint`; test: `cargo test --lib`.

## Next steps to find a real bug

1. **Fuzz mpl-core plugin memory manipulation** — Mollusk harness (see mpl-core CLAUDE.md: `core_mollusk()`, `MPL_CORE_NATIVE_PROGRAM=1 cargo test`), invariant: after any add/update/delete sequence, account round-trips and offsets are consistent.
2. **Fuzz the `execute` arbitrary-CPI boundary** — can asset PDA be coerced to sign a CPI the owner didn't approve?
3. **token-metadata + core-candy-machine + bubblegum v2** (Tier 2/3) not yet audited.
