#!/usr/bin/env python3
"""DNS wordlist brute — additive to passive/CT enumeration (security-recon Step 1b).

Passive subdomain tools (crt.sh, subfinder, amass -passive) source from certificate
transparency logs and therefore CANNOT return: internal app servers, hosts on a
wildcard cert, or services sharing a CDN cert. This script closes that gap.

Usage:
    python dns_wordlist_brute.py genians.com --threads 30 -o recon/dns_brute.json
    python dns_wordlist_brute.py genians.com genians.co.kr --words extra.txt

Notes:
  - No external tooling (no dnsx/massdns) required — socket.gethostbyname with timeout.
  - ~836 candidates resolve in ~6s at 30 threads. Keep threads <= 32 to stay polite.
  - Output JSON is {"resolved":[{host,ip}], "count":N, "probed":M} so a later pass
    can diff without re-requesting.
  - Result is a LEAD LIST, not a scope list: check each host against the program's
    scope wording before sending it any other request.
"""
import argparse
import json
import socket
import sys
from concurrent.futures import ThreadPoolExecutor

# Infrastructure ROLES matter more than product names — this is the list that surfaced
# internal Jira + a second Keycloak + Crowd SSO on a real engagement. Extend per target.
DEFAULT_WORDS = """
www mail webmail smtp pop imap ftp vpn remote gw gateway firewall
dev develop development staging stage test testing qa uat beta alpha demo sandbox lab poc trial
api api1 api2 apis graphql rest gateway proxy bff
admin administrator manage management console portal dashboard panel
git gitlab github gitea bitbucket svn jenkins ci cd build repo registry harbor nexus
jira confluence wiki docs documentation tech
monitor monitoring grafana kibana prometheus zabbix nagios status metrics logs
db database mysql postgres mssql redis mongo elastic elasticsearch
s3 storage files file upload cdn static assets img images media
auth sso login id idp sso2 account accounts keycloak ldap ad
cloud nac ztna mdr edr gsp pi gdpi sase
partner partners reseller sales crm erp hr intranet internal
k8s kubernetes docker swarm rancher openshift
backup bak old legacy temp tmp test1 test2 app apps mobile m
download downloads dl update updates upgrade patch release releases
invoice billing pay payment shop store
gov public secure private extranet ext
report reports analytics bi msp survey webfax rbi kimpd
ns1 ns2 dns mx autodiscover autoconfig ims help support
""".split()


def resolve(host, timeout=2.5):
    try:
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        ip = socket.gethostbyname(host)
        socket.setdefaulttimeout(old)
        return {"host": host, "ip": ip}
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domains", nargs="+", help="one or more apex domains")
    ap.add_argument("--threads", type=int, default=30)
    ap.add_argument("--words", help="extra wordlist file, one word per line")
    ap.add_argument("-o", "--out", default="dns_brute.json")
    args = ap.parse_args()

    words = list(DEFAULT_WORDS)
    if args.words:
        with open(args.words, encoding="utf-8", errors="ignore") as f:
            words += [w.strip() for w in f if w.strip() and not w.startswith("#")]
    words = sorted(set(words))

    # probe the bare apexes themselves too
    targets = list(args.domains) + [w + "." + d for d in args.domains for w in words]
    print(f"probing {len(targets)} hosts ({args.threads} threads)", flush=True)

    resolved = []
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        for r in ex.map(resolve, targets):
            if r:
                resolved.append(r)
                print(f"  {r['host']:<46} {r['ip']}", flush=True)

    # wildcard check — an apex wildcard makes every label resolve and invalidates the count
    import random, string
    print("\nwildcard check:", flush=True)
    for d in args.domains:
        label = "".join(random.choices(string.ascii_lowercase, k=20))
        r = resolve(f"{label}.{d}")
        print(f"  {d:<30} {'WILDCARD -> ' + r['ip'] if r else 'no wildcard'}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"resolved": resolved, "count": len(resolved),
                   "probed": len(targets)}, f, indent=2)
    print(f"\nTOTAL {len(resolved)}/{len(targets)} -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
