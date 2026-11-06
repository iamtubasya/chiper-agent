# DeXe Protocol (Immunefi) — GovPool engagement notes, 2026-10

Condensed state so a later session does not re-derive it. Full detail + raw artifacts live in
`D:\data hermes\bug-bounty\dexeprotocol\` (`REPORT.md`, `TOOL-COVERAGE-LEDGER.md`, `poc/`, `submission/`).

## Target shape

- Program: `https://immunefi.com/bug-bounty/dexeprotocol/` — SMART CONTRACT, max **$500k**, PoC + KYC
  required, **Primacy of Impact** for Critical/High/Medium. Mirror program exists on HackenProof
  (same cap).
- **All 10 listed assets are on BNB Smart Chain (chainId 56)**, not Ethereum — the scope table embeds
  name→address pairs as inline escaped JSON in the page HTML, so `curl` + regex recovers them without
  rendering JS.
- Assets: DeXe DAO `0xB562127efDC97B417B3116efF2C23A29857C0F0B` (GovPool beacon proxy) plus
  ContractsRegistry / UserRegistry / CoreProperties / PriceFeed / ERC721Expert / PoolFactory /
  PoolRegistry / SphereXEngine / PoolSphereXEngine.
- Out of scope includes basic economic/governance attacks, centralization, privileged-address access —
  which removes the "quorum uses live totalSupply" class from play.

## Source integrity (done, do not redo)

Sourcify (chain 56, no API key, `?fields=sources`, **lower-case address or it 400s**) returned sources
byte-identical to repo HEAD `f09a3ba` for all 8 implementations probed, and later for GovSettings
(via `PoolRegistry.getProxyBeacon("SETTINGS")` → beacon → `implementation()`). **Deployed == source**,
so repo-derived findings are live.

## The one proven finding (C1)

`GovPool.moveProposalToValidators()` (L212-216) and `execute()` (L155-159) both call
`_updateRewards(proposalId, msg.sender, RewardType.Execute)`, and
`GovPoolRewards.updateStaticRewards` (L29-46) is **additive** (`staticRewards[pid] += amount`;
`core.givenRewards += amount`). A validator-routed proposal therefore credits the execution reward
twice; one account taking both roles is credited exactly `2 × executionReward`. `givenRewards` also
feeds `GovPoolExecute._getCommission()`, so the DeXe commission is inflated.

- PoC: `poc/C1_repro.test.js` (+ `poc/make_c1_poc.py`) — 2 tests, both passing, injected inside the
  repo suite's `Fullfat GovPool` describe. Run:
  `cd repo && cp ../poc/make_c1_poc.py . && python3 make_c1_poc.py && npx hardhat test test/gov/C1_repro.test.js --grep "C1 "`
- Live config of the **flagship pool** (raw `eth_call` decode of `settings[1]`, corroborated against
  `deploy/config/configs/prod*.conf.js`): `validatorsVote = false`, `rewardToken = 0x0`,
  `creationReward = 0`, `executionReward = 0` — **rewards are disabled, so C1 moves no value there.**
  It also means the `moveProposalToValidators` branch is not even exercised by pool-executor proposals.
- Live reachability sweep (`sweep_pools2.py`, raw JSON-RPC): **228** pools, **21** with
  `validatorsVote = true` + `executionReward > 0`, 66 with rewards but unreachable. Largest reachable
  budgets 8.0e25–8.5e27; one pool denominates in **BUSD** (balance ≈ 10, smaller than its
  `executionReward`, so `sendFunds` caps it either way).
- Verdict recorded: **Medium candidate, submit only with the two caveats stated up front** (listed
  assets unaffected; affected instances are third-party DAOs and the tokens are theirs).
  Draft staged at `submission/C1-SUBMISSION-DRAFT.md`; PDF + Gmail draft generated.

## Tooling outcomes (what actually worked)

| tool | outcome | note |
|---|---|---|
| `forge build` | works | needs `solc` from the GitHub release into `~/.svm/0.8.20/` + `--use`; drop `node_modules` from `libs` or it looks hung |
| Hardhat `compile` / `test` | works after compiler-cache seed | HH502 → seed `compilers-v2/0.8.20/solc.exe` + hand-written `list.json`; first build ~10 min, 501 artifacts |
| `slither` | partial | 11 files analysed; **crashes (AssertionError) on GovPool, GovUserKeeper, PoolFactory, DistributionProposal** — both patch attempts fail, do not retry |
| `aderyn`, `mythril` | NOT RUN | WSL VM `CreateVm/ERROR_TIMEOUT` on this host |
| `cast` | works, with two traps | (a) mis-decodes structs ending in a dynamic member → use raw `eth_call` + manual words; (b) `cast rpc` output mangled by shell escapes → write JSON to a file with `curl` |
| Hardhat test harness | works | reuse a vendor suite by injecting a describe block into a **copy** of its test file |

## Verified negatives (closed — do not re-open)

`setDependencies` hijack (GovPool/PoolRegistry are `dependant`, GovUserKeeper `onlyOwner`);
`tryExecute` always reverts (simulation helper); `exec()` prepends `msg.sender` so payer spoofing is
impossible; withdraw vs `maxTokensLocked`; delegate→vote→undelegate double-spend;
GovValidators `executeAfter += block.timestamp` cannot accumulate (state becomes `Locked`, and `vote`
requires `Voting`); GovPoolCredit monthly-limit prefix-sum indexing; TokenSale double-claim / recover;
SphereX↔OZ proxy storage collision (dedicated `keccak("eip1967.spherex.*")-1` slots);
TokenAllocator merkle replay; PoolFactory CREATE2 salt; ERC721Expert transfer/burn;
ERC721Multiplier (multiplier is governance-set). `AbstractValueDistributor`'s unchanged-cumulative-sum
branch was re-walked end-to-end and is a **dead end** (`Σ protocol-accrued + Σ user-share` cannot
exceed `totalRewardsAmount`).

Note: the in-scope `SphereXEngine` / `PoolSphereXEngine` are **inert** — `_engineRules == 0` on both
(slot 3), so the engine returns immediately and provides no protection.
