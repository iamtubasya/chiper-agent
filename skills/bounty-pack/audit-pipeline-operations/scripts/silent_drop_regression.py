#!/usr/bin/env python3
"""
silent_drop_regression.py — regression guard for the THREE regex lexical-collision
silent-drops fixed 2026-11-02 (audit-pipeline-operations SKILL.md §2c).

A gate that classifies "dead/unverified" or "meta heading" via a BARE WORD will, at some
point, DELETE a valid finding whose name contains that word. These three cases are the
concrete instances. This script rebuilds the minimal fixtures, runs the real gates, and
asserts BOTH directions (valid finding survives; genuine junk still drops). Exit 0 = pass.

Distinct from severity_gate_regression.py (which tests the full aggregate->weaponize->
finding_gate->validate->triage severity chain, 4 positive + 5 negative). THAT pair does
NOT cover:
  1. DEAD_CHAIN bare `\\bunverified\\b` matching a finding's OWN title
     ("unverified email change" is a live ATO primitive — the ADDRESS is unverified = the bug)
  2. aggregate-findings skip_words SUBSTRING match ("OS Command Injection" contains "command",
     "HTTP method tampering" contains "method")
  3. aggregate-findings severity regex not consuming markdown-bold ("**Severity:** Critical")

Usage:
  python silent_drop_regression.py --scripts C:/Users/WINDOWS10/AppData/Local/hermes/scripts
"""
import argparse, json, re, subprocess, sys, tempfile, os, shutil
from pathlib import Path


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          errors="replace", timeout=120)


def case_finding_gate_dead_chain(scripts):
    """Case 1: DEAD_CHAIN bare \\bunverified\\b must NOT drop a finding titled
    'unverified email change'; a genuine 'remains unverified' SSRF must STILL drop."""
    data = [
        {"id": "F1", "title": "Unverified email change enables full account takeover",
         "severity": "high",
         "text": "POST /api/account/email updates the address with no verification token. "
                 "Then POST /api/account/password sends the reset link to the new unverified "
                 "address, and PUT /api/account/password logs the attacker in (HTTP/1.1 200 OK). "
                 "Impact: account takeover.",
         "impact_class": "account_takeover"},
        {"id": "N1", "title": "Possible SSRF in webhook URL",
         "severity": "medium",
         "text": "The SSRF finding remains unverified — no callback was observed, chain blocked."},
    ]
    d = Path(tempfile.mkdtemp(prefix="sd_case1_"))
    (d / "findings.json").write_text(json.dumps(data), encoding="utf-8")
    r = run([sys.executable, str(scripts / "finding_gate.py"),
             "findings.json", "--out", "gated.json", "--report", "report.md",
             "--survivors", "survivors.json"], cwd=d)
    out = json.loads((d / "gated.json").read_text(encoding="utf-8"))
    by_title = {x["title"]: x["verdict"] for x in out}
    ok = by_title.get(data[0]["title"]) == "REPORT" and \
         by_title.get(data[1]["title"]) == "DROP"
    detail = {t: v for t, v in by_title.items()}
    shutil.rmtree(d, ignore_errors=True)
    return ok, detail


def case_aggregate_skip_words(scripts):
    """Case 2: skip_words must not drop findings whose title CONTAINS a meta word;
    genuine meta headings (Summary, Commands used) must still be skipped."""
    worker = """# Worker output — RCE finding

## OS Command Injection (pre-auth RCE)

**Severity:** Critical

The `/api/debug/exec` endpoint passes the `cmd` parameter to subprocess.Popen.

**Evidence:** `GET /api/debug/exec?cmd=id` returned `uid=0(root)`.

## HTTP method tampering bypasses auth on /admin

**Severity:** High

Sending OPTIONS instead of GET to /admin/export skips the middleware auth check.

**Evidence:** HTTP/1.1 200 OK, body contained 40 admin records.

## Commands used

- nuclei -u https://target

## Summary

Scanned the target.
"""
    d = Path(tempfile.mkdtemp(prefix="sd_case2_"))
    (d / "worker-1.md").write_text(worker, encoding="utf-8")
    r = run([sys.executable, str(scripts / "aggregate-findings.py"),
             "worker-1.md", "--output", "out.json"], cwd=d)
    # aggregate takes a target DIR; feed the dir instead
    r = run([sys.executable, str(scripts / "aggregate-findings.py"),
             ".", "--output", "out.json"], cwd=d)
    out = json.loads((d / "out.json").read_text(encoding="utf-8"))
    titles = [f["title"] for f in out]
    ok = len(out) == 2 and \
         any("OS Command Injection" in t for t in titles) and \
         any("method tampering" in t for t in titles)
    detail = titles
    shutil.rmtree(d, ignore_errors=True)
    return ok, detail


def case_aggregate_severity_bold(scripts):
    """Case 3: severity regex must consume markdown-bold, not default to 'unknown'."""
    worker = """## Stored XSS in profile field

**Severity:** High

**Evidence:** HTTP/1.1 200 OK, <script> reflected.
"""
    d = Path(tempfile.mkdtemp(prefix="sd_case3_"))
    (d / "worker-1.md").write_text(worker, encoding="utf-8")
    r = run([sys.executable, str(scripts / "aggregate-findings.py"),
             ".", "--output", "out.json"], cwd=d)
    out = json.loads((d / "out.json").read_text(encoding="utf-8"))
    sev = out[0]["severity"] if out else "MISSING"
    ev = out[0].get("evidence", "") if out else ""
    ok = sev == "High" and not ev.startswith("*")
    detail = {"severity": sev, "evidence": ev}
    shutil.rmtree(d, ignore_errors=True)
    return ok, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", required=True,
                    help="path to ~/AppData/Local/hermes/scripts")
    args = ap.parse_args()
    scripts = Path(args.scripts)

    cases = [
        ("finding_gate DEAD_CHAIN bare \\bunverified\\b collision", case_finding_gate_dead_chain),
        ("aggregate-findings skip_words substring collision", case_aggregate_skip_words),
        ("aggregate-findings markdown-bold severity regex", case_aggregate_severity_bold),
    ]
    all_ok = True
    for name, fn in cases:
        try:
            ok, detail = fn(scripts)
        except Exception as e:
            ok, detail = False, f"EXCEPTION: {e}"
        print(f"{'PASS' if ok else 'FAIL'}  {name}  -> {detail}")
        all_ok = all_ok and ok
    print("RESULT:", "PASS — all 3 silent-drop guards hold" if all_ok
          else "FAIL — a silent-drop guard regressed")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()