# On-chain property probes — EVM + SVM

Read-only probes that turn a documentation claim into a yes/no fact. Nothing here signs or sends a
transaction. Verified live 2026-10-30 against relay.link (Solana mainnet + EVM chains).

---

## SVM (Solana) — upgradeability

### The loader is the answer

A Solana program's mutability is decided by **which loader owns the program account**:

| Owner | Meaning |
|---|---|
| `BPFLoaderUpgradeab1e11111111111111111111111` | **upgradeable** — logic can be replaced |
| `BPFLoader2111111111111111111111111111111111` | legacy, non-upgradeable |
| `BPFLoader1111111111111111111111111111111111` | deprecated, non-upgradeable |

`BPFLoaderUpgradeab1e…` is the whole finding. Everything else is detail.

```python
import json, urllib.request
RPC = "https://api.mainnet-beta.solana.com"
UPGRADEABLE = "BPFLoaderUpgradeab1e11111111111111111111111"

def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

v = rpc("getAccountInfo", [PROGRAM_ID, {"encoding":"base64"}])["result"]["value"]
print(v["owner"], v["executable"])     # owner == UPGRADEABLE -> falsifies "non-upgradable"
```

### Reading the upgrade authority (ProgramData layout)

The program account holds a 36-byte `Program` state: 4-byte little-endian tag (`2` = Program) then
the 32-byte ProgramData address. The ProgramData account holds:

| offset | size | field |
|---|---|---|
| 0 | 4 | tag, little-endian — `3` = ProgramData |
| 4 | 8 | last deploy slot, little-endian |
| 12 | 1 | `Option<Pubkey>` discriminator — **`1` = authority present** |
| 13 | 32 | upgrade authority pubkey (only if discriminator == 1) |
| 45 | — | program bytecode |

```python
import base64
A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58(b):
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, rem = divmod(n, 58); s = A[rem] + s
    for x in b:
        if x == 0: s = "1" + s
        else: break
    return s

raw = base64.b64decode(rpc("getAccountInfo", [PROGRAM_ID,
        {"encoding":"base64","dataSlice":{"offset":0,"length":36}}])["result"]["value"]["data"][0])
programdata_addr = b58(raw[4:36])

d = base64.b64decode(rpc("getAccountInfo", [programdata_addr,
        {"encoding":"base64"}])["result"]["value"]["data"][0])
tag3      = int.from_bytes(d[0:4],  "little")   # 3
slot      = int.from_bytes(d[4:12], "little")   # last deploy slot
has_auth  = d[12]                               # 1 = upgradeable by someone
authority = b58(d[13:45]) if has_auth == 1 else None
```

### Is the authority a multisig or a bare key?

```python
av = rpc("getAccountInfo", [authority, {"encoding":"base64"}])["result"]["value"]
if av is None:
    print("no account data -> plain system keypair")
else:
    print("owner:", av["owner"], "| executable:", av["executable"], "| data:", len(av["data"][0]))
```

- **owner == `11111111111111111111111111111111` (System Program), `executable == False`, `data == 0`**
  → a plain keypair. One person or one service holds it. Not a multisig, no on-chain approval flow.
- Any other owner → could be Squads / SPL Governance / a program vault. Identify the program before
  claiming anything about it.

Confirm the key is live with `getSignaturesForAddress` (limit 3) — a recently-signed authority is
not a dead placeholder.

### Worked result (relay.link, 2026-10-30)

Docs: *"Each contract is non-upgradable, meaning its logic cannot be changed after deployment"* —
explicitly scoped to *"EVM and Solana chains"*.

| Program | Loader | has_auth | Authority | Authority type |
|---|---|---|---|---|
| `99vQwtBw…SrN2` relay-depository | `BPFLoaderUpgradeab1e…` | 1 | `6Bz8AWWi…aMWD` | System-owned keypair |
| `DPArtTLbE…jwXUr` relay-forwarder | `BPFLoaderUpgradeab1e…` | 1 | `6Bz8AWWi…aMWD` | System-owned keypair |

Both upgradeable, **one shared single keypair**, key active (recent signature). Docs claim
non-upgradable. Divergence confirmed, severity bounded to S1 by the program's own
"admin-only = S1" rule.

---

## EVM — proxy / upgradeability

```bash
# 1. is it a proxy at all? EIP-1967 implementation slot
cast storage <ADDR> 0xREDACTED_******** --rpc-url $RPC
# 2. EIP-1967 admin slot
cast storage <ADDR> 0xREDACTED_******** --rpc-url $RPC
# 3. does the bytecode even contain upgrade entrypoints?
cast codesize <ADDR> --rpc-url $RPC
# grep selectors: upgradeTo(address)=0x3659cfe6, upgradeToAndCall(address,bytes)=0x4f1ef286
```

Non-zero admin/implementation slot → the contract is upgradeable regardless of what the docs say.

**UUPS vs Transparent vs Beacon** changes where the authority lives (`_authorizeUpgrade` in the
implementation for UUPS; the admin slot for transparent; the beacon contract for beacon proxies).
Read the verified source before naming the holder.

## EVM — is the owner a multisig?

```bash
cast call <ADDR> 'owner()(address)' --rpc-url $RPC
cast codesize <OWNER> --rpc-url $RPC        # 0 = EOA
# if it has code, check Safe:
cast call <OWNER> 'getThreshold()(uint256)' --rpc-url $RPC
cast call <OWNER> 'getOwners()(address[])'  --rpc-url $RPC
```

`codesize == 0` on the owner → EOA. That falsifies any "protected by a Security Council multisig"
claim. Seen on relay: `owner() = 0xf61a3051…775a` on every EVM depository, a single EOA.

## Role-based claims

When docs say "only addresses holding ROLE_X can do Y":

```bash
cast call <ADDR> 'ROLE_X()(bytes32)' --rpc-url $RPC      # reverts -> no such role
cast selectors <ADDR> --rpc-url $RPC | grep -i role      # does the selector exist at all?
```

A revert on the role getter means the deployed contract has **no role model** — the docs are
describing a different build. Combine with a source grep of the repo the docs name as the source:
`grep -rn 'ROLE_X\|hasRole\|AccessControl' <repo>` returning 0 hits is corroborating evidence.

## API-side claims ("key required")

```bash
for v in "" " " "null" "undefined" "*" "[]"; do
  curl -s -o /dev/null -w "$v -> %{http_code}\n" -H "x-api-key: $v" "$B/protected"
done
curl -s -o /dev/null -w "dup -> %{http_code}\n" -H "x-api-key: a" -H "x-api-key: " "$B/protected"
```

Two different 401 **bodies** (`Missing x-api-key header` vs `Unauthorized: Check API Key`) is normal
layering, not an oracle. An oracle would be a different **status** (403 vs 401) or a measurable
timing difference for a valid key.

---

## Safety

All probes above are `getAccountInfo` / `getCode` / `eth_call` / `cast call` / `GET`. They read public
state. Nothing is signed, no transaction is created, no funds move. State that explicitly in the
report — it is what makes a divergence finding safe for the vendor to receive.
