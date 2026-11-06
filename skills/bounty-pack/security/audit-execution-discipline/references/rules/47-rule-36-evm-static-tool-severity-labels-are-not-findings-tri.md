## ⛔ RULE 36: EVM static-tool SEVERITY LABELS ARE NOT FINDINGS — triage every one

`aderyn` and `mythril` emit confident "High" labels that evaporate on inspection. Verified 2026-10-01 on the
Superstate engagement: **4 scanner "High" findings, 0 real vulnerabilities**. Do the triage, don't pass the label through.

**aderyn's `High` classes are mostly template matches on the *shape* of a call.** All three that fired were FPs:
- `ETH transferred without address checks` -> it flagged plain `redeem(...)` functions. The caller pays and
  `receive()`/`fallback()` revert, so the contract holds no ETH.
- `Arbitrary from passed to transferFrom` -> the flagged line was `ERC20Upgradeable.transferFrom({from: src, ...})`
  inside a normal `transferFrom(src,dst,amount)` that spends the allowance first. That IS the ERC20 signature.
- `Storage array edited with memory` -> the helper was `internal pure`, comparing keccak hashes only; the real
  write was the next line. Read the callee before believing the label.

Rule: for each aderyn High, open the cited `file:line` **and the callee**, and write one sentence saying why it is
or isn't reachable. If you cannot name an actor who gains something, it is not a finding.

**mythril in bytecode mode cannot know the caller, so it labels arithmetic it cannot prove safe as High.** Attribute
the finding to a real function before judging it: mythril prints the calldata it used, so map the 4-byte selector
yourself.

```bash
# txn sequence from the mythril report: calldata e24df75400000...
cast sig "initialize(address,uint256,address,uint256)"   # -> 0xe24df754  <- attribution
cast sig "redeem(uint256)"                               # -> 0xdb006a75
```
On this target `e24df754` was `initialize(...)`, not the money math — which is what downgraded a "High" to QA.
Generating the whole selector table up front (`for s in "<each public fn>"; do cast sig "$s"; done`) makes
attribution a lookup instead of a guess.

**Your PoC must be able to FALSIFY your own model.** The first PoC for that finding asserted the contract was
*permanently* bricked. It FAILED, because `setRedemptionFee(0)` still succeeds — the cap only blocks increases
above the bound, so the owner can lower it back and recover. The failing assertion is what produced the correct
rating (Informational/QA). A PoC that only ever confirms your hypothesis is worthless: write the assertion you
expect to be hardest to satisfy, and if it fails, you learned the severity.

**Honest vocabulary for the result** — never "mythril says High so we have a High":
`CONFIRMED (PoC passes, actor + impact named)` · `FP (cited line read, impact impossible)` ·
`REAL BUT QA (reachable only by owner/deployer, self-recoverable, no funds at risk)` · `NO RESULT (tool never completed)`.
Record the downgrade and the reason in `findings.json`; the failed assertion is evidence, keep it.

