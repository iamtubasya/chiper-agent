#!/usr/bin/env python3
"""Gate a Substrate pallet finding against the DEPLOYED runtime.

Two jobs:
  1. discover the RPC when the project publishes none (scrape the block explorer's bundle)
  2. read state_getRuntimeVersion over websocket and compare spec_version with the
     runtime/src/lib.rs you audited

Substrate answers HTTP 405 to plain JSON-RPC, so websocket is mandatory.

Usage:
    python spec_version_gate.py --rpc wss://mainnet.example.network
    python spec_version_gate.py --explorer https://explorer.example.io --compare 76
    python spec_version_gate.py --rpc wss://... --repo ./repo --compare 76

Exit 0 = deployed matches the audited version. Exit 1 = mismatch (do NOT report yet).
Exit 2 = could not reach a runtime (findings stay unverified).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (research; runtime-version gate)"


def http_get(url: str, limit: int = 8_000_000, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit).decode("utf-8", "replace")


def discover_rpc(explorer: str) -> list[str]:
    """The explorer's own JS bundle carries the endpoint it dials."""
    found: set[str] = set()
    try:
        html = http_get(explorer)
    except Exception as e:
        print(f"[!] explorer fetch failed: {type(e).__name__}", file=sys.stderr)
        return []

    pat = re.compile(r"(?:wss?|https)://[a-z0-9.\-]+(?::\d+)?(?:/[a-z0-9/\-_]*)?")
    for m in pat.finditer(html):
        found.add(m.group(0))

    for src in re.findall(r'<script[^>]+src="([^"]+)"', html):
        url = src if src.startswith("http") else explorer.rstrip("/") + "/" + src.lstrip("/")
        try:
            js = http_get(url)
        except Exception:
            continue
        for m in pat.finditer(js):
            found.add(m.group(0))

    # keep only plausible chain endpoints
    keep = [
        u for u in found
        if u.startswith("ws")
        or any(k in u for k in ("rpc", "chain", "node", "api"))
    ]
    return sorted(keep)


async def read_runtime_version(rpc: str) -> dict:
    import websockets

    async with websockets.connect(rpc, open_timeout=30, max_size=2**22) as ws:
        await ws.send(json.dumps({
            "id": 1, "jsonrpc": "2.0",
            "method": "state_getRuntimeVersion", "params": [],
        }))
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if msg.get("id") == 1:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg["result"]


def repo_spec_version(repo: Path) -> int | None:
    """spec_version from runtime/src/lib.rs (or the first runtime crate found)."""
    for cand in (repo / "runtime" / "src" / "lib.rs",):
        if cand.exists():
            txt = cand.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"spec_version\s*:\s*(\d+)", txt)
            if m:
                return int(m.group(1))
    for cand in repo.glob("runtime*/src/lib.rs"):
        txt = cand.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"spec_version\s*:\s*(\d+)", txt)
        if m:
            return int(m.group(1))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc", help="wss:// endpoint (skip discovery)")
    ap.add_argument("--explorer", help="explorer URL to scrape for the RPC")
    ap.add_argument("--repo", help="cloned repo path, to read spec_version locally")
    ap.add_argument("--compare", type=int, help="expected spec_version")
    a = ap.parse_args()

    rpc = a.rpc
    if not rpc and a.explorer:
        cands = discover_rpc(a.explorer)
        print("[*] candidate endpoints from explorer bundle:")
        for c in cands:
            print("   ", c)
        ws = [c for c in cands if c.startswith("ws")]
        rpc = ws[0] if ws else None

    if not rpc:
        print("[!] no RPC found — pass --rpc explicitly", file=sys.stderr)
        return 2

    try:
        rv = asyncio.run(read_runtime_version(rpc))
    except Exception as e:
        print(f"[!] RPC {rpc} unreachable: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    live = rv.get("specVersion")
    print(f"[*] rpc            : {rpc}")
    print(f"[*] specName       : {rv.get('specName')}")
    print(f"[*] specVersion    : {live}")
    print(f"[*] implVersion    : {rv.get('implVersion')}")

    expected = a.compare
    if expected is None and a.repo:
        expected = repo_spec_version(Path(a.repo))
        print(f"[*] repo spec_version: {expected}")

    if expected is None:
        print("[?] no expected version supplied — cannot gate")
        return 0

    if live == expected:
        print(f"\n[OK] deployed spec_version {live} == audited {expected}")
        print("     findings against this commit are against LIVE code.")
        return 0

    print(f"\n[MISMATCH] deployed {live} != audited {expected}")
    print("     re-clone at the deployed version before writing any report.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
