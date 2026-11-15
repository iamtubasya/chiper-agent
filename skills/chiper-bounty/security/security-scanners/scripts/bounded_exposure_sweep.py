#!/usr/bin/env python3
"""Bounded document/config exposure sweep with built-in false-positive filtering.

Why: a full mirrorset nuclei run over a wide host list queues millions of requests and is
unusable (and often disqualifying) on a rate-limited program. This does 14 curated paths x N
hosts at ~4 req/s, then drops the three FP classes that dominate the raw output
(edge interstitial pages, SPA shells, duplicate bodies).

Usage:
  python bounded_exposure_sweep.py --hosts hosts.txt --outdir ./scan --rps 4 \
      --header "X-Bugcrowd: Bugcrowd-BC_USERNAME"

  hosts.txt: one hostname or https://host per line.
Outputs:
  <outdir>/sweep_<ts>.json   raw + classified hits
  stdout: only the survivors, so the log is readable
"""
import argparse, hashlib, json, os, sys, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

DEFAULT_PATHS = [
    "/README.md", "/README", "/readme.md", "/CHANGELOG.md", "/.env", "/.dev.vars",
    "/config.json", "/wrangler.toml", "/package.json", "/swagger.json", "/openapi.json",
    "/.git/config", "/.well-known/security.txt", "/api-docs",
]
LEAF_MARKERS = ("cloudflare access", "sign in ・ cloudflare", "cf-access", "access denied")
SPA_MARKERS = ("__next", "data-next-head", 'id="root"', 'id="app"', "@vite/client",
               "window.__nuxt__", "ng-version", "webpackjsonp")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")


def fetch(url, headers, timeout=10, cap=400000):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(cap)
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers or {}), e.read(20000)
        except Exception:
            return e.code, {}, b""
    except Exception as e:
        return "ERR", {}, str(e)[:120].encode()


def classify(body, ctype, root_sig, sha):
    """Return None if the hit is a false positive, else a short verdict string."""
    head = body[:1200].decode("utf-8", "replace").lower()
    if any(m in head for m in LEAF_MARKERS):
        return None, "edge-interstitial"
    if any(m in head for m in SPA_MARKERS):
        return None, "spa-shell"
    if sha == root_sig.get("sha"):
        return None, "same-as-root"
    if root_sig.get("len", 0) > 1000 and abs(len(body) - root_sig["len"]) < 8:
        return None, "same-as-root"
    if "html" in ctype and len(body) > 2000:
        return None, "html-shell"
    return "SURVIVOR", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", required=True)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--paths-file")
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--header", action="append", default=[], help="Extra header 'K: V' (repeatable)")
    a = ap.parse_args()

    hdr = {"User-Agent": UA, "Accept": "*/*"}
    for h in a.header:
        if ":" in h:
            k, v = h.split(":", 1)
            hdr[k.strip()] = v.strip()
    paths = open(a.paths_file).read().split() if a.paths_file else DEFAULT_PATHS
    delay = max(0.0, 1.0 / a.rps) * 4          # 4 workers -> ~rps total
    hosts = [l.strip() for l in open(a.hosts) if l.strip() and not l.startswith("#")]
    os.makedirs(a.outdir, exist_ok=True)
    print(f"hosts={len(hosts)} paths={len(paths)} ~{len(hosts)*(len(paths)+1)} requests @~{a.rps} rps")

    results, t0 = [], time.time()

    def probe(host):
        if not host.startswith("http"):
            host = "https://" + host
        st, h, b = fetch(host + "/", hdr)
        root = {"status": st, "len": len(b),
                "sha": hashlib.sha256(b[:200000]).hexdigest()[:16]}
        rows = []
        for p in paths:
            time.sleep(delay)
            st2, h2, b2 = fetch(host + p, hdr)
            if st2 != 200:
                continue
            sha = hashlib.sha256(b2[:200000]).hexdigest()[:16]
            verdict, why = classify(b2, (h2.get("content-type") or "").lower(), root, sha)
            rows.append({"host": host, "path": p, "verdict": verdict or "FP", "why": why,
                         "len": len(b2), "ctype": (h2.get("content-type") or "")[:60],
                         "head": b2[:300].decode("utf-8", "replace").replace("\n", " ")})
        return {"host": host, "root": root, "rows": rows}

    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, r in enumerate(ex.map(probe, hosts), 1):
            results.append(r)
            for row in r["rows"]:
                if row["verdict"] == "SURVIVOR":
                    print(f"SURVIVOR {row['host']}{row['path']} [{row['ctype']} {row['len']}b]")
                    print(f"         {row['head'][:180]}")
            if i % 25 == 0:
                print(f"  ...{i}/{len(hosts)} hosts, {int(time.time()-t0)}s")
    fps = sum(1 for r in results for row in r["rows"] if row["verdict"] == "FP")
    surv = sum(1 for r in results for row in r["rows"] if row["verdict"] == "SURVIVOR")
    out = os.path.join(a.outdir, f"sweep_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"hosts": len(hosts), "paths": paths, "results": results,
               "survivors": surv, "filtered_fp": fps},
              open(out, "w", encoding="utf-8"), indent=1)
    print(f"DONE survivors={surv} filtered_fp={fps} elapsed={int(time.time()-t0)}s -> {out}")
    print("Reminder: read every survivor's body before believing it (public config/template files "
          "are not findings).")


if __name__ == "__main__":
    sys.exit(main())
