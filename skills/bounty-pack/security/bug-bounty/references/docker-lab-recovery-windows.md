# Recovering a wedged Docker Desktop on the 6 GB Windows box

This host has **6 GB RAM**. A local lab (SQL Server + app server + agent) plus a heavy scan
(`nuclei` over a few thousand templates, `sqlmap`, a broad `SELECT ... LIKE` sweep across every
string column of a 291-table DB) will exhaust it. Free RAM drops to ~450 MB and the symptom is
**not** an obvious error — it is silence.

## Symptoms (in the order they appear)

1. `docker ps` / `docker info` / `docker images` return **empty output with exit 0**. A CLI call
   killed by `timeout` looks exactly like "nothing there".
2. Then: `request returned 500 Internal Server Error for API route ... /v1.56/containers/json,
   check if the server supports the requested API version`. Different Docker API versions reported
   by different tooling is a red herring — the daemon itself is the problem, not the client.
3. The shell is still fine. Prove it with `echo alive; hostname; date` before blaming the box.
4. `tasklist | grep -iE "docker|vmmem|wsl"` still shows Docker Desktop processes — so "Docker is
   running" is not evidence the engine is usable.
5. `wsl.exe -l -v` shows `docker-desktop  Running` even while the engine is dead.

## Diagnostic that separates "box" from "engine"

```bash
echo alive; hostname; date                     # shell health
docker context ls                              # CLI + context still fine -> engine is the problem
timeout 25 powershell.exe -NoProfile -Command \
  "'freeMB=' + [int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)"
timeout 50 powershell.exe -NoProfile -Command \
  "Get-Process | Sort-Object WS -Descending | Select-Object -First 10 Name,@{n='MB';e={[int](\$_.WS/1MB)}} | Format-Table -AutoSize"
```

`freeMB` under ~500 MB with the scan already finished = the VM has been squeezed and dockerd is
starved (swap-thrashing), so engine calls time out rather than error.

## Fix (worked twice, ~4 min to API-ready)

```bash
export PATH="~/.local/share/Programs/DockerDesktop/resources/bin:$PATH"
wsl.exe --shutdown                 # stops the docker-desktop VM (and any other WSL distro)
# wait ~25 s; Docker Desktop restarts its VM on demand
timeout 120 docker ps -a --format "{{.Names}}|{{.Status}}"
```

**Containers come back by themselves if they were started with `restart: unless-stopped`.** A compose
stack that has no restart policy stays down after the VM dies, and that is easy to mistake for data
loss. Put `restart: unless-stopped` on every service in a lab compose file, the moment you write it.

Verify recovery by polling the app, not by trusting `docker ps`:

```bash
for i in $(seq 1 12); do
  c=$(curl -s -m 8 -o /dev/null -w "%{http_code}" http://127.0.0.1:1322/api/)
  echo "[$i] http=$c"; [ "$c" = "200" ] && break; sleep 20
done
```

A .NET app server took ~10 × 20 s to answer 200 after the VM came back (SQL Server has to come up
first). Do not conclude "the restart lost my data" during those three minutes.

## Notes

- `wsl --shutdown` also stops unrelated distros (here `Ubuntu`, used by the smart-contract tooling).
  They restart on next use; nothing is lost.
- Other containers on the box may show `Exited (137)` (= OOM-killed) long before this. They are not
  the cause; `docker start <name>` restores them when memory allows.
- Prevention that actually works: run scanners at a low rate (`nuclei -rl 10`, `ffuf -p 0.15`) and
  avoid whole-database `LIKE` sweeps; target tables instead.
- The app itself may rate-limit a scanner (`Octopus-RateLimit-Policy: l=200;rpm=60`), making nuclei
  report "skipped as unresponsive". That is the target protecting itself, not a finding — and it
  also means a "0 findings" nuclei run against such a target is a **weak** negative. Say so.
