# Host Header Injection — hunting methodology (worked: mail.com 2026-10, defended: Adafruit volcano 2026-10)

A repeatable bug class across web2 targets: the app builds **absolute URLs** (redirect `Location`, password-reset
email links, form actions) from the untrusted `Host` header. Pays on programmes whose scope includes
"authentication systems" — the classic payout path is **password-reset link poisoning → account takeover**.

## 1. Probe shape (single request, no auth needed)

```bash
curl -s -D - -o /dev/null 'https://<host>/<auth-path>' \
  -H 'Host: attacker-controlled.example.com' -A 'Mozilla/5.0'
```

Look at the `Location` header of the 302 — if it echoes your host, the finding is live.

## 2. Sweep EVERY live host (the scope is rarely one endpoint)

httpx the subdomains first, then fire the poisoned-Host probe at all of them in parallel and grep both
the `Location` header and the first ~3 KB of the body:

```python
# parallel over live hosts
r = requests.get(u, headers={**UA, "Host": EVIL}, timeout=10, verify=False, allow_redirects=False)
if EVIL in r.headers.get("location","") or EVIL in r.text[:3000]: report(u, r.status_code, r.headers.get("location",""))
```

Worked result (mail.com): 5 hosts shared the root cause — `password.mail.com/passwordrecovery/`
(leaked `?srttkn=<uuid>`), `account.mail.com`, `ciss.mail.com`, `account-ba.mail.com`,
`account-lxa.mail.com` (all leaked `/ciss/login;jsessionid=<32-hex>`). Report the full host list, not
just the first endpoint found.

## 3. Impact taxonomy (state the proved part and the inference separately)

- **Proved:** server generates attacker-controlled absolute URLs in the auth flow; live session
  material appended to the poisoned URL (`srttkn` recovery token, `jsessionid` Java session id).
- **Inference (label it):** any email built from the same base URL (password reset) delivers an
  attacker-domain link → victim clicks → token harvested → ATO. Do NOT claim an observed reset email
  unless you actually received one.
- **Token leak via redirect:** a victim whose browser follows the poisoned redirect hands the token to
  the attacker's host in the URL (visible in server logs / referrer).

## 4. Negative controls that strengthen the report (run all, document each)

| Control | Expected if hardened | mail.com result |
|---|---|---|
| `X-Forwarded-Host: evil` | ignored, redirect stays on legit host | negative (only `Host` trusted) |
| URL-supplied `;jsessionid=` fixation | container mints a fresh session id, ignores URL value | negative |
| Cache poisoning of the poisoned redirect | no `CF-Cache-Status`, fresh token per request | negative |
| `TRACE` | ideally 405 | enabled but header-reflection only (informational) |

Counter-example worth remembering: Adafruit's `volcano.adafruit.com` (Zen Cart admin) answered the
poisoned-Host request with **403** — host-validating edge. A 403 there is a defence, not a finding.

## 5. Severity / scope framing

- Map to the programme's own words (mail.com scope: "web applications within the authenticated area …
  including the authentication systems"). Medium is honest for a reset-poisoning ATO path with no
  severity scale published.
- Remediation section: server-side hostname allowlist for absolute URL generation; reject/normalise
  unknown `Host` values; bind recovery/session tokens to the issuing host.

## 6. Report mechanics reminders for this class

- PoC = two verbatim curl transcripts (recovery endpoint + account endpoint), 3× reproduced with
  different attacker domains, plus the all-host sweep output.
- Live screenshot: render the REAL captured responses (same-session requests with the poisoned Host)
  into a page and screenshot it — never fabricate values.
- sha256 the PoC script, raw output, and PNG; the draft carries PDF + evidence txt + PNG.
