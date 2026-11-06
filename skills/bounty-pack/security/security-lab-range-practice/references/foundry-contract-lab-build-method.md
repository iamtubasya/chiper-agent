# Building a Web3 Contract Lab (Foundry) from a Hunt Skill's Probe Table

> Method extracted from the 2026-10-27 session that built 8 calibration suites / 48 tests
> covering every web3 hunt skill (`D:/isplab/web3-lab`). This is the contract-world counterpart
> to the PortSwigger loop in the parent skill: for web apps you *download* a lab, for contracts
> you **build** one, because the thing you need to verify is a specific probe's claim.

## When to use

- A web3 hunt skill has a "Minimum 5 probes" table and you want to verify the probes actually
  fire before trusting them on a live target.
- You wrote a severity claim and want a number behind it instead of a described pattern.
- A hunt skill's framing feels plausible but untested ("module install = arbitrary delegatecall").

## Setup — no Docker, no ports

```bash
mkdir -p <lab>/src/vulnerable <lab>/test
cd <lab> && forge init --no-git --force .
rm -f src/Counter.sol test/Counter.t.sol script/Counter.s.sol
```

`forge init` clones `forge-std` into `lib/`. One network step, once. Contract labs need no
image, no container, no RAM overhead — this is strictly cheaper than the Docker ranges.

## The five-step build

### 1. Take the probe table verbatim, one test per row

Do not invent probes. The point is to test the skill's own claims, so a probe that turns out
wrong is a correction to the skill — which is the actual yield.

```
| # | Probe (from skill)               | -> test_ProbeN_<whatItProves>()
| 1 | installModule with attacker addr | -> test_Probe1_UnrestrictedModuleInstall()
| 2 | empty-signature path             | -> test_Probe2_EmptySignatureAccepted()
```

### 2. Plant exactly the bug the probe hunts — comment the ABSENCE

One vulnerable contract per skill. The missing line is what a future reader needs:

```solidity
// BUG 2: missing `allowance[from][token][msg.sender] -= amount;`
function transferFrom(address from, address token, address to, uint256 amount) external {
    require(allowance[from][token][msg.sender] >= amount, "insufficient allowance");
    // <- the decrement that should be here is gone
}
```

### 3. Write the CONTROL beside every vulnerable path (non-negotiable)

For each probe, also implement the **FIX shape** in a sibling contract and assert the fix
*holds*. A probe with no control proves nothing — it may be passing because the harness is
broken, not because the bug is real.

```
test_Probe1_UnrestrictedModuleInstall() -> vulnerable accepts; SafeAccount reverts
test_Probe2_AllowanceNotDecremented()   -> spends twice;      SafePermit2 reverts
```

**Decision rule:** if the control also "fails", the harness is wrong, not the contract. Settle
that before writing any skill update.

### 4. Assert measured numbers, and log them

```solidity
// weak: assertTrue(gained > 0)
assertEq(gained, 1000e18);
assertLt(victimShares, 500e18 / 2);
emit log_named_uint("attacker net gain", gained);   // -vv output becomes the evidence you paste
```

### 5. Feed corrections back into the calibrated skill

Append to that skill a `## Lab calibration (<date> — <lab path>, N/N probes passed)` section
containing: probes confirmed as written, probes whose **framing was wrong** plus the corrected
framing, the measured numbers, and class-specific harness traps.

A calibration run with zero corrections is suspicious — either the probes were already precise
or the tests were too weak to tell.

## Harness traps that cost real time

Each of these produced a false "failure" that looked like a contract bug. Read before writing
the first test.

| Trap | Symptom | Fix |
|---|---|---|
| `sload(slot)` inside a test | reads 0 / garbage | it reads the **test** contract's storage. Use `vm.load(address(target), bytes32(slot))` |
| Assuming slot numbers | assert fails on a slot never written | dump slot 0..5 with `vm.load`, assert against **measured** layout |
| `immutable` in the target | expected var "missing" from storage | immutables live in **bytecode**; slot 0 is the first *non-immutable* state var |
| Foundry default `block.timestamp` | `panic: arithmetic underflow` | default is 1. `vm.warp(1_800_000_000)` in `setUp()` before any `block.timestamp - N` |
| `vm.prank` across two calls | second call runs as wrong sender | prank covers **one** call. Separate pranks, or a helper that books state for an explicit account |
| Mock simpler than the real interface | check passes silently | mock must return the **same tuple shape** (Chainlink uptime is a 5-tuple, not 2) |
| Decimal mismatch | every LTV comparison meaningless | 8-dp oracle vs 18-dp collateral needs explicit `× 1e10` |
| Proxy facet missing a selector | garbage return that looks like "no collision" | every selector used must be cut — **setter AND getter** |
| `delegatecall` writes `address(this)` | expected module address, got the account | inside delegatecall `address(this)` **is** the caller. That is usually the stronger finding |
| Callback into `msg.sender` (`unlock`-style) | `unlock failed` | the caller must expose the named function |
| Delta booked to caller | expected delta absent | swap AND unlock must originate from the **same** contract |
| Pool not seeded before slashing | `totalPooled -= x` underflow | deposit in `setUp()`, then recompute expected numbers **after** seeding |

## Verification

```bash
forge test                                 # all suites
forge test --match-contract <Suite> -vv    # probe + logged numbers
forge test --match-test test_ProbeN -vvvv  # full trace when a probe misbehaves
```

Green across the whole lab is the gate before any skill gets a `## Lab calibration` section.

## Report integrity rule

The lab exists to make claims falsifiable. When a test disagrees with what the skill says, **the
test wins** — update the skill. Never weaken an assertion to make it pass without first proving
the *assertion* (not the contract) was wrong.

## What calibration actually changed in practice

Four examples of the method paying for itself, to calibrate expectations that this is not
bookkeeping:

- A framing of "attacker steals everything" became "attacker nets 50% of the donation, victim
  loses 100% of the deposit". The report wording has to say *victim loss*, not *attacker gain*,
  or a triager can refute it by pointing at the attacker's own capital outlay.
- A 33% loss (fee-on-transfer desync) was hidden behind the phrase "dust". It was not dust.
- A "nonce-after-call = replay" claim did **not** reproduce on a naive reentrant call, because
  the re-entrant `msg.sender` is the callee, not the owner. The ordering bug is real and
  measurable, but exploitation needs a second path that carries the same `msg.sender`. Writing
  the claim without that path is refutable.
- "Pool ABI skew check" module takeover turned out to be **stronger** than the skill said: any
  module with a state variable at slot 0 clobbers `owner`, with no purpose-built payload needed.
