#!/usr/bin/env python3
"""Bugcrowd program scope extractor — no login required.

Usage:  python3 bugcrowd_scope_extract.py <engagement-slug>
Example: python3 bugcrowd_scope_extract.py tripadvisor-bb-og

Pulls the full brief (in/out-of-scope host lists, per-tier reward table, program rules, VRT
version) from a Bugcrowd engagement whose page looks login-gated. See
references/bugcrowd-scope-extraction.md for the mechanism.
"""
import json
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; scope-extractor)"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def find_changelog_id(slug):
    html = _get(f"https://bugcrowd.com/engagements/{slug}").decode("utf-8", "replace")
    m = re.search(r"changelog/([0-9a-fA-F-]{36})", html)
    if not m:
        raise SystemExit("changelog id not found — the page shape changed; grep the HTML for "
                         "'getBriefVersionDocument' and read the id from there")
    return m.group(1)


def strip_html(s):
    if not isinstance(s, str):
        return s
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</p>|</li>|</h[1-6]>", "\n", s)
    s = re.sub(r"<li>", "\n - ", s)
    return re.sub(r"<[^>]+>", "", s).strip()


def main(slug):
    cid = find_changelog_id(slug)
    # .json suffix is mandatory — the plain path 404s
    brief = json.loads(_get(f"https://bugcrowd.com/engagements/{slug}/changelog/{cid}.json"))
    data = brief["data"]

    b = data.get("brief", {})
    print("=" * 72)
    print(f"PROGRAM: {b.get('name', slug)}")
    print(f"VRT version: {brief.get('vrtVersion')}")
    print("=" * 72)

    print("\n## SCOPE + REWARD TIERS")
    for grp in data.get("scope", []):
        rr = grp.get("rewardRange") or {}
        tag = "IN " if grp.get("inScope") else "OUT"
        if rr.get("p1MinCents") is not None:
            money = "  P1 ${} P2 ${} P3 ${} P4 ${}".format(
                rr["p1MinCents"] // 100, (rr.get("p2MinCents") or 0) // 100,
                (rr.get("p3MinCents") or 0) // 100, (rr.get("p4MinCents") or 0) // 100)
        else:
            money = ""
        print(f"\n[{tag}] {grp.get('name')}{money}")
        for t in grp.get("targets", []):
            uri = t.get("uri") or t.get("name") or "(blank — see name field)"
            cats = ",".join(x.get("name", "") for x in (t.get("tags") or []))
            print(f"    {uri}   {('('+cats+')') if cats else ''}")

    print("\n## RULES (brief.description)")
    print(strip_html(b.get("description") or "")[:4000])
    print("\n## OUT-OF-SCOPE CLASSES (brief.targetsOverview)")
    print(strip_html(b.get("targetsOverview") or "")[:3000])
    print("\n## ADDITIONAL INFORMATION")
    ai = b.get("additionalInformation")
    print(strip_html(ai) if isinstance(ai, str) else json.dumps(ai, indent=1)[:3000])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: bugcrowd_scope_extract.py <engagement-slug>")
    main(sys.argv[1])
