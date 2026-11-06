## Missing-idempotency race (duplicate submit)

- Same-tick double submission: TWO `element.click()` calls inside one `Runtime.evaluate`
  → **two identical ledger/financial rows** (server action has no idempotency key).
- Realistic double-click (150 ms apart) → ONE row (modal closes after first click).
  So duplication needs a scripted/replayed trigger → severity Low/informational, pitched as
  "missing idempotency, matches API which dedups on externalRef".
- Verify with the app's own **export/data API** as ground truth — never by counting
  occurrences in page text (labels duplicate the amount, inflating counts).

