#!/usr/bin/env python3
"""h2_browser_client.py — HTTP/2 + full-browser-header probe harness.

For hosts where the edge denies HTTP/1.1 and denies the Go scanner stack outright
(see references/http2-alpn-edge-discriminator.md). GET or JSON POST, sequential,
delayed, policy identification header on every request.

  python h2_browser_client.py https://host/path
  python h2_browser_client.py --list urls.txt -o OUTDIR --delay 1.5
  python h2_browser_client.py --post-json '{"a":1}' https://host/api/thing
  python h2_browser_client.py --headers-only https://host/path     # status line only

Edit RESEARCHER_HEADER for the programme's own required identification value.
"""
import argparse
import json
import os
import time

import httpx

# Programme-mandated identification header. Set the value the policy names.
RESEARCHER_HEADER = ("X-BugBounty-Researcher", "BC_USERNAME")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Document-class request (page GET): Sec-Fetch-* = document/navigate/none.
PAGE_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    RESEARCHER_HEADER[0]: RESEARCHER_HEADER[1],
}

# API-class request: Sec-Fetch-* = empty/cors/cross-site.
API_HEADERS = dict(PAGE_HEADERS)
API_HEADERS.update({
    "Accept": "application/json, text/plain, */*",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "",
})
API_HEADERS.pop("Sec-Fetch-User")
API_HEADERS.pop("Upgrade-Insecure-Requests")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--list", dest="listfile")
    ap.add_argument("-o", "--outdir")
    ap.add_argument("--delay", type=float, default=1.2,
                    help="seconds between requests - keep >=1.0, this is a probe not a fuzzer")
    ap.add_argument("--api", action="store_true", help="use API-class Sec-Fetch values")
    ap.add_argument("--post-json")
    ap.add_argument("--headers-only", action="store_true")
    ap.add_argument("--snippet", type=int, default=200)
    a = ap.parse_args()

    urls = []
    if a.listfile:
        urls = [u.strip() for u in open(a.listfile, encoding="utf-8") if u.strip()]
    elif a.url:
        urls = [a.url]
    else:
        ap.error("need a URL or --list")

    hdrs = dict(API_HEADERS if a.api else PAGE_HEADERS)
    if a.outdir:
        os.makedirs(a.outdir, exist_ok=True)

    with httpx.Client(http2=True, headers=hdrs, timeout=30, follow_redirects=False) as c:
        for i, u in enumerate(urls):
            try:
                r = c.request("POST" if a.post_json else "GET", u,
                              content=a.post_json.encode() if a.post_json else None)
            except Exception as e:
                print(f"ERR {u} {type(e).__name__} {str(e)[:120]}", flush=True)
                continue
            print(f"[{r.status_code} {r.http_version} {len(r.content):>9}] {u} "
                  f"ct={r.headers.get('content-type','')} loc={r.headers.get('location','')}",
                  flush=True)
            if a.headers_only:
                pass
            else:
                body = r.content.decode("utf-8", "replace")
                print("   " + body[: a.snippet].replace("\n", " "), flush=True)
                if a.outdir and r.content:
                    safe = u.split("//", 1)[-1].replace("/", "_").replace("?", "_").replace("&", "_")[:150]
                    open(os.path.join(a.outdir, safe + ".body"), "w",
                         encoding="utf-8", errors="replace").write(body)
            time.sleep(a.delay)


if __name__ == "__main__":
    main()
