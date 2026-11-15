# Track-aware gates + run-lifecycle traps

Source: auditing Relay (relay.link) v3 Router `0xb92fe925…` on 2026-10-08, the first real
web3 run through the 0A–0F pipeline. Six gate/runtime defects surfaced that had **nothing to
do with the target** — every one made the pipeline look like it was working while it was not.

Read this before changing `asset-coverage.py`, the orchestrator's gate, or the tool-status
classifier. The per-tool *compiler* traps (wrong .sol, remappings, foundry.toml) live in the
`onchain-source-recovery` skill instead — this file is about the GATE, not the toolchain.

---

## 1. A required-asset manifest must be TRACK-AWARE

The first contract-only run failed **49 of 76 assets** at 0D. Every failure was a web tool:

```
0B:recon:subfinder   NOT_RUN   no entry in tools-usage.json
0B:recon:httpx       NOT_RUN   ...
0C:tools:nuclei      NOT_RUN   ...
```

A contract target has **no hostname**, so subfinder/httpx/nuclei/ffuf/sqlmap/dalfox/arjun/
wpscan/… can never run. They were reported as "skipped/failed" when the truth is
**not applicable**. An enforcement layer that demands the impossible trains the operator to
ignore it.

**Design rule.** Every required asset carries a track predicate. On a web3/contract track the
web-only set is dropped from the *requirement list* and the smart-contract set is required
instead:

```python
WEB_ONLY = frozenset({"subfinder","httpx","nuclei","ffuf","sqlmap","dalfox","arjun", ...})
SC_TOOLS = ["slither","aderyn","myth","echidna","medusa"]
SC_ONLY  = frozenset(SC_TOOLS)

def needed_for(phase, td):                 # the ONLY thing the gate may require
    is3 = _is_web3(td)
    out = []
    for cls, assets in MANIFEST.get(phase, {}).items():
        if cls == "refs_web3" and not is3:      continue
        for a in assets:
            if is3 and a in WEB_ONLY:           continue   # cannot run without a host
            if not is3 and a in SC_ONLY:        continue   # meaningless for a web target
            out.append(f"{phase}:{cls}:{a}")
    return out
```

Two further points that make it work:
- **`needed_for()` must be the single source of truth.** `check()` calls it; nothing else may
  rebuild the list from `MANIFEST` directly, or the two drift apart.
- **`init()` still seeds the full manifest** (both variants), so the ledger has a row for every
  asset. `derive()` marks the off-track ones `N/A — web2 track` / `N/A — contract track`, and
  `check()` never looks at them.

**Track detection** (`_is_web3`): primary signal is `run-meta.json:tech`; fallback is a `.sol`
or `sol-source*` artefact in the output dir. Marker list should cover `solidity web3 evm solana
foundry anchor vyper move cairo smart-contract` — a narrow list silently routes a Rust/Solana
target down the web path.

**Verify both directions, not just the one you care about.** The regression pair is:
```
web2 (tech=nginx)     -> 0C PASS    (refs_web3 = N/A, refs_web3 tools absent from the list)
web3 tanpa corpus     -> 0C FAIL    FAIL 0C:refs_web3:defi-exploit-forensics [NOT_RUN]
web3 + corpus dipakai -> 0C PASS
```
A gate only proven to FAIL is as untrustworthy as one only proven to pass.

---

## 2. Exit code is NOT status for an analysis tool

Smart-contract analysers **exit non-zero precisely when they succeed**:

| tool | exit != 0 means |
|---|---|
| slither | it found detections |
| echidna | an assertion FAILED — that is the finding |
| medusa | same, plus it reports its own summary |
| aderyn | detections present |

The classifier at the time read `rc != 0` → `RAN_WITH_ERROR`. So a run that produced **68 real
findings** was recorded as an error, and a run that fed the tool the wrong file looked
*identical* to a run that worked. Fix: a **completion marker overrides the exit code**.

```python
_SC_DONE_MARKERS = (
    "analyzed (", "result(s) found",                       # slither
    "running 88 detectors", "report printed",              # aderyn
    "total calls", "assertionfailed", "test(s) passed",    # echidna
    "test summary", "fuzz: elapsed",                       # medusa
    "analysis was completed",                              # mythril
)
# order: usage-error  ->  completion-marker  ->  rc!=0  ->  no-output  ->  EXECUTED
```

Order matters: a **usage error must still win**. `FAILED_USAGE` has to be checked before the
markers, or a tool that printed `--help` alongside a marker gets credited as executed.

Generalisation beyond Solidity: any scanner whose exit code encodes *"findings present"*
(semgrep, gitleaks, nuclei with `-e`, bandit) needs the same treatment. Decide status by what
the output says, never by `rc` alone.

---

## 3. Verify WHAT was analysed, not that the tool ran

`slither … ` returning exit 0 with `6 result(s) found` on a protocol contract reads like a
clean target. It was actually analysing a helper library. The tool "ran" and the pipeline said
`EXECUTED`.

**Rule: the evidence header must name the analysand.** Every SC tool's evidence file records
its `# COMMAND`. Before believing a pass — and especially before believing a *negative* — read
that line and confirm it points at the target contract, from the project root, with the right
relative path. A whole run's conclusions are void if the path is wrong, and nothing about the
exit code or the result count will tell you.

Corollary for the gate: a negative result is only reportable when the analysand is proven
correct. "0 findings" and "analysed the wrong file" are indistinguishable from the count alone.

---

## 4. Killing the parent does NOT kill the children on Windows

`taskkill` on the orchestrator leaves `force-full-execution` (and any `slither`/`forge`/
`echidna` beneath it) running. The orphan **finishes**, and writes
`trackers/force-state-<target>.json = {"status": "complete"}`.

The next run then logs `STEP 1: SKIP force-full-execution (force-state sudah complete)` — the
entire smart-contract phase is skipped. If you also deleted the evidence while cleaning (the
normal thing to do), the run reaches 0D with nothing to show and the gate reports
`Evidence files missing for: ['slither','aderyn','myth']`. The gate is right; the state was
lying.

**Re-run procedure — all four steps, every time:**

```bash
# 1. kill the TREE, not the parent
for pat in audit-pipeline-orchestrator force-full-execution slither echidna medusa; do
  pids=$(cmd /c "wmic process where \"commandline like '%$pat%'\" get processid" | tr -d '\r' | grep -E '^[0-9]+')
  for p in $pids; do cmd /c "taskkill /F /T /PID $p"; done
done
# 2. delete the tracker state for THIS target
rm -f trackers/*<target>*
# 3. delete the evidence you are about to regenerate
rm -rf <ws>/tool-evidence <ws>/tools-usage.json <ws>/asset-coverage.json
# 4. only then relaunch
```

Because the state and the evidence can disagree, **never delete one without the other.** Half a
cleanup is worse than none: it converts a stale-but-consistent run into an inconsistent one.

Related: the orchestrator's own `_force_state_complete()` docstring already warns that
`subprocess.run(shell=True, timeout=N)` does not kill grandchildren on Windows. That warning
covers the *timeout* case; this is the *manual kill* case, and it bites harder because the
orphan completes successfully.

---

## 5. A FAILING gate is the feature

Three runs in a row ended `❌ GATE FAILED after 3 attempts — HARD BLOCK / DO NOT GENERATE
REPORT`, and that was correct every time:

- attempt 1: `Evidence files missing for: ['slither','aderyn','myth']` (stale force-state)
- attempt 2/3: `asset-coverage FAIL for phase(s): ['0B','0C']` + `skill-usage.json missing`

Do not "fix" a failing gate by loosening it. Each failure named a real defect in a script, and
each was repaired at the source. The value of the whole exercise was that the pipeline refused
to emit a report about work it had not done.

**Corollary — enforce the mandate where it cannot be dropped.** `loaded-skills.txt` is the
authority for what a track owes. `verify-tool-usage` CHECK 13 originally only validated entries
*present* in `skill-usage.json`, so simply omitting an inconvenient skill made it pass. It now
cross-checks `loaded-skills.txt` and fails with
`mandated-but-unrecorded: ['<skill>']`. Any "was it used?" check needs this shape: compare the
required set against the recorded set — never trust the recorded set alone.

**Corollary 2 — a gate that demands a file nothing WRITES is unpassable, and that is not
enforcement.** CHECK 13 required `skill-usage.json` with per-skill evidence, but `grep` over the
whole script dir showed the file was only ever *read* (in `verify-tool-usage`, `audit-checkpoint`,
the orchestrator) and **never written by any component**. Every run therefore hard-failed on
`skill-usage.json missing — loaded skills not recorded as applied` — including runs where the
skills genuinely were applied. Enforcement that cannot be satisfied is indistinguishable from a
broken gate.

The fix is a **scaffold, not a relaxation**: `prepare_coverage_gate()` now seeds
`skill-usage.json` from `loaded-skills.txt` with `applied:false, evidence:""` for every mandated
skill, so the file always exists and the agent is forced to supply real evidence. Verify all
three directions:

```
scaffold untouched   -> ❌ CHECK 13 FAILED: not applied: ['bb-methodology', …]
scaffold filled      -> ✅ CHECK 13 PASS: N skills applied (evidence verified)
one skill dropped    -> ❌ CHECK 13 FAILED: mandated-but-unrecorded: ['defi-exploit-forensics']
```

**Generalisable rule:** for every gate requirement, name the component that *produces* the
artifact. If the answer is "nothing yet", the requirement is a TODO for the writer, not a rule
for the reader. Same audit applies to `tools-usage.json`, `reference-usage.json`,
`asset-coverage.json` — each must have exactly one writer and at least one reader.

---

## 6. Scope: the program brief is the authority, and it can EXCLUDE the obvious target

Relay's bounty brief (docs.relay.link/security/bounties) puts the **Vaults** contracts
(`RelayPool`, `RelayBridge`, `RelayPoolFactory`, `RelayBridgeFactory`,
`RelayPoolNativeGateway`, vaults API/UI) explicitly **out of scope**, while the protocol and
services are in scope. An auditor who "goes for the money" and lands on the vaults contract
produces a report that is worth $0 regardless of quality.

Read the brief's out-of-scope list **before** choosing a target, and state the exclusion in the
engagement record. `--scope` / the profile gate handles *domains*; out-of-scope **contracts**
are a judgment call the operator has to make explicitly.

Also from that brief — the scanner-severity discipline is vendor-mandated: *"raw automated
scanner output … does not count"*, and a report is ineligible unless an unprivileged party can
reach the bug. A slither `High` on a permissionless-by-design function is a **lead**, not a
finding, until a PoC shows damage.

---

## 7. FIRST: prove the run actually ENDED before diagnosing why it "died"

**This section exists because the first version of it was WRONG, and the wrong version cost real
time.** It claimed ten runs were "killed from outside by host RAM". They were not killed. When
the full log of one of them was finally read, it showed a **complete, successful run**:

```
05:15 SCOPE GATE PASSED  ->  0A COMPLETE
05:27 ✅ Force execution COMPLETE            (the SC tools really ran)
05:31 ✅ Variant execution COMPLETE
05:33 ✅ C3 business-logic COMPLETE
05:40 ✅ C4 + 1.4c PoC variant COMPLETE
05:45 ✅ C6 REFERENCES COMPLETE
05:52 ✅ C6b POC-TECHNIQUES COMPLETE
05:52 GATE attempt 1 -> FAIL (2)   ·   05:57 attempt 2 -> FAIL (6)   ·   06:00 attempt 3 -> FAIL (5)
06:00 ❌ HARD BLOCK   ·   === EXIT 0 ===
```

Nothing died. The pipeline **finished**, and the gate **correctly blocked the report**. The
"variable death point" was an artefact of **sampling a log while the run was still in progress**.

**The trap that produced the false diagnosis.** A run was launched as
`python … 2>&1 | tee -a run.log`. Mid-run the log tail showed `STEP 1.4a`, then stopped growing.
Two checks were taken (size unchanged, then unchanged again after a sleep) and declared "died at
1.4a". Both readings were of an **in-flight** log: `tee` holds output, and the orchestrator's own
step lines only appear once a child returns — a multi-minute child looks exactly like a hang.

**Before you diagnose a death, prove there was one:**

```bash
grep -c "=== EXIT" <log>          # 0 means the run has NOT finished yet — keep waiting, do not diagnose
tail -3 <log>                     # is the last line a step STARTING (in flight) or an EXIT sentinel?
# and only then, is the process actually gone?
MSYS_NO_PATHCONV=1 cmd /c "wmic process where \"commandline like '%orchestrator%'\" get processid"
```

| what you observe | what it means |
|---|---|
| no `=== EXIT ===` line | **the run is still going.** Sampling a log is not a liveness check. |
| `=== EXIT 0 ===` + gate FAIL | normal completion; the gate did its job. Read the failures, do not blame the host. |
| exited, **same** step every time | deterministic code defect — read that step |
| exited, **different** step, **with** a traceback | code defect on whatever data reaches that step |
| exited, **different** step, **no traceback**, process gone | *then* an external kill is plausible — check resources |

**Rule: a log that has stopped growing is not a corpse.** The only proof of termination is the
exit sentinel or the absence of the process — and for a long step, neither is available until it
finishes. Wait for the run; do not narrate its death from a mid-flight sample. If you catch
yourself writing "the run died at X" while also knowing the command is still in your process
list, stop and re-read the last three lines.

### Resources are still worth managing — but as hygiene, not as a diagnosis

`wmic OS get FreePhysicalMemory` and the per-process working set remain useful *before* a heavy
0C run (those steps spawn nuclei/sqlmap concurrency and the budget is not yours):

```bash
MSYS_NO_PATHCONV=1 cmd /c "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /format:list"
MSYS_NO_PATHCONV=1 cmd /c "wmic process get name,workingsetsize" \
  | awk 'NR>1 && $2+0>80000000 {printf "  %-22s %6.0f MB\n",$1,$2/1048576}' | sort -k2 -rn | head -14
grep -c Traceback <log>            # 0 alone proves nothing about death — see above
```

On this host (5.9 GB) RAM is genuinely tight — `vmmem`/WSL2, 30+ `chrome.exe`, node/python and
**orphaned** `nuclei.exe` from previously-killed runs (see §4) are the big consumers. Capping WSL
in `~/.wslconfig` (`memory=1024MB`, `processors=2`) and reaping orphans is worthwhile hygiene.

**But do not record it as the cause of anything unless a run is proven to have been killed.**
Concluding "host RAM killed it" from a stalled log sends the next session hunting memory while the
real (and mundane) answer is sitting in the gate output.

### Corollary — the `| tee` pipe and the subprocess call were both exonerated

Two cheap hypotheses were tested and both failed to reproduce the (non-)death: running with a
plain `> log` redirect changed nothing, and invoking `execute-variants.py` /
`execute-poc-variants.py` standalone returned `rc=0` with `stderr 0B` in 285 s / 431 s. Good —
they eliminated suspects. The mistake was not testing them; it was **adopting a root cause before
the run had finished**, so the tests were framed to confirm a death that never happened.

---

## 8. REWORK can make things WORSE — compare the failure COUNT

The gate's auto-rework loop re-ran `force-full-execution`, and the failure count went
**2 → 7** between attempt 2 and attempt 3:

```
attempt 2: ❌ asset-coverage FAIL ['0B','0C']  + ❌ skill-usage.json missing      (2 failures)
attempt 3: ❌ refs … ❌ poc-techniques-usage.json missing
           ❌ asset-coverage.json missing          + ❌ skill-usage.json missing  (7 failures)
```

The rework regenerated `tools-usage.json` but wiped/never rewrote `asset-coverage.json` and
`poc-techniques-usage.json`, so the re-verification failed on artefacts *the rework itself had
destroyed*.

**Rule: when a gate is allowed to rework, diff the failure sets between attempts, not just the
counts.** More failures after a rework attempt, or a failure naming an artifact the rework step
itself writes, means the loop is thrashing — stop the loop and fix the rework step, or the
outcome is decided by how many attempts you allow rather than by the audit.

Also: rework re-runs *only* the failed step. If a re-run can invalidate a sibling artifact,
the step must regenerate it too (or the gate must treat the pair atomically).
