---
name: linux-server-ops
description: Operate a Linux server/VM — diagnose "network is slow/heavy" and system-health complaints, inspect daemons (cloudflared, Tailscale, agent gateways), expose a NAT'd machine for SSH, and make a CLI available to a non-owner user.
---

# Linux Server Ops

Class-level playbook for the recurring sysadmin tasks on the user's Linux server
(Tencent Cloud VM running Chiper, Hermes, 9router, cloudflared, Tailscale).

## When to use
- User says "jaringan berat / network is slow / heavy", "cek RAM", "what's running"
- Setting up remote SSH access (e.g. Termius) to a machine behind NAT
- A CLI works for one user but "command not found" for another
- Inspecting cloudflared tunnels, Tailscale status, or agent daemons

## Diagnosing "slow / heavy network" — measure BEFORE concluding
The single most important lesson: **"feels heavy" is usually latency from many idle
keepalive connections, NOT bandwidth.** Prove it with a throughput sample, don't eyeball `ps`.

1. Current throughput over ~5s from `/proc/net/dev` (works without installing anything):
   ```bash
   R1=$(awk '/eth0/{print $2}' /proc/net/dev); T1=$(awk '/eth0/{print $10}' /proc/net/dev)
   sleep 5
   R2=$(awk '/eth0/{print $2}' /proc/net/dev); T2=$(awk '/eth0/{print $10}' /proc/net/dev)
   echo "DL $(( (R2-R1)/5/1024 )) KB/s  UL $(( (T2-T1)/5/1024 )) KB/s"
   ```
   If it's a few KB/s, the network is idle — state that plainly.
2. Count established connections by peer and identify the IPs:
   ```bash
   ss -tnp | awk '{print $5, $6}' | sort | uniq -c | sort -rn | head -40
   getent hosts <ip>   # resolve each peer (AWS/GCP/Cloudflare/Telegram etc.)
   ```
3. Check listening ports + which process owns them: `ss -tulnp`
4. If cloudflared is running, read its Prometheus metrics (see below) — high `request_errors`
   or `response_by_code{status_code="401"}` means **auth failures, not network load**.
5. Report: throughput, total volume since boot (`/proc/net/dev` cumulative), and the real
   cause (latency via tunnels, auth-failure retries, many keepalives).

## Cloudflare tunnel inspection
- Each running `cloudflared` exposes metrics on `127.0.0.1:20241/metrics` and
  `127.0.0.1:20242/metrics` (one per process). Grep the useful counters:
  ```bash
  curl -s http://127.0.0.1:20242/metrics | grep -iE 'ha_connections|total_requests|request_errors|response_by_code|total_retries|active_sessions'
  ```
  - `ha_connections == 4` → healthy (4 redundant edge connections).
  - `response_by_code{status_code="401"}` → requests rejected for bad auth, not load.
- Pitfall: `cloudflared tunnel list` FAILS for token-based (remotely-managed) tunnels with
  "Cannot determine default origin certificate path" — those are configured in the Cloudflare
  dashboard, not locally. Inspect via `ps` cmdline + the metrics endpoint instead.

## Expose a NAT'd machine for SSH (Tailscale → Termius)
Use when the VM has only a private IP (e.g. Tencent `10.x.x.x`) and no public IP.
1. Confirm no public IP: check cloud metadata (`public-ipv4` empty → behind NAT):
   ```bash
   curl -s http://metadata.tencentyun.com/latest/meta-data/public-ipv4   # empty = NAT'd
   ```
2. Install Tailscale (needs passwordless sudo — verify with `sudo -n true` first):
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```
3. Run `tailscale up --ssh` in the BACKGROUND and poll the auth URL (it blocks until auth):
   - `process(action='poll')` / `wait` on the bg session; the URL also shows in
     `sudo tailscale status` output (`Log in at: https://login.tailscale.com/a/...`).
   - Send that URL to the user; after they authenticate, `tailscale up` exits "Success.".
   - **Crucial**: Always enable Tailscale SSH (`tailscale up --ssh` or `sudo tailscale set --ssh`), otherwise remote Termius connection attempts will fail with `connection refused` on the Tailscale IP.
4. Get the stable IP: `sudo tailscale ip -4` (e.g. `100.x.x.x`) and `sudo tailscale status`.
5. Termius config: `Host = <100.x.x.x>`, `Port = 22`, `User = root` or `agentuser`, `Password/Key`.
6. Ensure SSH is on and reachable: `ss -tlnp | grep :22`, `PasswordAuthentication yes`.
7. **Keepalive & Watchdog Protection (Never Disconnect)**:
   - Systemd override for auto-restart:
     Create `/etc/systemd/system/tailscaled.service.d/override.conf`:
     ```ini
     [Service]
     Restart=always
     RestartSec=5s
     ```
   - Watchdog timer: Add a systemd oneshot timer that checks `tailscaled` service active status and `tailscale status` every 60s, automatically re-running `tailscale up --ssh` if marked Stopped.

## Make a CLI available to another user (sudo wrapper)
Problem: a CLI (e.g. `chiper`) lives under `/home/owner/.local/bin/` and the owner's home is
`700`, so another SSH user gets "command not found" and can't even traverse the path.
Fix with a global wrapper + scoped sudoers rule (keeps owner permissions intact):
```bash
# /usr/local/bin/<cmd>
#!/bin/bash
exec sudo -H -u <owner> /home/<owner>/.local/bin/<cmd> "$@"
```
```bash
sudo install -m755 /tmp/<cmd>-wrapper /usr/local/bin/<cmd>
echo '<user> ALL=(<owner>) NOPASSWD: /home/<owner>/.local/bin/<cmd>' | sudo tee /etc/sudoers.d/<cmd>
sudo chmod 440 /etc/sudoers.d/<cmd> && sudo visudo -c
```
- `-H` is REQUIRED so HOME becomes the owner's home and the CLI finds its `~/.config` profile.
- Verify over SSH with a forced TTY for interactive subcommands:
  `sshpass -p PW ssh -tt user@127.0.0.1 'cmd --help'`. Note: TUI subcommands (e.g. `model`)
  refuse non-interactive pipes with "requires an interactive terminal" — that's expected, not a bug.

## Making data folders accessible to an SSH user (The Primary Account Rule)
A common user desire: "I want to SSH in and `ls` / edit `~/.hermes`, `~/.chiperflux`, and the agent files."

**RULE: Prefer setting credentials directly on the primary owner account (`agentuser`) rather than creating a secondary user.**
- **Why creating a secondary user fails for agent files:**
  - `chmod 750` / group-sharing / POSIX ACLs (`setfacl`) on `~/.chiperflux` will be **silently undone** by Chiper Agent runtime, which enforces `0700` on every start / write cycle to protect API keys and tokens. Even if you open it, it locks back down within seconds.
  - POSIX ACL default masks (`mask::---`) get applied when permissions are recalculated, silently stripping `effective:r-x` permissions for secondary users.
- **The clean solution:**
  1. Simply set a password on the existing `agentuser`:
     ```bash
     echo '$USER:password' | sudo chpasswd
     ```
  2. If the user previously asked for a separate user (e.g. `chiper`), kill its processes and delete it:
     ```bash
     sudo pkill -9 -u <tempuser>
     sudo userdel -r <tempuser>
     ```
  3. Symlink the agent CLI globally so non-login shells can find it without path configuration:
     ```bash
     sudo ln -sf "$HOME/.local/bin/chiper" /usr/local/bin/chiper
     ```
  4. Now the user logs into Termius directly as the server user:
     - Full read/write access to `~/.chiperflux`, `~/.hermes`, projects, and sessions without permission fights.
     - Natural passwordless `sudo` (`NOPASSWD: ALL` already granted).
     - Native environment with no wrappers or sudoers shims needed.

## Create a user + password (SSH)
```bash
sudo useradd -m -s /bin/bash <user>
echo '<user>:<password>' | sudo chpasswd
sudo passwd -S <user>   # verify: '<user> P ...'
```
Verify real login: `sshpass -p PW ssh user@127.0.0.1 'whoami'`.

## Full System Access & Root Permissions (VPS Administration)
When a user demands complete, unrestricted access across all system files and other users' home directories:
- **Enable Root SSH Access over Tailscale**:
  ```bash
  echo 'PermitRootLogin yes' | sudo tee /etc/ssh/sshd_config.d/root_login.conf
  sudo sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
  echo 'root:<password>' | sudo chpasswd
  sudo systemctl restart ssh
  ```
- **Unblock Existing User Homes (e.g. `/home/ubuntu` access denied)**:
  Rather than telling the user to use `sudo` every time, apply POSIX ACLs recursively and open traversal permissions:
  ```bash
  sudo chmod 755 /home/ubuntu
  sudo setfacl -R -m u:agentuser:rwx /home/ubuntu
  sudo setfacl -R -d -m u:agentuser:rwx /home/ubuntu
  ```

## Disk / storage cleanup (free space)
Use when the user says "cek penyimpanan", "disk penuh", "mana yang harus dihapus vs dipertahankan".
The deliverable is a DELETE vs KEEP split with exact commands and a before/after `Use%`.

1. Measure first, then locate the big consumers:
   ```bash
   df -h /                                   # note Use% before
   du -sh ~/* ~/.[!.]* 2>/dev/null | sort -rh | head -20
   sudo du -h -d2 / 2>/dev/null | sort -rh | head -20
   ```
2. Classify each into **DELETE** vs **KEEP**:
   - **DELETE — caches (auto-rebuild, zero risk):** `~/.cache/*` (solana, uv, pip,
     ms-playwright), `~/.npm`, `/var/cache/apt`.
   - **DELETE — build artifacts (source stays):** Rust `target/` dirs, `node_modules`.
     A multi-GB git repo is almost always build artifacts — `.git` itself is tiny, so
     verify with `du -sh <repo>/*` before assuming the source is large.
   - **KEEP — active work / runtime:** source repos + `.git`, engagement workspaces,
     `~/.chiper` (agent runtime), system dirs (`/var/snap`, `/usr`, `/opt`).
3. Execute + verify:
   ```bash
   # build artifacts (source untouched)
   cd <repo> && cargo clean && rm -rf target
   find <repo> -type d -name target -prune -exec rm -rf {} +   # recurses nested target/
   # caches
   rm -rf ~/.cache/solana ~/.cache/uv ~/.cache/pip ~/.npm ~/.cache/ms-playwright
   npm cache clean --force
   sudo apt-get clean
   df -h /   # confirm Use% dropped
   ```
   Typical result on the user's VM: ~9-10G recovered, `Use%` 83% → ~63%.

## Pitfalls
- Don't conclude "network heavy" from connection counts or `ps` — sample throughput first.
- Deleting `~/.cache/ms-playwright` breaks the browser / agent-browser tool until it's
  reinstalled (`agent-browser install` or `playwright install`). It's re-creatable but
  costs a re-download — treat as "safe but has a reinstall cost", not "free".
- Deleting `~/.cache/solana` forces a 5-10 min SBF toolchain re-fetch on the next Solana
  build. Safe, but warn the user if they're actively building Solana programs.
- `700` home dirs block symlinks AND sudo wrappers for other users; the wrapper pattern avoids
  loosening permissions on secret-heavy dirs (`.chiperflux`, `.hermes` contain API keys/tokens).
- `sqlite3` CLI is often absent — read SQLite DBs with `python3 -c "import sqlite3; ..."`.
- Token-based cloudflared tunnels can't be listed locally; use the metrics endpoints.

## References
- `references/this-server.md` — concrete details of the user's Tencent Cloud VM
  (IPs, Tailscale account, cloudflared tunnel ports, 9router DB path, chiper CLI paths).
- `references/chiper-custom-repo.md` — customized Chiper repository architecture, data dir standard (`~/.chiper`), bundled skills auto-seeding, and URL audit rules.
- `references/chiperrouter-clone.md` — ChiperRouter architecture, 9router clone procedure, Next.js standalone data dir overrides (`~/.chiperrouter`), and Web UI theming tokens.
