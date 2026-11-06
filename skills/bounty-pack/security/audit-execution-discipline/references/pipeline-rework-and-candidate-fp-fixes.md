# Orchestrator rework/dedupe fixes + candidate-FP recipes — verified 2026-10-15 (jochen-schweizer.de, bluewin.ch); §8 added 2026-10-17 (energiekoers.gasunie.nl)

Signatures of bugs found while running the pipeline. All are FIXED in the on-disk scripts; this
file exists so a future session recognises the signatures instead of re-debugging them, and reuses
the validation recipes.

## 1. Gate-rework dispatcher matched the WRONG step (substring order) — FIXED

Symptom: 0D gate failed with `poc-variant-usage.json missing` yet the orchestrator logged
`🔁 REWORK: re-running execute-variants.py`. Cause: the dispatcher checked
`"variant-usage.json missing" in out` BEFORE the poc-pattern, and the poc-string CONTAINS that
substring. The rework re-ran a green step while the actually-missing artefact stayed missing.

Fix in `audit-pipeline-orchestrator.py`: specific patterns checked before generic
(`poc-variant-usage` → `poc-techniques-usage` → `poc-execution` → `variant-usage` ...), plus a new
`_rerun_poc_techniques_step()` branch (missing C6b artefacts used to fall into generic
force-full-execution).

Verify after any gate failure:
```bash
grep "🔁 REWORK: re-running" <orchestrator-log>   # must name the SAME step as the FAIL line
```
Different names ⇒ dispatcher order regressed; fix the order instead of blindly re-running.

## 2. Per-repo tool routing made C5/C6b unfinishable — FIXED (global per-class dedupe)

Symptom: `execute-poc-variants.py` / `execute-poc-techniques.py` called `route_and_run(...)`
PER REPO with `timeout_cap=None` on the SAME `fuzz_urls[0]`. With the manifest fallback
(1365 payload-bearing repos, cap 150) every ssti/sqli/xss-class repo re-ran
sstimap/dalfox/sqlmap to completion — sstimap measured ~40 min/run ⇒ step could not finish by
construction (same failure class as the C6 dalfox bug of 2026-10-10).

Fix: global `_ROUTED_CLASSES` set hoisted outside the repo loop (matches the code's own comment
"tools asli ... sekali per kelas") + `timeout_cap=600`.

Regrowth signature: `tool-evidence/*-sstimap.txt` resets to a small size repeatedly while
`poc-variant-usage.json` entry count stays frozen. Expected after fix: one invocation per class per
step; 150 repo entries land in ~10–40 min including WAF stall windows.

## 3. scope_checker blocked `www.` for a bare-domain --scope — FIXED

`SCOPE GATE BLOCKED: www.<domain> BUKAN dalam scope (<domain>)` although `--scope` was the bare
domain: `_domain_matches()` treated a bare pattern as exact-only. Fix: bare pattern now matches the
domain and any subdomain; negatives (`evil-target.com`, `<domain>.evil.com`) still block. Standalone
check: `python scripts/scope_checker.py https://www.<d> --domain <d> --json` → must be `true`.

## 4. Candidate FP recipes — run BEFORE anything reaches 0E/report

Pipeline impact-verify printed `confirmed=N of M` for artefacts that a deterministic test kills:

- **SSTI "confirmed"**: A/B excerpts identical SPA HTML, `a_has_49`/`b_has_56` true for every
  engine. Kill test: fetch `{{7*7}}`, `{{6*9}}` AND a control (`{{7*8}}`); if 49/56/64 all appear
  in every response, the numbers are page content → FP.
- **Open-redirect "confirmed"**: the verifier parsed a host out of a query VALUE. Kill test:
  `Location:` must be absolute AND external; a relative Location (`/path?q=<payload>`) is same-site
  → FP. Prove with `curl -L -w '%{url_effective}'` — final URL never leaves the origin.
- **DOM-XSS rows** (`dom-sink:mutated-node:SCRIPT`, `console: []`, `payload-present-in-dom`):
  present-in-DOM ≠ executed. Deterministic Playwright test: navigate
  `#<img src=x onerror="document.title='DOMXSSFIRE_9x7'">`, wait 2.5 s, check title/content for the
  marker. 0/8 fired across URL families → all FP.
- **S3-style 200s**: listing 200 + object GET 403 = inventory-only (LOW); never claim content
  access. Identical body bytes across paths = SPA catch-all (see security-scanners).

## 5. Expected NEGATIVE reconcile (not a bug)

0F may log `READY (review) and PASSED (triage) are DIFFERENT bars` / `passed-findings.json is EMPTY
→ NEGATIVE report` while 0E-REVIEW marked dozens READY: the stricter 7-question triage suppressing
impact_score=None/0. Correct behaviour — the NEGATIVE report (guard + COVERAGE sections) IS the
deliverable, not a pipeline failure.

## 6. Runtime planning notes

- SSTImap/poc-variant steps run to completion (no per-tool cap before the 600s fix); one ssti step
  can hold 30–60 min. `STALL-WARN` at 900 s is advisory — prove liveness by newest file mtime in
  the workdir, not by the warning text.
- WAF stall windows: processes idle 5–15 min with zero writes, then land the remaining entries in a
  burst. Idle 10 min ≠ dead.

## 7. Batch fuzzer execution (manual ffuf et al. beside the pipeline) — lessons that cost hours

- **ONE `-w` per FUZZ placeholder; merge wordlists.** `-w listA -w listB` with a single `FUZZ` in
  the URL produced corrupt output (bluewin.ch, 2026-10-15): every result row carried the same URL
  (first word of listB) while the row COUNT came from listA — 4,945 words "returned" 9,504 matches
  that were two paths. Merge first (`sort -u a b > combined.txt`) or add a real `FUZZ2` keyword to
  the URL. **Spot-check before believing counts:** print the first 5 `results[].url` from the JSON;
  repeated URL = broken invocation, discard the output.
- **Calibrate throughput BEFORE a multi-hour batch.** Run a 100–150-word subset of the same
  wordlist against the same host WITHOUT `-s` and read ffuf's own line
  (`Progress: [120/120] :: 4 req/sec :: Duration: 0:00:30`); ETA = words ÷ measured rate
  (measured case: 4 req/s ⇒ 5k words ≈ 21 min — matched the real run).
- **Liveness = the tool's own progress line or the output file's mtime — NEVER process I/O
  counters for Go binaries.** `wmic get ReadTransferCount,WriteTransferCount` does NOT move during
  healthy Go socket I/O on Windows; flat counters look exactly like "stuck" and healthy 100-minute
  runs were killed over this twice. CPU-idle is also normal (network-bound). If you must watch,
  tail the tool's live output (`-stats` / non-silent progress) in a file.
- **Long runs: always `-maxtime <seconds>`.** ffuf writes its JSON on a maxtime exit, so a bounded
  run always leaves a usable (possibly partial) results file; without it, a killed run leaves
  NOTHING — 100+ minutes of scanning produced zero bytes on disk.
- Gentle parallel batches are fine (4 jobs × `-rate 4`), one output path and one `-maxtime` per job;
  `-s` stdout flushed at kill time is not evidence of what the run saw — read the JSON.

## 8. New signatures — 2026-10-17 (energiekoers.gasunie.nl): 0-match plan starves the 0D gate

### 8a. `repos_matched: 0` → producer writes `[]` → gate HARD BLOCK ×3 — FIXED, resume still traps you

Symptom (3× identical rework cycles, then `❌ GATE FAILED after 3 attempts — HARD BLOCK`):

```
❌ asset-coverage FAIL for phase(s): ['0C'] — some asset was READ not USED / skipped-timeout
   (asset-coverage.json: poc-repos(C4), poc-variants(C5), poc-techniques(C6b), shelf
    poc-technique-atlas = NOT_RUN, reason "no evidence: poc-*.json")
```

Cause: `poc-pipeline.py` produced a **valid plan with `repos_matched: 0`** (a static/Foleon-type target
matches nothing in the PoC corpus). The old `if not plan:` branch in `track-poc-execution.py` never
fires for a truthy-but-empty plan, so `execution_log` stayed `[]`; `asset-coverage._no_poc` requires a
**non-empty** ledger with no `EXECUTED` entry, so `[]` fails it.

FIX already in `scripts/track-poc-execution.py` (2026-10-17): a plan with
`repos_matched == 0` and an empty `plan` list now writes
`[{"repo":"NONE","status":"NO_POC_MATCHED","reason":...,"evidence":"poc-plan.json ..."}]`.
`_no_poc` then passes C4, and C5/C6b (`(_no_poc and not pvc)`) pass on their empty ledgers.

**The resume trap:** RESUME mode skips 0C entirely, so the producer does **not** re-run and the stale
`[]` keeps failing the gate even though the script is fixed. Two legitimate exits (pick one):
1. write the `NO_POC_MATCHED` entry yourself **only when `poc-plan.json` proves `repos_matched: 0`**
   (evidence-driven bookkeeping, not fabrication), then resume; or
2. re-run the producer step (`track-poc-execution.py <target> --tech "<tech>" --target-dir <dir>`),
   then resume.

Diagnostic order: read `poc-plan.json` first — if `repos_matched > 0` you have a DIFFERENT problem and
must NOT hand-write a no-match ledger.

### 8b. Negative 0F finished but final gate fails on `REPORT-survivors.md [NOT_RUN]`

Symptom after a clean negative run: `audit-checkpoint` 32/33, failing checks
`0E-REVIEW:review:REPORT-survivors.md [NOT_RUN]` + `REPORT-survivors.md exists (finding_gate)`, while
`gated.json`/`survivors.json` exist and `passed-findings.json` is `[]`. `finding_gate.py` only writes
the report when invoked with `--report`, and the 0E-REVIEW path didn't pass it on this branch.

Fix, then resume the same orchestrator command:
```bash
cd <target-dir> && python <scripts>/finding_gate.py findings.json \
    --out gated.json --report REPORT-survivors.md --survivors survivors.json
```
Measured result: `REPORT-survivors.md` 1768 B written, checkpoint 32/33 → **33/33**, final gate
`🎯 AUDIT PIPELINE COMPLETE`. Note the gate file may list 1 "survivor" that triage still rejects —
§5 applies; the NEGATIVE report stands.

### 8c. FP re-confirmations from §4 on a second target (both killed again)

- open-redirect: raw-socket read showed `location: /stakeholder-event/?q=https%3A%2F%2Fevil…`
  (relative, same origin), hop-2 = `200` with **no** Location, baseline `/?q=marker` byte-for-byte the
  same redirect → checker's `offsite=true` came from the query value. Killed per §4 recipe.
- DOM-XSS: 5 `HIT hash` rows; Playwright showed `window.__DOMXSS` UNSET, payload absent from DOM,
  0 dialogs/0 pageerrors → instrumentation nodes (`mutated-node:SCRIPT`) counted as sinks. Killed per §4.
- SPA catch-all reuse: `/http://127.0.0.1/`, `/http://169.254.169.254/...`, `/api/*` all returned the
  identical homepage bytes (sha match) ⇒ SSRF/API "hits" are §4's SPA-catch-all case.
