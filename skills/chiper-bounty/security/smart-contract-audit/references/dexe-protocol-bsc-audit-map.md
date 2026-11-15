# DeXe Protocol — architecture map, traps, and prior-engagement state

Condensed from the 2026-10 Immunefi engagement (`D:\data hermes\bug-bounty\dexeprotocol\`). Reuse
this instead of re-reading 6k lines of Solidity. Repo: `github.com/dexe-network/DeXe-Protocol`
(Hardhat, ~190 compilable contracts under `contracts/`).

## 1. The bounty lives on BSC, not Ethereum

Program: `immunefi.com/bug-bounty/dexeprotocol`. Max $500k (Critical = 10% of funds affected,
min $10k). KYC + PoC required. Primacy of Impact for SC Critical/High/Medium.

**All 10 in-scope assets are BNB Smart Chain (chainId 56) — while the repo, audit PDFs and docs
are Ethereum-shaped.** Always read the explorer host out of the scope JSON (see SKILL.md).

| Asset (scope `description`) | Proxy (BSC) | Implementation |
|---|---|---|
| DeXe DAO | `0xB562127efDC97B417B3116efF2C23A29857C0F0B` | `0xB1578bF6A66b1Ec9Ae731643b9F8B6AC34351068` (beacon `0x83e2…95c8`) |
| ContractsRegistry | `0x46B46629B674b4C0b48B111DEeB0eAfd9F84A1c0` | `0x073ebc0036ade52544b62cdc441ea6ee1796d12c` |
| UserRegistry | `0x427a1214f12117b1AD48C817c203c5CF3Eb7E7C4` | `0x4fa40ed48c5671500dfec9f307e7ad0617fc3196` |
| CoreProperties | `0xaB9d2a2347D5fF5B760C0226C52d5C673b8D9e44` | `0xabd06d48d29240a6845d93072721e9af797e7f0c` |
| PriceFeed | `0xc7730074736c10ed0d3F928A10Ee4162DA9a7983` | `0xe94ba562fba30dce5daa24917e56deacd003b918` |
| ERC721Expert | `0x892B3292cF80CB298b7fA20D04EF4732640db404` | `0xd20db29bbd3f954a28d0edfcb9ff052915be8ad4` |
| PoolFactory | `0x85f86ef7E72e86BdEAb5F65e2B76A2c551f22109` | `0x0e03189fbe04da89736a87eacdda1d770758bb89` |
| PoolRegistry | `0xFEB26AAB75638440B3CEFe8B10de6118972f9C6B` | `0x850badf759a3cb03090a70752e0b4a98c04002f6` |
| SphereXEngine | `0x41260f637a993ce714Ece1ee9875F489e483e9b3` | self (standalone) |
| PoolSphereXEngine | `0x4fa2092E32934D3D3823E58C79ceD0e410a5B0D4b` | self (standalone) |

**Deployed == repo HEAD** (verified: 8/8 implementations byte-identical via Sourcify diff — see
`scripts/sourcify_repo_diff.py`). So the repo is safe to audit directly; no selector diff needed.
Caveat: re-verify at the start of any new engagement, the vendor upgrades proxies in place.

## 2. Architecture (who owns whom)

`PoolFactory.deployGovPool()` CREATE2-deploys, per pool, a `ProtectedPublicBeaconProxy` over the
`PoolRegistry` beacon for each of: **GovPool**, GovSettings, GovUserKeeper, GovValidators,
ERC721Expert, ERC721Multiplier, LinearPower or PolynomialPower, DistributionProposal,
TokenSaleProposal. Then it `transferOwnership(poolProxy)` on all of them, so **each sub-contract's
owner is its GovPool** — i.e. those `onlyOwner` functions are reachable by a passed proposal.

- `ContractsRegistry` (global) wires: userRegistry, poolFactory, poolRegistry, DEXE/WETH/USD/BABT,
  dexeExpertNft, priceFeed, tokenAllocator, treasury, coreProperties, networkProperties, SphereX.
- `PoolRegistry` holds the **beacons** per pool-type + the `onlyPoolFactory` register hook.
- Live DeXe DAO state: `name()` = "DeXe Protocol", `onlyBABTHolders()` = false, latestProposalId 28,
  userKeeper.tokenAddress = `0x6E88056E8376Ae7709496Ba64d37fa2f8015ce3e` (its own gov token),
  `nftAddress()` = 0, `getTotalPower()` = 2.2095e25, validatorsCount = 2, `getCreditInfo()` = `[]`.
  Funds: 1.28M gov-DEXE in the pool + 5.82M gov-DEXE in the userKeeper + ~8 USDT. **Funds at risk
  are the gov token, not blue-chips** — factor that into severity expectations.

## 3. Traps that cost real time

- **`exec()` prepends `msg.sender`.** `GovPool` calls `_govUserKeeper.withdrawTokens.exec(receiver, amount)`
  — that is `withdrawTokens(msg.sender, receiver, amount)` via `GovUserKeeperLocal.exec`
  (`contracts/libs/gov/gov-user-keeper/GovUserKeeperLocal.sol`), NOT a spoofable `payer`. Same for
  `depositNfts`/`delegateTokens`/`delegateNfts`/`undelegate*`. Read that helper before flagging a
  payer/receiver mix-up.
- **`maxTokensLocked` is a single MAX, not a sum.** You may vote your full balance in many
  concurrent proposals; withdraw allowance is `max(balance, maxLocked) − maxLocked`. The
  recompute in `updateMaxTokenLockedAmount` early-returns when `newLockedAmount == lockedAmount`,
  which is safe only given the invariant `lockedInProposals[x] ≤ maxTokensLocked` (lockTokens
  maintains it). Any future change to that invariant makes the early return a bug.
- **`GovPool.execute`/`tryExecute`/`multicall`/`onlyThis` surface.** `tryExecute` looks like an
  unauthenticated "call anything as the pool" gadget — it is safe: every path ends in
  `_throwRevert(bool)` and the outer `try/catch` catches it, so the delegatecall's state is
  unwound. It is the front-end simulation helper.
- **`dependant` = injector-once.** `setDependencies` with the solarity modifier sets
  `_INJECTOR_SLOT` to the first caller (PoolFactory/ContractsRegistry) and reverts later callers.
  `GovUserKeeper.setDependencies` is `external onlyOwner` instead. Neither is hijackable.
- **`GovPool._onlyBABTHolder` also passes for any registered GovPool** (`isGovPool(msg.sender)`) —
  that is the cross-pool / meta-governance path, not a missing check.
- **Two reward grants per validator-routed proposal.** `moveProposalToValidators` and `execute`
  both call `_updateRewards(..., RewardType.Execute)`, and `updateStaticRewards` is additive.
  Long-standing (since `4d10826`) → likely known/intended; do not lead a report with it.
- **SphereX is inert in production**: `_engineRules` (slot 3 of SphereXEngine) = 0 on both
  deployed engines → all validate hooks return immediately. The in-scope SphereX assets are
  effectively dormant; the default admin (slot 2) is the DeXe DAO pool.
- **Re(verified) negatives** — do not re-derive: setDependencies hijack (GovPool / GovUserKeeper /
  PoolRegistry), `exec` payer spoofing, withdraw-vs-maxTokensLocked, delegate→vote→undelegate
  double-spend, `GovValidators.executeAfter += block.timestamp` overflow-to-permanent-Lock (blocked
  because post-quorum state is `Locked`, failing `require(state == Voting)`), GovPoolCredit monthly
  limit prefix-sum, TokenSale double-claim / recover, SphereX↔OZ proxy storage collision,
  TokenAllocator merkle replay, PoolFactory salt reuse, ERC721Expert transfer/burn abuse.

## 4. Where the remaining value is (handoff notes)

1. Build the Foundry/invariant harness for `GovPoolRewards` + `GovPoolMicropool` and fuzz
   `Σ claims ≤ givenRewards`. `GovPoolMicropool._getExpectedRewards` (the
   `delegationTimes.lowerBound(quorumReachedTime)` index) is the one fund-distribution path with
   no upstream analogue and no audit coverage.
2. `AbstractValueDistributor` (StakingProposal, added in the final commit `f09a3ba` — post-audit):
   the `_cumulativeSum == newCumulativeSum` branch credits `_owedToProtocol` not only when
   `totalShares == 0` but also when `(value * PRECISION) / totalShares` truncates to 0.
3. slither cannot analyse `GovPool.sol`, `GovUserKeeper.sol`, `PoolFactory.sol`,
   `DistributionProposal.sol` (see SKILL.md crash signature) — those four are manual-review only.
4. Governance/economics/centralization-rooted findings are **out of scope** by the program's own
   filter; a "governance manipulation" report must be rooted in a *code defect*, not in 51%.
