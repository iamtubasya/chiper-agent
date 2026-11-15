# DeXe Protocol — engagement notes (Immunefi, BSC)

Session 2026-10. Kept because the work is unfinished (C2 open, C1 submission undecided) and the recon
below cost hours to establish. Full report: `D:\data hermes\bug-bounty\dexeprotocol\REPORT.md`.
Do **not** re-derive these.

## Scope shape (non-obvious)
- All 10 listed assets are **BNB Smart Chain (chainId 56)**, not Ethereum — the program page shows
  `bscscan` links only. Rewards are denominated in USD, paid in `$DeXe` (critical = 6-month vest).
- Immunefi scope lives in an inline escaped-JSON blob in the page HTML (`\"assets\":[{…}]`); a plain
  `curl` + regex recovers exact `name → address` pairs without rendering JS.
- Out of scope (filters that kill whole finding classes): basic economic/governance attacks (51%),
  centralization, privileged-address access, third-party oracles, test/mock files.

## Target map
| asset | proxy | impl |
|---|---|---|
| DeXe DAO (GovPool) | `0xB562127efDC97B417B3116efF2C23A29857C0F0B` (beacon `0x83e2…95c8`) | `0xB1578bF6A66b1Ec9Ae731643b9F8B6AC34351068` |
| ContractsRegistry | `0x46B46629B674b4C0b48B111DEeB0eAfd9F84A1c0` | `0x073ebc0036ade52544b62cdc441ea6ee1796d12c` |
| PoolRegistry | `0xFEB26AAB75638440B3CEFe8B10de6118972f9C6B` | `0x850badf759a3cb03090a70752e0b4a98c04002f6` |
| PoolFactory | `0x85f86ef7E72e86BdEAb5F65e2B76A2c551f22109` | `0x0e03189fbe04da89736a87eacdda1d770758bb89` |

DeXe DAO helper contracts: settings `0x57CbF649aC9b87FF8d0c710842bc26b5d05be566`,
userKeeper `0xbE8cB128fBCf13f7F7A362c3820f376b0971B7B2`, validators `0x6e290f6ae029006ABD5CEe8dAb7C4a552803E115`,
votePower `0x23BBBd553d310E8334e090cb5904E415734c4A18`.

## Verified facts
- **Deployed == repo.** 8 in-scope impls + the per-pool `GovSettings` impl (`0xaD8c754B5a2115D7d159307032c8514Df48aaA0b`,
  beacon `0x39648c953ad90f076b4746fFeB9181F565DAAFde`) are byte-identical to GitHub `dexe-network/DeXe-Protocol`
  HEAD `f09a3ba` after comment/whitespace normalisation. Source-derived findings are therefore live.
- Repo tree is the **Dec-2024** build; the five published audits (CertiK/Hacken/Ambisafe/Cyfrin) predate it,
  so post-audit surface = StakingProposal + AbstractValueDistributor (last commit), TokenAllocator + Clone,
  ERC20Gov variants, validators `monthlyWithdraw`/credit.
- `Globals.PRECISION = 1e25` (not 1e18). So `quorum = 5e25` means "5%", and `PERCENTAGE_100 = 1e27`.
  Do not read these as broken values.
- Flagship pool config (`settings[1]`, mapped to the pool itself): `validatorsVote = false`,
  **`rewardToken = address(0)`, `creationReward = 0`, `executionReward = 0`** → proposal rewards are OFF.
  Also `getCreditInfo() = []`, `validatorsCount = 2`, `onlyBABTHolders = false`, `latestProposalId = 28`.
  Holds 1,282,179.76 gov-DEXE + 7.99 USDT; userKeeper holds 5.82M gov-DEXE.
- **228 GovPools** on BSC; **21 have `validatorsVote = true` AND `executionReward > 0`** (finding reachable),
  66 have rewards but `validatorsVote = false`. See `templates/pool-fleet-config-sweep.py`.

## C1 (proven, Medium candidate) — duplicate Execute reward
`GovPool.moveProposalToValidators()` (L212-216) **and** `GovPool.execute()` (L155-159) both call
`_updateRewards(proposalId, msg.sender, RewardType.Execute)`, and `GovPoolRewards.updateStaticRewards`
(L29-46) is **additive** (`staticRewards[pid] += amount; core.givenRewards += amount`). One validator-routed
proposal therefore credits the execution reward twice; one account doing both roles accumulates
`2 × executionReward`. Also inflates `givenRewards`, hence the DeXe commission via `GovPoolExecute._getCommission()`.
Prior art: `git log -S` puts the call in the tree since `4d10826`/`f8a6a4d` (pre-audit) — flag that honestly.
PoC: `poc/C1_repro.test.js` (`npx hardhat test test/gov/C1_repro.test.js --grep "C1 "` → 2 passing).

## Still open
- **C2**: `AbstractValueDistributor._updateOnTime/_updateFromProtocol` (L37/L55) — the strict-equality branch
  credits `_getValueToDistribute` to `_owedToProtocol` not only when `totalShares == 0` but also when
  `(value * PRECISION) / totalShares` truncates to 0, re-attributing staker rewards to the protocol.
  Unproven; this is the least-audited fund-distribution code (StakingProposal path).
- `GovPoolMicropool._getExpectedRewards` / `GovPoolRewards._splitVotingRewards` — the other fund-distribution
  code with no upstream analogue. Manual review found no break; a fuzz campaign is the next step.
- Not run: aderyn, mythril (WSL VM `CreateVm/ERROR_TIMEOUT`); slither on GovPool/GovUserKeeper/PoolFactory/DistributionProposal.
