# Toolkit copy drift — why a fix you already applied "isn't there"

The audit toolkit exists in **three** places on this host. They are *supposed* to be the same code;
they are not, and nothing warned when they diverged.

| copy | role | state found (2026-10-10) |
|---|---|---|
| `%LOCALAPPDATA%\hermes\scripts\` | **LIVE — source of truth.** What the orchestrator, cron jobs and skills actually execute | 79 files, newest (Oct 7–9) |
| `%LOCALAPPDATA%\hermes\bundle-src\audit-pipeline-bundle-v1\toolkit\scripts\` | **handoff bundle** — a COPY, packaged for shipping to other agents | 23 files, ~2 weeks stale |
| `D:\data hermes\bug-bounty\bundle\toolkit\shared\` | deployed copy for the vuln-hunter bundle | 5 files, oldest |

Measured drift: **14 files differed**, every one of `audit-pipeline-orchestrator.py`,
`audit-checkpoint.py`, `finding_gate.py`, `verify-tool-usage.py`, `tool_router.py`,
`execute-*.py`, `chain_builder.py`.

## Why this is dangerous, not cosmetic

The stale bundle contained **`finding_gate.py` v1 — the fail-OPEN version** (default verdict
`REPORT`, label-driven impact matching, `Exit code: 0` counted as proof). The live copy was **v2**,
written specifically to fix *"garbage findings reach the report"* (RULE 39).

`bb-audit-launcher/SKILL.md` instructed the reader to run
`D:/data hermes/bug-bounty/bundle/toolkit/shared/finding_gate.py`. So **following the documentation
executed the exact defect the fix removed** — and the operator has no way to see that from the
output. A "fix didn't work" report here is really a "you ran the old binary" report.

`bb-methodology` likewise pointed the pipeline launch at the `bundle-src/...` copy (1 version
behind), while the live path is `scripts/`.

## The rule

- **`%LOCALAPPDATA%\hermes\scripts\` is the source of truth.** Skills must invoke scripts from there.
- The bundles are **copies**; the architecture is *sync live → bundle*, documented at
  `references/audit-pipeline-bundle-rezip-2026-09-29.md`.
- **Never edit a bundle copy directly** — the next sync overwrites it and the edit vanishes.
- **Never invoke a bundle copy in a skill instruction** — point at the live path.
- Two genuinely bundle-ONLY filesets are NOT drift and must be preserved (the sync tool only ever
  overwrites files that already exist in a target, it never creates or deletes):
  `web2/idor_harness.py`, `web2/scope_narrower.py`, `web3/diff_vs_upstream.py`,
  `web3/invariant_scaffold.py`, and the vendored `toolkit/tools/` (GraphQLmap, SSRFmap,
  race-checker).

## Keep it in step — `bundle-sync.py`

```bash
python %LOCALAPPDATA%/hermes/scripts/bundle-sync.py check    # report drift (exit 1 if any)
python %LOCALAPPDATA%/hermes/scripts/bundle-sync.py sync     # live -> bundle, backs up, then verifies
python %LOCALAPPDATA%/hermes/scripts/bundle-sync.py verify   # md5 only, no writes, exit 1 on drift
```

Deliberately surgical: it only overwrites files a target already holds, so bundle-unique harness
scripts and vendored tools are untouchable.

**Run `bundle-sync.py sync` in the same session as ANY edit to a pipeline script** — otherwise the
next person who follows the documentation gets the pre-fix behaviour. This is the same discipline as
RULE 31 (prove the patch landed), extended to the copies.

## Symptom → diagnosis

| symptom | first thing to check |
|---|---|
| a documented fix has no effect | are you invoking the LIVE path or a bundle copy? `bundle-sync.py check` |
| two skills disagree about a tool's behaviour | they are pointing at different copies; `md5sum` both |
| a gate behaves fail-open after it was made fail-closed | check the bundled `finding_gate.py` version |
