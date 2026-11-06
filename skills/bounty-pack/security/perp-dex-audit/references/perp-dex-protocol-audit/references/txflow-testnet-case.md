# TxFlow Testnet — Worked Case (Oct 2026)

Target: `txflow-testnet.xyz` — a perpetuals DEX L1 with its own bug bounty
(up to 150,000 USDC Critical; **testnet-only features explicitly in scope**, payouts may be lower).
Four leads were supplied by the operator and driven live; one real side-finding emerged.

## Surface map

| Layer | Host |
|---|---|
| Front-end | `https://txflow-testnet.xyz` (`/assets/*.js`, Vite) |
| REST read + write | `https://testnet-api.txflow-testnet.xyz` (`POST /info`, `POST /exchange`) |
| Node RPC (also serves `/info`) | `https://rpc.txflow-testnet.xyz` |
| Wallet / social | `https://api-wallet.txflow-testnet.xyz` (Privy) |
| Faucet | `POST https://testnet-api.txflow-testnet.xyz/request-fund` `{"address":"0x…"}` |
| Docs (full spec) | `https://docs.txflow-testnet.xyz/llms-full.txt` |

Config leaked straight from the bundle as `VITE_*` constants — worth grepping on any Vite front-end.

## Signing model (EIP-712 + MessagePack)

- Domain: `name:"TxFlow-Testnet"`, `version:"1"`, `chainId:2511`, `verifyingContract: 0x0`.
  Mainnet is `name:"TxFlow-Mainnet"`, `chainId:869`.
- **Two flows:**
  - *Direct EIP-712* (account key): `approveAgent`, `tokenSend`, `withdraw3`, builder-fee actions.
  - *Agent signing* (agent key): everything trading. The action body (minus `type`) is
    MessagePack-encoded, then `‖ nonceBE8 ‖ vaultFlag`, then `keccak256` → `connectionId`, wrapped in
    `Agent(string txflowNetwork, uint32 chainId, uint32 apiVersion, bytes32 connectionId)`.
- Envelope: `{action, signature:{r,s,v}, nonce, vaultAddress, signatureChainId}`; `v` is 27/28;
  low-S canonical required.

### Published test vectors (key `0xab…ab` → `0xe239cdc5fbe977a8a141b72194d3cf8c41bc5bc6`)

| Vector | Expected |
|---|---|
| `order` msgpack | `0xREDACTED_********REDACTED_********7463` |
| `order` connectionId | `0xREDACTED_********` |
| `order` signingHash | `0xREDACTED_********` |
| `approveAgent` signingHash | `0xREDACTED_********` |
| testnet domainSeparator | `0xREDACTED_********` |

Both vectors reproduced byte-for-byte with a hand-rolled canonical MessagePack encoder
(`scripts/eip712_msgpack_client.py`). **This is the gate that makes every later observation
trustworthy** — do not skip it on any exchange that publishes vectors.

## Key `/info` types

`perpMeta` · `perpMetaDetail` (margin tiers; query by **base** asset e.g. `BTC`, not `BTC-USDC`) ·
`clearinghouseState` (`accountType: perp|outcome`) · `l2Book` (`coin` = instrumentId) ·
`activeAssetCtx` (`markPx`,`oraclePx`,`lastPrice`) · `frontendOpenOrders` · `historicalOrders` ·
`userFills` · `userNonFundingLedgerUpdates`.

## Observed mechanics

- **Faucet**: `POST /request-fund` credits **999 USDC perp**, no email, virtually unlimited per fresh
  address. (Docs example said 300 — always verify what was actually credited.)
- **Price limits (asymmetric, oracle-anchored)** — the single most important environmental fact:
  - sell accepted from ≈ `0.846 × oracle`
  - buy accepted up to ≈ `1.05 × oracle`
  - `Market` order type is subject to the same limits and is **silently cancelled** past them
    (`cancelSource: CancelByPriceLimitRule`).
- **Mark price** = slow EWMA toward the book mid (resting a best bid just under the ask moved the
  mark ~+0.5% over ~16 s). Movable, but only as far as the price limits permit.
- **Oracle dislocation** is severe on illiquid markets (LDO: book 0.2596 vs oracle 0.4347; HYPE:
  mark 59.49 vs oracle 85.88).
- **Cross-margin liquidation** takes the whole account and cancels all its cross orders.

## Leads tested (operator-supplied)

**H-1 — reduce-only re-cap. ❌ NOT vulnerable (two variants).**
Burst: long 0.006 BTC; two concurrent RO sells of 0.006 → one filled, one **rejected** with
*"Place order failed: New order will increase your position. Turn off Reduce-only to continue."*
Resting variant: place 2 RO sells with remaining position → only the quantity up to position size
rests; the over-size order vanishes. The engine re-caps RO correctly.

**L1 — cross partial liquidation. ❌ No bug found — but the first verdict was RETRACTED, read this.**

> ⚠️ **Correction (same session, after the table below was first written).** The "full close" rows
> came from monitor samples that were **transient read failures** (a response with no `marginSummary`
> and no `assetPositions` while the position was still open). They were mis-read as liquidations. When
> the accounts were re-read directly, **E and F were still open.** The verdict was formally withdrawn
> to the operator. Treat the table below as *unverified*; the reliable observation is the last row.

Engineered positions (LDO; equity varied by transfer in/out):

| Account | Size req → opened | Tier | Reported | Status |
|---|---|---|---|---|
| A | 50,100 | 2 | full close | documented-correct if it fired (partial only from tier 3) |
| D | 20,298 | 2 | reduced to 20,000 | plausible, not re-verified |
| D | 70,001 | 3 | "full close" | **unverified — read artifact** |
| E | 99,000 → 21,806 | 2 | "full close" | **unverified — E still open on re-read** |
| F | 30,000 → 28,622 | 2 | "FLAT" | **unverified — F still open on re-read** |
| G | 28,622 → **25,702** | 2 | **stayed open at ratio 1.27** | **reliable: engine trimmed size, account solvent** |

**The only defensible read:** an order whose size does not fit the account's available margin is
**trimmed** to what fits (28622 → 25702) and the residual is cancelled
(`historicalOrders`: `Canceled — remaining size … beyond slippage protection`); the account is left
**open and solvent**, never forced negative. That is protective behaviour, not an L1 bug. The real L1
finding would require the *opposite*: a tier-3+ position **below maintenance** closed in full when a
partial reduction sufficed.

**Narrative does not survive the arithmetic.** Ratio<1 requires
`loss_at_open > initial_margin_deposited`, i.e. `(entry−mark)/mark > 1/L` under the assumption the
whole position must be marginable at open. On a tight market (`ask≈bid≈mark`) that needs
`L > 1/(mmr+fee)` — e.g. ~65× at mmr 1.5 % — above the tier cap. On a dislocated market the
half-spread does give `1/L < half_spread/mark`, but the band is narrow and easily overshot: **set the
equity from the live tier `mmr` (never an assumed constant)** or the ratio lands at the wrong place
(observed: target 0.6, actual 1.27, off by exactly the assumed-vs-real MMR error).

**L7 — bankruptcy-price staleness. ❌ Not proven.**
Forced a tier-2 liquidation (50,100 LDO): `userFills` shows
`dir="Liquidation: Sell" px=0.2736 sz=50100 closedPnl=-981.506`. Fill and formula were consistent;
no observable stale bankruptcy price. The takeover price is set at bankruptcy by design, so any
claim needs the *computed* bankruptcy price to demonstrably diverge from the settlement fill.

**L2 — IOC equity floor. ❌ Not vulnerable.**
IOC buy 85,000 CRO (cap 0.06427) swept a ~$9,930-book: fill 0.06132 vs mark 0.06126,
loss $5.56, ratio 8.15, equity still ~1,395. Position-size cap (85,000 @ 20×) and book depth
prevented any large slippage. Instruments that also have a small `maxMarketOrderSize` block the test
entirely (BTC 100, ETH 2000, HYPE 980).

## ⭐ Actual finding: position neither closable nor liquidatable

Chain of evidence (all live on testnet):

1. `l2Book` LDO best bid **0.2596**; `activeAssetCtx` oracle **0.4347**.
2. Sell floor = ~`0.846 × oracle` = **0.3678** → the book bid is **1.42× below** the floor.
3. Every close attempt is refused by the engine, quoting its own bound:
   *"Order sell price is not within the price limit (Minimum price: 0.3696; Maximum price: 2.1739)"*.
4. Orders submitted as `Market` report `{"status":"ok"}` yet `historicalOrders` shows
   `status: Canceled`, `cancelSource: CancelByPriceLimitRule`,
   `cancelReason: "Remaining size canceled: price moved beyond slippage protection"`.
5. A forced liquidation reduces the position but leaves a residual (`userFills` partial fill).
6. Result: a long at minimum leverage that **cannot be closed and does not fully liquidate** →
   collateral locked (≈ $193 + $263 observed across accounts).

Impact framing: *collateral becomes irrecoverable* — "loss of user funds / incorrect settlement"
class, not merely "an order failed".

Root cause shape (generic): the order price limit is anchored to the oracle while liquidation uses
the mark; when the oracle dislocates far from the book, the closing order price required to satisfy
the limit is unattainable on the book, and the liquidator's disposal cannot clear the residual.

## Reusable numbers

- LDO instrumentId 23 · HYPE 44 · CRO 33 · LTC 5 · ICP 28 · CASHCAT 82 (halted).
- Margin tiers: query `perpMetaDetail` by **base asset**. The tier-1 `mmr` is *not* the one that
  applies to a mid-size position. LDO worked example: tier-1 `mmr 0.006` / tier-2 `mmr 0.0106` /
  tier-3 `mmr 0.015`, `takerFeeRate 0.0006`, `priceTick 0.0001`, `szDecimals 0`. Using an assumed
  `0.0156` for `mmr+fee` (vs real tier-2 `0.0106`) is what silently broke five runs.
- CRO LDO sell-floor trap: `book bid 0.2596` vs `0.846 × oracle 0.4329 = 0.3662` → the floor is
  **1.42× above** the only executable price; both `Market` and floor-priced `Limit` closes are
  cancelled (`CancelByPriceLimitRule`, `CancelByReduceOnlyPrice`).
- Sweep cost to move an N-tier position past maintenance: sum of ask-side notional up to the required
  mid; on liquid markets this ran into the millions of USD, i.e. **not reachable** with faucet capital.
- The report for the stuck-position finding landed at
  `D:/data hermes/bugbounty/txflow/txflow-F1-position-lockup/` — PDF + `email-draft-F1.eml`
  (to `security@txflow.com`, obtained from the docs search index via `mailto:`), CVSS 6.5
  `AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H`, reproduced 3/3.
