# Severity matrix — does the validator pass Low/Medium, or only High/Critical?

> **STATUS: VERIFIED 2026-10-30 — all four levels pass.** The open risk recorded earlier that day
> ("proven for High/Critical only") is **closed by measurement**, not by argument. But it only
> passes *after* seven gate defects were fixed — see §4. Before those fixes the same four findings
> produced **0 survivors**, so "it's strict" was indistinguishable from "it's broken".
>
> Operator question that triggered the work: *"yakin nih bug low, medium, high, critical bakal lolos
> dengan semua alur kerja ini? kelihatannya ketat, seperti penjagaan bom nuklir."* He was right to
> ask — and right about the phase placement too (§2).

## 1. The answer, measured

One target dir, four findings differing **only** in severity, each with a real request+response
evidence file on disk, run through the actual chain:

| finding | declared | weaponize | finding_gate | validate | triage |
|---|---|---|---|---|---|
| Pre-auth RCE (unsafe deserialization) | critical | SHIP | REPORT (17) | ✅ | 7/7 PASS |
| IDOR cross-tenant IBAN | high | SHIP | REPORT (11) | ✅ | 7/7 PASS |
| CSRF → account takeover | medium | SHIP | REPORT (16) | ✅ | 7/7 PASS |
| Open redirect → OAuth code leak | low | SHIP | REPORT (22) | ✅ | 7/7 PASS |

**4/4 SHIP → 4/4 validated (100%) → 4/4 triage PASS.** Low and Medium are not second-class: the
chain does not require them to fake a terminal impact.

### What each level actually needs

- **Critical / High** — nothing extra. A terminal impact (RCE, ATO, PII, funds) is a chain of
  length 1. Declare `chain_class: STANDALONE` or `HEAD`; a *terminal* HEAD no longer needs a
  `next_to_hunt`.
- **Medium** — may need `chain_analysis` or `next_to_hunt` naming the step that converts the
  primitive to impact. CSRF alone is a primitive; *CSRF → password reset → ATO* is the finding.
- **Low** — must be terminal by itself or carry a **named link**. A bare open redirect is hygiene
  (correctly dropped). An open redirect that lands the OAuth authorization code on an attacker host
  is token theft and passes every gate.

This is the honest shape of the requirement: **bounded impact is not enough for a Low — it needs
either terminal impact or a named next step.** A Low that can articulate neither is hygiene, and
dropping it is correct.

### The negative controls that ran alongside it

| candidate | verdict |
|---|---|
| Missing HSTS header | DROP `info:headers` |
| Self-XSS in profile bio | DROP `info:self-xss` |
| `Server: nginx/1.18.0` | DROP `info:version-disclosure` |
| Bare open redirect `/go?url=` | DROP `info:open-redirect-alone` |
| IDOR "we believe … possibly exploitable" | DROP at weaponize **and** again at finding_gate |

**5/5 rejected, 0 survivors.** Running controls next to the positive matrix is what makes the
4/4 meaningful — a matrix that only shows shipping proves nothing about strictness, and a run that
only shows dropping proves nothing about usability.

## 2. The procedure in this file was WRONG — corrected

The original test sequence fed `findings.json` straight to `validate-findings.py` and put
`chain_builder` in the 0E chain. Both are wrong, and the operator caught the second one
(*"seingat sy chain builder ad d 0C"*).

Real placement, from `run_chain_layer()` / `run_findings_layer()`:

```
0C  C1..C6 → C7 = aggregate → weaponize-gate → chain_builder     ← CLOSES 0C
0D  verify-tool-usage (13 checks, HARD BLOCK)
0E  E4 finding_gate → E5 validate(survivors.json) → E6 triage_gate
    then 0E-REVIEW: review-candidates
0F  _gate_depth → _gate_na_discipline → _gate_negative_audit → report-agent
```

Correct sequence:

```bash
S="~/.chiper/skills/bounty-pack"; T="<target-dir>"
python $S/aggregate-findings.py "$T"
python $S/weaponize-gate.py "$T/findings.json" --out "$T/weaponized-findings.json" \
       --report "$T/WEAPONIZATION.md"
cp "$T/weaponized-findings.json" "$T/weaponized-shipped.json"      # orchestrator does this
python $S/finding_gate.py "$T/weaponized-shipped.json" --out "$T/gated.json" \
       --survivors "$T/survivors.json" --report "$T/REPORT-survivors.md"
python $S/validate-findings.py "$T/survivors.json" --output "$T/validated-findings.json"
python $S/triage_gate.py "$T/validated-findings.json" --out "$T/triage.json" \
       --passed "$T/passed-findings.json" --report "$T/TRIAGE.md"
```

Two contract rules the wrong sequence violates:

- **`validate-findings` must read `survivors.json`, not `findings.json`** — feeding it raw findings
  re-admits every lead `finding_gate` already killed.
- **An empty `weaponized-shipped.json` is not "nothing survived"** — fall back to `findings.json` and
  let `finding_gate` apply its own impact filter (measured: empty shipped → 0 survivors; same
  findings via fallback → 42 survivors with real impact).

Re-runnable harness for both directions: `audit-pipeline-operations/scripts/severity_gate_regression.py`.

## 3. Fixture shape that makes the matrix meaningful

A finding missing any mandatory weaponize field is DROPped **before** anyone judges its quality, so
a sloppy fixture produces a fake "the gate rejects Low" result.

```json
{
  "id": "L1", "severity": "low", "vuln_class": "open_redirect",
  "title": "...", "description": "...", "impact": "...",
  "endpoint": "...", "method": "GET", "verified": true, "confidence": "high",
  "weaponization": "<concrete request + what the attacker gains>",
  "chain_class": "HEAD | LINK | STANDALONE",
  "fix_regression": "<does the naive fix break legit use / move the bug / add a bypass>",
  "impact_class": "open_redirect | pii | rce | account_takeover | ...",
  "next_to_hunt": "<required only for a NON-terminal HEAD/LINK>",
  "chain_analysis": "<required when the finding is not terminal on its own>",
  "evidence": ["evidence/<file>.txt"]
}
```

The evidence file must contain a real `HTTP/1.1 <code>` line — triage Q2 matches
`http/\d(\.\d)?\s*\d{3}`. A capture that only says `=== RESPONSE ===` with no status line fails Q2,
and that is correct: a response without a status is not a capture.

## 4. The seven defects that made "strict" mean "broken"

All found and fixed 2026-10-30. Before them the same matrix yielded 0 survivors.

| # | defect | symptom | fix |
|---|---|---|---|
| 1 | `weaponize-gate` returned a fresh dict with only its own dimensions | pre-auth RCE filtered as "No proven impact" while medium CSRF passed (its text happened to contain "account") | start from `dict(rec)`, overlay verdict fields |
| 2 | `chain_class` had no `STANDALONE` branch; every HEAD required `next_to_hunt` | pre-auth RCE DROPped as "a head with nothing to chain to is a dead end" | `_is_terminal_impact()` — terminal impact stands alone |
| 3 | `classify_impact` walked critical→low, took first match | IDOR declared high came out critical; all four came out critical | take highest match, and let declared severity win |
| 4 | `triage_gate` built body from `f["evidence"]`, a **list of paths** | every finding BLOCKED 0/7 (Q2 searched for "HTTP/1.1" inside `evidence/proof.txt`; Q6/Q7 measured len=19<60) | `_read_evidence()` resolves and reads the files |
| 5 | triage `IMPACT_RE` had no redirect→token pattern; `HYGIENE_RE` killed "open redirect alone" unconditionally | open redirect → OAuth code leak scored Q1/Q3 False | added redirect→token patterns, removed blanket hygiene term |
| 6 | `finding_gate` projected survivors to `severity:"unknown"` + stringified evidence | validate could never resolve proof | `_keep_finding_shape()` starts from the raw record |
| 7 | `aggregate-findings` re-ingested `WEAPONIZATION.md` | phantom candidates `# WEAPONIZATION ANALYSIS`, `⛔ DROPPED …` ran through the gate that produced them | add artefact names to `SKIP_NAMES` |

Generalisation worth carrying: **a gate may ADD a verdict; it must never delete the fields that
prove the finding.** And any file whose job is to *describe* the engagement or *report on* a gate
must be in `SKIP_NAMES` — when you add a new artefact producer, add its output name in the same
change.

## 5. Why the operator's instinct was correct

"Ketat seperti penjagaan bom nuklir" is the right reading of a fail-closed pipeline. Fail-closed is
correct for **claims** (never over-report) and dangerous for **coverage** (never silently drop).
Every gate needs both directions proven — see `gate-self-test.md` §1. A gate that cannot be made to
PASS a legitimate Low is exactly as broken as one that cannot be made to FAIL a fabricated High.

The corollary that cost this session its first answer: when you *loosen* a check to fix a false
negative, you must immediately re-run the negative controls, or you have merely replaced a
false-negative gate with a rubber stamp. Both directions, same run, every time.

## 6. Reporting rule

Now that the matrix is verified, the coverage line can say so:
`validator verified for Low/Medium/High/Critical (4/4 matrix, 2026-10-30)`. Re-run
`scripts/severity_gate_regression.py` after any edit to the finding gates before reusing that claim —
a gate patch invalidates the verification, and the failure is silent.
