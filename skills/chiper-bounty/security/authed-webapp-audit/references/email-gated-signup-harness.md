# Email-gated signup harness — minting your own test accounts non-interactively

Many SaaS targets gate signup (and every subsequent login) behind an emailed 6-digit code.
Driving that by hand in a browser is the bottleneck for multi-account work: BOLA/IDOR proof
and business-logic tests need **2+ accounts you control, created on demand, repeatedly** —
including after a lockout or a session expiry.

Solve it once with a small client class. Built and used on an ASP.NET MVC + React SPA portal
with an Azure-Front-Door API edge; the shape generalises.

## Flow (OTP-gated signup)

```
GET  /Account/Register              -> scrape __RequestVerificationToken (regex on the form)
POST /Account/Register              -> 302 /Account/ConfirmEmail?sentTo=...   (password is set HERE)
GET  /Account/Login                 -> fresh token
POST /Account/Login                 -> 302 /Account/VerifyLogin (or /ConfirmEmail) = the code gate
GET  the code gate page             -> fresh token
      (poll IMAP for the newest code addressed to this mailbox)
POST the code gate                  -> 302 to the app = authenticated
      -> persist the cookie jar (Netscape) so curl / scanners / other scripts reuse the session
```

Keep two artefacts per account: `recon/session_cookie_header_<X>.txt` (cookie jar) and a small
`account_<X>.json` with email / password / object ids you created. Later phases reload from disk
instead of re-authenticating.

## Pitfalls that cost real time

- **Anti-forgery token is per page.** Re-GET before each POST and re-scrape. Anonymous tokens
  often survive reuse, but re-fetching removes a whole class of "why did that 200 instead of 302".
- **Sub-address tags must be alphanumeric.** Gmail `+tag` subaddressing works, but a tag with an
  underscore (`+otp1_595`) produced a register POST that returned the page with **no account
  created** and no error. Downstream every step then failed with a misleading "no code gate".
  Use `+otp1x30661` style tags.
- **Assert on the redirect, not on the status.** `register()` must fail loudly unless
  `Location` contains `/ConfirmEmail`. Registration is itself rate-limited: after ~4 signups from
  one IP it returns `200` (page re-render) instead of `302`. Without the assert you spend the next
  ten minutes debugging a phantom login failure.
- **Mailbox credentials can be redacted in your own tool output.** Reading the helper file may
  show `APP_PASSWORD="***"`. Do not try to copy the value by hand — have the helper parse
  `EMAIL` / `APP_PASSWORD` out of the source file at runtime and never print them; pipe only the
  extracted code and subject.
- **Poll with a time floor.** `since_ts = login_time - 600` plus a ~6 s retry loop; match on sender
  AND recipient sub-address, otherwise you grab another account's code.
- **Bearer/session tokens may be opaque, not JWT.** A 576-char base64url blob that does not split
  on `.` is encrypted — do not burn time decoding it. Keep the cookie jar and move on.
- **Session TTL is short (~1 h observed).** Order the engagement: authenticated + API work first,
  auth-abuse tests last, and re-mint from disk when a jar expires.
- **`requests` cookie domain matters.** A cookie scoped to `.example.com` must be set with
  `domain="example.com"` (or loaded from a Netscape jar) or it is not sent to `api.example.com`.

## Windows / git-bash path trap

MSYS rewrites arguments that look like POSIX paths.
- `--path /subscription` becomes `C:/Program Files/Git/subscription` → use `MSYS_NO_PATHCONV=1`
  for **URL-path** arguments.
- But that same env var keeps a literal `/c/Users/...` intact, so Python's `Path("/c/Users/...")`
  resolves to `C:\c\Users\...` — a different, empty tree. For **filesystem** arguments
  (`--target-dir`, `-o`) always pass the native `/home/agentuser` form.
  Verify by listing both before trusting a run.

## Compact skeleton

```python
import re, time, requests
T = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')

class App:
    def __init__(self, base, api, email, password):
        self.base, self.api, self.email, self.password = base, api, email, password
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA})

    def _tok(self, html):
        m = T.search(html or "")
        return m.group(1) if m else None

    def register(self):
        t = self._tok(self.s.get(self.base + "/Account/Register", timeout=45).text)
        r = self.s.post(self.base + "/Account/Register",
                        data={"__RequestVerificationToken": t, "FirstName": "Aud",
                              "Email": self.email, "Password": self.password, "terms": "on"},
                        allow_redirects=False, timeout=45)
        assert "/ConfirmEmail" in r.headers.get("Location", ""), f"register failed: {r.status_code}"
        return r

    def login(self):
        t = self._tok(self.s.get(self.base + "/Account/Login", timeout=45).text)
        return self.s.post(self.base + "/Account/Login",
                           data={"__RequestVerificationToken": t,
                                 "Email": self.email, "Password": self.password},
                           allow_redirects=False, timeout=45)

    def submit_code(self, gate_path, code):
        t = self._tok(self.s.get(self.base + gate_path, timeout=45).text)
        return self.s.post(self.base + gate_path,
                           data={"__RequestVerificationToken": t, "TwoFactorCode": code},
                           allow_redirects=False, timeout=45)

    def dump_jar(self, path):
        lines = ["# Netscape HTTP Cookie File"]
        for c in self.s.cookies:
            lines.append("\t".join([c.domain, "TRUE" if c.domain.startswith(".") else "FALSE",
                                    c.path, "TRUE" if c.secure else "FALSE", "0", c.name, c.value]))
        open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
```

IMAP side (credentials parsed from the existing mail helper, never printed):

```python
from imap_tools import MailBox, AND
def newest_code(email, pw, to_addr, since_ts, wait=150):
    end = time.time() + wait
    while time.time() < end:
        with MailBox("imap.gmail.com").login(email, pw) as mb:
            for m in mb.fetch(AND(from_="noreply@<target>"), reverse=True, limit=25):
                if to_addr.lower() not in " ".join(m.to or []).lower():
                    continue
                if m.date and m.date.timestamp() < since_ts - 30:
                    continue
                hit = re.search(r"\b(\d{6})\b", m.text or "") or re.search(r">(\d{6})<", m.html or "")
                if hit:
                    return hit.group(1)
        time.sleep(6)
```

## Two-account BOLA protocol (and its triage rule)

1. Mint account A and account B (separate jars).
2. Create one object on B **through the API** (`POST /properties` → capture the returned id);
   add a second-level object if the domain has one (`POST /leases` with `propertyId`, etc.).
   Without a real record on B, "A cannot see B's data" is untestable — empty results prove nothing.
3. From A, try every filter form against B's ids:
   `?PropertyId=`, `?propertyId=`, `/{id}`, and the sub-resources
   (`/{id}/notes`, `/{id}/documents`, `/{id}/reminders`).
4. **Triage rule — status-code inconsistency is not broken authorization.** Observed: A got
   `200 {"data":[]}` on `/payments?PropertyId=<B>` and `/leases?PropertyId=<B>` while identical
   sibling endpoints returned `403`. With a real lease on B, A **never** received B's rows through
   any form. That is a *response-code inconsistency*, not a data leak — not a reportable finding.
   Only report if the body actually contains the other tenant's object.
5. Record the negative clearly ("scoping enforced; only the status code differs") — a withdrawn
   candidate is worth more than an overstated one.
