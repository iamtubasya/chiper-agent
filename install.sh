#!/bin/bash
# ============================================================================
# Chiper Agent Installer
# ============================================================================
# One-liner install: clone repo + run setup
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/iamtubasya/chiper-agent/main/install.sh | bash
# ============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

REPO_URL="https://github.com/iamtubasya/chiper-agent.git"
INSTALL_DIR="$HOME/chiper-agent"

echo ""
echo -e "${CYAN}⚕ Chiper Agent Installer${NC}"
echo ""

# ============================================================================
# Git check
# ============================================================================
if ! command -v git &> /dev/null; then
    echo -e "${RED}✗${NC} git not found. Install it first:"
    echo "    sudo apt install git    # Debian/Ubuntu"
    echo "    sudo dnf install git    # Fedora"
    exit 1
fi

# ============================================================================
# Clone or update repo
# ============================================================================
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${CYAN}→${NC} Existing install found at $INSTALL_DIR, pulling latest..."
    cd "$INSTALL_DIR"
    git pull --ff-only || {
        echo -e "${RED}✗${NC} git pull failed. Resolve conflicts manually or delete $INSTALL_DIR and retry."
        exit 1
    }
else
    echo -e "${CYAN}→${NC} Cloning chiper-agent to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ============================================================================
# Run setup
# ============================================================================
echo -e "${CYAN}→${NC} Running setup..."
chmod +x setup-chiper.sh
./setup-chiper.sh
