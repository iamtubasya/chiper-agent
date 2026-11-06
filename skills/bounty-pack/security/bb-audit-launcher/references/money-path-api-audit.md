# Money-Path API Audit — auth, signature binding, calldata integrity

**Load at:** 0C when the target moves value (bridge, solver, DEX, lending, payments, custody).
Companion to `bounty-program-shape-and-payout-model.md` (read that first — it decides whether
this file is even relevant).

---

## 1. Map auth class per route BEFORE probing

Pull every spec you can find, then classify each route into exactly one bucket:

| Bucket | Meaning | Test |
|---|---|---|
| `KEY-REQ` | spec declares `security` / required header | send without it → expect 401 |
| `KEY-OPT` | header declared `required: false` | send without it → **if data returns, it is public** |
| `NO-AUTH-DECL` | `securitySchemes: {}` or no `security` key | send without it → mostly still 401 (enforcement is in code, not spec) |

**`NO-AUTH-DECL` ≠ no auth.** Relay's `api.relay.link/documentation/json` declared 53 routes with
zero `securitySchemes`; every money-path POST among them returned 401 anyway. The spec is a
documentation artefact, not the policy. Probe, don't infer.

Spec locations worth trying (in order):
```
/swagger.json /swagger/v1/swagger.json /swagger/doc.json
/openapi.json /openapi.yaml /api/openapi.json /v1/api-docs
/documentation/json  /documentation/yaml        <- Fastify swagger
/api-docs /swagger-ui.html /redoc /docs-json
/graphql (POST {__schema{queryType{fields{name}}}})
```

Keep the spec on disk. It is the difference between "I guessed endpoints" and "I enumerated the
published contract".

---

## 2. Auth-bypass sweep on the key check itself

Before accepting "401 = secure", try the shapes that break naive header parsers:

```bash
for v in "" " " "null" "undefined" "*" "[]" "0" "true"; do
  curl -s -o /dev/null -w "$v -> %{http_code}\n" -H "x-api-key: $v" "$B/protected"
done
curl -s -o /dev/null -w "dup -> %{http_code}\n" -H "x-api-key: a" -H "x-api-key: " "$B/protected"
curl -s -o /dev/null -w "case -> %{http_code}\n" -H "X-API-KEY: " "$B/protected"
curl -s -o /dev/null -w "query -> %{http_code}\n" "$B/protected?x-api-key="
curl -s -o /dev/null -w "bearer -> %{http_code}\n" -H "Authorization: Bearer " "$B/protected"
```

Then a short default-credential list (**not** brute force — 7 strings, one request each):
`test dev localhost admin changeme secret <product-name>`.

**Compare the 401 bodies.** Two different messages (`Missing x-api-key header` vs
`Unauthorized: Check API Key`) is fine and expected — the first is a pre-check, the second is
validation. That is not an oracle. An oracle would be a *different status* (403 vs 401) or a
*different response time* for a valid vs invalid key.

---

## 3. Signature-binding probe (off-chain permit / claim flows)

The highest-yield test on any "sign this to claim/move" endpoint. The question is not whether the
endpoint requires a signature — it is **whose signature it accepts**.

```
1. POST /app-fees/{W}/claim  body {chainId, currency, recipient: R}
   -> 200 {steps:[{items:[{data:{sign:{message: M}, post:{endpoint:"/execute/permits"}}}]}]}
2. Sign M with a key that is NOT W's owner (throwaway wallet).
3. POST /execute/permits?signature=<sig>  body {kind:"claim", requestId:M}
4. Verdict:
     "Invalid signature" / 4xx   -> SECURE, binding enforced
     200 + executable steps      -> CRITICAL: signature not bound to the fee owner
```

**Do step 3 once, immediately after step 2.** Relay's requestId expires fast — a late submit
returns `"Claim request inexistent or expired"`, which is *not* a secure result. Re-run the whole
sequence from step 1.

Variations worth one attempt each once you have a valid message:
- change `recipient` between step 1 and step 3 (is recipient inside the signed digest?)
- change `chainId` / `currency`
- reuse a message from wallet A against path `/app-fees/B/claim`
- replay the same signature twice (idempotency)

### The stop line (non-negotiable)

If W holds real balance and the signature is **accepted**, you have proven a fund-loss bug. You
must **not** complete it — several programs exclude *"attacks the reporter already exploited"*, and
taking fees is theft regardless of program rules.

Prove it with accounts you own:
1. `Account.create()` — fresh wallet, never funded, balance zero.
2. Dead identifiers for the victim side: `0x…dEaD`, `0x…0001`, `0x1234…5678`,
   `00000000-0000-0000-0000-000000000000`.
3. If the flow needs a real balance to even reach `steps`, that is a **blocker to report**, not a
   licence to use someone else's funds. Write it in the report's "not tested" section.
4. Never broadcast the resulting transaction. The HTTP verdict is the finding.
5. Delete throwaway key material after the run.

Observed on relay.link: `claim` for wallet `0x…dEaD` (~$50 fee) returned signing steps with a
**different** recipient — looked critical — then `/execute/permits` returned
`400 {"message":"Invalid signature"}`. Server verifies against the path wallet. Secure.

---

## 4. Calldata integrity — does the tx match what the UI promised?

For any endpoint that returns a transaction to sign, decode it and compare against the displayed
quote. A mismatch (different amount, different recipient, different destination chain) is the
classic bridge/swap S4.

```python
import json
d = json.load(open("quote.json"))
for step in d.get("steps", []):
    for item in step.get("items", []):
        tx = item.get("data", {})
        data = tx.get("data", "")
        if not data.startswith("0x"):
            continue
        print(step["id"], "to=", tx.get("to"), "selector=", data[:10])
        body = data[10:]
        for i in range(0, len(body), 64):
            w = body[i:i+64]
            print(f"  [{i//64}] int={int(w,16)} addr=0x{w[24:]}")
```

Then assert, by hand:
- the **amount** word equals the amount shown in `details.currencyIn`
- the **recipient / destination chain** words match `details.recipient` and `destinationChainId`
- the **spender** in an `approve` (`0x095ea7b3`) is the protocol contract, not an EOA
- no extra word appears that you cannot explain

Relay result: `approve` amount word `0x989680` = 10,000,000 = exactly the 10.00 USDC displayed.
The `deposit` (`0xe8017952`) call carries a commitment hash by design — amounts are verified
on-chain, so an opaque final word is expected, not a bug.

**Opaque calldata is not automatically suspicious.** Check whether the contract verifies a
commitment on-chain before calling it a mismatch.

---

## 5. Business-logic fuzz on the quote endpoint

Quote endpoints are usually unauthenticated (they must be, for the UI) and take 50+ parameters.
That is a wide surface. One request per case, compare output vs baseline:

| Case | What it proves if accepted |
|---|---|
| `amount: 0` | division-by-zero / free execution |
| `amount: -1` | signed integer reaching a uint path |
| `amount` = 1e24 | overflow in fee math |
| `slippageTolerance: 0` and `10000` | slippage not enforced → sandwich |
| `appFees[].fee: -500` | negative fee → protocol pays you |
| `appFees[].fee: 100000` (1000%) | fee > notional |
| `appFees` × 5 recipients | fee summation overflow |
| `subsidizeFees:true, subsidizationBps:10000` | protocol pays your fees |
| `EXACT_OUTPUT` above liquidity | input computed wrong |
| `useExternalLiquidity:true` | bypasses internal route/pricing |
| `overridePriceImpact` | caller asserts a false price |

Then **verify the arithmetic** rather than reading the reject/accept: appFees `10` bps on 10 USDC
must yield `0.01`; `100` bps must yield `0.10`. Relay matched exactly. If the numbers drift,
that is the bug.

Relay result: every abuse case was rejected by schema pattern or liquidity check; `subsidizeFees`
returned `subsidized: 0.0` without app context. No logic bug.

---

## 6. Web3 RPC surface (when the target runs a chain)

See `rce-surface-atlas.md` §B1 for the full method matrix. Minimum set:

```bash
for m in rpc_modules eth_accounts personal_listAccounts admin_nodeInfo admin_peers \
         admin_datadir debug_setHead miner_start txpool_content eth_sendTransaction; do
  curl -s -X POST -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$m\",\"params\":[],\"id\":1}" "$RPC"
done
```

`-32601 Method not found` = not exposed (good). Anything that returns data or accepts a write is
the finding. `eth_call` / `eth_getLogs` working is **by design** — public RPC, not a bug.

Relay: `rpc.chain.relay.link` (`sov-evm/0.3.0`, chainId 0x83471) returned `-32601` for every
namespace including `debug_setHead` and `miner_start`. Method whitelist, correctly configured.

---

## Coverage line to write

```
Diuji: auth class per route (N routes / M specs) · key-bypass K shapes · default keys J ·
       signature binding (verdict) · calldata integrity (amount/recipient/chain) ·
       quote logic Q abuse cases · RPC R methods · scan: nuclei V templates, control C hits.
BELUM diuji: <each blocker, named>.
```

A money-path audit that ends "no finding" is a legitimate result — but only with this line filled
in and every blocker named. Never "target is secure".

---

## 5. Withdrawal / fee-claim endpoints: the 17-test binding matrix

Value-moving "get my money out" endpoints (`/claim`, `/withdraw`, `/redeem`, `/settle`) almost
always use a prepare-then-sign flow:

```
POST /app-fees/{wallet}/claim  {chainId, currency, recipient}
  -> 200 {steps:[{items:[{data:{sign:{message:"0x<requestId>"},
                              post:{endpoint:"/execute/permits", body:{kind,requestId}}}}]}]}
POST /execute/permits?signature=<sig>  {kind, requestId}
```

The whole security question is: **what is `requestId` a commitment to, and whose key verifies it?**
Run these 17 tests in order. Each is safe with a throwaway key — you never produce a valid owner
signature, so nothing can move.

| # | Question | How | Secure answer |
|---|---|---|---|
| 1 | Non-owner signature accepted? | sign requestId with throwaway key, submit | `400 Invalid signature` |
| 2 | Is `recipient` in the commitment? | 3 different recipients, same wallet+amount | 3 distinct requestIds |
| 3 | Is `amount` in the commitment? | `null` / `1000000` / `<full balance>` | 3 distinct requestIds |
| 4 | Single-use? | submit same id twice | 2nd → `inexistent or expired` |
| 5 | `x-api-key` influence? | none / empty / `test` / 64 zeros | identical responses |
| 6 | `recipient == wallet` allowed? | set recipient to the fee owner | rejected (else it is a no-op) |
| 7 | Recipient validation | zero addr, short, uppercase, lowercase | malformed rejected, case-insensitive |
| 8 | Amount tampering | `0`, `-1`, `abc`, `1e30`, `0.5`, `" 1"`, `1;DROP` | regex + min + balance check |
| 9 | Chain/currency confusion | wrong chain, wrong currency, chain 0 | `No balance available` / `Failed to get balances` |
| 10 | Signature encoding abuse | v→0/1, v=255, 64-byte trunc, 66-byte pad, r=s=0, high-s, all-ff | all rejected |
| 11 | requestId oracle? | all-zero, all-ff, random 32-byte | uniform error, no existence leak |
| 12 | Address normalization | checksummed / lower / UPPER in path | same balance for all forms |
| 13 | Path traversal changes debited wallet? | `{me}%2F..%2F{victim}`, `/../`, `%20`, `+` | no substitution |
| 14 | Binds to wallet or to recipient? | sign with recipient key; sign with unrelated key | both `Invalid signature` |
| 15 | Cross-environment replay | mainnet id submitted to testnet | `inexistent or expired` |
| 16 | Traversal splits balance lookup from sig check | `{me}/../{victim}` then sign with my key | resolves victim's balance BUT still rejects my signature |
| 17 | Cross-kind confusion | claim id as `eip3009`/`permit2`/`multicall` and vice versa | `Could not find permit` — namespaces separated |

**Test 16 is the one people skip.** A router that normalizes `{me}/../{victim}` to `{victim}` will
happily return the victim's *balance* — which looks alarming — but the signature check still runs
against the victim's key. Balance-lookup path and authorization path are usually different code.
Prove both, or you will report a traversal that is only a lookup quirk.

**Test 14 is the actual takeover question.** If the signature verifies against `recipient`, anyone
can set `recipient = self` and self-authorize. If it verifies against the fee-owning `wallet`, the
endpoint is safe. Relay's binds to the wallet — `Invalid signature` for both a recipient-key and an
unrelated-key signature.

### What is still worth reporting when the boundary holds

A negative takeover does not mean zero findings. Three things reliably survive:

1. **Unhandled 500 on malformed input.** Feed `""`, `0x`, `abc`, 66-byte, `r=s=0`. If you get
   `500` with library-internal text (`signature missing v and recoveryParam`, `invalid signature
   string`) instead of `400`, that is an uncaught parse path. Check whether internals leak (stack,
   `node_modules`, ORM markers) and whether the service degrades under repetition.
2. **Missing rate limit on unauthenticated state-creating GET/POST.** Fire 30 concurrent claim
   creations from one IP. No `429` + ephemeral state per call = resource-consumption surface. Report
   it as hardening, not as DoS-with-impact, unless you can show fund loss.
3. **Blind signing.** If `sign.message` is a bare 32-byte hash with no EIP-712 `domain`/`types`, the
   wallet UI can only render hex — the signer cannot see amount, currency, or recipient. Not
   exploitable alone (the commitment is bound server-side), but it is the prerequisite for a phishing
   flow: attacker calls the unauthenticated prepare step with `recipient = attacker`, then asks the
   victim to sign an opaque hex string. Recommend an EIP-712 struct covering amount/currency/
   recipient/chain.

Check the program's exclusions before writing any of the three up — "DoS with no fund loss" and
"issues requiring social engineering" are commonly excluded, in which case say so in the report and
frame them as engineering notes rather than bounty claims.
