# Move / Supra program verification over public RPC

Verified 2026-10-08 against the Dexlyn DEX on Supra mainnet (`rpc-mainnet.supra.com`).
Supra's RPC is **genuinely rich for black-box audit**: no explorer, no source, no GitHub
needed. You can enumerate every module, read the full ABI, read state **and execute view
functions** to test the protocol's own math. Treat this as the Move sibling of §1 (EVM
`eth_call` replay) and §1c (Solana RPC).

## Endpoints that work

| Purpose | Endpoint |
|---|---|
| Account state | `GET /rpc/v1/accounts/{addr}` |
| **List modules at an address** | `GET /rpc/v1/accounts/{addr}/modules` |
| **Full ABI for one module** | `GET /rpc/v1/accounts/{addr}/modules/{module}` |
| Resources held | `GET /rpc/v1/accounts/{addr}/resources` |
| **Execute a view function** | `POST /rpc/v1/view` |
| List transactions | `/rpc/v2/accounts/{addr}/transactions` |

None of these exist (404): `.../module/{name}`, `.../modules/{name}/bytecode`,
`.../module_bytecode/{name}`, `.../modules/{name}/source`, `.../module_bundle`.
**Supra exposes ABI + structs, not bytecode or source.** Plan the audit around the ABI.

The module listing is the fastest way to learn what a protocol *is*. Two addresses gave the
whole Dexlyn architecture:

```
0xc3a61006…  CLMM core : pool factory liquidity fetcher partner fee_tier rewarder
                         clmm_math tick_math math_u64 math_u128 math_u256 calculator
                         config utils acl i32 i64 i128 u256
0xc7ce2262…  ve(3,3)   : voter voting_escrow voting_escrow_router bribe fee_distributor
                         minter emission vesting dxlyn_coin
                         gauge_clmm gauge_cpmm gauge_perp gauge_clmm_v2 gauge_vedxlyn
```

Module names alone tell you the design (`voter` + `voting_escrow` + `gauge_*` + `bribe` +
`fee_distributor` + `minter` = a Curve/Velodrome-style ve(3,3) port; `clmm_math` + `tick_math`
= concentrated liquidity). Aim the audit accordingly before reading a single function.

## `modules/{name}` response shape — the ABI you get for free

```json
{
  "address": "0x…",
  "name": "tick_math",
  "friends": ["0x…::factory", "0x…::liquidity"],
  "exposed_functions": [
    {"name":"get_tick_at_sqrt_price","visibility":"public","is_entry":false,
     "is_view":true,"generic_type_params":[],
     "params":["u128"],"return":["0x…::i64::I64"]}
  ],
  "structs": [
    {"name":"I64","is_native":false,"abilities":["copy","drop","store"],
     "fields":[{"name":"bits","type":"u64"}]}
  ]
}
```

`friends` is an access-control signal worth reading: friend-only modules (a `pool` with
**zero** `is_entry` functions) mean the user-facing surface lives elsewhere (`liquidity`,
`router`). Do not report "no entry points" as a defect — it is correct encapsulation.

`structs` gives you the **state layout and the exact integer widths**, which is where
overflow findings live. `LockedBalance{amount:u64,end:u64,is_perpetual:bool}` and
`Point{bias:I128,slope:I128,ts:u64}` immediately identify the Curve bias/slope math.

## Executing view functions — `POST /rpc/v1/view`

```json
{"function":"0xPKG::tick_math::max_tick","type_arguments":[],"arguments":[]}
-> {"result":[{"bits":"443636"}]}
```

This is the highest-value capability: **you run the protocol's own money math** and test it
against invariants (§2b applies unchanged — build controls).

### Argument encoding — learned the hard way

| Move type | Wire form | Note |
|---|---|---|
| `u64`, `u128`, `u256` | **JSON string** `"100"` | a JSON number is rejected |
| `bool` | JSON bool | |
| struct (`I64`, …) | **JSON object of its fields** `{"bits":"100"}` | field values follow the table |

Wrong encodings are self-documenting — the RPC names the expected type, so read the error
instead of guessing:

- `parse arguments[0] failed, expect string<u64>, caused by error: invalid type: number, expected a string`
  → you sent `100`; send `"100"`.
- `parse arguments[0] failed, expect string<move_struct_tag_id>, caused by error: Expecting a JSON Map`
  → you sent a bare string where a struct object belongs; send `{"bits":"100"}`.
- `expected 2 arguments [string<move_struct_tag_id>, string<u64>], but got 1`
  → arg count mismatch, and it tells you each expected type.

### Three error strings and what each means

| Message | Meaning |
|---|---|
| `Move VM error: INVALID_MAIN_FUNCTION_SIGNATURE and message function not marked as view function` | Args parsed fine; the function is not view-only. Cannot be called via `/rpc/v1/view`. **A parseable error here means your encoding was CORRECT** — a useful positive signal. |
| `Failed to execute view function: ABORTED with sub status 2 at location …` | The function ran and asserted. In tick math this is the *desired* out-of-range rejection. |
| `parse arguments[N] failed, expect string<…>` | Encoding problem, not a contract problem. |

Distinguishing "my call is malformed" from "the contract rejected the input" is the whole
game — ABORTED means the contract executed and decided; a parse error means you never
reached it.

## Signed integers: two representations in one protocol

Integers are per-package structs, not one shared type. Dexlyn carried **two**:

```
core       pkgs ::i64::I64 -> { bits: u64 }                      two's complement
tokenomics pkgs ::i64::I64 -> { value: u64, is_negative: bool }  sign-magnitude
```

Reading a tick: `bits` is unsigned on the wire, so a negative value arrives huge —
`18446744073709107980` is `-443636`, i.e. `bits - 2**64`. Always convert before comparing:

```python
b = int(result["result"][0]["bits"])
tick = b - (1 << 64) if b >= (1 << 63) else b
```

Two representations of one type across packages is a **structural observation worth a
hardening note**, but on its own it is not a finding: no exploit exists until a value
actually crosses between the packages and is misinterpreted. Do not claim it as a
vulnerability without a crossing path.

## The Move access-control sweep (do this first, it is cheap and high-signal)

Pull every module, take every function with `is_entry == true`, and split them:

```
entry WITHOUT "&signer" in params  -> callable by ANYONE, review hard
entry WITH "&signer" AND a bare "address" param -> ownership-check review
```

### The reasoning rule that kills most false positives

> In Move, a function with **neither `&signer` nor `&TxContext` cannot know who called it.**
> Therefore it cannot pay the caller — any value it releases must be credited to an address
> it was *given*. A no-signer function that takes `address` and pays that address is a
> gasless "poke / claim for someone else" helper, not a theft primitive.

Worked case (2026-10-08): `voter::claim_bribes_for_address(address, vector<address>, vector<vector<address>>)`
has no `&signer` while every sibling claim does (`claim_bribes(&signer,…)`,
`fee_distributor::claim(&signer,address)`). That reads like a critical "claim anyone's
bribes" bug. Move semantics say otherwise — it cannot see the caller, so the bribe must go
to the `address` argument. **Not a finding.** The same rule disposed of
`vesting::vest_individual(address, address)`.

The rule is a filter, not a proof: it rules out *paying the caller*. Still check whether an
authorization is required for the named address, and whether a shared/global resource can be
advanced in the caller's favour.

## Worked example — CLMM tick math verified against invariants

`tick_math::get_sqrt_price_at_tick` is **not** view (unreachable via RPC), but
`get_tick_at_sqrt_price(u128) -> I64` is, which is enough to test the money math:

```
bounds:  min_sqrt_price 4295048016                    -> tick -443636 == min_tick   ✓
         max_sqrt_price 79226673515401279992447579055 -> tick  443636 == max_tick   ✓
         min-1, max+1, 2^32-1, 2^96+1, 0, 1           -> ABORT                        ✓
         monotonic across 14 points spanning the range -> 0 violations               ✓
```

Out-of-range prices **abort** rather than being silently clamped, and both endpoints are
inclusive and agree exactly with `min_tick`/`max_tick`. Verdict: correct.

One trap from this test: a naive reference (`2*log_1.0001(p/2^96)`) was off by a constant
`443637` = `max_tick + 1` on every in-range point. A **constant** offset means your model of
the domain is wrong (a different tick-zero), not that the contract is wrong. Check whether the
error is constant before calling it a bug.

## Finding the addresses in the first place

No GitHub org, no explorer, Cloudflare-blocked scans. The addresses came from the **web app's
JS bundle**:

```bash
grep -ohE '0x[a-fA-F0-9]{64}' *.js | sort | uniq -c | sort -rn | head
grep -ohE '(pool|router|factory|vault)::[a-zA-Z_]{3,30}' *.js | sort -u
grep -ohE 'https://[a-z0-9.-]*supra[a-z0-9./-]*' *.js | sort -u
```

Frequency ranking finds the package addresses (they repeat across call sites); `module::function`
strings name the modules before you have the ABI; the RPC URL falls out of the same bundle.
Public audit/contest **disclosure pages** also leak structure — one HackenProof report for this
target named `sources/voting_escrow.move` and `check_point_internal()`, confirming the ve(3,3)
math as a paying area (and telling you which bug not to re-report).
