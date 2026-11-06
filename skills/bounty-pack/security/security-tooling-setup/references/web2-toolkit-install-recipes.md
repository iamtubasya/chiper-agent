# Web2 toolkit — install sources, exact commands, and wrong-path traps

Companion to RULE 1b. RULE 1b says *how* to equip a skill (matrix → batch by method → shim →
probe). This file is the concrete recipe per tool: the source that works, the source that
**looks** right and fails, and why.

Verified end-to-end 2026-10-07: matrix went **27 present / 54 missing → 75 / 7**.
Re-run the matrix any time with `scripts/tool-coverage-matrix.py` (deployed copy at
`~/AppData/Local/hermes/scripts/web2-tool-matrix.py`).

## Batch by METHOD, in this order

```
pip  →  go install  →  release binary / jar  →  git clone + shim  →  runtime-bound (Ruby/Java/Maven)
```
A whole batch degrades gracefully when a runtime is absent (e.g. no Ruby ⇒ the CMS batch is
skipped, everything else still lands). Never install all 50 in one loop — one failure aborts
the rest if you use `set -e` semantics.

---

## pip — the ones that actually exist on PyPI

```
pyjwt pytesseract graphw00f waymore droopescan pacu sslyze ScoutSuite
# note: ScoutSuite is capitalised; `scoutsuite` 404s
```

**clairvoyance + kube-hunter MUST be installed with `--no-deps` on Python 3.7+.**
Their pinned `install_requires` still declares the ancient PyPI backports `asyncio` and
`dataclasses`. Those backports SHADOW stdlib `asyncio`/`dataclasses` on any modern Python and
break `import asyncio` / `import dataclasses` process-wide (not just for these two tools).
Install them isolated:
```
pip install --no-deps clairvoyance kube-hunter
```
If `pip check` then reports "clairvoyance requires asyncio" / "kube-hunter requires dataclasses",
that is expected metadata noise — do NOT `pip install asyncio dataclasses` to silence it.
Not on PyPI despite the obvious name (clone instead): `gopherus`, `sstimap`, `dnsreaper`,
`nosqlmap`, `patator` (patator installs `--no-deps`).

**Big pip packages blow the foreground timeout.** `ScoutSuite` exceeded 500 s and aborted the
call mid-batch. Run long installs with `background=true, notify_on_complete=true`, never in the
foreground.

---

## go install — correct module paths (and the ones that lie)

| tool | command | note |
|---|---|---|
| gospider | `github.com/jaeles-project/gospider@latest` | |
| hakrawler | `github.com/hakluke/hakrawler@latest` | |
| assetfinder | `github.com/tomnomnom/assetfinder@latest` | |
| sourcemapper | `github.com/denandz/sourcemapper@latest` | |
| kxss | `github.com/Emoe/kxss@latest` | reads URLs from **stdin** — `kxss -h` prints nothing; that is not a failure |
| grpcurl / grpcui | `github.com/fullstorydev/{grpcurl,grpcui}/cmd/…@latest` | |
| act | `github.com/nektos/act@latest` | |
| subjack | `github.com/haccer/subjack@latest` | |
| puredns | `github.com/d3mondev/puredns/v2@latest` | |
| gitleaks | `github.com/zricethezav/gitleaks/v8@latest` | **`github.com/gitleaks/gitleaks/v8` fails**: the module still declares the old path (`module declares its path as github.com/zricethezav/... but was required as ...`). Use the declared one. |
| kiterunner | **no Windows release, no installable cmd path** — clone then `go build -o kr.exe ./cmd/kiterunner` | the cmd dir is `kiterunner`, **not** `kr`; `…/cmd/kr@latest` returns *"module does not contain package"* |

### CGO tools cannot be built here

`jsluice` (`github.com/BishopFox/jsluice/cmd/jsluice`) pulls `go-tree-sitter` and fails with
`undefined: Node` — it needs CGO and a C compiler. This box has **no gcc/mingw/clang**, and
WSL has **no Go installed**, so neither route works. Confirm a toolchain exists *before*
promising a CGO build:

```bash
command -v gcc cc clang            # empty ⇒ skip CGO tools
wsl -d <distro> -e bash -lc 'go version'   # empty ⇒ cannot build in WSL either
```
Functional substitute already present: `linkfinder` + `secretfinder` (JS URL + secret
extraction). Do not present a CGO tool as "installed".

---

## Showstopper: a release asset whose name has no "win" in it

Filtering GitHub assets for `win` misses real Windows builds. Read the **whole asset list**
first:

```bash
curl -sL https://api.github.com/repos/<owner>/<repo>/releases/latest \
  | grep -oE '"browser_download_url": *"[^"]+"' | cut -d'"' -f4
```
- `sslscan` ships `sslscan-2.2.3.zip` — no "win" substring, is the Windows build.
- `kiterunner` genuinely publishes only `darwin_amd64` + `linux_*` (no Windows) → build from source.
- `jsluice`, `marshalsec`, `xmlsec1` publish **no usable release asset** → source build or jar mirror.

---

## Jars (Java is present; Maven is not)

```bash
# ysoserial — from the maintained fork's release
curl -sL -o jars/ysoserial.jar \
  https://github.com/fnmsd/ysoserial/releases/latest/download/ysoserial.jar
# verify: unzip -l jars/ysoserial.jar  (a 404 HTML page is not a jar)

# marshalsec — the upstream repo has no release jar; use a published mirror
curl -sL -o jars/marshalsec.jar \
  https://github.com/RandomRobbieBF/marshalsec-jar/raw/master/marshalsec-0.0.3-SNAPSHOT-all.jar
```
Shim with `@echo off` + `java -cp "<jar>" marshalsec.%*`. Always `unzip -l` a downloaded jar
before declaring success — `curl -o` happily saves a 404 HTML body.

---

## The two-Pythons trap (cost a full debug cycle)

This box has **two** 3.14 interpreters:

```
C:\Users\<u>\AppData\Local\Programs\Python\Python314\python.exe     <- where `pip` usually targets
C:\Users\<u>\AppData\Local\Python\pythoncore-3.14-64\python.exe     <- what a tool's .exe launcher may use
```

Installing a dependency into the wrong one produces *"No module named X"* **after** a
successful install. Before installing deps for an existing script, resolve the launcher's
interpreter:

```bash
command -v <tool>          # then inspect that launcher / its Scripts dir
```
Symptom chain seen on `semgrep`: `httpx_sse` → `pydantic_settings` → `sse_starlette` →
`mcp==1.29.0 required but 2.x installed` → all because deps went to the other interpreter.
Fix: install into the interpreter the launcher uses, then **remove the broken duplicate** so
PATH resolves to the working one (`<main-python> -m pip uninstall -y semgrep`).

Semgrep on Windows additionally pins `click~=8.4.2` and `mcp==1.29.0`; newer `mcp` 2.x renames
`mcp.server.fastmcp` → `MCPServer` and semgrep's v1 code dies on import.

---

## Antivirus blocks *reading* the file, not just executing it

`nikto.pl` → `Errno 22 Invalid argument` on open, from both bash and Python, while `ls` shows
it plainly on disk. This is Defender quarantining on access (same family as RULE 1's
`impacket`/`kerbrute` cases). Distinguish "permission denied" from "AV denial": permissions
would be consistent across tools; AV denial lets `ls` succeed but blocks `open()`.

Same class, same remedy: keep that tool in WSL, or defang the payload-bearing strings. Tools
whose behaviour is already covered by `nuclei` + `ffuf` are low priority to unblock.

---

## Shim the clones (recap of RULE 1b)

One `.bat` per cloned repo in the Python `Scripts/` dir (already on PATH). Author it with
`write_file`, **never `printf`** (escape expansion turns `\tools` into a TAB). Add
`cd /d "<repo>"` whenever the repo imports its own package. Probe every tool afterwards —
`shutil.which()` plus a `shell=True` run.
