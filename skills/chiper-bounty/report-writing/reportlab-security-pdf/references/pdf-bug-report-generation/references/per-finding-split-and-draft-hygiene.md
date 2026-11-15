# Per-finding split + Gmail draft hygiene (verified live, 2026-10)

Session: an unpaid responsible-disclosure engagement where two unrelated findings landed on the same
target and therefore the same vendor mailbox (`ciso@<vendor>`). Everything below was hit for real
while staging two PDFs as two drafts.

## 1. The split decision (operator rule: 1 finding = 1 report)

The operator's wording: *"pastikan 1 temuan 1 laporan, gabung hanya kalau itu chain attack"*.

Do NOT merge just because the same mailbox receives both, or because they share a target, a session,
or a report-day. Run these two questions instead:

| Question | Same root cause | Chain attack |
|---|---|---|
| Does fixing item A also fix item B? | yes | no |
| Can item A be used to reach / amplify item B? | n/a | yes |
| Verdict | ONE report | separate reports (or one chain write-up) |

Worked example from the session:
- **Finding A** — an untrusted `X-Forwarded-For` value reflected into `Set-Cookie` on two hosts, and
  the same header used to mint the session token on 16 sibling hosts. Same construct, same fix
  (server-observed IP, validated) → **one report**, breadth stated as a section inside it.
- **Finding B** — reflected XSS in a legacy framework's 500 error page on an unrelated endpoint of
  the same target. Different root cause, different fix, and neither could reach the other → **its own
  report**, own subject, own PDF, even though both go to `ciso@`.

## 2. Severity honesty when the split looks lopsided

The session's first conclusion was "Low only"; a later deep-dive pass found the Medium XSS. Say so
plainly in the engagement log and in the reply to the operator ("the previous 'Low-only' conclusion is
withdrawn"). Do not quietly upgrade a report after sending — re-stage, delete the superseded draft,
and tell the operator which artefact changed.

## 3. Gmail draft staging — the Message-ID trap

`EmailMessage()` does not emit a `Message-ID`. Gmail's IMAP `APPEND` to `[Gmail]/Draf` with the
`\Draft` flag treats a message with no `Message-ID` as a **revision of the previously appended
draft**, so staging report B silently removed report A:

```
append report A -> APPENDUID 6 1089
append report B -> APPENDUID 6 1117
SUBJECT 'bits.orf.at' -> 0 hits      <-- report A is gone
```

Fix, and re-stage BOTH in one run:

```python
from email.message import EmailMessage
from email.utils import make_msgid, formatdate

msg = EmailMessage()
msg["From"] = EMAIL
msg["To"]   = VENDOR_SECURITY_MAILBOX
msg["Subject"] = SUBJECT
msg["Message-ID"] = make_msgid(domain="engagement.local")
msg["Date"] = formatdate(localtime=True)
msg.set_content(BODY_ENGLISH)
with open(PDF, "rb") as fh:
    msg.add_attachment(fh.read(), maintype="application", subtype="pdf",
                       filename=os.path.basename(PDF))
box.append(msg.as_bytes(), folder="[Gmail]/Draf", flag_set="\\Draft")
```

Then delete the superseded duplicate (the one **without** a `Message-ID`) in the same run, and assert
one draft per subject.

## 4. Verification that actually finds the draft

`box.fetch(reverse=True, limit=N)` is positional and silently under-returns once the folder grows —
with a 31-message draft folder, `limit=60` returned 30 messages and missed the target entirely, while
an IMAP `SUBJECT` search found it immediately. Use `imaplib` and `BODY.PEEK` so the check does not
mutate the draft:

```python
import imaplib
M = imaplib.IMAP4_SSL("imap.gmail.com"); M.login(EMAIL, PW)
print([b.decode() for b in M.list()[1] if b"Draf" in b])   # confirm the folder name per locale
M.select('"[Gmail]/Draf"')
for frag in ("pipe.orf.at", "bits.orf.at"):
    print(frag, M.search(None, 'SUBJECT', '"%s"' % frag)[1][0].split())   # expect one id each
M.fetch(ids[0], '(BODY.PEEK[HEADER.FIELDS (SUBJECT TO MESSAGE-ID)])')
M.select('"[Gmail]/Draf"'); M.store(dup_id, '+FLAGS', '\\Deleted'); M.expunge()
```

Notes:
- The Draft folder is locale-localised — Indonesian profile gives `[Gmail]/Draf`, not `[Gmail]/Drafts`.
  Always resolve it from `M.list()` rather than hardcoding.
- `imap_tools.fetch()` defaults to `mark_seen=True`; on a draft folder that is an unwanted side effect.
- After cleanup assert the totals: one draft per subject, and the folder count moves by exactly the
  net number of appends minus deletions (31 → 32 after re-staging both, 31 again after deleting the
  Message-ID-less duplicate).

## 5. Form-based programs: no mailbox exists, draft with To: unset

Some programs publish a **submission form** instead of a security mailbox (Cloudsmith: security.txt
`Contact:` is `https://www.<vendor>/vulnerability-disclosure/submit-vulnerability`). Do NOT invent a
recipient. Stage the draft with **`To:` unset**, put the submission URL in the body's intro
("Submission channel per your security.txt: <url>"), and tell the operator the draft is the
copy-paste source for the form — they submit manually. The verification assertions are unchanged:
one draft per subject, attachment filename/size, sha256(decoded attachment) == local PDF.

## 6. Gmail OAuth token expires hourly — refresh before every staging/verify run

The REST-API staging path (`POST /gmail/v1/users/me/drafts`) needs a fresh access token; the token
at `%LOCALAPPDATA%\hermes\google_token.json` lives ~1 hour. A staging run that worked earlier in
the day fails with bare `401 Unauthorized` later. Refresh first, every run:

```python
info = json.load(open(TOK))
r = urllib.request.Request("https://oauth2.googleapis.com/token",
    data=json.dumps({"client_id": info["client_id"], "client_secret": info["client_secret"],
                     "refresh_token": info["refresh_token"], "grant_type": "refresh_token"}).encode(),
    method="POST", headers={"Content-Type": "application/json"})
tok = json.loads(urllib.request.urlopen(r, timeout=30).read())
info["token"] = tok["access_token"]; json.dump(info, open(TOK, "w"))   # persist rotated refresh_token too
```

Also: the `drafts?q=subject:"..."` verification query needs URL-encoding — a raw space in the query
string raises `InvalidURL: URL can't contain control characters` AFTER the draft was already staged
(use `urllib.parse.quote`). And a `401` mid-verification means the token expired between staging and
verify, not that the draft is missing — refresh, re-verify.

## 7. Kept scripts (re-runnable shape)

Keep all three next to the PDFs so the whole chain is reproducible from disk:
`gen_<finding>_report.py` (constants → PDF), `stage_both_drafts.py` (unique Message-ID per report,
appends both), `verify_drafts.py` (IMAP SUBJECT search + attachment filename/size/content-type assert).
State the absolute paths in the reply — the CLI has no attachment channel.
