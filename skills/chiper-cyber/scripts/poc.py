#!/usr/bin/env python3
"""Generic smart-contract exploit PoC entrypoint (chiper-blockchain-web3).

Works standalone for the pure logic, and exposes main() for
    brownie run scripts/poc.py
    forge test --fork-url $RPC   (import the helpers)

Never point it at a live target without explicit authorisation.
"""
import argparse, json

def vulnerable_balance_of(state: dict, who: str) -> int:
    """Classic missing-zero-address / unchecked-return reading used in demos."""
    return int(state.get(who.lower(), 0))

def flash_loan_math(principal: int, fee_bps: int = 30) -> dict:
    fee = principal * fee_bps // 10_000
    return {"principal": principal, "fee": fee, "repay": principal + fee,
            "profit_possible": fee > 0}

def replay_nonce_sequence(nonces: list[int]) -> dict:
    """Detect a reused nonce that would permit transaction replay."""
    seen, dupes = set(), []
    for n in nonces:
        if n in seen:
            dupes.append(n)
        seen.add(n)
    return {"count": len(nonces), "unique": len(seen), "replayed": dupes}

def main() -> int:
    ap = argparse.ArgumentParser(description="Smart-contract PoC helper.")
    ap.add_argument("--demo", action="store_true", help="print demonstration output")
    args = ap.parse_args()
    if args.demo:
        print(json.dumps({
            "flash_loan": flash_loan_math(1_000_000),
            "nonce_replay": replay_nonce_sequence([1, 2, 3, 2, 4]),
            "balance": vulnerable_balance_of({"0xdead": 42}, "0xDEAD"),
        }, indent=2))
        return 0
    print("import this module from your tests, or run with --demo")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
