---
name: perp-dex-engine-audit
description: "Use when auditing a perp/derivatives exchange engine."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, defi, perp, derivatives, margin, liquidation, mark-price, matching-engine, signed-protocol]
  scope: [perpetual DEX, CEX perp engine, on-chain CLOB, prediction/outcome markets]
---

# Perp / Derivatives Exchange Engine Audit

## When to Use

Trigger on any of these:

- the target is a **perpetual DEX**, an on-chain CLOB, a CEX-style matching/risk engine, or a venue
  with outcome/prediction markets;
- the user hands you a **lead list about the engine itself** — liquidation behaviour, margin modes,
  reduce-only semantics, bankruptcy/settlement price, ADL, mark vs oracle, order TIF — and asks for
  CONFIRMED/REJECTED per lead with numbers;
- the product has **no public order endpoint**: writes go through a **signed envelope** (EIP-712 or
  similar) that you must reconstruct from the frontend bundle;
- the venue publishes its **margin system / risk engine** documentation and you intend to test
  whether the documented algorithm actually holds.

Do not use for: Solidity source reading (`smart-contract-audit`), binary-option settlement-bias
statistics (`cex-event-contract-audit`), or generic web2 surface work on the venue's marketing site
(the `hunt-*` skills).

Deliverable shape the operator expects: per lead, **CONFIRMED with numbers + evidence** or
**REJECTED with what was run**; then one draft per confirmed finding, PDFs attached. Never a
"looks fine" summary.

Use when the target is a **trading engine**: the finding classes here are not injection classes,
they are **accounting and market-mechanics invariants** — can a user be forced into a position they
did not choose, can a position not be exited, is the mark price the margin is computed against
reachable, is an order acknowledged but never executed, does the liquidation path actually complete.

Different from contract auditing (`smart-contract-audit`: you read Solidity) and from
`cex-event-contract-audit` (binary-option settlement bias from public trade statistics). Here the
surface is the venue's **own signed API + the documented risk engine**, and the deliverable is a
reproducible sequence of signed calls.

## Rule 0 — read the risk-engine docs as a SPEC, then test the spec

Before any call: fetch the engine's own documentation (margin system, risk engine, liquidations,
ADL, order types/TIF, mark price). These pages are the spec you will falsify. Quote them verbatim in
the report — a vendor cannot argue with its own published algorithm. Key things to extract:

- the exact margin-ratio formula (numerator and denominator, both levels: account/cross and
  position/isolated) and the threshold at which liquidation starts;
- how the mark price is derived from the oracle and *which term can move it*;
- the order price band, expressed relative to the oracle;
- whether partial liquidation exists, from which tier, and to which size it reduces;
- what the liquidation steps are, and specifically **what price the disposal order is placed at**.

The two highest-yield spec statements are "the mark is oracle + a smoothed premium term" and
"the liquidator places a reduce-only IOC priced past the bankruptcy price so the book can absorb
it" — each of those is falsifiable with a few reads and no special privileges.

## Method

1. **Learn the product's money path first** (per the operator's global rule): how does it earn,
   signup → plan → pay → entitlement, where does value flow. For a venue: fees, funding, the
   protocol/liquidator vault, referrals. Business logic pays.
2. **Get protocol access, then validate the client against the published test vectors** before
   spending a single live call. Signing is the gate on everything. See
   `references/signed-exchange-protocol-access.md` for the EIP-712 + canonical-MessagePack +
   agent-key-delegation recipe, the metadata-lookup traps, and the exact error strings.
3. **Enumerate instruments from the engine itself, not from the site.** Pull the venue's meta
   endpoint once and cache it in-process: it carries the authoritative instrument id, tick size,
   size decimals, order-size caps and the full margin-tier table. Hand-rolled price/size rounding
   is the #1 wasted iteration.
4. **Snapshot state before and after every mutation** and write each phase to an append-only
   JSONL. Position, equity, `rawUsd` (deposits — this is what makes a loss provable), withdrawable,
   maintenance-margin-used, account margin ratio, mark, oracle, best bid/ask. A finding is
   `before → after` with both numbers.
5. **Run the test classes below**, one hypothesis per experiment, with a positive control that must
   move and a negative control that must not.
6. **Compute feasibility BEFORE spending attempts.** For anything requiring a position of a given
   tier, do the reachability algebra first (see `references/margin-liquidation-test-design.md`).
   Six attempts on this class died for a reason that was computable in two lines.
7. **Convert every negative into a coverage statement**, not silence: list what you ran, the exact
   attempt count, and why the lead is closed vs merely unreached.
8. **Report shape:** one draft per finding (never bundle unrelated findings), PDF PoC attached,
   plus an explicit NEGATIVES section and tested/not-tested coverage lists so a triager cannot read
   the submission as "everything else is clean".

## Test classes (in yield order)

### A. Mark-price reachability (highest yield; usually one read)

The mark is what PnL and margin are computed against, so a mark that cannot converge to the oracle
is a system-created loss on every position entered near the oracle.

```
POST /info {"type":"activeAssetCtx","coin":"<id>"}   -> markPx, oraclePx, lastPrice
POST /info {"type":"l2Book","coin":"<id>"}           -> best bid / best ask
compare:  mark  vs  (bid+ask)/2  vs  oracle
```

If `mark == mid` and `oracle` is far from the mid, the premium term is saturated and there is no
term pulling the mark back. Scan every listed market and count how many are dislocated — a count
like "23 of 66 markets" is what turns an observation into a finding. See
`references/mark-price-band-deadlock.md`.

### B. Band vs book: is the exit reachable?

The order band is expressed relative to the oracle (e.g. sell `[oracle*0.85, oracle*1.05]`). If the
band floor sits **above** the whole visible bid book, then no sell that could execute is admissible:
the position cannot be exited by its owner, and the liquidator — which must *sell* to reduce — has
no admissible price either, so the liquidation cannot complete. Falsifiable with one comparison per
market. Verify the boundary to the tick before claiming it (one price rejected, one tick above
accepted).

### C. Acknowledgement vs execution (cleanest, most reproducible finding)

Compare the **shape of the ack** against the **position delta**, always with a same-shape control.

```
open long; then:
  leg 1  SELL n at the touch (market/IOC, reduceOnly=false)  -> ack + position after
  leg 2  repeat                                               -> ack + position after
  leg 3  BUY  n at the touch (control)                        -> ack + position after
```

`PlaceOrder / success` with an unchanged position, twice, while the BUY control moves it, is a
finding in its own right: a client cannot distinguish "your sell filled" from "your sell did
nothing". Also check whether the engine **rewrites the order semantics** (a `reduceOnly:false` order
stored and returned as `reduceOnly:true`, or the reverse).

### D. Order admission / sequencing races

- Two reduce-only orders in ONE batch, and two barrier-synchronised threads (<1 ms apart), to test
  per-batch vs per-fill validation (position flip). Repeat 6–8× each.
- Whether an order priced where it *cannot* fill is rejected or silently accepted-and-dropped.
- Tier/size caps applied at admission vs at fill.

### E. Margin & balance semantics

- Does a resting (non-crossing) order move the margin ratio, or only `withdrawable`? The docs'
  "balance = available + frozen" invites a freeze-the-ratio-below-1 attack; measure it (a resting
  order changing only the IM lock closes that vector). See the freeze-vector probe design.
- Leverage vs equity at open: can the engine admit a position whose initial margin exceeds equity,
  then build it progressively as the fill walks the book (leaving the account instantly below
  maintenance, sometimes negative)?
- Liquidation minimality: does a partial reduction exist where the docs say it does, and does it
  reduce to the documented tier cap or close everything?

## Pitfalls

- **Price/size precision.** Compute rounding from the instrument's own `priceTick` / `szDecimals`
  (from the meta endpoint). The rejection is explicit — read it as a bug in your client, not the
  target.
- **Metadata lookup by the wrong key.** Numeric instrument id and base-ticker lookups can be
  different endpoints with different accepted inputs. If one says "asset not found: <id>", the
  other wants the ticker.
- **Unapproved agent key looks like a broken client.** "Agent 0x… is not authorized by any account"
  on every action means the delegation step is missing, not that signing is wrong. Probe with one
  harmless post-only order far from the touch and cancel it, per account, before a test run.
- **Non-dict responses.** Rate-limited / WAF'd responses come back as HTML, so `resp.get(...)`
  explodes. Return the status code alongside the parsed body, assert the shape, and back off on
  429 instead of firing more calls.
- **Cost of staging.** Moving equity into an account via faucet + transfer is rate-limited and
  capped per claim; batch it and expect a multi-claim loop. Trim/`withdrawable - 20` style probes
  hit "insufficient balance" once the position freezes the balance — that is the engine working,
  not the bug.
- **A constant-rate state poller is a lot of calls.** Read the cheap getter for the loop and the
  expensive composite (book + ctx + orders) only every Nth iteration.
- **Instrument ids differ per environment.** Page ids from docs/tutorials are not the live ones;
  always read the meta endpoint.
- **Progress output lies.** A watcher that compares the live size against the *requested* size will
  print "size changed" when the order was merely partially filled at open. Compare against the
  actual pre-open snapshot.
- **Do not read a failed call as a result.** An endpoint returning an error payload
  (`{"message":"invalid request"}`) means the payload was wrong — record it as untested, never as
  evidence.

## Evidence & delivery

- Append-only JSONL per experiment under `ev/`, one `phase` per record; a summary JSON with the
  headline verdicts (`V1..V4` style) so a triager can read one file.
- A `FINDINGS.json` carrying both `findings[]` **and** `rejected[]`, where every rejected entry
  names what was run and the attempt count. Negatives are deliverable.
- `MANIFEST.txt` with size + SHA-256 per evidence file.
- Coverage block: `tested:` / `not_tested:`, plus a line stating which tool classes were
  **N/A** — for a signed binary protocol, web scanners are N/A; say that instead of filing them
  as "not run".
- PDF build: `reportlab` is the reliably-present library (`fpdf2` may not be). Verify the produced
  PDF by extracting its text (`pdftotext file.pdf -`) and grepping for the headline numbers plus
  forbidden attribution words; `pdfinfo`/`pypdf` may be absent, so do not depend on them. Watch for
  a `.get("response")` that returns a dict where a string was expected (slice error at build time).
- Stage the submission as a Gmail DRAFT with the PDFs attached, then re-fetch it over IMAP and
  print filename + content-type + decoded byte length as proof. Draft only — never send.

## References

- `references/signed-exchange-protocol-access.md` — EIP-712 + MessagePack + agent-key delegation,
  metadata traps, exact error strings, endpoint/cap inventory.
- `references/mark-price-band-deadlock.md` — the band-vs-book deadlock, the scan shape, the
  boundary test, and the impact chain.
- `references/margin-liquidation-test-design.md` — reachability algebra for liquidation tests, the
  freeze-vector probe, the false-ack differential, and the corpus of tested negatives.
- `templates/signed-exchange-client.py` — starter client: canonical MessagePack encoder, EIP-712
  agent signing, tick/size rounding from live metadata, order/cancel/leverage builders, a 429-safe
  transport, and the harmless auth probe.

## Worked case (calibration)

TxFlow testnet, 2026-10-11. Two findings shipped as **separate** drafts; six other leads closed as
untestable with attempt counts recorded.

- The mark was pinned to the book mid (`mark == mid` to the tick over 80 s) while the oracle sat
  +56.3 % above that mid — so the sell floor (`oracle*0.85`) was above the entire bid book in
  **23 of 66** markets and no sell that could fill was admissible. The liquidator's disposal step is
  a sell, so liquidation could not complete either.
- A marketable SELL returned `PlaceOrder / success` with the position unchanged, twice, while the
  BUY control moved it — and an order sent `reduceOnly:false` came back stamped `reduceOnly:true`.
- Live cost of the first defect on a real account: deposits 1240.77 → equity 498.39, and a
  100,000-unit buy filled at the touch was instantly marked at −$33,500.
- Negatives worth reusing as priors: the balance-freeze vector is closed (a resting order moves only
  `withdrawable`), and the reduce-only re-cap race did not reproduce in 3 variants. See
  `references/margin-liquidation-test-design.md` §7 before re-spending attempts on either.
