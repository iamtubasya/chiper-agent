#!/usr/bin/env python3
"""Prove (or disprove) that a LOCAL repo is what is actually DEPLOYED.

Pulls each deployed implementation's sources from Sourcify (works on any chain, no API key),
then compares them to the repo file after stripping comments + all whitespace. A byte-identical
result retires the whole "maybe I am auditing the wrong revision" doubt and is a sentence you
want in the report. A mismatch is the build-generation signal to switch to the selector diff
(scripts/deployed_vs_source_selector_diff.py) and to say which reading material is live.

Why Sourcify v2 has two hard gotchas this script handles for you:
  * `?fields=sources` is REQUIRED, otherwise you get metadata only and it looks unverified.
  * the address MUST be lower-case, else HTTP 400 "invalid address" even for verified contracts.

Usage
-----
Edit TARGETS (or pass a json file: `sourcify_repo_diff.py targets.json`).

    TARGETS = {
        "ChainIdHere": {                      # 1=ethereum 56=BSC 8453=base 137=polygon
            "<ContractName>": ("0xProxyOrImplAddr", "contracts/path/File.sol"),
        }
    }

Notes
-----
* Feed it the IMPLEMENTATION address for a proxy. Resolve it first:
    cast storage <proxy> 0xREDACTED_******** --rpc-url $RPC
  or, for a beacon proxy, read 0xREDACTED_********
  then `cast call <beacon> "implementation()(address)"`.
* Repo path is matched on basename because Sourcify keys sources by the COMPILER's import path
  (e.g. "@spherex-xyz/engine-contracts/src/SphereXEngine.sol"), not by the repo layout.
"""
import json
import os
import re
import sys
import urllib.request

TARGETS = {
    # 56: {
    #     "PoolRegistry": ("0x850badf759a3cb03090a70752e0b4a98c04002f6", "contracts/factory/PoolRegistry.sol"),
    # },
}

SOURCIFY = "https://sourcify.dev/server/v2/contract/{chain}/{addr}?fields=sources"


def norm(s: str) -> str:
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"\s+", "", s)


def fetch(chain: str, addr: str) -> dict:
    # lowercase is mandatory -> Sourcify 400s on a checksummed address
    url = SOURCIFY.format(chain=chain, addr=addr.lower())
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> int:
    targets = TARGETS
    if len(sys.argv) > 1:
        targets = json.load(open(sys.argv[1], encoding="utf-8"))

    bad = 0
    for chain, contracts in targets.items():
        for name, (addr, rel) in contracts.items():
            try:
                d = fetch(chain, addr)
            except Exception as e:  # noqa: BLE001 - report and continue
                print(f"{name:24} FETCH FAIL {e}")
                bad += 1
                continue

            sources = d.get("sources") or {}
            if not sources:
                print(f"{name:24} NO SOURCES (match={d.get('match')!r}) -- not in Sourcify")
                bad += 1
                continue

            base = os.path.basename(rel)
            hit = next((k for k in sources if k.endswith("/" + base) or k == base), None)
            if hit is None:
                print(f"{name:24} source for {base} not in bundle; keys={list(sources)[:3]}")
                bad += 1
                continue

            node = sources[hit]
            dep = node["content"] if isinstance(node, dict) else node
            if not os.path.exists(rel):
                print(f"{name:24} local {rel} missing")
                bad += 1
                continue
            repo = open(rel, encoding="utf-8").read()

            same = norm(dep) == norm(repo)
            flag = "identical" if same else "DIFFERENT <-- switch to selector diff"
            print(f"{name:24} {d.get('match'):12} dep={len(dep):6}b repo={len(repo):6}b {flag}")
            if not same:
                bad += 1
                open(f"/tmp/deployed_{name}.sol", "w", encoding="utf-8").write(dep)

    print("\nOK: deployed == repo (audit the repo with confidence)" if bad == 0
          else f"\n{bad} target(s) need follow-up (see rows above)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
