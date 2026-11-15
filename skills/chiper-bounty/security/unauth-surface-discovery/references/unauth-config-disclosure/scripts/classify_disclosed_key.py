#!/usr/bin/env python3
"""Classify a disclosed provider credential honestly, with a negative control.

Why this exists
---------------
A leaked key is only half a finding, and it is very easy to get the classification WRONG in both
directions:
  * claiming "live credential, restriction bypassable" for a string the provider does not even
    recognise, and
  * claiming "masked / inert" because you re-tested a value that your own runtime had REDACTED
    in the tool output (a 39-char `AIzaSy...` key rendered as `AIzaSy...PRgQ` looks exactly like
    a product-side placeholder).

The fix for both is the same: read the value PROGRAMMATICALLY from the saved evidence file, print
only length + hash, and probe a well-formed-but-invented CONTROL key in the same run. Only the
negative control makes the verdict auditable.

Usage
-----
    # a) pull keys straight out of a saved raw response / evidence file
    python classify_disclosed_key.py --evidence settings_full/*.json \
                                     --json-key googleDrivePickerConfig --sub-key devKey

    # b) classify literal values (kept short so they are visibly not the full secret)
    python classify_disclosed_key.py --value AIzaSy...AAA

    # c) emit machine-readable output for a report table
    python classify_disclosed_key.py --evidence raw/ --json-key dropboxPickerConfig \
                                     --sub-key appId --json-out verdicts.json

Never pass a secret on the command line if you can read it from disk instead; argv leaks into
shell history and process listings.

Interpretation (Google API keys, `drive/v3/files?key=<value>`)
-------------------------------------------------------------
    400 INVALID_ARGUMENT "API key not valid."            -> not a usable credential
    403 ... "Requests from referer <empty> are blocked."  -> REAL key, provider resolved it and
                                                             applied its restriction
    403 ... project/permission error after setting an
        accepted Referer                                  -> real key AND the Referer gate is
                                                             satisfiable by the caller
    403 "API has not been used in project <N> ..."        -> real key, that API is disabled on
                                                             the project (the message names it)

The control is the load-bearing part: an UNKNOWN key yields 400 INVALID_ARGUMENT, a REAL key
yields a 403 referer/permission error. Identical output for control and candidate means the
candidate is not a usable credential no matter how much it looks like one.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import time
import urllib3

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("needs requests:  pip install requests")

urllib3.disable_warnings()

DRIVE = "https://www.googleapis.com/drive/v3/files"
# referers worth trying; the first is deliberately a plausible-looking one for the target
DEFAULT_REFERERS = [None, "https://example.com/"]


def shape(value: str) -> str:
    """A printable, non-reversible fingerprint of a secret: prefix + length + hash."""
    if not isinstance(value, str) or not value:
        return "<empty>"
    return f"{value[:6]}...(len {len(value)}, sha256 {hashlib.sha256(value.encode()).hexdigest()[:12]})"


def walk_json(obj, sub_key):
    """Yield every value found under <sub_key>, including inside JSON-encoded strings."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == sub_key and isinstance(v, str):
                yield v
            yield from walk_json(v, sub_key)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_json(item, sub_key)
    elif isinstance(obj, str):
        s = obj.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                yield from walk_json(json.loads(s), sub_key)
            except Exception:
                pass


def collect_from_evidence(paths, json_key, sub_key):
    """Return {host_or_file: secret} read from disk. The secret is never printed by this tool."""
    found = {}
    files = []
    for p in paths:
        if os.path.isdir(p):
            files.extend(sorted(glob.glob(os.path.join(p, "**", "*.json"), recursive=True)))
        else:
            files.extend(sorted(glob.glob(p)))
    for f in files:
        try:
            obj = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        candidates = []
        if json_key:
            v = obj.get(json_key) if isinstance(obj, dict) else None
            if isinstance(v, str):
                try:
                    candidates.extend(walk_json(json.loads(v), sub_key))
                except Exception:
                    candidates.append(v)
        if not candidates and sub_key:
            candidates.extend(walk_json(obj, sub_key))
        for c in candidates:
            if c:
                found.setdefault(c, os.path.basename(f))
    return found


def probe(key, referer, timeout=20):
    headers = {"Referer": referer} if referer else {}
    try:
        r = requests.get(DRIVE, params={"key": key, "pageSize": 1}, headers=headers,
                         timeout=timeout, verify=False)
        try:
            e = r.json().get("error", {})
            msg = f"{e.get('status') or ''}: {(e.get('message') or '')[:110]}".strip(": ")
        except Exception:
            msg = r.text[:110].replace("\n", " ")
        return r.status_code, msg
    except Exception as exc:
        return "ERR", str(exc)[:90]


def classify(status, msg):
    low = (msg or "").lower()
    if "api key not valid" in low:
        return "INVALID"
    if "referer" in low and "blocked" in low:
        return "REAL_KEY_REFERER_BLOCKED"
    if "has not been used in project" in low or "is disabled" in low:
        return "REAL_KEY_API_DISABLED"
    if status == 403:
        return "REAL_KEY_GATE_PASSED"
    return "UNCLEAR"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", nargs="*", default=[],
                    help="files/dirs/globs to read the candidate secret from (preferred)")
    ap.add_argument("--json-key", default=None,
                    help="top-level field holding the secret or a JSON string containing it")
    ap.add_argument("--sub-key", default="devKey",
                    help="field name to search for recursively (default: devKey)")
    ap.add_argument("--value", nargs="*", default=[],
                    help="literal candidate values (avoid; argv leaks)")
    ap.add_argument("--control", default="AIzaSy" + "A" * 33,
                    help="well-formed but invented control key (default: AIzaSy+33xA)")
    ap.add_argument("--referer", nargs="*", default=DEFAULT_REFERERS,
                    help="referer values to try; pass an empty string for 'no referer'")
    ap.add_argument("--json-out", default=None, help="write verdicts to this JSON file")
    args = ap.parse_args()

    candidates = collect_from_evidence(args.evidence, args.json_key, args.sub_key)
    for v in args.value:
        candidates.setdefault(v, "<argv>")
    if not candidates:
        sys.exit("no candidate secrets found -- check --evidence/--json-key/--sub-key")

    print(f"candidates found: {len(candidates)}  (values shown as prefix+length+hash only)")
    for v, src in candidates.items():
        print(f"   {shape(v)}   from {src}")
    print()

    results = []
    # the control runs first so its baseline is visible next to every real verdict
    todo = [("CONTROL (invented, well-formed)", args.control, "<control>")]
    todo += [(shape(v), v, src) for v, src in candidates.items()]

    for label, key, src in todo:
        for ref in args.referer:
            ref_display = ref if ref else "<none>"
            status, msg = probe(key, ref or None)
            verdict = classify(status, msg)
            print(f"  {label:44s} referer={ref_display:28s} -> {status} {verdict:24s} {msg}")
            results.append({"label": label, "source": src, "referer": ref_display,
                            "status": status, "verdict": verdict, "message": msg})
            time.sleep(1.0)
        print()

    real = [r for r in results if r["label"] != "CONTROL (invented, well-formed)"
            and r["verdict"] != "INVALID"]
    print("=" * 72)
    print(f"usable credentials: {len({r['label'] for r in real})} of {len(candidates)}")
    print("Report line to use: state how many are real, name the API enabled on the project if the")
    print("provider said so, and state plainly what you could NOT reach (no data / no quota spend).")
    if args.json_out:
        json.dump(results, open(args.json_out, "w", encoding="utf-8"), indent=1)
        print("verdicts ->", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
