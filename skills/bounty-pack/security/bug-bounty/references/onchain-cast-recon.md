# On-Chain / DeFi Recon with Foundry cast (protocol triage playbook)

Applies when a bug-bounty target (Immunefi or similar) is a live DeFi protocol and on-chain
recon happens before/instead of code review. All examples from Benqi on Avalanche C-Chain.

## 0. Setup & RPC
- Always read `D:\data hermes\rpc\rpc_live.md` first for working RPCs.
- Avalanche C-Chain: `https://api.avax.network/ext/bc/C/rpc`.
- Fresh shells may lack Foundry: `export PATH="$HOME/.foundry/bin:$PATH"`.

## 1. Liveness gate — run FIRST, before any analysis
- `cast codesize <addr>` / `cast code <addr>` on every contract the docs/registry list.
- Registered-but-dead contracts are common: Benqi AVAX had a DEAD main comptroller
  (0x642C..., 0 bytes) while the live one was 0x486A...; 4 of 5 registered markets were
  zero-code; only qiAVAX was live.
- Findings reported against zero-code addresses = noise. Map code existence first.

## 2. Compound-fork market snapshot (batch these calls)
`totalSupply, totalBorrows, totalReserves, getCash, borrowIndex, exchangeRateCurrent,
borrowRatePerTimestamp, supplyRatePerTimestamp, reserveFactorMantissa, decimals, symbol`.
- Utilization = totalBorrows / (totalBorrows + cash − reserves).
- APYs from per-second rates × 31,536,000.

## 3. ⚠️ Exchange-rate scaling pitfall (top false-alarm generator)
- Textbook Compound V2: ER = (cash+borrows−reserves) × 1e(18+underlyingDec−cTokenDec) / totalSupply
  → 1e28 scaling for 18-dec underlying + 8-dec cToken.
- Benqi qiAVAX ACTUAL: ER = totalValue × **1e18** / totalSupply. The textbook formula showed a
  bogus "~1e12% mismatch"; 1e18 scaling matched the on-chain value to 0.000005%.
- RULE: never report a "mismatch" finding until the scaling convention is confirmed from the
  deployed bytecode or cross-checked across multiple markets. Wrong-scaling delta = agent math
  error, not protocol bug. Per EVIDENCE gate: unverified math is [THEORETICAL], never a finding.

### 3b. Immutable IRM params + delegate address discovery (Compound forks)
- IRM getters (kink(), jumpMultiplierPerTimestamp()) can REVERT when params are IMMUTABLE
  (no getters, no admin mutability — itself a good sign). Read storage slots directly:
  JumpRateModel layout slot0=multiplierPerTimestamp, 1=baseRatePerTimestamp,
  2=jumpMultiplierPerTimestamp, 3=kink (eth_getStorageAt; batch all markets in one script).
- Benqi uses per-TIMESTAMP rates (≈ per-second): APY = rate/1e18 × 31,536,000.
  Sanity range: base ~2%, jump 109–300%, kink 80–90%; kink=0 → flat base-rate market.
- qiAVAX implementation() reverts + EIP-1967 slot zero → market token is NOT a standard
  proxy. Get the QiErc20Delegate from the DELEGATOR's constructor args (explorer
  getsourcecode 'Implementation' field, or parse ctor args). Verified
  0x76145e99d3F4165A313E8219141ae0D26900B710 for all ERC20 markets.

## 4. cast output parsing pitfalls
- Human-readable `cast call` output appends scientific notation:
  `233298751317141288257325146 [2.332e26]` → Python `int()` ValueError.
  Strip with `| head -1 | awk '{print $1}'` or use `--to-raw`.
- ⚠️ CRLF TRUNCATION TRAP (Capyfi 2026-09): cutting addresses out of pipe output with
  `tail -c 41` after `jq -r`/curl keeps the `\r` inside those 41 bytes → the "address"
  ends up 39 hex chars → downstream `cast call` fails with "odd length" errors that
  LOOK like a broken RPC. Fix: extract with `jq -j` (no trailing newline) or
  `grep -oE '0x[a-fA-F0-9]{40}'`, never byte-count tail. Cost a whole debug cycle on
  what appeared to be an RPC problem before spotting the short address.
- NEVER GUESS selectors by hand — compute every one with `cast sig "borrowCaps(address)"`.
  Hand-copied/guessed sigs revert with "execution reverted" and get misread as
  "function doesn't exist". Verified Comptroller/cToken sigs (reusable):
  admin()=0xf851a440, comptroller()=0x5fe3b567, implementation()=0x5c60da1b,
  underlying()=0x6f307dc3, totalBorrows()=0x47bd3718, getCash()=0x3b1d21a2,
  markets(address)=0x8e8f294b, getUnderlyingPrice(address)=0xfc57d4df.
- ⚠️ totalBorrows > totalSupply (in underlying units) is NORMAL on aged Compound-fork
  markets — exchange rate > 1 after interest accrual, not an accounting bug. Capyfi
  caRPC/caLAC looked "flipped" until ER check confirmed it. Verify ER before flagging.
- Calling a zero-code contract: "does not have any code" error = liveness signal (see §1).
- "ABI decoding failed: buffer overrun" = wrong return type guess; retry with uint/int/address
  variants or fall back to raw call.

## 5. Unknown-interface oracle probing
1. Try standard sigs: `getUnderlyingPrice(address)`, `latestAnswer()`, `latestRoundData()`,
   `decimals()`, `description()`, `version()`, timelock sigs (`delay()`, `queuedTransactions`).
2. All reverting? Extract selectors from bytecode (PUSH4 = 0x63):
   `cast code $ORACLE | grep -oP '(?<=63)[a-fA-F0-9]{8}' | sort -u`
3. Probe each selector with and without args:
   `cast call $ORACLE "0x${sel}(address)" $ARG` then `"0x${sel}()"`.
4. Dump storage slots 0–20 (`cast storage`): tail-40-hex of slot0 = owner address; small
   mantissas (0.05e18, 0.20e18) = fee/reserve factors; embedded market addresses = registry refs.

### 5b. Dual-oracle freshness audit (high-yield pattern)
1. Probe `getUnderlyingPriceWithTimestamp(address)` → returns (price, updatedAt). Compute
   age = now − updatedAt and compare against per-asset staleness thresholds (read them from
   the verified oracle source assetConfigs, not guesses).
2. Manual-override signature: updatedAt ≈ block.timestamp (age ~0 or slightly NEGATIVE)
   + price exactly round (e.g. 1.000000) + feed address 0x0 → admin-set manual price,
   not a live feed. Check BOTH sub-oracles before concluding.
3. Common real finding: primary sub-oracle frozen for weeks/months while protocol silently
   runs on fallback (Benqi 2026-09: Edge oracle ALL 15 feeds frozen ~78 days, Chainlink
   serving every price). Impact = deviation cross-check inactive, single source of truth.
   Classify INFO/resiliency — fallback works by design, NEVER HIGH.
4. Related by-design behavior: when BOTH oracles go stale the price call reverts
   (`BothOraclesStale`) → full protocol freeze. Standard safety, usually excluded.

### 5c. Reward-distribution probing (Compound-fork with native rewards)
- Selectors: `supplyRewardSpeeds(uint8,address)`, `borrowRewardSpeeds(uint8,address)`,
  `rewardSupplyState(uint8,address)`, `rewardAccrued(uint8,address)`,
  `claimReward(uint8,address[],address[],bool,bool)`.
- Call reward-token `balanceOf(Comptroller)` — often 0 → reward paths dead even if code live.
  Native-token rewards: `eth_getBalance` on the Comptroller.
- claimReward accepting arbitrary `holders[]` is NOT theft (payout always goes TO the
  holder); at most reward-flushing griefing. Only report if payout destination is
  attacker-controlled.
- ABI-encoding trap: a `uint8` arg must be padded to a FULL 32-byte word. Sending `"00"`
  (1 byte) returns `execution reverted` / `0x` even though the selector and function are
  correct — this cost a debugging cycle on Benqi rewardSupplyState.

### 5d. Market-state sweep selectors (per market, batch in ONE script)
`markets(address)` (isListed, collateralFactor), `mintGuardianPaused(address)`,
`borrowGuardianPaused(address)`, `borrowCaps(address)`, plus qi-token
`totalBorrows/getCash/totalReserves/totalSupply/exchangeRateStored/decimals/
implementation()/interestRateModel()`.
A paused market (CF=0 + mint/borrow paused + borrowCap=1 wei) is frozen — stale manual
prices there are cosmetic, not exploitable. Verify the freeze before writing anything up.
qiBUSD example: listed, CF=0, both pauses true, cap=1 wei, manual $1.00 price on both
oracles, feed 0x0 → no user-reachable path; do not report.

### 5e. Explorer-source extraction quirks (Snowtrace pattern)
- `getsourcecode` returns `SourceCode` as DOUBLE-encoded JSON: `{{...}}` wrapper → strip
  one leading+trailing brace, then `json.loads` → `sources: {filename: {content: ...}}`.
  Several parse failures before this unwrapping pattern worked.
- Raw JSON-RPC over curl + placeholder explorer key (`apikey=YourApiKeyToken`) works on
  Snowtrace; web UI pages may render empty — always use the API module endpoints.
- Docs sites that are JS-rendered (docs.benqi.fi) return ~empty via curl; derive contract
  lists from on-chain probing + explorer source instead.
- Immunefi program pages: curl + web search both return blocked/empty → use the browser
  tool to load the program page and read the scope table from the rendered DOM (Benqi
  lesson, §8b). Never declare "no public scope" without trying the browser once.

## 6. Admin / multisig recognition
- ~170-byte bytecode + `getThreshold()` and `nonce()` answering = Gnosis Safe PROXY
  (delegatecall into singleton; real code lives in the singleton, not the proxy).
  Benqi admin: threshold=3, nonce=547.
- `owner()`/`admin()` can revert on proxies — always also probe Safe sigs
  (`getThreshold()`, `nonce()`, `getOwners()`).
- Guardians/timelocks: probe `owner()`, `delay()`, `queuedTransactions(bytes32)`.

### 6b. Legacy Safe + ERC-7201 role decode (when getOwners()/hasRole() REVERT)
- Legacy Safe proxies (pre-1.1.1, and Safe 1.4.1 proxies with legacy layouts) may revert on
  `getOwners()`/`owner()`. Decode via eth_getStorageAt instead: singleton=slot0, nonce=slot1,
  owners ARRAY=slot2 (length at slot2, element[i] at keccak(abi.encode(2))+i), threshold=slot4
  (deprecated slot), masterCopy check slot0. Read first ~10 array slots, filter the 32-byte
  words to 0x[0-9a-f]{40} patterns — some words are offset/length padding, not owners.
- OZ v5 AccessControl uses ERC-7201 namespaced storage:
  base = uint256(keccak256("openzeppelin.storage.AccessControl")) - 1, slot =
  keccak256(abi.encode(base)) & ~bytes32(uint256(0xff)). Inside: _roles[role].members mapping
  at offset 0. Read `keccak(abi.encode(account, keccak(abi.encode(role, slot))))` to check a
  grant directly. (Custom hashes may shift this — compare against the verified source layout.)
- ⚠️ hasRole() VIEW REVERT QUIRK (Capyfi wARS/LAC impls): hasRole(<PAUSER|MINTER|UPGRADER>,
  <any>) REVERTS in live bytecode while hasRole(<arbitrary role>, <any>) returns false.
  Verified source (OZ standard) would never revert — bytecode ≠ source. NEVER trust hasRole()
  on unverified impls; confirm roles via RoleGranted/RoleRevoked event history (Blockscan
  per-address filter) + storage reads + eth_call simulations from candidate holders.
- Governance-renunciation proof pattern: collect RoleGranted (deploy block) + RoleRevoked
  events per address, then storage-read the role mappings for the former holder (all zero),
  then simulate pause()/mint()/grantRole() from candidate EOAs (must revert). Three-way
  agreement = renunciation confirmed → "supply frozen, no admin path" INFO finding.
- Prove a pause role is LIVE: eth_call pause() from the candidate EOA. Success (returns 0x)
  = active pauser — that's evidence, not a guess. Mint reverting from the same EOA can mean
  the token simply has no mint path (fixed supply) — check source before calling it a role gap.

## 7. Recon-phase finding triage (anti-inflation)
- "Oracle has non-standard/undocumented interface" = INFO/LOW integration risk, NOT medium —
  no exploit chain. Interface obscurity alone is not a vuln.
- Single-Safe centralization = space default; only report with unusual trust assumptions
  (e.g., no timelock + instant pause, or EOA admin).
- SINGLE-EOA PAUSER on a lending-market token is reportable (MEDIUM): 1 key freezes all
  transfers → repayments/liquidations halt → market availability risk. Multisig-owned pause
  = standard; renounced governance = INFO-positive. Match severity to who holds the key,
  not to what the key could hypothetically do.
- References to dead comptrollers = LOW at best; confirm real integrators use the dead address.

## 8. Session case files — Benqi (Immunefi, Avalanche C-Chain)

### 8a. Cast-based triage (earlier session)
qiAVAX sole live market: TVL 631,634 AVAX, utilization 39.5%, available liq 572,400 AVAX,
reserve factor 20%, ER verified correct under 1e18 scaling. Oracle 0xf81B... (8KB, no standard
sigs, storage held qiAVAX ref + 0.05/0.20 mantissas). Admin Safe 0xb952... threshold 3.
All findings stayed INFO/LOW — correct outcome per quality gate; no inflation.

### 8b. Full 15-market sweep via raw eth_call (2026-09-10 session)
- Live addresses: Unitroller 0x486A...D9b4 (proxy) → Comptroller impl 0xd8e4...7dbd
  (Solidity 0.5.17 Compound fork); DualOracle 0xf81b...f15e (0.8.24, Ownable2Step) with
  Edge sub-oracle 0xb732...324b + Chainlink sub-oracle 0x30fb...4f12; admin Safe
  0xb952...db3d (GnosisSafeL2); pause guardian 0x10f3...82e6.
- 15 markets: qiAVAX/qiBTC/qiETH/qiUSDT/qiLINK/qiDAI/qiUSDC/qiQI/qiUSDCn/qiUSDTn/
  qisAVAX/qiBTC.b/qiBUSD/qiAUSD/qiEURC. CFs 0.20–0.85; BUSD & EURC CF=0.
- KEY FINDINGS (all correctly capped at INFO): Edge oracle fully stale ~78d across ALL
  feeds (Chainlink fallback serving); qiBUSD manual $1.00 price both oracles + fully
  paused market; reward speeds 0 & QI balance 0 (reward paths dead); claimReward
  arbitrary-holders = not theft. Zero HIGH/CRITE — right outcome, no inflation.
- CloseFactor 0.5, liqIncentive ~1.09, deviation thresholds 2–20% per asset.
- Next-phase targets (unexplored): InterestRateModel params, QiToken delegate
  (0.5.17 timestamp/rounding/seize-path), admin Safe tx history, official Immunefi scope
  page via browser (curl + search both blocked/empty).
- Progress NOT persisted that session (tool budget exhausted) — final summary message
  was the only record. Lesson: write progress.md EARLY, not at session end.

### 8c. IRM + delegate + oracle-mode follow-up (2026-09-10 session, D:\data hermes\bug-bounty\_progress\benqi)
- Persisted progress.md FIRST per 8b lesson — worked; progress survived tool-budget limits.
- 9 unique IRMs, all immutable JumpRateModels, math clean (slope AVAX 7.46%, jump 300%).
  qiQI kink=0 → flat 10% by design. qiAVAX slope 0 below kink (flat by design).
- Delegate 0x76145e99 (solc 0.5.17) clean: timestamp accrual capped by borrowRateMaxMantissa,
  mint uses actualMintAmount (fee-on-transfer safe), seize burns protocolSeizeShare,
  sweepToken guarded vs underlying.
- DualOracle enum OracleMode {EDGE_ONLY=0, CL_ONLY=1, DUAL=2}; live mode = CL_ONLY → the
  DUAL-mode deviation logic (deviationThreshold 5e16 / max 20e16, manual override skips
  validateFeedPriceDeviation) is DEAD CODE while CL_ONLY. Frozen Edge feeds (8b) therefore
  moot by MODE, not just by fallback. Always read the live mode enum before writing up
  dual-oracle deviation findings.
- Live price ground truth via getUnderlyingPrice on all 3 oracles: Dual == Chainlink
  EXACTLY for all 15 markets; Edge deviates (qiBTC.b ~20%, qiLINK ~35%) — consistent with
  CL_ONLY and explains why admin switched modes.
- Double decimal adjustment in getPriceAndTimestamp (underlying-dec delta × feed-dec delta)
  = Benqi convention, consistent on manual and feed paths — not corruption.
- Reward flywheel double-grant suspicion on claimReward: grantRewardInternal SELF-RESETS
  rewardAccrued=0 on success → pays incrementally, safe. Classic false alarm.

## 9. QiErc20Delegate code-review checklist (Compound-fork delegates, solc 0.5.x)
- accrualInterest: timestamp-based (not block-based) + borrowRateMaxMantissa cap present?
- mint/repay: actualMintAmount/actualRepayAmount (fee-on-transfer tokens) or raw amount?
- seize: protocolSeizeShare burned (not transferred)? liquidator/pair reentrancy guard?
- sweepToken/_sweep: guarded against sweeping the underlying token?
- transferIn/Out: real ERC20 transferFrom (not msg.value tricks on ERC20 markets)?

## 10. Verified-source review workflow (explorer getsourcecode, keyless)
- `curl "https://api.snowtrace.io/api?module=contract&action=getsourcecode&address=0x.."` (placeholder
  apikey works; same schema on every Etherscan-family explorer — snowtrace/bscscan/polygonscan/basescan).
- SourceCode shape branches: starts with `{{` → multi-file standard JSON (strip outer brace,
  json.loads → `sources[path].content`, flatten with `// ===== FILE: path =====` headers);
  otherwise it is a PLAIN single-file string. Handle BOTH in one fetch helper — most Benqi core
  contracts (QiAvax, veQI, GaugeController, MRD, Ignite) came back in each format.
- The `Implementation` field in the same response resolves proxies directly — no storage-slot probe
  needed for the impl address once the contract is verified.
- Flatten → save `sources/<name>.sol` + raw `.json` under the target progress dir; grep offline after.
- ⚠️ INTERFACE FALSE-HITS: in a flattened multi-file blob the FIRST `find("function deposit(")` is
  usually the interface declaration (IVeQi/IERC20 stubs), not the audited code. Use
  `[m.start() for m in re.finditer(re.escape(fn), src)][-1]` or anchor on the `===== FILE =====`
  section of the implementation. Cost several re-print cycles on Benqi veQI/Gauge before switching
  to last-hit.
- `function foo(` matches from OZ AccessControl doc comments — comment artifacts, not real functions;
  don't chase them.

### 10b. Deployed-vs-repo verification via Blockscout (Capyfi/Taiko pattern)
Etherscan-family getsourcecode not available (Blockscout UI). Workflow that worked:
1. Fetch flattened on-chain source per contract from Blockscout
   (`/api?module=contract&action=getsourcecode&address=...` works on Blockscout too when
   enabled; otherwise scrape the verified-source page).
2. Diff against GitHub repo: in the flattened blob, anchor extraction at the
   `^contract <Name>` line downward (everything above = imports/spdx/pragma noise). Use
   `difflib` — report DIVERGENT LINES count, not vibes.
3. Outcome "100% identical (0 diff lines)" is a HIGH-VALUE statement: it means auditing the
   repo == auditing deployed bytecode, and any fork-signature checklist (§11) applies to live
   state. Log it as the first INFO finding.
4. Same-file-multiple-impls pattern: identical CErc20Delegate bytecode at several impl
   addresses is NORMAL (per-market deployment of one source) — verify by bytecode hash, not
   address.
5. Cross-check delegate type: CErc20Delegator (ERC20 markets) vs direct CEther (native market)
   — native markets are NOT delegators; probe `admin()`/`comptroller()` directly.

## 11. Auditing forked DeFi components — 'clean signature' checklists (Benqi 2026-09 full sweep → 0 findings)
When the target is a known fork (Compound/Venus/Curve-vecrd), audit by EXPECTED-PATTERN MATCH:
conform = clean (log it), deviation = candidate finding. Persist per-component verdicts so the next
session never re-audits.
- **Venus/Tender-style MultiRewardDistributor**: calculateNewIndex clamps deltaTimestamps at endTime
  (accrue the remainder window ONCE, then short-circuit to 0 — check `>` not `>=`); user-index
  bootstrap via initialIndexConstant; sendReward is balance-guarded — insolvent distributor accrues
  locally + emits InsufficientTokensToEmit instead of reverting (no griefing-DoS, rewards deferred
  not lost); _rescueFunds only to comptroller.admin(). All present = clean flywheel.
- **LST w/ cooldown + historical rates (sAVAX pattern)**: redeem uses the rate SNAPSHOT AT CLAIMABLE
  TIME (binary search over historical timestamp array + cooldownPeriod), not current rate →
  post-request rate-gaming structurally impossible; rate<1 blocked by `avaxAmount >= shareAmount`;
  redeemOverdueShares = share-for-share (no AVAX); expiry pruning only inside accrueRewards →
  keeper-idle lockout is admin-grief INFO, never user-reachable.
- **veToken + Gauge vote bookkeeping**: bips cap (≤10000) computed pre-write; first-vote-per-node
  registers into nodeUsers with index maps; over-unvote blocked by uint underflow revert even though
  `require(x >= 0)` is a tautology (checked-math revert is the real guard — don't report the useless
  require); every swap-pop removal asserts `users[index] == user` first (stale index → revert, self-
  swap when index==last is benign); resetVotesFor only-callable-by-veToken + try/catch in withdraw.
- **Validator marketplace (Ignite pattern)**: `require(msg.value == fee)` exact (no overpay-lock);
  ERC20 fee via dual Chainlink (AVAX+token) with maxPriceAges staleness + decimals normalize;
  releaseLockedTokens role-gated with CEI (delete registration before external call), failed=true
  refund path symmetric with subsidisation cap decrement; redeem gated to original registerer +
  withdrawable flag.
- **veToken linear accrual (vecrd fork)**: deposit runs _claim at OLD amount BEFORE adding new stake
  (no double-count at new rate); withdraw burns ALL ve-balance + resets votes = documented loss, not
  a bug; pending capped by balanceOf < amount×maxCap.
- Benqi close-out: qiAVAX delegate, StakedAvax, veQI, GaugeController, MRD, Ignite all matched clean
  signatures → sweep CLOSED, zero findings, no PDF. Zero-finding IS the right outcome; record the
  VERDICT section in progress.md + list every dead-end so nobody re-runs the same 6 components.

### 8d. Capyfi (Taiko mainnet, Blockscout) — 2026-09-11 session
- Full topological recon done, progress persisted FIRST
  (`D:\data hermes\bug-bounty\_progress\capyfi\recon_topologi.md`) — 8b lesson applied.
- Deployed == repo 100% (0 diff) via §10b workflow: Comptroller impl 0x00dc…867e, CErc20Delegate
  bytecode 0xea6c…80966 (identical across 6 impl addrs), CEther direct, ChainlinkPriceOracle,
  JumpRateModelV2, Whitelist UUPS — all match GitHub repo.
- Admin Safe 1.4.1 0x6c15…ed24 (4/7). Whitelist gate is MINT-ONLY (CToken.sol L386
  `mintInternal` / modifier L1186): borrow/redeem/transfer/liquidate stay permissionless even on
  whitelisted markets (caRPC, caLAC) — a non-member can still receive cTokens via transfer and
  borrow. Likely by-design; do not inflate.
- Feed topology: 3× CapyfiAggregatorV3 (manual on-chain price, owner-toggleable bounds) + 4
  official Chainlink feeds. Notable: WARS feed owned by a SECOND Safe 0x21f73d…73ca (4/9)
  independent from the main admin Safe → cross-multisig trust gap (LOW/INFO). RPC feed stale
  7.08 days AND oracle's getUnderlyingPrice has NO staleness check (only `answer<=0 → 0`) —
  real pattern but dust TVL ($0.01/coin) → LOW/INFO max.
- WARS market CF=0 (borrow-only) → cannot be collateral; token-level risks: LAC owner = EOA,
  RPC proxy admin ≠ admin Safe (third-party-token-in-collateral-market INFO).
- Outcome: all INFO/LOW, no exploit chain — correct anti-inflation result. Novel lesson in §4
  (CRLF tail trap + cast sig rule + borrows>supply-is-normal) came from this session.

### 8e. Capyfi exotic/regional token audit (Ethereum mainnet, 2026-09-12)
Scope: 3 exotic tokens as lending markets — RPC (RipioCoinV2, TransparentProxy), wARS
(LatamStable, UUPS), LAC (LaCoin, UUPS). All OZ v5. Findings file:
`_progress\capyfi\exotic_tokens_findings.md`.
- wARS: ALL 4 roles renounced by EOA 0x5ca3f8ee (RoleRevoked x4 blk 24,995,207) → supply
  frozen, no admin path (INFO, positive). Verified via §6b 3-way pattern.
- RPC: PAUSER = single EOA 0x5f4f43ba, still ACTIVE (pause() simulation succeeds; role
  persisted through V1→V2 upgrade) → 1-key transfer freeze on a deposit-heavy market
  (4.09B cash) = MEDIUM. ProxyAdmin owner = legacy Safe 3-of-7 (0xf0b223f5). No minter.
- LAC: no mint/burn (fixed 10B at init). Owner = legacy Safe 4-of-7 (0x80c91e03), owners
  overlap RPC Safe → holds pause + UUPS upgrade = standard centralization MEDIUM.
- hasRole() revert quirk on both impls (§6b) — INFO integrity note, monitoring must use
  events/storage not hasRole().
- Triage applied (§7): Safe multisig ownership alone → standard MEDIUM at most; renounced
  governance → INFO; NO severity inflation on any frozen/dead path.
- Next-phase candidates: Comptroller admin path, timelock check on main admin Safe,
  caWARS borrow-heavy market (491M borrowed vs 260M cash) liquidation mechanics.

### 8f. Capyfi core-fork diff sweep (Ethereum mainnet, 2026-09-12) — SCOPE GATE LESSON
Full recipe: `references/fork-diff-audit.md` (Blockscout v2 API fetch + CRLF-normalized diff + pitfalls).
- Immunefi scope checked AFTER the deep contract pass — too late. In-scope = caUSDT/caRPC/
  caWBTC/Unitroller/caWARS/Comptroller/caUSDC/caLAC/caETH + app.capyfi.com ONLY. Oracle, IRM,
  Whitelist, 6 newer markets = OUT OF SCOPE → two real candidate findings (oracle staleness,
  getCompAddress=0 latent brick) DIED at scope. RULE: extract the bounty target list FIRST,
  before auditing anything custom.
- Diff results (vs upstream compound-protocol master, `diff <(tr -d '\r')` both sides):
  Unitroller/CErc20/JumpRateModelV2 verbatim; Comptroller = upstream V7 (0.8.10 + proposal65)
  verbatim EXCEPT getCompAddress() → address(0) (flywheel dead code, inert: compSpeeds all 0);
  CToken = upstream + whitelist mint-gate only; delegator + whitelist passthrough only.
  60KB Comptroller → 1-line diff in minutes. Verbatim = clean, log and move on.
- RewardsDistributor 0xd09931d9A7A320B5D0d407D47f28A269c08Ce04D (chain 480/8453) = standard
  Merkle claim, out-of-scope anyway.
- Web static recon: Next.js/Vercel/Cloudflare, no leaked keys; web3auth clientId + embedded
  infura-service proxy token = PUBLIC-BY-DESIGN, never report. 38 JS chunks saved
  `_progress/capyfi/js/`. Remaining paths: OZ audit report diff, subdomain takeover enum,
  interactive web test (Web Critical $8k flat).
- Latent admin-triggered DoS (compSpeeds>0 + Comp(0).balanceOf decode revert → permanent
  brick, reset path also reverts) = trusted-admin action → Info at best, NOT submitted.
- Immunefi SPA extraction: rendered-text parse empty; targets/impacts live in unicode-escaped
  JSON inside raw HTML script blob (`s.encode().decode('unicode_escape')` then regex).
- Program: Critical max $1M min $50k, High $10-50k, PoC + KYC, Primacy of Impact.

