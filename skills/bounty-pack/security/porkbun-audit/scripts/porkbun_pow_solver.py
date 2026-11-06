#!/usr/bin/env python3
"""Porkbun "Pork Captcha V1.3.1" proof-of-work solver (stdlib only).

Issue -> mine (12-bit SHA-256 PoW) -> challenge -> JWT token.
The token goes into the `porkcaptcha-token_accountCreate` form field, or is
sent as `pcaptcharesponse` in POST /api/user/accountCreateCheck.

Usage:  python porkbun_pow_solver.py [--action accountCreate]
"""
import hashlib
import json
import ssl
import sys
import time
import urllib.request

SITEKEY = "805d2807-7ec4-44f5-84c0-f5cb5187d587"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def _json_post(url, obj):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("User-Agent", UA)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
        return json.loads(r.read().decode())


def solve(action="accountCreate", sitekey=SITEKEY):
    issued = _json_post("https://porkbun.com/tools/porkCaptchaIssue", {"sitekey": sitekey})
    challenge, ct, bits = (
        issued["challenge"], issued["challengeToken"], int(issued.get("difficulty", 12))
    )
    full_nibbles, partial_bits = bits // 4, bits % 4
    prefix = "0" * full_nibbles
    extra = 0 if partial_bits == 0 else (1 << (4 - partial_bits))

    nonce, t0 = 0, time.time()
    while True:
        h = hashlib.sha256((challenge + str(nonce)).encode()).hexdigest()
        if h.startswith(prefix) and (extra == 0 or int(h[full_nibbles], 16) < extra):
            break
        nonce += 1

    body = {
        "challengeToken": ct,
        "nonce": str(nonce),
        "fingerprint": "ZmFrZQ==",          # b64(client fingerprint) — forgeable
        "sitekey": sitekey,
        "difficulty": bits,
        "elapsed": int((time.time() - t0) * 1000),
        "action": action,
        "interactionEntropy": 150,
        "botHints": {"webdriver": False, "languages": 1, "plugins": 5,
                     "hardwareConcurrency": 8, "colorDepth": 24, "maxTouchPoints": 0},
        "clickTimestamp": int(time.time() * 1000),
        "clickX": 120, "clickY": 80, "clickDelay": 250,
    }
    resp = _json_post("https://porkbun.com/tools/porkCaptchaChallenge", body)
    return resp.get("token"), {"bits": bits, "nonce": nonce,
                               "ms": int((time.time() - t0) * 1000)}


if __name__ == "__main__":
    action = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--action" else "accountCreate"
    token, meta = solve(action=action)
    if token:
        print(json.dumps({"token": token, "meta": meta}))
    else:
        print("FAILED to obtain token", file=sys.stderr)
        sys.exit(1)