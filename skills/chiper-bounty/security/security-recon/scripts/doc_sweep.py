#!/usr/bin/env python3
"""Bounded, SPA-catch-all-aware sensitive-file / exposure sweep.

Replacement for a full-template nuclei run on large scopes (see security-recon Step 6b).
Hosts x curated paths, low request rate, and a root-signature filter that removes the
"every path returns index.html" false positives that otherwise flood the output.

Usage
-----
python doc_sweep.py --hosts live_hosts.txt [--paths paths.txt] [--out ./sweep] \
                    [--rps 4] [--workers 4] [--header "X-Bugcrowd: Bugcrowd-<user>"] [--only-status 200]

  live_hosts.txt : one host or URL per line (https:// is added when missing)
  paths.txt      : one path per line; defaults to the curated list below

Output
------
<sweep>/hits_<ts>.json   -> every reported hit + the root signature of every host
                            (keep it: a later pass can re-triage without re-requesting)
stdout                   -> progress + hit lines

Triage the output with the filters in security-recon Step 6c before calling anything a finding.
"""
import argparse, hashlib, json, os, random, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

DEFAULT_PATHS = [
    "/README.md", "/README", "/readme.md", "/CHANGELOG.md", "/.env", "/.dev.vars",
    "/config.json", "/wrangler.toml", "/package.json", "/swagger.json", "/openapi.json",
    "/.git/config", "/.well-known/security.txt", "/api-docs",
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_lock = threading.Lock()
_last = [0.0]
_min_gap = 1.0 / 4.0          # set from --rps


def throttle():
    with _lock:
        now = time.time()
        wait = _last[0] + _min_gap - now
        if wait > 0:
            time.sleep(wait)
            now = _last[0] + _min_gap
        _last[0] = now


def get(url, headers, timeout=10, cap=400_000):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(cap)
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers or {}), e.read(20000)
        except Exception:
            return e.code, {}, b""
    except Exception as e:
        return "ERR", {}, str(e)[:120].encode()


def norm_host(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    return line if line.startswith("http") else "https://" + line


def sig(body):
    return hashlib.sha256(body[:200_000]).hexdigest()[:16]


def check(host, paths, headers):
    throttle()
    st, h, b = get(host + "/", headers)
    root = {"status": st, "len": len(b), "sha": sig(b)}
    hits = []
    for p in paths:
        throttle()
        st, h, b = get(host + p, headers)
        if st != 200:
            continue
        ct = (h.get("content-type") or "").lower()
        if sig(b) == root["sha"] or (root["len"] and abs(len(b) - root["len"]) < 8 and len(b) > 1000):
            continue                                  # SPA catch-all
        head = b[:400].decode("utf-8", "replace")
        looks_doc = (any(k in ct for k in ("json", "yaml", "toml", "text/plain", "xml", "octet-stream"))
                     or p.endswith((".md", "/.env", ".dev.vars", ".toml", ".json", ".txt")))
        if not looks_doc:
            continue
        hits.append({"host": host, "path": p, "status": st, "ctype": ct, "len": len(b),
                     "head": head.replace("\n", " ")[:300]})
    return {"host": host, "root": root, "hits": hits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", required=True)
    ap.add_argument("--paths")
    ap.add_argument("--out", default=".")
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--header", action="append", default=[])
    a = ap.parse_args()

    global _min_gap
    _min_gap = 1.0 / max(a.rps, 0.2)

    hosts = [h for h in (norm_host(l) for l in open(a.hosts)) if h]
    paths = ([l.strip() for l in open(a.paths) if l.strip() and not l.startswith("#")]
             if a.paths else DEFAULT_PATHS)
    headers = {"User-Agent": UA, "Accept": "*/*"}
    for h in a.header:
        k, _, v = h.partition(":")
        headers[k.strip()] = v.strip()

    os.makedirs(a.out, exist_ok=True)
    print(f"hosts={len(hosts)} paths={len(paths)} est_requests={len(hosts)*(len(paths)+1)} "
          f"rps={a.rps} -> ~{len(hosts)*(len(paths)+1)/max(a.rps,0.2)/60:.1f} min")

    hits, roots, t0 = [], [], time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, res in enumerate(ex.map(lambda h: check(h, paths, headers), hosts), 1):
            roots.append({"host": res["host"], "root": res["root"]})
            for x in res["hits"]:
                hits.append(x)
                print("HIT", x["host"], x["path"], x["status"], x["ctype"], x["len"])
                print("     ", x["head"][:160])
            if i % 20 == 0:
                print(f"  ...{i}/{len(hosts)} hosts, {len(hits)} hits, {int(time.time()-t0)}s")

    ts = time.strftime("%Y%m%d-%H%M%S")
    out = os.path.join(a.out, f"hits_{ts}.json")
    json.dump({"hosts": len(hosts), "paths": paths, "hits": hits, "roots": roots},
              open(out, "w", encoding="utf-8"), indent=1)
    print(f"DONE hosts={len(hosts)} hits={len(hits)} elapsed={int(time.time()-t0)}s -> {out}")
    print("Triage before reporting: security-recon Step 6c (Cloudflare Access pages, SPA shells, "
          "stock template READMEs and public front-end configs are NOT findings).")


if __name__ == "__main__":
    sys.exit(main())
