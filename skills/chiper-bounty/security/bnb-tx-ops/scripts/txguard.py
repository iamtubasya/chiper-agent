#!/usr/bin/env python3
"""txguard - read-only guard helper for BSC transactions made with baw.

Never signs, never sends, never needs keys. Network use: public BSC RPC
(receipt/call) and public price APIs (fx). Python 3 stdlib only.

  txguard.py units  <amount> [--decimals 18]
  txguard.py decode --data 0x.. [--value WEI] [--sig "list(uint256,uint256,uint64)"]
  txguard.py price-check --data 0x.. --expect <human> [--arg N] [--decimals 18] [--value WEI --expect-value <human BNB>]
  txguard.py preview <preview.json> [--expect-to 0x..] [--expect-value WEI]
  txguard.py receipt <txhash> [--rpc URL]
  txguard.py fx [<amount BNB>]
Exit code 0 = OK, 2 = GUARD FAILED (do not execute), 1 = usage/network error.
"""
import json, sys, time, argparse, urllib.request
from decimal import Decimal, getcontext
getcontext().prec = 80
RPCS = ["https://bsc-dataseed1.bnbchain.org", "https://bsc-dataseed2.bnbchain.org", "https://bsc-dataseed.bnbchain.org"]

# ---------- pure-python keccak256 (no pycryptodome needed) ----------
_RC = [0x0000000000000001,0x0000000000008082,0x800000000000808A,0x8000000080008000,0x000000000000808B,0x0000000080000001,
 0x8000000080008081,0x8000000000008009,0x000000000000008A,0x0000000000000088,0x0000000080008009,0x000000008000000A,
 0x000000008000808B,0x800000000000008B,0x8000000000008089,0x8000000000008003,0x8000000000008002,0x8000000000000080,
 0x000000000000800A,0x800000008000000A,0x8000000080008081,0x8000000000008080,0x0000000080000001,0x8000000080008008]
_R = [[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],[28,55,25,21,56],[27,20,39,8,14]]
_M = (1 << 64) - 1
def _rol(x, n): return ((x << n) | (x >> (64 - n))) & _M if n else x
def _f(A):
    for rc in _RC:
        C = [A[x][0]^A[x][1]^A[x][2]^A[x][3]^A[x][4] for x in range(5)]
        D = [C[(x-1)%5]^_rol(C[(x+1)%5],1) for x in range(5)]
        A = [[A[x][y]^D[x] for y in range(5)] for x in range(5)]
        B = [[0]*5 for _ in range(5)]
        for x in range(5):
            for y in range(5): B[y][(2*x+3*y)%5] = _rol(A[x][y], _R[x][y])
        A = [[B[x][y]^((~B[(x+1)%5][y])&B[(x+2)%5][y]) for y in range(5)] for x in range(5)]
        A[0][0] ^= rc
    return A
def keccak256(data: bytes) -> bytes:
    rate = 136; p = bytearray(data) + b'\x01'
    while len(p) % rate: p += b'\x00'
    p[-1] |= 0x80
    A = [[0]*5 for _ in range(5)]
    for o in range(0, len(p), rate):
        for i in range(rate // 8):
            A[i%5][i//5] ^= int.from_bytes(p[o+8*i:o+8*i+8], 'little')
        A = _f(A)
    return b''.join(A[i%5][i//5].to_bytes(8, 'little') for i in range(4))
def selector(sig): return '0x' + keccak256(sig.replace(' ', '').encode()).hex()[:8]

KNOWN = [  # signatures seen on BSC mints / markets; add your own with --sig
 "approve(address,uint256)", "setApprovalForAll(address,bool)", "transfer(address,uint256)",
 "transferFrom(address,address,uint256)", "safeTransferFrom(address,address,uint256)",
 "list(uint256,uint256)", "list(uint256,uint256,uint64)", "list(address,uint256,uint256)",
 "createListing(address,uint256,uint256)", "cancelListing(uint256)", "delist(uint256)",
 "buy(uint256)", "mint(uint256)", "mint()", "publicMint(uint256)", "freeMint()", "claimFree()", "claim()",
 "mintFree()", "updatePrice(uint256,uint256)", "makeOffer(uint256)",
]
SEL = {selector(s): s for s in KNOWN}
ADDR_ARGS = ('address',)

def human(raw: int, dec: int) -> str:
    q = Decimal(raw) / (Decimal(10) ** dec)
    s = format(q.normalize(), 'f') if q else '0'
    return s
def to_raw(amount: str, dec: int) -> int:
    q = Decimal(amount) * (Decimal(10) ** dec)
    if q != q.to_integral_value(): raise SystemExit(f"amount {amount} has more than {dec} decimals")
    return int(q)
def split_types(sig):
    inner = sig[sig.index('(')+1:sig.rindex(')')]
    return [t for t in inner.split(',') if t]
def words(data):
    h = data[10:] if data.startswith('0x') else data[8:]
    return [h[i:i+64] for i in range(0, len(h), 64)]

def decode(data, sig=None):
    data = data.strip().lower()
    sel = data[:10]
    s = sig or SEL.get(sel)
    out = {"selector": sel, "signature": s or "UNKNOWN (pass --sig)", "args": []}
    if sig and selector(sig) != sel:
        out["WARNING"] = f"--sig selector {selector(sig)} != calldata selector {sel}"
    ws = words(data)
    types = split_types(s) if s else ['?'] * len(ws)
    for i, w in enumerate(ws):
        t = types[i] if i < len(types) else '?'
        v = int(w, 16)
        a = {"i": i, "type": t, "hex": w}
        if t == 'address' or (t == '?' and w.startswith('0'*24) and v > 2**100):
            a["value"] = '0x' + w[-40:]
        elif t == 'bool': a["value"] = bool(v)
        else:
            a["int"] = v
            if v >= 10**9: a["as18dec"] = human(v, 18); a["as6dec"] = human(v, 6)
            if 1.6e9 < v < 2.2e9: a["asTimeLocal"] = time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(v))
            if v == 2**256 - 1: a["note"] = "MAX UINT (unlimited)"
        out["args"].append(a)
    if s and s.startswith('setApprovalForAll'): out["NOTE"] = "collection-wide approval: operator can move ALL your NFTs of this collection"
    if s and s.startswith('approve') and ws and int(ws[-1], 16) == 2**256 - 1: out["NOTE"] = "unlimited token approval"
    return out

def cmd_units(a):
    raw = to_raw(a.amount, a.decimals)
    print(json.dumps({"human": a.amount, "decimals": a.decimals, "raw": str(raw), "hex": hex(raw),
                      "gwei_if_18dec": human(raw, 9) if a.decimals == 18 else None}, indent=1))

def cmd_decode(a):
    r = decode(a.data, a.sig)
    if a.value is not None: r["value_wei"] = str(int(a.value, 0)); r["value_BNB"] = human(int(a.value, 0), 18)
    print(json.dumps(r, indent=1)); return 0

def cmd_price_check(a):
    r = decode(a.data, a.sig); ok = True; msgs = []
    want = to_raw(a.expect, a.decimals)
    if a.arg is None:
        cands = [x for x in r["args"] if x.get("int") == want]
        got = cands[0]["int"] if cands else None
        where = cands[0]["i"] if cands else None
    else:
        x = r["args"][a.arg] if a.arg < len(r["args"]) else {}
        got, where = x.get("int"), a.arg
    if got != want:
        ok = False; msgs.append(f"PRICE MISMATCH: expected {a.expect} ({want} raw, {a.decimals} dec) but calldata arg[{where}] = {got} -> {human(got, a.decimals) if got is not None else 'not found'}")
    else:
        msgs.append(f"price OK: arg[{where}] = {got} raw = {a.expect} (decimals {a.decimals})")
    if a.expect_value is not None:
        v = int(a.value or '0', 0); ev = to_raw(a.expect_value, 18)
        if v != ev: ok = False; msgs.append(f"VALUE MISMATCH: tx value {v} wei ({human(v,18)} BNB) != expected {a.expect_value} BNB ({ev} wei)")
        else: msgs.append(f"value OK: {v} wei = {a.expect_value} BNB")
    print(json.dumps({"ok": ok, "checks": msgs, "decoded": r}, indent=1))
    return 0 if ok else 2

def cmd_preview(a):
    p = json.load(open(a.file)); ok = True; notes = []
    if not p.get("success"):
        print(json.dumps({"ok": False, "error": p.get("error")}, indent=1)); return 2
    d = p["data"]; pt = d.get("parsedTx") or {}; sim = d.get("simulationResult") or {}; ti = {k.lower(): v for k, v in (d.get("tokenInfos") or {}).items()}
    to = (pt.get("contractAddress") or "")
    if a.expect_to and to.lower() != a.expect_to.lower(): ok = False; notes.append(f"CONTRACT MISMATCH: preview to {to} != expected {a.expect_to}")
    ch = []
    for b in sim.get("balanceChanges") or []:
        info = ti.get((b.get("contractAddress") or "").lower(), {})
        dec = info.get("decimals", 0 if b.get("tokenType") in ("Erc721", "Erc1155") else 18)
        raw = int(Decimal(str(b["change"])))
        e = {"token": info.get("symbol") or b.get("contractAddress"), "type": b.get("tokenType"), "owner": b.get("owner"), "raw": str(raw), "human": human(raw, dec)}
        if b.get("tokenId"): e["tokenId"] = int(b["tokenId"], 16) if str(b["tokenId"]).startswith('0x') else b["tokenId"]
        if info.get("price"): e["usd"] = str((Decimal(raw) / Decimal(10) ** dec * Decimal(info["price"])).quantize(Decimal('0.0001')))
        ch.append(e)
        if b.get("tokenType") == "Native" and a.expect_value is not None:
            ev = int(a.expect_value, 0)
            if -raw > ev + 10**15: ok = False; notes.append(f"native spend {human(-raw,18)} BNB > expected value {human(ev,18)} + 0.001")
    risks = d.get("risks") or {}
    if risks.get("riskDetails") or risks.get("riskBehaviors"): notes.append("RISKS FLAGGED by Binance: " + json.dumps(risks)[:400])
    if sim.get("authorityChanges"): notes.append("AUTHORITY CHANGES: " + json.dumps(sim["authorityChanges"])[:400])
    if sim.get("allowanceChanges"): notes.append("ALLOWANCE CHANGES: " + json.dumps(sim["allowanceChanges"])[:400])
    exp = d.get("expiresAt")
    out = {"ok": ok, "requestId": d.get("requestId"), "to": to, "action": pt.get("action"),
           "simulationCode": sim.get("simulationCode"), "txValue_BNB(gasTokenFromData)": human(int(sim.get("gasTokenFromData") or 0), 18),
           "balanceChanges": ch, "requireConfirmation": d.get("requireConfirmation"),
           "expiresAtLocal": time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(exp / 1000)) if exp else None,
           "expired": bool(exp and exp / 1000 < time.time()), "notes": notes}
    print(json.dumps(out, indent=1)); return 0 if ok else 2

def rpc(method, params, url=None):
    for u in ([url] if url else RPCS):
        try:
            req = urllib.request.Request(u, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                         {"content-type": "application/json", "user-agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(req, timeout=20)).get("result")
        except Exception as e: err = e
    raise SystemExit(f"rpc failed: {err}")

def cmd_receipt(a):
    r = rpc("eth_getTransactionReceipt", [a.tx], a.rpc)
    if not r: print(json.dumps({"tx": a.tx, "status": "pending/not found"})); return 1
    T = "0xREDACTED_********"
    tr = []
    for l in r["logs"]:
        t = l["topics"]
        if t and t[0] == T:
            e = {"contract": l["address"], "from": "0x" + t[1][-40:], "to": "0x" + t[2][-40:]}
            if len(t) == 4: e["kind"] = "ERC721"; e["tokenId"] = int(t[3], 16)
            else: e["kind"] = "ERC20"; e["raw"] = str(int(l["data"], 16)); e["if18dec"] = human(int(l["data"], 16), 18)
            tr.append(e)
    print(json.dumps({"tx": a.tx, "status": "SUCCESS" if r["status"] == "0x1" else "FAILED", "block": int(r["blockNumber"], 16),
                      "gasUsed": int(r["gasUsed"], 16), "transfers": tr, "bscscan": f"https://bscscan.com/tx/{a.tx}"}, indent=1))
    return 0 if r["status"] == "0x1" else 2

def getj(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"user-agent": "Mozilla/5.0"}), timeout=15))
def cmd_fx(a):
    out = {"time": time.strftime('%Y-%m-%d %H:%M %Z')}
    try: out["BNB_USD"] = float(getj("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT")["price"]); out["src_BNB"] = "api.binance.com BNBUSDT"
    except Exception:
        try: out["BNB_USD"] = float(getj("https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd")["binancecoin"]["usd"]); out["src_BNB"] = "coingecko"
        except Exception as e: out["BNB_USD"] = None; out["src_BNB"] = f"FAILED {e}"
    try: out["USD_IDR"] = float(getj("https://open.er-api.com/v6/latest/USD")["rates"]["IDR"]); out["src_IDR"] = "open.er-api.com"
    except Exception as e: out["USD_IDR"] = None; out["src_IDR"] = f"FAILED {e}"
    if a.amount and out["BNB_USD"]:
        usd = float(a.amount) * out["BNB_USD"]; out["amount_BNB"] = a.amount; out["amount_USD"] = round(usd, 4)
        if out["USD_IDR"]: out["amount_IDR"] = round(usd * out["USD_IDR"])
    print(json.dumps(out, indent=1)); return 0 if out["BNB_USD"] else 1

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="c", required=True)
    p = s.add_parser("units"); p.add_argument("amount"); p.add_argument("--decimals", type=int, default=18); p.set_defaults(f=cmd_units)
    p = s.add_parser("decode"); p.add_argument("--data", required=True); p.add_argument("--value"); p.add_argument("--sig"); p.set_defaults(f=cmd_decode)
    p = s.add_parser("price-check"); p.add_argument("--data", required=True); p.add_argument("--expect", required=True)
    p.add_argument("--arg", type=int); p.add_argument("--decimals", type=int, default=18); p.add_argument("--sig")
    p.add_argument("--value"); p.add_argument("--expect-value"); p.set_defaults(f=cmd_price_check)
    p = s.add_parser("preview"); p.add_argument("file"); p.add_argument("--expect-to"); p.add_argument("--expect-value"); p.set_defaults(f=cmd_preview)
    p = s.add_parser("receipt"); p.add_argument("tx"); p.add_argument("--rpc"); p.set_defaults(f=cmd_receipt)
    p = s.add_parser("fx"); p.add_argument("amount", nargs="?"); p.set_defaults(f=cmd_fx)
    a = ap.parse_args(); sys.exit(a.f(a) or 0)
if __name__ == "__main__": main()
