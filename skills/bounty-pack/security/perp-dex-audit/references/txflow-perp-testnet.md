# TxFlow testnet — worked case (Hyperliquid-derived perp DEX)

Target: `txflow-testnet.xyz` (app) + `testnet-api.txflow-testnet.xyz` (gateway) +
`rpc.txflow-testnet.xyz` (node). Public bug bounty (testnet in scope, up to 150k USDC Critical),
contact `security@txflow.com` (find it in the docs search-index / page HTML, not on the page text).

## Endpoints / surfaces

- `POST /info` — unauthenticated reads (also served by the node host at `/info`).
- `POST /exchange` — **signed** writes. Actions: `order`, `cancel`, `cancelByCloid`, `modify2`,
  `updateLeverage`, `updateMarginMode`, `updatePositionMode`, `updateIsolatedMargin`, `approveAgent`,
  `tokenSend`, `withdraw3`, `outcomeOperate`, builder-fee + vault/referral actions.
- `POST /request-fund` — faucet (gateway only). **Unlimited per fresh address**, `{"address": ...}`
  → `{"status":"success"}`, credits 999 USDC (no e-mail, no KYC).
- Docs: `docs.txflow-testnet.xyz/llms.txt` and `/llms-full.txt` (405 KB plaintext — grep it).
  WebSocket channels: `/ws`, `/api-ws`, `/ws-rtds`.

## Signing (test vectors reproduced byte-for-byte)

Domain: `name="TxFlow-Testnet"`, `version="1"`, `chainId=2511`,
`verifyingContract=0x000…0`. domainSeparator `0xREDACTED_********`.

**Agent flow** (trading actions): `connectionId = keccak256(msgpack(action minus "type") ‖
nonce_BE8 ‖ vaultflag)`; sign `Agent(string txflowNetwork,uint32 chainId,uint32 apiVersion,bytes32
connectionId)`. Verified vector — action `{"grouping":"na","orders":[{"a":1,"b":true,"p":"50000.0",
"s":"0.01","r":false,"t":{"limit":{"tif":"Gtc"}}}]}`, nonce 1700000000000 →
`connectionId 0xREDACTED_********`,
`signingHash 0xREDACTED_********`.

**Direct EIP-712** (account actions). Exact typehashes:
- `ApproveAgent(string txflowNetwork,uint32 chainId,uint32 apiVersion,address agentAddress,string agentName,uint64 nonce)`
- `SendToken(string txflowNetwork,address toAddress,string amount,string fromAccountType,string toAccountType,string token,uint64 nonce)`
- `TransferToken(string txflowNetwork,string amount,string fromAccountType,string toAccountType,string token,uint64 nonce)` (self-transfer, `toAddress` omitted)
- `Withdraw3(string txflowNetwork,address destination,string signatureChainId,address tokenAddress,string amount,uint64 nonce)` — **field order differs from the JSON shape**; `chainId` in the action stays 2511 but the domain overrides via `signatureChainId` (bridge supports only some chains → `Chain ID 4331028 is not supported`).

Order body abbreviated keys: `a`=asset index, `b`=buy(bool), `p`=px(str), `s`=sz(str),
`r`=reduceOnly, `t`={limit:{tif}} or {trigger:{isMarket,triggerPx,tpsl}}, `c`=cloid.

`encode_typed_data(full_message={"types","primaryType","domain","message"})` requires `primaryType`
explicitly. `font`/msgpack: preserve order, omit nulls, compact ints.

## Margin model observed

`margin ratio = (equity + uPnl) / (notional·(mmr+fee))`, liquidation at ratio < 1. Tier table per
instrument (`perpMetaDetail` → `instruments[0].marginTable.tiers`): e.g. LDO tier1 ≤7000 (50x,
mmr .006) … tier2 7001–70000 (25x, mmr .01) … tier3 70001+ (20x, mmr .015). **Partial liquidation is
documented tier ≥ 3 upward.**

## Constraints that bind (get these before designing a test)

- **Price limits**: buy `[0.2·oracle, 1.05·oracle]`, sell `[~0.846·oracle, 5·oracle]`.
- **Market orders** (tif `FrontendMarket`) bypass the floor check but are then cancelled by
  `CancelByPriceLimitRule` ("price moved beyond slippage protection").
- **Position cap is global**: `Maximum position size at <N>x leverage is <X>` — a leftover stuck
  position blocks others.
- **Mark is NOT oracle-pinned**; it lags toward the book mid (EWMA over tens of seconds). A resting
  order at the touch drags it (observed +1.2% in 16 s).
- Nonces = ms timestamps, −2d/+1d window.

## Outcome markets (separate sub-account)

`outcomeMeta` (gateway, snake_case) → 378 live markets on channel 1 (Probly). `outcomeOperate`
`{split:[{a,s}]}` / `{merge:[{a,s}]}` (agent-signed). Verified mechanics:
- split s → 2 hedge legs (±s @ entryPx 0.5) + `hold = s` (withdrawable −s). NO-leg entryPx reads 0.5.
- merge capped by the **smaller leg size**; merging without holdings → `Merge could not be completed`.
- orders are **async** (HTTP `ok` + traceId ≠ filled); a reject looks identical to a never-filled.
- settlement pays 1.0/share to the winning leg (verified end-to-end).

## Verified-NEGATIVE coverage ledger (report this honestly; don't redo)

| Vector | Result |
|---|---|
| Concurrent `tokenSend` 10×869 vs 3476 bal | 5 accepted (= balance), 4 rejected, balance → 0, never negative |
| Concurrent resting orders over-committing margin | exactly the number that fits; 1 order left resting |
| `outcomeOperate` merge×2, split+merge, merge>holdings | correct (idempotent / capped / rejected) |
| Outcome settlement end-to-end | correct payout |
| `withdraw3` over-balance / under-min | signature recovers; rejects correctly |
| Input validation (size 0/-1/1e30, px 0/off-tick) | all rejected with correct messages |
| L1 reduce-only flip burst, H-1 RO re-cap, L7 bankruptcy staleness, L2 IOC equity floor | not reproducible — engine correct |
| `/info` other-user reads | public by design, not IDOR |

**Escape this trap:** the four "leads" above (written by the operator from another review) looked like
classic financial bugs but were all **control-verified non-issues**. Grade the engine vs its documented
contract; deep-underwater ≠ partial-liq test.
