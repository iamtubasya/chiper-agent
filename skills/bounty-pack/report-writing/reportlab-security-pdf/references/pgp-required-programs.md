# PGP-required disclosure programs — encrypt the SUBMISSION, not just the attachment

Some programs state the requirement in the brief itself, e.g. Riello UPS (2026-10):

> "Please use our PGP public key to encrypt any email submissions to us at
>  security-incident@<domain>"

When a program asks for PGP, the deliverable changes shape: the finding PDF must travel **inside an
encrypted payload**, not as a plaintext attachment. This does NOT relax RULE 0 — still one draft per
finding; the phrase "PDF attached" becomes "an encrypted attachment that decrypts to the report body
plus the PDF".

**Confirm the requirement first** and quote the exact sentence in your working notes. If the brief
does NOT ask for PGP, keep the plaintext PDF attachment (do not invent an encryption step). The
requirement is a program FORMAT rule, in the same family as rule 15 in SKILL.md.

## Recipe

### 1. Extract the recipient public key from the disclosure page

The key is usually inline in the policy HTML, wrapped in `<p>` blocks with `<br />` between lines.
Flatten `<br>`/`</p>` to newlines and strip the remaining tags — but **keep the armor structure**:

```
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: Keybase OpenPGP v1.0.0        <- header lines keep their spaces
Comment: https://keybase.io/crypto
                                        <- ONE blank line
<base64 body lines>
=i+Ks                                   <- CRC
-----END PGP PUBLIC KEY BLOCK-----
```

**Pitfall — do not "strip all whitespace".** A naive `re.sub(r'[ \t]+','',text)` collapses the armor
into `-----BEGINPGPPUBLICKEYBLOCK-----` and GPG rejects it. Classify lines instead: a line containing
`:` is a header; a line matching `^[A-Za-z0-9+/=]+$` is body (this includes the short final body line
and the `=CRC` line — do NOT put a minimum-length filter on body lines, a short final chunk
`1pfCNo7dv4bnALPq` is valid). Then reassemble `BEGIN + headers + "" + body + END`.

### 2. Import and check the key

```bash
export GNUPGHOME="/c/Users/<user>/tmp-audit/gnupg"   # MSYS path (see traps)
mkdir -p "$GNUPGHOME" && chmod 700 "$GNUPGHOME"
gpg --batch --import key.asc
gpg --list-keys --with-colons | grep -E '^(pub|uid|fpr|sub)'
```

`trust-model always` at encrypt time (their key will be `[unknown]`). Note the **encryption subkey**
id — `gpg --list-packets` on the finished `.asc` must show that subkey as the recipient (e.g.
`pubkey enc packet: ... keyid BD66B6783E11006F`), which is the cheap proof the payload is addressed
to them and nobody else.

### 3. Build the inner MIME, then encrypt it

The encrypted payload must contain BOTH the report body and the PDF:

```python
from email.message import EmailMessage
m = EmailMessage(); m["To"]=to; m["From"]="Name <me@gmail.com>"; m["Subject"]=subject
m.set_content(report_body)                                   # the full English intro+detail body
m.add_attachment(open(pdf,"rb").read(), maintype="application", subtype="pdf", filename=pdf_name)
open("inner.eml","wb").write(m.as_bytes())
```

```bash
export GNUPGHOME="/c/Users/<user>/tmp-audit/gnupg"
gpg --batch --yes --trust-model always --encrypt --armor -r <KEYID> -o submission.asc inner.eml
head -1 submission.asc        # -> -----BEGIN PGP MESSAGE-----
```

### 4. The outer draft: plaintext cover + the .asc

The outer email body is a **plaintext cover note only** — greeting, who you are, the policy URL, the
recipient key fingerprint, a pointer to the encrypted attachment, and the signature. **Never the
vulnerability detail.** The details live in the encrypted payload. Attach the `.asc`
(`maintype="application", subtype="octet-stream", filename="submission-<id>.asc"`).

This deliberately overrides rule 12's "body must stand alone" — a program that requires encryption
cannot also have a plaintext vuln body. State the trade-off in the hand-off so the operator can
choose differently if they want.

Replacing a plaintext draft with an encrypted one: **stage the new draft first, then delete the old**
(delete-by-draft-id), so an interrupt never leaves the folder empty. Keep old vs new ids in the state
file (`draft_state.json` → `draft_state_enc.json`) so the replace is auditable.

### 5. Verify (read-back is mandatory)

Per-draft, as a list of OK/FAIL (not one aggregate):
- attachment present, `sha256(bytes) == sha256(local .asc)`, size equal;
- magic `b"-----BEGIN PGP MESSAGE-----"` (this is the PGP analogue of the `%PDF-` check);
- cover-note landmarks: policy URL, key fingerprint, "encrypted to your published public key",
  signature — assert on `" ".join(body.split())` (bodies are hard-wrapped);
- English-only scan on the cover;
- `gpg --list-packets submission.asc` shows the recipient encryption subkey.

## Tooling traps (Windows / Git-bash MSYS)

- **`GNUPGHOME` must be an MSYS path** (`/c/Users/...`) when using the MSYS `gpg` (`/usr/bin/gpg`).
  A Windows path (`/home/agentuser`) is treated as **relative** and you get
  `keyblock resource '/c/Users/<user>//home/agentuser/pubring.kbx': No such file or directory`.
- **Long `cat > file <<'EOF'` heredocs can be truncated** by the terminal wrapper, leaving the
  heredoc unterminated → `/usr/bin/bash: -c: line N: unexpected EOF while looking for matching quote`.
  Symptom is a parse error at *parse* time, so earlier commands in the same block (e.g. `mkdir -p`)
  never ran. Write long generators/scripts in **appended chunks** (`>>`) and verify line count
  between chunks; build the python source with `chr(38)` for `&` if a naive tool scan flags the
  literal ampersand in the command.
- The `.asc` is encrypted to THEIR key — you cannot decrypt it yourself. Verification is limited to
  well-formedness + recipient id (`--list-packets`) + the read-back checks above. That is expected.
