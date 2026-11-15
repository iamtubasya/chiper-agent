#!/usr/bin/env python3
"""
SKILL-USAGE — record that a LOADED skill was APPLIED (not merely read).
Writes <target_dir>/skill-usage.json ; enforced by verify-tool-usage.py CHECK 13.

Usage:
  python skill-usage.py <target_dir> --applied hunt-ssrf --evidence references-evidence/ssrf.txt --requests 12
  python skill-usage.py <target_dir> --read-only hunt-csrf            # loaded but NOT applied -> FAIL
  python skill-usage.py <target_dir> --check                          # exit!=0 if any not applied / no evidence
"""
import json, sys, argparse, pathlib

F = "skill-usage.json"

def load(td):
    p = td / F
    return json.loads(p.read_text()) if p.exists() else []

def save(td, d):
    (td / F).write_text(json.dumps(d, indent=2))

def upsert(d, skill, applied, evidence="", requests=0):
    for e in d:
        if e.get("skill") == skill:
            e.update(applied=applied, evidence=evidence, requests=requests); return
    d.append({"skill": skill, "applied": applied, "evidence": evidence, "requests": requests})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target_dir")
    ap.add_argument("--applied"); ap.add_argument("--read-only")
    ap.add_argument("--evidence", default=""); ap.add_argument("--requests", type=int, default=0)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    td = pathlib.Path(a.target_dir)
    if not td.exists(): print(f"FAIL: {td}"); sys.exit(1)
    d = load(td)
    if a.applied:
        upsert(d, a.applied, True, a.evidence, a.requests); save(td, d)
        print(f"marked '{a.applied}' applied (requests={a.requests}, evidence={a.evidence or '-'})"); return
    if a.read_only:
        upsert(d, a.read_only, False, "", 0); save(td, d)
        print(f"marked '{a.read_only}' READ-ONLY (will FAIL the gate)"); return
    # check
    if not d: print("FAIL: skill-usage.json empty/missing"); sys.exit(1)
    bad = [e["skill"] for e in d if not e.get("applied")]
    noev = [e["skill"] for e in d if e.get("applied") and (not e.get("evidence") or not (pathlib.Path(e["evidence"]) if pathlib.Path(e["evidence"]).is_absolute() else td/e["evidence"]).exists())]
    print(f"skills recorded: {len(d)} | applied: {len(d)-len(bad)} | not-applied: {len(bad)} | no-evidence: {len(noev)}")
    for s in bad: print(f"  FAIL not-applied: {s}")
    for s in noev: print(f"  FAIL no-evidence: {s}")
    sys.exit(1 if (bad or noev) else 0)

if __name__ == "__main__":
    main()
