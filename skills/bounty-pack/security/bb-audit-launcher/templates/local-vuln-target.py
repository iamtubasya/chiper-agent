#!/usr/bin/env python3
"""Local vulnerable fixture used to validate a scanner toolchain BEFORE pointing it at a target.

Never point scanners at a real target to "see if they work" — validate here first. Success criterion:
every tool prints a REAL result line, not a usage dump. Known-good expectations:

  nuclei    -> matches a template (e.g. zip-backup-files) + tech-detect
  ffuf      -> finds admin, login
  gobuster  -> admin (403), login (200), search (200)
  sqlmap    -> names the parameter and returns a verdict ("does not appear to be injectable")
  arjun     -> "Extracted N parameters"
  httpx     -> the host
  katana    -> crawls /, /admin, /login, /api/v1/users?id=1
  naabu     -> reports the open port
  wafw00f   -> runs a fingerprint pass

Usage:
    python local-vuln-target.py 8097
    # then point tools at http://127.0.0.1:8097  (on Windows/MSYS: export MSYS_NO_PATHCONV=1 first)
"""
import http.server, socketserver, urllib.parse, json, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8097


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ct="text/html"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Server", "LocalVulnTest/1.0")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/":
            self._send(200, "<html><body>home <a href='/admin'>admin</a> <a href='/login'>login</a>"
                            " <a href='/api/v1/users?id=1'>api</a></body></html>")
        elif u.path == "/search":
            # reflected param so dalfox/arjun have something to chew on
            self._send(200, "<html><body>results for: " + q.get("q", [""])[0] + "</body></html>")
        elif u.path == "/admin":
            self._send(403, "<html><body>forbidden</body></html>")
        elif u.path == "/login":
            self._send(200, "<html><body><form method=post><input name=user>"
                            "<input name=pass type=password></form></body></html>")
        elif u.path == "/api/v1/users":
            uid = q.get("id", ["1"])[0]
            self._send(200, json.dumps({"id": uid, "name": "user" + str(uid)}), "application/json")
        elif u.path == "/backup.zip":
            self._send(200, b"PK\x03\x04 fake", "application/zip")
        else:
            self._send(404, "<html><body>not found</body></html>")

    def do_POST(self):
        ln = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(ln).decode("utf-8", "replace")
        self._send(200, "<html><body>posted: " + body[:200] + "</body></html>")


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", PORT), H) as httpd:
    print("listening on", PORT, flush=True)
    httpd.serve_forever()
