# Long jobs, delegation limits, and falsifier triage

Two rules that belong in the main SKILL.md but could not be patched in (that file is already over the 100,000
character limit — see the note at the bottom). Read this alongside RULE 2c/2d (tool evidence) and RULE 35
(scanner false-positive classes).

---

## RULE 36 — Long scanner work goes to BACKGROUND JOBS, not delegated children

**Session (superstate 2026-10-01):** three `delegate_task` children were launched in parallel (web2 attack
surface, git-history secret scan, extra web3 tooling). ALL THREE hit the hard 600 s wall and returned
`status: timeout` with `summary: null` — a child's summary is discarded with the child. What survived was
everything they had already written to disk.

1. **Anything expected to run longer than ~5 minutes must be a background terminal job**
   (`terminal(background=True, notify_on_complete=True)`), never a delegated child. The child has a 600 s
   ceiling and no resume; a background job is unbounded and notifies on exit.
2. **A timed-out child is not a lost child.** Before redoing anything, list the output directory it was told to
   write to. Here the "lost" work had already produced: a full subfinder host list, a 20 KB httpx JSON, a
   402 KB nuclei JSONL, three full-history `git log -p` dumps, the decoded malware diff, and two complete
   aderyn reports. Re-running would have burned an hour and re-hit the same wall for nothing.
3. **Delegate the orchestration, not the waiting.** Give each child one bounded tool + one target; keep the long
   scans in the parent's background jobs.
4. Design the brief so the **artifact is the deliverable**: every child writes evidence to a path the parent can
   harvest without the child's summary. Then a timeout costs the narrative, not the work.

Practical shape that worked:
```
# in the parent, long work:
terminal(background=True, notify_on_complete=True)   # subfinder/httpx/nuclei/katana/gau/dir-brute/mythril
# delegated children only for bounded sub-tasks that WRITE TO DISK:
delegate_task(goal="... write raw output to <ABS DIR> and a summary to <DIR>/SUMMARY.md")
```

---

## RULE 37 — A falsifier's counterexample can be the HARNESS's bug

**Session (superstate 2026-10-01):** echidna reported 3 of 4 invariants `failed!💥` against the redemption
contracts. Two of them flipped to `passing` the moment a single action (`action_deployWithFee`, the path that
reaches the suspect `initialize` fee assignment) was removed from the harness — that proved they were genuinely
about the contract, and it mechanically corroborated a finding already rated Informational. The third kept
failing in BOTH runs and turned out to be **my own invariant formula**:
`maxUstbRedemptionAmount()` deliberately grosses the USDC up by the fee
(`* FEE_DENOMINATOR / (FEE_DENOMINATOR - redemptionFee)`) so the redeemer sends enough tokens to net the target
USDC; my check compared that grossed-up capacity against the raw balance, so it "failed" for every fee > 0.
Reporting it would have been a fabricated finding.

```
1. Run the harness WITH the suspect action/path enabled  -> note which properties fail.
2. Re-run with ONLY that path removed (comment the action out; change nothing else).
3. Flips to passing  => that path caused it; it is a contract result, keep it.
   Fails in BOTH runs => either a real invariant break OR a bad invariant. Do not report yet.
4. For the "fails in both" set, re-derive the invariant from the CODE's stated intent: read the natspec or the
   comment on the function it touches. A deliberate gross-up, an intentional rounding direction, or a documented
   bound is usually exactly where a hand-written invariant goes wrong.
5. Only step 4's survivors are findings.
```

Generalises beyond echidna: **for any tool that hands you a counterexample, the counterexample is evidence about
the harness until the invariant has been checked against the code's documented intent.** Same family as RULE 35 —
a tool's severity label is a hypothesis, not a result.

Worked example of the whole triage chain in one session (all four scanner "High" labels correctly rejected):

| tool | label | why it was wrong |
|------|-------|------------------|
| aderyn | High "ETH transferred without address checks" | flagged `redeem()`; the caller pays and `receive()`/`fallback()` revert so the contract holds no ETH |
| aderyn | High "Arbitrary `from` passed to transferFrom" | the internal call inside a standard `transferFrom(src,dst,amount)` that spends the allowance first |
| aderyn | High "Storage array edited with memory" | the helper is `internal pure`, compares keccak hashes only; the real write is the next line |
| mythril | High SWC-101 integer underflow | real code smell, but deployer-only via one-shot `initialize`, no funds at risk, and owner-repairable -> QA, not High |

Note the pattern: **read the flagged line before believing the label.** In all four cases the source line was
already in the repo; no exploit work was needed to downgrade them.

---

## Bloat note (for the curator)

`audit-execution-discipline/SKILL.md` is **100,823 characters**, over the 100,000 limit, so `skill_manage patch`
refuses any edit to it. It needs splitting: the RULE-by-RULE body should move to `references/rules-*.md` with a
short SKILL.md index. Until that happens this skill can only receive `references/`, `templates/` and `scripts/`
additions — and any new rule has to live in a references file like this one, which means new rules are no longer
discoverable from the SKILL.md body.
