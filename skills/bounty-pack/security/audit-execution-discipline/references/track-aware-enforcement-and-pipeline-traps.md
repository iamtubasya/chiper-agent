# Track-aware enforcement — and the traps that make a gate lie

Hard-won 2026-10-07/08 while wiring and then **really running** the 0A–0F pipeline
against a web3 target (Relay v3 Router). Everything here was proven by a live run,
not by reading code.

## 1. The pipeline can "COMPLETE" while doing nothing

Five separate defects each produced a run that reported success and analysed the
wrong thing. The general lesson: **an enforcement layer is only trustworthy once a
real run has been observed failing and passing.** Reading the code proves nothing.

| symptom the pipeline reported | what was actually true |
|---|---|
| `✅ Force execution COMPLETE` | all 5 SC tools had analysed a helper library, 6 cosmetic results |
| `STEP 1: SKIP force-full-execution (force-state sudah complete)` | a **killed** previous run's grandchild had finished and written `force-state=complete` |
| exit code 0 | tools had died on a compile error; only the exit code was swallowed |

> The SC-tool side of this — wrong-file selection, `remappings.txt`, `src="."` stack
> overflow, crytic's `out/build-info` requirement, the `offline=true` solc trap, and why
> `RAN_WITH_ERROR` is not automatically a failure — lives in the **`onchain-source-recovery`**
> skill, `references/sc-project-prep-and-tool-traps.md`. Read both when a web3 run looks
> "complete" but produced nothing.

## 2. Windows: killing the orchestrator does NOT kill the tree

`subprocess.run(shell=True, timeout=N)` on Windows leaves grandchildren alive
(`cmd.exe` dies, `force-full-execution.py` keeps running and holds the pipe). A
killed run therefore **completes in the background** and writes
`trackers/force-state-<target>.json` with `status: "complete"`.

The next run reads that file and **silently skips the entire exploit phase**.

Before re-running any target:

```bash
# 1. kill strays, not just the orchestrator
wmic process where "name like '%python%' and (commandline like '%force-full-execution%' or commandline like '%audit-pipeline-orchestrator%')" get processid,commandline
taskkill /F /T /PID <pid>          # /T is the part that matters
# 2. then clear the state that outlives the process
rm -f ~/AppData/Local/hermes/trackers/*<target>*
```

If the ledger and the state file disagree (state says complete, evidence files are
gone) the gate will report `Evidence files missing for: [...]` — that is the gate
working, not a false alarm.

## 3. A web-centric manifest fails every contract-only target

`asset-coverage.py` demanded subfinder/httpx/katana/nuclei/ffuf/sqlmap/… — none of
which can run without a hostname. A contract target produced **49 of 76 assets
NOT_RUN** and the 0D gate blocked the report.

Fix: make the requirement list track-aware rather than trimming the manifest.

```python
WEB_ONLY = frozenset({...})            # assets that need an HTTP host
SC_TOOLS = ["slither","aderyn","myth","echidna","medusa"]
SC_ONLY  = frozenset(SC_TOOLS)

def needed_for(phase, td):
    is3 = _is_web3(td)
    out = []
    for cls, assets in MANIFEST.get(phase, {}).items():
        if cls == "refs_web3" and not is3:
            continue
        for a in assets:
            if is3 and a in WEB_ONLY:   continue   # N/A, not a failure
            if not is3 and a in SC_ONLY: continue  # web track owes no SC tools
            out.append(f"{phase}:{cls}:{a}")
    return out
```

`check()` must call `needed_for(phase, td)` — building the list straight from
`MANIFEST` re-introduces the bug.

Track detection: `_is_web3(td)` reads `run-meta.json:tech` (markers: solidity, web3,
evm, solana, foundry, anchor, vyper, move, cairo, smart-contract), falling back to a
`.sol` / `sol-source*` artefact. Keep both signals — `--tech` is not always passed.

## 4. Three enforcement layers that each have to be wired separately

Adding one is not enough; the live run needed all three, and each has its own
failure mode.

| layer | where | fails when |
|---|---|---|
| mandated skill list | `prepare_coverage_gate()` writes `loaded-skills.txt` | skill omitted from the list (silently not required) |
| application record | `skill-usage.json` + CHECK 13 | skill present in the list but absent from the JSON |
| corpus actually used | class `refs_web3`, matched against `reference-usage.json` | library opened but no request fired |

**CHECK 13 must cross-check against `loaded-skills.txt`.** Checking only the entries
present in `skill-usage.json` lets an inconvenient skill be dropped entirely and
still pass ("9 skills applied" → PASS). The fix is a set-difference:

```python
want = [l.strip() for l in (target_dir/"loaded-skills.txt").read_text().splitlines()
        if l.strip() and not l.startswith("#")]
have = {e.get("skill") for e in entries if e.get("applied")}
missing = [s for s in want if s not in have]      # -> FAIL: mandated-but-unrecorded
```

Put it in the same `if/elif/else` chain as the other outcomes, or the log prints
`❌ FAILED` and `✅ PASS` in the same breath.

## 5. Evidence quality — size is not proof

A 2000-byte file of `x` passes a `>= 100 B` check. Require the **writer's own header
marker** in the first 4 KB:

| class | marker written by the real producer |
|---|---|
| tools / recon | `# TOOL EVIDENCE:` |
| variants (C2) | `# VARIANT EVIDENCE:` |
| business-logic (C3) | `# BUSINESS-LOGIC EVIDENCE:` |
| references (C6) | `# REFERENCE-DRIVEN ATTACK EVIDENCE` |

Then add cross-artefact consistency, which catches handed-down evidence:

- every USED evidence file's `# TARGET:` must equal `run-meta.json:target`
- its `# TIMESTAMP:` must be inside the run window (tolerate −1 h)

Skip both checks when `run-meta.json` is absent (manual runs) so there are no false
failures. Write `run-meta.json` in 0A — without it these checks are inert.

## 6. Testing the enforcement itself

Every gate here was verified by deliberately breaking a fixture and watching it fail,
then fixing it and watching it pass. The tests found **three bugs in the checks
themselves** (a dropped `pp = pp if pp.is_absolute() else target_dir / p` line that
made every evidence lookup fail; a `log` vs `self.log` NameError; a contradictory
PASS printed after a FAIL). A gate that has never been observed failing is a
decoration.

Pattern that works: build a fixture with real-format evidence → the run must PASS;
replace one evidence file with filler of the same size → that exact asset must FAIL
**with the asset named in the reason**.

## 7. Do not let the pipeline's own severity labels become findings

A scanner's `High arbitrary-send-eth` is a lead. Relay's own bounty rules state that
raw scanner output is not a finding and must be triaged against live reachability.
Record it, run it through the finding gate, and only then call it anything.
