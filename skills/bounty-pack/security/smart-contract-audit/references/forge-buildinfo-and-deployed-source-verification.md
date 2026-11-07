# forge ≥1.7 build-info, fuzzer invocation, and deployed-source verification

Session-proven detail (SSV Network, 2026-10) for the three things that block the standard toolchain on a
modern Foundry repo, plus the correct way to compare a deployed contract against a source tree. Companion
detail lives in the `live-vs-source-bytecode-forensics` skill.

---

## 1. ⛔ `forge` ≥1.7 `--build-info` breaks crytic-compile (slither / aderyn / echidna / medusa)

`forge` ≥1.7 writes `out/build-info/<id>.json` as **only** `{id, source_id_to_path, language}`. That is
NOT the hardhat-shaped `{solcVersion, input, output}` that `crytic-compile` 0.4.2 expects
(`foundry.py` → `hardhat_like_parsing` → `get_targets_json`).

Symptoms, in the order you hit them:

| attempt | result |
|---|---|
| `slither .` | `FileNotFoundError: .../out/build-info/<id>.output.json` |
| `slither .` (after creating a stub `.output.json`) | `KeyError: 'output'` |
| `slither . --compile-force-framework solc` | `contracts is a directory. Expected a Solidity file when not using a compilation framework.` |

**Fix — synthesise the shape yourself:**

1. Read `source_id_to_path` from the compact build-info; build a standard-JSON input using those paths as
   source-unit names, the project's real remappings, and `optimizer{runs}`, `viaIR`, `evmVersion` copied
   from `foundry.toml`. Request `abi, evm.bytecode, evm.deployedBytecode, evm.methodIdentifiers, devdoc,
   userdoc, metadata, ast`.
2. Run `solc --standard-json` yourself (Windows binary: download `solc-windows.exe` for the exact
   version from the solidity GitHub release).
3. Overwrite `out/build-info/<id>.json` with `{"id", "solcVersion", "input", "output"}`, and delete any
   `<id>.output.json` you created while debugging so the parser uses the real file.

Then `slither . --compile-force-framework foundry --foundry-ignore-compile` works normally.

**Gotcha that silently truncates results:** keep `solcVersion` a **bare** `0.8.24`. Slither's
`incorrect-solc` detector does `int()` on it and dies on `0.8.24+commit.e11b9ed9` with
`ValueError: invalid literal for int() with base 10: '24+commit'` — and it dies *after* several detectors
have already printed, so a truncated run is easy to mistake for a complete one. Distinguish the two by
the run's **final summary line** (`analyzed (N contracts with M detectors), K result(s) found`): present
= complete; a traceback instead = incomplete.

Also: `slither` can exit **127 while the analysis fully succeeded** — do not discard the run on `$?`.
Verify by the summary line + the `--json` artifact.

---

## 2. Fuzzer invocation that bypasses the build-info entirely

`echidna` compiles a single harness file directly, so a vendor's own property harnesses run unmodified:

```bash
echidna test/echidna/X.sol --contract X --test-mode property --test-limit 4000 --seq-len 100 \
  --crytic-args "--compile-force-framework solc --solc-remaps @openzeppelin=node_modules/@openzeppelin"
```

⛔ **Four invocation traps that each cost a failed run (Klima Protocol, 2026-11). Get all four right
the first time:**

1. **`--compile-force-framework solc` takes a FILE, not a directory.** `echidna . …` →
   `'. is a directory. Expected a Solidity file when not using a compilation framework.'` Always pass
   the harness path: `echidna contracts/harness/H.sol --contract H …`. This is also the *whole fix* for
   the forge ≥1.7 build-info breakage (section 1) — no build-info synthesis needed if you fuzz a single
   file.
2. **The flag is `--crytic-args` on echidna, NOT `--compile-force-framework` directly.** echidna 2.3.3
   rejects a bare `--compile-force-framework` with `Invalid option`; its `--help` lists `--crytic-args`
   and nothing else for this.
3. **`--solc-remaps` must be ONE comma-separated argument.** Space-separated remaps are parsed as
   positional file args:
   `error: unrecognized arguments: forge-std/=lib/forge-std/src/ @prb/math/=… H.sol`.
   Correct: `--solc-remaps a/=x/,b/=y/,c/=z/` (trailing comma fine).
4. **A fork harness needs `rpcUrl` + `rpcBlock` in the CONFIG, not just `--rpc-url`.** Without them
   echidna deploys on a fresh local chain where the target's tokens do not exist, and the harness
   constructor's first `approve` reverts with
   `Deploying the contract … failed (revert, out-of-gas, …)`. Put in `echidna.yaml`:
   ```yaml
   testMode: property
   testLimit: 30000
   seqLen: 60
   rpcUrl: "https://<archive-rpc>"
   rpcBlock: <pinned block>
   ```
   And **do not approve in the constructor** — approve lazily inside the fuzz action, or the deploy
   itself is the failure.

Working end-to-end invocation (fork harness, 125-source viaIR project, Windows + echidna 2.3.3):
```bash
echidna contracts/harness/H.sol --contract H --config echidna.yaml --test-mode property \
  --crytic-args "--compile-force-framework solc --solc-remaps @openzeppelin/=lib/openzeppelin-contracts/,@openzeppelin-upgradeable/=lib/openzeppelin-contracts-upgradeable/,forge-std/=lib/forge-std/src/,@prb/math/=lib/prb-math/src/,libraries/=src/libraries/,interfaces/=src/interfaces/"
```
Result shape to expect: `tests: 0/5, fuzzing: 30131/30000`, then one `echidna_<name>: passing` line per
property, then `Saving RPC cache to echidna-corpus/rpc-cache-<block>.json`. The RPC cache makes reruns
fast — keep it.

**Harness must live where crytic compiles it.** For a `src`/`test` Foundry layout, put the harness under
`contracts/harness/` (a real directory in the project). A harness in `test/` is not compiled by the
`--compile-force-framework solc` path and surfaces as `no property found` / `contract not found`.

**mythril on a viaIR project: flatten, then feed `--solc-json` the SETTINGS object directly.**
`myth analyze src/X.sol` dies on remappings (it has no `--solc-remaps` flag, and `--solc-args
"--base-path …"` hits `Ambiguous import` when a nested OZ copy exists under
`lib/*/lib/openzeppelin-contracts/`). Working path: `forge flatten src/X.sol > flat/X.flat.sol`,
rewrite the multi-version pragma to a single version, then
`myth analyze flat/X.flat.sol --solc-json myth_solc.json` where the JSON is the settings object
**unwrapped** — `{"remappings":[],"optimizer":{"enabled":true,"runs":700},"viaIR":true}`. A `"settings"`
key wrapper fails with `Solc experienced a fatal error. Unknown key "settings"`, and `--via-ir` inside
`--solc-args` fails with `The following options are not supported in the current input mode: --via-ir`.
Expect mythril's output on a flattened viaIR file to be **shallow** — on CarbonClassVault it reported
only 3 SWC-101 "internal compiler generated code" hits on OZ `decimals()/totalSupply()/approve()` and
never reached the swap/retire accounting. Label that a weak-coverage result, not a clean sweep.

Notes that cost time when missed:

- **Property-prefix trap.** echidna collects `echidna_*()`; medusa's property mode collects
  `property_*()`. A vendor suite written for echidna therefore yields **0 properties** under medusa —
  running it proves nothing and its green output is meaningless. Check the prefix before budgeting time.
- **medusa 1.5.1 has no `--crytic-args` CLI flag**; crytic args live in the config file.
- **Coverage caveat to read with the green ticks.** echidna logs
  `Running slither failed. Echidna will continue, however fuzzing will likely be less effective.` when its
  slither-guided fuzzing is off. Grep every log for that line: in one 16-harness batch it appeared in
  exactly **one** harness (15 ran guided). A degraded run is "no counterexample in a degraded campaign",
  **not** "the invariant is safe" — and a rerun of the same file reproduced the failure deterministically,
  proving it was the file + echidna's internal invocation, not memory pressure (slither run *directly* on
  that file analysed it fine).
- Do **not** derive a severity mix from slither's console output — it carries no `Impact:` field, so
  counting High/Medium there is a formatting artefact, not a measurement. Use `--json` and parse it.

---

## 3. halmos: the viaIR thrash trap

Adding a test file that imports a vendor's whole echidna suite forces a recompile of the entire test unit.
On a `viaIR = true` project (>100 sources) that can swap-thrash for 30+ minutes while writing **zero**
artifacts.

Detect before waiting: `find out -name '*.json' -newermt '-5 minutes' | wc -l` — `0` new artifacts plus a
pinned CPU means it is not progressing, it is thrashing. Kill it, drop the vendor-suite import (use a
minimal self-contained harness), and record the aborted run as a **tooling GAP with the cause** — never as
a clean result. Kill orphaned children too (`solc-*.exe`, `forge.exe` survive the parent and keep the box
saturated).

Good pattern when it *does* run: reuse the vendor's own harness instead of authoring a spec —
drive their `action_*` functions with symbolic arguments and assert their `echidna_*` properties, wrapping
each action in `try/catch` so an infeasible symbolic input is not counted as a revert-counterexample.

---

## 4. Comparing a deployed contract to a source tree — compare the CODE SECTION, not the length

Never treat a bytecode-length difference as proof that the deployed build differs from the source.

Solidity appends CBOR metadata that embeds the **source paths of the contract's dependency closure**. A
build whose paths are `project/contracts/...` (the usual verifier-db layout) is *longer* than one using
`contracts/...` with byte-identical code. On SSV Network this manufactured a fake "+231 bytes of
unexplained live code" that collapsed to **0 differing bytes** once the tree was recompiled with its
original paths + `npm/@openzeppelin@4.9.6` + `forge-std@1.9.4`.

Procedure:

1. Recover the live source from `https://eth.blockscout.com/api/v2/smart-contracts/<ADDR>`
   (`source_code`, `additional_sources[]`, `compiler_settings` with remappings/viaIR/optimizer runs).
2. Recompile that tree with those exact settings and its original paths.
3. Compare `deployedBytecode` vs `cast code <ADDR>`. **Equal length + code section identical + only the
   trailing metadata hash differing = same code.**
4. If the code section genuinely differs, pin the deployed build's branch before writing anything up:
   `git ls-remote --heads origin`, then per candidate `git diff --stat <audited-commit>..<branch> -- contracts/`.
   On SSV the whole live-vs-audited delta was `main` + **10 lines** living in a public `deploy/hotfix`
   branch — worth knowing before claiming "the deployed code is unaudited".

Related trap: a contract that does **not** use a given constant or library still verifies against a source
tree carrying a *different* version of it, so a module's own verification bundle can contain stale copies
of files it does not affect. Only files that change that contract's codegen are evidence.

Path trap on Windows/MSYS: `curl -o /tmp/x` (a Windows binary) writes `C:\tmp\x` while `head /tmp/x`
(MSYS) reads `/tmp/x` — so you can read a **stale file from an earlier write
and mistake it for this response's body**. Use explicit or relative paths for anything you then read back.

---

## 5. Proving "no hidden functions / no backdoor" — two-directional selector diff + facet collision + immutable audit

When the operator says "decompile it, there must be a bug" and the contracts are **verified**, the
decompiled source IS the Basescan-verified source IS the repo — so re-decompiling is redundant. What
actually matters is proving the *bytecode* is faithful. Four independent checks, all cheap (Klima Protocol
2026-11, 33 contracts / 4 diamonds, all confirmed clean):

### 5a. TWO-directional selector diff (the one-directional diff misses hidden functions)

The existing `deployed_vs_source_selector_diff.py` answers "is every source function deployed?" (`missing
= src - live`). It does NOT answer "does the deployed bytecode expose any function the source doesn't?"
(backdoor / hidden function). Run both directions:

```python
import subprocess, re
def push4(code):  # every PUSH4 (0x63) in runtime bytecode
    s=set(); b=bytes.fromhex(code[2:])
    for i in range(len(b)-4):
        if b[i]==0x63: s.add(b[i+1:i+5].hex())
    return s
src = {m.group(1) for m in re.finditer(r'\|\s*([0-9a-f]{8})\s*\|',
       subprocess.run(['forge','inspect',C,'methodIdentifiers'],capture_output=True,text=True).stdout)}
live = push4(subprocess.run(['cast','code',ADDR,'--rpc-url',RPC],capture_output=True,text=True).stdout.strip())
print("missing(src-live):", sorted(src-live), "extra(live-src):", sorted(live-src))
```

- `missing` (src − live) **≠ 0** = source function absent on chain → patched/hot-fixed deployment, or a
  source tree ahead of the live build. Pin the deployed branch before any claim (see section 4).
- `extra` (live − src) is **almost entirely false positives**. Known taxonomy, triage don't re-derive:
  - `4e487b71` = `Panic(uint256)` error selector (solidity checked-arithmetic).
  - `a9059cbb`/`23b872dd`/`095ea7b3`/`70a08231`/`18160ddd` = ERC20 `transfer`/`transferFrom`/`approve`/
    `balanceOf`/`totalSupply` — selectors of *called* interfaces, not own functions.
  - `4300081c` ("stor"), `74696f6e` ("tion"), `ea8e4eb5`, and bare masks `ffffffff`/`40000000`/`08000000`/
    `10000000`/`04000000`/`02000000`/`01000000`/`80000000`/`ff000000` = constants / string fragments that
    happen to be `PUSH4`.
  - `565bXXXX`, `00000000`-patterns = memory-layout offsets in code, not selectors.
  A *real* hidden function would add a new branch to the dispatcher; if bytecode length matches the source
  AND `missing == 0`, that cannot happen — `extra` is then necessarily all noise.

### 5b. Diamond facet SELECTOR COLLISION (Critical if present)

Two facets of one EIP-2535 diamond registering the same 4-byte selector = the first registration wins and
the second facet's function is shadowed → facet hijack / divergent dispatch. Check every diamond:

```bash
cast call <DIAMOND> 'facets()((address,bytes4[])[])' --rpc-url <RPC>
# parse the ((address,bytes4[])[]) tuple; count each selector, flag any selector seen on 2+ facets
```
Klima result: AAM 63/63, StakingManager 102/102, RewardManager 150/150, RA 30/30 — all unique, 0 collision.

### 5c. Immutable audit — the one thing source-reading can't catch

`forge inspect <C> deployedBytecode` zeroes immutables, so the ~50–200 differing bytes in a byte-length
match are the immutables + trailing CBOR metadata. Grep the source for security-relevant immutables and
confirm the deployed values are only expected constants, not hardcoded addresses:

```bash
grep -rn "immutable" src/ --include=*.sol | grep -v "lib/"
```
A hardcoded `address immutable admin = 0x…` that is WRONG is a real config bug invisible to the source-read
(because forge's artifact blanks it). On Klima the only immutables were `MAX_DEQUE_LENGTH = 10` (three
reward facets) and OZ UUPS `__self` (the contract's own address) — no admin/treasury/oracle baked in.

Combine 5a+5b+5c into one "faithfulness" block. It is the honest, evidence-backed answer to "decompile it":
for a verified contract, the bytecode === the repo source, with no hidden functions, no facet collision,
and no wrong hardcoded address — proven, not asserted.

### 5d. ⛔ Verify a nested-struct `cast call` decode BEFORE chasing a "config bug"

When `cast call <c> 'getX()((...))'` returns a garbage-looking value that *looks* like a config bug
(e.g. a `baseUnit` of `2.98e47`), **first re-read the struct's field ORDER and TYPES in the source**.
Solidity packs structs in DECLARATION order with EXACT types; a nested struct flattens its members
inline. Getting the tuple shape wrong produces garbage that reads as a real finding but is purely a
decode artifact.

Concrete (Klima 2026-11): `CreditConfig { TokenType tokenType; address tokenAddress;
ConversionConfig conversion; }` with `ConversionConfig { uint64 baseUnit; uint64 tonnesPerUnit;
uint64 precision; }` decodes as `(uint8, address, uint64, uint64, uint64)` = `(1, 0x3446…, 1, 1, 1e18)`
→ each ERC1155 NFT = 1 tonne, correct. Decoding it as `(uint8, uint256, uint256, uint256, address)`
yielded `(1, 2.98e47, 1, 1, 0x0de0…)` — the "2.98e47 baseUnit" and "tokenAddress = 1e18" were both
misaligned, and an hour was nearly spent chasing a phantom wrong-conversion-config finding. **Rule:
whenever a `cast call` tuple value looks nonsensical, the ABI shape is your first suspect, not the
target's config.** Recover the exact struct from the source, re-issue `cast call` with the correct
nested-tuple types, and only then judge whether a value is genuinely wrong.
