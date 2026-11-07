#!/usr/bin/env python3
"""
vendor_reply_watch.py — silent watchdog for vendor replies on submitted reports.

Watchdog shape: prints NOTHING when there is no new inbound mail, so it can run as a
`no_agent` cron job without generating noise. Alerts only when the vendor writes back.

Why this exists: after submitting a report the ack arrives within minutes and carries the
ticket number every later reply must quote. A human triage reply can land days later. Polling
the mailbox by hand wastes turns; this surfaces it automatically.

Usage
-----
    python vendor_reply_watch.py --domain telekom.de --domain bugbounty.telekom.de
    python vendor_reply_watch.py --domain telekom.de --to bugbounty@telekom.de --days 7
    python vendor_reply_watch.py --domain example.com --seed      # absorb current, no alert

State lives in ~/.chiper/skills/bounty-pack/trackers/<slug>-reply-seen.json so restarts do not
re-alert on the same message.

Exit codes: 0 = ok (silent or alert emitted), 1 = auth/API error.
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests not installed", file=sys.stderr)
    sys.exit(1)

HOME = Path(os.path.expanduser("~/.chiper/skills/bounty-pack"))
TOKEN_PATH = HOME / "google_token.json"
TRACKER_DIR = HOME / "trackers"

# Edit these for a standing engagement; --domain / --to override.
DEFAULTS = {
    "domains": [],
    "to": None,
    "days": 7,
}


def access_token() -> str:
    d = json.loads(TOKEN_PATH.read_text())
    r = requests.post(
        d["token_uri"],
        data={
            "client_id": d["client_id"],
            "client_secret": d["client_secret"],
            "refresh_token": d["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def build_query(domains, to, days) -> str:
    parts = []
    if domains:
        ors = " OR ".join(f"from:{d}" for d in domains)
        parts.append(f"({ors})")
    if to:
        parts.append(f"to:{to}")
    parts.append(f"newer_than:{days}d")
    return " ".join(parts)


def header(payload, name):
    for h in payload.get("headers", []) or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", action="append", default=None,
                    help="vendor domain to watch (repeatable)")
    ap.add_argument("--to", default=DEFAULTS["to"],
                    help="the submission address you mailed (adds 'to:' to the query)")
    ap.add_argument("--days", type=int, default=DEFAULTS["days"])
    ap.add_argument("--seed", action="store_true",
                    help="record current messages as seen without printing them")
    ap.add_argument("--slug", default=None,
                    help="state-file name; defaults to first domain")
    args = ap.parse_args()

    domains = args.domain or DEFAULTS["domains"]
    if not domains and not args.to:
        print("need --domain or --to", file=sys.stderr)
        return 1

    slug = args.slug or (domains[0] if domains else args.to)
    slug = slug.replace("@", "_").replace(".", "_")
    state_path = TRACKER_DIR / f"{slug}-reply-seen.json"

    tok = access_token()
    H = {"Authorization": f"Bearer {tok}"}
    q = build_query(domains, args.to, args.days)

    r = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        params={"q": q, "maxResults": 25},
        headers=H,
        timeout=30,
    )
    if r.status_code != 200:
        print(f"[vendor-watch] gmail error {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return 1

    msgs = r.json().get("messages", [])
    seen = set(json.loads(state_path.read_text())) if state_path.exists() else set()

    new = []
    for m in msgs:
        mid = m["id"]
        if mid in seen:
            continue
        mm = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
            params={"format": "metadata",
                    "metadataHeaders": ["From", "Subject", "Date"]},
            headers=H,
            timeout=30,
        ).json()
        labels = mm.get("labelIds") or []
        seen.add(mid)
        if "SENT" in labels:
            continue  # our own outbound is not a vendor reply
        new.append((
            mid,
            header(mm.get("payload", {}), "From"),
            header(mm.get("payload", {}), "Subject"),
            header(mm.get("payload", {}), "Date"),
        ))

    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(sorted(seen)))

    if args.seed:
        return 0  # first run after submission: absorb the acks silently

    if not new:
        return 0  # silent — nothing to report

    print("VENDOR REPLY DETECTED")
    for mid, frm, subj, date in new:
        print(f"  from   : {frm}")
        print(f"  subject: {subj}")
        print(f"  date   : {date}")
        print(f"  id     : {mid}")
        print()
    print("Reminder: quote the ticket/CDR number from the subject in any reply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
