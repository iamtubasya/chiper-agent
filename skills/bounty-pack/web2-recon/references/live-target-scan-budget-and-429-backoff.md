# Scanning a LIVE production target — scan budget, self-inflicted 429, and backoff

Verified 2026-10 on a bank VDP (nordnet.se). A broad nuclei sweep tripped Google Cloud
Armor and returned **HTTP 429 for ~45 minutes** across the whole platform, voiding a whole
round of testing. This is a self-inflicted wound, not a target property — avoid it.

## What went wrong (reproducible)

```
nuclei -l live_hosts.txt -t ~/nuclei-templates -severity critical,high,medium,low ...   # 14k templates × 73 hosts
```

`templates × hosts = requests`. 14k × 73 ≈ 1M requests. At `-rl 30` that is **~9 hours** and
a request volume no live production estate will tolerate. It also competes with the pipeline's
own scanners for RAM (host wedged at ~360 MB free).

## Rules

1. **Never point a full-template sweep at a live production host set.** Use *targeted* template
   dirs at a bounded rate:
   `nuclei -t http/exposures -t http/misconfiguration -t http/exposed-panels -t http/takeovers
   -t http/default-logins -rl 20..40 -c 10..20`
   Add `-t http/cves -tags <tech>` only for the specific stack you fingerprinted.
2. **Budget the request count before firing.** If `templates × hosts > ~50k`, narrow the target
   list or the template set first.
3. Prefer the pipeline's own gentle defaults (`nuclei -rl 50 -c 10`, `katana -rl 5 -c 2`) and keep
   *your* parallel scanners off the same host while the pipeline runs.

## Reading the 429 — GCP Cloud Armor vs WAF vs CDN

- `via: 1.1 google` on the 429 ⇒ **Google Cloud Armor / GCP load balancer**.
- **Shared LB across the whole domain family.** `www.<brand>.se/.fi/.dk/.no/.de` sat behind ONE
  LB keyed by client IP — a ban on one is a ban on **all**. Do not "just test another TLD" to
  dodge it; you'll get 429 on every one and waste requests.
- No `Retry-After` header; the window is opaque (observed ~45 min). The **apex** (`nordnet.se`)
  and other non-www hosts kept working (apex 301→www) — a bare redirect proves nothing.
- Cloudflare-fronted hosts answer 421 (misdirected request) / 403 Cloudflare page, not this.

## Backoff discipline when you see 429

1. **Stop the active scanners immediately.** Kill Go/Python tools via Python `taskkill /PID <n>/T /F`
   (shell `taskkill /F` gets path-mangled under MSYS).
2. Probe a cheap baseline (`GET /`) every few minutes; resume only at 200.
3. **Do NOT rotate egress** (WARP / other IP) to bypass the limit — that is evading a control and
   can void the engagement. Record the ban as a **blocker** in the coverage ledger instead.
4. **Mark every result captured during/after the window as POISONED, never "negative".** Tools
   exit `0` with empty output against a 429, which reads as a false negative. Grep the evidence
   for the tell: sqlmap prints `HTTP error codes detected: 429`; linkfinder errors
   `HTTP Error 429: Too Many Requests`; race-checker shows `429: N times`.

## MSYS probe construction (bit 3× this session)

Never iterate bare `/path` items in a `for` loop and hand them to curl:

```bash
for p in /wp-json/x /api/y; do curl -s "https://host$p" ...; done   # ← MSYS rewrites /wp-json → C:/Users/.../git/wp-json, curl exits 000
```

MSYS (git-bash) converts args that begin with `/` into Windows paths; curl then fails with code
`000`, and a **stale `/tmp` body from the previous call makes it look like a real response**.
Always build the full quoted URL, one per line:

```bash
probe() { curl -s -m12 -A "$UA" -o /tmp/rr -w "code=%{http_code} size=%{size_download}\n" "$1"; head -c 350 /tmp/rr; }
probe "https://host/wp-json/x"
```
