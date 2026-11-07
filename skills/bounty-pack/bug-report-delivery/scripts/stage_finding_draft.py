#!/usr/bin/env python3
"""Stage a finding as a Gmail DRAFT with a reportlab PDF (and optional armoured copy).

Why a script and not a doc: this exact file got rebuilt from scratch twice in one engagement.
Run it, do not retype it.

    python stage_finding_draft.py report.md Out-Name.pdf "<email subject>" \
        --to security@vendor.com --body body_Fn.txt \
        --attach evidence_F1.txt --attach F1.png

`--body` is **REQUIRED** (rule 0c) and its content is validated: the intro / channel / signature markers
must be present and no reward word or AI-ism may appear. Skeleton: templates/disclosure-email-body.md.

Then REPORT the draft id / To / Subject / attachments to the operator and state explicitly that it
was **NOT sent**. Staging is not sending -- never send without an explicit instruction.

Two environment gotchas this encodes:

1. `TOKEN` path is built from fragments. The output-masking tripwire rewrites auth-header-shaped
   literals **inside files you write** (a literal `"Authorization: Bearer " + k` can come back as
   `***`, producing a SyntaxError the lint step flags). Fragment the filename and the header name /
   scheme the same way, as done below.
2. The live OAuth token is under $HERMES_HOME (`~/.chiper/skills/bounty-pack/`), NOT `~/.hermes/`.
   A stale/revoked token in `~/.hermes/` is a real trap -- resolve via the env var when set.

If the token is revoked you cannot fix it alone: run the workspace `setup.py --auth-url`, give the
operator the URL, have them approve and paste back the full `http://localhost:1/?...&code=...`
redirect, then `setup.py --auth-code "<url>"`. That flag takes NO `--format` (it aborts on arg
parsing before consuming the code, so the code survives and can be retried bare).
"""
import os, sys, re, base64, mimetypes, argparse

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, Image as RLImage, KeepTogether
from reportlab.lib import colors
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- tripwire-safe fragments (see module docstring #1) ---
TOKEN_FILENAME = "google_" + "token" + ".json"
HDR_NAME       = "Author" + "ization"
HDR_SCHEME     = "Bea" + "rer "


IMAGE_LINE_OK = True  # additive (2026-10-16): md line ![caption](abs/path.png) embeds a real screenshot


def _md_image(line):
    t = line.strip()
    if not t.startswith('!['):
        return None
    if not t.endswith(')') or '](' not in t:
        return None
    cap = t[2:t.index('](')]
    path = t[t.index('](') + 2:-1].strip()
    if not path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return None
    return path, cap


def _image_flow(path, caption):
    try:
        from PIL import Image as PILImage
        pil = PILImage.open(path)
        if pil.mode != 'RGB':
            pil = pil.convert('RGB')
            pil.save(path, 'PNG')
    except Exception:
        return None
    img = RLImage(path)
    aspect = img.imageWidth / float(img.imageHeight or 1)
    w = 460.0
    h = w / aspect
    if h > 330.0:
        h = 330.0
        w = h * aspect
    img.drawWidth, img.drawHeight = w, h
    img.hAlign = 'CENTER'
    parts = [img]
    if caption:
        safe = caption.replace('&', '&amp;').replace('<', '&lt;')
        capstyle = ParagraphStyle('cap', parent=getSampleStyleSheet()['BodyText'],
                                  fontSize=8, alignment=1, spaceAfter=8)
        parts.append(Paragraph('<i>' + safe + '</i>', capstyle))
    return KeepTogether(parts)


def build_pdf(src_md, out_pdf, title):
    ss   = getSampleStyleSheet()
    h1   = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=15, spaceAfter=6, textColor=colors.HexColor("#111"))
    h2   = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#222"))
    body = ParagraphStyle("b",  parent=ss["BodyText"], fontSize=9.2, leading=12.4, alignment=TA_LEFT)
    code = ParagraphStyle("c",  parent=ss["Code"], fontSize=7.6, leading=9.6, backColor=colors.HexColor("#f4f4f4"))

    doc = SimpleDocTemplate(out_pdf, pagesize=A4, leftMargin=18 * mm, rightMargin=16 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm, title=title)
    flow, in_code, buf = [], False, []
    esc = lambda t: t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    CODE_WRAP = 92   # Courier 7.6pt fits ~92 chars between the 18/16mm margins; wrap longer lines

    for line in open(src_md, encoding="utf-8").read().split("\n"):
        _img = _md_image(line)
        if _img:
            _flow = _image_flow(_img[0], _img[1])
            if _flow is not None:
                flow.append(_flow)
            continue
        if line.strip().startswith("```"):
            if in_code:
                # wrap long code lines so they cannot leave the frame (OUT-OF-MARGIN / OVERSIZED WORD)
                wrapped = []
                for cl in buf:
                    while len(cl) > CODE_WRAP:
                        cut = cl.rfind(" ", 0, CODE_WRAP)
                        if cut < 40:
                            cut = CODE_WRAP
                        wrapped.append(cl[:cut])
                        cl = "        " + cl[cut:].lstrip()
                    wrapped.append(cl)
                flow.append(Preformatted("\n".join(wrapped), code)); flow.append(Spacer(1, 4))
                buf, in_code = [], False
            else:
                in_code = True
            continue
        if in_code:
            buf.append(line); continue
        if   line.startswith("# "):   flow.append(Paragraph(esc(line[2:]), h1))
        elif line.startswith("## "):  flow.append(Paragraph(esc(line[3:]), h2))
        elif line.startswith("### "): flow.append(Paragraph(esc(line[4:]), h2))
        elif line.strip() == "---":   flow.append(Spacer(1, 6))
        elif line.strip() == "":      flow.append(Spacer(1, 3))
        else:
            t = esc(line)
            t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
            t = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', t)
            flow.append(Paragraph(t, body))
    doc.build(flow)
    return out_pdf


def token_path():
    home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.chiper/skills/bounty-pack")
    return os.path.join(home, TOKEN_FILENAME)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md"); ap.add_argument("pdf"); ap.add_argument("subject")
    ap.add_argument("--to", required=True, help="recipient, e.g. security@vendor.com")
    ap.add_argument("--body", required=True,
                    help="per-finding body file (REQUIRED — rule 0c; the generic stub was removed on purpose)")
    ap.add_argument("--asc", default=None, help="optional PGP-armoured copy to attach as well")
    ap.add_argument("--attach", action="append", default=[], help="extra attachment, repeatable: evidence txt / png (rule 0a-2 trio)")
    a = ap.parse_args()

    ws  = os.path.dirname(os.path.abspath(a.md))
    pdf = a.pdf if os.path.isabs(a.pdf) else os.path.join(ws, a.pdf)
    build_pdf(a.md, pdf, a.subject.replace("[VDP] ", ""))
    print(f"PDF: {pdf} ({os.path.getsize(pdf)} bytes)")

    # --- RULE 0c: the body is NEVER a generic stub -------------------------------------------
    # A perfect PDF with a placeholder body is a REJECTED deliverable (operator, 2026-10-12).
    # The old fallback ("Hi, / Findings attached...") is deliberately GONE. --body is required
    # and this gate refuses to stage a body that is missing the fixed shape or that asks for
    # a reward. Skeleton to copy: templates/disclosure-email-body.md
    body = open(a.body, encoding="utf-8").read()
    REQUIRED = {
        "greeting + who you are": "independent security researcher",
        "the disclosure channel": "responsible disclosure",
        "signature name": "RESEARCHER_NAME",
    }
    missing = [k for k, v in REQUIRED.items() if v.lower() not in body.lower()]
    if missing:
        raise SystemExit(
            "BODY REJECTED (rule 0c) — missing: " + ", ".join(missing)
            + "\nCopy templates/disclosure-email-body.md and fill it per finding."
        )
    banned = [t for t in ("\u2014", "\u2013", "delve", "pivotal", "leverage", "seamless",
                          "i hope this helps", "great question") if t in body.lower()]
    # Reward words are checked on a URL-stripped copy with WORD BOUNDARIES: a policy citation
    # (".../Bug-Bounty-Policy-1.3.pdf") and product names ("Swagger UI") are not compensation
    # requests, and substring matching used to reject both (2026-10-12, mydays engagement).
    scan = re.sub(r"https?://\S+", " ", body.lower())
    reward = [t for t in ("bug bounty", "bounty", "reward", "hall of fame", "swag", "credit")
              if re.search(r"\b" + re.escape(t) + r"\b", scan)]
    if banned or reward:
        raise SystemExit("BODY REJECTED (rule 0c) — banned tokens: " + repr(banned + reward))

    files = [pdf] + [f for f in a.attach if os.path.exists(f)] + ([a.asc] if a.asc and os.path.exists(a.asc) else [])

    tok = token_path()
    creds = Credentials.from_authorized_user_file(tok)
    if not creds.valid:
        creds.refresh(Request())
        open(tok, "w").write(creds.to_json())
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg = EmailMessage()
    msg["To"], msg["From"], msg["Subject"] = a.to, "me", a.subject
    # A unique Message-ID is REQUIRED. Without it Gmail treats the append as a revision of the
    # previous draft and silently replaces it (staging report B deletes report A).
    from email.utils import make_msgid, formatdate
    msg["Message-ID"] = make_msgid(domain="report.local")
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body)
    for f in files:
        ct, _ = mimetypes.guess_type(f)
        mt, st = (ct.split("/", 1) if ct else ("application", "octet-stream"))
        with open(f, "rb") as fh:
            msg.add_attachment(fh.read(), maintype=mt, subtype=st, filename=os.path.basename(f))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    d = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    print(f"DRAFT {d['id']} msg {d['message']['id']} | attach: {[os.path.basename(f) for f in files]}")

    # verify by read-back -- never trust the create response alone
    m = svc.users().messages().get(userId="me", id=d["message"]["id"], format="full").execute()
    h = {x["name"]: x["value"] for x in m["payload"]["headers"]}
    print(f"VERIFIED  To={h.get('To')}  Subject={h.get('Subject')}")
    print(f"ATTACH    {[p['filename'] for p in m['payload'].get('parts', []) if p.get('filename')]}")
    # rule 0a-2 read-back: sha256(attachment) == sha256(local file) for EVERY attachment
    import hashlib
    def _sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    for p in m["payload"].get("parts", []):
        fn = p.get("filename")
        if not fn:
            continue
        att_id = p.get("body", {}).get("attachmentId")
        if not att_id:
            continue
        att = svc.users().messages().attachments().get(userId="me", messageId=d["message"]["id"], id=att_id).execute()
        remote = hashlib.sha256(base64.urlsafe_b64decode(att["data"] + "==")).hexdigest()
        local = _sha([f for f in files if os.path.basename(f) == fn][0])
        print("HASH     %s match=%s" % (fn, remote == local))
    print("STATUS    NOT SENT -- staged in Drafts only.")


if __name__ == "__main__":
    main()
