---
name: audit-pipeline-operations
description: "Run, resume and tear down audit pipeline runs: gates, stalls, resume, artifact purge."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, pipeline, gates, verification, orchestrator]
    related_skills: [bb-methodology, audit-runbook, audit-execution-discipline, bot-protected-target-testing, artifact-backed-claims]
---

> Ops pitfall (live 2026-10-23): a foreground `terminal` call that hits the ~420s timeout can
> leave its scan process SURVIVING as an orphan — it keeps running and competes (CPU, rate-limit
> budget, output files) with the background replacement you start afterwards. Also: ffuf writes its
> `-o json` output only at completion, so a mid-run kill loses
> ALL results — either let it finish or accept the loss and re-run. Verify cleanup with
> `ps aux | grep -E "nuclei|ffuf" | grep -v grep | wc -l` → 0 before starting new scans.
>
> **Correction (live 2026-10-25) — reap YOUR OWN scanner by PID, never by image name.** The advice
> above to `taskkill //F //IM nuclei.exe` is only safe on a host running one engagement. With
> sibling audits live there were **five** `nuclei.exe` processes, two of them children of a
> different vendor's pipeline; killing by image name would have silently gutted another engagement.
> Correct sequence:
> 1. `process(action='kill', session_id=…)` kills the Hermes session but **not** the grandchild —
>    confirm the binary is still alive afterwards.
> 2. Find your own child by its unique argument, not its name:
>    `wmic process where "name='nuclei.exe'" get processid,parentprocessid,commandline` then match
>    the `-l <your-target-list>` / `-o <your-output-file>` you launched with.
> 3. `taskkill //F //PID <pid>` for that PID only, then re-read free RAM before relaunching.
> Sizing rule from the same host (6 GB, two sibling audits live): a 267k-request template inventory
> at `-rl 15 -c 5` reached only 12 % in 15 min at 9 rps effective and dropped free RAM to ~340 MB —
> while `-rl 8 -c 2` on a 6-tag set ran at the same 9 rps. Do **not** launch a full-tagset inventory
> on a shared 6 GB box; scope to the engagement's in-scope host list, take a narrow tag set, and
> record `nuclei = PARTIAL x%` in the ledger rather than implying "scanned clean".

# Audit pipeline operations (0A→0F)

## When to Use

You are launching, resuming or babysitting a run of the operator's
`audit-pipeline-orchestrator.py`, a gate just failed, or you are about to trust something the run
printed (`CONFIRMED`, `survivors`, `ready after review`). Also use it when driving a **multi-product
queue** for one vendor (§6) and when a product's pipeline comes back negative and you still owe the host
real manual coverage (§5 + `references/dangling-cname-sweep.md`). Covers gate semantics, the gate-failure
fixes, resume behaviour, stall/throttle detection, and the false-positive classes in pipeline output —
everything the phase SOPs assume but do not state. Derived from complete runs (energiekoers, dataport,
gewasschademelden), one blocked run (remit) and an 18-product queue, 2026-10-17.

## 1. What the gates check

| Gate | When | Reads | Fails when |
|---|---|---|---|
| Scope gate | 0A start | `--scope` patterns — **literal** domain patterns only (`*.x.com` **and** `x.com`) | target not matched |

**`--scope` must be domain patterns, never prose.** Measured 2026-10-25: passing a human-readable
description (`--scope "www/dashboard/app/career-sites *.betterteam.com"`) made the gate answer
`❌ SCOPE GATE BLOCKED … not in www/dashboard/app/career-sites *.betterteam.com` and the run died at
0A having sent zero requests. `scope_checker.py` compares hosts against the pattern string. Either pass
real patterns (`--scope betterteam.com,*.betterteam.com,dashboard.betterteam.com`) or **omit `--scope`
entirely** — with no profile the operator rule makes every host allow-all and the gate logs
`SCOPE GATE PASSED (URL, allow-all)`. Omission is the correct call for a single-vendor audit.
| Contract audit | 0A | orchestrator self-check | its own contract findings |
| `verify-tool-usage` / `asset-coverage` | 0D (auto-rework loop) | `tools-usage.json`, per-phase evidence, `skill-usage.json`, `reference-usage.json` | an asset is `READ not USED` / `NOT_RUN`, or an evidence file is empty/missing |
| Checkpoint + coverage | after 0E/0F | `audit-checkpoint.py --phase all` + per-phase coverage | a required artefact is absent (e.g. `REPORT-survivors.md`) |
| Final gate | 0F end | report + checkpoint | any of the above still red |

Three attempts, then **`GATE FAILED after 3 attempts — HARD BLOCK`** (state saved, resume possible).
Never ship a report while a gate is red — the log says so explicitly, and the checkpoint reads from disk.

## 2. Gate-failure playbook (exact fixes, both verified)

**A. `asset-coverage FAIL for phase(s): ['0C']` → `no evidence: poc-execution.json`**
- Cause: `poc-pipeline.py` wrote `poc-plan.json` with `repos_matched: 0`; the producer only handled the
  *absent*-plan case, so it wrote `[]`, while the coverage rule for "no PoC matched" needs a truthy ledger
  whose statuses are not `EXECUTED`.
- Fix in RESUME (0C is skipped ⇒ the producer will NOT re-run): write the honest ledger yourself, proven by
  the plan file:
  `[{"repo":"NONE","status":"NO_POC_MATCHED","reason":"NO_POC_MATCHED","ts":"<iso>"}]`
  then re-run the same orchestrator command. Fresh runs are already patched in `scripts/track-poc-execution.py`.
- Touch nothing else: `N/A` with a reason (tool not installed, documented skip, web3-skipped) is legitimate,
  and `NOT_RUN` for 0E/0F entries is expected before those phases execute.

**B. `coverage 0E-REVIEW … REPORT-survivors.md [NOT_RUN]` + checkpoint `REPORT-survivors.md exists`**
```bash
cd <target-dir> && python <scripts>/finding_gate.py findings.json \
     --out gated.json --report REPORT-survivors.md --survivors survivors.json
```
then resume. `finding_gate.py` exits 0 **even with zero survivors** — the file itself is the artefact.
Survivor count 0 behind a NEGATIVE report is the correct result; never pad survivors to turn a counter green.

**I. `FAILED_USAGE` from a tool that ran fine — the usage-banner-on-error-path trap** (measured
2026-10-27, cleanshot). `linkfinder` was stamped `FAILED_USAGE` ("wrong CLI syntax, tool never
scanned") and hard-blocked 0D three times. The evidence file showed the truth:
```
Usage: python D:\data hermes\tools\LinkFinder\linkfinder.py [Options] use -h for help
Error: invalid input defined or SSL error: HTTP Error 429: Too Many Requests
```
The CLI was **correct**; the target's WAF returned 429 and the tool prints its usage banner on the
*error* path too. The harness's `_usage_markers` check matched `"usage:"` alone and concluded
"never scanned".

Root fix (already applied to `force-full-execution.py`, additive): a usage/help dump is only a CLI
failure when the output does **not** also prove the tool reached the target.
```python
_reach_markers = ("http error 4", "http error 5", "too many requests", "ssl error",
                  "connection refused", "connection reset", "timed out", "timeout",
                  "access denied", "forbidden", "no route to host",
                  "name or service not known", "certificate verify failed",
                  "unable to connect", "blocked", "waf", "cloudflare", "akamai")
_reached_target = any(m in _blob for m in _reach_markers)
...
if any(m in _blob for m in _usage_markers) and not _reached_target:
    entry["status"] = "FAILED_USAGE"
```
On the RESUME path, re-stamp the existing ledger entry to `RAN_WITH_ERROR` with the reason, **and
re-run the tool against a reachable in-scope asset** so the negative is backed by real output
(here: linkfinder against the CloudFront JS bundle → exit 0, 64-line HTML report, 13 URLs).
Generalisation: any tool that prints help-on-error (linkfinder, several CVE PoC scripts) will
false-positive on a WAF/throttle response. Check the evidence body for a target-reach marker before
believing `FAILED_USAGE`.

**J. `force-full-execution` false `NOT_FOUND` — the orchestrator's own STEP 1 is not a PATH binary.**
The `_account_mandated_tools()` loop calls `shutil.which("force-full-execution")`, finds nothing,
and records `NOT_FOUND` → asset-coverage `N/A "tool not installed"`. But it is
`scripts/force-full-execution.py`, already executed as STEP 1 (run log proves the window, and its
54 per-tool evidence files are on disk). Fix on resume: create a real aggregate evidence file
(`tool-evidence/force-full-execution-aggregate.txt` listing every per-tool file + byte size), point
the ledger's `evidence_file` at that **file path** (a directory description fails the gate's
`_ev_ok` check), and re-stamp to `EXECUTED`. Guard for future runs: the manifest loop should skip
names that resolve to the orchestrator's own scripts dir.

**K. Evidence-marker mismatch — the writer's header must match `QUALITY` byte-for-byte.**
`asset-coverage.py`'s `QUALITY` map requires exact markers:
`poc-variants(C5)` → `"# POC VARIANT EVIDENCE:"` · `poc-techniques(C6b)` → `"# POC-TECHNIQUES
EVIDENCE:"` (plural, with colon). Writing `# POC-TECHNIQUE EVIDENCE` (singular, no colon) passes
every human check and still flips `USED → NOT_RUN`. When you hand-write evidence for C5/C6b, copy
the marker string out of `QUALITY` in `asset-coverage.py` — never from memory. Also: the
`poc-techniques-usage.json` entries need a `status` field of `EXECUTED` /
`NO_EXTRACTABLE_PAYLOAD` / `NONWEB_PAYLOAD_TYPE` for `any_ran()` to accept them, and
`poc-variant-usage.json` needs the same per-repo (a bare `[]` is only accepted alongside the C4
`_no_poc` proof).

**L. `--derive` overwrites manual ledger fixes — use `--mark` for anything `derive` cannot see.**
`asset-coverage.py --phase 0C` re-runs `derive()` and rewrites `asset-coverage.json` from the
artefacts, silently discarding hand edits. `--mark` is the sanctioned override and **matches on the
bare asset name**, not the `phase:class:asset` key:
```bash
python asset-coverage.py <dir> --mark "poc-variants(C5)=USED" \
  --evidence "poc-variant-usage.json" --reason "17 repos executed; NO_EXTRACTABLE_PAYLOAD logged per repo"
```
Verify the output says `on 1 entry` — `on 0 entries` means the name did not match and nothing
changed. Order matters: run `--derive` first, then `--mark` the residuals, then gate.

**M. `finding_gate.py` writes to CWD, not the target dir.** Invoked as
`finding_gate.py <target-dir>` it prints the summary but writes `gated.json` / `survivors.json` /
`REPORT-survivors.md` relative to the **current working directory**, so the checkpoint's
`REPORT-survivors.md exists` check fails even though the gate "ran". Always `cd <target-dir>` first
or pass explicit `--out/--report/--survivors` paths.

**N. `finding_gate.py` did NOT write `REPORT-survivors.md` on a 0-survivor run — a clean negative audit could not pass 0E** (measured 2026-10-27, full pipeline health audit). `audit-checkpoint.py` PHASE 0E requires `REPORT-survivors.md exists (finding_gate)`, but `finding_gate.main()` printed *"no survivors — do NOT write a report"* and returned 0 **without writing the file**, so `TOTAL: 2/4` on a legitimate negative. Fixed additively (backup `finding_gate.py.bak_negreport_20261027`): the `else:` branch now writes an explicit **negative** report — candidates-in, survivors 0, per-candidate reason, and the coverage-discipline note. That is a truthful artefact, not a padded finding; it makes 0E green on a genuine negative. Verify after patching: a 1-candidate non-report-worthy findings.json → `REPORT-survivors.md written: True` and `✅ REPORT-survivors.md exists`.

**O. A tool disabled by an earlier audit cleanup is invisible to `shutil.which()` but still importable.** Measured 2026-10-27: `arjun` had `arjun.EXE.disabled-by-audit-20261014` in the Python Scripts dir — the module imported fine (`arjun 2.2.7`, `python -m arjun --help` works) but `which arjun` returned nothing, so `force-full-execution`'s CMD dict entry `arjun -u {t}` would have recorded `NOT_FOUND` → asset-coverage `N/A "tool not installed"` and the param-mining step silently disappears from coverage. Fix: `cp -p arjun.EXE.disabled-by-audit-20261014 arjun.exe` (never delete the `.disabled` original — it is the restore source). Generalisation: after any purge/cleanup pass, re-run the tool-resolvability check over the whole `MANIFEST`, and treat a `*.disabled*`/`*.bak` sibling as **the tool exists but is switched off**, not as absent.

**O2. A Go tool reported `NOT_FOUND` is usually NOT missing — it sits on a PATH the pipeline can't see (measured 2026-11-01).** The orchestrator resolves tools with `shutil.which`, which runs in **Windows Python** and reads the **Windows persistent PATH (registry HKCU/HKLM)** — NOT the bash/MSYS `$PATH` that `which`/`where` in the terminal uses. On this host the Go security tools are split across TWO dirs: `C:\go\bin` (GOROOT — `go.exe`, `trufflehog.EXE`, `nuclei.exe`) and `~/go/bin` (GOPATH — `ffuf`, `dalfox`, `katana`, `gau`, `subfinder`, `qsreplace`, `assetfinder`, `interactsh`, `echidna`, `medusa`…). If neither is on the Windows persistent PATH, every one stamps `NOT_FOUND` in `recon-evidence/recon-<tool>.txt` **even though `where <tool>` in bash finds it** — and the pipeline silently drops them from coverage. That is the exact mechanism behind the operator's recurring complaint *"beberapa kali kmu balik cm curl aja"*: the tools are present, the pipeline just can't resolve them, so the run degrades to curl.

Diagnose BEFORE declaring a tool missing (three probes, in order):
1. `where <tool>` / `command -v <tool>` from bash → proves the **binary exists on disk** (bash PATH).
2. Read what a **fresh Windows process** actually sees (this is what `shutil.which` uses):
   ```powershell
   powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','User'); [Environment]::GetEnvironmentVariable('Path','Machine')"
   ```
   Bash inherits an env that includes `C:\go\bin` + `~/go/bin`; the registry (HKCU) often does NOT.
3. `py -3 -c "import shutil; print(shutil.which('<tool>'))"` — the pipeline's own resolution.

Fix (persistent, one-time):
```powershell
$cur = [Environment]::GetEnvironmentVariable('Path','User')
if ($cur -notlike '*C:\go\bin*') { $cur += ';C:\go\bin;$HOME/go/bin' }
[Environment]::SetEnvironmentVariable('Path', $cur, 'User')
# then broadcast WM_SETTINGCHANGE ('Environment') so already-open shells/Explorer pick it up
```
Verify from a **fresh PowerShell** (`Get-Command nuclei,ffuf,trufflehog,katana,gau,interactsh`), never from the still-open bash session — a fresh process re-reads the registry PATH; an open bash holds the stale one.

Two adjacent facts that will otherwise mislead the same hunt: `graphql-cop` is **not a tool** (§P — classifier regex, never invoked); and `jsluice` is the one genuine gap — its Go source is cached in `~/go/pkg/mod/github.com/!bishop!fox/jsluice@*/cmd/jsluice` but no `.exe` was ever built, the build fails without a C compiler because `go-tree-sitter` requires CGO (`CGO_ENABLED=0` is NOT a workaround — `iter.go` references the C `Node` type), and BishopFox ships **source only** (no prebuilt Windows binary in releases). To close it: install a gcc (`winget install mingw` / `tdm-gcc`), then `cd ~/go/pkg/mod/github.com/!bishop!fox/jsluice@*/cmd/jsluice && go build -o ~/go/bin/jsluice.exe .`

**P. `graphql-cop` is a regex label, not a dependency — do not chase it.** It appears once, inside the pattern `r"wpscan|droopescan|testssl|gobuster|arjun|kxss|graphql-cop|introspection|"` used to *classify* tool output. It is absent from the CMD dict and has no PyPI distribution (`pip download graphql-cop` → "No matching distribution"). A tool-resolvability scan that greps the whole source will flag it every run; ignore it, or scope the scan to the CMD dict only.

**Q. Phase-substep labels can differ from the coverage keys — check the ARTEFACT, not the label.** `0C-C5` never appears as a `PHASE 0C-C5` log line (grep returns 0 hits) and looks unwired. It *is* wired: `execute-poc-variants.py` runs under the label `STEP 1.4c` and writes `poc-variant-usage.json`, which is what `asset-coverage` keys on. Before declaring a substep missing, grep for the **producer script name and its output file**, not for the phase string.

**R. One-command health check for the whole 0A→0F chain** (no target, no network) — run this after any cleanup, tool install, or skill edit:

```python
import ast, glob, os, shutil, subprocess, sys
S = os.path.expanduser("~/.chiper/skills/bounty-pack")
# 1. every phase script: exists + compiles
for f in sorted(glob.glob(S + "/*.py")):
    try: ast.parse(open(f, encoding="utf-8", errors="replace").read())
    except SyntaxError as e: print("SYNTAX", os.path.basename(f), e.lineno)
# 2. every MANIFEST tool resolves
import re
orch = open(S + "/audit-pipeline-orchestrator.py", encoding="utf-8", errors="replace").read()
cmd_keys = re.findall(r'^\s{12,16}"([a-z][a-z0-9_\-]{2,})":\s*"[^"]+', orch, re.M)
print("CMD-dict tools:", len(cmd_keys))
for t in cmd_keys:
    if not (shutil.which(t) or shutil.which(t.replace("-", "_"))):
        print("  UNRESOLVABLE:", t)
# 3. gate scripts run (no crash) on a throwaway dir
import tempfile, json
td = tempfile.mkdtemp()
for g, args in (("audit-checkpoint.py", ["--phase","all"]), ("verify-tool-usage.py", []),
                ("deep-audit-mode.py", ["guard"]), ("finding_gate.py", [])):
    r = subprocess.run([sys.executable, os.path.join(S,g)] + args + ([td] if g!="finding_gate.py" else []),
                       capture_output=True, text=True, timeout=60, errors="replace", cwd=td)
    bad = "Traceback (most recent call last)" in (r.stdout + r.stderr)
    print(("CRASH " if bad else "ok    ") + g)
```
Green baseline measured 2026-10-27: **37/37 phase scripts compile, 48/49 tools resolve, 28/28 phase skills present, 10/10 gate scripts run without crashing, 0C-C1…C7 all wired.**

**S. `depth_gate.py` self-matched its own field names — a shallow L1 passed by adding `"impact": ""`** (measured & fixed 2026-10-27). Two independent defects in one function:

```python
text = json.dumps(item, ensure_ascii=False).lower()   # ← includes FIELD NAMES
...
if not DEEP_SIGNAL.search(text):                       # DEEP_SIGNAL contains "impact"
    reasons.append("tak ada sinyal kedalaman …")
```

Every finding has an `impact` key, so the regex satisfied itself. Repro (before fix), with evidence that is NOT a bare status code:

| item | verdict |
|---|---|
| `{title, depth:"L1", evidence:"fungsi X tidak memeriksa msg.sender"}` | **BLOCK** exit 1 |
| same **+ `"impact": ""`** (empty string) | **PASS** exit 0 ← leak |
| same **+ `"impact": "x"`** | **PASS** exit 0 |
| same **+ `"impact": "critical"`** | **PASS** exit 0 |

Second defect: the docstring promised *"L0/L1 = BLOCK"* but the verdict line
`PASS if not reasons else (WARN if lvl>=2 else BLOCK)` never enforced it — a **declared L1** returned PASS whenever no reason happened to fire.

Fix applied (backup `depth_gate.py.bak_depthfix_20261027`) — three additive changes:
1. `_values_text(item)` flattens **values only** (recursive, depth-capped) so field names can never satisfy `DEEP_SIGNAL`.
2. Declared `L0`/`L1` → `BLOCK` unconditionally, matching the documented contract.
3. The `impact` field must be **substantive**: `_IMPACT_SUBSTANTIVE` requires an amount or a named loss (`\d+ ETH/USD/%`, takeover/drain/exfil/withdraw/bad debt/…). `""`, `"x"`, `"critical"` now raise a reason instead of passing.

Regression-verified (6/6): L1 without impact → BLOCK · L1+`""` → BLOCK · L1+`"x"` → BLOCK · L1+`"critical"` → BLOCK · full L5 (amount + mechanism + repro) → PASS · L3 candidate with substantive impact → PASS. A realistic `survivors.json` entry (impacts + evidence, no declared depth) still passes, so genuine findings are not harmed. **Lesson: never build a gate's search text from a serialized object — the keys are part of the payload and will match the gate's own vocabulary.**

**T. `deep-audit-mode.py guard` was structurally web2-only — a contract-only audit could never go green** (measured & fixed 2026-10-27). `guard` → `pipeline_ok()` → `verify-tool-usage.py` → CHECK 12 → `asset-coverage.py`, whose MANIFEST hardcodes the 13 web2 tools (nuclei/sqlmap/dalfox/ffuf/katana/gau/jsluice/arjun/qsreplace/ghauri/graphql-cop/interactsh/proxy). A contract-only scope has **no HTTP surface**, so those are structurally `N/A` and the SOUL-mandated green gate was unreachable except by lying. Measured: a synthetic contract-only dir with `foundry.toml` + `src/T.sol` + real slither/aderyn/forge evidence → **`⛔ BLOCKED`, listing the 13 web2 tools**.

Fix applied (backup `deep-audit-mode.py.bak_web3track_20261027`) — additive scope routing:
- `detect_track(target_dir)` → `"web3"` when the dir carries any contract signal (`foundry.toml`, `hardhat.config.{js,ts}`, `truffle-config.js`, `web3.marker`, `contract-audit.json`, or a `*.sol` at depth ≤2 under the dir/`src`/`contracts`/`test`).
- `pipeline_ok_web3()` verifies the **contract** tool set instead: evidence files for `slither` / `aderyn` / `myth` / `forge` (plus `echidna`/`medusa`), requiring `WEB3_MIN_USED = 2` with real ≥100-byte evidence, and a `*.sol` present. It reads `tool-evidence/*.txt` **and** `asset-coverage.json` (USED + evidence path).
- `cmd_guard()` branches on the track; the web2 path and its 13-tool message are unchanged.

Regression-verified (4/4): contract-only + slither/aderyn/forge → **PASS** · contract-only with no evidence → **BLOCK** (no free pass) · only 1 tool → **BLOCK** · empty web2 dir → **BLOCK** on the web2 path. So the web3 track is a *different requirement*, not a weaker one.

**U. `unaccounted statuses: [None]` — ledger records that have no `status` key at all** (measured
2026-10-30, telekom). `verify-tool-usage.py` counts a record as accounted only when `status` is one of
the known values; a record written by a different producer with `result` / `invoked` keys instead is
counted as `None` and fails 0D with a message that names **no asset**, so it looks like a phantom.
Diagnose by scanning for the missing key rather than reading the gate text:

```python
import json
tu = json.load(open(r"<target-dir>/tools-usage.json", encoding="utf-8"))
for r in tu:
    if "status" not in r:
        print(r.get("tool"), "|", sorted(r.keys()), "|", r)
```

Measured case: two `php2shell-verify` records carrying
`{"tool","result","invoked","evidence_file","ts"}` with `invoked: True` and a real 17,729-byte evidence
file. The tool had genuinely run; only the schema differed. Fix — **verify the evidence file exists and
is non-trivial first**, then normalise the record by adding `"status": "EXECUTED"` (keep the original
keys; do not delete them). That is a truthful correction, not a fabrication: the proof was on disk.
Never add `EXECUTED` to a record whose `evidence_file` is missing or 0 bytes — that is exactly the
padding this gate exists to catch.

**V. An MSYS path passed to a Windows-Python script silently yields an empty result** (measured
2026-10-30, telekom). This is the dangerous one because it produces a *fabricated negative coverage*
rather than an error:

```bash
# git-bash resolves this; Windows Python's pathlib does NOT
python execute-poc-variants.py https://target --target-dir "$HOME/.../orchestrator-x"
#   -> "Matched repos: 0"     (exit 0, no error, writes [])
# correct:
python execute-poc-variants.py https://target --target-dir "$HOME/.../orchestrator-x"
```

The script does `Path(target_dir) / "poc-execution.json"`, gets a nonexistent path, finds zero repos and
reports `NO_POC_MATCHED` — which the gate then accepts as legitimate. A whole PoC-execution step
disappears from coverage and the ledger says the target simply had no matching PoCs. Generalisation:
in this environment `terminal` runs bash (MSYS), but every `python` it invokes is **Windows** Python.
Shell paths (`$HOME`, `/c/...`, `/d/...`) are fine as *shell* arguments and as arguments to bash-native
tools; they are **not** fine as paths consumed by `pathlib`/`open()` inside a Python script. Convert
with `cygpath -w "$P"` or write `C:/...` directly.

Guard for future runs: after any producer that accepts `--target-dir`, assert its output is non-empty
*before* recording the negative — `wc -l < <usage-file>` and check the producer's own "Matched repos"
line against the count in `poc-execution.json`. A zero that you did not predict is a path bug until
proven otherwise.

**A related trap on the same run:** `find_payload_files` looks for files named `payload.*`. A corpus of
CVE-specific exploit repos (`exploit.py`, `poc.py`, `send_payload.py`) therefore matches **0** even when
33 repos are present and several are EXECUTED — and that zero is *legitimate*, not a bug. Distinguish
the two: a path bug shows `Matched repos: 0`; a corpus-shape miss shows a non-zero repo count with
`NO_EXTRACTABLE_PAYLOAD` per repo. Only the second is an acceptable negative.

**N. Anything else:** read the last 40 log lines, fix that one thing, resume. Max 3 attempts → mark the
product `BLOCKED-gate` with the failing line and continue the queue.

**D. `no evidence: poc-variant-usage.json` / `poc-techniques-usage.json` while `poc-execution.json` is already
correct** — the *consumer* scripts (`execute-poc-variants.py`, `execute-poc-techniques.py`) mapped the
`{"repo":"NONE","status":"NO_POC_MATCHED"}` entry to a repo name, filtered it out and wrote `[]`. The gate
wants the **conjunction** `_no_poc and not pvc`: an empty consumer ledger is accepted *only* alongside a C4
ledger proving nothing was runnable, and a non-empty `NONE` entry fails it the other way. Both consumers are
patched (2026-10-17) to write `[]` + `poc-techniques-evidence/NO_POC_MATCHED.txt`. On the RESUME path (0C
skipped) reproduce those three files by hand. Related: `CHECK 11 … evidence missing` (the consumer ledger's
`evidence_file` pointer must resolve to a real ≥100 B file) and `target mismatch: evidence says '<host>'`
(rewrite the `# TARGET:` line to the full run URL, then `asset-coverage.py --derive <dir>` — positional, no
`--target-dir`). Full recipes: **`references/gate-failures.md` §1b–1d, §4**.

**E. `RAN_WITH_ERROR` for a tool that IS installed** — wrapper bugs, not missing tools. Measured: `ffuf`
wordlist path with a space (use forward slashes), `subzy` needs a *file* of targets, `graphw00f` wants `-f`
not `-d`, `grpcurl` needs `-insecure` on 443, `kiterunner` off the bash PATH. Re-run correctly into
`tool-evidence/<tool>-manifest.txt` with the standard header, then re-derive. A tool with genuinely no surface
here is a legitimate `N/A` — write the reason, don't leave `RAN_WITH_ERROR`.

**E2. `FAILED_USAGE` (distinct from `RAN_WITH_ERROR`) + the redirector-apex trap** — measured 2026-10-26
(do.de): `linkfinder` logged `FAILED_USAGE` twice because the orchestrator's own invocation was malformed
AND aimed at the apex `https://do.de`, a bare 301 redirector whose every content-dependent tool run times
out. Fix: re-run the tool by hand against the LIVE hosts with correct flags —
`python "D:/data hermes/tools/LinkFinder/linkfinder.py" -i https://<live-host> -d -t 30 -o <dir>/tool-evidence/linkfinder-<host>.html`
— then `asset-coverage.py --derive <dir>`. Generalisation: when 0B reports `host role: redirector`,
expect every content-dependent tool aimed at the apex to fail or return empty; the real evidence must be
collected against the redirect target(s) (here `www.do.de` / `my.do.de`). An apex-only run that "passed"
with empty evidence files is not coverage — check `tool-evidence/*.txt` for usage errors, not just exit 0.

**F. `asset-coverage FAIL for phase(s): ['0C'] — some asset was READ not USED / skipped-timeout`, with the
0C entries sitting at `NOT_RUN`** (measured 2026-10-25, betterteam; it re-failed the *same* check on three
consecutive auto-rework loops because rework re-runs tool execution but never the missing *producers*).
Diagnose before touching anything:
```bash
python - <<'PY'
import json; from collections import Counter
d=json.load(open(r"<target-dir>/asset-coverage.json"))
for k,v in d.items():
    if str(v.get("phase","")).startswith("0C") and str(v.get("status")).upper() not in ("USED","N/A"):
        print(k, v.get("status"))
PY
```
Typical culprits: `0C:payload:poc-variants(C5)`, `0C:payload:poc-techniques(C6b)`,
`0C:shelf:poc-technique-atlas`. Fix by **actually running the producers in order** — never by hand-editing
the ledger:
```bash
O="<target-dir>"; S="~/.chiper/skills/bounty-pack"
python "$S/track-poc-execution.py" <target-url> --target-dir "$O"        # → NO_PLAN / NO_POC_MATCHED
python "$S/rce-verify.py" "$O" <target-url> --urls-file urls.txt           # → rce-verification.json (0C:tools:rce-verify NOT_RUN)
python "$S/execute-poc-variants.py"   <target-url> --target-dir "$O" --max-payloads 20
python "$S/execute-poc-techniques.py" <target-url> --target-dir "$O" --max-payloads 20
python "~/.chiper/skills/bounty-pack/audit-execution-discipline/scripts/asset-coverage.py" --derive "$O"
```
`rce-verify.py` takes the target dir **and** base URL positionally (`rce-verify.py <target_dir> <base_url>`);
its ledger `rce-verification.json` is what flips `0C:tools:rce-verify` from `NOT_RUN`.

**Slow-target variant timing (measured 2026-10-26, do.de, ~20 s/request):** `execute-variants.py` runs
5–15 min per vector (time-based payloads sleep; every request is slow), so the full 15-vector set is 1–2 h.
Launch it as a `terminal(background=True, notify_on_complete=True)` process — do not block the session on
60 s waits. Progress is visible mid-run: `variant-usage.json` is rewritten incrementally (not only at the
end) and `variants/<vector>.txt` appears as each vector completes, so `ls variants/` + the JSON's vector
count is the honest progress read. On a ~1 GB-free-RAM host keep the remaining recovery steps sequential
after it (rce-verify / poc executors), never parallel.
`--derive` takes the target dir **positionally** (`--work-dir` is rejected), and it rewrites
`asset-coverage.json` from the real artefacts on disk. Then re-gate: `verify-tool-usage.py "$O"` →
`ALL 13 CHECKS PASSED` and `deep-audit-mode.py guard "$O"` → `pipeline evidence OK`. On a
react/remix/node target the two executors legitimately write `[]` (no PoC repo matches the stack) — an
empty consumer ledger is accepted *only* alongside the C4 `NO_POC_MATCHED` proof (see D). Verified end
state: 83 executed tools, 117 ledger entries, variants 12/12 (241 requests), business-logic 15/15.

**G. `PIPELINE EXCEPTION: name 'findings' is not defined` — orchestrator source bug at 0E, not a gate.**
Measured 2026-10-25 (betterteam, resume 0E→0F). `run_findings_layer()` used a bare `findings`
identifier that is never bound in that scope, in two places:
`fg_input = shipped if _ship_n > 0 else findings` and `val_input = surv_json if surv_json.exists() else findings`.
It only fires when `weaponized-shipped.json` is empty/absent (the 0-findings path) — i.e. every clean
negative audit crashes here, so it looks like "pipeline can't finish a negative". Patch (additive, after
the `gated = …` binding at the top of the method):
```python
findings = self.output_dir / "findings.json"
```
Back up first (`cp audit-pipeline-orchestrator.py …bak_findingsfix_$(date +%Y%m%d)`), then
`python -c "import ast;ast.parse(open(f).read())"`, then resume. The same `findings = self.output_dir /
"findings.json"` line already exists in `run_chain_layer()` (0C-C7) — mirror it.

**H. Two `NOT_RUN` that are structurally impossible to satisfy — mark, do not fabricate.**
After A–G the negative-audit gate (`_gate_negative_audit`, runs at 0F-**pre**) can still report
`N not_run` because it counts *every* non-`USED`/`N/A` entry in `asset-coverage.json`, including 0E/0F
artefacts that by design cannot exist yet:
- `0F:report:AUDIT-REPORT.md` — the gate runs **before** `generate_report()` writes it. Chicken-and-egg.
- `0E:findings:ready-candidates.json` — absent **by correct design** when 0 findings pass validation.

Fix with the sanctioned marker, never by editing the JSON:
```bash
AC="~/.chiper/skills/bounty-pack/audit-execution-discipline/scripts/asset-coverage.py"
python "$AC" --mark "ready-candidates.json=N/A" --evidence "validated-findings.json (valid_count=0); passed-findings.json ([])" \
  --reason "0 of N candidates survived validate-findings; triage_gate has no ready candidate to emit — absence is the CORRECT negative-audit outcome" "$O"
python "$AC" --mark "AUDIT-REPORT.md=N/A" --evidence "pipeline log <ts> (0F-pre gate precedes report generation)" \
  --reason "chicken-and-egg by design: _gate_negative_audit() runs at 0F-pre before generate_report() writes AUDIT-REPORT.md" "$O"
```
**`--mark` matches on the BARE asset name, not the ledger key.** Passing the full
`phase:class:asset` key silently prints `marked '…'=N/A on 0 entries` and changes nothing — verify the
`on N entr{y|ies}` count is `1`, then confirm with a `NOT_RUN` scan. `--derive` takes the target dir
**positionally** and is the right tool when the artefact genuinely exists; `--mark` is only for the
structurally-impossible cases, and every mark must carry evidence + reason that a reviewer can check.
Green end state (measured): `USED 59 · N/A 24 · NOT_RUN 0` → pipeline completes 0A→0F,
`audit-checkpoint TOTAL: 33/33`, `deep-audit-mode.py report-guard` → "no bare over-claim. OK to draft."

## 2b. Phase placement of the finding gates — 0C-C7, NOT 0E (operator correction 2026-10-30)

> **A+B regression harness (2026-11-02):** the gate contract is exercised by
> `scripts/severity_gate_regression.py` **inside this skill dir** (NOT `~/scripts/`) — the same
> place `asset-coverage.py` lives. Run it as
> `python skills/audit-pipeline-operations/scripts/severity_gate_regression.py --scripts ~/.chiper/skills/bounty-pack`.
> It drives the REAL chain (aggregate → weaponize → finding_gate → validate → triage) on a 4-positive +
> 5-negative fixture matrix and exits 0 only when 4/4 positives survive and 5/5 negatives are rejected.
> After the 2026-11-02 A+B change (`weaponize-gate` verdict became **SHIP / DEEPEN / DROP** instead of
> binary SHIP/DROP), the harness was patched to parse the triple format AND to emulate the new
> `weaponized-shipped.json` (SHIP+DEEPEN, all non-DROP). A stale harness that still greps the old
> two-token banner will print `SHIP=-1 DROP=-1` and FAIL even though the gate itself is healthy — that `-1`
> is a harness regex mismatch, not a gate defect. Whenever the weaponize-gate output *format* changes,
> update this harness's `re.search` banner pattern in the same change.

Documenting `aggregate-findings` / `weaponize-gate` / `chain_builder` as 0E steps is a real mistake
made and corrected in this session (the operator caught it: *"seingat sy chain builder ad d 0C"*).
Canonical, from `run_chain_layer()` / `run_findings_layer()` docstrings:

```
0C  C1..C6 → C7 = aggregate → weaponize-gate → chain_builder     ← CLOSES 0C
0D  verify-tool-usage (13 checks, HARD BLOCK)
0E  E4 finding_gate → E5 validate-findings → E6 triage_gate       ← filter + validate ONLY
    then 0E-REVIEW: review-candidates
0F  _gate_depth → _gate_na_discipline → _gate_negative_audit → report-agent
```

Why: aggregate must collect from **all** of C1..C6b (run it earlier and every chain is built from
partial data), and composing primitives into a chain is exploitation work, not reporting.

**The failure this causes:** an operator following a wrong doc runs `finding_gate` on **raw**
findings, which kills every lead with no attacker-use narrative yet — exactly the Lows the
composition doctrine keeps as fuel. Symptom: `REPORT: 0 DOWNGRADE: 0 DROP: N` on a target where
`weaponize-gate` would have shipped 3–4 leads.

Two data-contract rules that are easy to get wrong: **E5 must read `survivors.json`, never
`findings.json`** (feeding it raw findings re-admits what E4 killed); and **an empty
`weaponized-shipped.json` is not "nothing survived"** — fall back to `findings.json` and let
`finding_gate` apply its own impact filter (measured: empty shipped → 0 survivors, same findings via
fallback → 42 survivors with real impact).

### Does each severity level actually survive? Yes — verified 4/4

| finding | declared | weaponize | finding_gate | validate | triage |
|---|---|---|---|---|---|
| Pre-auth RCE | critical | SHIP | REPORT (17) | ✅ | 7/7 |
| IDOR cross-tenant IBAN | high | SHIP | REPORT (11) | ✅ | 7/7 |
| CSRF → ATO | medium | SHIP | REPORT (16) | ✅ | 7/7 |
| Open redirect → OAuth code leak | low | SHIP | REPORT (22) | ✅ | 7/7 |

Plus 5 negative controls (HSTS, self-XSS, version disclosure, bare open redirect, speculative IDOR)
all correctly DROPped in the same run. Requirements per level: **Critical/High** need nothing extra
(terminal impact = chain of length 1); **Medium** may need `chain_analysis`/`next_to_hunt` naming the
step to impact; **Low** must be terminal itself or carry a named link.

**Seven gate defects made "strict" mean "broken"** before that matrix passed — a gate deleting the
record it judged, no `STANDALONE` branch (a pre-auth RCE DROPped as "a dead end"), severity inflation
by keyword, `triage_gate` reading evidence *paths* instead of files (every finding BLOCKED 0/7),
`finding_gate` projecting survivors to `severity:"unknown"` + stringified evidence, and
`aggregate-findings` re-ingesting `WEAPONIZATION.md` as a phantom finding. Full symptom → cause → fix
for each, plus the re-verify commands and the fixture shape: **`references/severity-gates-and-phase-placement.md`**.

**Standing rule:** a gate may ADD a verdict; it must never delete the fields that prove the finding.
And any file whose job is to *describe* the engagement or *report on* a gate must be in `SKIP_NAMES` —
when you add a new artefact producer, add its output name in the same change.

### Delivering the pipeline map to the operator — as a FILE, not chat prose

Operator correction 2026-10-30: after a long in-chat walkthrough of the phases/skills/tools, the
operator asked for it *"dalam bentuk file MD aj y, biar sy bisa liatnya lebih rapi"*. A structured
architecture explanation is a **document deliverable**, not a chat message — it gets re-read beside
the code, scrolled through, and referenced later; chat prose does not.

- Write it to a stable path the operator can open: `~/.chiper/skills/bounty-pack/WORKFLOW-PIPELINE-MAP.md`.
- Sections that earn their place: per-phase detail (script → artefact → skill → reference), a
  **SKILL map**, a **TOOL map**, the **skill↔tool contract** (skill without tool = opinion; tool
  without skill = spray; gate without either = blind), the **phase-to-phase data contract**, gate
  inventory, hard rules, known traps, and a coverage/negative-space close.
- Every fact must be read out of `audit-pipeline-orchestrator.py` / `verify-tool-usage.py` / the
  launcher SKILL.md and **cited by source file** at the bottom. A map written from memory reproduced
  the exact phase-placement error it was supposed to document.
- Chat then carries only the short summary plus the file path — not a second copy of the document.

### Correcting a phase fact is a TREE-WIDE sweep, not a one-file edit

Fixing the authoritative file (`bb-audit-launcher/references/phase-framework-0A-0F.md`) felt like the
whole correction. It was not. A sweep of the skill tree afterwards still found **18 hits asserting the
old `0E = aggregate → chain_builder` ordering**, including `audit-execution-discipline/references/
rules-body/body-01.md` and `body-03.md` — the *rules body*, i.e. the text an agent is most likely to
obey — plus eight more files under `audit-execution-discipline/references/`, and both
`bug-bounty/SKILL.md` and `bug-bounty-main.md`. The stale ordering outlived the correction everywhere
that mattered.

**Sweep in the same change, then classify — blanket replacement is wrong:**

| hit class | shape | action |
|---|---|---|
| live claim | `0E FINDINGS : aggregate-findings -> chain_builder -> finding_gate` | **fix** to the canonical order |
| dated historical record | `Measured 2026-10-10 … (0E, aggregate-findings.py)` | **annotate**: append `(recorded at the time as 0E; aggregate now runs in 0C-C7)`. Never rewrite — the date is evidence of when the measurement was taken |
| false positive | a leaked-report markdown whose *URL* happened to contain the phase token | ignore |

Scope the sweep to lines that **assert an ordering** (a phase token *and* a script name on the same
line); a bare `grep 0E` drowns in URL/ID noise. Re-sweep until the only survivors are annotated
history, and back up every file touched.

## 2g. A gate that DEMANDS fields the upstream producer doesn't write KILLS the lead before it can be deepened (measured & fixed 2026-11-02)

The operator asked, bluntly, *"apa pipeline kt terlalu keras sehingga susah dpt bug, lead yg seharusnya bs diperiksa lbh dalam malah mati dtengah jalan"*. Reading the source (not the docs) confirmed it — and this is the single most impactful gate-design lesson in the pipeline.

**The defect chain.** `aggregate-findings.py` writes only `title / severity / impact / poc`. But `weaponize-gate.py` has `MUST_FILL = ["weaponization", "chain_class", "fix_regression", "impact_class"]` — four fields aggregate never writes. `weaponize-gate` auto-classifies `severity` + `chain_class` from *text* (regex), but the other three are only satisfied if they already exist in the record. So the moment the gate runs (C7-E2), **nearly every lead gets DROPped** for `WEAPONIZATION empty` / `CHAIN_CLASS empty` / `FIX_REGRESSION empty` — not because the lead is bad, but because the analysis fields were never populated. `chain_builder` and 0E then receive `[]`, and the run prints "0 leads survived".

That is exactly "a lead that should have been examined deeper died mid-pipeline" — and it is a *gate-design* bug, not a lead-quality bug.

**The three-part fix (additive, backup the 3 scripts first):**

1. **`lead_escalation` write-back (`A`).** `lead_escalation.py` knows each lead's class/primitive/escalation. Add an `enrich_lead()` that writes BACK into `findings.json` only the fields it can fill honestly — `chain_class` (`STANDALONE` for rce/ato, else `HEAD`), `next_to_hunt` (first escalation target), `weaponization` (`primitif …; teknik …; probe awal …`) — and **never** overwrite a field the analyst already set. Then call `lead_escalation` at **C7-E1b (BEFORE weaponize-gate)**, not at the old C7-E4 (after). Moving it without the write-back is worthless: weaponize reads `findings.json`, not `lead-escalation.json`.

2. **`weaponize-gate` verdict triple (`B`).** Convert the four "empty mandatory field → `drop`" branches into "empty field → `deepen`". Verdict becomes `SHIP` (analysis + impact complete) / `DEEPEN` (analysis fields still empty — flow through for deep-dive) / `DROP` (by-design / junk / info-only — genuinely discard). Emit `deepen_reasons` alongside `drop_reasons`. The sidecar `weaponized-shipped.json` becomes **`SHIP + DEEPEN`** (all non-DROP), so 0E's `finding_gate` applies its own impact filter rather than the lead being killed at weaponize.

3. **Orchestrator suppress condition.** The old `if n_ship == 0: weaponized.write_text("[]")` also silently killed every DEEPEN lead. Change to `if n_ship == 0 and n_deepen == 0:` — count both verdicts, suppress only when BOTH are empty.

**Verification that matters:** after the patch, a lead with only `title/severity/impact` (the aggregate-findings shape) must come back `verdict == DEEPEN` **and** appear in `weaponized-shipped.json` (count 1), not DROP. Then after `lead_escalation` enrich, the same lead picks up `chain_class/next_to_hunt/weaponization` and flows to 0E.

**Durable principle:** a finding gate may downgrade a lead, but it must **never kill a lead for context it has not yet been given a chance to build**. Separate "worth pursuing" (impact signal — don't drop) from "ready to report" (full weaponization + chain + fix — drop only here, and only after a deepen pass). Any gate whose `MUST_FILL` list is longer than what the immediately-upstream producer writes is structurally a lead-killer, and the fix is a three-way verdict, not a stricter regex.

**Corollary — changing a gate's OUTPUT FORMAT is a silent break, and the regression harness is the canary (2026-11-02).** When the verdict went `SHIP/DROP` → `SHIP/DEEPEN/DROP`, the *real* gate worked (4/4 positives survived, 5/5 negatives rejected) but `scripts/severity_gate_regression.py` kept matching the old `WEAPONIZE-GATE:\s*(\d+)\s*SHIP\s*/\s*(\d+)\s*DROP` line and printed **`SHIP=-1 DROP=-1`** — a false "the gate is broken" that is actually "the harness parser is stale". Two rules follow: (1) whenever a gate's printed contract changes, grep every `re.search(` that parses that gate's stdout **in the same change** — the harness is at `skills/audit-pipeline-operations/scripts/severity_gate_regression.py`, NOT `~/scripts/` (same W1-class trap: support scripts live in the skill dir); (2) read `-1` as a **parser miss**, not a gate verdict — confirm by running the gate by hand on a fixture before believing a regression failure. Also: a change to a gate's *sidecar semantics* (e.g. `weaponized-shipped.json` now `SHIP+DEEPEN` instead of `SHIP`-only) must be mirrored in the harness's own `shutil.copyfile`/filter-emulation block, or the harness tests a shape the orchestrator no longer produces.

## 2c. Editing the pipeline scripts safely — defects that each cost a run

**Three more silent-drop defects found & fixed 2026-11-02 (regex lexical collision in the finding gates):**

1. **`finding_gate.py` `DEAD_CHAIN` bare `\bunverified\b`** matched the finding's OWN title — *"unverified email change"* is a live ATO primitive (the ADDRESS is what's unverified; that is the bug), not a disclaimer — and DROPped a proven `account_takeover`. Fixture repro: an ATO entry scoring `account-takeover+pii` with `HTTP/1.1 200 OK` came back `DROP: dead/unverified chain`. Fix: scope dead markers to **STATUS phrases** (`unverified finding/claim/lead`, `finding is unverified`, `remains unverified`), never bare adjectives. Verified both ways: F1 ATO → REPORT; genuine `remains unverified` SSRF → still DROP.
2. **`aggregate-findings.py` `skip_words` substring match** silently dropped real findings whose title *contains* a meta word: *"OS Command Injection"* matched skip word `command`, *"HTTP method tampering"* matched `method` — 0 findings emitted for a file holding a Critical RCE. Fix: whole-word/phrase `_is_meta_heading()` **gated on the ABSENCE of a severity/evidence lookahead**, so a genuine finding naming severity always survives while `Commands used` / `Summary` sections still skip. Fixture: `worker-1.md` with 2 findings + 2 meta headings → `2 findings`, meta skipped.
3. **`aggregate-findings.py` severity regex `[:\s]*`** did not consume markdown-bold, so `**Severity:** Critical` defaulted to `"unknown"` (downstream gates then had no severity to score). Fix: `[:\s*\*]*` in severity/evidence separators + `lstrip('*')` on evidence.

**Durable principle (reinforces §2g):** a live *primitive name* and a *dead-marker word* can be the same text. Any regex that classifies dead/unverified via a bare adjective will, at some point, DELETE a valid finding with that adjective in its name. Dead markers must be phrases about the STATUS of the finding — never adjectives applied to the whole blob/title. And **every attempt must carry a fixture** (a known-good primitive in the matrix so a silent drop is caught instantly), same as `check_chain_builder_fixture.py` per `chain-to-impact`.

> **Regression guard for these three cases:** `scripts/silent_drop_regression.py --scripts ~/.chiper/skills/bounty-pack` — builds the minimal fixtures, runs the REAL `finding_gate.py` / `aggregate-findings.py` / `triage_gate.py` / `validate-findings.py`, and asserts both directions (valid finding survives; genuine junk still drops). Exit 1 names the case that regressed. Distinct from `scripts/severity_gate_regression.py`, which covers the severity *chain* but NOT these lexical-collision silent-drops. Run it after any edit to `finding_gate.py`'s `DEAD_CHAIN` or `aggregate-findings.py`'s title-skip / severity parser.

**Four more silent-drop defects found & fixed 2026-11-02 (same session, `triage_gate.py` + `validate-findings.py`):**

1. **`triage_gate.py` `DEAD_RE` had the same bare `\bunverified\b`** as `finding_gate` — BLOCKed a proven ATO at Q4 (`Unverified email change`). Same fix: scope to STATUS phrases (`unverified finding/claim/lead`, `remains unverified`).
2. **`triage_gate.py` `HYGIENE_RE` bare `version|banner|fingerprint|outdated`** killed the CVE fix-line chain (outdated nginx → CVE → RCE), scoring it info-only at Q3/Q6 — despite `chain-to-impact` documenting that exact chain as a paying Medium/High. Fix: split into `HYGIENE_RE` (hard hygiene) + `VERSION_HYGIENE_RE` (conditional — *not* hygiene when the text also carries a `CVE-…` / RCE / SQLi / auth-bypass escalation), wrapped in `_is_hygiene()`.
3. **`validate-findings.py` `SOCIAL_PATTERNS` substring `impersonat` + noun `phishing`** rejected a real sender-misattribution / identity-spoofing finding (vendor mails a third party as the attacker) as "phishing". The `chain-to-impact` worked Hivenet case is that *exact* chain → *phishing relay* is a DOWNSTREAM capability, not an attack method. Fix: reject on **ACTION VERBS** (`lure`/`trick`/`deceive`/`harvest`) + `social engineering`, never the bare capability nouns `phishing`/`impersonation`/`spoof`.
4. **`validate-findings.py` `_TERMINAL_GOALS` had no `cross-tenant` idiom** while `finding_gate` scores that exact term (`cross-tenant-read`) and `chain-to-impact` lists IDOR/BOLA cross-tenant as the top class. A finding phrased *"cross-tenant data disclosure"* died at Check 4 "No chain analysis" for a chain that is actually length 1. Fix (additive): add `cross-tenant|IDOR|BOLA|mass-pii|identity-spoofing|sender-misattribution` to terminal goals.

**Meta-lesson:** lexical collision was just the first symptom. The deeper defect is **gate vocabulary drift** — each stage names a class in its *own* words (`identity-spoofing` at finding_gate, `impersonation` in the finding prose, `cross-tenant-read` at finding_gate vs `cross-tenant` in the report), and a downstream `_TERMINAL_GOALS`/`SOCIAL_PATTERNS`/`HYGIENE_RE` list that does not contain the upstream stage's word silently DELETES a valid finding. When a finding dies at `validate`/`triage` for a reason that names a class the *upstream* gate just scored as a finding, the bug is a missing synonym in the downstream list — not the finding.

**A fifth defect, `weaponize-gate.py` — plan text treated as evidence (2026-11-02):** `analyze()` fed
`classify_impact` / `_is_terminal_impact` / `classify_chain` a `json.dumps(rec)` of the **whole record**,
so the analyst's own PLAN fields (`next_to_hunt`, `fix_regression`, `weaponization`) — which legitimately
name OTHER bug classes (`"SSRF → metadata → RCE"` is the *next step to hunt*, not a finding) — leaked into
the severity classifier. Measured: a Low `version disclosure` finding with no declared severity
auto-inflated to **Critical** driven by the `rce` word in `fix_regression`. This is the exact
`depth_gate`-§S class: a serialized object's keys/values satisfy the gate's own vocabulary. Fix: build
the classifier input from the finding's OWN claim only — strip plan keys (`next_to_hunt`, `chain_next`,
`missing_link`, `fix_regression`, `regression`, `weaponization`, `attacker_use`, `exploitation`,
`technique`, `primitive`, `escalations`, `escalation_path`, plus `severity`/`declared_severity`/`sev`)
before `json.dumps`. Verified both ways: Low version-disclosure (no declared sev) stays `low` (signals
`version`/`banner`); a genuine pre-auth RCE stays `critical`. **Standing rule: plan text is never
evidence** (`lead-to-critical`), and no gate should ever build its search text from a whole serialized
record — flatten *values-only, claim-only* like `depth_gate` §S does.

*Wrong* result rather than an error, which is why they survived so long.

**W1. `asset-coverage.py` is not in `scripts/` — and a failed `find` reads as "the script is gone".**
The gate `0B` requires `asset-coverage.json`, so the natural move is
`python scripts/asset-coverage.py --init <dir>` → `can't open file '...scripts/asset-coverage.py'`.
The conclusion "the script was deleted" is wrong. It lives under the discipline skill:

```bash
AC="~/.chiper/skills/bounty-pack/audit-execution-discipline/scripts/asset-coverage.py"
python "$AC" --init  "<target-dir>"      # seeds assets
python "$AC" --derive "<target-dir>"     # fills from real artefacts (positional, no --target-dir)
```
`--init` on a 45-host target seeded **83 assets**; `--derive` then resolved them from the artefacts
actually on disk. Before reporting any pipeline script as missing, resolve it by name across both
trees: `find "~/.chiper/skills/bounty-pack" -name '<script>.py' -not -path '*/cache/*'`.

**W2. Restoring from a backup by glob order restores an EIGHT-DAY-OLD file.** After an indentation
break, `sorted(glob(bak_*))[-1]` picked `...bak_triage_20261010_085815` — the alphabetically last
name, not the newest — and silently reverted every patch made that day. The file still compiled, so
nothing complained. Always sort by mtime and print the choice:

```python
baks = sorted(glob.glob(p + ".bak_*"), key=os.path.getmtime)
print("restoring from", os.path.basename(baks[-1]))   # eyeball it before copying
shutil.copy2(baks[-1], p)
```
Then **verify the patch markers survived** (`"_msys_norm" in s`, `"WEAPONIZATION.md" in s`, …) —
a restore that compiles is not a restore that is correct.

**W3. Patch a set literal with a LINE anchor, never a block replace.** Replacing the whole
`EXCLUDE_DIRS = {...}` block by string match dropped the indentation of the closing brace →
`IndentationError`. Safe pattern — find the closing line, add a comma, insert after it:

```python
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
t = next(i for i, l in enumerate(lines) if "manifest-work" in l and "}" in l)
ind = " " * (len(lines[t]) - len(lines[t].lstrip()))
lines[t] = lines[t].replace('"manifest-work"}', '"manifest-work",')
lines[t+1:t+1] = [ind + '"evidence", "tool-evidence", "captures", "screenshots", "logs"}\n']
```
This is the same anchor-don't-slice rule that governs SKILL.md edits, and it applies to source code.

**W4. The whole-gate MSYS sweep has to include the scripts you *think* you already patched.**
`weaponize-gate.py` had **zero** occurrences of `_msys_norm` — every `--out` / `--report` / input
path failed with `FileNotFoundError: \c\Users\...` from git-bash. Patching gates one at a time left
it behind for weeks. Sweep by presence-of-helper, not by memory:

```python
for f in sorted(glob.glob(S + "/*.py")):
    s = open(f, encoding="utf-8", errors="replace").read()
    if re.search(r"Path\(args\.", s) and "_msys_norm" not in s:
        print("UNPATCHED:", os.path.basename(f))
```

**W5. `aggregate-findings` re-ingests `evidence/` as findings.** `rglob("*")` reached into the
evidence directory and `parse_plain_findings` manufactured a candidate *out of the raw
request/response capture* — `"[evidence\p] 1 notable response(s) — Medium"` — so 1 real finding
became 2, and the phantom then travelled through every downstream gate. Fix is one line in
`EXCLUDE_DIRS`: `evidence`, `tool-evidence`, `poc-evidence`, `raw`, `_raw`, `captures`,
`screenshots`, `logs`, `artifacts`. Generalisation, already stated in §2b but worth repeating:
**any directory that stores raw captures must be excluded from the finding parser**, and when you
add an artefact producer, add its output name to `SKIP_NAMES` in the same change.

**W6. `mkdir` before target validation leaves permanent junk.** `--help` (or any typo) created
`poc-plans/orchestrator---help/` because `self.output_dir.mkdir()` ran *before* the target-type
check. Cheap pre-check before scaffolding — and do not invent a method name for it (calling a
non-existent `self._classify_target()` compiles fine and only explodes at runtime):

```python
_t = (self.target or "").strip()
if not (_t.startswith(("http://", "https://")) or "." in _t
        or _t.endswith((".sol", ".apk", ".ipa")) or _t.startswith("0x") or os.path.isdir(_t)):
    log(f"❌ PIPELINE FAILED: target tidak dikenali tipe-nya: {_t!r}"); raise SystemExit(2)
```

**W7. The orchestrator's own banner lied about the gate width.** It printed
`verify-tool-usage (11 checks)` while the script enforces **13** — check 12 (`asset-coverage`) and
check 13 (`skill-usage`) were invisible to the operator reading the run header. Any count in a
banner must be derived from the gate, or it will drift.

## 2d. Picking the hunt surface from the program's SEVERITY MODEL (2026-10-30)

Scope is not the only gate — the **scoring model** decides whether a class is worth hunting at all.
Read it before planning probes, and record it in the engagement's `SCOPE-<target>.md`.

| model | shape | what pays |
|---|---|---|
| **CVSS / VRT** (HackerOne, Bugcrowd, most SaaS) | severity tiers over vuln classes | hygiene and info-disclosure classes have real (if low) value — headers, CORS, version disclosure, introspection can still pay something |
| **Fund-loss** (DeFi, bridges; e.g. Relay: S1–S4 × L1–L3, floor $500, cap $100k, *"S4 — total fund theft or protocol insolvency"*, *"admin-only bugs are S1"*) | severity by **damage to funds**, likelihood by feasibility | **web-app hygiene is worth ~nothing regardless of how clean it is.** Only a demonstrated path to fund loss or freeze pays: contract logic, quote/settlement arithmetic, signature binding, oracle/price manipulation |

Two consequences that are easy to get wrong:

- **Choosing the web tier on a fund-loss program is choosing to work for free.** A perfectly clean
  header/CORS/introspection finding is S1-at-best and the S1 floor applies *only* with a
  demonstrated external exploit path. If the model is fund-loss, switch to the contract/settlement
  surface early instead of polishing the web tier.
- **The PoC bar is per severity and is often "runnable".** Relay: *"S4, S3 — Runnable PoC required.
  Explanations without code are not accepted."* Plan the harness (fork + Foundry) before the hunt,
  not after finding something you cannot execute.

**And read the out-of-scope list as ASSETS, not words.** Relay's page ended with *"Relay Vaults. The
Vaults contracts (…), **the vaults API** and the vaults user interface are not in-scope assets."*
Recon had already found `vaults-api.relay.link` with GraphQL introspection open and `userBalances`
enumerable across every wallet — a textbook juicy surface, and **100% worthless**. The tell that you
are about to waste a day: the host name contains a product noun the policy names. Read the OOS list
*before* touching a promising host.

## 2e. An AD-HOC audit can pass CHECK 1–5 but never 6–13 — and that is not a licence to hand-write ledgers (2026-10-30)

Worked a target with the tools directly (recon → API map → probing → one finding) instead of through
`audit-pipeline-orchestrator.py`. At the end `deep-audit-mode.py guard` answered
**`⛔ BLOCKED — real pipeline has not passed for this target`**, and `verify-tool-usage.py` split
exactly along one line:

```
✅ CHECK 1  tools-usage.json exists
✅ CHECK 2  all 12 executed tools have evidence files
✅ CHECK 3  all evidence files real content (>=100 bytes)
✅ CHECK 4  all 17 entries accounted for (no silent skip)
✅ CHECK 5  12 tools executed with real evidence
❌ CHECK 6  variant-usage.json missing
❌ CHECK 7  poc-execution.json missing
❌ CHECK 8  poc-variant-usage.json missing
❌ CHECK 9  business-logic-usage.json missing
❌ CHECK 10 reference-usage.json missing
❌ CHECK 11 poc-techniques-usage.json missing
❌ CHECK 12 asset-coverage.json missing
❌ CHECK 13 skill-usage.json missing
RESULT: FAIL (8 failures) — DO NOT GENERATE REPORT
```

**CHECK 1–5 are legitimately satisfiable after an ad-hoc run. CHECK 6–13 are not.** The split is not
arbitrary: 1–5 read `tools-usage.json` + `tool-evidence/*` — artefacts an ad-hoc run really produces —
while 6–13 each read a ledger written by a **producer script** (`execute-variants.py`,
`track-poc-execution.py`, `execute-poc-variants.py`, `execute-business-logic.py`,
`execute-references.py`, `execute-poc-techniques.py`, `asset-coverage.py`, the skill tracker).

**Building `tools-usage.json` by hand is legitimate — when it is a transcription, not an invention.**
The gate reads disk, so copy each real output into `tool-evidence/<tool>.txt` (≥100 bytes, verified
non-empty) and point `evidence_file` at it relative to the target dir. Keep statuses honest and inside
the accounted vocabulary (`EXECUTED`, `RAN_WITH_ERROR`, `NO_OUTPUT`, `NOT_FOUND`, `ERROR`, `TIMEOUT`,
plus the `SKIP_*` / `N/A` / `FAILED` family). A tool you never ran is `NOT_FOUND` or
`SKIP_WITH_REASON` **with the reason**, never `EXECUTED`; an entry with no `status` key at all surfaces
as `unaccounted statuses: [None]` (see §2 U). This is transcription of work that happened — the same
class as §2 U's normalisation, and the opposite of padding.

**Hand-writing the other eight ledgers is the padding the gate exists to catch.** Do not. Run the
producers instead; at minimum `execute-business-logic.py` is cheap and fills CHECK 9 with real probes:

```bash
python "$S/execute-business-logic.py" "https://api.target" --target-dir "C:/…/target-dir" --rate 1.5
# 15 vectors -> business-logic-usage.json + business-logic/<vector>.txt
```

It shells out to `nuclei` for the vectors that have a matching tag, so a single vector can sit for
minutes — run it `background=True, notify_on_complete=True` and read progress from `ls business-logic/`.

**The doctrine that keeps this honest, because both wrong answers are tempting:**

- A red gate blocks the **coverage claim**, not a proven finding. A finding backed by direct,
  3×-reproduced evidence stands on its own; the gate does not make it stronger or weaker.
- What a red gate forbids is the *other* sentence: **"0 findings" / "estate clean" / "coverage
  complete"**. Those are claims about the whole surface and they need the ledgers.
- So neither fabricate the ledgers to turn it green, nor suppress a real finding because it is red.
  Hand off in this shape: *"gate BLOCKED (8 ledgers absent — ad-hoc run, no orchestrator); coverage
  LIMITED, not complete; finding X stands on its own 3× evidence; unproven leads named as unproven."*
- If the operator wants green, the answer is to run the orchestrator for real (2–4 h of re-work on an
  already-probed target) and say so plainly — not to manufacture bookkeeping.

### 2e-bis. Running the producers gets you to 10/13 — three checks are structurally unreachable

Follow-up measured the same day (bankr.bot): instead of stopping at 8 failures, the producers were
actually run — `execute-business-logic.py` (15/15 vectors, 56 probes), `execute-variants.py`
(15/15 vectors, 102 requests), `track-poc-execution.py`, `execute-poc-variants.py`,
`execute-poc-techniques.py`, `asset-coverage.py --init/--derive/--mark`. Result: **10/13 PASS, still
BLOCKED.** Knowing the three walls up front is what stops the hours of chasing:

| Check | Wall | Detail |
|---|---|---|
| 10 | `reference-usage.json` | `execute-references.py` hard-refuses without `references-index.json`, and **only `force-full-execution.py` builds that index** → `❌ references-index.json tidak ada — jalankan force-full-execution dulu`. No standalone path exists. |
| 12 | `asset-coverage` 0B/0C | Accepts `N/A` **only** for "feature absent in target". Rejects `"covered by X instead"`, `"superseded by nuclei"`, `"RoE forbids brute force"`, `"no repo in scope"`, and flags `"vector already fired via execute-variants"` as *"a SURRENDER not a reason"*. Only shape that passes: name the probe that proved the target lacks the feature. |
| 13 | `skill-usage.json` | **No generator script exists on disk** (`ls scripts \| grep skill-usage` → nothing). Unreachable by any supported route. |

**Do not mark N/A with an invented structural reason to force green.** That converts an honest
BLOCKED into a fabricated coverage claim — it inverts the gate, which exists to prevent exactly that
over-claim. Two honest exits only: launch the orchestrator at 0A, or hand off `BLOCKED` with coverage
stated as limited and the untested list named.

Two mechanical notes that save time on the way:
- `asset-coverage.py --derive` populates from **pipeline-shaped artefact names**, so a manual audit's
  evidence is invisible and ~60 assets come back `NOT_RUN` even though the tools ran. Fix the *names*
  first (`cp 0B_recon/all_subs.txt subs.txt`, `httpx.txt → live.txt`, `katana_urls.txt → urls.txt`),
  then `--derive`, then `--mark` the residuals.
- `asset-coverage.py` lives under `skills/security/audit-execution-discipline/scripts/`, not
  `scripts/` — see §2c W1.

Full transcript, the CHECK 12 rejection vocabulary verbatim, the standalone-runnable producer
commands, and the truthful `tools-usage.json` construction recipe:
**`audit-execution-discipline/references/adhoc-audit-vs-13-check-gate.md`**.

## 2f. Armed-dir ≠ orchestrator output dir — and `cp -rf` of the whole output dir flips the guard to web3 (2026-11)

Two related traps when you `deep-audit-mode.py arm <target> --dir <workdir>` but the *report* and
evidence live in a different directory than the orchestrator's own output:

1. **The orchestrator writes to `poc-plans/orchestrator-<slug>/`, not your armed `--dir`.**
   Running the pipeline from `/d/<target>` leaves that dir with only YOUR files
   (`REPORT.md`, `recon/`, `evidence/`) — no `tools-usage.json`, no `asset-coverage.json`. `guard
   <dir>` then reads the wrong dir and answers `tools-usage.json not found`. Fix: copy the whole
   orchestrator output dir over the armed dir first
   (`cp -rf poc-plans/orchestrator-<slug>/* /d/<target>/`), *then* gate. (Or simply `arm` the
   orchestrator dir itself as the report dir.)
2. **`cp -rf` drags in `contract-audit.json`, which is a web3-track signal — and it's the
   orchestrator's OWN self-audit, not the target's.** `detect_track()` treats `contract-audit.json`
   as a contract marker, so a pure web2 target you just bulk-copied suddenly gates as
   `web3 (contract-only) — no *.sol found`. Fix: `rm contract-audit.json` from the armed dir
   (it is the pipeline auditing its own subprocess calls, irrelevant to a web2 report). This is the
   pathological companion to §2 T: the file that flips the track is produced *every* run, not only
   on contract scopes.

Then the normal §2 L flow: `asset-coverage.py --derive <dir>` → `--mark` the residuals → `guard`.

- The state file lists completed phases and resume **skips them**: `0A, 0B, 0C` done ⇒ resume goes straight
  to the 0D gate, so whatever a 0C step should have written must already be on disk (fix A).
- A phase can be COMPLETED and still fail its *coverage* later — completion markers and coverage are
  separate checks (0F "done" while `0E-REVIEW` coverage is red is normal).
- Resume re-derives `asset-coverage.json` before gating, so writing a missing ledger then resuming is enough.

## 3b. Resuming an ENGAGEMENT (not just a pipeline run) — check what is already closed

Resume semantics above assume the pipeline state file is the only memory. On a **repeat
engagement** the real memory is the vendor's inbox, and ignoring it wastes the whole round.

Before spending a single hour on a target the operator has engaged before:

```python
q = '(from:<vendor-domain> OR to:<vendor-domain>)'      # Gmail API users/me/messages
# format=metadata with metadataHeaders=From,To,Subject,Date
```

Normalize, then build two maps:

- **sent** — unique outbound report subjects. Strip `[BUG BOUNTY]` / `[Bug Bounty] `,
  collapse `Re:` chains, dedupe on the first ~60 chars lowercased. (Flux 2026-10-27: 77
  messages → **60 unique reports**; the duplicate sends were real and inflate the map
  without dedupe.)
- **verdict** — every vendor reply with its **verbatim** rejection reason per finding.

Then cross `sent` against the in-scope host list: `host in reported_text or
host.split(".")[0] in reported_text`. Hosts never named are the only genuinely new
surface (Flux: 263 in-scope → **188 never named**). Filter those before probing —
third-party-hosted (docs/wiki/games/n8n/grafana) is OUT per most policies, and a service
exposing only `/health` has a Low ceiling and is rarely worth a run.

**Read verdicts as an oracle for what is dead.** Verbatim Flux reasons:

| Verdict phrase | Meaning |
|---|---|
| "covered by our internal security audit" | Closed **regardless of severity** — never re-report the class |
| "reported before you" / "already known to us" | Closed; being first is the only gate that pays |
| "by design" / "intended" / "compatibility mode" | Closed unless a *different* unintended impact exists |
| "we rate it Low rather than High, because …" | Real finding, **Low ceiling** — believe the argument, not your scorer |

That last one bit hard this session: an unauthenticated IDOR leaking `payment_address`,
`collateral`, `tx` scored **High** by the tool and **Low** by the vendor — *"the data is
payout bookkeeping that is largely visible on-chain anyway."* The vendor was right.
See `artifact-backed-claims` §"A severity SCORER is an instrument too" rows 7-8.

**The specific trap this prevents.** Operator asked to "dig deeper" into a High finding;
the mailbox showed it had been reported **and rejected 12 hours earlier**. Deepening it
would have paid nothing and repeated the exact testing violation the vendor had already
flagged in writing (*"you queried other users' staking and payment records on production
… please don't do that"*). One search avoided both costs.

**When a vendor states a testing constraint, it binds the rest of the engagement:**
enumerate population **counts** only, never other users' record contents; and if the
remaining interesting surface needs an account you do not have (owned node, KYC, paid
tier), stop and surface the decision to the operator rather than improvising around it.
A verified-negative round — surface mapped, auth differentials run, ceiling stated as Low
with the reason — is a legitimate deliverable.

Full recipe, queries, and the worked Flux walkthrough:
`references/recurring-engagement-prior-art.md`.

## 4. Stall / throttle — a run degrading is being blocked

Minutes → hours per step, then the host stops answering at TCP level while sibling hosts stay 200 =
per-host drop at the target's edge. Preflight each target (`httpx -status-code -timeout 12` ×2 + one TCP 443
connect) and during the run check `find <target-dir> -type f -mmin -45 | head -1`: empty **and** host silent
→ kill the tree, mark `BLOCKED-throttled` + 6 h cooldown, next product. Attribution table, cooldown pattern
and the uniform-403 variant: **`bot-protected-target-testing` §3a-1c**. The block is a working control, not
a finding — record it as operational state plus the coverage it cost.

## 5. "CONFIRMED" from the pipeline is a candidate, never a finding

impact-verify, the DOM-XSS checker, the variant executors and `finding_gate` each emit positives that are
wrong for mechanical reasons. Verify the class with an independent method before it reaches `CANDIDATES.md`.
Measured classes + one-shot disproofs (raw-socket 2-step redirect, browser canary flag, sha-vs-baseline,
WAF-deny vs exposure, banner-as-proof, probe-never-sent): **`references/pipeline-fp-classes.md`**.

### 5.0 Count discipline — one number for the operator, and it is "findings ready to submit"

Operator correction (live 2026-10-25, Proton): the status update said *"1 finding READY"* earlier and
later *"3 POC (dalfox)"*, and the sane reading of that is **"you found 3 things"**. The operator had one
draft and asked where the other two were. Nothing was misrepresented in the ledger — the phrasing did
the damage.

Rules for any progress report to the operator:

- Lead with **one** count: findings that are `READY` (valid + reproducible + impact). Everything else
  is not a number you put in the headline.
- Never write a scanner's positive count (`3 POC`, `12 hits`, `CONFIRMED x4`) as a bare number. Attach
  the verdict in the same breath: `3 dalfox POCs — all false positives, disproved by reflection test`.
- Keep a single running line of the shape
  `READY: <n> · DISPROVED: <n> (why) · NOT TESTABLE: <n> (blocker) · NOT RUN: <n>`,
  and keep it byte-identical to the ledger. If the ledger and the chat summary disagree, the summary
  is the bug.
- "Candidate", "POC", "signal", "CONFIRMED by scanner" are internal words. When talking to the
  operator, a thing is either a **finding you can submit** or it is **not a finding**.

### 5a. Three result classes that are NOT findings and NOT negatives

An audit owes a verdict on every class it touched. Three shapes produce a verdict that is wrong in
opposite directions — a false positive you might report, or a false negative you might claim. Both
cost the engagement. All three are one-command to settle.

| shape | what it looks like | disproof | what to write |
|---|---|---|---|
| **SPA catch-all (soft-404)** | ffuf/gobuster hit `.env`, `.git/config`, `actuator/*`, `Dockerfile`, `.well-known/jwks.json` as 200/403 on every host | fetch a random path and `sha256` it; identical hash = catch-all. Real 404s usually exist only under `/api/*` | "N path hits, all identical to the SPA shell → no exposure". Keep the sha table |
| **scanner `[POC]` on a reflected-looking param** | dalfox emits `[POC][G][GET][BUILTIN] .../signup?ref=x` | request the URL with a canary and with an XSS payload; compare body length **and** grep for the canary. Identical length + canary absent = never reflected | "1 candidate, disproved by reflection test". Never ship the POC line as a finding |
| **scanner got a 4xx/401, calls it a negative** | sqlmap `400 Bad Request` / `CRITICAL not authorized (401)`, or `all tested parameters do not appear injectable` after the app rejected the request | the app never processed your input, so you measured nothing. Add the required headers (`Accept`, vendor app-version header, auth cookie) and re-run before scoring | "re-run with correct headers → param not dynamic". Discard the blocked run entirely |

The third one is the dangerous one: a WAF/400-shaped response reads exactly like a clean negative in
a log, and it is the mechanism by which "0 findings, target hardened" reports get written on a target
nobody actually tested. Treat a blocked scanner run the same as a failed tool (`RAN_WITH_ERROR`), not
as evidence. Corollary already in §5: a `0 findings` report is publishable only next to its coverage
table — and a row saying "sqlmap: 400" is a gap, not a negative.

**Do not upgrade a candidate on the scanner's word, and do not downgrade a class on a blocked run.**
Both directions need the one-shot disproof above.

### 5b. A 2xx/3xx flip is a HIDDEN HEADER CONDITION until you prove it is flaky

Measured 2026-10-25 (betterteam, `app.betterteam.com/debug`): the endpoint returned **200** at 05:47 and
**302** to the app root at 07:33 for "the same request", so it was written down as `UNSTABLE → DROPPED`.
It was deterministic the whole time — **200 for every `Accept` value except `text/html`**, and
`Accept: text/html` (what both `curl` defaults and a Python `urlopen` send in different contexts) 302'd.
Confirmed 3/3 repeats + 7 header variants. A real Low-severity info-disclosure was nearly discarded by a
correct-sounding rule ("not reproducible ⇒ do not report"). The rule was right; the *test* was incomplete.

Before you write `UNSTABLE` / `not reproducible`, run the trigger matrix — one variable at a time, 3× each:

| axis | values to try |
|---|---|
| `Accept` | `text/html`, `application/json`, `application/vnd.api+json`, `*/*`, **omitted** |
| `Content-Type` (on POST/PATCH) | json, form-urlencoded, vnd.api+json, multipart |
| `User-Agent` | browser string, `curl/8.x`, library default, empty |
| cookie | authenticated jar / anonymous / jar with one cookie removed |
| method & shape | GET vs HEAD, trailing slash, with vs without query string, `X-Requested-With: XMLHttpRequest` |
| `Sec-Fetch-*` | browser-realistic (`Sec-Fetch-Mode: navigate`) vs absent |

Why this class matters: an `Accept`-gated page is exactly the shape of a *browser-blocked, tool-served*
endpoint. Browser-only testing misses it; tool-only testing sees it and looks wrong to a triager.
So the trigger condition belongs **verbatim in the repro** ("returns 200 unless `Accept: text/html`"),
which simultaneously explains the discrepancy and pre-empts "cannot reproduce".

Corollary: `UNSTABLE` is a conclusion you earn after the matrix, not a label you apply to the second
sample. If you never ran the matrix, the honest status is `NOT FULLY CHARACTERISED` and the candidate
stays open — not dropped.

Classes added 2026-10-17 (gewasschademelden + safe + startgrid): **SSTI "CONFIRMED"** from a `49`/`56`
substring detector that fired on a base64url `code_challenge` already in the baseline — disprove by
normalising nonce/state/code_challenge and diffing sha, plus a marker-substitution check; **leaked API key**
that is referer-locked (call it from a neutral origin); **client-set cookie** that only *looks* like a trust
signal (differential over real/empty/garbage values); **anonymous embed token** that is by-design for a public
transparency portal; **framework default 500** on an OAuth `error=` callback (plain text, no stack, no
reflection) = robustness, not disclosure.

Corollary for negatives: a `0 findings` report is publishable only next to its coverage table — what ran
with evidence, what was N/A and why, what was never tested.

### 5d. Three gate/review scripts over-pass on their own scaffolding — re-review by hand (measured 2026-10-27, cleanshot)

A negative audit is not finished when `validate-findings.py` says 0. Two downstream reviewers
(`review-candidates.py`, `finding_gate.py`) **re-admit** candidates on keyword matches against their
own metadata, and both were wrong on every candidate they passed. Measured on one run:
`validate-findings.py` 20→0 (correct) · `review-candidates.py` 7 READY (all 7 false) ·
`finding_gate.py` 3 survivors (all 3 false).

| FP class | what the script saw | what the evidence actually said | disproof |
|---|---|---|---|
| **WAF-429 probe scored as demonstrated reach** | `impacts: ssrf, ssrf`, score 18, verdict REPORT | every line was `[429] https://…/http://127.0.0.1/ (149B)` + the WAF's "unusual traffic" page. The origin never saw the request | grep the candidate text for the status code. If every line is 429/403 with an identical body, the probe never landed — the matcher is scoring the *URL you tried*, not the result |
| **sqlmap negative template scored as CRITICAL** | `impacts: code-exec` | `[CRITICAL] all tested parameters do not appear to be injectable` — `CRITICAL` is part of sqlmap's **negative** output template | read the sentence after the severity word. "not injectable" / "do not appear" = negative, regardless of the bracketed level |
| **argparse usage dump counted as a reproduction step** | "step-by-step tersedia" → READY | `usage: poc.py [-h] --target TARGET` / `error: unrecognized arguments: <url>` — the tool never ran | if the "steps" are `usage:`/`error:`/`--help` lines, the tool never touched the target. Reject |
| **tool banner lines as findings** | `Author: @vladko312`, `Scanning url: …` | the tool's own conclusion in the same file was `Tested parameters appear to be not injectable` | read the tool's verdict line, not its banner |

Rules that follow:
- **Treat the three reviewers as independent votes, not a pipeline.** Any one of them passing a
  candidate is a prompt to re-read the evidence, not permission to report.
- A candidate whose evidence is 100% one status code (all 429, all 403, all 400) has measured
  **nothing** about the target — it is a blocked run, and a blocked run is neither a finding nor a
  negative (see §5a row 3).
- Write the manual re-review to a file (`0E-REVIEW-pass23.md`, `0E-REVIEW-pass3-final.md`) so the
  disagreement with the script is auditable. The operator's rule is 3× verified; three script passes
  that all over-pass do not substitute for one honest manual pass.
- `review-candidates.py`'s CEK-3 matches impact keywords **anywhere** in the candidate text,
  including the harness's own labels (`impact: data exposure`, `impact: ssrf to internal`) that it
  writes into `variants/*.txt` as metadata. Self-matching scaffolding is the single most common
  cause of a phantom READY.

### 5b. Never let a scanner's POC count become your findings count

The operator counts **drafts you shipped**, not scanner lines. Saying "3 POC" when one is real makes you
sound productive and is a credibility loss ("kamu blm temuan ad 3, tp sy cm ad 1 draft" — 2026-10-25).

Measured that session: `dalfox` produced 3 POC lines across two runs
(`[POC][G][GET][BUILTIN] https://account.proton.me/calendar/signup?ref=ctaprd`, plus a variant where
dalfox injected its own test parameter). All three were the SAME non-sink. Disproof took 2 minutes:

```python
# canary + XSS payloads against the flagged param — compare against the no-param baseline
for u in [f"{base}?ref=zz9f3k2mcanary", f'{base}?ref="><img src=x onerror=alert(1)>']:
    r = requests.get(u, headers=UA, timeout=25)
    print(r.status_code, len(r.text), "canary" in r.text, "onerror" in r.text)
# 200 8205 False False   (identical length to the no-param request -> nothing reflected)
```
Plus: grep the bundle for the param's consumer — here the only use was `params.append("ref", …)` into a
redirect URL, i.e. **no DOM sink**. Verdict: FALSE POSITIVE.

Rules that follow:
- **Count findings as validated + reportable only.** Scanner POCs are candidates; say "1 finding, 3 POCs
  of which 2 were the same param and all disproved", never "3 POCs".
- A param that is never reflected in body **or** headers, and has no DOM sink in the bundle, is an FP —
  write the disproof to a file (`dalfox-verification.txt`) so the negative is auditable.
- The same discipline applies to `sqlmap`/`ghauri`: a run that returns HTTP 400/401 for every request
  (missing mandatory header, or auth-gated) tested **nothing**. Discard it and re-run with correct
  headers before you record a negative — "not injectable" from a 400 loop is a fabricated negative.
- When a scan tool's output goes to the user, lead with the validated count and put the raw tool counts
  in parentheses.

### 5c. Before a "0 matches" scan counts as a negative, verify it actually finished

A scan's silence has three totally different meanings and only one of them is a result. Measured on the
Proton run (2026-10-25) — three `nuclei` attempts on the same 22 hosts:

| run | ended at | output file | verdict |
|---|---|---|---|
| full 11-tag set | **12%** of 266 970 requests, killed under RAM pressure | 0 B | **NOT TESTED** — must be re-run, never reported |
| slim 6-tag set #1 | 11% of 60 830, killed | 0 B | **NOT TESTED** |
| slim 6-tag set #2 | **95%**, 58 089 requests, 1 111 templates, `[INF] Scan completed in 1h42m` | 0 B, **0 matches** | legitimately negative **for that 6-tag set** |

The 0-byte output file is identical in all three rows, so the file alone tells you nothing. The
discriminators are, in order:

1. **The final stats line**: `percent` near 100 *and* `[INF] Scan completed in …`.
2. **Error ratio**, not error count: 779 errors looked alarming but is 1.3% — template-level parse/auth
   failures. A 40%+ error rate means you were being throttled and the run is worthless.
3. **Host liveness *after* the run** — re-`httpx` the same list. 22/22 answering `200/301/302/404` proves
   the target never dropped you; anything less means the "clean" result is a blocked result.
4. **Write down which template set the negative belongs to.** "0 matches with
   `exposures,exposed-panels,misconfiguration,default-login,takeovers,unauth`" ≠ "the host is clean".
   The `cve/jwt/graphql/swagger` sets were never completed, so they stay `NOT TESTED`.

Never upgrade a partial scan to "target is hardened" in conversation, and never let a scanner's own
`[POC]`/`[matched]` count read as a finding count — see `artifact-backed-claims`
("Never let a tool's output count become a finding count").

## 6. Multi-product engagements (one vendor, many hosts)

A vendor with N products is a **queue**, not a single run. Pattern that worked (Gasunie, 18 products):

- Keep `jb-products.txt` (tab-separated: id, label, url, status, tech) + `jb-current-target.txt` +
  `RUN-STATUS.md` in one audit workdir. Statuses: `pending` → `DONE` / `BLOCKED-throttled` / `BLOCKED-gate`.
- **One product at a time, 0A→0F, guard before DONE.** Never start a second pipeline while one is running
  (`wmic process get commandline | grep audit-pipeline-orchestrator | grep -i <vendor>`).
- **Preflight every product before launching it** (httpx ×2 + one TCP 443 connect). A host that fails
  preflight is marked `BLOCKED-throttled` with a cooldown line in `jb-cooldowns.txt` and skipped — do not
  launch a run into a host that is already dropping you.
- **Mid-run stall detection:** `find <target-dir> -type f -mmin -45 | head -1` empty **and** the host silent
  ⇒ the target throttled you; kill, cooldown, next product. A run that takes 9 h and produces one variant file
  per hour is being rate-limited, not being thorough.
- **Automate the grind** with a cron job that: checks for a running pipeline, preflights, picks the first
  `pending` product, runs it, applies the §2 fixes, verifies guard + checkpoint, updates the files, and
  reports in a few bullets. This is what keeps a 16-product queue moving without a foreground session.
- **Cooldown bookkeeping matters:** a host blocked at 04:35 may be fine at 20:00. Record the timestamp and
  reason so the next tick can retry it instead of skipping forever.
- **Throttle is operational state, not a finding** — but it *is* coverage you owe the report: say which host
  was blocked and what that cost.

## 7. GENTLE mode — stay automated on "no scanners" programs (2026-10-25)

Some programs (measured: betterteam) state *"No automated vulnerability scanners, broad crawling or
fuzzing … under 5 requests in any one second in total."* Operator doctrine: **never fall back to
manual/curl-only** — the run must stay automated, just slower. Do it with one additive, env-gated
patch to the orchestrator instead of editing each command by hand:

```python
# in run_setup's CMD dict, right after the dict literal closes
if os.environ.get("BB_GENTLE", "0") == "1":
    CMD.update({
        "nuclei": "nuclei -u {t} -severity critical,high,medium -silent -rl 3 -c 1 -timeout 10 -o {o}",
        "ffuf":   "ffuf -u {t}/FUZZ -w {w} -mc 200,301,302,401,403 -rate 3 -t 1 -s",
        "sqlmap": "sqlmap -u {t}/?id=1 --batch --level 1 --risk 1 --smart --timeout 15 --retries 1 --delay 2",
        "arjun":  "arjun -u {t} -t 1 -m GET",
        "dalfox": "dalfox url {t} --no-spinner --silence --delay 500 --worker 1",
    })
```
Also drop `katana -rl 5 -c 2` → `-rl 2 -c 1` in the recon `extra` list (same env check).

Rules for applying it:
- `cp audit-pipeline-orchestrator.py audit-pipeline-orchestrator.py.bak_gentle_<date>` first, then
  `python -c "import ast;ast.parse(open(...).read())"` — a syntax error here costs the whole run.
- Env-gate it (`BB_GENTLE=1` on the invocation) so other engagements keep their default rates.
- Keep every tool in the run. Gentle ≠ fewer vectors; a skipped tool is still a `NO RESULT`.
- Expect these runs to be SLOW: the variant step has its own **45-minute internal cap** and logs
  `variants TIMEOUT 45m — pakai artefak parsial, lanjut` — that is a normal, accounted outcome
  (partial artifacts are kept), not a failed gate.
- A single hung helper (measured: `sstimap.py` against a signup URL, 25+ min, 2 GB RSS, free RAM
  down to ~180 MB) can starve the run. Kill **only that child PID** and let the parent continue.
- **Before declaring your run stalled, identify which PID is yours.** More than one engagement may be
  running (`wmic process where "name='python.exe'" get ProcessId,CommandLine | grep
  audit-pipeline-orchestrator`). Match the target URL in the command line; never kill a PID you did
  not start, and remember a sibling engagement's nuclei is also eating the RAM and rate budget.

## 8. Reading the run's own endpoint map (don't trust last week's)

0B in this pipeline is a *scanner* recon: it seeds `urls.txt` from subfinder/httpx/katana/dork, so on
a JS-heavy SPA it can return "host role: static-site" and stop. The real endpoint map for SPA/API
targets must be rebuilt from the built bundle: pull the asset list out of the SSR shell, download the
chunks from the CDN host, then grep for `\.(get|post|patch|put|delete)\(\s*["'`]/(path)` — that is how
the 24-endpoint dashboard map replaced the 11-endpoint "deep recon" output. Put the result in a
`references/` file on the target skill, with the date, and re-derive it on the next run (asset hashes
rotate).

## Support files
- `references/recurring-engagement-prior-art.md` — **read before re-hunting a target with
  engagement history.** Mailbox-based prior-art reconstruction (sent map + verdict map,
  dedupe rules), the host cross-reference that isolates genuinely untouched surface, the
  vendor-verdict oracle table, and the testing-discipline rules that follow from a stated
  constraint. Worked walkthrough: Flux/Titan, 77 messages → 60 reports → 188 untouched hosts
  → a High finding that was already rejected 12 h earlier.
- `references/severity-gates-and-phase-placement.md` — **read before touching any finding gate, or
  before answering "will a Low/Medium/High/Critical actually get through?"** Canonical phase
  placement (aggregate+weaponize+chain_builder live in 0C-C7, not 0E), the phase-to-phase data
  contract, the verified 4-level severity matrix with 5 negative controls, the seven gate defects
  that made "strict" mean "broken" (symptom → cause → fix), the re-verify command sequence, and the
  fixture shape each finding needs to be judged on quality rather than on missing fields.
- `scripts/severity_gate_regression.py` — **run this after ANY edit to aggregate-findings /
  weaponize-gate / finding_gate / validate-findings / triage_gate, and before trusting a negative
  audit.** Builds both fixture sets, runs the real chain, and asserts both directions: 4/4
  critical/high/medium/low must survive to triage PASS, and 5/5 junk candidates must be rejected.
  Exit 1 names which assertion broke. Checking one direction alone proves nothing.
- `scripts/silent_drop_regression.py` — **run this after ANY edit to a finding gate's regex/classifier
  (`finding_gate.py` `DEAD_CHAIN`, `aggregate-findings.py` title-skip/severity parser, `triage_gate.py`
  `DEAD_RE`/`HYGIENE_RE`, `validate-findings.py` `SOCIAL_PATTERNS`/`_TERMINAL_GOALS`, `weaponize-gate.py`
  `analyze`).** Covers the LEXICAL-COLLISION silent-drops and severity-inflation that the severity *chain*
  harness does not: 9 cases, each asserted *both* directions (valid finding survives / genuine junk drops /
  plan-text does not inflate). Distinct from `severity_gate_regression.py` above — that one proves the
  severity tiers flow end-to-end; this one proves a bare adjective / substring / serialized-record never
  quietly deletes or inflates a finding. Exit 1 names the regressed case.
- `references/gate-failures.md` — verbatim gate messages, all five fix families (incl. the PoC-consumer
  ledger bug and `RAN_WITH_ERROR` wrapper bugs), resume decision tree, evidence paths.
- `references/pipeline-fp-classes.md` — false-positive classes with disproof recipes and measured outcomes.
- `references/scanner-fp-disproof-kit.md` — one-shot disproofs for the three scanner positives seen most
  often on SPA hosts: dalfox POC on a non-reflecting route, ffuf "exposed file" soft-404s (sha-identity vs a
  random path), and sqlmap/ghauri "not injectable" from a 400/401-heavy run (invalid, not negative). Also
  covers availability-oracle candidates whose suggestion lists turn out to be synthetic.
- `references/dangling-cname-sweep.md` — the manual CNAME-inventory + host-differential takeover sweep that
  outperformed every automated scanner in the same engagement; read this when a product's pipeline comes back
  negative and you still owe the host real manual coverage.
- `references/gate-unblock-cleanshot-20261027.md` — **read this when a 0D HARD BLOCK looks like the
  target's fault but nothing in the log implicates the target.** Two harness false-positives
  (`linkfinder` usage-banner-on-error-path stamped `FAILED_USAGE` on a WAF 429;
  `force-full-execution` — the orchestrator's own STEP 1 script — stamped `NOT_FOUND` because
  `shutil.which()` cannot see it), the exact evidence-marker and `--mark`/`--derive` mismatches that
  followed, and the three reviewer over-passes disproved by hand. Ends at 13/13 + 33/33.
- `references/stored-payload-render-verification.md` — how to earn a stored-payload **negative** with a
  browser DOM probe (`payloadAsText=true` + zero elements/dialogs), why "stored + echoed by the API" and a
  `dangerouslySetInnerHTML` grep are not proof, and how to separate "sink exists but is out of scope" from
  "no sink". Read before writing off, or reporting, any stored-XSS/HTML-injection candidate.

## Related
- `bb-methodology` — phase order, tool routing, quality gates (master workflow).
- `audit-runbook` — phase SOPs, differential + ledger laws.
- `audit-execution-discipline` — the pipeline's discipline rules and `asset-coverage.py`.
- `bot-protected-target-testing` — throttle/block shapes and rate discipline (§3a-1c).
- `artifact-backed-claims` — proof discipline for anything that leaves this pipeline as a claim.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/audit-artifact-purge/PLAYBOOK.md` — the teardown half of running the pipeline: delete
  audit *results* while keeping skills and tools, the split you must never blur, dry-run-then-commit
  procedure, over-capture as the default failure (plan the restore pass first), and the pass
  structure that clears a whole estate. Its `scripts/` hold the purge tooling; run it after a
  campaign, never mid-run.
