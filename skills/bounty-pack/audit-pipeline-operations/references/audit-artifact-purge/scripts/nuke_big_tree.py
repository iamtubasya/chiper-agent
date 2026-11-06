# -*- coding: utf-8 -*-
"""Reliable deletion of large/locked Windows trees for an audit purge.

Why this exists (2026-10-04, measured): on a 52-item purge, `shutil.rmtree` / `rm -rf` /
a per-file os.remove loop HUNG indefinitely on node_modules/repo-shaped dirs, and a
detached Popen(DETACHED_PROCESS) never ran. The mirror-empty-with-robocopy -> rmdir path
cleared all 52 items, 0 failures.

Usage (import):
    from nuke_big_tree import nuke, rmfile
    nuke(r"D:\\data hermes\\bug-bounty\\_progress\\<target>")

Usage (CLI):
    python nuke_big_tree.py "D:\\path\\to\\dir" ["D:\\path2" ...]

Run it from a script that the terminal drives with background=true, notify=true -- never
foreground (a foreground run hits the tool timeout mid-purge and leaves a half-state).
Always print one OK/FAIL line per item so a re-run can be idempotent.
"""
import os, sys, time, shutil, subprocess, tempfile

# robocopy exit codes 0-7 are SUCCESS (bitmask of what it copied); >=8 is a real error.
_ROBO_OK = set(range(0, 8))


def _proc(cmd, timeout):
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        return None


def nuke(path, per_step_timeout=240):
    """Delete a dir tree reliably. Returns True if the path is gone afterwards."""
    if not os.path.exists(path):
        return True
    w = os.path.abspath(path).replace("/", "\\")

    # 1) mirror an empty dir over the target (fast bulk delete on Windows)
    empty = tempfile.mkdtemp(prefix="nuke_empty_")
    try:
        _proc(["robocopy", empty, w, "/MIR", "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS",
               "/R:0", "/W:0"], per_step_timeout)
    finally:
        shutil.rmtree(empty, ignore_errors=True)

    # 2) remove the now-empty shell
    if os.path.exists(path):
        _proc(["cmd", "/c", "rmdir", "/s", "/q", w], per_step_timeout)

    # 3) last resort: python
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    return not os.path.exists(path)


def rmfile(path):
    """Delete one file, falling back to native del (handles read-only/locked)."""
    if not os.path.exists(path):
        return True
    try:
        os.remove(path)
    except OSError:
        _proc(["cmd", "/c", "del", "/f", "/q", os.path.abspath(path).replace("/", "\\")], 60)
    return not os.path.exists(path)


def purge(items):
    """items: iterable of (path, label). Prints OK/FAIL/SKIP; returns (ok, fail, skip)."""
    ok = fail = skip = 0
    for p, label in items:
        if not os.path.exists(p):
            print("SKIP(gone) " + label); skip += 1; continue
        good = nuke(p) if os.path.isdir(p) else rmfile(p)
        print(("OK   " if good else "FAIL ") + label)
        ok += good
        fail += (not good)
    print("=== DONE ok=%d fail=%d skip=%d ===" % (ok, fail, skip))
    return ok, fail, skip


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: nuke_big_tree.py <path> [path ...]")
    start = time.time()
    purge([(a, a) for a in args])
    print("elapsed %.1fs" % (time.time() - start))
