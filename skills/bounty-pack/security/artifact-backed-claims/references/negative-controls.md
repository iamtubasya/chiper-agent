# Negative controls and attribution — concrete recipes

Real cases from an authorized engagement (2026-10-13). Each one is a claim that looked
solid and was wrong until a control was run.

---

## 1. The encoding control — the S3 `%2F` trap

**Claim that was wrong:** "the bucket listing leaks object names but the objects
themselves are protected — the KYC files return 404."

**What actually happened:** the probe percent-encoded the path separators.

```bash
# WRONG — %2F becomes PART of the key name, so S3 looks for a file literally called
# "%2Fvar%2Fwww..." and answers 404. Reads exactly like "names leak, objects protected".
curl -sI "https://BUCKET.s3.amazonaws.com/%2Fvar/www/html/app/file.pdf"    # 404

# RIGHT — plain slashes.
curl -sI "https://BUCKET.s3.amazonaws.com/var/www/html/app/file.pdf"       # 200, Content-Length, ETag
```

The same signature appears in Python:

```python
urllib.parse.quote(key, safe='')     # WRONG: every directory-separated key 404s
urllib.parse.quote(key)              # RIGHT: default safe='/'
f"{bucket}/{key}"                    # RIGHT: naive concatenation, no encoding
```

**Rule:** before concluding "objects are not retrievable", re-probe ONE key with naive
string concatenation. If the two probes disagree, the encoding was the bug and there is
no finding.

**Generalisation:** any time a probe returns a clean "not found" / "denied" for *every*
input, suspect the probe. Vary one dimension (encoding, header, method, trailing slash)
on a single case you expect to succeed.

---

## 2. Ownership control — bucket name is not attribution

**Claim that was wrong:** a bucket named `<audit-target>-staging` with a
`driving_licence_user/` folder belongs to the target being audited.

The bucket actually belonged to an unrelated Australian solar/STC ERP that shares the
same product name. Reporting it to the engagement vendor would have been wrong on two
counts (wrong vendor, wrong asset).

**Attribution table — evidence that holds, non-PII only:**

| Method | What it gives |
|---|---|
| Read ONE non-PII business object (`terms*.pdf`, `*.txt`) and extract its text | Names the real owner, its regulator/scheme, sometimes its internal product name in prose |
| `xmlns` in the raw listing XML | `doc.s3.amazonaws.com/2006-03-01` = **GCS**; `s3.amazonaws.com/doc/2006-03-01` = **AWS S3**. Same bucket name can exist on both clouds with different contents — confirm which cloud your saved evidence came from |
| `?location` / `?websiteConfig` / `?cors` / `?acl` | 403 on a public-listing bucket is normal; ACL read is a separate permission |
| Public code search for a distinctive internal field name | 0 hits is a valid negative — the app is just closed-source |
| `urlscan.io` `domain:<bucket-host>` and `page.domain:<bucket-host>` | 0 results = no public page references the bucket |
| App-store listing / product site matching the name found in the object text | Confirms owner domain + package id |

**Not attribution proof:** bucket-name similarity, the target using that cloud elsewhere,
a word appearing in the name.

**Extraction tip:** PDF content streams are usually Flate — decompress then pull the
parenthesised text strings rather than fighting a regex. `pdftotext` on a
retrieved-but-non-PII document is faster and cleaner than hand-parsing.

---

## 3. Blanket-cache control

A listing or endpoint that answers 200 for apparently interesting input may be a catch-all
responder (SPA fallback, permissive cache, CDN default document) rather than an exposure.

```bash
# control: a key that cannot exist must NOT be readable
curl -sI "https://BUCKET.s3.amazonaws.com/<dir>/does-not-exist-$RANDOM.jpg"   # expect 404

# companion control: a sibling asset with a restrictive ACL should deny
curl -sI "https://BUCKET.s3.amazonaws.com/"     # vs the sibling name -> 403 AccessDenied
```

An SPA catch-all is a common version of this on web targets: every unknown path returns
200 with the identical shell. Diff the **body**, not the status code — a 200 whose body is
byte-identical to baseline is not an exposure.

---

## 4. Reachability proof without reading the document

Satisfies the proof requirement while staying inside the usual safe-harbour clause
("do not access data beyond what is needed to demonstrate the issue").

```bash
curl -sI "https://BUCKET.s3.amazonaws.com/<key>"      # status, Content-Length, ETag, Content-Type
curl -s -r 0-3 "https://BUCKET.s3.amazonaws.com/<key>" | xxd
#    ffd8ffe0 / ffd8ffe1 / ffd8ffdb = JPEG
#    89504e47                       = PNG
#    25504446 ("%PDF")              = PDF
```

Then fingerprint the file **type** without reading its content:

```python
from PIL import Image
im = Image.open(path)
print(im.size, im.format, im.mode, im.getexif())
```

Tells that a file named like an ID document is **not** one: `pexels-<photographer>-<id>`
filename (stock photo), no EXIF, landscape dimensions, photo-tool ICC profile. A genuine
document photo is usually portrait, EXIF-bearing, named after a camera or a chat-app
export.

**Claim text that survives triage:**

> "objects under a folder named `driving_licence_user` are publicly retrievable (HEAD 200,
> N bytes, image/jpeg, JPEG magic bytes verified); I did not read their contents."

**Claim text that does not:** "customer driving licences are publicly exposed."

---

## 5. Reporting granularity

- Paginated listings: report "60,000+ keys, still truncated at 60 pages", not "60,000
  keys".
- Per-key instability is real (stale index, versioned delete, DeleteMarker). Keep a
  matrix `200: N | other: M` and never generalise one success to the whole prefix.
- Every artefact gets a `sha256` written next to it, so the operator can confirm the file
  they receive is the file that was captured.
