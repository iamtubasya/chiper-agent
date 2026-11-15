# Falsifying a candidate before you write it up

Complements RULE 24 (candidate review = 3× check). RULE 24 asks *is this real?*. This file is the
technique that actually answers it: **differential re-testing**. On the 2026-10-02 engagement three
"findings" were produced and two dissolved the moment a control was run — which is the normal ratio
for a mature target, not a failure.

Rule of thumb: **a candidate is a hypothesis about the app's rules. Before writing it up, design the
test that would FALSIFY it, and run that test.** If the falsifier contradicts you, drop the candidate
and keep the falsifier as evidence.

---

## Pattern 1 — Low-privilege access ⇒ compare the SAME request as a higher-privileged principal

Candidate: *"a user with permission 'Time' can call `GET /v2/contacts` (200) while the web UI denies
/contacts → broken function-level authorization."*

Falsifier: run the identical request with the **owner** token.

Result: owner received the full record (email, phone, address, balance); the low-privilege user
received a **reduced representation** (name/org only). The API is permission-aware → the 200 is
correct behaviour, the *response was shaped*, not the *rule was broken*. Verdict: by-design, DROP.

```python
# the control that decides it — same endpoint, two principals, diff the FIELD SETS
owner = json.loads(call("GET", "/v2/contacts/ID", tok=OWNER)[2])
lownp  = json.loads(call("GET", "/v2/contacts/ID", tok=EMP)[2])
print(sorted(owner["contact"]) - sorted(lownp["contact"]))   # non-empty ⇒ field filtering exists
```

Generalise: for any "low-priv user can reach X", diff against the higher-privilege response **before**
claiming an authz gap.

## Pattern 2 — "The control doesn't apply here" ⇒ compare against the authoritative source and sibling paths

Candidate: *"with the account lock active, invoices dated inside the locked period can still be
created/edited/deleted → closed-period integrity bypass (Medium)."* It reproduced cleanly across four
attempts, which is exactly when over-claiming happens.

Falsifiers, in order of strength:
1. **Sibling comparison** — the same operation on other document types: expenses and bills returned
   `422 dated_on is in a locked period`. So a rule exists and is enforced elsewhere.
2. **Authoritative-source comparison** — the ledger, not the document: balance sheet as at the lock
   date, before vs after writing the "locked-period" document → unchanged, because draft documents are
   unposted.
3. **The decisive one** — post a document dated *after* the lock, then try to re-date it *into* the
   locked period: `422 dated_on is in a locked period`. Posting into the closed period is blocked, and
   `mark_as_sent` inside the lock returns `403 Invoice is locked.`

Verdict: the lock is an **accounting** lock (blocks anything that *posts* into the period, permits
unposted drafts) — internally coherent, DROP. Without steps 2–3 this would have been a false Medium.

Generalise: for any "state/permission check is missing", test the operation that actually has
consequences (the posting, the payment, the transition), and check the number that matters (the
ledger), not the surface flag.

## Pattern 3 — "There is no rate limit / no throttle" ⇒ push past your own threshold, then re-test the happy path

Candidate: *"no lockout or rate limiting on the credential step — 6 sequential wrong passwords, all
200, ~8.8 s each."* Looks strong; it is an artifact of stopping early.

Falsifier: continue to ~15 attempts, then submit the **correct** credential.

Result: after 15 failures the correct password returned `Login attempt failed too many times` — the
lockout exists, the threshold simply sits above the sample window. Verdict: DROP the "no rate limit"
claim. (The OTP step had already shown its own limit at ~10 — the asymmetry was the tell that a
control existed somewhere.)

Generalise: **absence-of-control claims are only valid past the control's own threshold.** Bound the
probe deliberately (own account, small N, no mass brute force), report the exact N you reached, and
never state "no rate limit" from a sample below the plausible threshold.

## Pattern 4 — A `200` on a sensitive path ⇒ prove it is not a catch-all, then prove the differ

Two candidates from the `account.jetbrains.com` run (2026-10-10), both killed by the same two-step
control. **A 200 is a claim about routing before it is a claim about behaviour.**

### 4a. `/uploads/test.php` → 200 — "uploaded PHP probe is reachable, possible RCE"

```
HTTP/1.1 200 OK
Server: awselb/2.0
Content-Type: application/json
Content-Length: 54

{ "reference_code": "18#.1010", "message": "OK" }
```

Falsifier 1 — *is this path special, or does everything return 200?* Request a path that certainly
does not exist and diff the response. A **catch-all / SPA fallback** answers 200 with the same shell
for every unknown path, so "my probe returned 200" carries no information.

Falsifier 2 — *does the response look like the thing I claimed?* A reachable uploaded shell would
return PHP output or the uploaded bytes. This returned a generic JSON envelope from the load
balancer. Content-type `application/json` + a fixed message + no interpreter marker = the request
never reached any upload handler. Verdict: DROP (catch-all route, not an upload).

```
Rule: for "sensitive path returns 200", you must show the path is DISCRIMINATED —
      a control path returns something different. Otherwise the 200 is the router, not the app.
      Corroborate with content-type + body shape: an executed upload does not answer in
      `application/json` with a canned envelope.
```

### 4b. `/reset-password/<token>` → flapping 302/200 — "weak token accepted"

First observations were inconsistent across repeats: `00000000` → 302 with
`Location: /reset-password`, then later → 200. **Instability is not a finding** — it is the signal to
find the differ. Two controls:

Falsifier 1 — *vary the token and diff.* Random 8-hex, random 32-hex, `aaaaaaaa…`, `1234…` — **all**
returned byte-similar pages (~3.0–3.1 KB) and **no token was ever rejected differently**. A valid-token
acceptance path would separate from the invalid path.

Falsifier 2 — *read the body, not the status.* The page was:

```html
<title>Please confirm that you are not a robot</title>
```

i.e. a **generic CAPTCHA interstitial**, served before any token validation. The MD5s differed only by
a per-response nonce/session value, not by content branch.

Verdict: DROP. The 302↔200 flap was CDN / rate-limiter flakiness, and the CAPTCHA sits *in front of*
the token check, so the token was never evaluated. Note the honest ceiling: this disproves
"weak token accepted"; it does **not** prove the token logic is sound — say which one you proved.

```
Rule: when the same request gives different statuses across repeats, do NOT pick the interesting one.
      Re-run with VARIED inputs and diff the BODIES; if every input yields the same page, you are
      looking at a gate (CAPTCHA/WAF/interstitial), not an oracle.
```

### The generalised two-step control

For any "I got a 200 / a redirect / an odd status on a sensitive path":

1. **Discrimination test** — send a control request that should behave differently (nonexistent path,
   known-invalid input, a different principal). If control and candidate are indistinguishable, you
   have learned nothing about the app.
2. **Substance test** — read content-type, body shape, and the actual differ. Statuses and sizes alone
   are routing facts. Never report from status/size correspondence; report from a **differ in content**.

Both candidates above had been auto-DOWNGRADED by the pipeline (`impact_score=0`, reason "no in-scope
impact class proven"). The manual falsification **confirmed the gate was right** — which is the
expected outcome for a mature target and is itself worth recording, because it shows the downgrade was
earned rather than lazy.

---

## Checklist to attach to each candidate

```
[ ] what would falsify this? (the single test)
[ ] ran the falsifier                          (evidence file path)
[ ] compared against a control:   higher-priv principal / sibling endpoint / authoritative source /
                                  happy path after the probe
[ ] verdict: READY | DROP (by-design) | DOWNGRADE | INCONCLUSIVE (say which, and why)
```

Report shape when a candidate is dropped: keep it in the report as **"candidate disproven"** with the
falsifier quoted. It proves the control works, it protects you from re-raising it next session, and it
is exactly what separates an audit from a scan dump. Do not silently delete it.
