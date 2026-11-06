# Auditing a Uniswap-V4 module behind a beacon proxy (Arrakis, 2026-10-13)

Worked case: `UniV4StandardModuleV2Private` (Arrakis "UniV4 Private" LP module). Source was **not**
in a repo — it had to be recovered from the chain. Everything below is the path that worked, in order.

## 1. Unwrapping the deployed architecture (3 hops before you see any code)

```bash
RPC=https://ethereum-rpc.publicnode.com        # works; llamarpc/ankr/cloudflare-eth did not
cast code <module> --rpc-url $RPC | head -c 200      # 744 bytes -> a proxy, not the logic
```

The module read its implementation from a **custom** slot, not EIP-1967:

```bash
# the slot address is visible in the runtime bytecode as a PUSH32 constant
raw=$(cast storage <module> 0xREDACTED_******** --rpc-url $RPC)
impl="0x$(echo $raw | tail -c 41)"
```

That returned an **OZ `UpgradeableBeacon`**, not the module. One more hop:

```bash
cast call <beacon> "implementation()(address)" --rpc-url $RPC   # <- the real logic (45 931 bytes)
cast call <beacon> "owner()(address)" --rpc-url $RPC
```

Lesson: when `cast code` is a few hundred bytes and `cast storage <EIP-1967 slot>` reads **zero**, do
not conclude "not a proxy" — grep the runtime bytecode for `7f<64 hex>` PUSH32 constants and read each
as a slot. Beacon-in-front-of-proxy is two hops, and the beacon is itself a verified contract.

## 2. Source recovery: Sourcify v1 is GONE, use v2

`repo.sourcify.dev/contracts/full_match/...` and `sourcify.dev/server/files/any/...` both now answer
**404 / "API v1 is removed"** (and the first one 307-redirects to a dead path). Etherscan v1 is also
retired (`You are using a deprecated V1 endpoint`) and its v2 needs a key you may not have.
What works, keyless, one call, whole bundle:

```bash
curl -sL "https://sourcify.dev/server/v2/contract/1/<impl>?fields=sources" -o impl_src.json
curl -sL "https://sourcify.dev/server/v2/contract/1/<impl>"                    # matchId / exact_match
python - <<'PY'
import json, pathlib
d=json.load(open('impl_src.json'))
for k,v in d['sources'].items():
    p=pathlib.Path(k); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(v['content'] if isinstance(v,dict) else str(v), encoding='utf-8')
PY
```

`creationMatch`/`runtimeMatch: exact_match` is your deployed-vs-source starting point, but confirm it —
see §4. `Blockscout /api/v2/smart-contracts/<addr>` is a good cross-check (it named the beacon
`UpgradeableBeacon` and its `language`).

## 3. ⛔ `remappings.txt` was IGNORED — put remappings in `foundry.toml`

The extracted bundle compiled to **nothing** until the remappings moved. Two failure modes stacked:

- forge auto-generates remappings from `lib/` and its guesses use **bare** prefixes
  (`v4-core/=lib/v4-periphery/lib/v4-core/src/`), while the source imports `@uniswap/v4-core/src/...`.
  A `remappings.txt` sitting in the project root did **not** get picked up (`forge config --json`
  listed only the auto-generated set).
- `FOUNDRY_REMAPPINGS` with `;` separators does not work — the whole string is consumed as one entry
  and you get a nonsense `Source "…;@openzeppelin/…/src/types/PoolKey.sol" not found`.

What did work — the `remappings` array in `foundry.toml`:

```toml
[profile.default]
src = "src"
libs = ["lib"]
solc_version = "0.8.26"
optimizer = true
optimizer_runs = 1000000
evm_version = "cancun"
remappings = [
  "@uniswap/v4-core/=lib/v4-periphery/lib/v4-core/",
  "@uniswap/v4-periphery/=lib/v4-periphery/",
  "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
  "@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/contracts/",
  "@v3-lib-0.8/=lib/v3-lib-0.8/",            # note: NOT .../contracts/ — the import already carries it
  "@uniswap/v3-core/=lib/valantis-hot/lib/v3-core/",
]
```

Iterate one missing source at a time; each error names the exact prefix. Two traps in the loop:
a prefix that already ends in `contracts/` doubles it (`…/contracts/contracts/LiquidityAmounts.sol`),
and `forge build` printing `No files changed, compilation skipped` means the **previous** run succeeded
— check for that before believing another failure.

## 4. Prove the source IS the deployed code (selector diff, not length)

```bash
forge inspect src/modules/<C>.sol:<C> methodIdentifiers --json \
  | python3 -c "import sys,json;print('\n'.join(sorted(json.load(sys.stdin).values())))" > src_selectors.txt
cast code <impl> --rpc-url $RPC | grep -oE '63[0-9a-f]{8}' | sed 's/^63//' | sort -u > live_sel.txt
comm -23 <(sort -u src_selectors.txt) <(sort -u live_sel.txt)   # empty => same build
```

Result on this target: **src-only = 0** (all 50 source selectors present on chain) ⇒ the analysed
source is the deployed build. Never judge by bytecode length (metadata embeds source paths).

## 5. Slither on Uniswap-V4 code — the FP classes, named

259 results / 63 contracts (28 High, 86 Medium). Every High and almost every Medium was a **pattern
match**, not a defect. Triage by these four classes before reading anything:

| detector | count here | why it is an FP class |
|---|---|---|
| `unused-return` | 44 | `poolManager.settle()/take()/swap()/modifyLiquidity()` — V4's PoolManager **reverts** on failure; the return values are informational |
| `uninitialized-local` | 19 | solidity default-zeros a local assigned later in the same scope (`poolKey`, `ethToSend`, `balances`, `fee0/fee1`) |
| `divide-before-multiply` | 20 | the multiplications are `FullMath.mulDiv` helpers; the detector sees the helper's body, not the call site |
| `reentrancy-balance` / `reentrancy-events` | 23 | every flagged function carries OZ `ReentrancyGuardUpgradeable` `nonReentrant` — verify the guard is the standard bool/depth guard, then the whole class drops |

Also: `slither` can exit **127 with the analysis fully succeeding**; read the artifact's final
`analyzed (N contracts …)` line, and re-run with a **fresh `--json` path** — it refuses to overwrite an
existing file (`the overwrite is prevented`) and you will otherwise parse a stale/garbage JSON from an
earlier failed run (that is why the first parse here printed `total: 0`).

## 6. The candidate that stayed a candidate (the discipline that mattered)

A real source-level defect: `UniV4StandardModuleV2.initialize()` never assigns `_init0`/`_init1` and
never calls the V1 `initialize()` (the only writer), so `getInits()` — a documented public view
"amounts needed to open a position" — should return zeros. Slither flagged it `uninitialized-state`
(High) and it is genuinely absent from the source.

**It was still not reported.** The live probe killed it:

```bash
cast call <module> "getInits()(uint256,uint256)" --rpc-url $RPC     # -> (1, 1), not (0, 0)
cast call <module> "totalUnderlying()(uint256,uint256)"             # module holds real funds
```

Three live modules all returned `(1,1)` (so not garbage), the module holds ~190 422e18 token0 +
~28 139e18 token1 + 0.35 ETH, and the only consumer of `getInits()` is the **MetaVault, which was not
in the verified bundle** (interfaces only). Impact undemonstrable ⇒ candidate, not finding — logged
with its evidence as an open question for a MetaVault-scoped pass.

Two reusable rules from this:
- **A public view returning a constant is not automatically a bug** — check whether the contract is
  live and funded before writing it up.
- **A module-only bundle cannot prove the module's auth model.** Save every `/interfaces/*.sol` you
  *don't* have as an explicit gap (MetaVault / Guardian / Manager / Distributor here) instead of
  inferring their behaviour, and record the "if the MetaVault permits X, this becomes real" question
  rather than asserting it (e.g. `_fund`'s caller-supplied `depositor_` in an
  `onlyMetaVault` `safeTransferFrom` — flagged `arbitrary-send-erc20` High by slither, unresolvable
  without the MetaVault source).

## 7. Tool ledger for this pass (write the gaps down)

ran: `forge build` (63 files, OK after §3) · `slither` (63 contracts, 259 results, triaged above).
**NOT RUN:** aderyn, mythril, echidna, medusa, halmos, manticore, z3 — and no forge test harness was
written, so nothing on-chain had an executable PoC. Say that plainly; an empty scanner directory is a
gap, not a clean result.
