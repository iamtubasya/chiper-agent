# Solana black-box forensics from a public RPC

Same class as the EVM phases in the parent SKILL.md, Solana tooling. Verified live on the
LoopScale audit (2026-10-18/19): core program `1oopBoJG58DgkUVKkEzKgyG9dvRmpgeEm1AVjoHkF78`,
BEAM oracle `beamVVkNmKeXcuZ6zLpC9eM5YgVyAn4Z9xdPrz3gCW2`, open RPC found at
`rpc.loopscale.com` via subdomain DoH sweep. Everything below used nothing but JSON-RPC 2.0
over HTTPS plus a Python borsh decoder built from the target's own IDL.

## When to use
- A Solana/Anchor target publishes program IDs (docs, audits page, frontend bundle) and any
  reachable RPC exists (subdomain `/rpc`, the app's own frontend RPC, a public endpoint).
- You need: who controls upgrades, who can move funds, is the on-chain state consistent with
  the published security documentation, where is the value.

## Phase 0 — RPC access and gotchas
1. Find the RPC: DoH-sweep subdomains (`rpc.`, `api.`, `node.`), grep the frontend bundle,
   check docs. `getAccountInfo` on a program ID that returns `executable: true` confirms a
   live program; `owner: BPFLoaderUpgradeab1e...` means upgradeable.
2. JSON-RPC 2.0 shape: `{"jsonrpc":"2.0","id":1,"method":...,"params":[...]}` POSTed with
   `Content-Type: application/json`.
3. **`getProgramAccounts` with `dataSlice: {length: 0}` IGNORES the memcmp filter** — it
   returned the full program account count (47,507) for every discriminator. Either fetch
   full data and filter client-side, or use a non-zero dataSlice. Do not read the unfiltered
   count as "the filter worked".
4. `getTransaction` needs `maxSupportedTransactionVersion: 0` for versioned txs; `encoding:
   "json"` gives accountKeys with signer/writable flags, `"jsonParsed"` gives parsed
   instructions with resolved accounts.
5. dig/nslookup unreliable on this host — resolve via DoH (`dns.google/resolve?name=..&type=A`).

## Phase 1 — Account enumeration via IDL discriminators
Anchor accounts start with an 8-byte discriminator. Get them from the target's IDL
(codama-generated clients expose `pub const X_DISCRIMINATOR: [u8; 8]`, e.g. in
`clients/rust/src/generated/accounts/*.rs` of a published client repo). Then:

```python
def b58encode(b):  # base58 the discriminator for the memcmp filter
    ...
res = rpc("getProgramAccounts", [PROGRAM_ID, {
    "encoding": "base64",
    "memcmp": {"offset": 0, "bytes": b58encode(bytes(DISCRIMINATOR))},
    "dataSlice": {"offset": 0, "length": 0}}])
```

If the RPC ignores the filter (gotcha 3), paginate by fetching all accounts and filtering
locally, or use the target's own indexed API (if one exists) for the bulk set and spot-check
on-chain.

## Phase 2 — Decoding Anchor accounts (borsh from the IDL)
Codama-generated Rust types give you the exact borsh layout. Common Pod sizes:

| Type | Bytes | Notes |
|---|---|---|
| `Pubkey` | 32 | |
| `PodU64` / `PodU64CBPS` | 8 | |
| `PodU32CBPS` | 4 | |
| `PodDecimal` | 24 | 18-decimal fixed point |
| `Duration` | 5 | `PodU32` + `u8` |
| `[u8; 8]` discriminator | 8 | offset 0 |

Validate the decoder before trusting it: decode a known account (one the target's own API
also exposes) and assert borrower/amounts match. A decoder that reproduces one known loan
byte-for-byte is trustworthy for the rest.

## Phase 3 — Upgrade authority extraction (the highest-value 5 minutes)
For any upgradeable Solana program:

```
program account data (36 bytes): [4-byte enum][32-byte programdata address]
programdata account: [4-byte enum][8-byte slot][32-byte upgrade authority]  at offset 12
```

```python
prog_data = b64decode(getAccountInfo(PROGRAM_ID)["data"][0])
programdata = b58encode(prog_data[4:36])
pd = b64decode(getAccountInfo(programdata)["data"][0])
slot, upgrade_authority = unpack("<Q", pd[4:12])[0], b58encode(pd[12:44])
```

Then classify the authority:
- `getAccountInfo(authority)` → **not found** = a bare pubkey = a single EOA keypair holds
  upgrade rights (nobody can have "initialized" a signer-only address).
- owner = `SQDS4ep65T...` = a Squads vault PDA = multisig-controlled (good).
- owner = system program with data = a plain wallet.

**The finding pattern:** compare against the target's published security docs. LoopScale's
docs promised "All program upgrades require approval from a 3/5 multisig" and listed a
multisig address that was itself a plain wallet — while both the core program AND the oracle
program had the same bare single-key upgrade authority. A real Squads multisig existed
(GLke7iqy..., SQDS-owned, 495-byte config) and executed operations, but was NOT the upgrade
authority. That documented-control-vs-on-chain-reality gap is the reportable finding; the
single key alone is centralization risk most programs accept.

Calibrate honestly: report the gap between documented and actual control, state that you did
not attempt to use the key, and let the vendor explain custody. Do not inflate to Critical
without a demonstrated exploit.

## Phase 4 — Write-path authority analysis (who can move the numbers)
For any state account (oracle, config, vault):

```python
sigs = rpc("getSignaturesForAddress", [ACCOUNT, {"limit": 15}])
for s in sigs:
    tx = rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                 "maxSupportedTransactionVersion": 0}])
    # accountKeys[0] = fee payer/signer; find the target-program instruction and read its
    # accounts + the logMessages ("Instruction: WritePriceEntry" etc.)
```

This answers: which key writes this account, how often, in what instruction, and whether the
write path is a single hot key (documented centralization) or something broader. LoopScale's
NAV oracle: one pusher key (`4jHcKHTfb7...`) batching ~4 `WritePriceEntry` instructions per
tx every ~30 min — a documented design, not a finding, but the map you need before claiming
anything about oracle trust.

## Phase 5 — Multi-asset oracle account decoding
Oracle accounts that hold many asset prices in one account (LoopScale's BEAM NAV account:
76,656 bytes, 33 collaterals) decode by entry-stride discovery:

1. Base58-decode each known asset pubkey, `data.find(pubkey_bytes)` → offsets.
2. Sort offsets; a uniform stride (152 bytes here) confirms a fixed entry array.
3. Per entry: `[32B pubkey][8B value][...][8B value-dup][...][8B unix ts]` — the value was
   18-decimal fixed point ($15.75 stored as 15750000000000000000), confirmed by matching the
   target's own API/deals DB (`navBaseUnits "15750000"` = $15.75 at 6dp).
4. Cross-check every on-chain value against the off-chain source of truth (the target's API,
   a deals/valuations endpoint). On-chain NAV matched the last *accepted* valuation while a
   -36.5% valuation sat in `held_for_ack` — the staleness-masking observation (pusher
   refreshes timestamps on frozen values) came from that diff.

## Phase 6 — Squads multisig detection
- Real Squads multisig: `getAccountInfo` → owner `SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf`,
  data length ~495 bytes, contains the vault PDA.
- Vault PDA: system-owned, 0 data, holds SOL — the address that signs vault transactions.
- A "multisig" address in docs that is system-owned with 0 data is just a wallet. Verify
  every documented control address before repeating the claim in a report.

## By-design calibration (never report as findings)
- A single pusher key writing oracle prices on a schedule = documented centralization.
- A protocol admin authority updating market parameters (LTVs, caps) = admin function.
- An open public RPC serving getAccountInfo/getProgramAccounts = intended frontend infra.
- Protocol-created bootstrap/test positions executed through the multisig (e.g. 18 loans
  created via `VaultTransactionExecute` for a whitelisted test borrower with absurd LTVs) =
  intentional test setup, not an exploit — trace the creation tx before calling a state
  anomaly a bug.

## Output discipline
- One evidence file per program: upgrade authority + account checks, write-path signer map,
  decoded oracle table with cross-check column, discriminator→count table.
- The decoder script and the raw JSON stay on disk; context gets the verdict.
- Pair with `onchain-finding-verification` before any report; pair with `web3-audit` only
  after the on-chain state says there is value worth auditing.
