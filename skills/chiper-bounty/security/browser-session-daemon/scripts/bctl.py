#!/usr/bin/env python3
"""Controller for bd.py — send one command, print the daemon's result.

    python bctl.py '{"cmd":"goto","url":"https://target/login","wait":5}'
    python bctl.py '{"cmd":"dump"}'
    python bctl.py '{"cmd":"click","sel":"#onetrust-reject-all-handler"}'
    python bctl.py '{"cmd":"fill","sel":"#UserName","val":"me@example.com"}'
    python bctl.py '{"cmd":"eval","js":"() => location.href"}'
    python bctl.py '{"cmd":"cookies"}'
    python bctl.py '{"cmd":"exit"}'

BD_WORK must match the daemon's BD_WORK (defaults to cwd).
"""
import json, os, sys, time

WORK = os.environ.get("BD_WORK", os.getcwd())
CMD = os.path.join(WORK, "cmd.json")
RES = os.path.join(WORK, "res.json")

if len(sys.argv) < 2:
    print(__doc__); sys.exit(2)

cmd = json.loads(sys.argv[1])
cmd.setdefault("_n", time.time_ns())   # force uniqueness so the daemon never dedup-skips

if os.path.exists(RES):
    os.remove(RES)
json.dump(cmd, open(CMD, "w"))

t0 = time.time()
limit = cmd.get("timeout", 100)
res = None
while time.time() - t0 < limit:
    if os.path.exists(RES):
        try:
            res = json.load(open(RES))
            break
        except Exception:
            time.sleep(0.3)
    time.sleep(0.3)

if res is None:
    print(json.dumps({"ok": False, "err": f"daemon timeout after {limit}s — check bd.log"}))
    sys.exit(1)

print(json.dumps(res, indent=2, default=str)[:6000])
