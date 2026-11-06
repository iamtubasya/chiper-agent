#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decide the severity of a client-IP-header finding by measurement, not by argument.

When a target builds session ids (or any decision) from `X-Forwarded-For` / `Client-IP`, the
interesting question is NOT "is the header reflected" — it is "does ANY endpoint change its answer
when the header changes". This script answers that.

For every host x path it issues two requests — one clean, one carrying `X-Forwarded-For: 127.0.0.1` —
and diffs status code + body sha256 + body length. A diff means the endpoint is genuinely
client-IP-sensitive and the finding may escalate; zero diffs across the whole surface is what lets you
report the family honestly as Low.

Usage:
    python xff_authz_diff.py hosts.txt paths.txt out.json [--xff 127.0.0.1] [--delay 0.35]

    hosts.txt : one hostname per line (e.g. live hosts, or your in-scope set)
    paths.txt : one path per line, e.g.
                    /
                    /admin/
                    /static-api/
                    /api/
                    /actuator/health
    out.json  : full per-request record (clean + xff) so a later pass can re-triage without re-asking

Exit code is 0 whether or not diffs were found; read the printed DIFFS line and the JSON.

Deliberately low-rate (0.35 s between requests by default) — this is a measurement, not a scan, and it
is meant to stay inside a "no volumetric testing" program rule. 42 hosts x 5 paths x 2 = 420 requests
takes ~5 minutes. Redirects are NOT followed: a 303's Location can itself be the interesting signal.
"""
import argparse
import hashlib
import json
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def make_opener():
    ctx = ssl.create_default_context()
    return urllib.request.build_opener(NoRedirect,
                                       urllib.request.HTTPSHandler(context=ctx))


def fetch(op, url, xff, timeout):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    if xff:
        req.add_header("X-Forwarded-For", xff)
    try:
        r = op.open(req, timeout=timeout)
        body = r.read(6000)
        return {"s": r.status, "n": len(body), "loc": r.headers.get("Location", ""),
                "sha": hashlib.sha256(body).hexdigest()[:12]}
    except urllib.error.HTTPError as e:
        body = e.read(6000)
        return {"s": e.code, "n": len(body), "loc": e.headers.get("Location", ""),
                "sha": hashlib.sha256(body).hexdigest()[:12]}
    except Exception as ex:
        return {"err": type(ex).__name__}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hosts")
    ap.add_argument("paths")
    ap.add_argument("out")
    ap.add_argument("--xff", default="127.0.0.1",
                    help="spoofed client IP to test with (default 127.0.0.1)")
    ap.add_argument("--delay", type=float, default=0.35)
    ap.add_argument("--timeout", type=float, default=14.0)
    a = ap.parse_args()

    hosts = [h.strip() for h in pathlib.Path(a.hosts).read_text().splitlines() if h.strip()]
    paths = [p.strip() for p in pathlib.Path(a.paths).read_text().splitlines() if p.strip()]
    hosts = [h.replace("https://", "").replace("http://", "").rstrip("/") for h in hosts]

    op = make_opener()
    records, diffs = [], []
    for h in hosts:
        for p in paths:
            if not p.startswith("/"):
                p = "/" + p
            url = "https://" + h + p
            clean = fetch(op, url, None, a.timeout)
            time.sleep(a.delay)
            spoofed = fetch(op, url, a.xff, a.timeout)
            time.sleep(a.delay)
            rec = {"host": h, "path": p, "clean": clean, "xff": spoofed}
            records.append(rec)
            if (clean.get("s") != spoofed.get("s")
                    or clean.get("sha") != spoofed.get("sha")
                    or clean.get("n") != spoofed.get("n")):
                diffs.append(rec)

    pathlib.Path(a.out).write_text(json.dumps(records, indent=1), encoding="utf-8")
    print("hosts          :", len(hosts))
    print("paths          :", len(paths))
    print("requests       :", len(records) * 2)
    print("DIFFS          :", len(diffs))
    for d in diffs:
        print("  -", d["host"], d["path"], "clean:", d["clean"], "xff:", d["xff"])
    if not diffs:
        print("\n=> 0 client-IP-sensitive endpoints. Report the reflection family as Low and say the "
              "decisive test was run and returned nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
