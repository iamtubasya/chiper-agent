# Reentrancy guard: check whether it is DEPTH-COUNTED

A reusable check for ANY Solidity target with a `nonReentrant` modifier. Found live and
exploitable on Relay v3 Router (`0xb92fe925…`, Base) 2026-10-08 — and it generalises,
because the bug is a *pattern*, not a one-off.

## The pattern in one line

A guard that stores the caller in one slot and **clears it on every exit** is disarmed the
moment one permitted nested frame completes. After that, every subsequent address passes.

## How to spot it (30 seconds, no tooling)

```bash
# the whole question: does the exit path know whether it was the OUTERMOST frame?
rg -n "_nonReentrantBefore|_nonReentrantAfter|modifier nonReentrant" -A6 <target>.sol
```

**VULNERABLE** — exit is unconditional, entry overwrites unconditionally:

```solidity
modifier nonReentrant() { _nonReentrantBefore(); _; _nonReentrantAfter(); }
function _nonReentrantBefore() private { ...; tstore(SLOT, sender); }        // always writes
function _nonReentrantAfter()  private { ...; tstore(SLOT, address(0)); }    // always clears
```

**SAFE** — only the outermost frame owns the slot:

```solidity
modifier nonReentrant() {
    bool isOutermostCall = _nonReentrantBefore();
    _;
    if (isOutermostCall) { _nonReentrantAfter(); }
}
function _nonReentrantBefore() private returns (bool isOutermostCall) {
    ...
    if (storedSender == address(0)) { tstore(SLOT, sender); return true; }
    return false;                     // nested: neither overwrite nor clear
}
```

Equivalent storage-based variants (`sload`/`sstore`) have the same defect — check the
`_NonTstore` twin of any contract, they often differ.

## Reading the guard's allow-condition

Guards of this shape usually permit **two** senders:

```solidity
if (storedSender != address(0) && storedSender != sender && sender != address(this))
    revert InvalidMsgSender(storedSender, sender);
```

So a nested entry is allowed when `sender == storedSender` (the original caller) **or**
`sender == address(this)` (the contract calling itself). Both are reachable from a normal
multicall — which is why the disarm is trivial to trigger:

- **contract self-call** — any `calls[i].target == address(contract)`; for a router that
  means the documented `cleanup*` step
- **same-sender reentry** — a shared entry contract (e.g. an approval proxy) calling back in

## Proving it (Foundry template)

Three tests, and the CONTROL is the one that makes the finding real. Without it you cannot
tell "the guard blocked us" from "the body reverted for an unrelated reason".

```solidity
/// 1. CONTROL - no nested frame first. Must be REJECTED.
function test_control_reentryIsBlocked() public { ... assert blocked ... }

/// 2. MECHANISM - nested frame completes, then an unrelated address enters.
function test_nestedFrameDisarmsGuard() public {
    // calls[0]: contract self-call (allowed) that COMPLETES
    // calls[1]: unrelated contract reenters the guarded function
    // assert it SUCCEEDED -> guard was disarmed
}

/// 3. IMPACT - the reentry actually moves funds.
function test_inFlightFundsAreStolen() public { ... assert balance moved ... }
```

### Two traps that waste hours

1. **The reentrant call must succeed when the guard allows it.** Using
   `cleanupErc20s(...)` with an empty contract balance reverts inside `safeTransfer`, the
   `try/catch` catches it, and you wrongly conclude the guard held. Use a no-op that
   succeeds: `cleanupNative(0, addr, "")` with a zero balance.
2. **A `catch` cannot distinguish causes.** Always add the control and assert on the
   *observable* outcome (did the reentry succeed, did the balance move) — never on
   "it reverted".

## Reproduce against the DEPLOYED bytecode, not a local tree

A recovered source can be stale. Fork the chain and run against the live address:

```bash
forge test --fork-url <rpc> --match-path test/Live.run.sol -vv
```

That is what turns "the repo has this bug" into "the contract that holds funds has this
bug today". For Relay the two disagreed: `main` carried the fix (PR #62) while the
deployed router did not.

## When the fix exists but is not deployed

Check this before writing the report — it changes the framing, not the validity:

```bash
curl -s "https://api.github.com/repos/<org>/<repo>/commits?path=<guardfile>&per_page=5" \
  | grep -E '"date"|"message"'
```

Compare the fix commit date with the contract's deployment date (Sourcify
`deployment.blockNumber` → `eth_getBlockByNumber`). A fix merged months after deployment and
still absent on-chain is a **deployment gap**: funds are at risk regardless of who knew.
Say so plainly in the report instead of pretending it is novel.

## Escalation: is the trigger reachable without victim cooperation?

The strongest form of this finding needs **no** cooperation and **no** attacker address in the
call list — only that attacker-influenced code executes during the multicall. For a router
that moves arbitrary tokens, a **transfer hook** qualifies:

```solidity
function transfer(address to, uint256 a) external returns (bool) {
    _maybeReenter();        // fires while the guard is disarmed
    ...
}
```

Test it. If a hooked token in the route can sweep the in-flight balance, the finding is
High and the threat model writes itself: any token in the route is sufficient.

## Checklist

- [ ] Does `_nonReentrantAfter()` clear unconditionally? (`isOutermostCall` absent?)
- [ ] Is there ANY path where a nested `nonReentrant` frame completes mid-call?
      (self-call, shared entry contract, `calls[i].target == address(this)`)
- [ ] Does the contract hold value/funds for the duration of the call? (in-flight balance)
- [ ] Can attacker-influenced code run in that window? (token hook, callback, counterparty)
- [ ] Control test present and asserting the OBSERVABLE outcome?
- [ ] Verified on the DEPLOYED address via fork, not just the repo?
- [ ] Compared fix-commit date vs deployment date before claiming novelty?
- [ ] **Multi-chain: mapped every deployment before writing the report?** (see below)

## Multi-chain blast radius — do this BEFORE writing the report

A protocol that ships the same bytecode to N chains means one finding is N findings, and a
report that says "this contract" when it is 22 contracts understates it. But the opposite
error is worse: claiming all N when only some are affected. Both mistakes are avoidable.

### 1. Find the authoritative deployment registry

```bash
# protocol repos usually carry one
find . -iname "addresses.json" -o -iname "*deploy*" | head
# e.g. deployments/v3/addresses.json -> [{name, chainId, relayRouter, ...}, ...]
```

Enumerate **unique addresses**, not chains — a CREATE2 deployment gives one address for many
chains, which immediately tells you the blast radius shape:

```python
import collections
c = collections.Counter(e["relayRouter"].lower() for e in json.load(open("addresses.json")))
# -> {'0xe6b7...': 54, '0xb92f...': 22}   two code versions, two risk classes
```

**The registry is not the truth about production.** On one engagement the registry named
router A for a chain while the protocol's own quote API returned router B in live order data.
Treat the registry as a *starting point* that enumerates candidates, never as evidence of what
is deployed or in use.

### 2. Prove what is live, from the protocol's own API

```bash
curl -s -X POST https://api.<protocol>/quote -H 'Content-Type: application/json' -d '{...}' \
  | grep -oE '0x[a-fA-F0-9]{40}' | sort -u
```

Addresses appear ABI-padded inside calldata/extraData (`0x000...0000b92fe925...`), so grep for
the *lowercase hex body*. Whichever address the live quotes reference is the one that matters;
if the registry disagrees, that contradiction belongs in the report (it is a finding in itself —
a stale registry sends integrators to the wrong contract).

### 3. Verify per-chain by BYTECODE HASH, not by forking every chain

Forking 22 chains is slow and most public RPCs will flake. The cheap, equally rigorous test:

```python
# eth_getCode on each chain, sha256 the result, compare to a chain you already proved
# identical hash + identical length  =>  identical code  =>  identical behaviour
```

Report it as three buckets, never two:

- **verified identical** (same sha256 as the proven-vulnerable chain) — these inherit the finding
- **verified different** — these do not
- **unreachable** — no working public RPC/explorer responded

The third bucket is an **access limit, not a finding**. Say so explicitly. Do not fold
"couldn't reach it" into either conclusion, and do not let a reader assume it.

### 4. Keep the control in the probe

A per-chain probe that only asserts "the bug happened" cannot distinguish a fixed contract from
a broken fork. Every chain probe needs the same control as the local one: without the
precondition, the exploit must FAIL. If the control fails, the result is **INCONCLUSIVE** —
even if the exploit "passed". That is how a flaky RPC gets caught instead of being reported as
a live vulnerability.

### 5. Traps that cost time here

- **Verdict inversion.** A test named `test_defect_*` that *passes* means the defect is present.
  Getting this backwards silently reports every affected chain as safe. Re-read the assertion
  direction before trusting a summary table.
- **`address constant X = 0x...` fails to compile** when the registry stores lowercase addresses
  (Solidity enforces EIP-55). Python's `hashlib.sha3_256` is **NIST SHA-3, not keccak256**, so
  hand-rolling the checksum is wrong too. Write `address(uint160(<decimal>))` and sidestep it.
- **Binary-searching a deployment block via `eth_getCode` drifts to the chain head** when the RPC
  rate-limits (empty result reads as "no code" → search walks forward). Confirm the RPC answered
  before trusting a block number; a "deployed 91 blocks ago" answer on a year-old contract means
  the search is broken, not that the contract is new.
- **`getLogs` over large ranges on free RPCs silently returns nothing.** Zero logs is not
  evidence of no activity. Prefer the protocol's API or an indexer for usage questions.
- **Explorer APIs are worth trying when RPCs fail** (`/api/v2/addresses/<addr>` on
  Blockscout-style hosts), but do not burn an hour on 14 chains — log them as unreachable and
  move on. The report is stronger for naming the limit than for guessing past it.
