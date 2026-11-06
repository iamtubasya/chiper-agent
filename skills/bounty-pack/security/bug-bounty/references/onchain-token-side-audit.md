# On-chain Token-Side Audit (lending-listed underlying tokens)

Class: verifying the ERC20s *behind* cTokens of a Compound-v2 fork (fee/rebase/blacklist
vs exchange-rate accounting, mint/pause authority, proxy control). Session: CapyFi
(RPC/wARS/LAC), Sept 2026. Artifacts: `D:\data hermes\bug-bounty\_progress\capyfi\tokens\`
(`*_impl.sol`, `roles.json`, `fetch_roles.py`).

## 1. Find the REAL chain first — do not trust labels
- DefiLlama `https://api.llama.fi/protocol/<slug>` → `chain`/`chains` list. CapyFi said
  "LaChain Network" but the audited mainnet deployment was **Ethereum mainnet**.
- Discriminator: canonical Chainlink feed addresses (USDT `0x3E7d1eAB...`, ETH
  `0x5f4eC3Df...`) + `eth_getCode` on the Unitroller across every candidate RPC.
  Empty code = wrong chain, even if chainId handshake succeeds.
- Repo `HelperConfig.sol` often lists *alternative* deployments (e.g. "latestnet") —
  cross-check all proxy addrs, don't assume the config you see is the live one.
- Market enumeration: `eth_call` Unitroller `getAllMarkets()` selector `0xb0772d0b`;
  decode ABI array — **word0 = offset, word1 = count**; slicing from word0 yields fake
  addresses like `0x...20`. Correct: `["0x"+d[24+64*i : 64+64*i] for i in range(n)]`
  where `n=(len(d)//64)-1`.
- Per-market state: `underlying()`, `symbol()`, `decimals()`, `getCash()` `0x95dd9192`,
  `totalBorrows()` `0x47bd3718`, `totalSupply()` `0x18160ddd`, `exchangeRateStored()`
  `0x36c2b946`. Parse hex with `int(x, 16)` (a plain `int(x)` "fails silently" as
  exception — looks like a missing function, it isn't).

## 2. RPC plumbing (public endpoints bite here)
- Use the QuikNode/Helius URLs from `D:\data hermes\rpc\rpc_live.md`. Public ones
  (flashbots, llamarpc) **whitelist methods** → `eth_call` rejected with -32601;
  getCode may still work (misleading "contract doesn't exist" — retry on the good RPC).
- QuikNode `eth_getLogs` range cap = **10,000 blocks** (error -32614). Chunk loops.
- Long scans: `execute_code` dies at 300 s → write a script under the target's
  `_progress/<target>/` dir and run via `terminal(background=true, notify_on_complete)`.
- **Locate deployment block by binary search on `eth_getCode`** (~5 calls) instead of
  scanning event logs from block 0 — turns a 20-min scan into seconds. Then query the
  narrow window around it.
- Verify Etherscan V1 API is dead here → get verified source from Blockscout v2:
  `https://eth.blockscout.com/api/v2/smart-contracts/{addr}` (`source_code`,
  `is_verified`, `proxy_type` (eip1967/transparent), `creation_bytecode`).
  The `logs?topic=` filter endpoint is unreliable (returns 0/false negatives) —
  use `eth_getLogs` on RPC instead.
- `creation_bytecode` tail reveals the proxy's **initial impl + admin + init calldata**
  (constructor args appended) — that's how RPC's V1 impl was recovered.

## 3. Access-control archaeology (OZ AccessControl without Enumerable)
- `hasRole(bytes32 role, address account)` — **bytes32 FIRST**, selector `0x91d14854`.
  Common self-inflicted "REVERT": calling `hasRole(address,bytes32)` (`0xac4ab3fb`)
  hits no function. Sanity-probe with `getRoleMemberCount(bytes32)` `0xca15c873`:
  reverts ⇒ contract is plain AccessControl (no Enumerable) ⇒ members are
  **not enumerable on-chain** ⇒ reconstruct from events.
- Role membership truth = `RoleGranted(bytes32,address,address)` topic0
  `0xREDACTED_********` minus
  `RoleRevoked(bytes32,address,address)` topic0
  `0xREDACTED_********`.
  Index topics[1]=role, topics[2]=account, data[3]=sender. Query only the windows
  around deploy/upgrade blocks (roles are usually granted at `initialize()`).
- Role hash constants: `keccak256("PAUSER_ROLE")` etc. — read them live from
  `PAUSER_ROLE()/MINTER_ROLE()/UPGRADER_ROLE()` instead of hardcoding.

## 4. Proxy/admin topology
- EIP-1967 slots: impl `0xREDACTED_********`,
  admin `0xREDACTED_********`.
- TransparentUpgradeableProxy: `admin()` reverts for non-admin callers (also in
  `eth_call` from zero address) ⇒ read the admin **slot**, don't call the getter.
  Admin is normally a `ProxyAdmin` (OZ) — then `owner()` of THAT is the real key;
  follow the chain to an EOA or Safe.
- Identify Safes cheaply: `eth_getCode` len ≈ 344 ⇒ Gnosis SafeProxy (minimal
  delegate shim). Read its singleton from storage slot 0, then call
  `getOwners()`/`getThreshold()` on the proxy. Same 344-length trick for
  LAC's owner. Beware `getOwners()` decode: word0 = offset `0x20`, word1 = count.
- Impl contract has **empty storage** — ERC20 views return "" / hasRole returns
  false there; that is NOT a signal of broken roles, only of querying the wrong
  address. Always query through the proxy.

## 5. Token-risk checklist vs Compound accounting (what actually matters)
- Exchange-rate integrity breaks only on: fee-on-transfer, rebase/supply-changing
  hooks, transfer-blocking (blacklist/gas-token/return-false), decimals mismatch.
  Grep impl source for `_update`/`_beforeTokenTransfer`/`_transfer` overrides,
  `blacklist`, `fee`, `excludeFromRewards`. All three CapyFi exotics (RipioCoinV2,
  LatamStable/wARS, LaCoin/LAC) = clean OZ ERC20 + Pausable (+Permit/Votes/Burnable)
  ⇒ **accounting-safe**. State this as a negative result explicitly; it kills
  several false-positive chains in the report.
- Residual real risk for listed third-party tokens (reportable, usually
  Low-Med / informational-by-design depending program rules):
  - `pause()` (global, no exemptions) freezes `repayBorrow`/`liquidateBorrow`/
    `redeem` for that market while interest keeps accruing ⇒ bad-debt growth.
  - `MINTER_ROLE` ⇒ unlimited supply for a collateral/borrow asset (price-feed
    bounds on CapyFi's manual feeds blunt direct oracle manipulation).
  - Upgrade authority (UUPS `UPGRADER_ROLE` / Transparent `ProxyAdmin.owner`) ⇒
    malicious impl can mint/pause at will. Check whether it is a Safe or single EOA:
    wARS granted DEFAULT+PAUSER+MINTER+UPGRADER all to ONE address `0x5ca3f8ee…`
    (which is also an owner of LAC's 4-of-7 Safe) ⇒ concentration, not just
    upgrade-path risk. Cross-link role holders across the target's token set —
    shared keys are the finding.
  - CapyFi's own ProxyAdmins/Safes vs *token issuer* keys: issuer-controlled
    freeze/upgrade is third-party risk, NOT a CapyFi bug — frame severity accordingly
    (per §"no severity inflation": blocked chain = info).
- caWARS borrow-only market (CF 0) had ~491M wARS borrows vs 260M cash ⇒ issuer
  pause/mint on a borrow-heavy market is the highest-impact concrete scenario.

## 6. Style notes that paid off this session
- Terse progress lines in Indonesian + code blocks; "Pasar lengkap = Ethereum
  mainnet"-style declarations. Save intermediate JSON (`roles.json`) so a killed
  background scan isn't re-run from scratch.
- When a selector "reverts", first suspect your own ABI (arg order, int(x,16),
  proxy-vs-impl) before concluding the function doesn't exist. Three separate
  false conclusions this session were all self-inflicted selector/decode bugs.
