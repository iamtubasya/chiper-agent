---
name: onchain-source-recovery
author: RESEARCHER_NAME
description: "Recover and validate a verified smart-contract's source from the chain (Blockscout/Sourcify) when it is absent from the public repo, then run slither + forge tests on it. Use when a vendor documents a contract version (e.g. an upcoming v4.2) that exists in NO public branch but is deployed and verified on a testnet/mainnet."
metadata:
  hermes:
    tags: [security, smart-contract, bug-bounty, recon, blockscout, foundry, slither]
---

# On-chain source recovery + validation

## When to use
- The docs/blog announce a new contract version but the public GitHub branch does not contain it
  (e.g. Superstate Allowlist v4.2: 21 public branches, zero `v4.2/` directory).
- You need the exact audited/deployed artifact, not an old release.
- You must NOT ask the user for the source; recover it yourself.

## Step 0 — collect the addresses from the vendor docs
Pull every deployment address + its label (proxy vs implementation vs oracle) from the docs page.
Regex that works on GitBook text: `([A-Za-z0-9 \-]{3,45}?)\s*-?\s*https?://[^\s]*?(0x[a-fA-F0-9]{40})`.

## Step 1 — resolve the implementation behind a proxy (no API key needed)
ERC-1967 implementation slot = `0xREDACTED_********`

```bash
export PATH="$PATH:/c/Users/WINDOWS10/.foundry/bin"
RPC=https://ethereum-sepolia-rpc.publicnode.com      # works for regular (non-archive) eth_call
cast storage <PROXY_ADDR> 0xREDACTED_******** --rpc-url $RPC
# -> 0x000...000<impl address>
cast call <PROXY_ADDR> "VERSION()(string)" --rpc-url $RPC     # sanity-check you got the right version
```
TransparentUpgradeableProxy also exposes `admin()`; if `VERSION()` reverts on the proxy, you read the wrong slot type.

**Cheaper shortcut — the explorer already resolved it (verified 2026-10-12):** when the proxy is verified, the
proxy's own Blockscout v2 record carries `proxy_type: "eip1967"` and an `implementations: [{address_hash, name}]`
array. One GET on the proxy address therefore yields the implementation address *and* its contract name
(`…V2Proxy` → `…V2Implementation`) with no RPC call, no `cast storage`, and no key. Use the RPC slot read only
when the explorer record has an empty `implementations` list. Rejecting on the returned shape is a good habit:
a proxy record whose `source_code` is ~260 bytes with 6 `additional_sources` is a stub — the logic is always on the
implementation record you must fetch next.

## Step 2 — fetch the verified source (Blockscout API v2, no key)
```bash
curl -s -m 60 "https://<explorer>/api/v2/smart-contracts/<IMPL_ADDR>" -o impl.json
# Sepolia: https://eth-sepolia.blockscout.com
# Mainnet: https://eth.blockscout.com
```
Fields that matter: `name`, `file_path`, `source_code` (flattened, usually one big file), `additional_sources`
(0 entries = fully flattened, self-contained), `abi`, `compiler_version`, `optimization_enabled`,
`optimization_runs`, `evm_version`, `is_fully_verified`, `verified_at`.
Also try Sourcify (`https://sourcify.dev/server/v2/contract/<chainId>/<addr>?fields=all`) — it frequently has
NO match even when Blockscout does, so a Sourcify `match:null` does not mean "unverified".

**Sourcify API shape — the three traps that cost a step each (verified against a mainnet contract):**
- Script against the **v2** endpoint only: `GET https://sourcify.dev/server/v2/contract/<chainId>/<addr>?fields=all`.
  The legacy compatibility path `/server/files/any/<chainId>/<addr>` returns
  **403 `{"error":"This compatibility endpoint is only served to browsers…"}`**, and
  `repo.sourcify.dev/contracts/...` 307-redirects to the `/server/repository/...` form. Neither is scriptable.
- **The source files are a TOP-LEVEL `sources` key — NOT under `compilation`.** Walking
  `payload["compilation"]["sources"]` returns **0 files** and reads exactly like "not verified",
  which is the wrong conclusion and sends you off to another explorer for nothing. Correct access:
  `payload["sources"]` → `{ "<path>": {"content": "<solidity>"} }`.
- Useful siblings, all top-level: `match` (`"match"` = full match), `runtimeBytecode.onchainBytecode`
  vs `.recompiledBytecode` (byte-equal ⇒ your recompile is faithful), `immutableReferences`,
  `deployment.deployer`, `deployment.blockNumber` (hex).
A healthy full match yields the contract plus its library files (e.g. a Solady dependency tree);
write each file out preserving its original path so imports and remappings still resolve.

## Step 3 — prove the source is genuine by recompiling at the EXACT settings
Non-negotiable: same `solc_version`, `optimizer` flag and `optimizer_runs` as the explorer reports. Clean
compile = the flattened source is complete and bytecode-consistent.

```bash
mkdir -p v42/src && cp impl_source.sol v42/src/
cat > v42/foundry.toml <<'EOF'
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc_version = "0.8.28"
optimizer = true
optimizer_runs = 1000000
EOF
cd v42 && forge build --build-info
```

## Step 4 — slither it
```bash
slither . --foundry-ignore-compile > ../../tool-evidence/slither-<name>.txt 2>&1
grep -oE "^Detector: [a-z-]+" <out> | sort | uniq -c | sort -rn
```
`--build-info` first is mandatory: crytic needs a build-info json that has an `output` key, otherwise it
looks for a sibling `<id>.output.json` and dies with FileNotFoundError.

## Recipe that works on a FLAT explorer dump (no foundry, verified 2026-10-12)

Not every engagement needs a mini foundry project. When the explorer hands you `source_code` + 
`additional_sources[]` and you only want static analysis, reconstruct the tree and point slither at the entry file:

```python
# 1) reconstruct: source_code goes to its file_path, every additional_sources entry to its own path
for fp, src in [(rec["file_path"], rec["source_code"])] + \
               [(s["file_path"], s["source_code"]) for s in rec.get("additional_sources") or []]:
    (root / fp).parent.mkdir(parents=True, exist_ok=True)
    (root / fp).write_text(src, encoding="utf-8")
#    -> @openzeppelin/... lands as a LITERAL directory, which is exactly what the imports expect
```
```bash
solc-select install 0.8.24 && solc-select use 0.8.24        # the version the explorer reports
cd <root>
slither contracts/<path>/<Contract>Implementation.sol \
        --solc "C:/Users/<u>/AppData/Local/Programs/Python/Python314/Scripts/solc.exe" \
        --filter-paths "openzeppelin"
# → INFO:Slither:… analyzed (24 contracts with 102 detectors), 4 result(s) found
```

Shape rules that made it work, and the counters to watch:
- **A bare `slither .` on the reconstructed directory analyses 0 contracts** and prints
  `No contract was analyzed` — a directory with no `foundry.toml`/hardhat config is not a project. Point at the
  `.sol` file; the literal `@openzeppelin/` dir next to it satisfies the imports.
- Run **from the root**, pass the target as a root-relative path (trap 10 above).
- Read the closing summary line, never the exit code: `analyzed (N contracts with M detectors), K result(s)`.
  `N=0` means the setup is wrong, not that the contract is clean (trap 15).
- Judge scope by the detector list: on 6 Vana implementations the only results were
  `block-timestamp` in an `isActive()` view and three naming-convention nits — i.e. the automated layer was clean
  and the finding that mattered came from reading the money path (`settle`/`_payout`) by hand. Static analysis
  that reports nothing structural is a prompt to read the privileged functions yourself, not a verdict.

### Triage every detector before a result count becomes a claim

Vana escrow (`DataPortabilityEscrow`, 22 results across 9 detector classes, 2026-10-12). The mapping
that made the report honest — do this table for every detector, not just the scary one:

| Detector | Verdict | Why |
|---|---|---|
| `arbitrary-send-eth` | **TRUE, by-design role** | `_payout` sends native value to a caller-supplied `to`, but every entry point is `onlyRole(FACILITATOR_ROLE)` → this *is* the finding (a facilitator key can redirect any funded account's balance), not a second bug |
| `reentrancy-balance`, `reentrancy-benign` | **FALSE POSITIVE** | the flagged functions are `nonReentrant`; the `balanceBefore`/`received` delta is deliberate fee-on-transfer accounting |
| `incorrect-equality` | by design | `received == 0` is the zero-received guard |
| `calls-loop` | informational | the `_payout` loop can revert a batch, but the batch is built by the privileged caller — no unprivileged griefing path was demonstrated |
| `assembly`, `low-level-calls` | by design | revert-data bubbling; `(target, selector)` allowlisted call |
| `unused-return`, `naming-convention` | cosmetic | EnumerableSet return values; `*_TYPEHASH` constants |

Write the table into the findings file (`coverage_b.contracts.slither_triage`) with the raw detector
name and the reason for each verdict. It is the difference between "we ran slither" and "we reviewed
the 22 results", and it is what lets you state "no contract-level vulnerability beyond X" without
over- or under-claiming.

### A policy sentence in the docs is not an enforced invariant — check the role-gated functions

The same engagement's documentation said the settlement operator *"can collect only fees an account
has funded and **cannot redirect balances**"*. On-chain, `settle(from,to,…)` / `settleBatch` /
`runOpAndSettle` were `onlyRole(FACILITATOR_ROLE)` with **no binding between `to` and the fee
recipient** and no per-account owner check — the guarantee lived in the gateway's policy, not in the
contract. For any custodial / escrow / "operator can only do X" contract: read every balance-moving
function and ask *"what does the key holder NOT have to prove?"* Then report the mismatch at its
honest severity (usually Low: defence-in-depth or documentation accuracy, and explicitly note it is
not reachable unauthenticated) instead of inventing an exploit that requires the key to be stolen.

## Pitfalls (all hit for real)

1. **`slither <file.sol> --solc 0.8.28` fails** with `[WinError 2]` — crytic treats `0.8.28` as an
   *executable name*. Do NOT try to fix by pointing at a solc binary; build a mini foundry project (Step 3)
   and run `slither .` instead.

   **Refinement (verified 2026-10-12, Vana DataPortability implementations):** a **native Windows path to a real
   `solc.exe` IS accepted by `--solc`** and is the fastest route when you only have a reconstructed directory tree
   (no foundry project at all). Three variants, only the middle one works:

   | `--solc` value | result |
   |---|---|
   | `0.8.28` (bare version) | `InvalidCompilation: [WinError 2]` — treated as an executable name |
   | `/c/Users/<u>/…/Scripts/solc.exe` (MSYS path) | same `WinError 2` — Windows Python cannot exec the MSYS path |
   | `C:/Users/<u>/AppData/Local/Programs/Python/Python314/Scripts/solc.exe` (**native path**) | ✅ `analyzed (24 contracts with 102 detectors)` |

   The `Scripts/solc.exe` shim honours `solc-select use <version>`, so match the compiler the explorer reports
   (`solc-select install <ver> && solc-select use <ver>`) before pointing at it. Also: this slither build's
   argparse has **no `--solc-select` and no `--base-path`**, and `--filter-paths` is mutually exclusive with
   `--include-paths` — passing either pair aborts before compilation.
   The foundry route (Step 3) is still the right answer for multi-file projects with remappings; the `--solc`
   route is the answer for a flat explorer dump.
2. **foundry auto-remap trap.** Once `<lib>/src` exists, foundry remaps `<libname>/` -> `<lib>/src/`, so an
   import like `chainlink/src/v0.8/...` resolves to `chainlink/src/src/v0.8/...`. If you "fix" it by creating
   that dir, foundry re-detects and asks for a THIRD `src`. Correct fix: an explicit `remappings.txt` at the
   project root pointing at a directory that does NOT contain `src/`
   (e.g. `chainlink/=lib/chainlink-dep/` with the file at `lib/chainlink-dep/src/v0.8/...`).
   Explicit `remappings.txt` entries DO win over auto-remappings — verified.
3. **chainlink `AggregatorV3Interface.sol`**: the `develop`/`master` raw paths 404. Use a release tag:
   `https://raw.githubusercontent.com/smartcontractkit/chainlink/v2.14.0/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol`
4. **Empty submodules.** Public mirrors ship `lib/*` as empty dirs. `git submodule update --init --depth 1 <paths>`
   works; for nested/circular refs (repo A -> lib/B -> lib/A) just copy the sibling `src/` into the nested path
   instead of recursing. `lib/forge-std/lib/ds-test` needs `dapphub/ds-test` cloned or nothing compiles.
5. **Fork tests need an ARCHIVE node.** Telltale: `[FAIL: EVM error; database error: failed to get account for 0x...]`.
   - `ethereum-rpc.publicnode.com` -> `-32602 Archive requests require a personal token`
   - `rpc.flashbots.net` -> `state at block #N is pruned`
   - `eth.llamarpc.com` -> HTTP 525; `cloudflare-eth.com` -> -32603; `rpc.ankr.com/eth` -> needs a key
   - **`https://eth.drpc.org` works** (and `eth-mainnet.public.blastapi.io`).
   Quick probe before a long run:
   `curl -s -X POST -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_getStorageAt","params":["0x<some contract>","0x0","0x1"]}' <rpc>`
   An error response = no archive; a value = usable. NEVER record a fork test that died on the provider as a
   target negative — it is `NO RESULT / re-run pending`.
6. **Enumerable the real env var name per repo** (`ETH_RPC_URL` vs `RPC_URL`) — they differ between Superstate's
   two repos and both just surface as `vm.envString: environment variable "X" not found`.
7. **Do not edit upstream source files** to make a build pass. Only add `remappings.txt` / seed empty
   submodule dirs, and say so in the engagement log. If a test imports a weird nested path
   (`../../lib/ustb/lib/onchain-redemptions/src/interfaces/X.sol`) while its sibling test imports the normal
   `src/interfaces/X.sol`, that is a copy-paste artefact — seed the path, don't "fix" the test.
8. **Two jobs pointed at the SAME evidence path can clobber each other.** The first attempt here
   (`slither <file>.sol --solc 0.8.28`, which fails with WinError 2) and the working mini-project run both
   wrote `tool-evidence/slither-<name>.txt`. Had the failing run finished LAST, the "clean" evidence file
   would have contained a Python traceback and a negative verdict would have been reported off a crash.
   Rules that follow:
   - Give each attempt its own filename (`...-attempt1.txt`) or run them sequentially, never concurrently
     into one path.
   - After any rerun into an existing path, re-verify the body BY CONTENT MARKER + mtime, never by the
     order in which completion notifications arrive:
     `wc -c f; grep -c "WinError 2\|Traceback" f`  (must be 0)  and  `grep -c "analyzed ([0-9]* contracts" f` (must be 1)
   - A background completion notification can arrive long after the job actually finished (and after a
     later job already overwrote its output), so notification order is NOT execution order.

## Making a recovered source ACTUALLY analysable (5 traps, all hit for real 2026-10-08)

Recovering the source is only half the job. A Sourcify/Blockscout dump keeps the original import
prefixes as **literal directories** (`@openzeppelin/…`, `solady/…`, a nested `lib/`), and the naive
way of feeding it to slither/aderyn/myth/echidna/medusa fails in five different places — each one
silently producing "no findings" rather than an error you'd notice.

Real numbers from the relay.link v3 Router (`RelayRouterV3.sol`, 13 source files): naive setup gave
**6 trivial findings on a helper library**; after these five fixes, **68 findings on the actual
contract** (1 High, 2 Medium). Same source, same tools.

9. **`rglob("*.sol")[0]` picks the WRONG contract.** Directory-walk order is arbitrary, so a
   `sol-source/` dump with `src/common/Multicall3.sol` + `src/v3/RelayRouterV3.sol` hands the tools
   the *helper*. Symptom: slither reports a handful of nothing-burgers on a file you didn't mean to
   scan, and echidna/medusa die with `ABI is empty` / `no assertion … to find to fuzz`.
   Fix: score candidates — prefer a file whose path is NOT under
   `common|lib|interfaces|test|script|mock|node_modules|openzeppelin|solady`, then prefer the
   largest, and honour an explicit `sol-target.txt` pin if present. Always log which file won and
   how many were skipped, then **check the evidence header** (`# COMMAND:`) to confirm the tool
   really got the intended path.

10. **Run every SC tool from the PROJECT ROOT with remappings — never from the `.sol`'s directory.**
    `cd <dir-of-file> && slither <name>` breaks every `import "@openzeppelin/…"` because the prefix
    lives at the root. Symptom: a compile error pointing at the first `import` line of the contract.
    Fix: pick the nearest ancestor that CONTAINS the import prefixes, write a `remappings.txt`
    there (`@openzeppelin/=<root>/@openzeppelin/`, `solady/=<root>/solady/` — only for dirs that
    exist), and pass the target as a path relative to that root.

11. **`foundry.toml` with `src = "."` makes forge overflow its stack.** `forge clean` /
    `forge config --json` die with exit `3221225725` (0xC00000FD) and `thread '<unknown>' has
    overflowed its stack`, because forge walks `lib/` and the dump's nested duplicate package dirs.
    Fix: `src = "src"` when a `src/` exists, `libs = ["lib"]`, and drop `out` out of the walk.

12. **crytic-compile's Foundry backend REQUIRES `out/build-info`.** Without a prior build, slither
    fails with `Compilation failed. Can you run build command? … out/build-info is not a directory`.
    Fix: run `forge build --build-info` (at the project root) during setup — not as an afterthought.
    Also delete stale `crytic-export/`, `crytic-compile.json`, `combined_solc.json` first, or
    crytic-compile complains `Multiple frameworks detected: Foundry, solc, Solc-json` and can pick
    the wrong one.

13. **Do NOT add `offline = true` to the generated `foundry.toml`.** It looks like a sane
    hardening step and instead kills the build with
    `can't install missing solc 0.8.28 in offline mode`. Let forge fetch the compiler once.

14. **Per-tool flags that are NOT optional** (each one silently degrades to "nothing to
    analyse" if omitted):
    - echidna → `--contract <Name>`  (else: `No bytecode found for contract <path>`, because
      it treats the path as a contract name)
    - medusa  → `--target-contracts <Name>` — **plural**. The singular `--target-contract`
      does not exist (`unknown flag`); without the plural it dies with
      `Failed to initialize the test chain / specify target contract(s)`.
    - mythril → keep the WSL quoting SIMPLE. An over-escaped nested `\\\\\"` truncates the
      path and yields `FileNotFoundError` on a half-written name; use
      `bash -lc "cd <root> && SOLC=<solc> myth analyze <rel> …"`.
    - aderyn  → runs in WSL, so it needs the **`/mnt/c/...` form of the root** and the
      RELATIVE remappings (trap 3 in the other list); an absolute `C:/...` target makes it
      fail with `Compilation Error … Source "C:/…" not found`.

15. **A smart-contract analyser exits NON-ZERO when it WORKS.** slither exits 1 when it
    detects anything, and echidna/medusa exit non-zero when an assertion FAILS — which IS
    the finding. Judging status by exit code alone recorded a successful, 68-finding slither
    run as `RAN_WITH_ERROR` (found 2026-10-08). Decide by COMPLETION MARKER in the body
    instead: `analyzed (`, `result(s) found`, `running 88 detectors`, `report printed`,
    `total calls`, `assertionfailed`, `test(s) passed`, `test summary`, `fuzz: elapsed`,
    `analysis was completed`. Marker ⇒ `EXECUTED`, whatever the exit code.

16. **Killing the orchestrator does NOT kill its grandchildren on Windows.** The
    `force-full-execution` child survives the parent, runs to completion, and writes
    `force-state-<target>.json` with `status=complete`. The next run then prints
    `STEP 1: SKIP force-full-execution` and analyses NOTHING — while the evidence it
    should have produced was already deleted. The gate catches it as
    `Evidence files missing for: ['slither', 'aderyn', …]`. Before any re-run:
    `taskkill /F /T /PID <pid>` over the whole tree AND delete the state file, or the
    run is a silent no-op.

17. **BEFORE blaming resources: prove the run actually ended.** An earlier version of this item
    claimed a set of runs were "killed for MEMORY". That was **wrong** and it cost the operator
    real time. The runs had been *completing* — the log was being sampled mid-flight (through a
    `| tee` pipe, which holds output), looked stalled at `1.4a`/`C6`/`C6b`, and was narrated as a
    death. The full log showed `… → 0D gate → 3 attempts → HARD BLOCK → === EXIT 0 ===`.

    ```
    grep -c "=== EXIT" <log>   # 0  -> STILL RUNNING. Do not diagnose. Wait.
    ```

    A log that stopped growing is not a corpse; the only proof of termination is the exit
    sentinel or the absence of the process. Only *after* that is the death-shape meaningful:
    same step every time = code defect; different step with no traceback = external kill.
    "Still running" is a valid answer and beats a confident wrong one.

    Memory on a small host *is* still worth managing as **hygiene before** a heavy SC run —
    WSL `vmmem`, browsers, and **orphaned `nuclei`/`sqlmap` from previously-killed runs** are the
    big consumers (`~/.wslconfig` `memory=1024MB` + reap orphans). Just do not record it as the
    cause of a death you never confirmed.

    **Corollary for a *pipeline* (not just a build):** the orchestrator captures its child's
    stdout, so during `force-full-execution` the run log legitimately receives **no new lines for
    ~12 minutes**. Judge liveness by the **artefact directory** growing (`tool-evidence/*`,
    `tools-usage.json` entries), not by log growth. A static log with fresh evidence = working.

**Sequencing that works:** resolve source → write `remappings.txt` + `foundry.toml` → `forge build
--build-info` → then slither / aderyn / myth / echidna / medusa, all from the root.

**Verify the setup once by hand before re-running a long pipeline.** Run slither directly against
the prepared project and confirm it prints `… analyzed (N contracts with M detectors), K result(s)`.
If K is 0 or the `# COMMAND:` line names a helper file, the setup is wrong — fix it there, not after
a 20-minute pipeline run.

## Support files

- `references/sc-project-prep-and-tool-traps.md` — **read before running any SC tool on a
  recovered dump.** The traps that make slither/aderyn/myth/echidna/medusa report
  "complete" while analysing the WRONG FILE or nothing at all: `rglob("*.sol")[0]` picking a
  helper library, missing (or ABSOLUTE!) `remappings.txt` for `@openzeppelin/`+`solady/`,
  `src="."` causing a forge stack overflow (exit `3221225725`), crytic needing a pre-built
  `out/build-info`, `offline=true` blocking the solc download, stale crytic artefacts, the
  two mandatory per-tool flags (`echidna --contract`, `medusa --target-contracts` — plural),
  why `RAN_WITH_ERROR` is not automatically a failure, and the re-run no-op (kill the whole
  process tree + the state file or the next run skips the SC step entirely). Includes the
  known-good generated `foundry.toml` and the per-tool invocation table (Windows + WSL split).
  Proven: 6 cosmetic results on the wrong file → 68 results on the right one.
- `templates/allowlist-live-fork-test.sol` — ready-to-copy Foundry fork test for a recovered, signature-gated
  allowlist/permission contract: default-deny assertion, non-owner rejection, bogus-signature + wrong-nonce +
  expired-deadline rejection, "nonce not burned on failure", caller-restricted V3-compat reads, and the decisive
  symbol-spoofing test (a contract whose `symbol()` matches the real token must read only its OWN namespace).
  Verified 9/9 PASS against a live deployed v4.2 proxy.
- `references/` cross-ref — for the bytecode-analysis fallback and scanner-severity triage
  (`myth analyze -f`, selector attribution with `cast sig`, honest severity vocabulary) see the
  `audit-execution-discipline` skill, `skills/security/audit-execution-discipline/references/evm-and-recon-triage-2026-10-01.md`.

## If source-level analysis is blocked, analyse the DEPLOYED bytecode

Recovering the source can still leave you unable to run source-level tooling (mythril failing on imports,
remappings it silently ignores). Do not stop there and do not report "clean" — pivot to the artifact that
actually matters, the deployed runtime bytecode:

```bash
RPC=https://ethereum-rpc.publicnode.com
cast storage <PROXY> 0xREDACTED_******** --rpc-url $RPC  # impl
cast code <IMPL_OR_NONPROXY_ADDR> --rpc-url $RPC > target_deployed.hex
wsl -d Ubuntu -- bash -lc "myth analyze -f target_deployed.hex --execution-timeout 240 \
  --solver-timeout 20000 -t 1 --no-onchain-data"
```

Always pass `--no-onchain-data` on a third-party target, and bound the run — unbounded symbolic execution on a
~10 KB contract will not finish. **Attribute every finding to a real function before judging it**: mythril prints
the calldata it used, so resolve the 4-byte selector with `cast sig "<candidate signature>"`. A finding on a
one-shot `initialize(...)` is a different conversation from one on the live money path.

8. **When source-mode compilation keeps failing, analyse BYTECODE — and prefer the DEPLOYED bytecode.**
   mythril's `--solv 0.8.28` tries to download solc from `solc-bin.ethereum.org`, a **deprecated host** (Solidity
   moved to `binaries.soliditylang.org`), so it dies with a DNS error on machines that can't reach it. Fix:
   export a local compiler instead of asking for a version — `SOLC=/home/windows10/.local/bin/solc myth analyze
   <file>.sol` (WSL has 0.8.28). If imports still fail because mythril does not apply `--solc-json` remappings,
   stop fighting the compiler and switch to bytecode:
   ```bash
   cast code <ADDRESS> --rpc-url <rpc> > target_deployed.hex        # the REAL runtime bytecode
   cast storage <PROXY> 0xREDACTED_******** --rpc-url <rpc>
   # -> implementation address; then cast code that for a proxy-hosted contract
   myth analyze -f target_deployed.hex --execution-timeout 240 --solver-timeout 20000 -t 1 --no-onchain-data
   ```
   Bytecode mode has no source maps so `Function name:` is meaningless ("constructor" for everything) — attribute
   each finding by RECOMPUTING THE SELECTOR of the calldata mythril prints:
   `cast sig "candidateFunction(type,type)"` for each name in the ABI, and match the leading 4 bytes. That is how
   a `SWC-101 High` was pinned to `initialize(address,uint256,address,uint256)` (`e24df754`) rather than the money
   math, which is what made correct triage possible.
   Keep `--no-onchain-data` so the symbolic executor does not call out to RPC endpoints you did not intend.

## Support files
- `templates/allowlist-live-fork-test.sol` — live fork-test template for a recovered, signature-gated permission
  contract (default-deny check, auth checks, nonce/expiry checks, the symbol-spoofing differential test).
- `references/foundry-poc-and-harness-recipes.md` — isolated-project setup, `allow_paths`, proxy-deploy patterns,
  `abi.encodeCall` / payable-fallback / checksum compile traps, and the 3-test shape for an "unguarded initializer
  input" finding that decides High vs QA.

## Reporting what this gives you
- Saved source + ABI + the compile-config proof = you can now read the artifact the vendor has NOT published.
- Manual review checklist for signature-authorized writes (`setAllowedWithSignature`-style):
  typehash matches the encoded struct; digest = `keccak256(0x1901 || domainSeparator || structHash)`;
  domain = (name, version, chainId, verifyingContract); nonce scope and increment direction; the ECDSA lib
  reverts (OZ 5) vs returns address(0) (old) on a malformed signature; replay across chain/contract/upgrade.
- Also check: is the domain separator CACHED at init and only rebuilt on chainid/self change? Then after an
  in-place upgrade it keeps the init-time `version` string while `VERSION()` reports the new one — an
  integration footgun (signers must read `DOMAIN_SEPARATOR()`), not an exploitable bug.
- A guard built on a string (`symbol()`) rather than on identity is a label check, not an auth check — but
  score it honestly: if the guarded read is scoped to `msg.sender`, there is no privilege escalation and no
  info leak, so it is an observation and NOT a finding.

## Also analyse the DEPLOYED bytecode, not only the recovered source

Once you have the implementation address (Step 1), you can run symbolic execution against the bytecode that is
actually live — often more relevant than the repo, because the repo can be ahead of the deployment.

```bash
cast code <IMPL_OR_CONTRACT> --rpc-url <RPC> > deployed.hex          # runtime bytecode
myth analyze -f deployed.hex --execution-timeout 240 --solver-timeout 20000 -t 1 --no-onchain-data
```
Bound it tightly (`--execution-timeout`, `-t 1`): 7–10 KB of bytecode makes the solver slow. If
`myth --solv <version>` fails because it cannot download solc, pass the local compiler instead:
`SOLC=/home/<user>/.local/bin/solc myth analyze -f deployed.hex ...` (and drop `--solv`).
Bytecode mode cannot name functions — it prints `Function name: constructor` for every hit and gives you a raw
`calldata:` blob. Do not rate it off that label: take the 4-byte selector and match it yourself with
`cast sig "<signature>"`.

## Check VERSION() against the repo before scoping any finding

`cast call <PROXY> "VERSION()(string)"` and compare with the `VERSION` constant in the repo you analysed. If they
differ (Superstate: mainnet `"1.3.0"` vs repo `"4"`), the repository is **unreleased code**. A repo finding is
then only reportable if you (a) reproduce it on the deployed address, or (b) show it affects the vendor's release
plan. State that scoping explicitly in the report — never imply mainnet is affected.

Full recipe (bytecode-mode triage, selector attribution, evidence framing): see the
`audit-execution-discipline` skill, `skills/security/audit-execution-discipline/references/evidence-and-scanner-triage.md`.

## Adjudicate "by design?" from the vendor's own deploy tooling — BEFORE you report

Proven on Superstate 2026-10-01: a finding that looked like a real Low ("a fresh deployment of
SuperstateToken v3/v4 can never acquire an owner, so the token is inert") was withdrawn on evidence, not on
opinion. The PoC was solid — a passing Foundry test proving `owner()` stays `address(0)` and every admin path
reverts — but the *reachability* was the weak point, and reachability is decided by the vendor's own scripts.

Ask these three questions and answer them from the repository, not from the code's natspec:

1. **Is there any script that deploys the affected contract as a NEW instance?**
   ```bash
   grep -rlnE "new <ContractV[34]>|new <Fund>v[34]" script/ deploy/ contract_deployment/ 2>/dev/null
   ```
   Empty result ⇒ that path does not exist in their tooling.
2. **What do the versioned scripts actually execute?** Read the active (uncommented) statements. Here every
   v2/v3 script was named `DeployAndUpgrade*` and performed ONLY
   `tokenProxyAdmin.upgrade(...)` against an existing proxy; the `initializeV2()` step survived as a
   commented-out block annotated `// TODO (though might not use this script anymore...)`.
3. **How does a NEW instance actually start?** `script/v1/DeployScriptV1.s.sol` line 33 showed
   `new USTBv1(admin, wrappedPerms)` — the V1 implementation takes the admin through its **constructor**, so the
   immutable in question is populated for the only implementation that ever runs the migration step. Deploying
   v3/v4 fresh is simply not a supported path.

If the answer is "upgrade-only", the finding is BY DESIGN → **not reportable**. Withdraw the severity claim
explicitly in the engagement log (say what it was, why it died, and keep the PoC as documentation). A false
positive costs more credibility than a withdrawn claim ever will.

Corollary: a natspec line that *describes* a fresh-deploy flow ("If creating an entirely new contract, the
original `initialize` method still needs to be called") is documentation, not proof that the path is reachable.
The scripts are the proof.

> Sibling triage rules for this engagement type (wildcard-DNS FP sweep, S3 `AccessDenied` vs `NoSuchBucket`,
> verifying a vendor's advisory, in-memory malware handling): `bug-bounty` →
> `skills/security/bug-bounty/references/recon-triage-and-vendor-claim-verification.md`.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | `cast code <addr>` → bytecode size + selector census SEBELUM baca repo | Source bisa beda dari deployed; selector yang hilang = kode lebih tua |
| 2 | `cast implementation <proxy>` / EIP-1967 slot read → implementation address live | Proxy bisa sudah di-upgrade setelah repo di-clone |
| 3 | Constructor arg decode dari creation calldata (offset 0 = static args) | Owner/token/admin sering ada di constructor, bukan di source yang kamu baca |
| 4 | Revert-string census dari bytecode (`re.findall(rb'[ -~]{6,}')`) | Nama dev + custom ABI bisa direkonstruksi tanpa source |
| 5 | `eth_getLogs` address-filtered full-range → event history lengkap | Tanpa explorer, event log adalah satu-satunya riwayat transaksi |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## 2026 sweep (recovery yang masih jadi jebakan)

- **Verification-key binding** — zkVM/rollup proof: public input yang tidak di-bind ke VK = proof reuse lintas program. Cek apakah `verifyProof` meng-hash VK ke dalam public input.
- **Squads vs bare-pubkey upgrade authority** — Solana BPFLoaderUpgradeable: authority yang terlihat sebagai pubkey tunggal BUKAN berarti EOA; cek apakah itu program-derived address dari Squads (multisig) sebelum klaim "single-key upgrade".
- **Diamond facet selector collision** — EIP-2535: dua facet mendaftarkan selector sama, yang menang = urutan registrasi. Cek `facetAddresses` untuk selector duplikat.
- **ERC-7579 module registry** — account yang install module dari registry tanpa allowlist = arbitrary code execution atas account. Probe: install module dengan address attacker.
- **Deployed-vs-source selector diff dua arah** — selector ada di bytecode tapi TIDAK di source = hidden function (backdoor); selector ada di source tapi tidak di bytecode = patched on-chain.


## Critical severity anchor (apa yang membuat temuan dari skill ini Critical)

Skill ini menghasilkan *recon*, bukan bug. Yang membuat outputnya Critical adalah kalau recon
mengungkap primitif yang bisa dipakai:

| Temuan recon | Severity kalau terbukti bisa dipakai |
|---|---|
| Selector ada di bytecode tapi TIDAK di source (hidden function) | Critical — backdoor terverifikasi |
| Upgrade authority = pubkey tunggal (bukan Squads/multisig) | High-Critical kalau bisa dipicu attacker |
| Diamond facet selector duplikat | Critical — facet hijack |
| ERC-7579 module registry tanpa allowlist | Critical — arbitrary code execution atas account |
| zkVM public input tidak di-bind ke VK | Critical — proof reuse |
| Constructor arg mengungkap owner/token yang bisa diprediksi | Medium (recon value) |

**Kalibrasi wajib:** recon yang mengungkap "admin adalah EOA" tanpa fund-loss path = Info.
Recon yang mengungkap fungsi tersembunyi yang bisa dipanggil siapa saja = Critical. Selalu
tunjukkan panggilan yang bisa dilakukan penyerang, bukan hanya fakta on-chain-nya.
