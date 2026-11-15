#!/usr/bin/env python3
"""slow_probe.py - low-and-slow raw-socket probe for rate-limited / stateful-WAF targets.

Why raw sockets: when a WAF rate-limits by *client fingerprint* (curl/urllib TLS+headers) rather
than by IP, the cheapest control test is a plain socket that sends an HTTP/1.0 request with a
`Host:` header while connecting straight to the origin IP - no library fingerprint to match on.

Companion to this skill's workflow: after confirming the block is *rate-based* (quick burst -> 302,
30-60 s cooldown -> 200), enumerate with a gap of 5-6 s per request instead of hammering.

Usage:
  python slow_probe.py <host> <origin_ip> --path "/index.php?article=8" --delay 6
  python slow_probe.py <host> <origin_ip> --paths-file candidates.txt --delay 6
  python slow_probe.py <host> <origin_ip> --path "/a" --path "/b" --port 443 --tls --delay 5

Options:
  --path           repeatable; a path to request (may include query string)
  --paths-file     file with one path per line (blank lines / #comments ignored)
  --delay          seconds to wait BETWEEN requests (default 6)
  --port           default 80, or 443 when --tls
  --tls            wrap the socket in TLS (SNI = host)
  --timeout        per-request socket timeout (default 15)
  --header         repeatable extra header, e.g. --header "User-Agent: Mozilla/5.0"
  --method         default GET
  --show-body      print the first 300 chars of each body

Exit code: 0 if at least one 200 was seen, 1 otherwise (handy in shell conditionals).
Authorised testing only.
"""
import argparse
import socket
import ssl
import sys
import time

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="slow_probe.py", description="low-and-slow raw-socket probe")
    p.add_argument("host", help="Host header / SNI value (e.g. shop.example.com)")
    p.add_argument("origin_ip", help="IP to connect to directly (bypasses DNS/WAF fronting)")
    p.add_argument("--path", action="append", default=[], help="repeatable path (incl. query)")
    p.add_argument("--paths-file", help="file with one path per line")
    p.add_argument("--delay", type=float, default=6.0, help="gap between requests (s)")
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--tls", action="store_true")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--header", action="append", default=[])
    p.add_argument("--method", default="GET")
    p.add_argument("--show-body", action="store_true")
    return p.parse_args(argv)


def load_paths(a):
    paths = list(a.path)
    if a.paths_file:
        with open(a.paths_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    paths.append(line)
    return paths


def one_request(a, path, port, first=False):
    req = [f"{a.method} {path} HTTP/1.0",
           f"Host: {a.host}",
           f"User-Agent: {DEFAULT_UA}",
           "Accept: */*",
           "Connection: close"]
    req += a.header
    raw = ("\r\n".join(req) + "\r\n\r\n").encode()

    t0 = time.time()
    try:
        s = socket.create_connection((a.origin_ip, port), timeout=a.timeout)
        if a.tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s = ctx.wrap_socket(s, server_hostname=a.host)
        s.sendall(raw)
        chunks, total = [], 0
        while True:
            b = s.recv(65536)
            if not b:
                break
            total += len(b)
            if len(chunks) < 40:
                chunks.append(b)
        s.close()
    except Exception as e:
        return {"path": path, "error": f"{type(e).__name__}: {e}", "ms": int((time.time() - t0) * 1000)}

    data = b"".join(chunks)
    head, _, body = data.partition(b"\r\n\r\n")
    status = "?"
    lines = head.split(b"\r\n")
    if lines and lines[0].startswith(b"HTTP/"):
        parts = lines[0].split()
        if len(parts) > 1:
            status = parts[1].decode("ascii", "replace")
    return {"path": path, "status": status, "bytes": total,
            "ms": int((time.time() - t0) * 1000),
            "body": body[:300].decode("utf-8", "replace") if a.show_body else ""}


def main(argv=None):
    a = parse_args(argv)
    port = a.port or (443 if a.tls else 80)
    paths = load_paths(a)
    if not paths:
        print("no paths given (use --path or --paths-file)", file=sys.stderr)
        return 2
    print(f"target {a.host} -> origin {a.origin_ip}:{port}  tls={a.tls}  delay={a.delay}s  n={len(paths)}")
    print("-" * 72)
    hits = 0
    for i, path in enumerate(paths):
        if i:
            time.sleep(a.delay)        # the whole point: the gap
        r = one_request(a, path, port)
        if "error" in r:
            print(f"[ERR ] {r['ms']:>6}ms  {path}  {r['error']}")
            continue
        if r["status"] == "200":
            hits += 1
        flag = "HIT " if r["status"] == "200" else "    "
        print(f"[{flag}] {r['status']:>3}  {r['bytes']:>8}B  {r['ms']:>6}ms  {path}")
        if a.show_body and r["body"]:
            print("        " + r["body"].replace("\n", " ")[:200])
    print("-" * 72)
    print(f"done: {hits}/{len(paths)} returned 200")
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
