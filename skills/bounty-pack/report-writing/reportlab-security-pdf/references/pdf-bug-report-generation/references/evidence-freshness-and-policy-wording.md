# Evidence freshness, and the "no bounty wording" gate

Two failure modes that both produce a report that *looks* finished. Both were caught only because a
string-level assertion was run over the **built artefact**, never over the generator source.

## 1. Never paste evidence INTO the generator — read it at build time

A generator written this way freezes the capture at authoring time:

```python
ev = open(BASE + r"\evidence\oracle-evidence.txt").read()   # runs ONCE, when the file is written
emit("add(CODE_BLOCK(" + repr(ev) + "))")                   # frozen into gen_report.py as a literal
```

Sequence that bit twice in one engagement: fix the evidence file (an em dash, and a corrected claim) →
re-run the generator → it prints a new byte count and "succeeds" → the PDF still renders the OLD text,
because the fresh read never happened. `repr()` of a 4 KB capture is also what makes those generator
files 14 KB of unreadable one-liners, which is why the patch is easy to get wrong afterwards.

Fix — read inside the story builder:

```python
emit("add(CODE_BLOCK(open(r'<abs>/evidence/oracle-evidence.txt', encoding='utf-8').read().strip()))")
```

Assertion that catches it (run on the artefact, not the source):

```python
import pymupdf
pdf = "\n".join(p.get_text() for p in pymupdf.open(pdf_path))
assert "541 intervals" in pdf        # a string ONLY the corrected evidence contains
assert not any(ord(c) in (0x2014, 0x2013) for c in pdf)   # the characters you just removed
```

A build that succeeds is not a build that changed. This is the same family as the `re.sub`-patch trap in
SKILL.md: verify the output, and prefer rewriting the generator over string surgery on it.

Related hygiene that the same assertion loop catches cheaply:

```python
assert not re.findall(r"&[a-zA-Z]+;", pdf)          # entity artefact
assert not [l for l in body.split("\n") if l.startswith(".")]   # wrapped ".well-known/..." starts a line with a dot
assert "\n\n\n" not in body                          # double blank line from a re-wrap
assert max(len(l) for l in body.split("\n")) <= 78   # after re-wrapping, re-check
```

Wrapping is what introduces the last three: `textwrap.fill` will happily begin a continuation line with
`.well-known/security.txt` or leave a stray blank when paragraphs are re-emitted. Fix by rebuilding the
body from structured blocks (`("p"|"b"|"n"|"sig", text)`) rather than re-wrapping prose in place.

## 2. "No reward / no bounty wording" traps on honest scope prose

The pre-staging gate greps for `bounty|reward|compensation`. This sentence, written in good faith in the
scope section, **fails it**:

> "Reported under the bug bounty described in the project's SECURITY.md, which pays for information…"

Accurate, and still reads to a triager as soliciting. The operator's rule is to never raise the subject.
Say the channel and drop the programme entirely:

> "Sent privately to `security@<vendor>`, the contact published in the project's `SECURITY.md` and in the
> `security.txt` at the site root, which asks for private disclosure until a fix ships."

Two mechanical consequences, both easy to miss:

- The word appears in the **PDF** as well as the email (my first version had it only in the PDF's scope
  paragraph, so the email passed and the PDF failed). Grep both.
- Put the mailbox in the PDF meta table as `Sent to | security@…`. The gate asserts the address appears
  in **both** artefacts, and a report whose PDF never names the destination is one triage cannot file.

```python
hits = re.findall(r"\bbounty\b|\breward\b|\bcompensation\b", body + pdf, re.I)
assert not hits, hits
assert "security@<vendor>" in body and "security@<vendor>" in pdf
```

## 3. Which channel is real — verify it twice

Do not infer the mailbox from the repository name or from a `SECURITY.md` alone. Two independent sources
that agree, or it is a guess:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<host>/.well-known/security.txt
curl -s https://<host>/.well-known/security.txt    # Contact:, Expires:, Preferred-Languages:, Policy:
```

`security.txt` also answers the language question (`Preferred-Languages: en` — write in English even when
the operator and the vendor share another language) and gives an `Expires:` you can cite for currency. If
both the repo `SECURITY.md` and the live `security.txt` name the same address, that is the channel; note
both in the report. If they disagree, say so in the email rather than picking one silently.
