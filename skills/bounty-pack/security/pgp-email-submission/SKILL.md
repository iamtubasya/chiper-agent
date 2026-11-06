---
name: pgp-email-submission
description: Send bug-bounty reports by email, PGP-encrypted when the program asks for it. Discovers the key from security.txt, encrypts body+PDF, verifies delivery. Use for ANY vendor whose policy mentions PGP.
version: 1.0.0
author: RESEARCHER_NAME
metadata:
  hermes:
    tags: [security, disclosure, pgp, email, submission]
    related_skills: [bug-bounty-disclosure, report-writing, disclosure-contact-discovery]
---

# PGP email submission

Vendor policy says "encrypt with our PGP key" / "PGP encouraged" → send **encrypted**, don't ask.
Tool in this skill: `scripts/pgp_submit.py` (self-contained, run it directly — copy it anywhere).
Tested 2026-10-25 against Proton (`security@proton.me`, fpr `C4BC9337CC23A0BA855A3EF32EE753BBBA66EE76`),
round-trip verified byte-identical.

```bash
python scripts/pgp_submit.py discover --target proton.me
python scripts/pgp_submit.py send --to security@proton.me --subject "[Bug report] <title>" \
       --body body.txt --attach report.pdf --target proton.me --record send-record.json
# --no-pgp when the program does NOT ask for PGP;  --dry-run prints the resolved key fpr only
```

## 1. Discover before sending (never guess the address)

```bash
python ~/AppData/Local/hermes/scripts/pgp_submit.py discover --target proton.me
```
Prints `contact`, `encryption` (key URL), `policy`, and `pgp_asked: true|false`.
- `pgp_asked: true` → send encrypted (default behaviour of `send`).
- `pgp_asked: false` → plaintext is correct; `--no-pgp`.
- No security.txt at all → check the program page manually; do **not** invent an address or key.

Manual fallback (two URLs, both authoritative):
- `https://<domain>/.well-known/security.txt`
- `https://api.protonmail.ch/pks/lookup?op=get&search=security@proton.me` (Proton-style PKS)

## 2. Send

```bash
python ~/AppData/Local/hermes/scripts/pgp_submit.py send \
  --to security@proton.me \
  --subject "[Bug report] <title>" \
  --body   submission/body_F1.txt \
  --attach submission/Report.pdf \
  --target proton.me \
  --record submission/send-record.json
```
Dry run first (`--dry-run`) — prints the resolved key fingerprint and attachment list, sends nothing.

Credentials: `~/.smtp_cred` (line 1 = gmail address, line 2 = 16-char app password), or
`SMTP_USER` / `SMTP_PASS`. Harden on Windows:
```bash
icacls "$HOME/.smtp_cred" /inheritance:r /grant:r "$(whoami):(R,W)"
```

## 3. Verify — the send call returning OK is NOT proof

The script prints `SENT. refused recipients: (none)`; that only means SMTP accepted it.
Confirm via IMAP by Message-ID:
```python
from imap_tools import MailBox, AND
mb = MailBox('imap.gmail.com').login(user, pw); mb.folder.set('[Gmail]/Surat Terkirim')
[m for m in mb.fetch(AND(...)) if mid.strip('<>') in m.headers.get('message-id',('',))[0]]
```
Indonesian-locale Gmail: the folder is `[Gmail]/Surat Terkirim`, **not** `[Gmail]/Sent Mail`.

## Pitfalls (all hit for real)

1. **MSYS/git-bash gpg + absolute Windows `GNUPGHOME` = broken.** gpg prepends the cwd, giving
   `keyblock resource '/c/Users/.../C:\Users\...\pubring.kbx': No such file or directory` and
   `no writable keyring found`. Fix: create the throwaway homedir **inside the cwd** (`tempfile.mkdtemp(dir=os.getcwd())`)
   and pass only the **basename** as `GNUPGHOME`. The script already does this — don't "simplify" it back.
2. **`chmod 600` is a no-op on Windows.** Use `icacls` (above). A `0o666` from `ls -l` is not a finding.
3. **Never re-set `Message-ID`.** `msg["Message-ID"] = msg["Message-ID"] or ...` raises
   `ValueError: There may be at most 1 Message-ID headers`. Set it once, copy it into the encrypted wrapper.
4. **Don't trust redacted credentials in a viewed file.** A file printed as `APP_PASSWORD="***"`
   is display-redacted; reading it back literally and failing auth is a self-inflicted error, not a
   dead credential. Read the value with a regex from the raw file, print only its length.
5. **Cleanup on failure.** Remove the throwaway `GNUPGHOME` in a `finally`, and never leave an
   app-password scratch file behind (delete it the moment SMTP login is confirmed).

## What "encrypted" means here — and the MIME trap that will bite you

The whole RFC822 message (body + attachment) is encrypted, so the Subject stays visible — that is what
these programs expect. **But the wrapper must be RFC 3156 `multipart/encrypted`:**

```
Content-Type: multipart/encrypted; protocol="application/pgp-encrypted"

part 1: application/pgp-encrypted        body = "Version: 1"
part 2: application/octet-stream         body = the armored PGP MESSAGE (base64)
```

**Do NOT build it with `set_content(...)` + `add_alternative(armored, subtype="pgp-encrypted")`.**
That yields `multipart/alternative`, and clients then render only the first alternative
("This is an OpenPGP/MIME encrypted message") or show a wall of armor instead of a decryptable
message. The ciphertext is technically intact, so you will not notice from a "SENT OK" — you only
notice when you inspect the stored copy. Verify the tree before trusting a send:

```python
from email import message_from_bytes
p = message_from_bytes(sent_raw)
assert p.get_content_type() == "multipart/encrypted"
assert p.get_param("protocol") == "application/pgp-encrypted"
assert [x.get_content_type() for x in p.get_payload()] == \
       ["application/pgp-encrypted", "application/octet-stream"]
```

`MIMEApplication(...)` base64-encodes the blob, so searching the raw bytes for `BEGIN PGP MESSAGE`
returns False even when the message is correct — assert on the MIME tree, not on the raw text.

### Verify the KEY ID against the encryption SUBKEY, not the primary fingerprint

`gpg --list-keys` gives you the primary fingerprint, but PGP encrypts to the **encryption subkey**, so
`gpg --list-packets` on your ciphertext will show a DIFFERENT keyid. Comparing against the primary
fingerprint produces a false "encryption failed". Take the first `sub` line from
`gpg --with-colons --list-keys` and compare that keyid:

```python
# primary: pub line -> fpr  (signing, ed25519/algo 22)
# subkey : sub line -> keyid (encryption, ECDH/algo 18)  <-- what --list-packets must show
enc_keyid = next(l.split(":")[4] for l in listing.splitlines() if l.startswith("sub:")).upper()
pkout = subprocess.run(["gpg","--batch","--list-packets"], input=armored, capture_output=True, env=env)
assert enc_keyid in pkout.stdout.decode("utf-8","replace").upper()
```

**`gpg --batch --list-packets` via stdin can hang on MSYS/git-bash** (the input pipe stalls → 60s+;
hit on Flux 2026-11). Deterministic fallback that needs no gpg: the PK-ESK packet carries the
recipient keyid as the 8 bytes directly after the version octet. Parse the armor, base64-decode, and
check the target subkey's big-endian bytes appear in the first ~40 bytes:

```python
import re, base64
b64 = "".join(l.strip() for l in armor.splitlines() if l.strip()
              and not l.startswith("-----") and not re.match(r"^=[A-Za-z0-9+/]{4}$", l))
raw = base64.b64decode(b64 + "="*((4-len(b64)%4)%4))
assert bytes.fromhex("6F3BAE57CCA741E4") in raw[:40]   # Flux enc subkey -> True
# raw head is e.g. 85018c036f3bae57cca741e4...  (tag|len|ver=03|keyid)
```

For Proton's `security@proton.me`: primary `C4BC9337CC23A0BA855A3EF32EE753BBBA66EE76` (ed25519),
encryption subkey `42044407C43F4475` (ECDH). The ciphertext legitimately names the subkey.

### Final gate before you send

Send the **pre-built** bytes (`smtplib.sendmail(sender, [to], raw_bytes)`) rather than reconstructing
the message at send time, so what you verified is exactly what leaves. Then read the copy back out of
Gmail Sent and re-assert the tree — that is the only proof the recipient got a decryptable message.

Also verify a change with a round-trip test: generate a throwaway keypair, encrypt, decrypt, assert
bytes are identical.

## Non-PGP channels (when PGP is NOT required)

"PGP key available on request" is NOT "PGP required". Distinguish before drafting:
- security.txt carries an `Encryption:` field, OR the policy says "encrypt"/"PGP key"
  (mandatory wording) → PGP required.
- "PGP key available on request" and no `Encryption:` field (Rootly 2026-11-02) → PGP
  optional → plain email is correct.

Always read security.txt AND grep the policy for `pgp|encrypt|gpg` BEFORE composing the
draft. The operator's rule: cek rulesnya dulu; pakai PGP hanya kalau diminta.

## Gmail draft delivery (DRAFT via gmail_ops.py, not SMTP)

> **MANDATORY draft conventions BEFORE any `gmail_ops.py draft` call** (canonical home: `bug-bounty-disclosure` — the operator has corrected this twice, 2026-10-01 and 2026-11-04):
> 1. **Subject = vendor-mandated prefix + a DISTINCT per-finding descriptor.** Never ship N bare-identical
>    subjects (two "Bug Bounty: P4"). Gmail + vendor ticketing merge identical subjects into one thread
>    and only the first gets reviewed — the rest silently vanish. Example: "Bug Bounty: P4 - JSON type
>    confusion (HTTP 500)" vs "Bug Bounty: P4 - returnUrl open redirect". Keep the required prefix, add a
>    short (<=8 word) descriptor. ("judulnya perbaiki, masa cm tulis p4 aja untuk keduanya".)
> 2. **Body must OPEN with a polite perkenalan, not the finding.** Salam line ("Hi <team>,"), then a short
>    self-intro: name, "security researcher", "reviewing <target> under your public bug bounty program",
>    "responsibly share a finding", plus a scope + sandbox-repro note — THEN the technical finding. Never
>    start the body with "Summary" / "I found…". ("prkenalannya mana, kok gksopan lgsg share temuan".)

When the deliverable is a DRAFT (the default — never send without "kirim"):

- **Dedup against SENT first.** The operator often sends earlier drafts themselves from the Gmail UI,
  so before creating any new draft, list `SENT` for `to:<vendor>` and match subjects against your
  record file — otherwise you draft findings already submitted (hit 2026-11 Flux: 3 of 5 drafts had
  already been sent 20:00 the same day). Read each candidate with
  `gmail_ops.py read <id> --account RESEARCHER_USERNAME` and check `labels` (SENT vs DRAFT); only
  genuinely-unsent findings get a new draft.

- MUST pass `--account RESEARCHER_USERNAME`. `gmail_ops.py draft` defaults to the FIRST configured
  account (`akun3` = ympuspita@gmail.com), which is the wrong mailbox. The bounty mailbox is
  RESEARCHER_EMAIL. Prove it landed correctly: `gmail_ops.py read <id> --account RESEARCHER_USERNAME`
  and check the `from` field.
- `gmail_ops.py draft` has NO attachment support (body-only, wrapped in `<pre>`). To attach a
  `.md` (or any file), build a MIMEMultipart yourself and create it via the Gmail API:

```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
msg = MIMEMultipart()
msg["From"] = "RESEARCHER_EMAIL"; msg["To"] = target; msg["Subject"] = subj
msg.attach(MIMEText(body, "plain", "utf-8"))
att = MIMEText(md, "markdown", _charset="utf-8")          # -> text/markdown
att.add_header("Content-Disposition", "attachment", filename="report.md")
msg.attach(att)
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
```

Get `svc` from `bounty_mail`: `from bounty_mail import account_files, gmail_service`, then
`[p for l,p in account_files() if l=="RESEARCHER_USERNAME"][0]` → `gmail_service(Path(tok))`.
- `MIMEText(..., "markdown")` yields `text/markdown`; paired with
  `Content-Disposition: attachment; filename="*.md"` Gmail stores it as a downloadable `.md`.
- The `.md` can also be written to disk first (a real artifact) and its text read back into
  the attachment — keep both.
- Verify the attachment actually landed: fetch `format=full` and walk `payload.parts[]` for
  `filename` + `partId`; the create() return alone is not proof.

## PGP-encrypted DRAFT (pgp required + DRAFT delivery, combined)

> **USER PREFERENCE — inline armor in the body, one finding per draft (correction 2026-11, Flux).**
> The operator does NOT want `multipart/encrypted` for a DRAFT they will review in the Gmail UI.
> A `multipart/encrypted` draft shows as an unreadable binary attachment, so the operator cannot see
> the content and said so ("kenapa tidak terbaca… PGP-nya sebelumnya nampak di body email"). Their
> established pattern is **inline PGP armor**: set the body to the armored text with
> `msg.set_content(armored, subtype="plain", charset="ascii")` so the
> `-----BEGIN PGP MESSAGE----- …` block is visible text in the body. Also **1 finding = 1 draft** —
> do NOT merge multiple findings into a single email. Use the RFC 3156 wrapper below only for a
> straight SMTP `send` the operator never reviews; for DRAFT delivery, inline armor wins.

When the program REQUIRES PGP AND the deliverable is a DRAFT (not send), combine the two paths
above. `gmail_ops.py draft` is plaintext-only and `pgp_submit.py send` only does SMTP — neither
does "encrypted draft" alone. Reuse the pieces directly:

```python
import base64, sys
sys.path.insert(0, "C:/Users/WINDOWS10/AppData/Local/hermes/scripts")
import pgp_submit, bounty_mail
from pathlib import Path
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

msg = EmailMessage()                     # 1) inner RFC822: From/To/Subject/Date/Message-ID + body + attachments
msg["From"]="RESEARCHER_NAME <RESEARCHER_EMAIL>"; msg["To"]=to; msg["Subject"]=subj
msg.set_content(body, subtype="plain", charset="utf-8")
# ... msg.add_attachment(...) for evidence files ...

armored, fpr = pgp_submit.gpg_encrypt(msg.as_bytes(), armor_key)   # 2) encrypt WHOLE inner msg

out = MIMEMultipart("encrypted", protocol="application/pgp-encrypted")   # 3) RFC 3156 wrapper
for k in ("From","To","Subject","Date","Message-ID"): out[k]=msg[k]
ver = MIMEApplication(b"Version: 1\n", _subtype="pgp-encrypted"); ver.replace_header("Content-Type","application/pgp-encrypted")
out.attach(ver)
blob = MIMEApplication(armored.encode("ascii"), _subtype="octet-stream"); out.attach(blob)

tok = [p for l,p in bounty_mail.account_files() if l=="RESEARCHER_USERNAME"][0]     # 4) draft via Gmail API, NOT smtplib
svc = bounty_mail.gmail_service(Path(tok))
raw = base64.urlsafe_b64encode(out.as_bytes()).decode()
draft = svc.users().drafts().create(userId="me", body={"message":{"raw": raw}}).execute()
```

Verification notes specific to the encrypted draft:
- Read the message back `format=full` and assert `payload["mimeType"]=="multipart/encrypted"`
  with two `parts[]` = `application/pgp-encrypted` then `application/octet-stream`. That MIME tree
  is the proof; `drafts().create()` returning OK is not.
- `gmail_ops.py read <id>` shows `"body": ""` for a multipart/encrypted draft — expected, not a
  failure. The From/To/Subject are still visible; the body is the armor.
- The operator CANNOT review the encrypted body in the Gmail UI, so keep the plaintext report on
  disk (`draft_email.txt` + evidence) and hand them the path. Reuse `pgp_submit.gpg_encrypt` (it
  already handles the throwaway-GNUPGHOME MSYS quirk) rather than re-rolling gpg subprocess calls.

### To-address vs PGP key UID are DIFFERENT fields — don't conflate

The submission To: comes from the program page's own instruction ("Submissions can only be made
to <mailto>"). The PGP public key's User-ID can name a DIFFERENT canonical address. They do not
have to match. Flux (2026-11) is a live case: the page's mailto is `security@runonflux.com`, but
the key UID is `Flux Security <security@runonflux.io>`. Resolve `To:` from the page text/mailto
(and cross-check prior replies + memory), encrypt to the key's fingerprint regardless, and flag
the mismatch to the operator instead of silently picking one. Decode the key UID authoritatively
with `gpg --show-keys --with-colons <key.asc>` (grep `uid:`) — a naive base64 walk over the armor
produces garbage.

## Related
`bug-bounty-disclosure` (draft/body conventions) · `report-writing` · `disclosure-contact-discovery`
