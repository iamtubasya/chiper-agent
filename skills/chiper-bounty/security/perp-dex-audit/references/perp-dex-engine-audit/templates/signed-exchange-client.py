"""Signed-exchange protocol client — starter template.

Copy and adapt. Worked against an EIP-712 + canonical-MessagePack venue (TxFlow testnet shape);
the constants come from the app's frontend bundle, not from tutorials.

What is here (verified patterns, not pseudocode):
  * canonical MessagePack encoder (minimal ints, nulls omitted, insertion order preserved)
  * EIP-712 "Agent" signing over connectionId = keccak(msgpack(action) + nonce.to_bytes(8) + vault)
  * agent-key delegation (approveAgent) + main-key-only actions (tokenSend / margin)
  * tick / size rounding taken from the venue's LIVE metadata
  * order / cancel / leverage action builders
  * a polite transport with 429 backoff that never returns a non-dict as a dict

Requires: eth_account, eth_utils, requests.
"""
import json
import os
import secrets
import struct
import sys
import time

import requests
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

# ---------------------------------------------------------------- config
# pull these from the frontend bundle:
#   grep -o -E 'VITE_[A-Z0-9_]+' index.js | sort -u
API = "https://testnet-api.txflow-testnet.xyz"
NETWORK = "TxFlow-Testnet"
CHAIN_ID = 2511
API_VERSION = 1
SIGNATURE_CHAIN_ID = None           # may differ from CHAIN_ID; read it from the bundle
COLLATERAL = "USDC:0x0000000000000000000000000000000000000000"

DOMAIN = {"name": NETWORK, "version": "1", "chainId": CHAIN_ID,
          "verifyingContract": "0x0000000000000000000000000000000000000000"}

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36",
                  "Content-Type": "application/json",
                  "Origin": "https://txflow-testnet.xyz", "Referer": "https://txflow-testnet.xyz/"})


# ---------------------------------------------------------------- canonical msgpack
def _int(n):
    if n >= 0:
        if n < 0x80:
            return bytes([n])
        if n <= 0xFF:
            return b"\xcc" + n.to_bytes(1, "big")
        if n <= 0xFFFF:
            return b"\xcd" + n.to_bytes(2, "big")
        if n <= 0xFFFFFFFF:
            return b"\xce" + n.to_bytes(4, "big")
        return b"\xcf" + n.to_bytes(8, "big")
    if n >= -32:
        return bytes([0xE0 | (n + 32)])
    if n >= -128:
        return b"\xd0" + n.to_bytes(1, "big", signed=True)
    if n >= -32768:
        return b"\xd1" + n.to_bytes(2, "big", signed=True)
    if n >= -2147483648:
        return b"\xd2" + n.to_bytes(4, "big", signed=True)
    return b"\xd3" + n.to_bytes(8, "big", signed=True)


def _str(s):
    b = s.encode()
    n = len(b)
    if n < 32:
        return bytes([0xA0 | n]) + b
    if n <= 0xFF:
        return b"\xd9" + bytes([n]) + b
    if n <= 0xFFFF:
        return b"\xda" + n.to_bytes(2, "big") + b
    return b"\xdb" + n.to_bytes(4, "big") + b


def _bin(b):
    n = len(b)
    if n <= 0xFF:
        return b"\xc4" + bytes([n]) + b
    if n <= 0xFFFF:
        return b"\xc5" + n.to_bytes(2, "big") + b
    return b"\xc6" + n.to_bytes(4, "big") + b


def mp(obj):
    """Canonical: minimal int encoding, None omitted, dict insertion order preserved."""
    if obj is None:
        return b"\xc0"
    if obj is True:
        return b"\xc3"
    if obj is False:
        return b"\xc2"
    if isinstance(obj, int):
        return _int(obj)
    if isinstance(obj, float):
        return b"\xcb" + struct.pack(">d", obj)
    if isinstance(obj, str):
        return _str(obj)
    if isinstance(obj, (bytes, bytearray)):
        return _bin(bytes(obj))
    if isinstance(obj, (list, tuple)):
        n = len(obj)
        head = bytes([0x90 | n]) if n < 16 else (b"\xdc" + n.to_bytes(2, "big") if n <= 0xFFFF
                                                 else b"\xdd" + n.to_bytes(4, "big"))
        return head + b"".join(mp(x) for x in obj)
    if isinstance(obj, dict):
        items = [(k, v) for k, v in obj.items() if v is not None]
        n = len(items)
        head = bytes([0x80 | n]) if n < 16 else (b"\xde" + n.to_bytes(2, "big") if n <= 0xFFFF
                                                 else b"\xdf" + n.to_bytes(4, "big"))
        return head + b"".join(mp(k) + mp(v) for k, v in items)
    raise TypeError("unsupported msgpack type %s" % type(obj))


# ---------------------------------------------------------------- EIP-712 signing
_AGENT_TYPES = {
    "EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                     {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}],
    "Agent": [{"name": "txflowNetwork", "type": "string"}, {"name": "chainId", "type": "uint32"},
              {"name": "apiVersion", "type": "uint32"}, {"name": "connectionId", "type": "bytes32"}],
}


def connection_id(action, nonce, vault_address=None):
    body = {k: v for k, v in action.items() if k != "type"}
    pre = mp(body) + nonce.to_bytes(8, "big")
    pre += (b"\x01" + bytes.fromhex(vault_address[2:])) if vault_address else b"\x00"
    return "0x" + keccak(pre).hex()


def _sign(types, primary, message, key, domain=None):
    full = {"types": types, "primaryType": primary, "domain": domain or DOMAIN, "message": message}
    signable = encode_typed_data(full_message=full)
    return Account.sign_message(signable, private_key=key)


def sign_agent(action, agent_pk, nonce, vault_address=None):
    cid = connection_id(action, nonce, vault_address)
    msg = {"txflowNetwork": NETWORK, "chainId": CHAIN_ID, "apiVersion": API_VERSION, "connectionId": cid}
    sig = _sign(_AGENT_TYPES, "Agent", msg, agent_pk)
    env = {"action": action, "signature": {"r": hex(sig.r), "s": hex(sig.s), "v": sig.v},
           "nonce": nonce, "vaultAddress": vault_address, "signatureChainId": SIGNATURE_CHAIN_ID}
    return env


def sign_direct(action, main_pk, types_map, primary, message, chain_id=None, vault_address=None):
    dom = dict(DOMAIN)
    if chain_id:
        dom["chainId"] = chain_id
    sig = _sign(types_map, primary, message, main_pk, dom)
    return {"action": action, "signature": {"r": hex(sig.r), "s": hex(sig.s), "v": sig.v},
            "nonce": action.get("nonce"), "vaultAddress": vault_address, "signatureChainId": chain_id}


# ---------------------------------------------------------------- transport (429-safe)
def _post(path, payload, tries=6, base=2.0):
    """Never returns a str where a dict was promised: the caller gets (code, body) always."""
    for i in range(tries):
        try:
            r = S.post(API + path, data=json.dumps(payload), timeout=30)
        except Exception as e:
            print("   [api] %s; retry %d" % (e, i + 1))
            time.sleep(base * (i + 1))
            continue
        if r.status_code == 200:
            try:
                return 200, r.json()
            except Exception:
                return 200, r.text
        body = r.text[:200]
        if r.status_code == 429:
            print("   [api] 429; sleeping %ds" % int(base * (i + 1)))
        else:
            print("   [api] HTTP %s: %s" % (r.status_code, body[:120]))
        time.sleep(base * (i + 1))
    return 0, "GAVE_UP"


def info(body):
    return _post("/info", body)


def exchange(env):
    return _post("/exchange", env)


def now_ms():
    return int(time.time() * 1000)


# ---------------------------------------------------------------- live metadata (round from the venue)
_UNI = {"t": 0, "idx": {}, "name": {}}


def universe(force=False):
    if force or not _UNI["idx"] or time.time() - _UNI["t"] > 600:
        for _ in range(5):
            code, d = info({"type": "perpMeta"})
            if isinstance(d, dict) and d.get("universe"):
                _UNI["idx"], _UNI["name"] = {}, {}
                for u in d["universe"]:
                    _UNI["idx"][int(u["index"])] = u
                    _UNI["name"][u["name"]] = u
                _UNI["t"] = time.time()
                return _UNI
            print("   [meta] retry:", str(d)[:80])
            time.sleep(3)
    return _UNI


def uni(asset):
    u = universe()
    if isinstance(asset, str):
        return u["name"].get(asset) or u["name"].get(asset + "-USDC")
    return u["idx"].get(int(asset))


def px(asset, price):
    """round to the instrument tick -> exact decimal string"""
    t = float(uni(asset)["priceTick"])
    n = int(round(float(price) / t))
    s = ("%.12f" % (n * t))
    return s.rstrip("0").rstrip(".") if "." in s else s


def qty(asset, size):
    d = int(uni(asset)["szDecimals"])
    s = ("%.10f" % round(float(size), d)).rstrip("0").rstrip(".")
    return s or "0"


def tiers(asset):
    """margin tier table for one instrument (lookup by BASE ticker, not the numeric index)"""
    base = uni(asset)["baseCurrency"]
    code, d = info({"type": "perpMetaDetail", "assetName": base})
    for i in (d.get("instruments") or []) if isinstance(d, dict) else []:
        if i["perp"]["instrumentId"] == int(uni(asset)["index"]):
            return i["marginTable"]["tiers"], float(i["perp"]["takerFeeRate"])
    return [], 0.0006


# ---------------------------------------------------------------- action builders
def order(asset, side, price, size, tif="Gtc", reduce_only=False, cloid=None):
    o = {"a": int(uni(asset)["index"]), "b": side in ("buy", "B", True),
         "p": str(price), "s": str(size), "r": bool(reduce_only),
         "t": {"limit": {"tif": tif}}}          # Gtc | Ioc | Alo | FrontendMarket
    if cloid:
        o["c"] = cloid
    return {"type": "order", "grouping": "na", "orders": [o]}


def cancel(asset, cloid):
    return {"type": "cancelByCloid", "cancels": [{"asset": int(uni(asset)["index"]), "cloid": cloid}]}


def set_leverage(asset, lev, mode="cross"):
    return {"type": "updateLeverage", "asset": int(uni(asset)["index"]), "leverage": lev, "marginMode": mode}


def set_cross(asset, is_cross=True):
    return {"type": "updateMarginMode", "asset": int(uni(asset)["index"]), "isCross": bool(is_cross)}


# ---------------------------------------------------------------- account helpers
def state(addr, account_type="perp"):
    code, d = info({"type": "clearinghouseState", "user": addr, "accountType": account_type})
    return d if isinstance(d, dict) else {}


def snapshot(addr, asset=None):
    """one record with everything a before/after comparison needs"""
    d = state(addr)
    ms = d.get("marginSummary") or {}
    rec = {"ts": now_ms(), "equity": ms.get("accountValue"), "deposits_rawUsd": ms.get("totalRawUsd"),
           "withdrawable": d.get("withdrawable"), "maint_margin_used": d.get("crossMaintenanceMarginUsed"),
           "margin_ratio": d.get("crossMarginRatio"),
           "positions": [{k: p["position"].get(k) for k in
                          ("coin", "szi", "entryPx", "liquidationPx", "marginUsed", "unrealizedPnl")}
                         for p in d.get("assetPositions") or []]}
    if asset is not None:
        _, ctx = info({"type": "activeAssetCtx", "coin": str(uni(asset)["index"])})
        _, bk = info({"type": "l2Book", "coin": str(uni(asset)["index"])})
        rec["mark"] = ctx.get("markPx") if isinstance(ctx, dict) else None
        rec["oracle"] = ctx.get("oraclePx") if isinstance(ctx, dict) else None
        lv = (bk.get("levels") if isinstance(bk, dict) else None) or [[], []]
        rec["bid"] = lv[0][0]["px"] if lv[0] else None
        rec["ask"] = lv[1][0]["px"] if lv[1] else None
    return rec


def probe_auth(asset, agent_pk):
    """harmless liveness check: post-only far from the touch, then cancel by cloid."""
    bid = float(((info({"type": "l2Book", "coin": str(uni(asset)["index"])})[1])["levels"][0][0]["px"]))
    cl = "probe%d" % (now_ms() % 10 ** 7)
    env = sign_agent(order(asset, "buy", px(asset, bid * 0.5), qty(asset, 10), tif="Alo", cloid=cl), agent_pk, now_ms())
    code, r = exchange(env)
    ok = isinstance(r, dict) and r.get("status") == "ok"
    if ok:
        exchange(sign_agent(cancel(asset, cl), agent_pk, now_ms()))
    return ok, json.dumps(r)[:180]


def ev(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")
        f.flush()


if __name__ == "__main__":
    # fill accounts.json with {"A": {"main_pk":..,"main":..,"agent_pk":..,"agent":..}, ...}
    here = os.path.dirname(os.path.abspath(__file__))
    ACC = json.load(open(os.path.join(here, "accounts.json")))
    asset = int(uni("LDO-USDC")["index"])
    print("instrument id:", asset, "tick:", uni(asset)["priceTick"])
    print("auth probe:", probe_auth(asset, ACC["A"]["agent_pk"]))
    print("snapshot:", json.dumps(snapshot(ACC["A"]["main"], asset))[:400])
