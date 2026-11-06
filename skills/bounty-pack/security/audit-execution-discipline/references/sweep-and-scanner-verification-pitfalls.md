# Sweep & scanner-verification pitfalls (Vinted engagement, 2026-10-02)

Two failure modes found while trying to run a "use ALL tools" sweep across 10 in-scope hosts.
Both produce **fake negatives** — an empty or plausible-looking artifact that is not a result.

## 1. nuclei never leaves the parser when `-t` points at a huge template tree

```
nuclei -u "https://www.vinted.com" -silent -rl 4 -c 3 -timeout 10 \
       -t "D:/data hermes/nuclei-templates/http" \
       -tags tech,exposure,misconfiguration -no-meta -duc        # -> 0 bytes after 330 s
```

`D:/data hermes/nuclei-templates/http` holds **11,376** YAML files. nuclei parses *every* template
before the `-tags` filter is applied, so on this box the run never reached the request phase. The
evidence file is empty and a naive status mapper records `EXECUTED`.

**Canary first (run this before believing ANY nuclei negative):**

```bash
mkdir -p /tmp/nucleitest && cd /tmp/nucleitest && echo '<html><title>t</title></html>' > index.html
(python -m http.server 8123 &) ; sleep 3
curl -s -o /dev/null -w "canary=%{http_code}\n" http://127.0.0.1:8123/     # must be 200
time timeout 200 nuclei -u "http://127.0.0.1:8123" -silent \
     -t "D:/data hermes/nuclei-templates/http/technologies" -no-meta
# observed: prints the target twice (tech detected) in ~2m16s  -> tool works
```

**Fix:** repeat `-t` on **narrow subdirectories**, not the whole `http/` tree:

```
-t <root>/technologies -t <root>/exposures -t <root>/misconfiguration
```

`-tags` does NOT avoid the parse cost. Budget ~2-3 min per host even so.

## 2. `subprocess.run(capture_output=True, shell=True)` deadlocks its own timeout

A sweep wrapper invoking scanners through `shell=True` with `capture_output=True` hung well past
its `timeout=330`: the grandchild (`nuclei.exe`) inherited the stdout pipe, so `communicate()`
kept blocking after the shell was killed. Symptom: the job looks "still running" for 8+ minutes,
no evidence file appears, `taskkill` is needed to clean up.

**Fixes — apply both:**

```python
with open(evidence_file, "w", encoding="utf-8") as fh:
    fh.write(f"=== TOOL   : {tool}\n=== TARGET : {target}\n=== CMD    : {cmd}\n")   # Python writes it
    fh.flush()
    try:
        p = subprocess.run(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT, timeout=T)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc = "TIMEOUT"
    fh.write(f"\n=== END rc={rc} ===\n")                                            # sentinel
```

- `stdout=<file handle>`, never `capture_output=True` — nothing holds a pipe.
- Write the header/exit sentinel **from Python**. Interpolating the command line into a shell
  `echo "=== CMD: {}"` broke on the command's own double quotes; the shell then ran only the echo,
  every tool "completed" in 0.1 s, and a whole host was reported `EXECUTED` with **zero requests
  sent**. Always sanity-check the timing: a scanner cannot sweep a host in 0.1 s.

## 3. Status vocabulary for a sweep (never guess from the artifact)

| Observed | Status |
|---|---|
| expected tool banner present + rc=0 | `EXECUTED` |
| banner present, then error/timeout | `RAN_WITH_ERROR` |
| `usage:` / `flag provided but not defined` / `unrecognized arguments` | `FAILED_USAGE` (blocks the gate) |
| block page ("Just a moment", "Access Denied", "RBAC: access denied") | `BLOCKED_EDGE` — a coverage gap, **not** a negative |
| 0 bytes, no banner, no completion sentinel | `NO_OUTPUT` / re-run pending — **never** "clean" |

Also: kill stragglers before starting the next tool. After three aborted sweeps this box had
4 leftover `nuclei.exe` (323 MB / 353 MB RSS) still running and a stray `python -m http.server`
holding a port — check `tasklist | grep -iE "nuclei|gobuster|dalfox|corscanner"` and kill by PID,
not just by image name.
