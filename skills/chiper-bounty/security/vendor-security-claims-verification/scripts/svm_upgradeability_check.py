#!/usr/bin/env python3
"""
svm_upgradeability_check.py — is a Solana program upgradeable, and who holds the authority?

Read-only. Uses getAccountInfo / getBalance / getSignaturesForAddress only.
Nothing is signed, no transaction is created.

Usage:
    python svm_upgradeability_check.py <PROGRAM_ID> [<PROGRAM_ID> ...]
    python svm_upgradeability_check.py --rpc https://api.mainnet-beta.solana.com <ID> ...
    python svm_upgradeability_check.py --json <ID>          # machine-readable

Why this exists: a documentation claim of "non-upgradable" / "immutable" is falsified
outright when the program account's owner is BPFLoaderUpgradeab1e. That one field is the
whole answer; the rest (ProgramData, authority, key type) is the detail the report needs.

Exit codes: 0 = all checks completed (regardless of verdict), 2 = bad args, 3 = RPC failure.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request

UPGRADEABLE_LOADER = "BPFLoaderUpgradeab1e11111111111111111111111"
LEGACY_LOADERS = {
    "BPFLoader2111111111111111111111111111111111": "legacy BPFLoader2 (non-upgradeable)",
    "BPFLoader1111111111111111111111111111111111": "deprecated BPFLoader1 (non-upgradeable)",
}
SYSTEM_PROGRAM = "11111111111111111111111111111111"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, rem = divmod(n, 58)
        out = B58[rem] + out
    for byte in raw:
        if byte == 0:
            out = "1" + out
        else:
            break
    return out


class Rpc:
    def __init__(self, url: str, timeout: int = 25):
        self.url = url
        self.timeout = timeout

    def call(self, method: str, params: list):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.load(resp)
        if "error" in payload:
            raise RuntimeError(f"RPC error on {method}: {payload['error']}")
        return payload.get("result")

    def account(self, pubkey: str, **opts):
        cfg = {"encoding": "base64"}
        cfg.update(opts)
        res = self.call("getAccountInfo", [pubkey, cfg])
        return (res or {}).get("value")


def check_program(rpc: Rpc, program_id: str) -> dict:
    out: dict = {"program_id": program_id, "checks": [], "verdict": "unknown"}

    acct = rpc.account(program_id)
    if acct is None:
        out["verdict"] = "not-found"
        out["checks"].append("program account not found on this cluster")
        return out

    owner = acct.get("owner")
    out["owner_loader"] = owner
    out["executable"] = acct.get("executable")

    if owner == UPGRADEABLE_LOADER:
        out["verdict"] = "UPGRADEABLE"
        out["checks"].append(
            "owner is BPFLoaderUpgradeab1e -> program logic CAN be replaced "
            "(falsifies any 'non-upgradable' claim)"
        )
    elif owner in LEGACY_LOADERS:
        out["verdict"] = "immutable"
        out["checks"].append(f"owner is {LEGACY_LOADERS[owner]} -> claim of immutability HOLDS")
        return out
    else:
        out["verdict"] = "unknown-loader"
        out["checks"].append(f"unrecognised loader {owner!r} — inspect manually")
        return out

    # Program state (36 bytes): 4-byte LE tag (2 = Program) + 32-byte ProgramData address
    state = rpc.account(program_id, dataSlice={"offset": 0, "length": 36})
    try:
        raw = base64.b64decode(state["data"][0])
    except Exception as exc:  # noqa: BLE001
        out["checks"].append(f"could not read program state: {exc}")
        return out

    tag = int.from_bytes(raw[0:4], "little")
    if tag != 2:
        out["checks"].append(f"unexpected program state tag {tag} (expected 2)")
        return out

    programdata_addr = b58encode(raw[4:36])
    out["programdata_account"] = programdata_addr

    pd = rpc.account(programdata_addr)
    if pd is None:
        out["checks"].append("ProgramData account missing — cannot read authority")
        return out

    pd_raw = base64.b64decode(pd["data"][0])
    pd_tag = int.from_bytes(pd_raw[0:4], "little")
    deploy_slot = int.from_bytes(pd_raw[4:12], "little")
    has_auth = pd_raw[12]

    out["programdata_tag"] = pd_tag
    out["last_deploy_slot"] = deploy_slot
    out["has_upgrade_authority"] = bool(has_auth)

    if pd_tag != 3:
        out["checks"].append(f"unexpected ProgramData tag {pd_tag} (expected 3)")

    if has_auth != 1:
        out["checks"].append("no upgrade authority set -> effectively immutable")
        out["verdict"] = "upgradeable-but-frozen"
        return out

    authority = b58encode(pd_raw[13:45])
    out["upgrade_authority"] = authority

    # What kind of account is the authority?
    auth_acct = rpc.account(authority)
    if auth_acct is None:
        out["authority_type"] = "plain-keypair"
        out["checks"].append(
            "authority has no account data -> plain system keypair "
            "(single key, NOT a multisig / no on-chain approval flow)"
        )
    else:
        auth_owner = auth_acct.get("owner")
        out["authority_owner"] = auth_owner
        out["authority_executable"] = auth_acct.get("executable")
        if auth_owner == SYSTEM_PROGRAM and not auth_acct.get("executable") and not auth_acct.get("data", [""])[0]:
            out["authority_type"] = "plain-keypair"
            out["checks"].append("authority is a System-owned keypair -> single key holder")
        else:
            out["authority_type"] = "program-owned"
            out["checks"].append(
                f"authority is owned by {auth_owner} -> identify the program "
                "(Squads / SPL Governance / custom vault) before claiming anything"
            )

    # Is the key alive?
    try:
        sigs = rpc.call("getSignaturesForAddress", [authority, {"limit": 3}]) or []
        out["authority_recent_sigs"] = len(sigs)
        if sigs:
            out["authority_last_slot"] = sigs[0].get("slot")
            out["authority_last_blocktime"] = sigs[0].get("blockTime")
            out["checks"].append(f"authority is ACTIVE (last sig slot {sigs[0].get('slot')})")
        else:
            out["checks"].append("authority has no signatures — possibly dormant")
    except Exception as exc:  # noqa: BLE001
        out["checks"].append(f"could not list authority signatures: {exc}")

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Solana program upgradeability (read-only).")
    ap.add_argument("program_ids", nargs="+", help="program IDs (base58) to inspect")
    ap.add_argument("--rpc", default="https://api.mainnet-beta.solana.com")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()

    rpc = Rpc(args.rpc)
    results = []
    try:
        for pid in args.program_ids:
            results.append(check_program(rpc, pid))
    except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        print(f"RPC failure: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for res in results:
        print("=" * 72)
        print(f"{res['program_id']}")
        print(f"  VERDICT      : {res['verdict']}")
        if "owner_loader" in res:
            print(f"  loader       : {res['owner_loader']}")
        if "programdata_account" in res:
            print(f"  ProgramData  : {res['programdata_account']}")
        if "last_deploy_slot" in res:
            print(f"  last deploy  : slot {res['last_deploy_slot']}")
        if "has_upgrade_authority" in res:
            print(f"  has auth     : {res['has_upgrade_authority']}")
        if "upgrade_authority" in res:
            print(f"  authority    : {res['upgrade_authority']}  ({res.get('authority_type')})")
        for line in res["checks"]:
            print(f"    - {line}")
    print("=" * 72)
    print("Read-only probes (getAccountInfo/getSignaturesForAddress). Nothing signed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
