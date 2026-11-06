#!/usr/bin/env python3
"""Flag out-of-scope hosts BEFORE they appear in a bug-bounty report.

Policy clause this exists for (common wording):
  "All domain scopes exclude any host that is a CNAME alias for a third-party system or is
   proxied directly to a third-party platform ... Testing out-of-scope assets is not
   authorized and is not covered by safe harbor."

So: every host you list as "affected" must resolve to the target's OWN infrastructure.
First-party CNAMEs (target host -> another target host) are fine. Third-party aliases are
not, and naming one in a report is a scope violation regardless of how good the finding is.

Usage:
  python host_scope_check.py hosts.txt                       # one host per line
  python host_scope_check.py hosts.txt --keep-first-party    # rewrite a filtered list
  python host_scope_check.py hosts.txt --third-party-file third_party_patterns.txt

Exit code 1 if any third-party alias was found (handy in a pre-submission gate).

Notes
- Uses nslookup, which exists on Windows/POSIX without extra installs. If `dig` is present
  it is preferred (cleaner CNAME output).
- First-party judgement is deliberately conservative: anything resolving to a well-known
  third-party platform suffix is flagged, and everything else is reported as
  "CNAME -> <name>" so a human can decide. Never auto-trust a host you have not looked at.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import pathlib
import re
import shutil
import subprocess
import sys

# suffixes that mean "this host is served by somebody else"
THIRD_PARTY = (
    "cloudfront.net", "zendesk.com", "fastly.net", "akamaiedge.net", "akamai.net",
    "herokudns.com", "herokuapp.com", "azureedge.net", "azurewebsites.net",
    "cloudapp.azure.com", "trafficmanager.net", "elb.amazonaws.com",
    "s3.amazonaws.com", "s3-website", "googleusercontent.com", "ghs.googlehosted.com",
    "my.salesforce.com", "force.com", "hubspot.net", "hs-sites.com", "wpengine.com",
    "pantheonsite.io", "netlify.app", "vercel.app", "pages.dev", "webflow.io",
    "statuspage.io", "statuspage.xyz", "readme.io", "intercom.help",
    "cdn.cloudflare.net", "cloudflare.net", "incapsula.com", "impervadns.net",
    "chd01.com", "bitly.com", "short.io", "typeform.com", "surveymonkey.com",
    "squarespace.com", "shopify.com", "myshopify.com", "bigcartel.com",
    "freshdesk.com", "zendesk.com", "helpscoutdocs.com", "tawk.to",
)

DIG = shutil.which("dig")
NSLOOKUP = shutil.which("nslookup") or "/c/WINDOWS/system32/nslookup"


def cname_of(host: str) -> str | None:
    """Return the canonical name for `host`, or None when it is not a CNAME."""
    try:
        if DIG:
            r = subprocess.run([DIG, "+short", "CNAME", host], capture_output=True,
                               text=True, timeout=25)
            out = (r.stdout or "").strip().splitlines()
            if out:
                return out[-1].strip().rstrip(".").lower()
            return None
        r = subprocess.run([NSLOOKUP, "-type=CNAME", host], capture_output=True,
                           text=True, timeout=25)
        out = (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"ERROR:{e}"[:60]
    m = re.findall(r"canonical name\s*=\s*([^\r\n]+)", out, re.I)
    if m:
        return m[-1].strip().rstrip(".").lower()
    a = re.findall(r"[Aa]liases:\s*([^\r\n]+)", out)
    if a and a[0].strip():
        return a[0].strip().rstrip(".").lower()
    return None


def is_third_party(name: str, extra: tuple[str, ...]) -> bool:
    n = name.lower().rstrip(".")
    return any(n == s or n.endswith("." + s) or s in n for s in THIRD_PARTY + extra)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("hosts_file")
    ap.add_argument("--third-party-file", help="extra suffixes, one per line")
    ap.add_argument("--keep-first-party", action="store_true",
                    help="write <hosts_file>.in-scope.txt with only safe hosts")
    ap.add_argument("--target-suffix", action="append", default=[],
                    help="a suffix considered first-party (repeatable), e.g. --target-suffix acme.com")
    args = ap.parse_args()

    extra: tuple[str, ...] = tuple(args.target_suffix)
    if args.third_party_file:
        p = pathlib.Path(args.third_party_file)
        extra = extra + tuple(x.strip().lower() for x in p.read_text().splitlines() if x.strip())

    path = pathlib.Path(args.hosts_file)
    hosts = sorted({h.strip().lower().rstrip(".") for h in path.read_text().splitlines() if h.strip()})
    if not hosts:
        print("no hosts in file", file=sys.stderr)
        return 2

    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(lambda h: (h, cname_of(h)), hosts))

    in_scope, third, unknown = [], [], []
    for host, cname in res:
        if cname is None:
            in_scope.append(host)                      # A record directly: first party
        elif str(cname).startswith("ERROR:"):
            unknown.append((host, cname))
        elif is_third_party(cname, extra):
            third.append((host, cname))
        else:
            in_scope.append(host)                      # first-party CNAME chain

    print(f"hosts checked       : {len(hosts)}")
    print(f"OK (own infra)      : {len(in_scope)}")
    print(f"THIRD-PARTY ALIAS   : {len(third)}   <-- EXCLUDE from the report; do not test")
    for h, c in third:
        print(f"   {h:<56} CNAME -> {c}")
    if unknown:
        print(f"UNRESOLVED/ERROR    : {len(unknown)}")
        for h, c in unknown:
            print(f"   {h:<56} {c}")

    if args.keep_first_party:
        out = path.with_suffix(".in-scope.txt")
        out.write_text("\n".join(in_scope) + "\n", encoding="utf-8")
        print(f"\nsafe host list -> {out}")

    print("\nReminder: disclose any incidental requests you already sent to the excluded hosts"
          " in one line, then stop touching them.")
    return 1 if third else 0


if __name__ == "__main__":
    raise SystemExit(main())
