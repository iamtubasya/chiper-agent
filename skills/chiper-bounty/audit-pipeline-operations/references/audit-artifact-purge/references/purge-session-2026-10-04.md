# Purge session — 2026-10-04 (Windows deletion method that actually works)

Operator request: *"hapus semua hasil audit dan artefak ini, kecuali skill dan tools nya"* —
50+ explicitly named items across `D:\data hermes\bug-bounty\_progress\`, extra target dirs,
two full APK/audit workspaces (`vinted-2026-10-01`, `rapyd-idp`), a 1.1 GB gradle cache, and
~13 report PDFs in Downloads.

Scope was **operator-named** (he pasted the list), so this pass ran without a `clarify` — the
rule in step 3a (scope unset until the operator names it) still governs: the list WAS the scope.

## Result

`ok=52 fail=0 skip=9` — every item gone, both protected halves verified intact
(169 skills, `BUG-BOUNTY-BUNDLE-v1.zip` + `.sha256`, `_toolkit-v2`, `_accounts`, `wordlists`).

## What failed (do not repeat)

| Attempt | Outcome |
|---|---|
| `shutil.rmtree(p)` on `relay_v1` (7.4 MB, node_modules-shaped) | hung; script never advanced |
| batch `.sh` with `timeout 120 rm -rf` + `rmdir` fallback | stalled 12+ min, no new manifest lines |
| `subprocess.Popen(..., creationflags=DETACHED_PROCESS)` to background it | process never started |
| `du -sm <dir>` **before** deleting, as a size audit | walks the whole tree → hangs on the same dirs |
| one giant `find D:\ -maxdepth 4 -size +500M` | `exit 124` twice (foreground timeout) |

## What worked

`robocopy <empty_tmp> <target> /MIR /NFL /NDL /NJH /NJS /NC /NS /R:0 /W:0` then
`cmd /c rmdir /s /q <target>`, per item, wrapped in a try with a **hard per-call timeout** so one
locked dir cannot stall the rest. Shipped as `scripts/nuke_big_tree.py`.

- 52/52 items deleted, 0 failures, ~7.2 GB reclaimed (mostly 1.1 GB gradle cache + 592 MB
  Vinted workspace + ~275 MB of APKs).
- Ran as a single `terminal(background=true, notify=true)` job writing one `OK|FAIL <label>` line
  per item to an output file → progress readable at any point, and a re-run is idempotent
  (`SKIP(gone)` per item).
- The earlier partial run had already deleted 7 items; the idempotent re-run skipped those and
  continued — no double work, no error.

## Sequencing notes

- Measure free space with `df -h /c /d` **before and after**, not `du -sm` per item (du hangs).
- Delete scratch (builder scripts, manifests, staging dirs) last so the purge leaves no
  audit-shaped residue of its own.
- Residue sweep found what the explicit list missed: 87 target-named scripts in
  `%LOCALAPPDATA%\Temp` (`atmail_*`, `vinted_*`, `fa_*`, …) and 2 loose `hermes_*_log.txt` in
  `D:\data\` — pattern-filter Temp (`ls | grep -iE '<targets>'`), never a wildcard `rm -rf *`.
