#!/usr/bin/env python3
"""Read-only cross-tenant boundary probe.

Give it two tenants' credentials and a set of object ids; it prints a PASS/LEAK matrix for the whole
"can tenant B reach tenant A's data?" question (rows 1-14 of
references/tenant-boundary-matrix-and-ledger-oracles.md).

Usage
-----
  python tenant_boundary_probe.py --config probe.json

probe.json:
{
  "base": "https://target.example",
  "tenants": {
      "A": {"cookie": "session=<value>",          "label": "account-under-test"},
      "B": {"cookie": "session=<value2>",         "label": "own-second-tenant"},
      "A_key": {"bearer": "<api key>"}            # optional
  },
  "foreign_ids": {                                 # A's ids that B must not reach
      "source":    "35fb53f7-...",
      "client":    "8263b18c-...",
      "import":    "47a1ecec-..."
  },
  "paths": {
      "object_page":   "/app/sources/{id}",
      "export_pdf":    "/api/properties/{id}/export?format=pdf&taxYear=all",
      "export_xlsx":   "/api/properties/{id}/export?format=xlsx&taxYear=all",
      "api_children":  "/api/v1/sources/{id}/transactions"
  },
  "own_page": "/app",
  "unauth_paths": ["/app", "/api/account/export", "/app/clients/export.csv"]
}

Nothing here writes. Safe to run repeatedly. Every 200 on a foreign id is reported as a candidate LEAK
together with its size and a body excerpt for manual triage (a 200 with an empty page is not a leak).
"""
import argparse
import json
import pathlib
import re
import sys

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
SAFE = {301, 302, 303, 307, 308, 401, 403, 404, 405, 422}


def session(cfg):
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    if cfg.get("cookie"):
        s.headers["Cookie"] = cfg["cookie"]
    if cfg.get("bearer"):
        s.headers["Authorization"] = "Bearer " + cfg["bearer"]
    return s


def probe(sess, base, path, timeout=40):
    url = base + path
    try:
        r = sess.get(url, timeout=timeout, allow_redirects=False)
    except Exception as ex:                                    # network/edge error
        return {"status": "ERR", "len": 0, "ct": "", "body": str(ex)[:120]}
    ct = r.headers.get("content-type", "")
    if r.content[:4] == b"%PDF":
        kind = "PDF"
    elif r.content[:2] == b"PK":
        kind = "XLSX/ZIP"
    else:
        kind = "html" if r.content[:15].lower().startswith(b"<!doctype") else "text"
    body = "" if kind in ("PDF", "XLSX/ZIP") else re.sub(r"\s+", " ", r.text[:140])
    return {"status": r.status_code, "len": len(r.content), "ct": ct[:40], "kind": kind,
            "cf": r.headers.get("cf-cache-status", ""), "body": body}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--timeout", type=int, default=40)
    a = ap.parse_args()
    cfg = json.loads(pathlib.Path(a.config).read_text())
    base = cfg["base"].rstrip("/")
    sess = {k: session(v) for k, v in cfg["tenants"].items()}
    fids = cfg.get("foreign_ids", {})
    paths = cfg.get("paths", {})
    rows, leaks = [], []

    def run(tag, who, tpl, oid, note):
        p = tpl.format(id=oid)
        r = probe(sess[who], base, p, a.timeout)
        r.update({"tag": tag, "who": who, "path": p, "note": note, "object": oid})
        rows.append(r)
        flag = ""
        if tag == "foreign" and isinstance(r["status"], int) and r["status"] not in SAFE:
            # a redirect to /login is fine; anything else needs eyes
            if not (r["status"] in (200,) and r.get("kind") == "html" and len(r["body"]) < 60):
                leaks.append(r)
                flag = "  <== CHECK"
        print(f"  {tag:<9} {who:<6} {p[:74]:<74} {str(r['status']):>4} {r['len']:>8} "
              f"{r.get('kind',''):<8} cf={r.get('cf','')}{flag}")

    for who in [k for k in sess if k != "A_key"]:              # B (and any other non-A tenant)
        print(f"\n=== tenant {who} reaching A's objects ===")
        for name, oid in fids.items():
            for key, tpl in paths.items():
                if "{id}" in tpl:
                    run("foreign", who, tpl, oid, f"A's {name} via {key}")

    if "A_key" in sess:
        print("\n=== A's API key reaching random / null ids (no-oracle check) ===")
        for oid in ["00000000-0000-0000-0000-000000000000",
                    "deadbeef-1234-4567-89ab-cdef01234567"]:
            for key, tpl in paths.items():
                if "{id}" in tpl and tpl.startswith("/api/"):
                    run("rand", "A_key", tpl, oid, f"{key} random/null")

    print("\n=== header / param tenant overrides (tenant A) ===")
    for hdr in ["X-Account-Id", "X-User-Id", "X-Client-Id", "X-Organisation-Id",
                "X-Firm-Id", "X-Tenant-Id", "accountId", "X-Account"]:
        s = sess.get("A")
        if s is None:
            continue
        base_r = probe(s, base, cfg.get("own_page", "/app"), a.timeout)
        s.headers[hdr] = "deadbeef-1234-4567-89ab-cdef01234567"
        ov = probe(s, base, cfg.get("own_page", "/app"), a.timeout)
        if hdr.lower() == "x-account-id":
            print(f"  base={base_r['status']}/{base_r['len']}B  override={ov['status']}/{ov['len']}B")
        if ov["len"] != base_r["len"]:
            leaks.append({**ov, "tag": "header-override", "note": hdr})
            print(f"  {hdr:<20} response CHANGED size {base_r['len']} -> {ov['len']}  <== CHECK")

    print("\n=== unauthenticated ===")
    anon = requests.Session()
    anon.headers.update({"User-Agent": UA})
    for p in cfg.get("unauth_paths", []):
        r = probe(anon, base, p, a.timeout)
        print(f"  anon {p[:70]:<70} {str(r['status']):>4} {r['len']:>8}")

    print(f"\n=== {len(leaks)} candidate leak(s) — triage each by hand ===")
    for r in leaks:
        print(f"  {r['tag']:<10} {r['who']:<6} {r['path'][:70]:<70} {r['status']} {r['len']}B "
              f"{r.get('body','')[:90]}")

    out = pathlib.Path("tenant-boundary-probe.json")
    out.write_text(json.dumps({"rows": rows, "candidates": leaks}, indent=1))
    print(f"\nwrote {out} ({len(rows)} probes)")
    return 0 if not leaks else 1


if __name__ == "__main__":
    sys.exit(main())
