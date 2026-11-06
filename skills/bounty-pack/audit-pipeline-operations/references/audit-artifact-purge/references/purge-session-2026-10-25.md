# Class purge 2026-10-25 — 4.56 GB / ~170k files, seven passes, three restore waves

Operator request, twice in one session: first *"hapus hasil audit yg ada di local C dan D,
pastikan hanya hasil audit aja, jgn hapus skill n tools"*, then — after the report —
*"Hapus quarantine"*. Both executed. This is the largest class purge on record and it is the
reference case for **over-capture**.

## Final numbers

| stage | items | files | bytes |
|---|---|---|---|
| P1 explicit dirs+files | 148 OK / 3 FAIL→husk-retry | 167 907 | 4 091 MB |
| P2 loose files (C:, D:, Temp) | 233 OK / 0 fail | 140 | 4.5 MB |
| P3 residue dirs | 38 OK | 1 057 | 65 MB |
| P4/P5/P6 tool-state + staged PDFs | 20 OK | 15 / 1 555 / 11 | 0.1 / 399 / 0.1 MB |
| **total moved** | **444 records** | **170 685** | **4 559.9 MB** |
| permanent wipe | 6 dirs, `failed=0` | 170 685 | 4 559.9 MB |

Disk after: C: 12 → 14 GB free, D: 8.2 → 13 GB free. Quarantine root `_QUARANTINE` removed
(nothing else lived there).

## What over-capture actually took (restore list, all returned)

Three restore waves were needed. Without them the operator would have lost capability, not
just results.

| restored | count | why it was swept |
|---|---|---|
| `ps3_*`, `ps4_*`, `ps_*` PortSwigger lab HTML | 82 | per-target page dumps use the same `ps`/`p` prefix |
| `wb_*` blog/cheatsheet HTML | 8 | looked like target shorthand |
| `defillama_*` program research (incl. 8.7 MB `defillama_raw.json`) | 14 | "program research for one bounty" ≈ output |
| `ld_*.png` LDPlayer game-automation screenshots | 75 | looked like evidence screenshots |
| `domains*.txt`, `top-1m.csv`, `nuclei-index.json`, `vrt*.json`, `poc-exploits-github-*.txt` | 14 | recon **inputs**, not outputs |
| `rpc_allowlist.json`, `gated.json`, `moneykit-openapi.json`, `qidelegate.json`, `gmx_test_account/pw.txt` | 6 | engagement **config/credentials** |
| `apkpure_*`, `loginapp*`, `p1-*`, `rgeo*` | 20 | unrelated personal-project dumps |
| generic probe scripts (`.py`/`.sh`) | 2 | `KEEP_EXT` guard caught most, not all |

**Root cause:** P2 matched on *basename patterns* over C: root and D: root. Every one of the
above shares a 2–4 char prefix with a real target. A prefix-only filter cannot separate them.

## Fix that should be in P2 from the start

```python
KEEP_EXT  = {".py",".sh",".ps1",".bat",".mjs",".ts",".exe",".zip",".tar",".gz",
             ".docx",".xlsx",".pdf",".md",".yml",".yaml",".toml",".key",".pem",
             ".session",".db"}              # never touched by a loose sweep
RESTORE_PREFIX = ("ps3_","ps4_","ps_","wb_","bl_","defillama_","rgeo",
                  "ld_","loginapp","apkpure_","p1-","solidity-flow","hacktricks")
```

`KEEP_EXT` alone saved every script, archive, doc and key file in the home dir. The
`RESTORE_PREFIX` list must be declared **before** the first move, not discovered afterwards.

## The three FAILs — all completed moves, only husks left

`ace-audit`, `ace-contracts-public`, `lit-audit` all reported
`PermissionError [WinError 5] … .git/objects/pack/*.idx`. Count check told the truth:

```
C:/Users/WINDOWS10/lit-audit              | src=29211 | dst=29256 | dst_exists=True
C:/Users/WINDOWS10/ace-audit              | src= 984  | dst=1006  | dst_exists=True
C:/Users/WINDOWS10/ace-contracts-public   | src=8878  | dst=8896  | dst_exists=True
```

`dst > src` with src still populated = **copy finished, delete failed** (Windows counts
differ by git-object hardlinks). The husks then cleared with the robocopy mirror-nuke in
61 s total. This is the same `shutil.move` = copytree-then-rmtree classification documented
in the main pitfall — but note the direction: here `dst > src`, not `dst == src`.

## Residue sweep — expect allowed hits, don't chase zero

Final regex sweep (depth 3, skipping `AppData|node_modules|.git|$RECYCLE.BIN|System Volume
Information|Program Files`) returned **0 hits** only after P3–P6. Intermediate runs returned
14, then 9, of which these were **legitimate and kept**:

- `wordlists/nordnet-paths.txt` — a wordlist, not output
- `kompetitor_quarterwise_bugbounty.xlsx` — competitor research spreadsheet
- `bug-bounty/_extract_bbskills` + `bbskills-extract-v2-clean-*.zip` — skill-extract bundles
- `~/.ghauri/<host>/` dirs — per-target tool state (these DID go, P6)

State the allowed residue explicitly in the report instead of sweeping it to reach a clean count.

## Protected-side verification (the half that matters)

20-item existence check after the wipe, all present:
`skills/` (187 dirs, 10 862 files) incl. `skills/security` + `skills/tob` ·
`BUG-BOUNTY-BUNDLE-v1.zip` + `.sha256` · `HUNTING-TOOLKIT-v2.zip` · `bundle/` · `reference/` ·
`wordlists/` · `target-pool/pool.json` · `portswigger-progress.json` · `tools/` ·
`nuclei-templates` · `poc-compact` · `pocindex` · `spyhunt` · `kebersihan-sumatra` ·
`telegram_scraper` · `.foundry` · `codeql` · `dsm-lab` · `check_basabasi_email.py` ·
`qw_chrome_cdp` · `chrome-cdp/start.sh` — plus the restored knowledge files.
Binary check too: nuclei/ffuf/sqlmap/dalfox/katana/gau/subfinder all still on PATH.

## Operator-facing report shape that landed well

Two-sided, grouped by artifact class, with the disk delta and a count-based verification line.
He replied with one instruction (`Hapus quarantine`) — no pushback, no "kamu sembarangan".
The post-move turn **offered** the wipe as a separate decision rather than doing it.
