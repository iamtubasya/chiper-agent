#!/usr/bin/env python3
"""Extract JSON records from a headlessly-dumped Next.js App Router page.

Usage:
    python unwrap_next_flight.py page.html -o records.json
    python unwrap_next_flight.py page.html --probe-only

Pipeline: find self.__next_f.push chunks -> unescape -> join in document order
-> brace-match balanced arrays/objects -> emit the largest array of objects.

Why not regex: the flight payload is chunked at arbitrary offsets and contains
nested/escaped JSON, so greedy patterns silently truncate. We brace-match.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# Console on Windows defaults to cp1252; our output can contain any Unicode.
# Reconfigure BEFORE printing so a finding never crashes on the way out.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def find_chunks(html: str) -> list[str]:
    """Return the raw string arguments of every self.__next_f.push([1,"..."]) call."""
    out: list[str] = []
    needle = "__next_f.push("
    i = 0
    while True:
        i = html.find(needle, i)
        if i == -1:
            return out
        i += len(needle)
        try:
            arr, end = _match_balanced(html, i, "[", "]")
        except ValueError:
            continue
        # arr looks like: [1,"escaped payload"]
        try:
            parsed = json.loads(arr)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list) and len(parsed) >= 2 and isinstance(parsed[1], str):
            out.append(parsed[1])
        i = end


def _match_balanced(text: str, start: int, open_ch: str, close_ch: str) -> tuple[str, int]:
    """Return (substring including delimiters, index just past the closer)."""
    if start >= len(text) or text[start] != open_ch:
        raise ValueError("not at an opening delimiter")
    depth = 0
    in_str = False
    esc = False
    for j in range(start, len(text)):
        ch = text[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : j + 1], j + 1
    raise ValueError("unbalanced")


def join_payload(html: str) -> str:
    """Concatenate all flight chunks in document order."""
    return "".join(find_chunks(html))


def extract_records(payload: str) -> list[dict]:
    """Brace-match every top-level JSON array; return the largest list of dicts."""
    best: list[dict] = []
    i = 0
    while i < len(payload):
        i = payload.find("[", i)
        if i == -1:
            break
        try:
            blob, end = _match_balanced(payload, i, "[", "]")
        except ValueError:
            i += 1
            continue
        i = end
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(data, list)
            and len(data) > len(best)
            and all(isinstance(x, dict) for x in data)
        ):
            best = data
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", help="path to a --dump-dom output file")
    ap.add_argument("-o", "--out", help="write records here as JSON")
    ap.add_argument("--probe-only", action="store_true", help="report counts, write nothing")
    args = ap.parse_args()

    with open(args.html, "r", encoding="utf-8", errors="replace") as fh:
        html = fh.read()

    chunks = find_chunks(html)
    if not chunks:
        print("No __next_f chunks found.")
        print("Not a Next.js App Router page, or the dump was not rendered.")
        print("Try a larger --virtual-time-budget, or probe a JSON endpoint instead.")
        return 1

    payload = join_payload(html)
    records = extract_records(payload)

    print(f"chunks : {len(chunks)}")
    print(f"payload: {len(payload)} chars")
    print(f"records: {len(records)}")

    if not records:
        print("No array of objects matched. Inspect the payload prefixes")
        print("(they look like 'a:{...}', 'b:[...]') before assuming a failure.")
        return 2

    if args.probe_only:
        keys = sorted({k for r in records[:50] for k in r})
        print(f"keys   : {', '.join(keys)}")
        return 0

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
        print(f"wrote  : {args.out}")
    else:
        print(json.dumps(records[0], indent=2, ensure_ascii=False)[:2000])

    print("\nVERIFY before reporting: parsed count vs the total the page states;")
    print("spot-check one record against the rendered page; watch for a hard cap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
