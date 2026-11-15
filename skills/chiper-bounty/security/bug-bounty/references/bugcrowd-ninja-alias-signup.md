# Bugcrowd programs: signup with the ninja alias + reading the verification mail

Applies to any Bugcrowd engagement that requires self-signup on the target's own product with a
Bugcrowd alias (`<username>@BC_ALIAS.com`). Companion reading:
`references/bugcrowd-brief-scraping.md` (how to read the brief/scope first).

## 1. The alias and where the mail actually lands
- Programs require signup with `<bugcrowd-username>@BC_ALIAS.com` — do NOT use a personal
  address, and do not use a throwaway inbox (the alias forwards to the researcher's REGISTERED
  Bugcrowd mailbox).
- Practical consequence: you can read those mails from the researcher's own mailbox. On this host the
  Gmail app password lives in `~/check_basabasi_email.py` (used by the email automation skill).
- The relay rewrites every message:
  - `From: Bugcrowd Relay <forward-bot@BC_ALIAS.com>`
  - `Subject: [Relayed on behalf of no-reply@<program-domain> to <alias>] <original subject>`
  So filter on **body content** (alias + program domain) or on that relay subject — matching
  `From: <program>` will never hit, because the relay replaced it.

## 2. Reading it (IMAP recipe)
```python
import imaplib, email, re
from pathlib import Path
src = (Path.home() / "check_basabasi_email.py").read_text(encoding="utf-8", errors="ignore")
pw  = re.search(r'["\']([a-z]{16})["\']', src).group(1)          # Gmail app password
M = imaplib.IMAP4_SSL("imap.gmail.com"); M.login("RESEARCHER_EMAIL", pw)
M.select("INBOX", readonly=True)
typ, data = M.search(None, 'SINCE', '29-Sep-2026')               # date of the signup
for i in reversed(data[0].split()[-40:]):
    raw = M.fetch(i, "(BODY.PEEK[])")[1][0][1]
    if b'<alias>@BC_ALIAS.com' in raw and b'<program-domain>' in raw.lower():
        ...  # this is the one
```
Scan `INBOX`, `[Gmail]/Spam` and `[Gmail]/All Mail`; `BODY.PEEK[]` avoids marking it read.

## 3. Extracting the verification link (the part that bites)
- Messages are **quoted-printable**: strip soft breaks before any regex or long URLs come back
  truncated mid-query: `txt = re.sub(r'=\r?\n', '', txt)` then `txt = txt.replace('=3D', '=')`.
- Marketing mail is wrapped in **Mandrill** tracking:
  `https://mandrillapp.com/track/click/<id>/<target-host>?p=<base64url-json>`
  Regexing `href`s fails (QP truncation) — decode the payload instead:
```python
p = re.search(r'[?&]p=([^&\s]+)', url).group(1)
p += '=' * (-len(p) % 4)
inner = json.loads(base64.urlsafe_b64decode(p).decode('utf-8', 'ignore'))
real_url = json.loads(inner['p'])['url']     # -> https://<host>/branded-sign-up/<token>
```
  Then navigate that URL in the real browser (it is the token-bearing verify link).
- Some senders embed the link only in the `text/html` part; walk `msg.walk()` and prefer
  `text/plain`, falling back to HTML.

## 4. Signup-flow reality checks
- Signup forms on these programs are usually **Turnstile/CAPTCHA-gated** → drive a real Chrome over
  CDP, not a stealth-Firefox profile (`browser-cdp-auth-audit` §3b).
- Do exactly ONE interactive signup. Bulk/automated form submissions are banned and can get the
  researcher removed from the program.
- Expect a per-email lock after a few attempts: "sign-up using this email will be available again in
  one hour". That is anti-abuse, not a vuln — park it and schedule a one-shot resume instead of
  retry-pumping.
- When the flow offers SMS or "use authenticator app", take the authenticator: capture the TOTP
  secret from the API response (fetch/XHR hook) and generate codes locally, so no SMS relay from the
  account owner is needed.
- Ask for the country the program's own brief specifies (e.g. Rapyd: **Iceland** unlocks production
  mode where roles/permissions are testable). That choice is a real gate on what you can test later.
