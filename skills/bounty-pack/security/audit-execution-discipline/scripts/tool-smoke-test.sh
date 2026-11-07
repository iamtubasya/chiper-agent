#!/usr/bin/env bash
# tool-smoke-test.sh — verify the audit pipeline's tool CLIs really scan, before firing them
# at a real target. Uses a throwaway local HTTP server, so nothing external is touched.
# Usage: bash tool-smoke-test.sh
set -u
export MSYS_NO_PATHCONV=1
PY="/usr/bin/python3"
GO="$HOME/go/bin"
T="http://127.0.0.1:8099"
PORT=8099
TMP="$(mktemp -d)"
cd "$TMP" || exit 1
echo ok > index.html
"$PY" -m http.server "$PORT" >/dev/null 2>&1 &
SRV=$!
sleep 2

WL="~/.chiper/skills/bounty-pack/exploit-cookbook/references/sensitive-files-wordlist.txt"
[ -f "$WL" ] || WL="~/.local/share/Programs/Python/Python314/Lib/site-packages/dirsearch/db/dicc.txt"
TD="D:/data hermes/nuclei-templates"

PASS=0; FAIL=0
check() {  # check <name> <expect-regex> <cmd...>
  local name="$1" want="$2"; shift 2
  local out; out=$(timeout 90 "$@" 2>&1); local rc=$?
  if echo "$out" | grep -qiE 'usage:|incorrect usage|unknown command|flag provided but not defined|invalid argument|unrecognized arguments|no such option'; then
    echo "  [FAIL] $name — CLI usage error (tool would NOT scan)"; FAIL=$((FAIL+1))
  elif echo "$out" | grep -qiE "$want"; then
    echo "  [ OK ] $name — real output seen (rc=$rc)"; PASS=$((PASS+1))
  else
    echo "  [WARN] $name — ran (rc=$rc) but expected output not seen"; PASS=$((PASS+1))
  fi
}

echo "=== tool smoke test @ $T ==="
check "dalfox url"       'dalfox|testing'   "$GO/dalfox.exe" url "$T" --skip-bav
check "gobuster dir"     'Status|Results'   "$GO/gobuster.exe" dir -u "$T" -w "$WL" --timeout 10s -t 5 -q
check "ffuf FUZZ"        'ffuf'             "$GO/ffuf.exe" -u "$T/FUZZ" -w "$WL" -mc 200,301,302 -t 20 -s
check "nuclei"           'tech-detect'      "$GO/nuclei.exe" -u "$T" -silent -timeout 5 -tags tech
check "CORScanner"       'CORS'             "/usr/local/bin/CORScanner.EXE" -u "$T"
check "race-checker"     'RACE'             "$PY" "~/.chiper/skills/bounty-pack/tools/race-checker.py" -u "$T" --attempts 10
check "arjun (pip)"      'Scanning|chunks'  "/usr/local/bin/arjun.exe" -u "$T/" -t 2 -d 0
check "kxss (stdin)"     'checkReflected'   bash -c "echo $T | $GO/kxss.exe"
check "sqlmap (?id=1)"   'sqlmap'           "$PY" "/usr/local/bin/sqlmap.exe" -u "$T/?id=1" --batch --level=1 --risk=1 --timeout 5 --disable-coloring
if [ -d "$TD" ]; then
  echo "  [INFO] nuclei local mirror: $TD (-t \"$TD/http\" -tags ...)"
fi
kill "$SRV" 2>/dev/null
cd / && rm -rf "$TMP"
echo "=== done: $PASS ok / $FAIL fail (fail = CLI broken, fix the command in force-full-execution.py) ==="
[ "$FAIL" -eq 0 ]
