# Solana sBPF deployed-bytecode decompilation (no source)

When a Solana program's source is closed but the IDL is public, you can still extract the
**deployed sBPF ELF binary** from mainnet and mine it for source paths, error strings, instruction
names, and auth-check evidence. This is the on-chain equivalent of reading a compiled binary — it
does not replace an audit, but it tells you what the program validates and where to aim.

Worked on LoopScale (2026-10-19): core program 3.4 MB, BEAM oracle 680 KB. Recovered 42
instruction names, 150 error codes, and 40+ `programs/<name>/src/...` file paths from `.rodata`
alone, then cross-referenced against the IDL to confirm the auth model.

## 1. Extract the ELF from the programdata account

The program account is a 36-byte pointer; the ELF lives in the programdata account behind a
12-byte Anchor header (variant + slot). The ELF magic is **not** at offset 0 of the programdata
account — search for it.

```python
# program account -> programdata address
info = rpc("getAccountInfo", [prog, {"encoding": "base64"}])
raw = base64.b64decode(info["result"]["value"]["data"][0])
programdata = b58encode(raw[4:36])          # 4-byte slot + 32-byte pubkey

# programdata account -> ELF (magic is NOT at a fixed offset; find it)
pd = base64.b64decode(rpc("getAccountInfo", [programdata, {"encoding":"base64"}])
                        ["result"]["value"]["data"][0])
elf_off = pd.find(b'\x7fELF')               # was offset 45 on LoopScale
elf = pd[elf_off:]
```

⛔ **Do not assume a fixed header size.** The `01c02d84` sBPF magic precedes the ELF magic and the
gap varies. Always `find(b'\x7fELF')`.

## 2. Parse the ELF section table

sBPF ELF is 64-bit LE, `e_machine = 0xf7` (BPF). Section headers give you `.text` (code),
`.rodata` (strings + constants), `.data.rel.ro` (relocated data).

```python
e_shoff     = int.from_bytes(elf[40:48], 'little')
e_shentsize = int.from_bytes(elf[58:60], 'little')
e_shnum     = int.from_bytes(elf[60:62], 'little')
e_shstrndx  = int.from_bytes(elf[62:64], 'little')
# section i header at e_shoff + i*e_shentsize:
#   name(4) type(4) flags(8) addr(8) offset(8) size(8) ...
```

LoopScale core: `.text` 3.1 MB, `.rodata` 63 KB, `.data.rel.ro` 32 KB, `.rel.dyn` 172 KB.

## 3. Mine `.rodata` for strings — the highest-value 10 minutes

`re.findall(rb'[\x20-\x7e]{6,}', rodata)` on 63 KB of rodata yielded ~145 strings, of which ~94
were security-relevant. What to grep for:

| pattern | what it gives you |
|---|---|
| `Instruction: X` | **every instruction name** — cross-check against the IDL for missing/extra handlers |
| `Error Code: X. Error Number: N. Error Message: ...` | **the full error enum** — a free checklist of what the program validates |
| `programs/<name>/src/...rs` | **source file paths** — reveals module structure and where logic lives |
| `assertion failed: ...` | **runtime invariants** — each one is a check you should try to violate |
| `Arithmetic error in <file>:<line>` | **every arithmetic site** — overflow/underflow hunt list |
| `Invalid X` / `X is required` | validation points; absence of an expected check is the lead |
| `not yet implemented` | unreached code paths — check if any public instruction can reach them |
| `Protocol is frozen` / `must co-sign` | admin/emergency mechanics worth probing |

**Cross-reference discipline:** every string is a *claim* about the program. Confirm against the
IDL and against live behaviour before treating any of it as a finding. The strings tell you where
to aim; the IDL and RPC tell you what is true.

## 4. Instruction-discriminator search (mostly negative — know why)

Anchor discriminators are `sha256("global:<InstructionName>")[:8]`. Searching for them as literal
bytes in `.text`/`.rodata`/`.data.rel.ro` returned **0/33 hits** — sBPF loads them via `lpdw`
(load pseudo-direct word) from computed addresses, so they are not stored as contiguous literals.
Do not spend time on this; use the `Instruction: <Name>` strings from `.rodata` instead, and get
signer flags from the IDL.

## 5. Auth-model cross-check (the actual payoff)

Combine three sources:

1. **`.rodata` strings** — which instructions exist, which errors can fire.
2. **IDL account metas** — `signer: true|false` per account per instruction.
3. **Live RPC simulation** — build a tx via the API and read `meta.logMessages`.

Then classify every fund-moving instruction:

```
for ix in idl["instructions"]:
    signers = [a["name"] for a in ix["accounts"] if a.get("signer")]
    has_bs_auth = "bs_auth" in signers          # protocol co-sign (Secrets Manager)
    has_user    = any(k in signers for k in ["borrower","lender","user","payer","liquidator"])
    sensitive_non_signer = [a["name"] for a in ix["accounts"]
                            if not a.get("signer")
                            and any(k in a["name"].lower() for k in
                                    ["borrower","lender","user","owner","authority","admin","manager"])]
```

LoopScale result: **40/42 instructions require `bs_auth` co-sign**; the two exceptions are
`liquidate_ledger` (permissionless by design — solvency liveness) and `update_market_information`
(protocol admin). Every borrower action carries `borrower [SIGNER]`; `claim_vault_fee` carries
`manager [SIGNER]` plus an `InvalidManager` (6010) check. A consistent architecture like this is a
**verified negative worth recording** — it stops the next session re-deriving it.

## 6. Simulating a server-built transaction without a funded wallet

The API's transaction builders return `serializedTransaction` in the 400 body. To see the on-chain
verdict without paying gas or holding tokens:

```python
rpc("simulateTransaction", [tx_b64, {
    "encoding": "base64",
    "replaceRecentBlockhash": True,   # the built tx's blockhash is stale
    "sigVerify": False,               # we cannot sign
    "commitment": "confirmed",
    "innerInstructions": True
}])
```

`meta.logMessages` then shows exactly which instruction failed and why — e.g.
`AnchorError occurred. Error Code: InvalidWeightMatrix. Error Number: 6090` proved the on-chain
program **rejects** a manipulated `weightMatrixUpdate` that the API had spliced in verbatim.
`InvalidAccountForFee` means the fee payer has no SOL and the simulation stopped before the target
instruction — use a wallet that holds SOL (any public address with a balance works, since
`sigVerify: False`).

⛔ **`InvalidAccountForFee` is a simulation-environment limit, not a program behaviour.** It tells
you nothing about the target instruction. Re-run with a funded fee payer or find another way to
reach the instruction before drawing any conclusion.

## 7. Decoding the built transaction to compare attacker- vs victim-built

To prove an API builds a transaction for an arbitrary wallet, decode both and diff the account
lists. Solana **legacy** tx: `num_sigs(1) + sigs(64×n) + message`. The message header is at
`1 + num_sigs*64`, and may itself be a **v0 message** (`0x80` prefix) — check `tx[msg_off] == 0x80`
and skip it before reading the 3-byte header.

```python
off = 1 + tx[0]*64
if tx[off] == 0x80: off += 1        # v0 message prefix
num_req, num_ro_s, num_ro_u = tx[off], tx[off+1], tx[off+2]; off += 3
acct_len = tx[off]; off += 1
accounts = [b58encode(tx[off+i*32 : off+i*32+32]) for i in range(acct_len)]
```

Then `raw.find(b58decode(addr))` to test whether a specific wallet is present. LoopScale result:
the attacker-built withdraw tx contained the **attacker** as `account[0]` and the **borrower was
absent entirely**, while the borrower-built tx had the borrower at `account[0]`. That is the BOLA
proof — and the IDL's `borrower [SIGNER]` is what makes it non-exploitable.

## Pitfalls

- **`getProgramAccounts` `paginationKey` may be silently ignored.** Every page returned the same
  5,825 accounts, inflating a naive loop to 116,500. Verify first/last pubkey overlap between
  pages before trusting any paginated total.
- **`dataSize` filters are reliable; `memcmp` on some RPCs is not.** Use `dataSize` for bulk
  account-class fetches.
- **Bytemuck packed-C structs have no padding.** Confirm struct sizes empirically: LoopScale's
  `Ledger` computed to 182 bytes from the IDL, validated by checking which offset made the
  following `collateral[0]` decode to a valid mint + plausible amount.
- **Decimals come from the protocol's own config, per market — never assumed.** See the loan-health
  section of `loopscale-v2-2026-10-19.md`; a 6-vs-9 decimal assumption manufactured both false
  positives and false negatives in the same scan.
- **You have no private keys.** Public addresses found on-chain (borrowers, managers, upgrade
  authorities) are strings you can put in an API header — they are not wallets you control. State
  this explicitly in any report; implying wallet access you do not have is an honesty failure, and
  the user will catch it.
