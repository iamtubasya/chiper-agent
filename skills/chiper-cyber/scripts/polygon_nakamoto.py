#!/usr/bin/env python3
"""Measure Nakamoto-style stake concentration on a Polygon (or any EVM) RPC.

Usage:
    python3 scripts/polygon_nakamoto.py --rpc $MAINNET_RPC --threshold 0.33
    python3 scripts/polygon_nakamoto.py --rpc $RPC --blocks 500 --threshold 0.25
"""
import argparse, json, sys, urllib.request

def rpc(url: str, method: str, params=None):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                          "params": params or []}).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        doc = json.loads(resp.read())
    if "error" in doc:
        raise RuntimeError(doc["error"].get("message", "rpc error"))
    return doc["result"]

def main() -> int:
    ap = argparse.ArgumentParser(description="Nakamoto coefficient estimator over block proposers.")
    ap.add_argument("--rpc", required=True, help="JSON-RPC endpoint")
    ap.add_argument("--blocks", type=int, default=200, help="how many recent blocks to sample")
    ap.add_argument("--threshold", type=float, default=0.33,
                    help="share of blocks above which a single proposer is called dominant")
    args = ap.parse_args()

    try:
        latest = int(rpc(args.rpc, "eth_blockNumber"), 16)
    except Exception as exc:                       # noqa: BLE001 - surface any RPC failure
        print(f"error: cannot reach RPC {args.rpc}: {exc}", file=sys.stderr)
        return 2

    counts = {}
    start = max(0, latest - args.blocks)
    for num in range(start, latest + 1):
        try:
            block = rpc(args.rpc, "eth_getBlockByNumber", [hex(num), False])
        except Exception:                          # noqa: BLE001
            continue
        if not block:
            continue
        miner = (block.get("miner") or "unknown").lower()
        counts[miner] = counts.get(miner, 0) + 1

    total = sum(counts.values()) or 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    print(f"sampled blocks : {total}")
    print(f"distinct proposers: {len(ranked)}")
    coefficient = 0
    acc = 0
    for addr, n in ranked:
        acc += n
        coefficient += 1
        if acc / total >= args.threshold:
            break
    print(f"Nakamoto coefficient (>= {args.threshold:.0%} of blocks): {coefficient}")
    print("top proposers:")
    for addr, n in ranked[:5]:
        print(f"  {n:4d}  {addr}  ({n / total:.1%})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
