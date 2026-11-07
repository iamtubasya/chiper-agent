# This server — concrete inventory (Tencent Cloud VM)

Discovered 2026-11. Re-verify with live commands before relying on anything here.

## Identity & network
- Tencent Cloud VM, instance-id `ins-kiidjwia` (metadata: `http://metadata.tencentyun.com/latest/meta-data/`)
- Private IP `10.96.11.209/16` (eth0), **no dedicated public IP** (public-ipv4 metadata empty → behind NAT)
- Egress IP (ipify): `43.152.245.179` (shared NAT, NOT a way to reach this box inbound)
- Tailscale IP `100.109.0.18`, node name `vm-11-209-ubuntu`, account `mohammadtubagus321@`

## Users / SSH
- Primary account: `agentuser` (uid 1002) — owns everything; passwordless sudo (`NOPASSWD: ALL`).
- Termius SSH login configured directly as: `agentuser` or `root` / password `chiper`.
- Root login enabled: `PermitRootLogin yes` in `/etc/ssh/sshd_config` and `/etc/ssh/sshd_config.d/root_login.conf`.
- Secondary `chiper` user was created briefly and later completely deleted (`userdel -r chiper`) per user request to keep full access simple.
- `sshd` on `:22`, `PasswordAuthentication yes`, `PermitRootLogin yes`.
- CLI symlink: `/usr/local/bin/chiper -> /home/agentuser/.local/bin/chiper` (works cleanly for `agentuser` without wrappers).

## Chiper custom repository & fork
- Independent custom repo: `/home/agentuser/chiper` (author: Tubasya, git initialized).
- Full branding sterilization: all Hermes, Nous Research, and ChiperFlux references eliminated.
- Standardized runtime data dir: `~/.chiper/` (formerly `~/.chiperflux/`).
- GitHub remote: `https://github.com/iamtubasya/chiper-agent`.

## Chiper / Hermes / agent stack
- chiper CLI: `/home/agentuser/.local/bin/chiper`, venv `/home/agentuser/chiper-agent/.venv`,
  project `/home/agentuser/chiper-agent`. Version v0.16.0.
- chiper config/profile: `/home/agentuser/.chiperflux/` (auto-tightened to 700 at runtime) — memories, skills, API keys.
- Hermes: `/home/agentuser/.hermes/` (700), serve on `127.0.0.1:9119`, gateway port 9119.
- `chiper model` is an interactive TUI — refuses non-interactive pipes.

## Cloudflare tunnels (2, both token-based / remotely-managed)
- `cloudflared.service` (root, systemd): token `/etc/cloudflared/token`, config `/etc/cloudflared/config.yml`,
  tunnel id `92c05cef-2979-498f-a327-006e33895906`. Metrics `127.0.0.1:20242`.
- `cfd-tunnel-9router` (agentuser): token `/home/agentuser/.cloudflared/token`. Metrics `127.0.0.1:20241`.

## 9router (AI API aggregator/proxy)
- CLI `/home/agentuser/.npm-global/bin/9router`, Next.js dashboard `next-server v16.4.2` on `:20128` (`/` → 307 `/dashboard`).
- Data dir `/home/agentuser/.9router/`; SQLite DB `/home/agentuser/.9router/db/data.sqlite`.
- Tables of interest: `providerConnections` (107 rows, ~82 active), `usageHistory`, `requestDetails` (empty),
  `settings` (round-robin / stickyRoundRobinLimit:1 fallback strategies).
- Providers: many `openai-compatible-chat-*` (apikey) + OAuth accounts (qoder, antigravity, codebuddy-intl,
  grok-cli, kiro, kilocode). 401 errors on the tunnel = expired OAuth tokens / dead keys retried via round-robin,
  NOT network load. sqlite3 CLI absent → use `python3 -c "import sqlite3; ..."`.

## Other
- LXD containers (`lxdbr0`, `forkproxy` SSH on `:2222`); Xvfb + xfce4 + noVNC/websockify `:6080`, x11vnc `:5900-5904`.
