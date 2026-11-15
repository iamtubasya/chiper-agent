#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Objective scope map: which live hosts actually SERVE the program's security.txt?

Use at the top of Phase 0B when the program's policy defines scope by a marker such as
"only domains/subdomains which have a security.txt file in their root".

    python securitytxt_scope_map.py recon/httpx.txt recon/

Reads a host list (one URL per line, e.g. projectdiscovery httpx output -- extra columns are
ignored), requests /.well-known/security.txt from every host FOLLOWING REDIRECTS, and keeps the
host only if the FINAL body looks like the canonical file.

Why match the body and not the status code (both traps hit live, 2026-10):
  * a 3rd-party host answered 200 with an HTML error page -> a status check says "in scope", the
    Contact-line match correctly rejects it;
  * many hosts answer 302 -> https://<apex>/.well-known/security.txt with an identical body -> a
    strict "no redirect" reading throws away the estate where the real legacy apps live
    (41 in-scope hosts vs 1 on the engagement this was written for).

Outputs (into OUTDIR):
  securitytxt_map.txt   "<host> :: IN-SCOPE (canonical)" | "<host> :: out"
  in_scope_hosts.txt    bare host list, one per line  <- filter every later phase on this
  securitytxt_bodies/   the raw body per IN-SCOPE host, as evidence

Exit code 0 always (a scope map with zero hits is a valid finding, not an error).
"""
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Substrings that identify a real security.txt. Extend with the program's own Contact/Policy.
MARKERS = ("Contact:", "security.txt", "Policy:")

# Be a good citizen: one request per host, spaced. Raise for bigger estates.
DELAY_S = 0.4


def hosts_from(path):
    out, seen = [], set()
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        host = line.split()[0].split("//")[-1].split("/")[0].strip()
        if host and host not in seen:
            seen.add(host)
            out.append(host)
    return out


def probe(host):
    """-> (status, final_url, body) or (None, None, error)."""
    url = "https://%s/.well-known/security.txt" % host
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    ctx = ssl.create_default_context()
    try:
        r = urllib.request.urlopen(req, timeout=15, context=ctx)
        return r.status, r.geturl(), r.read(8000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, getattr(e, "url", url), e.read(8000).decode("utf-8", "replace")
    except Exception as ex:  # noqa: BLE001 - network variance is expected here
        return None, None, "%s: %s" % (type(ex).__name__, ex)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 0
    src = pathlib.Path(argv[1])
    outdir = pathlib.Path(argv[2] if len(argv) > 2 else ".")
    outdir.mkdir(parents=True, exist_ok=True)
    evid = outdir / "securitytxt_bodies"
    evid.mkdir(exist_ok=True)

    hosts = hosts_from(src)
    print("hosts to check: %d" % len(hosts))
    map_lines, in_scope = [], []

    for i, host in enumerate(hosts, 1):
        status, final, body = probe(host)
        is_txt = status is not None and any(m in body for m in MARKERS) and "<html" not in body[:400].lower()
        if is_txt:
            in_scope.append(host)
            (evid / (host + ".txt")).write_text(body, encoding="utf-8")
            verdict = "IN-SCOPE (canonical)"
        else:
            verdict = "out"
        map_lines.append("%s :: %s" % (host, verdict))
        print("  [%d/%d] %-40s %s %s" % (i, len(hosts), host, status, verdict))
        time.sleep(DELAY_S)

    (outdir / "securitytxt_map.txt").write_text("\n".join(map_lines) + "\n", encoding="utf-8")
    (outdir / "in_scope_hosts.txt").write_text("\n".join(in_scope) + "\n", encoding="utf-8")

    print("\nin scope: %d / %d" % (len(in_scope), len(hosts)))
    print("-> %s" % (outdir / "in_scope_hosts.txt"))
    print("\nReview anything that came back 200/302 but was rejected as 'out' -- a status-code-only")
    print("check would have called those in scope, and a vendored/3rd-party host wrongly swept in")
    print("is a program-rule risk, not just noise.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
