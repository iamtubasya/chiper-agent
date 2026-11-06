#!/usr/bin/env python3
"""Watchdog: refresh vendor advisories; print ONLY when NEW high/critical appeared.

Watchdog contract — EMPTY STDOUT = SILENCE. Use with cronjob(action='create', no_agent=true):
  script must be a BARE FILENAME relative to ~/.hermes/scripts/ (absolute path is rejected).
  Non-zero exit / timeout sends an error alert, so transient failures stay silent (sys.exit(0)).

Deploy:
  1. copy this file to ~/.hermes/scripts/advisory-watch.py
  2. ensure a table of watched repos + the fetch script path below
  3. cronjob(action='create', name='advisory-intel-watch', schedule='0 4 * * 1',
             no_agent=true, script='advisory-watch.py')
"""
import json, os, subprocess, sys

PY = os.environ.get("ADVISORY_PY") or sys.executable
BASE = os.environ.get("ADVISORY_BASE") or os.path.expanduser("~/advisory-intel")
FETCH = os.path.join(BASE, "fetch_advisories.py")

if not os.path.exists(FETCH):
    sys.exit(0)  # nothing deployed here -> stay silent

try:
    subprocess.run([PY, FETCH], cwd=BASE, capture_output=True, timeout=600)
    res = json.load(open(os.path.join(BASE, "last_sync_result.json"), encoding="utf-8"))
except Exception:
    sys.exit(0)  # transient failure must not spam the chat

lines = []
for repo, d in res.items():
    newh = d.get("new_high_critical") or []
    if newh:
        lines.append(f"{repo}: {len(newh)} NEW high/critical -> "
                     f"https://github.com/{repo}/security/advisories")
        lines.append("  " + ", ".join(newh[:25]) + (" …" if len(newh) > 25 else ""))

if lines:
    print("ADVISORY-INTEL: new high/critical advisories — extend the "
          "<vendor>-advisory-techniques.md playbook\n" + "\n".join(lines))
