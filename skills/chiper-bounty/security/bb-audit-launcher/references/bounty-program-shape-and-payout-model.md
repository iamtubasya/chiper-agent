# Bounty Program Shape — read the SEVERITY MODEL before hunting

**Lesson (2026-10-30, relay.link).** Reading scope is not enough. You must read *how the
program pays* before spending a single request. Two programs with identical scope lists can
have opposite economics.

## The two shapes

| Shape | Pays for | Ignores | Opening move |
|---|---|---|---|
| **Hygiene-shaped** (most web VDPs, Bugcrowd/I1 web targets) | Missing headers, version disclosure, open redirect, CORS, rate-limit, GraphQL introspection | — | Surface sweep: nuclei, headers, JS, endpoints |
| **Fund-loss-shaped** (bridges, DEX, lending, solvers, infra) | Theft, insolvency, permanent freeze | **Everything above** | Trace the money path: who authorizes a transfer, and can you be someone else |

Relay is fund-loss-shaped: `S1 = griefing/DoS-no-fund-loss/admin-only`, `S4 = total theft`.
On this program a missing header is **not S1** — it is not a finding at all. A full day of
nuclei + header + JS sweep yields **$0 by construction**.

## Procedure — 5 minutes, before 0B

1. Fetch the program page and answer: **what is the severity model?** CVSS, fund-loss tier,
   or impact-tier?
2. Find the phrase that defines the floor. Relay: *"Admin-only bugs are S1"* and
   *"DoS with no fund loss"* → confirms fund-loss model.
3. Write the model into `SCOPE-<target>.md` as a sentence: *"This program pays only for X."*
4. Derive the opening move from that sentence, not from habit.
5. Ask: **which assets are explicitly excluded?** (next section)

If the model is fund-loss, do NOT start with nuclei. Start with: which endpoint moves value,
and what proves the caller is who they claim to be?

## Out-of-scope lists name PRODUCTS, not words

Relay excluded: *"Relay Vaults: contracts (RelayPool, RelayBridge, RelayPoolFactory,
RelayBridgeFactory, RelayPoolNativeGateway) + the vaults API + the vaults UI."*

`vaults-api.relay.link` had **open GraphQL introspection** with an enumerable `userBalances`
query. It looked like the best finding of the engagement. It is worth **$0** — the program
named the API, not just the contracts.

Procedure: for every host in your live list, grep the OOS text for the host's *product name*
(not just its FQDN). "vaults API" excludes `vaults-api.*`, `*-vaults.*`, `/vaults/*`, and the
vaults UI. Match on product noun.

## Safe money-path testing (non-negotiable)

Fund-loss programs pay for *demonstrating* a path, not for taking funds. And several programs
exclude *"attacks the reporter has already exploited"* — so completing the theft disqualifies
the report.

Rules used on relay.link:

1. **Fresh zero-balance wallet** generated locally (`eth_account.Account.create()`), never funded.
2. **Dead identifiers**: `0x…dEaD`, `0x…0001`, `0x1234…5678`, `00000000-0000-0000-0000-000000000000`.
   Never a real user's address, never a real order ID.
3. **Stop at the verdict, not the execution.** For an off-chain claim/permit flow the server
   either accepts the forged signature (bug proven) or rejects it (secure). Both outcomes are
   readable from the HTTP response. **Do not broadcast the resulting transaction.**
4. **Testnet first** when the vendor publishes one (`api.testnets.<domain>` for relay). Real
   end-to-end only if testnet cannot express the bug.
5. Delete test key material after the run.

## Signature-binding probe (off-chain claim / permit endpoints)

Pattern found on relay: `POST /app-fees/{wallet}/claim` returns a signing message, then
`POST /execute/permits?signature=…` consumes it. The question is **who may sign**.

```
1. Request claim for wallet W (W = dead identifier or your own empty wallet)
2. Read steps[].items[].data.sign.message  -> hex digest M
3. Sign M with a DIFFERENT key (your throwaway wallet)
4. POST /execute/permits?signature=<sig>  body {kind, requestId: M}
5. Verdict:
   "Invalid signature" / 4xx          -> SECURE (binding enforced)  [relay.link result]
   200 + transaction steps            -> BUG: signature not bound to owner
```

Do step 4 exactly once, immediately after step 2 — the requestId expires
(`"Claim request inexistent or expired"` means you were too slow, not that it is secure;
re-run the sequence).

## Anti-pattern this prevents

Spending a whole engagement producing a beautiful, well-evidenced report of
medium-severity hygiene findings on a program that only pays for fund loss. The work is real;
the payout is zero. Read the model first.
