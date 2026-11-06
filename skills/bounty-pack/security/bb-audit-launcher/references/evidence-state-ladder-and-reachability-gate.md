# Evidence-State Ladder + Reachability Gate

> Load at **0E** (findings) and again at **0F** (report). This file decides whether a
> candidate may be called VERIFIED and what severity ceiling it may claim. It exists
> because "the PoC runs" and "an attacker can reach that state" are two different facts,
> and triagers reject on the second one.

Companion files: `feature-abuse-doctrine.md` (how to find), `severity-rules.md`
(what it's worth), `triage-validation-7qgate.md` (7-question kill gate).

---

## 1. Candidate states (every finding carries exactly one)

```
UNVETTED → CANDIDATE → REPRODUCED → REACHABILITY_CHECKED → VERIFIED
        → DEDUP_CHECKED → SCOPE_VERIFIED → IMPACT_PROVEN → RANKED
        → REPORT_READY → SUBMISSION_READY → SUBMITTED
```

| State | Meaning | What it unlocks |
|---|---|---|
| CANDIDATE | hypothesis formed from reading code/traffic; nothing executed | nothing |
| REPRODUCED | PoC ran and the mechanism works — **regardless of how the start state was produced** | nothing |
| REACHABILITY_CHECKED | every precondition the PoC relied on has a written answer to "which public function / which endpoint, called by whom, at what cost, produces this state?" | unlocks severity > MEDIUM |
| VERIFIED | PoC ran against state reached through public / adversary-controlled paths (live, or faithfully simulated from live state) | eligible for ranking |
| IMPACT_PROVEN | demonstrated unauthorized state-change or loss path — **not** TVL, not user count, not volume | eligible for SUBMISSION_READY |
| SUBMISSION_READY | VERIFIED + IMPACT_PROVEN + dedup lanes PASS + scope verified + final review + operator sign-off | may be submitted |

### Severity ceiling by state (hard)

```
CANDIDATE / REPRODUCED / REACHABILITY_CHECKED-failed  →  max LOW
FIXTURE-VERIFIED (reproduced, reachability not shown) →  max MEDIUM
VERIFIED (reachable state)                            →  severity per demonstrated impact
```

No severity above MEDIUM may be written before REACHABILITY_CHECKED passes. A gate that
fails does not promote — it holds, and the finding is labeled with the state it actually
reached.

### FIXTURE-VERIFIED — the label that saves the report

A PoC whose starting state was produced by the test harness rather than by an adversary is
**FIXTURE-VERIFIED**, not VERIFIED. It proves the code path exists. It does not prove
exploitability. Say so in the finding, in those words, and cap severity.

Web3 seeding that triggers this label:
- `vm.store(...)` / direct storage writes
- `deal()` of a balance that a real attacker could not obtain
- `vm.prank(owner)` / `startPrank(admin)` when the program excludes admin-key scenarios
- hand-built fixtures, mock oracles, hand-crafted signed messages that never pass the real relayer

Web2 equivalents: injecting a session cookie the login flow would never issue, hand-editing
a DB row, using a staff-only toggle that no self-service path reaches.

The honest sentence in the report: *"PoC is FIXTURE-VERIFIED: the precondition X was seeded
directly; the public path to produce X was not demonstrated, so this is reported at MEDIUM."*
That sentence is worth more than an inflated Critical that gets closed as Informative.

### IMPACT_PROVEN ≠ scale

`demonstrated impact` = a measured unauthorized state change or a measured loss path.
TVL, MAU, number of rows in the table, or "this is a big company" are **scope**, not impact.
Size belongs in the amplification paragraph after the demonstrated primitive, never in place
of it.

---

## 2. Failure classification (never collapse everything into "safe")

Every failed attempt gets exactly one label, recorded in the coverage ledger:

```
NOT_REPRODUCED         ran it, mechanism did not trigger
DISPROVEN              tested the exact claim, it is false — lane closed
BLOCKED                external gate stopped the test (WAF, KYC, captcha wall, IP ban)
ENVIRONMENT_LIMITATION local limitation (tool missing, no second account, no fork RPC)
LIKELY_SAFE            control test shows the guard works as designed
UNKNOWN                inconclusive — hypothesis stays alive, approach must change
CONFIRMED              evidence supports the conclusion
```

Rules:
- `UNKNOWN` never becomes `PASS`. An empty scan, a 403 wall, and a timeout are all UNKNOWN.
- `BLOCKED` and `ENVIRONMENT_LIMITATION` are **rework items**, not negatives — they must be
  named as blockers in the report of coverage, with what would unblock them.
- `DISPROVEN` requires the actual test, quoted. "Looks guarded" is not DISPROVEN.
- Absence of discovery is not evidence of absence of attack surface.

---

## 3. Reachability questions (write the answers, don't infer them)

For every precondition the PoC depends on:

```
PRECONDITION: <what must be true for the exploit to work>
PRODUCED BY:  <endpoint / function / user action>
CALLER:       <anonymous | any free account | specific role | tenant admin | owner key>
COST:         <$0 / paid plan / social engineering / victim interaction>
REPEATABLE:   <once per account | unlimited | time-gated>
```

Any precondition that cannot be filled in from a **public** path caps the finding at MEDIUM
and forces the FIXTURE-VERIFIED label. This applies to web2 exactly as it does to web3 —
"needs a staff role I cannot obtain" is the same failure as `prank(owner)`.

Chain-specific: a chain is not exempt because its parts are small. Each link carries its own
state; a CANDIDATE link pulled into a chain does not get upgraded by the chain's ambition, and
a chain PoC that seeds any intermediate state is FIXTURE-VERIFIED as a whole. See
`chain-to-impact` → "Multi-Low composition" for the composition procedure.

---

## 4. Dedup — four lanes, written down before submission

Duplicates are the single biggest silent killer of otherwise-good findings. Every candidate
carries this record before it can reach SUBMISSION_READY:

```
Program disclosures:  PASS / FAIL / UNKNOWN    (disclosed reports, resolved findings, changelog)
Repository:           PASS / FAIL / UNKNOWN    (issues, PRs, SECURITY.md, security commits)
Audits:               PASS / FAIL / UNKNOWN    (audit reports, contest findings, remediation)
Deployment history:   PASS / FAIL / UNKNOWN    (current source vs deployed vs audited commit)
```

Classification (exactly one):

```
EXACT_DUPLICATE | LIKELY_DUPLICATE | RELATED_BUT_DISTINCT | NEW_ROOT_CAUSE | UNKNOWN
```

**Any lane UNKNOWN = do not submit.** UNKNOWN is not "probably fine" — it is unverified, and
unverified duplicates are the same as duplicates. Search by root cause and function name, not
by the title you invented.

---

## 5. Asset register (0B output, lives in the workspace)

Every discovered asset gets a record. Status values are the only allowed ones:

```
ASSET:              <host / repo / contract / app / bucket>
TYPE:               <domain | subdomain | api | spa | repo | contract | proxy | mobile | bucket>
SOURCE:             <how it was found: crt.sh | subfinder | bundle | docs | scope page>
DEPLOYMENT:         <chain+address | host+env | repo+branch+commit>
TECHNOLOGY:         <framework / compiler / proxy pattern>
TRUST BOUNDARY:     <anonymous→auth | user→user | tenant→tenant | user→admin>
INTERESTING:        <value-moving / privilege / oracle / upload / export / webhook>
HYPOTHESIS:         <one line per attack surface>
STATUS:             UNKNOWN | CANDIDATE | VERIFIED | OUT_OF_SCOPE
```

`OUT_OF_SCOPE` must cite the program line that excludes it. Never mark an asset "clean" —
mark it UNKNOWN with the reason the test did not run.

---

## 6. STATE checkpoint (write this every few steps, and always before context loss)

```
STATE @ <target> <HH:MM>
findings:    <proven + candidates + state label each>
invariants:  <what must always hold>
tested-safe: <vector -> why it failed / which failure class>
untouched:   <surface not yet tested>
next:        <3 concrete moves>
```

This block is the resume artifact. If the session dies, the next run restarts from it instead
of re-deriving the whole hunt.

---

## 7. Submission shape — master record first

One finding = one internal master record in the workspace (root cause, attack path, PoC,
preconditions & reachability, fixture seeding, scope status, dedup lanes, severity per the
program's own scale, evidence list). The submission text is **derived** from that record and
re-rendered per program in a human researcher's voice — never written from scratch, never
pasted as a template.

A field you cannot fill is a gate you have not passed: mark it UNKNOWN and keep working.
Never delete the field, never invent the value.

Sign-off identity for every report and email: **RESEARCHER_NAME**. Platform aliases only where
the program mandates them.

---

## 8. Four-gate submission review (run in order, all four, before `SUBMISSION_READY`)

```
GATE 1 — REALITY   bug is real, in scope, reproducible from a clean session, evidence on disk
GATE 2 — IMPACT    what can the attacker do now that they could not before? is there a real victim?
GATE 3 — DEDUP     five most recent disclosed reports in the same class read, four lanes (§4) recorded
GATE 4 — QUALITY   title formula, copy-paste request, impact evidence (not a 200), CVSS, one-line fix
```

A gate that fails is not "a note" — it holds the finding at its current state. Two candidates that both
fail Gate 2 are not a Critical when added together; that is composition, and composition has its own
gate (`chain-to-impact` → Multi-Low).

## 9. The 60-second pre-submit sweep

Read the draft once, fast, and answer each line with yes/no. Any "no" = do not submit yet.

```
[ ] title follows "[Class] in [endpoint] allows [actor] to [impact]"
[ ] first sentence states the impact, not the background
[ ] the request in the repro section is copy-pasteable and complete (headers, body, cookie/token)
[ ] the evidence shows the GAIN (victim's data, changed state), not just a 200
[ ] two accounts used, and the report says which one is which
[ ] CVSS vector agrees with the impact paragraph
[ ] one-line remediation names the missing control
[ ] every path/param spelled exactly as in the captured request (no typo drift)
[ ] under 600 words, no hedging words ("possibly", "might", "could")
[ ] severity is what the impact reaches, not what the bug class usually scores
```
