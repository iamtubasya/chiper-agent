# Phase placement + the severity matrix (verified end-to-end 2026-10-30)

Two things this file settles with measurement rather than opinion:

1. **Where `aggregate-findings` / `weaponize-gate` / `chain_builder` actually live** (0C-C7, not 0E),
   and what breaks when you document them in the wrong phase.
2. **Whether a Low / Medium / High / Critical finding really survives the whole chain** — a 4-level
   matrix plus 5 negative controls, run through the real scripts.

Both were triggered by the operator asking the right question: *"Seingat sy chain builder ad d 0C,
dan kamu jg yakin ini nnti bug baik low, medium, high dan critical bakal lolos dgn smua alur kerja
ini? Kyknya ketat, spt penjagaan bom nuklir"* — i.e. "I remember chain_builder is in 0C" AND "is this
so strict that nothing gets through?". He was right on both counts.

---

## 1. Canonical phase placement

Read from `audit-pipeline-orchestrator.py` (`run_chain_layer` / `run_findings_layer` docstrings,
2026-10-18 refactor):

```
0C  C1 tools → C2 variants → C3 business-logic → C4 PoC → C5 PoC variants → C6 refs/techniques
    C7 = aggregate-findings → weaponize-gate → chain_builder        ← CLOSES 0C
0D  verify-tool-usage (13 checks, HARD BLOCK)
0E  E4 finding_gate → E5 validate-findings → E6 triage_gate          ← filter + validate ONLY
    then 0E-REVIEW: review-candidates (3x check, low → high)
0F  three hard gates (_gate_depth, _gate_na_discipline, _gate_negative_audit) → report-agent
```

**Why C7 is inside 0C** (orchestrator's own words):

1. aggregate must collect candidates from **all** of C1..C6b — run it earlier and every chain is
   built from partial data.
2. Composing primitives into an attack chain is *exploitation work*, not reporting. 0E must stay a
   pure filter+validate layer.
3. `C7` (not `C5`) because C5 was already taken by "PoC variants" in `run_variants_and_pocs()`.

### The failure mode if you document it as an 0E step

An operator following that doc runs `finding_gate.py` on **raw findings**, which kills every lead
with no attacker-use narrative yet — exactly the Lows the composition doctrine says to keep as fuel
(see `redteam-mindset` §3.5 / `chain-to-impact` Multi-Low). The gate isn't wrong; the sequence was.

Symptom in a run: `finding_gate` reports `REPORT: 0 DOWNGRADE: 0 DROP: N` on a target that
`weaponize-gate` would have shipped 3–4 leads from.

### Data contract between the phases

| phase | reads | writes |
|---|---|---|
| C7-E1 aggregate | worker files + `evidence/` | `findings.json` |
| C7-E1b lead_escalation (2026-11-02) | `findings.json` | enriches `findings.json` with `chain_class`/`next_to_hunt`/`weaponization` (write-back, before weaponize) |
| C7-E2 weaponize-gate | `findings.json` | `weaponized-findings.json` (all, each with verdict), `weaponized-shipped.json` (**SHIP + DEEPEN** — all non-DROP), `WEAPONIZATION.md` |
| C7-E3 chain_builder | `weaponized-shipped.json` | `chains.json` |
| E4 finding_gate | `weaponized-shipped.json` **if non-empty**, else `findings.json` | `gated.json`, `survivors.json`, `REPORT-survivors.md` |
| E5 validate-findings | `survivors.json` (**not** findings.json) | `validated-findings.json` |
| E6 triage_gate | `validated-findings.json` | `triage.json`, `passed-findings.json`, `TRIAGE.md` |
| 0F report-agent | `passed-findings.json` → else `validated-findings.json` | `AUDIT-REPORT.md/.pdf` |

Two contract rules that are easy to get wrong:

- **E5 must read `survivors.json`.** Feeding it `findings.json` re-admits every lead E4 already
  killed.
- **An empty `weaponized-shipped.json` is not "nothing survived".** The orchestrator falls back to
  `findings.json` and lets `finding_gate` apply its own impact filter. Measured on a real target:
  empty shipped → 0 survivors, while the same findings gave 42 survivors with real impact when run
  through the fallback path.

---

## 2. Severity matrix — does each level survive?

Method: 4 findings (one per level), each with a real request+response evidence file on disk, run
through the actual chain `C7 → E4 → E5 → E6`.

| finding | declared | weaponize | finding_gate | validate | triage |
|---|---|---|---|---|---|
| Pre-auth RCE (unsafe deserialization) | critical | SHIP | REPORT (17) | ✅ | 7/7 PASS |
| IDOR cross-tenant IBAN | high | SHIP | REPORT (11) | ✅ | 7/7 PASS |
| CSRF → account takeover | medium | SHIP | REPORT (16) | ✅ | 7/7 PASS |
| Open redirect → OAuth code leak | low | SHIP | REPORT (22) | ✅ | 7/7 PASS |

**4/4 SHIP → 4/4 validated → 4/4 triage PASS.** Every level passes.

What each level actually needs (this is the answer to "is it too strict?"):

- **Critical / High** — nothing extra. A terminal impact (RCE, ATO, PII, funds) is a chain of
  length 1. Declare `chain_class: STANDALONE` or `HEAD`; a terminal HEAD no longer needs a
  `next_to_hunt`.
- **Medium** — may need `chain_analysis` or `next_to_hunt` naming the step that converts it to
  impact. CSRF alone is a primitive; *CSRF → password reset → ATO* is the finding.
- **Low** — must be terminal by itself or carry a named link. A bare open redirect is hygiene; an
  open redirect that lands the OAuth authorization code on an attacker host is token theft and
  passes every gate.

### Negative controls (same run, all correctly rejected)

| candidate | verdict |
|---|---|
| Missing HSTS header | DROP `info:headers` |
| Self-XSS in profile bio | DROP `info:self-xss` |
| `Server: nginx/1.18.0` | DROP `info:version-disclosure` |
| Bare open redirect `/go?url=` | DROP `info:open-redirect-alone` |
| IDOR "we believe … possibly exploitable" | DROP at weaponize **and** again at finding_gate |

**5/5 rejected, 0 survivors.** So the gates are not rubber stamps after the fixes below — that is the
point of running controls alongside the positive matrix.

---

## 3. The seven defects that made "strict" mean "broken"

Before these fixes the same 4-finding matrix produced **0 survivors** — not because the findings
were weak, but because the gates were reading the wrong things. Each entry: symptom → root cause →
fix.

### 3.1 `weaponize-gate.py` deleted the record it judged

**Symptom:** pre-auth RCE filtered by validate with `No proven impact on data/user/dana/sistem`,
while a *medium CSRF passed* — because CSRF's own description happened to contain the word "account".

**Cause:** `analyze()` returned a fresh dict containing only its own dimensions
(`title/text/verdict/severity/chain_class/weaponization/next_to_hunt/fix_regression`). Everything the
analyst wrote was discarded: `impact`, `description`, `evidence` (the proof path list), `id`,
`endpoint`, `method`, `repro_steps`, `verified`, `impact_class`.

**Fix:** start from the original and overlay:
```python
out = dict(rec) if isinstance(rec, dict) else {}
out.update({"title": title, "text": orig_text, ...verdict fields...})
return out
```
**Rule:** a gate may ADD its verdict; it must never delete the fields that prove the finding.

### 3.2 `chain_class` had no `STANDALONE` branch and required a target from every HEAD

**Symptom:** a pre-auth RCE was DROPped with
`CHAIN_CLASS=HEAD but no next-bug-class named — a head with nothing to chain to is a dead end`.

**Cause:** the rule demanded `next_to_hunt` from every HEAD and had no terminal-impact escape. RCE /
ATO / PII read is a chain of length 1 — its impact is already terminal. The gate was dropping exactly
the findings worth the most, and pushing the operator into inventing a fake next step.

**Fix:** `_is_terminal_impact(impact_class, severity, text)` — terminal impact stands alone; only a
non-terminal HEAD/LINK needs a named target. `STANDALONE` + terminal → pass; `STANDALONE` +
non-terminal → drop with "name the missing link or the impact it reaches".

### 3.3 `classify_impact` inflated severity by keyword association

**Symptom:** an IDOR declared `high` came out `critical`, and all four findings came out `critical`.

**Cause:** it walked the ladder `critical → low` and returned the **first** match, over the whole
record blob. Any mention of "account takeover" promoted an IDOR to critical.

**Fix:** collect matches at every level and take the highest, **and let the analyst's declared
severity win** over the keyword guess (record the disagreement in `severity_signals` rather than
silently rewriting it).

### 3.4 `triage_gate.py` read the evidence *path*, not the evidence

**Symptom:** every finding BLOCKED `0/7`, including a pre-auth RCE with a full request/response
capture on disk.

**Cause:** `evaluate()` built `body` from `f["evidence"]`, which is a **list of relative paths**:
- Q2 searched for an HTTP status inside the string `evidence/proof.txt`
- Q6/Q7 measured `len("evidence/proof.txt") = 19 < 60`

**Fix:** `_read_evidence(f, base_dir)` resolves each path against the input file's parent, reads the
files, and concatenates the content (falls back to `text`/`poc`/`tool_output`/`description`). The path
is still included when it cannot be resolved, so a reviewer sees it.

### 3.5 `triage_gate.py` IMPACT_RE had no redirect-based token theft

**Symptom:** open redirect → OAuth authorization code leak scored `Q1_real_impact=False` and
`Q3_in_scope=False`.

**Cause:** the regex knew `token leak` but not the redirect shape; and `HYGIENE_RE` carried a blanket
`open redirect alone` term that fired regardless of chain.

**Fix:** added `open redirect … (oauth|sso|saml|id_token|access_token|authorization code|reset token|magic link|redirect_uri|token)`
both ways round, plus `authorization code (leak|theft)` and `redirect_uri (reuse|mismatch|bypass)`; removed
the blanket hygiene term.

### 3.6 `finding_gate.py` projected survivors down to a lossy shape

**Symptom:** validate could never resolve proof from `survivors.json`.

**Cause:**
```python
surv_json = [{"title": r["title"], "severity": "unknown", "impacts": r["impacts"],
              "evidence": r["text"][:4000], "source_file": r["source"]} for r in survivors]
```
`severity` hardcoded to `"unknown"`, `impact`/`description`/`id` dropped, and `evidence` turned into a
JSON **string** so the evidence files could never be resolved.

**Fix:** `_keep_finding_shape(r)` starts from `r["raw"]` (the original record — `collect_items()` now
stores `"raw": r`) and overlays `impacts`, `impact_score`, `gate_verdict`, `gate_reasons`; evidence
keeps the analyst's path list and only falls back to the source file when there is none.

### 3.7 `aggregate-findings.py` re-ingested the pipeline's own report

**Symptom:** `weaponize-gate` reported `6 DROP of 6` on a 4-finding target, with phantom titles
`# WEAPONIZATION ANALYSIS (attacker-side gate)` and `⛔ DROPPED (failed attacker-side gate)`.

**Cause:** `weaponize-gate` writes `WEAPONIZATION.md` into the target dir; the recursive ingest read it
back as a "finding" and pushed the phantoms through the very gate that produced them. (`TRIAGE.md` was
already in `SKIP_NAMES`; `WEAPONIZATION.md` was not.)

**Fix:** added `WEAPONIZATION.md`, `weaponized-findings.json`, `weaponized-shipped.json`, `triage.json`
to `SKIP_NAMES`. **Standing rule:** any file whose job is to *describe* the engagement or *report on* a
gate must never be readable as evidence of a finding. When you add a new artefact producer, add its
output name here in the same change.

---

## 4. Reproduce / re-verify this matrix

Run after ANY edit to `weaponize-gate.py`, `finding_gate.py`, `validate-findings.py`,
`triage_gate.py`, or `aggregate-findings.py` — a regression here is invisible until a real finding
silently vanishes.

```bash
S="$HOME/AppData/Local/hermes/scripts"; T="<target-dir>"
python $S/aggregate-findings.py "$T"
# A+B (2026-11-02): the sidecar weaponized-shipped.json is written by weaponize-gate
# itself = SHIP + DEEPEN (all non-DROP). Do NOT `cp weaponized-findings.json` over it —
# that reintroduces DROP records. If you are hand-driving, replicate the filter:
python $S/weaponize-gate.py "$T/findings.json" --out "$T/weaponized-findings.json" \
       --report "$T/WEAPONIZATION.md"     # writes BOTH weaponized-findings.json and weaponized-shipped.json
python $S/finding_gate.py "$T/weaponized-shipped.json" --out "$T/gated.json" \
       --survivors "$T/survivors.json" --report "$T/REPORT-survivors.md"
python $S/validate-findings.py "$T/survivors.json" --output "$T/validated-findings.json"
python $S/triage_gate.py "$T/validated-findings.json" --out "$T/triage.json" \
       --passed "$T/passed-findings.json" --report "$T/TRIAGE.md"
```

The **regression harness** (`scripts/severity_gate_regression.py` in THIS skill dir, not `~/scripts/`)
is the authoritative re-verify — prefer it over hand-driving, because it also asserts the negative
controls. Run it after ANY edit to the five gate scripts:
```bash
python "$HOME/AppData/Local/hermes/skills/audit-pipeline-operations/scripts/severity_gate_regression.py" \
       --scripts "$HOME/AppData/Local/hermes/scripts"
```

Expected on the 4-level matrix: `4 SHIP` → `REPORT: 4` → `Validation rate: 100.0%` → `PASS: 4`.
Expected on the 5 negative controls: `0 SHIP` / `DROP: 5` → `PASS: 0`.

Check the two directions **together**. A run that ships 4/4 with no controls proves nothing about
strictness; a run that drops 5/5 with no positives proves nothing about the pipeline being usable.

### Fixture shape that makes the matrix meaningful

Each finding needs all four mandatory weaponize fields, or it is DROPped before any judgement of
quality happens:

```json
{
  "id": "S-CRIT", "severity": "critical", "vuln_class": "deserialization",
  "title": "...", "description": "...", "impact": "...",
  "endpoint": "...", "method": "GET", "verified": true, "confidence": "high",
  "weaponization": "<concrete request + what the attacker gains>",
  "chain_class": "HEAD | LINK | STANDALONE",
  "fix_regression": "<does the naive fix break legit use / move the bug / add a bypass>",
  "impact_class": "rce | pii | account_takeover | ...",
  "next_to_hunt": "<required only for a NON-terminal HEAD/LINK>",
  "chain_analysis": "<required when the finding is not terminal on its own>",
  "evidence": ["evidence/<file>.txt"]
}
```

The evidence file must contain a real `HTTP/1.1 <code>` line — Q2 of the triage gate matches on
`http/\d(\.\d)?\s*\d{3}`. A capture that only says `=== RESPONSE ===` with no status line fails Q2,
which is correct behaviour (a response without a status is not a capture).

---

## 5. MSYS path bug — one helper, every gate

The same Windows pathlib trap bit six more scripts in this session (see `pipeline-invocation-traps.md`
§16 for the mechanism). Rather than patch one at a time, sweep:

```python
import os, re
S = os.path.expanduser("~/AppData/Local/hermes/scripts")
for f in sorted(os.listdir(S)):
    if not f.endswith(".py") or ".bak" in f: continue
    s = open(os.path.join(S, f), encoding="utf-8", errors="replace").read()
    sites = re.findall(r"Path\(\s*(?:sys\.argv\[[^\]]+\]|args\.[A-Za-z_]+)\s*\)", s)
    if sites and "_msys_norm" not in s:
        print(f"{f}: {len(sites)} un-normalised sites", sites[:4])
```

Any hit is a script that will report "not found" for a directory that exists, or (worse) silently
produce an empty result. Fix by importing `msys_path.norm` and wrapping each `Path(argv…)` /
`Path(args.…)`. Scripts confirmed needing it: `audit-checkpoint`, `verify-tool-usage`,
`review-candidates`, `aggregate-findings`, `clean_urls`, `php2shell-verify`, `validate-findings`,
`chain_builder`, `finding_gate`, `report-agent`, `weaponize-gate`, `triage_gate`.
