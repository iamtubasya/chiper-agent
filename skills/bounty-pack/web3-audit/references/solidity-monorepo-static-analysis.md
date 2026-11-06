# Solidity monorepo: fast static-analysis recipe + two false-positive killers

Distilled from a real engagement against a heavily-audited DeFi monorepo (The Graph contracts,
5 packages, ~30k LOC Solidity, solc pinned 0.8.35). Use as the opening move for any
Solidity/EVM audit where the repo pins a solc version.

## Why this exists
1. Pinned solc: the host's `solc-select` rarely has the pinned version, and slither stalls
   trying to download it.
2. The two commonest ways a promising lead dies: an un-checked "inflation / value extraction"
   claim, and a "new" bug that is really a sibling of a fix shipped last month.

## Recipe

### 1. Map the build matrix (mixed monorepos are normal)
```bash
for d in packages/*/; do
  if [ -f "$d/foundry.toml" ]; then echo "FOUNDRY  $d"
  elif [ -f "$d/hardhat.config.ts" ]; then echo "HARDHAT  $d"; fi
done
grep -h solc_version packages/*/foundry.toml   # the pinned version
```
Foundry packages → forge + slither. Hardhat-only packages → slither needs
`--compile-force-framework hardhat` (heavier; try last).

### 2. Install + build (once)
```bash
pnpm install --ignore-scripts          # monorepos are pnpm workspaces
cd packages/<pkg> && forge build       # forge fetches the pinned solc into ~/.svm/<ver>/
ls ~/.svm/<ver>/solc-<ver>             # confirm the binary exists before slither
```

### 3. Slither against the exact solc binary (fixes the stall)
```bash
slither . --solc "$HOME/.svm/0.8.35/solc-0.8.35" \
  --filter-paths "node_modules|test|mocks" > /tmp/slither-<pkg>.txt 2>&1
```
Run it once per package. On a pinned-solc monorepo `slither . --foundry-compile-all` hangs on
the solc download; `--solc <path>` is the fix. `EXIT=127` at the end of a run is often just the
shell after analysis finished — check "analyzed (N contracts ... M result(s) found)" instead.

### 4. Run the repo's own tests (cheap coverage gate)
```bash
cd packages/<pkg> && forge test --summary
```
Monorepo unit tests generally fuzz (often 256 runs/case). ~Zero authoring cost, real signal.
Read the `FAIL` lines; a green suite does not prove safety but a red one is a free finding.

### 5. Triage slither output — which detectors actually matter
Ignore wholesale: `naming-convention`, `solc-version`, `constable-states`, `unindexed-event`,
`assembly`, `too-many-digits`, `var-read-using-this`, `low-level-calls`, `dead-code`,
`shadowing`, `unused-return`, `external-function`, `immutable-states`, `cyclomatic`,
`function-max-lines`, `pragma`, `missing-inheritance`, `unimplemented-functions`.
Look at: `reentrancy-*`, `arbitrary-send-erc20`, `uninitialized-state/local`, `incorrect-equality`,
`divide-before-multiply`, `calls-loop`, `unprotected-upgrade`, `controlled-delegatecall`,
`suicidal`, `tx-origin`, `delegatecall-loop`.
Then VERIFY each by hand — on audited codebases these are ~always FP (reentrancy behind an
`onlyArbitrator`/no attacker callback; `arbitrary-send-erc20` = generic `TokenUtils`
`transferFrom(from,…)` where `from == msg.sender`; `uninitialized-state` on storage mappings =
Solidity zero-init; `divide-before-multiply` = intentional documented round-down).

## FP killer 1 — round-trip accounting for any "inflation / value extraction" lead
Claim shape to distrust: *"attacker inflates the pool so the victim's mint receives far less
X"*. Before writing it up, compute the MINT→BURN round trip **numerically at two pool sizes**.
- Linear curve (reserve ratio = 100%, e.g. The Graph L2 Curation `fixedReserveRatio = MAX_PPM`):
  `signalOut = poolSignal * tokensIn / poolTokens`, and burning that signal returns
  `poolTokens' * signalOut / poolSignal' = tokensIn`. Invariant of prior inflation.
- Therefore the victim receives fewer *shares/signal* but recovers ~the same *tokens*. Residual
  harm = diluted signal/reward weight, not stolen principal.
- Real worked case: the recently-fixed Graph GHSA was "curation inflation" via
  `paymentsDestination == SubgraphService`; the sibling no-slippage mints looked reportable until
  the round-trip math showed the attacker recovers only their own injection. Lead → killed.
A "diluted weight" story does not clear a ">$1M funds lost/stolen" impact bar.

## FP killer 2 — "sibling of a just-fixed bug" is usually a DUPLICATE
When git history shows a recent `security-fixes` merge / GHSA branch, and you find another
function with the SAME root cause (missing slippage param, missing guard, missing cap), assume
the program will call it a known issue / duplicate ("bugs rewarded once to the first reporter").
Only submit if you can show (a) a **distinct** impact and (b) a **working PoC for that specific
path**. Otherwise kill it and move on.

## Recon add-ons specific to this class of repo
- `packages/*/address-book/src/**/addresses.json` are often one-line **symlinks**
  (`../../../<pkg>/addresses.json`) → `json.load` throws "Expecting value: line 1 column 1".
  Read `packages/<pkg>/addresses.json` directly; it maps every deployed contract + proxy/
  implementation per chain id (fastest way to turn a bounty scope table into targets).
- Deepen shallow clones before recon: `git fetch --depth=200 origin`, then grep the last 90 days
  for `security|fix|advisory|ghsa|vuln|slippage|inflation` and read the diffs (`git show --stat`,
  `git diff <merge>^1 <merge> -- <file>`). `packages/*/CHANGELOG.md` restates the fix in prose.
- Agent/delegation tooling note: sub-agents with a 600s cap are a poor fit for multi-thousand-LOC
  contract review (they time out mid-read). Do the contract reading in the main thread.

## Example coverage ledger line (write it this way, per class)
- ran: forge build, slither (per package), forge test/fuzz, manual read
- not run + why: echidna/medusa (no invariant harness authored); halmos/hevm/Certora (not installed);
  on-chain source verification + fork simulation (not performed)
- N/A for scope: oracle-manipulation (no external oracle), ERC-4626/1153/4337 (unused),
  the web2 tool set (this was a pure on-chain scope)
