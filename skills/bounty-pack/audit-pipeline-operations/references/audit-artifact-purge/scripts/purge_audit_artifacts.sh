#!/usr/bin/env bash
# purge_audit_artifacts.sh — copy-and-edit purger for local audit RESULT data.
#
# Usage:  1) edit the items=( ... ) array below
#         2) bash purge_audit_artifacts.sh
#         3) read the manifest it prints at the end
#
# Safe by design: never globs. Delete = explicit item list only.
# Protected paths are asserted BEFORE any deletion; if one appears in `items`
# the script aborts so skills/toolkit/bundle can never be removed by accident.
set -u

MANIFEST="${LOCALAPPDATA:-/tmp}/Temp/audit_purge_manifest.txt"
: > "$MANIFEST"

# ---------------------------------------------------------------- edit this
items=(
  # C: drive — audit results / reports / loose scripts
  "/c/Users/WINDOWS10/nasa-vdp-recon"
  "/c/Users/WINDOWS10/nasa-cors-report"
  "/c/Users/WINDOWS10/nykaa_audit"
  "/c/Users/WINDOWS10/tv_recon"
  "/c/Users/WINDOWS10/fireblocks-bounty"
  "/c/Users/WINDOWS10/crowdproof-protocol"
  # D: drive — per-target progress + quarantined leftovers
  "/d/data hermes/bug-bounty/_progress/nykaa"
  "/d/data hermes/bug-bounty/_progress/capyfi"
  "/d/data hermes/_QUARANTINE/audit-purge-20260913-152009"
)
# ------------------------------------------------------------ end edit list

# capability that must survive — abort if any of these is in `items`
protected=(
  "/c/Users/WINDOWS10/AppData/Local/hermes/skills"
  "/d/data hermes/bug-bounty/bundle"
  "/d/data hermes/bug-bounty/_accounts"
  "/d/data hermes/bug-bounty/_toolkit-v2"
  "/d/data hermes/rpc"
  "/d/data hermes/kebersihan-sumatra"
)

freed_kb=0
ok=0
fail=0

size_kb() { du -sk "$1" 2>/dev/null | cut -f1 || echo 0; }

for p in "${items[@]}"; do
  for g in "${protected[@]}"; do
    case "$p" in
      "$g"|"$g"/*)
        echo "ABORT: '$p' is inside protected '$g' — refusing to run." | tee -a "$MANIFEST"
        exit 1;;
    esac
  done
done

for p in "${items[@]}"; do
  if [ ! -e "$p" ]; then
    echo "SKIP  (absent) $p" | tee -a "$MANIFEST"
    continue
  fi
  kb=$(size_kb "$p"); [ -z "$kb" ] && kb=0
  if rm -rf "$p" 2>/dev/null; then
    freed_kb=$((freed_kb + kb)); ok=$((ok + 1))
    echo "OK    $p  (${kb}K)" | tee -a "$MANIFEST"
  else
    # MSYS "Permission denied" on locked files -> native rmdir
    native=$(cygpath -w "$p" 2>/dev/null || echo "$p")
    if cmd /c rmdir /s /q "$native" 2>/dev/null; then
      freed_kb=$((freed_kb + kb)); ok=$((ok + 1))
      echo "OK    $p  (${kb}K via cmd rmdir)" | tee -a "$MANIFEST"
    else
      fail=$((fail + 1))
      echo "FAIL  $p" | tee -a "$MANIFEST"
    fi
  fi
done

echo "----------------------------------------"
echo "deleted: $ok   failed: $fail   freed: ~$((freed_kb / 1024)) MB"
echo "manifest: $MANIFEST"
