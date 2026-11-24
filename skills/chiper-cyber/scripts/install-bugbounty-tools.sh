#!/usr/bin/env bash
# Lightweight bug-bounty toolchain install (~250MB) for chiper-bootstrap.
# Full install needs ~8-15GB; this script only brings up the fast essentials.
set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

APT_TOOLS=(nmap ffuf gobuster httpie jq git)
GO_TOOLS=(github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
          github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
          github.com/projectdiscovery/katana/cmd/katana@latest)
PIP_TOOLS=(sqlmap)

run() {
  echo "+ $*"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    "$@"
  fi
}

echo "== apt packages (${#APT_TOOLS[@]}) =="
run sudo apt-get update -qq
run sudo apt-get install -y -qq "${APT_TOOLS[@]}"

if command -v go >/dev/null 2>&1; then
  echo "== go tools (${#GO_TOOLS[@]}) =="
  for tool in "${GO_TOOLS[@]}"; do
    run go install "$tool"
  done
else
  echo "== go not found, skipping go tools =="
fi

echo "== python tools (${#PIP_TOOLS[@]}) =="
for tool in "${PIP_TOOLS[@]}"; do
  run python3 -m pip install --quiet "$tool"
done

echo "done. verify with: command -v nmap ffuf subfinder naabu katana sqlmap"
