# The fail-open finding gate — why an audit produced only formalistic findings

**Date:** 2026-10-07 · **Trigger:** operator said the findings were "ngaco — banyak temuan yg hanya
formalities, by design, informational, dan tidak terkait dgn keamanan data, user, sistem, business
logic ataupun dana/keuangan". The audit output was garbage; this is the root cause and the fix.

## Symptom

`D:\data hermes\bug-bounty\gated.json` held **83 candidates, 12 flagged `verdict: REPORT`** — every
one of them junk:

| Claimed | Actual "evidence" |
|---|---|
| `# Vector 4: RCE/SSRF` — impact score **16** (code-exec + ssrf) | the **name of a test file**; body = `**Tool**: curl … **Exit code**: 0` |
| `# Vector 2: Auth bypass` — score 6 | a **procedure label**, no request/response |
| `Output` — score 5 | `curl: unknown --write-out variable` — a **tool error** |
| `2. 1. # Vector 4 …` | the gate had **re-ingested its own survivor report** |

## Four defects in `finding_gate.py` (all in the old version)

1. **FAIL-OPEN default.** `verdict = "REPORT"` was the initial value; findings had to be *knocked
   down*. → default must be `DOWNGRADE`; a finding must **earn** `REPORT`.
2. **Impact regexes ran over the WHOLE text** including the test/vector label, so the *name of a
   test* ("Vector 4: RCE/SSRF") scored as code-exec+ssrf (16). → strip labels first.
3. **"Proof" too weak.** Matching `curl|http|response|exit code … 0` treated *"the tool ran"* as
   evidence. → require a real HTTP status, response body, state change, or leaked value.
4. **No junk / non-finding filter.** Tool errors and reference listings became candidates.
   → drop `command not found` / `curl: … failed` / `timed out` / `traceback`, and titles like
   `Ref File`, `Payloads (20 loaded)`, `Output`.

Plus a **feedback loop**: the gate's own output (`REPORT-survivors.md`, `gated.json`) was re-ingested
as input → duplicates multiplied. Skip self-generated sources; dedupe near-identical records.

## Structural defect in the orchestrator (0E/0F)

- 0E handed the **raw unfiltered `findings.json`** to `validate-findings.py`, so the gate's verdict
  was silently bypassed. Correct chain: **gate → `survivors.json` → validate → report.**
- Gate failure was a **warning** (`⚠️ continue with findings.json`) → fail-**open**. Now: gate
  failure ⇒ **refuse to continue**; and on 0 survivors **suppress the report**.
- 0F, on missing/empty validated findings, **wrote an AUDIT-REPORT.md** that read "No findings
  identified … ✅ All mandatory steps completed / Validation passed" — a false "completed audit".
  Now it returns `None` (no report). **Silence is the correct output when nothing is proven.**
- `validate-findings.py` crashed with `ZeroDivisionError` when it received 0 candidates
  (`len(self.validated)/len(self.findings)`); guard added.

## The fix (v2 gate — what to keep)

```
IMPACT match (on label-stripped text)  AND  PROOF  -> REPORT   (else DOWNGRADE/DROP)
NOT_A_FINDING (ref/payload listing, label, scaffold) -> DROP
JUNK (tool error / empty output)                     -> DROP
info-only / by-design / dead-chain                   -> DROP
```

Proof = an HTTP status line, a JSON/HTML body, an observed state change (`before`/`after`,
`changed from`), or a leaked secret. `Exit code: 0` alone is **explicitly not proof**.

Also: the gate emits `survivors.json` (findings-shaped) as the ONLY input the report may use.

## Verification (do this before trusting any gate)

Control pair: one deliberately garbage entry + one deliberately real entry; verdicts must split.

```
same 83-record input:   old gate: 12 REPORT / 66 DOWNGRADE / 5 DROP
                        v2 gate :  0 REPORT /  2 DOWNGRADE / 81 DROP

control:  "# Vector 4: RCE/SSRF"                       -> DROP
          "missing HSTS header"                         -> DROP (info:headers)
          "GET /api/patient/2 -> HTTP/1.1 200 … other patient data leaked"
                                                        -> REPORT (authz-bypass, pii-exposure)
end-to-end 0E→0F on the real evidence: 0 survivors -> report SUPPRESSED, not a shell.
```

**A gate that never returns 0 is not filtering.** Re-run it on the last real engagement's artifacts
after any change to `finding_gate.py` / the orchestrator's 0E path.

## Files

```
~/AppData/Local/hermes/scripts/finding_gate.py                 (v2, fail-closed + survivors.json)
~/AppData/Local/hermes/scripts/audit-pipeline-orchestrator.py  (0E chain; 0F suppress-on-empty)
~/AppData/Local/hermes/scripts/validate-findings.py            (empty-input guard)
backups: finding_gate.py.bak_20261007_*, audit-pipeline-orchestrator.py.bak_20261007_*
```

## Related

- RULE 28 (pipeline output ≠ findings), RULE 24 (candidate review 3×), RULE 35 (scanner-output FP
  classes) — this is the mechanical enforcement of those rules.
- `triage-validation` (user-owned) owns the human 7-Question Gate; it needs the same
  fail-closed principle. **Recommend `hermes curator adopt triage-validation`** so the
  "default-to-REPORT is a finding-generator" lesson can be embedded there too.
