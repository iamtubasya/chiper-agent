#!/usr/bin/env python3
"""Roll a purge back OUT of quarantine — the over-capture repair tool.

Why this exists: a pattern sweep over a home directory ALWAYS over-captures.
Knowledge scrapes (PortSwigger lab HTML, cheat-sheet dumps), wordlists, taxonomy
JSON, program-research data and game-automation screenshots share prefixes with
engagement output and get swept with it. Never hand-move files back; this script
decodes the quarantine's flattened naming and restores exactly what you list.

Quarantine naming written by the purge passes:
    /home/agentuser/ps3_logic-flaws-idor.html
      -> <Q>/c__Users__WINDOWS10__ps3_logic-flaws-idor.html
    D:/data hermes/mail-com-audit
      -> <Q>/d__data hermes__mail-com-audit
Note: the drive letter is lowercased and the ':' is dropped by shutil.move, and
directory separators become '__'. On Windows filenames are case-insensitive, so
the on-disk name may be 'C__Users__...' — always match case-insensitively.

Usage:
    # 1. show what a restore WOULD take back (no writes)
    python quarantine_restore.py <QDIR> --list ps3_ ps4_ wb_ bl_ defillama_ ld_

    # 2. actually restore those prefixes
    python quarantine_restore.py <QDIR> --restore ps3_ ps4_ wb_ bl_ defillama_ ld_

    # 3. restore exact basenames instead of prefixes
    python quarantine_restore.py <QDIR> --restore-exact nuclei-index.json vrt.json

    # 4. multiple quarantine dirs at once (one pass per generation)
    python quarantine_restore.py Q1 Q2 Q3 --restore ps3_

Safety:
  * never overwrites — an existing original path is reported EXISTS and skipped
  * refuses to move a DIRECTORY back (prefix rules are for loose files); a dir
    restore is a deliberate manual decision, see --restore-dir
  * writes a RESTORED| line per item to $LOCALAPPDATA/Temp/audit-purge-restore-<ts>.txt
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time

TEMP = os.environ.get("LOCALAPPDATA") or os.environ.get("TMPDIR") or "/tmp"


def decode(flat: str) -> str | None:
    """c__Users__WINDOWS10__ps3_x.html -> /home/agentuser/ps3_x.html"""
    parts = flat.split("__")
    if len(parts) < 2:
        return None
    drive, rest = parts[0], "/".join(parts[1:])
    if len(drive) == 1 and drive.isalpha():
        return f"{drive.upper()}:/{rest}"
    return None


def build_index(qdir: str) -> list[tuple[str, str]]:
    rows = []
    for name in sorted(os.listdir(qdir)):
        src = os.path.join(qdir, name)
        rows.append((name, src))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("qdirs", nargs="+", help="quarantine dir(s)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", nargs="+", metavar="PREFIX",
                      help="show matches by basename prefix (no writes)")
    mode.add_argument("--restore", nargs="+", metavar="PREFIX",
                      help="restore matches by basename prefix")
    mode.add_argument("--restore-exact", nargs="+", metavar="NAME",
                      help="restore exact basenames")
    mode.add_argument("--list-exact", nargs="+", metavar="NAME",
                      help="show exact-basename matches (no writes)")
    ap.add_argument("--restore-dir", action="store_true",
                    help="also move matching DIRECTORIES back (default: skip)")
    args = ap.parse_args()

    prefixes = [p.lower() for p in (args.list or args.restore or [])]
    exacts = [n.lower() for n in (args.restore_exact or args.list_exact or [])]
    write = bool(args.restore or args.restore_exact)

    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(TEMP, f"audit-purge-restore-{ts}.txt")
    log = open(log_path, "w", encoding="utf-8") if write else None

    restored = skipped = failed = 0
    for qdir in args.qdirs:
        if not os.path.isdir(qdir):
            print(f"! not a dir: {qdir}")
            continue
        for flat, src in build_index(qdir):
            base = flat.split("__")[-1].lower()
            hit_exact = base in exacts
            hit_prefix = any(base.startswith(p) for p in prefixes)
            if not (hit_exact or hit_prefix):
                continue
            is_dir = os.path.isdir(src)
            if is_dir and not args.restore_dir:
                if not write:
                    print(f"DIR?(skip) {flat}")
                skipped += 1
                continue
            orig = decode(flat)
            if not orig:
                print(f"? cannot decode: {flat}")
                failed += 1
                continue
            if not write:
                print(f"would restore {orig}")
                restored += 1
                continue
            if os.path.exists(orig):
                log.write(f"EXISTS|{orig}\n")
                skipped += 1
                continue
            try:
                os.makedirs(os.path.dirname(orig), exist_ok=True)
                shutil.move(src, orig)
                log.write(f"RESTORED|{orig}\n")
                restored += 1
            except Exception as exc:  # noqa: BLE001
                log.write(f"FAIL|{orig}|{type(exc).__name__}:{exc}\n")
                failed += 1

    if log:
        log.write(f"# restored={restored} skipped={skipped} failed={failed}\n")
        log.close()
        print(f"\nrestored={restored} skipped={skipped} failed={failed}")
        print(f"log={log_path}")
    else:
        print(f"\n(dry run) would_restore={restored} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
