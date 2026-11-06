#!/usr/bin/env python3
"""Fleet sweep of an unauthenticated config/status endpoint.

Writes one raw JSON body per host to disk (you WILL need the untruncated values later),
then builds a key -> {value -> [hosts]} field map so you can see, per field, which tenants
are non-default. Never eyeball a handful of hosts and stop -- the interesting tenants are the
ones with populated values.

Usage:
    python fleet_config_sweep.py hosts.txt /api/settings --header "X-Bug-Bounty: you@example.com"
    python fleet_config_sweep.py hosts.txt /api/settings --out ./raw --insecure

Output:
    <out>/settings_full/<host>.json     raw bodies (untruncated)
    <out>/sweep_scan.json               per-host status / size / content-type / cache headers
    <out>/sweep_fieldmap.json           key -> value -> hosts  (the triage input)
    stdout                              field list with distinct-value and host-hit counts
"""
import argparse
import json
import os
import re
import sys
import time
import urllib3

import requests
from requests.adapters import HTTPAdapter

urllib3.disable_warnings()

# Fields that are worth looking at first. Extend per product; the point is to stop you
# reading 60 booleans before you notice the credential.
SENSITIVE = re.compile(
    r"(key|secret|token|pass|cred|apikey|devkey|appid|client|sso|saml|oidc|auth|url|host|"
    r"realm|tenant|domains?|endpoint|smtp|imap|ldap|licen[cs]e|airbrake|registry|salt|sig)",
    re.I,
)


def walk(o, p=""):
    """Yield (dotted path, scalar) for every leaf."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{p}[{i}]")
    else:
        yield p, o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hosts_file")
    ap.add_argument("path", help="e.g. /api/settings")
    ap.add_argument("--out", default="./sweep")
    ap.add_argument("--header", action="append", default=[],
                    help="repeatable, 'Name: value' (identity/scope header + UA)")
    ap.add_argument("--scheme", default="https")
    ap.add_argument("--delay", type=float, default=0.15,
                    help="keep low; a burst block turns every result into a fake 403")
    ap.add_argument("--insecure", action="store_true", default=True)
    a = ap.parse_args()

    headers = {"User-Agent": "Mozilla/5.0 (authorized-security-testing)"}
    for h in a.header:
        k, _, v = h.partition(":")
        headers[k.strip()] = v.strip()

    raw_dir = os.path.join(a.out, "settings_full")
    os.makedirs(raw_dir, exist_ok=True)

    hosts = [x.strip() for x in open(a.hosts_file) if x.strip()]
    hosts = [re.sub(r"^https?://", "", h) for h in hosts]

    # One pooled session for the whole run: a fresh TLS handshake per request trips burst
    # blocks on some edges even at a few requests per second.
    s = requests.Session()
    s.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=4, max_retries=0))

    scan, fieldmap = {}, {}
    ok = 0
    for h in hosts:
        url = f"{a.scheme}://{h}{a.path}"
        rec = {}
        for attempt in range(3):
            try:
                r = s.get(url, headers=headers, verify=not a.insecure, timeout=20,
                          allow_redirects=False)
                break
            except Exception as e:
                rec = {"status": "ERR", "err": f"{type(e).__name__}: {str(e)[:70]}"}
                time.sleep(3 + attempt * 4)
        else:
            scan[h] = rec
            continue

        rec = {"status": r.status_code,
               "ct": r.headers.get("content-type", ""),
               "len": len(r.content),
               "cache": r.headers.get("cache-control", ""),
               "server": r.headers.get("server", "")}
        if r.status_code == 200 and "json" in rec["ct"]:
            try:
                j = r.json()
            except Exception:
                j = None
            if isinstance(j, dict):
                fn = os.path.join(raw_dir, h.replace(":", "_") + ".json")
                with open(fn, "w", encoding="utf-8") as f:
                    json.dump(j, f, indent=1, sort_keys=True)
                rec["keys"] = len(j)
                ok += 1
                for k, v in walk(j):
                    if isinstance(v, (str, int, float, bool)) and str(v) != "":
                        fieldmap.setdefault(k, {}).setdefault(str(v)[:160], []).append(h)
        scan[h] = rec
        time.sleep(a.delay)

    with open(os.path.join(a.out, "sweep_scan.json"), "w") as f:
        json.dump(scan, f, indent=1)
    with open(os.path.join(a.out, "sweep_fieldmap.json"), "w") as f:
        json.dump(fieldmap, f, indent=1)

    # Canary sanity: if nearly everything shares one (status, len), you are looking at a block page.
    pairs = {}
    for r in scan.values():
        if isinstance(r.get("status"), int):
            pairs.setdefault((r["status"], r.get("len")), 0)
            pairs[(r["status"], r.get("len"))] += 1
    if pairs and max(pairs.values()) / max(1, len(scan)) > 0.9:
        top = max(pairs, key=pairs.get)
        print(f"!! WARNING: {pairs[top]}/{len(scan)} responses are identical "
              f"{top[0]} / {top[1]}b -- likely a burst/WAF block page, not real results.\n"
              f"   Re-run at a lower rate and canary a path you know returns 200.\n", file=sys.stderr)

    print(f"hosts probed: {len(hosts)}   JSON 200 config bodies: {ok}\n")
    print(f"{'field':58s} {'distinct':>8s} {'hosthits':>9s}")
    for k in sorted(fieldmap):
        if k.startswith("themes."):      # presentation noise -- drop before review
            continue
        vals = fieldmap[k]
        flag = "  <<<" if SENSITIVE.search(k) else ""
        print(f"{k:58s} {len(vals):8d} {sum(len(v) for v in vals.values()):9d}{flag}")
    print("\nraw bodies   ->", raw_dir)
    print("field map    ->", os.path.join(a.out, "sweep_fieldmap.json"))


if __name__ == "__main__":
    main()
