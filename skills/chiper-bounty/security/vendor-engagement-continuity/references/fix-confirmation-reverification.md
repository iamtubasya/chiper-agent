# Re-verifying a vendor's "we believe this is fixed"

Worked recipe from FIRST.org (2026-10-31), F1 = FCaptcha anti-automation bypass,
F2 = OAuth `redirect_uri` not validated. Both confirmed fixed, three rounds each, in the
thread the vendor opened. Use this whenever Step 8 fires.

The whole point of this pass is that the vendor's claim is a **hypothesis**, and your reply is
the artefact that closes the payout. A wrong "looks good, thanks" is unrecoverable.

---

## 0. Three rounds is the unit, and isolation is what makes them three

Two runs of the same script are one observation. Three rounds count only if each starts from a
clean state **and** you can show the mechanism differed.

```python
def fresh_opener(follow=True):
    """New cookie jar + new opener = no state carried between rounds."""
    jar = cj.CookieJar()
    handlers = [urllib.request.HTTPCookieProcessor(jar),
                urllib.request.HTTPSHandler(context=ssl.create_default_context())]
    if not follow:
        handlers.insert(0, NoRedirectHandler())   # return None from redirect_request
    return urllib.request.build_opener(*handlers)
```

Per round, per payload: **new opener, new CSRF, new page fetch.** Sleep 2–5 s between requests
and 5 s between rounds — on a captcha-protected endpoint, back-to-back requests pull a
rate-limit branch that looks like a different verdict (see §3).

Aggregate at the end and print the verdict, not the transcript:

```python
verdict = {
    "all_rounds_identical": len({frozenset(r["f1"].items()) for r in rounds}) == 1,
    "never_accepted": not any("ACCEPTED" in r["verdict"] for r in results),
}
```

`any ACCEPTED anywhere: False` is the single line the vendor can act on. Print it explicitly.

## 1. The CSRF trap that silently invalidates every test (cost: 9 wasted requests)

A confirmation/replay endpoint that carries `__req` (or any per-page token) will answer
**"This request is expired or invalid"** when the token is missing — and a naive classifier
that looks for the substring `captcha` in the body will read the widget's markup and score it
`REJECTED_CAPTCHA`. You then "prove" enforcement that never ran.

Two independent failures I made before getting it right:

| Mistake | Symptom | Fix |
|---|---|---|
| fetched `__req` from `GET /auth/signup` | signup **404**s; `csrf=""` on all 9 requests | dump `document.querySelector('form').outerHTML` — the token lives on the **same page as the form** (`GET /auth/confirm`) |
| classifier matched `captcha` anywhere in the body | widget markup → false `CAPTCHA_REJECT` | match the **error container only** (`class="s-msg s-msg-error"`), and assert the distinct strings |

Correct extraction, then assert before trusting any verdict:

```python
_, page = fetch(op, BASE + "/auth/confirm")
csrf = re.search(r'name="__req"[^>]*value="([^"]*)"', page).group(1)
assert csrf, "no CSRF token - every verdict below would be CSRF_FAIL, not a test"
```

**Always ship a deliberate-CSRF-failure control.** It must produce a *different* string
(`"expired or invalid"`) from the branch you are testing. That control is what proves your
other results reached the real gate.

## 2. Replay the form VERBATIM — read the shipped default before inventing payloads

The page's own HTML carried the answer:

```html
<input type="hidden" id="utoken" name="_utoken" value="none" data-fcaptcha="...">
```

`_utoken="none"` is what a real browser submits before JS replaces it. If the server accepted
that, the control was still bypassed. So the payload matrix must include **exactly what the page
ships**, not only the values you think are interesting:

```
shipped_none   "none"      <- the real-world bypass attempt
empty_string   ""
null_literal   "null"
omitted        <not sent>
```

All four × three rounds = 12 posts, each with a fresh CSRF. Result: **11 rejected at the captcha
branch, 1 rate-limited, 0 accepted.**

## 3. A rate-limit branch is not an acceptance — and not a captcha rejection either

Round 3's `omitted` case returned:

```
"You've sent more requests than allowed in a short period of time."
```

This is a **third** branch. Do not fold it into either column:

- it is **not** evidence the bypass works (no mail was dispatched — verify against a test inbox),
- it is **not** a clean captcha rejection, so `12/12 rejected` would be a small lie.

The honest sentence, which I put in the reply itself:

> Eleven of those twelve requests were refused with "This request requires additional
> verification…". The twelfth (the last one in round 3, so after a burst of traffic) returned the
> rate-limit message instead — I am flagging that explicitly rather than reporting a clean 12/12,
> because it is not a clean 12/12.

Vendors notice this. It costs one sentence and buys the credibility of every other number.

## 4. Branch discrimination beats "the control also got rejected"

FIRST.org killed the control Step 8 used to recommend:

```
siteKey=portal.first.org -> {"success":false,"score":0.6,"wouldBlock":true,...}
siteKey=nope.invalid     -> {"success":false,"score":0.6,...}   BYTE-IDENTICAL
```

That control cannot discriminate. What does discriminate:

```
broken __req    -> "This request is expired or invalid."                 CSRF   (earlier)
unverified tok  -> "requires additional verification ... robot"          CAPTCHA (the gate)
burst volume    -> "sent more requests than allowed ..."                 RATE   (third)
```

Three distinct strings from one endpoint = the captcha gate is real and the request reached it.
On F2, `client_id=bogus → 400 invalid_client` alongside six `redirect_uri → 400
redirect_uri_mismatch` proved both parameters are still evaluated — the endpoint is not failing
open, it is enforcing.

For a pre/post fix differential, the strongest evidence is still the **stored old response**:

```
2026-10-26  {"success":true,"score":0.40,"token":"eyJzaX...InRp..."}   token minted
2026-10-31  {"success":false,"score":0.6,"token":null,
             "reason":"pow_not_satisfied","recommendation":"block"}    no token
```

Note `token` is **present but null**. A check like `"token" in json_body` reports `True` and
inverts the verdict. Test `bool(body.get("token"))`, and print the value, not the presence.

## 5. Sweep every variant originally reported

F2 originally listed six redirect_uri tricks. Re-test all six, three rounds = 18 requests:

```
evil_domain        https://evil.example.com/cb                 400 redirect_uri_mismatch  ×3
userinfo_trick     https://portal.first.org@evil.example.com   400 redirect_uri_mismatch  ×3
protocol_relative  //evil.example.com/cb                       400 redirect_uri_mismatch  ×3
path_suffix        https://portal.first.org.evil.example.com   400 redirect_uri_mismatch  ×3
http_downgrade     http://evil.example.com/cb                  400 redirect_uri_mismatch  ×3
localhost          http://127.0.0.1:8080/cb                    400 redirect_uri_mismatch  ×3
```

Report `off-domain redirects: 0 / 18` and **`no Location header on any of them`** — absence of the
header is the mechanism, and it is what a prefix-only validator would not guarantee.

## 6. Prove the side effect did NOT happen, from outside the probe

Do not claim "no email was dispatched" from the response body. Query the inbox:

```
to:<your-plus-address> newer_than:2d      -> 0
from:<vendor-domain>   newer_than:1d      -> only the vendor's own replies
```

Gmail delivers plus-addressed mail to the base mailbox but **does not honour `to:` search for
the plus form**. What works: `deliveredto:` (alias addresses) or `to:` with the base address.
If both return 0 that is not proof — confirm the address is searchable at all by finding a
message you know arrived there, then report the checked query verbatim.

## 7. Attachments are generated FROM the JSON, never hand-written

The first attachment attempt was written by hand and silently mismatched the draft prose
(different run counts). Generate the attachment from the same `rounds.json` the verdict came
from, in the staging script that creates the draft:

```python
rounds  = json.loads((E / "rounds.json").read_text())
confirm = json.loads((E / "f1_confirm_3rounds.json").read_text())
lines = [f"{r['round']:<7}{r['variant']:<15}{r['verdict']}" for r in confirm]
```

Now the numbers in the mail, the attachment and the ledger cannot diverge. Also state the
protocol-level scope inside the attachment: *"no authorization code was successfully issued and
no tokens were exchanged — probes stop at the redirect decision."*

## 8. Restaging: delete the superseded draft only after the new one is verified

Drafts rot and drafts get superseded. Sequence that is safe:

1. verify the new body/attachment pair builds,
2. create the new draft **in the original `threadId`**,
3. re-fetch it and assert `threadId` matches and the attachment part is present,
4. delete the superseded draft id — never before step 3.

On FIRST.org the pre-fix report draft `r-4184621…` was **gone (404)** while its sibling survived.
Treat a missing draft as "already sent", not as data loss — and say so in the reply to the
operator rather than silently re-creating a report that may already be filed.

## 9. Ledger entry shape

Write the verdict back into `findings.json` so a later round inherits it:

```json
"reverify_2026_10_31": {
  "rounds": 3,
  "F1": {"verdict": "FIXED",
         "score_endpoint": "token=null, reason=pow_not_satisfied -- identical 3/3",
         "confirm_endpoint": "12 posts: 11 captcha-branch, 1 rate-limited, 0 accepted",
         "emails_dispatched": 0,
         "evidence": ["evidence/reverify_2026-10-31/rounds.json",
                      "evidence/reverify_2026-10-31/f1_confirm_3rounds.json"]},
  "F2": {"verdict": "FIXED",
         "result": "18/18 400 redirect_uri_mismatch, no Location header"},
  "drafts_staged": {"F1": {"draft_id": "...", "thread_match": true},
                    "superseded_deleted": ["..."]}
}
```

---

## Checklist before you tell the operator it is ready to send

```
[ ] 3 rounds, fresh session per round, round count stated in the reply
[ ] every variant from the original report re-tested, count stated (n/N)
[ ] control whose output DIFFERS from the target (branch discrimination, not "also rejected")
[ ] old-vs-new response quoted side by side
[ ] token/field presence tested with bool(), not `in`
[ ] rate-limit / partial results disclosed, not rounded away
[ ] explicit "what I did not replay" (no mail sent, no token minted)
[ ] side effect checked from the inbox, query quoted
[ ] attachment generated from the same JSON as the verdict
[ ] draft in the original threadId, re-fetched, thread_match asserted
[ ] recipient is the vendor's reply-to, subject is Re: <their subject>
[ ] credit handle + "let me know once the credit is processed" present
```
