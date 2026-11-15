---
name: perp-dex-audit
description: "Audit perp DEX / CEX trading venues: signed APIs, margin, liquidation, settlement, event contracts."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, web3, defi, trading-api, eip712, msgpack, margin, liquidation, replay]
---

# Perp-DEX / Trading-Venue API Audit (black-box)

## When to use

The target is a **trading venue API** — perpetual DEX, derivatives exchange, CEX, or a
prediction/outcome market — and you must drive it programmatically to test the money logic
(margin, liquidation, order matching, collateral accounting, transfers). There is usually **no
client library in your language**, so step 1 is reconstructing request **signing**. Load this the
moment a target advertises "trade", "positions", "liquidation", "leverage", or "outcome markets".

Sibling skills: `cex-event-contract-audit` (settlement/price-feed bias), `financial-logic-verification`
(figure correctness vs a regulator's rules), `hunt-business-logic` (generic write-endpoint tampering).
This skill is the perp/derivatives **mechanics + API-reconstruction** track.

**Operator workflow (this user):** execute-first — do NOT close a turn with a menu of options
("mau A, B, atau C?"). Pick the highest-expected-value remaining action, DO it, then report what
happened. Options only when the choice touches the operator's money/account/vendor scope.

## 0. Recon — cheapest wins first

1. **Docs site**: look for `/llms.txt` and `/llms-full.txt` — a single plaintext file is far cheaper
   and more complete than scraping rendered HTML. Grep it with python `s.find` (regex on a 400 KB
   blob is fine for targeted hunts).
2. **Frontend JS bundle**: pull `/assets/*.js`, grep for the API base and endpoints. Look for
   `VITE_*` (or similar) config blocks that leak base URLs, WS URLs, and app IDs; and for the
   endpoint table (`"/info"`, `"/exchange"`, `"/api/v1/...`). A venue often mirrors a known
   architecture — Hyperliquid-style `POST /info` (reads) + `POST /exchange` (signed writes).
3. **Node vs gateway split**: testnet node host (e.g. `rpc.<tld>`) and the gateway host often serve
   the *same* `/info`. Faucet and paged list endpoints usually live on the gateway only.
4. Enumerate instruments via `perpMeta` (perp markets) and `outcomeMeta` / `perpMetaDetail` (tier
   tables). Find the **margin tier table** per instrument — you cannot reason about liquidation
   without `mmr`, `maxLeverage`, and the tier size bounds.

## 1. Reconstruct signing and VALIDATE against published test vectors FIRST

Never fire a live signed call until your signature machinery reproduces the docs' test vectors
**byte-for-byte**. Two flows are typical (Hyperliquid-derived):

- **Direct EIP-712** for account-level actions (`approveAgent`, `tokenSend`, `withdraw3`,
  `approveBuilderFee`). Each action = its own primary type.
- **Agent signing** for trading actions: `msgpack(action without "type")` ‖ `nonce` BE8 ‖ vault flag
  → `keccak256` = `connectionId` → sign `Agent(chain,network,apiVersion,connectionId)`.

Pitfalls that cost real time:

- **The EIP-712 typehash field ORDER can differ from the action's JSON shape.** Read the exact
  typehash string from the docs (e.g. `Withdraw3(string txflowNetwork,address destination,string
  signatureChainId,address tokenAddress,string amount,uint64 nonce)` — destination *before*
  signatureChainId, and chainId is a **string**). A wrong typehash gives `failed to recover signer`
  — use that as your iterate-until-correct oracle.
- **msgpack must be canonical**: map with named keys, preserve field order (do NOT sort), omit null
  optionals, most-compact ints, native bool/str. A tiny encoder is ~40 lines and verifiable against
  the vector.
- **Nonces are millisecond timestamps**, not counters (window usually −2d/+1d). Canonical **low-S**
  signatures (most libs normalise).
- Python: `eth_account.messages.encode_typed_data(full_message={"types":..., "primaryType":...,
  "domain":..., "message":...})`; require `primaryType` explicitly or it raises.

## 2. Provision accounts, then control capital PRECISELY (the key enabler)

- **Faucet** is often unlimited **per fresh address** with no e-mail. Mint a fresh key, claim, and
  **consolidate** to your main test address with a signed `tokenSend` (transfer between accounts).
- **Agent authorization must be (re)done after the account first holds funds.** Order: fund →
  `approveAgent` → trade. Signing `approveAgent` on a zero-balance account fails with
  `Account not found`; trading with an unauthorized agent fails with
  `Agent 0x… is not authorized by any account`.
- **You can both RAISE and LOWER equity on demand**: send funds OUT to a throwaway address to lower,
  and consolidate fresh faucet addresses to raise. This is what lets you place a position **exactly
  inside a liquidation band** instead of only crossing it by market luck. Without this you can only
  produce deep-underwater positions (ratio ≤ 0) and will mis-conclude "the engine always full-closes".

## 3. Margin / liquidation model (compute before you act)

```
notional          = size × mark
initial margin    = notional / leverage
maintenance margin= notional × MMR          (MMR from the SIZE tier)
liquidation fee   = notional × takerFee
margin ratio      = (equity + unrealizedPnl) / (maintenance margin + liquidation fee)
liquidation when ratio < 1.0 ; bankruptcy price = where equity hits 0
```

- **Read the tier table** and pick the size class deliberately. Partial liquidation (documented at
  tier ≥ 3 on some venues) requires the position to sit **barely** below maintenance, i.e.
  `(entry − mark) ≈ (mmr + fee)·mark`. Deep underwater ⇒ full close (correct, not a bug).
- **Grade performance vs the documented contract**, not vs your intuition. If tier 1–2 says
  "full close", a full close there is correct.

## 4. Technique that WORKS — force a deterministic liquidation

On testnets the **oracle is routinely dislocated from the book** (oracle pinned to mainnet, book
thin). Two levers:

- **Mark is moveable and lagging.** It trends toward the book mid (EWMA), it is NOT oracle-pinned.
  A resting order that becomes best bid/ask drags the mark over seconds–tens of seconds.
- **Therefore you can** (a) open an *already-underwater* position by trading at the touch when
  `mark ≠ touch`, or (b) push the mark toward a resting order to cross maintenance.

Watch the transition live with a **background monitor** sampling `clearinghouseState` + book + ctx
to JSONL (0.05–0.4 s interval), then reconstruct the sequence. Verify the *transition*, not a single
snapshot.

## 5. PITFALLS (all hit for real)

- **Price limits are usually the binding constraint, not margin.** Observed on one venue: buy
  limited to `[×0.2, ×1.05]·oracle`, sell limited to `[×0.846, ×5]·oracle`. Asymmetric ⇒ pushing
  price **up** is cheap, **down** is near-impossible.
- **Market orders can execute below the sell floor but are then silently cancelled** —
  `CancelByPriceLimitRule` / "price moved beyond slippage protection". You get `status:ok` first.
- **Position limit is GLOBAL**: `Maximum position size at <N>x leverage is <X>`. A leftover position
  on that market (even dust, even a huge one) blocks placing/decreasing others. Clean accounts;
  one position per market at a time.
- **Reduce-only precedence is correct, not a bug**: a better-priced reduce-only order cancels the
  worse one (`CancelByReduceOnlyPrice`); RO size is re-capped at the position. (A naive "burst 2
  reduce-only orders → should flip net short" hypothesis is FALSE — the engine rejects the flip with
  an explicit message.)
- **⚠️ TRANSIENT READS CONTAMINATE STATE-TRANSITION CONCLUSIONS.** `clearinghouseState`
  intermittently returns `accountValue=None`, and a position can *appear gone* while still open.
  **Always** build a retry-loop reader (retry until a non-null field) and **never** conclude
  "FLAT / liquidated / position closed" from a single sample — re-read `assetPositions` until
  non-null before believing it. This one trap produced a false "5/5 full-close, no bug" conclusion
  that had to be retracted; the positions were still open.
- **Exact tick rounding**: prices must match the tick exactly or `Price precision does not match the
  tick size`. Python `f"{x:.10g}"` / scientific formatting **silently breaks** this. Use
  `round(px/tick)*tick` and format at full decimal precision.
- **`/info` reads are unauthenticated by design** (Hyperliquid-style). Reading other users'
  positions/fills is PUBLIC, NOT an IDOR — do not report it.
- Introductory margin: a position opened at ratio < 1 does **not** liquidate instantly on some
  venues — it is allowed to sit until the next risk sweep. Don't assume instant.

## 6. Concurrency & accounting probes (fast, high-value)

Fire N simultaneous ops that together exceed a balance/cap and read the authoritative state back:
transfers (`balance × 2.5` across 10 threads), **resting orders** over-committing margin, and
**merge/idempotency** (same op twice). Check for over-spend, negative balance, double-merge. A
correct engine validates each op independently and cancels the duplicate — record that as a
verified control, not an absence.

## 7. What is actually reportable (the failure class to hunt)

**`/exchange` returns `{"status":"ok","statuses":["success"]}` for actions the engine then silently
cancels.** The true outcome is only in `historicalOrders[].cancelSource` / `.cancelReason`. A client
that doesn't reconcile believes something happened that did not.

Escalate when the silently-cancelled action is a **reduce-only close on a dislocated market**: the
position can be *neither closed nor liquidated* → **collateral permanently locked**. Report the
**root cause** (price-limit floor validated against the oracle while execution is against the book),
with the engine's own ledger strings as evidence, honest severity, and the concrete remediation
(don't apply the oracle floor to reduce-only orders; return a truthful error instead of `ok`).
See `references/silent-cancel-and-position-lockup.md` for the worked case and evidence shape.

## 8. Discipline

- **Validate ≥3× before writing a report.** A candidate that does not reproduce is UNSTABLE — do
  not report it. Never fabricate; output from a tool that errored is not a result.
- Keep a tiny client module (`signing`, `transport`, `order builders`, `state reader`) + a
  **background monitor to JSONL** from the first minute; evidence must survive the session.
- One finding = one PDF PoC + one staged draft (Gmail DRAFT, not sent) — see `bug-report-delivery`.

## References

- `references/txflow-perp-testnet.md` — the worked TxFlow testnet case: EIP-712/msgpack test
  vectors, endpoints, margin-tier model, exact cancel-source strings, outcome-market (split/merge)
  mechanics, and the verified negative coverage ledger.
- `references/silent-cancel-and-position-lockup.md` — the `status:ok`-but-cancelled failure class
  and how to turn it into a reportable finding.

## Absorbed playbooks (complete sub-packages under `references/`)
Four formerly separate trading-venue skills now live here, each keeping its own
`references/`, `scripts/` and `templates/`. Load the one matching the venue shape.

- `references/perp-dex-engine-audit/PLAYBOOK.md` — engine-side view: read the risk-engine docs as a
  SPEC, mark-price reachability, band-vs-book exit reachability, acknowledgement-vs-execution,
  order-admission races, margin/balance semantics (`templates/signed-exchange-client.py`).
- `references/perp-dex-protocol-audit/PLAYBOOK.md` — phase-based live-API audit: the four rules,
  Phase 0-4, the "neither liquidatable nor closable" position, verification discipline
  (`scripts/eip712_msgpack_client.py`).
- `references/exchange-trading-api-audit/PLAYBOOK.md` — order-engine / margin / liquidation /
  settlement test grid plus the honest coverage ledger.
- `references/cex-event-contract-audit/PLAYBOOK.md` — CEX event and binary-option contracts:
  price-feed source tracing, cross-subdomain price inconsistency, settlement timestamp/direction
  statistics (Z-test), bias classification.
