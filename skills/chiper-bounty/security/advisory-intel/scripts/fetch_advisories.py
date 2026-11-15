#!/usr/bin/env python3
"""Fetch ALL published GitHub Security Advisories for watched repos.

- Follows the `Link: rel="next"` cursor (per_page=100 CAPS a page; page=2 re-returns the same rows).
- Dedupes by ghsa_id and keeps manifest.json so re-runs report ONLY NEW ids.
- Tokenless works (60 req/hr core); set GITHUB_TOKEN to raise the limit.

Usage:
  python fetch_advisories.py                 # uses REPOS below
  REPOS="openemr/openemr php/php-src" python fetch_advisories.py

Outputs (in this script's directory):
  adv_<owner>_<repo>.json        full advisories
  manifest.json                  seen ghsa_ids + last_sync + severity histogram
  last_sync_result.json          {repo: {new: [...], new_high_critical: [...], total, sev}}
"""
import json, os, sys, time, urllib.request, urllib.error, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
REPOS = (os.environ.get("REPOS") or "openemr/openemr php/php-src").split()
HDRS = {"Accept": "application/vnd.github+json", "User-Agent": "advisory-intel/1.0",
        "X-GitHub-Api-Version": "2022-11-28"}
if os.environ.get("GITHUB_TOKEN"):
    HDRS["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]


def get(url):
    req = urllib.request.Request(url, headers=HDRS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode()), r.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 2:
                print(f"  rate/abuse {e.code}, sleeping 20s", file=sys.stderr)
                time.sleep(20)
                continue
            raise
    raise RuntimeError("unreachable")


def next_link(link_header):
    for part in (link_header or "").split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return ""


def fetch_repo(repo):
    """Cursor-paginate until exhausted (page=2 is NOT reliable — must use ?after=)."""
    url = f"https://api.github.com/repos/{repo}/security-advisories?per_page=100&state=published"
    out, page = [], 0
    while url:
        page += 1
        data, link = get(url)
        if not isinstance(data, list):
            print(f"  !! non-list payload: {str(data)[:200]}", file=sys.stderr)
            break
        out.extend(data)
        url = next_link(link)
        if page > 25:  # runaway guard
            break
    return out


def main():
    mpath = os.path.join(BASE, "manifest.json")
    manifest = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}
    grand = {}
    for repo in REPOS:
        slug = repo.replace("/", "_")
        try:
            advs = fetch_repo(repo)
        except Exception as e:
            print(f"[FAIL] {repo}: {e}")
            continue
        advs = list({a["ghsa_id"]: a for a in advs}.values())  # dedupe
        json.dump(advs, open(os.path.join(BASE, f"adv_{slug}.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        sev = {}
        for a in advs:
            k = a.get("severity") or "unknown"
            sev[k] = sev.get(k, 0) + 1
        seen = set(manifest.get(repo, {}).get("seen_ghsa", []))
        ids = {a["ghsa_id"] for a in advs}
        new = sorted(ids - seen)
        new_hc = sorted(a["ghsa_id"] for a in advs
                        if a["ghsa_id"] in new and a.get("severity") in ("critical", "high"))
        manifest.setdefault(repo, {})
        manifest[repo].update({
            "last_sync": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total": len(advs), "severity": sev, "seen_ghsa": sorted(seen | ids)})
        grand[repo] = {"new": new, "new_high_critical": new_hc, "total": len(advs), "sev": sev}
        print(f"[OK] {repo}: {len(advs)} advisories {sev} | NEW={len(new)} (high/crit={len(new_hc)})")
    json.dump(manifest, open(mpath, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(grand, open(os.path.join(BASE, "last_sync_result.json"), "w", encoding="utf-8"), indent=1)
    print("NEW high/critical:",
          json.dumps({k: v["new_high_critical"] for k, v in grand.items()}))


if __name__ == "__main__":
    main()
