# Gate unblock: cleanshot.com (2026-10-27) — two harness FPs, three reviewer FPs

Worked example of a 0D HARD BLOCK that was **entirely harness-side**, plus the 0E over-pass that
followed. Use as the pattern for "gate failed but the target was never the problem".

---

## 1. Starting symptom

```
[02:59:58] ❌ GATE FAILED after 3 attempts — HARD BLOCK
[02:59:58] ❌ PIPELINE FAILED: TOOL USAGE VERIFICATION FAILED after 3 attempts with rework.
[02:59:58] ❌ Tool invocations that never scanned (wrong CLI / hard fail): ['linkfinder', 'linkfinder']
[02:59:58] ❌ asset-coverage FAIL for phase(s): ['0C'] — some asset was READ not USED / skipped-timeout
```

Checkpoint read `21/32`. Nothing in the log implicated the target.

## 2. Diagnosis order (do this before touching anything)

```bash
# a) which tools are stamped FAILED_USAGE, and what does their evidence say?
python - <<'PY'
import json, pathlib
W = pathlib.Path("<target-dir>")
for e in json.load(open(W/"tools-usage.json")):
    if e.get("status") in ("FAILED_USAGE","NOT_FOUND"):
        print(e["tool"], e["status"], e.get("evidence_file"))
        p = W/(e.get("evidence_file") or "")
        if p.exists(): print("   ", p.read_text(errors="replace")[:300])
PY

# b) which 0C assets are not USED/N/A, and what reason does the ledger give?
python - <<'PY'
import json
d = json.load(open("<target-dir>/asset-coverage.json"))
for k,v in d.items():
    if str(v.get("phase","")).startswith("0C") and v.get("status") not in ("USED","N/A"):
        print(k, "|", v.get("status"), "|", (v.get("reason") or "")[:90])
PY
```

Both answers were harness artefacts, not target results.

## 3. FP-1 — `linkfinder` FAILED_USAGE on a WAF 429

Evidence body:
```
Usage: python D:\data hermes\tools\LinkFinder\linkfinder.py [Options] use -h for help
Error: invalid input defined or SSL error: HTTP Error 429: Too Many Requests
```
`exit_code: 0`, `output_bytes: 163`. The tool ran, the WAF refused, and the tool printed its usage
banner **on the error path**. The harness matched `"usage:"` → "CLI wrong, never scanned".

Three-part fix:
1. **Re-run against a reachable in-scope asset** so the negative is real:
   ```bash
   python "D:/data hermes/tools/LinkFinder/linkfinder.py" \
     -i "https://<cdn-host>/build/assets/main-<hash>.js" -o "<target-dir>/linkfinder-out.txt"
   ```
   → exit 0, 64-line HTML report, 13 URLs (all public legal/product links). Write
   `tool-evidence/linkfinder-source-leak-rerun.txt` with the standard header.
2. **Re-stamp the ledger** `FAILED_USAGE → RAN_WITH_ERROR` with `rework_reason` recording that the
   usage banner was an error-path artefact and the CLI was correct.
3. **Fix the root cause** in `force-full-execution.py` (additive, see SKILL.md §2-I): add
   `_reach_markers` and gate the usage check with `and not _reached_target`. Verify with
   `python -c "import ast;ast.parse(open(f).read())"`.

## 4. FP-2 — `force-full-execution` NOT_FOUND

`_account_mandated_tools()` does `shutil.which("force-full-execution")` → nothing on PATH →
`NOT_FOUND` → asset-coverage `N/A "tool not installed"`. But it is the orchestrator's own STEP 1
script and the run log proves execution (`STEP 1: Running FORCE FULL EXECUTION...` 00:38:52 →
`Force execution COMPLETE` 00:50:34), with 54 per-tool evidence files on disk.

Fix: build a real aggregate evidence file, point the ledger at that **file** (a directory
description fails `_ev_ok`), re-stamp to `EXECUTED`:
```
# TOOL EVIDENCE: force-full-execution (orchestrator STEP 1, aggregate)
# RUN WINDOW: 2026-10-27T00:38:52Z -> 00:50:34Z (per run log)
# PER-TOOL EVIDENCE FILES: 54
--- FILES ---
<name>  <bytes>
```

## 5. Marker + schema mismatches (the last two failures)

- `poc-techniques(C6b)` needs the exact marker `# POC-TECHNIQUES EVIDENCE:` — plural, with colon.
  `# POC-TECHNIQUE EVIDENCE` silently fails.
- `poc-variants(C5)` needs `# POC VARIANT EVIDENCE:`.
- `poc-techniques-usage.json` / `poc-variant-usage.json` entries need a `status` of `EXECUTED`,
  `NO_EXTRACTABLE_PAYLOAD` or `NONWEB_PAYLOAD_TYPE` for `any_ran()`; a bare `[]` is only accepted
  with the C4 `_no_poc` proof (`poc-execution.json` present and containing no `EXECUTED`).
- `--derive` rewrites the ledger and discards manual edits → run `--derive` first, then `--mark`
  the residuals, then gate. `--mark` matches the **bare asset name** (`poc-variants(C5)`), not the
  `0C:payload:poc-variants(C5)` key; confirm `on 1 entry`.
- `finding_gate.py` writes `gated.json`/`survivors.json`/`REPORT-survivors.md` to **CWD** — `cd
  <target-dir>` first.

## 6. 0E over-pass — all three reviewers, disproved by hand

`validate-findings.py`: 20 → 0 ("No proven impact on data/user/dana/sistem") — correct.
`review-candidates.py`: 7 READY — all 7 false.
`finding_gate.py`: 3 survivors — all 3 false.

| survivor | script's reason | actual evidence | verdict |
|---|---|---|---|
| `variants/ssrf` | `impacts: ssrf, ssrf`, score 18 | 19/19 lines `[429]` + 149-byte WAF page; origin never saw the request | REJECT |
| `tool-evidence/sqli-sqlmap` | `impacts: code-exec` | `[CRITICAL] all tested parameters do not appear to be injectable` — negative template | REJECT |
| `tool-evidence/sqlmap-sqli` | `impacts: code-exec` | same, different parameter | REJECT |
| `Boreas37 CVE-2026-*-PoC` ×4 | "steps" present | argparse usage dumps; tools never ran | REJECT |
| `sstimap-ssti` | banner lines | own conclusion: `not injectable` | REJECT |
| `variants/waf bypass` | 100 notable | all `[429]`; no body differential | REJECT |

Lesson encoded in SKILL.md §5d: the reviewers are independent votes, not a pipeline; a candidate
whose evidence is 100% one status code has measured nothing.

## 7. Green end state

```
verify-tool-usage.py  → ALL 13 CHECKS PASSED
audit-checkpoint.py   → TOTAL: 33/33 checks passed
findings: 20 candidates → 0 validated → 0 survivors (3 manual passes)
```

## 8. What was NOT a harness problem (real negatives, keep separate)

Cross-tenant authz (403/404 both directions), S3 bucket (13 ops + anon PUT → 403), license
activation (no oracle), URL-scheme consent gate, injection negative, WAF-429 variant sweeps.
Those belong in the coverage table, not the gate-failure notes.
