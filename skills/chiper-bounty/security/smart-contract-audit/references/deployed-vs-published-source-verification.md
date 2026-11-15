# Verifying the DEPLOYED contract against the published/audited source

**When to load.** Any deployed-target engagement where the program says "the codebase is <repo>" and
excludes "anything identified in the audit report" / "anything documented in any branch of the repo".
Those exclusions are keyed to a *source tree*. If the live bytecode is not that tree, the exclusion
does not describe what runs on chain — and that changes what is winnable.

Do this BEFORE the write-up, and before accepting any triager claim of "known/fixed".

---

## 0. Why the selector diff is not enough

`scripts/deployed_vs_source_selector_diff.py` (source `methodIdentifiers` vs `cast code`) only tells you
whether a *public entry point* exists. It cannot see:
- changed *bodies* (a fixed function whose selector still exists),
- added internal-only logic,
- a module that was **swapped for a patched build** of the same contract.

The reliable primitive is a **full `deployedBytecode` byte-for-byte comparison**, with the two expected
classes of difference whitelisted: constructor-set **immutables** and the **CBOR metadata IPFS hash**.

## 1. Recover the verified source + compiler settings

```bash
addr=0x...; curl -s "https://eth.blockscout.com/api/v2/smart-contracts/$addr" -o impl.json
python3 - <<'PY'
import json; d=json.load(open('impl.json'))
print(d['name'], d['file_path'], d['compiler_version'], d['optimization_runs'], d['evm_version'])
print('verified_via_alliance', d.get('is_verified_via_verifier_alliance'),
      'partially', d.get('is_partially_verified'), 'changed_bytecode', d.get('is_changed_bytecode'))
print('viaIR', (d.get('compiler_settings') or {}).get('viaIR'))
print('additional_sources', len(d.get('additional_sources') or []))
# write every file, preserving file_path, into deployed_src/<name>/
PY
```

`additional_sources` are a full self-consistent tree (paths look like `project/contracts/...` plus
`npm/<pkg>@<ver>/...`). **Files that do not affect the target's bytecode may legitimately differ
between two verification records of the same repo** — so only trust the tree that is the *entry
contract's own* verification, and always confirm by compiling.

For a proxy, get the implementation from the EIP-1967 slot first:
`cast storage $PROXY 0xREDACTED_********`.

## 2. Compile the repo tree and the recovered tree, then compare

Same compiler, same `opt runs`, same `viaIR`, same `evmVersion` as the record. Then:

```python
live = cast_code(addr)          # strip 0x
comp = artifact_deployedBytecode
if len(live) != len(comp): print('LEN DIFF', len(live), len(comp))   # <- the finding
else: report byte-ranges that differ
```
Reading the result:
- **Same length, diffs only inside a 32-byte window at a `PUSH32` and in the trailing ~51 bytes** =>
  immutables + metadata. The build IS the source. Say so in the report — it pre-empts "is this even
  deployed?".
- **Different length** => the published source does **not** reproduce the deployed code. Now diff the
  *recovered live tree* against the repo tree file-by-file to name the delta in source terms.
- Cross-check the recovered tree by compiling **it** and re-matching the live bytecode. If it matches
  exactly (code-identical, metadata hash differing only because the tree uses a different path layout),
  the delta is proven, not inferred.

Parse an artifact instead of trusting `forge inspect` output for the immutable map:
`out/<C>.sol/<C>.json` → `deployedBytecode.immutableReferences` (maps AST-id → byte offsets). When a
live executable contains a value where the artifact has zeros, resolve the AST id in a
`solc --standard-json` output to learn *which* variable it is — this is how the OZ UUPS
`address private immutable __self = address(this);` (4 references, value == the contract's own address)
gets explained instead of looking like an anomaly.

## 3. Red-flag a *module* architecture: registry table + upgrade events

Diamond/dispatcher designs store module addresses in storage, so "the" address in the asset list is only
a proxy. Two reads make the whole system visible:

```
# 1. registry table: struct StorageData { ... mapping(SSVModules => address) ssvContracts; ... }
#    slot = keccak(<constant string>) - 1 + struct offset; entry = keccak(abi.encode(key, slot))
cast keccak "ssv.network.storage.main"                       # then slot = base + 3
cast index uint256 <enumIndex> <slot>                        # mapping key -> entry slot
cast storage $PROXY <entrySlot>                              # -> module address
```
Then wait for the timeline: a `ModuleUpgraded(uint8 indexed moduleId, address moduleAddress)`-style
event reveals *when* each module was installed/replaced. A **later replacement** is the strongest
possible signal of a post-audit patch.

```
T0=$(cast keccak "ModuleUpgraded(uint8,address)")
curl -s "https://eth.blockscout.com/api?module=logs&action=getLogs&fromBlock=<lo>&toBlock=<hi>&address=$PROXY&topic0=$T0"
```
Blockscout's logs API answers wide ranges when a public RPC's `cast logs` times out on ~1M blocks.

## 4. What to DO with the divergence

1. **Name the delta in source terms** (recovered vs published) and classify each hunk:
   * a guard the live build ADDED (=> the published/audited source has a *latent bug*; find it),
   * a guard the live build REMOVED / omits (=> a *live* defect the repo already fixed).
2. **The live-added hunks are unreviewed code.** Read them as the primary audit target: no audit report
   line covers them, so a bug there is neither "identified in the report" nor "documented".
3. **The published-only bugs are not payable on their own** (the asset is the deployed contract) — but
   they explain *why* the divergence exists, which makes the report credible.
4. For the program: the exclusion clause is unenforceable for a module whose deployed source is not
   published. Put that in the write-up explicitly and ask for the deployed sources.

## 5. Worked example (SSV Network, 2026-10)

9 in-scope contracts. 6 matched the repo exactly (immutables + metadata only). 3 did not:
SSV_CLUSTERS +58 B, SSV_VALIDATORS +123 B, SSV_OPERATORS_WHITELIST +231 B.
Compiling the *recovered live* SSV_CLUSTERS tree reproduced the live bytecode exactly (17 637 B,
code-identical) while the repo tree compiled to 17 579 B → proven divergence. `ModuleUpgraded` logs
showed modules 1 and 6 were **replaced at block 25 037 749**, after the audited commit, verified
2026-05-06/10 vs the audit's 2026-04-28. The two live-added hunks were guards in
`migrateClusterToETH()` and the legacy-SSV removal branch; the repo versions of those paths inject
phantom vUnits into `daoTotalEthVUnits` (breaks `daoTotalEthVUnits == ethDaoValidatorCount*BPS +
Σdeviations`, lets the staking pool accrue ETH no cluster pays) — a latent bug in the audited source,
patched only in the unpublished live build.

Record the negatives too: "+231 B with an apparently identical source" was left as an OPEN anomaly
rather than claimed — an unexplained length delta is a lead, not a finding.

## 6. Gotchas

- `cast code` on a **proxy** returns the proxy's ~680-byte delegate stub; all selectors will look
  "missing". Always compare against the implementation.
- Substring-testing a selector in hex is unsound (fails when a `PUSH0`/`PUSHn` encoding shifts it).
  Parse dispatch selectors or compare full bytecode instead.
- A verification record is evidence, not gospel: `is_partially_verified=true` appears on records that
  match perfectly, and trees can include unrelated files (e.g. `forge-std@1.9.4`). Confirm by compiling.
- WSL flakiness (host-side, one command to clear): if `wsl -d Ubuntu` dies with
  `Wsl/Service/CreateInstance/CreateVm/ERROR_TIMEOUT`, run `wsl --terminate Ubuntu` and retry; a
  freshly-created distro boots fine but has no tooling, so prefer repairing the existing one.
