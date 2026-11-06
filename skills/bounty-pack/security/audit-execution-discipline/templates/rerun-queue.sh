#!/usr/bin/env bash
# Sequential rerun of audit targets whose run directories were wiped (audit-execution-discipline §15).
# Copy, edit the QUEUE, then run:  bash templates/rerun-queue.sh
#
# Why sequential: this host has 6 GB RAM and parallel orchestrator runs get OOM-killed by
# Windows with no traceback (§9). One target at a time; each must exit before the next starts.
# Why quarantine: trackers/ survives a poc-plans wipe, so a "complete" tracker for a target whose
# directory is gone would make --resume skip 0A/0B whose artifacts no longer exist (§15.1).
set -u

PY="C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe"
SCRIPTS="C:/Users/WINDOWS10/AppData/Local/hermes/scripts"
PLANS="C:/Users/WINDOWS10/AppData/Local/hermes/poc-plans"
TRACK="C:/Users/WINDOWS10/AppData/Local/hermes/trackers"
LOGDIR="$PLANS/_rerun-queue"
mkdir -p "$LOGDIR"

# ---- EDIT ME: target | tech | scope -------------------------------------
# tech comes from trackers/audit-pipeline-<slug>.json or force-state-<slug>.json (§13.4).
# scope is the EXACT host — it is an exact matcher, not a suffix matcher (§0).
# Skip any target that is currently running; the SKIPPED guard below catches it anyway.
QUEUE=(
  "https://www.example.com|web2,nginx,php|www.example.com"
  "https://yandex.fr/|web|yandex.fr"
)
# -------------------------------------------------------------------------

echo "QUEUE START $(date '+%Y-%m-%d %H:%M:%S')  targets=${#QUEUE[@]}"
i=0
for entry in "${QUEUE[@]}"; do
  i=$((i+1))
  IFS='|' read -r TGT TECH SCOPE <<< "$entry"

  # dir slug: strip scheme, every non-alphanumeric -> _
  SLUG=$(echo "$TGT" | sed -E 's#^https?://##; s#[^A-Za-z0-9]#_#g')
  # tracker slug: only : and / -> _   (dots are KEPT — this differs from the dir slug)
  SAFE=$(echo "$TGT" | sed -E 's#[/:]#_#g')
  DIR="$PLANS/orchestrator-$SLUG"

  echo ""
  echo "=============================================================="
  echo "[$i/${#QUEUE[@]}] $TGT   tech=$TECH"
  echo "   dir  : orchestrator-$SLUG"
  echo "   track: $SAFE"

  NCNT=0
  [ -d "$DIR" ] && NCNT=$(find "$DIR" -type f 2>/dev/null | wc -l)

  # already running? match the slug in the cmdline, not the process name (§13.2)
  if tasklist /FI "IMAGENAME eq python.exe" 2>/dev/null | grep -q .; then
    if "$PY" - <<PYEOF
import sys, subprocess, re
slug = r"$SLUG".replace("_", "[._/]")
out = subprocess.run(["powershell","-NoProfile","-Command",
  "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'audit-pipeline-orchestrator' } | Select-Object -ExpandProperty CommandLine"],
  capture_output=True, text=True).stdout
sys.exit(0 if re.search(slug, out) else 1)
PYEOF
    then
      echo "   SKIP — a run for this slug is already live"
      continue
    fi
  fi

  if [ "$NCNT" -ge 50 ]; then
    echo "   SKIP — dir already has data ($NCNT files)"
    continue
  fi
  [ "$NCNT" -gt 0 ] && echo "   note — partial dir ($NCNT files), rerunning fresh"

  # quarantine stale tracker claims (§15.1): rename, never unlink
  for f in "$TRACK/audit-pipeline-$SAFE.json" "$TRACK/force-state-$SAFE.json" "$TRACK/$SAFE.json"; do
    if [ -f "$f" ]; then
      mv -f "$f" "$f.stale_wiped_$(date +%Y%m%d_%H%M%S)" && \
        echo "   quarantined: $(basename "$f")"
    fi
  done

  LOG="$LOGDIR/$SLUG.log"
  echo "   launching... log=$(basename "$LOG")  $(date '+%H:%M:%S')"
  cd "$SCRIPTS" || continue
  # -u : block-buffered stdout loses everything on a kill (§8)
  "$PY" -u audit-pipeline-orchestrator.py "$TGT" --tech "$TECH" --scope "$SCOPE" > "$LOG" 2>&1
  echo "   exit=$?   $(date '+%H:%M:%S')"
  sleep 20
done

echo ""
echo "QUEUE DONE $(date '+%Y-%m-%d %H:%M:%S')"
echo "--- final phase state (authoritative: trackers/phase-watch-state.json, §10) ---"
"$PY" - <<'PYEOF'
import json
p = r"C:\Users\WINDOWS10\AppData\Local\hermes\trackers\phase-watch-state.json"
try:
    s = json.load(open(p, encoding="utf-8"))
except Exception as e:
    print("  cannot read tracker:", e); raise SystemExit
for k, v in sorted(s.items()):
    print("  %-46s phase=%s complete=%s" % (k, v.get("phase"), v.get("complete")))
PYEOF
