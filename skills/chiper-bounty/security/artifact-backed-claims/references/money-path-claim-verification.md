# Money-path claim verification — probe recipes that produce a verdict

Use when the target moves value (bridge, solver, DEX, lending, payments, custody) and the
question is *"can I be someone else, or make the system pay me?"* Each recipe below ends in a
**readable verdict** from an HTTP response — no funds need to move.

Companion: the payout-model table in `SKILL.md` decides whether this file is even relevant.

---

## 0. The stop line (read before probing anything)

Fund-loss programs pay for **demonstrating** a path, not for taking funds. Several programs
explicitly exclude *"attacks the reporter has already exploited"* — completing the theft
disqualifies the report even when the bug is real.

1. **Fresh zero-balance wallet**, generated locally (`eth_account.Account.create()`), never funded.
2. **Dead identifiers** for the victim side: `0x…dEaD`, `0x…0001`, `0x1234…5678`,
   `00000000-0000-0000-0000-000000000000`. Never a real user's address or a real order id.
3. **Stop at the verdict, not the execution.** For an off-chain claim/permit flow the server
   either accepts the forged signature (bug proven) or rejects it (secure). Both outcomes are
   readable from the HTTP response. **Do not broadcast the resulting transaction.**
4. If the flow needs a real balance just to reach the signing step, that is a **blocker to
   report**, not a licence to use someone else's funds.
5. Delete throwaway key material after the run.

Near-miss worth recording: on relay.link a `claim` request returned signing steps for a wallet
that happened to hold ~$50 of fees. Continuing would have been theft of a stranger's balance, not
research. The switch to a self-generated empty wallet is what kept the engagement legitimate — and
the probe still produced its verdict.

---

## 1. Map the auth class per route, from the spec, before probing

Pull every spec you can, then classify each route into exactly one bucket:

| Bucket | Meaning | Test |
|---|---|---|
| `KEY-REQ` | spec declares `security` / required header | send without → expect 401 |
| `KEY-OPT` | header declared `required: false` | send without → **if data returns, it is public** |
| `NO-AUTH-DECL` | `securitySchemes: {}` or no `security` key | send without → mostly still 401 |

**`NO-AUTH-DECL` ≠ no auth.** relay.link's `api.relay.link/documentation/json` declared 53 routes
with zero `securitySchemes`; every money-path POST among them returned 401 anyway. The spec is a
documentation artefact, not the policy. **Probe, don't infer.**

Spec locations worth trying, in order:

```
/swagger.json  /swagger/v1/swagger.json  /swagger/doc.json
/openapi.json  /openapi.yaml  /api/openapi.json  /v1/api-docs
/documentation/json   /documentation/yaml        <- Fastify swagger
/api-docs  /swagger-ui.html  /redoc  /docs-json
/graphql  (POST {__schema{queryType{fields{name}}}})
```

Keep the spec on disk — it is the difference between "I guessed endpoints" and "I enumerated the
published contract". A per-route `required: false` on a header is also the cheapest way to find a
**version-downgrade** gap: check whether `/v2` of a route is laxer than `/v3`.

---

## 2. Auth-bypass shapes on the key check itself

Before accepting "401 = secure", try the shapes that break naive header parsers:

```bash
for v in "" " " "null" "undefined" "*" "[]" "0" "true"; do
  curl -s -o /dev/null -w "$v -> %{http_code}\n" -H "x-api-key: $v" "$B/protected"
done
curl -s -o /dev/null -w "dup  -> %{http_code}\n" -H "x-api-key: a" -H "x-api-key: " "$B/protected"
curl -s -o /dev/null -w "case -> %{http_code}\n" -H "X-API-KEY: " "$B/protected"
curl -s -o /dev/null -w "query-> %{http_code}\n" "$B/protected?x-api-key="
curl -s -o /dev/null -w "bear -> %{http_code}\n" -H "Authorization: Bearer " "$B/protected"
```

Then a short default-credential list — **7 strings, one request each, not brute force**:
`test dev localhost admin changeme secret <product-name>`.

**Compare the 401 bodies.** Two different messages (`Missing x-api-key header` vs
`Unauthorized: Check API Key`) is expected and fine — one is a pre-check, the other is validation.
An *oracle* would be a different **status** (403 vs 401) or a different **response time** for a
valid vs invalid key. Message wording alone is not an oracle.

---

## 3. Signature binding — the highest-yield test on any claim/permit endpoint

The question is not whether the endpoint requires a signature. It is **whose signature it accepts**.

```
1. POST /app-fees/{W}/claim  body {chainId, currency, recipient: R}
   -> 200 {steps:[{items:[{data:{sign:{message: M}, post:{endpoint:"/execute/permits"}}}]}]}
2. Sign M with a key that is NOT W's owner (throwaway wallet).
3. POST /execute/permits?signature=<sig>  body {kind:"claim", requestId:M}
4. Verdict:
     "Invalid signature" / 4xx   -> SECURE, binding enforced
     200 + executable steps      -> CRITICAL: signature not bound to the fee owner
```

**Do step 3 once, immediately after step 2.** relay's `requestId` expires fast — a late submit
returns `"Claim request inexistent or expired"`, which is **not** a secure result. Re-run the whole
sequence from step 1.

Variations worth one attempt each, once you hold a valid message:
- change `recipient` between step 1 and step 3 (is recipient inside the signed digest?)
- change `chainId` / `currency`
- reuse wallet A's message against `/app-fees/B/claim`
- replay the same signature twice

Observed on relay.link: claim for `0x…dEaD` returned signing steps with a *different* recipient —
looked critical — then `/execute/permits` returned `400 {"message":"Invalid signature"}`. Server
verifies against the path wallet. **Secure.**

---

## 4. Calldata integrity — does the tx match what the quote promised?

For any endpoint returning a transaction to sign, decode it and compare against the displayed
quote. A mismatch (amount, recipient, destination chain, spender) is the classic bridge/swap S4.

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

Assert by hand:
- the **amount** word equals `details.currencyIn`
- **recipient / destination chain** words match `details.recipient` / `destinationChainId`
- the **spender** in an `approve` (`0x095ea7b3`) is the protocol contract, not an EOA
- no extra word you cannot explain

**Opaque calldata is not automatically suspicious.** relay's `deposit` (`0xe8017952`) carries a
commitment hash by design — amounts are verified on-chain, so an unreadable final word is expected.
Check whether the contract verifies a commitment before calling it a mismatch. In the same quote the
`approve` amount word `0x989680` = 10,000,000 = exactly the 10.00 USDC displayed → consistent.

---

## 5. Business-logic fuzz on the quote endpoint

Quote endpoints are usually unauthenticated (the UI needs them) and take 50+ parameters. One
request per case, compare against a baseline:

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

**Verify the arithmetic rather than reading reject/accept.** appFees `10` bps on 10 USDC must
yield `0.01`; `100` bps must yield `0.10`. If the numbers drift, that is the bug. relay matched
exactly, and every abuse case was rejected by schema pattern or liquidity check.

---

## 6. RPC surface, when the target runs a chain

```bash
for m in rpc_modules eth_accounts personal_listAccounts admin_nodeInfo admin_peers \
         admin_datadir debug_setHead miner_start txpool_content eth_sendTransaction; do
  curl -s -X POST -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$m\",\"params\":[],\"id\":1}" "$RPC"
done
```

`-32601 Method not found` = not exposed (good). Anything returning data or accepting a write is the
finding. **`eth_call` / `eth_getLogs` working is by design** — public RPC, not a bug.

relay.link: `rpc.chain.relay.link` (`sov-evm/0.3.0`) returned `-32601` for every namespace
including `debug_setHead` and `miner_start`. Method whitelist correctly configured.

---

## 7. The coverage line to write

```
Diuji: auth class per route (N routes / M specs) · key-bypass K shapes · default keys J ·
       signature binding (verdict) · calldata integrity (amount/recipient/chain) ·
       quote logic Q abuse cases · RPC R methods · scan: nuclei V templates, control C hits.
BELUM diuji: <each blocker, named>.
```

A money-path audit ending "no finding" is a legitimate result — but only with this line filled in
and every blocker named. Never "target is secure".
