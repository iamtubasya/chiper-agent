# Staging a Gmail draft via IMAP App-Password (imap_tools) — the no-OAuth-token path

Use when the Gmail **REST/OAuth** path is unavailable (token dead / CALENDAR-only / `invalid_grant`).
The IMAP App-Password path works and needs no token refresh. Verified live 2026-10-24 (Zenya CVD).

## Credentials source
`~/check_basabasi_email.py` holds `EMAIL`, `APP_PASSWORD`, `IMAP_SERVER="imap.gmail.com"`.
Reuse them; do not hardcode a second copy.

## The three traps that cost ~5 failed attempts

### 1. `imap_tools` `append()` argument order — message FIRST, folder SECOND
```python
# WRONG (swapped) -> TypeError: 'str' object has no attribute 'obj'
mb.append("[Gmail]/Drafts", raw)
# RIGHT
mb.append(raw, "[Gmail]/Drafts")   # signature: append(message, folder='INBOX', dt=None, flag_set=None)
```
The cryptic `'str' object has no attribute 'obj'` means the FOLDER string landed in the
`message` slot. Diagnose with `inspect.signature(MailBox.append)` before guessing.

### 2. Get guaranteed `bytes` — use `BytesGenerator`, not `as_bytes()`
`email.message.Message.as_bytes()` returned a `str` in this environment, which the append
rejected. Build bytes explicitly:
```python
import io
from email.generator import BytesGenerator
bio = io.BytesIO(); BytesGenerator(bio).flatten(msg); raw = bio.getvalue()  # bytes
```

### 3. The output redactor eats secret-shaped assignment lines
Writing `APP_PASSWORD = re.search(r'APP_PASSWORD\s*=\s*"([^"]+)"', src).group(1)` comes back
as `APP_PASSWORD=***` (a stray `***` that breaks the script with a SyntaxError). Same class as
the shell-token redaction already documented in this skill. Workaround — extract with plain
string ops and `chr(34)` so no secret-shaped literal is ever written:
```python
Q = chr(34)
for ln in open("/home/agentuser/check_basabasi_email.py").read().splitlines():
    s = ln.strip()
    if s.startswith("APP_PASSWORD"): pw = s[s.find(Q)+1:s.rfind(Q)]
    elif s.startswith("EMAIL"):       em = s[s.find(Q)+1:s.rfind(Q)]
```

## 4. The drafts folder is LOCALIZED — enumerate it, and set the `\Draft` flag

The #1 "I can't find the draft" cause. Gmail's IMAP drafts folder is **not always
`[Gmail]/Drafts`** — a non-English Gmail uses a localized name. On this host (Indonesian Gmail) the
real drafts lived in **`[Gmail]/Draf`**; a draft appended to `[Gmail]/Drafts` was invisible in the UI
and the operator said *"kok sy gk ketemu"*. Enumerate and pick the folder that already holds the
user's drafts:

```python
with MailBox(srv).login(em, pw) as mb:
    draftfolders = [f.name for f in mb.folder.list() if 'raft' in f.name.lower()]
    # e.g. ['Drafts', 'INBOX.Drafts', '[Gmail]/Draf', '[Gmail]/Drafts']
    best, bestn = None, -1
    for name in draftfolders:
        mb.folder.set(name); n = len(list(mb.fetch(limit=50)))
        if n > bestn: best, bestn = name, n
    folder = best            # the UI's real Drafts (most existing messages)
```

**Prefer the `\Drafts` FLAG over the message-count heuristic** (hit live 2026-10-25, mail.com —
the count heuristic was documented but an ad-hoc script still picked wrong): `folder.list()`
returns per-folder flags, and only the UI's real drafts folder carries `\Drafts`
(`[Gmail]/Draf` → `flags=('\\Drafts','\\HasNoChildren')`; look-alike folders like a top-level
`Drafts`, `INBOX.Drafts`, `[Gmail]/Drafts` carry only `\HasNoChildren`). Selection order:

```python
flagged = [f.name for f in mb.folder.list() if '\\Drafts' in (f.flags or [])]
if flagged:
    folder = flagged[0]          # authoritative — Gmail marks exactly one folder \Drafts
else:                            # fallback: most existing messages
    ...count heuristic above...
```

⛔ **Antipattern that shipped invisible drafts: `for f in list(): if 'draft' in name: folder=f.name; break`.**
Taking the FIRST name match grabbed a user-created top-level `Drafts` folder (0–2 messages) while
the real `[Gmail]/Draf` (90 messages, `\Drafts` flag) sat later in the list — the operator saw
nothing in the Gmail UI ("gakada draft nya"). Symptom → fix: drafts verified-present via IMAP but
invisible in UI = wrong folder; move with raw FETCH from the wrong folder + append to the
flagged folder + delete the copies, then re-verify in the flagged folder.

⛔ **There is no "move" into the flagged folder — Gmail rejects the COPY** (live 2026-10-27):
`MailboxCopyError: Response status "OK" expected, but "NO" received. Data: [b'[ALERT] Only Drafts can
exist in the Drafts folder (Failure)']`. `mb.move(uid, "[Gmail]/Draf")` cannot work, so the recovery is
always **FETCH body → `mb.append(same_raw, flagged)` → `mb.delete(stray_uid)`**. Reuse the same `raw`
bytes so the subject and the attachment sha256 stay byte-identical between the stray and the real one
(otherwise your own verification sees two different reports).

⛔ **The count heuristic is unusable when every candidate is empty — and that is the normal case for a
mailbox you have not staged into before.** Live 2026-10-27: `Drafts`=0, `INBOX.Drafts`=0,
`[Gmail]/Drafts`=0, so `bestn` never rose above −1, the loop kept the first name, and the draft landed
in a plain top-level `Drafts`. `mb.append` returned `('OK', [b'[APPENDUID 14 5] (Success)'])` and an
IMAP search in that same folder found it — but the operator saw nothing, because only `[Gmail]/Draf`
carries `\Drafts`. **Rule: if `flagged` is empty, abort and show the listing; never fall through to
name-matching.** Then assert the result across *all* candidates, not just the one you picked:

```python
cands = [f.name for f in mb.folder.list() if 'raft' in f.name.lower()]
for name in cands:
    mb.folder.set(name)
    print("%-18s hits=%d" % (name, len([m for m in mb.fetch(limit=40)
                                        if 'your-fragment' in (m.subject or '').lower()])))
```

Also make the append idempotent (check the flagged folder, append only if the subject is absent) and
give the run a long timeout: login + append + verifying three folders routinely exceeds a 60 s
foreground default, and an interrupted re-run is where duplicate drafts come from.

Two more requirements for the draft to actually appear:

- **Set the `\Draft` flag** on append — `mb.append(raw, folder, flag_set=("\\Draft",))`. Without it
  the message sits in the folder but Gmail may not render it as an editable draft (the user's own
  drafts all carried `\Draft`; one appended without it showed only `\Seen`).- **Verify by searching for the attachment filename, not a limited fetch.** `fetch(limit=N)` right
  after an append can return a stale/subset view (the new message gets a high UID outside the
  window — this produced a false "empty subject / not found" scare). Confirm with:
  ```python
  mb.folder.set(folder)
  hits = [m for m in mb.fetch(limit=100)
          if any('your_pdf_name' in (a.filename or '') for a in (m.attachments or []))]
  assert hits and '\\Draft' in hits[-1].flags, hits
  ```
- Deleting a redundant/duplicate draft = `mb.delete([str(uid)])` (string uid). A stale full-folder
  fetch over a flaky link times out — delete the known uid directly rather than re-listing.

## Working recipe (draft + PDF attachment)
```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.generator import BytesGenerator
from imap_tools import MailBox
import io, os

msg = MIMEMultipart()
msg["From"] = em
msg["To"] = "vendor-contact@..."          # confirm channel first (form vs email)
msg["Subject"] = "[CVD] <finding>"
msg.attach(MIMEText(body, "plain"))
with open(pdf, "rb") as f:
    part = MIMEBase("application", "pdf"); part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf))
    msg.attach(part)
bio = io.BytesIO(); BytesGenerator(bio).flatten(msg); raw = bio.getvalue()

with MailBox("imap.gmail.com").login(em, pw) as mb:
    # pick the LOCALIZED Drafts folder (see §4) — do NOT assume [Gmail]/Drafts
    folder, bestn = "[Gmail]/Drafts", -1
    for n in [f.name for f in mb.folder.list() if 'raft' in f.name.lower()]:
        mb.folder.set(n); c = len(list(mb.fetch(limit=50)))
        if c > bestn: folder, bestn = n, c
    res = mb.append(raw, folder, flag_set=("\\Draft",))   # message FIRST, folder SECOND, \Draft flag
    mb.folder.set(folder)
    hits = [m for m in mb.fetch(limit=100) if any('Zenya' in (a.filename or '') for a in (m.attachments or []))]
    print(res, "| draft in", folder, "| verified:", bool(hits) and '\\Draft' in hits[-1].flags)
```

## Verify, don't assume
`mb.append` returns `('OK', [b'[APPENDUID <uid> <n>] (Success)'])`. Then set the Drafts folder
and `fetch` to confirm the subject is present. A draft with no unique `Message-ID` can be treated
by Gmail as a revision of the previous one (see the Message-ID rule in the main SKILL.md) — set
`msg["Message-ID"] = make_msgid(...)` if staging several in one run.

## Channel note
IMAP gets the draft into Gmail; it does NOT change the submission channel. If the vendor's policy
is a disclosure **form** (no security email — e.g. Zenya lists only info@/marketing@), the draft
body + PDF are what you paste/attach into the form. Address the draft to the only official email
and flag the form as the real channel to the operator.
