# Pipeline operations — backgrounding, stalls, workspace hygiene
Measured on one full web run (0A→0C), 2026-10-14.

## 0. Invocation gotchas (fail in the first 30 seconds)

- **`--scope` is an exact-host matcher, not a suffix matcher.** `--scope "gasunie.nl"` rejects
  the target itself: `❌ OUT OF SCOPE: www.gasunie.nl not in gasunie.nl`. Pass every variant
  explicitly, comma-separated: `--scope "www.gasunie.nl,gasunie.nl,*.gasunie.nl"`. The apex
  and `www.` are different strings to the matcher.
- **No `--help`.** The first positional arg must be the target URL; `--help` is parsed as a
  target and dies with `target tidak dikenali tipe-nya`. Read the `add_argument`/usage block
  from the script source instead (`grep -n "add_argument" audit-pipeline-orchestrator.py`).
- State persists per-target under `~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<slug>/`;
  a failed invocation still writes state, and re-running the fixed command resumes cleanly.

## 1. Background the orchestrator with a timeout that fits a real run

Observed wall-clock for one target: 0A ~3 min · 0B ~17 min (subfinder/httpx/dork-recon/amass/
naabu/katana/gau/waymore) · force-full-execution ~28 min · payload variants ~43 min ·
DOM-XSS ~20 min. **≈ 1h50m total.**

`timeout 3000` killed the run mid-variants and cost a rework cycle. Launch with
`timeout 7000`+ (or none) and let the notification tell you when it ends.

## 2. RESUME MODE is real — re-run the identical command

Log confirms both behaviours:
```
RESUME MODE: already completed ['0A','0B'] — skip those
STEP 1: SKIP force-full-execution (force-state sudah complete)
```
So a killed run costs only the phase it died in. Do not restart from a clean directory.

## 3. STALL-WARN is a warning, not a kill

```
[STALL-WARN] orchestrator: no step progress for 927s (last phase 0A, pid=18044)
             - still running, not killed. Unblock: python toolguard.py unblock --pid <pid>
```
It names the *watcher's* phase, which can lag reality — do not read "last phase 0A" as
"the run is stuck in 0A".

## 4. Diagnose the blocking CHILD, never restart the parent

Walk the tree (`psutil.Process(pid).children(recursive=True)`) and read `age` + `cpu_percent`:
the guilty process was a variant tool at `age≈764s, cpu=0.0%`. Killing that child (and its
`cmd.exe` wrapper) let the runner advance and record the tool as NO RESULT.

A hung variant tool may also be **re-spawned in a loop** by the runner — one kill is not
enough; watch for respawn over ~2 minutes before concluding you fixed it. When it respawns
immediately, stop killing and remove the blockage so the runner gets an instant failure
instead (only a fix that produces an honest `NOT_FOUND`/`NO RESULT` record — never a stub that
prints fake output).

## 5. Evidence lags the log

`tool-evidence/` kept filling (17 → 19 → 20 → 25 → 28 files) while `orchestrator.log` still
showed the same STEP line for many minutes. For liveness, watch **file count/mtime** in the
evidence directory, not log silence. (`STALL-WARN` firing during that time was noise.)

`PHASE_LOG.md` is worse: it freezes after `PHASE 0A — SETUP COMPLETE` and never gets another
line — two full 0B/0C runs left it untouched. Never diagnose progress from it; the truth is
`asset-coverage.json` (per-asset USED/N-A/NOT_RUN) + newest file mtime in the run directory.

## 6. Variant failures are recorded, not backfilled

The runner emits:
```
❌ Variants FAILED — flagged for REWORK: [tool_router] auth-bypass ->
   FAILED-UNCLASSIFIED:  (NO RESULT - record as such, do NOT substitute curl)
```
Honour it verbatim in the coverage section: `NOT RUN / NO RESULT`, with the reason. The gate
refuses a "clean" claim built on a tool that produced nothing.

## 7. One workspace, one tree (Windows/MSYS twin directories)

An engagement directory very often exists **twice** — once with the path segment that carries
a space (`D:/data hermes/<target>/`) and once without (`D:/data/hermes/<target>/`), because
`write_file` paths and shell paths get typed/normalised differently. Symptoms: a script you
just wrote is "not found", evidence files split across two directories, `cat` seeing files that
`ls` in the canonical dir does not.

Discipline:
1. After the **first** write into a new engagement dir, `ls -d` **both** candidate paths.
2. Pick the one matching the pool/engagement convention as canonical; immediately
   `mv` the stray files over and `rmdir` the twin.
3. Re-check after every `write_file` whose `resolved_path` you did not read; the twin re-forms
   silently.
4. Run scripts with `cd "<canonical>" && python3 <relative-name>` so no spaced path is ever
   passed as an argument (a spaced arg gets mangled between shell and Windows Python).

## 8. Redirected Python output is block-buffered

`python3 script.py > log` may show only a handful of lines for many minutes, and a
`timeout` kill **discards the buffer** — a killed run looks like it did almost nothing.
Use `python3 -u`, or tail the artefact files instead of the stdout log.

## 9. Dead parent across sessions — detect, then re-run identical command

The orchestrator run usually outlives its chat/CLI session; when you come back later the
parent may be **gone** (its `process` entry vanished, `run-meta.json`'s `pid` absent from
`tasklist`). Detection in 3 checks:
1. `process list` empty for the session that launched it (a new session never inherits it).
2. `tasklist /FI "PID eq <pid from run-meta.json>"` → "No tasks are running".
3. Newest mtime in `orchestrator-<slug>/` frozen minutes ago (compare `asset-coverage.json`,
   `tool-evidence/`).

Fix = **relaunch the identical command** (resume mode, §2); state picks up where it stopped.
Two things that look alarming but are normal on relaunch:
- `⚠️ RAM bebas <1.2 GB` warning — reclaim first with `wsl --shutdown` (~0.5-1 GB), the
  pipeline historically gets OOM-killed by Windows with no traceback.
- `❌ GATE FAILED (attempt 1)` at 0D followed by `🔁 REWORK (generic): re-running full force
  execution` — that's the built-in auto-rework loop doing its job, not a crash. Read the
  3 named failures, let it run; report only after the gate turns green.

## 10. Which files prove a job FINISHED — read the tracker, not the file listing

This pipeline does **not** write `report.md`, `summary.json`, `guard-result.json` or `guard.py`
into the run directory. Their absence is normal and proves nothing. Measured 2026-10-15: a report
listed all four as `MISS` across every run directory and it was read as *"0 jobs ever completed"* —
wrong; **12 runs had completed**. Never answer "is this job done?" from a directory listing.

Authoritative completion evidence, in order:

1. `~/.chiper/skills/bounty-pack/trackers/force-state-<slug>.json` → `"status": "complete"` = the C1
   (force-full-execution) completion marker. It is hardened: `_force_state_complete()` cross-checks
   the marker against `tool-evidence/`, so a marker whose evidence was quarantined no longer counts.
2. `~/.chiper/skills/bounty-pack/trackers/phase-watch-state.json` → per run
   `"orchestrator-<slug>": { "phase": "0A"…"0F", "complete": bool, "last_heartbeat_ts": … }`.
   `phase == "0C"` + `complete: false` is the *normal* mid-run state. `last_heartbeat_ts`
   (`ls -l --time-style=full-iso` on the run dir, newest mtime) is the liveness signal.
3. `poc-plans/orchestrator-<slug>/` = the run's artifacts; `variants/*.txt` +
   `tool-evidence/*.txt` show which payload vectors actually produced evidence.

Real state on this host (2026-10-15): 12 runs at `0F`/`0A` complete, 9 at `0C` incomplete — of
which 5 already had `force-state status: complete` and were merely held at 0C by variant execution.
Also check for the *inconsistent* case: `complete: true` with no artifacts. None existed here, which is
the hardening in `_force_state_complete()` working — say that rather than assuming it is fine.

## 11. The orphan reaper killed the WRONG pid (WMIC column order)

`audit-pipeline-orchestrator.py` reaps parentless tool processes before each run. The original parser
was:

```python
r = _sp.run(["wmic", "process", "where", f"name like '%{name}%'",
             "get", "processid,parentprocessid"], capture_output=True, text=True)
for ln in r.stdout.splitlines():
    parts = ln.split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        pid = int(parts[0])            # <-- WRONG: parts[0] is ParentProcessId
```

**WMIC returns its columns in ALPHABETICAL order, so `ParentProcessId` comes FIRST.** Verified
directly on this host:

```bash
wmic process where "name like '%dalfox%'" get processid,parentprocessid
#   ParentProcessId  ProcessId
#   17816            15344
```

So the reaper `taskkill`ed the parent id and logged `✓ reaped N orphaned tool process(es)` while the
real orphan survived untouched. Measured 2026-10-15: `dalfox.exe` PID 15024 held **700 MB / 312 threads
for 2 h** after its `cmd.exe` parent was already dead, with `xss-stored-xss.txt` never written.

Fix (applied 2026-10-15, backup `audit-pipeline-orchestrator.py.bak_reaperfix_*`): parse
`wmic ... /format:list` and map keys **by name**, then only kill a process whose parent is **no longer
alive** — a live parent means a run in progress, which must never be reaped.

Two more traps found while writing the fix, both silently produce PID 0:

- **`splitlines()` on WMIC output is wrong.** WMIC separates fields with `\n\n` and records with more
  newlines, but its line ending is `\r\r\n` — `splitlines()` oversplits it. Measured: `2407` lines → only
  `720` carried `=`, and only `240` PIDs parsed. **Split on `"\n"` and `strip()`.**
- **A blank line is NOT a record separator** — WMIC puts a blank between *every field*. Flushing the
  record on a blank yields one-key records with no `ProcessId` (`int(...) if isdigit() else 0` → PID 0).
  Start a new record when the **first key of a record (`Name`) repeats**, not on a blank.

Verification pattern that catches all three (run the REAL block out of the file, not a copy, with `taskkill`
stubbed): `scripts/audit-orphan-reaper-verify.py`. Expected output `records parsed == live pid set`
(this host: `240 == 240`, sanity PASS) and the live tool under execution must appear as `parent=ALIVE`
→ spared, `WOULD KILL pids: []`.

## 12. A hung tool blocks 0C forever — two gates that both refuse to kill

Two deliberate design choices in this repo combine into an unbounded block. Do not "fix" either — they are the
operator's policy. The lever is `toolguard.py unblock`, and it is operator-driven only.

| Gate | Rule | Consequence |
|---|---|---|
| `toolguard.py` | *"run a tool to COMPLETION, warn (never silently kill) when it stalls"* | a hung tool is **never** killed by time |
| `execute-variants.py` | `_TOOL_CAP = None` + `timeout_cap=None` **hardcoded** at the call site | **no per-tool timeout at all** |

`_TOOL_CAP`/`_BUDGET` default to `None` and orchestrator invokes without `--tool-cap`
(`execute-variants.py <target> --target-dir … --max-variants 100 --rate 3`), so a tool that hangs while
holding the output file **blocks 0C with no timeout and no warning**.

**Distinguish a HANG from "slow" before touching it.** Measured 2026-10-15 on one dalfox invocation:

| signal | hang | slow-but-working |
|---|---|---|
| ticks in `trackers/tool-stalls.jsonl` | 2 → 8 → 13 (`stalls: N` repeating) | plateaus |
| output bytes to its `-o` file | stays `0`, file never created | grows |
| thread count | **226 → 325 → 312**, never drops | stable |
| RSS | 522 → 708 MB, climbing | stable |
| CPU | tiny (~34 s over 75 min) | meaningful |

**A second invocation of the same tool starting while the first is still running is a liveness signal** — the
runner moved on and invoked the tool again, so the orphaned one is provably not being waited on.

Unblock (the sanctioned lever, never a code change):

```bash
python ~/.chiper/skills/bounty-pack/toolguard.py unblock --pid <wrapper-pid>
# equivalent: taskkill /F /T /PID <wrapper-pid>
```

Kill the **wrapper** (`cmd.exe`) and its child together (`/T`), not the child alone, or the runner stays blocked
on a pipe nobody will close. Then confirm the pipeline advanced: a NEW tool pid appears and the run dir gets a new mtime,
instead of waiting for a log line. Measured: after unblocking, `execute-variants.py` advanced and started the next
vector's dalfox within ~40 s.

`tool-stalls.jsonl` is the quickest stall census — one line per tick with `pid`, `silent_s`, `stalls`, and the full
`cmd`. `Get-Content … | Select-String '"pid": <pid>'` counts how many times one invocation stalled; counting distinct
`pid` values shows whether it is one hang or a systemic pattern (this host: **10 distinct dalfox invocations, up to 13 ticks**).

Do not read a stall as "the job is broken" and do not read a clean-looking run as "finished" without §10. Report the
vector and the recorded status as-is, including `NOT RUN / NO RESULT` for a vector killed mid-run.

## 13. Stopping stalled jobs and resuming only the selected ones

The operator's request shape here is a **whitelist again**: *"yang jalan harusnya hanya A dan B, yg lainnya
stop dan kill aja."* Treat it as a pass/fail checklist and print the result per target.

### 13.1 Before declaring anything "stopped", prove nothing will resurrect it

Three independent mechanisms can bring audit work back. Check all three — a stall is usually *already*
dead (killed by RAM pressure days ago), so the real work is making sure it **stays** dead:

| mechanism | how to check | what it means |
|---|---|---|
| Scheduled Task | `Get-ScheduledTask` filtered on `audit\|pipeline\|orchestr\|bounty` + `Actions.Execute -match 'audit-pipeline\|orchestrator'` | self-healing relauncher; needs `Disable-ScheduledTask` |
| hermes cron — **watchdogs** | read `~/.chiper/skills/bounty-pack/cron/jobs.json`, inspect each `prompt`/`script` | **monitors that ALERT, they do not relaunch the pipeline** |
| deep-audit arm | `python scripts/deep-audit-mode.py status` | an armed job keeps getting nagged until gated; `disarm <url>` to stop |

Measured 2026-10-15: the three recurring pipeline-related cron jobs on this host are
`unified_watchdog_v2.py` (5 min), `phase-watch.py` (3 min) and `deep_audit_watchdog.py` (4 h). All three *report*;
none launches `audit-pipeline-orchestrator.py`. Stating that explicitly is what makes "stopped" credible — say
*"no scheduled task and no cron relaunches it"* only after reading `jobs.json`, not from the job names.

Disarm the arms you are stopping, and **list the arms still active** to prove the kept targets survived:

```bash
python scripts/deep-audit-mode.py disarm https://<stopped-target>
python scripts/deep-audit-mode.py status      # kept targets must still appear
```

### 13.2 Verify "0 live process" by cmdline slug, not by process name

The orchestrator runs as `python.exe`, so a name filter proves nothing. Match the **target slug** in the
command line, and expect an empty result when the job already died days ago:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -and $_.CommandLine -match 'safeguard|aekktn|netplus_tv|gkb|caius|apnic|atg' } |
  Select-Object ProcessId, Name, @{n='Cmd';e={$_.CommandLine.Substring(0,[Math]::Min(120,$_.CommandLine.Length))}}
```

Reporting *"already down before the instruction; stop is a no-op + disarm so it stays down"* is the honest
answer — do not claim a kill you did not perform.

### 13.3 Trust the pipeline phase tracker over the watch state when resuming

Two files disagree, and the more advanced one is correct:

| file | field | meaning |
|---|---|---|
| `trackers/audit-pipeline-<slug>.json` | `current` + `completed_phases` | what the orchestrator actually finished |
| `trackers/phase-watch-state.json` | `phase` + `complete` | the **watcher's** view, can lag |

Measured 2026-10-15: `www.gasunie.nl` had `current: "0D"` with `completed_phases: [0A,0B,0C]` in
`audit-pipeline-*`, while `phase-watch-state` still said `phase: "0C", complete: false`. Resuming from the
watcher's value re-runs finished work; resume from `current`.

### 13.4 Resume = relaunch the identical command, with the tracker's `--tech`

Pass the tech string from `audit-pipeline-<slug>.json` (`run-meta.json` can hold an empty string for the same
run — `www.gasunie.nl` had `tech: ""` there but `"general"` in the tracker). Background it and let the
notification fire:

```bash
# background=true, notify=true — no nohup/& (the terminal tool refuses shell backgrounding)
python audit-pipeline-orchestrator.py https://<target> --tech <tracker-tech> --scope <explicit-hosts>
```

A resumed run re-hits `❌ GATE FAILED (attempt 1)` → `🔁 REWORK` on its first gate pass. That is §9 normal, not
a failure — do not "fix" it.

### 13.5 Deciding tool-vs-pipeline for a hang: reproduce it standalone

§12 lists the hang signals. The step that settles *whose* bug it is: run the exact failing command **on its own,
outside the pipeline**, with a short `timeout`. If it hangs identically with no pipeline attached, the tool is
the problem and the fix is manifest-level (drop/replace it for that target), not an orchestrator patch.

```bash
timeout 40 "<tool.exe>" url "<target>" --skip-bav -o "<scratch>/out.txt"   # no output + timeout => tool hangs
```

Measured 2026-10-15: `dalfox url "https://yandex.fr/?" --skip-bav -o …` hung past 40 s standalone with
**zero output bytes**, reproducing the in-pipeline hang (3 invocations: 312/325/— threads, 0-byte output file).
Run this before proposing a code change to the pipeline.

### 13.6 Report format for a stop/resume pass

Print the whitelist as a table with `status before → action → result` per target, then a separate
`running now` list with PID + start time for the kept targets. Include the disarm lines and the arm status.
Never report a stopped job without also showing that the kept ones are still alive.

### 13.7 Empty PoC ledger = legitimate result, NOT a gate failure (2026-10-15)

Measured on `www.gasunie.nl` (static-site, no tech-matched PoC repo) and `yandex.fr` (exfil
gadget text, same). `execute-poc-variants.py` and `execute-poc-techniques.py` read
`poc-execution.json`, find **zero matched repos** and honestly write `[]` (2 bytes). Three
separate validators then treated that empty file as a failure, so a valid run could never finish:

| File | Old rule | Fix (all in ONE logical change — the layer contract) |
|---|---|---|
| `verify-tool-usage.py` CHECK 8 (C5) | `[]` → FAIL | accept `[]` only when C4 proved no usable repo |
| `verify-tool-usage.py` CHECK 11 (C6b) | `[]` → FAIL | same gate |
| `audit-checkpoint.py` C5 | `< 50 bytes` → FAIL | same gate |
| `asset-coverage.py` `--phase` (CHECK 12) | `bool(pvc)` → NOT_RUN | marker check skipped when `not entries and _no_poc` |
| `asset-coverage.py` quality post-pass | empty ledger → NOT_RUN | skip downgrade under the same proof |

**Proof of "no usable repo"** = `poc-execution.json` exists AND contains at least one entry AND
**no** entry has status `EXECUTED`. That covers `NO_POC_MATCHED`, `NO_ENTRY_POINT` and
`PLANNED_NON_REQUIRED`. Do NOT accept empty ledgers without this proof — a time-skip or a
listed-but-never-run repo must still FAIL (that is the anti-fabrication intent).

**Orchestrator consequence:** the rework dispatcher in `audit-pipeline-orchestrator.py` had no branch
for `"poc-variant-usage.json empty"` / `"poc-techniques-usage.json empty"`, so it fell through to
`🔁 REWORK (generic): re-running full force execution` — which **never re-runs C4/C5/C6b**, so the gate
failed identically on attempts 1/3, 2/3, 3/3 and HARD-BLOCKED with `DO NOT GENERATE REPORT`. The 0C
executors (`skip_c4/c5/c6b`) only test `poc-*.json exists`, never the content — that asymmetry between
the executor (exists) and the gate (content) IS the bug.

**Wired check order:** pass `--phase` on `asset-coverage.py` to trigger `check()`; `--derive` only
**writes** the ledger and does not validate it. Stale ledgers (written before a fix) must be re-derived with
`asset-coverage.py <dir> --derive` before re-running the gate, otherwise `check --phase` keeps reporting
`NOT_RUN` from the old file.

**Three gates, not one.** Fixing CHECK 8/11 in `verify-tool-usage.py` is necessary but NOT sufficient — the
SAME empty-ledger rule is implemented independently in three files, and each one fails the run on its own:

| gate | runs at | check |
|---|---|---|
| `verify-tool-usage.py` | 0D (`STEP 1.5`) | CHECK 8 (C5) + CHECK 11 (C6b) |
| `asset-coverage.py --phase` (CHECK 12) | 0D | `bool(pvc)` / `bool(ptc)` per asset |
| `audit-checkpoint.py` | **post-0F final gate** | C5 `pv.stat().st_size >= 50` |

Measured 2026-10-15: after fixing only `verify-tool-usage.py` the gate went `3 failures → 1`
(`❌ CHECK 12 FAILED: uncovered assets in ['0C']`); after `asset-coverage.py` the 0D gate printed
`RESULT: ALL 13 CHECKS PASSED ✅` **and the final gate still failed** with
`❌ C4 required PoCs: 0 executed / ❌ C5 PoC variants: 0 repos processed`. Fix all three (plus
`--derive` to refresh the stale ledger) in one pass, then run **both** `verify-tool-usage.py <dir>` and
`audit-checkpoint.py <dir> --phase all` before reporting a fix as done.

## 14. Long-run durability, and the `force-state` skip that hides missing 0C work

Measured on the 2026-10-15 gasunie + yandex runs.

### 14.1 A long run must not depend on the agent session's process tree

A run launched from a `terminal` call can be **reaped together with the session's process tree when that call
ends**, and the result is indistinguishable from a crash: the orchestrator is simply gone, there is no traceback, the
tracker keeps its last phase, and the run directory stops growing.

Measured 2026-10-15: the yandex orchestrator was live at 03:24 (`impact-verify.py` child running, heartbeat
current) and was gone by 03:28:56 — the same moment a long `sleep` in the agent's own terminal call reached its
timeout. Nothing landed in `tool-stalls.jsonl`; no error line was printed; `impact-verification.json` was never
written though every input it needs already existed. §9's three checks do not catch this, because the parent was never a
separate session.

Discipline:
- **Verify liveness with an effect, not a sleep.** One `Get-CimInstance Win32_Process` filtered on `CommandLine`
  tells you whether the run is alive; a long blocking sleep tells you nothing and risks killing it.
- After any agent-side timeout, re-check the process list **before** reporting progress or failure.
- When a run did die mid-phase, resume from the tracker's `current` (§13.3) and re-run **only the missing steps**
  (14.2) instead of relaunching everything.
- Read the artifacts you already have to find the resume point: `impact-verification.json` missing while
  `rce-verification.json` exists means it died **inside** impact verification.

### 14.2 `force-state: complete` SKIPs the WHOLE 0C block — including C4/C5/C6b

A `force-state-<slug>.json` with `"status": "complete"` makes a resume print

```
STEP 1: SKIP force-full-execution (force-state sudah complete)
  SKIP sub-fase (verified fresh + this target): C2=Y C3=- C4=- C5=- C6=- C6b=-
PHASE 0C-C2d: Executing IMPACT verification (6 classes)...
```

The marker is a **C1 claim, not proof that every 0C sub-step ran**. When C4/C5/C6b artifacts do not exist
(the run that wrote the marker died before them, or they were never applicable) the resume **silently skips** them and
the final gate fails on artifacts nobody will write:

```
❌ PHASE 0E: FINDINGS (0/4 checks)      ❌ PHASE 0F: REPORT (0/1 checks)
TOTAL: 12/33 checks passed
```

Check the artifacts, not the marker:

```bash
for f in poc-execution.json poc-variant-usage.json poc-techniques-usage.json; do
  printf '%-28s %s\n' "$f" "$([ -f "$f" ] && stat -c%s "$f" || echo MISSING)"; done
```

Remedy, in order of preference:
1. Run the missing steps directly (`impact-verify.py`, then resume so C4 → C5 → C6b run), or
2. Delete the stale `force-state-<slug>.json` only when you intend a full C1 → C6b re-execution, and
   re-derive the ledger afterwards (`asset-coverage.py <dir> --derive`).

Never report "0C complete" from the marker alone.

### 14.3 `impact-verify.py` is the long pole — measure it, do not call it a hang

`impact-verify.py` (phase `0C-C2d`) is invoked unconditionally: the orchestrator has **no skip flag** for it
(`if iv_ledger.exists()` is the only guard). It probes 6 classes, and the time-based ones wait out their own
windows on purpose — `blind-sqli` alone is `baseline + 9 payloads + 1 control` at `--timeout 20` per candidate with
`--limit 12`.

Measured 2026-10-15 on `yandex.fr`: still running at **40+ min in this single step** (never reached completion in
that run), and it was **working, not hung**:

| signal (§12 table) | reading |
|---|---|
| CPU | 26.2 s → 28.9 s over ~3 min (advancing) |
| TCP connections | `Established <target>:443` → `SynSent <target>:443` (rotating = new requests) |
| `impact-verification.json` | not yet written — written once at the end |

So: do not kill it as a hang, and budget for it. On a latency-heavy production target this one step can cost an
hour-plus before any of C4/C5/C6b have run, which is why §14.1 matters.

## 15. Stop-everything, then rerun only what errored (mass-wipe recovery)

Operator request shape: *"Gasunie jg stop, kill aja, nnti sy ulang, skr semua proses audit stop dl"* —
followed later by the terse *"Ulangi yg eror dan perbaiki yg stall"*. Treat "stop all" as class-wide:
kill every audit producer, keep every non-audit process (powershell / hermes / explorer / MsMpEng / the
user's own chrome), then answer with ONE status block, not a narrative.

### 15.1 Symptom: run directories gone while the tracker still claims success

Measured 2026-10-17: `poc-plans/` came back with **0 directories** (all 44 `orchestrator-*` gone) while
`trackers/phase-watch-state.json` still listed `complete: true` for 19 runs. Consequences:

- The two trees are **independent**. `trackers/` survives `poc-plans/` being emptied, so a green tracker
  after a wipe is a *claim whose evidence no longer exists*. `_force_state_complete()` cross-checks
  `force-state` markers against `tool-evidence/`, but there is **no equivalent guard** for
  `phase-watch-state.json` — verify manually.
- Do **not** attribute the wipe to your own stop operation. `taskkill` only touches processes. Check the
  date inside `_delete_log.txt` before citing it (on this host it was an older, unrelated run).

Quarantine stale claims — the house rule is *delete = `_QUARANTINE` + manifest*, so rename, never unlink:

```bash
SAFE=$(echo "$TGT" | sed -E 's#[/:]#_#g')     # https://yandex.fr/ -> https___yandex.fr_
for f in "trackers/audit-pipeline-$SAFE.json" "trackers/force-state-$SAFE.json" "trackers/$SAFE.json"; do
  [ -f "$f" ] && mv -f "$f" "$f.stale_wiped_$(date +%Y%m%d_%H%M%S)"
done
```

Without this a relaunch prints `RESUME MODE: already completed ['0A','0B'] — skip those` plus
`SKIP sub-fase … C4=- C5=- C6b=-` for artifacts that no longer exist, and 0C starts with no
`urls.txt`/`subs.txt` to work from.

### 15.2 Slug derivation — get it wrong and the pass writes into a fresh directory

| input | orchestrator dir | tracker basename |
|---|---|---|
| `https://www.safeguard.sh` | `orchestrator-www_safeguard_sh` | `https___www.safeguard.sh` |
| `https://yandex.fr/` | `orchestrator-yandex_fr_` | `https___yandex.fr_` |
| `https://caius.dev.netplus.ch` | `orchestrator-caius_dev_netplus_ch` | `https___caius.dev.netplus.ch` |

- **dir slug**: strip scheme, then `s#[^A-Za-z0-9]#_#g` (dots **and** slashes become `_`).
- **tracker slug**: only `s#[/:]#_#g` (dots are kept). The two differ — reusing one for the other
  silently targets a path that does not exist.

`templates/rerun-queue.sh` implements both plus the quarantine and the sequential loop.

### 15.3 Orphan detection must walk to the ROOT, not stop at the parent

A tool whose **immediate** parent is alive can still be orphaned. Measured 2026-10-17:

```
ffuf.exe 15260  age=12.2h  mem=914 MB
  ← bash 7264 (ALIVE) ← bash 27000 (ALIVE) ← 26012 DEAD   <- root orchestrator
  output path: orchestrator-finanzen_net/  MISSING
```

An `is-the-parent-alive?` check spares it (`parent=7264 bash.exe`), so it ran 12 h writing into a
directory that never existed. Second orphan signal: `amass` PID 18672 with parent `9332 DEAD`, 9 h old.

**Rule:** a scanner is orphaned if (a) any ancestor above its wrapper chain is dead, or (b) the output
directory it writes to does not exist. Immediate-parent-alive proves only that a *wrapper* survives, not
that a *consumer* does. Walk the chain to the root before deciding.

### 15.4 Rerun sequentially — parallel queues OOM this host

6 GB RAM: a queue of simultaneous runs makes Windows kill children with no traceback (§9). One target per
background process, wait for its exit, then the next. Progress evidence for the first target:

```
[13:57:39] ✅ PHASE 0A COMPLETE      <- not skipping phases, quarantine worked
[13:57:55]   urls.txt: 183 candidate URLs
```

`RAM free 1245 → 2060 MB` after killing the two orphans alone — orphan reaping is the cheapest RAM win
available before starting anything new.

