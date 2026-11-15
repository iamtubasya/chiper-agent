# Retired-identifier chains — recon leak to money impact

Class-level recipe for the chain where a historical URL leaks an identifier the backend
still honours. Worked case: Hivenet, 2026-10-26, finding F4 (High 7.6).

## 1. Where the ids come from

```
gau --threads 3 --subs <host>            # or waybackurls <host>
```

Do not stop at the path list. Grep the **query strings** — that is where the money is:

```
grep -oE 'https://<host>/\?[^ ]*' gau_<host>.txt | sort -u
```

Parameters worth extracting every time: `plan_id`, `price_id`, `priceId`, `coupon`,
`promo`, `referral_code`, `variant`, `sku`, `tier`, `feature`, `flag`, `discount`.
Non-obvious formats count too — Hivenet had both a Stripe id
(`price_1OyEzIHCnr9Hivhnd4kjZ7nw`) and a bare ObjectId-shaped one
(`68272dd57e334bfa23b8c78b`) in different archived URLs.

## 2. The test

Two calls, in this order:

```
GET  <payment>/plans/public          # the published catalogue
POST <payment>/subscriptions         # body: {emailAddress, priceId: <leaked id>}
```

Interpretation:

| Result | Meaning |
|---|---|
| 400 "No such price" | the id is dead — record as a verified negative and move on |
| 201 + session URL | **the id is live and sellable** — this is the finding |

The gateway validating the id at all is *good* for the report: it proves the lookup
happens, so the missing piece is precisely the comparison against the published
catalogue. Quote both the 400 (control) and the 201 (finding) in the write-up.

## 3. Proving what the id actually sells

The Stripe checkout page is a JS app — the amount is **not** in the static HTML. Fetching
the session URL with curl returns a page with no price in it.

Two traps:
- The URL carries a `#fid...` fragment. Without it Stripe renders
  "This link is incomplete". Always use the **full** `sessionURL` from the API response,
  not just the `sessionId`.
- The page needs ~15 s to hydrate before the product block exists.

Working probe (Playwright):

```python
pg.goto(session_url, wait_until="load", timeout=60000)
time.sleep(18)
head = pg.inner_text("body")[:600]      # product name + amount live at the top
# -> "Subscribe to 1000GB Easter Offer / IDR 21,050.07 per month / Total due today IDR 21,050.07"
```

Read three things off the page: the **product name**, the **per-period amount**, and the
**total due today**. Convert the local-currency figure with the rate the page itself
prints ("1 EUR = 21,050.0613 IDR") rather than assuming.

## 4. Validation (3x, per the operator rule)

Three separate accounts, each with its own token, each producing its own session. Do not
reuse one session three times — that is one validation, not three.

Watch for **token expiry mid-run**: Hivenet's passwordless tokens lasted ~24 min, so a
batch that starts with three valid tokens can end with two 401s. Re-auth the failed
accounts and re-run them rather than reporting 1-of-3.

## 5. Honesty framing (what keeps the report alive)

State plainly what was not proved:
- "I did not complete a payment, so I cannot show the subscription being granted at the
  discounted price — only that the checkout session is created for it."
- "I found one unpublished id; I cannot enumerate the vendor's Stripe account, so I cannot
  say how many exist."

Then give the impact in the vendor's own units: same capacity, published price vs this
price, the percentage, and the fact that accounts are free and unlimited so the discount
can be claimed repeatedly. That is what turns "a weird price id" into a revenue finding.

## 6. Report shape

- Root cause in one sentence: *the backend validates that the identifier exists, never
  that it is currently offered.*
- Table: published prices (id, amount, capacity) with the rogue row marked
  "NOT published — still active".
- Controls that hold (fabricated id rejected, free-plan id rejected, second archived id
  rejected) — they prove the lookup and narrow the defect.
- Remediation: allowlist derived from the catalogue server-side; deactivate retired
  promotional prices; keep ids out of archivable URLs; alert on sessions for
  non-published prices.
