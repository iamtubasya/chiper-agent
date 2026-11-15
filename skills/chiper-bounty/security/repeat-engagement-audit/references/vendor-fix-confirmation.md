# Vendor said "we fixed it, please confirm" — the re-verification protocol

Measured 2026-10-31 on `first.org` (F1 FCaptcha empty-signal bypass, F2 OAuth `redirect_uri`).

This is the highest-value moment of an engagement: two findings moved from "submitted" to
"acknowledged + credit promised" the moment the program wrote *"we believe this issue was fixed…
we should credit you at the Bug Bounty HoF and issue you a token of our appreciation. But first we
would like to ask you to confirm this issue was fixed."*

At that point **new hunting on the target is the wrong use of the round**. The deliverable is a
correct, evidence-backed FIXED / NOT-FIXED answer per finding. Getting it wrong in either direction
either wastes the credit or embarrasses you in front of a program that already agreed to credit you.

---

## Step 0 — the on-disk record is stale; the mailbox is the truth

`findings.json` for this engagement said, for both findings:

```
"status": "validated 3x (fresh sessions), draft staged with PDF PoC"
"draft_id": "r-4184621740224655640"   (F1)
"draft_id": "r456641170016005055"     (F2)
```

Two days later the real state was:

- the vendor had replied **twice per finding** (29 Oct: "allow a few days to mitigate"; 30 Oct:
  "we believe this is fixed, confirm please") — and also told us **what** they fixed:
  *"we were running an outdated version of FCaptcha that allowed tokens for unverified pows"*;
- **F1's draft no longer existed** (`drafts.get` → HTTP 404); only F2's did.

So the json was wrong in both directions — it knew nothing about the fix, and it advertised a draft
that had been deleted. Had the operator not asked, the draft id would have been quoted as fact.

Rule: the prior round's `findings.json` / `COVERAGE-LEDGER.json` describes **your** last state, not
the program's current state. Before reporting on an "open" finding, read the vendor thread.

```python
# scripts/gmail_ops.py exposes pick_service() -> (label, service)  TUPLE, not service
label, svc = gmail_ops.pick_service('RESEARCHER_USERNAME')     # index 0 of account_files() is NOT the bounty account
res = svc.users().messages().list(userId='me', q='first.org', maxResults=25).execute()
```

Search the **bare domain** (it also matches signature lines and `no-reply@` senders), then read the
thread oldest→newest and quote the vendor's own words. Also re-`drafts.get` every draft id the
record claims exists before telling the operator "N drafts ready to send".

## Step 1 — replay the ORIGINAL variants, unmodified

Re-running the PoC that now fails is the whole point; do not "improve" it in the same run. Keep the
variant matrix from the original evidence files (`evidence/oauth_validation_run1.txt`, etc.) so
before/after is a like-for-like comparison.

F2 matrix (6 attacker-controlled `redirect_uri` shapes) + 1 control:

| case | 2026-10-26 | 2026-10-31 |
|---|---|---|
| `https://evil.example.com/cb` | 302 → attacker | **400 `redirect_uri_mismatch`** |
| `https://portal.first.org@evil.example.com/cb` | 302 | 400 |
| `//evil.example.com/cb` | 302 | 400 |
| `https://portal.first.org.evil.example.com/cb` | 302 | 400 |
| `http://evil.example.com/cb` | 302 | 400 |
| `http://127.0.0.1:8080/cb` | 302 | 400 |
| control: bogus `client_id` | `invalid_client` | `invalid_client` (unchanged) |

The unchanged control is what makes the other six rows mean something: the endpoint is alive and
still doing *some* validation, so six identical `400`s are a real fix, not a dead route.

## Step 2 — a "negative control" that returns the SAME body as the target is not a control

F1's control was a bogus `siteKey` (`nope.invalid`) sent to `/_fcaptcha/api/score`. Result:

```
real  siteKey=portal.first.org  signals={}  -> 200 {"success":false,"score":0.6,...}
bogus siteKey=nope.invalid      signals={}  -> 200 {"success":false,"score":0.6,...}   identical
```

Read the trap here: that does **not** mean "the control passed". Identical bodies mean `siteKey` is
now ignored on the scoring path, so the control cannot discriminate anything. The discriminator
that does work is the **pre/post flip on the same request**:

```
2026-10-26   {"success":true,  "score":0.40..., "token":"eyJzaX..."}   <- token minted
2026-10-31   {"success":false, "score":0.6, "wouldBlock":true, policy:"stealth-corroboration-v1"}
```

`success:false` with no `token` field is the fix, and it is visible only because the old evidence
file recorded the old body. When a re-verify produces a same-shape response for both real and bogus
parameters, say so explicitly and fall back to the historical body as the control.

## Step 3 — name which links became UNTESTABLE (do not call them hardened)

F1 was a two-link chain: `score (mint token)` → `/auth/confirm` (consume token). Once link 1 returns
`success:false` with no token, link 2 cannot be exercised by anyone, including you.

Write it that way:

> F1 is closed at token issuance. `/auth/confirm` was not exercised in this round because no token
> can be obtained; the report should say "fixed at the scoring endpoint", not "the confirmation
> endpoint is hardened".

Calling it "hardened end-to-end" would be an over-claim of exactly the kind `probe-validation` §5
exists to stop.

## Step 4 — verdict vocabulary

| verdict | requires |
|---|---|
| **FIXED** | same request that used to succeed now fails, mechanism changed in the direction the vendor described, and a control proves the route is alive |
| **STILL VULNERABLE** | original behaviour reproduces; say so plainly and re-attach evidence — credit is not lost for an incomplete fix |
| **PARTIAL** | one variant blocked, another still passes. Report the surviving variant only; it is usually more valuable than the original |
| **INCONCLUSIVE** | timeouts / WAF / 5xx. **Never** report this as fixed — that hands the program a free "resolved" |

## Step 5 — the reply

One email per finding (programs ask for it; FIRST's own page does). Each reply carries:

1. the test date and that the same PoC was replayed;
2. a before/after table of the exact requests;
3. the control row proving the endpoint is alive;
4. an explicit "confirmed fixed" sentence the triager can paste into their tracker;
5. credit confirmation (`Hall of Fame as Mr Fz`) — **no reward ask**, no severity re-litigation.

Keep the re-verify script re-runnable and dated: `tools/reverify_<YYYY_MM_DD>.py` writing
`evidence/reverify_<YYYY_MM_DD>/reverify.txt`, so a third party can repeat the answer next month.

---

## Appendix — harness gotchas that cost real calls here

| symptom | cause | fix |
|---|---|---|
| `TypeError: expected BaseHandler instance, got <class 'ssl.SSLContext'>` | `build_opener(handler, ctx)` — an `SSLContext` is not a handler | `urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))` |
| redirect never observable, everything looks like a 200 | default opener follows the 302 | custom `HTTPRedirectHandler.redirect_request → None` to force `HTTPError`, then read `e.headers['Location']` |
| `gmail_ops.pick_service()` returns a tuple, not a service | it returns `(label, service)` | `label, svc = g.pick_service('RESEARCHER_USERNAME')` |
| `curl ... -w "\n%{http_code}"` → `curl: (23) client returned ERROR on write` | broken pipe on the console writer under bash/MSYS | drop `-w`, or write a body to a file with `-o` — and prefer the Python harness anyway (curl is last resort) |

Working skeleton (stdlib only, no requests dependency):

```python
import ssl, urllib.request, urllib.error
from http.cookiejar import CookieJar

class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None

def req(url, data=None, headers=None, follow=True):
    h = {"User-Agent": "Mozilla/5.0 ... Chrome/131.0.0.0"}
    h.update(headers or {})
    r = urllib.request.Request(url, data=data, headers=h)
    ctx = ssl.create_default_context()
    https = urllib.request.HTTPSHandler(context=ctx)
    op = (urllib.request.build_opener(urllib.request.HTTPCookieProcessor(), https)
          if follow else urllib.request.build_opener(NoRedir, https))
    try:
        resp = op.open(r, timeout=25)
        return resp.getcode(), resp.read().decode("utf-8", "ignore"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore"), dict(e.headers or {})
```
