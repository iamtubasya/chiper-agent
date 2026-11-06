# Gmail draft send failures — the account-pinning trap and its siblings

Worked example: PubNub engagement, 2026-10-31. Two staged drafts (`F6` High, `F7` Medium)
failed to send with `HttpError 404 ... Requested entity was not found` on draft IDs that
`drafts().list()` displayed plainly. Nothing was wrong with the drafts.

## Root cause: `send-draft` resolves the DEFAULT account, not the draft's account

`gmail_ops.py send-draft <id>` calls `pick_service(None)`, which returns `accts[0]` —
whatever account sorts first in `account_files()`. On this host that is **not** the bounty
account. The CLI therefore looked for the draft in the wrong mailbox and reported 404.

```
$ python gmail_ops.py send-draft r6540703514995499059
googleapiclient.errors.HttpError: <HttpError 404 ... "Requested entity was not found.">

$ python -c "import gmail_ops as G; print([l for l,_ in G.account_files()])"
['akun3', 'akun4', 'RESEARCHER_NAME2', 'RESEARCHER_USERNAME']      # <- akun3 is the default
```

Memory already carried this ("DRAFT BOUNTY=RESEARCHER_USERNAME (akun3 SALAH)") but the CLI wrapper
was still used out of habit. **The wrapper's default is a trap; pin the account explicitly.**

## The fix — list, confirm, then send through the API

```python
import gmail_ops as G

label, svc = G.pick_service("RESEARCHER_USERNAME")        # pin the bounty account explicitly

d = svc.users().drafts().list(userId="me", maxResults=15).execute()
print("drafts on", label, ":", len(d.get("drafts", [])))
for x in d.get("drafts", []):
    m = svc.users().messages().get(
        userId="me", id=x["message"]["id"],
        format="metadata", metadataHeaders=["Subject"]).execute()
    subj = next((h["value"] for h in m["payload"]["headers"] if h["name"] == "Subject"), "")
    print(" ", x["id"], "|", subj[:80])          # confirm the ID is really there

for did in ["r6540703514995499059", "r3098684001586345733"]:
    r = svc.users().drafts().send(userId="me", body={"id": did}).execute()
    print("sent:", did, "-> message id", r["id"], "label", r.get("labelIds"))
# -> sent: r6540703514995499059 -> message id 1a1900df483b5018 label ['SENT']
```

## Then verify the SENT artefact, not the send call

`drafts().send()` returning a message ID means Gmail accepted the operation. It does not
prove the recipient got the right thing. Re-read by message ID and assert on the stored
message:

```python
for mid in ["1a1900df483b5018", "1a1900df90bad92d"]:
    m = svc.users().messages().get(userId="me", id=mid, format="full").execute()
    h = {x["name"].lower(): x["value"] for x in m["payload"]["headers"]}
    atts = [p["filename"] for p in m["payload"].get("parts", []) if p.get("filename")]
    print("id      :", mid)
    print("to      :", h.get("to"))
    print("subject :", h.get("subject", "")[:95])
    print("labels  :", m.get("labelIds"))        # must contain SENT
    print("attach  :", atts)                     # must list the PDF, right filename
```

Check, in order: `labelIds` contains `SENT`; `To` is the vendor address; the subject is
the final one; the attachment list names the expected PDF; and the body length matches
what was written. A draft that "sent" with no attachment part is the failure this catches.

## Sibling failure modes hit on the same run

| Symptom | Cause | Fix |
|---|---|---|
| `404 "Message not a draft"` on send | draft already went earlier in the session | check `drafts().list()` and SENT before re-sending, or you file the same finding twice |
| draft vanishes after several `drafts().update()` cycles | repeated in-place updates can silently destroy it | build the full MIME once and `drafts().create()`; to revise, create a new draft and delete the superseded one |
| duplicate drafts with near-identical subjects | re-running a staging script | delete by subject before re-staging; assert **1 draft per finding** |
| `json.loads` crash on draft delete | Gmail returns an **empty body** for `DELETE users/me/drafts/<id>` | guard the parse; an empty body is success |

## Rules

1. **Pin the account in every Gmail call.** Never rely on the wrapper's default. If the
   wrapper has no account flag, call the API directly as above.
2. **List before you send.** One `drafts().list()` confirms the ID exists on the account
   you are about to send from, and surfaces duplicates you would otherwise file twice.
3. **Verify the sent message by ID** — labels, recipient, subject, attachment, body length.
   The send call returning OK is not proof.
4. **One finding = one draft = one PDF.** When a finding is upgraded, delete the superseded
   draft and stage the replacement so only one version of each exists.
