# Live-Deployment Verification Gate (On-chain / DeFi findings)

> **CORE RULE: A code-level finding read from a GitHub repo is VOID until re-verified
> against the DEPLOYED bytecode/source on-chain.** Protocols upgrade; repos go stale.
> In the BENQI (Avalanche) audit this single gate killed 3 of 6 report findings
> (both oracle findings + one "missing control" INFO). Submitting repo-only findings
> = guaranteed NRM / reputation damage.

Run this gate BEFORE writing any PDF for an on-chain target.

---

## 1. Resolve the REAL contract behind each address

Most DeFi entrypoints are proxies. Never audit the proxy address's repo name —
fetch what it actually delegates to:

```bash
# Prefer explicit getters (Compound/BENQI Unitroller):
cast call $UNITROLLER "comptrollerImplementation()(address)" --rpc-url $RPC
cast call $PROXY "oracle()(address)" --rpc-url $RPC        # which oracle is live?
cast call $TOKEN "underlying()(address)" --rpc-url $RPC

# EIP-1967 slots (when no getter exists):
#   implementation slot = 0xREDACTED_********
eth_getStorageAt(proxy, <slot>, "latest")   # take last 40 hex chars = address
# Admin slot = keccak("eip1967.proxy.admin.subtract(1)") — compute it, don't guess:
#   cast keccak "eip1967.proxy.admin.subtract(1)"  → subtract 1
```

Then read the LIVE code (see §2). Do NOT continue with repo code you cloned.

---

## 2. Fetch verified source from the block explorer

```bash
# Avalanche (BENQI case):
curl -s "https://api.snowtrace.io/api?module=contract&action=getsourcecode&address=$ADDR" -o out.json
# Etherscan-family (Ethereum/BSC/Polygon/Base/Arbitrum/Optimism) — same param shape:
curl -s "https://api.etherscan.io/v2/api?chainid=$CID&module=contract&action=getsourcecode&address=$ADDR"
# Sourcify fallback (works when explorer is unverified/Cloudflare'd):
curl -s "https://sourcify.dev/server/files/any/1/$ADDR"
```

Parse quirks (all hit in this session):
- `SourceCode` for multi-file contracts is **double-braced** `{{ ... }}` → strip one
  layer before `json.loads`, then `obj["sources"]["path/File.sol"]["content"]`.
- Compiler version in the response tells you which era you're in — a version jump
  (e.g. repo `0.5.16` vs live `0.8.24`) is a screaming signal the repo is stale.
- Save per-file contents to disk (`comptroller_live.sol`, `oracle_live.sol`) so you
  can grep for the exact function you're claiming is vulnerable.

**If unverified → fingerprint the bytecode instead:**

```bash
curl -s -X POST $RPC -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_getCode","params":["'$ADDR'","latest"]}'
# extract PUSH4 selector constants from the dispatcher, then decode:
curl -s "https://www.4byte.directory/api/v1/signatures/?hex_signature=0x$selsix"
```

Compare the LIVE selector set vs the REPO function list. Different set = different
contract = your finding is about code that isn't deployed.

---

## 3. Reachability gate — is the vulnerable path even live?

A code smell that cannot be reached has no impact. Check on-chain state:

| Claim | What to read live | BENQI outcome |
|---|---|---|
| "Emission/reward logic griefs users" | `supplyRewardSpeeds(uint8,address)`, `borrowRewardSpeeds(...)`, `rewardAccrued(uint8,address)`, contract native balance | speeds were 1 wei/s ≈ dust; Comptroller held ~22,656 AVAX → path live but payout negligible |
| "No borrow caps / missing control" | the actual cap mapping, e.g. `borrowCaps(address)` | **FALSE** — all 10 markets had non-zero caps. Distinguish *guardian unset* (`borrowCapGuardian == 0x0`) from *caps unset*. Never conflate them |
| "No oracle staleness check" | live oracle's `getAssetConfig(asset)`, `stalenessThreshold()`, `deviationThreshold()`, custom errors (`*StalenessError`, `PriceDeviationDetected`, `ZeroPrice`) | repo oracle used `latestAnswer()` unchecked; **live** oracle was a different contract (Edge+Chainlink dual-feed, per-asset staleness, 5% deviation w/ 20% cap) → both oracle findings died |
| "First-depositor / donation exchange-rate inflation" | enumerate markets, read `totalSupply()` + `getCash()` per market | all markets mature & deep → donating to move the rate costs more than it can extract → downgrade. Only live if some market has `totalSupply() ≈ 0` |
| "Batch reward-claim DoS via reverting receive()" | who can put addresses into `holders[]`? | caller-chosen array → attacker can only revert batches that ALREADY include the attacker; victims claim solo. Real residual impact = *contract wallets whose `receive()` needs > 4029 gas permanently cannot self-claim* (self-lock), not a protocol-wide DoS |

---

## 4. Enumerate live market/asset sets

`cast call $C "allMarkets()(address[])"` mis-decoded (`buffer overrun`, and raw
`eth_call` returned `0x` for a wrong selector guess). Working recipe:

```python
# batch JSON-RPC + manual decode, loop the indexed getter:
def call(to, data): ...  # eth_call
n = int(call(C, "0xc473318f" ...), 16)      # getArrayLength / allMarkets() length
for i in range(n):
    m = call(C, sel_allMarkets_idx + pad32(i))   # cast sig "allMarkets(uint256)"
```
Also `cast sig "<fn>"` to confirm selectors before trusting a hand-typed one.
A QuikNode/other private RPC from `D:/data hermes/rpc/rpc_live.md` avoids public-RPC
rate limits/`-32000` reverts (public `rpc.ankr.com/avalanche` returned -32000 here).

---

## 5. Fork-PoC hygiene — kill fake "Fork Verified" labels

- Any test wrapped in `vm.skip(true)` is **source analysis**, not verification. It must
  not be described as "Fork Verified" in the report.
- A test that only `console.log`s state is exploration, not proof. Proof = an `assert`
  on an attacker-changed invariant (attacker balance delta, share/underlying delta).
- Pin a real recent block (`--fork-block-number`) so figures match the PDF, and re-run
  `forge test -vv` to capture the exact console output you paste as evidence.
- Re-check numbers quoted in the PDF against fresh live reads (cash/supply/exchangeRate
  drift every block — quote rates, not balances, unless block-pinned).

---

## 6. Severity discipline at this gate (hard rule)

- Chain dies on live → **informational or drop**, never HIGH/CRIT. (User's standing rule:
  "SEVERITY INFLATION = OMONG KOSONG — blocked exploit chain = info".)
- Tool impact labels (Slither `impact: High`) are **not** severity. This target's entire
  "High" set (reentrancy-eth, controlled-delegatecall, arbitrary-send-eth,
  controlled-array-length, unchecked-transfer, uninitialized-state) resolved to
  false-positive / by-design: state zeroed before external calls, 4029-gas stipend caps
  reentrancy, proxy admin is the intended pattern, `allMarkets` is admin-gated
  (`_supportMarket`), `accountAssets` capped by `maxAssets`.
- When findings die, say so plainly and recommend revising/downgrading the report rather
  than shipping the overclaim — and list the surviving ones with honest impact statements.

---

## 7. Worked example snapshot (BENQI, Avalanche C-Chain, Sep 2026)

- `Comptroller` Unitroller proxy `0x486Af39519B4Dc9a7fCcd318217352830E8AD9b4`
  → impl `0xd8E426C61b0FBBda06e9F603263ABea09d717dBD` = old Compound v2 fork (sol 0.5.17),
  QI + AVAX flywheel (`rewardType` 0=QI, 1=AVAX), `grantRewardInternal` AVAX send
  `call.value(amount).gas(4029)` + `require(success)`.
- `oracle()` → `0xf81B4C4abf7de8B8FC560D66F0eB70598D8BF15e` = **BenqiDualOracle**
  (sol 0.8.24): Edge primary + Chainlink backup, per-asset `stalenessThreshold`,
  `deviationThreshold` 5% (cap 20%), manual-price vs feed validation, Ownable2Step.
  ≠ repo's `BenqiChainlinkOracle` (`latestAnswer()`, no checks) → F1/F4 void.
- 10 markets, `borrowCaps` all non-zero (AVAX 400k, BTC 1, ETH 1000 …), QI+AVAX speeds
  active on 6 markets, USDT/USDC(n) zero.
- Verdict: no HIGH survived; the strongest true statement was the contract-wallet
  self-lock on AVAX claiming + best-practice items.
