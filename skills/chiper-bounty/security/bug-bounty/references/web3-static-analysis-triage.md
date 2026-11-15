# Web3 static-analysis: tool set, FP triage, and economics verification

Companion to `immunefi-recon-workflow.md`. Load this when auditing a Solidity/Rust contract
target and you must produce an honest coverage ledger + survive triage of analyzer output.

---

## 1. Tool set for a contract audit (and what is genuinely N/A)

| Tool | Role | How to run |
|------|------|-----------|
| `forge build` (per package) | compile + confirms toolchain | `forge build` in each `packages/<pkg>/` (foundry.toml has `solc_version`, `libs=["node_modules"]`) |
| **slither** (per package) | broad detector sweep | see solc pitfall below; run it for EVERY package, not once |
| `forge test` | repo's own unit + fuzz suite | `forge test --summary` — long (some suites take 8+ min); all-PASS is real coverage evidence |
| aderyn | fast Rust analyzers | Linux/macOS only (npm refuses `Windows_NT`); needs a working WSL/container |
| mythril | symbolic execution | WSL/Linux binary; very slow on big contracts |
| echidna / medusa | invariant fuzzing | REQUIRES a purpose-built harness — budget separately, do not claim it as "run" |
| halmos / hevm / Certora | formal | not installed by default |
| Arbiscan/Etherscan source match | deployed-vs-repo drift | only if the scope protects deployed bytecode |
| fork simulation (Tenderly / `forge --fork-url`) | live-state PoC | for economic attacks against real balances |
| sqlmap / dalfox / ffuf / nuclei / … | web2 | **N/A** on a Smart-Contract-scope program. Mark N/A, don't imply "pending". |

**Pitfall — slither stalls on a pinned solc.** Repos pin e.g. `solc_version = '0.8.35'`;
solc-select usually lacks it and slither spins 10+ min trying to fetch. Build once with
`forge build` (populates `~/.svm/0.8.35/`), then:
`slither . --solc "$HOME/.svm/0.8.35/solc-0.8.35" --filter-paths "node_modules|test|mocks"`.
For hardhat-only packages use `--compile-force-framework hardhat` instead.
Also bump the terminal timeout — the default on this host is 60s, which truncates every run.

---

## 2. Slither FP triage — verified reasons (copy these instead of re-deriving)

A detector hit is NOT a finding. Every round must state the FP reason, one line each.

| Detector | Typical cause here | How to settle it |
|----------|-------------------|------------------|
| `unprotected-upgrade` | **inherited custom modifier invisible to slither** | open the modifier's real definition. Real case: `GNS.initialize` is `external onlyImpl initializer`; `initializer` comes from OZ `contracts-upgradeable@3.x proxy/Initializable.sol:35` reached through `GNSV3Storage is … , Initializable`. `onlyImpl` = `require(msg.sender == _implementation())`, so calling via `Multicall.multicall` (delegatecall → `msg.sender == proxy != impl`) still reverts. **FP.** |
| `arbitrary-send-erc20` | generic `TokenUtils.pullTokens(token, from, amt)` | callers pass `msg.sender`; the helper is intended. FP. |
| `reentrancy-no-eth/-benign/-events` | state written after an external call | check whether ANY untrusted code can run in that window. If the only calls are token burn/push to a trusted ERC20 and the mutator is role-gated (`onlyArbitrator`), no attacker callback → FP. |
| `reentrancy-balance` | balance read before/after an external call | confirm the delta cannot be injected by the caller (no untrusted hook inside the window). |
| `divide-before-multiply` | fixed-point / intentional round-down | look for a `// round down, 1 wei max precision loss` style comment; if documented and bounded, FP. |
| `calls-loop` | view/audit helper looping over external getters | view-only → no state risk. FL. |
| `incorrect-equality` / `timestamp` | intentional block/id/period comparisons | read the surrounding logic before believing it. |
| `uninitialized-state` | mapping/struct storage vars | Solidity zero-initialises; detector noise. |
| `unchecked-transfer` | raw `token.transferFrom` without return check | safe ONLY if the token reverts on failure (GRT does). Say which token and why. |
| `encode-packed-collision` | string concat for a URL/tokenURI | not a hash → FL. |
| `shadowing-state` | `private constant` same name in child | no storage slot → FP. |
| `controlled-delegatecall` | delegatecall with a fixed selector to a known impl | FP unless the target/selector is caller-controlled. |

**Verification recipe for an inherited modifier:** grep the child for the modifier, then walk the
inheritance chain to the storage/base contract, then read the dependency file under
`node_modules/.pnpm/<pkg>@<ver>/node_modules/...` directly. Do not accept "slither says unprotected"
as fact.

---

## 3. Economics verification BEFORE claiming theft (bonding curves, slippage, "inflation attacks")

Recurring trap: a "missing slippage protection" or "pool inflation" pattern LOOKS like theft but is
not. Prove the value transfer numerically before writing it up.

- Establish the pool's price invariant. In a linear/constant-price pool
  (e.g. `reserveRatio = MAX_PPM` ⇒ `signal ∝ tokens`), mint→burn round-trip returns ~the same tokens
  **regardless of prior inflation**. Then a victim who mints into an inflated pool receives fewer
  SIGNAL but the signal redeems back to ~the same TOKENS → **no fund theft**.
- The real residual harm, if any, is *dilution of future fee/reward share* or locked position — that
  is a much weaker claim than ">$1M user funds lost/stolen". Label it honestly.
- Attacker P&L: write out `attacker_claim − (initial_mint + injection)`. If it nets ~0 (minus any
  protocol cut they burn), there is no profit and therefore no reportable economic attack.
- Also check duplication: if the team already shipped a fix for the same root cause (git history /
  CHANGELOG / a new audit report in the PR), the sibling path is likely a **known issue → OOS**.
  Report siblings only with a working PoC showing net victim loss > attacker cost.

---

## 4. What an honest "0 true positives" ledger looks like

For each package: tool → contract count → result count → **0 TP**, followed by the FP reasons above.
Separately list, with one-line reasons: tools not run AND tools that cannot run, plus the check you
performed before giving up. Never let the absence of a finding imply the absence of testing, and
never let a missed tool read as "coverage complete".
