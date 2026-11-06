# Cross-Chain Settlement / Bridge Attestation Audit

> Class: any protocol where an **off-chain attestor service** (oracle network,
> solver relayer) reads on-chain facts and produces a signed credit/mint, while a
> **separate on-chain program** moves the funds. Intent settlement protocols
> (Relay, Across-style hubs, CCTP-with-hub, deposit-address bridges) all fit.
> The bug class is NOT in either component alone — it is in the DIFFERENCE
> between them.

## The core technique: SAME QUANTITY, TWO COMPONENTS → DIFF THEM

A user deposit (or a solver fill) has one economic amount. Two different pieces
of code compute it:

1. the **on-chain program** (what the vault actually received)
2. the **off-chain attestor** (what gets minted/credited on the hub/ledger)

If those two definitions disagree, whoever gets the credit can be over/under-paid.
Read BOTH, side by side, for every value-carrying field: `amount`, `currency/mint`,
`recipient/depositor`.

### Quick classification grep (run per VM/chain adapter)

```bash
# In the attestor service, find where each credited field is set:
grep -rn "amount:" src/services/attestation/vm/*/index.ts
```

Then classify the SOURCE of each `amount` into exactly one class:

| Source | Example | Verdict |
|---|---|---|
| on-chain event arg | `log.args.amount` (EVM ERC20 Transfer/Deposit) | ✅ usually correct |
| balance delta | `postBalance - preBalance`, `pre/postTokenBalances` | ✅ correct (nets fees) |
| raw instruction data / args | `decodedInstruction.data.amount` | ⚠️ **RED FLAG** — verify the program transfers exactly this |
| caller-supplied hint | `hints[...].solverAddress`, `hints[...].lt` | ⚠️ check it is only a *locator*, never a value |
| re-derived value | `abi.decode(action, ...)` from data announced by the caller | ⚠️ check the on-chain verifier accepts the same encoding |

Mixed handling across code paths of the SAME adapter is the strongest signal:
if path A nets a fee and path B does not, one of them is wrong.

### Worked instance (Relay, 2026) — Solana `deposit_token` over-credit

- On-chain program `deposit_token` transfers `amount`; the vault receives
  `amount - transfer_fee` for Token-2022, and the program **emits the net value**
  in its `DepositEvent` (`amount: amount - transfer_fee`).
- The attestor **ignored the event** and credited `amount` straight out of the
  instruction args → over-credit by exactly the transfer fee.
- The attestor's own *direct-transfer* branch DID net the fee via
  `postTokenBalances - preTokenBalances` → proof the intent was to net, so this
  is an oversight, not a design choice.
- Fix: read `DepositEvent.amount`, or use the vault ATA balance delta like the
  sibling branch.
- Honest severity: the attacker's own round trip is fee-negative on both legs, so
  no attacker profit was demonstrated → S1/bounded, NOT an S4 drain. **Never
  upgrade a credit-mismatch to "theft" without a demonstrated profit path.**

### Fee-taking token variants to check on EVERY chain family

- EVM: fee-on-transfer / rebasing ERC20 (`safeTransferFrom` moves less than `amount`)
- Solana: Token-2022 `TransferFeeConfig` (`transfer_checked` credits less)
- Any chain with a "transfer hook" / memo fee

If the protocol emits/verifies an event carrying the NET amount, the attestor must
consume that event, not the instruction.

## Signature / id-derivation collision check (do this before hunting anything else)

Cross-chain ids are often `keccak(abi.encodePacked(chainId, encodedAddress))`.
`encodePacked` on `(string, bytes)` is ambiguous when one chain slug is a prefix
of another and the encoded lengths compensate.

Brute-force it against the REAL chain set — never reason about it in your head:

```python
# for every ordered (slugA, lenA) vs (slugB, lenB) with equal packed length,
# require slugA to be a prefix of slugB and la == (len(sb)-len(sa)) + lb  (or mirrored)
```
Verification result for Relay (60 live chains): only prefix pair `bob`/`boba`,
both EVM (equal 20-byte encodings) → different packed lengths → 0 constructible
collisions. Report as a LATENT hardening note (one future slug away from a
critical), not as a live finding.

## Recon for this class

- **Enumerate the attestor API from its own docs page.** Reference oracles
  commonly serve `/documentation/json` (raw OpenAPI) while `/openapi.json` is
  `401`. Fetch it to get the full route table (attestation endpoints + schemas)
  without auth. Confirm which `/attestations/*` routes are unauthenticated →
  then map every route that returns a signed `execution`/`mint`/`transfer`.
- **Get the deployed addresses from the protocol's own explorer, not the docs.**
  `GET /api/v2/search?q=<ContractName>` on a Blockscout explorer returns verified
  instances; then `GET /api/v2/smart-contracts/<addr>` returns the deployed source
  (send a browser UA — plain urllib gets 403). Diff it against the repo to confirm
  which version is live.
- **Chain config JSON** (e.g. `/chains`) often carries `httpRpcUrl`,
  `protocol.v2.depository`, `additionalData.fastMode` — enough to enumerate the
  real per-chain depository + RPC without guesswork.
- Clone BOTH repos: settlement/contracts AND the oracle service. A finding that
  spans them is invisible from either one alone.

## Scope traps specific to intent/bridge bounties

- Programs commonly exclude "the only exploit path requires a privileged role
  (owner, operator, **solver**, oracle)". An `oracle` signature path or a
  solver-only bypass (e.g. a `force` flag gated behind an API key) is therefore
  OUT of scope even when it looks like a bypass — check the exclusion list first
  and say so rather than filing.
- A mismatch that only lets an attacker grief third parties (vault/other
  depositors) with no self-profit is at best S1/low; state the absence of a profit
  path explicitly instead of implying theft.
- "Third-party protocols we compose with" (Hyperlane, Circle CCTP, Stork,
  Chainlink) are out of scope unless the root cause is in the protocol's own code.

## Verification checklist

- [ ] For every credited field: source classified (event / balance-delta / instruction / hint)
- [ ] Both components read for the same quantity; differences noted
- [ ] Mixed handling within one adapter flagged (fee netted on one path only)
- [ ] Fee-taking token variant checked per chain family
- [ ] id-derivation packing brute-forced over the live chain/slug set
- [ ] Attestor route table enumerated; which routes produce signed value
- [ ] Deployed source vs repo diffed
- [ ] Scope exclusions checked (solver/oracle/admin-only paths)
- [ ] Profit path demonstrated OR explicitly declared absent

## Round-2 sweep result (Relay, 2026-10-15) — the adapter-by-adapter verdict table

Re-run of the class-11 classification across ALL nine VM adapters
(`relay-protocol-oracle/src/services/attestation/vm/*/index.ts`). Cheap to redo,
and it is the single highest-yield pass on this protocol shape:

| adapter | credited `amount` source | verdict |
|---|---|---|
| `xrp-vm` | `tx.meta.delivered_amount` (NOT `Amount`) | HARDENED — also checks `validated===true`, `tesSUCCESS`, rejects outbound-from-depository, normalizes tagless X-address vs classic |
| `bitcoin-vm` | `sum(vout[].value to depository)` | safe (on-chain) — rejects >1 funded depository |
| `ton-vm` | `inMsg.info.value.coins` | safe (on-chain); comment `\|depositor=<addr>\|` lets a sender credit a third party (by design, gift-not-theft) |
| `ethereum-vm` / `gateway-vm` / `tron-vm` | event arg `log.args.amount` | safe class |
| `hyperliquid-vm` | RPC `txDetails` / `userNonFundingLedgerUpdates` delta | authoritative RPC; `hints["hyperliquid-vm"]{user,timestamp}` only *locates* the ledger entry and the tx hash must match |
| `lighter-vm` | `JSON.parse(txDetail.info).Amount` (provider API) | **needs-verify** — the only remaining API-sourced amount; diff against a live Lighter tx |
| `solana-vm` | `decodedInstruction.data.amount` | round-1 finding (bounded S1) |

`_hints` is **ignored** (`_hints`) by ethereum/gateway/bitcoin/solana — a hint-shaped
parameter that the adapter never reads is not a surface. Only hyperliquid + TON consume it.

## The auth-gate pattern to map FIRST (Fastify validation-then-auth)

These services run request **schema validation before the auth hook**, so an
empty body returns `400 required-property` even on a route that is actually
`401` for a well-formed body. Do not read the 400 as "open" — send a
minimal *well-formed* body per route and classify the second response:

| signature-class route | empty body | well-formed body | meaning |
|---|---|---|---|
| oracle `/attestations/transfer`, `withdraw-requests`, `depository-withdrawals`, `depository-deposits`, `recover` | 400 | **401** | value-signing, auth-gated ✅ |
| oracle `/attestations/solver-fills|refunds`, `withdraw-and-fill|refund`, `deposit-address-triggers` | 400 | 400 (nested schema) | need a fully valid `order`/`input` object -> keep drilling |
| relayer `/operator/*`, `/orders/:id/*`, `/router/*` | 401 | 401 | API-key gated (undocumented routes included — read the root `/` JSON that self-lists `endpoints[]`) |

## The recovery/withdrawal path is balance-bounded, not authorize-only

`POST /withdrawals/request` (api.relay.link) is signature-free at *prepare*:
`chainId`/`ownerChainId` are protocol **slugs** (`base`, `solana`, `bitcoin`),
not numeric ids. Prepare validates `amount` against the hub balance and returns
`{nonce, amount, additionalData}`; the owner signature is required only at
*execute*. Probed with a random owner: `400 "Insufficient balance: requested X,
available 0"` — i.e. you cannot prepare beyond a balance you do not have. The
execute-step signature is over a SHA-256 digest of the stable-stringified request
(`operation:"withdrawal"` + nonce + additionalData). **Control holds**; only
worth revisiting if the digest/`additionalData` binding ever changes.

## Websocket no-auth is a control gap, not a leak (check the whole picture)

`ws.relay.link` connects and accepts `{"type":"subscribe","event":"request.status.updated",
"filters":{"id":"<any|*>"}}` with **no** api key although the docs say key auth
is required (3/3 repro). But: (a) `id` is a mandatory filter (no firehose, and
`"*"` delivered **0 events in 100s**), and (b) the same request statuses are
already public via REST `GET /requests/v2`. Impact = nil ⇒ observation, **not**
a finding. The lesson generalises: before filing an "auth not enforced" report,
check whether the data is reachable by a cheaper public path — a documented
control that guards already-public data is a hardening note.
