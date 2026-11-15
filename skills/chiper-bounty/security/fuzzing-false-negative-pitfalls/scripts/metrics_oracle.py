#!/usr/bin/env python3
"""Metrics-oracle route discovery.

Finds HTTP routes that wordlists miss, by using a Prometheus /metrics registry
as a side-channel: probe a candidate path, see whether a specific counter moved.

Why this exists
---------------
On a real target, a 1,934-path ffuf sweep missed the payment callback entirely.
The public /metrics endpoint exposed
    binobi_moneygrator_callback_events_total{outcome="received"}
so probing POST /moneygrator/callback and watching that counter for a delta of
exactly +1 located the route in two attempts.

Usage
-----
    python metrics_oracle.py --metrics https://api.target.com/metrics \
        --counter 'moneygrator_callback_events_total{outcome="received"}' \
        --base https://api.target.com \
        --method POST --body '{}' \
        --paths candidates.txt

Each candidate is probed one at a time (serial on purpose: parallel probes make
the delta unattributable). A hit means the route exists AND executed real work.

Sanity gate
-----------
Run with --baseline-only first. If counters move while you are doing nothing,
ambient traffic will poison every probe and the result is meaningless.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def grab(metrics_url, timeout=20):
    """Fetch the registry and parse `name{labels} value` lines into a dict."""
    req = urllib.request.Request(metrics_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        text = f.read().decode(errors="ignore")
    out = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_:][A-Za-z0-9_:]*(?:\{[^}]*\})?)\s+([0-9.eE+-]+)$", line)
        if m:
            out[m.group(1)] = float(m.group(2))
    return out


def counter(reg, key):
    """Sum every series matching `key`.

    Accepts a bare metric name (sums all label sets) or a fully-qualified
    series such as 'foo_total{outcome="received"}'.
    """
    if "{" in key:
        return reg.get(key, 0.0)
    return sum(v for k, v in reg.items() if k == key or k.startswith(key + "{"))


def probe(url, method="POST", body=b"{}", headers=None, timeout=12):
    h = {"User-Agent": UA, "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    data = body if method.upper() not in ("GET", "HEAD") else None
    req = urllib.request.Request(url, data=data, headers=h, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as f:
            return f.status, f.read(400).decode(errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode(errors="ignore")
    except Exception as e:  # noqa: BLE001 - network noise is expected
        return 0, str(e)[:120]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True, help="Prometheus registry URL")
    ap.add_argument("--counter", required=True, help="counter name or full series")
    ap.add_argument("--base", required=True, help="base URL, e.g. https://api.target.com")
    ap.add_argument("--paths", required=True, help="file of candidates, one per line")
    ap.add_argument("--method", default="POST")
    ap.add_argument("--body", default="{}")
    ap.add_argument("--header", action="append", default=[], metavar="K:V")
    ap.add_argument("--settle", type=float, default=0.4, help="seconds to wait for flush")
    ap.add_argument("--baseline-only", action="store_true", help="just check the oracle is quiet")
    args = ap.parse_args()

    hdrs = {}
    for h in args.header:
        k, _, v = h.partition(":")
        hdrs[k.strip()] = v.strip()

    print("[*] baseline check (20s, expect zero deltas)")
    prev = grab(args.metrics)
    quiet = True
    for i in range(2):
        time.sleep(10)
        cur = grab(args.metrics)
        d = counter(cur, args.counter) - counter(prev, args.counter)
        print(f"    window {i + 1}: delta={d}")
        if d != 0:
            quiet = False
        prev = cur
    if not quiet:
        print("[!] oracle is NOT quiet - ambient traffic will poison results.")
        print("    Pick a more specific counter, or accept false positives.")
        if args.baseline_only:
            sys.exit(1)
    elif args.baseline_only:
        print("[+] oracle is quiet, safe to probe")
        sys.exit(0)

    paths = [p.strip() for p in open(args.paths) if p.strip()]
    if any(p.startswith("/") for p in paths):
        print("[!] wordlist has leading slashes -> doubled path (//x) false negatives.")
        paths = [p.lstrip("/") for p in paths]
        print("    normalised in memory")

    print(f"[*] probing {len(paths)} candidates against {args.counter}")
    hits = []
    prev = grab(args.metrics)
    for p in paths:
        url = args.base.rstrip("/") + "/" + p.lstrip("/")
        status, body = probe(url, args.method, args.body.encode(), hdrs)
        time.sleep(args.settle)
        cur = grab(args.metrics)
        d = counter(cur, args.counter) - counter(prev, args.counter)
        prev = cur
        if d > 0:
            hits.append((p, status, d, body))
            print(f"  HIT  +{d:g}  {args.method} {p}  -> {status}  {body[:90]!r}")
        time.sleep(0.15)

    print(f"\n[*] {len(hits)} route(s) confirmed by counter movement")
    if hits:
        print(json.dumps([{"path": h[0], "status": h[1], "delta": h[2]} for h in hits], indent=1))
    print("\nReminder: a hit means the route exists AND executed real work.")
    print("          Re-probe once more per hit to rule out coincidence.")


if __name__ == "__main__":
    main()
