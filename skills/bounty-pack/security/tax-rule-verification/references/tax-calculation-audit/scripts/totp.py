#!/usr/bin/env python3
"""RFC-6238 TOTP from a base32 secret — no dependencies.

Useful when an audit account gates login, API-key minting or password change behind an
authenticator code and the operator hands over the base32 secret instead of a live code.
Reproduces pyotp exactly; compare the two once before relying on it.

    python totp.py G4YOUY2T3V34PBYOQ6NBPFRP6JHTLCYY
    python totp.py <secret> --at 2026-10-08T12:00:00Z   # deterministic check
    python totp.py <secret> --watch                     # print each new code as it rolls
"""
import argparse, base64, hashlib, hmac, struct, sys, time


def totp(secret: str, at: float | None = None, digits: int = 6, period: int = 30, algo=hashlib.sha1) -> str:
    key = base64.b32decode(secret.upper().replace(" ", ""))
    counter = int((at if at is not None else time.time()) // period)
    digest = hmac.new(key, struct.pack(">Q", counter), algo).digest()
    offset = digest[-1] % 16
    value = struct.unpack(">I", digest[offset:offset + 4])[0] % 2147483648
    return str(value % (10 ** digits)).zfill(digits)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("secret", help="base32 TOTP secret")
    ap.add_argument("--at", help="ISO-8601 UTC timestamp for a deterministic code")
    ap.add_argument("--watch", action="store_true", help="emit a new code each period")
    args = ap.parse_args()

    if args.at:
        import datetime
        t = datetime.datetime.fromisoformat(args.at.replace("Z", "+00:00")).timestamp()
        print(totp(args.secret, t))
        return 0
    if args.watch:
        last = None
        while True:
            code = totp(args.secret)
            if code != last:
                print(code, "(%ds left)" % (30 - int(time.time() % 30)), flush=True)
                last = code
            time.sleep(1)
    print(totp(args.secret))
    return 0


if __name__ == "__main__":
    sys.exit(main())
