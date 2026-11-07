# Isolated Installer & Repository Testing Container

## Overview
When developing or testing complex installers (`setup-chiper.sh`, system dependency scripts, bug bounty toolchains), running directly on the host VM risks contaminating Python virtual environments, overwriting system configs, installing unwanted global packages, or modifying PATH.

This recipe provides a fully isolated, non-destructive Docker container environment that tests local, uncommitted code safely.

---

## Architecture & Guarantees

1. **Host Safety via `:ro` Mount**:
   The host git repo is mounted to `/repo-src:ro`. The container filesystem permissions strictly block writes to the host directory.
2. **Local Workspace Sync**:
   Inside the container, files are rsynced to the container user's home (`~/chiper`) while excluding host artifacts (`.venv`, `venv`, `__pycache__`).
3. **Identity Alignment**:
   Matches the container non-root user UID/GID to the host caller (`id -u` / `id -g`). Avoids `Permission denied` when accessing files created by the host user.
4. **Zero Git Noise**:
   The test environment directory (e.g. `docker/test-env/`) is placed in `.git/info/exclude` rather than `.gitignore`, so `git status` on the host remains 100% clean.

---

## Implementation Template

### 1. `Dockerfile`
```dockerfile
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm-256color

ARG TARGET_UID=1000
ARG TARGET_GID=1000

# Base utilities needed by setup scripts
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git sudo ca-certificates procps iputils-ping \
    net-tools rsync jq build-essential python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Align default ubuntu user with host user UID/GID
RUN groupmod -g ${TARGET_GID} ubuntu && \
    usermod -u ${TARGET_UID} -g ${TARGET_GID} ubuntu && \
    echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN mkdir -p /repo-src /workspace && \
    chown -R ubuntu:ubuntu /home/ubuntu /workspace

USER ubuntu
WORKDIR /home/ubuntu

COPY --chown=ubuntu:ubuntu test-runner.sh /home/ubuntu/test-runner.sh
RUN chmod +x /home/ubuntu/test-runner.sh

CMD ["/home/ubuntu/test-runner.sh"]
```

### 2. `test-runner.sh`
```bash
#!/bin/bash
set -e

# Sync repo from /repo-src into ~/chiper excluding heavy artifacts
rsync -av --exclude='.venv' --exclude='venv' --exclude='__pycache__' /repo-src/ ~/chiper/ >/dev/null

cat << 'EOF' >> ~/.bashrc
alias sync-repo="rsync -av --exclude='.venv' --exclude='venv' --exclude='__pycache__' /repo-src/ ~/chiper/"
alias test-setup="cd ~/chiper && ./setup-chiper.sh"
alias test-clean="rm -rf ~/chiper ~/.chiper && sync-repo"
export PATH="$HOME/.local/bin:$PATH"
cd ~/chiper
EOF

exec /bin/bash
```

### 3. `run-test-container.sh`
```bash
#!/bin/bash
set -e

HOST_UID=$(id -u)
HOST_GID=$(id -g)
IMAGE="chiper-test-env:latest"
CONTAINER="chiper-installer-test"
REPO_DIR="$(pwd)"

docker build --build-arg TARGET_UID="$HOST_UID" --build-arg TARGET_GID="$HOST_GID" -t "$IMAGE" docker/test-env

docker run -d --name "$CONTAINER" --hostname chiper-test -v "$REPO_DIR:/repo-src:ro" "$IMAGE" tail -f /dev/null
docker exec -it "$CONTAINER" bash
```

---

## Pitfalls & Lessons Learned

| Issue | Cause | Fix |
|---|---|---|
| `useradd: UID 1000 is not unique` | Ubuntu 24.04 pre-creates user `ubuntu` with UID 1000 | Modify the existing `ubuntu` user using `groupmod` and `usermod` instead of running `useradd` |
| `Permission denied` on `/repo-src` | Host directory has 750 permissions and different UID | Pass host `$(id -u)` and `$(id -g)` as build args and align container user UID/GID |
| Docker socket permission denied | Host user not in docker group or socket mode 660 | `sudo usermod -aG docker $USER && sudo chmod 666 /var/run/docker.sock` |
| Accidental host pollution | Direct write to mounted host volume | Mount host volume strictly with `:ro` flag; copy/rsync to container disk |
| `localhost:<port>` unreachable | Container bridge network cannot reach host loopback services (e.g. `localhost:20128` router/model endpoint) | Launch container with `--network host` so host loopback services are directly accessible as `localhost` |
| Bulk environment replication | Manual piecemeal hunting for API keys/configs is slow and error-prone | Bulk copy entire config directory: `docker cp ~/.chiper/. container:~/.chiper/`, fix ownership `chown -R`, and purge stale lockfiles (`rm -f gateway.lock gateway.pid`) |
| Telegram Gateway 409 Conflict | Both host and container polling Telegram with the exact same bot token | Always swap `TELEGRAM_BOT_TOKEN` in the container's `.env` to a dedicated test bot token so host and container gateways don't drop each other |
