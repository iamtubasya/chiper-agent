#!/usr/bin/env python3
"""Verify CloakBrowser install & stealth basics (deterministic probe).

Usage:  python verify_cloakbrowser.py        (from this skill's scripts/ dir, or absolute path)
Exit 0 = PASS (clean UA, webdriver flag off). Exit 1 = FAIL with reason.

Verified baseline 2026-09-10 (cloakbrowser v0.5.10, Chromium 146.0.7680.177.5):
  UA = "Chrome/146.0.0.0"  (no HeadlessChrome leak)
  navigator.webdriver = False
"""
import sys


def main() -> int:
    try:
        from cloakbrowser import launch
    except ImportError:
        print("FAIL: cloakbrowser not installed ->  pip install cloakbrowser")
        return 1

    try:
        b = launch(headless=True)
        p = b.new_page()
        p.goto("https://example.com", timeout=30000)
        ua = p.evaluate("navigator.userAgent")
        wd = p.evaluate("navigator.webdriver")
        title = p.title()
        b.close()
    except Exception as e:  # noqa: BLE001 - probe must report any launch failure
        print(f"FAIL: launch error: {e}")
        print("If binary missing run:  python -m cloakbrowser install")
        return 1

    ok = True
    if "HeadlessChrome" in ua:
        print(f"WARN/FAIL: UA leaks HeadlessChrome -> {ua}")
        ok = False
    if wd:
        print(f"WARN/FAIL: navigator.webdriver={wd!r} (expect False/undefined)")
        ok = False

    print(f"TITLE:    {title}")
    print(f"UA:       {ua}")
    print(f"WEBDRIVER:{wd}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
