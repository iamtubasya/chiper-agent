# Pool freshness fields + quarantine protocol (EW ingest)

## Fields EW ingest adds to `pool.json` domains

- `fresh_within_2m: <bool>` — COMPUTED (not hardcoded) from program-age signals:
  `wayback_first` (first Wayback CDX snapshot of the DISCLOSURE URL) + `securitytxt_expires`
  (`Expires:` from security.txt). See `fresh_within_2m()` in `search_scan.py`.
- `wayback_first: <YYYYMMDDHHmmss|"">` and `securitytxt_expires: <YYYY-MM-DD|"">` — the raw
  evidence, forwarded through `collect-search.json` → `pool_ingest.py` → pool record.
- `note: "EW search: program-age wayback=<ts> expires=<d> (fresh<=2bln DIUKUR dari umur
  program, bukan umur domain)"` — truncated to 28 chars in `pick`.
- `source: ew_search|ew_page|ew_securitxt|ew_feed` + `discovered_by: early-warning`.

`pool.py pick` renders `≤2bln✓(umur-program)` and `note:...`. `pick --new` =
`discovered_by == early-warning`.

## KEY RULE: measure program age, not domain age

Operator correction 2026-11-02: *"jangan skip karena domain lama; fokus ke program-nya."*
Reject a candidate ONLY when its PROGRAM is provably >2 months old — never because the domain
parked/was-registered long ago. Signals of program age:
- wayback first-snapshot of the DISCLOSURE URL >60 days ago → program old.
- security.txt `Expires:` already in the past → program ~1yr+ old.
If neither exists, default to candidate-new (don't discard a not-yet-indexed startup).

**Parking trap:** `cleanshot.com` root domain had a year-2000 wayback snapshot (parked),
but the *disclosure URL* snapshot was 2023. Snapshot the disclosure URL the dork returned,
never the bare domain root.

## Quarantine (reversible) — never hard-delete pool entries

Recipe (template: `~/AppData/Local/Temp/quarantine_stale_ew.py`, edit `BAD`/stale keys):

1. Select to purge by RE-PROBING program age (not by name blind): run `wayback_first` +
   `securitytxt_expires` + `fresh_within_2m` on each EW entry; purge those proven old.
2. Backup → `target-pool/backup/pool.bak_<ts>.json` (hard copy).
3. Move them → `target-pool/_QUARANTINE/ew_<reason>_<ts>.json` + `MANIFEST.txt` (count,
   reason, restore path, domain list).
4. Rewrite `pool.json` atomically (write `.tmp` then `os.replace`), append to
   `_quarantine_meta[]`.

Record each quarantine reason precisely. Restore = merge the quarantined `{domains:{}}`
back into pool.

## False positives are persistent without the right fix

The search cron re-ingested domains that had just been quarantined, until fixes landed in
`search_scan.py`:

1. **`www.` normalization** — `probe_url` must strip `www.` BEFORE the pool-dedup check, else
   `www.tcl.com` and `tcl.com` are treated as different domains and a re-run re-adds the one
   you just removed.
2. **MEGA_ORG blocklist (fallback only)** — mature mega-corp/gov/edu/IGO/vendor-mapan are
   "basi" even when their VDP is live (unesco.org, tcl.com, cidaas.com, exploitportal.com).
   Name-list is the FALLBACK; wayback/expires program-age is the primary signal. Full list in
   the parent SKILL.md.
3. **Homepage root rejection** — reject `path in ("", "/")`: mega-corp homepages mention
   "bug bounty" in a footer without being a program. Only accept real disclosure paths.

## Trap: security.txt is NOT the liveness probe for program pages

`/.well-known/security.txt` returned 403/404 for unesco.org, tcl.com, cidaas.com,
exploitportal.com — which made them look "dead". Their ACTUAL disclosure URLs were
`/en/vulnerability-disclosure`, `/legal/vulnerability-disclosure-policy`,
`/security/vulnerability-disclosure-policy`, `/responsible-disclosure` — all live 200.

Before calling a candidate dead/basi, probe the disclosure URL the dork actually returned,
NOT just `/.well-known/security.txt`. "No security.txt" ≠ "no program".