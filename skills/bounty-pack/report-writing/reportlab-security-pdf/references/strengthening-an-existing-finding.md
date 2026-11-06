# Strengthening an already-staged finding (and re-staging it safely)

Referenced from SKILL.md's STRENGTHENING PASS section. Written after the Gasunie engagement
(2026-10-14), where a finding already staged as a Gmail draft gained new corroborating evidence and
had to be rebuilt and re-staged without producing a duplicate draft.

## When this applies

A finding is already staged (draft + PDF attached). During continued work you find **new evidence for
the same root cause** — a second emission point, a framework message that states the risk in its own
words, an independent scanner rule firing on a different input.

That is **not** a new finding. RULE 0 is not suspended by a strengthening pass: same root cause ⇒ same
draft, rebuilt. A genuinely *different* root cause ⇒ its own draft and its own PDF.

**The same-root-cause test.** Ask: if the vendor fixes the thing I named in the remediation section,
does the new evidence stop being true?

- Yes → same finding. Fold it in. (Gasunie: the remediation named "missing generic error handling";
  the `/Error` page and the unhandled handler exception are both that one gap.)
- No → separate finding, separate draft.

## Method that produced the strengthening

1. **Read the scanner's own output file, not just its exit code.** A `nuclei` run whose process was
   killed mid-way had still written its findings to `-o`; everything in it was `[info]` hardening
   (missing security headers, cookie flags, SRI) — correctly dropped — *except* one rule,
   `aspnetcore-dev-env`, which named the same root cause as the staged finding. That single line was
   the strengthening.
2. **Fetch the application's own error page.** `/Error` answered `200` with the framework's own text:
   *"The Development environment shouldn't be enabled for deployed applications. It can result in
   displaying sensitive information from exceptions to end users."* A quote from the target's own
   output is stronger than the researcher's paraphrase, and it belongs in the report verbatim.
3. **Count independent confirmations.** Two unrelated inputs (the handler with malformed parameters,
   and the app's error page) plus one independent detector (the scanner rule) is three. Say so in the
   report: "the same missing generic error handling seen from two inputs, not two separate issues".

## Re-staging recipe

```
1. Edit report.md      -> add a supporting-evidence section AFTER the existing "Observed result"
                          (the skill's convention: new section 4b), never before it
2. Edit the body file  -> one paragraph, same framing, no new claim
3. GREP before building -> the five BAD_WORDS whole-word: watermark / draft / template /
                          evaluation copy / sample. Rephrase hits; never relax the checker.
4. Rebuild             -> the harness rebuilds the PDF from the markdown
                          (stage_finding_draft.py: <report.md> <Out.pdf> "<subject>" --to <addr>
                           --body <body.txt>). It does NOT accept a pre-built PDF — a hand-built one
                          is silently overwritten, so verify the PDF the harness produced.
5. Delete old draft    -> match by SUBJECT on format="full"; see below
6. Re-stage            -> same subject, so the vendor thread stays one thread
7. Gate                -> the four checks in "Verification gates"
```

### Delete the old draft by subject, not by id

Draft ids change between runs and appear in two shapes (`r-7371…` and `r7371…`), so matching on an id
is a trap. Match on the subject you are about to reuse:

```python
SUBJ_KEY = "<the exact subject string>"
for d in svc.users().drafts().list(userId="me", maxResults=50).execute().get("drafts", []):
    m = svc.users().messages().get(userId="me", id=d["message"]["id"], format="full").execute()
    h = {x["name"]: x["value"] for x in m["payload"]["headers"]}
    if SUBJ_KEY in (h.get("Subject") or ""):
        svc.users().drafts().delete(userId="me", id=d["id"]).execute()
```

Print the ids you removed. If the list is empty, you are editing the wrong subject and the re-stage
will duplicate.

`format="metadata"` returns `parts: []` for a draft that genuinely carries the PDF; it reads as
"attachment missing". Always verify with `format="full"`.

## Verification gates (all four, on the attached artifact)

1. `pdf_layout_check.py <pdf> --tokens "<researcher name>" "<finding id>"` → `problems=0`.
2. Rendered-text scans: no `&[a-zA-Z]+;` entities, no literal `</?(b|i|u|font|br)>` markup, no
   non-English words (the reports are English even when the operator and the vendor are not).
3. Attachment: magic `%PDF-` **and** `sha256` equal to the **local** file, downloaded via
   `messages/{msgId}/attachments/{aid}` (the part has `body.attachmentId`, not `body.data`).
4. Count: exactly one draft per subject. A second draft under the same subject is a duplicate the
   vendor reads as noise.

## Pitfall that bit in this session

`/Error` returning `200` does **not** mean the app is leaking there — that page was the *generic*
framework error page. The leak was in the handler, which answers with the exception text itself. Do not
upgrade the framing of the `/Error` page beyond what it proves: it corroborates the missing generic
error handling and identifies the runtime; it is not a second leak.
