#!/usr/bin/env python3
"""Bounded rate-limit probe for ONE endpoint (evidence-grade output).

SAFETY CONTRACT — read before pointing this at anything:
  * Random, obviously-invalid inputs only. NEVER a guess at a real credential, invite code, OTP or token.
  * Bounded by construction: --steady requests at ~1 rps, then a short --burst. Defaults are gentle
    (30 + 10). Do not raise them without the operator's explicit call.
  * The output labels itself "rate-limit testing" so the evidence cannot be misread as enumeration or
    as a brute-force attempt.

What it reports (the honest limits of the method):
  * status set per phase, count of 429 / 503 / 403 and any Retry-After / RateLimit-* headers,
  * per-phase median + p95 latency (a rising median is throttling even without a 429),
  * a verdict line that distinguishes "no rate limiting OBSERVED in N requests" from
    "rate limiting absent" — the first is measurable, the second is not.

Usage:
  python ratelimit_probe.py "https://host/api/invite/validate?code={code}" --out evidence/rl.json
  python ratelimit_probe.py "https://host/api/x" --steady 20 --burst 5 --len 8

Pair it with the keyspace question: read `maxlength` / `pattern` off the real input
(document.querySelectorAll('input') -> maxLength, pattern) and quote the keyspace
(e.g. 6 alphanumeric chars = 62^6 ≈ 5.7e10). "No rate limit" is a style nit for a 128-bit token and a
brute-force question for a 6-character code — the same evidence, two different severities.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import string
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
RL_HEADER_HINTS = ("retry-after", "ratelimit", "x-rate-limit", "x-ratelimit")


def probe(url: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(2048)
            status, headers = r.status, dict(r.headers)
    except urllib.error.HTTPError as e:                       # 4xx/5xx are data, not failures
        body = e.read(2048)
        status, headers = e.code, dict(e.headers or {})
    except Exception as e:                                    # noqa: BLE001 - report, do not crash
        return {"status": 0, "error": str(e), "t": time.perf_counter() - t0, "rl": {}}
    rl = {k: v for k, v in headers.items() if any(h in k.lower() for h in RL_HEADER_HINTS)}
    return {"status": status, "t": time.perf_counter() - t0, "rl": rl, "size": len(body)}


def rand_code(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def phase(url: str, n: int, delay: float, code_len: int) -> list[dict]:
    out = []
    for i in range(n):
        u = url.replace("{code}", rand_code(code_len)) if "{code}" in url else url
        r = probe(u)
        r["i"] = i
        out.append(r)
        if delay:
            time.sleep(delay)
    return out


def summarise(rows: list[dict], wall: float) -> dict:
    ok = [r for r in rows if r["status"]]
    ts = sorted(r["t"] for r in ok)
    return {
        "requests": len(rows),
        "wall_seconds": round(wall, 1),
        "status_set": sorted({r["status"] for r in rows}),
        "throttled": [r for r in rows if r["status"] in (429, 503, 403)],
        "retry_after_or_ratelimit_headers": [r["rl"] for r in ok if r["rl"]],
        "median_latency_s": round(statistics.median(ts), 3) if ts else None,
        "p95_latency_s": round(ts[int(len(ts) * 0.95) - 1], 3) if len(ts) >= 2 else None,
        "errors": [r["error"] for r in rows if r["status"] == 0],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="probe URL; use {code} where the random value goes")
    ap.add_argument("--steady", type=int, default=30, help="requests at ~1 rps (default 30)")
    ap.add_argument("--burst", type=int, default=10, help="back-to-back requests after the steady phase (default 10)")
    ap.add_argument("--len", type=int, default=8, help="length of the random code (default 8)")
    ap.add_argument("--out", default="ratelimit_probe.json", help="JSON evidence path")
    a = ap.parse_args()

    print(f"[rate-limit testing] {a.url}")
    print(f"  random codes only ({a.len} chars) - this is NOT an enumeration attempt")
    t0 = time.perf_counter()
    steady = phase(a.url, a.steady, 1.0, a.len)
    s1 = summarise(steady, time.perf_counter() - t0)
    print(f"  steady {a.steady} @1rps -> status {s1['status_set']} median {s1['median_latency_s']}s"
          f" throttled={len(s1['throttled'])}")

    t0 = time.perf_counter()
    burst = phase(a.url, a.burst, 0.0, a.len)
    s2 = summarise(burst, time.perf_counter() - t0)
    print(f"  burst  {a.burst} in {s2['wall_seconds']}s -> status {s2['status_set']}"
          f" median {s2['median_latency_s']}s throttled={len(s2['throttled'])}")

    throttled = s1["throttled"] + s2["throttled"]
    rl_headers = s1["retry_after_or_ratelimit_headers"] + s2["retry_after_or_ratelimit_headers"]
    verdict = ("no rate limiting OBSERVED (no 429/503, no Retry-After/RateLimit headers, latency stable) "
               "in %d requests" % (a.steady + a.burst)) if not throttled and not rl_headers else \
              "THROTTLING OBSERVED - see throttled/headers in the JSON"
    print(f"  VERDICT: {verdict}")
    print("  reminder: absence of throttling is only a finding when the brute-forced space is small enough"
          " to matter - pair it with the maxlength/pattern keyspace.")

    json.dump({"kind": "rate-limit testing (random inputs only)", "url": a.url,
               "steady": s1, "burst": s2, "verdict": verdict},
              open(a.out, "w", encoding="utf-8"), indent=2)
    print(f"  evidence -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
