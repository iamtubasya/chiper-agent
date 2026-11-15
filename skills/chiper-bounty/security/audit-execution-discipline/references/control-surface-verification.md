# Control-surface verification — kill these three false positives before reporting

Three candidates in one engagement (FreeAgent, 2026-10) looked like findings and were disproven by
one extra probe each. The pattern repeats across targets, so check for it deliberately.

---

## 1. "The API returns X to a low-privilege user" → check for **field-level filtering**

Observed: a `permission_level=1` ("Time only") token received `200` from `GET /v2/contacts` while the
web UI refused `/contacts` outright. Loud-looking authz gap.

Disproof: re-request the same object with the **owner** token. The owner response carried
`email`, `phone_number`, `address1`, `town`, `postcode`, `account_balance`; the low-priv response
carried the same resource **minus every sensitive field**. So the API is permission-aware and the
200 is intentional (the user needs contact names to log time).

**Rule:** a 200 is not an authorization finding. Diff the *field set* between privilege levels before
writing anything. Same-shape resources with reduced fields = by design.

## 2. "The control doesn't cover document type Y" → check whether **Y reaches the protected asset**

Observed: with an account lock set (`locked_to_date`), creating/editing/deleting **draft invoices**
inside the locked period succeeded, while expenses and bills were refused with
`dated_on is in a locked period`.

Disproof: the lock is an *accounting* lock. Drafts do not post to the ledger, and the operation that
would post (marking a locked-period invoice as Sent) **is** refused (`Invoice is locked.`), as is
re-dating an already-posted invoice. Ledger evidence: the balance sheet as at the lock date was
byte-identical before and after. The control is complete for everything that matters.

**Rule:** before calling a control incomplete, ask *what does the control protect?* Then test whether
the uncovered path actually reaches it. A lock/integrity control is about effect, not about a
verb. Verify with the downstream artefact (balance sheet, ledger, report), not with the HTTP status.

## 3. "No rate limiting / no lockout" → push until you find the **actual threshold**

Observed: six consecutive wrong passwords all returned a normal page, no 429/423, no CAPTCHA, ~8.7 s
round-trip, steady. Tempting to report "no lockout → unlimited online password guessing" (and the
program even keeps *auth-related* rate limiting in scope, so it would have been submittable).

Disproof: after 15 failures the correct password then returned
`Login attempt failed too many times`. The lockout exists; the threshold is simply above the sample.
Reporting it would have been a fabricated High.

**Rule:** probing a control's *absence* requires reaching past its threshold, and the honest answer to
a bounded probe is **inconclusive**, never "absent". Push one deliberate step further (a single extra
attempt after the last negative) rather than stopping at a round number. Stay inside the program's
brute-force limits: a bounded probe on your **own** account, with the finding framed as
"threshold ≈ N", is the defensible shape.

---

## Checklist to run on every "candidate" before it becomes a finding

```
□ For an authz 200:   diff the field set across privilege levels (owner vs low-priv).
□ For a control gap:  name the asset the control protects; test whether the uncovered path reaches it;
                      verify with the downstream artefact (ledger/report/state), not the status code.
□ For a missing limit: probe past the threshold on your own account; if you stopped early, write
                      INCONCLUSIVE. Never "absent" from a bounded sample.
□ Then re-read your wording: no "by design" labelled as a bug, no threshold you did not reach,
                      no field you did not diff.
```
