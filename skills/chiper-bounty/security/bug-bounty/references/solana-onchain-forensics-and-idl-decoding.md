# Solana On-Chain Forensics with an Available IDL/Client (LoopScale session, 2026-10-18)

Companion to `rust-solana-audit--blackbox-onchain-analysis.md` (which assumes NO source/IDL).
Use this when the protocol publishes a client repo (codama-generated Rust/TS IDL) or you can
otherwise get exact account/instruction layouts. Worked on LoopScale (Solana lending protocol,
closed-source program, open client at palindrome-eng/loopscale-client).

## 0. Find the RPC before anything else

Subdomain DoH sweep often reveals a protocol-run RPC that is faster and unthrottled vs public
endpoints (found `rpc.loopscale.com` this way; `dns.google/resolve?name=<host>&type=A`, then
probe `GET /` — a Solana RPC answers `405 Method not allowed. Use POST JSON-RPC.` with
`server: Google Frontend`). An open RPC is usually intended for their frontend; note it, do not
report it alone.

## 1. IDL from the client repo gives you exact layouts

A codama-generated client (`clients/rust/src/generated/`) contains:

- `accounts/*.rs` — every account struct with field order AND `LEN` (verify: sum of field sizes
  must equal LEN, e.g. Loan = 1634 bytes — a free correctness check on your decoder)
- `instructions/*.rs` — account lists with signer/writable flags (scan for authority-ish fields
  that are NOT signers — the missing-signer bug class) and `*InstructionArgs` structs
- `errors/*.rs` — the full error catalog (LoopScale: 150 codes). The error list tells you which
  checks EXIST on-chain; absence of an error for a check is a hunting lead
- `types/*.rs` — Pod type sizes you need for borsh offsets:
  `PodU64`=8, `PodU32CBPS`=4, `PodU64CBPS`=8, `PodDecimal`=24 (18-dec fixed point),
  `Duration`=PodU32(4)+u8(1)=5, Pubkey=32

**Hand-rolled borsh decoder pattern** (no deps, works on any host): parse the struct field by
field with `struct.unpack_from`, base58-encode pubkeys with a ~10-line pure-Python base58
(ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"). Validate the decoder
against ONE account whose values you know from an API/indexer before trusting a batch decode.

## 2. getProgramAccounts pitfall: memcmp + dataSlice

`getProgramAccounts` with `memcmp` filter AND `dataSlice:{offset:0,length:0}` SILENTLY IGNORES
the memcmp on many RPCs and returns ALL program-owned accounts (got 47,507 for every
discriminator). Fix: either fetch with full data and filter client-side, or use a dataSlice
length > 0. A uniform identical count across different discriminators is the tell.

## 3. Upgrade-authority forensics (reusable finding class)

For ANY upgradeable Solana program, the on-chain upgrade control is readable by anyone:

```
program account data (36B): bytes[4:36]  = programdata address
programdata account data:  bytes[12:44] = upgrade authority pubkey
```

Then classify the authority address with getAccountInfo:

| Observation | Meaning |
|---|---|
| owner = SQDS4ep65T..., data > 0 | real Squads multisig (decode config for members/threshold) |
| owner = system program, data length 0 | plain wallet (even if docs call it "the multisig") |
| account does not exist | bare keypair = single EOA key |

**The finding shape**: docs promise "3/5 multisig upgrades" but programdata shows a bare
single key -> one compromised key replaces program logic (drain vaults, reprice oracles).
Cross-check the real Squads multisig (find it in a `VaultTransactionExecute` tx from the SQDS
program) and confirm it is NOT the upgrade authority. Severity: Medium — centralization gap
with a documentation contradiction; triagers may class it as accepted risk, so lead with the
docs-vs-chain proof, not with "admin can rug". Same check applies per-program (core, oracle,
vault programs often have DIFFERENT authorities — enumerate all executable programs the
protocol documents).

## 4. Oracle account decoding + off-chain cross-check

Multi-asset oracle accounts (BEAM-style) are one big account with fixed-stride entries:
LoopScale NAV oracle = 152-byte entries `[32B mint][u64 price 18dp][u64 dup][u64 ts][pad]`,
33 entries. Decode by locating each collateral pubkey with `data.find(pubkey_bytes)`, sort
offsets, confirm uniform stride, then read price/ts relative to each entry start.

**The high-value cross-check**: compare on-chain oracle values against the protocol's own
off-chain record (deals/valuations API, partner submissions). What to look for:

- on-chain value == last ACCEPTED off-chain submission while newer submissions sit in a
  held/pending state (a -36.5% NAV drop was stuck in `held_for_ack` for 87 days while the
  on-chain value stayed at the old price)
- **timestamp refresh on frozen values**: the pusher rewrites the same value with a fresh
  timestamp every ~30 min, so the on-chain `maxAge` staleness check can NEVER trip. The
  freshness signal is decoupled from the data age. Observation-grade unless real (non-test)
  loans sit against the stale collateral — check loan collateral mints against the oracle
  entries before claiming impact
- who writes: pull `getSignaturesForAddress` on the oracle account, decode one tx — a single
  pusher key calling `WritePriceEntry` (price NOT in instruction data; read from a referenced
  account) is the documented centralization design, not a bug by itself

## 5. Loan/position health sweeps

To find liquidation gaps: pull all loans via the protocol's own indexed API (paginated
`/loans/core`-style endpoints), then fetch computed health per borrower via the user-scoped
endpoints (the BOLA endpoint doubles as an analysis oracle once found). Sort by healthRatio;
anything < ~0.02 that persists = liquidation-engine gap. LoopScale result: lowest 5.1%, none
underwater — a clean negative worth stating in the report.

## 6. Mintlify docs recon (any Mintlify-hosted target)

- `https://<host>/llms.txt` = complete page index (fetch first, maps the whole surface)
- append `.md` to any page URL for clean markdown (e.g. `/resources/audits.md`) — beats
  HTML stripping
- Mintlify sites are Next.js SSR; raw curl gets full content, no browser needed
- the OpenAPI spec is often at `/api-reference/openapi.source.json` — full endpoint list +
  schemas + server base URLs in one fetch (LoopScale: 126 paths, found the real API host
  `tars.loopscale.com` and a staging Cloud Run URL this way)
