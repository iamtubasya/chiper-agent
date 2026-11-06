# Run-observation discipline — do not declare a run dead from a log tail

## CHECK ZERO — the exit sentinel settles it, always run this FIRST

The guidance below (mtime, artefact growth) is **heuristic and it failed again**. On
2026-10-08 a run was declared "dead at PHASE 0C-C6" from a 29-line mid-run sample; the
log actually reached 66 lines and ended in `=== EXIT 0 ===`. The user was told the
pipeline had failed, with a RAM diagnosis built on top, and the run had **completed
twice**.

So make the wrapper write a sentinel and read the sentinel:

```bash
# the launcher appends this; if the line exists, the run is FINISHED. Full stop.
grep -c '^=== EXIT' "$LOG"        # 0 = still running or killed; 1 = finished
grep -E '^=== EXIT' "$LOG"        # shows the exit code and timestamp
```

**If `=== EXIT` is absent the run has not finished** — it may still be working or may
have died. **If it is present, never call the run dead, no matter what the tail says.**
That one grep replaces the whole guessing game below. Make it check zero.

## The counter-evidence that was in hand and ignored

This is the part that matters. Mid-run the following were **observed and then
discarded** in favour of the log tail:

```
tools-usage.json         14 -> 26 entries   (grew DURING the "dead" window)
poc-variant-usage.json   37 -> 139 entries  (grew during the same window)
tool-evidence/           26 -> 37 files
```

Ledger and artefact files **growing is positive proof the run is alive and working**.
The rule stated further down — "evidence-on-disk growth outranks log text" — was
already written in this file, was already satisfied, and was still overruled by a
mid-run tail. Do not treat these as corroboration: they are **dispositive**. A
shrinking or static ledger plus no sentinel is a dead run; a growing ledger is a
live one, full stop.

## Why a mid-run tail lies

The runs were launched as:

```bash
python -u audit-pipeline-orchestrator.py <target> ... 2>&1 | tee -a "$LOG"
```

`tee` (and `capture_output=True` inside the orchestrator, which swallows every
child's stdout) buffers. The log therefore sits at its last flushed line for
**many minutes** while the run is working perfectly. Run-9's log showed
`STEP 1.4a: Executing PAYLOAD VARIANTS...` and nothing else — I checked mtime,
saw no growth over 20 s, and concluded the process had died. The notification
later showed the same run reaching 0D at 05:52 and hard-blocking at 06:00.

## The three checks, in order — all of them, before any conclusion

```bash
# 1. is a process actually alive?
MSYS_NO_PATHCONV=1 cmd /c "wmic process where \"commandline like '%orchestrator%'\" get processid"
#    (run this from bash, not cmd — the quoting differs)

# 2. is ANY output being produced? (mtime + size, not the tail text)
stat -c '%y %s' "$LOG"; sleep 30; stat -c '%y %s' "$LOG"

# 3. are artefacts appearing on disk for the step you think it is stuck on?
ls -lat "$WORKDIR/tool-evidence" | head
```

A live run can show a flat log while `tool-evidence/` gains files every minute.
Evidence-on-disk growth outranks log text.

## Never conclude from absence of a traceback alone

"No Traceback in the log" was taken as proof of an external kill. It is not: the
orchestrator **captures** child stdout/stderr and only logs its own lines, so a
child failing loudly can leave nothing at all in the parent log. Absence of a
traceback is absence of a traceback — nothing more.

## What the run's own completion message looks like

The reliable signal is the process exiting and the background-completion
notification firing. Wait for it, or poll `process(action='poll')` on the tracked
session. Only then read the log end-to-end, with `grep -E "PHASE|COMPLETE|GATE|RESULT|EXIT"`
to get the actual timeline in one screen — which is what finally revealed that the
run had gone 0A → 0C → 0D all along.

## Corollary for reporting

Do not tell the user "the host is out of RAM / the toolchain is broken" from a
mid-run observation. Either wait for the completion signal, or state the
observation with its uncertainty ("the log has not advanced in 30 s") instead of
promoting it to a cause. A wrong root cause is worse than "still investigating".

## "Show me the process" — the operator will ask, and a flat parent looks dead

Verbatim 2026-10-10: *"tunjukkan proses nya, jadi sy tahu ini tidak stuck"*. Reassurance is not an
answer. When asked, produce a **two-sample snapshot** (t0, then t1 ~15 s later) so the numbers move
on screen:

```
1. the process chain          bash -> python <orchestrator PID> -> <tool> PID (with WS_MB)
2. CPU delta between samples  for the ORCHESTRATOR and for the CHILD tool
3. artefact deltas            tools-usage.json size, tool-evidence/ file count, newest file mtime
4. log timestamps             last 3-4 lines, with their HH:MM:SS
```

**The trap that makes this look stuck: a parent blocked in `communicate()` shows CPU +0.00 s.** That
is normal and is *not* evidence of a stall — the parent is asleep while the child scans. Lead with the
**child** process, the growing artefact, and the advancing log timestamp; explicitly say why the
parent's CPU is flat, or the operator reads the flat number as the whole answer.

Single-instant sampling also lies the other way: `business-logic-usage.json` is rewritten on **every
vector append**, so a read mid-rewrite shows a stale size/mtime. Never judge from one sample — take
two, ≥15 s apart, and prefer monotone counters (entry count, file count) over byte size.

Give the operator a command they can run themselves rather than asking them to trust you:

```bash
while true; do date +%T; tail -n 3 "<run-log>"; sleep 5; done
tasklist | grep -iE "nuclei|sqlmap|ffuf|dalfox|nikto|wpscan|subjack|gitleaks|trufflehog"
```

## Background-completion notifications arrive for runs you already superseded

Killing a run and relaunching leaves the **old** tracked session to fire its own
`completed (exit code 1)` notice minutes later. Read it as a fact about *that* PID, never about the
current run. Check the live log tail / state file before reacting — several notices this session were
for runs stopped an hour earlier, and one `exit code 0` notice was the run that genuinely succeeded.
Corollary: when relaunching, keep one instance only. Two orchestrators on one `--target-dir` corrupt
the incrementally-written ledgers (see `unstick-frozen-pipeline-tool-loop.md`).
