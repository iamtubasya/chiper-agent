#!/usr/bin/env python3
"""Map the auth posture of every endpoint in an OpenAPI spec.

Usage:
    python3 api_auth_map.py <openapi.json> <base_url> [--delay 0.25] [--out results.txt]

Probes each path with an empty body ({} for POST) or no params (GET),
substituting path params with placeholder values, and classifies:
    200        -> open (no auth)
    401/403    -> gated (record the error message — it often names the auth scheme)
    400/422    -> reachable WITHOUT auth (validation error = the handler ran)
    429        -> rate-limited (back off; re-run the 429'd subset after cooldown)
    5xx        -> server error on empty input (note it; usually not a finding alone)

Header discovery via error-message differential:
    After the first pass, re-send ONE gated endpoint with a dummy value under
    each candidate auth header (X-Api-Key, Api-Key, Authorization, X-ApiKey...).
    An error that changes from "not found" to "invalid/disabled" identifies the
    header the server actually reads.

Notes:
- Run as a background job with notify_on_complete for large specs; tight
  per-IP rate limits (esp. quote/pricing paths) will 429 mid-run.
- Path params are substituted with obviously-fake placeholders on purpose —
  this pass maps AUTH, not data. Never send valid-looking payloads that could
  mutate state.
"""
import json, sys, time, urllib.request, urllib.error, argparse

PLACEHOLDERS = {
    "{address}": "11111111111111111111111111111111",
    "{loan}": "11111111111111111111111111111111",
    "{strategy}": "11111111111111111111111111111111",
    "{mint}": "11111111111111111111111111111111",
    "{symbol}": "TEST",
    "{vault_address}": "11111111111111111111111111111111",
    "{project_id}": "00000000-0000-0000-0000-000000000000",
    "{id}": "1",
}

def substitute(path):
    for k, v in PLACEHOLDERS.items():
        path = path.replace(k, v)
    return path

def probe(base, method, path, timeout=15):
    url = base.rstrip("/") + path
    data = b"{}" if method == "POST" else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200).decode("utf-8", "replace").replace("\n", " ")
    except urllib.error.HTTPError as e:
        return e.code, e.read(200).decode("utf-8", "replace").replace("\n", " ")
    except Exception as e:
        return 0, str(e)[:120]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("base")
    ap.add_argument("--delay", type=float, default=0.25)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    spec = json.load(open(args.spec, encoding="utf-8"))
    paths = spec.get("paths", {})
    results = []
    for p in sorted(paths):
        for method in paths[p]:
            pp = substitute(p)
            status, body = probe(args.base, method.upper(), pp)
            results.append((status, method.upper(), pp, body))
            time.sleep(args.delay)

    lines = [f"{s} {m} {p} :: {b}" for s, m, p, b in results]
    report = "\n".join(lines)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(report + "\n")

    buckets = {"open(200)": 0, "gated(401/403)": 0, "reachable(400/422)": 0,
               "ratelimited(429)": 0, "other": 0}
    for s, _, _, _ in results:
        if s == 200: buckets["open(200)"] += 1
        elif s in (401, 403): buckets["gated(401/403)"] += 1
        elif s in (400, 422): buckets["reachable(400/422)"] += 1
        elif s == 429: buckets["ratelimited(429)"] += 1
        else: buckets["other"] += 1
    print(f"TOTAL {len(results)} | " + " | ".join(f"{k} {v}" for k, v in buckets.items()))
    print("\n--- reachable WITHOUT auth (400/422) — handler ran, no credential ---")
    for s, m, p, b in results:
        if s in (400, 422):
            print(f"  {s} {m} {p} :: {b[:100]}")
    print("\n--- gated (401/403) — record error text for header discovery ---")
    seen = set()
    for s, m, p, b in results:
        if s in (401, 403) and b[:80] not in seen:
            seen.add(b[:80])
            print(f"  {s} {m} {p} :: {b[:120]}")
    if args.out:
        print(f"\nfull results -> {args.out}")

if __name__ == "__main__":
    main()
