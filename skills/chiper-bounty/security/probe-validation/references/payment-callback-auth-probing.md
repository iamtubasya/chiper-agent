# Payment callback / webhook authentication — probing and falsifying it honestly

Origin: binobi.com engagement, 2026-10-28 (crypto casino, 15 payment providers, NestJS API behind
Cloudflare). Net result: **four callback routes located, zero bypasses**. That outcome is the point of
this file — the class is often well-defended, and the deliverable is a documented, reproducible
negative plus a precise inventory, not a forged finding.

---

## 1. Find the routes before you test them

Wordlists almost never contain payment-callback paths, because the path is the **provider's product
name**, not a dictionary word. Three discovery methods, in the order that worked:

1. **Telemetry oracle** — see
   `security-recon/references/metrics-oracle-route-discovery.md`. The exposed registry named 15
   providers AND exported a per-callback `events_total{outcome=…}` counter, which confirmed
   `POST /moneygrator/callback` in one request each.
2. **Sibling enumeration** — once one provider route is known, loop
   `/{provider}/{callback|callbacks|notify|webhook|deposit|bet|win|rollback|balance}` over the full
   provider list harvested from the registry, the front-end bundle, or a `/payments/rotation`-style
   config endpoint.
3. **Path-shape variants** on each provider prefix: trailing slash, capitalised (`/Moneygrator/`),
   and provider-second (`/payments/<p>/callback`). Case-insensitive routing is common on
   NestJS/Express — it does not change behaviour but your inventory should dedupe case-insensitively.

## 2. Read the auth shape from the error, not from a guess

| Response | Meaning | Next move |
|---|---|---|
| `{"message":"Missing signature header"}` → `{"message":"Invalid signature"}` with any value | header name is literally `signature`; the check is a comparison | brute the value space (§3) |
| `{"message":"Invalid <Provider> authentication"}` uniform for every body/header | proper guard, no oracle | stop probing headers, go to §3 formulas |
| `400 {"message":["field should not be empty", …]}` **before** any auth error | validation runs BEFORE the guard | DTO disclosure finding (§4); handler does work pre-auth |
| `200 {"error_code":"INTERNAL_ERROR","error_description":"Invalid sign"}` | game-aggregator style, always 200 by design | route confirmed; test the `sign` field |
| `410 {"message":"Payment provider is disabled"}` | route exists, provider switched off | record it — a config change re-arms it |
| generic `401 Unauthorized` | e.g. `.../fxmb/deposit` = authenticated deposit-create, not a callback | different class, needs a session |

Finding *which* header is cheap: send the same junk value under ~20 candidate names and watch the
error **change shape**. Only one name moves it.

```python
for h in ["signature","x-signature","sign","x-sign","x-callback-signature","x-api-key",
          "authorization","auth","token","x-token","x-secret","secret","key","checksum",
          "hash","x-hash","x-merchant-key","x-provider-signature"]:
    pass   # "Missing signature header" -> wrong name ; "Invalid signature" -> RIGHT name
```

## 3. The forgery matrix (run it all; report the whole table)

On binobi every one of these was rejected on all four routes. Run them anyway — a table of rejected
forgery attempts is what makes the negative credible, and one hit is Critical.

**Value space** — empty string, single space, `"true"`, `"1"`, `"admin"`; magic-hash family
(`0e0000…`, `00…0`, `A`*64, `a`*64); non-hex (`zzzz-not-hex`), `0x`-prefixed, base64 of the body,
uppercase hex.

**Formulas** — for each of `md5(secret+body)`, `md5(body+secret)`, `sha1(...)`, `sha256(...)`,
`hmac_sha256(secret, body)`, `hmac_md5(secret, body)`; with secrets `"" / "secret" / <provider> /
<brand> / "test" / "key"`:
- over the **raw body string** (byte-exact, including whitespace — capture the exact `postData`)
- over a **canonical sorted-key JSON** form
- over a **query-string** form, and over **timestamp+body** concatenation

**Type juggling / parser abuse** — `sign: []`, `{}`, `0`, `true`, `null`, `["a","b"]`,
`{"toString":"x"}`; `__proto__: {"sign":"x"}`; `constructor:{prototype:{sign:"x"}}`; oversized value
(5,000 chars) to test for truncated comparison.

**Transport abuse** — bodies: empty, `null`, `[]`, `"x"`, `{"sign":"x"}garbage`, invalid UTF-8.
Content types: json, form-urlencoded, text/plain, xml, multipart. Methods: POST only — GET/PUT
returning 404 is method-locked and itself confirms the route.

**Authorisation confusion** — replay your **user JWT** as `Authorization: Bearer *** (guards sometimes
honour the user principal); `X-Forwarded-For: 127.0.0.1`, `X-Real-IP`, `X-Original-URL`,
`X-Rewrite-URL`, `X-User-Role: admin`.

**Replay / settlement logic** — create a **real** deposit invoice on your own account, then hit the
provider's *return* URL (`/redirect/success/<provider>?tr_id=…`) and check whether the balance moves.
It should not: settlement must come from the signed server-to-server callback. On binobi the return URL
only rendered the SPA — balance stayed `null`, deposit stayed `PROCESSING`. That one test converts
"unpaid invoice" into proof that the browser return path cannot self-credit.

## 4. What this class actually produces when the crypto holds

Do not walk away with nothing. Four reportable, non-inflated outcomes were available on binobi:

1. **DTO disclosure before authentication** — `/fxmb/callback` ran the ValidationPipe ahead of the
   guard and returned the full required schema (12 fields, exact enums) to anonymous callers:
   `txid, type(deposit|withdrawal), customer_uid, request_amount, currency, actual_amount,
   status(completed|rejected|expired), method`. Low-Medium.
2. **Authentication oracle** — "Missing signature header" vs "Invalid signature" confirms the header
   name and that the check is a comparison, not a key lookup. Same remediation.
3. **Inconsistent guards across sibling controllers** — the provider that returned one uniform 401 had
   it right; the others leaked. The inconsistency *is* the bug, and it is a credible Low/Medium.
4. **Provider inventory exposure** — a `paymentMethod` / `/payments/rotation` config endpoint (or an
   exposed `/metrics`) enumerates every PSP, sometimes including **QA-labelled channels live in
   production**: `waidrea-qa` produced a real deposit link routed into the production cashier.

Remediation to recommend: run the signature guard as middleware/guard **ahead of** validation, return
one uniform 401/403 for both missing and invalid, and never derive the fee from the request.

## 5. Honesty rules specific to this class

- **Route located ≠ vulnerability.** The counter delta proves a handler exists. Write "route confirmed,
  signature verification held" — never "callback endpoint unauthenticated".
- **A 200 with an error body is not success.** The aggregator route always answers 200; read
  `error_code`, not the status line.
- **Only forge against your own identity.** Use your own `customer_uid`; a forged callback into another
  user's ledger is fund theft, not testing.
- **Stop at the return-URL test.** Do not complete a payment you did not fund; leave the deposit in
  `PROCESSING` and say so.
- **A clean matrix is a deliverable.** Write the table, state the Low/Medium items around it, and note
  explicitly what would have been Critical and did not happen. "Your callback crypto is sound; here are
  the four things around it that are not" protects credibility far better than padding.

## 6. The counter that matters

Watch the **`authenticated`** outcome, not `received`: it only increments on a *successful* auth, so a
single non-zero delta is an authentic bypass.

```python
def try_one(path, body, headers=None):
    before = metric(K_AUTHENTICATED)
    st, b = post(path, body, headers)
    time.sleep(0.35)                       # let the scrape see the increment
    return metric(K_AUTHENTICATED) > before, st, b
```
