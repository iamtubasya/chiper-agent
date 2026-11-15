# Gate calibration & negative-audit proof

Measured 2026-10-22 on `docs.obol.org` (rc=1 in 6 s) and `zkb.ch` (539 subdomains). Every
failure below was a gate I had added being **wrong**, not a target being clean. The rule
that generalises: *a fail-closed gate must be calibrated against the legitimate states of
the pipeline before it is allowed to block, and it must distinguish "absent" from
"present but mis-invoked".*

---

## 1. Three ways an over-aggressive gate blocks a legitimate run

### 1a. `depth_gate.py` scanned raw 0C candidates instead of report-bound findings

`findings.json` from 0C-C7 aggregate is a list of **raw candidates** (`url`, `payload`,
`title`) — artefacts that 0E is supposed to walk to L5. The gate treated all 123 as
findings and demanded a declared depth level, so a run with **zero reportable findings**
died at 0F with `123 BLOCK`.

Fix: gate only the files that actually reach a report —
`passed-findings.json`, `survivors.json`, `validated-findings.json`. Raw
`findings.json` / `candidates.json` are 0C→0E input, not gate input.

### 1b. `_gate_na_discipline` rejected legitimate pipeline statuses

The N/A vocabulary grew past the blocklist. These are **not** surrender and must pass:

| status | meaning |
|---|---|
| `SKIP_NO_PARAM` | tool has no parameter to test on this target |
| `STARTED_NO_TOKEN` | needs a session/token not yet captured |
| `NEEDS_REQUEST_TEMPLATE` | needs a request template |
| `SKIPPED_NO_SOLIDITY_TECH` | target is not Solidity |
| `NO_OUTPUT` / `FUZZ_ONLY` | ran, nothing to record |
| `tool not installed` | binary genuinely absent from the host |

Keep one shared `OK_RE` / `_OK_REASON` regex in **both** `asset-coverage.py` and the
orchestrator's `_gate_na_discipline`, or they drift and one of them blocks.

### 1c. `CHECK 2b` and `--derive` did not know the `N/A` status

`verify-tool-usage.py` CHECK 2b reported `unaccounted statuses: ['N/A']`, and
`asset-coverage.py --derive` mapped an `N/A` entry to `NOT_RUN`. Both need `N/A` in their
accepted set, with the reason carried through.

---

## 2. Negative audit must be PROVEN, never assumed

Operator correction (verbatim): *"negative audit ttp harus berdasarkan hasil proses skill
dan tools yg berjalan. kl tools da skill ny hanya djalankan secara tipis di permukaan aj,
atau malah hanya curl aja, ttp harus ditolak, wajib djalankan ulang, spy hasilnya beneran
0 temuan."*

`_gate_negative_audit()` runs **only when findings == 0** and requires:

1. `EXECUTED >= 25` (env `NEG_AUDIT_MIN_EXECUTED`) — below that the run looks curl-only.
2. **Zero `NOT_RUN`** — a tool that is installed but was never invoked blocks the negative.
3. Core-phase ledgers present: `business-logic-usage.json` (C3), `reference-usage.json`
   (C6), `impact-verification.json` (C2d), `dom-xss-usage.json` (C2b).

`NOT_FOUND` (binary absent) is a legitimate N/A and does **not** block. Only `NOT_RUN`
(installed but not invoked) does. Consequence: a thin negative is rejected and the
pipeline must be re-run — which is the intended behaviour.

---

## 3. `NOT_FOUND` vs `NOT_RUN` vs `RAN_WITH_ERROR` — the distinction that matters

Measured: `kiterunner` is installed at `go/bin/kiterunner.exe` (22.9 MB) but the CMD dict
called `kr`, which resolved to a **broken shim** under `Python314/Scripts/`. The shim
printed *"is not recognized as an internal or external command"*, the harness matched that
string, and the ledger recorded `NOT_FOUND` — for a tool that was present the whole time.
`puredns` was worse: absent from the CMD dict entirely, so it was never invoked.

Rules:
- Detect absence with `shutil.which(tool)` **first**; only fall back to output-string
  matching (`is not recognized|command not found|No such file`) when `which()` is empty.
- If `which()` finds a binary but the invocation failed, record `RAN_WITH_ERROR` and note
  the resolved path — that is a CMD-dict bug to fix, not a missing tool.
- Verify the real binary name and subcommand before writing a CMD entry
  (`kiterunner scan <host> -q` works; `kr scan`, `kite scan`, `content-discovery` do not).
- Check the tool's own dependencies (`puredns` requires `massdns` on PATH) before calling a
  dependency failure a tool failure.

---

## 4. Coverage is never reduced to fix a hang — add a timeout

Operator correction: *"Jgn Batasin, nnti skillny truncated"* after `--max-variants 100`
was lowered to 20 to make a 539-subdomain target finish.

Pattern that satisfies both:
```python
try:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=2700)  # 45 m
except subprocess.TimeoutExpired:
    log("  ⚠️ TIMEOUT — pakai artefak parsial, lanjut")
    r = subprocess.CompletedProcess(cmd, 0, "", "timeout-parsial")
```
Applied to `execute-variants.py` (45 m) and `rce-verify.py` (25 m). The variant count
stays at 100; the partial artefacts already on disk are used and the pipeline advances.
A cap silently drops coverage; a timeout only bounds wall-clock.

---

## 5. Batch-runner pitfalls (Windows + MSYS)

- **Never pipe a long run through `tail`** — `$?` becomes tail's exit code, so a failed
  orchestrator reports `rc=0`. Redirect with a Python file handle
  (`subprocess.run(..., stdout=fh)`) and read `r.returncode`.
- **`bash` redirects fail on Windows paths** (`D:\...` is not a bash path). Same fix:
  Python file handle, not shell redirection.
- **PHASE_LOG is the source of truth for progress**, not the exit code and not the
  orchestrator's stdout (buffered). Parse `## PHASE 0X — …\nCOMPLETE`.
- **Zombie duplicates**: a killed parent leaves children running against the same
  target-dir. Before launching, enumerate
  `Get-CimInstance Win32_Process | ? CommandLine -like '*execute-variants*'` and kill
  strays by PID. `taskkill //PID` is mangled by MSYS — use `MSYS_NO_PATHCONV=1 taskkill /PID <n> /F`.
- **RAM guard**: `chrome-headless-shell` + two `dalfox` processes peaked the host at
  ~1.2 GB free. Watch `FreePhysicalMemory`; below ~1 GB the DOM-XSS/RCE stages crash
  silently. One target at a time.
