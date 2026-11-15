#!/usr/bin/env python3
"""
claim_permit_probe.py — re-runnable harness for the claim/permit binding matrix.

SAFETY CONTRACT (enforced in code, not just documented):
  * Every signing key is generated fresh in-process and never funded.
  * The victim side is always a DEAD identifier (0x...dEaD) unless you override it.
  * No transaction is ever broadcast. No chain RPC is called. HTTP verdicts only.
  * Keys are discarded at exit.

Usage
    python claim_permit_probe.py --base https://api.relay.link \
        --prepare "/app-fees/{wallet}/claim" \
        --execute "/execute/permits" --kind claim

    # tests 1,2,3,11,14,17 (the decisive ones)
    python claim_permit_probe.py ... --tests 1,2,3,11,14,17

WHAT IT CANNOT DO
    Endpoint bodies differ per product. `--prepare-body` and `--execute-body` take JSON
    templates; `{wallet}`, `{recipient}`, `{amount}`, `{requestId}` are substituted.
    If the shape does not match, read the prepare response by hand and adapt — do not
    assume the harness's default shape is correct for your target.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

DEAD = "0x000000000000000000000000000000000000dEaD"
ZERO_ID = "0x" + "00" * 32
FF_ID = "0x" + "ff" * 32


def post(url: str, body: dict | None = None, timeout: int = 25) -> tuple[int, str]:
    """Return (status, body_text). Never raises on HTTP error status."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - network shape varies wildly
        return 0, f"__error__: {type(e).__name__}: {e}"


def classify(status: int, text: str) -> str:
    """Map a response to a verdict word. Extend the vocabulary per target."""
    t = text.lower()
    if status == 0:
        return "ERROR"
    if "invalid signature" in t:
        return "REJECTED-SIG"
    if "expired" in t or "inexistent" in t:
        return "REJECTED-EXPIRED"
    if "no balance" in t:
        return "REJECTED-NOBAL"
    if "could not find permit" in t:
        return "REJECTED-NOPERMIT"
    if status >= 500:
        return "SERVER-500"
    if 200 <= status < 300:
        return "ACCEPTED"
    return f"HTTP-{status}"


def fresh_key():
    """Throwaway signing key. eth_account is optional; returns None if unavailable."""
    try:
        from eth_account import Account
    except ImportError:
        return None
    return Account.create()


def sign_hash(key, message_hex: str) -> str | None:
    if key is None:
        return None
    try:
        from eth_account.messages import encode_defunct
        return key.sign_message(encode_defunct(hexstr=message_hex)).signature.hex()
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--prepare", required=True, help='e.g. "/app-fees/{wallet}/claim"')
    ap.add_argument("--execute", required=True, help='e.g. "/execute/permits"')
    ap.add_argument("--kind", default="claim")
    ap.add_argument("--wallet", default=DEAD, help="fee-owning wallet (default: dead addr)")
    ap.add_argument("--recipient", default=None)
    ap.add_argument("--amount", default=None)
    ap.add_argument("--tests", default="1,2,3,4,11,14,17")
    ap.add_argument("--prepare-body", default=None, help="JSON template for prepare")
    ap.add_argument("--execute-body", default=None, help="JSON template for execute")
    args = ap.parse_args()

    tests = {int(x) for x in args.tests.split(",") if x.strip()}
    base = args.base.rstrip("/")
    prep_url = base + args.prepare.format(wallet=args.wallet)
    exec_url = base + args.execute

    prep_tpl = json.loads(args.prepare_body) if args.prepare_body else {
        "chainId": 1, "currency": "0x0000000000000000000000000000000000000000",
        "recipient": "{recipient}", "amount": "{amount}",
    }
    exec_tpl = json.loads(args.execute_body) if args.execute_body else {
        "kind": args.kind, "requestId": "{requestId}",
    }

    def fill(tpl, **kw):
        s = json.dumps(tpl)
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        return json.loads(s)

    def mint(recipient=None, amount=None) -> tuple[str | None, str]:
        body = fill(prep_tpl, recipient=recipient or args.wallet, amount=amount or "")
        st, tx = post(prep_url, body)
        try:
            d = json.loads(tx)
            for step in d.get("steps", []):
                for item in step.get("items", []):
                    msg = item.get("data", {}).get("sign", {}).get("message")
                    if msg:
                        return msg, f"{st} {classify(st, tx)}"
        except Exception:  # noqa: BLE001
            pass
        return None, f"{st} {classify(st, tx)} :: {tx[:180]}"

    def submit(request_id: str, sig: str | None) -> str:
        url = exec_url + (f"?signature={sig}" if sig else "")
        body = fill(exec_tpl, requestId=request_id)
        st, tx = post(url, body)
        return f"{st} {classify(st, tx)} :: {tx[:180]}"

    key = fresh_key()
    results: list[tuple[str, str]] = []

    print(f"[*] wallet={args.wallet}")
    print(f"[*] prepare={prep_url}")
    print(f"[*] signer=throwaway ({key.address if key else 'eth_account MISSING'})")
    print()

    # --- test 1: non-owner signature accepted? -------------------------------
    if 1 in tests:
        rid, note = mint()
        if not rid:
            print(f"[1] CANNOT MINT requestId -> {note}")
        else:
            sig = sign_hash(key, rid)
            if not sig:
                print("[1] SKIP - cannot sign (install eth_account)")
            else:
                v = submit(rid, sig)
                print(f"[1] non-owner sig        -> {v}")
                results.append(("1", v))

    # --- test 2: recipient inside the commitment? ---------------------------
    if 2 in tests:
        ids = []
        for r in (args.wallet, DEAD, "0x1111111111111111111111111111111111111111"):
            rid, _ = mint(recipient=r)
            ids.append(rid)
        distinct = len({i for i in ids if i})
        print(f"[2] recipient binding    -> {distinct}/3 distinct requestIds "
              f"({'BOUND' if distinct == 3 else 'NOT BOUND - investigate'})")

    # --- test 3: amount inside the commitment? ------------------------------
    if 3 in tests:
        ids = []
        for a in ("", "1000000", "50560170"):
            rid, _ = mint(amount=a)
            ids.append(rid)
        distinct = len({i for i in ids if i})
        print(f"[3] amount binding       -> {distinct}/3 distinct requestIds "
              f"({'BOUND' if distinct == 3 else 'NOT BOUND - investigate'})")

    # --- test 4: single use? ------------------------------------------------
    if 4 in tests:
        rid, _ = mint()
        if rid:
            sig = sign_hash(key, rid)
            first = submit(rid, sig)
            second = submit(rid, sig)
            print(f"[4] replay               -> 1st: {first}")
            print(f"                            2nd: {second}")

    # --- test 11: existence oracle? ----------------------------------------
    if 11 in tests:
        out = [submit(i, sign_hash(key, i) if key else None) for i in (ZERO_ID, FF_ID)]
        print(f"[11] oracle all-zero     -> {out[0]}")
        print(f"[11] oracle all-ff       -> {out[1]}")
        print("     (identical errors => no oracle; differing => existence leak)")

    # --- test 14: binds to wallet or recipient? ----------------------------
    if 14 in tests:
        rid, _ = mint()
        if rid:
            rk = fresh_key()
            print(f"[14] unrelated-key sig   -> {submit(rid, sign_hash(rk, rid))}")
            rid2, _ = mint()
            if rid2:
                print(f"[14] (fresh id)          -> {submit(rid2, sign_hash(rk, rid2))}")

    # --- test 17: cross-kind confusion -------------------------------------
    if 17 in tests:
        rid, _ = mint()
        if rid:
            for other in ("eip3009", "permit2", "multicall"):
                st, tx = post(exec_url, {"kind": other, "requestId": rid})
                print(f"[17] kind={other:10s}     -> {st} {classify(st, tx)} :: {tx[:120]}")

    print()
    print("[!] Reminder: no transaction was broadcast. Verdicts above are the finding.")
    print("[!] A REJECTED-* verdict on every row means the boundary HELD - report it as a")
    print("    documented negative with hardening notes, not as a vulnerability.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
