#!/usr/bin/env python3
"""Extract real destinations from a saved email (ESP click-tracking aware).

Handles the Mandrill/ESP pattern where every href is
    https://<esp>/track/click/<id>/<original-host>?p=<base64 json {"p":"{\"url\":\"...\"}"}
and prints the decoded target, plus any direct (untracked) http links.

Usage
-----
python extract_mail_links.py mail.html            # saved html part
python extract_mail_links.py mail.eml             # raw message (html part is picked out)
cat mail.html | python extract_mail_links.py -

Why: an injected anchor is evidence, but the link in the received mail is an ESP-tracking URL.
The decoded `url=` value is what belongs in the report as the attacker-controlled destination.
"""
import base64, json, re, sys, urllib.parse as up


def decode_wrapper(link):
    q = up.parse_qs(up.urlparse(link).query)
    p = q.get("p", [""])[0]
    if not p:
        return None
    try:
        outer = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)).decode())
    except Exception:
        return None
    for cand in (outer.get("p"), outer):
        try:
            data = json.loads(cand) if isinstance(cand, str) else cand
            if isinstance(data, dict) and data.get("url"):
                return data["url"]
        except Exception:
            continue
    return None


def links_from(text):
    return sorted(set(re.findall(r'href="([^"]+)"', text)))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = sys.argv[1]
    raw = sys.stdin.read() if src == "-" else open(src, encoding="utf-8", errors="replace").read()

    # .eml / raw message: keep only the html part, and print the useful headers
    if "DKIM-Signature" in raw or "\nSubject:" in raw[:4000]:
        for hdr in ("From", "Return-Path", "Reply-To", "Subject", "Message-ID",
                    "Received-SPF", "Authentication-Results", "DKIM-Signature"):
            m = re.search(rf"^{hdr}:(.*(?:\n[ \t].*)*)", raw, re.M | re.I)
            if m:
                print(f"{hdr:<26}: {m.group(1).strip()[:300]}".replace("\n", " "))
        print("-" * 70)
        m = re.search(r"Content-Type:\s*text/html.*?\n\n(.*)", raw, re.S | re.I)
        if m:
            raw = m.group(1)

    links = links_from(raw)
    print(f"links found: {len(links)}")
    for l in links:
        real = decode_wrapper(l)
        if real:
            print(f"[tracked -> decoded] {real[:200]}")
            print(f"                     (wrapper: {l[:90]}…)")
        else:
            print(f"[direct ]           {l[:200]}")
    print("\nInjection check: look for uncompiled payload markers in the html part, e.g.")
    for pat in ("<b>MK</b>", "{{7*7}}", "&lt;b&gt;", "evil.example", "<iframe", "<a href"):
        n = raw.count(pat)
        if n:
            i = raw.find(pat)
            print(f"  {pat:<16} x{n}  ctx: {raw[max(0,i-120):i+140]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
