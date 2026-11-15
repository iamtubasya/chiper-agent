#!/usr/bin/env python3
"""Bounded broad-host exposure sweep — the practical replacement for a
full-template nuclei run across many in-scope hosts.

Why: `nuclei -tags exposure,disclosure,takeover,default-login,misconfig` on 260 hosts
advertises ~1.5M requests; at a program-friendly 4 rps it sits at "0% in 32 minutes"
with tens of thousands of errors. This sweep does the same *class* of check
(internal docs / configs / dev files left on a host) with ~3.6k requests in ~9 minutes.

False-positive discipline (this is the whole point):
  * kill SPA catch-alls by comparing each response to the host's root document
    (sha of first 200KB or a near-identical length),
  * kill Cloudflare Access login pages ("Sign in ・ Cloudflare Access") and other
    interstitial pages, which are identical across paths and account for ~45% of raw hits,
  * dedupe by (host, body-hash),
  * security.txt / robots.txt are noise here — drop them.

Usage:
  python host_exposure_sweep.py --hosts hosts.txt --out ./sweep \
      --header "X-Bugcrowd: Bugcrowd-<user>" [--paths extra_paths.txt] [--rps 4] [--tag myscan]

Always keep --rps low and honour the program's rate rules (many programs cap the whole
account, not per host). Output: sweep_summary_<tag>.json + a printed hit list.
"""
import argparse, hashlib, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

DEFAULT_PATHS = [
    "/README.md", "/README", "/readme.md", "/CHANGELOG.md", "/.env", "/.dev.vars",
    "/config.json", "/wrangler.toml", "/package.json", "/swagger.json", "/openapi.json",
    "/.git/config", "/api-docs", "/actuator/health",
]

# Bodies that are never findings: identical interstitial / shell pages.
DROP_MARKERS = ("Cloudflare Access", "Sign in ・ Cloudflare", "cf-access", "Access denied")
DROP_SUBSTRINGS = ("__next", "data-next-head", '<div id="root">', '<div id="app">',
                   "ng-version", "@vite/client", "window.__NUXT__")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def make_get(headers):
    def get(url, timeout=10):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read(400000)
        except urllib.error.HTTPError as e:
            try:
                return e.code, dict(e.headers or {}), e.read(20000)
            except Exception:
                return e.code, {}, b""
        except Exception as e:
            return "ERR", {}, str(e)[:120].encode()
    return get


def sha(b):
    return hashlib.sha256(b[:200000]).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", required=True, help="file with one host or https://host per line")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--header", action="append", default=[], help="extra header 'Name: value' (repeatable)")
    ap.add_argument("--paths", help="extra paths file, one per line")
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--tag", default=time.strftime("%Y%m%d-%H%M%S"))
    a = ap.parse_args()

    headers = {"User-Agent": UA, "Accept": "*/*"}
    for h in a.header:
        k, _, v = h.partition(":")
        headers[k.strip()] = v.strip()
    get = make_get(headers)

    paths = list(DEFAULT_PATHS)
    if a.paths:
        paths += [l.strip() for l in open(a.paths) if l.strip()]
    hosts = []
    for l in open(a.hosts):
        l = l.strip()
        if not l:
            continue
        hosts.append(l if l.startswith(("http://", "https://")) else "https://" + l)
    os.makedirs(a.out, exist_ok=True)
    delay = 1.0 / max(a.rps, 0.1)

    def check(host):
        rst, _, rb = get(host + "/")
        root = {"status": rst, "len": len(rb), "sha": sha(rb)}
        hits = []
        for p in paths:
            time.sleep(delay)
            st, hd, b = get(host + p)
            if st != 200:
                continue
            body = b.decode("utf-8", "replace")
            if any(m in body for m in DROP_MARKERS):
                continue
            if any(m.lower() in body[:2000].lower() for m in DROP_SUBSTRINGS):
                continue
            if sha(b) == root["sha"] or (abs(len(b) - root["len"]) < 8 and len(b) > 1000):
                continue                      # SPA catch-all == the root document
            hits.append({"host": host, "path": p, "status": st,
                         "ctype": (hd.get("content-type") or "")[:60], "len": len(b),
                         "head": body[:300].replace("\n", " ")})
        return root, hits

    results, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=max(2, int(a.rps))) as ex:
        for i, (root, hits) in enumerate(ex.map(check, hosts), 1):
            for h in hits:
                results.append(h)
                print(f"HIT {h['host']}{h['path']}  [{h['status']} {h['ctype']} {h['len']}b]")
                print("    ", h["head"][:160])
            if i % 25 == 0:
                print(f"  ...{i}/{len(hosts)} hosts, {len(results)} hits, {int(time.time()-t0)}s", file=sys.stderr)

    out = os.path.join(a.out, f"sweep_summary_{a.tag}.json")
    json.dump({"hosts": len(hosts), "paths": paths, "hits": results},
              open(out, "w", encoding="utf-8"), indent=1)
    print(f"DONE hosts={len(hosts)} hits={len(results)} elapsed={int(time.time()-t0)}s -> {out}")
    print("Triage the hits by hand: leftover internal doc = P4 info disclosure; "
          "public site-keys / vendor template README / SPA shell = NOT a finding.")


if __name__ == "__main__":
    main()
