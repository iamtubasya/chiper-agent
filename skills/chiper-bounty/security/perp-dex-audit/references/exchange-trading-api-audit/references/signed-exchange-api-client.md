# Signed Exchange API Client — EIP-712 + MessagePack reference

Reusable pattern for venues whose **writes are signed** (EIP-712 typed data) and whose
**action bodies are hashed via a compact binary encoding** (MessagePack here). Worked example =
TxFlow testnet (`TxFlow-Testnet`, chainId `2511`), but the shape generalises: swap the domain,
the action map, and the preimage layout.

> Golden rule: **reproduce the vendor's published test vectors byte-for-byte before sending
> any live write.** If a `signingHash` matches and the derived address matches, the rest of the
> client is trustworthy. If you skip this you will burn hours on `failed to recover signer`
> with no idea which field is wrong.

## Pieces

1. **EIP-712 domain** — four fields (`name`, `version`, `chainId`, `verifyingContract`).
   Per-network; docs publish the exact strings and the resulting `domainSeparator`.
2. **Two signing flows** (typical):
   - *Direct* — account-level actions signed as their own typed struct
     (`approveAgent`, `tokenSend`, `withdraw3`, …). Signer = account key.
   - *Agent / session* — trading actions (order, cancel, modify, margin) are **not** typed data:
     the body is encoded to a 32-byte `connectionId` and wrapped in one fixed struct
     (`Agent(network,chainId,apiVersion,connectionId)`). Signer = a key the account authorised.
3. **Request envelope** — `{action, signature:{r,s,v}, nonce, vaultAddress, signatureChainId}`.
   `nonce` is a **millisecond timestamp** (not a counter), usually repeated inside the action body.

## Canonical MessagePack encoder (why hand-rolled)

A generic msgpack library may reorder keys, emit a non-minimal int, or turn a Python `dict` into
an array — any of those changes the bytes and the hash. Encode **explicitly**, preserving field
order and using the most compact form. Nulls are **omitted**, not encoded as nil.

```python
import struct
def _mp_int(n):
    if n >= 0:
        if n < 0x80: return bytes([n])
        if n <= 0xff: return b"\xcc"+n.to_bytes(1,"big")
        if n <= 0xffff: return b"\xcd"+n.to_bytes(2,"big")
        if n <= 0xffffffff: return b"\xce"+n.to_bytes(4,"big")
        return b"\xcf"+n.to_bytes(8,"big")
    if n >= -32: return bytes([0xe0 | (n+32)])
    if n >= -128: return b"\xd0"+n.to_bytes(1,"big",signed=True)
    if n >= -32768: return b"\xd1"+n.to_bytes(2,"big",signed=True)
    if n >= -2147483648: return b"\xd2"+n.to_bytes(4,"big",signed=True)
    return b"\xd3"+n.to_bytes(8,"big",signed=True)

def _mp_str(s):
    b=s.encode(); n=len(b)
    if n<32: return bytes([0xa0|n])+b
    if n<=0xff: return b"\xd9"+bytes([n])+b
    if n<=0xffff: return b"\xda"+n.to_bytes(2,"big")+b
    return b"\xdb"+n.to_bytes(4,"big")+b

def _mp_bin(b):
    n=len(b)
    if n<=0xff: return b"\xc4"+bytes([n])+b
    if n<=0xffff: return b"\xc5"+n.to_bytes(2,"big")+b
    return b"\xc6"+n.to_bytes(4,"big")+b

def mp(o):
    if o is None: return b"\xc0"
    if o is True: return b"\xc3"
    if o is False: return b"\xc2"
    if isinstance(o,int): return _mp_int(o)
    if isinstance(o,float): return b"\xcb"+struct.pack(">d",o)
    if isinstance(o,str): return _mp_str(o)
    if isinstance(o,(bytes,bytearray)): return _mp_bin(bytes(o))
    if isinstance(o,(list,tuple)):
        n=len(o); head=bytes([0x90|n]) if n<16 else (b"\xdc"+n.to_bytes(2,"big") if n<=0xffff else b"\xdd"+n.to_bytes(4,"big"))
        return head+b"".join(mp(x) for x in o)
    if isinstance(o,dict):
        items=[(k,v) for k,v in o.items() if v is not None]        # omit nulls; preserve order
        n=len(items); head=bytes([0x80|n]) if n<16 else (b"\xde"+n.to_bytes(2,"big") if n<=0xffff else b"\xdf"+n.to_bytes(4,"big"))
        return head+b"".join(mp(k)+mp(v) for k,v in items)
    raise TypeError(type(o))
```

## Agent-action `connectionId`

```
connectionId = keccak256( msgpack(action_without_type) ‖ nonce_BE8 ‖ vault_flag )
# vault_flag = b"\x00" when no vault, else b"\x01" + 20 address bytes
```

## Full check against published vectors (do this first)

```python
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

DOMAIN = {"name":"TxFlow-Testnet","version":"1","chainId":2511,
          "verifyingContract":"0x0000000000000000000000000000000000000000"}
AGENT_TYPES = {
  "EIP712Domain":[{"name":"name","type":"string"},{"name":"version","type":"string"},
                  {"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"}],
  "Agent":[{"name":"txflowNetwork","type":"string"},{"name":"chainId","type":"uint32"},
           {"name":"apiVersion","type":"uint32"},{"name":"connectionId","type":"bytes32"}]}

def signing_hash(types, primary, message, domain=DOMAIN):
    m = encode_typed_data(full_message={"types":types,"primaryType":primary,"domain":domain,"message":message})
    return "0x"+keccak(b"\x19\x01"+m.header+m.body).hex(), m

# order vector (docs): nonce=1700000000000, key 0xabab..abab
act = {"grouping":"na","orders":[{"a":1,"b":True,"p":"50000.0","s":"0.01","r":False,"t":{"limit":{"tif":"Gtc"}}}]}
cid = "0x"+keccak(mp(act)+ (1700000000000).to_bytes(8,"big") + b"\x00").hex()
sh,_ = signing_hash(AGENT_TYPES,"Agent",
        {"txflowNetwork":"TxFlow-Testnet","chainId":2511,"apiVersion":1,"connectionId":cid})
assert sh == "0xREDACTED_********"
sig = Account.sign_message(_[1] if False else encode_typed_data(full_message={
        "types":AGENT_TYPES,"primaryType":"Agent","domain":DOMAIN,
        "message":{"txflowNetwork":"TxFlow-Testnet","chainId":2511,"apiVersion":1,"connectionId":cid}}),
        private_key="0x"+"ab"*32)
assert hex(sig.r)=="0xREDACTED_********"
assert hex(sig.s)=="0xREDACTED_********"
assert sig.v==27
```

`v` in JSON is `27`/`28` (`27 + recoveryId`). `signatureChainId` overrides only the EIP-712
domain chain for *direct* actions; agent actions ignore it.

## Action bodies you will reuse

- `order` — `{grouping, orders:[{a,b,p,s,r,t,c}]}`. `a`=asset/num-index, `b`=buy, `p`=px str,
  `s`=size str, `r`=reduce-only, `t`=`{limit:{tif:Gtc|Ioc|Alo|Gtd|FrontendMarket}}` (or
  `{trigger:{isMarket,triggerPx,tpsl}}` under grouping `normalTpsl`/`positionTpsl`/`normalTrigger`),
  `c`=client order id (cloid). Prices/sizes are **strings**, hashed verbatim ("50000.0" ≠ "50000").
- `cancel` — `{cancels:[{asset,oid}]}` (abbrev). `cancelByCloid` — `{cancels:[{asset,cloid}]}` (**full names**).
- `modify2` — body key is **`order`** (singular): `{order:{o,p,s}}`; only price+size amendable;
  RO/side/tif preserved.
- `updateLeverage {asset,leverage,marginMode}` · `updateMarginMode {asset,isCross}` ·
  `updatePositionMode {isOneway}` · `updateIsolatedMargin {asset,isBuy,ntli}` (ntli = integer string, 1e6 = 1 USDC).
- `approveAgent` (direct) — `ApproveAgent(network,chainId,apiVersion,agentAddress,agentName,nonce)`.
- `tokenSend` (direct) — `TransferToken(...)` between own sub-accounts, `SendToken(...)` with `toAddress`.
- `withdraw3` (direct) — `Withdraw3(string network,address destination,string signatureChainId,address tokenAddress,string amount,uint64 nonce)`
  — note the **different field order + a string chain-id**; the common "failed to recover signer"
  is almost always this struct being copied from the wrong action.

## Response envelope / statuses

- `{\"status\":\"ok\",\"response\":{\"type\":\"<Action>\",\"data\":{\"statuses\":[\"success\"]}}}` — accepted.
- **Outcome/prediction orders can be asynchronous**: `{\"status\":\"ok\",\"traceId\":\"<hex>\"}` =
  *queued, not matched*. Confirm via `historicalOrders` / `userFills` / the order-update channel.
- **Always cross-check the HTTP "ok" against the terminal ledger** — that gap is where the
  false-acknowledgement class of bugs hides (see parent SKILL.md §4).
