## ⛔ RULE 2f: LONG SCANS GO TO THE BACKGROUND — NOT INTO SUBAGENTS

**Session (superstate round-3 deep-dive, 2026-10-01):** three parallel `delegate_task` children were given
subfinder/httpx/nuclei/gobuster/CORScanner/katana/gau/trufflehog/aderyn/mythril/echidna as one bundle each.
**All three were killed at 600 s** (`Subagent timed out after 600.0s with 13 API call(s) completed`) and every
summary was lost. The lesson is not "don't delegate" — it is *what* to delegate and where long tool runs live.

### The rule
- **`delegate_task` children have a hard wall-clock cap (~600 s observed).** Anything that can legitimately run
  for minutes must NOT be handed to a child: nuclei over a host list, slither/aderyn on a multi-hundred-contract
  repo, mythril, echidna, `katana -jc`, `gau`, gobuster/ffuf with a big wordlist, `forge test` with fork tests.
- **Run those with `terminal(background=true, notify_on_complete=true)`** instead: no 600 s cliff, the job
  survives the turn, and you get a completion notification. Chains of steps are fine inside one background
  script (`for h in ...; do timeout N tool ... >> out; done`).
- **Delegate the reasoning, background the scanning.** Good child tasks: triage a pile of raw output, classify
  scanner results against a rule set, summarise a repo. Bad child tasks: "go run all the scanners".
- If a child DOES needs a scanner, cap it (`timeout 120 <tool>`) and tell it to prefer one tool per task.

### A timed-out child is NOT a total loss — harvest its on-disk artifacts first
Children keep writing to whatever output paths you gave them right up to the kill. Before redoing any work:

```bash
ls -la <outdir>          # what actually landed
wc -c <outdir>/*         # 0-byte files = step started but never produced; non-zero = usable
```

This session's three dead children still left, fully usable: subfinder subdomain list, httpx JSON, a 402 KB
nuclei jsonl, aderyn reports for two projects, trufflehog output for three repos, and full `git log -p` history
dumps. That was the majority of the round's evidence — recovered with one `ls`. **Never report "the delegate
failed, so no coverage"; check the disk and report what landed.**

The child's *summary* is what you lose, not its *files* — so always write the child's mandate as "write raw
evidence to `<abs path>`" and never as "tell me what you found".

### Same class of error as RULE 2c
Never say "all tools were used" off a delegate summary that never arrived. Coverage claims come from files on
disk, same as every other evidence claim in this skill.

> Cross-ref: clobber risk when two attempts target one evidence path — pitfall 8 in the `onchain-source-recovery`
> skill (give each attempt its own filename; verify by content marker + mtime, not by notification order).

