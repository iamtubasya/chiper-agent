# Verifying a Gmail draft made through the REST API (attachments included)

Companion to `gmail-draft-via-api.md`. Creating the draft is the easy half; **proving the PDF survived** is
the half that catches mistakes. Verified 2026-10-12 on a 7-draft multi-finding engagement.

## The trap: an attachment has NO `body.data`

A `GET users/me/drafts/{id}?format=full` returns attachments as

```json
{"partId":"1","mimeType":"application/pdf","filename":"F1-Low-thing.pdf","body":{"size":8084,
 "attachmentId":"ANGjdJ80jmlPWG..."}}
```

There is **no inline `data`** for an attachment (only the text part has it). A verification loop that
walks `payload.parts` and counts a part *only when `body.data` exists* therefore reports "no attachment"
for a draft that is perfectly fine — and the expensive failure mode is re-staging it, which is how you
end up with two drafts for one finding. Match on `mimeType == "application/pdf"` + `filename`, and use
`attachmentId`.

## Recipe (stdlib only, no google libs)

```python
# create (see gmail-draft-via-api.md), then verify:
lst = api(at, "drafts?maxResults=25&q=" + urllib.parse.quote('subject:"[Low]"'))
for d in lst.get("drafts", []):
    full = api(at, "drafts/" + d["id"] + "?format=full")
    mid  = full["message"]["id"]                      # message id != draft id
    for p in (full["message"]["payload"].get("parts") or []):
        if p.get("mimeType") == "application/pdf":
            blob = base64.urlsafe_b64decode(
                api(at, f"messages/{mid}/attachments/{p['body']['attachmentId']}")["data"] + "==")
            assert hashlib.sha256(blob).hexdigest() == local_sha256[p["filename"]]
```

- `messages/{id}/attachments/{aid}` needs the **message** id, not the draft id — they differ.
- base64url-decode with padding (`+ "=="`); Gmail strips it.
- Compare sha256 against the file on disk. Byte size alone is not proof (and this is the assertion that
  makes "attachment verified" a fact rather than a hope).

## Assert ONE draft per finding — not "the append succeeded"

Per-subject count is the only check that catches both duplicate staging and silent replacement:

```python
for frag in ("Builder identity can be registered", "Session-relay webhooks",
             "Data Gateway serves repository files", "app.vana.com exposes internal"):
    ids = [x["id"] for x in api(at, "drafts?maxResults=10&q=" +
           urllib.parse.quote('subject:"%s"' % frag)).get("drafts", [])]
    assert len(ids) == 1, (frag, len(ids))
```

Search on a **short lowercased fragment** of the subject (`subject:"["` alone matches every bracketed
subject in the mailbox and buries your drafts in noise — the first run of this engagement printed 14
unrelated drafts and its own new ones scrolled past the `tail`). Fetch a few more than you need and
print `(subject, attachments)` for each hit so a miss is visibly a miss.

## Operational rules that came out of this engagement

- **Set `Message-ID` and `Date` explicitly** (`email.utils.make_msgid(domain="<engagement>.local")`).
- **Never send.** Drafts only; the operator reviews and sends.
- **`To:` only when the vendor policy names a working mailbox.** Verify it first: `nslookup -type=MX
  <domain>` (a live MX proves the domain accepts mail). Otherwise leave `To:` unset and report the
  channel options in chat.
- **Stage in batches with separate scripts** (`stage_drafts.py`, then `stage_drafts2.py`, …). A single
  re-runnable script that re-creates every earlier draft is a duplicate factory: the second run adds a
  second copy of findings you already staged. Idempotency here means "the script only ever touches the
  findings in its own list".
- After staging N findings, print the per-subject count table (subject | drafts | attachment | sha256
  match) and only then tell the operator it is done.
