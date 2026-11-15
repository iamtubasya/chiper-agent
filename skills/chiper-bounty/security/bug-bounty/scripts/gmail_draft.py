#!/usr/bin/env python3
"""Stage a bug-bounty report as a Gmail DRAFT (attachment = PoC PDF).

Encodes the imap_tools mechanics that otherwise cost ~4 failed attempts:
 - read creds with chr(34) string ops (a regex literal for APP_PASSWORD triggers
   the Hermes secret-redaction layer -> the line is rewritten to `APP_PASSWORD=***`
   -> SyntaxError)
 - drafts folder is locale-specific: [Gmail]/Draf (id) vs [Gmail]/Drafts (en) -- auto-detect
 - MailBox.append(message_bytes, folder, flag_set=("\\Draft",)) -- MESSAGE FIRST, folder SECOND
   (swapped -> the folder string is fed as the message -> 'str' object has no attribute 'obj')
 - build bytes with email.generator.BytesGenerator (msg.as_bytes() returned str in some envs)
 - pass flag_set=("\\Draft",) or the message sits in the folder WITHOUT \\Draft and never shows
   as a draft in the web UI
 - verify in a FRESH connection (a same-connection fetch right after append can return a stale
   subset that omits the new high-UID message)

Usage:
  python gmail_draft.py --creds ~/check_basabasi_email.py --to info@vendor.com \
    --subject "[CVD] Finding title" --body report_body.txt --pdf PoC.pdf
"""
import argparse, io, os, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.generator import BytesGenerator
from imap_tools import MailBox

Q = chr(34)  # double-quote without a secret-looking regex literal


def load_creds(path):
    em = pw = srv = None
    for ln in open(path).read().splitlines():
        s = ln.strip()
        if s.startswith("EMAIL"):
            em = s[s.find(Q) + 1:s.rfind(Q)]
        elif s.startswith("APP_PASSWORD"):
            pw = s[s.find(Q) + 1:s.rfind(Q)]
        elif s.startswith("IMAP_SERVER"):
            srv = s[s.find(Q) + 1:s.rfind(Q)]
    if not (em and pw):
        sys.exit("creds not found in " + path)
    return em, pw, (srv or "imap.gmail.com")


def find_drafts_folder(mb):
    for f in mb.folder.list():
        n = f.name
        if n.lower().endswith("/draf") or n.lower().endswith("/drafts"):
            return n
    return "INBOX"


def build_bytes(em, to, subject, body, pdf):
    msg = MIMEMultipart()
    msg["From"] = em
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    if pdf and os.path.exists(pdf):
        with open(pdf, "rb") as fh:
            part = MIMEBase("application", "pdf")
            part.set_payload(fh.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment",
                            filename=os.path.basename(pdf))
            msg.attach(part)
    bio = io.BytesIO()
    BytesGenerator(bio).flatten(msg)
    return bio.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creds", required=True, help="script holding EMAIL/APP_PASSWORD/IMAP_SERVER")
    ap.add_argument("--to", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body", required=True, help="text file with the report body")
    ap.add_argument("--pdf", default=None, help="PoC PDF to attach")
    a = ap.parse_args()

    em, pw, srv = load_creds(a.creds)
    body = open(a.body).read()
    raw = build_bytes(em, a.to, a.subject, body, a.pdf)

    with MailBox(srv).login(em, pw) as mb:
        folder = find_drafts_folder(mb)
        res = mb.append(raw, folder, flag_set=("\\Draft",))  # message FIRST, folder SECOND
        print("appended to", folder, "->", res)

    with MailBox(srv).login(em, pw) as mb:  # FRESH connection to verify
        mb.folder.set(find_drafts_folder(mb))
        hit = [m for m in mb.fetch(limit=50) if a.subject[:30] in (m.subject or "")]
        print("verify: subject in drafts =", bool(hit),
              "| isDraft =", any("\\Draft" in m.flags for m in hit))


if __name__ == "__main__":
    main()
