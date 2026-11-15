#!/usr/bin/env python3
"""Decode a TOTP enrolment QR -> base32 shared secret (+ a live code).

Why this exists: when a target enforces TOTP (Google/Microsoft Authenticator,
Keycloak required actions, Authy) and the operator enrols the test account, you
are handed a *QR image*. Asking the operator for a fresh 6-digit code on every
re-auth does not scale: codes expire in 30 s, the browser flow has several
stages, and a hunting session needs dozens of logins. Decode the QR once, keep
the secret, generate codes locally forever.

Usage
-----
    python decode_totp_qr.py <image>                 # print secret + live code
    python decode_totp_qr.py <image> --json out.json # persist for the session
    python decode_totp_qr.py <image> --json out.json --quiet

Handles both URI shapes that appear in enrolment QRs:

    otpauth-migration://offline?data=<b64 protobuf>
        Google Authenticator multi-account export (the common one).
    otpauth://totp/<issuer>:<acct>?secret=...&digits=6&period=30&algorithm=SHA1
        Single account, produced by most other apps.

Requires: opencv-python, zxingcpp, pyotp
    (pip install opencv-python zxingcpp pyotp)

Exit codes: 0 ok, 1 no QR found, 2 QR found but parse failed.
"""

import argparse
import base64
import json
import sys
import time
import urllib.parse

# ---------------------------------------------------------------- QR decoding

def _read_qr(path):
    """Return the first decoded payload string, or None.

    Ladder matters. A phone screenshot of a QR often fails the raw pass and
    succeeds after an integer nearest-neighbour upscale (module edges stay
    crisp) -- whereas INTER_CUBIC smooths them and can make zxing fail. Order:
    raw -> nearest x2/x3/x4 -> grayscale+otsu -> invert (dark-mode screenshots).
    """
    import cv2
    import zxingcpp

    img = cv2.imread(path)
    if img is None:
        raise SystemExit("cannot read image: %s" % path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    attempts = [("raw", gray)]

    for s in (2, 3, 4):
        attempts.append(
            ("nearest x%d" % s,
             cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST))
        )

    try:
        _, otsu = cv2.threshold(gray, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        attempts.append(("otsu", otsu))
        attempts.append(
            ("otsu x3",
             cv2.resize(otsu, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))
        )
    except Exception:
        pass

    attempts.append(("invert", cv2.bitwise_not(gray)))

    for label, im in attempts:
        results = zxingcpp.read_barcodes(im)
        for r in results:
            txt = (r.text or "").strip()
            if txt.startswith("otpauth://"):
                print("[qr] decoded via %s" % label, file=sys.stderr)
                return txt

    # Some cameras/drivers hand back the payload with stray whitespace or as a
    # non-otpauth QR (e.g. a setup link that redirects). Surface anything found.
    for label, im in attempts:
        results = zxingcpp.read_barcodes(im)
        if results:
            txt = (results[0].text or "").strip()
            print("[qr] non-otpauth payload via %s: %r" % (label, txt[:120]),
                  file=sys.stderr)
            return txt
    return None


# ------------------------------------------------------------- protobuf parse
# otpauth-migration payload (Google Authenticator Export format) is a bare
# protobuf with no schema file. Field map, verified against real exports:
#
#   MigrationPayload
#     1  repeated OtpParameters  otp_parameters
#     2  int32  version
#     3  int32  batch_size
#     4  int32  batch_index
#     5  int32  batch_id
#
#   OtpParameters
#     1  bytes  secret      <-- the shared secret (raw, NOT base32)
#     2  string name        "issuer:account"
#     3  string issuer
#     4  enum   algorithm   0=unspecified 1=SHA1 2=SHA256 3=SHA512 4=MD5
#     5  enum   digits      0=unspecified 1=6 2=8
#     6  enum   type        0=unspecified 1=HOTP 2=TOTP
#     7  int32  counter     (HOTP only)

def _varint(buf, i):
    shift = 0
    val = 0
    while True:
        if i >= len(buf):
            raise ValueError("truncated varint")
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, i
        shift += 7


def _parse_fields(buf):
    """Minimal protobuf wire-format walker -> list[(field_no, wire_type, value)]."""
    out = []
    i = 0
    while i < len(buf):
        key, i = _varint(buf, i)
        field, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(buf, i)
            out.append((field, wt, v))
        elif wt == 2:
            ln, i = _varint(buf, i)
            out.append((field, wt, buf[i:i + ln]))
            i += ln
        elif wt == 5:
            out.append((field, wt, buf[i:i + 4]))
            i += 4
        elif wt == 1:
            out.append((field, wt, buf[i:i + 8]))
            i += 8
        else:
            raise ValueError("unsupported wire type %d" % wt)
    return out


ALG = {0: "SHA1", 1: "SHA1", 2: "SHA256", 3: "SHA512", 4: "MD5"}
DIGITS = {0: 6, 1: 6, 2: 8}
TYPE = {0: "TOTP", 1: "HOTP", 2: "TOTP"}


def _parse_migration(data_b64):
    raw = base64.b64decode(data_b64 + "=" * (-len(data_b64) % 4))
    accounts = []
    for field, wt, val in _parse_fields(raw):
        if field != 1 or wt != 2:
            continue
        d = {}
        for f, w, v in _parse_fields(val):
            d.setdefault(f, []).append(v)
        secret_raw = d.get(1, [b""])[0]
        if not secret_raw:
            continue
        accounts.append({
            "name": d.get(2, [b""])[0].decode("utf-8", "replace"),
            "issuer": d.get(3, [b""])[0].decode("utf-8", "replace"),
            "secret": base64.b32encode(secret_raw).decode().rstrip("="),
            "algorithm": ALG.get(d.get(4, [0])[0], "SHA1"),
            "digits": DIGITS.get(d.get(5, [0])[0], 6),
            "type": TYPE.get(d.get(6, [0])[0], "TOTP"),
            "counter": d.get(7, [0])[0],
        })
    return accounts


def _parse_otpauth(uri):
    """otpauth://totp/Issuer:acct?secret=... -> one account dict."""
    p = urllib.parse.urlparse(uri)
    q = urllib.parse.parse_qs(p.query)
    label = urllib.parse.unquote(p.path.lstrip("/"))
    issuer = (q.get("issuer", [""])[0]
              or (label.split(":", 1)[0] if ":" in label else ""))
    sec = q.get("secret", [""])[0].strip()
    if not sec:
        raise ValueError("otpauth URI has no secret parameter")
    return [{
        "name": label,
        "issuer": issuer,
        "secret": sec.upper().replace(" ", ""),
        "algorithm": (q.get("algorithm", ["SHA1"])[0] or "SHA1").upper(),
        "digits": int(q.get("digits", ["6"])[0] or 6),
        "type": (p.netloc or "totp").upper().replace("OTP", "OTP"),
        "counter": int(q.get("counter", ["0"])[0] or 0),
    }]


def decode_uri(uri):
    if uri.startswith("otpauth-migration://"):
        data = urllib.parse.parse_qs(
            urllib.parse.urlparse(uri).query).get("data", [""])[0]
        if not data:
            raise ValueError("migration URI with no data= parameter")
        return _parse_migration(data)
    if uri.startswith("otpauth://"):
        return _parse_otpauth(uri)
    raise ValueError("not an otpauth URI: %r" % uri[:80])


# -------------------------------------------------------------------- totp
def live_code(secret, digits=6, period=30, algorithm="SHA1"):
    import hashlib
    import pyotp
    digest = {
        "SHA1": hashlib.sha1,
        "SHA256": hashlib.sha256,
        "SHA512": hashlib.sha512,
    }.get(algorithm.upper(), hashlib.sha1)
    totp = pyotp.TOTP(secret, digits=digits, interval=period, digest=digest)
    return totp.now()


def remaining(period=30):
    return period - int(time.time()) % period


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--json", help="persist the first account to this JSON file")
    ap.add_argument("--index", type=int, default=0,
                    help="which account to persist when the QR holds several")
    ap.add_argument("--quiet", action="store_true", help="suppress the report")
    a = ap.parse_args()

    uri = _read_qr(a.image)
    if not uri:
        print("no QR found in %s" % a.image, file=sys.stderr)
        return 1

    try:
        accounts = decode_uri(uri)
    except Exception as e:
        print("QR found but parse failed: %s" % e, file=sys.stderr)
        print("payload: %r" % uri[:200], file=sys.stderr)
        return 2

    if not accounts:
        print("payload parsed but contained no accounts", file=sys.stderr)
        return 2

    if not a.quiet:
        for n, acc in enumerate(accounts):
            print("account[%d]" % n)
            print("  name      : %s" % acc["name"])
            print("  issuer    : %s" % acc["issuer"])
            print("  secret    : %s   (len=%d)" % (acc["secret"], len(acc["secret"])))
            print("  algorithm : %s" % acc["algorithm"])
            print("  digits    : %s" % acc["digits"])
            print("  type      : %s" % acc["type"])
            if acc["type"] == "TOTP":
                try:
                    print("  live code : %s   (%ds left)"
                          % (live_code(acc["secret"], acc["digits"],
                                       algorithm=acc["algorithm"]),
                             remaining()))
                except Exception as e:
                    print("  live code : <pyotp error: %s>" % e)

    if a.json:
        acc = accounts[min(a.index, len(accounts) - 1)]
        payload = dict(acc, period=30,
                       note="local TOTP for authorised test account; "
                            "never commit or share")
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        if not a.quiet:
            print("\npersisted -> %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
