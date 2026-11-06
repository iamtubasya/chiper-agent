#!/usr/bin/env python3
"""Unauthenticated WordPress REST-surface probe (read-only, GET only).

Why: `/wp-json/` is usually reachable without auth and enumerates EVERY registered
namespace -> a free plugin inventory. Plugin REST routes are frequently *inconsistently*
protected: one route returns data while its siblings 401. That authz inconsistency is the
finding class worth hunting (2026-09: `/wp-json/ithemes-security/v1/bans` returned the
banned-IP list on www.rapyd.net + join.rapyd.net while logs/settings/modules/actors/
site-scanner all returned 401).

Nothing here writes, submits or brute-forces. It only GETs.

Usage:
  python wp_rest_probe.py https://www.example.net [--save out.json]
  python wp_rest_probe.py https://www.example.net --only ithemes,redirection,userway

What it does
  1. GET /wp-json/  -> namespaces + routes (plugin map); writes the raw index to disk
  2. for each non-core namespace: GET its namespace root and a few sub-routes, flag
     HTTP 200 responses whose body looks like data (not `rest_no_route` / SPA HTML)
  3. author enumeration: /?author=1..6 -> /blog/author/<nicename>/  (works even when
     /wp-json/wp/v2/users is 401)
  4. /author-sitemap.xml (Yoast) as a second author-enumeration source
  5. plugin versions from /wp-content/plugins/<slug>/readme.txt  ("Stable tag:")
     -> version numbers are FINGERPRINTS, not vulnerabilities. Never claim a CVE from a
        version alone; verify the advisory's affected range first, and note that sites are
        often NEWER than a scanner's known-latest (nuclei reported `last_version` older
        than the deployed version on this engagement).
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse as up
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
HDR = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}

CORE_NS = ("wp/v2", "wp-site-health", "wp-block-editor", "wp-abilities", "oembed", "batch",
           "wp-block-", "wp-")
# plugin namespaces worth a direct poke (extend as you see them in the index)
HOT_SUFFIX = ("/bans", "/logs", "/settings", "/modules", "/users", "/actors", "/status", "/config",
              "/scans", "/rules", "/notifications", "/imports", "/redirect", "/redirects",
              "/packages", "/export", "/database", "/debug", "/info")


def get(base, path, accept=None, timeout=20):
    h = dict(HDR)
    h["X-Kyc"] = h.pop("X-Kyc", "")  # no-op placeholder keeps header dict simple
    if accept:
        h["Accept"] = accept
    req = urllib.request.Request(base + path, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(20000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return "ERR", str(e)[:140]


def is_spa(body):
    low = body[:600].lower()
    return "<!doctype html" in low or "<html" in low


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    base = sys.argv[1].rstrip("/")
    skip = [x for x in sys.argv[2:] if not x.startswith("--")]
    save = sys.argv[sys.argv.index("--save") + 1] if "--save" in sys.argv else None
    findings = []

    st, body = get(base, "/wp-json/", accept="application/json")
    print(f"[index] GET {base}/wp-json/ -> {st}  ({len(body)} bytes)")
    if st != 200 or is_spa(body):
        print("        no REST index exposed (or SPA catch-all) — stopping")
        return 1
    try:
        idx = json.loads(body)
    except Exception as e:
        print("        index is not JSON:", e)
        return 1
    ns = idx.get("namespaces") or []
    routes = list((idx.get("routes") or {}).keys())
    print(f"[index] namespaces={len(ns)} routes={len(routes)}")
    print("        " + ", ".join(ns))

    plugin_ns = [n for n in ns if not any(c in n for c in CORE_NS)]
    probes = []
    for n in plugin_ns:
        if skip and not any(s in n for s in skip):
            continue
        probes.append("/wp-json/" + n.lstrip("/"))
    # add every plugin route that looks security/config-ish
    for r in routes:
        if any(r.endswith(s) or s in r for s in HOT_SUFFIX):
            probes.append("/wp-json" + r)

    print(f"\n[probe] {len(probes)} candidate routes (unauthenticated GET)")
    for p in dict.fromkeys(probes):
        st, body = get(base, p)
        flag = ""
        if st == 200 and body and not is_spa(body):
            low = body.lower()
            if "rest_no_route" not in low and any(k in low for k in
                                                 ("\"label\"", "\"email\"", "\"slug\"", "version",
                                                  "\"ip\"", "\"user\"", "\"setting\"", "\"created")):
                flag = "  <== DATA"
                findings.append({"route": p, "status": st, "sample": body[:400]})
        print(f"  [{st}] {p[:88]}{flag}")
        if flag:
            print("        ", body[:200].replace("\n", " "))
        time.sleep(0.4)

    print("\n[enum] author enumeration via /?author=N")
    seen = {}
    for n in range(1, 7):
        st, body = get(base, f"/?author={n}", accept="text/html")
        m = re.search(r"/author/([a-z0-9._-]+)/", body)
        if m:
            seen[n] = m.group(1)
            print(f"  author={n}: {st} -> {m.group(1)}")
        else:
            print(f"  author={n}: {st} -> (none)")
    st, body = get(base, "/author-sitemap.xml", accept="application/xml")
    if st == 200 and "<loc>" in body:
        locs = re.findall(r"<loc>([^<]+)</loc>", body)
        print(f"  author-sitemap.xml: {st}, {len(locs)} locs, e.g. {locs[:3]}")

    print("\n[versions] plugin readme.txt fingerprints")
    for slug in ("ithemes-security", "better-wp-security", "redirection", "userway-accessibility-widget",
                 "wp-all-import", "object-cache-pro", "duplicate-post", "co-authors-plus",
                 "sitepress-multilingual-cms", "wordpress-seo"):
        for cand in (slug, slug.replace("-", "")):
            st, body = get(base, f"/wp-content/plugins/{cand}/readme.txt", accept="text/plain")
            if st == 200 and len(body) > 200 and ("Stable tag" in body or "Version" in body):
                m = re.search(r"Stable tag:\s*([0-9][0-9A-Za-z.\-]*)", body) or \
                    re.search(r"Version:\s*([0-9][0-9A-Za-z.\-]*)", body)
                print(f"  {cand:<34} {m.group(1) if m else '?'}   (fingerprint only — verify any CVE range before claiming)")
                break
        time.sleep(0.2)

    print("\n[controls] these SHOULD be blocked — if they are not, that is the finding")
    for p in ("/xmlrpc.php", "/wp-json/wp/v2/users", "/wp-json/wp/v2/settings", "/wp-json/wp/v2/plugins"):
        st, _ = get(base, p)
        print(f"  [{st}] {p}")

    if save:
        json.dump({"base": base, "namespaces": ns, "findings": findings, "authors": seen},
                  open(save, "w", encoding="utf-8"), indent=1)
        print("\nsaved", save)
    return 0


if __name__ == "__main__":
    sys.exit(main())
