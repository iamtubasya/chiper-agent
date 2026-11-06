---
name: live-vs-source-bytecode-forensics
description: "Use when auditing a deployed (bug-bounty) contract whose published repo may not match what is live. Proves, byte-for-byte, which source is deployed; recovers live source from verifier-alliance/eth-bytecode-db; locates the deployed build's branch; and unblocks slither/aderyn/echidna/medusa on a modern Foundry project."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, smart-contract, audit, solidity, foundry, slither, bytecode, bug-bounty]
    related_skills: [smart-contract-audit, bug-bounty, onchain-finding-verification]
---

# Live-vs-source bytecode forensics

> Chain scope: EVM/Solidity below. For a **Solana** program there is no `eth-bytecode-db` path —
> the equivalent "is this enforced / is this deployed build the published source" work is
> `onchain-finding-verification` §1c (RPC account + upgrade-authority forensics) and §1e
> (`simulateTransaction` with `sigVerify:false` to execute the program read-only).

> **Companion lane — TEE / attestation targets.** When the deployed thing is a TEE endpoint rather
> than a bare contract, "what is running" is answered by re-implementing the vendor's attestation
> verifier and running it against the live endpoint. Recipe, the crypto traps (raw `r||s` vs DER,
> PCK-chain verify direction, keccak `digest_bits`) and a runnable verifier live in
> `codebase-bounty-review` → `references/tee-attestation-and-live-deployment-verification.md` +
> `scripts/verify_tdx_attestation_v2.py`.

## When to use

**Scope: EVM/Solidity only** (selector tables, CBOR metadata, solc recompile, verifier-alliance
lookup, slither/aderyn/echidna/medusa). For **Solana / Anchor** targets do not load this skill —
there is no selector table and no verifier-db path; go to `onchain-finding-verification` §1c–§1e
(upgrade-authority forensics over RPC, account-layout round-trip checks, read-only
`simulateTransaction` to test what the program enforces). Confirming the target's VM *before*
loading saves a cycle on every Anchor engagement.

- The program's "codebase" link points at a repo/commit, but you cannot assume that is what runs.
- An audit report says "final commit for mainnet launch is #X" and you need to know if that is true.
- You want to know which of the audit's findings are actually fixed live.
- `slither`/`aderyn`/`echidna`/`medusa` are blocked on a modern Foundry repo.

## Cheap pre-check before the full recompile (do this first)

Full source recovery + recompile is the expensive path. If the question is only **"is this specific
fix live?"**, answer it in two calls against the deployed bytecode:

```bash
# 1) compute the selector of the FIX's function (and of its custom error)
python3 -c "from Crypto.Hash import keccak as K; \
k=K.new(digest_bits=256); k.update(b'isApprovedSolveCaller(address)'); print('0x'+k.hexdigest()[:8])"
# 2) is it in the runtime code?
cast code <address> --rpc-url $RPC | grep -o '63<selector>'
```

Every `external`/`public` function's 4-byte selector appears in the dispatcher, so a fix added
upstream but **absent from the deployed bytecode** proves the deployment predates it — without
recovering or compiling anything. This is how the ether.fi AtomicQueue case was resolved: the live
contract carried the *old* 5-arg `solve(...)` selector and none of
`toggleApprovedSolveCallers` / `isApprovedSolveCaller` / `AtomicQueue__UnapprovedSolveCaller`, while
the repo's `main` carried all three.

Limits, so you know when to escalate to the full method below: this proves **presence/absence of a
signature**, not that the bodies are identical. A selector can survive a logic change. Use it as a
fast gate, then fall through to the code-section diff when the answer has to be load-bearing.

Source of the worked example + the extraction method:
`defi-exploit-forensics` → `skills/security/defi-exploit-forensics/references/technique-library-2025-2026.md`, `case-etherfi-atomicqueue.md`.

### ⛔ The `grep -o '63<selector>'` above produces FALSE POSITIVES — extract the dispatcher instead

Measured 2026-10-30 (Bankr, Base). Grepping the raw runtime-code *string* for `63<selector>` matched
`70a08231 balanceOf(address)` and `e9fad8ee exit()`, neither of which is a function on that contract.
A 4-byte value occurs as a coincidental substring of unrelated code often enough to matter: the
runtime hex is 30–80 KB of data where any 4-byte pattern appears by chance, and `63` is a common
opcode prefix. Believing the grep would have "proved" two functions that do not exist.

Extract the real dispatcher — only `PUSH4` immediates the contract actually compares against:

```python
import re
code = open("runtime.hex").read().strip().removeprefix("0x")
sels = []
for m in re.finditer(r'63([0-9a-f]{8})', code):        # PUSH4 <4 bytes>
    if m.group(1) not in sels: sels.append(m.group(1))
print(len(sels), sels[:40])        # 115 on the Bankr staking contract
```

Then test membership against that set, not against the raw string. Cross-check a candidate by
computing the selector locally (`cast sig "fn(type)"`) rather than trusting a lookup service —
`4byte.directory` was blocked from this host, returning zero results for all 60 selectors queried,
which reads as "unknown function" when it is really "no network".

**And when the dispatcher is non-standard, stop trying to reverse the ABI.** A 120-name sweep
(stake/unstake/withdraw/claim/requestWithdraw/… × 5 argument shapes = 600 candidates) matched **zero**
of the 115 dispatcher selectors on that staking contract — its function names are not the conventional
ones. Guessing names has a poor hit rate; if the product exposes a state/economics API (that
contract's numbers were all in `GET /staking/overview` and `GET /staking/position/{addr}`), read the
numbers from there and keep the bytecode only for the selectors you actually confirmed.

## When the contract is NOT verified at all — triage before you plan

The whole method above assumes you can obtain *a* source to compare against. On an unverified
deployment there is nothing to diff, and the honest move is to establish that **before** planning a
white-box audit rather than after.

**Triage every in-scope address first, including proxy implementations.** Measured 2026-10-30 on a
program naming four in-scope contracts: exactly **one** was verified. The three carrying the money —
a staking contract (19,382 B, not a proxy), its reward-drip module, and the implementation behind an
orders proxy — had **no published source**, so no slither/aderyn/echidna run was possible on any of
them. Discovering that after building a plan wastes the session.

Use Etherscan **V2**, not the per-chain V1 host — V1 is retired and answers
`{"status":"0","message":"NOTOK","result":"You are using a deprecated V1 endpoint, switch to Etherscan API V2 …"}`,
which is easy to misread as "no source published":

```bash
KEY=$(cat ~/AppData/Local/hermes/secrets/etherscan.key)
curl -sS "https://api.etherscan.io/v2/api?chainid=8453&module=contract&action=getsourcecode&address=$A&apikey=$KEY"
# fields: SourceCode ('' = unverified), ContractName, Proxy ('1'/'0'), Implementation
```

`chainid` is **mandatory** on V2 and the key is the multichain key, not a per-chain one. For a proxy,
re-query `Implementation` — a verified proxy with an unverified implementation is still unverified for
audit purposes.

**Then run the black-box probes that need no source and no funds**, because they cover the
Critical-class outcomes programs actually pay for:

- **Solvency / backing check** — the cheapest insolvency probe there is, and it needs no ABI beyond
  `balanceOf`. Compare the contract's token balance to the accounting totals the product itself
  publishes:

  ```bash
  cast call $TOKEN "balanceOf(address)(uint256)" $CONTRACT --rpc-url $RPC
  # vs GET /staking/overview -> totalStaked + totalCooling
  ```
  Measured: 26,377,624,958 BNKR held against 25,940,787,689 staked+cooling = ~436.8 M headroom →
  over-collateralized, no shortfall. That is a **verified negative on the highest-paying class**
  ("protocol insolvency") and it belongs in the report as one.
- **Privileged-role shape** — `owner()` plus any role address the product exposes. Three EOAs and no
  multisig on a fee router is a centralization *observation*, not a bug: do not report it, but record
  it so the next session does not re-derive it.
- **Selector presence** for the one or two functions you care about (see the PUSH4 note above).

**Never manufacture findings from bytecode.** If the money contracts are unverified, the honest
outputs are (a) fork-test behaviour on a local chain, or (b) a stated coverage gap naming each
unverified address. Reading assembly and calling something a reentrancy is how a report gets closed as
speculation.

> Worked end-to-end example, including the two wrong turns that cost the most time (length-based
> comparison; claiming a divergence before enumerating remote refs), the dispatcher/module storage-table
> resolution, and the `ModuleUpgraded` swap-detection query:
> `references/ssv-network-live-vs-source-case-study.md`

> **Cross-chain parity + privileged-role forensics:** when the same system is deployed on a testnet, the
> proxy address is usually identical (CREATE2) while the implementation differs — compare IMPLEMENTATIONS,
> and check the explorer host isn't serving the other chain's data (identical block hash at one height on
> two chainIds is the giveaway). Then answer the impact question with two RPC calls: who holds the
> funds-moving role and who holds `DEFAULT_ADMIN_ROLE` (`_authorizeUpgrade`), EOA vs Gnosis Safe, and the
> current balance at risk. Recipe incl. the `eth_getLogs` 10k-range cap, the single-topic-per-query trap,
> the creation-window query and the Safe probes:
> `references/cross-chain-parity-and-role-holders.md`

## ⛔ THE ONE RULE THAT MATTERS: compare the CODE SECTION, never the bytecode LENGTH
Solidity appends CBOR metadata that embeds the **source paths of the contract's dependency closure**.
A build whose paths are `project/contracts/...` (typical verifier-db submissions) is *longer* than one
using `contracts/...` even with byte-identical code. On SSV Network this produced a bogus "+231 bytes of
unexplained code" that vanished (0 differing bytes) once the tree was recompiled with the original
paths. Length deltas are NOT evidence; locate the first differing byte and check whether it is inside
the code section or inside the trailing ~60-1200 metadata blob.

### The OTHER cause of a length delta: the deployment's BUILD PROFILE, not the source

Before blaming paths, check which compiler the deploy pipeline actually uses — read the
`Makefile` / CI workflow, **not** `foundry.toml`. A repo can ship both and build with only one.
Observed 2026-10 (LIT-Protocol/chipotle, Base diamond): `forge build` came out 2-3% **smaller** on
every facet than the live runtime code —

| facet | live | `forge build` | `npx hardhat compile` |
|---|---|---|---|
| APIConfigFacet | 2037B | 1961B | 2037B |
| BillingFacet | 1339B | 1302B | 1339B |
| ViewsFacet | 9217B | 8957B | 9217B |
| WritesFacet | 14916B | 14604B | 14916B |

— a delta that reads exactly like "the deployment is not the source". Cause: **Foundry's default
`evmVersion` is cancun (PUSH0); Hardhat's default is paris**, and the pipeline's `compile:` target ran
`npx hardhat compile`. Recompiling with the pipeline's compiler made every length match exactly, and
the only remaining diff was 32 bytes inside the trailing CBOR metadata blob ⇒ code-identical.

Rule: reproduce the deployed build with the compiler the DEPLOYMENT uses — same framework, same
`evmVersion`, same `viaIR`, same optimizer runs — then diff. Getting the framework wrong costs a full
recompile cycle and produces a false divergence claim against the vendor.

## Step 1 — resolve live addresses (proxy + modules)
```bash
cast storage $PROXY 0xREDACTED_******** --rpc-url $RPC   # EIP-1967 impl
cast storage $PROXY 0xREDACTED_******** --rpc-url $RPC   # admin
```
For modular/proxy-dispatch designs (SSV-style: one dispatcher `_delegate`s to module contracts held in a
storage mapping), derive the module addresses from the storage table:
```bash
BASE=$(python3 -c "print(hex(int('$(cast keccak 'ssv.network.storage.main')',16)-1))")
# field index of the mapping inside the struct -> slot = BASE + idx ; key -> cast index
idx=$(cast index uint256 0 $(python3 -c "print(hex(int('$BASE',16)+3))"))
cast storage $PROXY $idx --rpc-url $RPC
```
Then confirm which modules are live *and when they were swapped* from events:
```bash
cast keccak "ModuleUpgraded(uint8,address)"          # topic0
curl -s "https://eth.blockscout.com/api?module=logs&action=getLogs&fromBlock=$FROM&toBlock=$TO&address=$PROXY&topic0=$TOPIC0"
# eth.drpc.org times out on ~1M-block spans; Blockscout's getLogs API eats them happily
```
A post-launch `ModuleUpgraded` for a module is the single most useful signal that a hotfix happened.

## Step 1b — EIP-2535 diamond targets: facets, not "the implementation"

A diamond proxy has no single implementation contract. `eth_getCode` on the proxy returns ~200 bytes of
dispatch and the logic lives in N facets, so the EIP-1967 slot dance in Step 1 is irrelevant and diffing
the proxy tells you nothing. Recover the map over RPC:

```
facets()                          0x7a0ed627  -> (address facet, bytes4[] selectors)[]
facetAddresses()                  0x52ef6b2c  -> address[]
facetFunctionSelectors(address)   0xadfca15e  -> bytes4[]   (arg = facet address, 32B left-padded)
owner()                           0x8da5cb5b
supportsInterface(bytes4)         0x01ffc9a7
```

Return data is ABI: `word[0]=offset`, `word[1]=count`, then `count` words; a selector is the first 4
bytes of its word.

Cross-check the diamond address against the service's own config endpoint where one exists (Lit
exposed it at `GET /core/v1/get_node_chain_config` → `contract_address`) instead of trusting docs.

Then diff the live selector SET per facet, **both directions**:

```bash
for n in WritesFacet ViewsFacet APIConfigFacet BillingFacet DiamondCutFacet DiamondLoupeFacet OwnershipFacet; do
  forge inspect "$n" methodIdentifiers --json | tr -d '\r' > "sel_$n.json"
done
```
```python
norm = lambda s: s[2:] if s.startswith("0x") else s
print("hidden :", sorted(live_all - repo_all))   # a function no source will show you
print("missing:", sorted(repo_all - live_all))   # stale deploy, predates a fix
```

⛔ **Normalise `0x` before any set arithmetic.** `facetFunctionSelectors` returns `0x`-prefixed
selectors; `forge inspect` values are bare hex. Comparing raw produced **76 "hidden" + 76 "missing"**
on a diamond whose source matched exactly. An all-hidden-AND-all-missing result is a normalisation
bug, never a finding.

Then `eth_getCode` each facet and byte-diff against a local build **made with the pipeline's compiler**
(see the build-profile section above). On Lit: 7 facets / 76 selectors, 0 hidden, 0 missing, and every
facet byte-identical except the metadata hash.

⚠️ **Facets under `libraries/` get no Hardhat artifact** — Hardhat only compiles `sources`. The
EIP-2535 reference facets (DiamondCut / DiamondLoupe / Ownership) therefore have no compiled
counterpart: verify them by selector match plus stock-implementation reasoning, and say explicitly
which facets you could NOT byte-verify rather than implying a full sweep.

⚠️ `forge inspect` needs the **bare contract name** (`forge inspect WritesFacet …`); the
`path/File.sol:Name` form fails with *"Could not find source file for contract"*. Pipe through
`tr -d '\r'` on Windows or the JSON parse dies on CRLF.

## Step 2 — recover the LIVE source (free, no API key)
```bash
curl -s -H 'User-Agent: Mozilla/5.0' "https://eth.blockscout.com/api/v2/smart-contracts/$ADDR" -o impl.json
```
Fields that matter: `is_verified`, `is_verified_via_sourcify` / `is_verified_via_eth_bytecode_db` /
`is_verified_via_verifier_alliance`, `is_partially_verified`, `compiler_settings` (viaIR, optimizer runs,
evmVersion, **remappings**), `source_code`, `additional_sources[]` (the whole tree, with `npm/`-style paths).
Save `additional_sources` verbatim — the `remappings` tell you the exact build layout
(e.g. `project/:@openzeppelin/contracts/=npm/@openzeppelin/contracts@4.9.6/`).

## Step 3 — compile the recovered tree EXACTLY as deployed, then diff

**Run the packaged script instead of hand-typing this every time:**
`scripts/compare_live_vs_compiled.py` links off the trailing CBOR metadata using its own 2-byte length
field, so it compares the **code section only** and tells you which of the two verdicts you have:
```bash
python scripts/compare_live_vs_compiled.py --addr 0xADDR --rpc $RPC --contract SSVClusters
python scripts/compare_live_vs_compiled.py --live live.hex --compiled compiled.hex --include-metadata
```
`--include-metadata` is for when you want a literal 0-diff match (only achievable if you also reproduce the
deployed build's source paths).

Build a solc standard-JSON with the recovered paths as source-unit names and the recorded remappings, plus
`viaIR`, `optimizer.runs`, `evmVersion` from `compiler_settings`; request
`abi, evm.bytecode, evm.deployedBytecode, evm.methodIdentifiers, devdoc, userdoc, metadata, ast`.
```bash
./bin/solc-0.8.24.exe --standard-json solc_input_<bundle>.json > solc_out_<bundle>.json
```
Verdict rules:
- `deployedBytecode` equal ⇒ live == that source (paths included).
- equal length, code section equal, only the trailing metadata hash differs ⇒ **code-identical** (only
  paths/order differ). This is the common "same code, different build" case.
- code section differs ⇒ real source difference; locate it and read the delta.

### Step 3b — the three traps that make a MATCH look like a DIVERGENCE (all hit on the Vana six-contract sweep)

A clean verification is easy to misread as "the deployment is not the source". Check these before writing
anything alarming — a false divergence claim against a vendor is expensive in both directions.

1. **Copy the WHOLE `compiler_settings` block, not just optimizer runs / evmVersion.** The explorer's
   stored settings are the build recipe; the single most-forgotten key is **`viaIR`**. Sweeping the six
   Vana implementations without it gave `compiled=12977B vs onchain=11355B` on escrow and `9998 vs 9091`
   on permissions — a length delta that looks like one contract is not the other. Adding `viaIR: true`
   made every length match **exactly** (11355/11355, 9091/9091, 10401/10401, 8159/8159, 12257/12257,
   4973/4973). If lengths differ, re-check the settings block before forming any hypothesis.
2. **Select the contract by the explorer's `name` field, never "the first object with bytecode".**
   A standard-JSON output dictionary is full of interfaces and libraries; picking the first non-empty
   `evm.deployedBytecode.object` yielded a **17-byte** object and a nonsense diff. Match
   `res["contracts"][*][impl_name]` where `impl_name` is what the verified record calls it
   (`DataPortabilityEscrowImplementation` etc.), and sanity-check the byte length is in the thousands.
3. **Immutables are zero-filled in solc's `deployedBytecode.object`** — they are filled at construction.
   So for a UUPS implementation the CORRECT verdict is: identical length + only N×20-byte diffs + the
   on-chain bytes at those offsets equal **the implementation's own address** (the `__self` immutable,
   stored twice behind OZ's upgradeable base / proxiable check). On Vana: escrow/servers/dataRegistry/
   feeRegistry/permissions = 40 differing bytes (2 × 20B), grantees = 38. That is a **MATCH**, reported as
   "deployed bytecode is a faithful build of the verified source". `scripts/compare_live_vs_compiled.py`
   strips the metadata blob, not immutables — enumerate diffs, print the segmented hex, and compare the
   on-chain bytes to `address(this)` before concluding anything.

A pleasant interaction with `metadata.bytecodeHash: "none"`: there is no trailing CBOR blob at all, so the
only expected diff IS the zero-filled immutable — the code-section/metadata dance in Step 3 becomes moot.

**Verification-status fields are not a substitute for this.** The Vana records read `is_verified: true` +
`is_partially_verified: true` with `is_verified_via_sourcify`, `is_verified_via_eth_bytecode_db` and
`is_verified_via_verifier_alliance` **all false**. Those flags do not tell you whether the deployment equals
the source; the recompile does. One full sweep of six implementations was ~75 s of solc time — cheap enough
to run on every engagement that touches contracts, and its result (match / code-identical / real delta)
belongs in the report as a stated negative or a finding.

## Step 4 — locate the deployed build's branch in the public repo
```bash
git ls-remote --heads origin | sed 's#.*refs/heads/##' | sort
for b in <candidates>; do git fetch --depth 1 origin "$b" >/dev/null 2>&1; \
  git show FETCH_HEAD:path/to/File.sol | grep -c "<signature of the suspect code>"; done
git diff --stat <audited-commit>..<branch> -- contracts/     # quantifies the live-vs-audited delta
```
Branch names are intelligence: `fix/<audit-id>`, `deploy/hotfix`, `ops-2-emergency-rollback`,
`ssv-bug-fixer`, `internal-analysis`, `ab/stress-test` tell you what the team had to patch. **Read the
program's exclusion clause before you spend effort here** — an exclusion like *"any issue documented …
within any branch of the specified repository"* makes every bug with a `fix/*` branch unwinnable.
On SSV Network the whole live-vs-audited delta turned out to be `main` + 10 lines living in
`deploy/hotfix`; the honest conclusion was "no loophole, no unpublished code".

## Step 5 — unblock the toolchain on a modern Foundry repo
**`forge` ≥1.7 `--build-info` writes only `{id, source_id_to_path, language}`** — NOT the hardhat-shaped
`{solcVersion, input, output}` that `crytic-compile` (foundry platform → `hardhat_like_parsing`) expects.
Symptom: `FileNotFoundError: out/build-info/<id>.output.json` then `KeyError: 'output'`.
Fix — synthesise the hardhat shape yourself:
```python
# 1) build the standard-JSON input from out/build-info/<id>.json's source_id_to_path
#    (remappings/optimizer/viaIR/evmVersion must match foundry.toml)
# 2) run solc yourself:  solc --standard-json solc_input.json > solc_output.json
# 3) wrap and overwrite the build-info:
json.dump({"id": uniq, "solcVersion": "0.8.24", "in": inp, "output": out},
          open(f"out/build-info/{uniq}.json","w"))
```
Two more traps: keep `solcVersion` a bare `0.8.24` (slither's `incorrect-solc` detector crashes on
`0.8.24+commit.e11b9ed9` as `ValueError: invalid literal for int(): '24+commit'`), and delete any
`<id>.output.json` you created while debugging so the parser uses the real file.
After that, `slither . --compile-force-framework foundry --foundry-ignore-compile` works.
For `echidna`/`medusa`, bypass the build-info entirely and compile the harness file directly —
the repo's own harnesses then run unchanged (SSV ships 16):
```bash
echidna test/echidna/X.sol --contract X --test-mode property --test-limit 4000 --seq-len 100 \
  --crytic-args "--compile-force-framework solc --solc-remaps @openzeppelin=node_modules/@openzeppelin"
```
For `mythril`, flatten first so no remapping is needed, and give it a Linux solc:
```bash
forge flatten contracts/modules/X.sol > flat/X.flat.sol
wsl -d Ubuntu -- bash -lc 'export SOLC=$HOME/.solcx/solc-v0.8.24; python3 -m mythril.interfaces.cli analyze flat/X.flat.sol --solv 0.8.24 --execution-timeout 200'
```
⚠️ **A flattened file that only builds under viaIR will fail mythril** with
`CompilerError: Stack too deep. Try compiling with --via-ir` — mythril ignores `foundry.toml`, so pass the
setting explicitly (`--solc-json` expects a *settings* JSON, not standard-json input):
```bash
echo '{"viaIR": true, "optimizer": {"enabled": true, "runs": 200}}' > viair.json
… analyze flat/X.flat.sol --solv 0.8.24 --solc-json viair.json --execution-timeout 200
```
Do not write such a contract off as unanalysable. Note also that `--solc-json` clobbers any remappings you
patched into `mythril/ethereum/util.py`, which is another reason flattening is the better route.
A clean mythril run is WEAK evidence on layered DeFi logic — record it as "no issues detected" with that
caveat, never as proof of absence.
Windows-native mythril is not viable (`ModuleNotFoundError: No module named 'eth'`, plus missing
asn1crypto/blake2b-py/coincurve) — use the WSL path above. If you do try to unblock it, note that
`pip install py-evm` into the shared interpreter silently **downgrades `eth-utils`** and breaks `web3`'s
resolver (`web3 7.x requires eth-utils>=5.0.0`). Fix it immediately and verify, rather than leaving a
broken shared env behind:
```bash
python3 -m pip install --upgrade "eth-utils>=5.0.0"   # restore web3's resolver
python3 -c "import web3, eth_utils; print(web3.__version__, eth_utils.__version__)"
python3 -m pip check | head                            # remaining complaints are usually pre-existing
```

## Step 5b — an invariant harness that medusa/echidna will actually RUN

Fuzzers that never execute look like "clean" in a log. Each of these cost a full run on the Vana
DataPortabilityEscrow (2026-10) before the campaign started, and each fails *quietly*:

1. **The harness must live under the COMPILED source root, not `test/`.** Starting from a Foundry
   project whose `src`/`contracts` dir is what `crytic-compile` compiles, a harness in `test/` is simply
   invisible: medusa prints `error Failed to start fuzzer / no assertion, property, optimization, or
   custom tests were found to fuzz` and echidna `Given contract "X" not found in given file`. Move the
   harness (and any helper like a minimal proxy) into `contracts/harness/` and re-run `forge build`
   before launching either fuzzer.
2. **UUPS implementations cannot be initialised directly.** `constructor() { _disableInitializers(); }`
   means `new Impl()` + `initialize(...)` reverts. Deploy behind a proxy: a **minimal ERC1967 proxy is
   ~20 lines** (sstore the implementation slot `0x360894…2bbc`, delegatecall the init data) and is often
   necessary because the recovered OZ tree ships `ERC1967Utils.sol` but **not** `ERC1967Proxy.sol`.
   Starter file: `templates/invariant_harness_minimal.sol` (MiniProxy + MockERC20 + dual-named invariants).
3. **Make the harness the ADMIN, never the role under test.** The escrow rejected the mock token with
   `AssetNotSupported` until the harness (as `DEFAULT_ADMIN_ROLE` from `initialize(address(this), FAC)`)
   called `setTokenWhitelisted(token, true)`. If the harness also held the funds-moving role, the
   invariant "a role-less caller cannot move funds" would be vacuous. Pass the privileged role to an
   address the harness cannot impersonate (`address(0xFAC)`).
4. **Emit both naming styles** so one harness serves both engines: `invariant_*()` (foundry/medusa) plus
   `echidna_*()` aliases that call the same predicate.
5. **`address(this)` is not a compile-time constant** — `address internal constant OWNER = address(this)`
   fails with "… to be compile-time constant". Pass `address(this)` inline to `initialize`.
6. **A grouped redirect resolves against the OUTER shell's cwd.** `{ cd sub && tool …; } > ../../x.log`
   sends the redirect to `<outer-cwd>/../../x.log`; when that path does not exist the whole job dies with
   `bash: ../../x.log: No such file or directory` and **no tool ever ran** (it looks like an instant
   failure with an empty log). Use an absolute log path.
7. **Bound the campaign explicitly** (`--timeout 600/300`) and record the config with the result: "0
   violations in N sequences" is evidence; "no issues" is not.

## Static-analyzer triage: three recurring false positives

Aderyn on six proxy-implemented contracts produced 7 "High" hits, **all** non-reportable. Do not paste
analyzer output into a report — resolve each against the code first (write the triage to
`evidence/**/aderyn_triage.md` so the negative is auditable):

- **"Contract locks Ether without a withdraw function"** on a UUPS/upgradeable *implementation* = FP. The
  implementation never custodies native value; the proxy does. Check the one contract that does hold
  native for a real way out (escrow: `depositNative` in, `_payout` → `payable(to).call{value:…}` with
  `asset == address(0)` out, plus `receive()`).
- **"Reentrancy: state change after external call"** triggered by a fee-on-transfer deposit pattern
  (`balanceBefore = token.balanceOf(this)` … `received = balanceOf(this) - balanceBefore` …
  `_balances[acct][token] += received`) = FP: `balanceOf` is a STATICCALL and the write is the intended
  effect; every entry point carrying it is `nonReentrant`. Verify the modifier is actually present on each
  flagged function before dismissing (and note aderyn's `L-5 nonReentrant is not the first modifier` as
  style, no impact).
- **"Unsafe casting of integers"** where the value is internally derived (`uint64(version_)` with
  `version_ = uint256(currentVersion) + 1` and `currentVersion` itself a uint64) = not exploitable: the
  downcast cannot truncate. The residual note is the `unchecked` increment of a monotonic counter
  (informational at most).

## Verified negatives worth recording (they recur)
- **Whitelist/oracle callbacks declared `view` are STATICCALLs** (e.g. `ISSVWhitelistingContract.isWhitelisted`).
  A "malicious whitelisting contract re-enters to drain" hypothesis is therefore impossible — reverted on
  any state change. Check the interface's mutability before designing a reentrancy PoC.
- **UUPS `proxiableUUID()` reverting through the proxy is upstream OZ 4.9 behaviour** (`notDelegated`
  requires `address(this) == __self`); it returns the EIP-1967 slot when called on the implementation.
  Not a finding.
- **Module/owner hygiene**: compare `owner()` across every in-scope proxy — if the secondary proxy's owner
  is the same multisig, there is no weaker-owner finding (verified on SSV: Views proxy owner == Network
  proxy owner == 0xb35096b0…).

## halmos: reuse the VENDOR's echidna harness (and its thrash trap)
When a repo already ships echidna property harnesses, do **not** author a symbolic spec from scratch —
your restatement of the invariants would be the thing under test. Instead write a thin `Test` wrapper that
drives the vendor's own `action_*` functions with symbolic arguments and asserts the vendor's own
`echidna_*` properties:
```solidity
contract HalmosX is Test {
    VendorEchidna h;
    function setUp() public { h = new VendorEchidna(); vm.deal(address(h), 100_000 ether); }
    function check_stake(uint256 amt, uint8 u) public {
        try h.action_stake(amt, u) {} catch {}          // infeasible input must not count as a revert-CEX
        assert(h.echidna_accrued_within_pool());
    }
}
```
Wrap every action in `try/catch`: halmos otherwise reports an infeasible-input revert as a counterexample.
That wrapper works (harness constructors in this style are usually argument-less), **but**:
⚠️ adding a test file that imports the whole harness recompiles the entire test unit. On a
`viaIR = true` + `optimizer_runs = 10000` project that means 100+ sources through viaIR, which can exhaust
memory and **swap-thrash indefinitely while writing zero artifacts**. Symptom: the log shows only
`Compiling N files with Solc …` and `find out -name '*.json' -newermt '-5 minutes'` returns 0 while the box
is pinned. Do not wait it out — check for artifact progress before blocking, then either (a) run halmos
against a **minimal** harness that does not import the vendor suite, or (b) disable viaIR for the test
unit. Record the aborted run in the ledger as a **GAP with the cause**, never as a clean result, and kill
the orphaned `solc`/`forge` children (they survive the parent) so you don't leave the box saturated:
`taskkill /F /IM "solc-0.8.24.exe"` (image names are unique to your own downloaded binary).

## Egress hygiene + browser harness — do this BEFORE recon
- **Check the egress first:** `warp-cli status` and `curl -s https://api.ipify.org`. On this rig the machine
  egresses via **Cloudflare WARP (104.28.x.x)** and that pool is flagged on multiple targets: FreeAgent
  answered a 302 anti-fraud redirect after a scanner volley, and Cabify's apex returned **429 to every
  request including a real Chrome** (proved over CDP) while sibling hosts on the same estate answered
  200/302/404 normally. **A real browser passing where `curl` fails localises the block to YOUR egress**,
  not the site. Recovering = `warp-cli disconnect`, but that is a machine-wide change: propose it, never
  toggle the operator's network unilaterally — and don't report the limiter as a finding.
- **Per-host rate limits are often single-digit requests.** Cabify's `developers.cabify.com` 429'd after
  ~8 spaced requests. Budget a few requests per host, spread across hosts, identify every request
  (`X-Bug-Bounty: <email>`), and back off rather than retrying hot.
- **`browser_navigate` may target Camofox (port 9377), not the CDP browser** — if it 500s, launch your own
  Chrome on the port in `browser.cdp_url` (default 9222) and drive it with raw `browser_cdp`:
  `chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=<engagement>
   --no-first-run --window-position=-32000,-32000 about:blank`, then `Page.navigate` + `Runtime.evaluate`.
  Off-screen keeps a real (non-headless) fingerprint without disturbing the operator's screen.
- **Wildcard-DNS test before trusting any subdomain list:** resolve a random name
  (`zzz-not-real-92731.<domain>`). If it answers, every "finding" under that domain is parked-DNS noise.
  Cabify: `*.cabify.net` -> one parking IP, and `cabify.net` itself is a **third-party for-sale domain**
  (NS hichina/Alibaba, MX justemails.app) — its historic `vpn01/anyconnect/webvpn.external/portal` names
  are CT-log ghosts pointing at the squatter. Conversely `*.cabify.com` has no wildcard, so resolving
  names there are real. Also test whether the IdP still trusts the lost domain (Cabify's IdentityServer
  rejected all `*.cabify.net` redirect_uris — a verified negative worth having).
- **Archive output (gau/waybackurls) is historical, not live:** 3 of the 4 juiciest Cabify endpoints were
  dead on re-check. Verify each before use, and don't build an IDOR hypothesis on a `?code=` parameter
  without checking what it is (Cabify's were **driver referral** codes, not tracking codes).
- **A scanner's hit is not a finding.** 433 S3 name guesses returned 4 "publicly listable" buckets —
  all third parties (Botkeeper favicons, a US bootcamp, Portuguese media). Read the content and establish
  ownership before anything reaches a report.

## Environment quirks (Windows/WSL)
- `Wsl/Service/CreateInstance/CreateVm/ERROR_TIMEOUT` on a specific distro is transient: loop
  `wsl --terminate Ubuntu; sleep 6; wsl -d Ubuntu -- true` up to 5× before delegating work. Other distros
  (e.g. a bare `Ubuntu-26.04`) boot fine but have no tooling installed — do not assume they are usable.
- `write_file` to `/tmp/x.py` on Windows lands in `C:/Users/<u>/AppData/Local/Temp`, but a *program*
  running with cwd on `D:` resolves `/tmp/x.py` to `D:/tmp/x.py`. Pass absolute Windows paths to python.
- `MSYS_NO_PATHCONV=1` + `<<'PY'` heredocs mangle backslashes inside regexes; write the script to a file
  and run it instead.
