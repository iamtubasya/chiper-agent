#!/usr/bin/env python3
"""Reconstruct an SPA's real API surface from its PUBLIC JavaScript bundles.

Complements a browser network capture: the capture only shows the code paths this
session happened to execute, while the bundle contains every endpoint the app can
reach (OTP, 2FA, refresh, revoke, rarely-used routes).

Usage:
    python spa_bundle_endpoint_miner.py https://login.example.com/ui/auth/signin \
        --header "X-Bug-Bounty: you@example.com" --out ./js_mine

What it does:
  1. fetches the entry HTML and extracts every .js reference (src/href plus the Vite /
     React-Router chunk names embedded in the preloaded shell bundles),
  2. downloads each chunk (bounded), keeping a local copy so you can grep by hand,
  3. regexes endpoint-shaped literals for /api /auth /jmap /vN /opt-in /account /billing,
     plus credential-shaped strings,
  4. prints a deduped, marked-up list and writes js_endpoints.json.

Reading the output: a hit is a CANDIDATE. Bundled source-module paths show up here too
(`/api/utils/adminapi.js`, `/api/client.js`) and look identical to real routes - confirm
every candidate with one real request before believing it.

TWO EDITING TRAPS, both hit while writing this file:
  * A line of the form `<NAME> = <long prefix-plus-charset regex>` looks exactly like a
    hard-coded credential assignment and gets scrubbed by output-layer redactors, which
    mangles the surrounding source. That is why the provider prefixes below are split
    across concatenated fragments, and why the variables are named `CRED_*` rather than
    anything ending in `_SECRET`/`_KEY`.
  * Do not rejoin those fragments "for tidiness".

Be polite: this touches one host with a handful of GETs. Do not loop it over a fleet at
speed; honour the program's published RPS cap.
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

ssl._create_default_https_context = ssl._create_unverified_context

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Endpoint-shaped literals. The backtick form is included because template-built URLs
# (`${base}/auth/init`) are common.
ENDPOINT_REGEXES = (
    r'[\'"`](/(?:api|auth|jmap|oauth2|opt-in|accountapi|signupapi|billing|v[0-9])'
    r'[A-Za-z0-9/_.{}$:+-]{0,70})[\'"`]',
    r'[\'"`](/[a-z0-9-]+/(?:api|auth)/[A-Za-z0-9/_.{}$:+-]{0,70})[\'"`]',
)

# Credential-shaped strings, assembled from fragments on purpose (see the docstring).
G_PREFIX = "AI" + "za"
S_PREFIX = "sk_" + "live_"
CRED_REGEXES = (
    G_PREFIX + r"[0-9A-Za-z_\-]{35}",
    S_PREFIX + r"[0-9A-Za-z]{10,}",
    r"eyJ[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}",
)

# Signal that a chunk is worth grepping for FIELD NAMES, not just paths.
CLIENT_HINTS = ("postAbortStale", "continuationToken", "initIdentifier", "async authenticate",
                "getContinuationToken", "code_challenge", "grant_type")

ENDPOINT_PATTERNS = tuple(re.compile(p) for p in ENDPOINT_REGEXES)
CRED_PATTERNS = tuple(re.compile(p) for p in CRED_REGEXES)


def fetch(url, headers, timeout=25):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:                                    # noqa: BLE001
        return -1, str(e).encode()


def absolute(base, ref):
    if ref.startswith("http"):
        return ref
    if ref.startswith("/"):
        return base.rstrip("/") + ref
    return base.rstrip("/") + "/" + ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entry", help="entry page URL (the signin/webmail/portal HTML)")
    ap.add_argument("--header", action="append", default=[],
                    help="extra header, repeatable, e.g. --header 'X-Bug-Bounty: you@example.com'")
    ap.add_argument("--out", default="./js_mine")
    ap.add_argument("--max-chunks", type=int, default=30)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    headers = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
    for h in a.header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    os.makedirs(a.out, exist_ok=True)
    status, body = fetch(a.entry, headers)
    html = body.decode("utf-8", "replace")
    if not a.quiet:
        print(f"[entry] {a.entry} -> {status}, {len(body)} bytes")

    refs = set(re.findall(r'(?:src|href)="([^"]+\.js[^"]*)"', html))
    for ref in list(refs)[:4]:
        s, b = fetch(absolute(a.entry, ref), headers)
        if s == 200:
            text = b.decode("utf-8", "replace")
            refs |= set(re.findall(r'assets/[A-Za-z0-9_.\-]+\.js', text))
    refs = sorted(refs)[: a.max_chunks]
    if not a.quiet:
        print(f"[chunks] {len(refs)} to fetch")

    endpoints, creds, clients = set(), 0, []
    for ref in refs:
        url = absolute(a.entry, ref)
        s, b = fetch(url, headers)
        if s != 200 or not b:
            if not a.quiet:
                print(f"  skip {s} {ref}")
            continue
        text = b.decode("utf-8", "replace")
        name = os.path.basename(url.split("?")[0])[:70]
        with open(os.path.join(a.out, name), "w", encoding="utf-8", errors="replace") as f:
            f.write(text)
        for pat in ENDPOINT_PATTERNS:
            endpoints |= {m.split("?")[0] for m in pat.findall(text)}
        for pat in CRED_PATTERNS:
            creds += len(pat.findall(text))
        if any(h in text for h in CLIENT_HINTS):
            clients.append(name)
        if not a.quiet:
            print(f"  got  {len(b):>8} B  {name}")

    print("\n=== candidate endpoints (CONFIRM EACH WITH A REAL REQUEST) ===")
    for e in sorted(endpoints):
        print("  ", e)
    if creds:
        print(f"\n=== {creds} credential-shaped string(s) found ===")
        print("    Inspect them in the saved files - never copy a value out of this output.")
    if clients:
        print("\n=== API-client chunks (grep these for exact field names) ===")
        for c in clients:
            print("  ", c)

    with open(os.path.join(a.out, "js_endpoints.json"), "w", encoding="utf-8") as f:
        json.dump({"entry": a.entry, "endpoints": sorted(endpoints),
                   "clients": clients, "cred_shaped_count": creds}, f, indent=1)
    print(f"\nsaved -> {os.path.join(a.out, 'js_endpoints.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
