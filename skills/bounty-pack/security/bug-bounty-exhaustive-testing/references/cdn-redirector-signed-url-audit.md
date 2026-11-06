# CDN / signed-URL redirector audit recipe

**Why this file exists.** A whole 0A–0F run (2026-10-10, `download.jetbrains.com`) came back
"0 findings" with **33/33 gates green** and a fully-populated coverage ledger — while having tested
nothing. Every probe hit the same `302`. The generic vector list (XSS/SQLi/IDOR/SSRF/traversal) is the
wrong instrument for a redirector or a static CDN. This is the instrument that fits.

Use when recon shows: every path 302s to a CDN host, a CloudFront/S3 `Server:` header, an `X-Cache:` /
`Age:` pair, or a `?Signature=…&Key-Pair-Id=…` in the `Location`.

---

## 0. First, prove it is a wall (do this before ANY vector)

```bash
B=https://<target>
for p in / /robots.txt /sitemap.xml /nonexistent-xyz-12345 ; do
  printf "%-26s " "$p"
  curl -s -o /dev/null -w "HTTP %{http_code}  %{size_download}B  ct=%{content_type}  -> %{redirect_url}\n" \
       --max-time 15 "$B$p"
done
```
**All identical status + size + content-type ⇒ you are testing a redirector/catch-all, not an app.**
Stop the generic vector list. Everything below is the real surface.

## 1. Map the architecture (this IS the deliverable)

```bash
# follow the redirect once, look at the destination's headers — that names the origin
L=$(curl -s -o /dev/null -w "%{redirect_url}" --max-time 15 "$B/")
curl -sI --max-time 20 "$L" | grep -iE "^(HTTP|server|x-amz|via|x-cache|age|etag|content-type|location)"
```
Real output from the JetBrains case:
```
Server: AmazonS3                     <- origin is S3, not an app
x-amz-version-id: 1GaziBTpvHgaa…     <- versioning on; object metadata leaks
x-amz-replication-status: COMPLETED
X-Cache: Error from cloudfront       <- CDN caches ERRORS too (Age grows) — note it
Via: 1.1 …cloudfront.net
Age: 4116                            <- cached; TTL is long
```
Record: **redirector → CDN → origin bucket**, plus the `Key-Pair-Id` (CloudFront key group) from the
`Location` query string.

## 2. Get REAL artifact paths — never invent them

Guessing 404s and produces a false "clean". Vendor release APIs are public and authoritative:

```bash
curl -s --max-time 25 \
  "https://data.services.jetbrains.com/products/releases?code=IIU%2CPCP&latest=true&type=release" \
  | python -c "import sys,json;d=json.load(sys.stdin)
for k,v in d.items():
    r=v[0]; print(k, r['version'])
    for t,x in r['downloads'].items(): print('   ',t, x.get('link'))"
```
Generic form: `https://<vendor data>/products/releases?code=<ID>&latest=true&type=release`.
Gives e.g. `https://download.jetbrains.com/idea/idea-2026.2.3.exe`.

**Never GET a large object — use HEAD or a 1-byte range:**
```bash
curl -s -o /dev/null -D - --max-time 25 -r 0-0 "<signed-url>" | head -20
```

## 3. The redirector's own attack classes

| # | class | probe | what a finding looks like |
|---|---|---|---|
| 1 | **path normalisation → signature for an unintended path** | `/../../etc/passwd`, `/%2e%2e/…`, `/a/../b` | signer collapses `..` and signs the *collapsed* path — including outside the requested prefix |
| 2 | **cross-prefix signing** | `/idea/../python/pycharm.exe` | signature issued for a *different* prefix than requested |
| 3 | **double-encoding slips past normalisation** | `/%252e%252e%252f…`, `/....//` | signed **literally**, un-normalised |
| 4 | **Host-header injection** | `-H "Host: evil.attacker.com"` | target built from the request Host (403 here = defended) |
| 5 | **method tampering** | GET HEAD POST PUT DELETE OPTIONS TRACE | POST/PUT/DELETE 403 + TRACE 405 = defended; a 302 on a write method is the finding |
| 6 | **CORS on the artifact path** | `-H "Origin: https://evil.attacker.com"` | `access-control-allow-origin` reflection on a signed path |
| 7 | **error-page reflection** | path containing `<script>alert(1)</script>` | raw reflection in the 404 body |
| 8 | **signature tampering** | flip one char of `Signature=` | 403 (good) vs 404 (info) vs **200 (auth bypass — critical)** |
| 9 | **expiry / reuse** | re-request a captured signed URL after `Expires` | signature still honoured past expiry |
| 10 | **cache-key scope** | same path, 3 *different* `Signature=` values → compare `Age` | **identical `Age` ⇒ the cache key ignores the query string** |
| 11 | **cache poisoning → DoS** | see §4 — careful | mechanism only |

Worked results from the JetBrains case (all safe, non-destructive):
```
#1  /idea/../../../../etc/passwd   -> signs /etc/passwd        (collapses ..)
#2  /idea/../python/pycharm-….exe  -> signs /python/…          (cross-prefix)
#3  /%252e%252e%252fetc/passwd     -> signed LITERALLY         (no normalisation)
#4  Host: evil…                    -> 403                       (defended)
#5  POST/PUT/DELETE 403 · TRACE 405                            (defended)
#6  no access-control-* headers                                (defended)
#7  no reflection in the 404 body                              (defended)
#10 same Age across 3 signatures  -> cache key = PATH ONLY     (← the interesting one)
```

## 4. Cache poisoning — establish the mechanism, do NOT detonate it

**The reasoning that makes this a real class for a download host:**
`cache key = path only` + `error responses are cached` ⇒ a request for a **real** artifact path with a
*bad* signature could cache an error that later **legitimate** requests are served. That is a DoS on a
production download.

**Do this (harmless):** probe on a **non-existent path** and a **throwaway** signature. Different
signatures on the same path returning the same `Age` ⇒ the query string is not in the cache key.

**Do NOT do this:** request a real artifact path with a tampered signature to "confirm". You will
possibly break downloads for real users.

Then verify you changed nothing:
```bash
# the real artifact must still serve — and an untouched sibling as control
for u in idea/idea-<v>.exe python/pycharm-<v>.exe ; do
  L=$(curl -s -o /dev/null -w "%{redirect_url}" "$B/$u")
  printf "%-34s " "$u"; curl -s -o /dev/null -D - -r 0-0 "$L" | grep -iE "^(HTTP|x-cache|age)"
done
# both 206 + X-Cache: Hit  => you did not poison anything
```
In the JetBrains case the tampered-signature request returned `404` **and the cached object kept
serving `206`** — i.e. CloudFront did **not** overwrite a good cached entry with an error. The
hypothesis did **not** reproduce, and that is a legitimate, reportable negative.

**Report shape when it does not reproduce:**
> mechanism established (cache key ignores query string) · destructive impact NOT executed on a real
> artifact (no-DoS rule) · CDN served the cached object despite a tampered signature ⇒ defended.

## 5. Honest verdict template

```
Architecture : redirector (signs any path) -> CloudFront -> S3 origin, Key-Pair-Id <id>
Surface      : <N> real artifact paths enumerated from the public release API
Classes run  : normalisation, cross-prefix, double-encoding, Host, methods, CORS,
               reflection, signature tampering, expiry, cache-key scope  (9/11 executed)
Defended     : Host, methods, CORS, reflection, signature tampering
Partial      : cache-key = path-only  (mechanism proven; DoS impact deliberately NOT executed)
NOT tested   : <list> — with the reason each was excluded
Verdict      : 0 reportable — AND the classes above were actually exercised
```
The last line is the point. "0 reportable" is only worth anything when it can say *which classes ran*
and *which were deliberately withheld and why*.

## 6. Pitfalls

- **Hardcoded URL lists are the root cause.** `/`, `/login`, `/api/`, `/.env`, `/robots.txt`,
  `/sitemap.xml` on a CDN host is 6 requests to the same redirect. Recon must produce paths derived
  from the host's *purpose*, not a generic wordlist.
- **A generic 404 page can be big and look like content.** 5922 B of React HTML was the same for every
  path — size equality across unrelated paths is the tell.
- **`Server: AmazonS3` does not mean "raw bucket".** Here S3 was behind CloudFront *and* a custom 404 —
  test the fronting behaviour, not the bucket listing.
- **`X-Cache: Error from cloudfront` means errors are cached.** Note the `Age`; a *fixed* growing `Age`
  across different queries is what exposes a path-only cache key.
- **`Age` near-zero on a fresh path tells you the TTL**, which bounds how long a poisoning would last —
  useful for the write-up, not a reason to test it destructively.
