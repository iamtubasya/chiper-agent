---
name: web3-audit
description: Smart contract security audit — 12 bug classes (accounting desync, access control, incomplete path, off-by-one, oracle, ERC4626, reentrancy, flash loan, signature replay, proxy, cross-chain settlement/bridge attestation mismatch, Move-VM black-box RPC audit), pre-dive kill signals (TVL < $500K etc), REPO REALITY CHECKS for non-Solidity targets (Vyper `# @version`, vendored-submodule split, compiler-pin CVE lines, source-vs-deployed-bytecode gate), Foundry PoC template plus the harness-fault checklist that stops a broken probe reading as a contract bug, grep patterns for each class, and real Immunefi paid examples. Use for any Solidity/Vyper/Rust contract audit, for a Move-VM (Supra/Aptos/Sui) deployment with no source repo where you must read the ABI and execute view functions over RPC, or for bridge / intent-settlement protocols where an off-chain attestor service credits an on-chain vault, or when deciding whether a DeFi target is worth hunting.
sources: public_research, community
---

# WEB3 SMART CONTRACT AUDIT

> **HUNT DISPATCHER (read first on a web3 target):** `references/web3-hunt-dispatcher.md` — the one
> fingerprint→skill→kill-signal→first-probe routing table. The eight class-level `hunt-*` skills
> (vault-inflation, oracle-l2, permit2, amm-hooks, aa-modular, diamond-proxy, intent-settlement,
> restaking-lrt) are each already exhaustive. This file only routes you to the right one so you
> don't re-read all eight: each row is a fingerprint (repo/ABI/on-chain) → kill signal → first probe,
> plus the cross-class composition map and the one-grep that seeds every class.

11 bug classes. Pre-dive kill signals. Foundry PoC template. Real paid examples.
Class 11 covers bridge / intent-settlement protocols where the money path spans an
off-chain attestor AND an on-chain vault. Class 12 covers a Move-VM deployment you
must audit black-box from its RPC.

---

## PRE-DIVE KILL SIGNALS (check BEFORE any code review)

> ZKsync lesson: $322M TVL + OZ audit + 750K LOC + 5 sessions = 0 findings. Large well-audited bridges are extremely hard.

1. **TVL < $500K** → max payout capped too low for effort
2. **2+ top-tier audits** (Halborn, ToB, Cyfrin, OpenZeppelin) on simple protocol → bugs already found
3. **Protocol < 500 lines, single A→B→C flow** → minimal attack surface
4. **Formula**: `max_realistic_payout = min(10% × TVL, program_cap)` — if < $10K, skip

**Soft kill:** OZ/ToB/Cyfrin audit on current version + codebase > 500K LOC → expect 40+ hours for maybe 1 finding. Only proceed if bounty floor > $50K AND you have protocol-specific expertise.

**Target scoring (go if >= 6/10):**
- TVL > $10M: +2
- Immunefi program with Critical >= $50K: +2
> **Severity for Immunefi findings:** classify with **Immunefi VSS v2.3** (NOT CVSS) per domain — Smart Contracts / Blockchain-DLT / Websites-and-Apps. Read `skills/security/bug-bounty/references/immunefi-vss-v2.3.md` before assigning a level; the boundary that decides triage is *principal vs unclaimed yield* (Critical vs High) and *temporary vs permanent freeze*.
- No top-tier audit on current version: +2
- < 30 days since deploy: +1
- Protocol you've hunted before: +1
- Source code + natspec comments: +1
- Upgradeable proxies: +1

---

## REPO REALITY CHECKS — do these BEFORE trusting the source tree

> Five traps, each burned real time in the 2026-10-13 Zharta session (Vyper NFT-lending, ~14.8k
> LOC). Skip them and you either audit the wrong code or file a finding against code that was
> never deployed.

### 0. Confirm you cloned the LIVE PROTOCOL VERSION — the org may ship several
This precedes everything: if you are in a superseded repo, every later check is moot. Zharta
cost a full session on this. `protocol-v1` (last push **2025-04**) was cloned and reviewed
end-to-end, while the live protocol was `lending-protocol-v2` (push **2026-09**) — a *different
architecture* (P2P signed offers, loan replacement, broker fees, refinance proxies to
Nftfi/Gondi/Arcade/BendDAO) with audit status **Pending**. Nothing in the V1 tree said
"deprecated"; only the org's repo list and the README version table did.

```bash
# list every repo in the org, newest push first — the live one is usually obvious
curl -s "https://api.github.com/orgs/<ORG>/repos?per_page=100" -o /tmp/repos.json
python3 -c "import json;d=json.load(open('/tmp/repos.json'));[print(r['pushed_at'][:10],r['name']) for r in sorted(d,key=lambda x:x['pushed_at'],reverse=True)]"
# read the README version table + audit-status row BEFORE cloning anything
curl -s https://raw.githubusercontent.com/<ORG>/<likely-live-repo>/main/README.md | head -40
```
Signals you are in the **stale** repo: a sibling repo with a much newer `pushed_at`, a README
version table naming V1/V2, a higher star count on the sibling, or an audit-status table whose
newer version row says **Pending** (unaudited = that is the real target). After cloning, re-confirm
that the addresses you pull from `configs/prod/*` actually belong to the version you cloned.

### 1. Detect the language — do NOT assume Solidity
A DeFi repo can be 100% non-Solidity. Grep patterns below are all `.sol`; they silently return
nothing useful on a Vyper/Rust repo and that "clean" result is a lie, not a pass.

```bash
find . -name '*.sol' | wc -l      # solidity
find . -name '*.vy'  | wc -l      # vyper
find . -name '*.rs'  | wc -l      # anchor / native rust
grep -rn '@version\|pragma solidity' --include='*.sol' --include='*.vy' | sort -u
```

**Vyper specifics** (Zharta pinned `# @version 0.4.1` on all 23 files):
- Version pin is a **comment**, `# @version 0.4.1`, not `pragma solidity ^0.8.x`.
- `@nonreentrant` is opt-in per function and easy to forget entirely — Zharta had **zero**
  guards across every core contract. Its absence is a *hardening note*, not a finding, unless a
  concrete CEI violation is demonstrated (Zharta's liquidation path removed state **before** the
  external NFT transfer, so it held).
- Vyper has no `unchecked`; arithmetic underflow/overflow **reverts by default**. So the classic
  "unchecked math" class does not apply, and a suspected underflow must be reachability-tested,
  not assumed (see the `pay()` case below).
- Checked arithmetic flips a real bug into a **DoS**, not a drain: an unintended underflow makes
  `pay()` revert and can permanently block loan repayment. That is the shape to look for.

### 2. Separate first-party code from vendored dependencies
The Zharta repo showed **98 `.sol` files — all of them vendored** NFTX + SushiSwap under
`contracts/auxiliary/` as a **git submodule** (`gitlab.com/z106/auxiliary-smart-contracts`). A
file count and a `.sol` grep would have pointed the entire audit at someone else's audited code.

```bash
cat .gitmodules                                   # submodules = vendored, usually out of scope
find contracts -type d | grep -i 'aux\|lib\|vendor\|external\|third'
find contracts -name '*.sol' -not -path '*auxiliary*' -not -path '*lib*'   # first-party only
```
Read the **README's stated language** before counting files — Zharta's README said Vyper on line
three and I still ran a `.sol` count first. The protocol code was 20 `.vy` files; the 98 `.sol`
were 100% vendored.

### 3. Check the compiler pin against known CVE lines BEFORE reviewing the bug classes that
those CVEs created
A pin in the vulnerable range means a whole bug class is either **already broken for everyone**
(not reportable — it's the compiler, upstream) or **worth checking first**. Do this before you
spend a session reading reentrancy paths.

- **Vyper 0.2.15–0.3.0**: the `@nonreentrant` decorator was broken (lock shared across functions
  / not actually guarding). Zharta pinned **0.4.1** → class is off the table, move on.
- **Vyper 0.2.15–0.3.0**: several `sqrt` / `raw_call` / `slice` correctness bugs. Same check.
- **Solidity 0.4.x–0.5.x**: `transfer`/`send` 2300-gas assumptions, `delegatecall` patterns.
- **solc >= 0.8.0**: checked arithmetic on (unless `unchecked`).
If the pin is clean for a class, say so explicitly and *skip* the class — naming the skipped
class + why is part of the deliverable, not an omission.

### 4. Source ≠ deployed bytecode — verify BEFORE reporting anything
The repo can be **ahead of or behind** what is actually live. A finding against undeployed code
is not reportable, and a "confirmed live" claim you did not check is overclaiming.

```bash
RPC=https://ethereum-rpc.publicnode.com          # public node; ankr now needs an API key
cast code <addr> --rpc-url $RPC | wc -c          # >3 = real bytecode present, not an EOA
cast call <addr> "owner()(address)" --rpc-url $RPC
```
Cheap minimum: `cast code` non-empty (rules out "address in config is an EOA / not deployed") +
one view call that resolves. The full check is diffing deployed bytecode against the repo build —
**state plainly which of the two you did**. Prod addresses come from the repo's own config tree
(`configs/prod/<chain>/pools.json`) — that file is the authoritative deployment inventory, not
the docs.

**Sourcify = the no-compile verification route.** When you cannot build locally (Vyper blocked by
PEP 668, no toolchain, pinned solc you can't fetch), Sourcify answers "does live bytecode match the
published source" without compiling. **Use API v2 — v1 is removed** and 404s with a body naming the
replacement:

```
GET https://sourcify.dev/server/v2/contract/{chainId}/{address}   # v2, no API key
  -> {"match":"match"|"partial"|null, ...}      # "match" = exact bytecode+metadata
# old v1 paths (/check-all-by-addresses, /files/) now 404: "API v1 is removed. Use API v2."
GET https://repo.sourcify.dev/contracts/full_match/{chainId}/{addr}/   # raw verified files
```

Zharta result: prod `LendingPoolPeripheral` + `LoansPeripheral` returned `match` (repo == live,
exact); `LendingPoolCore` + `LoansOTC` returned `null` (not in Sourcify — **not a mismatch**, just
unverified). Etherscan `getsourcecode` needs an API key and was blocked, so Sourcify was the only
no-key route. Report the split honestly — "N of M verified exact, K unverified" — never fold
unverified into either bucket.

### Worked example — a reachability-killed underflow lead (both languages, same shape)
Zharta `Loans.vy:750`: `paidInterestAmount = paymentAmount - loan.amount`, but `paymentAmount`
was derived from *remaining* principal (`amount - paidPrincipal`). If `paidPrincipal > 0`, the
subtraction underflows → reverts → **loan can never be repaid** (a real DoS-class bug in Vyper,
where arithmetic reverts). It looked like a finding. It was not, for one checkable reason:
`paidPrincipal` is only ever set at the moment of **full** repayment (`updateLoanPaidAmount` is
always paired with `updatePaidLoan` setting `paid=True` in the same call), so while a loan is
open it is always 0 → the subtraction never underflows. **Trace the writer of the suspect state
variable before reporting.** The `+=` accumulation pattern in `LoansOTC.vy:365` is the same code
smell and the same dead end — but it becomes live the day anyone adds partial repayment, so it
belongs in the report as a hardening note with that condition spelled out.

---

## TOOL LEDGER — run this every round, and report it as a table

The owner repeatedly asks "sudah semua tools dipanggil? termasuk varian attack?" — the accepted
answer is an explicit **tool → result** table that also names the tools you did NOT run and the
NEGATIVE results. Negatives are deliverables. A silent omission reads as overclaim.

| Layer | Tool / action | Notes |
|-------|---------------|-------|
| Build | `pnpm install`, `forge build` per package | needed before any static tool |
| Static | `slither` **per package** | hangs on the pinned solc → `slither . --solc "$HOME/.svm/<ver>/solc-<ver>" --filter-paths "node_modules\|test\|mocks"`; for hardhat-only packages add `--compile-force-framework hardhat` |
| Static | `aderyn` | **no Windows build** (macOS/Linux only) → substitute slither; see `bug-bounty/references/tool-installation-windows.md` |
| Symbolic | `mythril`, `halmos`, `hevm` | only if reachable; state plainly when not run |
| Invariant | `echidna`, `medusa`, `forge test` fuzz/invariant | the repo's own `forge test --summary` exercises its invariants; run it and quote pass/fail counts |
| Manual | read every in-scope contract end-to-end | the highest-yield layer on audited code |
| Upgrade | storage-layout diff vs previous implementation | catches collision from a fresh upgrade |
| On-chain | block-explorer source match, fork simulation (Tenderly / `forge --fork-url`) | say so if skipped |
| History | `git fetch --depth=200` then hunt recent security-fix commits | fastest route to the bug class the team fears |
| Off-chain | indexer/node software in scope? | separate track — see `bug-bounty/references/graph-node-indexer-audit.md` |

Never apply the web2 ledger (sqlmap/dalfox/ffuf/nuclei…) to a contract-only scope: say it is N/A
and explain why, rather than listing it as "not run".

## THE ONE RULE

> "Read ALL sibling functions. If `vote()` has a modifier, check `poke()`, `reset()`, `harvest()`. The missing modifier on the sibling IS the bug."

This single rule explains 19% of all Critical findings.

### Companion: real-incident patterns (`defi-exploit-forensics`)

The classes below come from Immunefi paid reports and are the **audit** view. When you need the
**attacker** view — what an exploit transaction actually did, frame by frame — load
`defi-exploit-forensics`. It carries seven techniques extracted by tracing the on-chain
transactions of the last year's incidents (ERC4626 rate rounding, share/amount rounding through a
batch op, stableswap solver precision, governance timelock neutering, self-naming attacker
contracts, Safe-wrapped execution, and the non-EVM identify-from-calldata ceiling), plus the
selector signatures and call shapes that identify each one.

Use it in two moments:
1. **before** deciding where to read — the "rounding of a share↔asset conversion the caller can
   drive" pattern currently explains two of the largest incidents of the past year; start there;
2. **after** a pattern match, to turn "this looks exploitable" into a named technique with a
   reproduction shape (`defi-exploit-forensics` → `skills/security/defi-exploit-forensics/references/detection-patterns.md`).

Do not duplicate its content here — the two skills cross-reference on purpose, so the audit classes
stay stable while the incident set keeps growing.

---

## 1. ACCOUNTING STATE DESYNCHRONIZATION
> #1 Critical bug class — 28% of all Criticals on Immunefi.

### What It Is
Two state variables supposed to stay in sync. One code path updates A but forgets B. Later code reads both and makes decisions based on stale B.

```
Real Value = A - B
If A updated but B isn't → Real Value appears larger → phantom value
```

### Root Cause Patterns

**Variant 1: Phantom Yield** (Yeet protocol — 35 duplicate reports)
```solidity
function startUnstake(uint256 amount) external {
    totalSupply -= amount;  // decremented BEFORE transfer
    // aToken.balanceOf(this) still reflects old value
    // yieldAmount = aToken.balanceOf - totalSupply = phantom yield
}
```

**Variant 2: Fast Path Skips State Update** (Alchemix V3)
```solidity
function claimRedemption(uint256 tokenId) external {
    if (transmuter.balance >= amount) {
        transmuter.transfer(user, amount);
        _burn(tokenId);
        return;  // EARLY RETURN — cumulativeEarmarked, _redemptionWeight, totalDebt never updated
    }
    // Slow path: updates all state vars correctly
    alchemist.redeem(...);
}
```

**Variant 3: Update Happens in Wrong Order** (Alchemix)
```solidity
function deposit(uint256 amount) external {
    _shares = (amount * totalShares) / totalAssets;  // calculated BEFORE deposit
    totalAssets += amount;   // assets added AFTER shares calculated → wrong rate
}
```

### Grep Patterns
```bash
# Find all accounting variables
grep -rn "totalSupply\|totalShares\|totalAssets\|totalDebt\|cumulativeReward\|rewardPerShare" contracts/

# Find all early returns in claim/redeem functions
grep -rn "\breturn\b" contracts/ -B3 | grep -B3 "if\b"

# For each early return: which state updates in normal path are skipped?
```

---

## 2. ACCESS CONTROL
> #2 Critical — 19% of Criticals. $953M lost in 2024 alone.

### Variant 1: Missing Modifier on Sibling Function
```solidity
function vote(uint256 tokenId) external onlyNewEpoch(tokenId) {  // guarded
function reset(uint256 tokenId) external onlyNewEpoch(tokenId) { // guarded
function poke(uint256 tokenId) external {                         // NO GUARD → infinite FLUX inflation
}
```

### Variant 2: Wrong Check (Existence vs Ownership)
```solidity
function split(uint256 tokenId, uint256 amount) external {
    _requireOwned(tokenId);  // checks if token EXISTS, not if caller OWNS it
    _burn(tokenId);
    _mint(msg.sender, amount);  // attacker steals tokens they don't own
}
```

### Variant 3: Silent Modifier (if vs require)
```solidity
// VULNERABLE — non-admin silently gets through:
modifier onlyAdmin() {
    if (msg.sender == admin) {
        _;  // body only executes for admin, but non-admin doesn't revert
    }
}
// CORRECT: require(msg.sender == admin, "Not admin"); _;
```

### Variant 4: Uninitialized Proxy
```solidity
function initialize(address _owner) public {  // MISSING: initializer modifier
    owner = _owner;  // anyone can call → become owner
}
// Fix: constructor() { _disableInitializers(); }
```

### Grep Patterns
```bash
# Find sibling function families — do ALL have the same modifier set?
grep -rn "function vote\|function poke\|function reset\|function update\|function claim\|function harvest" contracts/ -A2

# Ownership check: existence vs ownership?
grep -rn "_requireOwned\|ownerOf\|_isApprovedOrOwner\|_checkAuthorized" contracts/ -B5

# Silent modifiers
grep -rn "modifier\b" contracts/ -A8 | grep -B3 "if (" | grep -v "require\|revert"

# Uninitialized initializer
grep -rn "function initialize\b" contracts/ -A3
grep -rn "_disableInitializers()" contracts/
```

### Real Paid Examples

| Protocol | Payout | Bug |
|---|---|---|
| Wormhole | $10M | Uninitialized UUPS proxy → anyone calls initialize() |
| ZeroLend | n/a | split() uses existence check, not ownership check |
| Alchemix | n/a | poke() missing onlyNewEpoch → infinite FLUX inflation |
| Parity | $150M frozen | No access control on initWallet() in library |

---

## 3. INCOMPLETE CODE PATH
> #3 Critical — 17% of Criticals.

### The Function Family Comparison Test
```
1. List all state changes in function A (deposit/place/create)
2. List all state changes in function B (withdraw/update/cancel)
3. For each state change in A: does B have the corresponding reverse?
4. For each token transfer in A: does B have the corresponding refund?
If A does X but B doesn't do the reverse of X → BUG.
```

### Variant 1: Update Function Missing Refund (ThunderNFT)
```solidity
function place_order(OrderInput calldata order) external {
    token.safeTransferFrom(msg.sender, address(this), order.price);  // takes tokens
    orders[orderId] = order;
}
function update_order(OrderInput calldata updatedOrder) external {
    // BUG: NO REFUND for sell orders when price decreases → tokens permanently stuck
    orders[orderId] = updatedOrder;
}
```

### Variant 2: Partial Fill Token Stuck (Plume)
```solidity
function swapForETH(uint256 amountIn) external {
    token.safeTransferFrom(msg.sender, address(this), amountIn);
    uint256 filled = dex.swap(amountIn);  // partial fill possible
    _refundExcessEth(amountIn - filled);  // BUG: refunds ETH only, not ERC20
}
```

### Variant 3: mint() Bypasses Check That deposit() Has (MetaPool)
```solidity
function deposit(uint256 assets, address receiver) public override {
    shares = _deposit(assets, receiver);  // includes receipt validation
}
function mint(uint256 shares, address receiver) public override {
    assets = convertToAssets(shares);
    _mint(receiver, shares);  // MISSING: _deposit() validation → mints without receiving assets
}
```

### Grep Patterns
```bash
grep -rn "function place_\|function create_\|function add_\|function open_" contracts/ -A5
grep -rn "function update_\|function modify_\|function cancel_" contracts/ -A5
grep -rn "safeApprove\b" contracts/    # safeApprove without zero-reset before
grep -rn "delete\b" contracts/ -B5 -A5  # delete before operation completes
grep -rn "function deposit\|function mint\|function withdraw\|function redeem" contracts/ -A10
```

---

## 4. OFF-BY-ONE & BOUNDARY CONDITIONS
> #4 High — 22% of Highs. Single character change. Massive impact.

### Root Cause
```solidity
// VeChain Stargate — post-exit reward drain:
function _claimableDelegationPeriods(address delegator) internal view returns (uint256) {
    if (endPeriod > nextClaimablePeriod) {  // BUG: should be >=
        return 0;  // exited users get nothing
    }
    return nextClaimablePeriod - lastClaimedPeriod;  // rewards for period AFTER exit
}
```

### Mental Test for Every Comparison
> For every `if (A > B)`: "What happens when A == B?" Is that correct?

### 6 Boundary Locations to Check
1. Period/Epoch boundaries: `>` vs `>=` at period end
2. Time-based locks: does `block.timestamp == deadline` lock or unlock?
3. Loop break conditions: `break` with `>` vs `>=`
4. Array index boundaries: `i <= array.length` (should be `i < array.length`)
5. Amount/balance boundaries: `>= amount` allows exact full withdrawal?
6. Rounding/precision: can any input produce 0 output that should be non-zero?

### Grep Patterns
```bash
# Boundaries in comparisons
grep -rn "Period\|Epoch\|Round\|Deadline\|period\|epoch\|deadline" contracts/ -A3 | grep "[<>][^=]"

# Loop breaks
grep -rn "\bbreak\b" contracts/ -B10

# Off-by-one in array access
grep -rn "\.length\s*-\s*1\|i\s*<=\s*.*\.length\b" contracts/
```

---

## 5. ORACLE / PRICE MANIPULATION
> 12% of all reports. Largest individual payouts. $117M Mango, $70M Curve.

### Bug A: Missing Staleness Check (most common)
```solidity
// VULNERABLE:
(, int256 price,,,) = priceFeed.latestRoundData();
return uint256(price);  // If Chainlink node goes down, stale price returned indefinitely

// CORRECT:
(, int256 price,, uint256 updatedAt,) = priceFeed.latestRoundData();
require(block.timestamp - updatedAt <= MAX_PRICE_AGE, "Stale price");
require(price > 0, "Invalid price");
```

### Bug B: Missing Confidence Interval (Pyth)
```solidity
// VULNERABLE:
PythStructs.Price memory p = pyth.getPriceUnsafe(priceFeed);
return p.price;  // ignores p.conf (confidence interval)

// CORRECT:
require(p.conf * 10 <= uint64(p.price), "Price too uncertain");
// conf > 10% of price = untrustworthy
```

### Bug C: TWAP Too Short (flash loan manipulatable)
```solidity
// VULNERABLE: 60-second TWAP
uint32[] memory secondsAgos = new uint32[](2);
secondsAgos[0] = 60; secondsAgos[1] = 0;
// Flash loan can shift price for entire 60s window

// CORRECT: 1800s minimum TWAP (30 min)
```

### Bug D: Single-Source Oracle
```solidity
// VULNERABLE: only Uniswap spot price
uint price = getUniswapSpotPrice(token);  // flash loan manipulatable

// CORRECT: Chainlink primary, Uniswap TWAP as fallback, require close agreement
```

### Grep Patterns
```bash
# Missing staleness check
grep -rn "latestRoundData" contracts/ -A5 | grep -v "updatedAt\|timestamp"

# Pyth price usage — confidence interval checked?
grep -rn "getPriceUnsafe\|getPrice\b" contracts/ -A8 | grep -v "conf\|confidence"

# TWAP windows — short TWAP flag
grep -rn "secondsAgo\|TWAP\|cardinality" contracts/ -A5
```

---

## 6. ERC4626 VAULT ATTACKS

### Exchange Rate Manipulation (near-empty vault)
```solidity
// VULNERABLE — first depositor attack:
// 1. Attacker deposits 1 wei → gets 1 share
// 2. Attacker donates large amount directly (transfer, not deposit)
// 3. Exchange rate: 1 share = (1 + donation) assets
// 4. Victim deposits → rounds down to 0 shares → free donation to attacker

// CORRECT: virtual shares (OpenZeppelin v4.9+)
function _decimalsOffset() internal view virtual override returns (uint8) {
    return 9;  // add 1e9 virtual shares + assets to prevent manipulation
}
```

### ERC4626 Transfer (moves shares but not stake/lock records)
```solidity
// VULNERABLE: shares transferred, but lock records stay with original owner
// → shares stuck, can't redeem → permanent freeze (Belong pattern)
function transfer(address to, uint256 amount) external override {
    _transfer(msg.sender, to, amount);  // moves shares
    // MISSING: transfer lock record from msg.sender to `to`
}
```

### Rounding in the conversion, inside a POOL or a BATCH (real paid exploits)
*(distinct from the first-depositor attack above — here the vault is fine, the caller drives the rate)*

```solidity
// A pool/vault prices wrapped tokens through convertToAssets()/toShare()/toAmount().
// If the conversion rounds in the trader's favour on ONE of the two legs, they extract the delta.
// Amplified by wrapping both directions in a single user-controlled batch call.
```

- **Balancer V2, 2025-11-03 (~$120M)** — ComposableStablePool over ERC4626 rate-bearing tokens
  (`osETH/wETH` and `wstETH-WETH` pools). Hot selectors in the exploit tx: `onSwap 0x01ec954a`,
  `getRate() 0x679aefce`, `convertToAssets(uint256) 0x07a2d13a`, `batchSwap 0x945bcec9`, 485 frames.
- **Abracadabra, 2025-10 (~$1.8M)** — BentoBox `cook(uint8[],uint256[],bytes[]) 0x656f3d64` driving
  `toShare 0xda5139ca` / `toAmount 0x56623118` back and forth across the rounding boundary.

Check: `toShare(toAmount(x)) != x` for some x, and can both directions be packed into one
caller-controlled batch (`cook`, `multicall`, `executeBatch`)? Simulate an add→remove round trip at
1 wei, 2 wei, 3 wei … A successful exploit tx in this class shows **hundreds of repeats** of one
conversion function (440× in the Yearn yETH case, 226× `onSwap` in the Balancer case) — repetition
at that scale means a rounding error is being harvested, not a single large transfer.

Full extracted techniques + trace evidence: `defi-exploit-forensics`,
`skills/security/defi-exploit-forensics/references/technique-library-2025-2026.md` (T1, T2, T3).

### Grep Patterns
```bash
grep -rn "function transfer\|function transferFrom" contracts/ -A15
grep -rn "function deposit\|function mint\|function withdraw\|function redeem" contracts/ -A10
```

---

## 7. REENTRANCY
> 2016–present. CEI pattern prevents it. Still found in DeFi.

### Variants
- **Single-function**: attacker re-enters same function before state updated
- **Cross-function**: re-enters a sibling function with stale state
- **Cross-contract**: re-enters via a callback to another protocol
- **Read-only**: re-enters a view function that returns stale data used by attacker
- **Guard disarm (guard BYPASS, not a missing guard)**: the `nonReentrant` modifier is
  present but its exit branch **writes 0 instead of restoring the previous value**, so it
  is not a depth counter. One nested nonReentrant call that *completes* zeroes the slot,
  and everything after it in the same transaction is unguarded. The trigger is usually the
  contract's own **self-call** (its documented cleanup/refund step), which the guard
  explicitly allows via `sender == address(this)`. Check the exit branch, not just the
  entry check.
- **Dangling approval**: an `approve(to, amount)` that is never reset, where an explicit
  amount also **bypasses the balance check** — a zero-balance contract hands out an
  unlimited, permanent allowance at no cost. Distinct from a missing `safeApprove` reset:
  here the grant is the *capability*.

**→ `references/reentrancy-guard-and-approval-poc.md`** — the disarm pattern with the
exact entry/exit check to grep for, the dangling-approval shape, and the **PoC discipline
that makes such a harness honest**: the probe's reentrant call must SUCCEED when the guard
allows it (otherwise a reverting body is misread as "guard held"), every claim needs a
matched **control test** with the trigger removed, and tests must assert the *observed*
behaviour so the suite fails loudly on the day the bug is fixed. Also: confirm which guard
build is deployed (transient-storage vs `_NonTstore` storage fallback) before claiming it.

### Root Cause Pattern
```solidity
// VULNERABLE (effects after interaction):
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount);
    (bool success,) = msg.sender.call{value: amount}("");  // INTERACTION first
    require(success);
    balances[msg.sender] -= amount;  // EFFECT after → reentrancy window
}

// CORRECT (CEI — Checks, Effects, Interactions):
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount);  // CHECK
    balances[msg.sender] -= amount;            // EFFECT
    (bool success,) = msg.sender.call{value: amount}("");  // INTERACTION last
    require(success);
}
```

### Grep Patterns
```bash
# External calls before state updates
grep -rn "\.call{value\|safeTransfer\|transfer(" contracts/ -B10 | grep -v "require\|revert"

# Missing nonReentrant modifier on critical functions
grep -rn "function withdraw\|function redeem\|function claim" contracts/ -A2 | grep -v "nonReentrant"

# Storage slot for reentrancy guard
grep -rn "nonReentrant\|ReentrancyGuard\|_notEntered" contracts/
```

---

## 8. FLASH LOAN ATTACKS

### Oracle Manipulation via Flash Loan
```solidity
// Attack flow:
// 1. Borrow $100M from Aave flash loan
// 2. Dump token in Uniswap pool → crash spot price
// 3. Protocol reads Uniswap spot → undercollateralized loans accepted
// 4. Borrow max against cheap collateral
// 5. Repay flash loan, keep profits
```

### Price Oracle Sanity Checks (what to look for)
```bash
grep -rn "getReserves\|getAmountsOut\|slot0\b" contracts/ -A5
# spot price from reserves = manipulatable with flash loan
# slot0 = Uniswap V3 spot price = manipulatable
```

---

## 8b. BONDING-CURVE "INFLATION ATTACK" — KILL TEST
> Claim shape: "the pool price can be raised (e.g. `collect()` adds tokens/ETH to the pool without
> minting shares or signal), so the next victim mint returns too little; attacker pre-mints and
> dumps." This claim is handed to you pre-packaged after every such disclosure — run the kill test
> before you repeat it.

1. **Read the curve.** If the reserve ratio is fixed at 1 (100 %), the curve is **linear** and a
   mint→burn round trip returns ~the same tokens regardless of any prior "inflation". Verify with
   the actual mint *and* burn formulas — not with intuition, and not from the `tokensToSignal`
   helper alone.
2. **Compute the victim's round trip, not just the shares received.** In a linear pool the victim's
   shares redeem back to ~the same tokens. No direct transfer of value happens; only the *weight*
   (share of future fees/rewards) is diluted. "Victim receives fewer shares/signal" ≠ "victim
   loses funds".
3. **Grade honestly.** If the only harm is future fee/reward-share dilution, it does not clear a
   ">$1M user funds lost or stolen" bar. Report as a lead, never as Critical/High.
4. **Check the sibling paths, then the duplicate clause.** The reportable variant is usually the
   *unguarded sibling* (e.g. one function got a `_signalOutMin` / slippage param or a
   `require(!isCurated(target))` guard, its neighbours did not). But confirm it is not already a
   disclosed "known issue" — same root cause on a different function is often treated as a dup.

**Worked instance (The Graph).** `L2Curation` has `fixedReserveRatio = MAX_PPM` (100 %) ⇒ linear.
The freshly-fixed `L2GNS.publishNewVersion` slippage bug therefore did NOT yield a demonstrable
>$1M loss on analysis (round-trip invariance), and the sibling bridge-receive mints
(`finishSubgraphTransferFromL1`, `_mintSignalFromL1` — both `mintTaxFree`, no slippage) were killed
for the same reason plus duplicate risk.

---

## 9. SIGNATURE REPLAY

### Missing Nonce
```solidity
// VULNERABLE:
function permit(address owner, address spender, uint256 value,
                uint256 deadline, uint8 v, bytes32 r, bytes32 s) external {
    bytes32 hash = keccak256(abi.encodePacked(owner, spender, value, deadline));
    // MISSING: nonce not included → same signature usable multiple times
    require(ecrecover(hash, v, r, s) == owner);
}
```

### Missing Chain ID
```solidity
// VULNERABLE: signature valid on mainnet AND testnet AND all forks
bytes32 hash = keccak256(abi.encodePacked(params));
// MISSING: block.chainid not in hash → works on any chain
```

### Grep Patterns
```bash
grep -rn "ecrecover\|ECDSA\.recover" contracts/ -B20
# Check: does the signed hash include nonce + chainId + contract address?

grep -rn "nonce\|_nonces\|nonces\[" contracts/
```

---

## 10. PROXY / UPGRADE ISSUES

### Storage Collision
```solidity
// Implementation and proxy share storage layout
// Proxy slot 0: _owner
// Implementation slot 0: _initialized
// → writing to _initialized overwrites _owner
```

### Uninitialized Implementation
```solidity
// If implementation can be initialized directly → anyone becomes owner of implementation
// Attack: call initialize() on implementation contract → call upgradeTo() → replace logic
```

### delegatecall to User-Controlled Address
```solidity
function execute(address target, bytes calldata data) external onlyOwner {
    target.delegatecall(data);  // target is validated, but what if owner is compromised?
}
```

### Grep Patterns
```bash
# UUPS initialization protection
grep -rn "function initialize\b\|_disableInitializers\|initializer" contracts/

# Delegate call
grep -rn "delegatecall\b" contracts/ -B3 -A5

# Storage layout — proxy uses EIP-1967 slots?
grep -rn "0x360894\|EIP1967\|_IMPLEMENTATION_SLOT" contracts/
```

---

## 11. CROSS-CHAIN SETTLEMENT / BRIDGE ATTESTATION MISMATCH
> Distinct class: the bug is not in a contract, it is the DIFFERENCE between an
> off-chain attestor service and the on-chain program it credits. Applies to
> intent-settlement hubs, deposit-address bridges, solver relays.

One economic amount, computed twice — by the on-chain program (what the vault
received) and by the off-chain attestor (what gets minted on the hub). Diff both.

```bash
# classify the SOURCE of every credited field in the attestor:
grep -rn "amount:" src/services/attestation/vm/*/index.ts
```
event arg / balance-delta = usually fine · **raw instruction data or a
caller-supplied hint = red flag** · mixed handling across two paths of the same
adapter = the strongest signal (e.g. one path nets a fee, the other does not).

Worked instance (Relay 2026): Solana `deposit_token` credited the GROSS
instruction amount while the program transferred net and emitted the net value in
its `DepositEvent` → over-credit by the Token-2022 transfer fee. Bounded (S1),
because the attacker's own round trip was fee-negative — do not inflate a
credit-mismatch into "theft" without a demonstrated profit path.

Also in that reference: the `abi.encodePacked(chainId, address)` id-collision
brute-force over the live chain set, and recon via a reference oracle's public
`/documentation/json` route table.

**→ `references/cross-chain-settlement-and-attestor-audit.md`** — full class
write-up, source-classification table, fee-token variants per chain, recon steps,
and intent/bridge scope traps (solver/oracle-only paths are usually excluded).

**→ `references/multi-chain-deployment-audit.md`** — the FLEET view, for any
protocol deployed across dozens of chains. Get the authoritative deployment
inventory from the protocol's own `/chains` config API rather than from docs; then
(a) verify every advertised contract actually has bytecode on every chain it is
advertised for, (b) read `owner()`/`allocator()` on every chain and diff for
outliers, (c) detect the CREATE2 identical-address pattern (audit the code ONCE,
fleet-wide), (d) map funds-at-rest per chain to size severity, (e) recover verified
source from Sourcify, (f) fall back to dispatcher-selector extraction + 4byte
lookup when no source exists. Carries the harness pitfalls that cost real time
(thread the sweep with short timeouts, never name a helper after a stdlib module,
control-address check before believing an anomalous balance) and the reporting
discipline for consistency results, which are usually context rather than payable.
Worked against a 61-chain settlement protocol.

---

## 12. MOVE-VM BLACK-BOX AUDIT (no source repo, RPC only)

> Supra / Aptos / Sui. The target ships a frontend and an RPC and nothing cloneable.
> You still get the ABI, and usually you can EXECUTE the pure math.

**→ `references/move-vm-rpc-blackbox-audit.md`** — full recipe: reading a package's
`exposed_functions` + `structs`, the `view` execution endpoint and its argument
encoding, the no-`&signer` sweep, the Move-semantics inference, and the harness
faults that disguise themselves as contract bugs.

The three moves that carry the class:

1. **The no-`&signer` sweep.** In Move a function without `&signer` is callable by
   anyone. Sweep every module for `is_entry` functions whose params contain no
   `&signer` — that is your access-control shortlist.
2. **Then apply the semantics rule before calling any of them a bug.** A function
   with **no `&signer` and no `&TxContext` cannot learn who called it**, so it
   cannot pay the caller; any value it releases must go to an address it can name,
   i.e. an argument. `claim_bribes_for_address(victim, …)` credits `victim` and is a
   gasless claim-on-behalf helper, NOT theft. This one inference killed a would-be
   Critical. A function taking **both** `&signer` and an `address` is the shape worth
   reading closely — but you cannot settle it from the ABI; say so.
3. **Execute the math to prove invariants.** `view` calls give you dated evidence a
   code read cannot: bounds abort outside the domain rather than clamping,
   monotonicity across the sampled range, cross-consistency between sibling
   price-transition functions, a rounding flag whose two directions differ by
   exactly 1, and fee arithmetic that closes to the unit
   (`amount_in + fee == amount_remaining`). Negatives proven this way are
   deliverables.

**Enumeration is the hard limit — but read the payload route first.** `/resources` lists type
*names* only, yet `/resources/<TYPE>` returns the **full payload**, so a `SimpleMap`-shaped
resource (fee tiers, ACL, config, a pool-owner signer capability) reads out completely. A
`Table`/`SmartTable` returns only a `handle` and has no key-listing endpoint, so gauge/pool
addresses may stay unreachable even when the global counters read fine. A guessed address returning `weights(gauge) == 0`
is the *correct* answer for a **wrong address**, not evidence of "total_weight is
unsupported". If you invented the addresses, you have no finding — report what you
verified, what you could not and why, and that the ambiguity is your reach, not their
bug. Disclosed reports on the target often name the source path
(`sources/<module>.move`), which both proves source exists and doubles as a duplicate
check.

---

## 13. OFF-CHAIN SIGNED-GATEWAY LAYER (EIP-712 / Web3Signed consent APIs)

> Class 11 diffs an off-chain attestor against an on-chain vault. This class is the other
> off-chain half: the protocol's **own HTTP gateway/relay**, where grants and consent are
> created, approved and delivered, and where the signatures are EIP-712 typed data or an
> EIP-191 signed request header. On a consent/grant protocol this layer usually holds more
> reportable surface than the contracts do — and auditing only the contracts misses all of it.

The four tests that carry the class:

1. **Build the signatures yourself** from the vendor's own SDK constants (domain =
   name/version/chainId/verifyingContract) and probe the binding: forged signer, field swap after
   signing, delegate-for-another-owner, replay, pubkey↔address binding.
2. **Open registration.** Ask whether *you* can register an identity, app URL or server you do not
   control. If yes, score it as registry impersonation — and do not claim grants/fees follow unless
   you proved it.
3. **Consent hand-off.** Any `approve`/`webhook` step that trusts caller-supplied values (grantId,
   userAddress, scopes) is delivering an unverified grant. Prove it with an OOB collector **and** a
   `404` on the authoritative API for the fabricated grantId.
4. **Unauthenticated reads and triggers.** Balance/nonce lookups by query parameter, reconciliation
   endpoints that mutate state for any account, and any lookup that happens *before* signature
   verification (that ordering is a Low, not an IDOR, until you own a real ID that is not yours).

**→ `references/eip712-signed-gateway-authz.md`** — the signature-construction recipe (eth_account
typed-data + Web3Signed header), the canonical-body-hash traps, the full binding test matrix, the
finding shapes this layer produced with their honest severities, and the by-design checks that keep
a Low from being filed as a Critical.

## FOUNDRY POC TEMPLATE

> **A passing PoC is not proof until it has a control.** Two harness traps that make an
> exploit test lie to you, both hit for real on 2026-10-08:
> 1. a reentrant probe whose call **body** reverts reads as "the guard held" — the probe's
>    action must SUCCEED when it is allowed, so success/failure isolates the guard;
> 2. a single "it worked" test cannot separate the trigger from coincidence — ship the
>    matched pair (`test_control_*` with the trigger REMOVED, `test_*_exploit` with it).
>
> Assert the **observed** behaviour and let the comment carry the meaning
> (`require(bypassed, "guard held - if this fails the defect is FIXED, update the finding")`)
> so the suite goes green, pins the defect, and fails the day it is fixed. Worked example +
> skeleton: `references/reentrancy-guard-and-approval-poc.md`.

### The harness-fault reflex — an anomaly is YOUR bug until proven otherwise

When a probe aborts, or a value looks like a serious bug, **suspect the harness before the
contract.** Every item below produced a fake finding in one session and each was my own error,
not the target's:

| Symptom | Real cause |
|---|---|
| call returns empty / decode error | the arg was an **EOA**, not a deployed contract — point at an instance |
| `Yul exception: … 1 too deep in the stack` | you compiled with **your** defaults; the repo's `foundry.toml` sets `optimizer=true`, `runs=200` |
| every call in a family ABORTS | an input is **out of domain** — read the protocol's own min/max constants and stay inside them |
| a tuple slot looks like a 1-in / 1e12-out exploit | you misread which field it is (a "remaining unfilled" slot, not the output) |
| invariant "violated" in every case | you misread which token/flag a `bool` selects (two bools in one module: `roundUp` vs direction) |
| the control fails while the "exploit" passes | the control used input the contract legitimately rejects — make it **well-formed** |
| an `Option<T>` sweep "finds" something for **every** input | `{"vec":[]}` is `Option::None`. Every probe looks like a hit — a 112-pair pool sweep read as 112 pools found |

Copy the target's build settings, stay inside its declared domain, and write the control as a
call you *expect* to succeed. Then try to DESTROY the hypothesis by execution: seven
reading-derived hypotheses in one engagement, seven killed by a test. Reporting any of them
would have been a false positive — and against a program scoped to *direct financial loss
only*, a false positive costs credibility, not just time.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../src/VulnerableContract.sol";

contract ExploitTest is Test {
    VulnerableContract target;
    address attacker = makeAddr("attacker");
    address victim = makeAddr("victim");

    function setUp() public {
        // Fork mainnet at specific block
        vm.createSelectFork("mainnet", BLOCK_NUMBER);

        // Deploy or load target
        target = VulnerableContract(TARGET_ADDRESS);

        // Fund accounts
        deal(address(token), attacker, INITIAL_BALANCE);
        deal(address(token), victim, VICTIM_BALANCE);
    }

    function test_exploit() public {
        console.log("Attacker balance before:", token.balanceOf(attacker));

        vm.startPrank(attacker);

        // Step 1: Setup conditions
        // Step 2: Execute exploit
        // Step 3: Verify impact

        vm.stopPrank();

        console.log("Attacker balance after:", token.balanceOf(attacker));
        assertGt(token.balanceOf(attacker), INITIAL_BALANCE, "Exploit failed");
    }
}
```

### Key Foundry Cheatcodes
```solidity
vm.prank(address)           // next call from address
vm.startPrank(address)      // all calls from address until stopPrank()
vm.deal(address, amount)    // set ETH balance
deal(token, address, amount) // set ERC20 balance
vm.warp(timestamp)          // set block.timestamp
vm.roll(blockNumber)        // set block.number
vm.createSelectFork("mainnet", blockNumber)  // fork mainnet
vm.expectRevert(bytes)      // next call should revert
vm.label(address, "name")   // label for trace output
vm.assume(condition)        // fuzz: discard inputs where false
```

### Running Tests
```bash
# Run specific test
forge test --match-test test_exploit -vvvv

# Run with fork
forge test --match-test test_exploit -vvvv --fork-url $MAINNET_RPC

# Gas report
forge test --gas-report

# Coverage
forge coverage --report summary
```

---

## STATIC-ANALYSIS WORKFLOW (Solidity monorepo) + TWO FALSE-POSITIVE KILLERS

> Heavily-audited repos pin a solc the host's solc-select lacks, so default tool runs stall;
> and the two commonest ways a strong-looking lead dies are the round-trip accounting check
> and the duplicate-of-a-recent-fix rule. Full recipe + commands:
> `references/solidity-monorepo-static-analysis.md`

- Build once with `forge build` (it fetches the pinned solc into `~/.svm/<ver>/`), then run
  `slither . --solc "$HOME/.svm/<ver>/solc-<ver>" --filter-paths "node_modules|test|mocks"` per
  package. Do NOT use `slither . --foundry-compile-all` on a pinned-solc monorepo — it stalls on
  the solc download. Check each package's build system first (`foundry.toml` vs `hardhat.config.ts`).
- Add `forge test --summary` as a cheap coverage gate — monorepo unit tests usually fuzz
  (256 runs/case) and give real signal for ~zero authoring cost.
- **Kill-test every "inflation / value extraction" lead with the MINT→BURN round trip** before
  reporting. On a linear curve (reserve ratio = 100%) the round trip returns ~the same tokens
  regardless of prior inflation: the victim gets fewer *shares/signal*, not less *principal*.
  Compute it numerically at two pool sizes. "Diluted weight" alone does NOT meet a
  ">$1M funds lost/stolen" bar.
- **A second function sharing a root cause with a just-fixed GHSA is a likely DUPLICATE.** After
  finding a recent security fix in git history, siblings with the same root cause are usually
  rejected ("known issues out of scope", "rewarded once to the first reporter"). Only report with
  a DISTINCT proven impact + a PoC for *that* path. Otherwise kill it — do not inflate a lead.
- Write the tool-coverage ledger per class, not per tool name: `ran` / `not run + why` /
  `N-A for this scope`. For a pure on-chain target the web2 set (sqlmap/dalfox/nuclei/ffuf) is
  N/A; the web3 equivalents are aderyn, mythril, echidna, medusa, halmos/hevm, Certora,
  on-chain source verification, and fork simulation. If a tool can't run on the host, list it as
  not-run with the reason — never silently drop it.

## Related Skills & Chains

- **`meme-coin-audit`** — When the target is a meme coin / SPL token rather than a DeFi protocol. Workflow primitive: pre-dive kill signals diverge — this skill's "TVL < $500K skip" doesn't apply to meme coins where the rug check (mint authority, freeze authority, LP lock) is the entire audit; route to `meme-coin-audit` instead.
- **`triage-validation`** — When a contract finding is ready to be filed on Immunefi. Workflow primitive: Immunefi has its own report format, but the impact-validated, chain-end-to-end discipline of `triage-validation` still applies; run the 7Q gate against the Foundry PoC before submitting.
- **`report-writing`** — When writing the Immunefi report body. Workflow primitive: `report-writing`'s Immunefi template (with Foundry PoC, root cause code snippet, quantified economic impact) is the body skeleton this skill's findings feed into.
- **`offensive-osint`** — When auditing a protocol's off-chain attack surface (frontend, admin API, RPC gateways). Workflow primitive: on-chain audit is this skill's job; any web2 component of the protocol (web-frontend, admin panel, indexer API) routes to `offensive-osint` for recon.
- **`bb-methodology`** — When deciding whether to dive at all. Workflow primitive: PART 0 of `bb-methodology` confirms engagement (web3 bug bounty / private audit / smart-contract review); this skill's pre-dive kill signals replace the standard scoring rubric for that engagement type.

---

## Operator Notes (Claude-BugHunter)

### Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Pre-dive kill signals dihitung (TVL, audit count, LOC, payout formula) | $322M TVL + 5 audit + 0 temuan = pelajaran; jangan mulai tanpa skor |
| 2 | Repo reality checks 0–4 (live version, language, vendored split, compiler CVE, source-vs-bytecode) | Audit repo yang salah = sesi hangus (Zharta V1 vs V2) |
| 3 | Inheritance chain walk sampai storage/base contract | `unprotected-upgrade` FP klasik; modifier inherited tidak di-resolve slither |
| 4 | `forge test` PoC satu perintah, `assertEq` pada balance/state | Immunefi auto-reject tanpa PoC; PoC multi-step = downgrade |
| 5 | Attacker P&L eksplisit + single-party pool check | "Missing slippage" sering net ~0; OTC single-lender = by design |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

### 2026 sweep (bug class yang masih dibayar)

- **ERC-7579 modular account** — validator/module registry tanpa allowlist = arbitrary delegatecall. Probe: module install dengan address attacker, cek `onInstall` revert vs silent accept.
- **EIP-7702 delegation** — EOA delegate ke implementation attacker-controlled; `tx.origin`-based auth jadi sink. Probe: cek setiap `tx.origin` guard di kontrak yang bisa dipanggil oleh 7702-delegated EOA.
- **Permit2 / ERC-3009** — signature replay lintas domain: cek `chainId` + `verifyingContract` + nonce di setiap permit. Permit2 `allowance` tidak di-reset setelah transfer = double-spend.
- **Uniswap v4 hooks** — `beforeSwap`/`afterSwap` callback tanpa access control = price manipulation via hook contract. Probe: hook address attacker-controlled di pool initialize?
- **Restaking / LRT (EigenLayer-style)** — operator-set slashing condition yang bisa dipicu attacker; withdrawal delay bypass via queue manipulation.
- **Donation attack / first-depositor inflation** — ERC-4626 vault kosong, `deposit(1, 0)` → inflate share price → victim deposit rounding ke 0 share.
- **Sequencer-uptime oracle** — L2 app yang percaya `sequencerUptimeFeed` tanpa grace period = stale price saat sequencer down.
- **EIP-2535 diamond** — `diamondCut` tanpa `onlyOwner` pada facet replacement; storage collision antar facet.
- **zkVM proof verification** — public input yang tidak di-bind ke verification key; recursive proof reuse.

> Engagement-derived + 2026-specific additions to the vendored foundation.
> Wisdom from real authorized engagements + Phase 2 verification across
> this repo's 31+ skill-area live tests. The upstream content covers the WHAT;
> this layer covers the WHEN-IT-WORKS-vs-WHEN-IT-DOESN'T.

### Bug classes still paying in 2026

Flash-loan attacks remain top-paid on Immunefi (top 5 in 2024-2026 by bounty). The economic primitive — borrow $50M, manipulate price oracle, drain pool, repay — keeps reappearing because new protocols keep shipping with composability assumptions that don't hold under flash-loaned imbalance.

Reentrancy IS still paying because new protocols keep shipping with ERC-777 / hooks / callbacks. Don't assume the class is dead — the 2023-2025 paid corpus contains 40+ reentrancy bugs against post-Checks-Effects-Interactions codebases (cross-function reentrancy, read-only reentrancy via view functions called during state-mid-flight).

Oracle manipulation: still paid heavily but harder. Most projects use Chainlink price feeds now; the attack target is the SECONDARY oracle most projects also use (TWAP from a low-liquidity Uniswap V2 pair, the protocol's own internal oracle, a stale fallback path). Audit the failover chain, not just the primary feed.

### What's new since the vendored content was written

- **EIP-1153 (transient storage)** — introduced in 2024. New reentrancy classes: transient-storage reads cached across the same transaction can desync from persistent storage. Audit any `tload`/`tstore` usage for read-after-external-call.
- **EIP-7702 (Pectra hard fork 2025)** — added EOA-to-smart-account upgrades. New ATO-like primitives via re-delegation: an EOA signed-once can delegate to a contract that the attacker controls, then signature replay across delegations.
- **Account abstraction (ERC-4337 bundlers)** — paymaster sponsorship abuse and bundler griefing. Paymaster contracts that don't enforce strict sender allowlists drain on first call.
- **ZK-rollup bridge bugs** — proof-replay across rollups, off-chain prover compromise, sequencer censorship leading to forced-inclusion edge cases.
- **LST/LRT depeg dynamics** — liquid-staking and liquid-restaking tokens that assume 1:1 peg under loss conditions; oracle assumes peg, market reflects depeg, liquidation logic breaks.

### Tool stack for 2026

Foundry remains the test framework. `forge test --gas-report --debug` for invariant testing; `forge fuzz` for property-based testing; `forge inspect` for storage-layout audits. Slither + Echidna for static + fuzz. Mythril for symbolic execution on smaller contracts. tenderly.co for forking + simulation (best UX for replicating attacks against mainnet state).

For Solana: anchor framework, sealevel-attacks corpus (curated PoCs by anchor maintainers), soteria-sec / sec3 scanner. For Move (Aptos, Sui, Supra): when the source repo IS available — move-prover, `aptos move test`; when it is NOT and you only have the RPC — read the module ABI (`/rpc/v1/accounts/<pkg>/modules[/<mod>]`) and execute the pure math through the view endpoint (class 12 and `references/move-vm-rpc-blackbox-audit.md`), which is often the difference between a code-read hunch and dated evidence.

For cross-chain: hyperlane and LayerZero each have audit-tooling repos; bridge bugs require simulating both endpoints, not just one.

### Where pre-dive kill signals matter

TVL under $500K isn't worth the audit time unless the bounty floor is high. Audit firm already covered it = low ROI unless you find what they missed — look at the audit-report scope-exclusion section for what they EXPLICITLY didn't audit (oracles, governance, off-chain components, frontend, the admin path).

Multisig signers > 5 + timelock > 48h = low rug-pull risk; if your finding requires team-malicious assumptions, it's low-impact and likely out of scope per Immunefi's "centralization risk" exclusion. Read the program brief — most Immunefi programs explicitly downgrade or reject findings that assume admin malice.

### Reporting discipline

Immunefi requires Foundry PoC. Submission without PoC is auto-rejected. Submission with a PoC that requires manual setup ("first deploy this, then call that") usually gets downgraded — the PoC should be a single `forge test` invocation that proves the impact, with explicit `assertEq` on the drained balance / minted token / corrupted state.

Severity claims must use Immunefi's severity matrix exactly; don't invent severities. The matrix gates on direct economic loss percentage of TVL — a critical against a $500K protocol pays differently than a critical against a $500M one. Read the program's specific severity assignment before claiming Critical.

### Analyzer output is not evidence (triage discipline)

Every static-analyzer hit must be settled with a named reason before it counts — or it doesn't count.
- **`unprotected-upgrade` is the classic FP**: slither cannot resolve an `initializer` modifier that
  is INHERITED from a dependency (e.g. OZ `contracts-upgradeable` reached via a storage base contract),
  so it flags a properly-guarded `initialize`. Verify by walking the inheritance chain down to the
  storage/base contract and reading the dependency's real modifier definition under
  `node_modules/.pnpm/<pkg>@<ver>/node_modules/...`. Real case: `initialize(...) external onlyImpl initializer`
  where `onlyImpl = require(msg.sender == _implementation())` → calling through a public `Multicall`
  (delegatecall sets `msg.sender == proxy`) still reverts. FP.
- Common FPs with verified reasons: `arbitrary-send-erc20` (generic `transferFrom(from,...)` helper),
  `reentrancy-*` (external call is a trusted token burn/push and the mutator is role-gated),
  `divide-before-multiply` (documented round-down), `calls-loop` (view helper), `unchecked-transfer`
  (token reverts on failure), `encode-packed-collision` (string URL concat), `shadowing-state`
  (`private constant`), `uninitialized-state` (mappings/structs).
- Full table + the solc-pin slither stall fix: `bug-bounty/references/web3-static-analysis-triage.md`.

### Prove the economics before claiming theft

A "missing slippage / pool inflation" pattern LOOKS like theft but usually isn't. Establish the pool's
price invariant first: in a constant-price/linear pool (`reserveRatio = MAX_PPM` ⇒ signal ∝ tokens) the
mint→burn round-trip returns ~the same tokens **regardless of prior inflation** — the victim gets fewer
SIGNAL but redeems ~the same TOKENS, so there is no fund loss. Compute attacker P&L explicitly
(`claim − (initial_mint + injected)`); if it nets ~0 minus a burned protocol cut, there is no reportable
economic attack. Then check duplication: if the team already fixed the same root cause (git history,
CHANGELOG, an audit PDF added in the PR), a sibling path is a **known issue → out of scope** unless you
have a PoC showing net victim loss greater than the attacker's cost.

**Before claiming a "socialized loss / unfair write-off", check whether the pool is multi-party at
all.** An asymmetry that would be a real finding in a shared pool can be plain by-design in a
single-party one. Zharta OTC `claim()` looked like a genuine economic bug: a lender claims the NFT
**without paying**, and the accounting (`fundsInvested -= principal`, `collateralClaimsValue +=
principal`) shrinks the pool total that every share is priced against — so in a multi-lender pool,
one person takes the asset while everyone eats the dilution. It was not a finding, for one checkable
reason: OTC pools hold exactly **one** lender. `lender: public(address)` is set once in `initialize()`
(no setter exists), `_deposit()` and `_withdraw_accounting()` both `assert msg.sender == self.lender`,
and `lenderFunds()` returns an empty struct for anyone else. The write-off lands on the same person
who takes the NFT. By design.

The mechanical check, before filing any write-off / dilution / unfair-share claim:
```bash
grep -rn "public(address)\|public(HashMap" <Pool>.vy | head    # a single named party var?
grep -n "msg.sender == self.lender\|== self.owner\|== self.vault" <Pool>.vy  # deposit/withdraw gated to one addr?
# does a funds/balance getter return empty(Struct) for everyone except that addr?  -> single-party
```
If the pool is single-party, kill the claim — or downgrade it to a centralization/design note with
the condition spelled out. Filing it as an economic bug is a guaranteed false positive against a
program scoped to direct financial loss.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Skill ini adalah audit class-level; yang membuat temuan Critical adalah **fund-loss path yang
bisa dicapai penyerang tanpa hak istimewa**:

| Kelas | Critical kalau |
|---|---|
| 1. Accounting state desync | share/asset tidak konsisten → insolvency terbukti |
| 2. Access control | fungsi privileged bisa dipanggil siapa saja |
| 3. Incomplete code path | update/refund path melewatkan cek yang punya jalur sibling |
| 4. Off-by-one / boundary | batas yang salah → overdraft / over-mint |
| 5. Oracle manipulation | harga bisa digeser → likuidasi paksa posisi sehat |
| 6. ERC4626 vault | exchange rate manipulable → victim dapat 0 share |
| 7. Reentrancy | memindahkan dana lewat callback |
| 8. Flash loan | oracle dimanipulasi dalam satu tx → drain |
| 9. Signature replay | signature valid untuk lebih dari yang dimaksud signer |
| 10. Proxy / upgrade | upgrade tanpa guard / storage collision / impl hijack |
| 11. Cross-chain settlement | attestor under-bound → mint ganda |
| 12. Move-VM black-box | authz bisa di-bypass lewat RPC |

**Kalibrasi wajib:** severity mengikuti **Immunefi VSS v2.3** per domain, BUKAN CVSS. Batas
triage: *principal vs unclaimed yield* (Critical vs High) dan *temporary vs permanent freeze*.
Sebelum klaim theft, buktikan ekonominya: attacker P&L eksplisit, single-party pool check, dan
duplication check (git history / CHANGELOG / audit PDF). Analyzer hit tanpa alasan terselesaikan
= bukan temuan.
