# Keeping the 0A–0F phase framework consistent across scripts + skills

The pipeline's phase model lives in **`audit-pipeline-orchestrator.py`** (single source of truth):

```
0A SETUP → 0B RECON → 0C EXPLOIT (C1..C6b) → 0D GATE (verify-tool-usage)
        → 0E FINDINGS   : finding_gate -> validate-findings -> triage_gate   (aggregate/weaponize/chain_builder = 0C-C7)
        → 0F REPORT
```

`audit-run-all.py` is a thin wrapper around it. Everything else must mirror that list.

## What had drifted (found 2026-10-01, user asked "cek dl phase auditnya ad 0a sampai 0f")

- `audit-checkpoint.py` only accepted `--phase 0A|0B|0C|0D|all` — **0E and 0F had no gate at all**, and its
  `0D` was labelled "REPORT" while the orchestrator uses `0D` = GATE and `0F` = REPORT. Two different meanings
  for the same phase id across two files that verify each other.
- **~35 skill/doc files** still used the old convention ("Phase 0D = report"). The drift was not only in the
  launcher's own SKILL.md but spread through `references/` of several skills (context budgets, per-tool
  "Phase 0D: include results in report" footers, per-vuln-class SKILL.md banners, the report skill's own
  pre-flight checks). A grep for `Phase 0D` returns dozens of legit-looking hits, most of them stale.
- The `PHASE_LOG.md` template and live engagement logs stopped at 0D.

## Fix checklist (run this whenever the phase model changes)

1. `grep -rn "0A-0D\|0A→0D\|Phase 0D\|PHASE 0D" scripts/ skills/` — every remaining hit must be
   gate-flavoured (`verify-tool-usage`, `checkpoint`, `--phase 0D`, `0D must PASS`). Anything mentioning
   *report / severity / extraction / trace evidence / deliver* is stale → `0F`.
2. Keep the checkpoint's `--phase` **choices list** identical to the orchestrator's phase names, or a gate for
   the new phase can never be invoked.
3. `PHASE_LOG.md` templates must list every phase; a log that stops at 0D is itself the signal the framework
   drifted.
4. Handoff bundle: after patching any pipeline script, copy it into `bundle-src/.../toolkit/scripts/` **and**
   re-zip, then md5-compare live vs zip (`audit-checkpoint.py` is inside
   `D:/data hermes/audit-pipeline-bundle-v1.zip` at `audit-pipeline-bundle-v1/toolkit/scripts/`).

## Bug: the 0F check crashed on a directory named `reports/`

`check_phase_0F` globbed `list(target_dir.glob("*report*"))` and then called `read_text()` on the first hit.
An engagement that keeps its output in a `reports/` **directory** matched the glob first and raised
`PermissionError: [Errno 13] Permission denied: '.../reports'`.

```python
report_candidates = [p for p in
                     (list(target_dir.glob("AUDIT-REPORT*"))
                      + list(target_dir.glob("*report*"))
                      + list(target_dir.glob("*REPORT*")))
                     if p.is_file()]
```

Rule of thumb for any evidence-glob in a checkpoint: `is_file()` before reading, and prefer a specific
prefix (`AUDIT-REPORT*`) over a bare `*report*`.

## Verify a gate change against real engagements, not just a fresh dir

Run the changed checkpoint over a completed audit as well as an empty workspace. A gate that only ever sees
empty dirs can pass while its success path is broken — the `reports/` crash above only appeared on an
engagement that had actually produced output.

## Known size problem

`audit-execution-discipline/SKILL.md` is **over the 100,000-character limit** (~102.7 KB), so
`skill_manage(action='patch')` refuses it: any patch is rejected on the resulting size, including a patch
that would shrink it. Until it is split (move a section such as the *Pipeline change checklist* or
*MECHANICAL ENFORCEMENT* block into `references/`), new lessons for that skill have to land in
`references/` files with a pointer added from a different, still-patchable skill.
