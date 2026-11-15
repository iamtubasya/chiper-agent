#!/usr/bin/env python3
"""Metadata-aware live-vs-compiled bytecode comparison.

WHY THIS EXISTS: raw deployedBytecode LENGTH is not evidence of a code difference. solc appends a CBOR
metadata blob (which embeds the source PATHS of the contract's dependency closure) and terminates it with
a 2-byte big-endian length. Two builds of identical code can differ in length purely because one used
`project/contracts/...` and the other `contracts/...`. Compare the CODE SECTION only.

The metadata is self-describing: the last 2 bytes give its length, so
    code_section = bytecode[: len(bytecode) - 2 - metadata_len]

Usage:
  # compare a compiled artifact against the live code
  python compare_live_vs_compiled.py --addr 0xADDR --rpc https://eth.drpc.org --contract SSVClusters
  # or with explicit hex files instead of forge/cast
  python compare_live_vs_compiled.py --live live.hex --compiled compiled.hex
  # include the metadata in the verdict (will normally differ because of differing source paths)
  python compare_live_vs_compiled.py ... --include-metadata

Exit codes: 0 = code sections identical, 1 = code sections differ, 2 = could not determine.
"""
import argparse, os, re, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def norm(h):
    h = (h or "").strip().lower()
    if h.startswith("0x"):
        h = h[2:]
    return re.sub(r"\s+", "", h)


def strip_metadata(h):
    """Return (code, metadata_hex). Unlinks the CBOR blob using its trailing 2-byte length."""
    if len(h) < 4:
        return h, ""
    try:
        mlen = int(h[-4:], 16)
    except ValueError:
        return h, ""
    cut = len(h) - 2 * (mlen + 2)
    if mlen == 0 or cut <= 0 or cut >= len(h):
        return h, ""
    return h[:cut], h[cut:]


def diff_ranges(a, b):
    """Byte ranges where a and b differ (equal length assumed)."""
    out, start, prev = [], None, None
    for i in range(0, min(len(a), len(b)), 2):
        if a[i:i + 2] != b[i:i + 2]:
            if start is None:
                start = prev = i
            elif i == prev + 2:
                prev = i
            else:
                out.append((start, prev)); start = prev = i
    if start is not None:
        out.append((start, prev))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addr")
    ap.add_argument("--rpc", default="https://eth.drpc.org")
    ap.add_argument("--contract")
    ap.add_argument("--live", help="file containing the live runtime hex")
    ap.add_argument("--compiled", help="file containing compiled deployedBytecode hex")
    ap.add_argument("--include-metadata", action="store_true",
                    help="also require the metadata blob to match (off by default)")
    ap.add_argument("--dump-live", help="write the fetched live runtime hex to this file")
    args = ap.parse_args()

    if args.live:
        live = norm(open(args.live).read())
    elif args.addr:
        live = norm(run(f'cast code {args.addr} --rpc-url {args.rpc}'))
    else:
        print("need --live or --addr"); return 2
    if args.dump_live:
        open(args.dump_live, "w").write("0x" + live)

    if args.compiled:
        comp = norm(open(args.compiled).read())
    elif args.contract:
        comp = norm(run(f'forge inspect {args.contract} deployedBytecode'))
    else:
        print("need --compiled or --contract"); return 2

    if not live or not comp:
        print(f"could not obtain bytecode (live={len(live)//2}B compiled={len(comp)//2}B)")
        return 2

    lc, lm = strip_metadata(live)
    cc, cm = strip_metadata(comp)
    print(f"live     runtime={len(live)//2:>7}B  code={len(lc)//2:>7}B  metadata={len(lm)//2}B")
    print(f"compiled runtime={len(comp)//2:>7}B  code={len(cc)//2:>7}B  metadata={len(cm)//2}B")

    verdict_code = (lc == cc)
    verdict_meta = (lm == cm)

    if len(lc) != len(cc):
        print(f"\nCODE LENGTHS DIFFER ({len(cc)//2}B compiled vs {len(lc)//2}B live) -> the sources differ.")
        n = min(len(lc), len(cc))
        for i in range(0, n, 2):
            if lc[i:i + 2] != cc[i:i + 2]:
                print(f"  first code difference at byte {i//2}")
                print(f"    compiled: {cc[max(0,i-32):i+48]}")
                print(f"    live    : {lc[max(0,i-32):i+48]}")
                break
        print("\nReminder: do NOT conclude 'unpublished source' before enumerating remote refs")
        print("  git ls-remote --heads origin ; for each: git show FETCH_HEAD:<file> | grep -c '<suspect code>'")
        print("  then quantify: git diff --stat <audited-commit>..<branch> -- contracts/")
        return 1

    if verdict_code:
        print("\nCODE SECTIONS: IDENTICAL")
        if verdict_meta:
            print("METADATA     : identical (same paths + settings)")
        else:
            print("METADATA     : differs -> source PATHS/order differ, code is the same.")
            print("               Recompile the recovered deployed tree with its original paths")
            print("               (e.g. project/contracts/... + npm/@openzeppelin@X) if you need a 0-diff match.")
        if args.include_metadata and not verdict_meta:
            return 1
        return 0

    print("\nCODE SECTIONS: DIFFER")
    for s, e in diff_ranges(cc, lc)[:10]:
        print(f"  bytes {s//2}-{e//2}: compiled={cc[s:e+2][:48]} live={lc[s:e+2][:48]}")
    print("\nNext: read the differing region, then find the branch that reproduces the live code")
    print("      (git ls-remote --heads origin; git diff --stat <audited>..<branch> -- contracts/).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
