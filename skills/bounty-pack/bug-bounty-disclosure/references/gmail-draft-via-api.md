# Create a Gmail DRAFT programmatically (raw API — when the wrapper has no `draft`)

`google_api.py` (google-workspace skill) exposes gmail `search|get|send|reply|labels|modify` — it has
**no `draft` subcommand**. To place a ready-to-review draft (NOT sent) in the operator's Gmail, call the
Gmail REST API directly with the same OAuth token the wrapper already uses. Stdlib only — no google libs.

```python
import json, base64, urllib.request, urllib.parse, os
HOME = os.path.expanduser(r"%LOCALAPPDATA%\hermes")          # = HERMES_HOME
tok  = json.load(open(os.path.join(HOME, "google_token.json"), encoding="utf-8"))

# 1) refresh an access token from the stored refresh_token (no browser, no re-auth)
data = urllib.parse.urlencode({**{k: tok[k] for k in ("client_id","client_secret","refresh_token")},
                               "grant_type": "refresh_token"}).encode()
at = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data), timeout=20))["access_token"]

# 2) build raw RFC822 (CRLF headers) and base64url-encode the whole thing
msg = ("To: security@target\r\n"
       "Subject: [Responsible Disclosure] <one-line issue>\r\n"
       "Content-Type: text/plain; charset=UTF-8\r\nMIME-Version: 1.0\r\n\r\n" + body)
raw = base64.urlsafe_b64encode(msg.encode()).decode()

# 3) create the draft
req = urllib.request.Request(
    "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
    data=json.dumps({"message": {"raw": raw}}).encode(),
    headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req, timeout=25)))    # -> {"id": ..., "message": {"id": ...}}
```

Verify it landed (don't claim "draft siap" without this):
`google_api.py gmail search "in:draft subject:Responsible Disclosure"`

## Notes / pitfalls
- Headers **must** use CRLF (`\r\n`); base64**urlsafe** (not standard b64) — Gmail rejects the wrong alphabet.
- Scope: `gmail.compose` is enough to create a draft; the google-workspace setup token normally has it.
  If the draft POST 403s, print `"gmail.compose" in tok["scope"]` / `"mail.google.com" in tok["scope"]`.
- **Draft, never send.** The operator reviews and hits Send. Auto-sending a disclosure is not your call.
- Vendor asks for an evidence bundle → attach the PDF via `multipart/mixed` (base64url each part).
- The `google-workspace` skill itself is bundled/protected — do not edit it; this recipe lives here.

## Two verified traps when the draft carries an attachment

Hit live 2026-10 staging four per-finding drafts. Both cost a false conclusion, and both are
cheap to avoid.

### 1. `format=full` does NOT inline an attachment — it returns `attachmentId`

A verification walk that only counts parts carrying `body.data` will report **"no attachments"**
for a perfectly good draft, and you will re-stage or "fix" something that was never broken:

```
draft <id>
  multipart/mixed
    text/plain        size=6828   hasData=True
    application/pdf   size=9482   hasData=False   attachmentId=ANGjdJ9SIGW8dEXaiz6hLZQC   <-- the attachment
```

So assert on **`filename` + `body.size` + `mimeType`**, not on `body.data`. To prove the bytes
survived, fetch them and compare hashes against the local file — that is the only check that
actually proves the operator will get your PDF:

```python
att  = api(at, f"messages/{msg_id}/attachments/{part['body']['attachmentId']}")
blob = base64.urlsafe_b64decode(att["data"] + "==")
assert hashlib.sha256(blob).hexdigest() == hashlib.sha256(open(local_pdf,"rb").read()).hexdigest()
```

### 2. One draft per subject — count it, do not trust the POST

Creating four drafts in one run produced the right result, but the *verification* is what proves it:
search per finding and assert **exactly one** hit each, because a re-run (or an earlier staging
attempt) silently leaves twins that the operator then has to disambiguate:

```python
for frag in ("Builder identity can be registered", "Session-relay webhooks",
             "Data Gateway serves repository files", "app.vana.com exposes internal"):
    lst = api(at, "drafts?maxResults=10&q=" + urllib.parse.quote(f'subject:"{frag}"'))
    assert len(lst.get("drafts", [])) == 1, f"expect 1 draft, got {len(lst.get('drafts', []))}"
```

Pick the fragment from the **finding title**, not from the subject prefix (`[Medium]` / `[Low]`
match everything). And when you later stage *more* drafts, keep the earlier findings' bodies in a
separate staging script — re-running the original script re-creates drafts that already exist.

Working MIME construction for the attachment (no hand-rolled base64url parts needed):

```python
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
m = EmailMessage()
m["To"] = TO; m["From"] = FROM; m["Subject"] = SUBJECT
m["Message-ID"] = make_msgid(domain="<engagement>.local")   # required, see the SKILL.md trap
m["Date"] = formatdate(localtime=True)
m.set_content(body)                                        # plain-text disclosure body
with open(pdf, "rb") as fh:
    m.add_attachment(fh.read(), maintype="application", subtype="pdf", filename=pdf.name)
raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
```

Scope note: a token with `gmail.modify` (the usual google-workspace set) can create drafts, so you
do not need `gmail.compose` specifically — check `t.get("scopes")` (the list key) rather than
`t.get("scope")` (absent on this install).

## Adding attachments to an EXISTING draft — `drafts.update` multipart returns 400

Hit live 2026-10-17 (CoderPad): a draft created thin (raw, no attachments), then updated with
`PUT users/me/drafts/<id>` carrying `Content-Type: multipart/related` (part 1 = JSON metadata with
`payload.headers/body`, parts 2+ = base64 attachment parts). Gmail answers **400 Bad Request** —
that stitching format is not accepted for drafts.update.

**What works: build the COMPLETE RFC822 `multipart/mixed` message yourself and PUT it as
`{"message": {"raw": ...}}`.** No API-side stitching at all:

```python
def build_mime(subject, body, files_mimes):          # files_mimes = [(path, mime), ...]
    b = "cpbound2026"
    lines = [f"To: {TO}", f"Subject: {subject}", "MIME-Version: 1.0",
             f'Content-Type: multipart/mixed; boundary="{b}"', "",
             f"--{b}", 'Content-Type: text/plain; charset="UTF-8"', "", body]
    for path, mime in files_mimes:
        fn = os.path.basename(path)
        data = base64.b64encode(open(path, "rb").read()).decode()   # STANDARD b64 inside MIME
        lines += [f"--{b}", f'Content-Type: {mime}; name="{fn}"',
                  "Content-Transfer-Encoding: base64",
                  f'Content-Disposition: attachment; filename="{fn}"', ""]
        lines += [data[i:i+76] for i in range(0, len(data), 76)]    # 76-char lines
    lines.append(f"--{b}--")
    return "\r\n".join(lines).encode("utf-8")

payload = {"message": {"raw": base64.urlsafe_b64encode(mime).decode()}}
api("PUT", f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{did}", json.dumps(payload))
```

Verify by re-fetching the draft (`format=full`) and asserting the attachment list
(filenames + `body.size` + mimeType — remember `format=full` gives `attachmentId`, not `data`).

## Correcting a staged draft in place (same ID, new evidence)

When later verification invalidates a staged draft's claims (2026-10-17: deepening killed the
DoS/CSRF impact claims after the drafts were staged), **update the SAME draft via the raw-MIME PUT
above** — do not leave overstated claims sitting in a draft the operator may send, and do not
create a twin. Body rules for the correction: remove every claim the new evidence does not support,
state the verified behaviour + "impact not demonstrated" explicitly, and add whatever the deeper
testing proved (e.g. cookie-auth rejected → CSRF chain broken). Then tell the operator plainly:
drafts are unsent, here is what changed, here is my send/don't-send recommendation.
