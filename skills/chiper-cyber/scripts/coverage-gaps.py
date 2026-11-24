#!/usr/bin/env python3
"""Compare covered ATT&CK techniques in coverage.json against a baseline list.

Usage:
    python3 scripts/coverage-gaps.py coverage.json
    python3 scripts/coverage-gaps.py coverage.json --baseline techniques.txt
Exit codes: 0 = no gaps, 1 = gaps found, 2 = usage/IO error.
"""
import argparse, json, sys
from pathlib import Path

def load(path: Path):
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    covered = set()
    if isinstance(doc, dict):
        for key in ("covered", "techniques", "technique_ids"):
            val = doc.get(key)
            if isinstance(val, list):
                covered.update(str(v).upper() for v in val)
        for entry in doc.get("rules", []) or []:
            if isinstance(entry, dict):
                for tag in entry.get("tags", []) or []:
                    t = str(tag).upper()
                    if t.startswith("ATTACK.T"):
                        covered.add(t.split(".", 1)[1])
    elif isinstance(doc, list):
        covered.update(str(v).upper() for v in doc)
    # buang awalan "ATTACK." saja - jangan dipotong di titik, karena
    # sub-teknik seperti T1003.001 juga mengandung titik.
    return {c[7:] if c.startswith("ATTACK.") else c for c in covered}

def main() -> int:
    ap = argparse.ArgumentParser(description="Report ATT&CK coverage gaps.")
    ap.add_argument("coverage", help="coverage.json produced by the detection pipeline")
    ap.add_argument("--baseline", help="file with one technique id per line")
    args = ap.parse_args()
    covered = load(Path(args.coverage))
    if args.baseline:
        try:
            baseline = {l.strip().upper() for l in Path(args.baseline).read_text().splitlines()
                        if l.strip() and not l.startswith("#")}
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        baseline = set()
    gaps = sorted(baseline - covered)
    print(f"covered: {len(covered)}")
    print(f"baseline: {len(baseline)}")
    print(f"gaps: {len(gaps)}")
    for g in gaps:
        print(f"  MISSING {g}")
    return 1 if gaps else 0

if __name__ == "__main__":
    raise SystemExit(main())
