# S3 / GCS bucket-lock verification — the 13-op probe + anonymous write test

A repeatable recipe for proving a storage bucket is **locked** (or open) before you write a
finding either way. Written from a live audit (2026-10-26) where the bucket was referenced
by an in-scope public page, so it was unambiguously the target's asset.

## Why this shape

A single `GET /?list-type=2` returning 403 is not enough to call a bucket safe, and a single
200 on one object is not enough to call it open. Buckets fail *per operation*, not per
bucket: listing can be denied while object reads are public, or writes can be open while
reads are closed. Run the whole matrix and report the matrix.

## The 13 bucket-level probes

```python
B = "https://<bucket>.s3.<region>.amazonaws.com"
PROBES = [
    ("/?list-type=2",              "list objects v2"),
    ("/?list-type=2&max-keys=10",  "list, capped"),
    ("/?prefix=public/",           "prefix-scoped list"),
    ("/?prefix=",                  "list, empty prefix"),
    ("/?acl",                      "bucket ACL"),
    ("/?cors",                     "bucket CORS"),
    ("/?policy",                   "bucket policy"),
    ("/?location",                 "bucket location"),
    ("/?versions",                 "object versions"),
    ("/?logging",                  "bucket logging"),
    ("/?lifecycle",                "lifecycle rules"),
    ("/?website",                  "static-website config"),
    ("/?uploads",                  "multipart uploads"),
]
```

Interpretation on a locked bucket: every one returns **403** with an XML
`<Error><Code>AccessDenied</Code>` body. That is the honest negative — record it as
"13/13 denied" rather than "bucket not found".

## Object-level differential

A locked bucket still serves the objects it intends to serve. Distinguish the two:

| probe | locked-bucket result | meaning |
|---|---|---|
| known public object (URL taken from an in-scope page) | 200 + correct `Content-Type` | by design |
| guessed object name | 403 | no anonymous read |
| `public/` prefix as a "directory" | 403 | no prefix listing |
| `private/` prefix | 403 | no prefix listing |
| root `/` | 403 | no listing |

**How to get a legitimate known object without guessing:** grep the in-scope pages and API
responses for `s3.*amazonaws.com` URLs. A public changelog/news API is a common source —
on the worked example the JSON payload embedded a full
`https://<bucket>.s3.<region>.amazonaws.com/public/changelog/<random>.png`, which both named
the bucket and supplied a valid object to diff against.

## Anonymous write test (do this, then clean up)

The write probe is the one that separates "read-only public bucket" from "open bucket", and
it is the difference between Low and Critical. Always use a unique marker and delete it:

```python
MARK = "/public/bounty-probe-<random>.txt"
req = urllib.request.Request(B + MARK, data=b"probe", method="PUT",
                             headers={"Content-Type": "text/plain"})
# 403 -> write denied. 200 -> CREATED: verify with a GET from a clean session,
# then DELETE the marker and confirm the 404 before writing the report.
```

**Never leave the marker behind.** A write probe that succeeds and is not cleaned up is
state you created on someone else's infrastructure.

## GCS equivalent

GCS uses the same REST shape on `https://storage.googleapis.com/<bucket>`:

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://storage.googleapis.com/<bucket>?prefix=public/"
curl -s "https://storage.googleapis.com/<bucket>?acl"      # 403 when locked
```

Anonymous write: `curl -X PUT --data-binary @marker.txt \
  -H "Content-Type: text/plain" \
  "https://storage.googleapis.com/<bucket>/public/bounty-probe-<rand>.txt"`

## Reporting shape

State the matrix, not a sentence. "13/13 bucket operations denied (list, ACL, CORS, policy,
location, versions, logging, lifecycle, website, uploads); object-level: known public
object 200 by design, guessed object 403, prefix listing 403; anonymous PUT 403, marker
never created" is a coverage claim a triager can act on. "Bucket is secure" is not.

## Pitfall — do not confuse a 403 with a nonexistent bucket

A nonexistent bucket returns **404 NoSuchBucket**; a locked one returns **403 AccessDenied**.
They look similar in a status-only summary and mean opposite things. Record the XML
`<Code>` element, not just the status line.
