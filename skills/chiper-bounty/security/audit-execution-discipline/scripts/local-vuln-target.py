#!/usr/bin/env python3
"""Local vulnerable target for toolchain dry-runs (127.0.0.1 ONLY).

WHY: before firing any scanner volley at a real target — and *always* when a program forbids
scanners and you are validating the toolchain instead of using it — prove every tool actually
scans something. A tool that returns rc=0 while printing a usage banner or an empty result is
the "fake coverage" trap; this fixture gives it something real to find.

USAGE
    python local-vuln-target.py 8097            # foreground
    # then point tools at http://127.0.0.1:8097
    nuclei -u http://127.0.0.1:8097 -silent -t "D:/data hermes/nuclei-templates/http" \
        -tags tech,exposure,misconfiguration -no-color
    ffuf -u http://127.0.0.1:8097/FUZZ -w "D:/data hermes/wordlists/0B-recon/directories/common.txt" \
        -mc 200,204,301,302,307,401,403 -t 20 -s
    gobuster dir -u http://127.0.0.1:8097 -w "D:/data hermes/wordlists/0B-recon/directories/common.txt" \
        --timeout 10s -t 5 -q
    dalfox url "http://127.0.0.1:8097/search?q=test" --skip-bav --no-color
    sqlmap -u "http://127.0.0.1:8097/api/v1/users?id=1" --batch --level=2 --risk=1 --smart
    arjun -u http://127.0.0.1:8097/api/v1/users -t 4 -d 1
    CORScanner -u http://127.0.0.1:8097
    katana -u http://127.0.0.1:8097 -silent -no-color
    naabu -host 127.0.0.1 -p 8097 -silent -no-color
    wafw00f http://127.0.0.1:8097

EXPECTED POSITIVES (what "the tool really fired" looks like)
    nuclei    -> a match on /backup.zip (zip-backup-files) + tech-detect
    ffuf      -> admin, login
    gobuster  -> admin (403), login (200), search (200)
    arjun     -> "Extracted 3 parameters"
    katana    -> 4 crawled URLs
    naabu     -> 127.0.0.1:8097 open
    sqlmap    -> "testing if GET parameter 'id' is dynamic" ... "not injectable" (a VERDICT, i.e. it tested)

Run it from the engagement's tools/ dir; it is deliberately single-threaded and silent.
"""
import http.server
import json
import socketserver
import sys
import urllib.parse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8097


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep stdout clean for the caller

    def _send(self, code, body, ctype="text/html"):
        payload = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Server", "LocalVulnTest/1.0")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        if url.path == "/":
            self._send(200, "<html><body>home <a href='/admin'>admin</a> "
                            "<a href='/login'>login</a> "
                            "<a href='/api/v1/users?id=1'>api</a></body></html>")
        elif url.path == "/search":
            # reflected parameter for dalfox / sqlmap parameter discovery
            self._send(200, "<html><body>results for: " + qs.get("q", [""])[0] + "</body></html>")
        elif url.path == "/admin":
            self._send(403, "<html><body>forbidden</body></html>")
        elif url.path == "/login":
            self._send(200, "<html><body><form method=post><input name=user>"
                            "<input name=pass type=password></form></body></html>")
        elif url.path == "/api/v1/users":
            uid = qs.get("id", ["1"])[0]
            self._send(200, json.dumps({"id": uid, "name": "user" + str(uid)}), "application/json")
        elif url.path == "/backup.zip":
            # nuclei's zip-backup-files template matches this
            self._send(200, b"PK\x03\x04 fake", "application/zip")
        else:
            self._send(404, "<html><body>not found</body></html>")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", "replace")
        self._send(200, "<html><body>posted: " + body[:200] + "</body></html>")


class Server(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print(f"listening on {PORT}", flush=True)
        httpd.serve_forever()
