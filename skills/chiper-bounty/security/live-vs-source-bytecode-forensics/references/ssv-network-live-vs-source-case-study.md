# Case study — SSV Network (Immunefi), 2026-10

Worked example of the whole procedure, including the two wrong turns, so a future run skips them.
Target: `https://immunefi.com/bug-bounty/ssvnetwork/information/` — modular "dispatcher + modules" design.

## Scope facts worth knowing before starting

- Critical max $250k (10% of funds, floor $50k), High $30k, Medium $10k, Low $1.5k; paid in SSV; **KYC**;
  functional **PoC required**; aggregate pool capped at 150,000 SSV.
- Assets: `SSV Network` proxy `0xDD9BC35aE942eF0cFa76930954a156B3fF30a4E1`, `SSV Network View` proxy
  `0xafE830B6Ee262ba11cce5F32fDCd760FFE6a66e4`, plus a **Primacy of Impact** placeholder ⇒ the 7 module
  contracts and the cSSV token are in scope for Critical/High/Medium/Low.
- Exclusions: every Quantstamp finding (SSV-1..SSV-21), 7 program known-issues (T39, T3a..T3f), anything
  documented on docs.ssv.network **or in any branch of the repo**. Repeatable attacks: only the first vector pays.

## Architecture discovery (the part that must not be skipped)

`0xDD9BC…` is a bare ERC-1967 proxy → impl `0xa72a8f31…`. The impl is a **dispatcher**: it `_delegate`s to
module contracts held in a storage mapping. Resolve them from the storage layout, not from docs:

```bash
BASE=$(python3 -c "print(hex(int('$(cast keccak 'ssv.network.storage.main')',16)-1))")   # struct base
# ssvContracts is field index 3 of StorageData -> slot = BASE + 3
for k in 0 1 2 3 4 5 6; do
  idx=$(cast index uint256 $k $(python3 -c "print(hex(int('$BASE',16)+3))"))
  echo "$k -> $(cast storage $PROXY $idx --rpc-url $RPC)"
done
```
Gave: SSV_OPERATORS `0x38daa3fc…`, SSV_CLUSTERS `0x3611d36a…`, SSV_DAO `0x94ef691d…`, SSV_VIEWS
`0xf73954ad…`, SSV_OPERATORS_WHITELIST `0xe8ceac3f…`, SSV_STAKING `0x238c9c4f…`, SSV_VALIDATORS `0x9122fded…`.

**Then check for post-launch module swaps — this is the highest-value single command in this design:**

```bash
T0=$(cast keccak "ModuleUpgraded(uint8,address)")
curl -s "https://eth.blockscout.com/api?module=logs&action=getLogs&fromBlock=$FROM&toBlock=$TO&address=$PROXY&topic0=$T0"
```
Result: block 24,920,727 installed modules 0..6; **block 25,037,749 replaced module 1 (SSV_CLUSTERS) and
module 6 (SSV_VALIDATORS)**. `eth.drpc.org` timed out on a 900k-block span; Blockscout's `getLogs` API ate it.

## The two wrong turns (do not repeat)

1. **Judged a source difference by bytecode LENGTH.** Compiled the repo (`contracts/...` paths) and got
   17,579 / 14,075 / 4,207 vs live 17,637 / 14,198 / 4,207 — concluded "live has +58/+123/+231 bytes of
   unpublished code". **Wrong.** The metadata blob embeds the dependency closure's source *paths*; the
   recorded deployed build used `project/contracts/...` + `npm/@openzeppelin@4.9.6` + `forge-std@1.9.4`.
   Recompiling the *recovered deployed tree with its original paths* gave SSV_OPERATORS_WHITELIST
   **4,207 B with 0 differing bytes** (anomaly gone) and code-identical output for the other two.
2. **Claimed "source absent from the repository" before enumerating remote refs.** It was in
   `deploy/hotfix`. `git diff main..deploy/hotfix -- contracts/` = **2 files, 10 inserted lines, 0 deletions**.

## Correct final procedure (as executed)

```bash
# 1. recover the live tree per address (no API key)
curl -s -H 'User-Agent: Mozilla/5.0' "https://eth.blockscout.com/api/v2/smart-contracts/$ADDR" -o impl.json
# note is_verified_via_eth_bytecode_db / _verifier_alliance, compiler_settings{viaIR,runs,evmVersion,remappings}
# and additional_sources[] (whole tree, incl. npm/ + forge-std)

# 2. compile that tree with solc 0.8.24, viaIR, runs 10000, cancun, and the SAME source-unit names
./bin/solc-0.8.24.exe --standard-json solc_input.json > solc_out.json

# 3. compare CODE SECTION against cast code $ADDR  (equal length + only trailing metadata hash differs = identical)
# 4. find the branch that reproduces it
git ls-remote --heads origin | sed 's#.*refs/heads/##'
for b in <candidates>; do git fetch --depth 1 origin "$b" >/dev/null 2>&1; \
  git show FETCH_HEAD:contracts/modules/SSVClusters.sol | grep -c "vUnitsCluster = 0"; done
git diff --stat main..deploy/hotfix -- contracts/     # => 2 files, 10 insertions(+)
```

Coverage completed only after the **cSSV token** (`0xe018D3…`, in scope via Primacy of Impact) was also
diffed: 4,113 B both; only the `ssvStaking` immutable (= the proxy `0xDD9BC…`, matching `cSSV.ssvStaking()`
on-chain) and the metadata hash differed.

## The 10 live-only lines (reviewed, correct)

```solidity
// SSVClusters.migrateClusterToETH()  (+4)
uint64 vUnitsCluster = ebSnapshot.vUnits;
if (cluster.validatorCount == 0 && vUnitsCluster > 0) { ebSnapshot.vUnits = 0; vUnitsCluster = 0; }

// SSVValidators._bulkRemoveValidator(), legacy-SSV branch  (+6)
cluster.validatorCount -= validatorsRemoved;
if (cluster.validatorCount == 0) { SSVStorageEB.load().clusterEB[hashedCluster].vUnits = 0; }
```
They close a real bug present only in the published/audited tree: `migrateClusterToETH` computed
`baseline = validatorCount*BPS = 0` for a 0-validator cluster and then added the whole stale
`clusterEB.vUnits` to `daoTotalEthVUnits` and to every operator's `operatorEthVUnits` — phantom vUnits that
break the documented invariant and let the network/staking pool accrue ETH no cluster pays for.
Both are fixed on-chain, so the published-source bug is NOT exploitable live.

## Outcome (be honest about this shape of result)

Verified negative. 163 echidna properties across the vendor's whole harness suite passed, 0 counterexamples;
slither (64 detectors) 33 results all FP/known with **no reentrancy-eth / arbitrary-send-eth /
unchecked-transfer**; aderyn 88 detectors all FP/known. Structural reason no finding landed: live ==
audited commit + 10 reviewed lines, and the exclusion clause plus per-finding `fix/*` branches close
essentially every known class. Reusable verified negatives from this run: `view`-declared whitelist
callback ⇒ STATICCALL ⇒ reentrancy impossible; both proxies share one multisig owner; `proxiableUUID()`
reverting through the proxy is upstream OZ 4.9.6 `notDelegated` behaviour; proxy SSV balance ≥ cSSV supply
+ DAO SSV (no staking under-collateralisation).
