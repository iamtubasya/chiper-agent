#!/usr/bin/env python3
"""
finding_report.py — Generate per-finding report.
Usage:
  python3 finding_report.py --title "Title" --severity P1 --url "https://..." --evidence "proof"
"""
import json, sys, os, argparse
from datetime import datetime

REPORT_DIR = os.path.join(os.path.dirname(__file__), ".finding_reports")

def generate_report(title, severity, url, evidence, description=""):
    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.now(__import__("datetime").timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"finding_{ts}.md"
    filepath = os.path.join(REPORT_DIR, filename)

    content = f"""# {title}

**Severity:** {severity}
**URL:** {url}
**Date:** {datetime.now(__import__("datetime").timezone.utc).isoformat()}
**Status:** Draft

## Description
{description}

## Evidence
```
{evidence}
```

## Steps to Reproduce
1. Navigate to {url}
2. [Add reproduction steps]

## Impact
[Describe impact]

## Remediation
[Add remediation]
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[REPORT] Generated: {filepath}")
    return filepath

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate per-finding report")
    parser.add_argument("--title", required=True)
    parser.add_argument("--severity", default="P2")
    parser.add_argument("--url", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--description", default="")
    args = parser.parse_args()
    generate_report(args.title, args.severity, args.url, args.evidence, args.description)
