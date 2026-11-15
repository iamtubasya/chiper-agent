# Phase-set parity: checkpoint ↔ orchestrator (0A–0F)

## The authoritative list

`audit-pipeline-orchestrator.py` is the single source of truth:

```
0A setup    → PHASE_LOG + tracker init
0B recon    → subfinder/httpx/URL probes → urls.txt
0C exploit  → C1 dedicated tools, C2 variants, C3 business-logic, C4 PoC, C5 PoC variants
0D gate     → verify-tool-usage (11 checks, HARD BLOCK)
0E FINDINGS   : finding_gate -> validate-findings -> triage_gate   (aggregate/weaponize/chain_builder = 0C-C7)
0F report   → report-agent → AUDIT-REPORT.md/.html/.pdf
```

`audit-run-all.py` is a thin wrapper around it — do not let a second phase model grow there.

## Why this drifts, and what breaks when it does

Finding (2026-10-01): `audit-checkpoint.py` still accepted only `0A|0B|0C|0D` and labelled `0D` as
"REPORT", while the orchestrator had moved the report to `0F` and made `0D` the verify-tool-usage
gate. The consequences are silent, not loud:

- a phase set that stops at `0D` never gates the findings layer (0E);
- `--phase 0D` reported "report exists" for a run that had not reached the report step;
- `--phase all` could come back clean on an engagement that was nowhere near done.

A checker that reads the wrong phase names is worse than no checker: it manufactures confidence.

## The self-check (run after ANY edit to either file)

```bash
grep -rn "0A-0D\|0A→0D\|Phase 0D" scripts/ skills/
```

Every remaining hit must mean **the GATE**. Two legitimate survivors are:

- the launcher's own rule text that quotes the grep, and
- `references/pipeline-triaging-*.md` explaining that `0A→0D` is the *wrong* model.

Everything else gets rewritten: `0D` → `0F` when the sentence is about writing/loading the report
(`bug-report-delivery`, "report phase", "severity classification in report", "REPORT GATE",
"include … results in report"), and left alone when it is about `verify-tool-usage` / `checkpoint`.

In this session that sweep touched ~30 files: the launcher SKILL.md and 8 of its references,
`bug-bounty/SKILL.md` + references, `audit-execution-discipline`, `bug-report-delivery`,
`context-resilient-skill-design`, seven `security/*` SKILL.md files, and the exploit-cookbook
references. **Sweep the documentation, not just the scripts** — one stale file re-teaches the wrong
model next session.

## Two mechanical traps

**1. `glob()` matches directories, and `read_text()` on one raises.**

```
PermissionError: [Errno 13] Permission denied: '_progress\\rapyd-2026-09-29\\reports'
```

`target_dir.glob("*report*")` matched a `reports/` folder inside the engagement directory. Always
filter before reading:

```python
report_candidates = [p for p in candidates if p.is_file()]
```

This applies to any checker that globs for evidence by name — it is a general pattern, not a
one-off.

**2. Phase renames must reach the templates and the handoff bundle.**

- `_progress/_template/PHASE_LOG.md` and each engagement's `PHASE_LOG.md` carry the phase list;
  a template that stops at 0D seeds the wrong model for every future engagement.
- Re-sync `bundle-src/.../toolkit/scripts/` and rebuild the shipped zip, then md5-compare the
  patched file live-vs-zip. A zip built before the last edit silently ships the old checker.

## Verification that the fix actually works

Run the checker against a **completed** engagement and confirm the new phases pass for real:

```bash
python scripts/audit-checkpoint.py _progress/<done-engagement> --phase 0F
# expected on a finished run: "ALL PHASES 0A-0F VERIFIED"
```

Then run it against a fresh engagement directory and confirm the early phases fail honestly rather
than erroring. Both directions matter: a gate that passes when nothing ran is worse than a gate
that fails.
