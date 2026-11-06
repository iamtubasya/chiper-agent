# Phase-model alignment (0A–0F) + operator-blocker discipline

Two rules that came out of a session where the phase model had silently drifted and an engagement
hit an access wall. Both are class-level: they apply to every audit, not to that target.

## RULE 33 — A phase-model change is a repo-wide grep, not a one-file edit

The pipeline's phase model lives in `audit-pipeline-orchestrator.py` (single source of truth):

```
0A setup      → PHASE_LOG + tracker init
0B recon      → subfinder + httpx + URL probes
0C exploit    → C1 dedicated tools · C2 payload variants · C3 business-logic ·
                C4 matched PoCs · C5 PoC payload variants
0D GATE       → verify-tool-usage (11 checks, HARD BLOCK, auto-rework ×3)
0E FINDINGS   : finding_gate -> validate-findings -> triage_gate   (aggregate/weaponize/chain_builder = 0C-C7)
                (+ 0E-REVIEW: review-candidates 3× check)
0F report     → report-agent → AUDIT-REPORT
```

Two failure modes recur whenever the model moves:

### (a) The checker lags the orchestrator
`audit-checkpoint.py` shipped knowing only `0A|0B|0C|0D`, and used **"0D = REPORT"** — so it
validated the *report* at the phase the orchestrator calls the *gate*, and had no 0E/0F gate at all.
When the phase model changes, patch three things together, never just one:

1. the `--phase` `choices` list,
2. the `phases = {...}` label map,
3. the per-phase check functions (move `findings.json` / `validated-findings.json` out of the
   exploit check into the findings check; add a real gate check that shells out to
   `verify-tool-usage.py` and inspects `FAILED_USAGE`).

Keep a `.bak_<date>_<reason>` copy before rewriting a checker.

### (b) The old convention is scattered through docs
"Phase 0D = report" survived in ~30 markdown files: the launcher and its `references/`,
`bug-bounty` (+ references), `audit-execution-discipline`, `bug-report-delivery`,
seven `security/*/SKILL.md` (`cex-event-contract-audit`, `crypto-library-audit`,
`onchain-finding-verification`, `security-cloud`, `security-scanners`, `security-web-attacks`,
`smart-contract-audit` — all of them literally shared the sentence
*"Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0D)."*),
`exploit-cookbook/references/` (`slowmist-vulns`, `sqli-exfiltration-lab`, `sqlmap-advanced`,
`phase-execution-enforcement`, `redteam-playbook`, `execution-discipline-protocol`),
`onchain-finding-verification/references/forensics-trace.md`,
`context-resilient-skill-design/SKILL.md`, and both copies of `redteam-playbook.md`.

Sweep with the launcher's own self-check grep — the launcher mandates it before declaring done:

```bash
grep -rn "0A-0D\|0A→0D\|Phase 0D" --include=*.md ~/AppData/Local/hermes/skills/
```

Classify each hit by intent, not by pattern:

| Hit looks like | Action |
|---|---|
| gate wording — `verify-tool-usage`, `checkpoint --phase 0D`, `0D→0E`, `must PASS`, `no FAILED_USAGE` | **correct, leave it** |
| report wording — `report`, `severity`, `writeup`, `extraction`, `trace evidence`, `deliver`, `REPORT GATE` | becomes **0F** |
| a `PHASE_LOG` checklist row | add the missing **0D / 0E / 0F** rows |

A safe bulk pass: for every line containing `Phase 0D`, replace with `Phase 0F` **only if** it
contains a report-ish word **and** none of the gate words. Re-run the grep until only gate hits
remain — a single pass leaves stragglers in per-tool reference files and top-level duplicates
(`skills/<x>/` vs `skills/security/<x>/`).

### Don't forget the non-markdown copies
- `_progress/_template/PHASE_LOG.md` (the starter every engagement copies)
- the live `_progress/<target>/PHASE_LOG.md`
- `bundle-src/audit-pipeline-bundle-v1/toolkit/scripts/` (the handoff bundle is a *copy*)
- the handoff ZIP — after rebuilding, **md5-compare live file vs zip entry**; a zip built before
  the last edit silently ships the old script.

### Evidence-checker pitfall — globs match directories
A report check written as `target_dir.glob("*report*")` matched a **directory** named `reports/`,
and `read_text()` raised `PermissionError`, aborting the entire checkpoint run (it looks like a
broken script, not a bad target). Always filter:

```python
report_candidates = [p for p in target_dir.glob("*report*") if p.is_file()]
```

Every checker that reads what a glob returned needs the same guard — audit dirs routinely carry
`reports/`, `evidence/`, `logs/`, `scans/`.

## RULE 34 — A blocker that needs the operator is reported ONCE, then work continues

The operator's standing rule is execution over interrogation. When an engagement hits a wall only
they can clear (an account the target auto-restricted, a session cookie, a scope ruling), the
correct shape is:

1. **State the blocker with exact evidence** — endpoint, HTTP status, response body, timestamp.
   ("`GET /restrictions/api/v1/user-restrictions` → `{"permitted_actions":[1,2],
   "restriction_type":2}`; first navigation resolved to `/main/banned`.")
2. **Give two or three concrete unblock paths**, each with the artifact that makes it actionable:
   a ready-to-send support ticket; the exact cookie names the harness needs
   (`_vinted_fr_session` + `access_token_web`); the quoted scope clause behind a ruling.
3. **Prepare that artifact yourself** — draft the ticket into the workspace, wire the harness to
   accept a handed-over session — so saying "go" costs the operator one word.
4. **Then keep working the remaining in-scope surface.** Re-asking the same question on later
   turns is the failure mode; so is idling on a "waiting for you" message. Enumerate what is still
   testable without the blocked dependency (unauthenticated API surface, secondary target groups,
   mobile app static analysis) and do that.

Two supporting habits:

- **Never route around an access block by creating a second account.** A target that
  auto-restricts a fresh account scores that as abuse; one support ticket is faster and safer.
- **When the operator asks "is the framework/tooling up to date?" treat it as a verification task**
  with a mechanical check (the grep above, a checkpoint run against a completed engagement dir),
  not as a memory question. Report what drifted, what you fixed, and the verification output.

## Reporting shape for a blocked engagement

End the status with the three lists the operator actually needs:

- **Tested and negative** (with the exact probe) — proves the surface was covered, not skipped.
- **Unreachable / coverage gaps** (NXDOMAIN, edge `RBAC: access denied`) — name the failure, do not
  imply a result.
- **Blocked** (what only they can clear) — plus the prepared artifact.

Never let a gap read as a negative, and never let a negative read as coverage you did not earn.
