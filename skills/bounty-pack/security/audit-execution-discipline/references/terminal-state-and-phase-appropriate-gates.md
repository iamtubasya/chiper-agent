# Terminal states, phase-appropriate gates, and gates that block on a CORRECT outcome

Second half of the 2026-10-08 relay.link session. The first half (wrong file analysed,
remappings, phantom requirements, REWORK spiral) is in
`gate-design-and-track-awareness.md`. Everything below is the same class of defect seen
from the other end: a gate rejecting a run **for doing exactly the right thing**.

---

## 1. A gate may only demand artefacts that can EXIST at its point in the sequence

The 0D gate demanded `triage-validation` and `onchain-finding-verification` in
`loaded-skills.txt`. Both are **0E-phase** skills — their evidence is `findings.json`,
which is written *after* the 0D gate runs. They could therefore never be satisfied, and
the run hard-blocked at 0D on every attempt.

Fix — split the mandate by the phase that can evidence it:

| file | contents | verified by |
|---|---|---|
| `loaded-skills.txt` | skills provable at 0D (SC tools ran, `sol-source` exists, refs fired) | 0D gate (`CHECK 13`) |
| `late-skills.txt` | 0E/0F skills (`triage-validation`, `onchain-finding-verification`) | `final_coverage_gate()` — where `findings.json` exists |

```python
core = ["bb-methodology", "security-arsenal"]          # provable by 0D
if web3: core += ["smart-contract-audit", "defi-exploit-forensics",
                  "live-vs-source-bytecode-forensics", "web3-audit",
                  "onchain-source-recovery"]
late = ["triage-validation", "onchain-finding-verification"]   # written to late-skills.txt
```

**Rule:** order every gate's requirements by *"when does the evidence first exist?"*
Anything whose evidence appears later than the gate itself is an impossible requirement
— and it will look perfectly reasonable in code review.

Note the ordering asymmetry that makes this easy to miss: `final_coverage_gate()` runs
after 0F and CAN see 0E artefacts, so a skill can be mandatory for the pipeline without
being mandatory *at 0D*. Mandatory != mandatory-at-this-gate.

---

## 2. A CORRECT REFUSAL still has to leave an artefact

0F did the honest thing and returned `None`:

```
PHASE 0F: Generating FINAL REPORT
  Report source: 105 READY candidates (lolos 3x cek)
  ⛔ validated-findings.json is EMPTY → report suppressed.
```

`final_coverage_gate()` then failed every time with:

```
0F: FAIL 0F:report:AUDIT-REPORT.md  [NOT_RUN]
0F: FAIL 0F:report:email-drafts     [NOT_RUN]
0F: FAIL 0F:report:poc-pdfs         [NOT_RUN]
```

So a **fully successful, honest, negative audit could never be marked complete**. The
gate was punishing the pipeline for refusing to fabricate a finding — i.e. the gate had
the *opposite* polarity to the anti-false-positive rules it was supposed to protect.

Fix — the refusal stands, but it leaves a record:

```python
def _write_no_findings_report(self, why):
    # writes AUDIT-REPORT.md with: "Result: NO REPORTABLE FINDINGS"
    #  + the `why` string, + a table of REAL counts
    #    (candidates / chains / reviewed / ready / validated)
    #  + scope, tech, evidence pointers
    #  + creates the marker dirs the 0F gate looks for,
    #    so the gate can tell "nothing to report" from "step never ran"
```

**Rule: "nothing found" is a RESULT, not an absence.**
Silence is the right output for a *claim*; it is the wrong output for a *record*.
Every terminal branch that returns `None` because it has nothing to do must instead
write a "nothing to do, and here is why" artefact — otherwise a correct negative is
byte-for-byte indistinguishable from a crash, and the gate cannot tell them apart either.

This sits one level below the overclaiming rules: not *"don't overclaim a finding"* but
*"don't let a correct negative look like a failure"*. Both are honesty requirements.

Corollary for the marker dirs: create them **present but empty with a README** rather
than omitting them. The gate then distinguishes "no drafts because no findings" from "the
drafting step never ran" — an omission cannot carry that distinction.

---

## 3. All gates for one artefact must read the SAME bar

```
0F draft requirement  ->  ready-candidates.json       (105 entries) -> demanded >=1 draft + >=1 PDF
0F report step        ->  validated-findings.json     (0 entries)   -> correctly suppressed
```

Two different bars for one decision: the gate demanded drafts for findings the report
had already refused to make.

Fix — drive both from the **final** bar:

```python
_vf = _j(td, "validated-findings.json") or {}
_vf = _vf.get("validated_findings", _vf) if isinstance(_vf, dict) else _vf
validated = _vf if isinstance(_vf, list) else []
...
elif not validated:
    setu(key, "N/A", reason="0 validated findings -> nothing to draft (negative audit)")
```

**Rule:** when two components disagree about whether work exists, they are reading
different intermediates. Pick the bar that actually gates the output (here: `validated`,
the reporting bar) and make every consumer read *that*. `ready` (cleared the review
checklist) is not `validated` (cleared the reporting bar) — and the difference is exactly
where a false positive would slip through.

Measured: `0F: 2 ok / 2 fail` → `3 ok / 0 fail`.

---

## 4. Resolving the skill-evidence circularity — the govern-artefact mapping

`gate-design-and-track-awareness.md` §2 left this open: a scaffold can only ever say
`applied: false`, and if the orchestrator fills its own entries then `CHECK 13` is
circular and certifies nothing. Operator resolved it as **option (b)** — auto-evidence
each skill from the artefact that skill *governs*:

```python
rules = {                                        # skill -> (precondition, evidence file)
    "smart-contract-audit":              (sc_ran,     sc_ev),
    "onchain-source-recovery":           (sol_src,    "sol-source"),
    "live-vs-source-bytecode-forensics": (sol_src,    "sol-source"),
    "web3-audit":                        (sc_ran,     sc_ev),
    "defi-exploit-forensics":            (refs_n > 0, "reference-usage.json"),
    "bb-methodology":                    (refs_n > 0, "reference-usage.json"),
    "security-arsenal":                  (refs_n > 0, "reference-usage.json"),
}
for e in entries:
    ok, ev = rules.get(e.get("skill", ""), (False, ""))
    if ok and ev and (W / ev).exists():          # evidence MUST exist on disk
        e["applied"] = True; e["evidence"] = ev; e["auto_evidenced"] = True
```

Why this is not circular: the evidence file is written by a **different component** (the
SC toolchain, the reference firer), not by the entry that cites it. The check still
certifies something external.

Measured: 7 of 9 auto-evidenced. The 2 that stayed `false` were exactly the
phase-mismatched ones from §1 — the mechanism correctly **refused** to certify them
rather than inventing evidence. Keep that property:

- Only mark applied when the evidence file exists on disk.
- An unmapped skill stays `false` → the gate fails → correct.
- Never let a missing mapping default to "applied". A default of `True` here would
  recreate the exact false-certification the whole gate exists to prevent.

---

## 5. Checkpoint checks inherit every one of these traps

`audit-checkpoint.py` — the 33-check whole-pipeline verifier — carried four of the same
defects simultaneously. All four produced false FAILs and all four were in a *different*
script from the gate that had already been fixed, which is why they survived the first
pass.

| check | defect | fix |
|---|---|---|
| 0B `subs.txt/live.txt/ports.txt/crawled.txt` | impossible on a contract target (no hostname) | `_is_web3_track()` → N/A |
| 0F `Report contains severity / CWE` | impossible in a negative report | gate on `_has_validated_findings()` |
| 0C `candidates.json exists` | legacy name **nothing writes** any more (pipeline emits `review-candidates.json` / `findings.json`) | accept the live artefacts |
| 0C `C4 required PoCs: 0 executed` | empty `poc-execution.json` judged as failure | see below |

The C4 one is worth stating on its own — it is a pure boolean trap:

```python
# WRONG: for an EMPTY list this evaluates False -> "failure"
no_match = len(entries) > 0 and all(e.get("status") == "NO_POC_MATCHED" for e in entries)

# RIGHT: empty means nothing was applicable -> "no match", not "failed"
no_match = (len(entries) == 0) or all(e.get("status") == "NO_POC_MATCHED" for e in entries)
```

**Rule:** a condition written `X > 0 and all(...)` is `False` for the empty case, which
usually means "nothing was produced" — and that is normally *not applicable*, not
*failed*. Decide the empty case explicitly, every time.

Result: **27/33 → 33/33**, with all 6 flipped checks being false-FAILs.

---

## 6. Where the umbrella ends

With all of the above: `0A → 0F`, 0D tool-usage gate PASS, `final_coverage_gate` PASS,
`audit-checkpoint 33/33`, report = an honest negative.

Across every fix in both halves of this session the pipeline was never short of work.
Every single blocker was a gate comparing against something that **could not exist**, or
a correct refusal with **no record** — never a target that had nothing to find.

Useful shorthand when a gate blocks and the run looks fine:

1. Does the artefact the gate names actually exist on disk right now? (if not: §2/§6b)
2. Does anything in the repo ever WRITE it? (`grep -rn "<name>" scripts/`)
3. Can the thing it demands exist *at this phase*? (§1)
4. Is the gate reading the same intermediate the producer reads? (§3)
5. Does the empty/negative case mean "failed", or "not applicable"? (§5)
