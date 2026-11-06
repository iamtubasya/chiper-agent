## Verification discipline

### The "gated resource got created" false positive (near-miss, do not repeat)

Testing whether a free tier's limit could be bypassed, `addPropertyAction` was fired
directly and returned a redirect body — no `error`. The check was "does a property named
`Second Property FREE TIER` now appear on the dashboard?" It did. That looks like a
severity-worthy plan-gate bypass.

It was not. That account had **no** income source yet — the action had legitimately created
its *first* property, under a name the tester chose. Firing the action again on the same
account returned the real gate message ("Your free plan includes 1 property you own").
Firing 12 concurrent `addProperty` calls returned the same message 12/12 — no TOCTOU.

Rules that fall out of this:

- A success-looking create on a quota/plan-gated resource proves nothing until you count.
  **Attempt the N+1th object, or read the authoritative list/export, and count rows.**
- Never name or label your own test data ("Second…", "Bypass…", "Pwned…") before you have
  verified the effect — a misleading name is how a self-inflicted false positive gets
  written up. Name it neutrally, verify by count.
- Race the SAME action in parallel (`Promise.all` of N submissions inside one
  `Runtime.evaluate`, or N threads) — a serial single-shot cannot distinguish a real gate
  from a client-side one.
- When you catch your own false positive, retract it explicitly in the write-up. A
  self-debunked candidate is a stronger signal of a real audit than an inflated one.

### General

- Claim findings only against a source-of-truth endpoint (e.g. `/api/account/export`
  returns the real stored rows: dates, amountPence, category, externalRef).
- Baseline + test pairs: legit action from own session, then the tampered variant; if the
  legit one also 500s, your POST construction is broken — fix that before concluding.
- After stored-XSS / formula-injection tests, RESTORE the data (rename back, delete test
  notes/properties/reminders) and verify the restore.

