---
name: linux-server-diagnostics
description: Diagnose Linux server performance complaints — "feels slow", "network heavy/lemot", RAM/CPU pressure, "what's running", service health. Ordered diagnostic ladder with exact commands, plus the key insight that perceived slowness is usually latency or app-side retries, NOT bandwidth saturation.
---

# Linux Server Diagnostics

Use when a user reports the server "feels slow", "network is heavy", asks to check
RAM/CPU/processes, or wants to know what's running. Work the ladder in order and
**measure before concluding** — the most common mistake is declaring the network
congested without measuring actual throughput.

## The diagnostic ladder

### 1. RAM / load (always first — cheap and rules out the obvious)
```bash
free -h && uptime
```
- Report **available**, not `free`. `free` (the truly-empty column) looks tiny on
  any healthy box because Linux keeps pages in `buff/cache`; that cache is
  reclaimable and shows up in `available`.
- `uptime` load average < #cores = fine.

### 2. What's actually running (by memory)
```bash
ps aux --sort=-%mem | head -30
```
- Process names are truncated in `ps` (e.g. `next-server (v1...`). For the full
  command line use `cat /proc/<PID>/cmdline` or `ss -tnlp`.

### 3. Network throughput — MEASURE, don't assume
Sample the interface counters twice over an interval:
```bash
R1=$(awk '/eth0/{print $2}' /proc/net/dev); T1=$(awk '/eth0/{print $10}' /proc/net/dev)
sleep 5
R2=$(awk '/eth0/{print $2}' /proc/net/dev); T2=$(awk '/eth0/{print $10}' /proc/net/dev)
echo "down $(( (R2-R1)/5/1024 )) KB/s  up $(( (T2-T1)/5/1024 )) KB/s"
```
- **Key insight:** a box can be near-idle (2–3 KB/s) while the user insists the
  network is "heavy". The real causes are usually one of:
  1. **Latency**, not bandwidth — every hop through a tunnel (cloudflared) or VNC
     adds round-trip delay but carries almost no bytes.
  2. **App-side retry loops** — an app retrying failed/unauthorized requests
     (401) across many accounts makes it *feel* slow while generating tiny traffic.
  Always confirm throughput before blaming bandwidth.

### 4. Who's connected (listening + established)
```bash
ss -tulnp                              # listening sockets + owning process
ss -tnp | awk '{print $5, $6}' | sort | uniq -c | sort -rn   # established, grouped
```
- Grouping established connections by remote `addr:port` immediately shows the
  dominant outbound targets. Resolve unknown IPs with `getent hosts <ip>`.

### 5. Service health (the actual root cause is usually here)
Go to the app's own telemetry/logs/database, not just network counters. When
throughput is low but the user reports slowness, look for **auth failures and
retries** inside the app (e.g. a router proxying to many provider accounts, where
expired OAuth tokens / dead keys produce a stream of 401s).

## Pitfalls
- **Don't conflate "feels heavy" with "is heavy".** Measure current throughput
  (step 3) first. Idle + many persistent connections = latency problem, not
  bandwidth problem.
- **`free -h` misreading** — never quote the `free` column as "low memory"; quote
  `available`.
- **`sqlite3` CLI is often absent** on minimal boxes. Use Python's stdlib instead:
  ```bash
  python3 -c "import sqlite3; c=sqlite3.connect('/path/db'); \
    print([r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")])"
  ```
- **`cloudflared tunnel list` fails** on remote-managed (token-based) tunnels —
  no origin cert present. Use the local Prometheus metrics endpoint instead
  (see `references/cloudflared-and-9router.md`).
- **`journalctl -u <svc>` can return "No entries"** for a non-privileged user
  when the service runs as root — logs may go to a file or be invisible without
  `sudo`. Check the process's `environ` and file descriptors for the real log sink.

## References
- `references/cloudflared-and-9router.md` — cloudflared metrics endpoint usage and
  the 9router (AI API aggregator) SQLite schema, used to trace 401 auth failures.
