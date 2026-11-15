---
name: hunt-business-logic
description: Hunting skill for business logic vulnerabilities. Built from real engagements — includes the inert-value probe for testing write endpoints safely, cart/quantity/coupon patterns, and Hybris/commercetools specifics.
---

# Business-logic hunting — field-tested notes

## References

- `references/unauthenticated-business-logic-endpoints.md` — AppSumo/promo/redeem endpoint hunting pattern: how to find unauthenticated business-logic endpoints, Rails flash-message enumeration oracle extraction, rate-limit absence testing, and CVSS guidance (Medium 5.3).
- `references/deal-voucher-platform-logic-matrix.md` — daily-deal / voucher / loyalty-stamp / gift-card products (Groupon-shaped). Measured pass/fail matrix for all 5 mandatory probes on a live target, the `items[][unique]` decoy, the payment-method allowlist with its body-length oracle, the `requires_pin` gift-card state machine, and the **multi-stack auth pitfall** (calling the legacy login wipes the modern JWT cookie).
- `references/vpn-service-logic-matrix.md` — consumer VPN billing/entitlement logic: quota bypass, simultaneous-connection limit, server/region access control, token reuse, protocol downgrade, kill-switch/DNS-leak. (2026 checklist; distinct from `enterprise-vpn-attack`.)
- `references/fintech-tax-logic-matrix.md` — fintech/tax SaaS: precision/rounding, currency-race, idempotency-key body-mismatch, KYC-gate bypass, negative balance via race, multi-entity session isolation. (2026 checklist; pairs with `tax-rule-verification`.)

## The inert-value probe (test a WRITE endpoint's auth wall without creating anything)

When a write endpoint (create/issue/generate) validates its arguments BEFORE it checks
authorization — visible from validation errors arriving with no 401/403 — you can still settle
the security question with zero side effects: send arguments that PASS the declared format but
are semantically inert.

Worked example (SAP Commerce / Hybris, target.com.au 2026-09):
  POST /rest/v2/target/vouchers  -> ExtendedVouchersController.createSerialVoucherCodes
  * gating pattern leaked in the error: `code must match ^[A-Z0-9]{3}$`
  * send {"code":"ZZ9","quantity":0}  -> 401 Access is denied   => control holds, nothing created
  * send {"code":"ZZ0"}               -> 400 (only `quantity` missing) => field names confirmed
Quantity 0 makes the "generate N codes" operation a no-op no matter what happens next, so the
test is decisive AND harmless. Do that BEFORE you ever consider sending quantity>=1 against a
live base record — minting real vouchers/gift cards is a business side effect, and a VDP is not
the place to produce one without explicit operator sign-off.

Generalise: for any "create N of X" endpoint, find the parameter that scales the side effect and
set it to zero (quantity, count, iterations, amount). For "apply/consume" endpoints use an
obviously invalid identifier. Only escalate to a real value when the zero/sentinel test shows
the auth wall is missing AND the operator has approved the side effect.

## The read-only QUOTE endpoint is a better oracle than the create endpoint

Before reaching for the inert-value probe on a create/write path, check whether the product
exposes a **price-computation endpoint that returns the figures without committing anything**.
Modern billing stacks split "compute" from "commit": `POST /payments/v5/subscription/check`,
`.../products/check`, `/quote`, `/preview`, `/estimate`, `/calculate`. The compute half is
read-only by design, so you can sweep the entire money surface with zero side effects and no
approval needed.

Measured on Proton (account.proton.me, 2026-10-25, authenticated free account, no card):

```
POST /api/payments/v5/subscription/check
{"Plans":{"mail2022":1},"Currency":"USD","Cycle":12}
-> 200 {"Amount":4788,"AmountDue":4788,"Proration":0,"Credit":0,"Gift":0,"CouponDiscount":0}
```

Swappable axes, each a separate differential: `Plans` quantity, `Cycle` (1/12/24/999/0),
`Currency` (20-code sweep), `Codes`/`CouponCode`, `ProrationMode`, `VatId`, `BillingAddress`.
Safe to run dozens of times — nothing is created, so a mistake costs nothing.

What the sweep bought, in one pass:
- **Validation matrix** — quantity `-1`/`0`/`1000` → `422 Invalid plan selection`; `Cycle` 0/999
  → `422 Invalid input`; bad currency → `422`. Server-side, correct. Record as verified negative.
- **Currency arithmetic** — USD 4788, EUR 4788, CHF 4788, GBP 3828, JPY 5988, KRW 47880,
  BRL 16788, PLN 11988; `Amount == AmountDue` in every one. Zero-decimal currencies (JPY/KRW)
  scale by 100 correctly. Unsupported currencies fail closed (`422`), they do not silently
  default to USD. That is the check that would have exposed a real rounding/unit bug.
- **Coupon stacking** — 1–2 codes → `200` with `CouponDiscount: 0`; 4 codes →
  `422 Invalid coupon selection.`

### The three coupon states — do not confuse them

| response | meaning |
|---|---|
| `200` + `CouponDiscount > 0` | coupon **applied** → now test stacking/reuse/expiry |
| `200` + `CouponDiscount: 0`, `Coupon: null` | coupon **ignored** (wrong plan/product, or client-side only) — NOT a finding |
| `422 Invalid coupon selection` | coupon **rejected** (validation works) |

"200 with zero discount" is the trap: it looks like the code was accepted and a discount is
missing, but the server simply didn't apply it to that plan. Only state 1 is a lead.

### Control-value rule for every money assertion

Before believing a tampered value was accepted, prove an **obviously invalid** value is
rejected by the same code path. If both succeed, your assertion is broken, not the product.
(This session: three different PGP passphrases — including a deliberately wrong string — all
appeared to "work", because the test grepped stdout for an armour header that gpg prints before
it fails. The control exposed the broken method, not three working passphrases. Same failure
shape applies to any "the server accepted my tampered input" claim.)

### When the commit path is gated behind a payment method, stop and say so

`POST /api/payments/v4/subscription {"Plans":{...}}` → `400 No valid payment method available`.
Invoice creation checks for a **stored payment method before it evaluates the price**, so
price/amount tampering is not reachable without a card on file. That is the honest end of the
line: do **not** attach a test/fake card to a live PSP (real money, real fraud controls, and a
program ban is the usual outcome). Write it into the report's not-tested bucket —
"price tampering unreachable: invoice creation requires a stored payment method; no card was
added" — which is a coverage statement, not a negative result, and never claim the flow is safe.

## Wallet-signed write endpoints — the inert target is YOUR OWN keypair

For an API whose write path is gated by a wallet signature (`POST …/add` with
`{data, signature, signer}`) there is no session to steal and no login to bypass, so the inert
probe becomes "sign for an account I just minted". You hold the key, so every check is decidable
in one pass and none of them touches anyone else's record:

1. honest self-signed write → `200`, then read back **under your own signer's namespace** —
   proves the endpoint is live and shows where the record is keyed.
2. same message but a **field edited after signing** → `401 Invalid signature` (server verifies).
3. valid signature with the **`signer` swapped for another pubkey** → `401`. This is the check that
   settles cross-user injection: Ed25519 cannot recover a pubkey from a signature, so the server
   must be verifying against the claimed signer — if instead it stored by a client-supplied owner
   you would have to write into a victim's namespace to learn that.
4. a field the **client** validates only (length ≤ 24, regex) → oversized/HTML value →
   `400 Label cannot exceed 24 characters` = real server-side validation, not just UI.

Two details that decide whether the test even runs: the signed bytes are
`JSON.stringify({fieldA, fieldB})` — **no spaces, no domain, no nonce** — so reproduce them with
`json.dumps(..., separators=(',',':'))`, otherwise you get a `500 Internal server error` that reads
like "the server accepted it". And an unbound message (no domain/purpose/expiry) is a hardening
note about signature reuse or phishing, not an access-control finding.

Finish with the read-back: `GET …?wallet_address=<your signer>` **and** `?<the account you
labelled>`. Only the first returning your value means the store is signer-keyed and there is no
cross-user injection — a negative worth stating because you executed it, not inferred it.

## On-chain counterpart: SIMULATE the transaction, never send it

When the write path is a blockchain instruction, the "prove it without side effects" discipline above has a
native implementation: `simulateTransaction` runs the instruction against current state and rolls everything
back. Use it whenever a hypothesis would otherwise cost a real transfer to confirm. Worked case — DFX
MerkleDistributor claim, 0.xyz audit, 2026-10:

- **Hypothesis:** distributor `startTs→endTs` was a 5-minute span, so every other claimant must be locked out
  by `ClaimExpired` while the site's FAQ says "claim until October 2027".
- **Instead of sending a claim** (real funds, real state change, needs a key I don't hold) I rebuilt the exact
  transaction the client builds and called `simulateTransaction` with
  `{"sigVerify":false,"replaceRecentBlockhash":true,"encoding":"base64"}`.
- **Result:** `Program log: Created new claim with locked 0 and 2985147 unlocked with lockup start:1791822372
  end:1791822672` + `Program … success`. The window is a **lockup/vesting stamp, not a claim gate** —
  hypothesis refuted, zero side effects, and it would have been reported as a critical finding otherwise.

Getting the simulation to run took three fixes, each surfacing as a *different* error worth memorising:
1. `InstructionDidNotDeserialize (102)` → Anchor `Vec<T>` lengths inside instruction data are **u32 LE**, not
   shortvec. Shortvec is only for message-level counts (signatures / account keys / instructions).
2. `AccountNotInitialized (3012)` on account `to` → the client sends `createAssociatedTokenAccountIdempotent`
   **before** the claim; instruction order inside one transaction is part of the contract.
3. A 64-byte zero signature satisfies the wire format when `sigVerify:false`, but the required signer still
   must be *marked* signer in the message header.

**Verification anchor before trusting any account parse:** check a field you already know independently. Here
`MerkleDistributor.mint` had to equal the DFX mint; once it did, the offsets were right and the "5-minute
window" reading was confirmed as a lockup. Without that check an off-by-N offset produces confident nonsense
that looks exactly like a finding.

The same simulation answers the *authorization* half of the question: reading the client's
`keys:[{pubkey, isSigner:true}]` showed the claimant must sign, so the **publicly fetchable Merkle proof is
not a bearer credential** — an unauthenticated `GET /api/proof/{wallet}` leak stays a privacy issue and never
gets mis-filed as "anyone can claim someone else's allocation".

## Cart / quantity patterns actually observed

### Clean-state rule — establish it before you believe ANY cart manipulation

**The single most expensive false positive in this class.** On a Rails/Brightsites-style
store, "add to cart" creates a **NEW line item on every call** (line-item IDs increment:
46599427, 46599428, 46599429…). If your test loop calls `add_item()` before each probe, the
cart ACCUMULATES — and the quantity/total you read back is the sum of your own adds, not
the value you sent.

Measured shape of the trap (Kohl's Insider Shop, 2026-10-29):

```
sent 0.1 -> stored qty 2, total $26
sent 0.5 -> stored qty 3, total $39
sent 0.9 -> stored qty 4, total $52
sent 1.5 -> stored qty 6, total $78     <-- reads as "fractional qty rounded up = BUG"
```

Every value looked accepted because the quantity climbed by exactly 1 per iteration —
that was `add_item()`, not the server. The isolated controlled test refuted all of it:

```
qty=1.5 -> total stays $13.00   (fractional IGNORED)
qty=0.5 -> total stays $13.00   (fractional IGNORED)
qty=3   -> total $39.00         (integer validated correctly)
qty=-1  -> item removed         (no negative total)
```

**The protocol — run every cart probe from a known-clean state:**

```python
def clean_probe(qty):
    clear_cart()                  # set every line_items[<id>][quantity] = 0
    add_one()                     # exactly one line item
    cid, tok, before = read_cart()
    assert before == EXPECTED     # e.g. "$13.00" — DO NOT SKIP THIS
    post_cart(qty)                # the single mutation under test
    return read_cart()            # compare against `before`
```

Three things make it decisive:
1. **Assert the baseline.** If `before` isn't the expected single-item total, the state is
   dirty — fix it, don't interpret the result.
2. **One mutation per clean state.** Never chain probes in one session.
3. **Count line items, not just the quantity.** `len(re.findall(r'cart-item', html))`
   tells you whether an "add" merged or appended.

Also read the **line-item ID from the form**, not a hardcoded one — it changes on every add
(`line_items[46599427][quantity]`), so a stale ID silently no-ops and reads as "ignored".

Corollary for the report: a quantity/price manipulation claim not run from an asserted
clean baseline is **unproven**, and the honest write-up is the negative.

### The email-change → password-reset chain (the ATO that actually paid here)

Pattern confirmed end-to-end on the same target, 3x validated:

1. `POST /account` with `website_user[email]=<attacker address>` → **changed with no
   verification step**, even though the app's own embedded config carries
   `"force_email_verification": true`.
2. `POST /account/password` with the new address → reset link **delivered to the
   unverified address**.
3. Use the reset token → set a new password → login succeeds, the old password dies.

Two things that made it provable rather than theoretical:
- **The config flag is the proof of intent.** Grep the rendered page for the app's own
  settings blob (`force_email_verification`, `use_custom_currency_symbol`, …) — a flag set
  to `true` that the server ignores is a much stronger report than "no verification
  observed".
- **Read the reset mail.** Confirmation that the link went to the *unverified* address
  (not the original one) is what upgrades this from "email changed" to full ATO. Capture
  the token from the mailbox as evidence.

Note the account-edit form still requires `website_user[current_password]` — so the
primitive needs a session first (session theft / XSS / brief physical access), which is
exactly how the report should frame the precondition.

### Before any cart probe: map which auth stack owns the cart

On an estate that has been through a re-platform, the cart may live in the OLD stack while the
account UI lives in the NEW one, with different cookies. Calling the legacy `POST /login/` after a
modern API login **wipes the modern session cookie and does not authenticate the legacy app**, so
every member endpoint then answers "not authorised" and it reads as a missing route. Log in once per
stack, note which cookie you got, and never call the other stack's login afterwards. Full symptom
table (cookie names, the `{"shouldLogin":true}` JSON, and the `429 "Invalid credentials"` rate-limiter
disguise): `references/deal-voucher-platform-logic-matrix.md`.
- Negative and zero quantities: Kmart (commercetools) rejects server-side ("quantity must not be
  less than 1") — correct. target.com.au (Hybris) answers **500** instead, which is sloppy input
  handling but no impact (no stack trace, no state change) → typically INFORMATIVE.
- Silent caps: adding 999 gave a cart of 99, and repeating the add did NOT exceed it → the cap is
  enforced on the cart, not per-request. Always test the *repeat* case before claiming a bypass.
- Client-supplied fields in the add payload (postCode, storeCode) are worth watching for pricing
  or fulfilment-logic deviations — but only report when a price/entitlement actually changes.

## Two front-ends, one cart = inconsistent protection
target.com.au exposes two cart write paths:
  POST /uir-pdp/api/cart/add   — no CSRF token at all (201 from the PDP itself)
  POST /ws-api/v1/target/cart/add — carries `_csrf` in the JSON body
When you see that, test the untokened path with CORS-simple content types (text/plain,
x-www-form-urlencoded) to see whether a cross-site form could drive it (that is the CSRF test
that matters — a JSON content type forces a preflight and is therefore not CSRF-reachable).
Note: an edge rate/reputation rule (Akamai `429 {"cpr_chlge":"true"}`) can start blocking your
POSTs mid-session after a burst; that is environment, not the app — pace yourself, and use the
parameterised content-type trick from `bot-protected-target-testing` when you need back in.

## Mass-assignment probe on add-to-cart (cheap, high-signal)
Send the app's own payload plus every price-shaped field you can think of, then READ THE CART BACK:
    {"productCode":"X","quantity":1,"postCode":2020,"storeCode":"5121",
     "price":1,"basePrice":1,"totalPrice":1,"unitPrice":1,"discount":99,"shippingCost":0,
     "currency":"AUD","discountCode":"FREE100","lineItemPrice":0.01,
     "custom":{"priceOverride":"0.01"}}
On target.com.au this returned 200 and the cart still charged $22.00/unit → pricing is
server-side and extra fields are ignored. Record it as a verified negative; on a less careful
stack the same request would have rewritten the price.

Same trick for fulfilment: the delivery-estimate endpoint took a bogus postcode (0000) without
complaint but the cost stayed flat ($9 HD / $0 CC), while a bogus storeNumber produced a business
error. Conclusion: server-computed, no client leverage — with the hardening note that the
postcode value itself is never validated.

## Registrar / hosting guest carts — the premium-class re-pricing check (and its FP trap)

Domain registrars expose a **guest cart API** before login (do.de measured 2026-10-26:
`/api/shoppingCart/{addItem,addItems,updateItem,update,removeItem,get,addVoucher,setCampaign}`,
CSRF `_token_` + a server-issued ~22-char cart key in a `shoppingcart` cookie). The money test
specific to this vertical is **premium-domain re-pricing**:

1. Add a **standard** domain (e.g. `x.shop`, ~2 EUR) → note the cart total.
2. Tamper `params[domain]` on the existing item via the update endpoint to a **premium** domain
   (find one first via the public domain-check API — free premium names show a `premiumClass`
   object with `priceRuntime` in the hundreds/thousands).
3. **Read the cart TOTAL and the item's CHILDREN — never just the parent item's `price`.**
   The premium surcharge is applied as a separate child line item (`domain premium`,
   ~6 379 EUR on do.de). A correct implementation re-prices on update: parent stays 2.04,
   child appears, total becomes 6 381. Reading only the parent price produces a confident
   FALSE POSITIVE ("price didn't change!") — the exact trap hit live this session before the
   children were inspected.

Also cheap on the same API, all verified negatives on do.de:
- **Cross-cart IDOR:** `removeItem` with YOUR cart key + a FOREIGN item id → `NOT_EXISTS`
  (item↔cart ownership validated). Reading a cart with a known key works **by design** — the
  key IS the bearer token (~130-bit random, no PII in a guest cart) — so that is not a finding.
- **Mass assignment on cart params:** arbitrary `params[...]` keys are stored but pricing is
  recomputed server-side from the catalog; injected `price`/`discount`/`free` keys change nothing.
- **Bulk vs single limits:** single add enforces an item cap (`TOO_MANY_ITEMS`); the bulk
  `addItems` endpoint accepted 30 in one request — check whether the cap is per-request or
  per-cart before calling it a bypass.
- **Voucher/campaign oracles:** invalid codes return a uniform `NOT_EXISTS` (no enumeration
  oracle); campaign values that don't match a known campaign are accepted but silently not
  stored — verify persistence in the cart read-back before testing reflection/XSS.

## Legacy endpoints outlive their front-end — sweep the API host with historical paths

A route whose SPA page now returns "404 / page not found" is **not** gone. Measured on a casino
platform (2026-10-28): `/vault`, `/transfer` and `/bonuses` all served the Next.js 404 page, yet
`POST /exchange` — the API those removed pages used — answered validation errors and was fully
live in production. A dead UI is not a dead endpoint.

Where the paths come from when the current bundle no longer contains them:

```bash
gau --threads 4 target.com api.target.com | sort -u > gau.txt
# parse out paths, strip locale prefixes, de-dupe, then probe against the API host
```

Then **probe the historical paths against the API base, not the web host** — `/exchange` on `www`
is a 404 page, `/exchange` on `api.` is a live handler. Anything answering with a structured
validation error is a shadow endpoint the vendor forgot to retire, and retired features are where
the validation is oldest.

## Enumerate the money DTO by counting validation errors (finds fields the bundle never names)

When an endpoint validates a DTO before doing anything else, an empty body gives you a **count of
missing fields**. Add one candidate at a time: if the count drops, that field is part of the DTO.
Cheaper and more complete than grepping the bundle — which is exactly the situation when the calling
UI has been deleted from the front-end.

```
POST /exchange {}                          -> 1 error   ("Amount must be correct")
POST /exchange {"amount":100000}           -> 1 error   (amount accepted, next field still missing)
POST /exchange {"amount":100000,"fee":0}   -> 0 errors  -> `fee` IS in the DTO
```

On that target ~40 money-shaped candidates (`amountTo`, `amountCrypto`, `amountUsd`, `total`,
`price`, `rate`, `commission`, `receiveAmount`, …) left the count unchanged; **`fee` was the only
one that consumed it**. Sweep the whole vocabulary in one loop and diff the error count — do not stop
at the obvious names.

**Why this matters:** an optional money field is the least-validated field in the system (same
lesson as the `tips` booking CVE above). `fee`, `serviceFee`, `margin`, `surcharge`, `tip`,
`donation`, `shipping` are all "feature" names for a number that moves money.

### What the error text tells you before you touch a balance

The constraint the server enforces is free reconnaissance about its arithmetic. Observed:

| request | response | reading |
|---|---|---|
| `amount:100000, fee:-99999` | `not_enough_balance` | passed validation → server computes `amount + fee` |
| `amount:100000, fee:-100000` | `invalid_amount` | the only guard is `amount + fee > 0` |
| `amount:-1` | `invalid_amount` | the amount itself is sign-checked |
| `fee:1000000000` | `not_enough_balance` | **no upper bound on the fee** |

A server that arithmetic-checks `amount + fee` and then stops at a balance test is a *lead*, not a
finding: you have proven the fee is client-controlled, not that a negative fee mints value.

### Proof bar — a client-controlled fee is UNPROVEN without a funded balance

Name this honestly or the report dies in triage. The credit side is only observable with money in
the account, so:

- With a zero balance **every** leg terminates at `not_enough_balance` and the credit formula is
  unobservable. That is **not** a finding yet — it is a held lead.
- Do **not** ship it in the same batch as proven findings. A body headed "9 findings" that contains
  one the author themself calls unproven invites the triager to discount the whole set.
- State the exact gate and the exact unlock: *"impact unproven: account balance is zero; one minimum
  deposit (≈ USD 1.10) on my own account would settle whether a negative fee mints value."* Then let
  the operator decide — never deposit on your own initiative.
- The zero-cost alternative close: ask the vendor to confirm the fee comes from the rate table
  rather than the request. `fee` being in the DTO at all is a legitimate hardening finding.

## The read-back is what makes it evidence
Never report a business-logic bug from a status code. After each tampering step, re-read the
authoritative state (cart JSON, order total, entitlement list) and diff it. "200 + unchanged
price" is a control working; "200 + changed price" is the finding; "500 + unchanged state" is
informative-only and belongs in a hardening note, not a report.

## Idempotency / replay checks on a write API (the test has two halves)

When the docs say writes are idempotent on your own reference key, prove BOTH:
1. **same key + same payload** → deduplicated, no duplicate row created;
2. **same key + DIFFERENT payload** → also deduplicated, and the ORIGINAL value is kept (no overwrite).
Half 2 is the one people skip, and it is where a silent overwrite hides. Re-read the resource after
each call and diff the stored value, not the status code.

## Body-shape trap: "Required" for fields you DID send

If a write endpoint returns per-field errors (`0.date: Required`, `0.type: Required`, `0.amountPence:
Required`) for fields that ARE in your body, the **envelope is wrong, not the fields**. Many APIs take
a BARE JSON ARRAY (`[{...},{...}]`), not a wrapper object (`{"transactions":[...]}`) — and the validator
reports "missing" because it iterates the wrong level. Read the error's array index (`0.x`) as the tell,
and re-send as a bare array before you start doubting your field names. Same class: an `?mutation=1` op
that answers **415 on POST** but **400 on GET** is a GET-with-query-vars endpoint, not a POST one — the
415 is the edge rejecting the method/body, and the 400 is the app parsing you.

## The prior pass's leftover data is a confound, not baseline

On a re-audit, the account often still carries the LAST pass's scenario rows (identifiable by names like
"R4 audit test …"). Any control that is evaluated on an AGGREGATE (a running total, a shared allowance,
a bucket) is then contaminated: the rule may be evaluated against the old data and never exercise the
case you are testing. Note the existing rows first, and if the aggregate hides the case, temporarily
clear the other rows, run the isolated leg, then restore them exactly and re-read the aggregate to
confirm you are back to the starting figures.

## The automated/pipeline pass is NOT a business-logic check

The audit pipeline's 0C biz-logic phase fires a fixed vector set and reports something like
`business-logic: 15/15 vectors, 56 probes, 0 interesting`. Treating that as "business logic covered"
invites the direct question — *"sudah kamu cek dr sisi business logic nya?"* — and the honest answer
on that occasion was no, not by hand. That question is the operator running the check the agent
should have run.

The automated pass fires payloads at endpoints; a real pass asks *"what is this product supposed to
DO, and can I make it do something else?"* — limits, caps, idempotency, eligibility, ordering,
quotas, state transitions, cross-entity rules — with the product's own copy/claims as the oracle.
Run it as its own step. And report negatives as results: "the write validates its argument (400 on a
non-existent id), rejects duplicates (idempotent), and is session-scoped (no write-IDOR)" is a
deliverable, not an absence — that verdict only exists because you replayed the mutation and read the
state back.

## Edge throttling is part of the methodology
After a few dozen POSTs the same request that returned 200 starts returning the edge challenge.
Plan bursts, leave the "must be tested" cases for a fresh session, and record which tests were
abandoned for that reason instead of quietly reporting them as negative.

sources: hackerone_public, github
report_count: 25
---

## Crown Jewel Targets

Business logic vulnerabilities pay highest in platforms where financial transactions, identity verification, and access controls intersect with real-world consequences. The richest targets are:

- **E-commerce & payment platforms** (Valve/Steam, Shopify) — payment flow manipulation, free goods, price tampering
- **Marketplace & gig economy apps** (Airbnb, Uber) — identity/verification bypass enabling fraud or unsafe interactions
- **SaaS with tiered access** (Mozilla Monitor) — bypassing verification to unlock monitoring features without entitlement
- **High-traffic consumer apps** (Snapchat, Yelp) — rate-limit bypass enabling spam, enumeration, or abuse at scale

Asset types that pay: checkout flows, subscription endpoints, callback/verification systems, webhook handlers, employee/internal portals exposed to the internet, and any endpoint that trusts client-supplied data to make authorization decisions.

---

## Attack Surface Signals

**URL patterns to watch:**
- `/checkout`, `/order`, `/subscribe`, `/payment`, `/verify`, `/confirm`, `/callback`
- `/internal`, `/employee`, `/summit`, `/staff`, `/admin` — internal pages accidentally public
- `/api/v*/payment`, `/api/v*/notify`, `/webhook` — payment provider callbacks
- Endpoints accepting `X-Forwarded-For`, `X-Real-IP`, `CF-Connecting-IP` headers

**Response/header signals:**
- `Set-Cookie` with unvalidated session state tied to cart or order data
- Payment provider names in responses: `Smart2Pay`, `Stripe`, `PayPal`, `Braintree`
- Redirect chains through third-party payment pages (in-flight data opportunity)
- `200 OK` on subscription/verification endpoints with no CAPTCHA or token

**JS patterns:**
- Hardcoded internal URLs in frontend bundles (`/employee/`, `/staff/`, `/internal/`)
- Client-side price calculation before server submission
- Verification logic that only checks on the frontend (`if (verified) { ... }`)
- `fetch('/api/subscribe', { method: 'POST', body: ... })` with no anti-CSRF token or rate-limit token

**Tech stack signals:**
- Shopify storefronts with draft/unpublished channel pages
- Apps using IP-based rate limiting without session/account binding
- Payment webhooks with no HMAC signature validation
- SMS/phone callback flows that don't verify ownership before enabling features

---

## Step-by-Step Hunting Methodology

1. **Map all authentication boundaries.** Spider the target. Identify pages/endpoints that serve authenticated content (employee portals, premium features, order pages) and test each unauthenticated. Look for internal pages indexed in JS bundles or linked from robots.txt/sitemap.xml.

2. **Identify every verification flow.** Enumerate: email verification, phone/SMS verification, payment verification, CAPTCHA, age gates. For each, test: what happens if you skip the verification step entirely? What happens if you replay a valid token on a different account?

3. **Test rate-limiting controls on every form.** For every POST endpoint (subscribe, login, OTP, search), send 50+ rapid requests. Vary: remove cookies, rotate `X-Forwarded-For` / `X-Real-IP` headers, change `User-Agent`. Check if the server uses IP from headers rather than connection IP.

4. **Intercept and tamper with payment flows.** Use Burp Suite to intercept every request between your browser, the application, and the payment provider. Identify where price, currency, order ID, or status fields are set. Attempt to modify amounts to $0.01 or currency to a low-value currency. Look for POST-back/webhook endpoints that accept payment confirmation — test if they validate HMAC/signature.

5. **Test phone/callback number verification.** Whenever a platform accepts a callback number, test: can you set it to a number you don't own? Does the platform call/text that number and grant trust based solely on submission? Try setting it to a victim's number.

6. **Check for unprotected employee/internal surfaces.** Search Shodan, GitHub, JS bundles, and Wayback Machine for internal subdomain/path references. Test access without authentication. Check if these surfaces allow order placement, data access, or privilege escalation.

7. **Validate business impact.** For each finding, determine: does this result in financial loss, unauthorized access, or data exposure? Document the end-to-end chain.

---

## Payload & Detection Patterns

**Rate limit bypass via header rotation:**
```bash
# Rotate X-Forwarded-For to bypass IP rate limiting
for i in $(seq 1 100); do
  curl -s -X POST https://target.com/api/subscribe \
    -H "X-Forwarded-For: 10.0.0.$i" \
    -H "X-Real-IP: 10.0.0.$i" \
    -H "Content-Type: application/json" \
    -d '{"email":"victim+'"$i"'@example.com"}' \
    -o /dev/null -w "%{http_code}\n"
done
```

**Payment tampering — modify in-flight price:**
```http
POST /payment/initiate HTTP/1.1
Host: target.com

amount=0.01&currency=USD&order_id=12345&product_id=99
```
```bash
# Look for unvalidated webhook endpoints
curl -X POST https://target.com/payment/callback \
  -H "Content-Type: application/json" \
  -d '{"status":"success","amount":"0.01","order_id":"12345","transaction_id":"fake-txn"}'
```

**Unauthenticated internal page discovery:**
```bash
# Check robots.txt and sitemap for internal paths
curl -s https://target.com/robots.txt | grep -iE "(disallow|allow)" 
curl -s https://target.com/sitemap.xml | grep -iE "(employee|internal|staff|summit|admin)"

# Grep JS bundles for internal paths
curl -s https://target.com/assets/app.js | grep -oE '"/[a-zA-Z0-9/_-]{3,50}"' | sort -u
```

**Email verification bypass:**
```bash
# Skip the verification step: hit the post-verification API endpoint directly
# with an unverified session. If it succeeds, the gate is UI-only.
curl -s -X POST https://monitor.target.com/api/monitoring/enable \
  -H "Cookie: session=<your_unverified_session>" \
  -H "Content-Type: application/json" \
  -d '{"email":"victim@example.com"}'

# Replay verification token on different account
curl -X POST https://target.com/verify \
  -d 'token=VALID_TOKEN_FROM_ACCOUNT_A&email=account_b@example.com'
```

**Grep patterns for client-side logic issues:**
```bash
# Find price calculations in JS
grep -iE "(price|amount|total|cost)\s*[=*+]" app.js

# Find internal URLs in JS bundles
grep -oE '"/(employee|internal|staff|admin|summit)[^"]*"' *.js

# Find unvalidated IP header usage in server code
grep -iE "x-forwarded-for|x-real-ip|cf-connecting-ip" src/ -r
```

---

## Common Root Causes

1. **Server trusts client-supplied data for financial decisions.** Developers offload price calculation to the frontend or pass amount fields through forms/URLs without re-validating on the server against a canonical source (the product database).

2. **Verification is enforced only in the UI, not the API.** Frontend hides features behind a verification gate, but the backend API endpoints are fully functional without a verified status — any authenticated request succeeds.

3. **IP-based rate limiting reads from spoofable headers.** Developers implement rate limits using `request.headers['X-Forwarded-For']` instead of the actual connection IP, allowing trivial bypass by header manipulation.

4. **Payment webhooks lack signature validation.** Developers implement "success" webhooks without verifying the HMAC signature provided by the payment provider, allowing anyone to POST a fake success notification.

5. **Internal/employee pages aren't access-controlled.** Internal tools are deployed to production domains without authentication middleware, either because developers assume obscurity (unlisted URL) or forgot to apply auth to a new route.

6. **Phone/callback verification is advisory, not enforced.** Systems accept a phone number and grant trust to whoever submitted it, without confirming the submitter owns or controls that number.

7. **Draft/channel-specific storefronts inherit full order functionality.** Platforms like Shopify allow creating storefronts for specific channels (employee events) that are unlisted but still fully functional for order placement if the URL is known.

---

## Bypass Techniques

| Defense | Bypass |
|---|---|
| IP-based rate limiting | Rotate `X-Forwarded-For`, `X-Real-IP`, `True-Client-IP`, `CF-Connecting-IP` headers per request |
| CAPTCHA on subscription forms | Use header-based bypass first; if CAPTCHA is only on the web form, call the underlying API endpoint directly |
| Email verification gate | Access the post-verification API endpoint directly; replay valid tokens; check if `verified=true` is a client-set cookie/param |
| Payment amount server validation | Modify currency to a lower-value currency; test with $0.00 or negative amounts; manipulate order IDs to reference different products |
| Webhook HMAC validation | Test with no/empty signature header (is validation enforced at all — a modified payload only "passes" if it isn't); replay an UNMODIFIED captured webhook to test missing idempotency/anti-replay |
| Auth on internal pages | Try unauthenticated; try with a low-privilege account; try path traversal variants (`/employee/../employee/`) |
| Phone verification (OTP sent) | Submit someone else's number without OTP validation; check if the system grants trust on submission vs. OTP confirmation |

---

## Off-chain entitlement / claim-proof endpoints (DeFi, airdrops, incident recovery)

When a product pays out from an **off-chain-computed** allocation — Merkle tree, points DB, loss
snapshot after an exploit — the client only ever needs `amount + proof`, so it asks for them over
plain HTTP. That read endpoint is where this class lives. Check it in this order:

1. **Does it answer for a wallet that is not yours?** `GET /api/proof/<arbitrary-wallet>` returning
   `{"amount":"2985147","proof":[…18 nodes]}` unauthenticated is the candidate. The `404
   {"error":"not_found"}` for a wallet outside the tree is the **control** that proves the endpoint is
   really querying the allocation set rather than stubbing — without the negative you cannot tell
   enumeration from echo.
2. **Membership oracle.** `200` vs `404` / `"no DFX entitlement in this snapshot"` lets an attacker
   test whether an arbitrary wallet was affected by a publicised incident. Reportable on its own
   when the amounts are not.
3. **Amplifier: read `access-control-allow-origin` on that response.** `*` means any web page can
   pull a victim's entitlement **from the victim's own browser** with zero server infrastructure;
   no `ACAO` header means the same URL is only reachable server-side. Identical body, one tier apart
   in severity, decided by that one header.

Then the gate that decides the whole class — **who can act on the proof?** Read the claim
instruction's account metas in the client bundle before choosing words:

- `{pubkey: claimant, isSigner: true}` + destination derived from the claimant's own key ⇒ the proof
  is **not** a bearer credential; the report is confidentiality/Low, never theft. Also verify the
  client-only gate against the chain: a hard-coded `earlyClaimants` Set or a `startTs`/`endTs` window
  enforced only in JS must be checked against the program (`onchain-finding-verification` §1e —
  read-only `simulateTransaction`, never a live send). In the worked case the 5-minute window turned
  out to be a *vesting lockup*, and the simulation refuted a "138k users locked out" story before it
  was written.
- claimant **not** a signer ⇒ stop, prove it with that simulation first; do not report theft from a
  source reading.

**Triage rule for the data itself.** Anything recomputable from public chain state (positions,
health, TVL, bad debt) is **abuse/cost**, not confidentiality — the reportable part is the
*delivery*: e.g. an unauthenticated `Content-Length: 82255403` aggregate (87,774 accounts) served
with `ACAO: *` and no observed rate limit despite the spec documenting an "anonymous rate limit".
Numbers that exist nowhere else off-chain (points, adjustments, a pre-claim loss snapshot) are real
confidentiality — Low unless they unlock an account-level action. Always say which of the two you
are reporting; conflating them is how a privacy note gets bounced as "that data is on-chain anyway".

---

## Gate 0 Validation

Before writing any report, answer all three:

1. **What can the attacker DO right now?**
   Be specific: "An unauthenticated user can place an order for physical goods at $0 cost" or "An attacker can bypass email verification and monitor any email address without owning it" or "An attacker can send unlimited subscription emails to any address." Vague impact = reject.

2. **What does the victim LOSE?**
   Identify a concrete, attributable loss: financial loss (free goods, fraudulent payments), privacy loss (phone number spoofed, unauthorized monitoring), service abuse (spam campaigns via rate-limit bypass), or security degradation (unverified identity trusted for sensitive actions). If the loss is purely theoretical, re-evaluate severity.

3. **Can it be reproduced in 10 minutes from scratch?**
   Create a fresh account (or use no account). Follow your documented steps. Achieve the impact. If you can't reliably reproduce it end-to-end in under 10 minutes with the steps you've written, your methodology is incomplete — refine before submitting.

---

## Real Impact Examples

**Scenario 1 — Free Physical Goods via Exposed Internal Storefront (Shopify-style)**
An employee summit page was deployed to a public Shopify storefront as a private channel for distributing free books to staff. The URL was discoverable via JS bundle analysis or link sharing. An anonymous user who navigated to the URL could browse and complete a checkout with no authentication required, receiving physical merchandise shipped at the company's expense. Impact: direct financial loss per order, potential for bulk ordering if not caught quickly.

**Scenario 2 — Payment Manipulation via In-Flight Tampering (Valve/Steam-style)**
A payment flow passed order amount and currency through client-controlled parameters before redirecting to a third-party payment provider (Smart2Pay). By intercepting the redirect with Burp Suite and modifying the amount field, an attacker could complete a real payment for $0.01 while the application's webhook — lacking HMAC validation — accepted the provider's confirmation and credited the full item/service to the account. Impact: critical financial loss; attacker receives full value goods/services for near-zero cost, infinitely repeatable.

**Scenario 3 — Email Verification Bypass for Unauthorized Monitoring (Mozilla-style)**
A breach-monitoring service required email verification before enabling monitoring alerts for an address. The verification check was enforced in the UI flow but the underlying API accepted monitoring setup requests for any address using a valid session — skipping the verification step entirely. An attacker could set up monitoring for email addresses they don't own, receiving breach notification data (potentially including credential exposure status) for victim accounts. Impact: privacy violation; attacker gains intelligence on whether a target's email was in a breach without the target's knowledge or consent.

---

## Disclosed Report Citations (Backfill +5 — 2016-2023)

The following real, verified bug-bounty / coordinated-disclosure cases extend this skill. All five share a measurable financial-impact angle (actual $ loss demonstrated or quantifiable platform-wide exposure).

8. **Stripe — Fee discount race redemption** ([H1 #1849626](https://hackerone.com/reports/1849626))
    - Subclass: coupon/discount race-multi-redemption + financial primitive
    - Payload: Stripe Support applied a one-time $20,000 fee-credit. Researcher captured the "accept-discount" POST and replayed it 30× in parallel via Burp Turbo Intruder, each acceptance crediting the account anew
    - Root cause: idempotency missing on discount-acceptance endpoint; no unique constraint on (account_id, discount_id)
    - Year: 2023 — **$5,000**, $600,000 of fee-free transactions accrued before fix (~$18,000 real Stripe loss at 3% take rate)

9. **Reverb.com — Gift-card race multi-redemption** ([H1 #759247](https://hackerone.com/reports/759247))
    - Subclass: gift-card / store-credit race-redemption
    - Payload: single valid gift card, parallel-POST to `/redeem` from 10 sockets via Turbo Intruder. Balance credits N× the face value
    - Root cause: no row-level lock on gift_card table; balance debit and credit live in separate transactions
    - Year: 2019 — **$1,500**

10. **Upserve / OLO — Negative-quantity price manipulation** ([H1 #364843](https://hackerone.com/reports/364843))
    - Subclass: negative-quantity-in-cart price tampering
    - Payload: `POST /api/order {"items":[{"id":1,"qty":1,"price":50},{"id":2,"qty":-3,"price":50}]}` — order total computes to `-$100`, floors to ~$0 at payment capture, food still fulfills
    - Root cause: server multiplies `qty * price` with no `qty >= 1` guard
    - Year: 2018 — textbook citation for the subclass (acknowledged-only program)

11. **Krisp — Pay-less-per-seat via PUT tampering** ([H1 #1446090](https://hackerone.com/reports/1446090))
    - Subclass: price-per-unit mass-assignment / quantity-discount manipulation
    - Payload: `PUT /v2/seats` body includes a server-trusted `price` field. Set `price=1` instead of $60. Subscription updates, billing engine charges $1/seat for 100 seats
    - Root cause: server reads price from request body instead of looking it up by plan_id; classic mass-assignment
    - Year: 2021 — Stripe-billed SaaS pricing exposure

12. **Stripe — Pay using archived price via mid-flow swap** ([H1 #1328278](https://hackerone.com/reports/1328278))
    - Subclass: cart-state TOCTOU / cancel-then-deliver (price-version race at checkout)
    - Payload: merchant archives an old price (e.g., $5 instead of new $50). Buyer starts checkout via the new payment-link, then mid-flow swaps `price_id` back to the archived one. Stripe charges $5; subscription provisions at the new tier
    - Root cause: payment-link validates "is active", price object validates "exists" — but the join "price.active AND price ∈ link.allowed_prices" is missing
    - Year: 2021 — Stripe Medium (per-subscription recurring loss)

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Price/amount tamper: ubah `price`, `amount`, `total` di body & bandingkan server recompute | Invariant finansial paling sering bocor |
| 2 | Kuantitas negatif / nol / float: `-1`, `0.0000001`, `1e10` | Overflow & sign error |
| 3 | Coupon/voucher stacking: pakai 2x, pakai setelah refund, pakai lintas akun | Race & reuse pada diskon |
| 4 | Lewati langkah workflow: langsung POST ke step akhir (checkout/success) | State machine jarang divalidasi di server |
| 5 | Currency/rounding: kirim amount yang dibulatkan beda di client vs server | Selisih pembulatan = financial impact |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** langkahi aturan bisnis

**Teknik pengembangan:** race pada voucher/kuota; manipulasi harga/refund; entitlement bypass

**Eskalasi ke:** `hunt-race-condition` · `hunt-ato`

**Depth target:** L2 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **`hunt-race-condition`** — Every uniqueness/quota check in a logic flow is a race candidate. Chain primitive: Business logic (coupon/credit/promotion) + race condition → coupon redeemed N times in a single TCP packet via Turbo Intruder.
- **`hunt-idor`** — Logic flows that trust a client-supplied identifier (order_id, tenant_id, beneficiary_id) overlap directly with IDOR. Chain primitive: business-logic step-skip + IDOR on beneficiary_id → transfer funds from victim account.
- **`hunt-api-misconfig`** — Step-skip and verification-bypass often live next to mass-assignment fields. Chain primitive: business-logic email-verify skip + API mass assignment (`verified:true, role:admin`) → ATO without email control.
- **`hunt-ato`** — Logic bugs in password reset, email change, and recovery flows are core ATO paths. Chain primitive: business logic (email change accepts without re-auth) + `hunt-ato` Path 2 → silent victim email swap → password reset to attacker mailbox.
- **`security-arsenal`** — Load the Business-Logic Probe Checklist (negative quantity, decimal overflow, currency swap, step-skip via direct URL nav, state-machine reverse) and the Always-Rejected list to avoid filing self-inflicted bugs.
- **`triage-validation`** — Apply the 7-Question Gate (especially Q4 "Is this exploitable by an outside attacker without unrealistic preconditions?"): logic bugs need a concrete dollar/PII/state impact, not just "the flow looks weird".

---

## 2026 writeup sweep (PortSwigger + Bugcrowd, dork pass 2026-10-18)

- **Excessive trust in client-side validation** (PortSwigger *Logic flaws → Examples*) — the
  core business-logic mistake. It is especially dangerous because it leads to the further
  assumption that client-side validation prevents malicious input; an attacker simply
  tampers with the data after the browser sends it but before the server processes it.
  Accepting data at face value without integrity checks and server-side validation lets an
  attacker do all kinds of damage.
- **Unhandled edge cases** — the application may accept arbitrary values of a data type, but
  the *logic* decides whether that value makes sense. If there is no explicit logic for a
  given case, the result is unexpected and potentially exploitable behaviour. Test the values
  the developer never considered: zero, negative, max-int, and "the type allows it but the
  business does not".
- **Quantity/price tampering** — when ordering products users specify a quantity, and that
  value flows straight into pricing. The canonical first probe on any commerce target.
- **Race window definition** (Bugcrowd *Racing Against Time*) — the critical period during
  which a system is vulnerable to unintended behaviour, caused by the unpredictable order in
  which threads access shared resources. You do not pick the locks; you exploit the gap
  between *resource exposed* and *resource protected*.
- **One-time-resource races** (PortSwigger) — e.g. a promotional code: the app checks you
  have not already used it, then applies it. Two concurrent requests both pass the check.
  This is the pattern to look for on any single-use coupon, voucher, invite or credit.

---

## Reference — PayloadsAllTheThings (extracted 2026-10-17)

`security/bug-bounty/references/pat-techniques/business-logic.md` (6.2KB, 96 lines) —
PAT section: negative/zero/overflow quantity, price & currency tamper, coupon &
referral stacking, step-skip via direct URL, workflow reversal. Raw-payload shelf
behind this skill's techniques.
Cadangan versi komunitas: `references/cbh-hunt-skills/hunt-business-logic.md` (17.4KB).

## 2026 sweep (dork pass 2026-10-26 — CVE terverifikasi dari WPScan/Patchstack/NVD)

- **CVE-2026-78137 — StoreGrowth Smart Sales Booster (WooCommerce) < 2.1.2: unauth arbitrary price manipulation via BOGO add-to-cart.** Dua aksi `admin-ajax.php` tak terautentikasi (`update_offer_product`, `offer_product_add_to_cart`) menerima harga dari browser (`data[offer_product_cost]`, `data[bogo_price]`) tanpa validasi, dan harga itu terbawa sampai ke total checkout. CVSS 7.5, CWE-862.
  Lesson: cari **field harga yang namanya terdengar seperti parameter fitur** (`*_cost`, `*_price`, `bogo_price`) — developer menamainya sesuai fitur, bukan sesuai fakta bahwa itu harga.
- **CVE-2026-79630 — WPFunnels < 3.13.0: unauth price manipulation via order-bump product-ID substitution.** Diskon 90% dikonfigurasi untuk produk murah; penyerang mengirim `product=<ID_MAHAL>` dengan `key=<index_bump_murah>`. Order jadi memuat produk 2000.00 dengan harga 200.00. CWE-639, CVSS 5.3.
  Lesson: **cek ID produk pada baris order, bukan nama yang ditampilkan** — nama yang tampil adalah yang dikonfigurasi di bump, sehingga pembaca yang mencocokkan berdasarkan nama akan mengira substitusi gagal. Ini juga jebakan verifikasi: selalu bandingkan `product_id`, bukan label.
- **CVE-2026-8738 — PublicCMS 5.202506.d: business-logic flaw in the Trade Payment Flow.** Eksploitasi remote pada alur pembayaran (CWE-840).
  Lesson: alur pembayaran multi-langkah (buat order → pilih metode → konfirmasi → callback) punya state machine; uji setiap transisi, terutama yang mundur dan yang dilewati.
- **CVE-2026-2519 — Bookly (WordPress): auth bypass + pricing manipulation via the `tips` parameter.** Parameter tip tidak divalidasi terhadap server-side booking price.
  Lesson: field uang **opsional** (tip, donasi, biaya layanan, ongkir) paling jarang divalidasi — uji itu lebih dulu sebelum field `price` utama.
- **CVE-2026-49110 — Upsell Order Bump Offer for WooCommerce <= 3.1.4: unauthenticated broken authentication pada aksi order bump.** CVSS 7.5 `AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N` — integritas tinggi tanpa kerahasiaan, bentuk klasik bug harga (tidak ada yang bocor, tapi total bisa diubah).
  Lesson: vector `C:N/I:H` adalah **sidik jari bug business-logic finansial**; kalau kamu melihat pola itu di advisori, yang bocor adalah uang, bukan data.

**Pola gabungan (2026):** ketiga CVE WooCommerce berbagi satu akar — **nilai uang datang dari request pada aksi yang mengaku sebagai fitur pemasaran** (BOGO, order bump, upsell). Saat merecon plugin/endpoint commerce, grep nama aksi yang mengandung `offer`, `bump`, `upsell`, `bogo`, `discount`, `promo` lalu periksa apakah ada field harga di body-nya.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Fast path skip state update; workflow step skip; negative/zero bypass; TOCTOU pada transisi state (double-spend, double-claim, coupon reuse); quote endpoint sebagai oracle yang aman untuk di-sweep. Kalibrasi: limit field yang sama sekali tidak divalidasi = per-user allocation input (by-design), BUKAN quota bypass — real bypass menunjukkan server BERUSAHA enforce dan gagal.
