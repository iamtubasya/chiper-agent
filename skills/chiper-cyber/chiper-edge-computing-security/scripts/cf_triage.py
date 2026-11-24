#!/usr/bin/env python3
"""cf-triage — 60-second Cloudflare gate triage before any expensive work.

Answers three questions in one shot:
  1. Is the target fronted by Cloudflare, and is the gate a managed challenge?
  2. Is the origin IP discoverable from passive sources?
  3. Is OUR egress IP good enough to even attempt a browser bypass?

Usage:
    python3 cf_triage.py target.example
    python3 cf_triage.py target.example --egress-only

Exit code 0 always — this is an information gatherer, not a gate.

Rationale (see references/cloudflare-managed-challenge-bypass.md):
stealth-browser grinding from a datacenter IP is wasted effort. Check the egress
ASN FIRST, decide, then spend time.
"""
import json
import subprocess
import sys
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

CLOUDFLARE_NETS = [
    "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "162.158.0.0/15",
    "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
    "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20",
    "131.0.72.0/22", "173.245.48.0/20",
]

TRANSIT_HINTS = ("cloudflare", "amazon", "aws", "google", "microsoft", "azure",
                 "digitalocean", "linode", "vultr", "hetzner", "ovh", "tencent",
                 "alibaba", "oracle", "contabo", "choopa")


def http(url, timeout=20, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(200_000).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - network flake is expected
        return None, {}, f"ERROR: {e}"


def section(t):
    print(f"\n=== {t} ===")


def egress_check():
    section("EGRESS IP / ASN (the thing people forget to check)")
    code, _, body = http("https://ipinfo.io/json", 12)
    if code != 200:
        print("  could not resolve egress:", body[:200])
        return True
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        print("  unparsable:", body[:200])
        return True
    org = (d.get("org") or "").lower()
    datacenter = any(h in org for h in TRANSIT_HINTS)
    print(f"  ip      : {d.get('ip')}")
    print(f"  org     : {d.get('org')}")
    print(f"  country : {d.get('country')}")
    print(f"  verdict : {'DATACENTER — CF will auto-challenge' if datacenter else 'likely residential/mobile — stealth may work'}")
    if datacenter:
        print("  action  : do NOT grind on fingerprint patches. Use residential proxy,")
        print("            a solver API, or hand the page dump to the user's own browser")
        print("            and harvest cf_clearance (bind it to their UA + IP).")
    return not datacenter


def gate_check(host):
    section(f"CLOUDFLARE GATE — https://{host}/")
    code, hdrs, body = http(f"https://{host}/")
    lower = {k.lower(): v for k, v in hdrs.items()}
    print(f"  status          : {code}")
    print(f"  server          : {lower.get('server', '-')}")
    print(f"  cf-ray          : {lower.get('cf-ray', '-')}")
    print(f"  cf-mitigated    : {lower.get('cf-mitigated', '-')}")
    print(f"  content-length  : {lower.get('content-length', '-')}")
    print(f"  body length     : {len(body)}")

    managed = lower.get("cf-mitigated", "").lower() == "challenge"
    turnstile = "challenges.cloudflare.com/turnstile" in body
    orchestrate = "/cdn-cgi/challenge-platform" in body
    localized = any(k in body for k in ("Tunggu sebentar", "Melakukan verifikasi",
                                        "Just a moment", "Un momento"))
    print(f"  managed challenge : {managed}")
    print(f"  orchestration JS  : {orchestrate}")
    print(f"  Turnstile widget  : {turnstile}")
    print(f"  localized shell   : {localized}")

    if not (managed or localized):
        print("  verdict : NOT gated (or already cached-past) — proceed with normal testing")
        return False
    print("  verdict : GATED — origin not reachable from here without a valid CF token")
    return True


def robots_leak(host):
    section("ROBOTS / LOW-COST PROBES")
    for path in ("robots.txt", "sitemap.xml", ".well-known/security.txt", "favicon.ico"):
        code, _, body = http(f"https://{host}/{path}", 12)
        note = ""
        if path == "robots.txt" and code == 200:
            note = "  <- leaks through! confirms live zone + CF managed robots feature"
        print(f"  /{path:<24} {code}{note}")


def origin_passive(host):
    section("ORIGIN IP — PASSIVE SOURCES")
    code, _, body = http(f"https://crt.sh/?q=%25.{host}&output=json", 30)
    names = set()
    if code == 200 and body.strip().startswith("["):
        try:
            for e in json.loads(body):
                for n in e.get("name_value", "").split("\n"):
                    if n.strip():
                        names.add(n.strip().lower())
        except json.JSONDecodeError:
            pass
    print("  crt.sh names :", ", ".join(sorted(names)) or "(none)")
    if names and names <= {host, f"*.{host}"}:
        print("                         wildcard-only → NO subdomain leak")

    try:
        out = subprocess.run(["subfinder", "-d", host, "-silent", "-all"],
                             capture_output=True, text=True, timeout=120).stdout
        subs = sorted({s.strip() for s in out.splitlines() if s.strip()})
        print("  subfinder    :", ", ".join(subs) or "(none)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  subfinder    : unavailable/skipped")

    code, _, body = http(
        f"https://urlscan.io/api/v1/search/?q=domain:{host}&size=10", 20)
    if code == 200:
        try:
            d = json.loads(body)
            print("  urlscan hits :", d.get("total"))
            for r in (d.get("results") or [])[:5]:
                print("     ", r["task"]["url"], "|", r["page"].get("ip"))
        except json.JSONDecodeError:
            print("  urlscan      : unparsable")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return
    host = args[0].replace("https://", "").replace("http://", "").strip("/")

    if "--egress-only" in sys.argv:
        egress_check()
        return

    ok_egress = egress_check()
    gated = gate_check(host)
    robots_leak(host)
    if gated:
        origin_passive(host)

    section("DECISION")
    if not gated:
        print("  → not gated. Enumerate endpoints (/api/*, /admin, stats paths) now.")
    elif ok_egress:
        print("  → residential egress + gate: run stealth browser, expect pass in <10s.")
        print("    Then dump storage/cookies and replay cf_clearance with the SAME UA.")
    else:
        print("  → datacenter egress + gate: browser stealth is a dead end.")
        print("    (i) residential proxy / solver  (ii) user-browser dump + cf_clearance")
        print("    (iii) passive intel only. Report 'not reachable from this vantage'.")


if __name__ == "__main__":
    main()
