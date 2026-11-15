#!/usr/bin/env python3
"""
chain_builder.py — Document attack chains from findings.
Usage:
  python3 chain_builder.py build --target URL
  python3 chain_builder.py list
  python3 chain_builder.py export --output chains.json
"""
import json, sys, os
from datetime import datetime

CHAIN_FILE = os.path.join(os.path.dirname(__file__), ".chains.json")

def load_chains():
    if os.path.exists(CHAIN_FILE):
        with open(CHAIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chains": [], "created": datetime.now(__import__("datetime").timezone.utc).isoformat()}

def save_chains(data):
    with open(CHAIN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def build_chain(target):
    chains = load_chains()
    chain = {
        "id": f"chain_{len(chains['chains'])+1:04d}",
        "target": target,
        "steps": [],
        "created": datetime.now(__import__("datetime").timezone.utc).isoformat()
    }
    chains["chains"].append(chain)
    save_chains(chains)
    print(f"[CHAIN] Created: {chain['id']} for {target}")
    return chain

def list_chains():
    chains = load_chains()
    if not chains["chains"]:
        print("[CHAIN] No chains documented.")
        return
    for c in chains["chains"]:
        steps = len(c.get("steps", []))
        print(f"  {c['id']} — {c['target']} — {steps} steps")

def export_chains(output):
    chains = load_chains()
    with open(output, "w", encoding="utf-8") as f:
        json.dump(chains, f, indent=2)
    print(f"[CHAIN] Exported to {output}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 1:
        print(__doc__)
        sys.exit(0)
    cmd = args[0]
    if cmd == "build":
        target = args[1] if len(args) > 1 else "https://example.com"
        build_chain(target)
    elif cmd == "list":
        list_chains()
    elif cmd == "export":
        output = args[1] if len(args) > 1 else "chains.json"
        export_chains(output)
    else:
        print(__doc__)
