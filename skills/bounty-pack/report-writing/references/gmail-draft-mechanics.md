# Delivering a report as a Gmail draft (this host, verified 2026-10-28)

Mechanics that actually work when the API path is unavailable. Saves the 4 failed attempts it took to
rediscover them.

## Preferred path — Gmail API

`~/AppData/Local/hermes/google_token.json` holds `gmail.modify` + `gmail.send` and a `refresh_token`.
Check liveness **first**, in one call:

```python
import json, os, requests
t = json.load(open(os.path.expanduser("~/AppData/Local/hermes/google_token.json")))
r = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/profile",
                 headers={"Authorization": "Bearer " + t["token"]}, timeout=20)
print(r.status_code)     # 401 -> try the refresh grant below
```

If the stored access token is expired, refresh it:

```python
requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": t["client_id"], "client_secret": t["client_secret"],
    "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
```

`{"error":"invalid_grant", "Token has been expired or revoked"}` means the API path is dead for this
session — **do not** keep retrying it. Fall back to IMAP.

## Fallback — IMAP APPEND with a Gmail app password

The app password is already on disk. Recover it the same way the helper script does:

```python
import re, imaplib, time
from email.message import EmailMessage
src = open(r"C:\Users\WINDOWS10\check_basabasi_email.py", encoding="utf-8", errors="replace").read()
APP = (re.search(r"APP_PASSWORD\s*=\s*re\.\w+\([^,]+,\s*['\"]([^'\"]+)['\"]", src)
       or re.search(r"APP_PASSWORD\s*=\s*['\"]([^'\"]+)['\"]", src)).group(1)

msg = EmailMessage()
msg["From"] = "RESEARCHER_EMAIL"; msg["To"] = "<vendor>"
msg["Subject"] = "<subject>"
msg.set_content(body)
with open(pdf, "rb") as f:
    msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=name)

M = imaplib.IMAP4_SSL("imap.gmail.com"); M.login("RESEARCHER_EMAIL", APP)
M.append("[Gmail]/Draf", "\\Draft", imaplib.Time2Internaldate(time.time()),
         msg.as_bytes().replace(b"\n", b"\r\n"))
```

### ⛔ The folder name trap — this cost a draft that Gmail would never show

`M.list()` on this account returns **both** of these:

```
(\HasNoChildren) "/" "Drafts"            <- a stray LOCAL folder, NOT Gmail's draft label
(\Drafts \HasNoChildren) "/" "[Gmail]/Draf"   <- the real one (account locale = Indonesian)
```

Appending to `Drafts` reports `OK [APPENDUID ...] (Success)` and the message is **invisible in the
Gmail UI**. Always pick the folder carrying the `\Drafts` attribute — parse the flags, do not match the
substring "Draft":

```python
for d in M.list()[1]:
    line = d.decode(errors="replace")
    if "\\Drafts" in line:                      # attribute, not name
        target = re.search(r'"([^"]*)"\s*$', line).group(1)
```

Also: `[Gmail]/Draf` and `[Gmail]/Drafts` are distinct entries here. Selecting the wrong one shows
`count 0` and reads as "the append failed" when it landed elsewhere.

### Verify the draft really carries the attachment(s)

A successful APPEND does not prove the MIME structure survived. Fetch the structure and count parts:

```python
M.select(target)
t, ids = M.search(None, 'SUBJECT', '"<distinct subject fragment>"')
t, d = M.fetch(ids[-1], "(RFC822.SIZE BODYSTRUCTURE)")
s = d[0][1].decode(errors="replace") if isinstance(d[0], tuple) else str(d[0])
print(re.findall(r"RFC822.SIZE (\d+)", s),
      s.count('"PDF"'),
      re.findall(r'"FILENAME" "([^"]+)"', s))
```

Expect `SIZE`, `PDF` count equal to the number of attachments, and the exact filenames. Note: fetching
`(BODY.PEEK[HEADER.FIELDS (TO SUBJECT)])` alone gives **no** BODYSTRUCTURE — a `"PDFs attached: 0"`
from that fetch is an artefact of the fetch, not a missing attachment. Ask for `BODYSTRUCTURE`
explicitly.

## Housekeeping

- **One submission, not two.** When an addendum supersedes an earlier draft, delete the earlier one in
  the same run (`STORE +FLAGS \Deleted` then `EXPUNGE`) so triage cannot action a stale copy. The new
  APPEND may reuse the same UID — re-check the **subject**, not the UID, to confirm which draft you are
  looking at.
- **Never send without an explicit instruction.** Default is draft-only.
- Long bodies: `msg.set_content(body)` produces quoted-printable automatically; do not hand-mangle
  encoding. The `\n` → `\r\n` conversion before APPEND is required for a well-formed message.
