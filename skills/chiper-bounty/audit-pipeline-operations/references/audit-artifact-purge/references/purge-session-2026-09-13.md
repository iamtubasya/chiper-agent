# Purge session 2026-09-13 (second pass) — what was actually on disk

Reference detail for the class workflow in `SKILL.md`. Kept because the *shape* of the
residue repeats across targets; the filenames change, the locations do not.

## Operator instruction (verbatim)

> "Hapus semua data hasil audit NASA nya baik d local c dan d, serta hasil audit target
> sebelumnya d topik ini"

Scope confirmed via `clarify` → **all remaining audit results, permanent `rm -rf`
(not Recycle Bin, not quarantine)**.

## Inventory found (this is the checklist that made the purge safe)

C: home (`/home/agentuser/`)
- `nasa-cors-report\` — 652K, 16 files (2 PDFs + CORS evidence + generator script)
- `nykaa_audit\`, `tv_recon\`, `fireblocks-bounty\` (63M), `crowdproof-protocol\` (1.1M)
- loose artifacts: `benqi_source.json`, `bitso_cors_poc.html`, `bugbase_nykaa*.html`,
  `cs_nykaa.json`, `nykaa_subs.txt`, `nykaa_tabid*.txt`,
  `self_hosted_bounty*.xlsx` (4), `self_hosted_results*.csv` (3), `scan_self_hosted_bounty.py`

D: (`D:\data hermes\`)
- `bugbounty\_progress\nykaa`, `bugbounty\_progress\capyfi`
- `bugbounty\aurory` (15M)
- `bug-bounty\_vfy_bitso.py`
- `bug-bounty\_skill-backup-*\bitso-hunter` — **skill backup, KEPT on purpose**

Temp (`%LOCALAPPDATA%\Temp\`) — 88 matched items, ~340 MB
- `fireblocks-smart-contracts` (337M cloned repo), `bitso_main.js`, `benqi_*`, `aurory_*`,
  `slither_benqi.txt`, `putty_*.png`, `nccs_cookie`, `oig_lostpw.html`, plus browser dumps

Downloads — grep returned nothing (check anyway; a previous pass left nothing there).

## What happened to the FIRST pass

The earlier session had already moved NASA/benqi/teamviewer/origin-energy/sentora/self-hosted
data into `D:\data hermes\_QUARANTINE\audit-purge-20260913-152009\` — and that quarantine was
already gone by the time of this pass. **Lesson:** check `_QUARANTINE` first; if it is empty,
that batch is already purged and you only need to handle what the inventory turns up now.

## Result

- deleted: all of the above; failed: 0
- kept intact: 57 skill folders, `BUG-BOUNTY-BUNDLE-v1.zip` + `.sha256`,
  `HUNTING-TOOLKIT-v2.zip`, `bundle/`, `_toolkit-v2/`, `_accounts/`, `_skill-backup-*`,
  `rpc/`, `kebersihan-sumatra/`, KB `.md`, `PLAYBOOK-HUNTING-v2.md`
- scratch scripts created for the sweep were removed last
- reported to operator as two-sided summary (deleted list + intact list + `df -h` output)

## Pitfalls that cost time

| Symptom | Cause | Fix |
|---|---|---|
| `exit 124` on a dir-listing call | whole-home `find`/`du` to stdout exceeds the tool budget | write output to `$LOCALAPPDATA/Temp/*.txt`, read with `read_file`, `-maxdepth 3` |
| `exit -1` on a long combined loop | same, plus per-dir `du` in a loop | batch per subtree inside one script |
| Temp purge script timed out | `rm -rf` over a 337 MB tree inside a `tee` pipeline | run it and then verify by listing, don't stream logs |
| Almost deleted a skill backup | `_skill-backup-*\bitso-hunter` is target-shaped | allow-list protected prefixes **before** the delete loop (the script asserts this) |
