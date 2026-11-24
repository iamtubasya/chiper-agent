#!/usr/bin/env python3
"""origin-hunt — wider passive origin-IP recon for a CDN-fronted target.

Complements cf_triage.py (which covers crt.sh / subfinder / urlscan). Use this
when the target sits behind Cloudflare and you still need the real origin IP.

Sources, cheapest first:
  1. DNS history aggregators that don't need paid keys
  2. Favicon hash (Shodan-style) — the classic way to find a CF origin by body fingerprint
  3. Historical CDX over the domain, with backoff (web.archive.org rate-limits hard)
  4. Censys/FOFA/Shodan query hints printed for manual use (no API key assumed)

Usage:
    python3 origin_hunt.py target.example
    python3 origin_hunt.py target.example --no-cdx

Nothing here touches the target directly — all requests go to third-party
datasets, so it is quiet and safe to run before any active testing.
"""
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url, timeout=20, retries=2, backoff=3):
    """GET with retry/backoff — archive.org and crt.sh both 429 aggressively."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(500_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:
                time.sleep(backoff * (attempt + 1))
                continue
            return e.code, ""
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(1)
    return None, f"ERROR: {last}"


def section(t):
    print(f"\n=== {t} ===")


def prepend_scheme(h):
    return h if "://" in h else f"https://{h}"


def dns_history(host):
    section("DNS HISTORY (free sources)")
    checks = [
        ("hackertarget hostsearch",
         f"https://api.hackertarget.com/hostsearch/?q={host}"),
        ("rapiddns subdomains",
         f"https://rapiddns.io/subdomain/{host}?full=1"),
        ("rapiddns same-IP", f"https://rapiddns.io/sameip/{host}?full=1"),
    ]
    for label, url in checks:
        code, body = get(url)
        if code != 200:
            print(f"  {label:<28} -> {code}")
            continue
        hits = [ln for ln in body.splitlines()
                if host in ln and "<" not in ln][:15]
        print(f"  {label:<28} -> {code}, {len(hits)} line(s)")
        for h in hits:
            print("     ", h.strip()[:160])


def favicon_hash(host):
    section("FAVICON HASH (feed this to Shodan / FOFA / Censys)")
    code, body = get(prepend_scheme(host) + "/favicon.ico", timeout=15)
    if code != 200 or not body:
        print(f"  could not fetch favicon ({code}) — likely blocked by the CDN gate")
        print("  fallback: get the icon from the user's browser and hash locally:")
        print("    import mmh3, requests")
        print("    print(mmh3.hash(base64.encodebytes(requests.get(url).content)))")
        return
    raw = body.encode("utf-8", "replace")
    import base64
    b64 = base64.encodebytes(raw)
    try:
        import mmh3  # noqa: F401
        print(f"  mmh3 hash : {mmh3.hash(b64)}")
    except ImportError:
        print(f"  sha256    : {hashlib.sha256(raw).hexdigest()}")
        print("  (pip install mmh3 for the Shodan-compatible favicon hash)")
    print("  queries   :")
    print('    Shodan: http.favicon.hash:<hash>')
    print('    FOFA  : icon_hash="<hash>"')


def cdx_lookup(host):
    section("WAYBACK CDX (historical URLs, host-leaking)  [rate-limited]")
    url = (f"http://web.archive.org/cdx/search/cdx?url=*.{host}"
           "&output=json&limit=200&collapse=urlkey&fl=original,timestamp")
    code, body = get(url, timeout=30, retries=1)
    if code != 200 or not body.lstrip().startswith("["):
        print(f"  unavailable ({code}) — archive.org throttles fast, retry much later")
        return
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        print("  unparsable response")
        return
    urls = [r[0] for r in rows[1:]] if len(rows) > 1 else []
    print(f"  {len(urls)} archived URL(s)")
    interesting = [u for u in urls if any(k in u.lower() for k in
                   ("admin", "api", "panel", "login", "backup", ".env", "debug",
                    "staging", "dev", "internal", "phpmyadmin"))]
    for u in interesting[:25]:
        print("     ", u[:180])
    if not interesting:
        for u in urls[:10]:
            print("     ", u[:180])


def manual_queries(host):
    section("MANUAL API QUERIES (need your own key)")
    print("  SecurityTrails : /v1/history/{host}/dns/a      (most reliable history)")
    print("  Shodan         : hostname:{host} ; ssl:{host} ; http.html_hash:-<hash>")
    print("  Censys         : names: {host} AND NOT autonomous_system.name: CLOUDFLARENET")
    print("  FOFA           : domain=\"{host}\" && cert=\"{host}\"".format(host=host))
    print("  VirusTotal     : /api/v3/domains/{host}/resolutions")


def verdict(host):
    section("NEXT STEPS")
    print("  Any non-Cloudflare IP that answers with Host: {h} is the origin:".format(h=host))
    print(f"    curl -k -sS -o /dev/null -w '%{{http_code}}\\n' --resolve {host}:443:<IP> https://{host}/")
    print("  If every path is CF anycast, origin discovery has failed passively.")
    print("  Do NOT port-scan Cloudflare's ranges — you'll hit the edge, not the origin.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return
    host = args[0].replace("https://", "").replace("http://", "").strip("/")
    if host.startswith("www."):
        host = host[4:]

    print(f"[*] target: {host}")
    dns_history(host)
    favicon_hash(host)
    if "--no-cdx" not in sys.argv:
        cdx_lookup(host)
    manual_queries(host)
    verdict(host)


if __name__ == "__main__":
    main()
