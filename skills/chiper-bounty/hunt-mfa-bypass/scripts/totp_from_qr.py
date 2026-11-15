#!/usr/bin/env python3
"""Extract TOTP secrets from an otpauth-migration QR (Google Authenticator export).

Use when you own the test account and need unlimited codes instead of waiting on
the operator for a 30-second one.

Usage:
    python totp_from_qr.py <image>            # decode + print secrets
    python totp_from_qr.py <image> --json     # emit totp.json for reuse
    python totp_from_qr.py --uri '<uri>'      # skip the image step

Requires: opencv-python, zxingcpp, pyotp
    pip install opencv-python zxingcpp pyotp

Notes
-----
* Works on screenshots and phone photos of a screen. Escalation ladder is applied
  automatically: raw -> upscale 2..8x -> fixed threshold -> adaptive -> invert -> OTSU.
* The decoded payload is a protobuf `MigrationPayload`; each `otp_parameters` entry
  carries the secret in field 1 (raw bytes -> base32 for pyotp).
* A truncated/mangled QR in an email is a different problem: if the vendor emails a
  verification link with the parameter value literally missing (e.g. `&user_idw74`
  instead of `&user_id=74`), that is a functional defect, not a security bug --
  record it, do not report it as a vulnerability.
"""

import base64
import json
import sys
import time
import urllib.parse

ALG = {0: "unspecified", 1: "SHA1", 2: "SHA256", 3: "SHA512", 4: "MD5"}
DIG = {0: "unspecified", 1: "6", 2: "8"}
TYP = {0: "unspecified", 1: "HOTP", 2: "TOTP"}


def read_varint(buf, i):
    shift = 0
    val = 0
    while True:
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, i


def parse(buf):
    """Minimal protobuf wire parser -> list of (field, wiretype, value)."""
    i = 0
    out = []
    while i < len(buf):
        key, i = read_varint(buf, i)
        field, wt = key >> 3, key & 7
        if wt == 0:
            v, i = read_varint(buf, i)
            out.append((field, "varint", v))
        elif wt == 2:
            ln, i = read_varint(buf, i)
            out.append((field, "bytes", buf[i:i + ln]))
            i += ln
        elif wt == 5:
            out.append((field, "32bit", buf[i:i + 4])); i += 4
        elif wt == 1:
            out.append((field, "64bit", buf[i:i + 8])); i += 8
        else:
            raise ValueError("unexpected wiretype %d at offset %d" % (wt, i))
    return out


def decode_uri(uri):
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(uri).query)
    data = qs["data"][0]
    raw = base64.b64decode(data + "=" * (-len(data) % 4))

    top = parse(raw)
    params = [v for (f, t, v) in top if f == 1 and t == "bytes"]
    if not params:
        raise SystemExit("no otp_parameters in payload")

    accounts = []
    for p in params:
        d = {}
        for f, t, v in parse(p):
            d.setdefault(f, []).append(v)
        secret = d.get(1, [b""])[0]
        accounts.append({
            "secret": base64.b32encode(secret).decode().rstrip("="),
            "name": d.get(2, [b""])[0].decode("utf-8", "replace"),
            "issuer": d.get(3, [b""])[0].decode("utf-8", "replace"),
            "algo": ALG.get(d.get(4, [0])[0], d.get(4, [0])[0]),
            "digits": DIG.get(d.get(5, [0])[0], "6"),
            "type": TYP.get(d.get(6, [0])[0], "TOTP"),
            "counter": d.get(7, [0])[0],
        })
    return accounts


def decode_image(path):
    import cv2
    import zxingcpp

    img = cv2.imread(path)
    if img is None:
        raise SystemExit("cannot read image: %s" % path)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    hits = []

    def try_decode(im, tag):
        for r in zxingcpp.read_barcodes(im):
            hits.append(r.text)
        return bool(hits)

    try_decode(gray, "raw")
    if not hits:
        for s in (2, 3, 4, 5, 6, 8):
            if try_decode(cv2.resize(gray, (w * s, h * s), interpolation=cv2.INTER_CUBIC), "x%d" % s):
                break
    if not hits:
        for th in (100, 120, 140, 160, 180, 200):
            _, b = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
            if try_decode(b, "thr%d" % th):
                break
            if try_decode(cv2.resize(b, (w * 3, h * 3), interpolation=cv2.INTER_NEAREST), "thr%dx3" % th):
                break
    if not hits:
        ad = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 10)
        if not try_decode(ad, "adaptive"):
            try_decode(cv2.resize(ad, (w * 3, h * 3), interpolation=cv2.INTER_NEAREST), "adaptive-x3")
    if not hits:
        try_decode(cv2.bitwise_not(gray), "invert")
    if not hits:
        bl = cv2.GaussianBlur(gray, (3, 3), 0)
        _, o = cv2.threshold(bl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if not try_decode(o, "otsu"):
            try_decode(cv2.resize(o, (w * 3, h * 3), interpolation=cv2.INTER_NEAREST), "otsu-x3")
    if not hits:  # last resort: quadrant tiles
        for y0 in (0, h // 2):
            for x0 in (0, w // 2):
                c = gray[y0:min(h, y0 + max(h // 2, 200)), x0:min(w, x0 + max(w // 2, 200))]
                for s in (2, 4, 6, 8):
                    if try_decode(cv2.resize(c, (c.shape[1] * s, c.shape[0] * s),
                                             interpolation=cv2.INTER_CUBIC), "tile"):
                        break
                if hits:
                    break
            if hits:
                break

    if not hits:
        raise SystemExit("no barcode decoded after full escalation ladder")
    for t in hits:
        if t.startswith("otpauth-migration://"):
            return t
    raise SystemExit("decoded a barcode but not otpauth-migration: %s" % hits[0][:80])


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return

    if argv[0] == "--uri":
        uri = argv[1]
    else:
        uri = decode_image(argv[0])

    accounts = decode_uri(uri)
    emit_json = "--json" in argv

    for i, a in enumerate(accounts):
        print("=== account %d ===" % i)
        for k in ("name", "issuer", "secret", "algo", "digits", "type"):
            print("  %-7s: %s" % (k, a[k]))
        try:
            import pyotp
            print("  code   : %s  (valid ~%ds)" % (
                pyotp.TOTP(a["secret"]).now(), 30 - int(time.time()) % 30))
        except ImportError:
            print("  code   : (pip install pyotp to generate)")

    if emit_json:
        payload = accounts[0] if len(accounts) == 1 else accounts
        with open("totp.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print("\nwrote totp.json")


if __name__ == "__main__":
    main()
