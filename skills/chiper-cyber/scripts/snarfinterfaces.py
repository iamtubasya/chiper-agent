#!/usr/bin/env python3
"""Enumerate network interfaces straight from sysfs (no root, no deps).

Usage:
    ./scripts/snarfinterfaces.py
    ./scripts/snarfinterfaces.py --json
Part of chiper-firmware-reverse interface triage.
"""
import argparse, json, os, sys
from pathlib import Path

SYS = Path("/sys/class/net")

def read(path: Path, default=""):
    try:
        return path.read_text().strip()
    except OSError:
        return default

def interfaces():
    if not SYS.is_dir():
        return []
    out = []
    for dev in sorted(SYS.iterdir()):
        out.append({
            "name": dev.name,
            "mac": read(dev / "address"),
            "state": read(dev / "operstate"),
            "mtu": read(dev / "mtu"),
            "type": read(dev / "type"),
            "rx_bytes": read(dev / "statistics" / "rx_bytes"),
            "tx_bytes": read(dev / "statistics" / "tx_bytes"),
        })
    return out

def main() -> int:
    ap = argparse.ArgumentParser(description="List network interfaces from sysfs.")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    ap.add_argument("--up", action="store_true", help="only interfaces that are up")
    args = ap.parse_args()
    rows = interfaces()
    if not rows:
        print("error: /sys/class/net not available on this host", file=sys.stderr)
        return 2
    if args.up:
        rows = [r for r in rows if r["state"] == "up"]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    print(f"{'iface':<12} {'state':<8} {'mtu':>5} {'mac':<18} {'rx':>12} {'tx':>12}")
    for r in rows:
        print(f"{r['name']:<12} {r['state']:<8} {r['mtu']:>5} {r['mac']:<18} "
              f"{r['rx_bytes']:>12} {r['tx_bytes']:>12}")
    print(f"\n{len(rows)} interface(s)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
