# Off-chain claim / permit endpoints — proving the signature is bound to the owner

Sibling of `payment-callback-auth-probing.md`. That note covers *inbound* webhooks (does the server
verify the sender). This one covers the **outbound** direction: an endpoint that hands the client a
digest to sign, then releases value when the signature comes back.

Measured 2026-10-30 against a cross-chain bridge's solver API.

## The shape

```
POST /<resource>/{owner}/claim        or  /withdrawals/request  or  /execute
  -> 200 {"steps":[{"id":"authorize","kind":"signature",
                    "data":{"sign":{"signatureKind":"eip191","message":"0x<32-byte digest>"},
                            "post":{"endpoint":"/execute/permits","method":"POST",
                                    "body":{"kind":"claim","requestId":"0x<same digest>"}}}}]}
```

The server hands you a digest, you sign it, you POST the signature back. **The whole question is
whether the recovered signer is compared against `{owner}` from the path** — or whether the server
only checks that *a* valid signature exists.

## Probe (run this before reading any contract source)

1. Pick `{owner}` that is **not yours** but whose value is publicly visible — read
   `/{owner}/balances` and choose a burn address (`0x…dEaD`) showing a non-zero balance.
   **Never pick a real user.**
2. Request the claim with `recipient` = **your own** address. Capture the digest.
3. Sign with **your** key. Submit to the `post.endpoint` from the response.
4. Read the verdict:

| Response | Meaning |
|---|---|
| `400 {"message":"Invalid signature"}` | **Bound correctly** → NEGATIVE. Record the body verbatim |
| `200` + tx steps | **Unbound** → non-owner signature accepted, value moves to your `recipient` → S3/S4 |

**Do NOT broadcast the resulting transaction.** A `200` with steps is already the proof. Executing it
is theft, and most programs explicitly exclude *"attacks the reporter has already exploited"* — you
would disqualify your own report. Stop at the response code.

## The `recipient` inversion tell

Watch for the case where the **"correct" request fails and the suspicious one succeeds**. Live
example: `POST /app-fees/{wallet}/claim` with `recipient == wallet` returned
`400 "Invalid destination chain and/or recipient"`, while `recipient = <attacker>` returned `200` +
a signing step.

That inversion is a **signal to run the probe**, not proof — in this case the digest still bound the
owner and step 3 returned `400 Invalid signature`. But it is exactly what makes the two-minute probe
worth running, and it is easy to miss because the "correct" request is the one that errors.

## API-key enforcement matrix (run the whole grid, not one variant)

An `openapi.json` with `securitySchemes: {}` and `security: NONE DECLARED` on every route proves
**nothing** — it is the absence of a declaration, not the absence of a control. Test it.

| Probe | Observed (well-built) |
|---|---|
| no key | `401 {"message":"Missing x-api-key header"}` |
| `x-api-key:` (empty) | 401 |
| `x-api-key: ` (space) | 401 |
| `x-api-key: null` / `undefined` / `*` / `[]` | 401 |
| duplicate header (`a` + empty) | 401 |
| case flip (`X-API-KEY`) | 401 |
| `Authorization: Bearer ` | 401 |
| `?x-api-key=` in query | 401 |
| **bogus key** | `401 {"message":"Unauthorized: Check API Key"}` |

Two different messages (`Missing` vs `Unauthorized`) are **not** an oracle — both are 401 and both
fail closed. Do not report a message difference as information disclosure unless a *valid* key is
distinguishable from an invalid one without possessing one.

Also probe common defaults (`test`, `dev`, `localhost`, `admin`, `changeme`, `<product>`, `secret`)
and any second key header the spec mentions (`x-dev-portal-key`). All 401 on a well-built target.

## Order of auth checks vs body validation

An endpoint can answer `400` for a malformed body **before** it evaluates auth. That is not a bypass,
but it does mean *"400 means unauthenticated"* is a wrong inference. Prove auth separately by sending
a **schema-valid** body:

```
POST /wallets/screen/override  {"wallet":"0x…dEaD","action":"allow"}    -> 400 (enum mismatch)
POST /wallets/screen/override  {"wallet":"0x…dEaD","action":"ALLOW"}    -> 401  <- auth, correctly
```
Read the enum out of the OpenAPI schema rather than guessing; `allow` vs `ALLOW` was the whole
difference between "looks unauthenticated" and "is authenticated".

## Quote-endpoint arithmetic (the business-logic half)

A `/quote` with **no API key** and 55 parameters is a fund-loss surface. Probe the fee fields:

| Input | Correct behaviour observed |
|---|---|
| `amount: 0` | reject `"Amount must be greater than 0"` |
| negative `amount` | reject pattern `^[0-9]+$` |
| `amount` above pair max | reject `"exceeds the maximum for this pair"` |
| `appFees[].fee: -500` | reject pattern `^[0-9]*\.?[0-9]+$` |
| `appFees[].fee: 100000` (1000 %) | reject `"output too small to cover fees"` |
| `appFees` × 5 recipients @100 bps | fee = 0.5 on 10 USDC → scales **linearly**, not multiplicatively |
| `subsidizeFees:true, subsidizationBps:10000` | `subsidized: 0.0` — no subsidy without an app context |
| `EXACT_OUTPUT` over available liquidity | reject `"Max amount is $349"` |

Verify the arithmetic instead of eyeballing it: 10 bps on 10 USDC must produce `0.01`, 100 bps must
produce `0.1`. If the numbers track, the fee path is sound and you record a negative.

**Calldata integrity** is the other half — decode the returned `deposit()` / `fill()` calldata and
confirm the amount and destination inside it match what the UI displayed:

```
approve(0x095ea7b3)  spender=0x4cd0…, amount=0x989680 = 10_000_000 = exactly 10 USDC (6dp)  ✓
```
A commitment-hash design (the calldata carries a hash, not the plaintext amount) is fine. A
**mismatch between the displayed amount and the signed amount** is the finding.

## Node RPC namespace probe (same engagement, different surface)

For any chain/RPC host found during recon:

```
POST {"jsonrpc":"2.0","method":"rpc_modules","params":[],"id":1}
```
Then probe `eth_accounts`, `personal_listAccounts`, `admin_nodeInfo`, `admin_peers`,
`admin_datadir`, `debug_setHead`, `debug_traceTransaction`, `miner_start`, `txpool_content`,
`eth_sendTransaction`.

Well-built result: every dangerous method returns `-32601 Method not found`; only read methods
(`eth_chainId`, `web3_clientVersion`, `eth_call`, `eth_getLogs`) answer. **A public RPC that serves
read methods is by design — not a finding.** The finding is `personal_unlockAccount` succeeding plus
`eth_sendTransaction` signing, or `admin_*` / `debug_setHead` succeeding.

## ⛔ Probe hygiene: the token is SINGLE-USE, so mint a fresh one per test

The most expensive false negative in this class. `requestId` / digest is consumed on first submit, so
if you reuse one across a test matrix, **every test after the first returns
`"inexistent or expired"` — which reads exactly like a rejection and proves nothing.**

Measured 2026-10-30 (`relay.link`, app-fees claim): a 10-test matrix reused one `requestId`. Tests
2–10 all came back `inexistent or expired`. Read naively that is "10/10 rejected, secure". It was
actually **1 real result + 9 non-results**. Re-run with a freshly minted digest per test, the same
tests produced genuine distinct verdicts (`Invalid signature`, `Could not process permit`, `500`).

Rule:

```
for each test case:
    POST /<resource>/{owner}/claim   -> capture a NEW requestId
    sign it (or don't, per the test)
    POST /execute/permits            -> this is the ONLY valid submit for that id
```

Also distinguishes "expired" from "rejected": `inexistent or expired` = the id is gone (re-run it),
whereas `Invalid signature` = the server actually evaluated your signature. Only the second is data.

**Corollary — a `500` is not a rejection either.** `signature:""`, `"0x"`, `"abc"`, a 66-byte value
and `r=s=0` all returned HTTP `500` with library-internal text (`signature missing v and
recoveryParam`, `invalid signature string`). That is an uncaught parse path, not an auth decision —
score it as hardening, never as "bound correctly".

## The binding matrix (17 tests, one fresh digest each)

The whole question is **what the digest commits to, and whose key verifies it**. Run all of these;
each is safe with a throwaway key because you never produce a valid owner signature.

| # | Question | Secure answer |
|---|---|---|
| 1 | Non-owner signature accepted? | `400 Invalid signature` |
| 2 | Is `recipient` in the commitment? (3 different recipients, same wallet+amount) | 3 **distinct** requestIds |
| 3 | Is `amount` in the commitment? (`null` / `1000000` / full balance) | 3 distinct requestIds |
| 4 | Single-use? | 2nd submit → `inexistent or expired` |
| 5 | `x-api-key` influence? (none / empty / `test` / 64 zeros) | identical responses |
| 6 | `recipient == wallet` allowed? | rejected (otherwise it is a no-op) |
| 7 | Recipient validation (zero addr, short, UPPER, lower) | malformed rejected; case-insensitive |
| 8 | Amount tampering (`0`,`-1`,`abc`,`1e30`,`0.5`,`" 1"`,`1;DROP`) | regex + min + balance check |
| 9 | Chain/currency confusion (wrong chain, wrong currency, chain 0) | `No balance available` |
| 10 | Signature encoding abuse (v→0/1, v=255, 64-byte trunc, 66-byte pad, r=s=0, high-s, all-ff) | all rejected |
| 11 | requestId oracle? (all-zero, all-ff, random 32-byte) | **uniform** error, no existence leak |
| 12 | Address normalization (checksummed / lower / UPPER in path) | same balance for all forms |
| 13 | Path traversal changes debited wallet? (`{me}%2F..%2F{victim}`) | no substitution |
| 14 | Binds to wallet or to recipient? (sign with recipient key / unrelated key) | both `Invalid signature` |
| 15 | Cross-environment replay (mainnet id → testnet) | `inexistent or expired` |
| 16 | **Traversal splits balance lookup from sig check** | see below |
| 17 | Cross-kind confusion (claim id as `eip3009`/`permit2`/`multicall` and vice versa) | `Could not find permit` — namespaces separated |

### Test 16 — the one that produces the best false positive

`{me}/../{victim}` normalizes to `{victim}`, so the balance endpoint happily returns **the victim's
balance** — alarming, and easy to file as IDOR. But the signature check still runs against the
victim's key, so your throwaway signature is rejected anyway.

**Balance-lookup path and authorization path are usually different code.** Prove both sides or you
will report a traversal that is only a lookup quirk. The finding exists only if you can show the
*debited* wallet and the *verified* signer diverge — and with a traversal you cannot.

### Test 14 is the actual takeover question

If the signature verifies against `recipient`, anyone sets `recipient = self` and self-authorizes.
If it verifies against the fee-owning `wallet`, the endpoint is safe. Relay binds to the wallet:
both a recipient-key and an unrelated-key signature returned `Invalid signature`.

## What survives when the boundary holds

A negative takeover is not zero findings. Three things reliably survive — check the program's
exclusions first, because "DoS with no fund loss" and "issues requiring social engineering" are
commonly out of scope, in which case frame these as **engineering notes, not bounty claims**:

1. **Unhandled 500 on malformed input** (see above). Check whether internals leak (stack,
   `node_modules`, ORM markers) and whether the service degrades under repetition.
2. **No rate limit on unauthenticated state-creating POST.** 30 concurrent claim creations from one
   IP all returned `200` at ~26 req/s with no `429`, minting ephemeral state per call. Report as
   resource-consumption hardening unless you can show fund loss. Verify it does not pollute state
   (`/claims` still `[]` after ~50 creations).
3. **Blind signing.** `sign.message` as a bare 32-byte hash with no EIP-712 `domain`/`types` means the
   wallet renders hex only — the signer cannot see amount, currency, or recipient. Not exploitable
   alone (the commitment is bound server-side), but it is the prerequisite for phishing: attacker
   calls the unauthenticated prepare step with `recipient = attacker`, then asks the victim to sign
   an opaque hex string. Recommend an EIP-712 struct covering amount/currency/recipient/chain.

**Say plainly in the report that you could not take over the fees and are not claiming a bounty.**
A documented negative plus three cheap fixes is a credible submission; a stretched DoS/phishing claim
on an excluded class is not, and it burns your credibility with that team for the next round.

## Honest-close checklist for this class

- Signature binding tested with a **wrong-key** signature and the exact response recorded.
- API-key matrix run in full (≥8 variants), defaults included.
- Auth proven with a schema-valid body, not a 400.
- Quote arithmetic verified numerically, calldata decoded.
- No transaction broadcast; no third-party value moved; test wallet created fresh with zero balance.
- If a request needs a real balance to return `steps`, that is a **blocker to report**, not a reason
  to reach for someone else's funds.
