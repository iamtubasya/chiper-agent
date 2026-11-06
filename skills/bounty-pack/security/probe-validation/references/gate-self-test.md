# Gate self-test — proving a HARNESS works, not just a probe

> Companion to §2f (negative assertion without a positive control). §2f covers **probes** that
> assert about a target. This file covers **gates**: the checker scripts that decide whether an
> audit run may proceed or report. Same law, different victim.

## 0. Why this is its own problem

A probe that never fires gives you a false negative you can notice. A **gate** that is broken gives
you a verdict you will believe, because it looks exactly like a gate that correctly blocked:

```
❌ Target directory not found: \c\Users\...\target     <- dir exists
❌ No tool output evidence                              <- proof file is 437 bytes on disk
❌ No chain analysis                                    <- nothing ever writes that field
⛔ DEEP-AUDIT GATE: BLOCKED                             <- indistinguishable from a real block
```

**Rule: a gate that reports "missing / not found / no evidence" for something that plainly exists is
a GATE DEFECT, not a finding about the target.** Do not accept a BLOCKED verdict until you have seen
the same gate PASS.

## 1. SWEEP THE WHOLE TOOLKIT FIRST — never fix gates one failure at a time

This is the most expensive lesson in this file. A defect in a shared convention (path handling,
output anchoring, evidence ingestion) is **systematic**: it is present in every script that follows
the same convention, and you will meet them one by one, each time thinking "one more bug".

Measured 2026-10-30: the same Windows path bug was fixed **six separate times** across
`validate-findings`, `chain_builder`, `finding_gate`, `report-agent`, `clean_urls`, `php2shell-verify`
— each discovered only when that particular script was next in the chain. Every round cost a full
run-fail-diagnose-patch cycle, and each fix looked like progress.

Do this instead, **once**, before the first run:

```bash
# 1. find every script that turns a CLI arg into a Path without normalising
grep -rn "Path(\(sys\.argv\|args\.\|arg\)" scripts/*.py | grep -v _msys_norm
# 2. find every bare-filename output default (CWD-relative artefact trap)
grep -rn 'default="[A-Za-z0-9_.-]*\.\(json\|md\|txt\)"' scripts/*.py
# 3. find every ingest loop that can read a metadata file as evidence
grep -rn "rglob\|glob(" scripts/*.py
```

Fix all hits in one pass, then compile-check the toolkit and run the smoke test **once**. The
sweep takes minutes; serial discovery takes hours and leaves the last few scripts broken because
the run never reaches them.

Corollary: when you patch one gate, **grep for the identical pattern across the toolkit in the same
step** — not after the next failure. A fix applied to the script that happened to fail is a
partial fix that reports itself as complete.

## 1b. The same law applies to DOCUMENTATION — a wrong fact has many copies

The sweep above is about code. Documentation drifts the same way, and the copies are worse: a wrong
script is one broken execution, but a wrong **documented phase order** is a wrong instruction that
every future session reads and obeys.

Measured 2026-10-30: a phase-ordering error (`aggregate` / `weaponize-gate` / `chain_builder` written
as 0E steps when they are 0C-C7) was corrected in the authoritative file and reported as fixed. A
tree-wide sweep afterwards found **18 further copies** still asserting the old order — including the
`rules-body/body-01.md` and `body-03.md` files, which are the text an agent is most likely to follow.

Rules:

- **A documentation correction is not done until you have swept for the claim.** Correcting the file
  you happened to be reading is step one, not the fix.
- **Classify each hit before editing.** Blanket replacement corrupts history: a line reading
  `Measured 2026-10-10 … (0E, aggregate-findings.py)` is a *dated record of what was true then*, not a
  live claim. **Annotate** it (`recorded at the time as 0E; now 0C-C7`); rewrite only lines that
  assert the current ordering.
- **Scope the grep to assertions, not tokens.** A bare `grep 0E` matches URLs, UUIDs and report IDs.
  Require the phase token *and* the subject (script name / artefact name) on the same line.
- **Numbers drift too.** The same sweep found `verify-tool-usage.py` documented as "11 checks" when
  the script defines **13**. A count in prose is an unverified claim — read the count out of the
  script before repeating it.
- **Derive explainer documents from the source, never from memory.** A pipeline map written from
  memory reproduced the very error it was meant to document. Read the orchestrator and the gate
  scripts, and cite which file each fact came from.

## 2. Two-sided gate test (mandatory before trusting any gate)

| run | input | required outcome |
|---|---|---|
| **positive** | genuinely good artefact set | gate PASSES |
| **negative A** | good set with the proof removed | FAILS, reason names the missing proof |
| **negative B** | plausible but worthless content | FAILS, reason names the weakness |

Cannot make it PASS → the gate is broken, not the target.
Cannot make it FAIL → it is a rubber stamp.
Both defects ship silently, because the pipeline "runs".

Negative controls that must STILL fail after any edit to a validation gate (verified 2026-10-30):

| control | expected verdict |
|---|---|
| "Missing security headers on login page" | filtered — no proven impact |
| "… possibly useful for attackers" | filtered — speculative wording |
| finding whose evidence path does not exist | `No tool output evidence` |
| real evidence, non-terminal impact, no chain | `No chain analysis` |
| same finding present in the chain ledger | **PASSES** (composition path works) |
| report with findings but no severity rating | severity check FAILS |
| report containing "follow"/"below" but no rating | must still FAIL (word boundaries) |

The last two are the pair that matters: when you fix a case-sensitivity bug by switching to a
case-insensitive regex, you must also stop `follow`/`below` from satisfying it — otherwise you traded
a false negative for a rubber stamp. Use `\b(...)\b`.

## 3. Readiness smoke test — validate the harness by making it produce artefacts

Do not validate a pipeline by reading its code. Build a throwaway target, run every stage, confirm
each artefact lands **where the next stage reads it**, then delete the target.

Two failures this catches that code review cannot:

- **CWD-relative defaults.** A stage whose output path defaults to a bare filename writes into
  whatever directory you launched it from (`scripts/`), so the target ends up empty and the next
  phase fails with "not found" — while the script itself printed success. Symptom: junk files
  accumulating in the toolkit dir. Anchor defaults to the input file's parent.
- **Metadata ingested as evidence.** An engagement brief (`scope.md`, `README.md`, `NOTES.md`,
  `policy.md`) living in the same tree as the artefacts gets parsed as a worker output and
  manufactures a phantom candidate that then consumes a real gate slot. Any file whose job is to
  *describe* the run must be excluded from anything that ingests artefacts as findings.

Scaffold shapes matter — the gates are substring/filename checks, not parsers. A phase log needs the
literal tokens the checker greps for, and recon files must sit at the exact paths the checks open.
Write the scaffold to satisfy the checker's expectations exactly, then confirm each phase reports
`N/N` for the phases whose inputs you supplied — and confirm the phases you did *not* feed stay red.
**A smoke test where everything is green is a broken smoke test.**

## 4. Do not "fix" a gate that is right

When the smoke test leaves a phase red because that phase needs real work (a live scan, a tool run
that cannot be faked), that is the gate doing its job. Distinguish:

- red because **inputs are absent** → expected in a smoke test; leave it.
- red because **the gate cannot see inputs that exist** → defect; fix the gate.

Write that distinction into the smoke-test expectation itself, so a later session does not
"helpfully" weaken the gate to make the run green. Weakening a gate to reach green is the same
failure class as fabricating a finding.

## 5. Checklist before shipping any new checker

1. Path handling: normalise shell-supplied paths before `Path()` — a POSIX path from git-bash
   (`/c/Users/...`) becomes drive-relative (`\c\Users\...`) under Windows `pathlib`, so every
   existence check fails. Keep one shared helper and use it in every script, including new ones.
2. Output anchoring: defaults derive from the input's parent, never from CWD.
3. Evidence ingestion: exclude descriptive/metadata files.
4. Positive + two negatives, with the artefacts kept.
5. Compile-check the whole toolkit, then run the smoke test — a syntax error in a rarely-run checker
   only surfaces at the last step, when the most work is at stake.
