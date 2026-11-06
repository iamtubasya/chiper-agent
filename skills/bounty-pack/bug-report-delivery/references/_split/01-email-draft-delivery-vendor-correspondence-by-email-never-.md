## Email-draft delivery (vendor correspondence by email) — NEVER SEND without an explicit go-ahead

**Hard rule from the user, stated repeatedly: never send a finding or report by email on your own
initiative.** Always write it into the mailbox as a **draft** and let the user send it personally.
This covers first reports, replies to a vendor triager, follow-ups after a fix, and any re-send after
corrections.

**Stage the draft as part of the deliverable — do not stop at offering it.** For this operator the
finished artifact of a finding is *the PDF plus the draft sitting in the Draft folder*; asking
"shall I make the draft?" just costs a round trip. Once a finding has survived the gate and the PDF
is verified, write the draft, verify it by enumeration + byte size, and report the uid — the operator
presses send. Two guardrails keep this safe: staging is non-destructive and reversible, and the
never-send rule above is absolute. When several findings exist, stage one draft per finding in the
same pass rather than one draft per conversation turn. Prefer **updating the existing draft** over writing another one — three variants of the
same report in the Draft folder gets the wrong one sent.

### The ONE permitted exception — explicit, per-message, after "I finished reading"

The user's exact refinement (2026-10): *"jalankan kirim kalau sy udh konfirmasi selesai di baca,
hardrule y ttp"* — sending is allowed, but ONLY once the user confirms they have finished reading,
and ONLY for the specific item(s) they name.

- A casual one-liner ("kirim aj", "go ahead", "send it", "ok kirim") is **not** that confirmation.
  The user had already said "I read it, send it" and *still* restated the hard rule afterwards. When
  it is ambiguous, do not send — name the finding(s) and wait for an explicit yes.
- Never treat "buat aj" / "buat aja" (make them) as permission to send — that is permission to
  *generate* the artifact only.
- **Gate the sender script itself** so it cannot fire by accident, and never remove the guard or set
  the env var on a general instruction:
  ```python
  import os, sys
  if os.environ.get("I_CONFIRM_USER_FINISHED_READING") != "yes":
      sys.exit("REFUSING TO SEND - hard rule: send only after the user confirms they finished reading.")
  ```
- **If you send by mistake:** say so plainly and immediately, and reconcile reality instead of
  guessing — you cannot unsend, so the honest move is to read the Sent folder and report exactly
  which messages exist. (Observed 2026-10: one message sent in error; the formal apology + the
  factual Sent-folder list is what the user needed, not a retraction attempt.)

### Platform-based programs (Immunefi / HackenProof): there may be NO recipient — never invent one

Before drafting, establish the channel. Platform programs (Immunefi, HackenProof, HackerOne,
Bugcrowd) take submissions through their **dashboard**, and the policy page often publishes no
security e-mail at all. Confirmed 2026-10 on Immunefi/DeXe: the repo's `README`/`audits/`/`.github/`
contained no contact address, and the program's own page lists only the dashboard + vault address.

Rules:

1. **Do not fabricate a recipient.** Guessing `security@<vendor>` sends a live vulnerability report to
   an address that may be unmonitored or wrong — a real harm, not a cosmetic one. Probed options that
   consistently come up empty for crypto programs: the repo's `SECURITY.md`, `audits/README.md`,
   `.github/`, and the policy page itself.
2. **Leave `To:` unset and say so.** A draft with a subject, verified body and attached PDF is a
   complete deliverable; the operator fills one field. State the channel choices in your reply rather
   than in the letter — the body must read like it was written to the team, with no meta-notes in it.
3. **Check for a mirror program.** The same target is frequently listed on a second platform with the
   same cap (found 2026-10: the DeXe program exists on **both** Immunefi and HackenProof, both up to
   $500k). Worth surfacing as an alternative route, and worth checking whether the operator already
   has an account with one of them before writing to a mailbox that does not exist.
4. **The introduction rule still applies to platform reports**, not just self-hosted VDPs: open the
   body with who you are (handle), your researcher status, the channel (e.g. "through the Immunefi
   <program> program"), and the good-faith/coordinated-disclosure statement — *before* any technical
   content. Then summary, then code references, then impact.
5. **Staging mechanics** (verified 2026-10): `imap_tools`' `MailBox.append()` accepts **raw bytes**, and
   `MailMessage.__init__` only takes `fetch_data`, so build the message with the stdlib and hand over
   bytes:
   ```python
   from email.message import EmailMessage
   from imap_tools import MailBox
   msg = EmailMessage()
   msg["From"] = EMAIL
   msg["Subject"] = SUBJECT          # no To: on purpose (see rule 2)
   msg.set_content(BODY)
   with open(PDF, "rb") as fh:
       msg.add_attachment(fh.read(), maintype="application", subtype="pdf",
                          filename=os.path.basename(PDF))
   with MailBox("imap.gmail.com").login(EMAIL, app_password()) as box:
       print(box.append(msg.as_bytes(), folder="[Gmail]/Draf", flag_set="\\Draft"))
   ```
   Then **verify by fetching the draft back** — assert subject, `attachments[0].filename`,
   `len(attachment.payload) == os.path.getsize(PDF)`, and that the body contains one keyword from each
   of the intro and the technical half. `APPEND OK` alone is not verification.
6. **Guard the shared strings that feed more than one artifact.** The subject string is also passed to
   the PDF's canvas header/footer, and the shared style module asserts the header contains no `&`
   (raw `&` becomes an HTML-entity artifact in reportlab). Fail fast at the top of the draft script
   instead of discovering it at PDF-build time:
   ```python
   if "&" in SUBJECT:
       raise SystemExit("subject must not contain '&' (it is reused as the PDF canvas header)")
   ```

### When the vendor replies, map their justification onto the PARTS of your finding

A triage reply often accepts the report but explains it away with a single constraint. **Check which
sub-claim that constraint actually covers** — a justification that explains half your finding does
not explain the other half, and the uncovered half is your grounds for one polite follow-up.

Observed 2026-10 (Nym, IPC + DACL finding, result: *informational*): *"We are aware of this class of
issues, and are limited in how we can fix it due to how Windows implements IPC support."* That covers
the **DACL** half (Windows genuinely constrains per-pipe permissions) but says nothing about the
Rust-side `else { true }` fail-open branch, which is a plain logic decision — not a platform
limitation. Flag the distinction to the operator; don't let the vendor's blanket sentence swallow the
part they didn't address.

- **Record the reply verbatim** in the engagement's `FINDINGS.md` / `PHASE_LOG.md`, with the exact
  tier assigned ("informational"), so the next session neither re-litigates it nor re-reports it.
- **Expect the same verdict for siblings of the same shape.** If they downgrade because they are
  "aware of this class", say so to the operator *before* they submit the next one, so expectations
  are honest rather than inflated. (But note when a sibling is a different *substance* — e.g. a DNS
  **leak** is a privacy compromise, not local IPC auth — that one is still worth filing.)
- **Never fire the follow-up unprompted.** Draft it, let the operator decide (the never-send rule).

### Reconcile the Sent folder after ANY send (ground truth)

`Sent` is the only record of what actually left the mailbox — the draft folder tells you nothing.

```python
M.select('"[Gmail]/Surat Terkirim"', readonly=True)          # quoted! name has a space
ids = M.search(None, "TO", '"contact@vendor.example"')[1][0].split()
for i in ids:
    h = M.fetch(i, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)])")[1][0][1]
```

Report per-message (subject + date + Message-ID). Do **not** assume every match is yours: the user
may send drafts themselves from the web UI, so the folder can hold more than you pushed. Distinguish
"sent by the script" from "sent by the user" before claiming authorship of anything.

Workflow:

1. **Thread the reply.** Capture the vendor's last `Message-ID` once, store it as a constant in the
   script, and set `In-Reply-To` + `References`. Hardcoding the captured Message-ID avoids a slow
   subject-search on every later run — that search is what silently hung a run in 2026-09.
2. **Build `multipart/mixed`**: a `multipart/alternative` part (plain text + HTML) first, then the
   attachments. Set `X-Unsent: 1` so Gmail opens it in compose rather than as received mail. Attach
   the evidence (screenshots, spreadsheets, exports) instead of referencing local paths.
3. **Delete YOUR previous draft** of the same report after appending, so exactly one draft exists.
   Leave the user's own drafts untouched.
3b. **When the root cause is revised, replace — never leave both.** If a deliverable already exists
   with an explanation that later turns out to be WRONG (e.g. a PDF that blames the wrong subsystem),
   regenerate the PDF, then move the superseded draft to `[Gmail]/Tong Sampah` + `expunge()` and append
   the corrected one. Verify afterwards that exactly one draft matches the attachment *filename* AND
   the new byte size — a stale draft carrying the old explanation is worse than a late send, because
   the user may send the wrong version. Same rule if the finding list changes (a dropped or added
   item): the draft is the last-mile artifact, so it must match the final PDF, not the first.
4. **Verify after append**: subject, attachment count + filenames, `In-Reply-To`, and a keyword
   presence check per major section of the body. Any "MISS" means the append went out truncated.
   - **`IMAP SEARCH SUBJECT "..."` is unreliable — verify by ENUMERATING the folder instead.**
     A subject containing brackets, parentheses, colons or `Re:` (e.g.
     `[TimbSwap][F3] ... release() can never run`) silently returned **0 ids for a draft that was
     definitely there**, both when replacing an old draft and when confirming the new one. A search
     that finds nothing is NOT evidence that nothing exists. Do it the robust way: `search(None, "ALL")`,
     fetch `(BODY.PEEK[HEADER.FIELDS (SUBJECT TO)])` per uid, and match in Python. Use the subject
     search only as an optional extra.
   - **Compare the sent/appended attachment's decoded BYTE SIZE against the local file.** It is the one
     check that catches a stale or truncated attachment: fetch `(RFC822)`, walk the parts, and assert
     `len(part.get_payload(decode=True)) == os.path.getsize(local_path)`. Filenames matching proves
     nothing — two builds of the same report share a filename.
4b. **Verify by fetching the raw message — NOT by BODYSTRUCTURE alone.** `M.fetch(uid,
   "(RFC822.SIZE BODYSTRUCTURE)")` can come back with no size and no media type (observed
   2026-10: `size=?`, `pdf=False` on a draft that genuinely carried the PDF). That is a false
   alarm, and it invites "fixing" a draft that was already correct. The reliable check is a full
   fetch plus a MIME parse, asserting the decoded attachment length equals the local file
   byte-for-byte — that is the real proof, and it also catches a stale superseded PDF of the
   same name:

   ```python
   typ, d = M.fetch(uid, "(RFC822)")
   raw = b"".join(x[1] for x in d if isinstance(x, tuple))
   msg = email.message_from_bytes(raw)
   att = {p.get_filename(): len(p.get_payload(decode=True))
          for p in msg.walk() if p.get_filename()}
   assert att[os.path.basename(PDF)] == os.path.getsize(PDF)   # byte-exact: correct artifact
   assert msg.get("X-Unsent") == "1"                           # compose, not received mail
   ```
   Report exactly what came back: uid, size, attachment filenames with byte counts, and
   "not sent". Never upgrade a `size=?` into a pass.
5. **Report to the user** as: draft uid, subject, attachment list, and "not sent".

6. **If the ANALYSIS behind a staged draft was wrong, replace the draft — never leave a superseded
   explanation in the mailbox.** Observed 2026-10-01: a PDF + email draft had already been staged
   explaining a calculator defect as a "taper" bug; a later pass read the served code and found the
   real cause (band widths). The correct sequence is: rebuild the artifact (PDF v2) → move the OLD
   draft to the localised Trash (`mb.move(uid, "[Gmail]/Tong Sampah")` then `mb.expunge()`) →
   append the corrected draft → re-list the folder and confirm **exactly one** draft with the
   expected attachment byte-size. A wrong root cause sitting as a sendable draft is worse than a
   delayed send, because the operator's next action is "press send". Verify the attachment size
   matches the newly built file (it is the cheapest proof the new PDF, not the old one, is attached).

### A draft that already carries a SUPERSEDED EXPLANATION must be replaced, not followed up

"Update the draft when findings change" is the easy case; the harder one is your own *reasoning*
changing after the draft was written — the first pass blamed the personal-allowance taper, then
reading the target's own JavaScript showed the real cause was the rate-band widths. Rules:

- Regenerate the artifact and the body **together**. Never leave the old PDF attached to a corrected
  body — a body that contradicts its own attachment is worse than a late send.
- Replace rather than add: append the corrected message, move the superseded uid to the localised
  Trash (`mb.move(uid, "[Gmail]/Tong Sampah")` + `expunge`; `delete` alone often does not stick),
  then **re-list the folder** and check subject, attachment filename and byte count against the file
  you just built. Exactly one draft per topic.
- Say it plainly to the operator ("draft lama salah soal X, sudah saya ganti") so they never send a
  stale explanation — and do not append a correction to a mail they already sent.
- Same re-verify rule when the target redeploys mid-engagement: the artifact generated an hour ago
  may no longer describe the live build.

IMAP pitfalls (Gmail — learned the hard way):

- Always construct with an explicit timeout: `MailBox("imap.gmail.com", timeout=150)`. A bare
  `MailBox(...)` can block forever with no error and no output.
- **Run the append in the background** (`terminal(background=True, notify_on_complete=True)`), never
  foreground. A tool-level timeout kills the process mid-run — and because the delete-old-draft step
  runs first, an interrupted run can leave you with **no draft at all**.
- Gmail's IMAP folders are **localized per account**: `[Gmail]/Draf` (not "Drafts"),
  `[Gmail]/Tong Sampah` (Trash), `[Gmail]/Surat Terkirim` (Sent), `[Gmail]/Semua Email`,
  `[Gmail]/Berbintang`. Call `mb.folder.list()` rather than guessing names.
- **A localised folder name can contain a SPACE → it MUST be quoted.** `[Gmail]/Surat Terkirim`
  does; `[Gmail]/Draf` does not. Passing it bare to raw `imaplib` fails with
  `imaplib.IMAP4.error: BAD [b'Could not parse command']` — which reads like a protocol error but is
  purely a quoting bug. Use `M.select('"[Gmail]/Surat Terkirim"')` and
  `M.append('"[Gmail]/Surat Terkirim"', r"(\\Draft)", ...)`. The trap: the untested `Draf` path works
  unquoted, so the bug first surfaces in the **Sent** step — i.e. only *after* the message has
  already gone out. If you script a send, exercise both folders once before trusting it.
- **Gmail SMTP does not file a copy in Sent.** `smtplib.send_message()` only delivers; nothing is
  saved. Append the same raw bytes to the quoted Sent folder yourself, and do the append in its own
  try/except per message so one failure cannot abort a multi-report batch half-way through (which is
  how a batch ends up with 1 of 6 sent and no record of the rest).
- `mb.delete(uid)` alone may leave the message visible; `mb.move(uid, "[Gmail]/Tong Sampah")` then
  `mb.expunge()` is the reliable delete.
- Many rapid login/append cycles in one session can stall new connections — space them out, one
  append per report version.
- A ~1 MB message with six attachments (3 PNG screenshots + 3 XLSX) appends fine; keep the attachment
  set deliberate rather than attaching every artefact.
- **UID spaces are PER FOLDER.** The same message has a different UID in `INBOX` than in
  `[Gmail]/Semua Email` (observed live: the same vendor reply was uid `54068` in INBOX and `60558`
  in All Mail). A UID captured while iterating one folder is meaningless against another, so a
  dump script that hardcodes UIDs seen earlier will silently match **nothing** (no error, exit 0,
  empty output). Two rules: (a) resolve UIDs in the folder you are about to fetch from — do the
  search and the dump against the same folder in one script; (b) prefer re-fetching by query
  (`TEXT "domain.com"`) over storing UIDs between runs.
- **Never pipe a multi-folder mail scan through `tail`/`head`.** The per-folder `=== <folder> ===`
  headers are what tell you which UID space a hit belongs to. Truncating the top of the output
  hides them and it reads as if the last folder printed were the only one — which is exactly how
  the UID mix-up above gets diagnosed an hour too late. Print the folder name on every line
  (`print(f"{folder} uid={m.uid} ...")`) so any truncation stays safe.

### Self-hosted VDPs (no platform — submission is an e-mail) — one finding per draft

Some programs have no HackerOne/Bugcrowd/Intigriti form at all: the policy page names **a single
mailbox** and nothing else. Confirmed 2026-10 (cardoma.shop). Workflow:

1. **Find the channel before writing anything.** Read the policy page (e.g.
   `/report-security-issues/`), then check `/.well-known/security.txt` and the contact page. If there is
   no platform and no security.txt, the mailbox printed on the policy page **is** the channel. Quote
   their stated rules back to yourself: first-valid-report-per-issue, one root cause = one report,
   they may publish, "do not contact employees directly".
2. **One finding = one draft = one PDF.** Never bundle several findings into a single e-mail. Create a
   separate draft per finding, each attaching that finding's own PDF. **If you already staged a
   combined draft, delete it first** (subject search → `+FLAGS \Deleted` → `expunge`) so there is no
   duplicate topic in the Draft folder.
3. **The body MUST open with an introduction** (user's explicit instruction, 2026-10): name/handle,
   the exact policy URL you tested under, and a good-faith sentence ("I did not access any private
   account or data, and I did not disrupt the service"). Then a short per-finding summary (severity +
   CWE + the reproducible one-liner). The full root cause / evidence / remediation lives in the PDF.
4. **Name the attachment after the finding and match it to the subject**:
   `<Program>_F<n>_<ShortTitle>_<Handle>.pdf`. Verify after append — do NOT trust `APPEND OK` alone:
   the draft's `BODYSTRUCTURE` must contain `application/pdf` **and** `RFC822.SIZE` should be roughly
   (PDF bytes + body bytes). Fetch by subject and assert both.
5. **Severity authority for a self-hosted program = CWE + CVSS, not VRT** (there is no Bugcrowd
   taxonomy to map into). Put CWE + CVSS vector in the PDF meta table and state the proposed tier
   against THEIR published reward table.
6. Keep the per-finding PDF count honest: report which findings you deliberately did **not** ship
   (Low/Info ones) and offer them as additional separate PDFs — don't silently drop or silently bundle.
7. **Never hard-code the mailbox password in each generator.** Keep one helper (e.g.
   `~/check_basabasi_email.py`) that holds the Gmail app password and read it back at run time:
   `re.search(r'APP_PASSWORD\s*=\s*["\']([^"\']+)["\']', open(helper).read()).group(1)`, then print only
   its length. Raw `imaplib` + `EmailMessage.add_attachment(...)` + `append(folder, r"(\Draft)", ...)`
   is enough here — no need to pull in `imap_tools` for a plain text+PDF draft.

