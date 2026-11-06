#!/usr/bin/env python3
"""Enumerate a publicly-readable object-storage bucket exposed behind a CDN CNAME.

Works against the GCS XML API and the S3 API (same query shape). Writes keys
incrementally so a mid-run connection reset does not lose collected data.

Usage:
    python bucket_list.py assets.example.com keys.txt
    python bucket_list.py assets.example.com keys.txt ui/releases/   # limit to a prefix

Exit codes: 0 = listing worked (keys written), 2 = not listable, 3 = transport error.
"""
import ssl, sys, time, urllib.parse, urllib.request, urllib.error, re

HOST = sys.argv[1]
OUT = sys.argv[2]
PREFIX = sys.argv[3] if len(sys.argv) > 3 else ""
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"
ctx = ssl._create_unverified_context()
MAX_PAGES = 2000


def page(token=None):
    q = {"list-type": "2", "max-keys": "1000"}
    if PREFIX:
        q["prefix"] = PREFIX
    if token:
        q["continuation-token"] = token
    url = "https://%s/?%s" % (HOST, urllib.parse.urlencode(q))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30, context=ctx).read().decode("utf-8", "replace")


def main():
    if not PREFIX:
        try:  # cheap probe first: is listing actually open?
            body = page()
        except urllib.error.HTTPError as e:
            detail = e.read(200).decode("utf-8", "replace")
            print("NOT LISTABLE: HTTP %s %s" % (e.code, detail.replace("\n", " ")))
            return 2
        except Exception as e:
            print("TRANSPORT ERROR: %s" % e)
            return 3
        if "<ListBucketResult" not in body:
            print("NOT LISTABLE: response is not a ListBucketResult")
            return 2
        name = re.search(r"<Name>([^<]+)</Name>", body)
        print("LISTABLE bucket=%s" % (name.group(1) if name else "?"))

    token, pages, total = None, 0, 0
    f = open(OUT, "w", encoding="utf-8")
    while True:
        for attempt in range(3):
            try:
                body = page(token)
                break
            except Exception as e:
                if attempt == 2:
                    print("stopped after %d keys (transport: %s)" % (total, e))
                    f.close()
                    return 0
                time.sleep(1.5 * (attempt + 1))
        pages += 1
        keys = re.findall(r"<Key>([^<]+)</Key>", body)
        for k in keys:
            f.write(urllib.parse.unquote(k) + "\n")
        f.flush()
        total += len(keys)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", body)
        token = m.group(1) if m else None
        if pages % 20 == 0:
            print("  page %d, keys %d" % (pages, total), flush=True)
        if not token or pages >= MAX_PAGES:
            break
        time.sleep(0.03)
    f.close()
    print("DONE pages=%d keys=%d -> %s" % (pages, total, OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
