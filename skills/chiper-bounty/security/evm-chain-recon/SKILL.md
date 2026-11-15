---
name: evm-chain-recon
description: "Black-box forensics of unknown EVM and Solana chains from public RPC."
version: 1.0.0
author: Hermes
tags: [web3, evm, rpc, chain-recon, testnet, forensics, security]
metadata:
  hermes:
    tags: [web3, evm, rpc, chain-recon, testnet, forensics, security]
    related_skills: [security-recon, web3-audit, offensive-osint]
---

# EVM Chain Recon — Black-box Forensics from a Public RPC

> Class-level skill. Verified workflow from the Monarca/SELEMAN audit (2026-09-24),
> where a chain (chainId 73571) was found only via a subdomain `/rpc` endpoint and had
> no explorer, no docs, and mislabeled DefiLlama addresses. Everything below worked
> with NOTHING but JSON-RPC over HTTPS.

## When to use
- Recon surfaces an RPC URL for an unfamiliar chain (subdomain `/rpc`, `/api` 301 to an
  explorer domain, ChainList/DefiLlama entry).
- Explorer/adapter claims (TVL, DEX pairs, factories) look wrong, stale, or point at
  addresses with no bytecode.
- You need to answer: **what is this chain, who is on it, where is the value, is it
  worth a full contract audit?**

## Phase 0 — Connection gotchas (all hit live, all verified)
1. **CF-fronted RPC may return EMPTY data instead of 403 when User-Agent looks non-browser-like.**
   Symptom: `eth_blockNumber` → `"0x0"`, `eth_getCode` → `"0x"` for contracts that DO have
   bytecode. Add `-A "ethers/6.13/axios"` (curl) or a `User-Agent` header (urllib/requests).
   Do NOT read empty results as "empty chain" — re-verify with a realistic UA first.
2. **`eth_call` param shape:** params[0] must be a JSON object `{"to":..,"data":..}`,
   params[1] = `"latest"`. Passing a pre-serialized JSON *string* as params[0] →
   `cannot unmarshal string into Go value of type ethapi.TransactionArgs`.
3. **`eth_getLogs` without filters times out** (`-32002 request timed out`) even in
   ~50k-block chunks. ALWAYS filter by `address` (and topic) — an address-filtered
   full-range query returns instantly and gives a token's complete history.
4. **Kernel cwd ≠ terminal cwd.** Files written by `terminal` in its working dir are
   invisible to `execute_code`/sandboxed Python — pass ABSOLUTE paths between the two.

## Phase 1 — Method allowlist (the node's posture)
Probe ~80 methods in one pass and classify each as: allowed / `method not allowed on
public RPC` / param-error / unknown. Dump the classification to disk; don't re-probe.

Probe set:
- `eth_*`: blockNumber, chainId, gasPrice, maxPriorityFeePerGas, syncing, accounts,
  getBalance, getCode, getStorageAt, getTransactionCount, getBlockByNumber/Hash,
  getTransactionByHash, getTransactionReceipt, estimateGas, call, getLogs, feeHistory,
  sendRawTransaction, newFilter/newBlockFilter/newPendingTransactionFilter,
  uninstallFilter, getFilterChanges, getFilterLogs
- `net_version`, `net_peerCount`, `net_listening` · `web3_clientVersion`, `web3_sha3`
- `admin_*`: peers, nodeInfo, datadir, unixSocket, fullSanityCheck, setHead
- `debug_*`: traceBlockByNumber, traceBlock, storageRangeAt, getBadBlocks, getBlockRlp
- `trace_*`: block, filter, transaction, call, replayBlockTransactions
- `miner_*`: start, stop, setEtherPrice · `personal_*`: listAccounts, newAccount,
  sendTransaction, unlockAccount, sign, signTypedData
- `txpool_status`, `txpool_content`, `txpool_inspect`
- PoA snapshot namespaces: `clique/ibft/parlia/authority/poa_getSnapshot`
- consensus/payload: `engine_getPayload`, `engine_forkChoiceUpdated`

Read the result the same way a node-admin config would:
- Strict allowlist (`not allowed on public RPC` on all sensitive) = correct lockdown,
  a **positive observation**, not a finding.
- `eth_sendRawTransaction` reachable through the allowlist is **normal for any public
  chain** (that's how you submit txs). A well-formed EIP-155 tx with a fake sig →
  `invalid sender` after passing signature recovery = working as designed. Only report
  if the node exposes `admin_*`/`debug_*`/`personal_*`/`miner_*` (then it's critical).

## Phase 2 — Chain identity + liveness
```
web3_clientVersion      # Geth/vX.Y.Z-stable-.../linux-amd64/go...
eth_chainId, eth_blockNumber, eth_gasPrice, eth_maxPriorityFeePerGas
net_peerCount, net_listening, eth_syncing
eth_getBlockByNumber 0x0   # genesis: timestamp, extraData, difficulty, totalDifficulty
eth_getBlockByNumber latest # head: timestamp, miner field, txs
```
Interpretation:
- Recent genesis timestamp + difficulty `0x1` + totalDifficulty `0x1` + PoA-looking
  extraData (hash blob) + `net_peerCount` < 10 + `miner` = zero address →
  **fresh private/testnet/GPU-simulator chain**. Set expectations: no mainnet value.
- `eth_getBalance` on the deployer(s) you find next: trivial native balance reinforces
  testnet verdict.
- `identityMode: parent-fork` in a sister explorer's token list + a cached parent-chain
  (e.g. Ethereum) token registry = fork testnet; all "tokens" may be parent fakes.

## Phase 3 — Full contract-creation enumeration (young chains are SHORT)
Walk blocks `0x1 .. ~0x500` (adjust: young testnets rarely exceed ~10k blocks):
1. `eth_getBlockByNumber(n, true)` for each block.
2. Every tx with `to == null` / `""` = **contract creation** →
   `eth_getTransactionReceipt(hash)` → `contractAddress` + `status`.
3. Record deployer, deploy gas, input length, tx timestamp.

Then classify:
- One deployer mass-deploying one identical template (same input length, e.g. ~3.2KB)
  across consecutive blocks = **simulation/GPU workload**, not an organization's app.
- Small number of distinct deployers with distinct contracts = real ecosystem; dig each.
- `inputLen` differences at the same deployer often = same template with a different
  constructor arg (e.g. different symbol).

## Phase 4 — Token/ABI forensics per candidate contract
For each interesting `contractAddress`:
1. `eth_getCode` → `0x` = EOA/dead (drop). Note bytecode size; ~1.5KB is a small
   custom token, ~3-15KB typical Solidity, >100KB proxy-ish/verified-library.
2. Standard ERC20 view selectors (batch, short sleep between calls):
   | selector | fn |
   |---|---|
   | `0x06fdde03` | name() |
   | `0x95d89b41` | symbol() |
   | `0x313ce567` | decimals() |
   | `0x18160ddd` | totalSupply() |
   | `0x8da5cb5b` | owner() |
   | `0x70a08231` + addr | balanceOf(addr) |
   | `0x095ea7b3` + addr | approve |
   | `0xa9059cbb` + addr,amt | transfer |
   | `0x23b872dd` + from,to,amt | transferFrom |
   | `0xdd62ed3e` + owner,spender | allowance |
   Dynamic strings: decode offset/len at words 1-2 (`ln=int(b[32:64])`, value `b[64:64+ln]`).
3. **Non-standard custom tokens** (custom storage layout, misspelled revert strings):
   read `eth_getStorageAt` slots `0x0..0xc` and decode ASCII/uints. E.g. slot0 = name,
   slot1 = symbol, slot2 = decimals, slot3 = totalSupply.
4. **Embedded revert strings in the deployment calldata** reveal dev naming even with a
   fully custom ABI: `re.findall(rb'[ -~]{6,}', bytes.fromhex(calldata[2:]))` —
   e.g. `"SEED: allownance"`, `"Alkimi [OLD]"`.
5. ERC721 candidates: try `0x80ac58cd` (tokenURI), `0x01ffc9a7` (supportsInterface),
   `0x6352211e` (ownerOf).

## Phase 5 — Event history without an explorer
```
eth_getLogs {"fromBlock":"0x0","toBlock":"latest","address":CONTRACT}
```
- Transfer topic0 = `0xddf252ad...55a4df523b3ef84`.
- topic1 == 20-byte zero = **MINT**; topic2 == zero = BURN.
- Aggregate holders, total minted, distribution, and first-mover.
- A contract with totalSupply > 0 but only 2 Transfer events and no DEX pair =
  launched-and-abandoned; no liquidity to attack.

## Phase 6 — DEX / value check
- Uniswap-V2 factory selectors: `0xe6a43905` (getPair), `0xf851a440` (allPairs).
  `execution reverted` on a 1.5KB "factory" = it's a token, not a DEX.
- Cross-check adapter/registry claims (DefiLlama PRs, ChainList): if their "factory"/
  "pair"/token addresses have **no code** on the live chain, the chain re-forked or the
  registry is stale — treat registry data as unverified.
- Value gate: if there is no DEX, no liquidity, peerCount < 10, and deployer balances
  are dust → **no bounty-grade value on-chain**. Kill the contract-audit track and say so
  explicitly (a fresh testnet with simulation workloads is not a DeFi protocol).

## By-design calibration (never report as findings)
- Public testnet RPC accepting `eth_sendRawTransaction` (EIP-155 replay-protected;
  fake sig → `invalid sender` after passing sig-recovery) = how public chains work.
- Public list endpoints (tokens/blocks/txs) on a testnet explorer = intended public access.
- A strict RPC method allowlist = correct lockdown, a POSITIVE observation.
- Parent-fork token lists (Ethereum token registry replayed on a testnet) = by design.

## Output discipline
- One `$DIR/evidence/BUNDLE.txt` per chain: allowlist table, genesis/head, deployers,
  contract table (addr, deployer, blk, template?), token table, events summary, DEX
  verdict, value verdict.
- Context gets only the verdict; the bundle stays on disk.
- Pair with `web3-audit` (class-level contract hunting) ONLY after Phase 6 says value
  exists; pair with the `security-recon` skill's `references/rpc-fingerprint.md` for
  node-posture reporting.

**Solana/Anchor targets** (program IDs published, any reachable RPC): the same
locate→enumerate→decode→authority spine with Solana tooling lives in
`references/solana-rpc-forensics.md` — IDL-discriminator account enumeration, borsh
decoding from codama-generated types, the BPFLoaderUpgradeable programdata layout for
upgrade-authority extraction (bare-pubkey vs Squads-vs-wallet classification, the
documented-multisig-vs-on-chain-reality finding pattern), write-path signer analysis via
getSignaturesForAddress/getTransaction, multi-asset oracle account stride decoding with
off-chain cross-check, and the by-design calibration list (single pusher keys, admin
authorities, multisig-created bootstrap positions are NOT findings).

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Method allowlist census (~80 method, satu pass, dump ke disk) | Node posture: strict allowlist = positive observation, BUKAN finding |
| 2 | CF-fronted empty-data check: `eth_getCode` → `0x` → re-test dengan UA browser | CF bisa balas `0x0`/`0x` alih-alih 403; jangan baca sebagai "empty chain" |
| 3 | Full contract-creation enumeration blok 0x1..~0x500 | Young chain pendek; deployer + template bisa dikenali dari sini |
| 4 | Value gate: DEX pair ada? liquidity ada? deployer balance dust? | Tidak ada value = kill contract-audit track, katakan eksplisit |
| 5 | Registry cross-check: alamat DefiLlama/ChainList punya bytecode? | Registry stale = chain re-fork; treat registry data as unverified |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## 2026 sweep (chain recon yang masih jadi jebakan)

- **EIP-7702 delegated EOA** — chain dengan 7702 aktif: `eth_getCode` pada EOA bisa balik delegation-designation (0xef0100...). Jangan klasifikasi sebagai "EOA/dead" dan drop.
- **ERC-7579 account module** — smart account yang install module registry: enumerasi module via `accountId` selector, bukan cuma ERC20 view.
- **Sequencer-uptime feed sebagai chain-posture signal** — L2 RPC yang balas `eth_blockNumber` beku = sequencer down, bukan chain mati. Cek uptime feed sebelum klaim "chain dead".
- **Parent-fork token registry** — explorer dengan `identityMode: parent-fork` me-replay registry chain induk; semua "token" bisa jadi fake. Cek bytecode tiap alamat sebelum percaya.
- **PoA snapshot namespace** — `clique`/`parlia`/`authority` snapshot mengungkap validator set; berguna untuk menilai sentralisasi chain sebelum audit.


## Critical severity anchor (apa yang membuat temuan dari skill ini Critical)

Skill ini menghasilkan *chain posture*, bukan bug. Yang membuatnya Critical adalah kalau node
atau registry mengungkap akses yang seharusnya tertutup:

| Temuan recon | Severity |
|---|---|
| `admin_*`/`debug_*`/`personal_*`/`miner_*` terbuka di public RPC | Critical |
| `txpool_content` terbuka → melihat pending tx termasuk yang sensitif | High-Critical |
| `debug_traceTransaction` terbuka → analitik penuh atas semua tx | Medium-High |
| Registry (DefiLlama/ChainList) menunjuk alamat tanpa bytecode | Info (stale registry) |
| Strict method allowlist | **positive observation** — BUKAN temuan |
| `eth_sendRawTransaction` reachable | normal untuk public chain |

**Kalibrasi wajib:** `eth_sendRawTransaction` yang bisa diakses public RPC = cara kerja chain
publik (EIP-155 replay-protected; fake sig → `invalid sender`). Jangan lapor. Hanya laporkan
kalau namespace sensitif (`admin`/`debug`/`personal`/`miner`) benar-benar terbuka.


## Exposed RPC: debug_ / admin_ / personal_ (added 2026-10-30)

Black-box recon of an unknown chain stops at "what is this chain". This section is the step that
actually pays: deciding whether the node's RPC is **misconfigured open** or just public-read.

### Step 1 — enumerate enabled modules (never assume)
```
curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"rpc_modules","params":[],"id":1}' https://RPC/
```
`rpc_modules` returns the enabled namespaces. Public-read nodes return `eth,net,web3`.
Anything containing `admin`, `personal`, `debug`, `miner`, `txpool`, `les`, `clique` is a lead.

### Step 2 — probe the namespaces that matter
```
admin_nodeInfo          admin_peers            admin_datadir
personal_listAccounts   personal_unlockAccount eth_accounts
debug_traceTransaction  debug_traceCall        debug_setHead
miner_start / miner_stop                       txpool_content
```
- `eth_accounts` returning a **non-empty** list means node-managed accounts exist.
- `personal_listAccounts` non-empty + `personal_unlockAccount` succeeding = the node will sign and
  send transactions for you. That is the fund-loss path, not a recon curiosity.
- `admin_addPeer` / `admin_setHead` / `debug_setHead` succeeding = control of node state.
- `admin_datadir` succeeding = filesystem path disclosure, useful pivot into LFI chains.

### Step 3 — prove impact, safely
```
# DO NOT move third-party funds. Use an account you control.
cast rpc --rpc-url $RPC personal_unlockAccount 0x<YOUR_ACCOUNT> '' 60
cast rpc --rpc-url $RPC eth_sendTransaction '{"from":"0x<YOUR_ACCOUNT>","to":"0x<YOUR_ACCOUNT>","value":"0x1"}'
```
A self-transfer of 1 wei from an unlocked node account proves signing authority without touching
anyone else's assets. If `personal_*` is disabled but `eth_sendTransaction` still works with an
unlocked account, that is the same finding.

### The distinction that decides reportability
| Observation | Verdict |
|---|---|
| `eth_call`, `eth_getLogs`, `eth_getBalance` work | **By design — NOT a finding** |
| Port 8545 open, `rpc_modules` shows only `eth,net,web3` | **Not a finding** |
| `admin_*` / `debug_*` enabled but every call errors with "method not allowed" | Not a finding |
| `personal_unlockAccount` succeeds + `eth_sendTransaction` signs | **Critical — signing authority** |
| `admin_addPeer` / `debug_setHead` / `admin_datadir` succeed | **High→Critical — node control / path disclosure** |

Always test with your own account. Never unlock or move an account you do not own.

### Chains
- `admin_datadir` → path disclosure → LFI/`eth_getProof` abuse → file read
- `personal_unlockAccount` → `eth_sendTransaction` → drain any node-managed account
- `debug_traceCall` on a contract → internal call graph → reveals privileged entry points
- exposed RPC → `admin_addPeer` → eclipse/sybil the node → consensus-level impact
