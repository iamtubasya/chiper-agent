# Margin & Liquidation Test Design (and the tested negatives)

How to design liquidation/margin experiments so they actually reach the state they claim to test —
plus the probes that closed several leads on the worked case, so a future session does not repeat
them.

## 1. Reachability algebra — do this BEFORE spending attempts

A liquidation test is only valid if you can (a) *build* a position in the tier you need, and (b)
*sit* just below the maintenance threshold it implies. Both are usually constrained by caps you can
compute in advance. On the worked case six attempts died here.

Definitions per instrument (from the tier table; `N` = size, `markPx`):

```
deposit_needed       = N * markPx / leverage
MM                   = N * markPx * mmr(tier)
liquidation_fee (LF) = N * markPx * takerFeeRate
E_liq                = MM + LF              # the equity at which the cross ratio hits 1.0
E_span               = MM + LF              # how much room you have to push equity down
```

Two hard gates:

1. **Can the book even fill the tier you need?** The band caps the sweep: a buy can only lift the
   asks priced `<= oracle*1.05`. Sum that depth and multiply by price. On the worked case the total
   sweepable notional on the chosen market was ≈$12,000 — so a tier-4 (≥100k units) position was
   **never buildable**, regardless of equity. Compute `depth_available_within_cap` first; if the
   tier minimum exceeds it, the test is impossible and no amount of attempts will fix that.
2. **Is the equity window reachable?** For a partial-liquidation test you must place equity inside
   `(loss, loss + MM)`. `deposit_needed` is always above `MM` (since `leverage > 1/MMR` normally),
   so you must *remove* equity — which requires `withdrawable` to be positive. Once the position is
   open, the position's initial margin freezes the balance and trims start failing with
   `Insufficient balance`. Budget the trim in advance and expect the window to be narrow.

Sizing rule of thumb: **the smaller the better.** Prefer the cheapest market where a tier-3 minimum
is affordable; scan the tier table across all markets and sort by `tier3_min * markPx` before
locking a plan. A tier-3 position with a $2k notional is a far better laboratory than a tier-4 one
you cannot afford.

## 2. Do not open a position you cannot close

On a venue with an oracle-anchored band, an oversized open is **one-way**. The worked case ended
with a live account holding a position whose equity was down 60% and which could not be closed at
any admissible price. Before every experiment ask: *if this leaves me long, can I get out?*
Calculate `oracle*0.85 > best_bid` first; if true for the chosen market, do not build a long there
unless the long itself is the thing under test.

## 3. The freeze-vector probe (margin semantics)

Because the docs defined `balance = available + balance frozen by open orders`, a resting order
looked like it could push the cross ratio below 1 without any loss. Measure it explicitly:

```
snapshot -> place a large non-marketable bid (px just under the best ask, tif GTC)
         -> sample every ~1.2 s for 12 s -> cancel -> sample again
```

Compare `withdrawable`, the ratio and the mark before/after. On the worked case a resting 5,000-unit
bid dropped `withdrawable` by exactly the IM/lock (768.99 → 708.87) and left the ratio **unchanged**
(9.7483 → 9.7449) — so the frozen balance is *not* re-included in the numerator. **Vector closed.**
Write that as a negative; it is a genuinely useful control result.

Beware the confound: a resting *bid* at the top of the book also moves the mid, and therefore the
mark, which moves the ratio through uPnL. If the ratio drifts, decompose it — check `mark` on both
samples before attributing the change to the frozen balance.

## 4. The minimal-deficit trim (getting into the window on purpose)

Once you know `MM` and the live ratio, the exact trim that lands the ratio on a target `TR` is:

```
amount = MM * (ratio - TR)
```

One step, no overshoot, instead of the 20–30 small steps a percentage-based loop needs. Guard it:
the trim fails with `Insufficient balance` when the open position has frozen the balance — reduce
slightly and retry, and treat repeated failure as "the window is not reachable on this market",
which is itself the answer.

## 5. The acknowledgement differential (cheap, high-confidence, always runnable)

Independent of whether a liquidation can be triggered:

```
open long n  ->  SELL n at the touch (reduceOnly=false)   -> ack + position
             ->  SELL n again                            -> ack + position
             ->  BUY  n at the touch (control)            -> ack + position
```

Findings to look for in the pair of responses:
- `PlaceOrder / success` + position unchanged, **twice**, while the BUY control moves the position.
  Latency in the 0.2 s range rules out a timeout. This is the finding.
- The engine **rewriting order semantics**: an order sent `reduceOnly:false` and returned by the
  open-orders endpoint as `reduceOnly:true`. Check the flag the engine echoes back, never assume the
  flag you sent is the flag it used.
- An admission decision that depends on the *position's entry price* rather than the supplied flag
  (same price rejected on one account, accepted on another).

Always include the control leg in the report and in the evidence file — without it the ack is
arguable.

## 6. Race probes that need care to be meaningful

- **One batch**: put both reduce-only orders in a single action so they are deterministically
  ordered in the same block. This is stronger than two requests, and cheap.
- **Two threads**: synchronise on a `threading.Barrier(2)` and sign before the barrier so the two
  POSTs leave within ~0.2–0.5 ms of each other. Measure and report the actual delta; a "burst" that
  was actually 50 ms apart proves nothing.
- Price the orders where they **must** cross (through the book, inside the band). An order that
  rests because it was priced non-marketably produces a "no flip" result that is about your price,
  not about the engine.
- Sample the position every 0.2 s for ~3 s after each burst; a single read can miss a transient.

## 7. Tested negatives — do not re-spend these

From the worked case (TxFlow testnet, LDO-USDC, 2026-10-11). Carry these forward as *priors*, and
re-verify only cheaply:

| lead | attempts | result |
|---|---|---|
| Reduce-only re-cap bypass (2 reduce-only orders flipping a long) | 3 variants × 6–8 each: single batch; two barrier threads at 0.0002–0.0005 s; priced through the book | **Not reproduced.** Position never left the long side. The inverse anomaly was real (the reduce-only sells never executed at all). |
| Balance-freeze → ratio below 1 | resting 1-unit and 5,000-unit bids; 12 s sampling | **Vector closed.** `withdrawable` moved by the IM lock only; ratio unchanged. |
| Cross-margin partial vs full liquidation | 3 separate mechanisms (depth-limited open, freeze, minimal-deficit) | **Not demonstrated.** Blocked by tier reachability (buy cap ≈ $12k notional), never entered the window. Report as unreached, not as safe. |
| Stale bankruptcy price after partial fill | — | **Untestable** without producing a partial liquidation first. |
| IOC extreme slippage / equity floor | attempted a dump at `bid*0.5` | **Blocked by the band**: the request was rejected at the price floor, so no extreme fill can be produced on markets whose book is below the band. |
| ADL creating bad debt | — | **Not reached**: ADL needs the disposal step to fail, and it fails one step earlier. Note that the mark staleness (a separate finding) would be inherited by any ADL fill price, since ADL is documented to fill at the previous mark. |

Rule for the report: every one of these is written as *what was run + attempt count + why it is
closed vs merely unreached*. A negative with no attempt count is indistinguishable from a claim.

## 8. Staging hygiene

- Keep `accounts.json` (main + agent keys per account) and separate the **funding/trim helper** from
  the **experiment script**, so a crashed experiment does not lose the staged equity.
- Reuse a runner that takes the target params as env vars and writes to its own evidence file — the
  same script then serves the retest rounds without edits.
- Restore state at the end: flatten, cancel resting orders, and record the account state you leave
  behind. The operator submits; leave the accounts in a describable state.
