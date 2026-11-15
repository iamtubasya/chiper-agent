# BEAM oracle IDL recovery + full on-chain decode (no source repo)

> Round-2 technique from LoopScale 2026-10-19. Round 1 gave up on BEAM ("layout
> unclear"); round 2 cracked it by recovering the IDL from on-chain zlib and
> decoding 133 price entries. This is the highest-value black-box technique for
> any Solana program whose source is closed.

## 1. Recover the Anchor IDL from on-chain (no source repo needed)

Anchor programs store their IDL in a dedicated account. The PDA derivation
(`findProgramAddress(["anchor:idl"])`) often fails. **Faster: scan every program
account for zlib-compressed JSON.**

```python
import json, urllib.request, base64, zlib

def rpc(method, params):
    r = urllib.request.Request(RPC, data=json.dumps(
        {"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read())

PROGRAM = "<program_pubkey>"
res = rpc("getProgramAccounts", [PROGRAM, {"encoding":"base64","limit":100}])
for a in res["result"]:
    raw = base64.b64decode(a["account"]["data"][0])
    # Anchor IDL: 8-byte disc + 32-byte authority + 4-byte len + zlib JSON
    # zlib magic at offset 44: 0x78 0x9c (default), 0x78 0x01, 0x78 0xda
    if len(raw) > 100 and raw[44:46] in [b'\x78\x9c', b'\x78\x01', b'\x78\xda']:
        idl = json.loads(zlib.decompress(raw[44:]))
        print(f"IDL at {a['pubkey']}: {len(idl.get('instructions',[]))} instructions")
```

LoopScale BEAM result: 4 instructions (`get_price_entry`, `initialize`,
`update_asset`, `write_price_entry`), `BeamAccount` type, 12 error codes.
`write_price_entry` has NO signer but requires `instructions_sysvar` → CPI-only.

## 2. Decode BeamAccount state

Layout from the recovered IDL: disc(8) + version(1) + authority(32) +
currency_id([u8;8]) + _padding([u8;39]) + pricing_map(raw) + pricing_metadata_map(raw).

```python
off = 8
version = raw[off]; off += 1
authority = b58e(raw[off:off+32]); off += 32
currency_id = raw[off:off+8]; off += 8
off += 39  # padding
pricing_map = raw[off:off+38792]  # BeamPricingMap.raw
```

## 3. Decode price entries (152-byte stride)

pricing_map entries start at offset 16 within the map, stride 152:

| entry offset | field | type |
|---|---|---|
| 32 (32 bytes) | asset mint | pubkey |
| 64 (8 bytes) | price | u64 LE, 18-decimal fixed point |
| 112 (8 bytes) | timestamp | u64 LE, unix seconds |

```python
import struct
now = int(time.time())
for i in range(256):
    eoff = 16 + i * 152
    entry = pm[eoff:eoff+152]
    if all(b == 0 for b in entry): continue
    mint = b58e(entry[32:64])
    price = struct.unpack_from("<Q", entry, 64)[0] / 1e18
    ts = struct.unpack_from("<Q", entry, 112)[0]
    age_h = (now - ts) / 3600
    # cross-reference with market config maxAge
```

LoopScale result: 133 entries decoded. ~30 stale (>24h), 2 never-updated (ts=0).

## 4. Cross-reference staleness vs market maxAge

The highest-value check on a lending protocol: **does the protocol accept stale
oracle prices?**

1. Decode all oracle entries (step 3) → find old timestamps.
2. Pull market configs from API → `maxAge`, `ltv`, `liquidationThreshold`,
   `oracleType` per asset.
3. Cross-reference: assets where `oracle_age > maxAge` AND `ltv > 0` are candidates.
4. **Verify exploitability before reporting.**

LoopScale result: 6+ assets had BEAM price 65+ hours old while market
`maxAge=900s` (15 min), LTV 40-90%, verified=True. Three active loans used a
stale asset as collateral.

**Verification showed FAIL-SAFE, not bug:**
- Withdraw stale collateral → `"collateral valued at zero because no fresh oracle
  price is available"` — protocol locks the collateral.
- Repay → SUCCESS (no price needed).
- No overborrow path exists.

## 5. simulateTransaction is unreliable for API-built txs

`simulateTransaction` with `sigVerify:False` on API-built transactions often
returns `err: None` with **0 logs** — the RPC silently skips execution. Do NOT
treat this as proof of on-chain acceptance.

**Instead:** check actual on-chain transaction history:
```python
res = rpc("getSignaturesForAddress", [CORE_PROGRAM, {"limit":500}])
failed = [s for s in res["result"] if s.get("err")]
# 0 failed in 500 tx = mature protocol with working controls
```

## 6. ALT (Address Lookup Table) parsing for v0 transactions

v0 txs resolve account indices via ALT. ALT account layout:
- byte 0: enum variant (0=Uninitialized, 1=Deallocated, 2=Active)
- If Active(2): last_extended_slot(u64) + start_index(u8) + authority_option(u8) + [authority(32)]
- Then: Vec<Pubkey> (u64 length + 32 bytes each)

**Deallocated ALTs (variant=1) can still be referenced** — the runtime resolves
them read-only. Don't assume a deallocated ALT invalidates the tx.
