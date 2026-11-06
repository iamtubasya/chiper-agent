#!/usr/bin/env python3
"""
PortSwigger Lab Helper — spawn lab instance + exploit via requests.
Mengelola cookies login, spawn lab, dan memudahkan exploit SQLi labs.

Usage:
  python ps_helper.py spawn <lab-description-url> [--out URL_FILE]
  python ps_helper.py solved <lab-url>              # cek solved banner
  python ps_helper.py req <lab-url> <path>          # GET request instance
"""
import json, sys, time, re, requests
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIES_FILE = Path("C:/Users/WINDOWS10/AppData/Local/Temp/ps_cookies.json")


def get_cookies():
    if not COOKIES_FILE.exists():
        raise RuntimeError(f"cookies tidak ada: {COOKIES_FILE} — login dulu")
    return json.loads(COOKIES_FILE.read_text())


def spawn(lab_desc_url, wait_sec=15, out_file=None):
    """Buka halaman deskripsi lab -> klik ACCESS THE LAB -> return URL instance."""
    cookies = get_cookies()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120")
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto(lab_desc_url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(4)
        with page.expect_popup(timeout=25000) as popup_info:
            page.click('a:has-text("ACCESS THE LAB")')
        lab = popup_info.value
        time.sleep(wait_sec)
        lab_url = lab.url.rstrip("/") + "/"
        print(f"SPAWNED: {lab_url}")
        if out_file:
            Path(out_file).write_text(lab_url)
        browser.close()
        return lab_url


def solved_check(lab_url):
    """Cek banner solved di instance lab."""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    for path in ["/", "/filter?category=Gifts"]:
        r = s.get(lab_url.rstrip("/") + path, timeout=15)
        if "congratulations" in r.text.lower() or "Congratulations" in r.text:
            return True
    return False


def req(lab_url, path):
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r = s.get(lab_url.rstrip("/") + path, timeout=20)
    print(f"{r.status_code} len={len(r.text)}")
    if "congratulations" in r.text.lower():
        print("SOLVED!")
    return r


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "spawn":
        url = sys.argv[2]
        out = None
        if len(sys.argv) > 3 and sys.argv[3] == "--out":
            out = sys.argv[4]
        spawn(url, out_file=out)
    elif cmd == "solved":
        print("SOLVED" if solved_check(sys.argv[2]) else "NOT SOLVED")
    elif cmd == "req":
        req(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "/")
    else:
        print(__doc__)