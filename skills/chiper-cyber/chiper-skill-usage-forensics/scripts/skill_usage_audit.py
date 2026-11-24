#!/usr/bin/env python3
"""Audit which Chiper skills are actually used and what they cost.

Read-only. Never writes to ~/.chiper.

Usage:
    python3 skill_usage_audit.py                 # full report
    python3 skill_usage_audit.py --dead          # never-loaded skills only
    python3 skill_usage_audit.py --cost          # token cost from logs only
    python3 skill_usage_audit.py --json          # machine-readable
    python3 skill_usage_audit.py --home /path/to/.chiper

Reconciled, as no single source is complete:
    .usage.json  -> lifetime counters (survives session pruning)
    agent.log*   -> per-call payload size, duration, errors (rotates away)
    state.db     -> per-call session + arguments (pruned by sessions prune)
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ (\w+) \[([^\]]*)\] (.*)$")
OK = re.compile(r"tool (\w+) completed \(([\d.]+)s, (\d+) chars\)")
FAIL = re.compile(r"Tool (\w+) returned error \(([\d.]+)s\): (.*)")


def paths(home: str) -> dict:
    return {
        "usage": os.path.join(home, "skills", ".usage.json"),
        "logs": os.path.join(home, "logs", "agent.log*"),
        "db": os.path.join(home, "state.db"),
        "skills": os.path.join(home, "skills"),
    }


def load_usage(p: str) -> dict:
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"[warn] cannot read {p}: {exc}", file=sys.stderr)
        return {}


def parse_logs(pattern: str) -> tuple[list, list]:
    calls, failures = [], []
    for path in glob.glob(pattern):
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                m = LINE.match(line.strip())
                if not m:
                    continue
                ts, _lvl, sess, msg = m.groups()
                if "skill" not in msg.lower():
                    continue
                m2 = OK.search(msg)
                if m2:
                    calls.append({"ts": ts, "sess": sess, "tool": m2.group(1),
                                  "dur": float(m2.group(2)), "chars": int(m2.group(3))})
                    continue
                m3 = FAIL.search(msg)
                if m3:
                    failures.append({"ts": ts, "sess": sess, "tool": m3.group(1),
                                     "dur": float(m3.group(2)), "err": m3.group(3)[:160]})
    calls.sort(key=lambda x: x["ts"])  # filename order is not chronological
    return calls, failures


def parse_db(path: str, window: int = 300) -> list:
    if not os.path.exists(path):
        return []
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = list(conn.execute(
            "SELECT session_id, tool_calls, timestamp FROM messages "
            "WHERE role='assistant' AND tool_calls LIKE '%\"skill_view\"%'"
        ))
    except Exception as exc:
        print(f"[warn] cannot query {path}: {exc}", file=sys.stderr)
        return []

    all_calls, views = [], []
    for r in rows:
        try:
            tcs = json.loads(r["tool_calls"])
        except Exception:
            continue
        if not isinstance(tcs, list):
            continue
        for tc in tcs:
            fn = (tc or {}).get("function") or {}
            name = fn.get("name")
            if not name:
                continue
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            rec = {"ts": r["timestamp"], "sess": r["session_id"],
                   "tool": name, "skill": args.get("name"),
                   "file": args.get("file_path")}
            all_calls.append(rec)
            if name == "skill_view":
                views.append(rec)

    out = []
    for sv in views:
        follow = [x for x in all_calls
                  if x["sess"] == sv["sess"]
                  and x["ts"] > sv["ts"]
                  and x["ts"] - sv["ts"] <= window
                  and x["tool"] != "skill_view"]
        out.append({**sv, "worked": bool(follow), "follow": len(follow),
                    "tools": list(dict.fromkeys(x["tool"] for x in follow))[:4]})
    return out


def audit(home: str, window: int = 300) -> dict:
    p = paths(home)
    usage = load_usage(p["usage"])
    calls, failures = parse_logs(p["logs"])
    timeline = parse_db(p["db"], window)

    agg = collections.Counter()
    last = {}
    for k, r in usage.items():
        base = k.split(":")[-1]
        agg[base] += int(r.get("view_count") or 0)
        ts = r.get("last_used_at")
        if ts and ts > last.get(base, ""):
            last[base] = ts

    installed = set()
    for dirpath, _dirs, files in os.walk(p["skills"]):
        if "SKILL.md" in files:
            installed.add(os.path.basename(dirpath))

    used = {k for k, v in agg.items() if v > 0}
    views = [c for c in calls if c["tool"] == "skill_view"]
    total_chars = sum(c["chars"] for c in views)

    return {
        "records": len(usage),
        "distinct_skills": len(agg),
        "installed": len(installed),
        "never_used": sorted(installed - used),
        "coverage": (len(used & installed) / len(installed)) if installed else 0.0,
        "top": agg.most_common(15),
        "last_used": last,
        "log_calls": len(calls),
        "log_failures": len(failures),
        "log_by_tool": collections.Counter(c["tool"] for c in calls).most_common(),
        "view_calls": len(views),
        "avg_payload": (total_chars / len(views)) if views else 0,
        "total_payload": total_chars,
        "est_tokens": total_chars // 4,
        "top_payloads": sorted(views, key=lambda x: -x["chars"])[:10],
        "timeline": timeline,
        "failure_detail": failures[:20],
        "forked_keys": [k for k in usage if ":" in k],
    }


def render(rep: dict, show_dead: bool, show_cost: bool) -> str:
    L = []
    L.append("=== SKILL USAGE AUDIT ===")
    L.append(f"records in .usage.json : {rep['records']}"
             f"  (distinct after normalise: {rep['distinct_skills']})")
    L.append(f"skills installed       : {rep['installed']}")
    L.append(f"coverage               : {rep['coverage']:.1%}  "
             f"({rep['installed'] - len(rep['never_used'])}/{rep['installed']} ever used)")

    if rep["forked_keys"]:
        L.append("")
        L.append("!! forked counters (same skill, two names) — normalise with split(':')[-1]:")
        for k in rep["forked_keys"]:
            L.append(f"   {k}")

    L.append("")
    L.append("--- top skills (lifetime, .usage.json) ---")
    if rep["top"]:
        for name, n in rep["top"]:
            L.append(f"{n:>5}x  {name:<45} last={rep['last_used'].get(name, '-')}")
    else:
        L.append("  (none)")

    if show_dead:
        L.append("")
        L.append(f"--- never loaded ({len(rep['never_used'])}) ---")
        for n in rep["never_used"][:80]:
            L.append(f"   {n}")
        if len(rep["never_used"]) > 80:
            L.append(f"   ... and {len(rep['never_used']) - 80} more")

    if show_cost:
        L.append("")
        L.append("--- cost (agent.log*) ---")
        L.append(f"parsed calls   : {rep['log_calls']}   failures: {rep['log_failures']}")
        L.append(f"skill_view     : {rep['view_calls']}   "
                 f"avg payload: {rep['avg_payload']:.0f} chars")
        L.append(f"total payload  : {rep['total_payload']:,} chars  "
                 f"~{rep['est_tokens']:,} tokens")
        L.append("")
        L.append("--- by tool ---")
        for tool, n in rep["log_by_tool"]:
            L.append(f"{n:>5}x  {tool}")
        L.append("")
        L.append("--- heaviest skill_view payloads ---")
        for c in rep["top_payloads"]:
            L.append(f'{c["ts"]}  {c["chars"]:>8,} chars  {c["dur"]:>5.2f}s  [{c["sess"]}]')

    if rep["timeline"]:
        worked = sum(1 for t in rep["timeline"] if t["worked"])
        L.append("")
        L.append("--- timeline (state.db) ---")
        L.append(f"{len(rep['timeline'])} skill_view events, "
                 f"{worked} followed by real work ({worked / len(rep['timeline']):.0%})")
        for t in rep["timeline"][-25:]:
            stamp = datetime.fromtimestamp(t["ts"]).strftime("%Y-%m-%d %H:%M")
            flag = "USED" if t["worked"] else "VIEW-ONLY"
            L.append(f'{stamp}  {flag:<10} {str(t["skill"]):<42} '
                     f'follow={t["follow"]} {",".join(t["tools"])[:34]}')

    if rep["failure_detail"]:
        L.append("")
        L.append(f"--- recent failures ({rep['log_failures']} total) ---")
        for f in rep["failure_detail"]:
            L.append(f'{f["ts"]}  {f["tool"]}: {f["err"][:110]}')
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=os.environ.get("CHIPER_HOME",
                                                     os.path.expanduser("~/.chiper")))
    ap.add_argument("--window", type=int, default=300,
                    help="seconds after skill_view to count follow-up work as 'used'")
    ap.add_argument("--dead", action="store_true", help="list never-loaded skills")
    ap.add_argument("--cost", action="store_true", help="token cost detail")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--all", action="store_true", help="everything (dead + cost)")
    args = ap.parse_args()

    if not os.path.isdir(args.home):
        print(f"CHIPER_HOME not found: {args.home}", file=sys.stderr)
        return 2

    rep = audit(args.home, args.window)

    if args.json:
        rep = {**rep, "top_payloads": rep["top_payloads"],
               "timeline": rep["timeline"][-100:]}
        print(json.dumps(rep, indent=2, default=str))
        return 0

    show_dead = args.dead or args.all or not (args.dead or args.cost)
    show_cost = args.cost or args.all or not (args.dead or args.cost)
    print(render(rep, show_dead, show_cost))
    return 0


if __name__ == "__main__":
    sys.exit(main())
