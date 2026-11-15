# Failure class: `status:ok` for actions the engine then cancels

## Symptom

`POST /exchange` returns `{"status":"ok","response":{"type":"PlaceOrder","data":{"statuses":
["success"]}}}` — but nothing happened. The terminal outcome lives only in the account ledger:

```
historicalOrders[] -> order.cancelSource, order.cancelReason, order.status ("Canceled")
```

Observed cancel sources (TxFlow):
- `CancelByPriceLimitRule` / *"Remaining size canceled: price moved beyond slippage protection"* —
  a reduce-only **market** sell whose executable (book) price is below the engine's minimum limit
  (`~0.846 × oracle`). Includes the engine's own numbers: `Minimum price: 0.3696; Maximum price: 2.1739`.
- `CancelByReduceOnlyPrice` / *"Canceled: a better-priced reduce-only order took precedence"* — a
  second reduce-only order at the same/worse price is dropped in favour of the better one.
- `UserCanceled` — normal.

A client that never reconciles via `historicalOrders` / the WS order-update channel believes the
order worked. This same class shows up as:
- an outcome IOC order returning `ok` + traceId, then never filling (async queue);
- N concurrent order submissions all returning `ok` while the engine only kept the ones that fit
  (`hold` on the balance is the truth, an `ok` ack is not).

## Why it can reach "collateral permanently locked"

If the silently-cancelled order is the only way to *close* a position on a market whose oracle is
dislocated above the book, then:
- you cannot close (sell blocked below the floor; market orders cancelled by the same rule);
- you cannot be liquidated either (with margin, the deposit bonus keeps ratio > 1);
- ⇒ the collateral is inaccessible. Demonstrated on a long where the book bid was 1.42× below the
  engine's minimum sell price.

## How to prove it (evidence shape)

1. Reproduce **3×** with a fresh account state each time; capture raw `/exchange` responses AND the
   `historicalOrders` cancel source for the same order.
2. Show the position is **unchanged** after each attempt (`clearinghouseState.assetPositions`) —
   with a retry-loop reader, because a single read can transiently return nulls.
3. State the root cause: the price-limit floor is validated against the **oracle** while execution
   is against the **order book**; on dislocated markets the two disagree.
4. Remediation: don't apply the oracle-derived floor to reduce-only orders (risk is bounded by the
   position), constrain the limit to the executable book range, guarantee the position is exitable,
   and stop returning `ok` for orders the engine will cancel.

Report the **specific consequence** (position locked / ack mismatch), not "the API lies" in the
abstract — triagers rate on demonstrated impact. Keep severity honest (testnet + a normal
dislocated-market precondition ⇒ Medium/high-range, not automatic Critical).
