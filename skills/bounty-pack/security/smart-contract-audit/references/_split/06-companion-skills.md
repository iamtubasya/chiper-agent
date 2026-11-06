## Companion Skills

Dump every configurable counterparty of every deployed contract with read-only calls
(`cast call <addr> "<getter>()(address)"`) and cross-check against the project's own front-end
address config. Two things fall out for free:

- a mis-set pointer is itself a finding class (a farm configured at the staking address, a treasury
  pointed at a retired router, a prize bound to an old registry);
- **a getter that REVERTS on a contract you expected to have it is the cheapest signal that the
  deployed build is older than the source you were handed** — which is the entry point to the
  selector diff below. Always do this before concluding anything is "already fixed".

Formalise the second half with `scripts/deployed_vs_source_selector_diff.py` (source
`forge inspect methodIdentifiers` vs live `cast code`, reports the selectors missing on chain).

### PoC design: make the proof self-isolating (controls on ONE identical state)

A revert or an odd number on its own proves nothing about *why*. Every claim in this class needs a
second observation on the **same** state so the only difference is the variable under test:

| Shape | Real-engagement example |
|---|---|
| control passes, target fails | the registry answers a selector it really implements; the selector the contract calls reverts with empty data |
| same path, condition fixed | wire a mock oracle that works and the *same* vault releases exactly half and pays out |
| A/B on one identical state | the same farm pool earns X while an empty pool holds weight; call `pausePool` to release that weight and the same pool earns 2X — nothing else changed |
| path A fails, path B works on identical input | the source router's ETH add-liquidity reverts on a dusted pair, while the token/token path seeds that same dusted pair and mints LP |

Without a positive control a triager can always answer "that reverts for some other reason"; without
the A/B pair they can answer "your setup caused it". Build both, assert the numbers, and let the
A-versus-B sentence carry the finding.

### Delegating contract review: the brief decides whether it works

A broad "review these five contracts for bugs" brief **timed out at 600 s with zero output**. The
same contracts answered productively once the brief was hard-bounded:

```
HARD CONSTRAINTS: read at most 3 files. Do not run any build or test. Answer in under 25 lines total.
Files (read in this order, stop when you have an answer): <absolute paths>

Mechanism to attack precisely (show the arithmetic, do not hand-wave): <exact functions + invariant>

KNOWN ISSUES ALREADY REPORTED (never report these): <paste the program's list verbatim>

Specifically test these hypotheses and say whether each holds:
  H1 ... H2 ... H3 ...

Answer format: 'H1: holds/does not hold - one sentence why (file:line)'. Then any NEW candidate as
'CONTRACT:function:line | root cause | concrete gain or loss | non-owner reachable? yes/no'.
If nothing holds, say 'none found'. Precision over volume. Respond in English.
```

Two rules that follow:

- **A subagent summary is a lead, not a finding.** Every "holds" verdict still has to be confirmed by
  reading the exact lines yourself before it reaches `findings.json`. In one engagement the useful
  candidates were sound but the hypothesis set around them was mostly wrong — the value was in the
  one or two that survived your own re-read.
- **Never delegate PoC design.** Subagents report mechanisms and verdicts; the controls, the numbers
  and the wording are yours, because the controls are what make the claim survive triage.

