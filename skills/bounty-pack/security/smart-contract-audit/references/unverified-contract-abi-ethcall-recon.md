# Unverified / closed-source contract recon — ABI + eth_call access-control test

When a target contract is **unverified on Etherscan** (no source, no ABI) and the source-recovery
paths in this skill fail, you can still characterise its **access-control surface** without any
source. This is the ChainPort bridge-Vault case (2026-10): proxy `0xca9a74c…` → impl
`0xa3e950bf…`, both unverified.

## 1. Resolve the proxy → implementation, then try source
- Etherscan **V2** `getsourcecode` on the proxy returns `Proxy=1` + `Implementation=<impl addr>`.
  Fetch the **implementation** address for the real source/ABI.
- ⛔ **Etherscan V1 is dead.** `api.etherscan.io/api` (no `chainid`) answers
  `You are using a deprecated V1 endpoint, switch to Etherscan API V2`. Use:
  `https://api.etherscan.io/v2/api?chainid=1&module=contract&action=getsourcecode&address=0x…&apikey=KEY`
  Key on this host: `~/.chiper/skills/bounty-pack/secrets/etherscan.key`.
- If impl is also `SourceCode == ""` → closed-source. Note it as the barrier; do NOT claim "no bugs".

## 2. heimdall still gives you the ABI (even when source-gen fails)
- `heimdall decompile "<runtime-bytecode>"` prints the **ABI** (function names + input types +
  `stateMutability`) to stdout. `-o <dir>` writes `<dir>/abi.json`.
- ⛔ `--include-yul` / `--include-sol` are **beta and can emit nothing** (ran clean, 0 lines, only
  warnings like `couldn't find any resolved matches for '<selector>'`). Do not block on decompiled
  source — the ABI alone is enough for the access-control sweep.
- Get runtime bytecode via Etherscan V2 `module=proxy&action=eth_getCode` on the **implementation**.

## 3. Dynamic access-control sweep via eth_call (the durable technique)
For every function in the heimdall ABI, call it from an **arbitrary address** and read the result:
- `REVERT`  → gated (protected) — good.
- `OK`/`0x` → for a **state-changing** fn this is a candidate unprotected function → investigate.
- `view`/`pure` fns legitimately return `OK` (public getters) — not findings.

```python
from Crypto.Hash import keccak
def sel(sig):
    k=keccak.new(digest_bits=256); k.update(sig.encode()); return k.hexdigest()[:8]
def enc(inputs, token):            # dummy args by type
    d=""
    for i in inputs:
        t=i["type"]
        d += token[2:].rjust(64,"0") if t=="address" else "1".rjust(64,"0")
    return d
# eth_call {to: proxy, data: "0x"+sel(f"{name}({types})")+enc(inputs,USDT), from: ATTACKER}
# public RPCs that honour a custom `from`: ethereum-rpc.publicnode.com, eth.llamarpc.com
```
- Iterate `stateMutability` in `{view,pure}` = skip; `{nonpayable,payable}` = must REVERT from a
  non-privileged `from`. Report a **table** (fn → REVERT/OK). "All 16 state-changing fns REVERT"
  is a real, reportable *negative* — write it down with the evidence.
- Named admin setters (`setBridge`, `setGateKeeper`, `setChainportCongress`, `freeze`, `unfreeze`)
  and the `Unresolved_*` deposit/withdraw variants all REVERTED on ChainPort → access control solid.

## 4. Honest boundary (do not overclaim)
This sweep proves **functions are gated**. It does NOT prove the fund-loss logic is safe:
validator-signature verification, replay protection, deposited-vs-withdrawn accounting, and
wrapped-token mint authority all need **source**. If the contract is closed-source, state exactly
that as the blocker and offer the source-dependent next step — never "audited, no bugs".

## 5. Wrapped-token addresses from a bridge API can be MISLABELED
`/api/port/tokens` on ChainPort returned COPI's EVM approval address as an unrelated verified
ERC20 ("XNLToken", Ownable+Pausable+vesting, `_mint` internal, no bridge ref). The
`tokens_to_be_approved_by_exact_user_amount` field is a spender/approval target, **not necessarily
the wrapped token**. Verify a token contract actually references the bridge before auditing it as
the protocol's minter.
