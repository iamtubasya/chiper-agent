# PGP-encrypted submissions (programs that require it)

Some VDPs/bounties state in their policy: *"use our PGP public key to encrypt any email
submissions."* When they do, the plaintext-PDF-attachment shape in SKILL.md does not apply —
the **submission** (report body + PDF) must be encrypted. This is the working flow, proven on a
live engagement (2026-10, Swiss broadcaster).

## Rule interaction

RULE 0 still holds (1 finding = 1 draft + its own PDF), but the PDF rides **inside** the encrypted
payload, not as a directly-openable attachment. Flag that deviation explicitly in the hand-off so the
operator knows why the attachment isn't a `.pdf`. The outer email body becomes a short **plaintext
cover note** (greeting, policy URL, the vendor key fingerprint, "encrypted submission attached",
signature) carrying **no vulnerability detail**.

## Step 1 — extract the vendor's public key from the policy page

The key is usually pasted into the policy HTML wrapped in `<br />` line breaks and `<p>` blocks.
Naive tag-stripping mangles the armor (collapsing the spaces in the `-----BEGIN PGP PUBLIC KEY
BLOCK-----` header and eating the blank line before the base64 body → `gpg: invalid radix64
character` / `CRC error`). Rebuild it properly:

```python
import re, urllib.request, html as H
raw = urllib.request.urlopen(urllib.request.Request(policy_url, headers={"User-Agent":"Mozilla/5.0"})).read().decode("utf-8","replace")
t = re.sub(r'(?is)<br\s*/?>', "\n", raw)
t = re.sub(r'(?is)</p>', "\n", t)
t = re.sub(r'(?is)<[^>]+>', "", t)
t = H.unescape(t).replace("\r", "")
m = re.search(r'-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----', t, re.S)
hdr, body = [], []
for l in [x.strip() for x in m.group(0).split("\n") if x.strip()]:
    if l.startswith("-----"):            continue
    if ":" in l:                          hdr.append(l)          # Version: / Comment:
    elif re.match(r'^[A-Za-z0-9+/=]+$', l): body.append(l)      # base64 body + CRC "=xxxx"
armor = ("-----BEGIN PGP PUBLIC KEY BLOCK-----\n" + "\n".join(hdr) + "\n\n"
         + "\n".join(body) + "\n-----END PGP PUBLIC KEY BLOCK-----\n")
```

Key classifier trap: do NOT decide "header vs body" by line length — the **last base64 body line can
be short** (e.g. 16 chars) and would be mis-filed as a header. Classify by `":" in line` (headers)
vs base64-charset match (body).

Import (Git-bash/MSYS gpg needs an **MSYS** `GNUPGHOME`, not `C:/...` — a native path gets treated as
relative and yields `no writable keyring found`):
```bash
export GNUPGHOME="/c/Users/<user>/tmp/gnupg"; mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"
gpg --batch --import riello-pub.asc      # -> 'public key "<uid>" imported'
gpg --list-keys --with-colons | grep -E '^(pub|uid|fpr)'
```

## Step 2 — build the inner MIME, then encrypt it

Build a normal `multipart/mixed` MIME containing the plaintext report body **and** the PDF, write it to
`inner_F1.eml`, then encrypt that whole file:
```bash
gpg --batch --yes --trust-model always --encrypt --armor -r <KEYID> \
    -o submission-F1.asc inner_F1.eml
```
Use the 64-bit key id or fingerprint (e.g. `8944CB7232BFC6B2`); GPG auto-selects the encryption
subkey. Confirm the recipient is the **encryption subkey**, not the primary:
```bash
gpg --list-packets submission-F1.asc | grep -i keyid   # -> pubkey enc packet: ... keyid BD66B6783E11006F
```
You cannot decrypt it yourself (you only hold the public key) — `--list-packets` and the armor header
are the verification you get, and they are sufficient.

## Step 3 — stage the Gmail draft (cover note + .asc attachment)

Per `references/gmail-rest-draft-staging.md`: build the outer `EmailMessage`, `set_content(cover)`,
`add_attachment(asc_bytes, maintype="application", subtype="octet-stream", filename="submission-F1.asc")`,
then `drafts().create`. Keep the outer subject plaintext (subjects aren't encrypted anyway).

## Step 4 — verify (read back with `?format=raw`)

Same read-back discipline as the plaintext flow, with the magic string swapped:
- attachment present; `ab.startswith(b"-----BEGIN PGP MESSAGE-----")`
- `len(ab) == os.path.getsize(local_asc)` and sha256 match
- cover phrases present (policy URL, key fingerprint, "encrypted to your published public key", signature)
- english-only scan on the **plaintext cover body**

## Replace in place, and clean up the plaintext predecessors

Staging the encrypted set does not remove any earlier plaintext drafts. Stage the encrypted draft
first, then `DELETE .../drafts/<oldId>` for each superseded plaintext draft (the reference's
"stage-new-then-delete-old" rule, so an interrupt never leaves the folder empty). Record the new
draft ids + `.asc` byte sizes in the hand-off.
