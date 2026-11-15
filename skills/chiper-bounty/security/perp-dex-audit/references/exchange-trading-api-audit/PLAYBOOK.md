---
name: exchange-trading-api-audit
description: "Audit a perp DEX / CEX exchange trading-API logic."
version: 1.0.0
author: "[K]vk"
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, security, exchange, dex, perp, order-engine, margin, liquidation, eip712, trading-api]
    related_skills: [bug-bounty, vuln-hunter, cex-event-contract-audit, onchain-source-recovery, report-writing]
---

# Exchange / Trading-API Audit (order engine, margin, liquidation, settlement)

## When to use

The target is a **trading venue you can hit over an HTTP(s) API**: a perp DEX, a CEX front-end
API, a prediction/outcome market, a vault or margin engine. Signals: docs pages with
`/info` (reads) + `/exchange` (signed writes), an EIP-712 / "signing" spec, an "agent key"
or API-key concept, faucet/testnet keys, order-book + clearinghouse endpoints.

**Not this skill** if the target is only a website UI, or a pure on-chain contract with no
order API (use `smart-contract-audit` / `onchain-source-recovery`). For binary-option
*settlement-bias* specifically, `cex-event-contract-audit` is the closer sibling.

The highest-value bugs in this class live in the **money path**, not in HTTP plumbing:
margin accounting, liquidation, settlement, entitlement, and the *honesty* of the API response.

## 0. Recon — get the spec before writing any client

1. **Find the API host, not just the website.** Grep the front-end bundle for
   `VITE_*API*`, `baseURL`, `wss://`, `https://[a-z0-9.-]*api*`. Fetch `/assets/*.js` and, if a
   sourcemap is served, `.js.map` → `sourcesContent`.
2. **Docs sites often expose a machine-readable full or summary spec** — a `/llms-full.txt`,
   `/llms.txt`, `openapi.json`, `/documentation/json`. These give the *complete* endpoint +
   signing contract without reading HTML. (Provided-vs-guessed: the spec told us the exact
   EIP-712 domain, the MessagePack framing, and the request envelope.)
3. **Rebuild the non-obvious wire formats from the SPA's own doc bundle.** Rendered docs pages
   embed only a placeholder component (`<ExchangeBody action=... field=.../>`); the real field
   list ships in the per-page doc chunk (`assets/<action>-<hash>.js`) or a search index JSON
   (`/assets/../search-index-*.json` → `storedFields`). Read the `field="<name>"` attribute to
   learn the JSON key (`field="order"` singular vs `field="orders"` array is the difference
   between `invalid request` and a working call).
4. **Write down the response envelope and the status vocabulary** before testing. Two things
   you will need constantly: what an accepted-but-not-final response looks like
   (e.g. `{"status":"ok", <traceId>}` = **queued**, not matched), and which read shows the
   **terminal** lifecycle (`historicalOrders`, `userFills`, `*OrderUpdates`).

## 1. Build a signed client that is verified against published test vectors FIRST

Most of these APIs sign every write. Before touching live state:

1. Implement the signing exactly (typed-data hash + the per-venue preimage, e.g.
   msgpack/nonce/vault-flag → `connectionId` → EIP-712 struct).
2. **Assert your output against the vendor's own test vectors** (docs usually publish an
   expected `signingHash` / `r` / `s` for a throwaway key). Match **byte-for-byte** before
   anything else. If they don't publish vectors, sign, then have the server recover your
   signer: a wrong hash surfaces as `failed to recover signer` / `not authorized`.
3. Only when vectors match do you start sending live writes.

A working reference implementation (EIP-712 typed-data + a canonical minimal MessagePack
encoder + `connectionId` derivation + envelope) is in
`references/signed-exchange-api-client.md` — copy and re-point it per venue.

## 2. Provision accounts + capital the legitimate way

- Faucets on testnets are frequently **per-address and unlimited for fresh addresses** —
  generate N throwaway keys, claim, then **consolidate** with a signed transfer
  (`tokenSend`-style) into your working account. This turns a $999 cap into arbitrary
  working capital without abusing anything.
- **Fund the account BEFORE approving the agent/session key.** An `approveAgent` on an
  unfunded account fails with `Account not found`; re-approve once it has a balance.
- Note the sub-account model (perp vs outcome vs spot, or isolated margin buckets) — collateral
  usually has to be moved between them explicitly, and *that move is often owner-signed only*.
- Keep one dedicated account per experiment. When you need a **clean** margin state, don't
  reuse one that already has stuck/partial positions — a leftover position silently consumes
  the position cap and invalidates the run (`Maximum position size ... is N`).

## 3. The test grid — enumerate the money path, then hit each stage

Map the ledger first, then test:

| Stage | What to attack |
|---|---|
| Order lifecycle | accept→rest→fill→cancel; partial fills; modify/replace; reduce-only semantics; IOC/FOK/post-only |
| Margin | initial vs maintenance, cross vs isolated, tiered-margin boundaries, margin-ratio formula |
| Liquidation | full vs partial, bankruptcy price, takeover price, ADL, collateral release |
| Settlement | expiry/resolution payout, price source, stale price |
| Transfer / withdraw | boundary (over-balance, below-min), fee, idempotency, concurrency |
| Entitlement | what unlocks a feature/balance — is the unlocking state trusted from the client? |

**To reach a liquidation band you must engineer the state.** Two levers that work:
- **Oracle-vs-book dislocation.** Price limits are usually validated against the *oracle* but
  fills occur on the *book*. On illiquid/new markets these can differ by tens of percent. That
  spread is both (a) a way to open a position instantly underwater and (b) the source of the
  real finding below.
- **Equity control.** `withdrawable = equity − marginUsed`, so you can *drain* equity with
  transfers to move ratio into any narrow band, and *add* equity to open bigger positions.
  Recompute the target equity from the venue's own margin formula, then trim precisely.

**Discriminator for "full vs partial liquidation":** open a size that sits in a **higher margin
tier** whose *tier-below* cap is below the position size, land the margin ratio just under 1.0
(not deeply underwater), and observe whether the engine closes everything or reduces to the
tier-below cap. The relevant band is razor-thin when both the entry loss and the freed margin
come from the same `(ask−mark)` spread — so prefer reaching it via an engineered band
(equity control) over hoping a market move lands there.

## 4. The finding class that actually pays: dishonest acknowledgements

**Verified real (TxFlow testnet 2026-10):** the engine returns
`{"status":"ok","statuses":["success"]}` for orders it then **cancels or never executes**.
Concrete case:

- Price limit derived from the **oracle** (sell floor `= 0.846 × oracle`), execution on the **book**.
- On a dislocated market (oracle +43…+76% over mark) the book sits **below the floor**, so every
  reduce-only close is accepted (`ok`) and then cancelled —
  `cancelSource: CancelByPriceLimitRule` / `CancelByReduceOnlyPrice`.
- The position is then **neither closeable nor liquidatable** → collateral permanently locked.

Generalise the hunt: for **every** write action, compare the HTTP response against the
**terminal lifecycle** (`historicalOrders.cancelSource`, fills, position delta, balance delta).
Any action that says `ok` but leaves no trace is a candidate. We found the same shape in three
independent surfaces (market-close, outcome IOC, order submit) — one **root cause**, several
symptoms, so **report one finding, not three**.

Report it as what it is: an **availability / loss-of-access-to-funds** defect
(CVSS `.../I:N/A:H`), scored honestly against the program's impact table — not inflated to
critical unless the venue's own table maps it there.

## 5. Pitfalls (all hit for real)

- **`status: ok` ≠ done.** Never conclude an action succeeded from the HTTP response alone.
  Re-read the object (position/order/balance) *and* the terminal ledger.
- **A transient read failure looks exactly like a state change.** A monitor/clearinghouse read
  that momentarily returns `null`/empty is **not** "the position closed". Re-read before drawing
  any conclusion; a single empty sample produced a wrong "always full-close" finding that had to
  be retracted. Poll ≥3× and require the engine's own ledger before asserting a state change.
- **Use the venue's real parameters, not round guesses.** Substituting a wrong maintenance-margin
  rate (we used 0.0156 where the tier said 0.0106) silently keeps the margin ratio above 1 and
  makes a reachable band look "unreachable" — you then wrongly declare the vector closed. Pull
  the tier table (`perpMetaDetail`-style) and compute from it.
- **Order price limits are asymmetric and side-specific.** On some venues buys may sit far above
  mid while sells are floored near the oracle (or vice-versa). Read the actual band by probing
  one order per side; don't assume a symmetric ±N%.
- **Ticks are exact.** `0.0001` and `0.00010001` are different errors; format prices to the
  instrument tick and sizes to `szDecimals`, or you get `Price precision does not match the tick size`.
- **Dust positions can be impossible to close** on the same dislocation that created the finding —
  if a reduce-only sell is rejected, pass the *minimum order amount* or route it through a
  counterparty account; a sub-minimum cleanup order just fails.
- **401 on a long-running job = token expiry.** Refresh the OAuth/API token mid-run rather than
  assuming the API is down (see the retry pattern, not "the tool is broken").

## 6. Honest coverage ledger

End with a table of **stage → tested / partial / N-A → result**, including negatives
("concurrent transfers > balance: 5 succeeded = exactly 2.5× balance, remainder rejected, balance
never negative — control correct"). A clean negative on a stage is a deliverable; an untested
stage is not. Never write "solid/locked down" without the ledger, and never dress a
not-reproduced hypothesis as a finding.

## Related

- `references/signed-exchange-api-client.md` — reusable EIP-712 + MessagePack signing client,
  test-vector validation, and the request envelope (with a worked venue as the example).
- `references/txflow-testnet-dex-2026-10.md` — full worked engagement: recon chain, the
  account/faucet/agent flow, the confirmed false-acknowledgement finding, and the per-stage
  negative results (outcome split/merge/settlement, concurrency races, `/info` disclosure).
- `bug-bounty` (pipeline/router) · `vuln-hunter` (generic hunter) ·
  `cex-event-contract-audit` (settlement-bias sibling — see overlap note in this skill's reply).
