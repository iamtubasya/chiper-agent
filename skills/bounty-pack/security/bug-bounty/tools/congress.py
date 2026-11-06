#!/usr/bin/env python3
"""
congress.py — Automated bug report formatting for submission.
Usage:
  python3 congress.py --input findings.json --output report.md --format bugcrowd|immunefi|custom
"""
import json, sys, os, argparse
from datetime import datetime

def format_bugcrowd(findings):
    """Format findings for Bugcrowd submission."""
    lines = [
        "# Bug Report",
        f"**Date:** {datetime.now(__import__("datetime").timezone.utc).strftime('%Y-%m-%d')}",
        f"**Total Findings:** {len(findings)}",
        "",
        "---",
        ""
    ]
    for i, f in enumerate(findings, 1):
        lines.append(f"## {i}. {f.get('title', 'Untitled')}")
        lines.append(f"**Severity:** {f.get('severity', 'P2')}")
        lines.append(f"**URL:** {f.get('url', 'N/A')}")
        lines.append("")
        lines.append(f"### Description")
        lines.append(f"{f.get('description', 'No description provided.')}")
        lines.append("")
        lines.append(f"### Steps to Reproduce")
        for step in f.get('steps', ['[Add steps]']):
            lines.append(f"1. {step}")
        lines.append("")
        lines.append(f"### Impact")
        lines.append(f"{f.get('impact', 'No impact description.')}")
        lines.append("")
        lines.append(f"### Remediation")
        lines.append(f"{f.get('remediation', 'No remediation provided.')}")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)

def format_immunefi(findings):
    """Format findings for Immunefi submission."""
    lines = [
        "# Vulnerability Report",
        f"**Date:** {datetime.now(__import__("datetime").timezone.utc).strftime('%Y-%m-%d')}",
        "",
        "---",
        ""
    ]
    for i, f in enumerate(findings, 1):
        lines.append(f"## Vulnerability {i}: {f.get('title', 'Untitled')}")
        lines.append(f"**Severity:** {f.get('severity', 'Medium')}")
        lines.append(f"**Type:** {f.get('type', 'Unknown')}")
        lines.append("")
        lines.append(f"### Summary")
        lines.append(f"{f.get('description', 'No description provided.')}")
        lines.append("")
        lines.append(f"### Vulnerability Details")
        lines.append(f"**Affected Component:** {f.get('url', 'N/A')}")
        lines.append(f"**Attack Vector:** {f.get('vector', 'Network')}")
        lines.append("")
        lines.append(f"### Step-by-Step Guide")
        for step in f.get('steps', ['[Add steps]']):
            lines.append(f"1. {step}")
        lines.append("")
        lines.append(f"### Impact")
        lines.append(f"{f.get('impact', 'No impact description.')}")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Format bug report for submission")
    parser.add_argument("--input", required=True, help="Findings JSON file")
    parser.add_argument("--output", default="report.md", help="Output markdown file")
    parser.add_argument("--format", default="bugcrowd", choices=["bugcrowd", "immunefi", "custom"])
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    findings = data if isinstance(data, list) else data.get("findings", [])

    if args.format == "bugcrowd":
        content = format_bugcrowd(findings)
    elif args.format == "immunefi":
        content = format_immunefi(findings)
    else:
        content = json.dumps(findings, indent=2)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[CONGRESS] Report formatted ({args.format}) → {args.output}")

if __name__ == "__main__":
    main()
