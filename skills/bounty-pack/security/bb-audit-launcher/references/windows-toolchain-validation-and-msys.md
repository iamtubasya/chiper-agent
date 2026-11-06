# Windows/MSYS tool-invocation + toolchain validation recipe

Why this exists: on a Windows + git-bash host, four scanners returned **rc=0 while scanning nothing**
because MSYS rewrote their arguments. A run fired as-is would have produced empty/usage-dump evidence
and still been reported as "tools executed" — textbook fake coverage. Validate locally first; read
evidence bodies, never sizes.

---

## 1. The two MSYS path-conversion traps

MSYS (git-bash) rewrites arguments that *look like POSIX paths* into Windows paths when handing them
to native `.exe` binaries. Two failure modes, both silent-ish:

### (a) HTTP paths passed as CLI args → bogus hostname

```bash
python fa_api.py GET /v2/company      # arg becomes C:/v2/company
# client does base + path  ->  "https://api.example.comc:/v2/company"
# urlparse hostname        ->  "api.example.comc"
# symptom: socket.gaierror [Errno 11001] getaddrinfo failed  for a host that curl resolves fine
```

Diagnosing it: print the *final URL* and the parsed host. The malformed host looks like
`<real-host>c` (or a drive letter glued on). `getaddrinfo` works standalone, `curl` works — only the
script fails, because only the script's argument was rewritten.

**Fix:** `export MSYS_NO_PATHCONV=1` before running, *or* never pass `/v2/...` as a CLI arg — build the
path inside the script. (Memory of the session: `MSYS_NO_PATHCONV=1` in the invoking shell is not
inherited by nested scripts unless it is exported inside them too.)

### (b) File paths inside scripts → "file not found" for real files

```bash
WL="/d/data hermes/wordlists/dirs/common.txt"   # script hands it to a native .exe
nuclei  -> [FTL] Could not run nuclei: no templates provided for scan
ffuf    -> CreateFile D:\d\data hermes\wordlists\dirs\common.txt: cannot find the path
gobuster-> wordlist file "/d/data hermes/..." does not exist
sqlmap  -> can't open file 'D:\c\Users\...\Scripts\sqlmap.py'
```

All four exited **0**. `D:\d\...` and `D:\c\Users\...` are the doubled/mangled forms.

**Fix:** use native paths for anything a native binary opens (`WL="D:/data hermes/wordlists/..."`),
**and** put `export MSYS_NO_PATHCONV=1` at the top of the script itself. For Python-invoked tools,
call the launcher (`sqlmap`), not `python "<msys path>/sqlmap.py"`.

---

## 2. Local-target validation harness (do this before any "tools work" claim)

Skeleton that proved the toolchain and produced a per-tool verdict table:

```bash
set -u
export MSYS_NO_PATHCONV=1          # trap (b) fix
WL="D:/data hermes/wordlists/0B-recon/directories/common.txt"     # native path
NUCLEI_TPL="D:/data hermes/nuclei-templates"                       # native path
OUT="tool-evidence-local"; mkdir -p "$OUT"; PORT=8097
"$PY" local_vuln_target.py $PORT > "$OUT/_server.log" 2>&1 & SRV=$!; sleep 2
T="http://127.0.0.1:$PORT"

run() {  # run <name> <cmd...>   -> size, rc, usage-dump detection
  local n="$1"; shift; local f="$OUT/$n.txt"; local t0=$(date +%s)
  timeout 300 "$@" >"$f" 2>&1; local rc=$?
  local status=EXECUTED
  grep -qiE "unknown command|unrecognized arguments|Usage:|flag provided but not defined|error: the following arguments are required" "$f" && status=FAILED_USAGE
  [ "$(wc -c <"$f")" -lt 20 ] && [ "$status" = EXECUTED ] && status=NO_OUTPUT
  printf '%-14s rc=%-4s %ss %7sB %s\n' "$n" "$rc" "$(( $(date +%s)-t0 ))" "$(wc -c <"$f")" "$status"
}
```

The local target should expose a few *findable* things so a working tool visibly finds them —
e.g. `/`, `/admin` (403), `/login`, `/search?q=` (reflected), `/api/v1/users?id=1` (JSON param),
`/backup.zip`. Then "did the tool really run?" is answerable by looking.

Per-tool invocations confirmed working this way:

| tool | correct invocation | notes |
|---|---|---|
| nuclei | `nuclei -u <t> -silent -no-color -rl 20 -t "D:/…/nuclei-templates/http" -tags tech,exposure,misconfiguration` | `-t` accepts a *directory*; `-template-dir` is not a flag. `-no-color` matters for grep-ability |
| ffuf | `ffuf -u <t>/FUZZ -w "<native wordlist>" -mc 200,204,301,302,307,401,403 -t 10 -rate 25 -s` | FUZZ keyword required; wrong `-w` prints help (looks like a run) |
| gobuster | `gobuster dir -u <t> -w "<native wordlist>" --timeout 10s -t 5 -q --delay 100ms` | native wordlist path or it silently "does not exist" |
| dalfox | `dalfox url "<t>/search?q=test" --skip-bav --no-color --delay 300` | `url` subcommand required |
| sqlmap | `sqlmap -u "<t>/api/v1/users?id=1" --batch --level=2 --risk=1 --threads=4 --timeout 15 --retries=1 --smart` | needs a parameterised URL; verdict line is "all tested parameters do not appear to be injectable" |
| arjun | `arjun -u <t>/api  -t 4 -d 1` | slow (~2 min) but real |
| CORScanner | `CORScanner -u <t>` | |
| httpx / katana / naabu / wafw00f | `httpx -u <t> -silent -no-color` · `katana -u <t> -silent -d 2 -rl 20` · `naabu -host 127.0.0.1 -p <port> -silent` · `wafw00f <t>` | |
| interactsh-client | `timeout 12 interactsh-client -n 1 -v` | proves the OOB listener works (prints a token) |
| trufflehog | `trufflehog filesystem <dir> --no-update --json` | exit 0 + empty stdout = 0 secrets (it logs counts to stderr) |

Verification rules:
- **A usage dump is `FAILED_USAGE`, never coverage.** Re-verify per host with `--help`/`--version`
  before relying on a tool; if a tool refuses even `--help` on this host, record it BROKEN and do not
  count it (commix did this; semgrep CLI tracebacked → use `semgrep-core` per file instead).
- **Bound everything with `timeout`.** Tools that read from stdin (e.g. `waybackurls`) can hang
  indefinitely on a local/dry target.
- Tools whose output is legitimately empty on a dry target (subfinder/gau/waybackurls against
  `localhost`) are "RAN, no data" — not "broken". Keep that distinction in the verdict table.

---

## 3. Reporting the validation result

Publish a per-tool table with three honest classes — INSTALLED-and-fired, RAN-no-data, BROKEN — plus
the count (`13 of 17 scanners proven to fire and leave real evidence`). An installed-but-never-fired
tool is the gap you get caught on; a fired-but-erroring tool is worse if you call it coverage.
