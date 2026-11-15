#!/usr/bin/env python3
"""grep_assemblies.py — attribute a behaviour to a class by grepping a directory of binaries.

Use when auditing a SHIPPED, CLOSED-SOURCE component (self-hosted product, container image, agent
installer) and you know the name of the class/type that produces the behaviour you reproduced.

Why this beats decompiling: a .NET/Java/Go binary carries its own type and method names as plain
strings. A single pass tells you WHICH assembly implements the control, which is exactly what a
bug-bounty report needs to name the affected product ("the same masking classes ship in
Octopus.Core.dll, Octopus.Shared.dll AND Octopus.Server.dll").

Example
-------
    python grep_assemblies.py ./server-bin/Octopus \
        SensitiveValueMasker SensitiveDataMask AhoCorasick SafeSanitize

    SensitiveValueMasker  -> Octopus.Core.dll, Octopus.Shared.dll, Octopus.Server.dll
    SensitiveDataMask     -> Octopus.Core.dll, Octopus.Shared.dll
    AhoCorasick           -> Octopus.Shared.dll
    SafeSanitize          -> Octopus.Shared.dll

Then fetch the matching public source (if the component is open) and read the exact rule that
explains the reproduced behaviour.

Notes
-----
* Length-prefixed (Go/Rust) and UTF-16 (JavaScript/minified) strings are still found because we
  search the raw bytes, not decoded strings — but a hit on a very common word can be a false
  positive. Confirm by checking the hit sits in a plausible assembly name.
* Reads files in chunks, so it is safe on multi-GB directories; skips files above --max-mb.
* On Windows, pass a native path (C:\\... or D:/...) — an MSYS path is fine too.

Options
-------
    --ext .dll,.exe,.so   only these suffixes (default: .dll,.exe,.so,.dylib,.jar,.war,.node,.pyc)
    --max-mb N            skip files larger than N MB (default 400)
    --any                 OR semantics: report files matching ANY needle (default: report per needle)
"""

from __future__ import annotations

import argparse
import os
import sys

DEFAULT_EXT = {".dll", ".exe", ".so", ".dylib", ".jar", ".war", ".node", ".pyc"}
CHUNK = 1 << 22  # 4 MB
OVERLAP = 4096  # so a needle straddling a chunk boundary is still found


def iter_files(root: str, exts: set[str], max_bytes: int):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if exts and ext not in exts:
                continue
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > max_bytes:
                    continue
            except OSError:
                continue
            yield path


def scan(path: str, needles: list[bytes]) -> set[bytes]:
    """Return the subset of needles present in the file."""
    remaining = set(needles)
    tail = b""
    try:
        with open(path, "rb") as fh:
            while remaining:
                chunk = fh.read(CHUNK)
                if not chunk:
                    break
                hay = tail + chunk
                for n in list(remaining):
                    if n in hay:
                        remaining.discard(n)
                tail = hay[-OVERLAP:]
    except OSError as exc:
        print(f"  ! cannot read {path}: {exc}", file=sys.stderr)
        return set()
    return set(needles) - remaining


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="directory or single file to search")
    ap.add_argument("needles", nargs="+", help="class/type/method names to look for")
    ap.add_argument("--ext", default=None, help="comma-separated suffixes to include")
    ap.add_argument("--max-mb", type=int, default=400, help="skip files larger than this (MB)")
    ap.add_argument("--any", action="store_true", help="report files matching any needle instead of per needle")
    ap.add_argument("--quiet", action="store_true", help="only print the summary table")
    args = ap.parse_args()

    exts = set()
    if args.ext is None:
        exts = DEFAULT_EXT
    else:
        for e in args.ext.split(","):
            e = e.strip().lower()
            if e:
                exts.add(e if e.startswith(".") else "." + e)

    needles = [n.encode() for n in args.needles]
    max_bytes = args.max_mb * 1024 * 1024

    hits: dict[bytes, list[str]] = {n: [] for n in needles}
    any_hits: list[str] = []
    scanned = 0

    for path in iter_files(args.root, exts, max_bytes):
        scanned += 1
        found = scan(path, needles)
        if not found:
            continue
        name = os.path.basename(path)
        if args.any:
            any_hits.append(name)
            if not args.quiet:
                print(f"{name}: {sorted(n.decode() for n in found)}")
            continue
        for n in found:
            hits[n].append(name)

    print()
    if args.any:
        print(f"scanned {scanned} files; {len(any_hits)} matched")
        for n in sorted(any_hits):
            print("  ", n)
    else:
        print(f"scanned {scanned} files under {args.root}")
        for n in needles:
            files = sorted(hits[n])
            print(f"  {n.decode():<28} -> {', '.join(files) if files else '(not found)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
