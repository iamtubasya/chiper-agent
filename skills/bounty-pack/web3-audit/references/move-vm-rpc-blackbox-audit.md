# Black-box auditing a Move-VM deployment from its RPC (Supra worked example)

When a Move chain's contracts are **not** in any repo you can clone — the target ships a
frontend and an RPC, nothing else — you are not blind. The node exposes the module ABI, and
often **lets you execute the pure/view math directly**. That turns an unverifiable
"reading the code" audit into an evidence-based one.

Worked against Dexlyn (Supra L1, CLMM DEX + ve(3,3) tokenomics), 2026-10.

---

## 1. Find the packages

The frontend bundle names the module functions it calls (`pool::swap_routing`,
`router::get_amount_out`, `voter::vote`, …). That tells you the protocol is a **Move**
deployment and gives you the module names. Then get addresses:

- grep the bundles for `0x[0-9a-f]{64}` and count occurrences — the package addresses are the
  high-frequency ones (33× and 20× in one bundle here);
- confirm by querying the RPC.

```bash
curl -s "https://<rpc>/rpc/v1/accounts/0x<PKG>/modules"
# -> {"Modules":{"modules":[["0x<PKG>::pool",{"name":"pool"}], ...]}}
```

A package with `pool / factory / liquidity / tick_math / clmm_math` is a **CLMM**; one with
`voter / voting_escrow / gauge_* / bribe / fee_distributor / minter` is a **ve(3,3)** stack.
Both are high-value: the first holds swap math, the second holds reward accounting.

## 2. Read the ABI — it is not just names

`/rpc/v1/accounts/<PKG>/modules/<mod>` returns `exposed_functions` and `structs`:

```
exposed_functions[] -> name, visibility, is_entry, is_view, params[], return[]
structs[]           -> name, abilities, fields[] (name + type)
```

**This is the access-control surface.** It is also the state layout — struct field types tell
you where `u64`/`u128`/`I128` arithmetic happens, which is where overflow bugs live.

## 3. The no-`&signer` sweep — the single highest-signal check

In Move a function **without `&signer` can be called by anyone**. Sweep every module and flag
every `is_entry` function whose params contain no `&signer`:

```python
for f in mod["exposed_functions"]:
    if f.get("is_entry") and not any("&signer" in p for p in f["params"]):
        print(mod_name, f["name"], f["params"])
```

Real output from one protocol: 7 such functions, including
`vesting::vest(address)`, `vesting::vest_individual(address, address)`,
`voter::claim_bribes_for_address(address, vector<address>, vector<vector<address>>)`.

### Then apply the Move-semantics rule BEFORE calling any of them a bug

> A function with **no `&signer` and no `&TxContext`** cannot learn who called it.

So it cannot pay the caller. Any value it releases must go to an address it can *name* — i.e.
an argument. `claim_bribes_for_address(victim, …)` therefore credits `victim`, and is a
gasless "claim on someone's behalf" helper, **not** theft.

This killed a would-be Critical in one inference step. Check for `&TxContext` explicitly —
`tx_context::sender(ctx)` is the one other way a Move function can identify its caller.

A function that **does** take `&signer` **and** an `address` (`remove_all_liquidity(&signer,
pos, …)`) is the shape worth reading closely — the question is whether the address argument
is verified against the signer. You cannot settle it from the ABI alone; say so.

## 4. Executing the math: the `view` endpoint

```
POST /rpc/v1/view
{"function":"<PKG>::<mod>::<fn>", "type_arguments":[], "arguments":[...]}
```

### Argument encoding (this is where you will lose an hour)

| Move type | Send as |
|---|---|
| `u8/u64/u128/u256` | **STRING** — `"100"`. A JSON number fails with `invalid type: number, expected a string` |
| `bool` | **JSON boolean** — `true`. `str(True)`→`"True"` fails with `expect boolean` |
| a struct, e.g. `I64` | object with its fields — `{"bits":"100"}` |
| `&signer` param | not callable via `view` at all — entry functions need a real tx |

Errors are informative; read them. `expect string<move_struct_tag_id>` vs
`expect boolean` vs `Move VM error: INVALID_MAIN_FUNCTION_SIGNATURE and message function not
marked as view function` each tell you a different thing — the last means **your args parsed
and the function simply is not view-callable**.

Returns come back as `{"result":[...]}`; a struct-typed return is `{"bits":"…"}` for a
`{bits: u64}` I64/u64 wrapper, a bare string for a plain integer.

### Negative numbers are two's complement in the display

```
get_tick_at_sqrt_price("1000000000000000000") -> {"bits":"18446744073709493315"}
18446744073709493315 - 2**64                   = -58301     <- the real tick
```

Always subtract `2**64` when the value exceeds `2**63`. A "huge" return is usually just a
negative. Conversely: a protocol may define **two different I64 structs** in different
packages (`{bits:u64}` two's complement vs `{value:u64, is_negative:bool}` sign-magnitude).
Note it as a structural observation; do not report it without a proven crossing path.

## 5. What actually paid off as *evidence*

Pure-math view functions let you verify invariants that a code read can only suggest:

- **Bounds.** `get_tick_at_sqrt_price(min_sqrt_price)` == `min_tick`, `max` == `max_tick`;
  `min-1` and `max+1` **abort** rather than clamp. Rejecting out-of-range is correct.
- **Monotonicity.** Sample across the whole domain and assert the function never decreases.
  14 points, 0 violations = a real negative you can state with a date.
- **Cross-consistency.** `from_input(a_up) == a_up`, `from_output(b_down) == b_down` — the
  four price-transition variants must agree pairwise.
- **Rounding flag.** `get_delta_a(p0, p1, L, roundUp=True)` vs `False` must differ by exactly
  **1**. A larger gap means the ceiling/floor is wrong.
- **Fee arithmetic (the cleanest proof).** For exact-in:
  `amount_in + fee_amount == amount_remaining` **exactly**, and
  `fee_amount / amount_remaining == feePips / fee_rate_denominator`. When both hold to the
  unit, the swap step is correct.

## 6. Harness faults that look exactly like contract bugs

**Every one of these produced a fake anomaly before being identified as MY error.** When a
probe aborts or a value looks wrong, suspect the harness FIRST.

| Symptom | Real cause |
|---|---|
| view call returns an empty/decode error | the "oracle"/target arg was an **EOA**, not a contract — point at a deployed instance |
| `Yul exception: ... 1 too deep in the stack` | you compiled with **your** defaults; the repo's `foundry.toml` sets `optimizer=true` with `runs=200`. Copy their settings |
| every swap/tick call ABORTS | an input is **out of domain** — here `Q96 > max_sqrt_price`, so *every* price I passed was invalid. Read the protocol's own min/max constants first and stay inside them |
| `[1, 1000000000000, …]` looks like 1-in / 1e12-out | the 2nd tuple slot is the **remaining unfilled amount**, not the output. Swap-step structs carry `remainer_amount` (sic) for a reason |
| invariant "violated" across all cases | you misread which token the `bool` selects. Two different bools existed in the same module: one = `roundUp`, one = `atob` (direction) |
| control test fails while "exploit" passes | your control used an input the contract legitimately rejects. Make the control a **well-formed** call |
| an `Option<T>` sweep returns "a result" for every input | `{"vec":[]}` is `Option::`**`None`**. Every probe looks like a hit — a 112-pair `get_pool` sweep read as *112 pools found*, then filtered to zero |

**Rule: form the hypothesis from reading, then try to DESTROY it by execution.** Seven
hypotheses in one engagement, seven killed by a test (auth binding enforced; Move semantics;
out-of-domain inputs; `str(True)`; tuple misread; wrong bool; addresses I invented). Reporting
any of them would have been a false positive against a program whose scope is *only* direct
financial loss.

## 7. Where black-box legitimately stops — and what to say

### Enumeration routes, in order of yield

| Endpoint | Returns |
|---|---|
| `GET /rpc/v1/accounts/<addr>/modules` | module name list |
| `GET /rpc/v1/accounts/<addr>/modules/<mod>` | full ABI — `exposed_functions` + `structs` |
| `GET /rpc/v1/accounts/<addr>/resources` | resource **type names** only (+ a `cursor` to page) |
| `GET /rpc/v1/accounts/<addr>/resources/<TYPE>` | **the resource PAYLOAD** |
| `GET /rpc/v1/accounts/<addr>/transactions` | that address's recent txs |
| `GET /rpc/v1/events/<TYPE_TAG>?start=&end=` | events — type goes in the **PATH**, range **≤ 10 blocks** |

`/resources/<TYPE>` is the one worth knowing: a `SimpleMap`-shaped resource comes back
**fully populated**, which is how you read a protocol's real config and registries without any
source. A `table::Table` / `SmartTable` resource returns only a `handle`, and there is no
key-listing endpoint — those stay unenumerable.

```jsonc
// /resources/<PKG>::fee_tier::FeeTiers  -> readable in full
{"result":[{"fee_tiers":{"data":[
  {"key":"1","value":{"fee_rate":"100","tick_spacing":"1"}},
  {"key":"60","value":{"fee_rate":"3000","tick_spacing":"60"}}]}}]}

// /resources/<PKG>::config::GlobalConfig -> readable in full
{"result":[{"is_pause":false,"pool_create_authority":"0x0",
            "protocol_authority":"0x<PKG>","protocol_fee_rate":"3333"}]}

// /resources/<PKG>::factory::Pools -> handle only, unenumerable
{"result":[{"data":{"handle":"0x…"},"index":"98"}]}
```

A live `GlobalConfig` is worth reading on every engagement: `is_pause`, the authority
addresses, the fee rates. A **zero-address authority** (`pool_create_authority: "0x0"`) is a
lead you cannot resolve from the ABI —
`assert!(sender == authority)` and `if (authority != @0x0) assert!(…)` are indistinguishable
from outside, and the second means permissionless creation. Pools *existing at all* while the
field reads `0x0` argues it is not blocking — which is not the same as proving it is open.
State it as an open question, never as a finding.

`view` cannot take a **reference** argument: `has_role(&acl::ACL, address, u8)` fails with
`Invalid move type for converting into TypeTag: Reference`. Reference-parameterised getters are
unreachable — read the resource payload instead. And the RPC's own parse errors leak the correct
shape (`unexpected token Name("by_type"), expected type tag` is what revealed the events URL).

### Where it stops

You **cannot** enumerate an on-chain `SmartTable` from the RPC, so gauge/pool **address
enumeration can fail even when the global counters are readable** (`voter::length() == 5`,
`total_weight` non-zero).

**The trap:** a guessed address returning `weights(gauge) == 0` looks exactly like
"total_weight is unsupported by any gauge" — a serious accounting claim. It is the *correct*
answer for a **wrong address**. If you invented the addresses, you have no finding.

The honest deliverable there is:
- what you verified by execution,
- what you could not verify **and why** (no source, no enumeration route),
- an explicit statement that the ambiguous reading is an artefact of your reach, not evidence.

Ask for the `sources/*.move` repo. Disclosed HackenProof reports on the same target name the
source path (e.g. `sources/voting_escrow.move`) — that both proves source exists and tells you
which module holds an already-paid bug class, which is also a duplicate check.
