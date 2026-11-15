#!/usr/bin/env python3
"""
finding_gate.py — Validate findings severity & quality before report.
Usage:
  python3 finding_gate.py add --sev S|A|B --json '{"finding":"..."}'
  python3 finding_gate.py list
  python3 finding_gate.py check
"""
import json, sys, os, hashlib
from datetime import datetime

GATE_FILE = os.path.join(os.path.dirname(__file__), ".finding_gate.json")

SEVERITY_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}

def load_gate():
    if os.path.exists(GATE_FILE):
        with open(GATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"findings": [], "created": datetime.now(__import__("datetime").timezone.utc).isoformat()}

def save_gate(data):
    with open(GATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def add_finding(sev, finding_json):
    gate = load_gate()
    finding = json.loads(finding_json) if isinstance(finding_json, str) else finding_json
    finding["severity"] = sev.upper()
    finding["added"] = datetime.now(__import__("datetime").timezone.utc).isoformat()
    finding["id"] = hashlib.md5(json.dumps(finding, sort_keys=True).encode()).hexdigest()[:12]
    finding["verified"] = False
    finding["reproduction_count"] = 0
    gate["findings"].append(finding)
    save_gate(gate)
    print(f"[GATE] Added: {finding['id']} (sev={sev})")

def list_findings():
    gate = load_gate()
    if not gate["findings"]:
        print("[GATE] No findings.")
        return
    for f in gate["findings"]:
        status = "VERIFIED" if f.get("verified") else "UNVERIFIED"
        print(f"  [{f['severity']}] {f['id']} — {status} — {f.get('title', 'untitled')}")

def check_gate():
    gate = load_gate()
    findings = gate["findings"]
    if not findings:
        print("[GATE] BLOCKED: No findings to report.")
        sys.exit(1)

    s_count = sum(1 for f in findings if f.get("severity") == "S")
    a_count = sum(1 for f in findings if f.get("severity") == "A")
    b_count = sum(1 for f in findings if f.get("severity") == "B")
    unverified = sum(1 for f in findings if not f.get("verified"))

    print(f"[GATE] Total findings: {len(findings)}")
    print(f"[GATE] Severity: S={s_count} A={a_count} B={b_count}")
    print(f"[GATE] Unverified: {unverified}")

    if unverified > 0:
        print(f"[GATE] WARNING: {unverified} findings not yet verified. Run evidence_collector.py first.")
    
    print(f"[GATE] PASSED: {len(findings)} findings ready for report generation.")
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Finding Gate - validate findings")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add")
    add_p.add_argument("--sev", default="B")
    add_p.add_argument("--json", dest="finding_json", default='{"finding":"test"}')

    sub.add_parser("list")
    sub.add_parser("check")

    args = parser.parse_args()
    if args.command == "add":
        add_finding(args.sev, args.finding_json)
    elif args.command == "list":
        list_findings()
    elif args.command == "check":
        check_gate()
    else:
        print(__doc__)
