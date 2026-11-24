#!/usr/bin/env python3
"""Diff two evaluation result files and report regressions.

Documented usage (chiper-llm-red-team):
    python3 report/diff_baseline.py \
      --old ../results/cyberseceval-prev.json \
      --new ../results/cyberseceval.json
"""
import argparse, json, sys
from pathlib import Path

def load(path: Path):
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    scores = {}
    if isinstance(doc, dict):
        for key in ("results", "scores", "tests"):
            if isinstance(doc.get(key), dict):
                scores.update({str(k): v for k, v in doc[key].items()})
                break
        else:
            scores = {k: v for k, v in doc.items()
                      if isinstance(v, (int, float, bool))}
    elif isinstance(doc, list):
        for entry in doc:
            if isinstance(entry, dict) and "name" in entry:
                scores[str(entry["name"])] = entry.get("score", entry.get("pass"))
    return scores

def main() -> int:
    ap = argparse.ArgumentParser(description="Diff two evaluation result files.")
    ap.add_argument("--old", required=True, help="baseline results JSON")
    ap.add_argument("--new", required=True, help="current results JSON")
    ap.add_argument("--fail-on-regression", action="store_true",
                    help="exit 1 when a score went down")
    args = ap.parse_args()

    old, new = load(Path(args.old)), load(Path(args.new))
    keys = sorted(set(old) | set(new))
    regressed, improved, added, removed = [], [], [], []
    for k in keys:
        if k not in old:
            added.append(k); continue
        if k not in new:
            removed.append(k); continue
        o, n = old[k], new[k]
        if isinstance(o, (int, float)) and isinstance(n, (int, float)):
            if n < o:
                regressed.append((k, o, n))
            elif n > o:
                improved.append((k, o, n))
        elif o != n:
            regressed.append((k, o, n))

    print(f"baseline keys: {len(old)}   current keys: {len(new)}")
    print(f"improved: {len(improved)}   regressed: {len(regressed)}   "
          f"added: {len(added)}   removed: {len(removed)}")
    for k, o, n in regressed:
        print(f"  REGRESSION {k}: {o} -> {n}")
    for k, o, n in improved:
        print(f"  improved   {k}: {o} -> {n}")
    for k in added:
        print(f"  added      {k}")
    for k in removed:
        print(f"  removed    {k}")

    if regressed and args.fail_on_regression:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
