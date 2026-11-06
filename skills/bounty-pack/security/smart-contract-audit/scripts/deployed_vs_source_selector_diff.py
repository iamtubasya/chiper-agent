#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deployed_vs_source_selector_diff.py — is the contract on chain the source you were handed?

Why: many programs say "the deployed build is an earlier build than the published source" and
then close every already-fixed issue as known-and-unpaid. Reading the source cannot tell you
which fixes are live. This measures it.

Method: derive the selector set from the source (forge inspect methodIdentifiers) and check each
4-byte selector against the runtime bytecode (cast code). A selector present in source but absent
on chain means the deployed build is OLDER than the source -> any fix carried by that function is
NOT live. Map the absent names onto the fix they carry before you spend effort on it.

Usage
-----
  python deployed_vs_source_selector_diff.py \
      --src  /path/to/foundry-project \
      --rpc  https://sepolia-rollup.arbitrum.io/rpc \
      --pairs "TimbPrize=0x6027...,GameRegistry=0x11C2...,TIMBSToken=0x2Aaa..."

  # or point at a JSON map  {"TimbPrize": "0x...", ...}
  python deployed_vs_source_selector_diff.py --src . --rpc $RPC --pairs-file pairs.json

Reading the output
------------------
  all source selectors present  -> deployed == source. A source-derived finding is certainly live;
                                   say so in the report, it pre-empts "is this even deployed?".
  MISSING ON CHAIN (n)          -> older build. Group the missing names and map each to its fix
                                   (e.g. epoch()/newEpoch() = a stale-weight epoch guard,
                                   minNudgeAmountIn = a paid-nudge floor, retiredPrize = an
                                   escrow-repoint fix, maxTimbsPerWallet = a per-wallet cap).
                                   If the absent function IS a listed known-issue fix, the live
                                   system still has that bug and it earns nothing.

Also useful as a first pass: a getter that REVERTS under `cast call` on a contract you expected to
have it is the cheapest possible hint that the build is older. This script formalises that.

Note: `forge inspect` needs a buildable project (remappings in foundry.toml). With via_ir enabled
the first build is slow — run it once and cache the source selectors if you are iterating.
"""
import argparse, json, os, subprocess, sys

FOUNDRY_BIN = os.path.expanduser("~/.foundry/bin")


def run(cmd, cwd=None):
    env = dict(os.environ)
    env["PATH"] = FOUNDRY_BIN + os.pathsep + env.get("PATH", "")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)


def source_selectors(contract, src):
    r = run(["forge", "inspect", contract, "methodIdentifiers", "--json"], cwd=src)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout).strip().splitlines()[-1][:160]
    try:
        return json.loads(r.stdout), None
    except Exception as e:                                   # noqa: BLE001
        return None, f"unparsable output: {e}"


def onchain_code(addr, rpc):
    r = run(["cast", "code", addr, "--rpc-url", rpc])
    return r.stdout.strip() if r.returncode == 0 else ""


def parse_pairs(args):
    if args.pairs_file:
        with open(args.pairs_file, encoding="utf-8") as fh:
            return list(json.load(fh).items())
    out = []
    for chunk in (args.pairs or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            sys.exit(f"bad --pairs entry {chunk!r}; expected Contract=0xAddress")
        name, addr = chunk.split("=", 1)
        out.append((name.strip(), addr.strip()))
    if not out:
        sys.exit("nothing to check: pass --pairs or --pairs-file")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="foundry project dir (contains foundry.toml)")
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--pairs", help='comma list: "Contract=0xaddr,Other=0xaddr"')
    ap.add_argument("--pairs-file", help="JSON map {Contract: address}")
    args = ap.parse_args()

    print("=== deployed build vs published source: missing selectors ===\n")
    older, same, failed = [], [], []
    for name, addr in parse_pairs(args):
        sels, err = source_selectors(name, args.src)
        if sels is None:
            print(f"--- {name}: SKIPPED (inspect failed: {err})\n")
            failed.append(name)
            continue
        code = onchain_code(addr, args.rpc).lower()
        if not code or code == "0x":
            print(f"--- {name} @ {addr}: NO CODE ON CHAIN\n")
            failed.append(name)
            continue
        missing = sorted(sig for sig, sel in sels.items() if sel.lower() not in code)
        print(f"--- {name} @ {addr}")
        print(f"    source methods: {len(sels)}   on-chain bytes: {len(code) // 2 - 1}")
        if missing:
            print(f"    MISSING ON CHAIN ({len(missing)}) — deployed build is OLDER than source:")
            for m in missing:
                print(f"        {m}")
            older.append((name, missing))
        else:
            print("    all source selectors present (deployed == source)")
            same.append(name)
        print()

    print("=" * 60)
    print(f"deployed == source : {', '.join(same) or '-'}")
    print(f"OLDER than source  : {', '.join(n for n, _ in older) or '-'}")
    if failed:
        print(f"not checked        : {', '.join(failed)}")
    print("\nNEXT: map each missing name onto the fix it carries. If that function IS a listed")
    print("known-issue fix, the live system still has the bug — and it earns nothing. Concentrate")
    print("reporting on defects that are live on BOTH (the 'deployed == source' set).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
