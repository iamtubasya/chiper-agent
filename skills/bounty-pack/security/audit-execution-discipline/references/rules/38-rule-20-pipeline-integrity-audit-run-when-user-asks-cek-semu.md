## ⛔ RULE 20: Pipeline Integrity Audit (run when user asks "cek semua file/phase/workflow/pipeline")

**User correction (2026-09-24): "All file, phase, workflows dan Pipeline cek lg, apa ad yg error, salah path, orphan, atau empty shell, intinya harus aman semua" + "Cek Pipeline orchestrator, ad yg missing file gk"**

Four-part verification, ALWAYS from disk (never from claims). Run in this order:

**Part 1 — Script integrity.** For every audit script in `~/.chiper/skills/bounty-pack/`:
- exists, >200B (no empty shell), `python -m py_compile` passes
- count the real ones: 17 scripts as of 2026-09-24 (orchestrator, force-full-execution, execute-variants, track-poc-execution, execute-poc-variants, verify-tool-usage, validate-findings, report-agent, audit-sequential, audit-checkpoint, audit-state, audit-exec-tracker, aggregate-findings, poc-pipeline, audit-run-all, finding_gate, chain_builder)

**Part 2 — Cross-script contracts.** What the GATE reads must be exactly what executors write:
- `verify-tool-usage.py` reads: tools-usage.json, variant-usage.json, poc-execution.json, poc-variant-usage.json, variants/, poc-variants/
- grep the `target_dir / "..."` write patterns in each executor and diff. Any gate-read file with no writer = contract gap = pipeline silently passes/fails wrong.

**Part 3 — Flag & path cross-check (the #1 silent bug class).**
- Every `--flag` the orchestrator passes to a subprocess MUST exist in that script's argv parser. Live bug found 2026-09-24: orchestrator called `audit-sequential.py --recon-only` (flag doesn't exist) so auto-rework recon was a guaranteed failure.
- Every skill-reference path in scripts MUST resolve: payload/hackskill files live in `skills/security/exploit-cookbook/references/` (92 files). Scripts had pointed at `bb-audit-launcher/references/` (wrong dir, 0/20 refs) — all 3 occurrences fixed.
- Skill-level: grep SKILL.md internal refs (`references/x.md`, `scripts/x.py`) against the skill dir + global scripts dir. 0 broken refs allowed in security/ (audit pipeline); other domains are lower priority.

**Part 4 — Data integrity + manifest sweep.**
- `D:/data hermes/poc-compact/manifest.json`: valid JSON, count repos (2223)
- `nuclei-index.json` + `nuclei-templates/` exist
- FULL sweep: for every manifest entry, `repo_dir / f` must exist (try `\\`→`/` and `/`→`\\` variants — manifest uses backslashes). 2026-09-24 sweep: 61,135 files, found 40 missing across 36 repos → all recovered via raw.githubusercontent.com fetch (`https://raw.githubusercontent.com/{owner}/{repo}/main/{path}`, fallback `master`). Repo name format: `Owner_RepoName` (first `_` splits owner/repo).
- Zero-file repos (304) are legit empty entries, not data loss — do not "fix" them.

**MSYS pitfall (recurring):** MSYS `/tmp` ≠ Windows `C:\tmp` for native Python; `python "C:\tmp\..."` fails. Copy to `$LOCALAPPDATA/Temp` with native-style `/home/agentuser` paths, or `wslpath -w` to convert.

**When a fix is needed:** patch the script, re-run `py_compile`, re-run the failed part of the sweep, report before/after with numbers.

> **Recipes & sweep code:** `references/poc-data-integrity.md` — full manifest sweep + GitHub raw-fetch recovery + MSYS path gotchas.

