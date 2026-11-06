#!/usr/bin/env python3
"""Live evidence screenshot server (template).

WHY: browser screenshots of raw curl output look staged. This server performs the REAL
request the moment the page is rendered, then shows the exact request line and the raw
response on the page. Headless Chrome screenshots of that page are real captures of real
traffic (permitted evidence format: "HTML terminal render of REAL tool output ... in a
polished terminal-style layout").

USAGE
  1. Edit the CONFIG + the probe functions at the bottom (each probe runs server-side when
     its route is opened; return (title, [(request_line, raw_response), ...]) or an HTML
     string for browser-executed proofs).
  2. python evidence_screenshot_server.py          # serves 127.0.0.1:8571
  3. Screenshot each route (FRESH profile per shot or Chrome profile-locks the second run):

       "/c/Program Files/Google/Chrome/Application/chrome.exe" \
         --headless=new --disable-gpu --hide-scrollbars \
         --user-data-dir=<fresh dir per shot> --window-size=1280,1500 \
         --virtual-time-budget=14000 --timeout=70000 \
         --screenshot=<abs path.png>  http://127.0.0.1:8571/<route>

     --virtual-time-budget is REQUIRED when the page runs JS (cross-origin fetch proofs);
     server-rendered pages only need --timeout.
  4. Ink-check before trusting: PIL unique-grey > 100 and an ink ratio away from 0;
     cross-check the content with --dump-dom of the same route (grep the key line).
  5. Ship the trio: PDF with `![caption](abs png)` embedded, evidence txt, the PNG.
  6. Stop the server when done; kill lingering headless chrome processes.

CROSS-ORIGIN PROOF PATTERN (route returning an HTML page with credentials:'include' fetch):
the page's own origin is the attacker origin; if the foreign body renders in #results, the
server allowed that origin. Note browsers hide ACAO/ACAC from page JS (not in the exposed
header set) while still permitting the read - capture the header truth separately with curl
-H "Origin: ..." and print both in the page so the reader is not confused by "null".
"""

import html
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------- CONFIG
HOST, PORT = "127.0.0.1", 8571
RESEARCH_HEADER = {"X-BugBounty-Researcher": "REPLACE-ME@example.com"}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE_HEADERS = {**RESEARCH_HEADER, "User-Agent": UA}
DOC_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
# ---------------------------------------------------------------- helpers


def esc(t):
    return html.escape(str(t))


def render(title, blocks, extra_body=""):
    """Dark terminal-style page: blocks = [(request_line, raw_response), ...]."""
    body = "".join(
        '<div class="blk"><div class="req">' + esc(b[0]) + "</div><pre>" +
        esc(b[1]) + "</pre></div>" for b in blocks)
    return ("<!doctype html><html><head><meta charset='utf-8'><title>" + esc(title) + "</title>"
            "<style>body{background:#0d1117;color:#c9d1d9;font:13px/1.45 Consolas,monospace;"
            "margin:0;padding:18px}h1{color:#58a6ff;font-size:16px;margin:0 0 12px}"
            ".blk{margin-bottom:14px}.req{color:#7ee787;font-weight:bold;white-space:pre-wrap}"
            "pre{background:#161b22;border:1px solid #30363d;padding:10px;margin:4px 0 0;"
            "white-space:pre-wrap;word-break:break-all;color:#e6edf3}"
            ".lbl{color:#f0b72f;font-weight:bold}"
            "#results{background:#161b22;border:1px solid #30363d;padding:10px;"
            "white-space:pre-wrap}</style></head><body><h1>" + esc(title) + "</h1>" +
            body + extra_body + "</body></html>")


def get_with_retry(url, headers, tries=3, backoff=12, session=None):
    """GET with backoff on edge blocks (Akamai interstitial check: bm-verify in first 1500)."""
    import requests
    s = session or requests
    r = None
    for _ in range(tries):
        r = s.get(url, headers=headers, timeout=30)
        if r.status_code != 403 and "bm-verify=" not in r.text[:1500]:
            return r
        time.sleep(backoff)
    return r


def xorigin_page(target_url, extra_note=""):
    """Browser-executed cross-origin proof (the page origin is the attacker origin)."""
    return render(
        "LIVE cross-origin PoC - Origin of THIS page is the attacker origin",
        [("TARGET", target_url),
         ("HOW THE BROWSERS READ IT", "fetch(url, {credentials:'include'}) from this page; "
          "a rendered foreign body = the server allowed this origin. " + extra_note)],
        extra_body=(
            "<div class='lbl'>LIVE RESULT:</div><div id='results'>running...</div>"
            "<script>(async()=>{const out=[];const nl=String.fromCharCode(10);"
            "try{const r=await fetch('" + target_url + "',{credentials:'include'});"
            "const t=await r.text();out.push('HTTP '+r.status);"
            "out.push('BODY OF THE FOREIGN ORIGIN READ BY THIS PAGE: '+t.slice(0,300));"
            "}catch(e){out.push('FETCH BLOCKED BY BROWSER: '+e.message);}"
            "document.getElementById('results').textContent=out.join(nl);})();</script>"))


def post_probe(url, data, headers, request_line):
    """Server-side POST replay (no cookies => anonymous proof; add session cookies for authed)."""
    import requests
    r = requests.post(url, data=data, headers=headers, timeout=30)
    return (request_line,
            "HTTP " + str(r.status_code) + "\n" + r.text[:1500])


def login_session(meta):
    """Example: open YOUR session helper here (own test accounts only) and return it."""
    raise NotImplementedError("wire this to the engagement's login helper")


# ---------------------------------------------------------------- probes
# Replace with the real probes of the finding being screenshotted.

def route_f1():
    return xorigin_page("https://TARGET-EXAMPLE/oauth/authorize?client_id=x",
                        "Server-side truth of the same request (curl -H 'Origin: this page') "
                        "belongs above the fold in the evidence txt.")


def route_f2():
    request_line = ("POST https://TARGET-EXAMPLE/user-api/thing.asp   (NO captcha token)\n"
                    "body: strFunction=create&title=SCREEN_PROOF")
    block = post_probe(
        "https://TARGET-EXAMPLE/user-api/thing.asp",
        {"strFunction": "create", "title": "SCREEN_PROOF"},
        {**BASE_HEADERS, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
         "Origin": "https://www.TARGET-EXAMPLE", "Referer": "https://www.TARGET-EXAMPLE/"},
        request_line)
    time.sleep(1.5)
    # follow-up: prove the state change is visible (page render or GET)
    # block2 = ...
    return render("F2 LIVE - state change accepted without the required token", [block])


ROUTES = {
    "/f1": route_f1,
    "/f2": route_f2,
    # "/f3": ..., "/f4": ...
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ROUTES:
                out = ROUTES[path]()
            elif path == "/":
                out = "<html><body>routes: " + " ".join(sorted(ROUTES)) + "</body></html>"
            else:
                out = "<html><body>404</body></html>"
            data = out.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = ("ERROR: " + type(e).__name__ + ": " + str(e)).encode()
            self.send_response(500)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


if __name__ == "__main__":
    print("evidence server on http://%s:%d  routes: %s" % (HOST, PORT, " ".join(sorted(ROUTES))),
          flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
