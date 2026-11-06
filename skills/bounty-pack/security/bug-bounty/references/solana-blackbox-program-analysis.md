# Solana black-box program analysis (no source)

When the program source is closed but the protocol is live on mainnet, public RPC plus the client
IDL give you a full analysis surface. Worked end-to-end on LoopScale (core `1oopBoJG...`, BEAM
oracle `beamVVk...`, 2026-10): produced a single-key upgrade-authority finding contradicting
documented 3/5-multisig control, decoded the RWA NAV oracle, and mapped the co-sign architecture.

## 1. Get the IDL from the client repo
Search GitHub for `<protocol>-client`, `generated`, codama. `palindrome-eng/loopscale-client`
carried the full IDL: account discriminators, per-instruction account metas WITH signer flags,
borsh struct layouts, and a 150-entry error enum. The error enum is a free checklist of what the
program validates (oracle staleness, uncertainty, slippage, weight-matrix, caps, timelocks) -
absence of an error code is where to hunt.

## 2. Decode accounts with a from-scratch borsh reader
- Discriminators: `grep DISCRIMINATOR clients/rust/src/generated/accounts/*.rs`
- Pod types: PodU64=8B, PodU32CBPS=4B, PodDecimal=24B (10^18 scaled), Pubkey=32B
- Worked Loan layout (1634B, validated against the project's own indexed API):
  disc(8) version(1) bump(1) status(1) borrower(32) nonce(8) start(8) ledgers[5]x182
  collateral[5]x73 weight/ltv/lqt matrices 3x(5x5x4)
  - Ledger(182): status(1) strategy(32) principalMint(32) marketInfo(32) due(8) repaid(8)
    interestOut(8) lastUpdate(8) duration(4+1) interestPerSecond(24) start(8) end(8) apy(8)
  - Collateral(73): mint(32) amount(8) type(1) identifier(32)
- ALWAYS validate the decoder against a known account before trusting any decoded value
- `getMultipleAccounts` in batches of ~20; `getProgramAccounts` with `dataSlice length 0`
  IGNORES memcmp on some RPCs and returns every program account - never trust that count

## 3. Upgrade authority: the docs-vs-chain check (finding class)
BPFLoaderUpgradeable layout:
- program account (36B): bytes 4-36 = programdata address
- programdata: bytes 4-12 = last deploy slot, bytes 12-44 = upgrade authority
- authority account NOT FOUND on-chain => bare EOA keypair (single key)
- authority owned by `SQDS4ep65T...` => Squads vault PDA (multisig-controlled)
- a "documented multisig" that is system-owned with 0 data is a plain wallet, not a multisig
- a real Squads multisig is SQDS-owned WITH config data; its vault PDA is system-owned, 0 data,
  and is referenced inside the multisig config
Report shape: docs claim 3/5 multisig -> on-chain shows one bare key on BOTH core and oracle
programs -> Medium (centralization + documentation-accuracy gap; state honestly that key custody
is unknown and the finding may triage as informational).

## 4. Instruction co-sign mapping
Regex every `instructions/*.rs` for `AccountMeta::new(?:_readonly)?\(self\.(\w+),\s*(true|false)`
to build instruction -> signer list. Look for fund-moving instructions missing the expected
co-signer, and check whether exceptions are by design (liquidations MUST be permissionless for
solvency; market-info updates are admin functions). A consistent co-sign architecture is a
NEGATIVE worth reporting to the operator ("your safeguard works as documented").

## 5. Multi-asset oracle account decoding
- base58-decode each configured collateral mint; `data.find(pubkey_bytes)` gives entry offsets
- offset differences reveal the stride (LoopScale NAV: 152B entries)
- field map recovered: pubkey(32) price(8, 18-decimal fixed point) pad(24) price-dup(8) pad(16)
  timestamp(8, unix) - validate by cross-checking known values against an off-chain source
  (the deals API NAVs matched the decoded prices exactly)
- cross-check on-chain values+timestamps against the off-chain submission DB: a refreshed
  timestamp on a frozen value (87-day-old accepted NAV with freshened ts) is a liveness-masking
  design observation - only a finding if real (non-test) loans sit behind it

## 6. Transaction tracing
`getSignaturesForAddress(account, {limit})` -> `getTransaction(sig, {encoding:"jsonParsed",
maxSupportedTransactionVersion:0})` -> read `meta.logMessages` for `Instruction: X` and the
account lists. A loan account's own history reveals its creation path (LoopScale RWA loans were
created via Squads `VaultTransactionExecute` -> `CreateLoan`, i.e. protocol bootstrap positions,
not user flow - which reframed an "impossible LTV" non-finding before it was reported).

## 7. RPC + authz discovery
- `rpc.<domain>` via DoH; a JSON-RPC endpoint answers GET with "Method not allowed. Use POST
  JSON-RPC" (405)
- API authz map: probe every endpoint (GET bare / POST `{}`), classify by status code; use the
  ERROR DIFFERENTIAL to name the mechanism (`ApiKeyNotFound` vs `Invalid or disabled API key`
  once a header is supplied => that header is the key slot; `User Wallet not in headers` =>
  presence-only header auth). Negative control (random address -> empty 200) proves
  data-dependent responses
- presence-only header auth (no signature) on user-scoped endpoints = systemic BOLA; a sibling
  endpoint that DOES require a signature is the in-codebase proof the pattern exists

## Pitfalls
- Repeated POSTs to a write endpoint with an INVALID address produced a 500 storm - validate
  addresses before probing; a mid-session 500 is usually your own bad input, not a new bug
- base58: implement encode+decode inline (no dependency guaranteed on this host)
- Rate limits: per-IP on expensive endpoints; space probes, run big maps in background
- An RPC's `getProgramAccounts` memcmp may be silently ignored (see section 2) - verify counts
  against a second source before concluding anything about account populations
