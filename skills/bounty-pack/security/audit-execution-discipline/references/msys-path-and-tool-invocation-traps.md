# MSYS path conversion — the silent tool-killer on Windows audit hosts

Two failure modes, both observed on this host (git-bash / MSYS on Windows) and both of which
manufacture **fake coverage** if you trust exit codes.

## Symptom A — looks like DNS, is actually argument mangling

```
$ python fa_api.py GET /v2/company
urllib.error.URLError: <urlopen error [Errno 11001] getaddrinfo failed>
```
…while `curl https://api.freeagent.com/v2/company` works, and
`socket.getaddrinfo('api.freeagent.com', 443)` succeeds in a fresh interpreter.

Cause: MSYS rewrites a bare POSIX-looking argument (`/v2/company`) into a Windows path
(`C:/v2/company`). The URL becomes `https://api.freeagent.comC:/v2/company`, so the hostname is
parsed as **`api.freeagent.comc`** and DNS fails.

Debug tell: print the URL (or `urllib.parse.urlparse(url).hostname`) — you will see the appended
drive letter. A fabricated "DNS outage" retry loop is wasted time.

Fix: `export MSYS_NO_PATHCONV=1`, or keep the argument inside a script instead of on the shell
command line.

## Symptom B — tools fail while returning rc=0

A script that passes POSIX paths to native binaries:

```
ffuf     -> CreateFile D:\d\data hermes\wordlists\0B-recon\directories\common.txt: cannot find the path
gobuster -> wordlist file "/d/data hermes/…/common.txt" does not exist
nuclei   -> Could not run nuclei: no templates provided for scan
sqlmap   -> can't open file 'D:\c\Users\WINDOWS10\…\Scripts\sqlmap.py'
```

Every one of those returned `rc=0` and wrote a non-empty evidence file. A size-based or
status-based gate would have called them EXECUTED.

Fix, both halves:
1. native paths in the script: `D:/data hermes/wordlists/...`, `D:/data hermes/nuclei-templates`
2. `export MSYS_NO_PATHCONV=1` as one of the script's first lines (exported inside the script, not
   only on the invoking command line)
3. for Python entry points prefer the launcher (`sqlmap …`) over
   `python.exe /c/Users/.../Scripts/sqlmap.py`

## Rule

`rc=0` is not evidence. Before trusting any `tool-evidence/*` file:

```
for f in <out>/tool-evidence/*.txt; do echo "=== $(basename $f)"; tail -c 400 "$f" | tr -d '\r'; echo; done
```

Treat as NOT-RUN if the body contains: `unknown command`, `unrecognized arguments`,
`Usage:`, `no templates provided`, `cannot find the path`, `does not exist`, `can't open file`.

## Symptom C — a generated `.bat` shim whose path contains a TAB

Writing a Windows launcher with `printf` from bash silently corrupts it:

```bash
printf '@echo off\r\n"%s" "%s" %%*\r\n' "$PYEXE" 'D:\data hermes\tools\x.py' > shim.bat
```

`printf` interprets escapes in its **format** string, so `\t` inside the path argument is emitted as
a literal TAB. The shim then fails with

```
The filename, directory name, or volume label syntax is incorrect.
python.exe: can't open file 'D:\data hermes<TAB>ools\...': [Errno 22] Invalid argument
```

`cat -A shim.bat` shows `^I` where the `\t` should be; `od -c` shows `\t` directly.

Fix: write launchers with a **file writer** (a Python script using `write_text`), never with
`printf`. Regex-replacing or `sed`-patching a broken shim is how you end up re-breaking it.

## Symptom D — a `.bat`/`.cmd` shim is found but will not run

`shutil.which("foo")` resolves `foo.bat` (PATHEXT includes `.BAT`) but

```python
subprocess.run(["foo", "-h"])              # WinError 2: The system cannot find the file
subprocess.run("foo -h", shell=True)       # OK
```

So detection and execution are again separate failure points. Before concluding a shim is broken,
check **how the caller invokes it**: this pipeline's `tool_router` / `force-full-execution` both use
`shell=True`, so `.bat` shims are fine there. A bare-`list` `subprocess.run` is the thing that
fails — not the shim.

Corollary: bash's own `command -v foo` does **not** resolve `.bat` (it is not in its lookup list),
which makes a perfectly good shim look missing. Verify Windows-facing shims with Python's
`shutil.which`, not with the shell.

## Symptom E — "installed but broken" because two interpreters are in play

A console script on PATH can be a launcher for a **different** interpreter than the one you
`pip install`ed into. Tell: `import X` works under one `python.exe` and fails under the tool, or a
dependency error names a site-packages path you do not recognise.

Diagnose before reinstalling:

```bash
command -v <tool>                       # where the launcher lives
head -2 "$(command -v <tool>)"          # its shebang / which python it targets
<that-python> -m pip show <pkg>         # is the dep actually in THAT interpreter?
```

Fix: install the missing dependency into the interpreter the launcher actually uses — or remove the
shadowing install so PATH resolves the one you meant.

## Symptom F — a shell-quoted POSIX path inside a Python heredoc tests the WRONG path

Same root cause as A, but it disguises itself as a **code bug**. When you probe a
Windows-host script by piping a heredoc into Python and interpolating a bash path:

```bash
"$PY" - <<EOF
import pathlib
td = pathlib.Path(r"$HOME/AppData/Local/hermes/poc-plans/$RUN")
print("ada:", (td/"run-meta.json").exists())     # -> ada: False
EOF
```

`$HOME` is expanded by bash to `/c/Users/WINDOWS10`, so Windows Python is handed
`/c/Users/WINDOWS10/AppData/...`, which does not exist — **plus** the unquoted
heredoc makes bash mangle anything that looks like a path.

Seen for real 2026-10-08: this printed `_is_web3(td) = False` and looked like a
freshly-written track-detection bug. It was not. The same call with
`C:\Users\WINDOWS10\AppData\...` returned `True` immediately. A debugging cycle
was spent on a test that never asked the right question.

Rules:
- In a probe, build Windows paths **literally** (`r"C:\Users\WINDOWS10\..."`) or via
  `pathlib.Path.home()` **inside** the Python process — never from `$HOME`.
- Prefer a quoted heredoc (`<<'EOF'`) so bash interpolates nothing, and pass values
  through argv/env instead.
- When a probe reports a negative, **first ask whether the probe could see the file
  at all** (`print(td, td.exists())`) before concluding the code is wrong.

**The generalisation that matters on this host:** a failing probe is at least as
likely to be a wrong path as a wrong program. Distinguish them before you patch
anything — a "fix" applied to a phantom bug is how real bugs get introduced.

Same trap, other surfaces seen the same day:
- `wsl -d Ubuntu -- bash -c "PATH=/usr/local/bin:/usr/bin:/bin aderyn …"` — MSYS
  rewrote the WSL PATH into Windows fragments
  (`C:UsersWINDOWS10AppDataLocalhermesgitusrlocalbin: command not found`).
  Prefix the whole command with `MSYS_NO_PATHCONV=1`.
- `cd /d "D:\..."` inside a `.bat` or a `cmd /c` string — `/d` is converted to a
  path. `MSYS_NO_PATHCONV=1` again.

## Related traps seen in the same session

- **PATH-shape detection**: `shutil.which` finds the tool, then the invocation still fails on a
  mangled argument — detection and invocation are separate failure points.
- **Interrupted foreground command loses buffered stdout**: a long loop killed by `timeout` prints
  nothing. Use `python -u` (or `-u` on the interpreter) when a script's progress matters.
- **Tripwire vs shell scripts**: content that looks like a credential path or token is redacted to
  `***` on write, which silently produces a broken `.sh`. After writing a script that mentions
  tokens, always `grep -c '\*\*\*' file && bash -n file`.

## Symptom G — `MSYS_NO_PATHCONV=1` INVERTS the conversion; now every POSIX path breaks

The flag is not a global cure. With it **exported**, MSYS stops translating POSIX paths — so a
POSIX path you hand to a *native* consumer is passed through verbatim and the native binary resolves
it against the current drive:

```
$ MSYS_NO_PATHCONV=1 python.exe ~/AppData/Local/hermes/scripts/audit-pipeline-orchestrator.py ...
python.exe: can't open file 'D:\c\Users\WINDOWS10\AppData\Local\hermes\scripts\...': [Errno 2]
```

Note the `D:\c\...` — the `/c/...` prefix survived as a literal path segment under the CWD drive.
This is the mirror image of Symptom B, and it bit twice in one session (an orchestrator relaunch that
had to be re-issued).

Rule: **the flag and the path style travel together.**

| state | paths you must pass |
|---|---|
| `MSYS_NO_PATHCONV` unset | POSIX (`/c/...`) or MSYS `~` — MSYS converts them for the native consumer |
| `MSYS_NO_PATHCONV=1` exported | **native only** (`C:/Users/...`, `D:/data hermes/...`) for every argument handed to `python.exe`, `nuclei`, `ffuf`, etc. |

Also: `~` is a **bash** expansion. A native consumer never expands it — always let bash expand it
(unquoted, outside the flag's reach) or write the literal `C:/Users/<user>/...`. When a command mixes
both styles, split it: `cd` in bash with a POSIX path, then pass native paths to the tool.

## Symptom H — a `terminal` command carrying an auth header gets mangled into a bash syntax error

Redaction rewrites credential-shaped text **in the command that is actually executed**, not only in
what you see. A one-liner of the shape `curl -s -H "Authorization: Bearer <token>" https://x/api` was
repeatedly returned as `bash: unexpected EOF while looking for matching '"'` — the substituted value
ended the quoting and the shell then choked several tokens later.

Fix, and it is the better workflow anyway: **do authenticated HTTP from Python, not from a bash
one-liner.** `urllib.request` + `req.add_header("Authorization", "Bearer " + key)` never touches the
shell's quoting rules, keeps the secret out of the command line, and lets you write the raw response
straight to an evidence file. Reserve `curl` for unauthenticated, header-free probes.

Corollary: when a bash one-liner about a URL/header fails with a *syntax* error rather than a network
error, suspect the command text — not your quoting. Re-issue it as a Python step.

## Symptom I — `--help` on the pipeline scripts is not help, and a stale tracker silently skips phases

Two run-lifecycle traps on the orchestrator family:

1. **`audit-pipeline-orchestrator.py --help` prints no help.** It treats `--help` as the *target* and
   dies with `❌ PIPELINE FAILED: target tidak dikenali tipe-nya: '--help'`. Read the `sys.argv`
   loop in the script instead (it accepts `--tech`, `--scope`, `--exclude`).
2. **A stale tracker makes a fresh run lie.** With a leftover
   `~/AppData/Local/hermes/trackers/audit-pipeline-<host>.json`, the next start prints
   `RESUME MODE: already completed ['0A','0B'] — skip those` and **skips recon entirely** — the run
   looks like it started but never enumerated anything.

Before starting a fresh engagement on a host that was audited before: list the tracker dir, move the
stale `<host>.json` (and the `audit-pipeline-<host>.json`) into a dated `_archive_<host>_<YYYYMMDD>/`,
and confirm nothing active matches the host. `.bak_*` files are already archives and can stay.

Same family: `force-full-execution.py` has an internal **3600 s** timeout. When it trips, the
orchestrator prints `PIPELINE EXCEPTION … PARTIAL STATE SAVED — auto-resume dari 0C` and **starts
again**. On a target whose program forbids scanning load that loop is not a bug to wait out — kill
the tree rather than letting it re-fire the volley every hour.

## Symptom J — writing the file is its own set of traps (truncation, `&`, and the flag again)

Three traps hit while *creating* scripts on this host — all cost a re-run:

1. **A single long heredoc is truncated.** `cat > gen.py <<'PYEOF'` with ~150 lines came back as
   `bash: -c: line 119: unexpected EOF while looking for matching '…'`. It reads like a quoting bug
   in your content; it is a **command-length** cut, so the heredoc never closed. Write long files in
   **appended chunks** (`> file` for part 1, `>> file` for the rest), each comfortably under ~100
   lines, and `wc -l < file` after each chunk to confirm it landed before appending the next.
2. **A literal `&` inside the heredoc body trips the tool's backgrounding pre-scan** — the command is
   rejected before bash runs it (`Foreground command uses '&' backgrounding`). Fixes: build the
   character in the file (`A = chr(38)`, then `s.replace(A, A+"amp;")`) instead of typing `&`, keep
   bare `&` out of the content, or write the file from a Python `- <<'PY'` step whose body has no
   literal `&`.
3. **With `MSYS_NO_PATHCONV=1` exported, `curl -o /dev/null` fails** —
   `curl: (23) client returned ERROR on write of 8000 bytes` / `Failure writing output to destination`
   — because native curl opens a literal `/dev/null`. Use `-o NUL` (or a real temp file). Likewise a
   `-w` format string that *begins* with `/` (e.g. `-w "/admin -> %{http_code}"`) gets path-converted
   into `C:/…`; prefix every `-w` string with a letter (`-w "R${p} -> …"`) so it is not mistaken for a
   path.
4. **An UNQUOTED heredoc expands variables at WRITE time — producing a script that scans nothing.**
   `cat > run_tools.sh <<EOF` (no quotes on the delimiter) interpolates `$TGT`, `$OUT`, `$UA` **as the
   file is created**, from the *writer's* shell, where those names are usually unset. The emitted
   script still looks right to the eye. Observed end to end:

   ```
   $ bash run_tools.sh
   --- wafw00f   rc=0 bytes=905        # file non-empty, exit clean
   --- httpx     rc=0 bytes=0
   --- nuclei    rc=0 lines=0          # reads as "0 findings" — actually 0 REQUESTS
   ### run done
   $ cat tool-evidence/wafw00f.txt
   [*] Checking https://
   ERROR:wafw00f:Something went wrong Invalid URL 'https://': No host supplied
   ```

   This is the most dangerous variant of the class, because the runner reports **success** and every
   gate that checks file existence + size + exit code goes green. `nuclei` even printed
   `[INF] Templates loaded for current scan: 1512` while scanning nothing.

   Fix: **quote the delimiter** (`cat > run_tools.sh <<'EOS'`) so the body is written verbatim, and pass
   runtime values in via `export VAR=...` before invoking the script. After writing any generated
   script, confirm the variables are still literal rather than substituted:

   ```bash
   grep -nE '\$[A-Z_]+' run_tools.sh    # must still show $TGT / $OUT / $UA inside the body
   ```

   And per the Rule section above, read the body of **every** evidence file before believing a clean
   sweep — `No host supplied`, `no templates provided`, or `0 lines` on a target with known endpoints
   are NOT-RUN, not NOT-FOUND.

## Symptom K — quoting a path SEGMENT silently removes the space, and both spellings "work"

The host's engagement root is `D:\data hermes\...` — it contains a **space**. Quoting the whole path
protects it; quoting one *segment* does the opposite:

```bash
D=/d/data/"hermes/bug-bounty"/quarterwise_v6     # WRONG — writes to /d/data/hermes/bug-bounty/...
D="/d/data hermes/bug-bounty/quarterwise_v6"     # RIGHT — the space survives
```

Because `"hermes/bug-bounty"` is one shell word, the first form builds a path **without the space**:
`/d/data/hermes/bug-bounty/quarterwise_v6`. `mkdir -p` happily creates that parallel tree and
`ls "$D"` lists the files just written — so the session's deliverables (reports, findings) land in a
phantom directory while every check looks green. Nothing errors until a later command uses the
correct spelling and reports `No such file or directory` for a file you *know* you wrote.

Seen 2026-10-09: a whole engagement's v6 write-ups (`FINDINGS-*.md`, `TAX-ENGINE.md`) sat under
`/d/data/hermes/...` while the audit dir `/d/data hermes/...` had none of them.

Detection — list the two spellings side by side before trusting a path:

```bash
ls -d "/d/data hermes/bug-bounty"   /d/data/hermes/bug-bounty 2>&1
```

Fixes:
- Define the base **once**, fully quoted, and only ever append: `B="/d/data hermes/bug-bounty"; D="$B/quarterwise_v6"`.
- Never quote a fragment inside an otherwise-unquoted path.
- If deliverables may already be split across both trees, `find /d/data -maxdepth 3 -name "<engagement>"`
  and `mv` the stray one back — do it before the next phase reads "missing" files.
- A `No such file or directory` on a file you definitely wrote is the tell: suspect the **path**, not
  the writer (same family as Symptoms F and J).

## Symptom L — `taskkill` flags are path-converted, so the kill SILENTLY does not happen

Any switch that looks like a rooted path is rewritten before the native binary sees it. `/F` becomes
`F:/`, and `taskkill` then rejects the whole invocation:

```
$ taskkill /F /T /PID 19056
ERROR: Invalid argument/option - 'F:/'.
Type "TASKKILL /?" for usage.
```

The command **exits non-zero and prints an error**, so it is not silent in isolation — but inside a
loop that kills several PIDs it is easy to read past, and the processes stay alive. Worse, if you
only check "did the command run", the real effect (a 2.5-hour stale `nuclei` still holding RAM) is
invisible.

Seen 2026-10-10 killing stale audit processes: four `TradingBot` PIDs survived a `/F /T /PID` loop
and still showed in the process list.

Fixes, in order of preference:

1. **Do process management from Python, not from bash.** `subprocess.run("taskkill /F /T /PID N",
   shell=True)` is not subject to MSYS argument conversion — the string reaches `cmd.exe` intact.
   This host already has the wrapper: `toolguard.py unblock --pid N` (also records the action to
   `trackers/tool-stalls.jsonl`, and on non-Windows falls back to `kill -9`).
2. `MSYS_NO_PATHCONV=1 taskkill //F //T //PID N` — doubled slashes defeat the converter, but note
   Symptom G: the flag inverts conversion for *everything else* in that command.
3. Verify by effect, never by exit code: re-list the PIDs afterwards and confirm they are gone.
   `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '<marker>' }` is the check
   that actually answers "did it die".

Corollary — **identify the process before killing it.** The same `tasklist`/`CommandLine` read that
finds the targets also proves which run owns them. On this host several long-lived stacks look alike
(`hermes_cli.main gateway run`, `Camoufox`/`node`, a trading bot, another engagement's orchestrator);
filter on `CommandLine` (target name, script path) and `CreationDate`, never on image name alone.
A stale run from a *different engagement* is the classic mis-kill.

## Symptom M — the heredoc rewrites your CONTENT: an escaped `\n` becomes a real newline

Same family as J/K, different victim: the *text you are writing*. A Python string that is supposed to
**contain** an escape can lose the backslash and become the escaped character itself:

```bash
python - <<'PY'
from pathlib import Path
Path("x.py").write_text('    body += f"\\nTIMEOUT after {t}s"')   # intent: write a literal \n
PY
```

What lands in `x.py`:

```
    body += f"
TIMEOUT after {t}s"
```

→ `SyntaxError: unterminated f-string literal (detected at line N)`. Hit **twice in one session**, and
each time it read like a bug in the *generated* code rather than in the writer.

Rules:
- Never route an escape through a heredoc. Compose it in the target language:
  `body += chr(10) + "TIMEOUT ..."` — no backslash reaches the shell at all.
- Sanity-check **the written file**, not the command: `python -m py_compile <file>` after every
  generated edit (it caught both occurrences immediately).
- `unterminated f-string/string literal` in code you just generated is a **writer** bug, not a logic
  bug — fix the generator, don't hand-edit the output.

## Symptom N — inline PowerShell inside a bash heredoc fails SILENTLY

```bash
python - <<'PY'
import subprocess
ps = '''Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*audit-pipeline*' } |
        Select-Object -ExpandProperty ProcessId'''
print(subprocess.run(['powershell','-NoProfile','-Command',ps], capture_output=True, text=True).stdout)
PY
# -> empty output, exit 1, NO error message
```

The `'*…*'` quoting collides with the heredoc/quoting layers and the pipeline returns nothing —
indistinguishable from "no matching process", which is exactly the wrong conclusion when you are
triaging whether a run is alive. Seen three times in one session.

Fixes:
- For process triage prefer **`wmic process get CommandLine,Name,ProcessId /format:csv`** parsed with
  Python's `csv.reader`. Remember the column order is `Node,CommandLine,Name,ProcessId`; a bare
  `split(',')` breaks on commas inside a command line and fabricates PIDs out of `--tech` args.
- If you need CIM, pass the script as a **list argument** to `subprocess.run([...])`, or write a
  `.ps1` to disk and invoke the file — never interpolate it through a shell heredoc.
A PowerShell step that returns *nothing* has **not** proven that nothing matched. Confirm with a
second, independent reader before acting on the empty result.

## Symptom O — three false-negative generators inside a recon bash loop

All three were hit in one engagement (Nordnet VDP, 2026-10-12) and each produced a *wrong
conclusion* rather than an error, so they belong together.

**O1 — a loop argument that starts with `/` is path-converted, so `curl` gets no host.**
The offending shape:

```bash
for p in /api/2/login /wp-json/... ; do
  curl -s "https://$h$p" -o /tmp/x -w "$p -> %{http_code}\n"     # $p prints as C:/Users/.../git/api/...
done
```

MSYS rewrites every *bare* argument that looks like a rooted path — including the value expanded
into `-w`. The result is a mix of `000` codes and mangled labels. Rule: **build the full URL and
quote it as one word for every call** (`curl -s "https://$h$p"`), and never echo a leading-`/`
fragment as a bare argument. If a probe prints a `C:/…` or `D:/…` path where you expected `/api/…`,
suspect the converter, not the target (same family as Symptoms A/F/G).

**O2 — a stale temp file makes a FAILED request look like a SUCCESSFUL one.**
`curl -o /tmp/x` does not truncate `/tmp/x` when the request fails (exit 000 / connection refused).
The *previous* request's body is still there, so `head -c 200 /tmp/x` prints a real-looking response
that belongs to a different host. Observed: an `sso.b2b.prod…` probe reported `403` / `GCS
AccessDenied` bodies that were leftovers from earlier hosts in the same loop.

Rule: **use a unique temp file per probe, or `: > /tmp/x` before the call**, and treat `http_code=000`
as "no answer — the body is meaningless". Never read an evidence body without first confirming the
status code came back non-000.

**O3 — a Python-written host list holds CRLF, so consecutive hostnames concatenate.**
`Path.write_text("\n".join(hosts))` on Windows can emit `\r\n`; a `while read h; do curl "https://$h"…`
loop then hands curl `hostA\r` and — on a final line with no trailing newline — glued names like
`wifi-user-admin.dcc.example.comwww-no.other.example.com` → `000`.

Rule: normalise before looping —
`tr -d '\r' < hosts.txt | grep -vE '^\s*$' | sort -u > hosts.clean.txt` — and always loop with
`while IFS= read -r h; do … done < hosts.clean.txt`. A `000` whose URL contains two hostnames is this
bug, not a network block.

**General rule for the class:** a `000`/empty result from a bash probe loop is *unverified*, not
*negative*. Before writing "host dead / NXDOMAIN / no service", re-run that one host with a single
explicitly-quoted full URL and a fresh temp file.

**O4 — a tool given a flag it does not support exits 0 and writes a DEGENERATE file, which then
reads as a catastrophic negative.** `dnsx -l hosts.txt -silent -a -resp -retries 1` — the build has no
`-retries`; it printed `flag provided but not defined: -retries` and produced a **1-line** output.
Taken at face value that says "1 of 14,410 hostnames resolve", which would have discarded an entire
recon branch (the zone was in fact well-populated). The later correct run (same command, no bad flag)
returned 514.

Rule: when a tool's output count is implausible — a near-total negative against a zone you have
independent reason to believe is populated — do not record the negative. Grep the evidence for a
usage/flag error and re-run against a flag set you have checked. The same session also produced
`dig +short` returning EMPTY for names that DO resolve; **confirm every DNS negative with a second
resolver** (`nslookup <h> 8.8.8.8`, `python -c "import socket;print(socket.gethostbyname('<h>'))"`)
before it becomes a line in the ledger.

## Symptom P — a `.ps1` you just wrote will not parse: BOM-less UTF-8 read as ANSI

Symptom N says "write a `.ps1` to disk instead of interpolating PowerShell through a shell" — but the
file itself has an encoding requirement. **Windows PowerShell 5.1 reads a `.ps1` with no BOM using the
system ANSI codepage**, so every multi-byte UTF-8 character decodes as 2–3 garbage bytes, which
typically destroys a string terminator and turns your script into a parse error.

Real transcript (2026-10-17, a process-kill helper written with `write_file`):

```powershell
At C:\...\kill_yandex.ps1:43 char:46
+     Write-Output ("  SKIP  PID {0} ({1}) <mojibake>\" protected" -f $t, $nm)
+                                              ~~~~~~~~~~~~~~~~~~~~~~
Unexpected token 'protected" -f $t, $nm)
...
The string is missing the terminator
```

The body was `Write-Output ("  SKIP PID {0} ({1}) — protected" -f $t, $nm)` — a single **em-dash**.
Its 3 UTF-8 bytes were decoded as `â€”`, the closing `"` never registered as a terminator, and the
error surfaced **many lines away** from the real cause (the same file also used `✅`/`❌`, which
contributed). It looks like a quoting bug in your logic; it is a **writer encoding** bug.

Rules:
- **Write `.ps1` helpers ASCII-only.** No em-dash `—`, no `–`, no curly quotes, no `✅`/`❌`/`⚠️`.
  Use `-`, `OK`, `FAIL`, `!!`. Keep emotive output for stdout of *other* tools, not for `.ps1` literals.
- If non-ASCII is genuinely needed, write the file as **UTF-8 with BOM** (`EF BB BF`) — that is the
  only encoding PS 5.1 honours without a `-Encoding` flag.
- Detect it in one line before running:

  ```bash
  python -c "b=open(r'C:\path\to\x.ps1','rb').read(); print('ASCII-OK' if max(b)<128 else 'NON-ASCII at ' + str(b.index(next(c for c in b if c>127))))"
  ```
- Syntax-check without executing:

  ```powershell
  [scriptblock]::Create((Get-Content -LiteralPath x.ps1 -Raw)) | Out-Null   # throws on parse error
  ```

Same family as Symptom J (the file you wrote is not the file you think) and Symptom M (the writer
corrupts content). The common tell: **an error located far from the line you edited.** Fix the writer,
re-write the whole file, do not hand-patch the reported line.

A related, easier-to-miss variant in the same scripts: a `-f` format string where a bare `%` sits
adjacent to a closing brace (`"… {1}% | …"`) plus a later broken string makes PowerShell attribute the
failure to the `%` operator. If an error points at `%`, look for an **unterminated string above it** —
usually the encoding case above.

## Symptom Q — the kill "succeeded" but the process is back: auto-restart, not a failed kill

Two independent causes seen on this host, both producing "I killed it and it returned":

1. **A Scheduled Task with a restart policy.** Measured 2026-10-17 on the trading bot:

   ```powershell
   Get-ScheduledTask -TaskName '<name>' | Select-Object TaskName, State,
     @{n='Restart';e={$_.Settings.RestartCount}},
     @{n='Interval';e={$_.Settings.RestartInterval}}
   #  State=Running  Restart=999  Interval=PT1M  Trigger=MSFT_TaskLogonTrigger
   ```

   `RestartCount=999` + `RestartInterval=PT1M` means the wrapper returns within a minute no matter how
   hard the child was killed. **`Stop-Process`/`taskkill` is a no-op here — you must
   `Stop-ScheduledTask` first (State -> `Ready`), then kill the tree, then `Disable-ScheduledTask`
   (`Enabled=False`) if you want it to stay down across a reboot/logon.** Order matters: disabling
   after killing prevents the logon trigger from resurrecting it.

2. **An autorun that respawns within seconds.** The office suite re-launched itself through three
   tasks (`…_startup`, `…_interval`, `…_update`), so a kill sweep that does not also disable the tasks
   sees 10 fresh processes 2 seconds later and reads it as "the kill failed". Discover them by name:

   ```powershell
   Get-ScheduledTask | Where-Object { $_.TaskName -match '<product>' -or
     ($_.Actions.Execute -join ' ') -match '<product>' } |
     Select-Object TaskName, State, @{n='Exec';e={$_.Actions.Execute -join ';'}}
   ```

Before reporting "stopped", prove **all three** (same discipline as pipeline-ops §13.1): no live process
matched on `CommandLine`, every owning task is `Disabled`, and a 5-second re-scan is still empty. A
single successful `taskkill` proves none of them.

Corollary for cleanup sweeps: always re-list after a short delay and report the *second* count. The
first count only proves the signal was delivered.

