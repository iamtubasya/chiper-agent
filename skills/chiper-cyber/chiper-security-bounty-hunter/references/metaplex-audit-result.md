# Metaplex — Full In-Scope Audit Result (2026-11-05)

## Verdict: NO confirmed vulnerability across all 5 in-scope programs.

Method: exhaustive manual source review of every critical path + randomized
invariant fuzzing (Mollusk) of mpl-core plugin layout + group membership.
Toolchain built from scratch (Agave 4.3.2, cargo-build-sbf, SBF ELF built).

## Per-program coverage (all reviewed, all clean)

| Program | Tier | Surface reviewed | Result |
|---------|------|------------------|--------|
| mpl-core | 1 | dispatch, authority, plugin lifecycle, transfer, execute-CPI, groups, collect, compression | 6 fuzzers + 455 tests pass |
| token-auth-rules | 2 | all 18 V2 constraints, merkle root, assert_derivation | clean |
| token-metadata | 1 | delegate (MIP-7), escrow, transfer, print, collection verify/unverify, get_authority_type, auth_rules_validate | clean |
| bubblegum | 2 | delegate, set_tree_delegate, collect, verify/unverify creator+collection, redeem, transfer v1/v2 | clean |
| candy-guard (core-candy-machine) | 3 | 30+ guards: allow_list (merkle), mint_limit, allocation, sol/freeze payment, third_party_signer, bot_tax, mint_v1 dispatcher, group selection | clean |

## Leads investigated and DISPROVEN (do not re-report)

1. `MintLimit::pre_actions` `count += 1` (u16) — `overflow-checks=true` in
   `[profile.release]`; and `validate` blocks at `count >= limit`, so overflow
   unreachable. Fail-closed.
2. `AllowList` replay — proof PDA is a *persistent identity cache* (address is
   allow-listed, not one-time). Not a replay vuln.
3. `unverify_collection_v1` `data.borrow()[0]` — account always owned by
   program (≥1 byte); `||` short-circuit. Safe.
4. `decrement_collection_size` before authority check — Solana tx atomic;
   rollback on later error. Not exploitable.
5. **`bot_tax` "swallows" guard errors via `process_error` → `Ok(())`** — this
   is the INTENDED anti-bot design. `assertBotTax` in JS tests confirms the
   mint does NOT happen (no NFT) and the penalty is charged. NOT a bypass.
   (I initially mis-claimed this as a confirmed bug and retracted it.)
6. `freeze_nft` `frozen_count += 1` — `overflow-checks=true`; and `thaw_nft`
   uses `saturating_sub`. Safe.

## Honest assessment

These are among the most-audited smart contracts in the entire blockchain
ecosystem (Solana NFT standards since 2021; audited by OtterSec, Neodyme,
Kudelski, Halborn, etc.). No bug found is the expected, honest result of a
thorough review. The reusable fuzz harness (see metaplex-fuzz-harness.md) is
the durable asset — it can be pointed at ANY Metaplex program for future
coverage, and the toolchain is now installed.
