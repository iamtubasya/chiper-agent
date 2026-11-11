# Skip Guards & Ledger Provenance — the "existence is not evidence" family

Measured 2026-10-11 on `account.jetbrains.com` (JetBrains Hub/account audit). Operator
verdict after three hours of rework: *"kenapa jadi malah bolak balik bug … kamu harus
lebih fleksibel, jgn dkit2 bug"* and later *"jgn ada skip2 lagi, udh berkali2 d setting"*.

**Root cause of that whole session was ONE function.** The audit work itself was done and
correct (15/15 variants, 15/15 business-logic, 69/70 tool-evidence all stamped with the
right target). The pipeline refused to believe it.

---

## §1 The existence-only skip guard (the primary defect)

```python
# audit-pipeline-orchestrator.py — BEFORE
def _done(fname):
    f = self.output_dir / fname
    return f.exists() and f.stat().st_size > 100
```

Six sub-phases were gated on it:

```python
skip_c2  = _done("variant-usage.json")
skip_c3  = _done("business-logic-usage.json")
skip_c4  = _done("poc-execution.json")
skip_c5  = _done("poc-variant-usage.json")
skip_c6  = _done("reference-usage.json")
skip_c6b = _done("poc-techniques-usage.json")
```

`output_dir` is **reused across targets**, so five ledgers left over from
`plugins.jetbrains.com` (dated 2026-10-10) satisfied the check. Result:

```
SKIP sub-fase (sudah ada di disk): C2=Y C3=Y C4=Y C5=Y C6=Y C6b=Y
```

**Zero work executed, full credit in the report.** The report claimed
"15/15 variants, 15/15 business-logic, 16 references" for `account.jetbrains.com` —
all of it inherited from a different target.

### The fix — three conditions, all required

```python
_run_start_ts = None
try:
    _rmd = json.loads((self.output_dir / "run-meta.json").read_text(encoding="utf-8"))
    _sa = str(_rmd.get("started_at") or "")
    if _sa:
        _run_start_ts = datetime.fromisoformat(_sa).timestamp()
except Exception:
    _run_start_ts = None

_host = (self.target or "").replace("https://", "").replace("http://", "").strip("/")

def _done(fname):
    f = self.output_dir / fname
    if not (f.exists() and f.stat().st_size > 100):     # 1. exists, real content
        return False
    if _run_start_ts is not None:
        if f.stat().st_mtime < _run_start_ts - 3600:    # 2. written during THIS run
            log(f"  ⚠️  {fname} is STALE — stage will RE-RUN, not skip")
            return False
    if _host:
        raw = f.read_text(encoding="utf-8", errors="replace")
        if _host not in raw:                            # 3. belongs to THIS target
            others = set(re.findall(r"https?://([a-z0-9.-]+)", raw))
            foreign = {o for o in others if _host not in o and "target.com" not in o}
            if foreign:
                log(f"  ⚠️  {fname} references OTHER host(s) — stage will RE-RUN")
                return False
    return True
```

**Verify the guard both directions before trusting it.** The test that mattered:

```
variant-usage.json          RE-RUN   STALE (mtime 2026-10-10 11:14)
business-logic-usage.json   RE-RUN   STALE (mtime 2026-10-10 12:41)
poc-execution.json          RE-RUN   STALE
reference-usage.json        RE-RUN   STALE
dom-xss-usage.json          SKIP     fresh + this target
rce-verification.json       SKIP     fresh + this target
impact-verification.json    SKIP     fresh + this target
```

A guard that only ever says "SKIP" is indistinguishable from no guard. A guard that only
ever says "RE-RUN" is just slow. **Both verdicts must appear in the same test run.**

### The same shape in `_force_state_complete()`

```python
f = Path(os.environ.get("CHIPER_PATH") or os.environ.get("CHIPER_HOME") or (Path.home() / ".chiper")) / f"/skills/bounty-pack/trackers/force-state-{safe}.json"
if d.get("status") != "complete": return False
n = len(list(ev.iterdir()))                       # ONLY counted files
if n == 0: return False
return True
```

`trackers/` is shared across targets and the slug can collide after a reset. Add:

```python
# CROSS-CHECK 1: the marker must describe THIS target
_mk_t = str(d.get("target") or "")
if _mk_t and _mk_t.rstrip("/") != self.target.rstrip("/"):
    log(f"  ⚠️  force-state belongs to {_mk_t!r}, not this target — C1 will run")
    return False
# CROSS-CHECK 2: non-empty evidence/ is not enough — must be OUR evidence
_host = self.target.replace("https://", "").replace("http://", "").strip("/")
if not any(_host in p.read_text(encoding="utf-8", errors="replace")[:2000]
           for p in files[:80]):
    log(f"  ⚠️  no tool-evidence file names {_host} — C1 will re-run")
    return False
```

**Generalisable rule:** every "already done, skip it" guard must answer
*whose* work this is and *when* it was produced, not merely *whether a file exists*.

---

## §2 `--derive` must trust the LOG over a file-name scan

`asset-coverage.py --derive` validated a ledger row by parsing the header of
`v["evidence"]`. But `v["evidence"]` was filled by **scanning for any file whose name
matched the tool** — so it could point at a *different run's* file:

```
tools-usage.json had:   nuclei -> tool-evidence/nuclei-cmdi.txt   @09:46 (correct, today)
ledger had been filled: nuclei -> tool-evidence/xxe-nuclei.txt    @2026-10-10
--derive read the second one -> "timestamp predates the run" -> NOT_RUN
```

22 genuinely-executed assets flipped `USED → NOT_RUN` on **every** re-derive. That is the
mechanical cause of "fix one thing, gate fails again, fix another thing".

### Fix — the log is authoritative when it has an entry

```python
_authoritative = None
for _e in (tools_usage or []):
    if str(_e.get("tool", "")).lower() == str(v.get("asset", "")).lower():
        _ep = (_e.get("evidence_file") if Path(_e["evidence_file"]).is_absolute()
               else td / _e["evidence_file"])
        if _ep.exists():
            _authoritative = _ep
            break

if _authoritative is not None:
    _a = _parse_evidence_header(td, _authoritative)
    ... judge _a ...          # never fall through to the scanned file
    continue
# only when the log has NOTHING for this asset: judge the scanned file
```

### And a CHILD URL of the target is not a mismatch

```python
# BEFORE: strict equality rejected genuine same-run evidence
if _norm_target(hdr["target"]) != run_target:  -> bad_t

# AFTER: only a DIFFERENT HOST is a mismatch
_et = _norm_target(hdr["target"])
_same_host = (_et == run_target
              or _et.startswith(run_target + "/")
              or _et.split("/")[0] == run_target.split("/")[0])
```

Real case it wrongly rejected:
`run target https://account.jetbrains.com` vs evidence
`# TARGET: https://account.jetbrains.com/assets/bad/fonts.less?v=ff619074`.

---

## §3 Cross-target MERGE pollution

```python
# force-full-execution.py — BEFORE
# MERGE with existing log (re-runs must NOT wipe earlier evidence)
merged = list(existing) + new_entries
```

The comment is right for a **re-run of the same target** and poison for a **different
target**. Measured: `tools-usage.json` held **71 entries, 56 of them from
`plugins.jetbrains.com`**. `--derive` then rejected the fresh ones as stale.

```python
def _this_target(e):
    t = str(e.get("target") or e.get("url") or "")
    if t:
        return self.target.rstrip("/") in t or t in self.target
    if _run_start:                       # no target field -> use the run window
        ts = str(e.get("timestamp") or e.get("executed_at") or "")
        return bool(ts) and ts >= _run_start
    return False

kept = [e for e in existing if _this_target(e)]
_dropped = len(existing) - len(kept)
```

Verified both directions on the real file: **56 dropped, 15 kept**; a synthetic same-target
entry still merges.

---

## §4 Regex-parsing Python source turns COMMENTS into data

```python
# audit-pipeline-orchestrator.py — BEFORE
m = _re.search(r'"0C":\s*\{[^}]*?"tools":\s*\[([^\]]+)\]', asset_coverage_src, _re.S)
MANIFEST = [x.strip().strip('"').strip("'") for x in m.group(1).split(",") if x.strip()]
```

A regex cannot see `#`. When a comment was added inside the list:

```python
MANIFEST["0C"]["tools"] = [
    "dom-xss",
    # DOM-XSS browser engine (2026-10-10) — closes the SPA blind spot.
    "rce-verify",
]
```

…the comment became a **tool name**. `force-full-execution` executed
`# DOM-XSS browser engine (2026-10-10) — closes the SPA blind spot.` as a command
(exit 127) and wrote entries whose `tool` field was **prose**:

```
{"tool": "# DOM-XSS browser engine (2026-10-10) — closes the SPA blind spot"}
{"tool": "so\n               # a \"clean\" result there is a false negative"}
{"tool": "# RCE/command-injection VERIFIER (2026-10-10) — detection is..."}
```

`--derive` could never match a real asset to those. **Fix: parse with `ast`** — comments
are not nodes, so only string literals can come out:

```python
import ast
tree = ast.parse(src)
for node in ast.walk(tree):
    if not isinstance(node, ast.Dict): continue
    keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
    if "0C" not in keys: continue
    ...
    MANIFEST = [e.value for e in lst.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)]
```

**Detection heuristic for the audit tool:** any script that does
`re.search(...)` over a **`.py` file it reads** is suspect — flag it.

---

## §5 `subprocess(text=True)` without `errors=` loses output SILENTLY

```python
p = subprocess.run(cmd, capture_output=True, text=True)          # no errors=
```

The decode happens in a **reader thread**. On invalid UTF-8 the thread raises
`UnicodeDecodeError` — and `subprocess.run` returns **`returncode=0` with EMPTY stdout`.
No exception surfaces. Proof, side by side with a fixture that writes `b"OK\xfa\xff\xfeEND"`:

```
UNFIXED (text=True)       -> rc=0  stdout=''        <- OUTPUT GONE, no error
FIXED   (errors='replace') -> rc=0  stdout='OK???END' <- content preserved
real pipeline function    -> out='OK???END'
```

Scanner output is full of non-UTF-8 bytes, so a tool producing real findings would be
recorded as **"ran, produced nothing"** — the same class as §1.

**Fix — 51 call sites, applied by AST, not by hand:**

```python
# AST-driven bulk fix: only rewrite real subprocess spawn calls
SPAWN = {"run", "Popen", "call", "check_output", "check_call"}
for node in ast.walk(tree):
    if not isinstance(node, ast.Call): continue
    nm = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
    if nm not in SPAWN: continue
    kws = {k.arg: k for k in node.keywords if k.arg}
    if "text" not in kws and "universal_newlines" not in kws: continue
    if "errors" in kws: continue                     # idempotent
    # splice `, errors="replace"` right after the `True`
```

Never `sed`/regex this — a string literal or comment containing `text=True` would corrupt.

---

## §6 A classifier that reads one stream is blind (dalfox "SILENT")

`tool-health-probe.py` decided `SILENT` from **stdout only**. dalfox writes its banner,
progress AND findings to **stderr**:

```
dalfox-xss.txt  (1459 B)  stdout=95 B   stderr=1323 B
```

Classified `SILENT` ("ran, no output"). It had in fact parsed the response and mined
parameters:

```
[I] Found 0 testing point in DOM base parameter mining
[I] Content-Type is text/html;charset=UTF-8
[I] X-Frame-Options is SAMEORIGIN
```

**Prove a tool WORKS by giving it something to find** — spin an echo server that reflects a
parameter and confirm the tool reports the hit:

```python
# reflect ?q= verbatim into the body, then
subprocess.run(["dalfox","url",f"http://127.0.0.1:{PORT}/?q=test","--skip-bav","--no-color"])
```
```
[POC][V][GET][headless] http://127.0.0.1:8947/?q=%3Cimg%2Fsrc%2Fonerror%3D.1%7Calert%601%60%3E
[V] Triggered XSS Payload (found dialog in headless)
```

Silence on the real target then means **no reflectable parameter** — a valid negative —
not a broken tool.

### Corollary: never write the tool registry by hand

A hand-written registry recorded `nikto: WORKS` for a wrapper whose target script
**did not exist on disk**. Rebuild the registry **from an actual invocation**:

```python
# probe: exists? runs? reaches the network/parses input?
BAD  = ("not recognized","command not found","can't open file","no such file",
        "modulenotfounderror","no module named","is not a valid win32")
ARGS = ("error: the following arguments","unrecognized arguments")
# WORKS = no BAD/ARGS marker AND >=1 live signal
# SILENT = ran with no output on EITHER stream
```

Also distinguish **legitimately-slow** from **broken**: `arjun` (51 chunks) and
`cloud_enum` (1837 checks) were both classified TIMEOUT at caps that were simply too
small — they progressed steadily. `interactsh` is an **OOB canary**: registering then
waiting IS success, so a wall-clock cap tripping is expected, not a failure.

---

## §7 `go install` on Windows: MSYS paths leak into `go.exe`

```
go: GOMODCACHE entry is relative; must be absolute path: "\c\Users\WINDOWS10\go\pkg\mod"
```

bash passes MSYS-style paths to the native `go.exe`, which refuses them. Set native
absolute paths first and persist them:

```bash
export GOPATH='$HOME/go'
export GOMODCACHE="$GOPATH\pkg\mod"
export GOCACHE="$GOPATH\cache\build"
export GOBIN="$GOPATH\bin"
go env -w GOPATH="$GOPATH" GOMODCACHE="$GOMODCACHE" GOCACHE="$GOCACHE" GOBIN="$GOBIN"
```
A `.bat` with `set VAR=C:\...` then `cd /d "<dir>"` also works when the bash→native hop
keeps mangling them.

Module paths worth knowing (both were wrong on the first attempt):
- `github.com/assetnote/kiterunner@latest` — v1.0.2 has **no** `cmd/kr` package; the
  binary is `kiterunner.exe`.
- `github.com/PentestPad/subzy@latest` — the repo was **renamed**; `LukaSikic/subzy`
  declares its module as `github.com/PentestPad/subzy`.
- `byp4xx` is **Go** (`byp4xx.go`), not bash — needs `go mod init` + `go build`.

### Exact-stem matching, never substring

Locating a produced binary with `glob("*kr*")` matched **`hakrawler.exe`** (`kr` is inside
"haKRawler") and it was recorded as kiterunner. Require an exact stem:

```python
next((f for f in GOBIN.glob("*.exe") if f.stem.lower() in ("kr","kiterunner")), None)
```
**And reject any path that is not `Path(p).is_file()`** — a `"."` fallback scored a
non-existent path as `WORKS`.

---

## §8 Diagnostic order that ends the loop

When the same gate fails repeatedly, do **not** fix the next symptom. Establish which
layer is lying, in this order:

1. **Is the work actually done?** Count the evidence artefacts and read their target
   stamps. On `account.jetbrains.com` all 15 variants / 15 bizlogic / 69 tool files were
   real and correctly stamped — the *ledger* was the liar, not the work.
2. **Who wrote the ledger, and when?** `stat()` its mtime against `run-meta.json
   started_at`. Stale ⇒ §1.
3. **Which file did the validator actually read?** Print the resolved evidence path, not
   the asset name. Different file from the one the log names ⇒ §2.
4. **Did the producer even run?** Look for the skip line (`SKIP sub-fase …`). If the
   producer was skipped, no downstream fix can help.

Only then touch code. Rewriting a ledger **from artefacts that exist and name this target**
is reconciliation, not fabrication — but say so in the record (`regenerated_from_evidence:
true`) and never let it mark anything USED that has no artefact.

---

## §9 Checklist to run before declaring a pipeline fix effective

```
[ ] contract audit clean           python pipeline-contract-audit.py   (exit 0)
[ ] skip guards proven BOTH ways    at least one SKIP and one RE-RUN in the same test
[ ] decode fixed everywhere         grep for `text=True` without `errors=`
[ ] registry from real invocations  not hand-written
[ ] streams read together           stdout AND stderr in every classifier
[ ] paths that are not files rejected
[ ] stale artefacts quarantined     `_QUARANTINE/`, never deleted
```
