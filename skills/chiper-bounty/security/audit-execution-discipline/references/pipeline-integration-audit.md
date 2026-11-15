# Pipeline integration audit — "aktif semua? ada yg orphan / empty shell?"

**When:** the operator asks whether the skills/tools are actually integrated with the workflow and
pipeline, whether anything is orphaned / an empty shell / listed-but-never-called, and whether the
audit "berjalan sebagaimana mestinya". Also run it proactively when an audit's *output quality* is
questioned — the two are usually the same question.

## Method (four passes, all cheap)

**Pass 1 — enumerate.** Walk `skills/**/SKILL.md`; collect `{name, size}`. Same for
`~/hermes/scripts/*.py|*.sh`. Report totals.

**Pass 2 — who is referenced by the pipeline.** Grep each skill/script name against the *actual
entry points*, not against every file:
`security/bug-bounty/SKILL.md` (router) · `security/bb-audit-launcher/SKILL.md` +
`references/reference-loader.md` · `security/security-recon/SKILL.md` · `hunt-dispatch/SKILL.md` ·
`scripts/audit-pipeline-orchestrator.py`. A name found in any of these = **integrated**.

**Pass 3 — orphans and empty shells.**
- orphan = not referenced by any entry point.
- empty shell = `SKILL.md` < 900 B, or a reference file < 400 B.

**Pass 4 — classify the orphans, don't just count them.** The count is meaningless without buckets:

| Bucket | Action |
|---|---|
| Non-security domain (crypto/creative/email/automation) | leave |
| Security but *situationally* triggered (loaded when a condition matches, e.g. `waf-stateful-bypass`, `mobile-pentest`, `onchain-source-recovery`) | leave |
| Helper / meta (`skill-*`, `humanizer`) | leave |
| Near-duplicate copies (same skill at top level and under another path) | candidate to consolidate |
| One-off per-engagement scripts (`<client>_*.py`) | candidate to archive |

## Expected result (measured 2026-10-07, 340 SKILL.md)

```
340 SKILL.md total · 109 referenced by pipeline · 231 not referenced
  231 orphans = 156 non-security + ~60 situational-security + ~15 helper  -> all intentional
empty shells (<900B SKILL.md): 0      empty references (<400B): 0
94 scripts · 21 called by the orchestrator · 73 orphan (66 of them one client's <client>_*.py)
```

**Lesson: a high orphan count is normal and is NOT the defect.** A skill registry is a
library, not a wiring diagram — most of the library is meant to be loaded on demand. Do not
"fix" orphans by deleting them; classify, and only flag true duplicates and dead scripts.

## Where the defect usually IS

When output quality is the complaint, the wiring is almost always fine and the **quality gate** is
wrong. In the 2026-10-07 case every phase was correctly wired, every script ran, and the gate was
still the problem — it was fail-open (`references/finding-gate-fail-open-2026-10-07.md`). Audit the
gate's *decision logic* before touching the wiring.

Two real gaps found in that pass, worth re-checking each time:
- a script that exists but **nothing references** (a dork-recon runner with 0 skill pointers) — it
  would never be invoked. Grep for the *script filename* in skills, not just skill names in scripts.
- a skill referenced by prose but **never enforced mechanically** (`triage-validation` is invoked
  by the agent, not by any script) — acceptable, but note it so nobody assumes it is a hard gate.

## Reporting shape

Give the operator four explicit answers: (1) what IS integrated, grouped by phase; (2) what is NOT,
bucketed with a keep/act verdict per bucket; (3) orphan/empty-shell counts with the "normal vs
defect" split; (4) whether it currently runs correctly — and if the complaint was output quality,
the root cause plus the measured before/after of the fix.
