#!/usr/bin/env bash
# ============================================================================
# Chiper Agent — Core Bug Bounty Tools Installer
# Installs essential offensive security tools:
#   - apt: curl, nmap, sqlmap, hydra, whatweb, wafw00f, unzip, tar
#   - pre-compiled Go binaries: subfinder, httpx, nuclei, ffuf, gobuster
# Works on Debian/Ubuntu (amd64 & arm64)
# ============================================================================

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}       🎯  CHIPER CORE BUG BOUNTY TOOLS INSTALLER  🎯${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"

# 1. Determine architecture
ARCH=$(uname -m)
case "$ARCH" in
    x86_64)  GOARCH="amd64" ;;
    aarch64) GOARCH="arm64" ;;
    armv7l)  GOARCH="arm" ;;
    *)       GOARCH="amd64" ;;
esac

SUDO_CMD=""
if [ "$EUID" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO_CMD="sudo"
    else
        echo -e "${RED}Error: script must be run as root or with sudo installed.${NC}"
        exit 1
    fi
fi

# 2. Install apt packages
echo -e "${CYAN}→${NC} Memeriksa paket APT inti (nmap, sqlmap, hydra, whatweb, wafw00f)..."
APT_PKGS=()
for pkg in curl nmap sqlmap hydra whatweb wafw00f unzip tar; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        APT_PKGS+=("$pkg")
    fi
done

if [ ${#APT_PKGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Menginstal paket APT:${NC} ${APT_PKGS[*]} ..."
    $SUDO_CMD apt-get update -qq >/dev/null 2>&1 || true
    $SUDO_CMD DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${APT_PKGS[@]}" >/dev/null 2>&1
    echo -e "${GREEN}✓ Paket APT berhasil dipasang.${NC}"
else
    echo -e "${GREEN}✓ Semua paket APT inti sudah terpasang.${NC}"
fi

# 3. Helper to resolve latest release tag without GitHub API rate limits
get_github_latest_tag() {
    local repo="$1"
    curl -fsSIL "https://github.com/${repo}/releases/latest" 2>/dev/null | grep -i "^location:" | head -1 | sed -E 's|.*/tag/||' | tr -d '\r\n '
}

TMP_DIR=$(mktemp -d /tmp/chiper-bb-tools-XXXXXX)
trap 'rm -rf "$TMP_DIR"' EXIT
cd "$TMP_DIR"

INSTALL_DIR="/usr/local/bin"
[ -w "$INSTALL_DIR" ] || SUDO_BIN="$SUDO_CMD"
SUDO_BIN="${SUDO_BIN:-}"

# 4. Install subfinder
if ! command -v subfinder >/dev/null 2>&1; then
    echo -e "${CYAN}→${NC} Mengunduh subfinder..."
    TAG=$(get_github_latest_tag "projectdiscovery/subfinder")
    TAG="${TAG:-v2.17.0}"
    VER="${TAG#v}"
    URL="https://github.com/projectdiscovery/subfinder/releases/download/${TAG}/subfinder_${VER}_linux_${GOARCH}.zip"
    if curl -fsSL -o subfinder.zip "$URL" 2>/dev/null; then
        unzip -qo subfinder.zip subfinder
        $SUDO_BIN install -m 755 subfinder "$INSTALL_DIR/"
        echo -e "${GREEN}✓ subfinder terpasang di $INSTALL_DIR/subfinder${NC}"
    else
        echo -e "${YELLOW}⚠️ Gagal mengunduh subfinder dari GitHub release.${NC}"
    fi
else
    echo -e "${GREEN}✓ subfinder sudah terpasang.${NC}"
fi

# 5. Install httpx
HTTPX_CMD=$(command -v httpx 2>/dev/null || true)
if [ -z "$HTTPX_CMD" ] || [[ "$HTTPX_CMD" == *"/.venv/bin/httpx"* ]] || [[ "$HTTPX_CMD" == *"/venv/bin/httpx"* ]] || ! "$HTTPX_CMD" -version 2>&1 | grep -qi "projectdiscovery"; then
    if [ ! -f "$INSTALL_DIR/httpx" ]; then
        echo -e "${CYAN}→${NC} Mengunduh ProjectDiscovery httpx..."
        TAG=$(get_github_latest_tag "projectdiscovery/httpx")
        TAG="${TAG:-v1.12.0}"
        VER="${TAG#v}"
        URL="https://github.com/projectdiscovery/httpx/releases/download/${TAG}/httpx_${VER}_linux_${GOARCH}.zip"
        if curl -fsSL -o httpx.zip "$URL" 2>/dev/null; then
            unzip -qo httpx.zip httpx
            $SUDO_BIN install -m 755 httpx "$INSTALL_DIR/"
            echo -e "${GREEN}✓ httpx terpasang di $INSTALL_DIR/httpx${NC}"
        fi
    else
        echo -e "${GREEN}✓ httpx sudah terpasang di $INSTALL_DIR/httpx.${NC}"
    fi
else
    echo -e "${GREEN}✓ httpx sudah terpasang.${NC}"
fi

# 6. Install nuclei
if ! command -v nuclei >/dev/null 2>&1; then
    echo -e "${CYAN}→${NC} Mengunduh nuclei..."
    TAG=$(get_github_latest_tag "projectdiscovery/nuclei")
    TAG="${TAG:-v3.11.1}"
    VER="${TAG#v}"
    URL="https://github.com/projectdiscovery/nuclei/releases/download/${TAG}/nuclei_${VER}_linux_${GOARCH}.zip"
    if curl -fsSL -o nuclei.zip "$URL" 2>/dev/null; then
        unzip -qo nuclei.zip nuclei
        $SUDO_BIN install -m 755 nuclei "$INSTALL_DIR/"
        echo -e "${GREEN}✓ nuclei terpasang di $INSTALL_DIR/nuclei${NC}"
    fi
else
    echo -e "${GREEN}✓ nuclei sudah terpasang.${NC}"
fi

# 7. Install ffuf
if ! command -v ffuf >/dev/null 2>&1; then
    echo -e "${CYAN}→${NC} Mengunduh ffuf..."
    TAG=$(get_github_latest_tag "ffuf/ffuf")
    TAG="${TAG:-v2.3.0}"
    VER="${TAG#v}"
    URL="https://github.com/ffuf/ffuf/releases/download/${TAG}/ffuf_${VER}_linux_${GOARCH}.tar.gz"
    if curl -fsSL -o ffuf.tar.gz "$URL" 2>/dev/null; then
        tar -xzf ffuf.tar.gz ffuf
        $SUDO_BIN install -m 755 ffuf "$INSTALL_DIR/"
        echo -e "${GREEN}✓ ffuf terpasang di $INSTALL_DIR/ffuf${NC}"
    fi
else
    echo -e "${GREEN}✓ ffuf sudah terpasang.${NC}"
fi

# 8. Install gobuster
if ! command -v gobuster >/dev/null 2>&1; then
    echo -e "${CYAN}→${NC} Mengunduh gobuster..."
    TAG=$(get_github_latest_tag "OJ/gobuster")
    TAG="${TAG:-v3.8.2}"
    [ "$GOARCH" = "amd64" ] && GB_ARCH="x86_64" || GB_ARCH="arm64"
    URL="https://github.com/OJ/gobuster/releases/download/${TAG}/gobuster_Linux_${GB_ARCH}.tar.gz"
    if curl -fsSL -o gb.tar.gz "$URL" 2>/dev/null; then
        tar -xzf gb.tar.gz gobuster
        $SUDO_BIN install -m 755 gobuster "$INSTALL_DIR/"
        echo -e "${GREEN}✓ gobuster terpasang di $INSTALL_DIR/gobuster${NC}"
    fi
else
    echo -e "${GREEN}✓ gobuster sudah terpasang.${NC}"
fi

echo ""
echo -e "${BOLD}${GREEN}===================================================================${NC}"
echo -e "${BOLD}${GREEN}  ✅ SEMUA TOOLS INTI BUG BOUNTY SIAP DIGUNAKAN DI TERMINAL!      ${NC}"
echo -e "${BOLD}${GREEN}===================================================================${NC}"
echo "  • nmap       : $(command -v nmap)"
echo "  • sqlmap     : $(command -v sqlmap)"
echo "  • subfinder  : $(command -v subfinder)"
echo "  • httpx      : $(command -v httpx)"
echo "  • ffuf       : $(command -v ffuf)"
echo "  • nuclei     : $(command -v nuclei)"
echo "  • gobuster   : $(command -v gobuster)"
echo "  • hydra      : $(command -v hydra)"
echo "  • whatweb    : $(command -v whatweb)"
echo "  • wafw00f    : $(command -v wafw00f)"
echo ""
