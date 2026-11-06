# Guarded scanner volley · path traps · orphan-process cleanup

Written after firing an automated volley at a program that **forbids** automated scanning
(FreeAgent Responsible Disclosure), with the operator's verbal GO. Result: zero findings, a
temporary IP flag on the whole application estate. Use this as the checklist, not as a
recommendation to fire.

---

## 1. The guarded script shape

```bash
#!/usr/bin/env bash
set -u
export MSYS_NO_PATHCONV=1          # see §3 — without this 4 tools fail while returning rc=0

if [ "${FA_SCANNER_APPROVED:-0}" != "1" ]; then
  cat <<'EOF'
REFUSED: the program forbids automated scanning. Fire only after a written exception, with:
    FA_SCANNER_APPROVED=1 bash fire_scanners.sh
EOF
  exit 2                            # verified: exits 2 when the env var is unset
fi

IN_SCOPE=("https://signup.target.com" "https://api.target.com" "https://dev.target.com")
allow() { for s in "${IN_SCOPE[@]}"; do [ "$1" = "$s" ] && return 0; done; \
          echo "SCOPE-GUARD: refusing $1" >&2; return 1; }

run() {                             # run <name> <cmd...>
  local n="$1"; shift
  timeout 600 "$@" >"tool-evidence/$n.txt" 2>&1
  local rc=$? sz=$(wc -c <"tool-evidence/$n.txt") status=EXECUTED
  grep -qiE "unknown command|unrecognized arguments|Usage:|flag provided but not defined" \
       "tool-evidence/$n.txt" && status=FAILED_USAGE
  [ "$sz" -lt 20 ] && [ "$status" = EXECUTED ] && status=NO_OUTPUT
  printf '{"tool":"%s","status":"%s","bytes":%s,"rc":%s}\n' "$n" "$status" "$sz" "$rc" \
    >> tool-evidence/_usage.jsonl
}
```

Keep it scope-guarded, rate-limited (`-rl 20` / `-rate 25` / `--delay 100ms`), writing
`tools-usage.json` so the 0D gate has its artifact. Then **do not fire it** until the exception
exists — and when you do, watch for the block signature below.

## 2. Block detection + what to expect

```bash
grep -rliE "429|too many requests|rate limit|attention required|access denied|cloudflare|blocked" \
     tool-evidence/*.txt
```

The real tell was subtler: a host that normally answers `200`/`400` suddenly answered
`302 → support.<target>/hc/…/Preventing-fraud` (their anti-fraud article). Once that is set it applies
to **every** application host: signup, login, each tenant subdomain, the API and the dev dashboard
(the marketing site outside it stays 200). So the blast radius includes your own manual access.

Recovery: no action is needed beyond stopping. In the observed case it cleared in ~15 minutes, the
accounts and API tokens still worked, and nothing else was needed. Do **not** retry and do **not**
route around it with a proxy before the vendor confirms — evading an access control after being
blocked is a different, worse situation than the original testing.

## 3. The MSYS path trap (silent fake coverage)

On Windows/git-bash, an argument beginning with `/` is rewritten to a Windows path — including inside
a script:

```
ffuf -w /d/data/wordlists/dirs.txt   →  CreateFile D:\d\data\wordlists\dirs.txt  (not found)
nuclei -t /d/data/nuclei-templates   →  "no templates provided for scan"
sqlmap.py /c/Users/…/sqlmap.py       →  can't open file 'D:\c\Users\…'
```

Every one of those returned **rc=0**, so a naive run reports "4 tools executed" with empty output.
Fix: `export MSYS_NO_PATHCONV=1` inside the script **and** use native `D:/…` paths. Invoke the
sqlmap launcher (`sqlmap -u …`) rather than `python <msys-path>/sqlmap.py`.

**Rule:** a non-zero size is not evidence. Read the body — `Usage:`, `unknown command`,
`unrecognized arguments`, `no templates`, `does not exist` all mean the tool never scanned.

## 4. Kill verification (killing the wrapper is not enough)

A bash loop that runs `timeout 600 nuclei …` per host keeps going after you kill the tracked
background session: the wrapper dies, the loop and its `timeout`/`nuclei` children do not.

```bash
# 1) kill the tree
taskkill //F //T //PID <pid>
# 2) enumerate by CommandLine (name-based `tasklist` misses nothing but confirms nothing either)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | \
  Where-Object { \$_.CommandLine -match 'fire_scanners|nuclei|amass|ffuf|gobuster' } | \
  Select-Object ProcessId,Name,@{n='CL';e={\$_.CommandLine.Substring(0,80)}} | Format-Table -Auto"
# repeat until empty; note your own grep command matches the pattern too — read the output
```

Verify the environment is actually quiet before reporting "stopped": a still-running scanner keeps
generating block traffic while you write the incident note.

## 5. Reporting the incident honestly

Record in PHASE_LOG: start/finish times, which tool ran, byte counts of each evidence file, the exact
block URL, which hosts it covered, when it lifted, and the finding count (here: **0**). State plainly
that the volley produced nothing, so a future session does not assume the scanners found-and-cleared.
