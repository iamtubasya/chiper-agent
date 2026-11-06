# Pre-submission review gate + the Gmail drafts-folder trap

Provenance: 2026-10-27, Tacit `TacVault` report. The operator opened the review turn with
*"cek lg draft nya sdh sesuai rules submit blm, dan apakah benar submit k email, tata bahasanya
gmn, isinya jg udh bagus kah poc nya?"* — four separate questions, and the honest answer to the
first one was **no** (the body carried no steps to reproduce, which is one of the three things the
policy explicitly demands). Treat that question as an instruction to re-audit the deliverable with
assertions, not to read it again.

---

## Part A — the five-part review gate

Run all five and report each as PASS/FAIL in the reply. Each one has caught a real defect.

### 1. Channel — prove it from two published sources

```bash
curl -s https://<host>/.well-known/security.txt
# Contact: mailto:security@tacit.finance
# Expires: 2027-09-30T00:00:00.000Z
# Preferred-Languages: en            <- settles the language of the body
# Policy: https://github.com/<org>/<repo>/blob/main/SECURITY.md
```

Then read `SECURITY.md` itself for the same address. Two sources agreeing is the proof; one is a
guess. It also tells you the FORM case does not apply here.

Detect the form case before concluding "email is correct":

```bash
curl -s "$POLICY_URL" | grep -oiE 'href="[^"]*\.(docx|doc|pdf|odt)[^"]*"'
curl -s "$POLICY_URL" | grep -oiE '(complete|fill|submit)[^.]{0,80}(form|request|template)[^.]{0,40}'
```

A hit on either means a separate deliverable exists (see
`submission-form-and-scope-anchoring.md`). Tacit's policy has neither: prose only, address only.

### 2. Policy field list, asserted over the STAGED draft

Tacit `SECURITY.md`, verbatim: *"Include what you found, where it is, and the steps to reproduce
it. Please keep it private until it is fixed."* That is a literal triple. Turn it into assertions:

```python
gate = [
 ("channel = published mailbox", "security@tacit.finance" in body and "security@tacit.finance" in pdf),
 ("'what I found'",             "What I found" in body and "stopped recording" in body),
 ("'where it is' (addresses)",  all(a in body for a in (V1, PAIR, V2))),
 ("'steps to reproduce'",       "Steps to reproduce" in body and "Steps to reproduce" in pdf),
 ("'private until fixed'",      "keeping it private" in body),
 ("English only",               not any(w in body.lower() for w in ("yang ","tidak ","adalah "))),
 ("PDF has a figure",           sum(len(p.get_images()) for p in fitz.open(pdfp)) >= 1),
 ("no reward/bounty wording",   not re.search(r"\bbounty\b|\breward\b|\bcompensation\b", body+pdf, re.I)),
]
```

The failure this catches: version 1 of the body had the finding and the addresses but pushed the
reproduction into the PDF's Section "Steps to reproduce" and mentioned it only as *"the full
write-up is attached"*. The policy asks for the steps **in the report**, so the three-line
condensed version belongs in the body too. Mirror the policy sentence; do not paraphrase its
absence.

### 3. Body typography lint — deterministic, catches what reading misses

```python
assert max(len(l) for l in body.split("\n")) <= 76
stray   = [l for l in body.split("\n") if "  " in l.strip() and not l.startswith("  ")]
trail   = [l for l in body.split("\n") if l != l.rstrip()]
repeat  = re.findall(r"\b(\w+)\s+\1\b", body, re.I)
dot     = [l for l in body.split("\n") if l.startswith(".")]        # URL wrapped at a dot
punct   = re.findall(r"\s+[,.;:]", body)
blanks  = body.count("\n\n\n")
banned  = [t for t in ["\u2014","\u2013","delve","pivotal","testament","leverage","seamless"]
           if t.lower() in (body + pdf).lower()]
```

Defects actually found this session: `\n\n\n` runs from a naive join; `.well-known/security.txt`
wrapped so a line began with `.well-known`; no blank line before a bullet list and none before the
signature block; and `security@tacit.finance` appearing in the PDF but not in the PDF's meta table
(the mailbox belongs in "Sent to" *and* in the scope section).

Fix the wrapping at the source, not by hand-reflowing afterwards:

```python
textwrap.fill(t, width=74, initial_indent="  - ", subsequent_indent="    ",
              break_on_hyphens=False, break_long_words=False)
```

`break_on_hyphens=False` is what stops `.well-known` and long hex addresses from splitting.

### 4. Arithmetic re-check — every number, to 12+ decimals

The report is a measurement document; a hand-typed total is a credibility hole. Recompute from the
raw reads and diff:

```python
tot = 639.680028162796876634 + 609.705779083309376879          # two vault balances
abs(tot - 1249.385807246106253513) < 1e-12                    # vs the string in the PDF
tot * 66643301542025 / 1e18                                    # vs "about 0.0833 ETH"
541*50*12/86400, 1053*50*12/86400                              # vs "3.76" and "7.31"
118354072967904 / 63200656445905                               # vs "1.87"
525725-525184, 525725-524672                                   # vs "541" and "1,053"
```

Also assert the derived strings are actually IN the built PDF
(`all(s in pdf for s in ("541 intervals","1,053","3.76","1.87"))`) — a generator rewrite that drops
a section still builds cleanly.

### 5. Liveness re-check at submission time

```bash
cast block-number --rpc-url $RPC
cast call $PAIR "latest()(uint256)"       # must still be 0
cast call $PAIR "prices(uint256)" 28800   # must still revert 0xa889a81f
```

A finding that decayed since discovery is `UNSTABLE` and does not ship. Print the block number in
the report so the reader knows the claim is a snapshot, not an invariant.

---

## Part B — Gmail drafts: the folder must be chosen by the SPECIAL-USE flag

The older guidance ("enumerate the candidate folders, pick the one holding the most messages")
**picks the wrong folder**, and the reason is circular: the first `append` creates the stray
message that inflates the count. Observed on an Indonesian-locale Gmail:

| folder | `\Drafts` flag | UI-visible | holds |
|---|---|---|---|
| `Drafts` | no | no | nothing the user sees (my stray draft landed here) |
| `INBOX.Drafts` | no | no | empty |
| `[Gmail]/Drafts` | no | no | empty |
| **`[Gmail]/Draf`** | **yes** | **yes** | the user's real drafts |

```python
folder = next(f.name for f in mb.folder.list()
              if "\\Drafts" in " ".join(sorted(str(x) for x in (f.flags or []))))
```

### Two hard constraints

1. **Appending into the unflagged `Drafts` makes a draft the user cannot find.** Your fetch-back
   verification passes (the message IS there) while the operator reports *"kok sy gk ketemu"*.
   Verify by listing **every** candidate folder and printing the per-folder count, not by finding
   your own message.
2. **`COPY`/`MOVE` into the special-use folder is refused**:
   ```
   imap_tools.errors.MailboxCopyError: Response status "OK" expected, but "NO" received.
   Data: [b'[ALERT] Only Drafts can exist in the Drafts folder (Failure)']
   ```
   You cannot relocate a stray draft. **Delete it, then `append` fresh.** Do this unconditionally
   whenever the subject already exists in any folder, so a re-stage never leaves two generations:

   ```python
   for folder in ("Drafts", DRAFT):
       mb.folder.set(folder)
       for uid in [m.uid for m in mb.fetch(limit=40) if "tacvault" in (m.subject or "").lower()]:
           mb.delete(uid)
   mb.append(raw, DRAFT, flag_set="\\Draft")
   ```

### Re-staging is normal, not a failure

Three re-stages happened in one session (finding corrected → PDF rebuilt → body rewritten), and
each one required delete-then-append plus a fresh `sha256` assertion. That is the correct cost of
the review gate. See `per-finding-split-and-draft-hygiene.md` for the `Message-ID` trap that runs
alongside this one.

### The generator must read evidence at build time

A generator that carries the captured evidence as a pasted literal
(`add(CODE_BLOCK('<4400-char paste>'))`) has no invalidation signal: corrections to
`evidence/*.txt` are ignored, and a character you just stripped from the file reappears in the
rebuilt PDF, which reads like your sweep failed. Always:

```python
add(CODE_BLOCK(open(BASE + "/evidence/run.txt", encoding="utf-8").read().strip()))
```

and after any rebuild assert a string only the new evidence contains (`"525184" in pdf_text`). A
build that succeeds is not a build that changed.
