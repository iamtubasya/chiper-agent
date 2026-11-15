# On-chain exploit forensics — free RPC matrix and workflow

Verified 2026-10-05 by testing each endpoint live. Purpose: dissect a past exploit transaction
(your own example txs, or a reference incident) into a **detection pattern** for hunting the same
bug shape in other protocols.

## Which free RPCs actually work

| Endpoint | basic calls | `debug_traceTransaction` | Notes |
|---|---|---|---|
| `https://eth.drpc.org` | yes | **YES** (`tracer: "callTracer"`) | the only free one that worked; intermittent `{"code":19,"message":"Temporary internal error"}` → retry 2-3x with a sleep |
| `https://ethereum-rpc.publicnode.com` | yes | no — `the method does not exist/is not available` | fine for tx + receipt + logs |
| `https://1rpc.io/eth` | yes | no — method unavailable | |
| `https://rpc.flashbots.net` | yes | no — `rpc method is not whitelisted` | |
| `https://rpc.ankr.com/eth` | no | no | demands an API key |
| `https://eth.llamarpc.com` | no | no | HTTP 525 |
| `https://eth.merkle.io` | no | no | rate limited |

**Client gotcha:** `urllib` / `requests` get **HTTP 403** from drpc (user agent blocked). Use
`curl -A "Mozilla/5.0" --data-binary <json>` in a subprocess, or set a browser UA header. A 403 here
is not an endpoint problem.

Other chains: same method names, but free trace support varies — probe `debug_traceTransaction`
first and say so honestly if only basic calls are available.

## Workflow

1. `eth_getTransactionByHash` → `from`, `to`, `blockNumber`, `value`, `input`.
   The selector is `input[:10]`; a **bare 4-byte input** (e.g. `0x6f3ce701`) means the exploit
   contract does everything internally — the trace is the only way in.
2. `eth_getTransactionReceipt` → `status`, and `logs` (ERC-20 `Transfer` topics give per-address
   balance deltas, i.e. your own version of a "balance_change" figure).
3. `debug_traceTransaction(tx, {"tracer":"callTracer"})` → recurse `result.calls[]`, printing
   depth / `type` / `from` / `to` / `value`. CALL vs DELEGATECALL vs STATICCALL immediately reveals
   proxy hops and read-only oracle checks.
4. Cross-check against the target's **verified source** (explorer) to name the function behind each
   selector.
5. Write the finding up detection-first (see below).

## Output shape for a *bounty* skill (not an attack recipe)

For each case record:

- **Anatomy** — chain, block, addresses, the call path, the profit.
- **Invariant violated** — stated as a property, e.g. "quorum must be measured against eligible
  supply, not a wrapper's supply".
- **Code shape to grep for** in OTHER protocols — this is what converts a historical hack into a
  hunting heuristic.
- **Pre-conditions an auditor must confirm** on the target.
- **Verification procedure** — the concrete read that proves it (dust fee "write to verify"
  discipline applies here too: an unused variable can flip a naive check).

## Worked example (regression fixture)

tx `0xREDACTED_********`
("Aztec Connect" drain, block 25315715, ~$2.19M):

- `eth_getTransactionByHash` → from `0x0f18d8b44a740272f0be4d08338d2b165b7edd17`,
  to `0x06f585f74e0da633ae813a0f23fb9900b61d0fcd`, input `0x6f3ce701` (selector only).
- `eth_getTransactionReceipt` → status success, 27 logs.
- `debug_traceTransaction` → **714 call frames, max depth 5**:
  EOA → exploit contract → `0xe810f602` → `0xff1f2b4a` (RollupProcessor) → DELEGATECALL to the
  implementation → many STATICCALLs (verifier path).

Use this tx to sanity-check any forensic script you write: if it does not reproduce ~714 frames and
that call path, it is broken.

## Secondary sources for root cause + verification method

- **defimon.xyz** (by Decurity) — ~24 posts, ~18 detailed incident reports that include the actual
  Solidity of the exploit actions, the protocol's parameters, and explicit verification instructions
  (e.g. "read `getPastTotalSupply` at the proposal snapshot block and compare to the attacker's
  balance"). Also 4-5 explainers: flash-loan attacks, oracle manipulation, bridge exploits.
  Useful as a cross-check for root cause and as a index of recurring bug shapes.
