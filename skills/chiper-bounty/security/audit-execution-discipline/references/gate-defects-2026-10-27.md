# Gate defects: the regex that matched its own container, and the gate that cannot go green on web3

Found 2026-10-27 while reconciling the web3 hunt skills against the 0A–0F pipeline. Companion to
`gate-defects-2026-10-08.md` (18 pipeline defects) — same genre: **the gate said healthy while
doing nothing, or blocked a run that had actually succeeded.**

Both are reproducible in one command each. Neither is an environment problem; both are code
defects in the gate itself.

---

## D1. `depth_gate.py`: `DEEP_SIGNAL` matches the finding's own `impact` field

### Symptom

A deliberately shallow candidate passes the gate that exists to block shallow candidates.

```
{ "title": "diamondCut has no access control modifier",
  "vuln_type": "access-control", "severity": "critical",
  "impact": "attacker can upgrade the diamond",
  "evidence": "function diamondCut(...) external {",
  "depth": "L1" }
-> [depth-gate] survivors.json: 1 pass, 0 warn, 0 BLOCK      exit 0
```

Remove the `impact` field and the identical candidate is blocked:

```
{ ...same, no "impact" key... }
-> [depth-gate] Temuan dangkal ... Lihat skill exploit-depth.   exit 1
```

### Root cause

`assess()` builds `text = json.dumps(item).lower()` — the whole candidate — then requires
`DEEP_SIGNAL.search(text)`. `DEEP_SIGNAL` includes `impact`. Every finding in this pipeline has
an `impact` key (it is one of the `REPORT_KEYS` used to select candidates). So the regex matches
the container it is stored in, `reasons` stays empty, and `verdict` is `PASS`.

The same self-echo applies to `chain`, `escalat`, `primitive`, `mechanism`, `differential`,
`reproduc` — all of them are plausible *field names* in this schema, not just prose. Any of them
appearing as a key satisfies the "has depth signal" test with zero prose evidence.

### Why it matters more than a normal bug

This is the gate standing between "I saw something alarming" and "I am reporting it", and it is
the one the report-quality discipline leans on. A gate that can be satisfied by adding a key is
worse than no gate: it produces a green tick that a future session cites as evidence of rigour.

### Fix shape (apply to the evaluated fields, not the container)

Score only the *prose* fields, and strip the structural keys before matching:

```python
PROSE_KEYS = ("evidence", "proof", "notes", "summary", "detail", "reproduction", "steps")
STRUCTURAL = {"impact", "title", "name", "vuln_type", "severity", "depth", "level", "id",
              "chain", "primitive", "mechanism"}   # keys that must NOT satisfy DEEP_SIGNAL

def assess(item):
    prose = " ".join(str(item.get(k, "")) for k in PROSE_KEYS).lower()
    ...
    if not DEEP_SIGNAL.search(prose):
        reasons.append("tak ada sinyal kedalaman di BUKTI (differential/mekanisme/primitif/impact)")
```

The `impact` value may still be *read* for the L5 "concrete impact" check as long as it is
checked against a stricter pattern (a named consequence: `ato|takeover|rce|exfil|dump|drain|
insolven|fund loss`), not against the loose `DEEP_SIGNAL` alternation that just contains the word.

### Verification after patching

Re-run both fixtures. The shallow candidate must BLOCK **with and without** an `impact` key; a
real L5 finding with a forge PoC must still PASS. Test both directions — a fix that blocks
everything is the same defect mirrored.

```
python depth_gate.py <shallow-with-impact>.json   # expect exit 1
python depth_gate.py <shallow-no-impact>.json     # expect exit 1
python depth_gate.py <l5-forge-poc>.json          # expect exit 0
```

---

## D2. `deep-audit-mode.py guard`: mandatory web2 toolset makes web3 unconditionally BLOCKED

### Symptom

A contract-only audit with real evidence on disk cannot reach the green gate:

```
target dir: evidence/forge-test.log (PASS), evidence/slither.json, verified source, FINDINGS.md
-> ⛔ DEEP-AUDIT GATE: BLOCKED — real pipeline has not passed for this target.
   MANDATORY tools (all of them, on every enumerated endpoint):
     nuclei · sqlmap · dalfox · ffuf · katana · gau · jsluice · arjun · qsreplace ·
     ghauri · graphql-cop · interactsh · proxy/mitm(8080)
```

### Root cause

`cmd_guard()` delegates to `verify-tool-usage.py`, whose required-tool set and asset manifest are
web-centric: subfinder/httpx/nuclei/ffuf cannot run against a contract with no hostname. On a
web3 track those assets are **structurally** N/A, not unrun.

`gate-defects-2026-10-08.md` §B#10 already fixed this inside the **orchestrator's** asset
manifest (`WEB_ONLY` / `SC_ONLY`, track-aware `needed_for()`). The `guard` path did not receive
the same treatment, so the two disagree: the pipeline can pass, the gate still blocks.

### Why it matters

The standing hard rule is "guard must be GREEN before reporting". On web3 that rule is currently
unsatisfiable by honest means, which leaves exactly two outcomes — a permanently blocked audit, or
a fabricated green. Both are worse than a track-aware gate.

### Fix shape

Give the guard a track argument and two required-tool sets, mirroring the orchestrator:

```
WEB_TOOLS = [nuclei, sqlmap, dalfox, ffuf, katana, gau, jsluice, arjun, qsreplace,
             ghauri, graphql-cop, interactsh, mitmproxy]
SC_TOOLS  = [forge build + forge test, slither, aderyn, and one of {echidna, medusa},
             cast code (deployed bytecode), source-or-bytecode recovery]

--track web|sc   (default web; auto-detect `w3` when the target dir has foundry.toml
                  or *.sol and no live-hosts.txt)
```

And the guard's failure text must name the *track's* toolset, so a web3 operator is not told to
run nuclei against a contract.

### Boundary rule to keep honest

Track-awareness must not become an escape hatch from the curl-only prohibition. The web3
equivalent of "run the mandatory tools" is: `forge build`, `forge test` (a PoC, not a read),
`slither`, `aderyn`, one fuzzer, `cast code` on the live address, and source/bytecode recovery.
Reading a verified contract's source is in-bounds and is the highest-value legitimate track; it is
not a substitute for running the analyzers and the PoC.

---

## Method note — how these two were found

Neither was found by reading the gate. Both were found by **feeding the gate a fixture it should
reject and checking the exit code**:

1. Take the gate's own stated contract ("L0/L1 = BLOCK"; "green means the mandatory tools ran").
2. Construct the minimal input that must fail that contract.
3. Run it. Read the exit code, not the prose.

A gate that has never been fed a negative fixture is untested by definition — its green means
"the code ran", not "the standard was met". Add this to any pre-report checklist: for every gate
you rely on, you should be able to name the fixture you have seen it reject.
