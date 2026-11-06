# Staging pitfalls and fixes (hard-won, 2026-10-20 djangoeurope session)

Each of these shipped a broken or duplicate deliverable once. Check them mechanically, every time.

## 1. A typo'd image path silently produces a PDF without the screenshot

Symptom: PDF is ~6KB instead of ~45KB; `build_pdf` reports success. The markdown image line
`![caption](abs/path.png)` is silently skipped when the path does not resolve (wrong drive prefix,
missing `_v1` in a workspace dir, MSYS `/c/...` vs native `C:/...`).

**Fix (mandatory post-build assertion):**
```python
data = open(pdf, "rb").read()
assert b"/Subtype /Image" in data or b"/Subtype/Image" in data, "screenshot NOT embedded"
```
Also sanity-check size: a report with an embedded full-page screenshot is typically >30KB.
A ~6KB "clean layout" PDF is the tell.

## 2. Re-running the stager creates a SECOND draft (never updates in place)

`stage_finding_draft.py` always calls `drafts().create()`. Fixing a staged finding by re-running
the script leaves the old draft AND a new one in the mailbox. The operator sees duplicates.

**Fix:** after re-staging, delete the stale draft by id (`drafts().delete(id=...)`) and assert
exactly one draft per subject remains via `messages().list(labelIds=['DRAFT'])`. For in-place
fixes of an existing draft, build the raw MIME and `drafts().update(id, ...)` instead.

## 3. Body validator requires the literal channel phrase

The rule-0c validator checks for `"responsible disclosure"` (plus `"independent security
researcher"` and the signature name). A body that says "sending this report to your security
address" is REJECTED even though it describes the same thing. Use the exact phrase
"through your responsible disclosure programme/channel at <url/address>".

## 4. Gmail token file: expiry deserializes as int after refresh

`Credentials.from_authorized_user_file()` raises `AttributeError: 'int' object has no attribute
'rstrip'` when the token JSON's `expiry` is a unix int (happens after some refresh paths).

**Fix:**
```python
d = json.load(open(tok))
if isinstance(d.get("expiry"), (int, float)):
    d["expiry"] = datetime.datetime.fromtimestamp(d["expiry"], datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(d, open(tok, "w"))
```

## 5. The output redactor masks secrets in DISPLAY, not in files

Passwords/tokens shown in tool output appear as `cekChr...aB1!` (literal dots) while the file on
disk holds the full value. Never re-type a credential from displayed output; read the file. When
capturing request bodies for evidence, expect the display to be redacted and say so in the
evidence file if needed.

## 6. Windows/MSYS path traps in evidence scripts

- Windows Python cannot read MSYS `/tmp/...` paths; write artifacts under the workspace dir.
- `ssh-keygen -f /tmp/x` writes where bash python can't read; use a workspace-relative path.
- Heredocs break on: backticks inside JS template literals, `\\n` escape chains, and single quotes
  inside triple-single-quoted Python. Build JS payloads with `chr(10)` and pass arrays as
  `page.evaluate(js, [args])` instead of embedding literals.
