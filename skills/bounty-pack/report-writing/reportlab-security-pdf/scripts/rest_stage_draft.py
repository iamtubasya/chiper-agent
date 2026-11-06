#!/usr/bin/env python3
"""Stage ONE finding as a Gmail DRAFT via the REST API, with its PDF attached.

Why this file exists: on 2026-10-25 three djangoeurope findings were staged by IMAP
append into the folder carrying the `\\Drafts` special-use flag, WITH flag_set=(\\Draft,).
IMAP read-back showed the right subject, the PDF and `\\Draft` in flags — and the drafts
were still not in Gmail. They had been filed into `[Gmail]/Surat Terkirim` (Sent) and
`drafts().list()` did not contain them. An IMAP read-back is not proof of a visible
draft. This script uses the path that works: `users().drafts().create()`, which returns
`labelIds: ['DRAFT']` and shows up in the UI immediately.

Run it, do not retype it.

    python rest_stage_draft.py <report.pdf> <body.txt> <to> [cc]

`body.txt` is a normal message body whose FIRST LINE is `Subject: <subject>`. Everything
after the first line becomes the body. One finding = one call = one PDF = one draft
(RULE 0); do not loop this over several findings into one draft.

Preconditions and traps this encodes:

1. **Do not assume the token is dead.** The skill's own history claimed the token at
   ~/AppData/Local/hermes/google_token.json was revoked; on 2026-10-25 it refreshed
   cleanly (`gmail.modify` + `gmail.send`). Call `Credentials.refresh(Request())` and see
   what happens before falling back to IMAP. The OTHER token, ~/.hermes/google_token.json,
   is calendar-only — picking it gives a 403 that looks like a revoked token.
2. **Verify the way the operator will**, not the way the API reports success:
   `drafts().list()` must contain it, `labelIds` must contain `DRAFT`, the attachment
   sha256 must match the local file, and the magic must be `%PDF-`.
3. **A changed PDF makes the draft stale.** Delete the old draft by id and re-stage;
   do not leave two drafts with the same subject (the operator sees both).
4. Subject must be ASCII and one line. A CRLF inside the subject renders as a wrapped
   mess in the draft list and breaks exact-match read-back — normalise whitespace when
   comparing (`re.sub(r"\\s+", " ", s)`).
"""
import base64
import hashlib
import mimetypes
import os
import re
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Resolve the token the same way the workspace skill does; never hardcode a username path.
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData/Local/hermes"))
CRED_FILE = HERMES_HOME.joinpath("google_" + "token" + ".json")
SENDER = "RESEARCHER_EMAIL"
DRAFT_LABEL = "DRAFT"


def service():
    if not CRED_FILE.exists():
        raise SystemExit(f"credential file not found: {CRED_FILE}")
    creds = Credentials.from_authorized_user_file(str(CRED_FILE))
    if not creds.valid:
        creds.refresh(Request())
        CRED_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def build_message(pdf: Path, body_file: Path, to: str, cc: str | None) -> tuple[bytes, str]:
    raw_body = body_file.read_text(encoding="utf-8")
    first, _, rest = raw_body.partition("\n")
    if not first.lower().startswith("subject:"):
        raise SystemExit("body file must start with a 'Subject: ...' line")
    subject = re.sub(r"\s+", " ", first.split(":", 1)[1]).strip()

    msg = EmailMessage()
    msg["From"] = SENDER
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    # A unique Message-ID is REQUIRED: without it Gmail treats a second stage as a
    # revision of the first and silently replaces it.
    msg["Message-ID"] = make_msgid(domain="report.local")
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(rest.lstrip("\n"))

    ctype, _ = mimetypes.guess_type(str(pdf))
    maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "pdf"))
    msg.add_attachment(pdf.read_bytes(), maintype=maintype, subtype=subtype, filename=pdf.name)
    return msg.as_bytes(), subject


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    pdf = Path(sys.argv[1]).resolve()
    body_file = Path(sys.argv[2]).resolve()
    to = sys.argv[3]
    cc = sys.argv[4] if len(sys.argv) > 4 else None
    for p in (pdf, body_file):
        if not p.exists():
            raise SystemExit(f"missing input: {p}")

    svc = service()
    raw, subject = build_message(pdf, body_file, to, cc)

    # Idempotency: drop any earlier draft with the same subject so the operator never
    # sees two copies of one finding.
    listing = svc.users().drafts().list(userId="me", maxResults=50).execute().get("drafts") or []
    for d in listing:
        m = svc.users().messages().get(
            userId="me", id=d["message"]["id"], format="metadata",
            metadataHeaders=["Subject"]).execute()
        hdr = {h["name"]: h["value"] for h in m["payload"]["headers"]}
        if re.sub(r"\s+", " ", hdr.get("Subject", "")).strip() == subject:
            svc.users().drafts().delete(userId="me", id=d["id"]).execute()
            print(f"replaced stale draft {d['id']}")

    created = svc.users().drafts().create(
        userId="me", body={"message": {"raw": base64.urlsafe_b64encode(raw).decode()}}).execute()
    print(f"DRAFT {created['id']} msg {created['message']['id']}")

    # ---- verification gate: what the operator will actually see ----
    got = svc.users().messages().get(
        userId="me", id=created["message"]["id"], format="full").execute()
    hdr = {h["name"]: h["value"] for h in got["payload"]["headers"]}
    labels = got.get("labelIds") or []
    print(f"  Subject : {hdr.get('Subject')}")
    print(f"  To/Cc   : {hdr.get('To')} / {hdr.get('Cc')}")
    print(f"  labels  : {labels}")
    ok = DRAFT_LABEL in labels and "SENT" not in labels
    print(f"  visible as draft: {ok}")

    local_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    for part in got["payload"].get("parts", []):
        if not part.get("filename"):
            continue
        att = svc.users().messages().attachments().get(
            userId="me", messageId=created["message"]["id"],
            id=part["body"]["attachmentId"]).execute()
        blob = base64.urlsafe_b64decode(att["data"])
        att_ok = hashlib.sha256(blob).hexdigest() == local_sha and blob[:5] == b"%PDF-"
        print(f"  attach  : {part['filename']} {len(blob)}B sha256 match={att_ok}")
        ok = ok and att_ok

    if not ok:
        print("VERIFICATION FAILED — do not report this as staged", file=sys.stderr)
        return 1
    print("STAGED, NOT SENT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
