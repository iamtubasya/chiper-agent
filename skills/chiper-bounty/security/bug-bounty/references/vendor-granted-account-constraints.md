# Vendor-granted accounts: honouring — and proving — "do not touch X" constraints

When a vendor grants you access (Pro trial, test tenant, sandbox) they usually attach a written
rule. Real example, verbatim: *"The same rules apply: please don't connect an HMRC account or
submit anything to HMRC."* That sentence is now a **hard scope boundary** for the whole
engagement, and the deliverable includes evidencing that you kept it.

## 1. Turn the sentence into enforceable artifacts

1. **Write it down in the engagement dir** (`_progress/<target>/RULES-<THING>-FORBIDDEN.md`):
   the verbatim quote, the source (email + date), and the explicit list of what is now off
   limits. Future sessions read the file, not your memory.
2. **Guard the tooling, not your intentions.** Any recon/automation script that walks a route
   list gets an env-var skip-list so the forbidden pages are never even navigated to:

```python
VISITS = ["/app", "/app/file", "/app/year-end", "/app/hmrc", "/app/billing", ...]
# GUARD: vendor-granted account — forbidden feature. QW_NO_HMRC=1 drops it entirely.
if os.environ.get("QW_NO_HMRC"):
    VISITS = [v for v in VISITS if v not in ("/app/hmrc", "/app/file", "/app/year-end")]
```

   Then export the guard variable in every run for that engagement (and say so in the log).
3. **Prefer capability checks over page visits.** An API capability flag is a compliant way to
   prove the boundary holds: `GET /api/v1/me` → `capabilities.hmrcSubmission: false` shows the
   API cannot submit regardless of what anyone does. App status strings ("Quarterly period: not
   set yet", "Not checked with HMRC yet") prove no connection exists.
4. **State it in the report.** One short paragraph in the disclosure email: what was
   connected/created (test data only), what was removed afterwards, and that the forbidden area
   was never touched. Vendors reward this; it also pre-empts the triager's first question.

## 2. The near-miss worth internalising

While hunting an unrelated form on a page that ALSO contained the FORBIDDEN action, a generic
fallback — *"find a form and click `button[type=submit]`"* — fired that page's only submit
("Refresh from HMRC"). Two consequences:

- the session was invalidated (next navigation 307 → `/login`), silently making later results
  meaningless until re-login;
- it risked a policy violation on the one action the vendor had ruled out.

Rules that follow:

- On any page that **contains a forbidden control, never use positional/generic clickers.**
  Target an explicit selector AND explicit button text; if the control isn't identified yet,
  dump the DOM and read it instead of clicking a neighbour.
- After ANY unexpected navigation or failed interaction, re-check `location.href` and re-login
  before interpreting results.
- If something forbidden may have fired: verify the resulting state, disclose it in one line to
  the user (and the vendor if relevant), and avoid that page for the rest of the engagement.
  Verify, don't panic — in this case the status still read "Not checked with HMRC yet" and no
  account was connected, i.e. nothing actually happened.

## 3. Untestable-by-constraint is a result, not a gap

Features gated behind the forbidden area (e.g. CGT entry behind "2FA + connect to HMRC") get
recorded as **"not tested within the engagement constraints"**. Never imply a negative finding,
never bypass the gate, and never let a summary table score them as clean.
