# Scanner false-positive disproof kit

Measured 2026-10-25 on Proton (SPA hosts, single-identity run). Three scanners each emitted a
positive; all three were false. These are the one-shot disproofs — run them before a scanner
candidate reaches `CANDIDATES.md`, and record the dismissal so the coverage section can cite it.

## 1. dalfox POC on an SPA route => reflection test, not payload test

dalfox reported:
```
[POC][G][GET][BUILTIN] https://account.proton.me/calendar/signup?ref=ctaprd
```
plus a second entry for an invented parameter (`?pleasedonthaveanamelikethis_plz_plz=DalFox`).
That invented-parameter line is itself a tell: dalfox flags *any* reachable URL shape, the `[BUILTIN]`
marker is not evidence of execution.

Disproof (four checks, all cheap):
```python
import requests, hashlib
base = "https://host/route?ref="
for p in ["zz9f3k2mcanary", '"><img src=x onerror=alert(1)>', "javascript:alert(1)",
          "<svg/onload=alert(1)>"]:
    r = requests.get(base + quote(p), timeout=25)
    print(r.status_code, len(r.text), hashlib.sha256(r.content).hexdigest()[:12],
          [m in r.text for m in ("zz9f3k2mcanary","alert(1)","onerror")])
# and compare: same URL with NO param at all
```
Verdict rule: identical body length **and** identical sha for every payload **and** for the
no-parameter request => the parameter is never reflected; it is a catch-all SPA shell => FALSE POSITIVE.
Also check response headers for reflection, and grep the bundle for the parameter to see whether it
reaches a DOM sink at all — on Proton the only use was `params.append("ref", ...)` into a redirect
URL, i.e. no sink.

## 2. ffuf "exposed file" hits on an SPA host => sha-identity against a random path

ffuf (80 words x 7 hosts) returned `.env`, `.git/config`, `actuator/env`, `actuator/heapdump`,
`Dockerfile` as 200/403 — which reads like a jackpot. It is a soft-404: the SPA serves `index.html`
for every unknown path and Cloudflare adds a 403 variant.

Disproof:
```python
for p in ["/zz-nonexistent-9f3k2m", "/actuator/env", "/.git/config", "/Dockerfile", "/.env"]:
    r = requests.get(host + p, allow_redirects=False)
    print(r.status_code, len(r.content), sha256(r.content).hexdigest()[:12], r.headers["content-type"])
```
Rule: a finding is real only if its `(status, length, sha)` tuple differs from the **random-path**
baseline. On Proton every one matched the baseline exactly (same 21247 bytes / same sha) while
`/api/doesnotexist` returned a genuine `404 application/json` 50-byte body — so the API namespace is
the only place a real 404 exists. Compare against a random path in the same namespace, and against
one known-bad API path, before believing any 200.

## 3. sqlmap 400/401 is an INVALID run, not a negative

Two traps hit in one session:
- First run: every request returned `400` because the mandatory headers (`Accept`,
  `x-pm-appversion`) were not sent. sqlmap then reported "all tested parameters do not appear to be
  injectable" — that conclusion is worthless, the server never parsed the parameter.
- Second run with headers: `401` for the unauth endpoint, `422` once authenticated, and the parameter
  was "not dynamic". That IS a real negative.

Rule: after any sqlmap/ghauri run, check the HTTP code histogram at the bottom of the log. If the
dominant code is 400/401/403/415, the run is **invalid** — re-run with the application's required
headers/cookies and `--ignore-code` only if intentional. Never let "not injectable" from a 400-heavy
run reach the ledger. ghauri behaves the same; note that "heuristic shows parameter might not be
injectable" is a heuristic, not a verdict, and a boolean-blind sweep can run for 10+ minutes while
saying nothing — capture the log, do not infer.

## 4. Username-availability "oracle" => check whether the suggestions are synthetic

`GET /core/v4/users/available?Name=auditfz77310` returned 409 "Username already used" with
`Suggestions: ["auditfz773109","auditfz773107",...]` for a taken name and 200 for a free one. That
looks like username enumeration. It is not: the endpoint is a *documented availability check*, and
the suggestion list is generated, not sampled. Verify by querying each suggested name — on Proton all
of them returned 200 (free). If suggestions are not real accounts, nothing about other users leaked.
