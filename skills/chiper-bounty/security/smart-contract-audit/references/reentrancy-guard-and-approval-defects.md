# Reentrancy-guard and approval defects: finding them, and proving them

Source: auditing Relay (relay.link) **v3 Router, live on Base**
(`0xb92fe925DC43a0ECdE6c8b1a2709c170Ec4fFf4f`, `evmVersion: cancun`), 2026-10-08.
Two defects, 11 PoC tests, all verified against the **deployed** bytecode via a fork.

Read this when a contract has a `msg.sender`-keyed reentrancy guard, or a
permissionless `cleanup*` / `rescue*` / `sweep*` family.

---

## 1. Bug class — a non-depth-counted guard can be DISARMED mid-call

### The shape to grep for

```solidity
modifier nonReentrant() {
    _nonReentrantBefore();
    _;
    _nonReentrantAfter();          // <-- runs for EVERY frame, including nested ones
}
function _nonReentrantBefore() private { ...; tstore(SLOT, msg.sender); }  // always overwrites
function _nonReentrantAfter()  private { ...; tstore(SLOT, address(0)); }  // always zeroes
```

Check: `storedSender != address(0) && storedSender != sender && sender != address(this)`.
That third clause — **"allow the contract to reenter itself"** — is what makes the defect
reachable: a router self-call passes, then its exiting `_nonReentrantAfter()` **wipes the
slot**, and every later entry in the same transaction sees `storedSender == 0` and passes
the check. The guard is a flag, not a depth counter, and nested frames destroy it.

### The FIXED shape (compare against it)

```solidity
modifier nonReentrant() {
    bool isOutermostCall = _nonReentrantBefore();
    _;
    if (isOutermostCall) { _nonReentrantAfter(); }     // only the outermost clears
}
// _nonReentrantBefore: if (storedSender == address(0)) { tstore(SLOT, sender); return true; }
//                      return false;                 // nested frames must not overwrite
```

If the deployed code zeroes unconditionally and the repo's does not, that difference *is*
the finding (see §4).

### Trigger — the contract's OWN documented usage arms the bug

`cleanupNative` / `cleanupErc20s` are usually meant to be **included in the multicall as a
call whose `target` is the router itself**:

```solidity
calls[0] = Call3Value({target: ROUTER, allowFailure: false, value: 0,
                       callData: abi.encodeWithSignature(
                           "cleanupNative(uint256,address,bytes)", 0, refundTo, "")});
```

`msg.sender` at that inner entry is `address(this)`, so it is allowed, and on exit the slot
is zeroed. Everything the multicall touches *afterwards* runs with the guard down.

### Impact — in-flight funds become stealable

The protected asset is the router's **transient balance**: tokens sitting in it for the
duration of a multicall. Once disarmed, any address that gets code executed later in that
transaction can call a `cleanup*` function and redirect that balance. Measured: 5 000e18
swept to the attacker.

---

## 2. Bug class — a dangling, unbounded approval in a permissionless cleanup

```solidity
uint256 amount = amounts[i] == 0 ? IERC20(token).balanceOf(address(this)) : amounts[i];
if (amount > 0) {
    IERC20(token).approve(to, amount);     // never reset; return value unchecked
    (bool success, ) = to.call(data);
    if (!success) revert CallFailed();
}
```

Two independent problems:

1. **The approval is never revoked.** It outlives the transaction.
2. **An explicit `amounts[i]` bypasses the balance check.** Passing
   `amounts[i] = type(uint256).max` grants an unlimited allowance *while the contract holds
   nothing*, so the grant is invisible on-chain and no monitor fires.

An unprivileged caller then runs `approve(attacker, type(uint256).max)` for free, and keeps
it forever — as long as the contract later receives that token, the attacker pulls it with a
plain `transferFrom`.

Note the honest severity: if `cleanupErc20s`-style functions already let anyone send the
contract's balance to any recipient, the dangling approval adds **persistence and stealth**,
not a new capability. Say that out loud rather than inflating it.

---

## 3. PoC discipline — the part that actually decides whether you have a finding

### 3a. Pair every claim with a control

Two tests minimum, and the control must differ **only** in the trigger:

| test | purpose |
|---|---|
| `test_defect_*` | asserts the **observed** (buggy) behaviour, so the suite PASSES while pinning the defect |
| `test_control_*` | same call without the trigger → must NOT reproduce |

The control is what proves causation. Without it you have a coincidence.

### 3b. ⛔ A test can pass for the WRONG reason — make the payload succeed when allowed

My first probe wrapped the reentrant call in `try/catch` and treated *any* revert as
"the guard blocked me". It reported the guard as working — but the revert was the **call
body** failing (a transfer from an empty balance), not the guard. The fix:

```solidity
try router.cleanupNative(0, address(this), "") {   // a successful NO-OP when allowed
    reentered = true;
} catch {
    reentryReverted = true;
}
```

**Rule: the probed call must SUCCEED when the guard lets it through, or a body-level revert
is indistinguishable from the guard holding.** If every path reverts, you have measured
nothing. Corollary: a suite going green is not evidence; a suite going green *for the right
reason* is.

### 3c. Also note the reverting-sender trap

A guard keyed on `msg.sender` blocks a *different* address, so an intermediate contract that
calls in on your behalf fails with `InvalidMsgSender(storedSender, actualSender)` even when
the guard is otherwise disarmed. Choose the trigger accordingly — a **contract self-call**
(`calls[i].target == address(this)`) is the cleanest, because it is allowed by design.

### 3d. ⛔ Verify against the LIVE bytecode, not just your recovered tree

A local test only proves your *reconstruction* is vulnerable. Re-run the same probe against
the deployed address with a fork URL and the right `evm_version`:

```bash
forge test --match-path test/LiveGuardDisarm.run.sol --fork-url https://mainnet.base.org -vv
# foundry.toml: evm_version = "cancun"   (transient storage needs it)
```

Then confirm the deployed build really uses transient storage — `evmVersion: cancun` in the
verifier record, plus `TLOAD`/`TSTORE` present in the runtime bytecode. The chain result is
the one you report; the local result is only how you got there.

An address literal in a fork test must be **EIP-55 checksummed** or solc refuses to compile it.

### 3e. Pure-external vs victim-cooperative triggers decide the severity

Rank triggers by how little they ask of the victim, and test the strongest one you can:

| trigger | what it demands of the victim |
|---|---|
| a **hooked token on the route** | nothing — the attacker signs nothing and never appears as a `target`; their token just has to be somewhere in the route |
| a third-party contract the victim calls after the cleanup step | the victim routes through attacker-influenced code |
| a self-call the victim authors | victim cooperation — weakest framing, best as the *mechanism* proof |

A token whose `transfer`/`transferFrom` reenters is the realistic pure-external form: moving
it is an ordinary route leg, so no attacker address appears in the calls at all.

---

## 4. ⛔ Read the vendor's OWN test suite for known-issue IDs, then check the deployment

When you find a live defect, before writing the report grep the repo's tests for the
mechanism. This audit found `test/ReentrancyGuardMsgSenderVIG084Test.sol` — the team had
already written a test asserting the guard must **not** be cleared by a nested frame.

That single file reframes the whole finding:

- The bug class is **known internally** (`VIG084` = an internal finding ID).
- The **fix exists in the repo** but the **deployed contract still has the vulnerable code**.
- A "known issue" defence may apply to the payout — say so in the report instead of
  discovering it in the triage response.

How to check whether the fix is deployed (do not trust the source you recovered):

1. Diff the guard/mechanism source recovered from the chain against the repo's current file.
2. If they differ, the repo is **ahead** of the deployment — that is the finding.
3. Confirm behaviourally on a fork (§3d). A behavioural proof survives any argument about
   which source is authoritative.

Generalise: `git log -S "<mechanism line>"` and a grep for `VIG`, `AUDIT`, `FIX`, `SEC-`
in test filenames tell you what the team already knows. That changes severity, framing, and
whether to spend a report slot at all.

---

## 5. Checklist for this class

- [ ] Guard stores a sender and compares it — is the "clear" step conditional on the outermost frame?
- [ ] Does any allowed nested path (`address(this)`, a shared entry contract) complete and zero the slot?
- [ ] Is a `cleanup*` / `rescue*` self-call part of the documented multicall recipe? (that arms it)
- [ ] What does the contract hold *transiently* during a normal call, and who can reach a `cleanup*` while it does?
- [ ] Any `approve(...)` with no matching reset, and any caller-supplied amount that skips a balance check?
- [ ] Control test paired with every claim, and both re-run against the deployed address on a fork.
- [ ] Vendor test suite grepped for known-issue IDs before the report is written.
