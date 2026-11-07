---
name: google-dork-consistent
description: Use when Google dorking / Google SERP scraping hits the "unusual traffic" CAPTCHA wall, or when you need consistent, repeatable Google search results from an automated browser. Covers the profile-bound nature of Google's bot wall, persistent-profile reuse, profile rotation, and resolving Google's opaque /goto?url= result links.
---

# Consistent Google Dorking (no CAPTCHA wall)

## When to use
- A Google dork / `site:` query returns the "Our systems have detected unusual traffic" wall.
- You need repeatable Google SERP results across many queries for recon.
- Google results show `href="/goto?url=CAES..."` instead of real URLs.

## Core findings (verified 2026-10-01, Windows, Chrome 138, Cloudflare WARP egress)

1. **The CAPTCHA wall is bound to the browser PROFILE and to query volume, not to the IP.**
   Proven by running two browsers at the same moment from the same IP:
   a brand-new profile returned 30 organic results while a previously-used
   profile was walled. Plain `curl` from the same IP never got the wall.
2. **One profile survives roughly 8–12 queries, then gets flagged.** After that
   it keeps returning the wall for a long time — a flagged profile was still
   walled **~18 minutes later**, and deleting all `.google.com` cookies did not
   clear it. So **recycle the profile; do not wait it out.**
3. **A profile's ORIGIN does not matter — only its recent query history does.**
   Head-to-head, same query, run back to back:
   persistent profile / brand-new profile / profile copied from an old Chrome
   install all returned **identical results (10 hits, 10 resolved URLs)**.
   Which one walls first is decided purely by how many queries it has already
   served. Do not bother importing cookies to "improve" Google results.
4. **Never run automated queries through a copy of the user's real logged-in
   Chrome profile** — you risk getting their live Google account flagged.
   Automation profiles should be empty and disposable.
5. **No-JS Google is dead.** `curl` with `&gbv=1`, a Lynx/Googlebot UA, etc.
   now returns the "enable JS" page (`/httpservice/retry/enablejs`), not
   results. A JS-capable browser is required.
6. **Cloudflare WARP is not the cause.** WARP egress (104.28.x / 2a09:bac1::)
   is flagged for *browser automation fingerprints*, but curl from the same
   IP is unaffected. Don't disable WARP or hunt proxies to fix this.
7. **Result URLs are opaque.** Modern Google SERPs put
   `href="/goto?url=CAES<opaque>"` on result links; the real destination is
   absent from the HTML. Resolve it with an authenticated request:
   `GET https://www.google.com/goto?url=<token>` → **302** with the true URL in
   `Location`. Playwright: `page.request.get(url, max_redirects=0).headers["location"]`.

## Working harness

`D:/data hermes/advisory-intel/gdork.py`

```bash
PY="/usr/bin/python3"
cd "D:/data hermes/advisory-intel"

# normal run (persistent profile: D:/data hermes/browser-profiles/gc-dork)
"$PY" gdork.py -n 20 "site:target.com inurl:login"

# JSON for pipelines
"$PY" gdork.py -n 20 --json "site:target.com ext:php" > out.json

# profile walled -> auto-create a fresh profile and retry
"$PY" gdork.py -n 20 --rotate "site:target.com"

# other profile / faster cadence
GDORK_PROFILE="D:/data hermes/browser-profiles/gc-dork-<ts>" "$PY" gdork.py --min-interval 0 "..."
```

Exit codes: `0` ok/no-results, `3` walled after all retries.

## Full recon stack — `dork-recon.py` (3 layers)

`~/.chiper/skills/bounty-pack/dork-recon.py` — Google is layer 3, not the
workhorse. Use the layered script for recon; use `gdork.py` directly only for one-off queries.

| layer | engine | role | why |
|---|---|---|---|
| 1 | **Camoufox + DDG** (Bing fallback) | primary | fast, bulk, never CAPTCHAs |
| 2 | **Wayback CDX** (`matchType=domain`) | bulk URLs | volume no engine hands over; no search engine at all |
| 3 | **Google** (`gdork.py --pool`) | fallback | most complete, but rate-limited → only for thin queries |

```bash
PY="/usr/bin/python3"
"$PY" dork-recon.py --target target.com --out ./dork-recon            # all 3 layers
"$PY" dork-recon.py --target target.com --layers 1,2                  # skip Google
"$PY" dork-recon.py --target target.com --queries my_dorks.txt --google-all
```
Outputs into `--out` only: `dork-urls.txt`, `dork-results.json`, `dork-report.md`.
Verified: `--target vinted.com` L1+L2 → 418 unique URLs (18 DDG, 400 CDX, 56 "juicy"); L3 alone → 11.

Pitfalls: CDX needs `matchType=domain` + a `from`/`to` window (a bare `url=big.site*&limit=3000`
times out with a 504); reuse ONE Camoufox browser across all queries (cold start is ~50 s);
Camoufox must be run headful with `humanize=True` to stay stealthy.

Integration into the audit pipeline is **additive only** (`audit-pipeline-orchestrator.py`,
`run_dork_recon()` called at the end of `run_recon()`): it writes solely into
`<output_dir>/dork-recon/` and never rewrites `subs.txt` / `live.txt` / `urls.txt` unless
`DORK_MERGE=1`. Knobs: `DORK_RECON=0` disable, `DORK_LAYERS=1,2,3`, `DORK_CDX_LIMIT`, `DORK_TIMEOUT`.

## Operating rules — use POOL MODE

```bash
PY="/usr/bin/python3"
cd "D:/data hermes/advisory-intel"

# RECOMMENDED: rotate a pool of profiles, auto-recycle walled ones
"$PY" gdork.py -n 20 --pool "site:target.com inurl:login"

# batch of dorks, still 100% success after a recycle
for q in "site:t.com inurl:login" "inurl:admin.php" "intitle:index.of passwd"; do
  "$PY" gdork.py -n 10 --pool --min-interval 0 "$q"
done
```

Measured: pool mode **11/12 queries OK** (the single miss was the pool profile
hitting its ~10-query limit, auto-recycled, then 11 straight successes).
A single hammered profile: 0/10.

- `--pool` picks the least-recently-used `D:/data hermes/browser-profiles/gc-pool-*`
  profile, and on a wall **wipes + recreates** it (only ever touches `gc-pool-*`).
- `--pool-size` (default 3), `--cooldown` (park time if `--no-recycle`).
- `--min-interval` (default 25 s) spaces queries per profile — keep it on for
  long dork lists.
- Keep `--retries` on (default 2, backoff 30/90/180 s): short walls often
  clear on a single reload.
- **Never trust `hits: 0` at face value** — read the `status:` line.
  `NO_RESULTS` ≠ `WALL_CAPTCHA`. Empty output from a walled run is a tool
  failure, not "no findings".
- Headful (`headless=False`) is the default for a reason; a visible real
  Chrome window is far less suspicious than headless.
- Other modes: `--rotate` (throwaway fresh profile on wall), plain default
  profile `gc-dork`, or `GDORK_PROFILE=<dir>` / `--profile <dir>`.

## Pitfalls
- Seeding from a live Chrome profile fails while Chrome runs — the `Network/Cookies`
  SQLite file is locked (`Permission denied`, `Device or resource busy`); not even
  `robocopy /B` (needs Backup privilege) or `esentutl /vss` (needs admin) can read it.
- Chrome 136+ ignores `--remote-debugging-port` when the *default* user-data-dir
  is used, but honours it if `--user-data-dir` is passed explicitly.
- Playwright `channel="chrome"` + `launch_persistent_context` is the reliable
  path; `p.chromium` bundled Chromium is more fingerprint-detectable.
- Locale/consent: pass `locale="en-US"` and auto-click `button:has-text("Accept all")`
  on the consent interstitial, then re-navigate.
