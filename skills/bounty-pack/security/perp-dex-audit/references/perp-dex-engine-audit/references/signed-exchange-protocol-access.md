# Signed Exchange Protocol Access

Getting write access to a venue that has no public REST "place order" endpoint and no API key —
only signed envelopes over HTTP. Worked case: TxFlow testnet (`testnet-api.txflow-testnet.xyz`),
network `TxFlow-Testnet`, chainId 2511, but the shape generalises to any EIP-712/MessagePack venue.

## 1. Recover the protocol facts from the frontend bundle, not from tutorials

Reads (`/info`) are usually open. Writes go through a signed envelope, and the exact signing scheme
lives in the app's minified bundle. Grep it for the constants:

```bash
grep -o -E 'VITE_[A-Z0-9_]+' index.js | sort -u          # config object (base URLs, chain id, contracts)
grep -o -E '"/api/v1/[a-zA-Z0-9/_-]+"' index.js          # REST routes
grep -o -E 'https://[a-zA-Z0-9.-]+' index.js | sort -u   # every host the app talks to
```

`grep -o` with a pattern, never a giant minified dump into context. What you want out of it:
chain id, network name, the API base URL, the collateral token string, any WS URLs, and the
`approveAgent` / session-key flow.

## 2. The signing scheme (three parts, all required)

```
envelope = { action, signature:{r,s,v}, nonce, vaultAddress|null, signatureChainId }

action                 = the typed payload plus  {type, chainId, apiVersion}
connectionId            = keccak( canonical_msgpack(action_without_type)
                                  + nonce.to_bytes(8,'big')
                                  + (0x01 + vault_bytes  if vault else 0x00) )
EIP-712 domain          = { name:<network>, version:"1", chainId:<id>,
                            verifyingContract:0x000...000 }
primary typed struct    = Agent{ txflowNetwork:string, chainId:uint32,
                                 apiVersion:uint32, connectionId:bytes32 }
```

Two things break a hand-rolled client:

- **Canonical MessagePack matters.** Omit `null`/`None` values, preserve dict insertion order, use
  the minimal integer encoding (fixint / uint8 / uint16 / …). A key-order or null-handling
  difference produces a different `connectionId` and therefore a signature that fails recovery.
- **`signatureChainId` is not the network chain id.** On the worked target the envelope carried
  `signatureChainId: 421614` (an unrelated testnet) while `chainId` inside the action was `2511`.
  Take both from the bundle; do not derive one from the other.

Validate the encoder against the venue's published test vectors before any live call. If the docs
publish expected hashes, use them; otherwise verify with one harmless write (below).

## 3. Agent-key delegation is a separate step

A user controls a **main** key; an **agent** key is what signs orders, and it must be authorised
first. Symptom of a missing delegation, on every action:

```
{"status":"err","response":"Authorization failed: Invalid transaction:
  Agent 0x… is not authorized by any account"}
```

That is not a signing bug — the envelope was fine, the account is not bound. Authorise it with a
signed `ApproveAgent` action from the *main* key:

```
ApproveAgent{ txflowNetwork, chainId, apiVersion, agentAddress, agentName, nonce }
```

Money movement (`tokenSend`) and margin/leverage changes are likewise **main-key** actions; only
orders go through the agent key. Keep both private keys per account.

**Harmless liveness probe** (do this per account before a test run): send a post-only (`ALO`) order
far from the touch, confirm `status: ok`, then cancel it by client-order-id. If that fails you have
a client bug, not a target finding.

## 4. Reads worth knowing (the ones that actually matter)

| request | gives you |
|---|---|
| `perpMeta` / `meta` | every instrument: `index` (the order id), `priceTick`, `szDecimals`, `maxLimitOrderSize`, `maxMarketOrderSize`, `maxLeverage` |
| `perpMetaDetail` with **the base ticker** | that instrument's `marginTable.tiers` (`minSize`,`maxSize`,`maxLeverage`,`mmr`) and `takerFeeRate` |
| `clearinghouseState` | `marginSummary.accountValue`, `totalRawUsd` (**deposits**), `withdrawable`, `crossMaintenanceMarginUsed`, `crossMarginRatio`, `assetPositions[]` with `szi`,`entryPx`,`liquidationPx`,`marginUsed`,`unrealizedPnl`,`adlQuantile` |
| `activeAssetCtx` | `markPx`, `oraclePx`, `lastPrice`, `openInterest`, `prevDayPx` |
| `l2Book` | `levels[0]` bids / `levels[1]` asks, each `{px,sz,n}` |
| `frontendOpenOrders` | resting orders incl. `reduceOnly`, `tif`, `cloid`, `oid` |
| `userFills` | may be **disabled** on the node ("history is indexed; use the data-querier") — do not build a test on it |
| `outcomeMeta` (needs `exchangeId`) | prediction/outcome market list with `instrument_id` |
| `outcomeBalances` / `outcomePositions` / `outcomeFrontendOpenOrders` | the outcome sub-account |

`{"message":"invalid request: malformed <type> payload"}` means the payload shape is wrong (e.g.
`outcomeMeta` without `exchangeId`). Record as untested — not as evidence.

## 5. Order action shape

```
{"type":"order","grouping":"na","orders":[{
   "a": <instrument index>,          # NOT the ticker
   "b": true|false,                  # buy/sell
   "p": "<price>", "s": "<size>",    # strings, rounded to tick / szDecimals
   "r": <bool>,                      # reduceOnly
   "t": {"limit":{"tif":"Gtc|Ioc|Alo|FrontendMarket"}},
   "c": "<client order id>"          # cancel by this
}]}
```

Cancel: `{"type":"cancelByCloid","cancels":[{"asset":<id>,"cloid":"<c>"}]}`.
Index/margin: `{"type":"updateLeverage","asset":id,"leverage":N,"marginMode":"cross"}`,
`{"type":"updateMarginMode","asset":id,"isCross":true}`.
Transfer between sub-accounts: `tokenSend` with `fromAccountType`/`toAccountType` = `perp|outcome`.

## 6. Exact error strings, and what each means for you

| response | meaning |
|---|---|
| `Order sell price is not within the price limit (Minimum price: …; Maximum price: …)` | the band; the engine prints both bounds — use them, they reveal the band's base |
| `Price precision does not match the tick size: 0.001` | your rounding is wrong (read `priceTick`) |
| `Order failed. Maximum position size at <N>x leverage is <S>` | tier cap at admission |
| `Insufficient margin in account` | the position's margin freezes the balance — including for trims |
| `Amount must be greater than fee (1 USDC)` | transfer dust threshold |
| `asset not found: <number>` | wrong lookup key (use the ticker) |
| `Agent 0x… is not authorized by any account` | missing/incorrect `approveAgent` |
| HTTP 429 → HTML body | rate limited; back off, do not parse as JSON |

## 7. Rate limits and staging cost

- Space calls out; a per-second composite poll (book + ctx + orders) will trip a 429 within a
  couple of minutes. Poll the single cheap read in the loop, the composite every Nth iteration.
- Faucet claims are per-address and capped (observed ≈999 units per claim, hard-limited by the
  caller's own balance). Moving a few thousand units of equity requires several claims in sequence
  with a sleep between. Write the loop once and reuse it.
- Keep the funding/trim helper separate from the experiment so a failed run does not lose the
  staging work.
