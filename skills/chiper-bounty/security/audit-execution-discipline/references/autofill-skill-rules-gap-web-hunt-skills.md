# CHECK 13 can NEVER pass for the web hunt-* skills — autofill rules gap

**Symptom (sunshine.ch, 2026-10-08).** The orchestrator hard-blocked after 3 rework attempts, every
time with the same line, regardless of how genuinely the skills had been applied:

```
❌ skills loaded but NOT applied: ['hunt-idor', 'hunt-auth-bypass', 'hunt-xss', 'hunt-sqli', 'hunt-ssrf']
RESULT: FAIL (2 failures) → HARD BLOCK → DO NOT GENERATE REPORT
```

Manually marking `applied:true` in `skill-usage.json` did not help: `audit-run-all.py` /
`audit-pipeline-orchestrator.py` **re-generate that file on every run** and reset it to `applied:false`.
Editing the artefact is worthless — the defect is in the producer.

## Root cause

`audit-pipeline-orchestrator.py::_autofill_skill_usage()` decides `applied` from an artefact, never
from a claim — correct design. But its `rules` dict was populated only for the **web3/contract** track
plus a few generics:

```python
rules = {
    "smart-contract-audit": (sc_ran, sc_ev),  "onchain-source-recovery": ...,  "web3-audit": ...,
    "onchain-finding-verification": ...,  "triage-validation": ...,  "defi-exploit-forensics": ...,
    "bb-methodology": ...,  "security-arsenal": ...,  "hunt-rce": (sc_ran, sc_ev),
}
ok, ev = rules.get(e.get("skill",""), (False, ""))   # <-- no key => permanently False
```

There was **no entry for the five web hunting skills**, so `rules.get(...)` returned `(False, "")`
for each and `applied` could never become true. On a web2 target those five are exactly the mandated
set in `loaded-skills.txt` — so CHECK 13 was unsatisfiable by construction. A pure web2 engagement
could not reach 0F at all.

(Distinct from the documented 0D-vs-0E split — that one is about a skill's artefact being a *later*
phase artefact; this one is a key that simply does not exist.)

## Fix

Map each web hunting skill to an evidence file that exists at 0C time, and create those files with
the real technique application:

```python
"hunt-idor":        ((W/"skill-evidence"/"hunt-idor.md").exists(),        "skill-evidence/hunt-idor.md"),
"hunt-auth-bypass": ((W/"skill-evidence"/"hunt-auth-bypass.md").exists(), "skill-evidence/hunt-auth-bypass.md"),
"hunt-xss":         ((W/"skill-evidence"/"hunt-xss.md").exists(),         "skill-evidence/hunt-xss.md"),
"hunt-sqli":        ((W/"skill-evidence"/"hunt-sqli.md").exists(),        "skill-evidence/hunt-sqli.md"),
"hunt-ssrf":        ((W/"skill-evidence"/"hunt-ssrf.md").exists(),        "skill-evidence/hunt-ssrf.md"),
```

Evidence content = what was actually done per class (e.g. `hunt-idor.md`: "two accounts, A read B's
favourites by userId, differential vs control → CONFIRMED"). That is the same honesty bar as the rest
of the gate: the file must describe a real test, not a claim.

Back the script up first (`audit-pipeline-orchestrator.py.bak_<ts>`), then `grep` to confirm the keys
landed (`grep -n '"hunt-idor"' <script>`).

## Round 2 (2026-10-10) — the keys landed, the gate STILL failed. One layer deeper.

The fix above was applied, and this session verified the five keys are present and correct
(`audit-pipeline-orchestrator.py` lines ~978-982). CHECK 13 **still** hard-blocked with the identical
line. Same symptom, different defect — do not assume a recurring symptom means the old cause.

```
❌ skills loaded but NOT applied: ['hunt-idor','hunt-auth-bypass','hunt-xss','hunt-sqli','hunt-ssrf']
```

Root cause this time: every rule demands `skill-evidence/<skill>.md`, and **nothing in the pipeline
ever wrote that file**. The rule is satisfied only when the artefact exists; the artefact had no
producer. A rule that points at a file nobody writes is exactly as unsatisfiable as a rule that does
not exist — the failure just moved from `rules.get(...)` to `Path.exists()`.

**Fix:** the producer must generate it from what actually ran, in the orchestrator (not by hand —
`skill-usage.json` is regenerated each run, so hand-written `applied:true` is worthless):

```python
def _write_skill_evidence(self):
    """Emit skill-evidence/hunt-<class>.md from the artefacts THIS RUN produced."""
    # classes -> keyword sets matched against variant-usage / business-logic-usage / tools-usage
    CLASSES = {"hunt-idor": ("idor","bola","access control","privilege","priv-esc","mass-assign"),
               "hunt-auth-bypass": ("auth","jwt","bypass","session","login","oauth","password","403"),
               "hunt-xss": ("xss","kxss","dalfox","script","ssti"),
               "hunt-sqli": ("sql","sqli","sqlmap","nosql","blind"),
               "hunt-ssrf": ("ssrf","interactsh","oob","redirect")}
    # write a file ONLY when that class has real execution rows; no rows -> no file ->
    # the skill stays applied=false and the gate still fails (correctly).
```

Call it **before** the gate runs (immediately before `verify_tool_usage`/`_autofill_skill_usage`).
Result on a real run: 5 files, 807–1257 B each, each listing the executed vectors with their
`status` + `evidence_file` from the source artefact.

**Discriminator for this whole family** — before blaming your own application of the skill:

```bash
grep -rn "skill-evidence" scripts/          # hits ONLY inside _autofill_skill_usage? -> no producer
```

If the only hits are the *reads*, there is no writer and the rule is unpassable. See
`references/phantom-requirements.md` for the generalised procedure (it is the same class as the 0B
recon ledger in that file).

## Pitfall — do NOT map a hunt skill to `findings.json`

The obvious-looking mapping is circular: `findings.json` is a **0E** artefact, and 0E only runs
*after* the 0D gate passes. Mapping `hunt-idor → findings.json` means the gate waits on an artefact
its own failure prevents. Use a 0C-time file (the `skill-evidence/<skill>.md` pattern above) or an
already-produced 0C artefact.

## Generalisation

A gate that auto-evidenced from artefacts is only as complete as its `rules` dict. When CHECK 13
fails on a skill you demonstrably applied:

1. `grep -n "rules = {" scripts/audit-pipeline-orchestrator.py` and read the dict.
2. If the skill has **no key**, that is the bug — not your application of it. Add a rule pointing at
   an artefact that exists *before* the phase that checks it.
3. Re-check the whole mandated set (`loaded-skills.txt`) has a key, or the next engagement on the
   other track fails for the same non-reason.

Same family as `terminal-state-and-phase-appropriate-gates.md` §1/§4 (phase-appropriate artefacts,
auto-evidence) — but the failure mode here is a missing rule key, so the fix is in the producer’s
dict, not in the artefact.
