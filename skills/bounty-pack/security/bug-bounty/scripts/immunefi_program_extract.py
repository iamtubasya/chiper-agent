#!/usr/bin/env python3
"""Extract the authoritative Immunefi program record from the page's Next.js flight stream.

Why: the Immunefi bounty page is a client-rendered Next.js app. `curl` returns HTML whose scope
section is empty, and stripping tags yields nav scaffolding only — which historically led to the
wrong conclusion "scope data is unavailable, fall back to web_search". In fact the ENTIRE program
record (reward tiers, asset list with primacy flags, impacts table, the program's known-issues
do-not-report list, KYC, prohibited activities) is shipped inside the `self.__next_f.push` payloads.
Parse those and you get the program's own JSON — the scope gate — before touching the target.

Usage
    curl -sL -A "Mozilla/5.0" \
        "https://immunefi.com/bug-bounty/<SLUG>/information/" -o prog.html
    python3 immunefi_program_extract.py prog.html            # prints a summary
    python3 immunefi_program_extract.py prog.html --json out.json

Notes / pitfalls
  * The page has NO `__NEXT_DATA__` and no `__remixContext`; look for `self.__next_f.push([1,"…")`.
  * Chunks are escaped JSON string literals: parse them as JS string literals (handle `\\` escapes,
    stop at the first unescaped `"`), join, then unescape ONCE.
  * `unicode_escape` is used for the unescape and can replace non-ASCII (em-dashes etc.) with U+FFFD.
    That is fine — every structural character of the JSON is ASCII — but do not use the output for
    prose display.
  * The program object is `{"bounty": {...}}`; brace-match it rather than regexing, because the record
    nests arrays (assets/impacts/bounties/knownIssues).
  * `web_extract` fails outright when the configured backend is search-only (e.g. ddgs, whose error is
    "DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content"). That is a BACKEND
    config issue, not evidence the page is unextractable — this script is backend-independent.
"""
from __future__ import annotations

import json
import sys


def flight_chunks(data: str) -> list[str]:
    """Return the raw (still-escaped) arguments of every self.__next_f.push([1, "…"])."""
    out: list[str] = []
    marker = "self.__next_f.push([1,"
    i = 0
    while True:
        j = data.find(marker, i)
        if j < 0:
            break
        k = j + len(marker)
        while k < len(data) and data[k] in " \t\r\n":
            k += 1
        if k >= len(data) or data[k] != '"':
            i = k
            continue
        k += 1
        buf: list[str] = []
        while k < len(data):
            c = data[k]
            if c == "\\":            # keep the escape pair verbatim
                buf.append(data[k:k + 2])
                k += 2
                continue
            if c == '"':             # unescaped quote terminates the literal
                k += 1
                break
            buf.append(c)
            k += 1
        out.append("".join(buf))
        i = k
    return out


def bounty_object(raw: str) -> dict:
    i = raw.find('{"bounty"')
    if i < 0:
        raise SystemExit("no {\"bounty\": ...} object found - is this the /information/ page?")
    depth = 0
    k = i
    while k < len(raw):
        if raw[k] == "{":
            depth += 1
        elif raw[k] == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    return json.loads(raw[i:k + 1])["bounty"]


def summarize(b: dict) -> None:
    print(f"PROJECT      : {b.get('project')}  (slug={b.get('slug')})")
    print(f"MAX BOUNTY   : {b.get('maxBounty')}   KYC: {b.get('kyc')}   "
          f"PoC: {b.get('proofOfConceptType')}")
    print(f"PAID IN      : {b.get('rewardsToken')} on {b.get('rewardsTokenNetwork')}")
    print(f"LAUNCH/UPDATED: {b.get('launchDate')} / {b.get('updatedDate')}")

    print("\nREWARD TABLE")
    for r in b.get("bounties") or b.get("rewards") or []:
        if r.get("rewardModel") == "range":
            print(f"  [{r.get('severity'):<8}] min {r.get('minReward')} - max {r.get('maxReward')} "
                  f"({r.get('rewardCalculationPercentage')}% of funds at risk) type={r.get('assetType')}")
        else:
            print(f"  [{r.get('severity'):<8}] fixed {r.get('fixedReward')} type={r.get('assetType')}")

    print("\nASSETS (in scope)")
    for a in b.get("assets", []):
        flag = " [PRIMACY OF IMPACT]" if a.get("isPrimacyOfImpact") else ""
        print(f"  [{a.get('type')}] {a.get('description')} {a.get('url')}{flag}")

    print("\nIMPACTS (in scope)")
    for im in b.get("impacts", []):
        print(f"  [{im.get('severity'):<8}] {im.get('type'):<14} {im.get('title')}")

    print("\nKNOWN ISSUES (program-level do-not-report list)")
    for k in b.get("knownIssues", []) or []:
        print(f"  {k.get('description')}  (updated {str(k.get('lastUpdatedAt'))[:10]})  {k.get('link')}")

    print("\nAUDITS")
    for a in b.get("audits", []):
        print(f"  {a.get('date')} {a.get('auditor')}  {a.get('url')}")

    print("\nCODEBASE / DOCS")
    for c in b.get("programCodebases", []) or []:
        print(f"  codebase: {c.get('url')}")
    for d in b.get("programDocumentations", []) or []:
        print(f"  docs    : {d.get('url')}")
    print(f"  website : {b.get('websiteUrl')}\n  github  : {b.get('githubUrl')}")

    print("\nPROHIBITED / OUT OF SCOPE (non-empty fields)")
    for key in ("customProhibitedActivities", "customOutOfScopeInformation",
                "prioritizedVulnerabilities", "responsiblePublicationCategory",
                "eligibilityCriteria", "networkType", "reductionPercentage"):
        v = b.get(key)
        if v not in (None, [], {}, "_blank_", ""):
            print(f"  {key}: {json.dumps(v)[:400]}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    data = open(path, encoding="utf-8", errors="replace").read()

    raw = "".join(flight_chunks(data))
    if not raw:
        raise SystemExit("no self.__next_f.push payloads found - did the fetch actually succeed? "
                         "(check http code / size before parsing)")
    raw = raw.encode("utf-8", "surrogatepass").decode("unicode_escape", errors="replace")

    b = bounty_object(raw)
    summarize(b)

    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        json.dump(b, open(out, "w"), indent=1)
        print(f"\nsaved full program record -> {out}")


if __name__ == "__main__":
    main()
