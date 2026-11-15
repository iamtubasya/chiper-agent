---
name: claim-permit-authz-testing
description: "Use when testing claim/permit endpoints for takeover."
version: 1.0.0
author: curator
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, authorization, signature-binding, negative-results]
    budget_kb: 16
---

# Claim / Permit Endpoint Authorization Testing

Every product that lets a user *get value out* — accrued fees, rewards, balances, refunds,
settlements — exposes a **prepare-then-sign** flow:

```
POST /app-fees/{wallet}/claim   {chainId, currency, recipient}
  -> 200 {steps:[{items:[{data:{sign:{message:"0x<requestId>"},
                                post:{endpoint:"/execute/permits"}}}]}]}
POST /execute/permits?signature=<sig>   {kind, requestId}
```

The security question is never "does it require a signature". It is: **what is `requestId` a
commitment to, and whose key verifies it?** A single signature probe answers only half of that.

## When to Use

- Testing `/claim`, `/withdraw`, `/redeem`, `/settle`, `/app-fees/*`, permit/approval relays.
- A fund-loss-shaped bounty program where the only payable class is theft or insolvency.
- Any endpoint that returns `{sign: {message}}` and expects a signature back.
- Auth is established as enforced, and you now need to know whether it is *correctly bound*.

## The stop line — read before probing anything

Fund-loss programs pay for **demonstrating** a path, not for taking funds. Several exclude
*"attacks the reporter has already exploited"*, so completing a real theft disqualifies the report
even when the bug is genuine.

1. **Fresh zero-balance wallet**, generated locally (`eth_account.Account.create()`), never funded.
2. **Dead identifiers** for the victim side: `0x…dEaD`, `0x…0001`, `0x1234…5678`,
   `00000000-0000-0000-0000-000000000000`. Never a real user's address.
3. **Stop at the verdict, not the execution.** The server accepts the forged signature (bug proven)
   or rejects it (secure). Both are readable from the HTTP response.
4. **Never broadcast** the resulting transaction.
5. If the flow needs a real balance just to reach the signing step, that is a **blocker to report**,
   not a licence to use someone else's funds.
6. Delete throwaway key material after the run.

## The 17-test binding matrix

Run all seventeen. The rows people skip are the rows that hide bugs — and the rows that manufacture
false Criticals. Measured 2026-10-30 on `api.relay.link/app-fees/{wallet}/claim`; all held.

| # | Question | How | Secure answer |
|---|---|---|---|
| 1 | Non-owner signature accepted? | sign requestId with throwaway key, submit | `400 Invalid signature` |
| 2 | Is `recipient` in the commitment? | 3 different recipients, same wallet+amount | 3 distinct requestIds |
| 3 | Is `amount` in the commitment? | `null` / `1000000` / full balance | 3 distinct requestIds |
| 4 | Single-use? | submit the same id twice | 2nd → `inexistent or expired` |
| 5 | Does `x-api-key` change anything? | none / empty / `test` / 64 zeros | identical responses |
| 6 | Is `recipient == wallet` allowed? | set recipient to the fee owner | rejected (else it is a no-op) |
| 7 | Recipient validation | zero addr, short, UPPER, lower | malformed rejected, case-insensitive |
| 8 | Amount tampering | `0`, `-1`, `abc`, `1e30`, `0.5`, `" 1"`, `1;DROP` | regex + min + balance check |
| 9 | Chain/currency confusion | wrong chain, wrong currency, chain 0 | `No balance available` |
| 10 | Signature encoding abuse | v→0/1, v=255, 64-byte trunc, 66-byte pad, r=s=0, high-s, all-ff | all rejected |
| 11 | requestId existence oracle? | all-zero, all-ff, random 32 bytes | uniform error, no existence leak |
| 12 | Address normalization | checksummed / lower / UPPER in path | same balance for all forms |
| 13 | Path traversal changes the debited wallet? | `{me}%2F..%2F{victim}`, `/../`, `%20`, `+` | no substitution |
| 14 | Binds to wallet or to recipient? | sign with the recipient's key; sign with an unrelated key | both `Invalid signature` |
| 15 | Cross-environment replay | mainnet id submitted to testnet | `inexistent or expired` |
| 16 | Does traversal split balance-lookup from signature check? | `{me}/../{victim}`, then sign with **my** key | resolves victim's balance BUT still rejects my signature |
| 17 | Cross-kind confusion | claim id submitted as `eip3009` / `permit2` / `multicall`, and vice versa | `Could not find permit` — namespaces separated |

### The three rows that decide the verdict

**#14 is the actual takeover question.** If the signature verifies against `recipient`, anyone can set
`recipient = self` and self-authorize. If it verifies against the fee-owning `wallet`, the endpoint is
safe. relay binds to the wallet — `Invalid signature` for both a recipient-key and an unrelated-key
signature.

**#16 is the row that manufactures false Criticals.** A router that normalizes `{me}/../{victim}` to
`{victim}` will happily return the victim's *balance*, which reads exactly like theft. It is not: the
signature check still runs against the victim's key. Balance-lookup path and authorization path are
different code. Observed live — the traversal DID return the victim's balance, and the forged
signature was still rejected. Testing only the first half produces a Critical that dies on review.

**#11 needs a uniform-error check, not a single probe.** One `inexistent or expired` proves nothing.
The oracle exists only if a *real* id answers differently from a random one — send all-zero, all-ff
and a random 32-byte id and compare. Identical errors mean no oracle.

## Reusing a requestId will fool you into a false "secure"

requestIds are typically single-use and short-lived. Submitting the same id for several variants
returns `inexistent or expired` for every attempt after the first — which *looks* like a rejection of
each attack, but is only the burned id. **Mint a fresh requestId for every attempt.** Same failure
shape as an expired token: the instrument, not the target, produced the result.

## What to report when the boundary holds

A held boundary is a legitimate outcome and worth sending — but only if it carries actionable
content. Shape that works (relay.link, 2026-10-30):

1. **Open with the negative, in the first line.** *"I could not take over another party's accrued
   fees, and I am not submitting a vulnerability claim."* A vendor who reads "no claim" stops bracing
   and actually reads the rest.
2. **State the safety contract.** Throwaway keys holding nothing, no valid owner signature ever
   produced, nothing broadcast, no on-chain call. This is what makes a negative credible.
3. **List what HELD as evidence, not opinion.** Each bullet is a test and its observed rejection
   (`Invalid signature` for a non-owner key; three recipients → three distinct requestIds;
   resubmit → `inexistent or expired`). A negative with no enumerated tests is worthless.
4. **Demote the hardening notes into their own section**, prefixed so they cannot be read as a claim.
5. **Quote the program's own exclusion clause and concede it.** *"Items 2 and 3 fall under your
   stated exclusions for DoS without fund loss and for issues requiring social engineering. I am not
   claiming otherwise."* This is the most persuasive paragraph in the letter.
6. **Close with an offer and a stop clause.** Transcripts on request; "if you would prefer I stop
   testing this surface, tell me and I will."

### Three notes that survive a negative

All three are usually **excluded** by policy — label them engineering notes:

1. **Unhandled 500 on malformed input.** `""`, `0x`, `abc`, 66-byte, `r=s=0` returning `500` with
   library text (`signature missing v and recoveryParam`) instead of `400` is an uncaught parse path.
   Check for leaked internals and whether the service degrades under repetition — if neither, it is
   hygiene, not a finding.
2. **Missing rate limit on unauthenticated state creation.** 30 concurrent claim creations, no `429`,
   ephemeral state per call = resource-consumption surface. Report as hardening unless fund loss is
   shown; "DoS with no fund loss" is a near-universal exclusion.
3. **Blind signing.** A bare 32-byte hash with no EIP-712 `domain`/`types` means the wallet can only
   render hex — the signer cannot see amount, currency, or recipient. Not exploitable alone (the
   commitment is bound server-side, proven by #2/#3), but it is the prerequisite for phishing: call
   the unauthenticated prepare step with `recipient = attacker`, then ask the victim to sign an opaque
   hex string. Recommend an EIP-712 struct over amount/currency/recipient/chain.

**When NOT to send:** if the negative required nothing of the vendor and there are no hardening
notes, there is no letter to write. A negative with zero actionable content is a local artifact.

## Pitfalls

1. **One signature probe is not a binding test.** It proves the check exists, not what it commits to.
2. **Reusing a requestId** turns every subsequent variant into a fake rejection. Mint fresh each time.
3. **A traversal that returns the victim's balance is not a takeover** until #16's second half fails.
4. **A held control is not a finding.** Do not let the words "bypass"/"secret"/"admin" in your own
   notes resurrect a test that returned 4xx every time.
5. **Do not complete the theft** even to "prove impact". The HTTP verdict is the proof; completing it
   disqualifies the report and is theft regardless of program rules.
6. **Check the payout model first.** On a fund-loss-shaped program, missing headers, CORS, rate limits
   and introspection are not S1 — they are not findings at all.

## Related

- `artifact-backed-claims` — claim discipline, negative/coverage claims (user-owned; this skill
  supplies the endpoint-specific probe matrix).
- `triage-validation` — the go/no-go gate before writing anything up.
- `report-writing` — report structure and tone once a claim clears the gate.
