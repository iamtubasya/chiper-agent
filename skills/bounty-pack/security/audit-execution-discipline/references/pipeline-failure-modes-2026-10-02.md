# Pipeline failure modes observed 2026-10-02 (landlordstudio.com resume) — and the fixes

Session: interrupted 0C at 09:36, resumed 16:13. Five engine bugs made the pipeline die or
hang on this target. All were fixed in `~/.chiper/skills/bounty-pack/`. None of them said
anything about the target.

## 1. C2 `execute-variants.py` — unbounded per-tool timeouts kill the whole orchestrator

Symptom:
```
PHASE 0C: STEP 1.4a: Executing PAYLOAD VARIANTS...      <- last line, then nothing
```
`FINDINGS.md` recorded it as "❌ TIMEOUT 1800s → orchestrator MATI". Root cause is exactly the
one documented in `pipeline-tool-timeout-budget.md` §1 — and this file was NOT patched:

```python
res = tr.route_and_run(cls, fuzz_base, target_dir, vector=vector, ev_dir=evidence_dir)   # no timeout_cap
```

Each vector's route_and_run inherits the full tool timeout (sqlmap 900 s, nuclei 1200 s,
arjun 600 s); the orchestrator gives the whole step `timeout=1800`. Any target where ≥2 heavy
tools trigger is guaranteed to abort. `subprocess.TimeoutExpired` is uncaught in
`run_pipeline`, so the *entire* 0C→0F chain dies.

Fix (mirrors `execute-references.py`):
- module globals `_BUDGET = 1500`, `_TOOL_CAP = 120`, `_HTTP_TIMEOUT = 20`
- flags `--budget / --tool-cap / --http-timeout`
- `route_and_run(..., timeout_cap=tool_cap)` in `run_vector_with_tool`
- absolute deadline `time.monotonic() + budget`; loops break early and append a
  `{"status": "SKIPPED_BUDGET"}` entry so the gate still sees a non-empty file and the log
  is honest (skipped ≠ negative)
- `http_probe(url, timeout=None)` → defaults to `_HTTP_TIMEOUT` (was hardcoded 120 s: one
  hanging request cost two minutes)
- `global _TOOL_CAP, _HTTP_TIMEOUT` must be the FIRST statement in `main()` — placing it after
  the argv loop that reads `_BUDGET` raises `SyntaxError: name '_TOOL_CAP' is used prior to
  global declaration`

Same cap added to the other looping layers: `execute-poc-techniques.py` (also gained
`--budget` + a `SKIPPED_BUDGET` meta row), `execute-poc-variants.py` (60 s), and
`execute-business-logic.py` (120 s).

## 1b. The C2 "SKIP" was cosmetic — the subprocess still ran

`run_variants_and_pocs` computed `skip_c2` and changed only the *log line*:

```python
if skip_c2:
    log("STEP 1.4a: SKIP variants (variant-usage.json sudah ada)")
else:
    log("STEP 1.4a: Executing PAYLOAD VARIANTS...")
cmd_v = [...]                                   # <- unindented: runs either way
r = subprocess.run(cmd_v, ..., timeout=1800)
```

So every resume re-ran the full C2 battery (observed: 21 minutes, 16:13:31 → 16:34:37).
The `log` said SKIP while the work happened — the exact "honest label" failure this skill
warns about. Fix: indent the `cmd_v` / `subprocess.run` / result-handling block under the
`else:`. C3–C6b were already gated correctly; only C2 had this shape.

## 2. Scope leak — recon `urls.txt` carries third-party hosts

`urls.txt` had 67 × `cdn.prod.website-files.com` plus youtube / instagram / facebook /
twitter / `play.google.com` (the dork layer adds them). `discover_urls` took the first 10
URLs regardless of host, so C2 (and in an earlier session, nuclei auth-bypass) pointed at
third parties — a scope violation, not just noise.

Fix: `discover_urls` derives the registrable root from the target and keeps only
`h == root or h.endswith("." + root)`.

## 3. Fuzz target was non-deterministic (and picked dork garbage)

`discover_urls` built a `set`, so ordering varied per process; the first element became the
fuzz target. Real log line:

```
TOOL dalfox -> https://landlordstudio.com/tel:(270)6719733
```

Fix: explicit `sorted()`, plus a priority key that ranks application hosts
(`portal.`, `api-portal.`, `api-`, `tenant.`, `nexus-`, …) above the marketing site, then
shortest URL first.

## 4. C1 re-runs on every resume, and on Windows it can hang forever

`run_pipeline` called `self.run_force_execution()` unconditionally inside the 0C block, so a
resume re-fires the whole dedicated-tool battery even though
`trackers/force-state-<target>.json` already said `{"status": "complete"}`.

Worse, on Windows `subprocess.run(shell=True, timeout=N)` kills only `cmd.exe`; the grandchild
(arjun/sqlmap/nuclei) survives, keeps the stdout pipe open and `communicate()` blocks past the
timeout. Observed: orchestrator alive 20+ minutes after arjun was started, log frozen at
`STEP 1: Running FORCE FULL EXECUTION...`.

Fix: `_force_state_complete()` reads the force-state file and 0C skips C1 when it is
`complete`. Also note the tree-kill in `tool_router._run` is what makes *its* timeouts real —
but C1 does not go through the router, hence the separate guard.

## 5. What actually happened to the target (so the next session does not re-derive it)

- C2 finished cleanly after the fix: 244 requests, 15/15 vectors, **0 real positives**
  (the "interesting" hits were a 404 page echoed for a dork URL and the helpdesk SPA
  answering 200 for every `?test=`).
- Sustained multi-endpoint activity (~60+ requests: register/login/OTP/forgot-password) from
  one IP earned an **Azure Front Door WAF block on `portal.landlordstudio.com/Account/Login`**:
  `GET → 403` (body `We could not complete your request, please try again or contact support.`,
  header `x-azure-ref`), `POST → 500`. The block is host-scoped: the same path on
  `sparkrental.staging.landlordstudio.com` still returned 200.
- **Lesson for triage:** a "no rate limit, all HTTP 200" observation taken during the first
  ~15 attempts is NOT evidence of missing throttling — the control here only manifests after
  tens of requests, as a non-standard 403/500 at the edge instead of 429/`Retry-After`.
  Do not write an unthrottled-login finding from a short burst. Reserve ~30 requests of
  budget for a *throttle-shape* test, and re-read the status codes after it.
- Once the WAF blocks the login endpoint you cannot mint fresh sessions, and the API session
  cookies are short-lived (~1 h). Order the manual work accordingly: do all
  authenticated/api-portal testing FIRST, keep the auth-abuse tests LAST.

## 5b. `execute-poc-techniques.py` was broken in three ways (C6b + gate CHECK 11)

Found only because the 0D gate refused the report. All three are needed for C6b to
produce anything the gate accepts.

1. **Regex with doubled escapes crashed on the first payload.**
   `detect_payload_class` read `r"(select|union|' or |sleep\\(|…)"` — in a raw string
   `\\(` is "literal backslash + open group", so `re.search` raised
   `re.PatternError: missing ), unterminated subpattern at position 0`. The whole C6b
   step died instantly. Six more patterns in the same function had the same class of
   error (`\\.` instead of `\.`). Fix: single backslashes. Verify:
   `detect_payload_class("' UNION SELECT 1--") == "sqli"`.

2. **Wrong output filenames — C6b clobbered C5.** The script was a copy of
   `execute-poc-variants.py` and still wrote `poc-variant-usage.json` and
   `poc-variants/`. So `poc-techniques-usage.json` never existed and gate CHECK 11
   (`verify_poc_techniques`) reported "execute-poc-techniques.py never ran" forever —
   while quietly overwriting C5's evidence. Fix: write
   `poc-techniques-usage.json` + `poc-techniques-evidence/`.

3. **Entries without `evidence_file` trip the 30%-missing rule.** CHECK 11 requires
   each entry's `evidence_file` to exist and be ≥100 bytes, with ≤30% missing. The
   repo set here is ~150 entries of which only ~41 are executable; the
   `NONWEB_PAYLOAD_TYPE` remainder carried no evidence file at all (73% missing → FAIL).
   Fix: write a real evidence file for *every* entry (the non-web ones document which
   files were inspected and why they are not HTTP-fireable) and set
   `entry["evidence_file"]` accordingly.

Also: `urlopen(req, timeout=120)` per probe in that script — one hanging request cost
two minutes. Lowered to 20 s.

**Gate-blocking statuses.** `verify-tool-usage.py` CHECK 2b hard-fails on
`status in ("FAILED_USAGE", "FAILED")`. `FAILED` is reserved for "we claimed to scan and
did not". A tool that ran and legitimately produced nothing is `NO_OUTPUT` (accepted), and
one that needs flags you cannot supply is `NEEDS_REQUEST_TEMPLATE` / `FUZZ_ONLY`. Here
`arjun` was recorded `FAILED` only because the invocation used `-d 1` against a static
page and hit the 300 s budget; re-running with arjun's own `db/small.txt`, `-d 0 --stable`
completed with `No parameters were discovered.` → recorded `NO_OUTPUT` with the retry
evidence file. **Re-run and re-classify; never just relabel.**

## 6. Pitfall: `MSYS_NO_PATHCONV=1` + `/c/Users/...` silently writes to `C:\c\Users\...`

To stop git-bash mangling `--path /properties`, the reflex is `export MSYS_NO_PATHCONV=1`.
That keeps `/home/agentuser/C:/Windows/...` **literal**, so Python's
`Path("/c/Users/...")` resolves to `C:\c\Users\...` — a different, empty tree. A C6b run
"finished" and left `poc-techniques-usage.json` nowhere the gate looks; the evidence was
sitting under `C:\c\...\`. When a pipeline script takes `--target-dir`, always pass the
**native Windows path** (`/home/agentuser` works too); use `MSYS_NO_PATHCONV=1` only for
URL-path arguments (`--path /subscription`). Confirm with
`ls -la "$OUT/poc-variants"` *and* `ls -la /c/c/Users/...` before trusting a run.

## 7. Verification commands

```bash
python -m py_compile execute-variants.py execute-poc-techniques.py execute-poc-variants.py \
                      execute-business-logic.py audit-pipeline-orchestrator.py
grep -c timeout_cap execute-variants.py execute-poc-techniques.py execute-poc-variants.py \
                     execute-business-logic.py            # expect 1 each
grep -c SKIPPED_BUDGET execute-variants.py execute-poc-techniques.py   # expect >=2 each
```
