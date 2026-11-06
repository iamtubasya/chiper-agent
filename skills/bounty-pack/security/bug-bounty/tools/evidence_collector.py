#!/usr/bin/env python3
"""
evidence_collector.py — Gather evidence (headers, screenshots, PoCs).
Usage:
  python3 evidence_collector.py --url "https://..." --output evidence/ --headers
"""
import json, sys, os, argparse, subprocess, hashlib
from datetime import datetime

def collect_headers(url, output_dir):
    """Collect HTTP headers as evidence."""
    headers_file = os.path.join(output_dir, "headers.txt")
    try:
        result = subprocess.run(
            ["curl", "-sI", "-m", "10", url],
            capture_output=True, text=True, timeout=15
        )
        with open(headers_file, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            f.write(f"Collected: {datetime.now(__import__("datetime").timezone.utc).isoformat()}\n\n")
            f.write(result.stdout)
        print(f"[EVIDENCE] Headers saved: {headers_file}")
        return result.stdout
    except Exception as e:
        print(f"[EVIDENCE] Header collection failed: {e}")
        return None

def collect_response(url, output_dir):
    """Collect full response body."""
    body_file = os.path.join(output_dir, "response_body.txt")
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "10", url],
            capture_output=True, text=True, timeout=15
        )
        with open(body_file, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            f.write(f"Collected: {datetime.now(__import__("datetime").timezone.utc).isoformat()}\n\n")
            f.write(result.stdout[:50000])  # limit to 50KB
        print(f"[EVIDENCE] Response body saved: {body_file}")
        return result.stdout[:5000]
    except Exception as e:
        print(f"[EVIDENCE] Response collection failed: {e}")
        return None

def collect_cookies(url, output_dir):
    """Collect cookies."""
    cookies_file = os.path.join(output_dir, "cookies.txt")
    try:
        result = subprocess.run(
            ["curl", "-sI", "-m", "10", url],
            capture_output=True, text=True, timeout=15
        )
        cookies = [line for line in result.stdout.split("\n") if "set-cookie" in line.lower()]
        with open(cookies_file, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            f.write(f"Collected: {datetime.now(__import__("datetime").timezone.utc).isoformat()}\n\n")
            for c in cookies:
                f.write(c.strip() + "\n")
        print(f"[EVIDENCE] Cookies saved: {cookies_file}")
        return cookies
    except Exception as e:
        print(f"[EVIDENCE] Cookie collection failed: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Evidence collector for bug bounty")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--output", default="evidence", help="Output directory")
    parser.add_argument("--headers", action="store_true", help="Collect headers")
    parser.add_argument("--body", action="store_true", help="Collect response body")
    parser.add_argument("--cookies", action="store_true", help="Collect cookies")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if not any([args.headers, args.body, args.cookies]):
        # Collect everything by default
        args.headers = True
        args.body = True
        args.cookies = True

    evidence = {"url": args.url, "collected": datetime.now(__import__("datetime").timezone.utc).isoformat()}

    if args.headers:
        evidence["headers"] = collect_headers(args.url, args.output)
    if args.body:
        evidence["body_preview"] = collect_response(args.url, args.output)
    if args.cookies:
        evidence["cookies"] = collect_cookies(args.url, args.output)

    # Save evidence manifest
    manifest_file = os.path.join(args.output, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, default=str)
    print(f"[EVIDENCE] Manifest: {manifest_file}")
    print(f"[EVIDENCE] Complete: {args.output}/")

if __name__ == "__main__":
    main()
