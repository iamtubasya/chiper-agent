# audit-run-all.py — Permanent Execution Architecture

> **2026-10 UPDATE — the architecture changed.** `audit-run-all.py` is now a **thin wrapper** that
> delegates to `audit-pipeline-orchestrator.py`, which is the **single source of truth**. An earlier
> version kept its own parallel phase logic inside `audit-run-all.py`; that dual-runner drift is the
> documented root cause of "incomplete execution" reports. Do not re-add phase logic to the wrapper.
> Details below.

## Why This Exists

User correction (2026-09-22): "Enforce, rule, checkpoint, hard gate — tapi semua apa efeknya? Tetap kamu langkahi juga. Sy mau solusi permanen."

ALL rules, checkpoints, hard blocks are TEXT the agent can read and ignore.
The PERMANENT fix is a SCRIPT that forces execution.

## Architecture (current)

```
audit-run-all.py <TARGET> --tech "<tech>"        # thin wrapper, forwards args, exits with child rc
  └── audit-pipeline-orchestrator.py <TARGET> --tech "<tech>" [--scope A,B] [--exclude X]
        │
        ├── PHASE 0A-SCOPE  HARD GATE before any request
        │     └── scope_checker.py --domain <scope> --json
        │         (no profile/--scope -> allow-all, does NOT block; writes _scope_allow_all)
        │
        ├── PHASE 0A: SETUP
        │     ├── PHASE_LOG.md
        │     └── audit-exec-tracker.py init
        │
        ├── PHASE 0B: RECON
        │     └── subfinder + httpx + URL probes -> urls.txt
        │
        ├── PHASE 0C: EXPLOIT — ONE layer, 5 sub-steps, no duplication
        │     ├── C1 dedicated tools : force-full-execution.py
        │     │                       (sqlmap/dalfox/SSRFmap/race-checker/...)
        │     ├── C2 payload variants: execute-variants.py
        │     ├── C3 business logic  : execute-business-logic.py  (15 vectors, incl. nuclei tags)
        │     ├── C4 PoC repos       : track-poc-execution.py -> poc-pipeline.py
        │     ├── C5 PoC variants    : execute-poc-variants.py  (<=150 repos x payload files)
        │     └── C6/C6b references  : execute-references.py, poc-techniques-index.py
        │
        ├── PHASE 0D: GATE
        │     └── verify-tool-usage.py — reads DISK, not claims.
        │         On fail -> REWORK the specific failed step -> re-verify. max_attempts=3.
        │         After 3 failed attempts -> raise RuntimeError = HARD BLOCK (no report).
        │         Failure strings it maps to rework functions:
        │           "variant-usage.json missing"      -> execute-variants.py
        │           "ALL variant vectors skipped" / "no fuzzable URLs" -> recon step 0B
        │           "poc-execution.json missing"     -> track-poc-execution.py
        │           "poc-variant-usage.json missing" -> execute-poc-variants.py
        │           "reference-usage.json"           -> execute-references.py
        │           "business-logic-usage.json"      -> execute-business-logic.py
        │           "tools-usage.json" + "not found" -> force-full-execution
        │           "Thin evidence"                  -> force-full-execution
        │           anything else                    -> generic full force execution
        │
        ├── PHASE 0E: FINDINGS LAYER
        │     ├── E1 aggregate-findings.py <output_dir> -> findings.json
        │     │     (rglob over the dir; parses .md via ## sections, .json/.txt as plain findings;
        │     │      SKIP_NAMES excludes findings.json/PHASE_LOG.md/urls.txt/AUDIT-REPORT.md/...)
        │     ├── chain_builder.py      (weak -> impact chains)
        │     ├── finding_gate.py       (REPORT / DOWNGRADE / DROP)
        │     └── validate-findings.py  -> validated-findings.json
        │
        ├── PHASE 0E-REVIEW: review-candidates.py — each candidate 3x checked, low->high severity.
        │     Only verdict=="READY" entries land in ready-candidates.json, which is the ONLY
        │     legitimate source for the report.
        │
        └── PHASE 0F: REPORT
              └── report-agent.py validated-findings.json --output-dir <dir>
                  -> AUDIT-REPORT.md / .html / .pdf
```

Wrapper contract worth knowing: `--tech` is forwarded, **`--output-dir` is silently swallowed**
(the orchestrator fixes its own output dir under `~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<slug>`).
Exit codes: `0` = all done, `1` = gate blocked / failure, `2` = fatal.

## Verification Chain

Every step verified by:
1. File exists on disk (not self-reported)
2. File has content (not empty)
3. State saved (resume works)
4. Checkpoint PASS before next phase

## Resume on Failure

Per-phase state is persisted to `~/.chiper/skills/bounty-pack/trackers/audit-pipeline-<sanitised-target>.json`
under `completed_phases`, written *after each phase* — so a provider/session drop resumes at the next
phase instead of restarting from 0A.

```bash
audit-state.py list                       # show last saved state
python audit-run-all.py <TARGET> --tech "..."   # resumes; completed phases are skipped
```

To force a genuine re-run of 0A/0B (delete the tracker file) — see
`references/pipeline-phases-and-fresh-run.md`.

Each phase is idempotent — safe to re-run.

## Why Scripts > Rules

- Rules are advisory text → agent can skip
- Scripts are executable code → forces execution
- Scripts verify their own output → can't claim done without proof
- Scripts save state → resume works
- One command → no room for "I'll do it later"
