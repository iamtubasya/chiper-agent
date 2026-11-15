# PGP-encrypted disclosure submission (when the vendor requires PGP)

Many EU/CH vendors put this in their VDP: *"Please use our PGP public key to encrypt any email
submissions."* When that line is present the deliverable changes **shape** — the report body AND the
PDF PoC must be encrypted, so the PDF is no longer a directly-openable attachment. Confirm the
requirement by reading the policy page; do not encrypt on assumption, and do not ship plaintext
against a stated PGP requirement.

## Shape that works (one draft per finding, RULE 0 still holds)

- **Outer Gmail draft**: plaintext cover note (English) + ONE attachment `submission-<F>.asc`.
  - Cover note content: greeting + independence + policy URL; the recipient key **fingerprint**;
    a sentence that "the submission is PGP-encrypted to your published key and attached"; the
    finding title; signature. **No vulnerability detail in the plaintext** — the details live only
    inside the ciphertext.
- **Inner payload (what gets encrypted)**: a full MIME message = `text/plain` report body **+**
  `application/pdf` attachment (the PDF PoC). Build it with `EmailMessage`, `set_content(body)`,
  `add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=PDF)`.
- Encrypt: `gpg --batch --yes --trust-model always --encrypt --armor -r <FPR> inner_F1.eml -o submission-F1.asc`
- Attach the `.asc`: `add_attachment(asc_bytes, maintype="application", subtype="octet-stream", filename="submission-F1.asc")`.

Working split (do the MIME build in Python via stdlib — `urllib`+`json` for the Gmail REST call per
`gmail-rest-draft-staging.md`; do the `gpg` call in the shell).

## Extract a PGP public key from an HTML policy page

The armor is usually wrapped in `<p>`/`<br>` HTML. Naive tag-stripping that also collapses spaces
breaks the armor (symptoms: `invalid radix64 character 2E skipped`, `CRC error`, `[don't know]: invalid packet`).
Reconstruct structurally:

1. `re.sub(r'<br\s*/?>', '\n', html)`; `re.sub(r'</p>', '\n', html)`; strip remaining tags; `html.unescape`; drop `\r`.
2. Slice from `-----BEGIN PGP PUBLIC KEY BLOCK-----` to `-----END PGP PUBLIC KEY BLOCK-----`.
3. Classify each non-empty line: contains `":"` → **header** (Version:/Comment:); matches
   `^[A-Za-z0-9+/=]+$` → **body**. Do **not** length-filter body lines — the short tail line and the
   `=<crc>` line are valid body. (A `<40` char filter silently misroutes `1pfCNo7dv4bnALPq` into the
   header list and the import fails again.)
4. Reassemble exactly: `BEGIN` + headers + **one blank line** + body + `END`. The blank line between
   headers and body is mandatory; missing it makes GPG try to base64-decode the headers.

## MSYS / Git-bash gpg on the Windows host — pitfalls

- `gpg` on PATH is the MSYS build (`/usr/bin/gpg`, GnuPG 2.4.x). `GNUPGHOME="$HOME"` is
  treated as **relative** → `keyblock resource '/c/Users/<user>/$HOME'`. Use the MSYS path:
  `export GNUPGHOME="/c/Users/<user>/.../gnupg"` then `chmod 700 "$GNUPGHOME"`.
- Import confirms the identity: `gpg --batch --import key.asc` prints the uid; then
  `gpg --list-keys --with-colons | grep -E '^(pub|uid|fpr|sub)'` shows the fingerprint + encryption subkey.
- **Encrypt to the encryption SUBKEY, and verify it**: `gpg --list-packets submission-F1.asc | grep keyid`
  must show the key's `sub ... [E]` subkey id (e.g. the pubkey-enc packet keyid), not the primary key.

## Verification (same read-back discipline as the plaintext flow)

- Read the draft back with `?format=raw`, walk the parts, then assert as a per-check OK/FAIL list:
  attachment present; `ab.startswith(b"-----BEGIN PGP MESSAGE-----")`; `len(ab) == len(local_asc)`;
  `sha256(ab) == sha256(local_asc)`; cover phrases present (policy URL, fingerprint, "attached");
  English-only. Equal sizes alone are not enough — the PGP magic + hash is the pair that catches a
  stale/plaintext attachment.
- **Replace, do not append**: stage the encrypted draft first, then `DELETE` the old plaintext draft
  by draft id (the ids differ; see `gmail-rest-draft-staging.md`).
