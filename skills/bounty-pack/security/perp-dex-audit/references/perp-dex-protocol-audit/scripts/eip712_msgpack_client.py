"""Generic EIP-712 + MessagePack signing/transport harness for exchange-style trading APIs.

Validated byte-for-byte against TxFlow testnet's published vectors (see
references/txflow-testnet-case.md). Adapt DOMAIN / action builders to the target.

Requires: eth_account, eth_utils, requests.
`self_check()` proves the encoder + signer before you touch the live API — run it first.
"""
import json, time
import requests
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

# ---- network / domain (EDIT per target) ----
RPC = "https://rpc.<target>"
API = "https://api.<target>"
DOMAIN = {"name": "TxFlow-Testnet", "version": "1", "chainId": 2511,
          "verifyingContract": "0x0000000000000000000000000000000000000000"}
CHAIN_ID, API_VERSION = 2511, 1
USDC = "USDC:0x0000000000000000000000000000000000000000"

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
                  "Origin": "https://<frontend>", "Referer": "https://<frontend>/"})


# ================= canonical MessagePack encoder =================
# Keys are preserved in insertion order; null values are omitted (nulls must not be encoded).
def _mp_int(n):
    if n >= 0:
        if n < 0x80: return bytes([n])
        if n <= 0xff: return b"\xcc" + n.to_bytes(1, "big")
        if n <= 0xffff: return b"\xcd" + n.to_bytes(2, "big")
        if n <= 0xffffffff: return b"\xce" + n.to_bytes(4, "big")
        return b"\xcf" + n.to_bytes(8, "big")
    if n >= -32: return bytes([0xe0 | (n + 32)])
    if n >= -128: return b"\xd0" + n.to_bytes(1, "big", signed=True)
    if n >= -32768: return b"\xd1" + n.to_bytes(2, "big", signed=True)
    if n >= -2147483648: return b"\xd2" + n.to_bytes(4, "big", signed=True)
    return b"\xd3" + n.to_bytes(8, "big", signed=True)


def _mp_str(s):
    b = s.encode(); n = len(b)
    if n < 32: return bytes([0xa0 | n]) + b
    if n <= 0xff: return b"\xd9" + bytes([n]) + b
    if n <= 0xffff: return b"\xda" + n.to_bytes(2, "big") + b
    return b"\xdb" + n.to_bytes(4, "big") + b


def _mp_bin(b):
    n = len(b)
    if n <= 0xff: return b"\xc4" + bytes([n]) + b
    if n <= 0xffff: return b"\xc5" + n.to_bytes(2, "big") + b
    return b"\xc6" + n.to_bytes(4, "big") + b


def mp(obj):
    if obj is None: return b"\xc0"
    if obj is True: return b"\xc3"
    if obj is False: return b"\xc2"
    if isinstance(obj, int): return _mp_int(obj)
    if isinstance(obj, float): return b"\xcb" + __import__("struct").pack(">d", obj)
    if isinstance(obj, str): return _mp_str(obj)
    if isinstance(obj, (bytes, bytearray)): return _mp_bin(bytes(obj))
    if isinstance(obj, (list, tuple)):
        n = len(obj)
        head = bytes([0x90 | n]) if n < 16 else (b"\xdc" + n.to_bytes(2, "big") if n <= 0xffff else b"\xdd" + n.to_bytes(4, "big"))
        return head + b"".join(mp(x) for x in obj)
    if isinstance(obj, dict):
        items = [(k, v) for k, v in obj.items() if v is not None]
        n = len(items)
        head = bytes([0x80 | n]) if n < 16 else (b"\xde" + n.to_bytes(2, "big") if n <= 0xffff else b"\xdf" + n.to_bytes(4, "big"))
        return head + b"".join(mp(k) + mp(v) for k, v in items)
    raise TypeError(f"unsupported msgpack type {type(obj)}")


# ================= EIP-712 =================
_AGENT_TYPES = {
    "EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                     {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}],
    "Agent": [{"name": "txflowNetwork", "type": "string"}, {"name": "chainId", "type": "uint32"},
              {"name": "apiVersion", "type": "uint32"}, {"name": "connectionId", "type": "bytes32"}],
}


def connection_id(action, nonce, vault_address=None):
    body = {k: v for k, v in action.items() if k != "type"}      # type field removed
    pre = mp(body) + nonce.to_bytes(8, "big")
    pre += (b"\x01" + bytes.fromhex(vault_address[2:])) if vault_address else b"\x00"
    return "0x" + keccak(pre).hex()


def _sign_typed(types, primary, message, key, domain=None):
    tm = {"types": types, "primaryType": primary, "domain": domain or DOMAIN, "message": message}
    signable = encode_typed_data(full_message=tm)
    sig = Account.sign_message(signable, private_key=key)
    signing_hash = "0x" + keccak(b"\x19\x01" + signable.header + signable.body).hex()
    return sig, signing_hash


def sign_agent(action, key, nonce, vault_address=None):
    cid = connection_id(action, nonce, vault_address)
    msg = {"txflowNetwork": DOMAIN["name"], "chainId": CHAIN_ID, "apiVersion": API_VERSION, "connectionId": cid}
    sig, sh = _sign_typed(_AGENT_TYPES, "Agent", msg, key)
    env = {"action": action, "signature": {"r": hex(sig.r), "s": hex(sig.s), "v": sig.v},
           "nonce": nonce, "vaultAddress": vault_address, "signatureChainId": None}
    return env, cid, sh


def sign_direct(action, key, types_map, primary, message, chain_id=None, vault_address=None):
    dom = dict(DOMAIN)
    if chain_id: dom["chainId"] = chain_id
    sig, sh = _sign_typed(types_map, primary, message, key, dom)
    env = {"action": action, "signature": {"r": hex(sig.r), "s": hex(sig.s), "v": sig.v},
           "nonce": action.get("nonce"), "vaultAddress": vault_address, "signatureChainId": chain_id}
    return env, sh


# ================= transport =================
def info(body, host=API):
    r = S.post(f"{host}/info", data=json.dumps(body), timeout=30)
    try: return r.status_code, r.json()
    except Exception: return r.status_code, r.text


def exchange(env, host=API):
    r = S.post(f"{host}/exchange", data=json.dumps(env), timeout=30)
    try: return r.status_code, r.json()
    except Exception: return r.status_code, r.text


def now_ms():
    return int(time.time() * 1000)


# ================= action builders (EDIT per target; these are the TxFlow shape) =================
def order(asset, side, px, sz, reduce_only=False, tif="Gtc", cloid=None, grouping="na"):
    o = {"a": asset, "b": side in ("buy", "B", True), "p": str(px), "s": str(sz),
         "r": bool(reduce_only), "t": {"limit": {"tif": tif}}}
    if cloid: o["c"] = cloid
    return {"type": "order", "grouping": grouping, "orders": [o]}


def market_order(asset, side, px, sz, reduce_only=False, cloid=None):
    return order(asset, side, px, sz, reduce_only, "FrontendMarket", cloid)


def cancel_cloid(asset, cloid):
    return {"type": "cancelByCloid", "cancels": [{"asset": asset, "cloid": cloid}]}


def set_leverage(asset, leverage, margin_mode="cross"):
    return {"type": "updateLeverage", "asset": asset, "leverage": leverage, "marginMode": margin_mode}


def set_margin_mode(asset, is_cross):
    return {"type": "updateMarginMode", "asset": asset, "isCross": bool(is_cross)}


def set_pos_mode(is_oneway):
    return {"type": "updatePositionMode", "isOneway": bool(is_oneway)}


def set_isolated_margin(asset, is_buy, ntli):
    # ntli is an INTEGER string: "1000000" == 1 USDC
    return {"type": "updateIsolatedMargin", "asset": asset, "isBuy": bool(is_buy), "ntli": str(ntli)}


# ================= reads =================
def state(user, account_type="perp"):
    return info({"type": "clearinghouseState", "user": user, "accountType": account_type})


def book(coin):
    return info({"type": "l2Book", "coin": str(coin)})


def ctx(asset):
    return info({"type": "activeAssetCtx", "coin": str(asset)})


def meta_detail(base):
    return info({"type": "perpMetaDetail", "assetName": base})   # BASE asset, not "XXX-USDC"


def historical_orders(user):
    return info({"type": "historicalOrders", "user": user})


def user_fills(user):
    return info({"type": "userFills", "user": user})


# ================= helpers =================
def rpx(px, tick):
    """Round a price to the instrument tick. Never use float formatting — the engine rejects it."""
    n = int(round(float(px) / tick)); s = f"{n * tick:.10f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def self_check():
    """Prove the encoder + signer against TxFlow's published vectors. Run BEFORE any live call."""
    key = "0x" + "ab" * 32
    assert Account.from_key(key).address.lower() == "0xe239cdc5fbe977a8a141b72194d3cf8c41bc5bc6"
    act = {"type": "order", "grouping": "na",
           "orders": [{"a": 1, "b": True, "p": "50000.0", "s": "0.01", "r": False,
                       "t": {"limit": {"tif": "Gtc"}}}]}
    mpb = mp({k: v for k, v in act.items() if k != "type"}).hex()
    assert mpb == ("REDACTED_********30303030"
                   "2e30a173a4302e3031a172c2a17481a56c696d697481a3746966a3477463"), "msgpack mismatch"
    env, cid, sh = sign_agent(act, key, 1700000000000)
    assert cid == "0xREDACTED_********", "connectionId mismatch"
    assert sh == "0xREDACTED_********", "signingHash mismatch"
    assert env["signature"]["r"] == "0xREDACTED_********"
    assert env["signature"]["s"] == "0xREDACTED_********"
    assert env["signature"]["v"] == 27
    print("self_check OK — encoder + signer match the published vectors")


if __name__ == "__main__":
    self_check()
