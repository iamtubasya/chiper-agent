#!/usr/bin/env python3
"""
panel_func_enum.py -- generic vendor-panel function enumerator.

Logs in as a given identity, calls every function in a function list with no
parameters, classifies each response, and writes per-identity JSON so two
scans can be diffed.

Part of the `security/vendor-product-lab` skill. See its SKILL.md Phase 7 for
the methodology this implements.

Usage
-----
  # 1. extract the function list from the product's UI metadata first, e.g.
  #    grep -o 'func="[^"]*"' billmgr.xml | sed 's/func="//;s/"//' | sort -u > funcs.txt
  #
  # 2. enumerate as the lowest-privilege identity
  python3 panel_func_enum.py --base https://127.0.0.1:1500/billmgr \
      --user user1 --password Pass1234 --funcs funcs.txt --out scan_user1.json
  #
  # 3. repeat as a higher-privilege identity, then diff
  python3 panel_func_enum.py --base ... --user emp1 --password ... --out scan_emp1.json
  python3 panel_func_enum.py --diff scan_user1.json scan_emp1.json

Classification
--------------
  DENIED            access control fired -> deprioritise
  GATE_PASSED       "missing parameter" -> the access gate PASSED, ownership
                    check may live after param validation. PRIME LEAD.
  DATA              real payload returned -> investigate immediately
  ERR:<type>        other structured error (config gap, validation, ...)
  EMPTY / OTHER     unclassified, inspect manually

Design notes (each of these was a real bug once)
------------------------------------------------
* The panel's web server usually binds the distro/container IP, NOT 127.0.0.1.
  Pass --base explicitly; do not assume localhost.
* `X-Requested-With: XMLHttpRequest` is frequently REQUIRED. Without it the
  server returns the SPA HTML shell and every function looks like a failure.
* urllib: `urllib.request.urlopen()` does NOT use your opener, so an
  HTTPCookieProcessor never fires and you silently scan as ANONYMOUS. Always
  call `opener.open(req)`. The script asserts the cookie is non-empty.
* Retries with backoff: WSL/container services are often still booting.
"""

import argparse
import concurrent.futures
import http.cookiejar
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Response bodies can be large; only the head matters for classification.
CLASSIFY_WINDOW = 4000

DENIED_MARKERS = (
    '"$type":"access"',
    "Insufficient privileges",
    "access denied",
    "Access denied",
)


def build_opener(verify_tls: bool):
    ctx = ssl.create_default_context()
    if not verify_tls:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def open_with_retry(opener, req, timeout=30, attempts=8):
    """Open with backoff. Services in a fresh container are often not up yet."""
    last = None
    for i in range(attempts):
        try:
            return opener.open(req, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - we re-raise the last one
            last = exc
            time.sleep(1.0 + 1.0 * i)
    raise last


def post(opener, base, cookie, params, timeout=30):
    """POST a form and return (status, body). Never raises on HTTP errors."""
    body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        base,
        data=body,
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with open_with_retry(opener, req, timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def login(opener, base, user, password, auth_func="auth", lang="en"):
    """Authenticate and return the Cookie header string.

    Uses a dedicated opener wired to a CookieJar -- and calls opener.open(),
    never urlopen(), or the jar stays empty and the scan runs anonymously.
    """
    jar = http.cookiejar.CookieJar()
    auth_opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
        urllib.request.HTTPCookieProcessor(jar),
    )
    params = {
        "func": auth_func,
        "username": user,
        "password": password,
        "lang": lang,
        "sok": "ok",
    }
    req = urllib.request.Request(
        base,
        data=urllib.parse.urlencode(params).encode(),
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        },
    )
    open_with_retry(auth_opener, req).read()
    cookie = "; ".join(f"{c.name}={c.value}" for c in jar)
    if not cookie:
        raise SystemExit(
            "FATAL: no session cookie captured. Either the credentials are wrong "
            "or the auth endpoint differs -- inspect the login form's actual "
            "request before enumerating. Refusing to scan anonymously."
        )
    return cookie


def classify(body):
    if not body:
        return "EMPTY"
    head = body[:CLASSIFY_WINDOW]
    if any(m in head for m in DENIED_MARKERS):
        return "DENIED"
    if '"error"' in head:
        m = re.search(r'"\$type":"([a-z_]+)"', head)
        etype = m.group(1) if m else "other"
        # A missing-parameter error means the access gate already passed.
        if etype in ("missed", "missing") or "missed" in head.lower():
            return "GATE_PASSED"
        return "ERR:" + etype
    if '"doc"' in head:
        return "DATA"
    return "OTHER"


def enumerate_functions(opener, base, cookie, funcs, workers=2, delay=0.0):
    results = {}

    def work(func):
        if delay:
            time.sleep(delay)
        status, body = post(opener, base, cookie, {"func": func, "out": "json"})
        return func, status, classify(body), len(body)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for func, status, klass, size in pool.map(work, funcs):
            results[func] = {"status": status, "class": klass, "len": size}
            if klass != "DENIED":
                print(f"{klass:14s} {status} {size:8d}  {func}", flush=True)
    return results


def diff_scans(path_a, path_b):
    a = json.load(open(path_a, encoding="utf-8"))
    b = json.load(open(path_b, encoding="utf-8"))
    print(f"\n=== DIFF {path_a} (A) vs {path_b} (B) ===")

    only_a = [f for f in a if f not in b]
    only_b = [f for f in b if f not in a]
    escalated = [
        f for f in a
        if f in b and a[f]["class"] != "DENIED" and b[f]["class"] == "DENIED"
    ]
    gated = [f for f in a if a[f]["class"] == "GATE_PASSED"]

    print(f"\n[A] functions absent from [B] ({len(only_a)}):")
    print("   " + ", ".join(sorted(only_a)) or "   (none)")
    print(f"\n[B] functions absent from [A] ({len(only_b)}):")
    print("   " + ", ".join(sorted(only_b)) or "   (none)")
    print(f"\nReachable by A but DENIED for B ({len(escalated)}) -- privesc candidates:")
    print("   " + ", ".join(sorted(escalated)) or "   (none)")
    print(f"\n[A] gate-passed leads ({len(gated)}) -- drive these with real object IDs:")
    print("   " + ", ".join(sorted(gated)) or "   (none)")

    from collections import Counter
    for label, scan in (("A", a), ("B", b)):
        print(f"\n[{label}] class distribution: "
              + str(dict(Counter(v["class"] for v in scan.values()))))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="panel base URL, e.g. https://10.0.0.5:1500/billmgr")
    ap.add_argument("--user")
    ap.add_argument("--password")
    ap.add_argument("--funcs", help="file with one function name per line")
    ap.add_argument("--out", help="where to write the per-identity JSON result")
    ap.add_argument("--auth-func", default="auth")
    ap.add_argument("--workers", type=int, default=2,
                    help="keep low; these panels are single-process C++ daemons")
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--verify-tls", action="store_true",
                    help="panel certs are self-signed by default; off is normal")
    ap.add_argument("--diff", nargs=2, metavar=("SCAN_A", "SCAN_B"),
                    help="diff two previous scan outputs instead of scanning")
    ap.add_argument("--no-auth", action="store_true",
                    help="unauthenticated-reach probe: enumerate with NO session "
                         "cookie. A separate, valuable scan -- any function that "
                         "does not return access-denied here is reachable with no "
                         "credentials at all. Run it IN ADDITION to the "
                         "authenticated scan, never instead of it.")
    args = ap.parse_args()

    if args.diff:
        diff_scans(args.diff[0], args.diff[1])
        return

    if args.no_auth:
        for req in ("base", "funcs", "out"):
            if not getattr(args, req):
                ap.error(f"--{req} is required (unless --diff is used)")
    else:
        for req in ("base", "user", "password", "funcs", "out"):
            if not getattr(args, req):
                ap.error(f"--{req} is required (unless --diff or --no-auth is used)")

    funcs = [l.strip() for l in open(args.funcs, encoding="utf-8") if l.strip()]
    funcs = sorted(set(funcs))
    print(f"loaded {len(funcs)} functions from {args.funcs}", flush=True)

    opener = build_opener(args.verify_tls)
    if args.no_auth:
        cookie = ""
        print("WARNING: no session cookie -- this is an UNAUTHENTICATED-REACH "
              "probe. Anything not DENIED here is reachable with no credentials.",
              flush=True)
    else:
        cookie = login(opener, args.base, args.user, args.password, args.auth_func)
        print(f"authenticated as {args.user}; session cookie acquired", flush=True)

    results = enumerate_functions(opener, args.base, cookie, funcs,
                                  workers=args.workers, delay=args.delay)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)

    from collections import Counter
    who = "ANONYMOUS (--no-auth)" if args.no_auth else args.user
    print(f"\n=== SUMMARY {who} ===", flush=True)
    for klass, count in sorted(Counter(v["class"] for v in results.values()).items(),
                               key=lambda kv: -kv[1]):
        print(f"  {klass:14s} {count}")
    print(f"\nwrote {args.out}")
    print("REMINDER: GATE_PASSED and DATA are LEADS, not findings. Execute the")
    print("action with competing identities and reproduce 3x before reporting.")


if __name__ == "__main__":
    sys.exit(main())
