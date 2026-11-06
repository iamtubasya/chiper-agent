# Multi-Session Audit Resume — Implementation (2026-09-26)

Problem: 0C exploit layer (C1..C6b) can run for hours with 150-repo caps; a
session/context/provider break forced full restart from 0A because the
orchestrator never persisted per-phase progress (only force-full-execution
saved its own state file, and `audit-state.py` was not wired in at all).

## Files

`~/AppData/Local/hermes/scripts/audit-pipeline-orchestrator.py` additions:

```python
def _state_file(self):          # trackers/audit-pipeline-<safe>.json
def _load_state(self):          # {target, tech, completed_phases:[], current, updated}
def _save_state(self, completed_phase=None, current=None, note=""):
def _phase_done(self, phase):   # phase in completed_phases
```

`run_pipeline` now:
```python
if not self._phase_done("0A"): self.run_setup(); self._save_state(completed_phase="0A", current="0B")
if not self._phase_done("0B"): self.run_recon(); self._save_state(completed_phase="0B", current="0C")
if not self._phase_done("0C"): self.run_force_execution(); self.run_variants_and_pocs(); self._save_state(completed_phase="0C", current="0D")
if not self._phase_done("0D"): self.verify_tool_usage(); self._save_state(completed_phase="0D", current="0E")
if not self._phase_done("0E"): validated_json = self.run_findings_layer(); self._save_state(completed_phase="0E", current="0E-REVIEW")
if not self._phase_done("0E-REVIEW"): self.run_review_candidates(); self._save_state(completed_phase="0E-REVIEW", current="0F")
if not self._phase_done("0F"): final_report = self.generate_report(); self._save_state(completed_phase="0F", current="DONE")
```

## Sub-phase skip (Level 2) — inside run_variants_and_pocs

```python
def _done(fname):
    f = self.output_dir / fname
    return f.exists() and f.stat().st_size > 100
skip_c2  = _done("variant-usage.json")
skip_c3  = _done("business-logic-usage.json")
skip_c4  = _done("poc-execution.json")
skip_c5  = _done("poc-variant-usage.json")
skip_c6  = _done("reference-usage.json")
skip_c6b = _done("poc-techniques-usage.json")
```
Each block then wraps with `if skip_cX: log SKIP else: run`.

## Verified behavior (unit test)

```
SAVED: completed=['0A'] current=0B
SAVED: completed=['0A','0B'] current=0C
0A done: True, 0C done: False
state file contains full JSON {target, tech, completed_phases, current, updated}
```

## Rerunning after you FIX a bug in the pipeline itself (not after a session break)

Resume is correct when nothing changed. It is actively dangerous when you just repaired the setup,
because the run resumes and presents **pre-fix evidence as if it were current**.

Observed 2026-10-08 (relay.link v3 Router): after fixing the Solidity source resolver, a re-run
logged

```
RESUME MODE: already completed ['0A', '0B'] — skip those
STEP 1: SKIP force-full-execution (force-state sudah complete)
```

…so the smart-contract tools never re-ran and the evidence on disk was still the wrong-contract
output. Two state stores have to be cleared, not one:

| store | path | governs |
|---|---|---|
| phase state | `~/AppData/Local/hermes/trackers/audit-pipeline-<safe>.json` | which of 0A/0B/0C/0D/0E/0E-REVIEW/0F are skipped |
| force state | `~/AppData/Local/hermes/trackers/force-state-<safe>.json` | whether C1 (force-full-execution) runs at all |

Reset recipe (replace `<target>` and keep the `sol-source/` + `run-meta.json` you want to survive):

```bash
rm -f ~/AppData/Local/hermes/trackers/*<target>*
rm -rf <out>/tool-evidence <out>/tools-usage.json
rm -f  <out>/{variant,business-logic,poc-execution,poc-variant,reference,poc-techniques}-usage.json
```

Also delete the artefacts the bug produced inside the source tree (`out/`, `crytic-export/`,
`combined_solc.json`, a wrong `foundry.toml`/`remappings.txt`) — otherwise the new run inherits them.

**Before spending a full pipeline run, verify the fix with ONE tool by hand.** Run the repaired
tool directly and check its output header (`# COMMAND:`) names the intended target and that it
reports real analysis (`… analyzed (N contracts with M detectors), K result(s)`). A 30-second manual
run beats discovering at 0D that the run analysed the wrong file again.

General rule: state skipped work is only trustworthy if the code that produced that work has not
changed. Any edit to the pipeline → clear the state for the affected phases.

## Notes

- Sanitize target for filename: `re.sub(r'[^A-Za-z0-9._-]', '_', target)` —
  colon/slash in URL breaks Windows paths.
- Test state files (`audit-pipeline-https___example.com.json`) must be cleaned up
  after testing; real target state files should be left alone (no delete without approval).
- `audit-state.py` remains for simple list/save/complete but the orchestrator
  does NOT depend on it — do not expect one to update the other.