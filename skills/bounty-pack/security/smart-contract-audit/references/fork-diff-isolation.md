# Fork-diff isolation — find the *modified* code first (highest-signal DeFi audit technique)

## Why
Most large DeFi targets are forks: **verbatim** upstream code (Morpho Blue,
MetaMorpho, Pendle, Uniswap, Aave, OZ) is battle-tested and almost never where the
bug is. Fira's own diff showed SisuVault = MetaMorpho verbatim, LendingMarket =
Morpho Blue verbatim + 6 declared additions. Reading 16k LOC line-by-line is a
waste; diffing 4 repos isolates the surface in ~15 min.

Rule: **if a file diffs to "only renames/comments", it is NOT the attack surface.
Say so explicitly in the report as a verified negative.**

## Step 1 — clone the upstreams (cheap, do it early, in the background)
```bash
git clone --depth 1 https://github.com/<org>/<repo>.git
# typical lineage for lending/yield protocols:
#   morpho-org/morpho-blue            (LendingMarket/Morpho.sol + libs)
#   morpho-org/metamorpho             (SisuVault/MetaMorpho.sol + PendingLib)
#   morpho-org/morpho-blue-oracles    (ChainlinkOracleV2, ChainlinkDataFeedLib, VaultLib)
#   pendle-finance/pendle-core-v2-public (Market/MarketMathCore, router/math, YT/PT)
```
Upstream version may be NEWER than the fork (e.g. PendleMarketV7 vs FiraMarketV3)
— still useful, but expect churn noise. Say so honestly in coverage notes.

## Step 2 — comment/whitespace-insensitive diff
Raw `diff -u` is useless: header comments and renames dominate. Use:

```python
# sdiff.py <A> <B> [maxlines]
import re, sys, difflib
def norm(p):
    s = open(p, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return [l.strip() for l in s.split("\n") if l.strip()]
A, B = norm(sys.argv[1]), norm(sys.argv[2])
print(f"### A={len(A)} B={len(B)}")
for l in difflib.unified_diff(A, B, lineterm="", n=2)[:int(sys.argv[3]) if len(sys.argv)>3 else 400]:
    print(l)
```
Then read ONLY the `+` lines that are logic (skip import blocks / renames).

## Step 3 — enumerate the modifications, then attack only those
Produce an explicit list, e.g. for a Morpho fork:
```
ltv / isLtvEnabled / _isHealthyLTV      <- new borrow+withdraw guard
marketConstants (grace, liqIncentive)
whitelist check inside supply()
uslLiquidator + modifier                <- DECLARED BUT UNUSED (dead code)
_liquidatePostMaturity + liquidateExpiredBt   <- new post-maturity path
getUserPosition (view helper)
liquidate() itself = unmodified Morpho (incl. bad-debt write-down)
```
Anything marked "unmodified upstream" gets one line in the negatives, not a
paragraph.

## Pitfalls learned
1. **Merge collisions when building the project from block-explorer sources.**
   Two contracts can share the same `file_path` with *different* content
   (FiraLendingMarket vs VariableLendingMarket both pointed at
   `lib/fira-lending-market/src/lending_market/LendingMarket.sol`, 761 vs 762
   lines). Verify which copy is deployed by re-fetching the source for the
   specific address and comparing to your local file — do not trust the merged
   tree.
2. **Blockscout has no API key requirement** and returns everything needed:
   `GET https://eth.blockscout.com/api/v2/smart-contracts/{addr}` ->
   `source_code`, `additional_sources[]` (with real repo paths), `file_path`,
   `compiler_version`, `evm_version`, `optimization_runs`, `proxy_type`,
   `implementations`, `constructor_args`. Rebuild the tree at the real
   `file_path`s + union of `additional_sources`, then add remappings:
   `@openzeppelin/contracts/`, `@openzeppelin/contracts-upgradeable/`, plus the
   project's own (`@lending-market/` -> `lib/<name>/src/`).
3. Forked routers often need `via_ir = true` (ActionAddRemoveLiqV3 hits
   "Stack too deep" otherwise). Set it in the first foundry.toml, not after.
4. Verify diamond-ish storage claims instead of trusting comments:
   recompute ERC-7201 slots with cast:
   `cast keccak $(cast abi-encode "f(uint256)" $(python -c "print(hex(int(<keccak>,16)-1))"))`
   then `& ~0xff` and compare to the in-code constant. Also check
   `MarketParamsLib.id()` hashes the **full** struct (`N * 32` bytes) — if a new
   field were excluded from the hash, caller-supplied struct fields (whitelist,
   ltv) would be spoofable. That is a 30-second, high-value check.
5. **mythril on a foundry project**: it ignores foundry.toml, so
   (a) remappings must be patched into `~/.local/lib/python3.12/site-packages/mythril/ethereum/util.py`
   (`settings["remappings"] = [...]` right after `settings = {}`),
   (b) **WSL cannot resolve `solc-bin.ethereum.org`** (WARP/VPN DNS), so solcx
   auto-download dies with `ConnectionError`. Fix: download the compiler on the
   Windows side and drop it in WSL by hand —
   `curl -sL -o solc-0.8.30 https://github.com/ethereum/solidity/releases/download/v0.8.30/solc-static-linux`
   then `cp` it to `~/.solcx/solc-v0.8.30` + `chmod +x` (verify with
   `~/.solcx/solc-v0.8.30 --version`), and
   (c) contracts that require via-ir will fail with "Stack too deep" — report
   that file as BLOCKED rather than pretending it ran.
   **Output hygiene:** a fixed tool produces several failed logs before it
   works, and late background notifications will surface those failures *after*
   you already consumed the good run. Name them distinctly and drop a
   `README.txt` in the output dir stating which log is authoritative, how many
   successes/failures each contains, and what the remaining gap is. Never let a
   stale failure log be mistaken for a result — or for coverage.
6. aderyn in WSL: use `wsl -d Ubuntu -e bash -c 'cd ... && /home/windows10/.local/bin/aderyn ...'`.
   `wsl -d Ubuntu -- bash -lc 'export PATH=...'` breaks with
   "not a valid identifier" because the Windows PATH leaks in.
7. Slither/aderyn on a big fork produce ~700 findings of pure noise
   (naming-convention, unused-return, assembly, divide-before-multiply,
   reentrancy-events, timestamp). Classify by detector count, then say
   "all FP after review" — do not paste them as findings.
   **Slither exits NON-ZERO whenever detectors fire** (observed 127) — that is
   documented CLI behaviour, NOT a failure, so never wrap it in
   `if rc != 0: raise`. Prove completeness independently instead: JSON valid,
   `success == true`, `errors[]` empty, and the json/txt detector counts agree.
8. Background-job completion notifications can arrive LONG after you already
   polled the job and consumed its output (and after a *failed* first attempt of
   the same job). When a late notification contradicts what you used, re-verify
   the artifact on disk (validity + completeness + tail) rather than assuming
   either the notification or your earlier read is right.
9. **The upstream contract is often RENAMED**, so `find upstream -name "<ForkName>.sol"`
   returns nothing and you wrongly conclude "no upstream to compare". Real cases:
   `ChainlinkOracleV2` == `MorphoChainlinkOracleV2`, `SisuVault` == `MetaMorpho`,
   `LendingMarket` == `Morpho`, `CouponToken` == `PendleYieldToken`. Search by a
   distinctive *identifier* instead of the filename:
   `grep -rl "BASE_VAULT_CONVERSION_SAMPLE\|SCALE_FACTOR" upstream`.
   Also note upstreams live in subdirs (`src/morpho-chainlink/...`), so re-check
   the path before declaring a file missing.
10. State the diff size, not just "verbatim". "0 differing lines" (VaultLib,
   ChainlinkDataFeedLib), "22 lines all pragma/import/rename"
   (ChainlinkOracleV2), "40 lines all mechanical renames" (BalancesLib) is
   evidence. "Looks the same" is not.
