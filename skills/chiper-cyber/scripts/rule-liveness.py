#!/usr/bin/env python3
"""Report Sigma rules whose `date`/`modified` field is older than a threshold.

Usage:
    python3 scripts/rule-liveness.py --since 90d
    python3 scripts/rule-liveness.py rules/malware/old-ransom-family.yml --since 730d
Exit codes: 0 = all fresh, 1 = stale rules found, 2 = usage/IO error.
"""
import argparse, re, sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2)

AGE = re.compile(r"^(\d+)([dwmy])$", re.I)
UNIT = {"d": 1, "w": 7, "m": 30, "y": 365}

def parse_since(text: str) -> int:
    m = AGE.match(text.strip())
    if not m:
        raise ValueError(f"bad --since {text!r}, expected e.g. 90d, 12w, 6m, 2y")
    return int(m.group(1)) * UNIT[m.group(2).lower()]

def rule_date(doc: dict):
    raw = doc.get("modified") or doc.get("date")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def collect(target: Path):
    if target.is_file():
        return [target]
    return sorted(p for p in list(target.rglob("*.yml")) + list(target.rglob("*.yaml"))
                  if p.is_file())

def main() -> int:
    ap = argparse.ArgumentParser(description="Find stale Sigma rules.")
    ap.add_argument("target", nargs="?", default=".", help="rule file or directory")
    ap.add_argument("--since", default="90d", help="age threshold, e.g. 90d, 12w, 6m, 2y")
    args = ap.parse_args()
    try:
        days = parse_since(args.since)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    target = Path(args.target)
    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 2
    rules = collect(target)
    if not rules:
        print(f"error: no rules under {target}", file=sys.stderr)
        return 2
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    stale, fresh, undated = [], 0, []
    for rule in rules:
        try:
            doc = yaml.safe_load(rule.read_text(encoding="utf-8")) or {}
        except Exception:                          # noqa: BLE001
            continue
        if isinstance(doc, list):                  # multi-document falco style
            continue
        when = rule_date(doc)
        if when is None:
            undated.append(rule); continue
        if when.timestamp() < cutoff:
            stale.append((rule, when.date().isoformat()))
        else:
            fresh += 1
    for rule, when in stale:
        print(f"STALE  {rule}  last={when}  threshold={args.since}")
    for rule in undated:
        print(f"UNDATED {rule}")
    print(f"\nchecked {len(rules)} rule(s): {fresh} fresh, {len(stale)} stale, "
          f"{len(undated)} undated")
    return 1 if stale else 0

if __name__ == "__main__":
    raise SystemExit(main())
