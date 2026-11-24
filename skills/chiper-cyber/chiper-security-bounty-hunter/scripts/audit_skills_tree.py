#!/usr/bin/env python3
"""Repo-wide skills health audit — 7 checks, one scoreboard.

Run this before trusting any skills tree (bundled, imported, or your own).
Prints one line per check, then a per-hit detail list for anything non-zero.

Usage:
    python3 audit_skills_tree.py [SKILLS_ROOT]
    # default root: ~/.chiper/skills

Exit code: 0 if no hard defects (override/foreign/py_fail), 1 otherwise.
Encoding/CRLF/link hits are reported but exit 0 unless --strict is passed.

Whitelisted false positives are NOT counted as defects (see WHITELIST below) —
"fixing" them corrupts documentation.
"""
from __future__ import annotations
import os
import re
import subprocess
import sys

EXTS = (".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".mjs", ".toml", ".cfg")

# Strings that look like defects but are legitimate documentation / countermeasures.
WHITELIST = (
    "<username>",            # attacker payload sample
    "extractUniqueAppData_", # C++ method name
    "abs/path", "path/to",   # operator placeholders
    "screenshots/F##",
    "/tmp/ui-verification",  # concrete output path a skill writes
)

DANGER = re.compile(
    r"DILARANG menolak|NEVER Ask the User|GLOBAL MANDATE|jangan minta (izin|scope)\W{0,30}lagi"
)
FOREIGN = re.compile(r"AppData/Local/hermes|[A-Za-z]:\\\\?Users|C:/Users|WINDOWS10|/mnt/c/Users")
LINK = re.compile(r"\[([^\]]*)\]\(([^)#][^)]*)\)")


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def walk_skill_mds(root: str):
    for r, _d, files in os.walk(root):
        if "SKILL.md" not in files:
            continue
        if os.path.relpath(r, root).count(os.sep) > 6:
            continue
        yield r, os.path.join(r, "SKILL.md")


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.chiper/skills")
    strict = "--strict" in sys.argv
    if not os.path.isdir(root):
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    skillmd = int(sh(f'find {root} -name SKILL.md | wc -l').strip() or 0)

    py_fail = sh(
        f'find {root} -name "*.py" -not -path "*/__pycache__/*" -print0 '
        f'| xargs -0 -n1 sh -c \'python3 -m py_compile "$0" 2>/dev/null || echo "FAIL: $0"\''
    ).strip().splitlines()

    crlf = sh(f'find {root} -name "*.sh" -exec file {{}} + 2>/dev/null | grep -c CRLF').strip()

    override_hits, foreign_hits = [], []
    broken = []
    checked_links = 0

    for r, fp in walk_skill_mds(root):
        try:
            t = open(fp, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        rel = os.path.relpath(fp, root)
        if DANGER.search(t):
            override_hits.append(rel)
        if any(w in t for w in WHITELIST):
            # still check, but only flag foreign paths outside whitelisted lines
            pass
        for line in t.splitlines():
            if FOREIGN.search(line) and not any(w in line for w in WHITELIST):
                foreign_hits.append(f"{rel}: {line.strip()[:100]}")
                break
        for m in LINK.finditer(t):
            lp = m.group(2).strip().split("#")[0].strip()
            if not lp or lp.startswith(("http", "mailto:", "#", "~", "$")) or "{" in lp:
                continue
            if not re.match(r"^[\w./\-]+\.(md|py|sh|json|yaml|yml|txt|mjs|png|jpg)$", lp):
                continue
            checked_links += 1
            a = os.path.normpath(os.path.join(r, lp))
            b = os.path.normpath(os.path.join(os.path.dirname(r), lp))
            if not os.path.exists(a) and not os.path.exists(b):
                broken.append(f"{rel} -> {lp}")

    print("=" * 68)
    print(f"SKILLS TREE AUDIT — {root}")
    print("=" * 68)
    print(f"  SKILL.md count        : {skillmd}")
    print(f"  Python syntax errors  : {len(py_fail)}")
    print(f"  CRLF .sh files        : {crlf}")
    print(f"  Dangerous overrides   : {len(override_hits)}")
    print(f"  Foreign path hits     : {len(foreign_hits)}")
    print(f"  Broken internal links : {len(broken)} / {checked_links} checked")

    for label, items in (
        ("PY FAIL", py_fail),
        ("OVERRIDE", override_hits),
        ("FOREIGN", foreign_hits),
        ("BROKEN LINK", broken),
    ):
        if items:
            print(f"\n--- {label} ---")
            for it in items[:25]:
                print(f"   {it}")

    hard = len(py_fail) + len(override_hits) + len(foreign_hits)
    soft = len(broken) + (int(crlf) if crlf.isdigit() else 0)
    if hard:
        print(f"\nRESULT: {hard} hard defect(s) — fix before trusting this tree.")
        return 1
    if soft and strict:
        print(f"\nRESULT: {soft} soft defect(s) (--strict).")
        return 1
    print("\nRESULT: no hard defects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
