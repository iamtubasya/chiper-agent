#!/usr/bin/env bash
# sqlmap_verdict.sh — decide whether a scanner negative on a WAF-fronted target is real.
#
# Usage:
#   sqlmap_verdict.sh <url-with-params> <header-file> [outdir]
#
#   <header-file>: a file holding ONE header line, e.g.
#       Authorization: Bearer <key>
#     Kept in a file on purpose so no credential is embedded in this script or in shell history.
#
# Why this exists (learned the hard way):
#   A "no injection found" sqlmap run once logged 3,742 x HTTP 403. The 403s were NOT payload
#   filtering — the edge was blacklisting sqlmap's own User-Agent, so the application never saw a
#   single probe. Step 1 below is the diagnosis; do it before reading any scanner verdict.
#
# Exit: 0 = verdict captured (read the greps), 2 = usage/IO error.
set -u

URL="${1:-}"
HDRFILE="${2:-}"
OUT="${3:-sqlmap_verdict_out}"

if [ -z "$URL" ] || [ -z "$HDRFILE" ]; then
  echo "usage: $0 <url-with-params> <header-file> [outdir]" >&2
  exit 2
fi
[ -f "$HDRFILE" ] || { echo "header file not found: $HDRFILE" >&2; exit 2; }

BROWSER_UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
SCANNER_UA='sqlmap/1.9#stable (https://sqlmap.org)'
HDR="$(tr -d '\r\n' < "$HDRFILE")"
mkdir -p "$OUT"

echo "=== step 1: the diagnostic that matters — is the TOOL'S OWN UA the block? ==="
code_tool=$(curl -s -o /dev/null -w '%{http_code}' -m 25 -A "$SCANNER_UA" -H "$HDR" "$URL")
code_brow=$(curl -s -o /dev/null -w '%{http_code}' -m 25 -A "$BROWSER_UA" -H "$HDR" "$URL")
echo "   scanner UA -> $code_tool"
echo "   browser UA -> $code_brow"
if [ "$code_tool" = "403" ] && [ "$code_brow" != "403" ]; then
  echo "   => UA-based blocking confirmed. Any earlier scan log full of 403s is VOID: the app never"
  echo "      saw those requests. Re-run with --random-agent / --user-agent and require 0 x 403."
elif [ "$code_tool" = "$code_brow" ]; then
  echo "   => UA is not the differentiator here; the negative may be genuine (keep going)."
else
  echo "   => mixed result ($code_tool vs $code_brow) — read the bodies before concluding."
fi
echo

echo "=== step 2: hand probes beat the scanner verdict ==="
echo "   For each parameter send one shape-breaking value and record the APPLICATION's reply, e.g."
echo "     limit=25'          -> expect 422 'limit must be a whole number from 1 to 200'"
echo "     cursor=' OR 1=1--  -> expect 422 'cursor must be a transaction id...'"
echo "     from=notadate      -> expect 422 'must be real dates in YYYY-MM-DD'"
echo "   'Every parameter is shape/enum-validated with a named reason' is the defensible positive."
echo

echo "=== step 3: focused verdict run (level 2, one tamper, browser UA) ==="
LOG="$OUT/sqlmap_verdict.log"
sqlmap -u "$URL" --headers="$HDR" --level=2 --risk=2 --technique=BEUST --batch \
       --disable-coloring --timeout=25 --delay=1 --random-agent \
       --tamper=space2comment --text-only -v 2 > "$LOG" 2>&1
rc=$?
echo "   sqlmap exit=$rc  log=$LOG  ($(wc -l < "$LOG" 2>/dev/null || echo 0) lines)"

echo "   --- verdict lines ---"
grep -aE 'does not seem to be injectable|appears to be injectable|all tested parameters|CRITICAL' "$LOG" | tail -20
echo "   --- edge signals (403 count must be ZERO for the verdict to mean anything) ---"
grep -ac '403' "$LOG" | sed 's/^/   403 occurrences: /'
echo "   --- did sqlmap merely SUSPECT a WAF? (it may be your app's validator, not an edge block) ---"
grep -aE 'WAF/IPS|interfere with the results' "$LOG" | tail -3

echo
echo "Done. Archive the full log as evidence; if nothing was injectable, quote the verdict line plus"
echo "the per-parameter 422 messages, and state whether the app or the edge produced them."
exit 0
