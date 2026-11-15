# Worked case — mail.com Host Header Injection (2026-10-21)

Finding: the mail.com authentication services (United Internet / 1&1 Mail & Media) built absolute
redirect URLs from the untrusted `Host` header and appended live session material to them.
Validated 3x, report SENT by operator to report@bugbounty.mail.com, supplement staged.

## What was proven

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

## Method that found it (reusable)

1. **Sweep EVERY live host, not the two you think are interesting.** After proving it on
   `password.mail.com` and `account.mail.com`, a parallel sweep of all 67 live hosts found three
   more with the same root cause: `ciss.mail.com`, `account-ba.mail.com`, `account-lxa.mail.com`
   (all the Wicket `ciss` cluster). Scope in the report went from 2 endpoints to 5 — that is the
   difference between "a bug" and "the bug class on this estate".
2. **Sweep pattern:** `requests` + ThreadPoolExecutor(15), GET each live host with
   `Host: attacker-controlled.example.com` and `allow_redirects=False`, flag any response whose
   `Location` contains the evil host OR whose first 3 KB of body reflect it. Run it once after the
   first manual confirmation.
3. **Drive the recovery flow in a real browser** (Playwright) before curl-probing — the flow was
   Apache Wicket; the app's own JS revealed the endpoint contract. The API layer
   (`api.fastmail.com`-style trust header `x-trustedclient: Yes` on other targets) may reject
   scripted requests with "Request not from trusted source" — capture the header set from the
   browser and replay it.
4. **Validation battery that must accompany the finding** (each is a separate negative that
   strengthens the report and pre-empts triager questions):
   - **Repeat 3x with 3 different evil domains** — consistent reflection each time.
   - **X-Forwarded-Host / X-Forwarded-Server** — often NOT trusted when Host is (mail.com: XFH
     ignored, redirect stayed on the legit host). State which header is the vector.
   - **Session fixation via URL jsessionid** — Java containers usually mint a fresh session and
     ignore the URL value (mail.com did). Test `;jsessionid=KNOWN` and confirm the Set-Cookie
     differs; document as a negative.
   - **Cache poisoning** — check `CF-Cache-Status`/`Age` on the poisoned redirect; a fresh token
     per request + no cache headers = negative.
   - **Token replay cross-host** — a token minted under the evil Host generally does not load the
     legit flow (302 to a fresh token). Say so; it bounds the impact honestly.

## Impact framing that shipped

Primary: **password-reset link poisoning → account takeover**. The reset email is generated from
the same base URL, so the victim receives a reset link on the attacker's domain, clicks it, and
hands over the reset token. Secondary: session-token (`srttkn`/`jsessionid`) leakage to a
third-party host via the redirect.

Honest boundary that was stated in the PDF: no victim account was used and no reset email was
requested or received — the email-link poisoning is the direct consequence of the demonstrated
URL-generation behaviour, not an observed email.

## Where it does NOT work (defence reference)

- **Adafruit volcano** (Zen Cart admin): same test returned **403 Forbidden** — the host validates
  the Host header. A 403/400 on the poisoned Host is the correct defence; record it and move on.
- **Origin-direct access** does not bypass a server-side geo/abuse check: hitting the origin IP
  directly (bypassing the CDN) still returned `countryCode: ID` on mail.com signup — the
  geolocation is origin-side, not a CDN header. Do not promise "origin bypass" as an impact.

## Reporting notes

- Channel: report@bugbounty.mail.com (per policy page); body per the 0c shape, signed RESEARCHER_NAME
  Susanto, no reward words. mail.com's policy has no AI-disclosure clause and no
  no-severity-claims clause.
- After the operator sent the original report, the expanded 5-host version was staged as a
  **supplement draft** (`Re:` + In-Reply-To/References to the original Message-ID), not an
  in-place update — the original had already left the DRAFT label, and `drafts.update` on a sent
  message fails with "Message not a draft".
