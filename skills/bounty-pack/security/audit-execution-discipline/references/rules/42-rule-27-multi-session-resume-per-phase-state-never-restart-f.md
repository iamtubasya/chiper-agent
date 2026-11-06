## ⛔ RULE 27: Multi-Session Resume — Per-Phase State, Never Restart from 0A

**User requirement (2026-09-26): "Pastikan jg kalau proses audit Exploit ny makan waktu, session dan context, agar bisa djalankan multi session tanpa harus mengulang dr awal"**

Long audits (0C alone can run hours: C1-C6b with 150-repo caps) MUST survive session/context/provider loss. Two-level resume, both disk-based:

**Level 1 — per-phase (0A→0F).** Orchestrator `run_pipeline` wraps every phase:
```python
if not self._phase_done("0A"):
    self.run_setup()
    self._save_state(completed_phase="0A", current="0B")
```
State file: `~/AppData/Local/hermes/trackers/audit-pipeline-<safe-target>.json`
`{target, tech, completed_phases:[...], current, updated}` — helpers `_state_file()`, `_load_state()`, `_save_state()`, `_phase_done()`.

**Level 2 — per-sub-phase inside 0C (C2..C6b).** The sub-phase scripts write their own usage JSON; on re-run, orchestrator skips any whose output file already exists on disk (>100B):
- C2 `variant-usage.json`, C3 `business-logic-usage.json`, C4 `poc-execution.json`, C5 `poc-variant-usage.json`, C6 `reference-usage.json`, C6b `poc-techniques-usage.json`

So if 0C dies at C4, resume continues from C5 — C2/C3 are NOT re-run. This is the "exported artifact = resume checkpoint" pattern, same rule as the gate (truth from disk, not claims).

**Pitfall:** `audit-state.py list` (old resume tool) only tracked phase+step historically; the orchestrator now uses its own per-phase state file. Don't confuse the two. If session breaks → just re-run the SAME orchestrator command; it auto-resumes and prints `RESUME MODE: already completed [...]`.

> **Reproduction recipe + measured numbers:** `references/poc-techniques-index-recipe.md` — build command, extraction regex per technique type, fire rules, gate check, and the 3014-techniques build output.

