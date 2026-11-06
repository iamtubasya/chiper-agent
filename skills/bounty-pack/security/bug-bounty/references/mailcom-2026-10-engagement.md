# mail.com — 2026-10-21 — Host Header Injection in auth flow (FOUND, validated, shipped)

Target: mail.com (United Internet / 1&1 Mail & Media). Program: bugbounty.mail.com
(report@bugbounty.mail.com). Discretionary rewards; scope = "web applications within the
authenticated area processing customer data ... including the authentication systems". OOS:
missing headers / info leakage / self-XSS / logout-CSRF style items.

## Finding MC-HOSTHDR-01 — Host header injection (validated 3x)

The auth services build absolute redirect URLs from the untrusted `Host` header and append
live session material:

```
$ curl -s -D - -o /dev/null 'https://password.mail.com/passwordrecovery/' \
    -H 'Host: attacker-controlled.example.com'
HTTP/1.1 302 Found
Location: https://attacker-controlled.example.com/passwordrecovery/?srttkn=1fa6a183-...

$ curl -s -D - -o /dev/null 'https://account.mail.com/' -H 'Host: attacker-controlled.example.com'
HTTP/1.1 302 Found
Location: https://attacker-controlled.example.com/ciss/login;jsessionid=17CFFF01289785F3065D4F0B7726D19C
```

A Host-header sweep over every live host found **5 affected** (same root cause):
password.mail.com, account.mail.com, ciss.mail.com, account-ba.mail.com, account-lxa.mail.com.

Impact framing that shipped: password-reset link poisoning -> ATO (the reset email is built
from the same base URL, so the victim's reset link points at the attacker domain and the token
is harvested); plus session-token leakage (srttkn / jsessionid) to a third-party host.

## Verification runs (the 3x rule)

1. `Host: evil.example.com` -> poisoned Location with srttkn
2. `evil1.example.com` / `evil2.example.com` -> identical behaviour, fresh token each time
3. `attacker-controlled.example.com` -> reproduced + sweep confirmed all 5 hosts

## Negatives documented (so the triager need not repeat)

- URL-supplied `;jsessionid=` session fixation: container issues a fresh JSESSIONID and
  ignores the URL value.
- Cache poisoning of the poisoned redirect: no `CF-Cache-Status`, fresh token every request.
- `X-Forwarded-Host`: not honoured (only `Host` is trusted).
- TRACE enabled on the Wicket hosts: informational only (reflects headers).

## Reusable technique — Host-header sweep

After mapping live hosts, replay one GET per host with `Host: evil.example.com`
(`allow_redirects=False`) and flag any response whose `Location` or body contains the evil
host. Run it across the WHOLE live-host list, not just the host you found it on — the same
root cause usually covers a cluster (here: the Wicket "ciss" account cluster + the password
recovery service). Report the full host list in the finding.

## Walls hit

Signup is geo-gated: an Indonesian egress gets redirected to
support.mail.com/info/reject.html ("Your IP address suggests you are trying to sign up in a
country where mail.com registration is no longer possible"). The finding was found entirely
on the unauthenticated surface. Authenticated area (webmail/calendar/storage) untested =
coverage limit, stated as such, not a clean bill.

## Disclosure flow

Report SENT by operator 13:26 UTC (message 1a15d203e948990c). Later sweep expanded the host
list 2 -> 5, so an expanded PDF + a supplement draft (Re:/In-Reply-To on the original
Message-ID, same 3 attachments) were staged; operator decides whether to send it.
