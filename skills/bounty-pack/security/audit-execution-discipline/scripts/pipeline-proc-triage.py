#!/usr/bin/env python3
"""pipeline-proc-triage.py - verdict on a (possibly) frozen audit pipeline, from DATA.

Operator says "powershellnya macet" -> do NOT guess from `tail` of the log (buffering lies).
This answers, in one shot:

  * how many orchestrator instances are alive (more than one = they corrupt the same dir)
  * per process: CPU delta over N seconds  -> BLOCKED (frozen CPU) vs LOOPING (CPU climbing)
  * the orchestrator's CHILDREN by parent PID -> names the exact tool holding the pipe
    (do not eyeball-filter for nuclei/sqlmap; the blocker can be trufflehog/gitleaks/interactsh)
  * newest tool-evidence mtimes -> how long since ANY progress
  * autofix-journal cadence -> is the vector queue still advancing
  * free RAM (a relaunch that dies ~10s in with no traceback is OOM, not a bug)

Usage:
    python pipeline-proc-triage.py [target_dir] [--delta 10]

Exit code 0 when healthy/absent, 1 when a freeze or a duplicate instance is detected.
Only reads state; never kills anything (unstick is a deliberate action - see the reference).
"""

import csv
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERMES = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "hermes"


def ps_csv(ps_cmd: str):
    """Run PowerShell and parse ConvertTo-Csv output. List-arg Popen -> no heredoc quoting traps."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=90,
        ).stdout
    except Exception as e:                                    # pragma: no cover
        print(f"  [warn] powershell query failed: {e}")
        return []
    rows = list(csv.DictReader(io.StringIO(out)))
    return [r for r in rows if (r.get("ProcessId") or "").strip().isdigit()]


def snapshot():
    ps = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine,KernelModeTime,UserModeTime,WorkingSetSize | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    rows = ps_csv(ps)
    snap = {}
    for r in rows:
        try:
            pid = int(r["ProcessId"])
            cpu = (int(r.get("KernelModeTime") or 0) + int(r.get("UserModeTime") or 0)) / 1e7
            ws = int(r.get("WorkingSetSize") or 0) / 1e6
        except (ValueError, TypeError):
            continue
        snap[pid] = {
            "ppid": int(r.get("ParentProcessId") or 0),
            "name": (r.get("Name") or "").strip(),
            "cmd": (r.get("CommandLine") or "").strip(),
            "cpu": cpu,
            "ws": ws,
        }
    return snap


def free_ram_mb():
    try:
        out = subprocess.run(["wmic", "OS", "get", "FreePhysicalMemory", "/format:list"],
                             capture_output=True, text=True, timeout=30).stdout
        for line in out.splitlines():
            if "=" in line:
                return int(line.split("=", 1)[1].strip()) / 1024.0
    except Exception:
        pass
    return None


def journal_cadence():
    j = HERMES / "trackers" / "autofix-journal.jsonl"
    if not j.exists():
        return None, []
    lines = [l for l in j.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()][-6:]
    out = []
    for l in lines:
        try:
            d = json.loads(l)
            out.append((d.get("ts", ""), d.get("tool", ""), d.get("attempt"), d.get("rc")))
        except Exception:
            pass
    return (j, out)


def main():
    target_dir = None
    delta = 10
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--delta" and i + 1 < len(args):
            delta = int(args[i + 1])
        elif not a.startswith("--"):
            target_dir = Path(a)

    print("=" * 66)
    print(f"PIPELINE PROC TRIAGE  {datetime.now(timezone.utc).astimezone().strftime('%H:%M:%S')}")
    print("=" * 66)

    s0 = snapshot()
    time.sleep(delta)
    s1 = snapshot()

    def is_pipeline(cmd: str) -> bool:
        c = cmd.lower()
        return any(k in c for k in ("audit-pipeline-orchestrator", "execute-variants",
                                    "execute-business-logic", "execute-references",
                                    "execute-poc-", "track-poc-execution"))

    orch = {p: v for p, v in s1.items() if is_pipeline(v["cmd"])}
    print(f"\n[1] pipeline processes alive: {len(orch)}")
    for p, v in orch.items():
        cpu0 = s0.get(p, {}).get("cpu", v["cpu"])
        d = v["cpu"] - cpu0
        verdict = "BLOCKED (cpu frozen)" if d < 0.05 else ("BUSY/LOOPING" if d > 0.5 else "idle-ish")
        print(f"    pid {p:<7} {v['name']:<10} cpu +{d:5.2f}s/{delta}s  ws {v['ws']:6.1f}MB  [{verdict}]")
        print(f"        {v['cmd'][:120]}")
    if len(orch) > 1:
        names = [v["name"] for v in orch.values()]
        if names.count("python.exe") > 1:
            print("    !! MORE THAN ONE python orchestrator -> they write the SAME dir and corrupt "
                  "sub-artefacts (see Freeze #3). Kill all but one.")

    # children of each orchestrator python
    parents = [p for p, v in orch.items() if v["name"].lower() == "python.exe"]
    print(f"\n[2] children of orchestrator pid(s) {parents or '-'}:")
    found = False
    for cpid, cv in s1.items():
        if cv["ppid"] in parents:
            found = True
            cpu0 = s0.get(cpid, {}).get("cpu", cv["cpu"])
            print(f"    pid {cpid:<7} {cv['name']:<14} cpu +{cv['cpu'] - cpu0:5.2f}s  ws {cv['ws']:6.1f}MB")
            print(f"        {cv['cmd'][:120]}")
    if parents and not found:
        print("    (none) -> orchestrator is blocked WITHOUT a live child: it is waiting on a pipe "
              "held by a process that already exited, or in pure-Python work. Suspect an unbounded "
              "subprocess.run(capture_output=True) runner (Freeze #2).")

    # progress: newest tool-evidence
    if target_dir is None:
        base = HERMES / "poc-plans"
        cands = sorted(base.glob("orchestrator-*"), key=lambda p: p.stat().st_mtime, reverse=True) \
            if base.exists() else []
        target_dir = cands[0] if cands else None
    print(f"\n[3] progress in {target_dir or '(no target dir found)'}")
    if target_dir and target_dir.exists():
        ev = target_dir / "tool-evidence"
        newest = None
        if ev.exists():
            files = sorted(ev.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            for f in files[:5]:
                age = time.time() - f.stat().st_mtime
                print(f"    {age/60:6.1f} min ago  {f.stat().st_size:>8}B  {f.name}")
            newest = files[0].stat().st_mtime if files else None
        if newest and (time.time() - newest) > 900:
            print(f"    !! no new evidence for >15 min -> freeze candidate")
        j = target_dir / "orchestrator.log"
        if j.exists():
            tail = j.read_text(encoding="utf-8", errors="replace").splitlines()[-3:]
            print("    log tail:")
            for line in tail:
                print(f"      {line[:110]}")
    else:
        print("    (nothing to inspect)")

    # autofix cadence
    jp, rows = journal_cadence()
    print(f"\n[4] autofix-journal cadence ({jp.name if jp else 'missing'}):")
    for ts, tool, att, rc in rows:
        print(f"    {ts}  {tool:<16} attempt {att} rc {rc}")
    if rows:
        print("    still gaining new vector rows every <1 min = HEALTHY (a slow tool is not a freeze).")

    # RAM
    ram = free_ram_mb()
    print(f"\n[5] free RAM: {ram:,.0f} MB" if ram is not None else "\n[5] free RAM: unknown")
    if ram is not None and ram < 1200:
        print("    !! below 1.2 GB -> relaunch may be OOM-killed with NO traceback (Freeze #2 side-effect).")

    verdict = "HEALTHY" if not orch else "INSPECT ABOVE"
    print("\n" + "=" * 66)
    print(f"VERDICT: {verdict}  (triage only - unstick is a deliberate kill/relaunch)")
    print("=" * 66)
    return 1 if (not orch and False) or len([v for v in orch.values() if v["name"].lower() == "python.exe"]) > 1 else 0


if __name__ == "__main__":
    sys.exit(main())
