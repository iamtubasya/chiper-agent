# Black-box Solana forensics without program source — worked method (LoopScale, 2026-10)

When the target program is NOT open source but a client IDL exists (codama-generated
`clients/{js,rust}/src/generated/`), you can still do real on-chain analysis. Everything below was
executed live against LoopScale (core `1oopBoJG58DgkUVKkEzKgyG9dvRmpgeEm1AVjoHkF78`, BEAM oracle
`beamVVkNmKeXcuZ6zLpC9eM5YgVyAn4Z9xdPrz3gCW2`) with no program source.

## 0. Find an RPC first

Subdomain-enumerate the target's zone via DoH; hosting panels often expose their own node
(`rpc.<domain>` resolving to Google Frontend answering `{"error":"Method not allowed. Use POST
JSON-RPC."}` on GET is a Solana JSON-RPC). One open RPC replaces every block-explorer scrape.

## 1. Build a borsh decoder from the IDL (validate before trusting)

Type sizes come from the generated `types/*.rs`: `PodU64`=8, `PodU32CBPS`=4, `PodU64CBPS`=8,
`PodDecimal`=24 (10^18-scaled), `Pubkey`=32, enums = 1 + variant. Account structs give the field
order; `LEN` in the `impl` block is the checksum (Loan LEN=1634 matched exactly).

```python
# decode: 8B disc | version u8 | bump u8 | status u8 | borrower 32B | nonce u64 | start u64 |
#          ledgers[5] (182B each) | collateral[5] (73B each) | weight/ltv/lqt matrices (3x25 u32)
```

**Validate the decoder against a known account before using it for anything**: fetch one account
whose fields the target's own API reports (borrower, principalDue, collateral amount) and assert
byte-equality. A decoder that matches on one account is trustworthy for the rest.

## 2. Upgrade authority — the highest-value 60-second check

Both programs were upgradeable (`owner == BPFLoaderUpgradeab1e...`). The program account data is
36 bytes: `[4B enum][32B programdata pubkey]`. Fetch the programdata account; its layout is
`[4B enum][8B last-deploy slot][32B upgrade authority]`.

```
upgrade_authority = programdata[12:44]
```

Interpretation rules:
- authority == a **bare pubkey with no on-chain account** → a single EOA keypair can upgrade
  (a Squads vault PDA would be SQDS-owned and would EXIST on-chain; a never-initialized pubkey
  cannot be a PDA).
- authority == the documented multisig → control as advertised.
- Cross-check the docs' "multisig" address itself: a plain system-owned 0-data wallet is not a
  Squads multisig (real ones are SQDS-owned with ~495B config).
- A real Squads multisig can exist for OPERATIONS (VaultTransactionExecute in tx logs) while
  upgrades sit on a separate bare key — check both, they are different questions.
- LoopScale finding: docs promised 3/5 multisig upgrades; both programs' upgrade authority was one
  bare key. Reportable as a documented-control gap, not as "admin can rug".

## 3. Decode fixed-format oracle/config accounts

Method that worked on the BEAM NAV account (76,656 B, 33 entries):

1. b58-decode each known collateral pubkey, `data.find(pubkey_bytes)` → offsets.
2. Sort offsets; a constant stride (152 B here) confirms a fixed-entry array.
3. Read the fields around one entry and identify them by cross-check: the value at +32 was
   18-decimal fixed point and matched the off-chain deals DB NAV exactly ($15.75 = 15.75e18);
   +80 was a unix timestamp.
4. Decode all entries, then diff against the off-chain source of truth (the deals API): on-chain
   values matched the last *accepted* submissions; `held_for_ack` submissions were NOT pushed.

Staleness observation worth reporting: the pusher re-wrote the same value with a FRESH timestamp
every ~30 min, so the on-chain maxAge check (65535 s) never trips while the underlying valuation
was 87 days old. A frozen value with a refreshed timestamp defeats freshness checks.

## 4. Instruction-level analysis from the IDL (no source needed)

- **Signer map**: regex every `instructions/*.rs` for
  `AccountMeta::new(_readonly)?\(\s*self\.(\w+),\s*(true|false)` → per-instruction signer sets.
  LoopScale: 40/42 instructions required a `bs_auth` co-sign; only `liquidate_ledger` (liveness,
  by design) and `update_market_information` (admin) skipped it. A fund-moving instruction missing
  a co-sign its siblings all require is the thing to look for.
- **Instruction data vs accounts**: `WritePriceEntry` carried only the 8-byte discriminator — the
  price came from a referenced account, not an argument. When data is discriminator-only, the
  payload is in the accounts; decode those.
- **Who writes**: `getSignaturesForAddress` on the oracle account, then `getTransaction` on a few
  and read accountKeys[0] — one pusher key, batching ~4 writes/tx every ~30 min.

## 5. Squads vs EOA in one query

`getAccountInfo` on the address: owner `SQDS4ep65T...` + ~495 B data = real multisig; owner
`1111...` + 0 data = plain wallet; account-not-found = bare pubkey (never initialized). No
explanation needed beyond that table.

## 6. Health/liquidation state via the target's own API

The indexed API computes health ratios per wallet (LoopScale: `POST /user/loans` returned
`healthRatio`, `ltv`, `liquidationThreshold` per loan). Pull the full loan set
(`/loans/core` paginated), rank borrowers by principal, batch-query the top N wallets' health, and
sort ascending. Lowest-health + zero loans under ~0.02 = the liquidation system is keeping up —
record that as a verified negative with the numbers, not as "no findings".

## Pitfalls

- `getProgramAccounts` with `dataSlice.length=0` IGNORES the memcmp filter on some nodes (returned
  the full 47,507 program accounts for every discriminator). Use the indexed API for sets and
  `getMultipleAccounts` for batches of known addresses instead.
- RWA "smoke test" deals and whitelisted test borrowers produce absurd-looking loan shapes
  (1 NFT collateral vs $100k principal). Trace the loan's creation tx before calling it a bug —
  LoopScale's were created via Squads `VaultTransactionExecute` for the protocol's own test key.
- Vision/OCR may be unavailable; verify screenshots with the PIL unique-grey ink check and a
  `--dump-dom` content grep instead.
