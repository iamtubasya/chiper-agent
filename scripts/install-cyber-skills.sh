#!/bin/bash
# ============================================================================
# Chiper Cyber Skills Installer Helper
# Dipanggil oleh setup-chiper.sh saat proses setup
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHIPER_HOME="${CHIPER_HOME:-$HOME/.chiper}"
TARGET_CYBER_DIR="$CHIPER_HOME/skills/chiper-cyber"
SOURCE_CYBER_DIR="$SCRIPT_DIR/skills/chiper-cyber"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

if [ ! -d "$SOURCE_CYBER_DIR" ]; then
    exit 0
fi

echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}          🛡️   CHIPER-CYBER SECURITY SUITE SETUP   🛡️${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "Pilih opsi instalasi skills keamanan siber untuk Chiper Agent:"
echo ""
echo -e "  ${BOLD}[1]${NC} ${GREEN}🚀 Full Cyber Security Suite${NC} (140 Domains)"
echo -e "      (Web, Network, Cloud, AI Red Team, Telecom, Hardware, Exploit Dev)"
echo ""
echo -e "  ${BOLD}[2]${NC} ${YELLOW}🎯 Bug Bounty Hunter Edition${NC} (28 Domains Terpilih)"
echo -e "      (SQLi, XSS, SSRF, XXE, Auth Bypass, IDOR, API, Race Condition, Recon)"
echo ""
echo -e "  ${BOLD}[3]${NC} ⏭️  Lewati / Jangan install skills cyber saat ini"
echo ""

# Baca input user
if [ "$INTERACTIVE" = false ] || [ ! -t 0 ]; then
    CYBER_CHOICE="1"
    echo -e "Non-interactive mode terdeteksi, default: ${BOLD}[1] Full Suite${NC}"
else
    read -p "Masukkan pilihan Anda [1/2/3] (Default: 1): " CYBER_CHOICE
    CYBER_CHOICE="${CYBER_CHOICE:-1}"
fi

case "$CYBER_CHOICE" in
    1)
        echo ""
        echo -e "${CYAN}→${NC} Menginstal Full Cyber Security Suite (140 domains)..."
        mkdir -p "$TARGET_CYBER_DIR"
        cp -rf "$SOURCE_CYBER_DIR/"* "$TARGET_CYBER_DIR/" 2>/dev/null
        # Pasang SOUL.md ke root CHIPER_HOME agar otomatis di-load oleh prompt_builder.py
        if [ -f "$SOURCE_CYBER_DIR/SOUL.md" ]; then
            cp -f "$SOURCE_CYBER_DIR/SOUL.md" "$CHIPER_HOME/SOUL.md"
        fi
        if [ -f "$SOURCE_CYBER_DIR/TOOLS.md" ]; then
            cp -f "$SOURCE_CYBER_DIR/TOOLS.md" "$CHIPER_HOME/TOOLS.md"
        fi
        echo -e "${GREEN}✓ Full Cyber Suite + SOUL.md & TOOLS.md berhasil dipasang di $CHIPER_HOME${NC}"
        ;;
    2)
        echo ""
        echo -e "${CYAN}→${NC} Menginstal Bug Bounty Hunter Edition (28 domains)..."
        rm -rf "$TARGET_CYBER_DIR"
        mkdir -p "$TARGET_CYBER_DIR"
        
        # Salin file meta utama, docs, dan validation tools
        for meta in README.md SKILL.md SOUL.md TOOLS.md HEARTBEAT.md AGENTS.md IDENTITY.md MEMORY.md TEMPLATE.md CHIPER_TOOLS_BASELINE_2026_07.md CHIPER_TOOLS_BASELINE_2026_08.md CHIPER_TOOLS_BASELINE_2026_09.md; do
            [ -f "$SOURCE_CYBER_DIR/$meta" ] && cp -f "$SOURCE_CYBER_DIR/$meta" "$TARGET_CYBER_DIR/"
        done
        for mdir in docs validation; do
            [ -d "$SOURCE_CYBER_DIR/$mdir" ] && cp -rf "$SOURCE_CYBER_DIR/$mdir" "$TARGET_CYBER_DIR/"
        done
        
        # Pasang SOUL.md & TOOLS.md ke root CHIPER_HOME agar aktif saat eksekusi Bug Bounty
        [ -f "$SOURCE_CYBER_DIR/SOUL.md" ] && cp -f "$SOURCE_CYBER_DIR/SOUL.md" "$CHIPER_HOME/SOUL.md"
        [ -f "$SOURCE_CYBER_DIR/TOOLS.md" ] && cp -f "$SOURCE_CYBER_DIR/TOOLS.md" "$CHIPER_HOME/TOOLS.md"
        
        # Daftar 28 skill bug bounty terpilih (termasuk chiper-tool-mastery untuk TOOLS.md)
        BB_SKILLS=(
            "chiper-security-bounty-hunter"
            "chiper-recon-osint"
            "chiper-osint"
            "chiper-dns-attacks"
            "chiper-web-sqli"
            "chiper-web-xss"
            "chiper-web-ssrf"
            "chiper-web-xxe"
            "chiper-web-auth-bypass"
            "chiper-web-access-control"
            "chiper-web-deserialization"
            "chiper-file-inclusion"
            "chiper-command-injection-advanced"
            "chiper-api-security"
            "chiper-cms-framework-attack"
            "chiper-concurrency-exploitation"
            "chiper-open-banking-attack"
            "chiper-secret-management-attack"
            "chiper-repo-scan"
            "chiper-patch-to-poc-pipeline"
            "chiper-ai-fuzzing"
            "chiper-payload-generation"
            "chiper-verification-loop"
            "chiper-pentest-reporting"
            "chiper-darkweb-intel"
            "chiper-blockchain-web3"
            "chiper-tool-mastery"
            "chiper-bootstrap"
        )
        
        installed_count=0
        for skill in "${BB_SKILLS[@]}"; do
            if [ -d "$SOURCE_CYBER_DIR/$skill" ]; then
                cp -rf "$SOURCE_CYBER_DIR/$skill" "$TARGET_CYBER_DIR/"
                installed_count=$((installed_count + 1))
            fi
        done
        echo -e "${GREEN}✓ Berhasil memasang $installed_count skills Bug Bounty + SOUL.md & TOOLS.md di $CHIPER_HOME${NC}"
        ;;
    3)
        echo ""
        rm -rf "$TARGET_CYBER_DIR"
        echo -e "${YELLOW}→${NC} Instalasi skills cyber dilewati. Anda bisa memasangnya nanti via skrip."
        ;;
    *)
        echo ""
        echo -e "${YELLOW}Pilihan tidak valid, instalasi skills cyber dilewati.${NC}"
        ;;
esac
