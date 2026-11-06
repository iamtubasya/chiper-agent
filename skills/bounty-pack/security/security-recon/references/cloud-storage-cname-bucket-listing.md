# Cloud storage bucket listing behind a CDN CNAME (Step 6d)

**Class of bug:** a static-asset CDN host (`assets.`, `static.`, `cdn.`, `files.`) is a CNAME to an
object-storage bucket (GCS / S3 / R2 / Azure Blob). Object *read* is public by design — that is the
CDN. The defect is **anonymous bucket LISTING**: an ACL/IAM binding at the *bucket* level
(`allUsers → objectViewer` / `AllUsers:READER` / `roles/storage.objectViewer`) grants
`storage.objects.list`, so anyone can enumerate every object, not just fetch names they already know.

This is one of the highest-yield "recon-to-finding" shortcuts on an otherwise-hardened target: it
takes one request to check, it is almost never intended, and it yields the whole deploy history.

## Detection (one request)

The GCS XML API and the S3 API both answer a listing request on the CNAME host:

```bash
# S3-compatible (GCS buckets expose this too)
curl -s "https://assets.<target>/?list-type=2&max-keys=25"

# older / GCS-native marker form
curl -s "https://assets.<target>/?prefix=&max-keys=25"
```

Tell-tells:
- a `<ListBucketResult>` / `<Contents><Key>…` body → **listing is public** (finding)
- `<Error><Code>AccessDenied</Code>` → list blocked; the bucket name may still leak
- 404/403 HTML or the SPA shell → not a bucket, or listing disabled

Enumerate the bucket name and top-level layout with a delimiter query:

```bash
curl -s "https://assets.<target>/?list-type=2&delimiter=%2F&max-keys=1000" \
  | grep -oE '<Prefix>[^<]+</Prefix>|<Name>[^<]+</Name>'
```

Run `scripts/bucket_list.py <host> <outfile>` to page the whole bucket with the continuation token
and write every key to a file. Real run against one target: **711,360 objects across 466 releases**
(one directory per production deploy) — that scale is normal for a long-lived asset bucket, so page
it and count, don't assume a sample is representative.

## Determining severity: test the WRITE path

Read/list exposure vs write exposure are an order of magnitude apart (write → arbitrary content on
the production asset origin → stored XSS / supply-chain). Test write anonymously with a single
benign, obviously-labelled marker; never upload HTML/JS.

```bash
curl -sS -X PUT --data "authorized good-faith write-probe; safe to delete" \
  "https://assets.<target>/security-research-probe-<rand>.txt"
```

- `403 … Anonymous caller does not have storage.objects.create access …` → **no write** (Low/Med,
  info-disclosure only). The 403 body also confirms the bucket name and project path — quote it.
- `200` → write primitive → escalate immediately (CDN origin content control), and name the marker
  file in the report for cleanup.

Record the outcome either way; "write tested, denied" is part of a complete report.

## Framing the impact (what triage will accept)

The objects themselves are public by design, so **do not claim the objects are the bug**. The bug is
the *listing* capability, and the impact is what enumeration enables:

- full deploy/build history (every retained release directory)
- ability to **diff any two releases** to recover code, endpoints, feature flags or values that
  existed in an older build and were removed from the current one
- internal build identifiers and release cadence
- a complete asset map of the front end without touching authenticated functionality

Then check the *content*: page the listing and grep for `.map`, `.env`, `config`, `secret`, `backup`,
`.sql`, `.gz`, `.json`. No source maps or secrets in the bucket keeps it Low; a stray `.env` or
source map elevates it. Also compare the oldest vs newest release's config chunk — a value that
existed only in an old build is still fetchable and is a stronger finding than the listing itself.

## Remediation to recommend

- drop the bucket-level `allUsers → objectViewer` binding
- serve assets via per-object public read or a CDN/signed-URL layer that does not grant
  `storage.objects.list`
- enable bucket "Public access prevention"

## Pitfalls

- A 404 on `/…/some.js.map` from the CDN proves nothing about listing — always hit the bucket root
  with `?list-type=2`.
- Don't conflate "the CDN serves public files" with "the bucket is exposed". Verify `list`, state
  explicitly that object read is by design, and lead with enumeration.
- Large buckets get connections reset mid-enumeration; page in a retry loop and keep whatever you
  collected (see the script's incremental write).
