---
name: financial-logic-verification
description: "Verify a money-handling product's computed figures against the authoritative domain rules (tax, fees, interest, entitlements) using its own itemised output as the oracle."
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [tax, business-logic, arithmetic, compliance, fintech, hmrc, verification, bug-bounty]
---

# Financial / Tax Logic Verification

Use when the target computes money: tax software, payroll, billing and invoice engines, fee
and interest calculators, payout/settlement logic, entitlement maths. The question is not
"can I break the endpoint" but **"is the number it shows correct, and what does being wrong
cost the user"**. This is a product-correctness class, not a security class — and it is where
tax and fintech engagements actually produce value once the injection/IDOR surface is clean.

This operator asks for it explicitly and repeatedly on financial SaaS: *"review kepatuhan
aturan pajak … diverifikasi ke sumber resmi, bukan cuma bug teknis"*. Assume it is in scope
whenever the product touches a regulator's rules.

## The oracle: never grade the app against your memory

Two sources, and you need both before you test anything:

1. **The rule** — from the authority, not from the app's marketing. gov.uk / HMRC internal
   manuals (PIM, BIM, HS helpsheets), the regulator's published tables, the fee schedule.
   Write the expected arithmetic by hand, with the specific numbers you are going to enter.
   If you cannot state the expected figure to the penny before you run the scenario, you are
   not ready to test.
2. **The product's own itemised breakdown** — the dashboard estimate, the P&L card, the
   invoice line items, the CSV/Excel/PDF export. This is the oracle you compare against. It
   is also the best evidence for the report: the vendor cannot argue with their own export.

Two bonus sources that make a report land better:
- **The vendor's own public calculators / guides / FAQ.** They encode the vendor's stated
  understanding of the rule. If the app contradicts its own calculator, that is a very strong
  bug argument ("your public Section 24 calculator applies the 20% reducer; the ledger does
  not"). If they contradict the authority, quote both.
- **The plan boundary.** Many of these panels are paid-tier only. Check what a free account
  shows before concluding "the estimate ignores X" — it may just not render that panel.

## Method

1. **Harvest the rules.** Read the vendor's guides, FAQ and public tools; then pull the
   authoritative rule and write the expected figures down. Keep them in a reference file
   (see `references/uk-landlord-tax-rules.md` for the UK landlord set, with worked examples).
2. **Build a controlled scenario, one variable at a time.** A fresh property/source/invoice,
   exact amounts posted through the API (bulk post beats UI typing for precision), and a
   positive control that must not move.
3. **Read the itemised output.** Capture the whole breakdown block, not just one figure — the
   label text often contradicts the arithmetic and is itself the bug.
4. **Minimise with a pair.** "Rent £60,000 + interest £20,000" tells you less than
   "£60,000 alone" versus "£60,000 + £1 of interest": the pair isolates which input changes
   which line.
5. **Convert the delta into money at each band.** "Taxable is £1,000 too high" is abstract;
   "£200 too much at 20%, £400–£450 at 40/45%" is a finding. Always state the rate(s) used.
6. **Decide the class honestly.** Arithmetic errors that only affect the user's own figures are
   product-correctness defects, not access-control findings — say which it is, and check
   whether it is arguably by-design before writing it up.
7. **Clean up and verify.** Delete the probe sources and entries, restore any share/percentage
   you changed, then read the state back through the API. Vendors lend accounts; leave them as
   found and say in the report what you created and removed.

## The quote/check endpoint: money testing with no payment method

Most billing stacks expose **two** doors: `POST …/subscription` (creates an invoice, usually refuses
without a stored payment method — `"No valid payment method available"`) and `POST …/subscription/check`
or `…/products/check` (a *quote* that prices the basket and returns `Amount`, `AmountDue`, `Proration`,
`Credit`, `CouponDiscount`, `Coupon`, `Cycle`, `Currency` without side effects). The quote door is the
real testing surface: unlimited, idempotent, and it does not touch the customer's money.

Find it by grepping the app bundle for `check` next to the payments namespace:

```
payments/v5/subscription/check   payments/v5/products/check   payments/v5/credit/check
```

Then sweep the invariants one dimension at a time, keeping a known-good baseline beside every mutation:

| Dimension | Cases that should be rejected | Cases that should change the total coherently |
|---|---|---|
| Quantity | 0, −1, 1000 | 1 vs 2 (linear, no rounding drift) |
| Cycle | 0, 999 | 1 / 12 / 24 — check the *stated* discount actually applies |
| Currency | unknown ISO code | high- and low-exponent currency (JPY, KRW vs USD) and check `Amount == AmountDue` |
| Coupons | 4+ stacked codes, garbage code | single valid code — `CouponDiscount > 0` **and** `AmountDue` drops by the same amount |
| Credit | negative credit balance | existing credit applied ≤ available |

Report a finding only when the numbers *disagree* (`Amount ≠ AmountDue`, discount not applied,
quantity not linear, proration wrong sign). A sweep that returns "validated correctly across every
dimension" is a **negative result with evidence** and belongs in the coverage section — it is not
nothing, and it is far stronger than "payment flow untested".

Two traps specific to this door:
- **Silently ignored ≠ rejected.** On Proton, 1–2 unknown coupon codes returned 200 with
  `CouponDiscount: 0` (ignored), while 4 codes returned 422 `Invalid coupon selection`. Ignoring an
  invalid code is normal UX; *stacking* being refused is a control working. State which you observed.
- **The quote is not the charge.** A correct quote does not prove the invoice/charge path recomputes
  server-side. Never infer "price tampering is not possible" from the quote alone — say the charge path
  was **not reached** because it required a stored payment method, and never use test cards against a
  live PSP to get there.

## The checkout / order-object ladder (DTC commerce, in-game stores, PSP front-ends)

Same discipline as the quote door above, different door names. Verified on a DTC payments platform for
mobile games (Aghanim, 2026-10-27): the entire ladder held, and the run is now a documented negative.

**Four doors, cheapest first:**

| door | shape here | side-effect free? |
|---|---|---|
| order resolve (read/projection) | `POST /order/v1/orders/{id}/resolve {}` | yes — **this is the read oracle** |
| payment-session quote | `POST /ps/{method}/calculate {order_id, billing_address{iso_code}}` | yes — re-prices per method + country |
| payment-method availability | `GET /ps/?order_id={id}` | yes — returns each method's computed `payment` block |
| the actual charge | `POST /ps/{method}/submit {card…}` | **no** — sandbox test cards only, never a live PSP |

`GET /order/v1/orders/{id}` was `405`; when the resource's GET sibling does not exist, the SPA's own POST
projection (`/resolve`) **is** the state read. Use it for every before/after comparison — never the write
response echo.

**Mutations to attempt, in this order** (all should recompute or reject):

```
PATCH  /order/v1/orders/{id}                items[].price, items[].quantity, amount, total, subtotal,
                                            currency, payment_amount, email, return_url, player_id
POST   /order/v1/orders/{id}/resolve        same fields in the body
POST   /ps/{method}/calculate               amount / total / subtotal overrides
POST   /order/v1/orders/{id}/apply_coupon   {} and a garbage code
POST   /order/v1/orders/{id}/apply_reward_points   {} / {"amount":N} / {"points":N}
POST   /order/v1/orders/{id}/select_subscription_plan  {}
```

Measured result: PATCH returned **200 with the full object echoed** and silently ignored *every* field above
while honouring only `country` (which re-priced correctly). That "200 + echo + silent drop" is the designed
behaviour of an allow-listed PATCH handler — see `api-authz-probe-ordering` §9a. A `404 "Coupon doesn't
exist"` on `apply_coupon` is a correct rejection; `400 "Order does not contain a subscription item"` on
`select_subscription_plan` proves the handler reached business validation.

**The positive control you must run (it is the finding if it fails):** switch `country` and verify the
currency re-price is coherent — SKU priced 1.99 USD went IDR 29 000 / JPY 300 / USD 1.99 / BRL 10.99 /
TRY 99.99 / NGN 3 090, with `payment_amount_usd` stable at 1.61–2.31. Tax was computed from billing country
and marked `included` (`PPN 11 %` for ID, `VAT 20 %` for GB, `subtotal = total − tax`). A wrong FX table,
a stale tax rate, or `total ≠ subtotal + tax` on any single country is the reportable defect — so iterate
*all* of them, not just the default.

**Three traps specific to redemption endpoints** (`apply_reward_points`, `apply_coupon`, store credit):

1. **Re-applying on the same order returns 0 — that is idempotency, not a bypass.** The first apply
   consumed the balance; every later call reports `applied_reward_points: 0` with an unchanged total.
   **Use a fresh order per probe**, otherwise you will read "redemption does nothing" as a control failure.
2. **A `200` on a flag-disabled feature is worth chasing, a `200` you cannot repeat is not.** One guest
   order (no auth) dropped from 2 900 000 to 0 with `applied_reward_points: 161` while
   `feature_flags.reward_points_enabled` was **false** — and 8 fresh orders with the same body, player and
   sequence all returned 0/unchanged. Unreproducible ⇒ lead, not finding; log the recipe and move on.
3. **Replay/idempotency of the charge itself is a separate check.** Re-submitting an already-paid order must
   fail (`400 {"error":{"code":8}}`, `payments/last` → `{}`). If a paid order can be resubmitted, that is a
   double-charge or re-grant bug — test it before you touch anything else on the payment path.

Cross-links: tenant/authz mechanics for the same sweep are in `api-authz-probe-ordering` §9;
the full worked negative matrix for this engagement is
`api-authz-probe-ordering/references/aghanim-2026-10-engagement.md`.

## Pitfalls that produce wrong conclusions

- **Aggregates poison isolation.** The account-level estimate sums every source. Once three
  probe properties exist, "income £130,000" tells you nothing about the scenario you just
  built. Either delete between scenarios or read the per-source panel.
- **A floored estimate hides the effect.** If the computed liability is already £0, adding a
  legitimate deduction cannot visibly change it — the screen shows £0.00 before and after.
  Raise income until the tax is clearly positive before testing whether something reduces it.
- **"No error message" is not "accepted".** Read the raw response. On RSC/Server-Action apps
  the real error lives in the flight segment (`1:{"error":"..."}`); a plain page render with no
  visible error often means a silent no-op. Capture it with `page.on("response")`.
- **A validation error may be about your test value, not the logic.** We concluded "replay
  prevented" from an action that had actually failed because the test identifier was
  invalid (a check-digit suffix). Always run a positive control — same action, same code path,
  a value you know is accepted — before attributing a failure to the rule you were testing.
- **Do not hand-compute with the wrong tax year or band.** Rates change annually; state the
  year you assumed and cite the source. Off-by-one-year assumptions are how you write a false
  positive against a tax product.
- **Regulator-gated features are legitimately untestable.** If the arithmetic sits behind a
  connection to the authority that you are not allowed to make, do not fake it — report it as
  untested, explain the gate, and cite the vendor's public calculator for the rule set.

## Reporting shape that works

- Lead with what is **correct** (the verified-working list). It is the reason a vendor trusts
  the rest, and it is genuinely useful to them.
- Each issue: scenario, the app's own output verbatim, the authoritative rule, the corrected
  figure, the money delta per band, and — where it exists — the vendor's own copy that
  contradicts the behaviour ("we've used whichever saves you more").
- Bundle cosmetic/UI defects (wrong example in an error message, a fabricated status string,
  a duplicate element id) into one paragraph rather than separate reports; they are real but
  they are not findings.
- Keep "not tested / gated" separate and explicit. Never let an untested area read as clean.
