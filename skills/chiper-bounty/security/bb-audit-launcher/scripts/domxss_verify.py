#!/usr/bin/env python
"""Deterministic DOM-XSS false-positive verifier.

Why: headless scanners flag `dom-sink:mutated-node:SCRIPT` / `window.onerror` for any hash
fragment that appears in the DOM, even when it never EXECUTES (observed 110 candidates on
bluewin.ch, 0 real). This script separates "payload present in DOM" from "payload executed":
for each URL it injects `<img src=x onerror="document.title='MARKER'">` into the hash, loads
the page, and checks whether the marker landed in document.title (execution) or not.

Usage:
  python domxss_verify.py urls.txt [marker]        # one URL per line, '#' fragments ok
  echo https://target/#<img src=x onerror="..."> | python domxss_verify.py - [marker]

Exit code 0 always (it is a measurement, not a gate). Output: JSON with per-URL fired flags.
Verdict: fired==0 across all URLs => the scanner's DOM-XSS candidates are false positives.
fired>=1  => capture page.content() + title as evidence and keep it as a candidate.
"""
from __future__ import annotations

import json
import sys

DEFAULT_MARKER = "DOMXSSFIRE_9x7"
# Both a bare-hash and a quote-broken variant: the two shapes scanners flag most.
PAYLOAD_TEMPLATES = [
    '#<img src=x onerror="document.title=\'{m}\'">',
    '#"><img src=x onerror="document.title=\'{m}\'">',
]


def load_urls(src: str) -> list[str]:
    if src == "-":
        raw = sys.stdin.read()
    else:
        with open(src, encoding="utf-8", errors="ignore") as fh:
            raw = fh.read()
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("http"):
            out.append(line.split()[0])
    return out


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    marker = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MARKER
    urls = load_urls(src)
    if not urls:
        print(json.dumps({"error": "no input urls"}))
        return 0

    # Dedupe by route (strip existing fragment): one execution test per route.
    routes = []
    seen = set()
    for u in urls:
        base = u.split("#", 1)[0]
        if base not in seen:
            seen.add(base)
            routes.append(base)

    results = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"error": "playwright not installed"}))
        return 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-gpu"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"
        )
        for base in routes:
            for tmpl in PAYLOAD_TEMPLATES:
                test_url = base + tmpl.format(m=marker)
                page = ctx.new_page()
                rec = {"url": test_url[:200], "fired": False, "payload_in_dom": False,
                       "console_n": 0, "error": None}
                try:
                    console: list[str] = []
                    page.on("console", lambda m: console.append(m.text[:120]))
                    page.goto(test_url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(2500)
                    title = page.title()
                    body = page.content()
                    rec["fired"] = marker in title or marker in body
                    rec["payload_in_dom"] = "onerror" in body
                    rec["console_n"] = len(console)
                    rec["title"] = title[:80]
                except Exception as exc:  # noqa: BLE001 - report, never crash the batch
                    rec["error"] = str(exc)[:150]
                results.append(rec)
                page.close()
        browser.close()

    fired = [r for r in results if r.get("fired")]
    print(json.dumps({
        "routes_tested": len(routes),
        "checks": len(results),
        "fired": len(fired),
        "verdict": "FP (payload present but never executed)" if not fired else "CANDIDATE - execution proven",
        "results": results,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
