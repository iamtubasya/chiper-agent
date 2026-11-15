#!/usr/bin/env python3
"""Verify a candidate bounty program's policy is LIVE before proposing it.

Answers the seven questions from SKILL.md §Step 2 in one pass, per candidate:
reachability (DNS vs HTTP/HTTPS), freshness date, funded-vs-discretionary wording,
reward currency, whether the WEB surface is named in scope, and pause/retire banners
(with surrounding context so a threat-model sentence is not mistaken for a sunset).

Usage:
    python policy_verify.py https://example.com/security
    python policy_verify.py https://raw.githubusercontent.com/org/repo/main/SECURITY.md \
                            https://www.example.com/bug-bounty
    python policy_verify.py --json https://example.com/bug-bounty > out.json

Notes that matter on this host:
  * stdlib only — no requests dependency, works from python.exe directly.
  * follows the GitHub raw trick for you: a /blob/ URL is rewritten to raw.githubusercontent.com
    (the blob page is JS-rendered and truncates, the raw file does not).
  * amount extraction runs on the POLICY text, never the homepage — marketing pages carry price
    tickers ($0.00, $0.52) that a naive regex reads as rewards.
  * a dead/paused verdict is only issued when a keyword appears WITH context; a bare keyword hit is
    reported as "review" so a threat-model sentence is not treated as a shutdown notice.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

DEAD_WORDS = ("sunset", "shut down", "shut ?down", "acquired by", "no longer",
              "discontinu", "paused", "retired", "not currently", "suspended")
AMOUNT_RE = re.compile(r"(?:\$|€|£|USD ?|EUR ?)\s?\d[\d,\.]{1,}")
SEVERITY_RE = re.compile(r"(critical|high|medium|low)[^.\n]{0,90}?"
                         r"(?:\$|€|£|USD ?|EUR ?)\s?[\d,\.]+", re.I)
WEB_SURFACE = ("web app", "webapp", "frontend", "console", "dashboard", "dapp",
               "portal", "backend", "services", "api", "mobile app")
DATE_RE = re.compile(r"(?:last update|effective|updated|version date)\s*:?\s*"
                     r"([0-9]{1,2}\s+\w+\s+[0-9]{4}|\w+\s+[0-9]{1,2},?\s+[0-9]{4}|"
                     r"[0-9]{4}-[0-9]{2}-[0-9]{2})", re.I)


def raw_github(url: str) -> str:
    """blob URL -> raw URL (the raw file is complete and JS-free)."""
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/blob/(.+)", url)
    if m:
        return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return url


def fetch(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=CTX)
        return r.status, r.read(), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, b"", url
    except Exception as e:                                   # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"[:120].encode(), url


def to_text(body: bytes) -> str:
    t = body.decode("utf-8", "replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def dns(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except Exception:                                        # noqa: BLE001
        return "DNSFAIL"


def context_hits(text: str, limit: int = 3) -> list[dict]:
    """Every dead-word hit WITH 220 chars of surrounding sentence."""
    out = []
    for w in DEAD_WORDS:
        for m in re.finditer(w, text, re.I):
            s = max(0, m.start() - 220)
            out.append({"word": m.group(0),
                        "ctx": text[s:m.start() + 240].strip()})
            if len(out) >= limit:
                return out
    return out


def verify(url: str) -> dict:
    target = raw_github(url)
    host = urllib.parse.urlparse(target).netloc
    res = {"input": url, "url": target, "host": host, "dns": dns(host.split(":")[0])}
    code, body, final = fetch(target)
    res["http"] = code
    res["final_url"] = final
    if code != 200 or not body:
        res["verdict"] = "UNREACHABLE"
        return res

    text = to_text(body)
    res["chars"] = len(text)
    res["date"] = (DATE_RE.search(text).group(1) if DATE_RE.search(text) else None)

    amounts = AMOUNT_RE.findall(text)
    sev = SEVERITY_RE.findall(text) or []
    sev_pairs = [m.group(0) for m in SEVERITY_RE.finditer(text)]
    res["amount_samples"] = amounts[:8]
    res["severity_bands"] = sev_pairs[:8]

    low = text.lower()
    res["web_surface"] = sorted({w for w in WEB_SURFACE if w in low})
    res["discretionary"] = bool(re.search(
        r"discretion|may recognize|at (?:our|their) (?:sole )?discretion|"
        r"appropriate reward|other form of recognition|indicative", low))
    res["token_pay"] = bool(re.search(
        r"paid in (?:[A-Z]{2,6}|tokens?|locked)|locked (?:for )?\d+ ?months?", text))
    res["ai_clause"] = bool(re.search(r"\bAI\b.{0,120}(?:submission|report|written|verbose)",
                                      text, re.I))

    hits = context_hits(text)
    res["dead_hits"] = hits

    # verdict logic: hard kill only on an explicit pause banner near "program"
    hard = [h for h in hits if re.search(r"program|bounty|reward|submission", h["ctx"], re.I)
            and re.search(r"paus|suspend|retir|discontinu|sunset|clos", h["ctx"], re.I)]
    funded = bool(sev_pairs)
    if hard:
        res["verdict"] = "PAUSED_OR_RETIRED"
    elif not funded and res["discretionary"]:
        res["verdict"] = "LIVE_DISCRETIONARY"
    elif funded:
        res["verdict"] = "LIVE_FUNDED"
    else:
        res["verdict"] = "LIVE_UNQUANTIFIED"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = [verify(u) for u in args.urls]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    for r in rows:
        print("=" * 78)
        print(f"{r['host']}  http={r['http']}  dns={r['dns']}  {r['verdict']}")
        if r["verdict"] == "UNREACHABLE":
            continue
        print(f"  date       : {r['date'] or '-'}")
        print(f"  funded     : {'yes' if r['severity_bands'] else 'no amount table'}"
              f"{'  (discretionary wording)' if r['discretionary'] else ''}"
              f"{'  (token/lockup pay)' if r['token_pay'] else ''}")
        if r["severity_bands"]:
            for b in r["severity_bands"][:4]:
                print(f"    band     : {b[:110]}")
        print(f"  web surface: {', '.join(r['web_surface']) or 'NOT NAMED — check the asset table'}")
        if r["ai_clause"]:
            print("  ⚠ AI-report clause present — keep the write-up short and verified")
        for h in r["dead_hits"]:
            print(f"  ? '{h['word']}' -> {h['ctx'][:200]}")
        if r["verdict"] == "PAUSED_OR_RETIRED":
            print("  ⛔ hard pause banner near 'program/bounty' — do NOT invest without confirming")
    return 0


if __name__ == "__main__":
    sys.exit(main())
