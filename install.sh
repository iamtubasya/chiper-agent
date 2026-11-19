#!/usr/bin/env bash
# ============================================================================
# Chiper Agent Installer — compatibility shim
# ============================================================================
# This file used to be a *second, divergent* installer (56 lines: plain
# `git clone` + `./setup-chiper.sh`). It created no venv, installed no
# dependency extras, synced no skills, skipped the PATH symlink and did no
# post-install verification — so `curl .../main/install.sh | bash` produced a
# materially different (and often broken) install than the documented
# `curl .../main/scripts/install.sh | bash`.
#
# There is now exactly one implementation: scripts/install.sh. This shim keeps
# the old URL working and forwards every argument verbatim.
#
# Usage (unchanged):
#   curl -fsSL https://raw.githubusercontent.com/iamtubasya/chiper-agent/main/install.sh | bash
# ============================================================================

set -euo pipefail

REPO_RAW="${CHIPER_REPO_RAW:-https://raw.githubusercontent.com/iamtubasya/chiper-agent}"
BRANCH="${CHIPER_BRANCH:-main}"

# Local checkout case (`bash install.sh` from the repo root, or setup-chiper.sh
# invoking it): delegate to the real installer next door.
_self="${BASH_SOURCE[0]:-}"
if [ -n "$_self" ] && [ -f "$_self" ]; then
    _dir="$(cd "$(dirname "$_self")" && pwd)"
    if [ -f "$_dir/scripts/install.sh" ] && [ -f "$_dir/pyproject.toml" ]; then
        exec bash "$_dir/scripts/install.sh" "$@"
    fi
fi

# Piped case (`curl ... | bash`). $BASH_SOURCE is not usable and no local
# checkout exists, so fetch the real installer from the same repo + branch.
if ! command -v curl >/dev/null 2>&1; then
    echo "✗ curl is required to bootstrap the installer." >&2
    exit 1
fi

_tmp="$(mktemp)"
trap 'rm -f "$_tmp"' EXIT

echo "→ Fetching the Chiper installer (scripts/install.sh, branch: $BRANCH)..."
if ! curl -fsSL "$REPO_RAW/$BRANCH/scripts/install.sh" -o "$_tmp"; then
    echo "✗ Could not download scripts/install.sh from $REPO_RAW/$BRANCH" >&2
    echo "  Fall back to a git clone:" >&2
    echo "    git clone https://github.com/iamtubasya/chiper-agent.git" >&2
    echo "    cd chiper-agent && bash scripts/install.sh" >&2
    exit 1
fi

exec bash "$_tmp" "$@"
