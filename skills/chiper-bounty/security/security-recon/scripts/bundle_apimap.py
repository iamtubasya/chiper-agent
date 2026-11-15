#!/usr/bin/env python3
"""bundle_apimap.py - extract the API endpoint map from a page's JS bundles.

Recon Step 3b helper. Stdlib only. Fetches the HTML entry, pulls every .js asset,
regex-mines endpoint-shaped strings and sibling-service hosts, and optionally
prints call-context around a chosen needle using windowed str.find - the correct
way to read a minified bundle (grep -oE '.{N}needle.{N}' hangs on it).

Usage:
    python bundle_apimap.py https://target.example/app
    python bundle_apimap.py https://target.example/app --ctx "oauth2/auth"
    python bundle_apimap.py https://target.example/app --json out.json
"""
import sys
import re
import json
import argparse
import urllib.request
import urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

TOKENS = "graphql|oauth2|oauth|login|sso|webapi|token|reset|verify|callback|upload|invite|auth|session|account|user|v1|v2|v3"
ENDPOINT_RE = re.compile(r'"(/[A-Za-z0-9_./{}:$-]*(?:' + TOKENS + r')[A-Za-z0-9_./{}:$-]*)"')
HOST_RE = re.compile(r'https://[A-Za-z0-9.-]+\.(?:[A-Za-z0-9-]+\.)*[A-Za-z]{2,}[A-Za-z0-9_./-]*')
JS_RE = re.compile(r'(?:src|href)="([^"]+[.]js)"')
REL_FETCH_RE = re.compile(r'window[.]location[.]pathname\s*[+]\s*"([^"]+)"')


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--ctx", help="print call-context around this needle in each bundle")
    ap.add_argument("--json", help="write endpoint map to this JSON file")
    ap.add_argument("--max-js", type=int, default=40)
    a = ap.parse_args()

    base = re.match(r"https?://[^/]+", a.url).group(0)
    html = fetch(a.url)

    js_urls = [urllib.parse.urljoin(base, m) for m in JS_RE.findall(html)]
    js_urls = list(dict.fromkeys(js_urls))[: a.max_js]
    print("[i] %d JS asset(s) on %s" % (len(js_urls), a.url))

    endpoints, hosts, rels, ctx_hits = set(), set(), set(), []
    for u in js_urls:
        try:
            data = fetch(u)
        except Exception as e:
            print("[!] %s: %s" % (u, e))
            continue
        endpoints.update(ENDPOINT_RE.findall(data))
        hosts.update(HOST_RE.findall(data))
        rels.update(REL_FETCH_RE.findall(data))
        if a.ctx:
            i = 0
            while True:
                i = data.find(a.ctx, i)
                if i < 0:
                    break
                ctx_hits.append((u.rsplit("/", 1)[-1], data[max(0, i - 130):i + 150]))
                i += 1

    print("\n=== ENDPOINTS ===")
    for e in sorted(endpoints):
        print("  ", e)
    print("\n=== SIBLING HOSTS ===")
    for h in sorted(hosts):
        print("  ", h)
    print("\n=== RELATIVE FETCH BASES (real API root is often per-path) ===")
    for r in sorted(rels):
        print("  ", r)

    if a.ctx:
        print("\n=== CONTEXT for '%s' ===" % a.ctx)
        for name, snippet in ctx_hits:
            print("  [%s] ...%s..." % (name, snippet))

    if a.json:
        json.dump({"endpoints": sorted(endpoints), "hosts": sorted(hosts),
                   "relative_fetch": sorted(rels)}, open(a.json, "w"), indent=2)
        print("\n[i] wrote %s" % a.json)

    print("\n[i] Classify before testing: SPA routes are not endpoints; 302-to-home = fallback; "
          "'/base/webapi' = real API; POST-only paths 405 on GET.")


if __name__ == "__main__":
    sys.exit(main())
