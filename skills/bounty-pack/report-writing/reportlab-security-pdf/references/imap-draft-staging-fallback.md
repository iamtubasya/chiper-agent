# IMAP draft staging (fallback when the Gmail REST token is dead)

> **Read `references/staging-dedup-and-script-tripwires.md` FIRST.** Two things that bite before the
> transport even matters: (1) this operator submits disclosures himself — check SENT
> (`[Gmail]/Surat Terkirim` on a localised account) for the finding before staging, or you hand him
> duplicates he has to delete; (2) heredocs that contain an auth header get rewritten by the
> output-redaction layer into silently-valid-but-wrong Python (a real 401 that looks like a dead token).
>
> ⛔ **NEVER MIX IMAP STAGING AND REST STAGING ON THE SAME FINDINGS (measured 2026-10-25).**
> After staging three findings via IMAP and then re-staging the same three via REST, the two REST
> drafts vanished from `drafts().list()` within minutes while a third survived. The likely mechanism
> is Gmail reconciling near-duplicate messages (same subject, same recipient, same attachment) that
> arrived through two different protocols, plus the IMAP `delete(uid)` calls I made on the strays.
> Re-staging via REST *only* made all three persist (verified 75 s later: `labelIds ['DRAFT']`,
> attachment sha256 + `%PDF-` matched). Rule: pick ONE transport per engagement and stick to it;
> if you must switch, delete the old copies first and re-verify persistence after a delay — a
> stage-time verification is not enough, Gmail's reconciler runs afterwards.
>
> ⛔ **IMAP APPEND DOES NOT PRODUCE A UI-VISIBLE DRAFT.**
> Three drafts appended to `[Gmail]/Draf` (folder carrying the `\Drafts` special-use flag) with
> `flag_set=(\Draft,)` read back perfectly over IMAP — right subject, PDF attached, `\Draft` in
> `flags` — and the operator still reported "the drafts are not in Gmail". They were not in Drafts:
> Gmail had filed them in **`[Gmail]/Surat Terkirim` (Sent)**, and REST `drafts().list()` did not
> contain them at all. An IMAP read-back showing `\Draft` is **not** proof of a visible draft; it only
> proves the folder accepted the append.
>
> Verify the way the operator will: `users().drafts().list(userId="me")` plus `labelIds` containing
> `DRAFT`, and the message absent from `SENT`. If REST works, **always prefer `drafts().create()`** —
> that path produced `labelIds: ['DRAFT']` first time, every time (uid-visible, PDF sha256 matched).
>
> Before declaring the REST token dead, actually try `Credentials.refresh(Request())`. On this host the
> token at `~/.chiper/skills/bounty-pack/google_token.json` carried `gmail.modify` + `gmail.send` and
> refreshed cleanly on 2026-10-25 despite a long-standing note that it was revoked; a stale note sent
> the whole engagement down the IMAP path for three findings. The wrong token is also easy to pick:
> `~/.hermes/google_token.json` is **calendar-only**, while `token_path()` resolves the AppData one
> under `$HERMES_HOME`.
>
> If IMAP really is the only route, check the Sent folder before reporting success, and delete the
> stray copies — a `Sent` copy of an unsent report is a delivery-audit false positive.

Use when `google_token.json` is calendar-only / refresh revoked (the REST
`drafts().create()` path in `stage_finding_draft.py` cannot run). Same deliverable:
one draft per finding, PDF attached, staged NOT sent.

## Recipe (imap_tools)

```python
import time, os, re, hashlib
from email.message import EmailMessage
from imap_tools import MailBox, MailMessageFlags

# resolve the App Password from the script that already works (masking tripwire)
SRC = os.path.expanduser("~/check_basabasi_email.py")
APP_PW = re.search(r'APP_PASSWORD\s*=\s*"([^"]+)"', open(SRC, encoding="utf-8").read()).group(1)

msg = EmailMessage()
msg["From"] = "RESEARCHER_NAME <RESEARCHER_EMAIL>"
msg["To"] = "report@vendor.com"
msg["Subject"] = subject
msg.set_content(body)
msg.add_attachment(open(pdf, "rb").read(), maintype="application", subtype="pdf",
                   filename=os.path.basename(pdf))

with MailBox("imap.gmail.com").login("RESEARCHER_EMAIL", APP_PW) as mb:
    drafts = next((f.name for f in mb.folder.list() if "draft" in f.name.lower()), "Drafts")
    mb.append(msg.as_bytes(), drafts, flag_set=[MailMessageFlags.SEEN, MailMessageFlags.DRAFT])
    time.sleep(10)                      # Gmail sync delay — verify too early = false FAIL
    mb.folder.set(drafts)
    match = [m for m in mb.fetch() if "<unique-subject-token>" in (m.subject or "")]
    for a in match[0].attachments:
        assert a.payload[:5] == b"%PDF-"
        assert hashlib.sha256(a.payload).hexdigest() == hashlib.sha256(open(pdf, "rb").read()).hexdigest()
```

## Pitfalls (all hit live 2026-10-25)
- **imap_tools signature is `append(message, folder='INBOX', dt=None, flag_set=None)`** —
  NOT `folder.append(raw, folder, flags=...)`. The `flags=` kwarg raises TypeError.
- **Sleep >=10s before read-back verification.** The first append succeeded but the
  immediate fetch found nothing ("VERIFY-FAIL") — the draft appeared seconds later.
- **Long subjects come back RFC-5322 folded, so `m.subject == subject` fails.** Gmail
  re-wraps anything past ~78 chars with CRLF+space; a byte-exact comparison reports
  "draft not visible" on a draft that staged perfectly (hit live 2026-10-25 with a
  99-char subject). Compare on a whitespace-collapsed copy:
  `re.sub(r"\s+", " ", (m.subject or "")).strip() == re.sub(r"\s+", " ", subject).strip()`
  — and the same normalization applies to the `To:`/`Cc:` tuples you print.
- **There is no single-uid fetch.** `mb.fetch("<uid>")` raises `StopIteration`. Fetch a
  window and match the uid yourself:
  `m = next(x for x in mb.fetch(limit=6, reverse=True) if x.uid == "<uid>")`.
  `mb.delete("<uid>")` *does* take the uid as a plain string — that is how you remove a
  duplicate left by a failed-verify attempt.
- **Pick the folder you actually append to, by name.** `[Gmail]/Draf` (Indonesian
  locale) and `[Gmail]/Drafts` can both appear in `folder.list()`; a "draft" substring
  match is not enough and a draft appended to the wrong one is invisible in the UI.
  Resolve the exact name first, append to it, and read back from that same variable.
- **Read back more than the hash.** Assert attachment sha256 + `%PDF-` (as above), and
  additionally `To`/`Cc` + a greeting marker and the signature name in `m.text` — a
  draft with the right PDF and an empty/mangled body is still a rejected deliverable.
- **Dedup by subject.** A failed-verify attempt that actually appended leaves a
  duplicate; delete all but the newest (`mb.delete([uid])` on the older ones).
- Working script from the mail.com engagement:
  `D:/data hermes/mail-com-audit/stage_draft_imap.py` (subject/body/to/attachments as
  argv, verify + dedup built in).
