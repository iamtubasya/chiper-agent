#!/usr/bin/env python3
"""Capture the FULL pre-auth request surface of an SPA login/webmail/portal front end.

Why: a path wordlist cannot guess product-specific endpoints. The unauthenticated page already
calls them, so load the page in a real browser and read the list off the wire. This is how
endpoints like `GET /auth` and `GET /auth/spa/config?app=webmail` were found on a target where a
215-name product wordlist and a ~900-path sweep had both come up empty.

Usage:
    python preauth_spa_capture.py https://host1/ https://host2/login --skill X-Bug-Bounty: you@x
    python preauth_spa_capture.py -f urls.txt --out preauth.json --wait 6

Output: a deduped table of (method, URL, status, content-type) for every XHR/fetch and every
/api//auth/ URL, plus every POST body seen (POST bodies reveal request shapes you would otherwise
have to guess). Static /ui/assets/* noise is filtered; use --all to keep it.

Notes that matter:
  * Set the identity header on the CONTEXT, so every subresource request carries it too -- a
    header added only to page.goto() does not propagate to XHR.
  * `wait_until="networkidle"` alone is not enough; lazy calls fire after settle. Keep the trailing
    sleep + a scroll + an optional click on a sign-in control.
  * Keep query strings (dedupe on path only, print the full URL). Cache-busting and per-app
    parameters (`?app=webmail`, `?app=account-portal`) tell you which variants exist.
  * Run it against each distinct front end separately (webmail vs auth vs account portal); the
    surfaces differ and a 200 on one is often a 404 on another.
  * Then verify each candidate unauthenticated with a plain HTTP client -- the browser proves the
    app calls it, not that it answers 200 without a session.
"""
import argparse
import json
import sys
import time
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright not installed: pip install playwright && playwright install chromium")


def load_targets(args):
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            return [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    return args.urls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*", help="seed URLs (login / webmail / portal roots)")
    ap.add_argument("-f", "--file", help="file with one URL per line")
    ap.add_argument("--skill", "--header", dest="header", default="<you>",
                    help='identity header value, e.g. --header "X-Bug-Bounty: you@example.com"')
    ap.add_argument("--hname", default="X-Bug-Bounty", help="identity header name")
    ap.add_argument("--out", default="preauth_spa_capture.json")
    ap.add_argument("--wait", type=float, default=4.0, help="seconds to linger after networkidle")
    ap.add_argument("--timeout", type=int, default=45000, help="navigation timeout ms")
    ap.add_argument("--all", action="store_true", help="keep static asset noise")
    args = ap.parse_args()

    targets = load_targets(args)
    if not targets:
        sys.exit("no targets: pass URLs or -f urls.txt")

    records, errors = [], []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
        for url in targets:
            hdr = {}
            if args.header:
                hdr[args.hname] = args.header
            ctx = br.new_context(ignore_https_errors=True, extra_http_headers=hdr,
                                 user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                                             "Chrome/124.0 Safari/537.36"))
            page = ctx.new_page()
            seen = []

            def on_req(req, label=url):
                try:
                    seen.append({"seed": label, "method": req.method, "url": req.url,
                                 "rtype": req.resource_type,
                                 "post": (req.post_data or "")[:400]})
                except Exception as exc:                       # noqa: BLE001
                    errors.append(str(exc))

            def on_resp(resp, label=url):
                try:
                    seen.append({"seed": label, "method": resp.request.method, "url": resp.url,
                                 "rtype": "RESPONSE", "status": resp.status,
                                 "ct": resp.headers.get("content-type", "")})
                except Exception:                              # noqa: BLE001
                    pass

            page.on("request", on_req)
            page.on("response", on_resp)
            try:
                page.goto(url, wait_until="networkidle", timeout=args.timeout)
                time.sleep(args.wait)
                page.mouse.wheel(0, 1200)
                time.sleep(2)
                for sel in ("text=Sign in", "text=Login", "text=Log in", "button[type=submit]"):
                    try:
                        el = page.query_selector(sel)
                        if el:
                            el.click(timeout=2500)
                            time.sleep(3)
                            break
                    except Exception:                          # noqa: BLE001
                        pass
            except Exception as exc:                           # noqa: BLE001
                errors.append(f"{url}: {exc}")
            records.extend(seen)
            print(f"[seed] {url} -> {len(seen)} request events", file=sys.stderr)
            ctx.close()
        br.close()

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"records": records, "errors": errors}, fh, indent=1)

    KEY = ("/api/", "/auth", "/jmap", "/login", "/config", "/opt-in", "/upload", "/download",
           "/sso", "/oidc", "/session", "/token")
    uniq = {}
    for r in records:
        u = r.get("url", "")
        if not args.all and "/ui/" in u and "/assets/" in u:
            continue
        if r.get("rtype") not in ("xhr", "fetch", "RESPONSE") and not any(k in u for k in KEY):
            continue
        path = urlparse(u).path
        key = (r.get("method"), path)
        slot = uniq.setdefault(key, {"n": 0, "status": None, "ct": "", "url": u, "post": ""})
        slot["n"] += 1
        if r.get("status") is not None:
            slot["status"] = r["status"]
            slot["ct"] = (r.get("ct") or "")[:32]
        if r.get("post"):
            slot["post"] = r["post"]

    print(f"\n=== PRE-AUTH SURFACE ({len(uniq)} unique method+path) ===")
    for (m, path), v in sorted(uniq.items(), key=lambda kv: (kv[0][1], kv[0][0] or "")):
        st = v["status"] if v["status"] is not None else "?"
        line = f"  {v['n']:>3}x {m or '?':5s} {str(st):>4}  {v['url'][:160]}"
        if v["ct"]:
            line += f"   [{v['ct']}]"
        print(line)
        if v["post"]:
            print(f"        POST body: {v['post'][:220]}")
    print(f"\n{len(records)} events, {len(errors)} errors -> {args.out}")
    print("NEXT: verify each candidate with a plain HTTP client (browser proves the app calls it,\n"
          "      not that it answers 200 without a session), then triage per the skill's Step 3.")
    if errors:
        print("\nerrors:", *errors[:10], sep="\n  ")


if __name__ == "__main__":
    main()
