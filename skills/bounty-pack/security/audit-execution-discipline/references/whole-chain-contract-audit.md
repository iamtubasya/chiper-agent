# Whole-chain contract audit — kill the bug CLASS, not one bug per restart

Operator, 2026-10-10, after the 5th restart of the same target:
*"Dan ini kenapa banyak bug muncul, gkberes2 auditnya"* — "why do so many bugs keep
appearing, the audit never finishes".

That was a **workflow correction**, not a question. This file is the answer.

## The anti-pattern that caused it

```
find bug → fix it → restart the 4-hour run → find the NEXT bug → repeat
```

Measured cost: **5 restarts, 10 bugs, ~20 hours of wall clock**, and the audit still
had not reached 0F. Each restart was a 4-hour bet that the fix was the last one.

Every fix WAS correct. The method was wrong: a full pipeline run is the most expensive
possible bug detector, and a 7-layer pipeline has an enormous surface for this class of
defect — so you find one per run and never converge.

**The rule:**

> Before restarting a long pipeline, run the STATIC contract audit of the whole chain.
> It takes seconds. The run takes hours. An audit that reports 0 findings is the
> precondition for a restart, not a nice-to-have after one.

## The tool

```bash
python ~/.chiper/skills/bounty-pack/pipeline-contract-audit.py
```

Reads the whole 0C call chain (`audit-run-all` → `audit-pipeline-orchestrator` →
`force-full-execution` → `execute-variants` → `execute-business-logic` →
`execute-references` → `execute-poc-variants` → `tool_router`) and reports six families.
Exit code 1 when a HIGH finding is present, so it gates a restart.

## The bug CLASS it hunts

Every one of the 10 bugs was the same shape:

> **a value / rule / claim is declared at one layer, and silently ignored, discarded,
> or outlived by its own evidence at the next layer — with nothing checking the gap.**

| # | Declared | Actual behaviour | What should have checked |
|---|---|---|---|
| 1 | wordlist paths in a file | `host` + `.env` → `host.env` (DNS fail, 46/100 probes) | URL join normalisation in ONE helper |
| 2 | host scope check | substring test passed `host///other-host` | compare netloc against ROOT DOMAIN |
| 3 | crawl keeps in-scope URLs | absolute third-party URLs appended raw | scope filter at the crawl hop |
| 4 | protocol-relative `//host` href | fell to the "relative path" branch → `root///host` | explicit `//` branch + backstop |
| 5 | `deep-recon: 27 -> 123` reported OK | root-domain one-liner produced a tuple → whole merge threw, 104 endpoints silently lost | `isinstance(str)` + never a bare one-liner |
| 6 | `timeout_cap` param | reset to `None` on every call (3 layers deep) | honour the param you accept |
| 7 | `subprocess.run(timeout=N)` | does NOT return at N on Windows — waits for the tool to finish | Popen + tree kill |
| 8 | `force-state: "complete"` | trusted after its evidence was quarantined → C1 skipped, 28 tool files missing | cross-check the artifacts still exist |
| 9 | `applied: True` for skills | the evidence files were written AFTER the check that reads them | write evidence before evaluating it |
| 10 | C6 reference cap | passed but unused; 3909 clues → unfinishable phase | cap actually reaches the runner |

**Only two of the ten were "logic bugs".** Eight were **contract violations between
layers** — which is why testing one layer at a time never found them, and why a real
run was the only thing that could.

## Writing the auditor: measure CODE, not text

The first version produced **13 findings, and 11 were false positives**. Fixing the
AUDITOR (not the code it was accusing) took it 13 → 8 → 2 → 0. Do this before
believing any static-audit output.

| False positive | Cause | Fix |
|---|---|---|
| 5 × "decorative timeout" | the BUGFIX comments *describing* the bug matched the regex | parse with `ast`, only `ast.Call` nodes count |
| 1 × `DORK_TIMEOUT` unused | the name appeared only in a usage docstring | AST sees only real code; docstrings are `Constant` nodes |
| 1 × `taskkill` timeout | a `taskkill` INSIDE `except TimeoutExpired:` is the FIX | look BACKWARD 8 lines for `TimeoutExpired` → mark OK |
| 3 × utility calls | `taskkill`/`powershell`/`wmic` are short-lived; seconds, not hours | context-match the next 5 lines, skip the bug class |

**Lesson:** a noisy static guard is worse than no guard — it trains you to ignore the
tool. When the auditor reports something, first ask whether the auditor is right.

## Two timeout layers — do NOT conflate them

Raising a false alarm because the wrong layer's cap was quoted:

| layer | scope | value |
|---|---|---|
| **C1** `force-full-execution` | per tool, `SLOW_FUZZ` class (sqlmap/ffuf/nuclei/gobuster/katana/naabu/arjun/kxss/**dalfox**) | **1200 s** |
| **C1** other tools | per tool | 600 s |
| **C1** smart-contract | per tool | 1800 s |
| **C6** `execute-references` | **per clue**, via `--tool-cap` / `REF_TOOL_CAP` | **60 s** |

dalfox at 8 minutes inside C1 is **normal** (cap 20 min). It is only anomalous if it
exceeds the layer's own cap. Check which layer the process belongs to before alarming.

## The measurement that lied

An earlier report in this session claimed: *"`subprocess.run(timeout=)` returns but the
2 child processes are STILL ALIVE"*.

**That was wrong.** The search used `wmic process where "CommandLine like '%MARKER%'"`
and the MARKER sat inside wmic's OWN command line — so wmic reported itself plus its
shell wrapper. Correct method: snapshot the PID set before, run, kill, snapshot after,
diff the sets. That showed **survivors: none** in both implementations.

The real defect is different and still serious — it just had the wrong name:

```
OLD  subprocess.run(timeout=4) against a 45 s sleep  → returned after 45.1 s
NEW  Popen + taskkill /F /T                          → returned after  4.2 s
```

Not a leaked child. **The bound simply never interrupted anything**: it waited for the
tool to finish and only then reported `TIMEOUT`. Same user-visible outcome (dalfox 44 min,
later 84 min on one reference), different mechanism — and the wrong mechanism would have
sent the next agent hunting for orphan processes that do not exist.

**Rule:** when a measurement accuses something, reproduce it with a method that cannot
self-match. Corrections are cheap; a wrong root cause persisted into the skill is not.

## Checklist before any long-pipeline restart

```bash
python ~/.chiper/skills/bounty-pack/pipeline-contract-audit.py     # must be 0 findings
python ~/.chiper/skills/bounty-pack/reset-stale-markers.py <slug> <target>
python -m py_compile <every file you touched>
# then sync: cp to bundle-src/... + bundle-sync.py  (must report 0 drift)
```

Only then start the run. If the audit reports a HIGH finding, fix it first — restarting
with a known finding is choosing to spend 4 hours to re-discover it.
