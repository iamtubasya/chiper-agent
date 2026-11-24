#!/usr/bin/env python3
"""Check Sigma rules for required metadata tags.

Usage:
    python3 scripts/check-tags.py rules/
    python3 scripts/check-tags.py rules/malware/old-ransom-family.yml
Exit codes: 0 = every rule carries the required tags, 1 = findings, 2 = usage/IO error.
"""
import argparse, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2)

REQUIRED = ("title", "id", "description", "logsource", "detection", "level", "falsepositives")

def check(path: Path):
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:                      # noqa: BLE001 - report and continue
        return [f"unparseable YAML: {exc}"]
    if not isinstance(doc, dict):
        return ["document is not a mapping"]
    findings = [f"missing field: {f}" for f in REQUIRED if f not in doc]
    tags = [str(t) for t in (doc.get("tags") or [])]
    if not any(str(t).startswith("attack.") for t in tags):
        findings.append("no attack.* tag")
    if str(doc.get("level", "")).lower() not in ("informational", "low", "medium", "high", "critical"):
        findings.append(f"invalid level: {doc.get('level')!r}")
    return findings

def collect(target: Path):
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*.yml") if p.is_file()) +                sorted(p for p in target.rglob("*.yaml") if p.is_file())

def main() -> int:
    ap = argparse.ArgumentParser(description="Validate Sigma rule metadata tags.")
    ap.add_argument("target", help="rule file or directory")
    ap.add_argument("--quiet", action="store_true", help="only print rules with findings")
    args = ap.parse_args()
    target = Path(args.target)
    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 2
    rules = collect(target)
    if not rules:
        print(f"error: no .yml/.yaml rules under {target}", file=sys.stderr)
        return 2
    dirty = 0
    for rule in rules:
        findings = check(rule)
        if findings:
            dirty += 1
            print(f"{rule}:")
            for f in findings:
                print(f"  - {f}")
        elif not args.quiet:
            print(f"{rule}: ok")
    print(f"\nchecked {len(rules)} rule(s), {dirty} with findings")
    return 1 if dirty else 0

if __name__ == "__main__":
    raise SystemExit(main())
