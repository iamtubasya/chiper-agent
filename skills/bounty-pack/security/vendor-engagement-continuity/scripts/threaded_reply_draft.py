#!/usr/bin/env python3
"""Stage a THREADED reply draft (never sends) into an existing Gmail thread.

Why a dedicated script instead of gmail_ops.py:
  * gmail_ops.encode_mime() has NO attachment support and never sets In-Reply-To
    beyond the immediate parent. Vendor follow-ups routinely need an evidence
    attachment plus the full References chain so the mail lands inside the
    existing ticket thread (Freshdesk/Zendesk split threads otherwise).
  * gmail_ops.pick_service() returns a (label, service) TUPLE, not the service.
    Unpack it or you get "'tuple' object has no attribute 'users'".

What it guarantees:
  * the reply is created as a DRAFT — no --send flag exists on purpose
  * In-Reply-To / References point at the real parent Message-ID
  * threadId is passed on create AND re-verified by re-fetching the draft, so a
    silent thread split is caught before the operator sends it

Usage
-----
    python threaded_reply_draft.py --parent-msg-id <gmail-message-id> \
        --body-file reply.txt [--attach evidence.txt] [--account RESEARCHER_USERNAME] \
        [--dry-run]

Find the parent message id first:
    python gmail_ops.py thread <threadId>      # or list/search in gmail_ops

Output: JSON with draftId, resolved threadId, expected threadId, thread_ok.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

_chiper_base = os.environ.get("CHIPER_PATH") or os.environ.get("CHIPER_HOME")
_pack_dir = (Path(_chiper_base) if _chiper_base else (Path.home() / ".chiper")) / "skills/bounty-pack"
sys.path.insert(0, str(_pack_dir))
import gmail_ops as g  # noqa: E402


def build(to: str, subject: str, body: str, parent_msgid: str,
          references: str, attach_name: str | None,
          attach_text: str | None) -> MIMEMultipart:
    root = MIMEMultipart("mixed")
    root["To"] = to
    root["Subject"] = subject
    if parent_msgid:
        root["In-Reply-To"] = parent_msgid
        refs = f"{references} {parent_msgid}".strip() if references else parent_msgid
        root["References"] = refs

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body, "plain", "utf-8"))
    # MUST escape: a raw "<word ...>" in the body is parsed as an HTML tag and
    # disappears from the delivered mail (verified 2026-10-31 on a FIRST.org
    # fix-confirmation reply -- "<unique per request>" and "<variant>" were lost,
    # leaving "&state=" and "&redirect_uri=" empty in the sent copy).
    alt.attach(MIMEText(g.html_pre(body), "html", "utf-8"))
    root.attach(alt)

    if attach_name and attach_text is not None:
        part = MIMEApplication(attach_text.encode("utf-8"), Name=attach_name)
        part["Content-Disposition"] = f'attachment; filename="{attach_name}"'
        root.attach(part)
    return root


def lost_tokens(source: str, delivered: str) -> list[str]:
    """Tokens present in the source body but absent from the delivered body.

    Catches HTML-swallowing and encoding damage BEFORE the operator sends.
    Rewrapping only moves whitespace, so whitespace-delimited tokens survive.
    """
    src = set(re.findall(r"\S{3,}", source))
    got = set(re.findall(r"\S{3,}", delivered))
    return sorted(tok for tok in src - got if tok not in ("\n",))


def delivered_plain(svc, draft_id: str) -> str:
    d = svc.users().drafts().get(userId="me", id=draft_id, format="full").execute()
    msg = d["message"]
    return g.body_of(msg).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent-msg-id", required=True,
                    help="Gmail message id of the vendor message you are replying to")
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--attach", default=None, help="evidence file to attach")
    ap.add_argument("--attach-name", default=None)
    ap.add_argument("--account", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    label, svc = g.pick_service(a.account)  # NOTE: tuple unpack

    src = svc.users().messages().get(
        userId="me", id=a.parent_msg_id, format="metadata",
        metadataHeaders=["From", "Reply-To", "Subject", "Message-ID", "References"],
    ).execute()
    h = g.hdrs(src)

    to = h.get("reply-to") or h.get("from") or ""
    subj = h.get("subject", "")
    if not subj.lower().startswith("re:"):
        subj = f"Re: {subj}"
    parent = h.get("message-id", "")
    references = h.get("references", "")
    expected_thread = src.get("threadId")

    body = Path(a.body_file).read_text(encoding="utf-8")
    attach_text = Path(a.attach).read_text(encoding="utf-8") if a.attach else None
    attach_name = a.attach_name or (Path(a.attach).name if a.attach else None)

    root = build(to, subj, body, parent, references, attach_name, attach_text)

    info = {"to": to, "subject": subj, "parent_message_id": parent,
            "expected_thread": expected_thread,
            "body_chars": len(body),
            "attachment": f"{attach_name} ({len(attach_text or '')} b)" if attach_name else None}

    if a.dry_run:
        info["staged"] = False
        print(json.dumps(info, indent=1))
        return 0

    raw = base64.urlsafe_b64encode(root.as_bytes()).decode("ascii")
    payload = {"raw": raw}
    if expected_thread:
        payload["threadId"] = expected_thread

    res = svc.users().drafts().create(userId="me", body={"message": payload}).execute()

    # Re-fetch: Gmail silently starts a new thread if threadId/References disagree.
    check = svc.users().drafts().get(userId="me", id=res["id"]).execute()
    got = check["message"].get("threadId")
    got_h = g.hdrs(check["message"])

    delivered = delivered_plain(svc, res["id"])
    lost = lost_tokens(body, delivered)

    info.update({
        "staged": True,
        "draftId": res["id"],
        "messageId": res["message"]["id"],
        "threadId": got,
        "thread_ok": got == expected_thread,
        "in_reply_to": got_h.get("in-reply-to"),
        "body_roundtrip_chars": len(delivered),
        "lost_tokens": lost,
        "sent": False,
    })
    print(json.dumps(info, indent=1))
    if lost:
        print(f"\n!! {len(lost)} token(s) lost between your file and the draft - "
              f"DO NOT SEND until fixed:", file=sys.stderr)
        for tok in lost[:10]:
            print(f"   {tok!r}", file=sys.stderr)
        return 3
    return 0 if info["thread_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
