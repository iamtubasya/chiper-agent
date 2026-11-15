# The Message-ID trap ALSO fires on the REST path (`drafts().create()`) — hit live 2026-10-13

The SKILL.md warnings describe the silent draft replacement as an **IMAP `append`** problem. It is not
IMAP-specific. Reproduced on the Gmail REST path with the operator's own staging helper.

## What happened (Arrakis engagement, 2 findings)

1. Finding F1 was staged with a helper that built the MIME with `EmailMessage()` and **no `Message-ID`**:
   `POST users/me/drafts` -> `{"id": "r-5210246277126474992"}`. Read back, verified, attachment hash
   matched, `To:` correct. Looked done.
2. Finding F2 was staged the same way minutes later -> `{"id": "r-965476603062793082"}`. Also verified.
3. A per-subject audit then showed **F1 gone**: `drafts().list()` returned exactly one Arrakis draft.
   F2 had replaced F1. No error, no warning, both `create()` calls returned success.

So the dedupe-by-absent-Message-ID behaviour lives in the API, not in IMAP.

## Fix (now inside `scripts/stage_finding_draft.py`)

```python
from email.utils import make_msgid, formatdate
msg["Message-ID"] = make_msgid(domain="report.local")   # unique per draft — REQUIRED on REST too
msg["Date"] = formatdate(localtime=True)
```

Backup of the pre-patch script: `scripts/stage_finding_draft.py.bak_msgid_20261013_011100`.

## Two corollaries that matter more than the fix

- **Stage N drafts, THEN assert N live subjects in one pass.** The "stage one, verify one" loop is what
  hides this bug: each individual verification passes, and the loss only appears once a *later* draft
  lands. Count by subject (`drafts().list()` + metadata `Subject`) after the whole batch.
- **`Message-ID: NONE` in the metadata view is NOT evidence of a missing header.** After the fix the
  metadata read-back still showed `MSGID: NONE` — Gmail normalises the header on API-created drafts.
  The authoritative proof is (a) one draft per subject and (b) `sha256(attachment) == sha256(local pdf)`
  read back via `messages().attachments().get()`. Do not "fix" a draft that is already correct.

## Related trap in the same helper: body rule 0c

`stage_finding_draft.py --body` validates the body before staging and aborts with
`BODY REJECTED (rule 0c)`. It requires the literal phrase **"responsible disclosure"** and a signature,
and it **bans the words `bounty`, `reward`, `credit`, `swag`, `hall of fame`** (word boundaries, on a
URL-stripped copy) plus the usual AI-isms. A body that says "I could not find a bug bounty programme"
is rejected on the word `bounty`. Reword to "published vulnerability disclosure policy".
