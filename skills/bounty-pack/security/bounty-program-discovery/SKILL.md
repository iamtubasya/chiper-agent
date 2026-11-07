---
name: bounty-program-discovery
description: Use when finding new just-launched bug bounty targets.
version: 1.0.0
author: operator
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, target-discovery, dorking, early-warning, target-pool]
    related_skills: [target-pool, google-dork-consistent, offensive-osint]
---

# Bounty Program Discovery — find NEW targets before other hunters

## When to use
- Operator asks for "early warning" of fresh bug bounty programs, or wants to beat others
  to a just-launched program.
- Building / maintaining the every-15-min discovery cron.
- A bare dork returns stale programs, articles, or 404 pages and you need it cleaned up.
- Adding new domains into `D:/data hermes/target-pool/pool.json` automatically.

## The architecture (5 layers, cheapest→dearest)

Where it lives: `~/.chiper/skills/bounty-pack/early-warning/`.
Cron job (no_agent, `*/15 * * * *`) runs `scripts/early_warning_run.py` → `ew_run.py`.

| layer | script | what it finds | cost |
|---|---|---|---|
| L1 | `ew_scan.py` | feed diff — HackerOne/Bugcrowd/Intigriti/YesWeHack (commit-check first, download only on change) | ~0 |
| L2 | `page_scan.py` | program pages — probe `/bug-bounty` `/responsible-disclosure` `/vulnerability-disclosure` `/security.txt` on self-hosted pool domains (rotated batch) | probe per domain |
| L3 | `search_scan.py` | search-engine dorking (Camoufox + DDG) with date filter | ~1 browser |
| L4 | `ew_scan.py` security.txt sweep | self-hosted pool domains missing Contact | curl batch |
| — | `resolve_target.py` | website + email-dev resolution from X-project scrapes (per-project pipeline) | curl + whois/dig |
| — | `pool_ingest.py` | atomic merge of verified domains into `pool.json` | local |

## CRITICAL: cron hard-kills at 300s

Measured 2026-10-25: `no_agent` cron scripts that run >300s are killed ("Script timed out
after 300s"). A full 5-layer run measured ~482s and failed until budgets were sized down.
Rules:
- **Size each stage's subprocess `timeout` so worst-case total < 270s** (leave margin).
  Working budget: feeds 100s + pages 85s + search 85s ≈ 270s worst case; measured happy
  path ~150s.
- Rotate coverage rather than shrinking forever: each stage keeps a `seen_domains` /
  `query_rotation` / `last-checked` cursor so N small batches converge over runs.
- `search_scan.py` reads `EW_MAX_DORKS` env (default 3) — lower it per run, not the timeout.

## Dorking for NEW programs (the core technique — verified 2026-10-30)

A bare `inurl:bug-bounty` returns mostly stale programs + articles. Fix = date-filter +
verification pipeline with 3 gates.

1. **Date-filter DDG** — `&df=` biases to recently indexed. `df=d` day, `df=w` week,
   `df=m` month. URL: `https://duckduckgo.com/?q=<enc>&ia=web&df=m`. Without it you get
   years-old basi programs. Short dorks (no `-site:` stacking which returns 0):
   `inurl:bug-bounty` · `inurl:responsible-disclosure` · `inurl:vulnerability-disclosure` ·
   `inurl:security.txt bug bounty` · `bug bounty program launch` · `new bug bounty program reward`.

2. **Selector = `a[data-testid="result-title-a"]` ONLY.** The article
   (`article[data-testid="result"] a[href]`) form grabs every `<a>` in the card: DDG returns
   ~61 links but 55+ are INTERNAL (ad `y.js`, `?q=` refinement, `site:` refinements,
   related-search). The title-only selector yields the 1-2 organic results.

3. **Strip internal + aggregator domains** from hrefs. Drop hosts containing
   `duckduckgo.com|bing.com|google.com|yahoo.com|yandex.` (refinement/ad, not results), and
   aggregators/directories which are NOT the program itself:
   `bountyhunte.rs|bugbountydirectory|bbradar|hacktrophy|huntbug`.

4. **Decode DDG redirect** — organic links come as `//duckduckgo.com/l/?uddg=<url-encoded>`;
   parse `uddg=` + `urllib.parse.unquote`.

5. **Three verification gates, in order** (each candidate URL):
   - **Liveness** — `curl -sL -w %{http_code}`; keep only 2xx/3xx, drop 404/5xx.
   - **Signal** — body must match program regex, else it's an article/news page:
     `bug bounty|responsible disclosure|vulnerability disclosure|hall of fame|security.txt|
     report a vulnerability|bounty program|reward`.
   - **Path filter** — drop `/blog /news /article /help /guide /tutorial /docs /wiki /learn
     /what-is /how-to /list /directory` (those are articles even when live, e.g.
     `geeksforgeeks.org/blog/...`).

6. **Blocklist media/edu domains** (articles, not programs):
   `geeksforgeeks|towardsdatascience|freecodecamp|dev.to|portswigger|owasp.org|sans.org|
   infosec|thehackernews|bleepingcomputer|darkreading|medium`.

7. **Dedup against pool + seen set** before ingest, so a re-run feeds new domains only.
   Measured: 61 raw links → ~4 verified → ~1-2 survive path/noise filtering.

Bare `curl` to Google/Bing/DDG is dead (consent wall / poisoned results / 202). Use
Camoufox (`humanize=True`). See `google-dork-consistent` for the profile-bound CAPTCHA detail.

## Pool ingest protocol (atomic + honest)

`pool_ingest.py` merges verified domains into `pool.json`:
- **Only adds** domains not already present; never overwrites an existing record.
- **Atomic write** — `tmp` then `os.replace(POOL)`; daily backup to `pool-backups/` before
  first change; every add appended to `pool-ingest-manifest.jsonl`.
- **Honest freshness fields.** New entries get `status: "active"` BUT `live: "unverified"`
  and `discovered_by: "early-warning"` + `first_seen: today`. Reason: a search hit hasn't been
  probed for liveness by the audit pipeline yet. `pool.py pick` then labels them
  `live=?(belum diprobe)` instead of `live✓` — never claim a domain is live that you only saw
  in a SERP.
- **`pool pick --new`** lists only `discovered_by == early-warning`; `pick` sorts by
  `first_seen` desc so newest surface first. (This "newest first" behaviour was added to
  `pool.py` this session; see target-pool skill for the rest of the pick CLI.)

## whois + dig on Windows (no binary)

```
winget install Microsoft.Sysinternals.Whois --silent   # Sysinternals whois
winget install ISC.Bind --silent                        # brings dig.exe + nslookup
```
WinGet installs land under
`~/.local/share/Microsoft/WinGet/Packages/<Id>_.../`. `dig +short <domain> MX`
is the email-validity gate (empty MX = domain can't receive mail, skip `security@` guesses).
`whois` (Sysinternals) emits registrant/creation lines for RDAP fallback.

## Per-project pipeline (X discovery → report)

Six-step loop the operator specified (state in `state/projects.json` via `proj_state.py`):
```
[1] x_discovery.py  search X keywords (disclosure, security.txt, vdp, bug-bounty, bug, bounty, reward)
[2] resolve_target.py  website from bio/links (strip platform domains: twitch/vercel/pump.fun ...)
[3] email dev — priority: security.txt → /security /contact /about → GitHub SECURITY.md → RDAP → role-guess (MX-gated)
[4] audit (audit-pipeline-orchestrator 0A-0F)
[5] draft + PDF (report-agent.py) + PGP (gpg 2.4.9) — operator approves before send
[6] proj_state.py retry-once-then-skip: 0 findings → retry_audit=1 → still 0 → skipped_no_finding (no email)
```
Email must be on the target's OWN domain — a platform email (`security@twitch.tv` for a project
that only has a Twitch account) is a reputation hazard; block platform domains in both the
website resolver and the email clean pass.

## Pitfalls
- **X cookie `auth_token` expires** → `api.x.com` returns 401 / browser redirects to
  `/i/jf/onboarding`. That's a session/credential expiry, not a code bug — re-export a fresh
  `x_cookies.json` (dict `{auth_token, ct0, ...}`, not list-of-dicts). Don't rewrite the scanner.
- **Immunefi / Hackenproof / Code4rena feeds are dead** (404/DNS-fail as of 2026-10) — web3
  discovery currently relies on platform-feed keyword regex + the pool's `web3_*` category, not
  those API endpoints.
- Read-before-write: `pool.py` and the discovery scripts live under
  `~/.chiper/skills/bounty-pack/` and `~/early-warning/` — verify paths exist before a run
  (the scripts dir has vanished once before).

## "Basi" vs "baru launch" — the whole point of the filter (2026-11-02)

A dork hit can be a **real, live VDP** that is STILL the wrong result because the program is
mature/established ("basi"), not "just launched". Reverse-engineered this session:

| domain | what it is | why it's basi (NOT a 404!) |
|---|---|---|
| unesco.org | PBB IGO | `/en/vulnerability-disclosure` LIVE, decades-old IGO VDP |
| tcl.com | TV maker | `/eu/en/legal/vulnerability-disclosure-policy` live, vendor-mapan |
| cidaas.com | Ubisecure CIAM | long-standing vendor VDP |
| exploitportal.com | — | real disclosure page, established |

**Trap that caused a wrong "dead/404" call:** probing `/.well-known/security.txt` returned
403/404 for ALL of them, so they were first (wrongly) judged dead. Their ACTUAL disclosure
page was a `/.../vulnerability-disclosure` path returning 200. **When a candidate has
"no security.txt", probe the disclosure URL the dork actually returned before calling it
dead or basi** — the security.txt probe is NOT the liveness signal for program pages.

**The filter (MEGA_ORG blocklist):** reject mega-corp / gov / edu / IGO / vendor-mapan even
when they have live VDPs — they are never "new launch":
`unesco|un.org|who.int|europa.eu|gov.|gob.|mil.|edu.|ac.|tcl.com|cidaas|exploitportal|
google|microsoft|apple|meta.com|facebook|amazon|netflix|oracle|ibm|cisco|sap|salesforce|
adobe|intel|amd|nvidia|dell|hp.com|lenovo|samsung|sony|lg.com|visa|mastercard|paypal|stripe|
ing.com|hsbc|barclays|cloudflare|akamai|fastly|cloudfront`.

Two dedup/liveness bugs fixed alongside, in `search_scan.py`:
- **`www.` vs apex not deduped** → normalize `www.<x>` → `<x>` in `probe_url` BEFORE the
  pool-dedup check, else a re-run re-adds `www.tcl.com` separately from `tcl.com` (this is
  exactly how cleared domains got re-ingested this session).
- **Homepage root resolves positively** → reject `path in ("", "/")`: mega-corp homepages
  mention "bug bounty" in a footer without being a program. Only accept real disclosure paths
  (`/security`, `/bug-bounty`, `/.../vulnerability-disclosure`, `/responsible-disclosure`).

## Program age ≠ domain age (operator correction 2026-11-02)

Operator: *"jangan skip cuma karena domain lama; fokus ke program-nya, bukan umur domain."*
A domain can be 20 years old while its bug-bounty PROGRAM just launched last week — that is
still a valid "baru launch" target. The `MEGA_ORG` name-blocklist above is a *fallback*, NOT
the primary signal. The primary signal measures **when the program page was first published**:

1. **`wayback_first(disclosure_url)`** — Wayback CDX first snapshot timestamp of the
   disclosure URL (NOT the domain root). Endpoint:
   `http://archive.org/cdx/search/cdx?url=<url>&output=json&limit=1&fl=timestamp`.
   **TRAP: never snapshot the bare domain root.** A parked-then-reacquired domain shows a
   2000-era snapshot (e.g. `cleanshot.com` root → year 2000) which would wrongly mark a
   brand-new startup as "old". Snapshot the *disclosure URL the dork returned* instead.
2. **`securitytxt_expires(domain)`** — parse `Expires:` from `/.well-known/security.txt`.
   Not a publish date, but `Expires` in the PAST → program is ~1yr+ old (freshness fallback
   when no wayback snapshot exists).
3. **`fresh_within_2m(wayback_ts, expires)`** — returns `True` (candidate-new) unless there
   is PROOF of age: wayback first-snapshot >60 days ago, OR security.txt already expired.
   Defaults to `True` when neither signal exists — "can't prove it's old → treat as candidate".
   (To be strict-only-new, flip the default to `False`, but that discards not-yet-indexed
   startups.)

Measured verdicts (all correctly rejected for NEW programs): unesco.org (disclosure wayback
2024-11), tcl.com (2025-07), cidaas.com (2023-06), engageware.com (2013-05).

**Field plumbing:** `search_scan.py` must forward `wayback_first` / `securitytxt_expires` /
`fresh_within_2m` into `collect-search.json`, and `pool_ingest.py` must read them back into
the pool record (do NOT hardcode `fresh_within_2m: True`). `pool.py pick` labels
`≤2bln✓(umur-program)`.

**Surface the dates to the operator — don't just filter silently (2026-11-02).**
Operator: *"kasih tgl di cron early-nya kapan publish-nya, jadi bisa milih."* The dates must
be VISIBLE in two places so the operator can pick, not merely used as an invisible gate:
1. **Cron report** (`search_scan.py` report block) — after each `- `domain`` line, print
   `    publish: <wayback_first or '-'>  |  expires: <securitytxt_expires or '-'>`.
2. **`pool.py pick` display** — same two fields as a second indented line under each row,
   only when `wayback_first` or `securitytxt_expires` is non-empty. `-` means "no source
   available (no wayback snapshot AND no security.txt)" — honest, not a crash.
The report path is `search_scan.py`'s verified loop; the pick path is `cmd_pick`'s display
loop (guard the indent — see the print-loop bug below; keep lines at 8-space indent inside
the `for` loop, and any nested `print` under `if wb or ex:` at 12).

## pool.py print-loop bug (found + fixed this session)

`cmd_pick`'s display loop was reading `live` / `ew_unverified` variables defined **in the
prior aggregation loop**, so `live✓` / `live=?` were wrong for every row except the one that
leaked them. Fix: recompute `lv = (r.get("live") or "").lower()` and
`ew_unv = ...` **inside** the display `for age, sc, dom, r in rows` loop. Symptom to spot:
many candidate rows showing an identical `live✓`/`live=?` label that the per-row `r["live"]`
contradicts.

## Cron split — search on its own job (2026-11-02)

The single 15m job ran feeds+pages+search inside one 300s budget and produced `EW error`
timeouts whenever the Camoufox search stage hung (browser = heavy, ~60-90s, and its hang
poisoned the whole run). Split into two no_agent jobs:
- `4bb99ba57ff8` `early_warning_run.py` → feeds+pages only, every 15m (curl, light)
- `6dd3439321ce` `ew_search_run.py` → `search_scan.py` + ingest + report, every 30m
Both still write `collect-*.json` → merged by `pool_ingest.py` → pool. Keep the failure
domains independent: a browser hang must not kill the curl layers.

## search_scan.py validation-loop timeout (serial → parallel, 2026-11-02)

After adding the recency checks (wayback + security.txt expires), the search cron began
repeated `EW search error` timeouts. Root cause: the validation loop was **serial** —
`probe_url(u)` (8s) → `wayback_first(url)` (15s) → `securitytxt_expires(d)` (10s) = **33s
per candidate**, × up to 25 candidates ≈ 825s, against a 120s subprocess budget in the
wrapper. It fit when the loop was probe-only (25 × 8s ≈ 200s); adding wayback+expires
serially exploded it.

Fix = parallelize the two phases (curl/subprocess releases the GIL while waiting on I/O, so
`ThreadPoolExecutor` gives real wall-clock wins):
- **Phase 1 (probe)** — `_probe_one(q, u)`: liveness+signal+`_valid_domain`+pool/seen dedup,
  via `ThreadPoolExecutor(max_workers=8)`.
- **Phase 2 (recency)** — `_recency_one(r)`: `wayback_first` + `securitytxt_expires` +
  `fresh_within_2m`, via `max_workers=6`, but only over the de-duplicated survivors of phase 1.
- Lower the per-call timeouts: `wayback_first` 15→**8s**, `securitytxt_expires` 10→**6s**.
- Cap candidates: `uniq[:EW_MAX_CANDIDATES]` where `EW_MAX_CANDIDATES` env defaults **15**
  (was hardcoded `[:25]`).

Measured: 1 dork `120s timeout→36s`; 3 dorks (cron default) `120s timeout→98s`. Import the
futures carefully: `from concurrent.futures import ThreadPoolExecutor, as_completed`.

## Editing these scripts — the two corruption traps (2026-11-02)

Patching `search_scan.py` repeatedly corrupted it twice via two distinct failure modes worth
knowing before ANY future edit:
1. **Partial-string `patch` drops a regex closing group.** When the `old_string` / `new_string`
   stops mid-regex (e.g. editing a `NOISE = re.compile(...)` tail), the trailing `)` + `\b`
   can silently vanish, leaving an unterminated group. Symptom: `re.PatternError: missing ),
   unterminated subpattern` at `import search_scan` — the WHOLE script won't load, and the stage
   returns rc=1 (`EW error`), not a regex mismatch at runtime. **Fix:** after any patch that
   touches a `re.compile`, run `python -c "import search_scan"` (not just `py_compile`, which
   does NOT evaluate the regex) — and eyeball that every `(` has a matching `)` on the same
   visual block.
2. **Indentation corruption on nested `print`/block replace.** A fuzzy `patch` that replaces a
   multi-line block frequently lands the interior lines at 8 spaces instead of 4 (or 16 instead
   of 8). TWO traps here:
   - **`py_compile` and `ast.parse` can BOTH report OK on this** when the over-indentation is
     still syntactically valid — e.g. an over-indented block that silently nests *inside* the
     preceding `for`/`if` instead of at function-body level. `ast.parse` only fails on a true
     `IndentationError`; valid-but-wrong nesting parses clean and is a **semantic** bug that
     only shows as wrong behavior (the loop runs N× instead of once, or a whole stage is
     skipped). Do NOT trust `py_compile`/`ast.parse` alone after a block replace.
   - **Verify byte-level indent, not just compile.** Read the lines and print
     `repr(line[:50])` (or `read_file` the numbered lines) to SEE the leading spaces. Spot the
     tell: a comment at 4 spaces immediately followed by a statement at 8 spaces with no
     opening block in between = the block got pulled into the parent loop. **Fix:** overwrite
     the whole contiguous block with `execute_code` `lines[i:j] = [<correct block>]` at the
     intended 4-space indent — never chase it with another fuzzy `patch` (the "correct"
     `old_string` won't match 8/16-space reality). On this Windows host `terminal` heredocs are
     blocked, so `execute_code` with an absolute path is the reliable editor for multi-line
     block replacement.

Pool freshness fields, quarantine protocol, and the security.txt-vs-disclosure-URL trap are
spelled out in `references/pool-freshness-quarantine.md`.