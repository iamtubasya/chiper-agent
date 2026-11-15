---
name: cloud-bucket-exposure-forensics
description: "Prove a public S3/GCS bucket exposure before reporting."
metadata:
  hermes:
    tags: [cloud, aws, gcp, s3, gcs, storage, forensics, evidence]
---

# Cloud Bucket Exposure Forensics

**Use when** a public S3/GCS/Blob listing or object exposure is suspected, or when a bucket is found
during recon and you are about to call it a finding.

A `200` on a bucket listing is a **signal, not a finding**. Three gates must pass, in this order, and
each one has killed a "finding" that would otherwise have shipped:

1. **Ownership** — is this bucket actually the target's?
2. **Encoding** — am I requesting the key the way the server expects?
3. **Reachability** — is the object actually served, per object?

Only after all three, plus the delivery rule at the end, is this reportable.

> Scope note: credential escalation after a leak belongs to `cloud-iam-deep`; Kubernetes/Docker exposure
> to `hunt-k8s`; the report artefact itself to `bug-report-delivery`.

---

## Gate 1 — Ownership (run this FIRST, it is the cheapest kill)

### 1a. The same bucket NAME can exist in two clouds, owned by two different companies

Seen live: `blink-staging` answered `200` on **both**

- `blink-staging.s3.amazonaws.com` (AWS S3) — one owner, one dataset
- `storage.googleapis.com/blink-staging` (GCS) — a *different* owner, different data

…because both picked the same obvious word. `blink-web` / `blink-dev` similarly listed on GCS while
returning `NoSuchBucket` on AWS. Check only the hostname you guessed and you will attribute one company's
leak to another.

**Discriminate by the XML namespace in the listing body, never by the URL you happened to use:**

| Listing body | Which store |
|---|---|
| `xmlns="http://s3.amazonaws.com/doc/2006-03-01/"` | **AWS S3** |
| `xmlns='http://doc.s3.amazonaws.com/2006-03-01'` | **Google Cloud Storage** (S3-compat XML mode) |
| JSON with `"kind": "storage#objects"` + `nextPageToken` | **GCS JSON API** |

Endpoint facts worth memorising:

```
# GCS — XML listing (GCS namespace)
https://storage.googleapis.com/<bucket>
# GCS — JSON API, paginate on nextPageToken
https://storage.googleapis.com/storage/v1/b/<bucket>/o?maxResults=1000&pageToken=<token>
# GCS — bucket METADATA is 401 anonymous (do not read that as "closed")
https://storage.googleapis.com/storage/v1/b/<bucket>
# AWS — path-style is deprecated; this 301s PermanentRedirect
https://s3.amazonaws.com/<bucket>
# AWS — virtual-host style is what works
https://<bucket>.s3.amazonaws.com/?list-type=2&max-keys=1000
```

Use `list-type=2` and follow `NextContinuationToken` to completion — an `IsTruncated=true` listing is not
an inventory. A 117,706-key bucket enumerated in 118 pages; stopping at page 1 (206 keys) produced a
materially wrong picture of what the bucket held.

### 1b. A guessable name is NOT a relationship to the brand you are auditing

Ownership evidence, cheapest first:

1. **Read a NON-PII object from inside the bucket and let its content name the owner.** Decisive test: the
   bucket's own `terms_and_condition.pdf` (a licensing agreement naming a specific council and industry)
   plus a business-process `.txt` ("installer permissions: add panels, inverter and batteries… register
   STC…") identified a completely different product and country. That killed the engagement's core
   assumption outright, cheaply, and *before* anything was written up.
2. `?location` / `?versioning` / `?acl` / `?policy` — a bucket can 403 all four while its listing is wide
   open. That pattern localises the misconfig to listing/object ACLs and shows the owner did not intend it.
3. **External corroboration returning zero is still evidence.** `urlscan.io` `domain:<bucket-host>` →
   `total: 0`; GitHub code search for distinctive upload-field names → no hits. Nobody links this bucket,
   which argues against "it is the well-known company's asset".
4. **Probe each top-level prefix for a hosted app** (`index.php`, `index.html`). None found, plus legacy
   absolute server paths in the keys (`/var/www/html/<app>/…`) and generic PHP-app folder names, points at
   an old standalone app rather than the modern product.
5. **Fingerprint the corpus, not just one file.** Hash-dedupe a sample; stock-asset filenames
   (`pexels-…`, `nature3`, `NETCCLogo`, `icon`, `download`, `images`) mixed with "sample"/"test" tokens mark
   dev placeholders. A folder named `driving_licence_user` full of duplicate stock JPEGs is dummy data.

### 1c. If ownership resolves to a different legal entity — STOP

Do **not** send it to the brand you were auditing, and do not reshape the write-up so it fits. Two correct
outcomes:

- park it as a **separate third-party engagement** (its own scope, its own disclosure channel), or
- record `excluded — third-party asset, ownership confirmed different entity` and say so explicitly.

Reporting company A's namesake's leak to company A is a wasted report and a burned relationship. Sending it
to the *actual* owner without a scope/authorisation basis is worse.

---

## Gate 2 — Key encoding (the silent 404)

**Never percent-encode `/` inside a key.** Keys that themselves contain `/` must be fetched with literal
slashes. `%2F` is treated as *part of the key name*, so a thoroughly public object returns
`404 NoSuchKey` whose message echoes the mangled key — and the natural (wrong) conclusion is "not exposed":

```bash
# WRONG — leading slash encoded as %2F. 404 NoSuchKey; the error body echoes the key
#         WITHOUT the leading slash, which is your tell:
curl -sI "https://BUCKET.s3.amazonaws.com/%2Fvar/www/html/app/uploads/terms_and_condition.pdf"

# RIGHT — literal slashes. 200 + Content-Length returned:
curl -sI "https://BUCKET.s3.amazonaws.com//var/www/html/app/uploads/terms_and_condition.pdf"
```

**Rule:** when a key you *listed* 404s on GET, suspect your encoding before the ACL. Confirm by re-listing
the exact prefix and re-fetching a key verbatim from that response:

```bash
curl -s "https://BUCKET.s3.amazonaws.com/?prefix=<folder>/&max-keys=12" | grep -o '<Key>[^<]*</Key>'
```

This mistake produced a retracted conclusion mid-engagement ("the identity-document objects are 404, not
exposed") that had to be corrected in front of the operator once literal slashes were used. Withdraw it
plainly and re-verify; do not quietly move on.

---

## Gate 3 — Reachability is per-object, and prove it without over-collecting

Listing open does **not** imply objects readable, and ACLs are not uniform within one bucket. Measured
inside a single bucket: some keys `200`, some `403`, and a key that `200`'d an hour earlier `404`'d later.
Report per-object status with a stability check — never a blanket claim.

**Prove reachability with HEAD + a 4-byte Range — never by pulling the document.** The claim you need is
"an anonymous caller receives this object"; the bytes of a stranger's identity document are not part of
that claim.

```bash
curl -sI "$URL"                          # 200 + Content-Length + ETag + Last-Modified = served
curl -s -r 0-3 "$URL" | xxd -p           # ffd8ffe0 = JPEG, 89504e47 = PNG -> a real renderable file
curl -sI "$URL-does-not-exist-$RANDOM"   # 404 -> the control that kills "blanket public" theories
```

`206 Partial Content` with `Content-Range: bytes 0-3/<total>` plus a valid magic number proves the artefact
is real, **without the file leaving the bucket**. State the method in the report: *"HEAD plus a 4-byte range
read; no document body was retrieved."* Run the stability check 3× before writing anything up and record
the raw status codes.

---

## Corpus studies: dedupe by hash before you characterise

`sha256` every sampled object and group before drawing any conclusion about content. Sampling 96 objects
across 8 folders labelled `driving_licence_user` / `operational_driving_licence` / `bank_statement_photo` /
`customer_signature` yielded only **76 unique hashes** — one file reused **6×** — and the repeated filenames
were stock assets. That is a placeholder pattern, not a KYC store.

Report unique-hash counts alongside key counts. **Never present N keys as N leaked documents.**

---

## Delivery to the operator (mandatory)

**Do not assert the evidence — hand over the artefact.** Stating "I verified 4 objects return 200, here are
the headers" is rejected as *"that is just you writing it."* For an object-exposure study, produce:

- the **actual file(s)** for a small focused sample, and/or
- for a corpus study, a **ZIP of ~100 sampled objects plus `INDEX.csv`** with columns
  `file, family, source_key, bytes, dims, magic, duplicate_of_hash`

Then verify and report: `zipfile.testzip()` result, entry count, byte size. Write only **PII-free** metadata
into the index — do not transcribe document content. Attach via the platform's media syntax and let the
operator judge dummy-vs-genuine; **do not pre-classify on their behalf**, and state plainly what you did
*not* claim.

---

## Quick sequence

```
1. list with list-type=2 / nextPageToken -> full key set, note the XML namespace (AWS vs GCS)
2. read ONE non-PII object -> who actually owns this bucket?
3. urlscan + code-search + prefix-app-probe -> corroborate or contradict
4. ownership mismatch? -> stop; park as third-party, or exclude with the reason written down
5. sample identity-shaped folders -> HEAD + 4-byte range, 3x, + 404 control
6. sha256-dedupe the sample -> unique vs duplicated; spot placeholder filenames
7. build ZIP + INDEX.csv, testzip(), report entry count and size, attach it
8. only now: did the gate-1 owner match the engagement scope?
```

Re-runnable probe implementing gates 1–3: `scripts/bucket-forensics.py`.
