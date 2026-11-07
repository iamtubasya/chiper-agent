#!/usr/bin/env python3
"""Verify the audit-pipeline orphan reaper WITHOUT killing anything.

Why this exists: the reaper in audit-pipeline-orchestrator.py silently killed the
WRONG pid for months (WMIC returns its columns in alphabetical order, so
`get processid,parentprocessid` puts ParentProcessId first). Every run logged
"reaped N orphaned tool process(es)" while the real orphan survived holding
hundreds of MB and hundreds of threads.

This script exec()s the REAL reaper block read out of the live orchestrator file —
never a re-implementation, which would pass while the file stays broken — with
`taskkill` stubbed, so it is safe to run any time.

Usage:
    python audit-orphan-reaper-verify.py [path/to/audit-pipeline-orchestrator.py]

Expected on a healthy box with one tool in flight:
    records parsed  : <N>
    live pid set    : <N>          (must EQUAL records parsed)
    sanity          : PASS         (100 < live pid set < 2000)
    WOULD KILL pids : []           (nothing orphaned)
    <tool.exe>  PID <n>  PPID <n>  parent=ALIVE   <- in-progress run protected

Failure signatures:
  - `records parsed != live pid set`, or PID 0 rows  -> parser is oversplitting
    WMIC output (needs split("\\n"), and must NOT flush the record on a blank line).
  - a running tool shown as `WOULD KILL`             -> reaper would kill a live run.
"""
import os
import re
import subprocess as _sp
import sys
import textwrap
from pathlib import Path

DEFAULT_ORCH = Path.home() / "~/.chiper/skills/bounty-pack/audit-pipeline-orchestrator.py"


def extract_reaper_block(src: str) -> str:
    """Pull the real reaper block out of the orchestrator source."""
    m = re.search(r"(orphans = \(\"nuclei\".*?)\n        if reaped:", src, re.S)
    if not m:
        raise SystemExit("reaper block not found — has the script been restructured?")
    block = m.group(1)
    # group(1) starts AT "orphans", so the leading indent is lost and
    # textwrap.dedent() would compute a common indent of 0 and do nothing.
    if not block.startswith("        "):
        block = "        " + block
    block = textwrap.dedent(block)
    # drop the log() line that expects the real logger
    return "\n".join(l for l in block.splitlines() if "orphaned tool process" not in l)


class _FakeSP:
    """Subprocess shim: neutralise taskkill, pass everything else through."""

    def __init__(self):
        self.killed = []

    def run(self, cmd, **kw):
        if isinstance(cmd, list) and cmd and cmd[0] == "taskkill":
            pid = cmd[cmd.index("/PID") + 1] if "/PID" in cmd else "?"

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            self.killed.append(pid)
            return R()
        return _sp.run(cmd, **kw)


def main() -> int:
    orch = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ORCH
    if not orch.exists():
        print(f"orchestrator not found: {orch}")
        return 2

    src = orch.read_text(encoding="utf-8", errors="replace")
    block = extract_reaper_block(src)

    sp = _FakeSP()
    ns = {"_os": os, "_sp": sp, "log": lambda *a, **k: None}
    exec(block, ns)

    procs = ns.get("procs", [])
    live = ns.get("live_pids", set())
    orphans = ns.get("orphans", ())

    print(f"source          : {orch}")
    print(f"records parsed  : {len(procs)}")
    print(f"live pid set    : {len(live)}")
    print(f"sanity          : {'PASS - parse ok' if 100 < len(live) < 2000 else 'FAIL - parse broken'}")
    print(f"reaped (dry)    : {ns.get('reaped')}")
    print(f"WOULD KILL pids : {sp.killed}")
    print()

    for p in procs:
        name = (p.get("Name") or "").lower()
        if not any(o in name for o in orphans):
            continue
        pid = p.get("ProcessId") or "-"
        ppid = p.get("ParentProcessId") or "-"
        alive = "ALIVE" if (str(ppid).isdigit() and int(ppid) in live) else "DEAD"
        print(f"  {p.get('Name'):<16} PID {str(pid):<7} PPID {str(ppid):<7} parent={alive}")

    if len(procs) != len(live):
        print()
        print("WARNING: records parsed != live pid set -> parser is oversplitting")
        print("WMIC output. Split on LF (not splitlines()) and do NOT flush the")
        print("record on a blank line (WMIC emits a blank between every field).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
