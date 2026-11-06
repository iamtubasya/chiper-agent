# Deployed-vs-source verification for dispatcher / module-architecture protocols

**Use when** the target is live (proxy, upgradeable, or a dispatcher that `delegatecall`s into separately
deployed "module" contracts) and you must know whether the GitHub repo is actually what runs. An audit's
stated "final commit for launch" is a *claim*. Measure it.

Worked end-to-end on SSV Network (2026-10): 9 in-scope contracts, 2 of which were **not** the audited
commit. Total cost ~1 h of wall clock, all commands reproducible.

---

## Step 0 — resolve the live implementation / module set

EIP-1967 implementation slot (ERC1967 / UUPS proxies):

```bash
cast storage <PROXY> 0xREDACTED_******** --rpc-url $RPC
# also useful: proxy admin = 0xREDACTED_********
```

For a **dispatcher** (the implementation `delegatecall`s business logic into per-module contracts), the
module addresses live in custom storage, not in the proxy's code. Read the storage layout, compute the
base slot, then index it:

```bash
# SSV worked example
BASE=$(cast keccak "ssv.network.storage.main")          # SSV_STORAGE_POSITION = keccak - 1
SLOT_SSVCONTRACTS=$(python3 -c "print(hex(int('$BASE',16)-1+3))")   # field #3 of StorageData
for k in 0 1 2 3 4 5 6; do
  idx=$(cast index uint256 $k $SLOT_SSVCONTRACTS)
  val=$(cast storage <PROXY> $idx --rpc-url $RPC)
  echo "module[$k] = 0x${val:26}"
done
```

Sanity check the result against the ABI's enum order and against the contract's own `getVersion()`.
Do **not** report a selector/bytecode mismatch against the proxy — a minimal ERC1967 proxy contains no
selectors at all (SSV's `SSVNetwork` proxy is ~680 B of delegate logic; the real dispatcher is the
*implementation*). Diff against the implementation address.

---

## Step 1 — recover the live source + the exact compiler settings of the deploy build

```bash
curl -s -A "Mozilla/5.0" "https://eth.blockscout.com/api/v2/smart-contracts/<ADDR>" -o impl.json
python3 - <<'PY'
import json
d = json.load(open('impl.json'))
print(d['name'], d['file_path'], d['compiler_version'], d['optimization_runs'])
print(json.dumps(d.get('compiler_settings'), indent=1))          # <-- the valuable part
print(len(d.get('additional_sources') or []))
PY
```

`compiler_settings` carries `viaIR`, `optimizer.runs`, `evmVersion`, and the **remappings** — the
remappings reveal (a) the pinned npm dep versions (`npm/@openzeppelin/contracts@4.9.6/`) and (b) the
**source-path prefix** the deploy build used (`project/contracts/...`). Also check
`is_verified_via_eth_bytecode_db` / `is_verified_via_verifier_alliance` / `is_partially_verified` so you
know whether the record is an exact match or a best-effort one.

---

## Step 2 — compare bytecode, correctly

```bash
cast code <ADDR> --rpc-url $RPC > live.hex                  # live runtime
forge inspect <Contract> deployedBytecode > comp.hex        # from the repo
```

⛔ **NEVER judge equality (or difference) by bytecode LENGTH.** The solidity metadata appended to the
bytecode embeds the *source paths* of the contract's dependency closure. A build whose keys are
`project/contracts/...` and `npm/...` is **tens to hundreds of bytes longer** than one using
`contracts/...` and `node_modules/...` with byte-identical code. Observed on SSV:

| contract | repo-path compile | deployed-path compile | live | conclusion |
|---|---|---|---|---|
| SSV_OPERATORS_WHITELIST | 3,976 B | **4,207 B, 0 differing bytes** | 4,207 B | identical code — the "+231 B" was pure metadata |
| SSV_CLUSTERS | 17,579 B | 17,637 B (code section identical) | 17,637 B | code really differs (a 4-line guard) |
| SSV_VALIDATORS | 14,075 B | 14,198 B (code section identical) | 14,198 B | code really differs (a 6-line guard) |

I burned a chunk of the session chasing the "+231 B anomaly" before realising it was metadata. Do it the
right way the first time: **recompile the recovered tree with its own paths + pinned deps and compare the
code section.**

```python
# group the differing byte ranges; the tails are noise, the head is signal
diffs = [i for i in range(0, len(a), 2) if a[i:i+2] != b[i:i+2]]
# a diff confined to the last ~51 bytes (+ a 32-byte blob) = metadata / IPFS hash. Expected.
# a diff early in the body = a real code difference. Investigate, then map it back to source.
```

**Expected divergences that are NOT findings:**

* **Immutables.** Forge's artifact has them zeroed; the chain holds the constructor value. A
  `PUSH32 000…000<addr>` in the artifact vs `<addr>` live is normal. OZ 4.9 `UUPSUpgradeable` declares
  `address private immutable __self = address(this)`, so the implementation legitimately carries **its
  own address** as an immutable in 4 places — that is not a misconfiguration.
* **Metadata IPFS hash** (last ~51 bytes). Differs whenever source paths differ, even for identical code.

---

## Step 3 — if the code really differs, find the DEPLOYMENT BRANCH before crying "unpublished"

Almost always the build is public, just not on the default branch. Enumerate, then bisect:

```bash
git ls-remote --heads origin | sed 's#.*refs/heads/##' | sort
# then, for each plausible ref, test for the distinguishing lines
for b in deploy/hotfix deploy/v2.0.0-mainnet fix/remove-dead-cluster-flag ssv-bug-fixer ...; do
  git fetch --depth 1 origin "$b" >/dev/null 2>&1
  echo "$b $(git show FETCH_HEAD:contracts/modules/X.sol 2>/dev/null | grep -c '<distinctive line>')"
done
git diff --stat <default-branch>..<candidate> -- contracts/
```

Refs worth trying in order: `deploy/hotfix`, `deploy/*`, `deploy/<version>-mainnet`, `fix/<finding-id>`,
`ops-*-rollback`, `main-with-*`, `mixed-version-*`. On SSV the answer was `deploy/hotfix` =
`main` + exactly 10 lines (2 files). **Beware:** `git diff main..fix/<audit-id>` on stale branches shows
hundreds of lines because the branch is *behind* main, not because it carries a big fix — diff the
specific file, or check whether main's version already contains the fix.

---

## Step 4 — prove module swaps on chain (timeline evidence)

```bash
T0=$(cast keccak "ModuleUpgraded(uint8,address)")
curl -s "https://eth.blockscout.com/api?module=logs&action=getLogs&fromBlock=<lo>&toBlock=<hi>&address=<PROXY>&topic0=$T0"
```

Wide `eth_getLogs` ranges time out on free RPCs; Blockscout's `/api?module=logs` endpoint handled a
2.1M-block span. Read `topics[1]` as the module id and the last 20 bytes of `data` as the new address.
On SSV this showed modules 0..6 installed at block 24,920,727 and **SSV_CLUSTERS + SSV_VALIDATORS
replaced at block 25,037,749** — the patch timeline, straight from the chain.

---

## Step 5 — make crytic-compile work again (slither / aderyn / medusa)

forge 1.7.1's build-info is `{id, source_id_to_path, language}` only; crytic-compile 0.4.2 expects
hardhat-shaped `{solcVersion, input, output}`. Synthesize it:

```python
import json, os
meta = json.load(open('out/build-info/<id>.json'))
sources = {p: {"content": open(p, encoding='utf-8').read()} for p in meta['source_id_to_path'].values()}
inp = {"language": "Solidity", "sources": sources, "settings": {
    "remappings": ["@openzeppelin/=node_modules/@openzeppelin/"],
    "optimizer": {"enabled": True, "runs": 10000}, "viaIR": True, "evmVersion": "cancun",
    "outputSelection": {"*": {"*": ["abi","evm.bytecode","evm.deployedBytecode","evm.methodIdentifiers",
                                    "devdoc","userdoc","metadata"], "": ["ast"]}}}}
json.dump(inp, open('solc_input.json','w'), separators=(',',':'))
```
```bash
./solc-0.8.24.exe --standard-json solc_input.json > solc_output.json     # ~16 min, viaIR
python3 -c "import json;json.dump({'id':'<id>','solcVersion':'0.8.24',\
  'input':json.load(open('solc_input.json')),'output':json.load(open('solc_output.json'))},\
  open('out/build-info/<id>.json','w'),separators=(',',':'))"
rm -f out/build-info/<id>.output.json
slither . --compile-force-framework foundry --foundry-ignore-compile --filter-paths "contracts/test/|node_modules/" --exclude-dependencies
```

Gotchas: get a matching `solc` binary (`solc-windows.exe` per release from github.com/ethereum/solidity
/releases/download/v0.8.24/); move files that need a different pragma (`pragma solidity =0.8.4`,
`=0.8.18`) **out of `src/`** before building or `forge build` refuses; `solcVersion` must be a bare
version string. When comparing against a *verified deploy tree*, feed the tree's own paths
(`project/contracts/...`, `npm/@openzeppelin/contracts@4.9.6/`, `npm/forge-std@1.9.4/src/Test.sol`) and
its recorded remappings — otherwise fork/test files that import `forge-std/Test.sol` won't resolve.

---

## Step 6 — running the vendor's own echidna harnesses cheaply

```bash
cp <repo>/test/echidna/*.sol test/echidna/
for h in SSVDAOEchidna SSVClustersEchidna ...; do
  echidna "test/echidna/$h.sol" --contract "$h" --test-mode property --test-limit 4000 --seq-len 100 \
    --crytic-args "--compile-force-framework solc --solc-remaps @openzeppelin=node_modules/@openzeppelin" \
    > "scanners/echidna/$h.log" 2>&1
  grep -E "passing|failing" "scanners/echidna/$h.log" | tail -30
done
```

Run these even though the vendor already CI-runs them: a clean sweep is a strong, cheap "verified
negative" row in the coverage ledger, and their harness pattern (one contract inheriting all modules
`is SSVValidators, SSVOperators(0), SSVOperatorsWhitelist, …`, relying on the assembly-fixed storage
slots to share state) is *also the fastest way to write a Foundry PoC* without the proxy.

---

## Pitfalls that cost time here

* Comparing deployed bytecode by **length** → false "unpublished code" alarm. Compare the code section.
* Assuming the audit's "final commit" is the launch build. Diff it against the deploy branch.
* Claiming `deployed != source` before enumerating **all** remote heads. `git ls-remote --heads` first.
* Reporting a proxy's `cast code` selector set as "functions missing on chain" — a minimal proxy has no
  selectors. Use the implementation.
* A `view` interface function compiles to **STATICCALL**. Before building a reentrancy PoC through a
  hook like `isWhitelisted(...)`, open the interface: if it's `view`, the hypothesis is dead on arrival.
* WSL distro VM can wedge (`Wsl/Service/CreateInstance/CreateVm/ERROR_TIMEOUT`) mid-run; the fix is
  `wsl --terminate <distro>` and retry — the tools themselves are fine.
