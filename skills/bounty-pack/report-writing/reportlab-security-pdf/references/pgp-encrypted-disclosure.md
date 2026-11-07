# PGP-encrypted disclosure submissions (program requires its public key)

Some VDPs state outright: *"Please use our PGP public key to encrypt any email submissions to
us at security-<team>@target"* (many EU programs do; the riello-ups.com.ar policy did). When it
does, the submission — report body AND the PDF PoC — must go inside the ciphertext. This is the
recipe. The RULE 0 shape still holds (1 finding = 1 draft = 1 PDF); the PDF simply rides inside
the encrypted payload instead of being a directly-openable attachment.

**Detect it:** read the policy page before drafting. Grep for `PGP`, `public key`,
`BEGIN PGP PUBLIC KEY BLOCK`. If present, apply this path to *every* finding's draft for that
program, not just the first.

## 1. Extract the vendor's public key (the HTML-wrap trap)

The armor is usually HTML-wrapped (`<p>` blocks with `<br />` line breaks). The trap: **do not
collapse whitespace** — the armor header lines carry a single meaningful space, and the blank
line between the headers and the base64 body is REQUIRED. Collapsing it yields
`-----BEGINPGPPUBLICKEYBLOCK-----` and gpg rejects with `invalid radix64 character` / `CRC error`.

Correct reconstruction: convert `<br>` → `\n`, `</p>` → `\n`, strip remaining tags, unescape
entities, drop `\r`. Then classify each non-empty line:
- `-----BEGIN/END … -----` → skip (re-add verbatim)
- contains `:` → armor header (e.g. `Version:`, `Comment:`) → keep
- matches `^[A-Za-z0-9+/=]+$` (any length, includes the trailing `=CRC`) → base64 body → keep

Reassemble: `BEGIN` + headers + **one blank line** + body + `END`.

## 2. Import — GNUPGHOME must be an MSYS path

On Windows the terminal gpg is the Git/MSYS gpg (`/usr/bin/gpg`). A Windows-style `GNUPGHOME`
(e.g. `/home/agentuser/gnupg`) is treated as a *relative* path → `no writable keyring found`. Use the
MSYS form:

```bash
export GNUPGHOME="/c/Users/<user>/tmp/gnupg"; mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"
gpg --batch --import /c/Users/<user>/tmp/riello-pub.asc
gpg --list-keys --with-colons | grep -E '^(pub|uid|fpr|sub)'
```
`gpg --batch --import` succeeding is the validation that your armor rebuild was correct. Note the
**encryption subkey** id from the `sub` lines (rsa4096 keys usually encrypt to the subkey, not the
primary — that is expected).

## 3. Encrypt an inner MIME (body + PDF) → ASCII armor

Build a normal `EmailMessage` carrying the report body + the PDF attachment, then encrypt the whole
message file:

```bash
gpg --batch --yes --trust-model always --encrypt --armor \
    -r <ENC_SUBKEY_ID> -o submission-F1.asc inner_F1.eml
```
`head -1 submission-F1.asc` must be `-----BEGIN PGP MESSAGE-----`. Confirm the recipient without
the private key: `gpg --list-packets submission-F1.asc | grep -i keyid`.

## 4. Stage the Gmail draft — cover note plaintext, payload encrypted

Outer body = a SHORT plaintext cover note only (greeting, policy URL, the key **fingerprint**, and
"the submission is encrypted to your published public key and attached as submission-<id>.asc").
No vulnerability detail in the plaintext body — it lives inside the ciphertext. Attach the `.asc`
as `maintype="application", subtype="octet-stream", filename="submission-<id>.asc"`.

Read-back verification (same traps as the plaintext path — walk parts, don't call `.get_body()`):
- attachment present, starts `b"-----BEGIN PGP MESSAGE-----"`, size + sha256 match the local `.asc`;
- cover-note landmarks present (policy URL, fingerprint, signature), English-only.

## 5. Replace, don't append

Stage the new encrypted draft FIRST, then DELETE the old plaintext draft by its **draft id** (not
message id). Keep one state file mapping `finding -> draft id` and upsert in place.

## Honesty note for the handoff

Report to the operator that the PDF is no longer a directly-openable attachment (it is inside the
cold ciphertext, per the program's own requirement) and offer a plaintext variant if they prefer.
State clearly that nothing was sent — drafts only.
