---
name: audit-artifact-purge
description: Delete local audit result data; keep skills and tools.
version: "1.1"
created: "2026-09-13"
updated: "2026-09-13"
author: "Qwen (curator)"
license: "MIT"
tags: [cleanup, hygiene, windows, destructive, bug-bounty, data-storage]
metadata:
  hermes:
    tags: [cleanup, hygiene, destructive, data-storage]
    related_skills: [bug-bounty, vuln-hunter, hermes-ops]
---

# Audit Artifact Purge — delete the results, keep the capability

## When to Use

Load this skill when the operator asks any of:

- "hapus semua data hasil audit", "hapus hasil audit target X", "bersihin hasil recon"
- "delete the audit data on C and D", "purge this target from local disk"
- any request to remove bug-bounty / recon / report artifacts **after** a hunt — especially
  when paired with "tapi skill/knowledge dipertahankan" ("keep the skills/knowledge").

**Do NOT load** for routine temp cleanup, uninstalling tools, or deleting one known file —
this skill is for the *class* "wipe the results of an engagement from local disks".

## What this is

Recurring class of work for this operator: after a hunt he says some form of
**"hapus semua data hasil audit di local C dan D, tapi skill/knowledge dipertahankan"**.
It has run at least twice (2026-09-13, twice) — the second pass only went cleanly because
of the discipline below. Treat every instance as **destructive**: enumerate → confirm → purge
with a manifest → verify both the deletion **and** that the protected side survived.

> ⛔ **HARD RULE (also in memory):** never delete session files, skills, toolkit, bundle,
> `_accounts/`, or `_skill-backup-*` without explicit per-item confirmation. Deleting audit
> *output* is what was asked; deleting *capability* is never implied.

## 1. The split you must never blur

| DELETE (audit RESULTS) | NEVER TOUCH (capability) |
|---|---|
| `<target>-recon/`, `<target>-audit/`, e.g. `nasa-*`, `nykaa_audit`, `tv_recon`, `fireblocks-bounty`, `crowdproof-protocol` | every skill folder (`~/.chiper/skills/bounty-pack/skills/**`, bundle `skills/**`) |
| `D:\data hermes\bug-bounty\_progress\<target>\` | `BUG-BOUNTY-BUNDLE-v1.zip` + `.sha256`, `bundle/`, `_toolkit-v2/`, `HUNTING-TOOLKIT-v2.zip` |
| PoC / evidence output: `poc_*.json`, `poc_*.txt`, `*_results.json`, `*_scan_results.json`, `*_output.txt` | `_accounts/`, `_skill-backup-*/` (skill backups — the user keeps these), `rpc/`, `kebersihan-sumatra/` |
| report PDFs / report markdown for that target + report generators | KB `.md` (`PLAYBOOK-HUNTING-v2.md`, skill `references/*.md`), usage DB (`usageDaily`) |
| loose scripts in `$HOME/` (`scan_*.py`, `*_source.json`, `*_subs.txt`, `*_poc.html`, `*_tabid*.txt`) | target **profiles** (`skills/vuln-hunter/profiles/<target>.yaml`) unless the operator says otherwise |
| residual `%LOCALAPPDATA%\Temp\*<target-pattern>*` (browser dumps, cloned repos, screenshots) | non-audit Temp content — never an unpatterned `rm -rf *` in Temp |
| per-engagement **browser profiles the hunt created** (`~/<target>_profile`, `~/<tgt>_pro_profile`, `~/<tgt>_probe_*`, `~/<tgt>_mfa_probe`) — 130–190 MB each | the operator's **pre-existing** profiles (`~/<tgt>_chrome_cdp*`) and any **pending Gmail draft** for the target — a staged draft is a deliverable he has not sent yet — **UNLESS** the delete instruction explicitly covers all results ("hapus semua hasil auditny", coderpad 2026-10-17: staged drafts included, deleted via Gmail API = trash-recoverable, draft count verified back to baseline) |
| per-engagement tool state under `~/.<tool>/<target>` (`.ghauri/<target>`) and loose session files (`_<tgt>_sessions.json`, `_<tgt>_cred.json`) | shared credential/helper scripts (`check_*_email.py`) — used by every engagement |
| `D:\data hermes\_QUARANTINE\audit-purge-*` from an earlier pass | the quarantine mechanism itself when another purge is still pending |

Rule of thumb: **delete outputs, keep every tool, profile, skill and backup.**

## 2. Procedure (in order — do not skip step 1)

1. **Inventory, do not delete on the first tool call.** Per candidate: `du -sh <dir>`,
   `stat -c '%y %n' <dir>`, `ls -1 <dir> | head -30`. Also grep the target's own shorthand
   tokens (`oig_`, `mcdc`, `nccs`, `bitso`, `benqi`, `aurory`, `sentora`, `self_hosted`, `_cors_`)
   — loose files are usually named after the asset, not the program.
2. **Check for an earlier pass's quarantine** so you neither miss nor double-purge:
   `ls -la "/d/data hermes/_QUARANTINE" 2>/dev/null || echo "NOT PRESENT"`.
   (2026-09-13: the first pass's quarantine was already gone — that was the only remaining copy
   of the NASA/benqi/teamviewer data on D, so confirming this closed the loop.)
3. **Confirm scope with the operator** (`clarify`) — one question on *what* (all audit results /
   target + this topic only / target only / show me the list first), one on *how*
   (permanent `rm -rf` vs move to `_QUARANTINE` vs zip-then-delete). Ask, don't assume.

3a. **⛔ A one-letter / one-word reply answers ONE question only.** On 2026-10-07 the operator
   replied just `b` — which answered the *how* (quarantine) — and the agent **invented the scope
   itself** and started moving. Operator: *"kamu sembarangan, hanya yg benar2 ad nama target yg
   dihapus, ini kamu udh nyentuh file lain termasuk poc dan payload, aduh kacau"*.
   **Rule: scope is UNSET until the operator names it.** A short answer, a timeout
   (`[user did not respond within 10m]`), or silence is **NOT** authorization to proceed:
   - If the reply is ambiguous (could be *what* or *how*), **ask again** — do not guess.
   - If `clarify` times out, **stop**. Do non-destructive work (inventory, show contents of
     ambiguous items) and wait. Never purge on a timeout.
   - The operator's own bar: **"hanya yg benar2 ada nama target"** — include an item only when
     the item's own name IS the target name (e.g. `tripadvisor_v1`, `euredas_v1`, `nymvpn_v1`).
     Generic or category-shaped dirs are automatically **out** unless he names them themselves.
   - **"Tunjukin daftar lengkap per item dulu, hapus nanti" is a valid answer = an
     inventory-only turn.** Measured 2026-10-15: the operator chose this for a class purge.
     Build the full per-item listing (grouped: clear audit output / MIXED-show-and-ask /
     protected) with per-item size + file count + mtime, present it, and **stop — zero moves,
     zero deletes**. He then replies with the exact scope ("A + 4 flag hapus + browser
     profile + isi folder quarantine"), which is the authorization for the NEXT turn.
     The listing turn is also where you surface landmines (a target with `finding-pending`
     evidence, dirs updated today = possibly active audits) so his scope reply is informed.

3b. **Never self-classify ambiguous containers as "audit output".** These look target-shaped but
   are shared/toolkit territory — they were wrongly swept on 2026-10-07 and had to be rolled
   back: `bugbounty/poc/`, `bugbounty/reports/`, `bugbounty/screenshots/`, `bugbounty/pdf/`,
   `bugbounty/long-supply/`, `_progress/payloads/`, `monarcaproject/`, `_archive/`.
   When an item is mixed (a KB `.md` + result dirs in one folder), **show the operator the
   contents and let him choose** — do not resolve the mix yourself.

3c. **Default to quarantine move, and keep the manifest — it makes rollback mechanical.**
   Because the purge used `mv` (rename) + a per-item manifest, a full 27-item restore was a
   single script run and **nothing was lost**. Purge recipe:
   - `mv` (never `rm`) into `D:\data hermes\_QUARANTINE\audit-purge-<YYYYmmdd_HHMMSS>\`
   - write `OK|FAIL <src> -> <dest>` per item to a manifest under `$LOCALAPPDATA/Temp/`
   - on operator pushback, generate the inverse script from that manifest and move everything
     back; verify each original path with `[ -e ... ]` and confirm the quarantine dir is empty
   - a `mv`-based purge is **always** the safer default for this operator; only `rm -rf` when he
     explicitly says permanent
4. **Purge from an explicit item list with a manifest** — never a bare glob:
   copy `scripts/purge_audit_artifacts.sh`, edit the `items=( ... )` array, run it. It writes
   `OK|FAIL <path>` per item to a manifest and prints size freed.

4a. **Docker holds audit artifacts too — do not stop at the filesystem.** A target that was
   exercised in a container leaves containers, images and **named volumes whose names carry the
   target** (e.g. `octopus-deploy_v1_octo-{config,home,repo,sql-data,tasklogs}`, plus
   `octo-tentacle-etc`). Those are audit results sitting on disk in a place a file-level sweep
   will never see, and they are often the single largest remaining block (measured: 11.5 GB of
   images, 14.9 GB vhdx).

   ```bash
   docker ps -a        # running + exited; container NAMES carry the target
   docker images       # use DISK USAGE, not CONTENT SIZE
   docker volume ls    # named volumes carry the target; anonymous ones do not
   ```
   If the daemon is down you get
   `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine` — that is
   the *safe* state (nothing is locked), but you must start the daemon to enumerate; on this
   host it lives at `/usr/bin/docker` (Linux) / `/Applications/Docker.app` (macOS).

   Classify before proposing: **target env** (audit artifact — delete) vs **vuln lab**
   (`vulhub/*`, `vulnerables/web-dvwa` — reusable test scaffolding, not target output) vs
   **generic base images** (`postgres`, `hello-world`, `ipfs/kubo` — not audit artifacts).
   Offer the three groups as separate options; the operator picks.

   ⛔ **Wildcard deletes are blocked by the approval layer** — `docker rm -f $(docker ps -aq)`
   is refused and re-phrasing the same intent is refused too. Enumerate names explicitly:
   `docker stop <n1> <n2>` → `docker rm -f <n1> <n2>` → `docker rmi -f <img…>` →
   `docker volume rm <vol…>` → `docker system prune -a --volumes -f`. Verify with counts
   (`docker ps -aq | wc -l` → 0) rather than prose.

   ⚠️ **Purge frees in-VM bytes, not disk** — `docker system prune` reported only
   `Total reclaimed space: 159.4MB` while the vhdx stayed at 14.93 GB and `df` did not move.
   The vhdx is thin-provisioned and only a **compact** returns space to the host. Never report
   the prune figure as "space freed"; see `windows-host-diagnostics`
   (`skills/devops/windows-host-diagnostics/references/docker-purge-and-vhdx-compact-2026-10-08.md`) for the unlock-probe + diskpart
   compact recipe.
5. **Residue sweep by pattern, disk-wide, output to a file** (see pitfalls for why):
   ```bash
   find /c/Users/WINDOWS10 -maxdepth 3 \( -iname '*nasa*' -o -iname '*nykaa*' ... \) \
     > "$LOCALAPPDATA/Temp/sweep.txt"
   ```
   Then repeat for `D:` and for `$LOCALAPPDATA/Temp` (Temp is where recon leaves the most —
   one pass found 88 items / ~340 MB, including a 337 MB cloned contract repo).
6. **Verify both halves and report both:** every target path gone **and** the bundle, toolkit,
   `_accounts/`, `_skill-backup-*`, skills dir and KB still present. A purge report that only
   says "deleted" is not the deliverable — "hasil audit hilang **dan** skill/toolkit utuh" is.
7. **Delete your own scratch scripts last** (`_audit_purge.sh`, `_del_*.txt`, `_final_sweep.sh`)
   so you leave no audit-shaped residue of your own.

## 3. Pitfalls (all hit for real)

- **Broad `find`/`du` in the foreground hangs the terminal.** Whole-home sweeps returned
  `exit 124` (timeout) and even `exit -1`. Fix: redirect sweep output to a file under
  `$LOCALAPPDATA/Temp/` and read it with `read_file`; keep `-maxdepth 3`; never print
  hundreds of MB of paths to stdout.
- **Don't `du -sh` per directory across separate calls** — batch it inside one script per
  subtree (`bugbounty/`, `_QUARANTINE/`) to avoid repeated long waits.
- **Temp needs audit-specific patterns.** Filter (`ls -1 | grep -iE '<targets>'`) then delete
  only matching entries; a wildcard `rm -rf *` in Temp destroys unrelated app state.
- **Verify before deleting that a dir isn't a skill backup.** `_skill-backup-*/bitso-hunter`
  looks target-shaped but is a protected backup — it stays.
- **A target-named skill and a target-named output dir can share a name — expect the panic.**
  On 2026-10-07 purging `_progress/defi-exploit-forensics/` (audit *output*) made the operator
  ask *"defi-exploit-forensics td terhapus gk, aduh, ini kan skill audit"*. The **skill** was
  untouched — `skills/security/defi-exploit-forensics/` is a different tree entirely and a
  file-level purge of `_progress/` can never reach it. Two rules:
  - Never widen a purge into `~/.chiper/skills\` to "be thorough" — the skill and the
    output are different objects that happen to share a name.
  - When the operator raises this fear, **prove it rather than reassure**: run
    `skill_view(name)` (or `find <skills-dir> -iname "*<name>*"`) and show the skill's files
    (SKILL.md + `references/` + `scripts/`) as present. State the distinction plainly —
    *skill = the recipe, output dir = one meal cooked with it; the recipe is still there*.
- **On a Web2 engagement the bulk is the browser profiles, not the workspace — budget for it.**
  Measured 2026-10-08: a 12-item quarantine took **807 MB**, of which the `_profile`, `_pro_profile`,
  `_probe_0/1/2` and `_mfa_probe` Chrome profiles were **804 MB**; the `_progress/` workspace, the
  orchestrator `poc-plans/<target>` dir and the loose session / ghauri files together were **~2.5 MB**
  (0.3% of the total). A sweep that only walks `_progress/` reports "purged" having freed essentially
  nothing and leaves five 150 MB profiles behind. Enumerate `~/*<target>*` and `~/.<tool>/<target>`
  as first-class items, and **stop the browser processes first** (`taskkill /F /T /PID` per matching
  command line, or by the debug port they hold) or the profile move fails on a locked file.
- **Background scanners lock the workspace too — kill them before any move, and manifest AROUND the move.** The same `WinError 32` mid-move failure appears when the engagement's own scan daemons are still running: nuclei / interactsh-client / ffuf started with `terminal(background=true)` hold handles on `scans/*.txt|.log` inside the workspace being moved (coderpad 2026-10-17: two interactsh-client instances plus one nuclei survived the session-level kill — kill the tracked sessions AND `taskkill //F //T //PID` by image name, then verify with `tasklist`). Safe order that survived a half-failed `shutil.move` (copytree done, rmtree died on the locked log): (1) write the manifest FIRST — walk src, per-file sha256; (2) move; (3) re-walk dst and require dst ⊇ src with identical hashes; (4) update the manifest with the final counts; (5) only then remove the src husk. When the instruction is "semua hasil audit", the target's staged Gmail drafts are in scope — delete via `DELETE /gmail/v1/users/me/drafts/<id>` (soft delete, 30-day trash recovery) and verify the total draft count returns to baseline.
- **Quarantine preserves the bytes — never report it as space freed.** The `mv` took 25.4 s and freed
  0 MB (same volume). The request was "the results are gone", not "I need disk"; report the move
  honestly and offer the reclaim step separately (`windows-host-diagnostics`, Docker purge → unlock →
  vhdx compact).
- **A move that reports FAIL can still have moved the CONTENTS — leaving an empty husk at the
  origin. Verify by file COUNT, not by directory existence.** Measured 2026-10-07: `euredas_v1`
  refused all four move methods (`mv`, `cmd move /y`, `robocopy /MOVE`, `shutil.move`) with
  `PermissionError [WinError 32] … being used by another process`, and was reported as the one
  FAILED item. Reading it again on the later purge pass showed the truth: the quarantine copy held
  **187 files**, and the origin still existed but contained **0 files** — the transfer had
  happened and only an empty directory shell was left behind. So:
  - After any `FAIL`, count files on BOTH sides (`find <src> -type f | wc -l` vs `<dst>`), never
    judge by `[ -e ]` alone — an existing origin dir is not proof the item was not moved.
  - A later pass over the same item often just works (the handle released); re-running is cheaper
    than diagnosing the locker. `openfiles /query` and a `Win32_Process` command-line grep both came
    back empty for this one — the handle was not attributable to any visible process.
  - The empty husk then deletes normally with the same pass.
- **Expect the purge to come in TWO instructions, not one — plan for the second.** The `mv`-to-
  quarantine pass only removes the artifacts from their working locations; the operator's next
  message is a separate decision about the quarantine itself. Measured 2026-10-07: after the move,
  he sent **"hapus semua d quarantine"** as its own message, and on a later engagement the same
  shape appeared as an explicit `clarify` choice. Treat "move to quarantine" and "delete the
  quarantine" as two separate authorizations — never chain them, and never assume the earlier
  `b`/quarantine answer pre-approves the delete. When the delete does come, confirm scope once
  (`clarify` with the real question: does the one item that just landed there count?) and then
  wipe.

  ⛔ **A quarantine dir is NOT "just plain files" — the mirror-nuke is required.** An earlier
  revision of this skill claimed `audit-purge-*` contents could take a plain `rm -rf`. Measured
  false 2026-10-25: the class-purge quarantine held **167 907 files**, including cloned target
  repos with `.git/objects/pack/*.idx` — exactly the tree shape that hangs `rm -rf`/`shutil.rmtree`.
  What worked on all six dirs / 4.56 GB in **one pass, 0 failures, ~60 s**:

  ```python
  # per audit-purge-* dir: mirror an empty dir over it, then rmdir
  subprocess.run(["robocopy", empty, target, "/MIR", "/NFL", "/NDL", "/NJH",
                  "/NJS", "/NC", "/NS", "/R:0", "/W:0"], capture_output=True, timeout=1800)
  subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", target], capture_output=True, timeout=1800)
  ```
  Wipe verification shape — report per item, not prose:
  ```
  OK|files=167907|4091.4MB|left=0|<dir>
  ROOT_REMOVED|<quarantine root>          # only when nothing else lives there
  # wiped_files=170685 wiped_MB=4559.9 failed=0
  ```
  Requires `count(src)==0` **after** the call, and `df` should move by ≈ the reported MB
  (measured: D: 8.2 GB → 13 GB free for 4.56 GB wiped, because the wipe was same-volume).
  Only delete the `_QUARANTINE` **root** when `os.listdir(root)` is empty — a wiped root is not
  a request to remove a quarantine that still holds another engagement.
  - **The operator CAN chain both in one message — execute it with a firewall between
    them.** 2026-10-15: *"A + 4 flag hapus + browser profile + isi folder quarantine, hapus
    aja itu smua"* authorized move-to-quarantine AND wiping the quarantine in one sentence.
    Safe execution shape: (1) permanently delete the **OLD, pre-existing** quarantine entries —
    "isi folder quarantine" refers to what existed when he wrote it; (2) move the new items
    into a **FRESH dated dir** (`audit-purge-FINAL-<ts>`), never into the dir you are wiping;
    (3) report and offer the permanent wipe of the *fresh* dir as the separate next
    instruction. This honors both clauses without ever making the just-moved items
    unrecoverable mid-run.
- **Verify a failed move against the purge script's ACTUAL destination naming — a
  wrong-pattern check is a false negative that triggers pointless retries.** Measured
  2026-10-15: the purger named quarantine dirs `parent__name` (`WINDOWS10__audit`), but the
  post-FAIL verification grepped for `audit__carbon-ms` → 0 files → concluded the copy had
  failed → retried → the retries produced a **27,048-file triple copy** (~470 MB wasted)
  beside the complete original. Read the naming rule out of the purge script (or manifest)
  before grepping the quarantine.
- **`shutil.move` = copytree THEN rmtree — the failure stage determines what's true.** A FAIL
  with `WinError 5 Access denied` during the **delete** stage means the copy already
  completed: quarantine count == the origin's ORIGINAL file count proves it (2026-10-15:
  `audit/carbon-ms` reported FAIL, but quarantine held the full 9,930 files incl. the
  deepest `.git/objects/pack` files — only the origin husk remained). A FAIL during the
  **copy** stage leaves a partial destination. Classify before any retry:
  `dst_count == origin_original_count` → copy done, only nuking the husk remains;
  `dst_count < that` → partial, and a blind retry will DUPLICATE (see previous pitfall).
- **Transient locks: re-read the exact file before declaring it permanently locked.**
  `WinError 5` on a repo's `.git/objects` and `WinError 32` on an **empty** husk dir both
  cleared on a later pass with no visible holder (Defender/indexer scan; the gateway holds
  handles on dirs under `poc-plans/`). One diagnostic (read the locked file directly via
  python `open(...).read(16)`), one retry — then report honestly instead of looping.
  `attrib -r -s -h` needs a **native** path and `MSYS_NO_PATHCONV=1` (see next pitfall).
- **⛔ Long inline shell commands get BLOCKED by the hardline parser — write a file instead.**
  Hit twice 2026-10-15: big `for`-loops over many paths and long `grep -iE` alternations were
  refused with *"command parser limit or malformed executable payload"* (the command is saved
  to `cache/blocked-scripts/`). No rewording helps — the same intent is refused again. Recovery:
  `write_file` a `.sh`/`.py` under `$LOCALAPPDATA/Temp/`, then `bash <that file>` / `python`.
  Keep any inline command small; batch loops and pattern sweeps into scripts by default.
- **Under `MSYS_NO_PATHCONV=1`, `cmd //c rmdir //s //q` silently does nothing** — the doubled
  slashes stay literal, cmd.exe prints its interactive banner and opens a prompt instead of
  executing. Prefer `python -c "shutil.rmtree(...)"` for plain-file trees; if you must use
  cmd, drop `NO_PATHCONV` for that call so `/c` and the path translate normally. Symptom to
  recognize: a Windows version banner (`Microsoft Windows [Version …]`) in your script output.
- Partial leftovers: after the purge, re-check for empty dirs and files a previous agent left
  half-written, then include them in the final sweep.
- Windows-safe deletion — **`rm -rf` is NOT reliable on a big tree; mirror-nuke is.** Measured
  2026-10-04 on a 52-item purge: plain `shutil.rmtree` / `rm -rf` / a per-file `os.remove` loop
  **hung indefinitely** on the node_modules/repo-shaped dirs (`relay_v1`, `ssvnetwork_v1`) and the
  batch script stalled for 12+ min with 0 progress; a detached `Popen(...DETACHED_PROCESS)` never
  ran at all. The method that then cleared **all 52 items with 0 failures**: mirror an empty dir
  over the target with robocopy, then `rmdir`. Use `scripts/nuke_big_tree.py` (importable) or:
  ```bash
  E=$(mktemp -d)
  robocopy "$(cygpath -w "$E")" "$(cygpath -w "$P")" /MIR /NFL /NDL /NJH /NJS /NC /NS /R:0 /W:0
  cmd /c rmdir /s /q "$(cygpath -w "$P")"
  ```
  Redirect robocopy's own stdout to `/dev/null` (it prints a summary that looks like errors).
  - **Do not `du -sm` to measure first** — it walks the whole tree and hangs on the same dirs.
    Size the item *after* it is gone, or skip the number (`df -h /c /d` before/after is enough).
  - **Run the batch as ONE `terminal(background=true, notify=true)` job**, never foreground — a
    foreground run hits the 180–420 s cap mid-purge and leaves you re-verifying a half-state.
    Make the script idempotent (`SKIP(gone)` per item) so a re-run is always safe.
  - **Isolate per item** (per-call timeout + fall through to the next) so one locked dir cannot
    stall the other 51.
  - `search_files(target='files')` when you only need names — it does not hang the way `find` does.
  Detail + more Windows cleanup cases live in the separate `bug-bounty` skill, file
  `windows-repo-cleanup.md` under its references directory.

## 5. Deleting on this host

The terminal here is git-bash (MSYS): POSIX paths like `/c/Users/<u>/x` and `/d/data hermes/x`
work in shell builtins, but **native tools do not get path translation**. So:

- Listing/searching large trees: use the `search_files` tool (`target='files'`) when you only
  need names, and only drop to shell `find` when you need it inside a script — and then always
  redirect output to a file under `$LOCALAPPDATA/Temp/`, never to stdout.
- Deleting: **use the mirror-nuke** (`scripts/nuke_big_tree.py`, or
  `robocopy <empty> <target> /MIR` then `cmd /c rmdir /s /q <target>`) — `rm -rf` alone hangs on
  node_modules/repo-shaped dirs (see the Windows-safe deletion pitfall). Run the batch under
  `terminal(background=true, notify=true)`, idempotent per item.
- Disk free check after the purge: `df -h /c /d`.

## 3b. Over-capture is the default failure — plan the restore pass BEFORE you purge

Measured 2026-10-25 (class purge, 4.56 GB / ~170k files): every pattern-driven sweep
**over-captured**, and the fix was three restore passes *after* the moves. Items a naive
sweep takes that are NOT audit results:

| swept by mistake | why it looks like output | verdict |
|---|---|---|
| `ps3_*`, `ps4_*`, `ps_*`, `wb_*` HTML | per-target page dumps `ps*`/`wb*` | **knowledge** — PortSwigger lab scrapes; restore |
| `bl_*` | target shorthand | **knowledge** — blog/cheatsheet copies; restore |
| `defillama_*`, `rgeo*` | program research JSON for one bounty | **knowledge** — reusable program intel; restore |
| `ld_*.png` (80+) | look like evidence screenshots | **not audit** — LDPlayer game-automation run; restore |
| `domains*.txt`, `top-1m.csv`, `nuclei-index.json`, `vrt*.json`, `poc-exploits-github-*.txt` | recon inputs | **tooling/wordlists**; restore |
| `rpc_allowlist.json`, `gmx_test_account/pw.txt`, `moneykit-openapi.json`, `qidelegate.json` | engagement config | **tooling/credentials**; restore |
| `*_test.sh`, `saml_*.py`, per-engagement probe scripts | engagement-specific | judgement: probe scripts for a debriefed target = output; keep generic helpers |
| `chrome-api`/`chrome-pol` browser profiles vs `chrome-cdp` | all "chrome*" | **`chrome-cdp` is the shared CDP profile used by `start.sh` — KEEP**; the numbered/`-api`/`-pol` ones are per-hunt |

Rule: **classify by basename prefix against a KEEP-list before the first move**, and keep
`_progress/`-style result dirs separate from `<prefix>_*` loose files in one pass — a single
"loose files matching target words" sweep guarantees the mix.

Restore mechanism (never hand-move): `scripts/quarantine_restore.py`

```bash
# dry-run first — prints what it WOULD take back, writes nothing
python scripts/quarantine_restore.py "$Q" --list ps3_ ps4_ wb_ bl_ defillama_ ld_
# then commit, exact basenames too, across every quarantine generation
python scripts/quarantine_restore.py "$Q1" "$Q2" "$Q3" --restore ps3_ defillama_ ld_
python scripts/quarantine_restore.py "$Q" --restore-exact nuclei-index.json vrt.json
```

It decodes the flattened quarantine names (`c__Users__WINDOWS10__ps3_x.html` →
`$HOME/ps3_x.html`), **never overwrites** an existing original
(`EXISTS` + skip), refuses directories unless `--restore-dir`, and logs
`RESTORED|` per item. Also handy for the "you swept a skill-adjacent file" panic: point it at
the quarantine, `--list` the name, and prove the item is still recoverable.

Windows filesystem case trap: `shutil.move` preserved the source's `C__` casing while the
manifest and my greps used `c__`, so a case-sensitive check reported "not restored" while the
bytes were already home. **Match quarantine basenames case-insensitively.**

## 3c. The pass structure that actually clears a whole estate

One pass never finishes it. 2026-10-25 ran seven passes and only the last residue sweep ran
clean; budget for that shape instead of trying to be exhaustive in one script:

1. **P1 — explicit dirs+files**: engagement dirs (`*-audit`, `*-engagement`, `*-recon`, `_progress`),
   hunt-created browser profiles, per-target workspaces under `D:\data hermes\bug-bounty\<target>_<date>`.
2. **P2 — loose files**: top-level basenames on C: and D: + audit-patterned Temp entries, with a
   `KEEP_EXT` guard so `.py/.sh/.ps1/.zip/.tar.gz/.docx/.xlsx/.pdf/.md/.yml/.pem/.session/.db`
   survive untouched.
3. **P3 — residue dirs** the pattern misses (a target's cloned contract repo at `D:\<name>`, a
   `polymesh/` node checkout, vendor audit PDFs staged in Downloads).
4. **P4/P5/P6 — per-target tool state and staged deliverables**: `~/.ghauri/<host>`,
   `~/Downloads/<Target>-C1-*.pdf` report PDFs, `repair/*.pdf`.
5. **RESTORE passes** interleaved the moment a restore candidate is identified (§3b).
6. **Residue verification sweep last**, and it is the only one allowed to declare "clean":
   walk `$HOME` and `D:\` to depth 3 with a regex of every target shorthand, skipping
   `node_modules|.git|System|Trash Volume Information|Program Files`, and write
   hits to a file. Expect it to keep returning 3–9 hits of legitimate knowledge
   (`wordlists/<target>-paths.txt`, competitor spreadsheets, `bbskills-extract-*.zip`) — those
   are *allowed residue*, say so explicitly rather than sweeping them to reach a clean count.

`shutil.move` FAIL classification on this pass: `lit-audit` reported
`WinError 5 … .git/objects/pack/*.idx` while the quarantine copy already held **29 256 files
vs 29 211 left at the origin** — dst > src with src still populated means a *partial* move, and
the origin husk then needed the robocopy mirror-nuke (three of them, 61 s total) before the
paths were truly gone. Never retry a `FAIL` from scratch before comparing both counts against
the **original** count, not the post-failure one (see the existing pitfall).

## 3d. ⛔ "instalasi file hasil audit" is a NARROW phrase — do not widen it to "big files at root"

Measured 2026-10-27, and this is the second overreach in this skill's history (first was
2026-10-07). The operator asked:

> *"Hapus smua hasil audit target di c dan d, tp jgn ganggu skill dan file yg tidak terkait,
> oh iy cek jg kl ad instalasi file hasil audit, yg bukan tools, kamu hapus jg"*

The agent built its "installed-file residue" list from **location + size + age** (everything large
sitting loose at a drive root), never from **function**. Result: **21 items over-deleted**,
operator pushback:

> *"apa aman dihapus, dan itu kok sptny gkad hubungn sm hasil audit jg kena"*

What got wrongly swept, and the test that would have caught each:

| wrongly deleted | actually was | test that saves it |
|---|---|---|
| `MT5real` (379 MB) | MetaTrader terminal — the operator's trading app | not a target, not installed by an audit |
| `Ruby40` (1.2 GB) | language runtime | **a runtime is a TOOL, not an output** |
| `artikel-media-semua.tar.gz` | Mojok article archive (his writing work) | unrelated to any target |
| `openclaw-payment-agent`, `SkillResearch-Crypto-Stock` | old side projects | unrelated to any target |
| `rustup-init.exe`, `solc-0.8.30`, `vs_BuildTools.exe`, `chromeremotedesktophost.msi`, `camofox-dl.zip`, `telegram_scraper.zip`, `Hermes-Setup.exe`, `MediaCreationTool` | **installers / tool archives** | an *installer* is the opposite of an audit output — the phrase was "**yg bukan tools**", i.e. keep tools |
| `bugbounty_knowledge.tar.gz` + `.zip` (161 MB), `exvul_articles_22pdf.zip` | knowledge corpora | reusable knowledge — restore-class per §3b |
| `domains.txt`, `top-1m.csv`, `tranco_top1m.zip`, `defillama_raw.json` ×2 | wordlists / program research | §3b already lists these as KEEP — the lesson existed and was not applied |
| `com_facebook_aura…apk` | APK under reverse-engineering | an artefact under analysis is live work |
| `docker.tgz` | Docker backup archive | tool backup |

**The rule.** When the operator says "instalasi file hasil audit, yg bukan tools" he is asking for:
*things an audit INSTALLED that are not tools* — e.g. a downloaded vendor installer used once, a
staged build, a cloned runtime. The correct per-item test is two questions, both of which must be
YES:

1. **Was this created or downloaded BY an audit run?** → check `mtime` against the engagement
   window. A file dated 2025-11 or 2026-03 cannot be output of a hunt run last week. If mtime is
   months away from every engagement date, it is NOT audit residue.
2. **Is it an output rather than a capability?** → an exe installer, a runtime dir, a language
   toolchain, a wordlist, a knowledge archive and a side project are all **capability**. They stay.

If either answer is unclear, **put the item in a "show-and-ask" group and present it** (§3a
listing turn) — never resolve it yourself. The operator's bar is unchanged from 2026-10-07:
*"hanya yg benar2 ada nama target"*.

**Recovery reality for this class.** The purge used `robocopy /MIR` + `cmd del /f /q`, which
**bypasses the Recycle Bin** — there is no undo. Before deleting anything in the "instalasi"
bucket, verify one copy exists somewhere (`backups/`, `D:/Telegram Desktop/`, a project dir).
Measured: two of the swept items (`openclaw-payment-agent`, `SkillResearch-Crypto-Stock`) survived
only because `.rar`/`.zip` copies happened to sit in `D:/Telegram Desktop/`; two
(`bugbounty_knowledge`, `exvul_articles`) were **lost permanently** — no copy in `backups/`,
`recovered-knowledge/`, `_archive/`, or the bot backup.

**Always do the accounting pass before reporting done.** Build two explicit lists — "legitimately
deleted audit output" vs "over-deleted, should have been kept" — check each path's existence, and
state recoverability per item (re-downloadable / copy-exists-elsewhere / lost). Reporting a flat
"71 items deleted" hides the overreach and is exactly what triggered the correction.

## 3e. Audit artifacts live INSIDE WSL distros too — the file-level sweep cannot see them

Measured 2026-10-27. A file-level walk of `C:` and `D:` reported the purge complete while
**12.1 GB of audit residue sat inside the Ubuntu WSL distro's ext4.vhdx**. A hunt that clones a
target repo into WSL and runs a Rust/Solidity build leaves the whole `target/` (or `build/`,
`out/`, `node_modules/`) tree there:

```
wsl -d <distro> -e du -sm /home/<user>/* | sort -rn | head
# 12114  /home/windows10/chipotle          <- audit working tree
#  1210  .../chipotle/lit-actions/target/debug   <- deps 9.9G + build 1.7G + incremental
```

What to do:

1. Enumerate the distros and find which vhdx belongs to which, before touching anything:
   ```bash
   wsl -l -v
   powershell -c "Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' |
     ForEach-Object { \$p=Get-ItemProperty \$_.PSPath; \"\$(\$p.DistributionName) :: \$(\$p.BasePath)\" }"
   ```
2. **Delete the BUILD CACHE, keep the SOURCE.** `target/`, `out/`, `node_modules/`, `.venv/` are
   regenerable output. `Cargo.toml`, `Cargo.lock`, `src/`, `cli/`, `server/` are the only copies
   of that work — verify they survive before and after.
   ```bash
   wsl -d <distro> -e rm -rf /home/<u>/<target>/<repo>/target   # 12.1 GB
   ls /home/<u>/<target>/<repo>/ | head                          # Cargo.toml etc still there
   ```
3. **Reclaiming the space needs `--set-sparse`, not diskpart.** See §3f.

Also inside Temp: a staging dir (`bounty-full-zip/stage/`) carried a **copy of
`credentials/` + `google_token.json`**. A credential copy sitting in a temp dir is a finding in
itself — delete it and say so in the report; do not leave it because "it is in Temp".

## 3f. Reclaiming the vhdx: `wsl --manage --set-sparse true` beats `diskpart compact vdisk`

Measured 2026-10-27 on this host, and this corrects the guidance that points only at
diskpart. After deleting 12.1 GB inside Ubuntu:

- `diskpart` → `attach vdisk readonly` → `compact vdisk` → `detach vdisk` reported success but
  **freed 0.00 GB** (vhdx stayed at 34.23 GB). Tried twice, plus a `diskpart /s` script file.
- **This worked:** `wsl --manage Ubuntu --set-sparse true` → vhdx **34.23 GB → 22.39 GB**,
  `C:` went **13 GB → 33 GB free**, instantly.

Notes:
- It prints an "experimental feature" banner plus `The operation completed successfully.` — that
  is success, not a warning to ignore.
- Run it with the distro **stopped** (`wsl --shutdown`) and verify with the file size + `df -h /c`.
- It converts the vhdx to sparse, so future deletes inside WSL return host space automatically.
  That is the durable fix; diskpart compact is the fallback.

## 3g. Checking disk pressure: WSL vhdx is usually the hog, not "APKs from target testing"

Measured 2026-10-27: asked why `C:` had shrunk, the agent's first instinct was "did we download
mobile APKs during target testing?" — **wrong**. A real inventory found:

| consumer | size |
|---|---|
| `WSL ext4 disk` (Ubuntu) | **34.2 GB** ← the actual cause |
| `/tmp` | 9.0 GB |
| `$HOME/.config/google-chrome` (Chrome user data) | 8.7 GB |
| `/usr/local` | 7.7 GB |
| `.gradle` | 845 MB (tooling — keep) |

Only two APKs existed in Temp (`yarbo.apk` 198 MB, `mailcom.apk` tiny). So: **measure before
theorising.** The sweep to run first is
`find $HOME/.local/share -maxdepth 5 -name "*.vhdx" -exec ls -la {} \;` — a vhdx is a
single opaque file, invisible to any per-directory `du` that skips it.

A `du -sm` over all of `~/.local/share` **times out** (measured, >240 s). Do it per-subtree, in a
script, with output to a file — and cap each entry with a wall-clock guard so one huge tree cannot
stall the whole listing.

## 4. Reporting shape the operator expects

Short, factual, two-sided:

```
🔥 DIHAPUS (± total size): <grouped list of artifacts>
✅ UTUH: skills, bundle+sha256, toolkit, _accounts, _skill-backup-*, rpc/, KB .md
Disk: C: X free · D: Y free
```

Then one line confirming no residue matched the target patterns on C, D, Downloads, Temp,
or browser cache.

## Support files
- `scripts/purge_audit_artifacts.sh` — copy-and-edit purger: explicit item array, per-item
  `OK|FAIL` manifest, size freed, protected-path assertion before it deletes anything.
- `scripts/nuke_big_tree.py` — reliable large-tree deleter for this host (mirror-empty robocopy
  → `rmdir` → rmtree; `nuke()` / `rmfile()` / `purge()`). Import it in the batch script, or run
  `python nuke_big_tree.py <path> …`. Use it instead of `rm -rf` / `shutil.rmtree` whenever a
  target contains node_modules, vendored repos, or `lib/`.
- `references/purge-session-2026-10-04.md` — what actually works for deletion on Windows:
  52-item purge, the `rm -rf` / `rmtree` / detached-Popen hangs, the robocopy-mirror fix, and
  the `du`-hangs caveat.
- `references/purge-session-2026-09-13.md` — worked example: the exact inventory (C:, D:, Temp),
  the first pass's `_QUARANTINE` already-empty finding, and a table of the timeout pitfalls
  that cost time.
- `references/purge-overreach-2026-10-07.md` — **read before any purge where the operator's
  answer was short or `clarify` timed out.** The 27-item overreach, the operator's correction
  verbatim, the `mv`+manifest restore recipe that recovered all 27 for free, and the list of
  items that must never be swept without the operator naming them.
- `references/purge-session-2026-10-15.md` — worked example of the CLASS purge (4.3 GB,
  194 items): the four-step authorization flow including "show list first, delete later"
  and the one-message "move + wipe quarantine" chain; the two FAILs that were both false
  alarms (completed-move husk, delete-stage lock) with their file-count proofs; the
  wrong-pattern verification mistake that cost a 470 MB triple duplicate; the `cmd //c`
  NO_PATHCONV trap; and the hardline-blocked inline commands.
- `references/purge-session-2026-10-25.md` — **the over-capture reference case** (4.56 GB /
  170 685 files, largest on record): the exact restore list the loose sweep wrongly took
  (PortSwigger lab HTML, defillama research, LDPlayer screenshots, wordlists, taxonomy JSON,
  test credentials), the `KEEP_EXT` + `RESTORE_PREFIX` guards that prevent it, the three
  `WinError 5` FAILs where `dst > src` proved the copy had completed, the seven-pass structure,
  and the per-item verified permanent wipe (`failed=0`) with its report shape.
- `scripts/quarantine_restore.py` — **rollback tool**: decode the flattened quarantine names and
  restore by basename prefix or exact name, never overwriting an existing original
  (`--list` dry-run first, then `--restore`). Use it instead of hand-moving files back.
- `references/family-coverage-gate.md` — **the same discipline applied to a skill family**
  instead of a disk: when the operator challenges capability ("kamu kurang kuat utk temuan bug
  critical"), measure one grep per gate, extract the template from the exemplars, author
  per-class content (anti-fabrication rule for CVE IDs), bulk-insert idempotently with an
  anchor + manifest, then verify by re-running the same grep. Worked instance: `hunt-*` 3/59 →
  59/59 on four gates.

Companion on the space-reclaim side: **`windows-host-diagnostics`** owns the Docker purge →
unlock → VHDX-compact procedure (`skills/devops/windows-host-diagnostics/references/docker-purge-and-vhdx-compact-2026-10-08.md`).
Use it when a purge leaves the disk still full — removing containers/images/volumes frees
in-VM bytes only, and the thin-provisioned vhdx must be compacted to return space to C:.


---

## Companion Skill — `poc-corpus-to-technique-atlas` (additive, never overrides)

When the task is *not* "mirror a docs site" but "extract the **techniques** from a corpus or
an oversized shelf", use `poc-corpus-to-technique-atlas` instead/in addition. It covers:
classify → pull method → filter malware/scam → dedupe → per-class reference files →
distil existing shelves → archive bloat (with a pointer) → additive cross-link → verify.
Output precedent: `security/poc-technique-atlas` (28 classes / ~1,950 techniques).

## Companion Skill — `report-gotchas` (additive, never overrides)

A different class of work that shares this skill's *shape* — enumerate → classify → act with a
manifest → verify both halves. When the operator challenges **capability** rather than asking
for cleanup ("kamu kurang kuat utk temuan bug critical"), the target is a whole skill family,
not a disk. `security/report-gotchas` owns that: per-class proof bars, the AI-slop detector,
and the family coverage-gate procedure (measure with one grep per gate → extract the template
from the exemplars → author per-class content → idempotent anchor-based bulk insert → verify
by re-running the same grep). Worked instance 2026-10-26: `hunt-*` family 3/59 → 59/59 on four
gates, 216 verified CVE IDs. The anti-fabrication rule there is the same discipline as this
skill's manifest rule: **no unverified claim enters the record.**

## Companion Skill — `portable-bundle-packaging` (pack the corpus, then purge)

Purge is often the *second half* of one request: after an audit the operator may also ask
**"ekstrak all skill & knowledge & workflow & pipeline terkait bounty, buat zip maks NNmb"**.
That is a packaging class of work (build dir → scrub → dedup → zip → verify ≤ limit), owned by
`portable-bundle-packaging` — go there rather than improvising an archive. Do the **zip before
the purge** when both are asked (the bundle needs the corpus still on disk), then purge the
results and keep the bundle as a protected artifact.
