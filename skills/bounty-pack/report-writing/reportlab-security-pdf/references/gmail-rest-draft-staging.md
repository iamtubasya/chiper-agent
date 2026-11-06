# Staging a report draft WITH a PDF attachment via the Gmail REST API

Use this when the machine already has a Google OAuth token (the `google-workspace` skill's
`~/.hermes/google_token.json` + `google_client_secret.json`) but the `gws` / `google_api.py`
wrapper has **no draft subcommand** — it supports `gmail search|get|send|reply|labels|modify`
only. This is the REST path; rule 13 in SKILL.md covers the IMAP path for other setups.

The user's standing rule still governs: **draft only, never send. One finding = one draft = one
email = one PDF.** If you staged a combined draft earlier "to keep it tidy", delete it and stage
one draft per finding.

## Refresh the access token (stdlib only — no google libs needed)

```python
import json, base64, os, urllib.request, urllib.parse
HOME = os.path.expanduser(r"C:\Users\<user>\AppData\Local\hermes")   # HERMES_HOME
TOK = json.load(open(os.path.join(HOME, "google_token.json"), encoding="utf-8"))
data = urllib.parse.urlencode({"client_id": TOK["client_id"], "client_secret": TOK["client_secret"],
        "refresh_token": TOK["refresh_token"], "grant_type": "refresh_token"}).encode()
AT = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data), timeout=20))["access_token"]
```

`scope-has-compose` may read `False` from the token JSON yet draft creation still succeeds — the
scope string in the token file is not authoritative. Do not abort on it; attempt and check the HTTP
status.

## Create the draft (multipart/mixed, attachment from bytes)

```python
from email.message import EmailMessage
m = EmailMessage()
m["To"] = "security@target.com"; m["From"] = "Name <me@gmail.com>"
m["Subject"] = "[Responsible Disclosure] Finding 1 - <title>"
m.set_content(body)                                   # plain text; body must open with an intro
m.add_attachment(open(pdf_path, "rb").read(),
                 maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))
raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
req = urllib.request.Request("https://gmail.googleapis.com/gmail/v1/users/me/drafts",
        data=json.dumps({"message": {"raw": raw}}).encode(),
        headers={"Authorization": f"Bearer {AT}", "Content-Type": "application/json"})
resp = json.load(urllib.request.urlopen(req, timeout=30))     # -> {"id": <draftId>, "message": {"id": <msgId>}}
```

Note the **draft id and the message id differ** — you delete/replace by the *draft* id.

## Read the draft back and verify the ATTACHMENT, not just the body

Two traps, both look like a pass:

- **`?format=full` returns NO `message.raw`** → `KeyError: 'raw'`. Use **`?format=raw`**:
  `https://gmail.googleapis.com/gmail/v1/users/me/drafts/<draftId>?format=raw`.
- `email.message_from_bytes(raw)` returns a `Message`, which has **no `.get_body()`** — walk parts:
  `for part in m.walk(): if part.get_content_type()=="text/plain" and not part.get_filename(): …`.

Then assert, per draft, as a list of `OK/FAIL` (not one aggregate — an aggregate hides which check
failed):

- attachment present, `b[:5] == b"%PDF-"`, and `len(bytes) == os.path.getsize(local_pdf)` (equal
  sizes alone are not enough; the `%PDF-` magic plus hash/size equality catches a stale attachment);
- body landmark phrases: intro phrase, the policy URL, "In short", "attached as a PDF", signature.
  **Collapse whitespace first** — the body is hard-wrapped, so `"a phrase" in body` false-FAILs when
  it straddles a newline: assert on `" ".join(body.split())`;
- English-only scan on the body.

## Replacing / cleaning up

- To supersede a draft, **stage the new one first, then delete the old** (an interrupt between
  delete and append otherwise leaves the folder empty).
- Delete a draft: `DELETE https://gmail.googleapis.com/gmail/v1/users/me/drafts/<draftId>` with the
  Bearer header. Delete the **combined/deprecated draft** this way after splitting into per-finding
  drafts.
- Touch only your OWN drafts; the operator often has their own draft in the same folder.

## Deliverable shape the operator expects

One draft per finding, each carrying its own finding-scoped PDF
(`Target-F1-<slug>-Low.pdf`), English subject + body, an introduction in the body (rule 12), and a
sentence pointing at the attachment. Report the draft ids + attachment byte sizes in the handoff so
the operator can review and press send themselves.
