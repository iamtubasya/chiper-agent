# DeFiLlama Target Discovery — New DeFi Protocols Pipeline

**Purpose:** Discover NEW DeFi protocols (listed < 1 year, TVL > $10M) as bug bounty targets. New protocols = fresh attack surface (new versions, forks, untested code) and often NO public bounty yet → opportunity for private-program contact.

**Complements** `references/immunefi-program-discovery.md` (which finds programs already listed on Immunefi). DeFiLlama finds protocols BEFORE they list bounties.

**Session proven:** 2026-09-07 — 8,190 protocols fetched, 153 matched filter, top-15 enriched → 3 contact emails + 3 confirmed bounty programs.

---

## Pipeline

### Step 1 — Fetch protocol list (ALWAYS via file, never stdout)
```bash
curl -s 'https://api.llama.fi/protocols' -o ~/defillama_raw.json
# ~8.4MB, 8000+ protocols. See Pitfall 1 — do NOT pipe through captured stdout.
```

### Step 2 — Filter new protocols
```python
import json, time, os
with open(os.path.expanduser('~/defillama_raw.json')) as f:
    data = json.loads(f.read(), strict=False)   # strict=False: control chars in descriptions

one_year_ago = time.time() - 365*24*3600
new_protos = [p for p in data
              if (p.get('listedAt') or 0) > one_year_ago   # guard None — Pitfall 5
              and (p.get('tvl') or 0) > 10_000_000]
new_protos.sort(key=lambda x: x.get('tvl') or 0, reverse=True)
# Useful fields: name, slug, tvl, chains[], category, listedAt (unix ts), url (website)
```

Filters proven useful:
- `tvl > $10M` — below that, bounty payoff unlikely
- **Skip `category == 'CEX'`** — centralized exchanges rarely run bounties via DeFi channels
- High-value categories: Lending, Bridge, RWA, Yield, Staking Pool, Basis Trading, Risk Curators

### Step 3 — Enrich each target (bounty + contact)

| Source | Method | Yield (2026-09-07, 15 targets) |
|---|---|---|
| Bounty program | `web_search("<name> bug bounty immunefi security")` | Aave → immunefi.com/bug-bounty/aave/, Obol → docs.obol.org bug-bounty page, Huma → cantina.xyz bounty |
| security.txt | `curl -sL https://<domain>/.well-known/security.txt` | Grove: contact@grove.finance, Spark: contact@spark.finance |
| Main site scrape | curl homepage + email regex | Huma: hi@huma.finance |
| GitHub README scan | raw.githubusercontent.com/<repo>/main/README.md | 0 hits — LOW YIELD, skip |
| DDG HTML scrape | curl html.duckduckgo.com | **BROKEN — see Pitfall 3** |

Email regex:
```python
import re
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
SKIP = {'example.com', 'sentry.io', 'duckduckgo.com', 'png', 'jpg', 'wixpress'}
```

Follow-up priority:
1. Confirmed bounty (Immunefi/Cantina/own docs) → start hunting immediately
2. High TVL ($200M+) + no public bounty → email contact for private-program inquiry

### Step 4 — Save outputs
```
D:/data hermes/bugbounty/defillama/   # global rule: ALL bb data on D:, never C:
```
Raw JSON + enriched summary + report markdown. (2026-09-07 session mistakenly wrote to C: home — next runs must target D:.)

---

## Windows Environment Pitfalls (cost the session ~10 min)

### ⛔ Pitfall 1: execute_code terminal() stdout truncated at ~20,000 chars
`terminal()` inside `execute_code` truncates stdout → 8.4MB DeFiLlama JSON never parses (`JSONDecodeError` at char 20000, repeatedly, even with `strict=False`).
**Fix:** Never route large payloads through captured stdout. Run `curl -o <file>` via the `terminal` TOOL directly, then parse from the file.

### ⛔ Pitfall 2: MSYS /tmp ≠ Windows Python /tmp
curl (MSYS) writing to `/tmp` lands in `%TEMP%` (`C:\Users\...\AppData\Local\Temp\`), but Windows-native Python resolving `/tmp/...` raises FileNotFoundError — even though `ls /tmp` works in bash.
**Fix:** Use `~/` (home dir) as the handoff directory between bash tools and Windows Python, or explicit `C:\...` paths.

### ⛔ Pitfall 3: DuckDuckGo HTML endpoint returns garbage
`curl https://html.duckduckgo.com/html/?q=...` returns an error/bounce page whose ONLY email is `error-lite+66d9@duckduckgo.com` — every query, every target. Email regex on it yields one useless address for all targets (looks like success, is poison).
**Fix:** Use the `web_search` tool (importable in execute_code: `from hermes_tools import web_search`) — worked for all 14 bounty-program queries.

### Pitfall 4: Enrichment loop timeouts
Long loops (13 targets × 5 URLs × curl each) can exceed the 180s foreground terminal timeout. Run enrichment in batches of ~5 targets or set explicit timeout.

### Pitfall 5: None values in DeFiLlama data
`tvl` and `listedAt` can be `None` → `TypeError: '>' not supported between 'NoneType' and 'int'`. Always guard with `(p.get('tvl') or 0)`.

---

## 2026-09-07 Results Snapshot (calibration reference)

Top new protocols by TVL (filter: <1yr, >$10M): Sentora Curator $2.39B, Grove Finance $2.15B, CCIP $1.79B, Spark Savings $1.24B, Falcon Finance $1.18B, Obol $634M, Aave V4 $384M, Re $344M, RockawayX $292M, Huma V2 $279M, GTBTC $277M, Mellow Core $252M, Cooler Loans $239M, Solstice $238M, KPK $201M.

Best bounty targets found: Aave V4 (Immunefi, V4 = fresh attack surface), Obol (own bounty program), Huma Finance (Cantina), Grove Finance + Sentora Curator (high TVL, no public bounty → private-program email candidates).
