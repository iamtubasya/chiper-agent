#!/usr/bin/env python3
"""Bugcrowd VRT lookup helper.

Fetches the official VRT taxonomy and prints either a named category subtree
(e.g. "broken access control") or a keyword search across all nodes.

Usage:
  python lookup_vrt.py tree "broken access control"
  python lookup_vrt.py search "privilege escalation"
  python lookup_vrt.py search "iterable"

Notes:
  - VRT JSON top key is `content` (a LIST), not `image`.
  - Recursion must handle BOTH dict nodes ({name,id,priority,children}) and list wrappers.
"""
import json
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/bugcrowd/vulnerability-rating-taxonomy/master/vulnerability-rating-taxonomy.json"


def walk(node, path=""):
    """Yield (node, full_path) for every node; tolerant of dict and list."""
    if isinstance(node, dict):
        name = node.get("name", "")
        full = (path + " > " + name).strip(" >")
        yield (node, full)
        for c in node.get("children", []) or []:
            yield from walk(c, full)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item, path)


def find_by_name(content, name_lower, exact=True):
    for node, full in walk(content):
        nm = node.get("name", "").lower()
        if (exact and nm == name_lower) or (not exact and name_lower in nm):
            return node, full
    return None, None


def show_tree(node, depth=0):
    print("  " * depth + f"[{node.get('id')}] {node.get('name')} (P{node.get('priority')})")
    for c in node.get("children", []) or []:
        show_tree(c, depth + 1)


def main():
    data = json.loads(urllib.request.urlopen(URL, timeout=30).read())
    content = data.get("content", [])

    if len(sys.argv) < 3:
        print(__doc__)
        return

    cmd, term = sys.argv[1].lower(), sys.argv[2].lower()

    if cmd == "tree":
        node, full = find_by_name(content, term)
        if node:
            print(f"FOUND: {full}")
            print(f"id={node.get('id')} priority={node.get('priority')}\n")
            show_tree(node)
        else:
            print("not found; top-level categories:")
            for n, f in walk(content):
                if ">" not in f:
                    print(" ", f)
    elif cmd == "search":
        for node, full in walk(content):
            if term in node.get("name", "").lower():
                print(f"[{node.get('id')}] {full} (P{node.get('priority')})")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()