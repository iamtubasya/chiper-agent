#!/usr/bin/env python3
"""Replay / proof-of-concept harness for an L2 bridge deposit-withdraw flow.

Meant to be driven by Brownie or Ape:
    brownie run scripts/bridge_poc.py
    ape test --network ::foundry:      (import the functions from your tests)

The module stays import-safe without a chain connection so unit tests can
exercise the pure logic (commitment hashing, replay window checks).
"""
import argparse, hashlib, json, time

SEQUENCE_WINDOW = 600          # seconds a deposit commitment stays replayable

def commitment(deposit_tx: str, recipient: str, amount: int) -> str:
    """Canonical commitment an honest bridge should require before minting."""
    payload = f"{deposit_tx.lower()}|{recipient.lower()}|{amount}".encode()
    return "0x" + hashlib.sha256(payload).hexdigest()

def is_replayable(seen: dict, deposit_tx: str, now: float | None = None) -> bool:
    """True when this deposit has never been seen inside the replay window."""
    now = time.time() if now is None else now
    first = seen.get(deposit_tx.lower())
    return first is None or (now - first) > SEQUENCE_WINDOW

def simulate(withdrawals, deposits) -> dict:
    """Compare withdrawals against deposits and report unbacked mints."""
    backed = {d["tx"].lower(): d for d in deposits}
    unbacked = [w for w in withdrawals if w["deposit"].lower() not in backed]
    return {"withdrawals": len(withdrawals), "backed": len(withdrawals) - len(unbacked),
            "unbacked": unbacked}

def main() -> int:
    ap = argparse.ArgumentParser(description="Bridge PoC / replay harness.")
    ap.add_argument("--demo", action="store_true", help="run the offline demonstration")
    args = ap.parse_args()
    if args.demo:
        deposits = [{"tx": "0xabc", "amount": 100}]
        withdrawals = [{"deposit": "0xabc"}, {"deposit": "0xdef"}]
        print(json.dumps(simulate(withdrawals, deposits), indent=2))
        print("commitment:", commitment("0xabc", "0x1111", 100))
        return 0
    print("import this module from your Brownie/Ape tests, or run with --demo")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
