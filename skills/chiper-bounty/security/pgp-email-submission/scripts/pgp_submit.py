#!/usr/bin/env python3
"""pgp_submit.py - email a bug report, PGP-encrypted when the program asks for it.

    discover : python pgp_submit.py discover --target proton.me
    send     : python pgp_submit.py send --to security@proton.me --subject "[Bug report] ..." \
                 --body body.txt --attach report.pdf --target proton.me \
                 --record send-record.json

    plaintext: add --no-pgp   (only when the program does NOT ask for PGP)
    dry run  : add --dry-run  (resolves the key, prints the fingerprint, sends nothing)

Key discovery order: security.txt `Encryption:` field -> --key -> PKS lookup for the recipient.
Encryption runs in a throwaway GNUPGHOME so ~/.gnupg is never touched.

Credentials: --cred-file (default ~/.smtp_cred: line1 = address, line2 = app password)
             or env SMTP_USER / SMTP_PASS.

Three pitfalls are encoded here on purpose - do not "simplify" them away:
  1. GNUPGHOME must be a RELATIVE path on git-bash/MSYS. An absolute Windows path gets the cwd
     prepended by the MSYS gpg build and fails with `no writable keyring found`.
  2. Message-ID is set ONCE. Re-assigning it raises
     `ValueError: There may be at most 1 Message-ID headers`.
  3. Cleanup runs in a finally block and removes the absolute temp dir.
"""
import argparse
import json
import os
import re
import shutil
import smtplib
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

UA = {"User-Agent": "Mozilla/5.0 (compatible; pgp_submit/1.0)"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def find_security_txt(domain):
    for scheme in ("https", "http"):
        for path in ("/.well-known/security.txt", "/security.txt"):
            url = "%s://%s%s" % (scheme, domain, path)
            try:
                txt = fetch(url)
                if "Contact:" in txt:
                    return url, txt
            except Exception:
                continue
    return None, None


def parse_security_txt(txt):
    out = {"contact": [], "encryption": [], "policy": []}
    cur = None
    for line in txt.splitlines():
        if line[:1] in (" ", "\t") and cur:
            out[cur][-1] += " " + line.strip()
            continue
        m = re.match(r"^(Contact|Encryption|Policy|Expires|Preferred-Languages):\s*(.+)$",
                     line.strip(), re.I)
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        cur = key if key in out else None
        if cur:
            out[cur].append(val)
    return out


def fetch_key(url, timeout=25):
    """Return an ASCII-armored public key from a URL or an HKP/PKS lookup URL."""
    if "op=get" in url or "search=" in url:
        return fetch(url, timeout)
    try:
        body = fetch(url, timeout)
        if "BEGIN PGP PUBLIC KEY BLOCK" in body:
            return body
    except Exception:
        pass
    m = re.match(r"https?://([^/]+)", url)
    me = re.search(r"search=([^&]+)", url)
    if m and me:
        return fetch("https://%s/pks/lookup?op=get&search=%s" % (m.group(1), me.group(1)), timeout)
    raise RuntimeError("no armored key at %s" % url)


def gpg_encrypt(plaintext_bytes, armor_key):
    # pitfall 1: RELATIVE homedir, created inside the cwd (MSYS-safe)
    home_abs = tempfile.mkdtemp(prefix="pgpsub-", dir=os.getcwd())
    home = os.path.basename(home_abs)
    env = dict(os.environ, GNUPGHOME=home)
    try:
        imp = subprocess.run(["gpg", "--batch", "--quiet", "--import"],
                             input=armor_key.encode(), capture_output=True, env=env)
        if imp.returncode != 0:
            raise RuntimeError("gpg import failed: %s" % imp.stderr.decode()[:300])
        listing = subprocess.run(["gpg", "--batch", "--with-colons", "--list-keys"],
                                 capture_output=True, text=True, env=env).stdout
        fpr = None
        for line in listing.splitlines():
            if line.startswith("fpr:"):
                fpr = line.split(":")[9]
                break
        if not fpr:
            raise RuntimeError("no key found after import")
        enc = subprocess.run(
            ["gpg", "--batch", "--yes", "--trust-model", "always", "--armor",
             "--encrypt", "--recipient", fpr],
            input=plaintext_bytes, capture_output=True, env=env)
        if enc.returncode != 0:
            raise RuntimeError("gpg encrypt failed: %s" % enc.stderr.decode()[:300])
        return enc.stdout.decode("ascii"), fpr
    finally:
        shutil.rmtree(home_abs, ignore_errors=True)   # pitfall 3: absolute dir


def read_creds(args):
    path = os.path.expanduser(args.cred_file)
    if os.path.exists(path):
        lines = [l.strip() for l in open(path) if l.strip()]
        if len(lines) >= 2:
            return lines[0], lines[1]
    user, pw = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS")
    if not user or not pw:
        sys.exit("need %s (two lines: address, app-password) or SMTP_USER/SMTP_PASS" % path)
    return user, pw


def cmd_discover(args):
    domain = re.sub(r"^https?://", "", args.target).split("/")[0]
    url, txt = find_security_txt(domain)
    if not txt:
        print(json.dumps({"target": domain, "security_txt": None,
                          "verdict": "no security.txt - read the program page manually; "
                                     "do not invent an address or key"}, indent=1))
        return
    f = parse_security_txt(txt)
    print(json.dumps({"target": domain, "security_txt_url": url, "contact": f["contact"],
                      "encryption": f["encryption"], "policy": f["policy"],
                      "pgp_asked": bool(f["encryption"]),
                      "next": ("send with --target %s (key auto-fetched)" % domain)
                              if f["encryption"] else "no key advertised - plaintext is correct"},
                     indent=1))


def cmd_send(args):
    user, pw = read_creds(args)
    body = open(args.body, encoding="utf-8").read()

    msg = EmailMessage()
    msg["From"] = "%s <%s>" % (args.from_name, user)
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")   # pitfall 2: set once
    msg.set_content(body, subtype="plain", charset="utf-8")
    for path in (args.attach or []):
        subtype = "pdf" if path.lower().endswith(".pdf") else "octet-stream"
        msg.add_attachment(open(path, "rb").read(), maintype="application",
                           subtype=subtype, filename=os.path.basename(path))

    encrypted, fpr = False, None
    if not args.no_pgp:
        key_url = args.key
        if not key_url and args.target:
            domain = re.sub(r"^https?://", "", args.target).split("/")[0]
            _, txt = find_security_txt(domain)
            if txt:
                enc = parse_security_txt(txt)["encryption"]
                key_url = enc[0] if enc else None
        if not key_url:
            key_url = "https://api.protonmail.ch/pks/lookup?op=get&search=%s" % args.to
        armored, fpr = gpg_encrypt(msg.as_bytes(), fetch_key(key_url))

        out = EmailMessage()
        for h in ("From", "To", "Subject", "Date", "Message-ID"):
            out[h] = msg[h]
        out.set_content("This is an OpenPGP/MIME encrypted message (RFC 4880).\n")
        out.add_alternative(armored, subtype="pgp-encrypted")
        msg, encrypted = out, True

    mid = msg["Message-ID"]
    print("---- PRE-SEND ----")
    print("to         :", args.to)
    print("subject    :", args.subject)
    print("pgp        :", ("ENCRYPTED (fpr %s)" % fpr) if encrypted else "plaintext")
    print("attachments:", args.attach or "(none)")
    print("message-id :", mid)
    if args.dry_run:
        print("DRY RUN - nothing sent")
        return

    with smtplib.SMTP_SSL(args.smtp_host, args.smtp_port, timeout=60,
                          context=ssl.create_default_context()) as s:
        s.login(user, pw)
        refused = s.send_message(msg)
    print("SENT. refused recipients:", refused or "(none)")
    print("VERIFY NEXT: the send returning OK is NOT proof - confirm the Message-ID in the Sent "
          "folder over IMAP before telling anyone it was delivered.")
    if args.record:
        json.dump({"to": args.to, "subject": args.subject, "message_id": mid,
                   "encrypted": encrypted, "recipient_key_fpr": fpr,
                   "refused": refused or {}, "attachments": args.attach or []},
                  open(args.record, "w"), indent=1)
        print("record written:", args.record)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover")
    d.add_argument("--target", required=True)

    s = sub.add_parser("send")
    s.add_argument("--to", required=True)
    s.add_argument("--subject", required=True)
    s.add_argument("--body", required=True)
    s.add_argument("--attach", nargs="*")
    s.add_argument("--target", help="domain whose security.txt advertises the key")
    s.add_argument("--key", help="explicit armored-key URL")
    s.add_argument("--no-pgp", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--from-name", default="RESEARCHER_NAME")
    s.add_argument("--cred-file", default="~/.smtp_cred")
    s.add_argument("--smtp-host", default="smtp.gmail.com")
    s.add_argument("--smtp-port", type=int, default=465)
    s.add_argument("--record")

    a = ap.parse_args()
    cmd_discover(a) if a.cmd == "discover" else cmd_send(a)


if __name__ == "__main__":
    main()
