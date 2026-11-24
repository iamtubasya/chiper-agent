#!/usr/bin/env python3
"""Probe a Windbg WDB remote-debug endpoint (default port 17185).

Usage:
    python3 payloads/wdb_probe.py --target 10.0.0.5 --port 17185
Authorised testing only (chiper-embedded-rtos-security).
"""
import argparse, socket, sys

MAGIC = b"\x1f\x00\x00\x00WDB"          # WDB transport hello
TIMEOUT = 4.0

def probe(host: str, port: int) -> dict:
    with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
        sock.settimeout(TIMEOUT)
        try:
            sock.sendall(MAGIC)
            banner = sock.recv(256)
        except socket.timeout:
            banner = b""
    return {"target": f"{host}:{port}", "reachable": True,
            "banner_hex": banner[:64].hex() or "none",
            "banner_len": len(banner)}

def main() -> int:
    ap = argparse.ArgumentParser(description="Probe a WDB debug endpoint.")
    ap.add_argument("--target", required=True, help="host or IP to probe")
    ap.add_argument("--port", type=int, default=17185, help="WDB port (default 17185)")
    args = ap.parse_args()
    try:
        result = probe(args.target, args.port)
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        print(f"unreachable {args.target}:{args.port} ({exc})")
        return 1
    print(f"reachable {result['target']}  banner_len={result['banner_len']} "
          f"banner={result['banner_hex']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
