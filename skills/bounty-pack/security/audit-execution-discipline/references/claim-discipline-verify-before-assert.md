# Claim discipline: never assert a state before running the check that would disconfirm it

Eight times in one session (2026-10-08, Relay v3 Router audit) a conclusion was stated to the
operator **before** it was verified. Seven were false alarms; one would have destroyed a real
finding. Every one was caught by a check that cost seconds. This file exists so the check happens
first, not after the operator has been told something untrue.

**The failure recurred AFTER this file already existed.** The "run keeps dying" claim in §1 below
was made, corrected, written down — and then made a *second time* the same session, this time
about a run that had exited 0 six minutes earlier. Documenting the rule is not the fix; running
the check at the moment of speaking is. Treat this list as a pre-speech checklist, not a post-mortem.

## The eight, verbatim

| asserted | reality | what the check would have cost |
|---|---|---|
| "the run keeps dying — RAM" | three runs had **completed**; the gate was rejecting them | `stat` the log size twice, or look for fresh evidence files |
| "my PDF violates RULE 0 (two findings in one)" | the PDF contained **one** finding | `grep` the rendered text for the second finding's keywords |
| "an empty `To:` is legitimate here" | the same page carried `support@<domain>` | one `curl \| grep mailto:` on the page already in hand |
| "Base is NOT AFFECTED" (from a sweep runner) | Base was **AFFECTED** — proven earlier by a fork test | compare the new verdict against the already-established fact |
| "the pipeline died at 0C-C6, RAM pressure" | it had printed **PIPELINE COMPLETE / EXIT 0**; the log was sampled mid-run | `grep -c "=== EXIT" <log>` — 0 means still running, 1 means done |
| "Taiko is missing from the PDF" | the PDF said `taiko`; my own token check was case-sensitive | look at the artefact's actual text before believing the checker |
| "stage_drafts created duplicate drafts" | exactly two drafts existed, one per finding | count them (`drafts().list`) before announcing duplication |
| "the patch removed `_prepare_sc_project`" | true — but caught by re-parsing + grepping for the def, in the same turn | already the correct behaviour; keep doing this |

The first three cost the operator's attention. The fourth would have **retracted a valid finding**.
The fifth told him a working pipeline was broken, and he was one message away from re-running a job
that had already succeeded.

## The rules

**0. A verification that FAILED is evidence about the VERIFIER first.** When your own checker
reports a defect, suspect the checker's matching before the artefact: case (`Taiko` vs `taiko`),
whitespace, HTML-entity escaping, partial paths. A deterministic checker that disagrees with a
deterministic artefact usually has the bug — and a false FAIL sends you "fixing" something correct.

**1. A conclusion that contradicts an already-proven fact is a HARNESS or DIAGNOSIS bug, not new
information.** When a fresh measurement disagrees with something you established independently,
the measurement loses. Go back and re-derive the label mapping, the parser, the filter — do not
narrate the contradiction as a discovery. In the session above, the sweep runner mapped
`[PASS] test_guard_is_disarmed` → "NOT AFFECTED" (inverted), and only the contradiction with the
earlier fork test revealed it.

**2. Never report a negative or a violation you have not grepped for.** "X is missing", "Y is
empty", "this violates the rule" are all *positive claims about absence*. Absence is the easiest
thing in the world to hallucinate from a partial read. Run the search, quote the count.

```python
assert "dangling" not in full_text, "check before claiming the report is single-finding"
```

**3. Before asserting "the target/program does nothing / is not affected / has no address", look
at the artefact you already have open.** All four instances above shared one shape: the
disconfirming evidence was already in hand or one cheap call away.

**4. "It's not growing" is not "it's dead."** A wrapper that captures a child's stdout shows
**nothing** for the whole duration of that child. Liveness is proven by *side effects*
(evidence files appearing, counters incrementing), never by log line count. If you catch yourself
about to say "it keeps dying", check for side effects first.

**5. State confidence, not conclusion.** When you have not run the disconfirming check, say what
you observed ("the log has not grown in 90 s; force-execution output is redirected") instead of
what you concluded ("it died"). The operator can then decide with you instead of being corrected
later.

## Why this matters more than it looks

An operator who is told something false has to spend time disproving it, and — worse — stops
trusting the next assertion. In this session the operator had to ask, twice, for something that
should have been checked unasked (the recipient address; whether the finding was even valid).
That is the real cost: every unverified claim taxes the next true one.

**The asymmetry is what makes this worth being strict about: a verification that fails costs
seconds; a claim that fails costs the operator's trust in the whole run.**

## Checklist before stating ANY of these

- [ ] "it's broken / dead / crashed" → checked for side effects, not just log growth?
- [ ] "X is missing / empty / absent" → ran the search and quoted the count?
- [ ] "this violates <rule>" → read the rendered artefact, not the source or the intention?
- [ ] "the target is not affected" → does this contradict anything already proven? If yes, suspect
      the harness FIRST.
- [ ] "there is no <address / endpoint / option>" → grepped the page/file already in hand?
- [ ] Am I stating an **observation** or a **conclusion**? If conclusion without a check, downgrade
      the wording to the observation.
