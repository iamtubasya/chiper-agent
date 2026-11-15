# Mark Price ↔ Price Band Deadlock

The highest-yield finding class on a perp venue that publishes an **oracle** and derives the
**mark** from its own book. Worked case: TxFlow testnet, LDO-USDC, 2026-10-11.

## The mechanism

The published model was:

```
mark      = oracle + 30s-smoothed average of ( (bid1+ask1)/2 - oracle )
order band = [oracle*0.85 .. oracle*1.05]  (sell)
             [oracle*0.95 .. oracle*1.05]  (buy)
```

The premium term is the **only** thing that can move the mark relative to the oracle, and it can
only be moved inside the band. So:

1. spot (oracle) moves further than the band permits the book mid to follow;
2. the mid is stuck, so the premium saturator has nothing left to transmit — the 30 s average and
   the fresh 3 s oracle updates cancel out;
3. **the mark parks at the book mid** and never returns to the oracle.

Once that is true, the band now points the *wrong way*: the permitted sell floor sits far above the
best bid, so no sell order that could fill is admissible. The position cannot be exited by its
owner, and the liquidator — whose disposal step is a *sell* — has no admissible price either, so the
liquidation cannot complete. The engine also cannot close the position it is trying to liquidate.

## The measurement (two reads, no privileges)

```
POST /info {"type":"activeAssetCtx","coin":"<id>"}  -> markPx, oraclePx
POST /info {"type":"l2Book","coin":"<id>"}          -> best bid, best ask
```

```
bid 0.2596   ask 0.2940   mid 0.2768
mark   0.2768   <- identical to the mid (delta 0)
oracle 0.4326   <- +56.3% above the mid
mark/oracle = 0.64  (-36.0%)
```

`mark == mid` to the tick, sampled 80 s, is the tell. A live premium term should *not* be pinned to
the mid — a genuine premium is `mid - oracle`, and here it is `-0.15655` and never moves.

### Confirm the premium is live but bounded

Place a resting (non-crossing) order that becomes the best bid, 1 unit and then a large size, and
watch the mark for 10–15 s. On the worked case each attempt moved the mark by **+0.0001**. That is
the proof that the estimator is working and *bounded*, i.e. that the failure is the band, not a dead
process. Include this — it pre-empts "the mark service was down".

## Turn the observation into a finding: scan every market

One decoupled market is a curiosity; a count is a finding. For each listed instrument compute
`oracle*0.85` (the sell floor) and compare with the live best bid:

```python
floor   = oracle * 0.85
blocked = floor > best_bid          # no sell that COULD execute is admissible
gap_pct = (floor - best_bid) / best_bid * 100
```

Result on the worked case: **23 of 66 markets**, worst `PUMP +198%`, then `STRK +141%`,
`UNI +112%`, `ENA +111%`, `NEAR +83%`, `ARB +82%`, `AAVE +52%`, `CRV +45%`, `LDO +42%`.
Persist the whole table (`ev/<target>_band_scan.json`) — the triager needs the list, not the count.

## Verify the band to the tick before claiming it

A one-tick differential makes the band mechanism undeniable:

```
px 0.3677 (oracle*0.85 rounded down) -> rejected
     "Order sell price is not within the price limit (Minimum price: 0.3678; Maximum price: 2.1634)"
px 0.3678                            -> accepted
```

The engine prints its own bounds, which also reveals the formula — read the bounds to infer the base
(`Minimum`/`0.85 ≈ oracle`, `Maximum`/`1.05 ≈ oracle`).

## The impact chain to argue in the report

1. **Mark ≠ oracle, unreachable.** Measured, plus the market-wide count.
2. **Owner cannot exit.** Every sell that could fill is inadmissible (tick-verified boundary).
3. **Liquidation cannot complete.** Cite the venue's own Risk Engine wording for the disposal step
   ("a single reduce-only IOC order, priced past the bankruptcy price, so the book has room to
   absorb it"). If the sell floor is above the whole bid book, that order cannot reach liquidity.
   This is why liquidation attempts fail *while the account is provably at maintenance margin*.
4. **Loss is system-created and quantified.** `deposits (rawUsd) 1240.77 → equity 498.39`, margin
   ratio 3.87, position -59.6% of equity. And the direct cost of the mechanism: a market BUY of
   100,000 units filled at the 0.2940 touch and was **instantly marked at −$33,500** (mid 0.2768 vs
   fill 0.2940). Always report the entry-vs-mark gap as money.

## What NOT to claim

- Do not claim the oracle itself is wrong — the book is wrong, and the mark follows the book.
- Do not claim "manipulable" from the resting-order experiments: +1 tick is the *bounded* response,
  not an exploit. It is evidence that the premium is alive.
- The market count is a **snapshot**; the affected set changes as spot moves. Say so, and state the
  mechanism as the finding.
- If the venue's impact table separates "outage/degradation" from "incorrect final state / financial
  loss", present both readings and let the vendor classify. Do not inflate.

## Candidate fixes to hand the vendor

Widen the band; clamp the mark to the oracle within a tolerance; mark PnL/margin against the oracle
while the book is dislocated; or fall back to an oracle-anchored mark when the book holds no
admissible liquidity.
