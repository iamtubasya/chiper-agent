# Tool health & invocation truth — "EXECUTED" ≠ "tested the target"

Operator, 2026-10-11 (second time this engagement):

> *"Sy udh capek setting kamu spy semua tools bs djalankan dgn benar, tp msh kejadian spt ini"*
> *"kenapa jadi malah bolak balik bug ... kmu harus lebih fleksibel, jgn dkit2 bug, tp kl ketemu yg
> salah, kamu perbaiki dan lanjut ke target yg benar, kl gk gitu, kamu bolak balik spt ini terus
> kapan selesau proses auditnya"*

Two separate lessons, both first-class:

* **§1–§4** — the pipeline reported tools as `EXECUTED` **on the strength of an exit code**, so a
  broken invocation was indistinguishable from a clean scan. Fix = probe once, persist the verdict.
* **§5** — the *behaviour* correction: **fix the thing, then ADVANCE.** Do not symptom-chase.

---

## 1. The measurement that exposes it

Classify every file in `tool-evidence/` by **what it proves**, not by its exit code:

| class | test | meaning |
|---|---|---|
| **REAL** | output shows the tool reached the target (HTTP status/URL/host name/parsed response, ≥2 distinct markers) | a genuine test |
| **VALID SILENT NEGATIVE** | thin output **but** the tool is a silent-by-design scanner (`nuclei`/`dalfox`/`ffuf`/`gobuster`/`sslscan`…) **and** its command carries `-o <file>` or `-silent` | ran, found nothing — a legitimate negative |
| **FAILED** | output contains `not recognized` / `command not found` / `can't open file` / `no module named` / `error: the following arguments` / `unrecognized arguments` / `Traceback` | **executed nothing.** This is the overclaim. |
| **ABSENT** | binary not on disk at the path the router believes | mis-wired tool path |
| **N/A** | class cannot exist for this target (`wpscan` on non-WordPress, web3 tools on a web app) | honest skip, must carry a reason |

Measured on `account.jetbrains.com`: **70 evidence files → 37 REAL, 12 valid silent negatives,
15 FAILED, 5 N/A, 1 absent.** The log claimed **63 `EXECUTED`**; only ~28–53% had actually exercised
the target. **The 0D gate passed 13/13 anyway** — it counted files, never content.

**The silent-negative nuance matters.** An 18-byte `nuclei-<vector>.txt` is *not* an overclaim: nuclei
writes findings to `-o`, so "ran, found nothing" is legitimately small. Do **not** sweep those into
"broken" — that turns a clean negative into a false alarm and buries the 15 real failures.

---

## 2. `tool-health-probe.py` — probe every tool once, persist the verdict

Run once per host (or whenever a tool's behaviour is in doubt). Writes
`~/AppData/Local/hermes/tools-registry.json`:

```json
{ "summary": { "WORKS": [...], "RAN": [...], "SILENT": [...], "TIMEOUT": [...], "BROKEN": [...] },
  "tools": { "<name>": { "status": "WORKS", "rc": 0, "secs": 12.4, "bytes": 546, "cmd": "..." } } }
```

Status vocabulary (keep it — the pipeline reads it):

* `WORKS` — reached the target (≥1 live signal)
* `RAN` — executed, no target signal (e.g. `--help`, or an API that needs a live peer)
* `SILENT` — **no output on EITHER stream** (see the stderr trap in §6)
* `TIMEOUT` — exceeded its cap (tree-killed) — **not automatically a failure**, see §9
* `BROKEN` — bad path/invocation, detected from the output markers in §1

**Read BOTH streams before assigning any status.** A probe that reads `stdout` only will score a
perfectly healthy tool as `SILENT` if that tool logs to `stderr`. Measured: `dalfox` wrote **3049 B to
stderr and 95 B to stdout** — the first probe called it `SILENT` and the registry then claimed a working
XSS scanner was producing no output. It was proving the opposite of the truth (§6).

**Gate 0A reads this file** and logs `tool health: N invocable, M broken/silent (…)`, persisting the
summary into `contract-audit.json`. That is what converts "a tool is broken" from a per-run
rediscovery into a recorded fact.

### Probe result on this host (2026-10-11) — the shape to expect

```
WORKS  19 : dnsreaper ffuf gitleaks httpx katana linkfinder naabu nuclei secretfinder
            sqlmap sslscan subfinder subjack theHarvester trufflehog wafw00f whatweb
            wpscan xsstrike
RAN     6 : gobuster graphw00f grpcurl jwt_tool kube-hunter patator
SILENT  1 : dalfox            (legit: silent-by-design, 0 findings)
TIMEOUT 4 : amass arjun cloud_enum interactsh
BROKEN 13 : CORScanner DNSReaper byp4xx clairvoyance cmseek fierce graphqlmap
            kiterunner nikto smuggler sstimap subzy
```

Six of those `BROKEN` were **path/entrypoint** problems, fixed in §3; six were **genuinely not
installed**; one needs a runtime (PHP) that is absent. **Distinguish those three cases before
reporting anything** — "not installed" is not a bug, it is a state.

---

## 3. Repair recipes (the six that were repairable)

### 3.1 Python tools are `.bat` shims — not repos under `tools/`

`nikto`/`clairvoyance`/`graphqlmap`/`smuggler`/`sstimap`/`xsstrike`/`nikto`/`wpscan`/`patator` resolve
to `<Python>/Scripts/<name>.bat`. Looking for `tools/<name>/<name>.py` produces `can't open file`.
**Take the path from `tool_router.TOOL_PATHS`, never guess a directory** — that dict is the router's own
belief and is the right starting point:

```python
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("tr", r"...\hermes\scripts\tool_router.py")
tr = importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)
tr.TOOL_PATHS["nikto"]     # -> ...\Python314\Scripts\nikto.bat   (use THIS)
```

### 3.2 Go on MSYS — the shell hands `go.exe` POSIX paths and it refuses

Symptom (two different wordings, same cause):
```
go: GOPATH entry is relative; must be absolute path: "/c/Users/WINDOWS10/go".
go: GOMODCACHE entry is relative; must be absolute path: "\\c\\Users\\WINDOWS10\\go\\pkg\\mod"
```
Fix — set **native** absolute paths in the child env (and persist with `go env -w`):

```python
env = dict(os.environ)
env["GOPATH"]     = r"C:\Users\<user>\go"
env["GOMODCACHE"] = r"C:\Users\<user>\go\pkg\mod"
env["GOCACHE"]    = r"C:\Users\<user>\go\cache\build"
env["GOBIN"]      = r"C:\Users\<user>\go\bin"
subprocess.run("go install <mod>@latest", shell=True, env=env)
```
A `.bat` wrapper with `set GOPATH=...` works equally well when you must run it from a shell.

### 3.3 Module paths drift — read `go.mod`, do not trust the repo URL

| tool | naive | correct | why |
|---|---|---|---|
| `kiterunner` | `assetnote/kiterunner/cmd/kr` | `assetnote/kiterunner@latest` | v1.0.2 has **no `cmd/kr`** package; root package emits `kiterunner.exe` |
| `subzy` | `LukaSikic/subzy` | `PentestPad/subzy@latest` | repo declares `module github.com/PentestPad/subzy` |
| `byp4xx` | bash script | **Go**: `go mod init byp4xx && go build -o byp4xx.exe .` | the repo contains `byp4xx.go`, no `.sh` |

Error text to recognise: `module declares its path as: X but was required as: Y` →
**use the declared path**. `does not contain package <pkg>` → the package path is wrong, try the root.

### 3.4 Two traps when *locating* a built binary

* **Never substring-match a short name.** Glob `*kr*` matched **`hakrawler.exe`** ("ha**kr**awler") and
  the pipeline then recorded kiterunner as WORKS pointing at the wrong binary. Match the **exact stem**
  (`f.stem.lower() in ("kr", "kiterunner")`) and, when cheap, confirm the binary **self-identifies**
  (`"kiterunner" in --help output`).
* **Never accept a path that is not a real file.** A fallback that yielded `"."` then ran `"." --help`,
  which exits non-zero *with output* → scored `WORKS`. Require `Path(p).is_file()` **before** recording,
  and drop any previously-written `TOOL_PATHS` entry that fails that test.

---

## 4. `subprocess(text=True)` without `errors=` silently destroys output

Found while investigating an unrelated crash. On Windows, when a tool emits non-UTF-8 bytes (nuclei,
dalfox and sqlmap do routinely), the decode error is raised **inside subprocess's reader thread** — so
the call **returns `rc=0` with EMPTY stdout**. No exception, no traceback: the tool looks like it ran
and produced nothing.

Measured, with a 45-byte fixture `b"OK\xfa\xff\xfeEND\n"`:

```
text=True                 -> rc=0, stdout=''            <<< OUTPUT LOST, silently
text=True, errors="replace" -> rc=0, stdout='OK???END'    <<< content preserved
```

Fix: **every** text-mode spawn gets `errors="replace"`. 51 call sites needed it across
`audit-pipeline-orchestrator.py` and `force-full-execution.py`. Splice mechanically from the AST (find
each `subprocess.{run,Popen,call,check_output}` whose keywords include `text` but not `errors`) rather
than editing by hand; back up first, `py_compile` after, then feed real non-UTF-8 bytes through the
patched function and assert the readable part survives.

This is the same family as §1: **a loss that presents as a success.**

---

## 5. Behaviour rule — fix, then ADVANCE (do not symptom-chase)

The operator's complaint was about **cadence**, not about any single bug:

```
wrong:  run 4h → find bug → fix → restart 4h → find next bug → fix → …
right:  audit the whole chain statically (5 s) → fix EVERYTHING found → run ONCE
```

Symptom-chasing produced **5 restarts ≈ 20 h for 10 bugs**, then another 9 in the follow-on
(`#15`–`#19`), several of which were **created by the previous fix**: #11 (214× loop) came from the
skill-evidence order fix, #16 (comments executed as commands) came from declaring a new stage.

Concrete discipline:

1. **Before any restart**, run `pipeline-contract-audit.py` — it is a *prerequisite*, not a
   post-mortem. Also run `tool-health-probe.py` if tools are in doubt.
2. **Fix the found defect and keep moving.** One correct fix at the right layer > five patches on
   symptoms. When a fix lands, do not re-litigate it; go to the next target/finding.
3. **When a gate blocks, ask which of five things it is** before editing anything:
   producer doesn't write the artefact · vocabulary mismatch · phase-inappropriate requirement ·
   **stale/foreign data** · genuinely missing work. Four of those five are *not* "run more tools".
4. **Report coverage by content, never by count.** `N tools executed` is meaningless until §1 has been
   applied. Say `37 of 70 exercised the target; 15 executed nothing` — with the numbers.
5. **A signal from a tool is not a finding.** `byp4xx` printed `Access-Control-Allow-Origin: *  : 302`.
   Verifying properly (4 endpoints × 4 attacker origins, checking ACAO **and**
   `Access-Control-Allow-Credentials`) returned `ACAO: "-"` on all 16 — not exploitable, because a lone
   wildcard cannot be combined with credentials. **Verify, then call it negative** — never promote
   scanner output straight into the report.

---

## 6. Related

* `references/whole-chain-contract-audit.md` — the cross-layer bug class (`#1`–`#16`) and how to write
  the auditor so it measures **code, not text** (the AST-not-regex lesson; and AST is also the fix for
  the manifest that executed comments as commands).
* `references/msys-path-and-tool-invocation-traps.md` — path/quoting traps when writing run scripts.
* `references/gate-artefact-schema-and-status-contract.md` — status vocabulary the gate accepts, and
  the producer↔gate contract when you add a new status.
