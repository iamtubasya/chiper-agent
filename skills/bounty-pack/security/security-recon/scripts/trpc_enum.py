#!/usr/bin/env python3
"""Enumerate tRPC procedures unauthenticated (GET-only existence oracle).

tRPC error codes:  -32001 UNAUTHORIZED (401) = exists, gated
                   -32004 NOT_FOUND    (404) = does not exist
                   -32005 METHOD_NOT_SUPPORTED (405) = exists, is a mutation
    => 200 on a GET is a PUBLIC procedure (the prize).

GET only: never POST to a mutation. GET-to-mutation returns 405 without invoking it.

Usage:
    python trpc_enum.py app.example.com procedures.txt
    # procedures.txt: one "router.procedure" per line, '#' comments allowed

Harvest candidate names from the SPA chunks first:
    grep -rhoE '[A-Za-z_$][\\w$]*(\\.[A-Za-z_$][\\w$]*){1,3}\\.(useQuery|useMutation|invalidate)'
"""
import concurrent.futures, json, ssl, sys, urllib.error, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"
ctx = ssl._create_unverified_context()
HOST = sys.argv[1]
NAMES = [l.strip() for l in open(sys.argv[2]) if l.strip() and not l.startswith("#")]

TAG = {200: "PUBLIC!", 400: "needs-input", 401: "auth", 404: "missing",
       405: "mutation", 500: "ERROR"}


def probe(proc):
    q = urllib.parse.quote(json.dumps({"json": None}))
    url = "https://%s/trpc/%s?input=%s" % (HOST, proc, q)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/json", "trpc-accept": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=12, context=ctx)
        return proc, r.status, r.read(500).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return proc, e.code, e.read(300).decode("utf-8", "replace")
    except Exception as e:
        return proc, 0, str(e)


def main():
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for proc, code, body in ex.map(probe, NAMES):
            rows.append((code, proc, body))
    rows.sort()
    public = []
    for code, proc, body in rows:
        if code == 404:            # keep the output clean; the oracle is the point
            continue
        print("%4d %-11s %s" % (code, TAG.get(code, str(code)), proc))
        if code == 200:
            public.append((proc, body))
    print("\n=== PUBLIC (200) ===")
    for p, b in public:
        print("--- %s\n    %s" % (p, b[:300]))
    print("\nexists/auth=%d mutations=%d public=%d missing=%d" % (
        sum(1 for c, _, _ in rows if c == 401),
        sum(1 for c, _, _ in rows if c == 405),
        len(public),
        sum(1 for c, _, _ in rows if c == 404)))


if __name__ == "__main__":
    main()
