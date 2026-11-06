#!/usr/bin/env python3
"""cors_origin_sweep.py — classify the Access-Control-* shape of every reachable host.

Sends TWO requests per host (attacker Origin + benign Origin) so that reflection,
wildcard, fixed-allowlist and no-CORS separate cleanly.  A single-origin probe cannot
tell those apart.

A REFLECTS-EVIL + ACAC:true result is a LEAD, not a finding.  Before reporting anything,
verify in a real browser WITH a same-origin control, then answer what the readable body
actually contains and whether the host can set a session at all — see
references/cors-verification-readable-is-not-a-finding.md.

Usage:
    python cors_origin_sweep.py --live live.txt [--delay 1.2] [--out cors-sweep.json]

`--live` accepts the plain `httpx -sc` output (`https://host [200] [tech]`) or a bare
URL-per-line list.  Hosts whose status is not in the reachable set are skipped, as are
the usual static-asset subdomains.
"""
import argparse
import json
import os
import re
import time

import httpx

H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "*/*",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "X-BugBounty-Researcher": "BC_USERNAME",          # set to YOUR programme identifier
}
EVIL = "https://evil.example"
BENIGN = "https://www.finanzen.net"            # set to the target's own apex

ASSET_HOST = re.compile(r"(styles|scripts|images|shared-components|static-content|assets\d?)\.", re.I)
REACHABLE = {"200", "401", "302", "307"}


def load_urls(path):
    urls = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(\S+)\s+\[(\d+)\]", line)
        if m:
            url, code = m.group(1), m.group(2)
            if code not in REACHABLE:
                continue
        else:
            url = line
        if ASSET_HOST.search(url):
            continue
        urls.append(url)
    return urls


def probe(c, url, origin):
    h = dict(H)
    h["Origin"] = origin
    try:
        r = c.get(url, headers=h)
    except Exception as e:
        return {"url": url, "origin": origin, "error": f"{type(e).__name__}: {str(e)[:80]}"}
    return {
        "url": url, "origin": origin, "status": r.status_code,
        "acao": r.headers.get("access-control-allow-origin", ""),
        "acac": r.headers.get("access-control-allow-credentials", ""),
        "acam": r.headers.get("access-control-allow-methods", ""),
        "vary": r.headers.get("vary", ""),
    }


def classify(evil, benign):
    acao = evil.get("acao", "")
    if not acao:
        return "none"
    if EVIL in acao:
        return "MULTI-ITEM" if "," in acao else "REFLECTS-EVIL"
    if acao == "*":
        return "WILDCARD"
    if acao == benign.get("acao") and acao:
        return "FIXED-ALLOWLIST"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True)
    ap.add_argument("--delay", type=float, default=1.2)
    ap.add_argument("--out", default="cors-sweep.json")
    a = ap.parse_args()

    urls = load_urls(a.live)
    print(f"hosts to probe: {len(urls)}")
    results = []
    with httpx.Client(http2=True, headers=H, timeout=25, follow_redirects=False) as c:
        for u in urls:
            evil = probe(c, u, EVIL)
            benign = probe(c, u, BENIGN)
            shape = classify(evil, benign)
            rec = {"shape": shape, "evil": evil, "benign": benign}
            results.append(rec)
            if shape != "none":
                creds = " +ACAC" if evil.get("acac") == "true" else ""
                print(f"[{shape}{creds}] {u}  acao={evil.get('acao')!r}")
            time.sleep(a.delay)

    json.dump(results, open(a.out, "w", encoding="utf-8"), indent=1)
    from collections import Counter
    print("\nshape histogram:", dict(Counter(r["shape"] for r in results)))
    leads = [r for r in results if r["shape"] in ("REFLECTS-EVIL", "MULTI-ITEM")]
    print(f"LEADS requiring browser verification: {len(leads)}")
    for r in leads:
        print(f"   {r['shape']:14} {r['evil']['url']}")
    print("saved:", os.path.abspath(a.out))
    print("\nREMINDER: a REFLECTS-EVIL lead is not a finding until a real-browser "
          "credentialed read succeeds AND the body is sensitive AND the host can set a "
          "session. See references/cors-verification-readable-is-not-a-finding.md")


if __name__ == "__main__":
    main()
