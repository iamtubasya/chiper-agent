## Per-Tool Timeout Values — **HISTORICAL, DO NOT APPLY**

> ⛔ **As of 2026-10-10 this entire model was removed.** There are no per-tool timeouts, no
> `_TIMEOUT_CAP`, no `--budget`, no `--tool-cap`, and no `SKIPPED_BUDGET`. Every one of the 38
> orchestrator step-timeouts and every `_run(cmd, timeout=N)` call was deleted.
> **Current policy: `references/runtime-execution-policy-2026-10-10.md`.**
>
> If you are reading this because you found `--budget` / `--tool-cap` / `_TIMEOUT_CAP` in a script,
> you are looking at a stale copy — check `bundle-sync.py check` for toolkit drift.

### What the values used to be (kept only so old logs make sense)

| Tool | old timeout | old retry |
|------|---------|-----------|
| sqlmap | 900s | 3x |
| dalfox / nuclei (per tag) / gobuster dir | 600s | 3x |
| CORScanner / race-checker.py | 300s | 3x |
| graphqlmap | 120s | 3x |
| subfinder | 180s | 2x |
| httpx | 240s | 2x |

---

## The lesson that SURVIVED — and is why the whole design changed

**Windows: `subprocess.run(..., shell=True, timeout=N)` kills only `cmd.exe`. The grandchild keeps
the stdout pipe open, so `communicate()` blocks until the grandchild finishes. The timeout value is
a lie.** Measured: a 3 s child under `timeout=1` returned after 3.2 s while *reporting* `TIMEOUT 1s`.

This is the single root cause behind three separate downstream failures:

1. A tool that had already succeeded got killed mid-write because the *parent's* clock ran out.
2. Because killing was unreliable, executors that loop the router (`execute-references.py`,
   `execute-poc-techniques.py`, …) needed their own wall-clock budget — and once a budget existed,
   the loop **skipped the remaining work** (`SKIPPED_BUDGET` meta entries) rather than finishing it.
3. Skipped work then got "covered" by a hand `curl`, producing garbage that read like coverage.

The operator's verdict on that chain, verbatim:

> *"mmg gkbs kamu buat kl run jalan tanpa batas, lalu kl timeout ad guard auto start atau auto fix
> agar problemnya diperbaiki baru djalankan lagi tools nya? krn kdg diskip yg buat akhirnya cm curl
> dan sia2 hasilnya sampah semua"*

### The replacement model

| problem | old answer | current answer |
|---|---|---|
| tool runs long | kill at N seconds | **run to completion** — no clock |
| tool goes silent | kill at N seconds | `toolguard.py` → `[STALL-WARN]` with PID + command; **never killed** |
| tool fails | skip, fall through to curl | `autofix.py` → diagnose → repair → **re-run the same tool** |
| tool cannot be fixed | silent skip | record **NO RESULT**; `NO_CURL_FALLBACK` forbids a curl substitute |
| unblock needed | automatic | deliberate: `toolguard.py unblock --pid N` |

### If you inherit a script that still loops the router

Do **not** re-add a budget. A loop over N calls is fine now — each call is unbounded and
stall-guarded. What you must verify instead:

```bash
grep -c "timeout=" <script>          # live timeout= must be 0 (comments/legacy path excluded)
grep -n "SKIPPED_BUDGET" <script>    # must be gone — nothing may be skipped for time
python autofix.py verify             # 7/7
python toolguard.py verify           # 6/6
```

A `SKIPPED_BUDGET` status surviving in a producer means the loop still silently drops work, and the
0D gate will read that as thin evidence.
