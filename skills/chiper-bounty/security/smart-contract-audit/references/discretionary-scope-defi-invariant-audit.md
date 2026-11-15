# DeFi protocol audit against a DISCRETIONARY bug-bounty scope

Session-proven method (Klima Protocol v1.0.0 on Base, 2026-11 — a 3-diamond + 8-proxy carbon-credit
protocol, ~291k tCO2e live). Use this when the programme pays only for a **named impact set**
(fund loss / unauthorised mint / admin takeover / pricing-or-accounting manipulation) and explicitly
excludes griefing, gas, style, "theoretical findings", and privileged-access paths. In that regime the
job is not "find any bug" — it is **prove or disprove a small number of economic invariants**, and
write the negatives down as deliverables.

---

## 0. Read the reward clause as a SPEC, not as boilerplate

Extract the exact verbs the programme pays for and turn each into a testable invariant. Klima's clause
("steal or permanently destroy user or Protocol funds, mint $kVCM or $K2 without authorisation, take
over admin/owner privileges or force a malicious upgrade, or extract value by manipulating AAM pricing
or accounting") decomposes to:

| clause | invariant to test |
|---|---|
| steal/destroy funds | no path moves value out without paying in the same value |
| unauthorised mint | every mint entrypoint is role-gated AND the amount is bounded by real backing |
| admin takeover / forced upgrade | no permissionless function reaches an upgrade authoriser |
| pricing/accounting manipulation | **no free round-trip**: cost(retire X) >= minted(swap X) for all X |

The last one is the highest-yield test on any AMM/quoter protocol and it is cheap — see §2.

## 1. Privilege-chain reachability (do this before reading the money path)

Role-based protocols form a graph; a Critical lives where a **permissionless entry** reaches a
**privileged sink**. Build the graph explicitly, both halves:

```bash
# half A: who holds what (hasRole over every role id x every contract address)
for role in $(seq 1 16); do for a in $CONTRACTS; do
  cast call $ACCESS_MANAGER "hasRole(uint64,address)(bool)" $role $a --rpc-url $RPC; done; done

# half B: what does each state-changing function require (grep the modifiers)
grep -n "function .*external" src/contracts/X.sol      # then read each modifier
grep -rn "_authorizeUpgrade" src/ --include=*.sol -A1  # every upgrade gate
```

Klima's graph: `AAM (permissionless swap) → holds LIQUIDITY_MANAGER → CarbonLedger → holds
SYSTEM_ADMIN → can upgrade CarbonClassVault`. That *looks* Critical. It is not, because **half B**
shows every CarbonLedger state-changing function is `onlyAdmin*/onlyMaturityExecutor` — no
permissionless function reaches the sink. **Record the chain AND the kill.** A chain with no
permissionless entry is a non-finding; writing it down stops the next auditor re-deriving it.

Sub-trap: a contract can hold a role that gates *its own* upgrade. `CarbonLedger._authorizeUpgrade` is
`onlyAdminOrManager` (roles 2/4) while CarbonLedger holds only role 1 — so it **cannot self-upgrade**.
Check the holder's own role set against its own gate before claiming a self-escalation.

Sub-trap 2: a factory that calls `vault.upgradeTo()` needs SYSTEM_ADMIN on the vault, so the multisig
**temporarily grants then revokes** the role around the upgrade tx. Finding the factory holding *no*
role right now is correct, not a bug — the CHANGELOG/multisig-execution log shows the grant/revoke pair.

## 2. The no-arbitrage invariant sweep (the highest-yield test)

For any protocol with a swap entrypoint (X → token) and a retire/redeem entrypoint (token → X), the
protocol spread must be non-negative in **both** directions. Write one Foundry fork test that, for
**every class and a dense amount sweep**, compares `swapQuote(amt).minted` against
`retireQuote(amt).cost`:

```solidity
for (uint256 c; c < nClasses; c++) {
    uint256 tot = IVault(classes[c].vault).getTotalTonnes();
    for (uint256 k = 1; k <= 20; k++) {              // 0.5% .. 10% of vault, 20 points
        uint256 amt = (tot * k) / 200;
        if (amt < MIN) continue;
        (uint256 t, uint256 minted,,) = IAAM(AAM).getSwapQuote(vault, credit, tokenId, amt, 0, EMPTY);
        if (t == 0) continue;
        (,, uint256 cost,,) = IAAM(AAM).getRetirementQuote(vault, credit, tokenId, amt, EMPTY);
        if (cost < minted) { violations++; /* log class + amounts */ }
    }
}
```

Run it **3×** (the operator's standing rule: every claim re-verified >=3x) — cheap, and it converts
"looks fine" into "300 quote-pairs, 0 violations". Also test the **split-swap** variant (one big swap
vs N sequential smaller swaps): if splitting is *more* profitable, that is a pricing manipulation. On
Klima it was strictly worse (single 50 t → 140,936 kVCM vs 5×10 t → 140,618) — a clean negative.

**Direction matters — always state which way an anomaly errs.** A stale rate-limiter snapshot sitting
*above* the real balance only *lowers* the payout (safe direction) because the quote denominator is
`max(real, effective)`. Write the direction into the finding, or a non-issue reads as a bug.

## 3. Enumerate the permissionless surface, then the gate that hides the rest

```bash
grep -n "function .*external" src/**/*.sol | while read l; do ...; done   # then classify each modifier
```
On Klima only **two** entrypoints were unauthenticated (AAM swap, RA retire); everything else sat
behind a zkMe KYC gate (`whenVerified`). Note the inverted-guard shape:
`if (!config.zkMeRequired) revert ZkMeRequired();` means verification is required when the flag is
**true** — read the flag, don't assume the name. Then spend the budget on the two live entrypoints.

## 4. Negative-result discipline (this is most of the deliverable)

For a discretionary scope, "no Critical found" is a legitimate outcome **only** if the negatives are
enumerated with the test that produced each. Write them as a numbered list, each with the guard that
killed it:

1. no unauthorised mint — mint entrypoints role-gated; amount = quote bounded by real backing
2. no free round-trip / arbitrage — 300 quote-pairs, 0 violations (§2)
3. no coupon abuse — `reservedTonnes == 0`; issuer roles are admin-only; `validateCouponOwnership`
   forces `from == msg.sender`
4. no cross-user theft — `from` forced to `msg.sender`; third party cannot spend another's approval
5. no admin/owner takeover from unauth surface — privilege chain unreachable (§1)
6. no accounting desync — `totalTonnes == liquidTonnes + Σ maturityTonnes`; echidna 30k calls, 5/5
7. no reentrancy — every value-moving entry is `nonReentrant` (aderyn's H-2 instances verified guarded)

Then a **Residual risk / coverage gaps** section: which path is not live (Klima's forward-pricing had
all discount factors == 0, so forward swaps revert by design → any forward finding is *theoretical* and
outside the rewarded set), which tools were not run (medusa, halmos) and why. A ledger with no gaps is
implausible; an explicit gap list is what makes the clean rows credible.

## 5. Scope-reading traps specific to this shape

- The docs "Contract addresses" page may list only tokens + fair-launch. The real deployment map lives
  in the repo (`protocol-config/<chainid>/protocol-config.toml` + `classes/*.toml`). Read the repo.
- A "third-party" contract in the scope exclusion list may in fact be **protocol-owned** (same owner
  multisig). Check `owner()` before excluding it — Klima's RetirementAggregator was owned by the same
  admin Safe, so it was in scope and its facets were pulled from the explorer and reviewed.
- Verify the deployed code IS the repo code before auditing it: a PUSH4 selector scan of live
  `cast code` vs `forge inspect <C> methodIdentifiers` over every contract is fast and gives a
  one-line "0 missing across 14 contracts" claim. (`scripts/deployed_vs_source_selector_diff.py`.)

## 6. Ordering / "first-of-day" asymmetries: trace branch SYMMETRY for BOTH paths before claiming

When you suspect a timing/ordering asymmetry ("retire-first vs swap-first leaves different daily
state", "the first swap of the day prices differently than later swaps"), do NOT present it as a
"closest-to-real lead" or "future hardening note" until you've traced EVERY branch of the governing
`if/else` for BOTH entry paths. Two recurring patterns usually kill the claim outright:

1. **The symmetric branch.** The imagined divergence doesn't exist because both paths enter the same
   branch. Klima's `_resolveClassBalancePaths` branch 3 (`stored==0 && discountFactors.length>0`) calls
   `_getDiscountedForwardTonnage(isLiquidSwap=true)`, and swap AND retire both pass `isLiquidSwap=true`,
   so both return the same `Σ discounted(forwards)`. The retire path does NOT write the stored
   forward-balance to 0 — the "retire poisons the stored value to 0" hypothesis was wrong; that reset
   only lives in the branch-4 fallback (DFs absent), which I had wrongly generalised.
2. **The divergent branch is gated on dormancy that also kills its own precondition.** The one true
   swap-vs-retire divergence (branch 4: retire→0 vs swap→`totalTonnes-liquidSupply`) requires
   `discountFactors.length==0`; but when DFs are 0, forward swaps revert (`NoDiscountFactorForMaturity`)
   → no unprivileged actor can create forward tonnage → the branch is a no-op unless an admin seeds
   forwards directly (`addCreditLiquidityToClassVault(maturityId>0)`, `onlyAdminOrLiquidityManager`).

When the operator presses *"combine the leads"* / *"can't you fork-test it?"*, the right move is the
**precise branch re-trace** — it runs before any fork test and self-corrects — or a `vm.store`-injected
fork test that sets the dormant preconditions into their EIP-7201 slots. Run the re-trace FIRST and
self-correct the finding rather than defending the speculative chain. A dormant edge is usually dead in
**three layers** (no writer · reverting entrypoint · no permissionless way to create the precondition);
check all three before calling anything "future-exploitable". Self-correcting a finding costs less
trust than over-claiming a hardening note.
