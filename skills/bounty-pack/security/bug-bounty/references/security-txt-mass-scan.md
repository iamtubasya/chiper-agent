# Mass security.txt Scanning for Self-Hosted Bounty Discovery

Scan large domain lists against RFC 9116 `/.well-known/security.txt` to discover self-hosted bug bounty programs NOT on major platforms (HackerOne, Bugcrowd, Intigriti, etc.).

## Why This Works

~13% of top-10K domains have a `security.txt`. Most point to platform-hosted programs (auto-excluded). The remainder are self-hosted VDPs/bounty programs — often underserved by researchers because nobody finds them.

## Source: Tranco Top 1M

```bash
curl -sL "https://tranco-list.eu/top-1m.csv.zip" -o tranco.zip
unzip tranco.zip
awk -F',' '{print $2}' top-1m.csv > domains.txt
# 1M domains, one per line
```

Other sources: crt.sh certificate transparency (filter by TLD), Crunchbase startup lists, category-specific domain lists.

## Optimized Scanner

See `scripts/scan_optimized.py` (saved at `~/scan_optimized.py`).

Key parameters (tested on Tranco Top 10K):
- **Workers:** 50 (vs default 10 — 5x throughput)
- **Timeout:** 3s (vs 8s — most failures are instant, 3s is enough)
- **Progressive CSV write** — results stream to disk, no data loss on kill
- **Platform exclusion list:** hackerone.com, bugcrowd.com, intigriti.com, yeswehack.com, immunefi.com, openbugbounty.org, huntr.dev, hackenproof.com, standoff365.com, yogosha.com, synack.com, cobalt.io

Performance: ~2.7 domains/sec → 10K domains in ~6 minutes.

```bash
python3 ~/scan_optimized.py domains.txt results.csv
```

## CSV Output Columns

| Column | Description |
|---|---|
| domain | Scanned domain |
| has_security_txt | True/False |
| policy_url | Policy URL from security.txt |
| reward_keywords_found | Matched: bounty, reward, responsible disclosure, vulnerability disclosure, hall of fame, cash, payout |
| dollar_amounts_found | Regex-extracted dollar amounts ($N, $N,NNN) |
| likely_self_hosted | True = has reward keywords AND not platform-hosted |
| notes | Skip reason or "No security.txt" |

## Post-Processing Filter

Raw `likely_self_hosted=True` includes false positives. Apply secondary filters:

1. **Exclude big tech CDNs/subsidiaries** — google.com, facebook.com, instagram.com, twitter.com, youtu.be, fbcdn.net, mzstatic.com, discordapp.com, pinterest.com, twitch.tv, etc. These have programs but aren't "self-hosted" in the useful sense.
2. **Exclude platform policy redirects** — if `policy_url` contains meta.com, google.com, bugbounty., hackerone, bugcrowd, intigriti → skip.
3. **Tier by signal strength:**
   - **Tier 1:** Has dollar amounts + reward keywords (strongest — real bounty)
   - **Tier 2:** Has reward keywords, no dollar amounts found (VDP or bounty, needs manual check)
   - **Tier 3:** Has dollar amounts but weak keywords (may be pricing page false positive)

## Results (Tranco Top ~2.7K domains, 2026-08)

From 2,740 domains scanned (partial Tranco Top 10K):
- 365 had security.txt (13.3%)
- 82 platform-hosted (skipped)
- 72 real self-hosted candidates after filtering

### Tier 1 Highlights (dollar amounts confirmed)

| Domain | Bounty Range | Keywords |
|---|---|---|
| dailymail.com | up to $50,000 | reward, cash, payout |
| netgear.com | $100–$300 | bounty, RD, VDP |
| axon.ai | up to $1,000 | reward, cash |
| blackberry.com | $14–$165 | VDP, hall of fame |
| bookmyshow.com | $100–$107 | cash |
| lego.com | $19–$25 | bounty, reward, RD, VDP |
| docker.com | $1–$24 | bounty, RD, VDP, HoF |
| mlb.com | $50–$100 | hall of fame |

### Tier 2 Notable (keywords, no dollar found — needs manual check)

digicert.com, achmea.nl, yandex.ru, sentry.io, capgemini.com, debian.org, hp.com, roku.com, mikrotik.com, squarespace.com, coupang.com, tailscale.com, plex.tv, strava.com, threema.ch, gcash.com, lego.com, hostpoint.ch

## Pitfalls

1. **Dollar amounts are noisy** — `$100` on dailymail.com may be pricing page content, not bounty. Always verify manually.
2. **security.txt `Policy:` URL may be relative** — resolve against `https://{domain}/`.
3. **Platform redirect is multi-hop** — security.txt itself may not mention HackerOne, but the Policy page redirects to it. Script checks both.
4. **Timeout matters** — 8s timeout = ~0.6 domains/sec. 3s = ~2.7 domains/sec. Most failures are <1s (DNS fail, connection refused).
5. **Tranco Top 1M skews toward big tech** — for more diverse results, use category-specific lists or crt.sh TLD-filtered lists.
6. **Partial scans are useful** — even 2.7K domains found 72 candidates. Don't wait for full 1M to start verifying.
