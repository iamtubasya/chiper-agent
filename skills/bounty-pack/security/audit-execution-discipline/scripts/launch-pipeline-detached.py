#!/usr/bin/env python3
"""Launch audit-pipeline-orchestrator.py DETACHED (survives closing the host console/window).

Why: the orchestrator inherits the lifetime of whatever shell started it. Launch it from a
PowerShell/console window and closing that window kills the whole tree mid-run. This launches it
with DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW, stdout/stderr into the
engagement's orchestrator.log, and writes orchestrator.pid.

Resume is file-based, so re-running this with the SAME target continues where the last run stopped
(the orchestrator prints "RESUME MODE: already completed [...]" and skips sub-phases whose marker
files exist). Never restart from 0A, never delete artefacts to "start clean".

Usage:
    python launch-pipeline-detached.py https://account.example.com \
        --tech "java,spring,oauth2,saml,node" --scope "*.example.com,example.com"
    python launch-pipeline-detached.py <target> --cwd "D:\\data hermes\\bug-bounty"

Verify ~40 s later (BOTH checks):
    tail -40 <outdir>/orchestrator.log          # expect RESUME MODE / next STEP line
    tasklist /FI "PID eq <pid>"                 # process must be alive
If the log stops ~10 s after a STEP line with no traceback, suspect RAM/OOM (free < 1.2 GB),
not a code bug — see references/unstick-frozen-pipeline-tool-loop.md.
"""
import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path


def output_dir_for(target: str) -> Path:
    """Mirror audit-pipeline-orchestrator.py main() so resume finds the right artefacts."""
    slug = (target.replace("https://", "").replace("http://", "")
            .replace("/", "_").replace(":", "_").replace(".", "_")
            .replace("?", "_").replace("=", "_"))
    _chiper_base = os.environ.get("CHIPER_PATH") or os.environ.get("CHIPER_HOME")
    _poc_root = (Path(_chiper_base) if _chiper_base else (Path.home() / ".chiper")) / "skills/bounty-pack/poc-plans"
    return _poc_root / f"orchestrator-{slug}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--tech", default="")
    ap.add_argument("--scope", default="")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--cwd", default=None, help="working dir for the run (optional)")
    ap.add_argument("--scripts-dir", default=None,
                    help="dir holding audit-pipeline-orchestrator.py (default: <hermes>/scripts)")
    args = ap.parse_args()

    hermes = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "hermes"
    scripts = Path(args.scripts_dir) if args.scripts_dir else hermes / "scripts"
    script = scripts / "audit-pipeline-orchestrator.py"
    if not script.exists():
        print(f"orchestrator not found: {script}", file=sys.stderr)
        return 2

    outdir = output_dir_for(args.target)
    outdir.mkdir(parents=True, exist_ok=True)
    logf = outdir / "orchestrator.log"

    cmd = [sys.executable, str(script), args.target]
    if args.tech:
        cmd += ["--tech", args.tech]
    if args.scope:
        cmd += ["--scope", args.scope]
    if args.exclude:
        cmd += ["--exclude", args.exclude]

    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    fh = open(logf, "a", encoding="utf-8", errors="replace")
    fh.write(f"\n\n===== DETACHED LAUNCH {datetime.datetime.now().isoformat()} =====\n{cmd}\n")
    fh.flush()

    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS|NEW_PROCESS_GROUP|NO_WINDOW
    p = subprocess.Popen(cmd, cwd=args.cwd, stdout=fh, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, env=env,
                         creationflags=flags, close_fds=True)
    (outdir / "orchestrator.pid").write_text(str(p.pid))
    print(f"LAUNCHED pid={p.pid}")
    print(f"log   : {logf}")
    print(f"verify: tail -40 \"{logf}\"  ;  tasklist /FI \"PID eq {p.pid}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
