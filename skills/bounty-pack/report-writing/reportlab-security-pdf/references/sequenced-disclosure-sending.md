# Sending a batch of disclosure drafts — one at a time, on a gap, with recovery

Staging is not sending. This file covers the phase AFTER the PDFs and drafts exist: getting N drafts out
the door in sequence, proving what actually left, and recovering when the runner dies mid-batch.

Derived from the mydays.de engagement (2026-10-12/13): 4 findings, 4 Gmail drafts, sent 30 minutes apart
on the operator's instruction, one runner killed by a host-side socket abort at the 2nd send.

## 1. The operator's cadence rule

Operator instruction, verbatim: ***"ok kirim, sesuai saran kamu, kasih jeda 30 menit setiap send
draftnya"***. What that means in practice:

- **One draft per send.** Never batch the whole set into one runner call that fires them back-to-back.
  A vendor receiving four reports in the same second reads automation, and the reports are then triaged
  as one noisy thread instead of four findings.
- **Gap between sends, not between attempts.** 30 minutes here; make it a parameter
  (`SEND_GAP`, default 1800) so the cadence is a knob, not a hardcoded sleep.
- **Run it in the background and let it be quiet.** The whole batch is ~90 minutes of sleeping. Launch
  it as a background process with completion notification, then stop narrating each step to the
  operator — they asked for the cadence, they do not need a message per send.

```python
GAP = int(os.environ.get("SEND_GAP", "1800"))
for idx, (fid, pdfname, key) in enumerate(ORDER):
    ...send...
    if idx < len(ORDER) - 1:
        log(f"{fid} sleeping {GAP}s ({GAP/60:.0f} min) before the next send")
        time.sleep(GAP)
```

## 2. Pre-send check: re-verify the attachment on EVERY send, not once at staging time

Between staging and the send that happens 60 minutes later, the PDF on disk can change (a rebuild after a
layout-gate failure, a re-staged draft after an edit). Re-hash immediately before sending and abort that
finding rather than sending a stale file:

```python
local = open(os.path.join(ENG, pdfname), "rb").read()
want  = hashlib.sha256(local).hexdigest()
d     = svc.users().drafts().get(userId="me", id=did, format="raw").execute()
msg   = email.message_from_bytes(base64.urlsafe_b64decode(d["message"]["raw"] + "=="))
att_ok = any(p.get_filename() == pdfname and
             hashlib.sha256(p.get_payload(decode=True) or b"").hexdigest() == want
             for p in msg.walk() if p.get_filename())
to_ok  = msg["To"] == "it-security@<vendor>"
if not (att_ok and to_ok):
    log(f"{fid} ABORT: pre-send check failed (att={att_ok} to={to_ok})"); continue
```

This is the same `%PDF-` + sha256 pair as the staging read-back, moved to the last possible moment.

## 3. Send-level idempotency: ask the SENT folder, never trust the script's own log

The failure that motivates this section: the runner had logged
`MD-C2 SENT … / sleeping 1800s` and then died. Did MD-C2 go out? **The log cannot answer that** — the
line is written before the sleep, and the send that killed the process may or may not have completed
server-side.

Ground truth is the mailbox. Before sending anything, list the SENT folder per subject:

```python
res = svc.users().messages().list(userId="me", q=f'in:sent subject:"{key}"', maxResults=10).execute()
already = len(res.get("messages", []))
```

Observed on the recovery run — this is the shape of a correct answer:

```
MD-C1: messages in SENT matching subject = 1     <- already out, do NOT resend
MD-C2: 0
MD-C3: 0
MD-C4: 0
to send now: ['MD-C2', 'MD-C3', 'MD-C4']
```

So the recovery runner is the *same* script with `todo = [x for x in ORDER if sent_map[x[0]] == 0]`.
That makes the whole batch safe to re-run at any point: it sends what is missing and nothing else. This is
the send-phase analogue of the draft-level "adopt by subject" self-heal, and it is what makes an aborted
batch recoverable instead of duplicating mail to a vendor's security team.

Also re-check at the end, per finding, and report the count — not the ids:

```
=== final SENT check
  MD-C1: sent=1   MD-C2: sent=1   MD-C3: sent=1   MD-C4: sent=1
```

Sweep for subject *variants* too if there is any chance a finding got staged under two subjects.

## 4. Transient socket aborts: retry, do not declare failure

`ConnectionAbortedError: [Errno 10053] An established connection was aborted by the software in your
host machine` inside `httplib2`/`ssl.sendall` is a **host-side** error, not a rejection. It aborted this
batch exactly at the second send and looked like a Gmail problem.

Wrap every API call (draft lookup, get, send, list) in a retry, and log the attempt so a genuine
persistent failure is distinguishable from a blip:

```python
def retry(fn, tries=5, wait=20):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            log(f"  transient error (try {i+1}/{tries}): {type(e).__name__}: {str(e)[:90]}")
            time.sleep(wait)
    raise last
```

Note the `lambda` capture: `retry(lambda k=key: svc.users().messages().list(...q=f'subject:"{k}"...))` —
bind the loop variable as a default argument or every retry re-uses the last iteration's value.

## 5. Verification failures are hypotheses — inspect the match before "fixing" anything

Two false positives hit the same batch, both of which would have corrupted correct deliverables:

| Reported FAIL | Reality |
|---|---|
| `no reward-ask: FAIL` on all four bodies | the matched word was `bounty` inside the **cited policy URL** `https://…/Bug-Bounty-Policy-1.3.pdf`. The bodies contain no compensation request. |
| `no reward-ask: FAIL` / `credit` | product vocabulary, not a reward ask |

The fix belongs in the *checker*, not the document: strip URLs before the scan and match on word
boundaries.

```python
scan = re.sub(r"https?://\S+", " ", body.lower())
reward = [t for t in ("bug bounty", "bounty", "reward", "hall of fame", "swag", "credit")
          if re.search(r"\b" + re.escape(t) + r"\b", scan)]
```

Same principle as the `pdf_layout_check.py --tokens` case-sensitivity rule in the SKILL: **grep the
extracted text for the match and read its context before rewriting the document.** A checker that
produces a false FAIL on a correct artifact is worse than no checker, because the "fix" damages a good
report.

## 6. Dedupe duplicates by choosing the one that matches the CURRENT local file

Re-staging after an edit leaves two drafts with the same subject. Do not keep the newest id and do not
keep the first one — keep the one whose attachment hash equals the local PDF, delete the rest, then
assert exactly one remains:

```python
keep, drops = None, []
for h in hits:                      # all drafts matching the subject
    body, sha = parts(raw_of(h["id"]))
    if sha == want_sha and keep is None: keep = h["id"]
    else:                                drops.append(h["id"])
for did in drops:
    svc.users().drafts().delete(userId="me", id=did).execute()   # response body is EMPTY: never json-parse it
```

Print the per-finding count afterwards (`{'MD-C1': 1, 'MD-C2': 1, 'MD-C3': 1, 'MD-C4': 1}`) and state
RULE 0 HELD only when every value is 1.

## 7. Final independent audit — read SENT, not the runner's stdout

After the batch completes, re-audit from the mailbox as a separate script. This is what proves the
deliverable, and it catches a runner that "succeeded" while sending a stale attachment:

```python
m = svc.users().messages().get(userId="me", id=msg_id, format="raw").execute()
msg = email.message_from_bytes(base64.urlsafe_b64decode(m["raw"] + "=="))
att = [(p.get_filename(), len(p.get_payload(decode=True) or b""),
        hashlib.sha256(p.get_payload(decode=True) or b"").hexdigest() == want)
       for p in msg.walk() if p.get_filename()]
print(f"[{fid}] to={msg['To']}  att={att}")
```

Expected output shape — one line per finding with `to=`, one attachment, and `True` on the hash:

```
[MD-C1] to=it-security@vendor  att=[('JSMG-MD-C1-Medium.pdf', 7066, True)]
…
ALL FOUR SENT EXACTLY ONCE, ATTACHMENTS MATCH LOCAL PDFs: YES
ATTACHMENT COUNT PER MESSAGE: 1 (no bundling)
```

Report *that*, not "the script said it sent them".

## 8. Interactive-CLI output truncation is not evidence of progress

A background job's captured output can arrive truncated ("Showing last 1902 chars") right at a failure.
Do not infer what happened from the tail you were given — read the persistent log the runner writes
(`send-log.txt`, one timestamped line per action) or query the mailbox. The log file and the SENT folder
are the two durable records; the process stdout is neither.
