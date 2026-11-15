# Rebuild + staging hygiene (Tacit report, 2026-10-27)

Two mechanics that cost cycles. Neither is caught by "the build exited 0".

## 1. Never inline captured evidence into the generator

A generator that embeds an evidence transcript as a Python literal **freezes that text at authoring
time**. Rebuilding then reproduces the OLD capture, so the PDF silently keeps claims already corrected.
On the Tacit report the evidence block was a `repr()` literal; an em dash from an older capture survived
two full rebuilds after the source file had been cleaned, and the layout gate passed both times.

```python
# WRONG — frozen at authoring time
add(CODE_BLOCK('...entire captured log inline...'))

# RIGHT — always the current capture
EVIDENCE_TXT = os.path.join(BASE, 'evidence', 'oracle-evidence.txt')
add(CODE_BLOCK(open(EVIDENCE_TXT, encoding='utf-8').read().strip()))
```

Detecting it: grep the generator for a very long single line —

```bash
awk 'length($0) > 2000 {print FILENAME": line "NR" is "length($0)" chars"}' poc/gen_report.py
```

A 4,000-character string literal is an inlined capture. Replace it with a runtime read.

Same discipline as "a build that succeeds is not a build that changed": after every rebuild, assert
something only the NEW content contains (the corrected figure, a changed date, a new metadata row).
The em dash was found exactly this way:

```python
pdf = "\n".join(p.get_text() for p in pymupdf.open(PDF))
assert not any(ord(c) in (0x2014, 0x2013) for c in pdf), "stale em dash survived the rebuild"
assert "1,249.385807246106253513" in pdf, "corrected total missing"
```

## 2. IMAP verification: `reverse=True`, and a timeout is not a failure

Two independent ways to end up with the wrong draft state, both silent.

### `mb.fetch(limit=N)` reads the OLDEST messages

It is chronological ASCENDING. A verification loop built on it inspects the oldest N, does not see the
draft just appended, and prints `drafts=0` — while the append had already succeeded (`APPENDUID` in the
response). That reads exactly like "append failed" and invites a pointless re-append.

```python
# WRONG
hits = [m for m in mb.fetch(limit=25) if FRAG in (m.subject or '').lower()]   # -> 0
# RIGHT
hits = [m for m in mb.fetch(reverse=True, limit=25) if FRAG in (m.subject or '').lower()]
```

### A script killed by a timeout may still have appended

Observed: a staging run hit the 300 s tool timeout and was killed; it had nonetheless completed
`mb.append(...)` first. The next run deleted "the superseded draft", re-appended, and left two. So:

- on timeout, **verify before retrying** — never assume a killed run did nothing;
- make cleanup enumerate every match and keep exactly one (newest).

```python
hits = [m for m in mb.fetch(reverse=True, limit=25) if FRAG in (m.subject or '').lower()]
print('found:', len(hits), [(m.uid, m.date) for m in hits])
for m in hits[1:]:                     # keep the newest, drop the rest
    mb.delete(m.uid)
hits = [m for m in mb.fetch(reverse=True, limit=25) if FRAG in (m.subject or '').lower()]
assert len(hits) == 1, len(hits)       # one finding, one current draft
```

### A draft in a plain `Drafts` folder is invisible in the UI

Gmail refuses `COPY` into its real Drafts folder:

```
[ALERT] Only Drafts can exist in the Drafts folder (Failure)
```

So a draft that landed in a plain `Drafts` folder (no `\Drafts` special-use flag, not shown in the web UI)
must be **deleted and `APPEND`ed** into the flagged folder — not moved. Enumerate and pick by flag:

```python
for f in mb.folder.list():
    if 'raft' in f.name.lower() or 'Drafts' in " ".join(sorted(str(x) for x in (f.flags or []))):
        print(f.name, f.flags)
# Drafts                \HasNoChildren            <- decoy, no flag
# [Gmail]/Draf          \Drafts \HasNoChildren    <- the real one (Indonesian locale)
```

### Staging script skeleton that survived all of the above

```python
msg = EmailMessage()
msg["From"], msg["To"], msg["Subject"] = em, TO, SUBJECT
msg["Message-ID"] = make_msgid(domain="<engagement>.local")   # unique, or Gmail revises the previous draft
msg["Date"] = formatdate(localtime=True)
msg.set_content(BODY)
msg.add_attachment(open(PDF, "rb").read(), maintype="application", subtype="pdf",
                   filename=os.path.basename(PDF))
bio = io.BytesIO(); BytesGenerator(bio).flatten(msg); raw = bio.getvalue()   # bytes, not as_bytes()

with MailBox("imap.gmail.com").login(em, pw) as mb:
    for folder in ("Drafts", DRAFT):          # clear strays in both
        try:
            mb.folder.set(folder)
            for uid in [m.uid for m in mb.fetch(reverse=True, limit=40)
                        if FRAG in (m.subject or '').lower()]:
                mb.delete(uid)
        except Exception:
            pass
    print(mb.append(raw, DRAFT, flag_set="\\Draft"))
    # ... then verify: count == 1, attachment sha256 == local, body markers present
```

Verify attachment byte-identity, not just presence:

```python
local = hashlib.sha256(open(PDF, "rb").read()).hexdigest()
assert hashlib.sha256(a.payload).hexdigest() == local, "attachment drifted from the local PDF"
```

## 3. Order that works

1. patch evidence/source → **rebuild PDF**
2. `qa_pdf_layout.py --margin-mm <MARGIN_pt*25.4/72>` → require `layout: clean`
3. assert new content is present + no stale markers
4. **only then** stage the draft (a rebuilt PDF is a changed PDF, so any earlier draft is stale)
5. delete superseded, append, verify count == 1 + sha256 match
