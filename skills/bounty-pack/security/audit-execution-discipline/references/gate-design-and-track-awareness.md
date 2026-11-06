# Designing an audit gate that fails for the RIGHT reason

Learned 2026-10-08 while wiring web3 enforcement into the 0A–0F pipeline and then
running it live against relay.link. Every item below is a way a gate LOOKS
strict while being either unpassable or wrong. A gate that can never pass gets
disabled by the operator; a gate that passes on nothing is decoration.

## 1. A gate must be TRACK-AWARE, or it fails legitimately

`asset-coverage.py` demanded `subfinder / amass / puredns / httpx / katana / gau /
waymore / jsluice / naabu / dork-recon / subs.txt / live.txt` plus the whole web
tool list (`nuclei / ffuf / sqlmap / dalfox / interactor / arjun / wpscan / …`) for
**0C on every track**. On a contract-only target none of those can run — there is
no hostname. Result: **49 of 76 assets NOT_RUN** and a failed run that had done
nothing wrong.

Fix shape (mirrors cleanly to any multi-target-class gate):

```python
WEB_ONLY = frozenset({...})   # assets that cannot act without an HTTP host
SC_TOOLS = ["slither", "aderyn", "myth", "echidna", "medusa"]
SC_ONLY  = frozenset(SC_TOOLS)

def needed_for(phase, td):
    is3 = _is_web3(td)
    out = []
    for cls, assets in MANIFEST.get(phase, {}).items():
        if cls == "refs_web3" and not is3:
            continue
        for a in assets:
            if is3 and a in WEB_ONLY:      # cannot run on a contract target
                continue
            if not is3 and a in SC_ONLY:   # cannot run on a web target
                continue
            out.append(f"{phase}:{cls}:{a}")
    return out
```

Two rules that fall out of it:
- **Put the track-specific assets in the MANIFEST** so `init()` seeds them, and
  filter in `needed_for()` only. Appending them a second time in `needed_for`
  made `check()` report every SC tool twice. One source of truth.
- Track detection must read run metadata, with an on-disk fallback:
  `_is_web3()` reads `run-meta.json:tech` and falls back to a `.sol` /
  `sol-source*` artefact.

## 2. A gate must not demand an artefact NOTHING PRODUCES

`CHECK 13` required `skill-usage.json`. Three scripts **read** it
(`audit-checkpoint`, `verify-tool-usage`, `audit-pipeline-orchestrator`); **none
wrote it**. The gate could therefore never pass — it hard-failed on every run
(`skill-usage.json missing — loaded skills not recorded as applied`).

Before adding a requirement, `grep -rn "<artefact>" scripts/` and confirm at least
one component WRITES it. If the answer is "the agent is supposed to", scaffold it
so the obligation is visible and machine-checkable:

```python
su = self.output_dir / "skill-usage.json"
if not su.exists():
    su.write_text(json.dumps(
        [{"skill": s, "applied": False, "evidence": "", "requests": 0,
          "note": "TODO: set applied=true and point evidence at the file proving you USED it"}
         for s in mandated], indent=2), encoding="utf-8")
```

The agent fills it. Verified both directions: scaffold untouched → `CHECK 13
FAILED: not applied: [...]`; filled with evidence → `CHECK 13 PASS: 9 skills
applied (evidence verified)`.

**Where you PUT the scaffold decides whether it ever runs.** The first version of
this fix was written *inside* the neighbouring `if not lk.exists():` branch (the
one that creates `loaded-skills.txt`) and consequently never fired again: on a
**resume**, `loaded-skills.txt` already existed, the guard was false, and the
scaffold was skipped — so the gate kept hard-failing with the exact symptom the
fix was meant to remove, and the fix looked broken when it was merely
unreachable.

Rule: **key every scaffold on the file it writes, never on a sibling's
existence**, and place it at the same level as that guard:

```python
lk = self.output_dir / "loaded-skills.txt"
if not lk.exists():
    ...build + write loaded-skills.txt...

su = self.output_dir / "skill-usage.json"      # OUTSIDE the guard, own condition
if not su.exists():
    skills = [l.strip() for l in lk.read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.strip().startswith("#")]
    su.write_text(json.dumps([{"skill": s, "applied": False, "evidence": "", "requests": 0}
                              for s in skills], indent=2), encoding="utf-8")
```

An initialiser guarded by *another* file's existence is a latent no-op on every
resume. Test the resume path (run on a directory that already has the sibling
file), not just the cold-start path.

**One design question this leaves open, decide it explicitly:** a scaffold can
only ever say `applied: false`. Nothing in an unattended pipeline can *prove* a
skill was applied — if the orchestrator fills its own entries with
`applied: true`, `CHECK 13` becomes circular and certifies nothing. Either an
agent supplies the evidence, or the check is deliberately weakened to "every
mandated skill has an entry". Do not let the scaffold masquerade as proof.

**RESOLVED 2026-10-08 — auto-evidence each skill from the artefact it GOVERNS.**
Operator chose this over "agent fills it" (does not work unattended) and over weakening
the check. Map `skill -> (precondition, evidence file)`; set `applied: true` only when
that file **exists on disk**; unmapped skills stay `false` and the gate fails, correctly.
It is not circular because the evidence file is written by a *different* component (the
SC toolchain, the reference firer), not by the entry citing it. Measured: 7 of 9
auto-evidenced, and the 2 refusals were exactly the phase-mismatched skills — the
mechanism declined to certify them instead of inventing evidence. Full code plus the
phase-order rule behind those 2 refusals:
`terminal-state-and-phase-appropriate-gates.md` §4 and §1.

## 3. Exit codes LIE for smart-contract analysers

`force-full-execution` classified `rc != 0` as `RAN_WITH_ERROR`. But these tools
exit non-zero **precisely when they work**: slither exits 1 on detections,
echidna/medusa exit non-zero when an assertion FAILS (the failure *is* the
finding), aderyn likewise. A successful 68-finding slither run was recorded as an
error.

Fix — a completion marker overrides the exit code, checked BEFORE the rc branch:

```python
_SC_DONE_MARKERS = (
    "analyzed (", "result(s) found",                       # slither
    "running 88 detectors", "report printed",              # aderyn
    "total calls", "assertionfailed", "test(s) passed",    # echidna
    "test summary", "fuzz: elapsed",                       # medusa
    "analysis was completed",                              # mythril
)
if any(m in _blob for m in _usage_markers):     entry["status"] = "FAILED_USAGE"
elif any(m in _blob for m in _SC_DONE_MARKERS): entry["status"] = "EXECUTED"
elif rc != 0:                                   entry["status"] = "RAN_WITH_ERROR" if len(_blob.strip()) > 50 else "FAILED"
```

Generalisation: a "did it really run?" status must be decided by *evidence of
completion in the output*, never by the exit code alone.

## 4. REWORK can make things WORSE

Observed live: attempt 1 failed with **2** problems → orchestrator re-ran
`force-full-execution` → attempt 3 failed with **7** problems, including
`asset-coverage.json missing` and `poc-techniques-usage.json missing` that had
been fine before. The rework step regenerated some artefacts and invalidated
others.

If you add a rework loop, snapshot the failure set before reworking and warn when
it grows. "More failures after a fix attempt" is a signal to stop and inspect, not
to loop a third time.

## 5. State-skip + deleted evidence = a run that silently analyses nothing

`step 1: SKIP force-full-execution (force-state sudah complete)` fires when
`force-state-<target>.json` says complete. If you deleted `tool-evidence/` but not
the state (or vice versa), the gate then reports
`Evidence files missing for: ['slither', 'aderyn', 'myth']` and the run did no
analysis at all.

Rules for any stateful pipeline on Windows:
- Delete the state AND the evidence together, or neither.
- `taskkill /F /PID` on the parent does **not** kill grandchildren — a surviving
  `force-full-execution` completes on its own and writes `status=complete` AFTER
  you cleaned up. Kill the tree (`taskkill /F /T /PID`) first.
- Re-read state files after killing; do not trust the state you read before.

## 6b. A gate must match the VOCABULARY the producer actually emits

Distinct from §2 ("nothing writes the artefact"). Here the artefact exists and is
full of real entries — the gate just compares it against strings that can never
appear in it, so it hard-blocks forever while looking perfectly reasonable.

Live case 2026-10-08, and it was the single blocker that survived every other fix:

```python
# MANIFEST["0C"]["refs"] — the gate's expectation
["bugbounty-playbook", "poc-technique-atlas", "security-arsenal", "audit-execution-discipline"]

# reference-usage.json — what execute-references.py ACTUALLY writes
[{"ref": "403-bypass.md", ...}, {"ref": "graphql-attacks.md", ...}, ...]
```

`refs` recorded the **fired reference FILENAME**; the corpus is collected from
`skills/security/exploit-cookbook/references/`. `a.lower() in r.lower()` could
therefore never hit — an unpassable requirement, blamed on the run every time.

**How to detect it — do not reason about it, diff the two sides:**

```bash
python -c "import json;print({e['ref'] for e in json.load(open('reference-usage.json'))})"
python -c "import ...asset-coverage... as m;print(set(m.MANIFEST['0C']['refs']))"
```
Zero intersection ⇒ the gate is comparing two different namespaces. That is a
manifest bug, not a run failure.

**Fix shape — decide on what the producer emits, and treat an unknown name as a
manifest error rather than a run failure:**

```python
REF_CORPORA = frozenset({"exploit-cookbook", "security-arsenal", ...})  # real dirs on disk

for key in allkeys("refs"):
    a = d[key]["asset"]
    if fired_n and a in REF_CORPORA:   setu(key, "USED",   reason=f"{fired_n} ref-driven request(s) from {a}")
    elif fired_n:                      setu(key, "N/A",    reason=f"'{a}' is not a real corpus dir (manifest error)")
    else:                              setu(key, "NOT_RUN", reason="no reference-driven request fired at all")
```

The `N/A + manifest error` branch matters: an asset naming no real corpus is a
**bug in the manifest**, and saying so out loud stops it being silently retried
forever. Keep `NOT_RUN` for the genuine case (corpus truly never fired).

Measured effect, same ledger, `--derive` then `--phase 0C`:
`6 ok / 8 fail` → `11 ok / 1 fail` (remaining one was the §2 scaffold) → `12 ok / 0 fail`.

**Corollary for every new gate:** name requirements after the *producer's* output
field, not after the concept in your head. Then prove both directions — re-derive
on a real run directory and read which assets it still blames.

## 7. Keep the anti-fabrication cross-checks

The pipeline verifies that evidence **belongs to the current target**
(`target mismatch: evidence says 'X' but the run target is 'Y'`). That is what
stops a pasted-evidence report. Do not weaken it to make a fixture pass — fix the
fixture.

## Verification pattern that caught all of the above

Build a synthetic run directory and assert BOTH directions:

1. Feature present → gate PASSES.
2. Feature withheld (drop one skill, un-fill the scaffold, mark the wrong track)
   → gate FAILS **and names the missing item**.

A gate that has never been observed failing is not yet known to work. Every fix in
this file was found by running the gate on a real target and reading which assets
it blamed — then checking whether it was right to blame them.
