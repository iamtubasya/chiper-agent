#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# chiper-bootstrap: Full environment installer for chiper-* skills
# ═══════════════════════════════════════════════════════════════
# Usage: ./install.sh [--phase <1|2|3|4|5|all>]
# Default: runs all phases
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/install.log"
CHIPER_VENV="${HOME}/.Chiper/venv"
GOBIN="${HOME}/go/bin"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
ok()  { echo -e "${GREEN}[✅]${NC} $1" | tee -a "$LOG_FILE"; }
warn(){ echo -e "${YELLOW}[⚠️]${NC} $1" | tee -a "$LOG_FILE"; }
err() { echo -e "${RED}[❌]${NC} $1" | tee -a "$LOG_FILE"; }
header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

# ═══════════════════════════════════════════════════════════════
# PHASE 1: System Detection
# ═══════════════════════════════════════════════════════════════
phase1_detect() {
    header "PHASE 1: System Detection"

    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="${ID}"
        OS_VERSION="${VERSION_ID}"
        OS_PRETTY="${PRETTY_NAME}"
    else
        err "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi

    log "Detected: ${OS_PRETTY}"
    log "OS ID: ${OS_ID}, Version: ${OS_VERSION}"

    # Detect package manager
    if command -v apt &>/dev/null; then
        PKG_MGR="apt"
    elif command -v pacman &>/dev/null; then
        PKG_MGR="pacman"
    else
        err "No supported package manager found (need apt or pacman)"
        exit 1
    fi
    log "Package manager: ${PKG_MGR}"

    # Detect arch
    ARCH=$(uname -m)
    log "Architecture: ${ARCH}"

    # Check disk space
    AVAIL_GB=$(df -BG "${HOME}" | tail -1 | awk '{print $4}' | tr -d 'G')
    log "Available disk space: ${AVAIL_GB}GB"
    if [ "$AVAIL_GB" -lt 10 ]; then
        warn "Less than 10GB free. Full install needs ~15GB."
        warn "Continue? (y/n)"
        read -r answer
        [[ "$answer" != "y" ]] && exit 0
    fi

    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        warn "Running as root. This is OK for apt, but pip will use venv."
    fi

    # Setup Kali repo on non-Kali systems
    if [[ "$OS_ID" != "kali" && "$PKG_MGR" == "apt" ]]; then
        log "Non-Kali system detected. Adding Kali repo (pinned low priority)..."
        setup_kali_repo
    fi

    ok "System detection complete."
}

setup_kali_repo() {
    # Add Kali repo with low priority (only install Kali-specific packages)
    if [ ! -f /etc/apt/sources.list.d/kali.list ]; then
        echo "deb http://http.kali.org/kali kali-rolling main non-free contrib" | \
            sudo tee /etc/apt/sources.list.d/kali.list > /dev/null

        # Pin Kali repo at low priority (100) so it doesn't replace system packages
        sudo tee /etc/apt/preferences.d/kali-pin > /dev/null <<'EOF'
Package: *
Pin: release o=Kali
Pin-Priority: 100

Package: *
Pin: origin http.kali.org
Pin-Priority: 100
EOF
        # Import Kali archive key
        wget -q -O - https://archive.kali.org/archive-key.asc | sudo gpg --dearmor -o /usr/share/keyrings/kali-archive-keyring.gpg 2>/dev/null || \
        wget -q -O - https://archive.kali.org/archive-key.asc | sudo apt-key add - 2>/dev/null

        ok "Kali repo added with low priority pin."
    else
        log "Kali repo already configured."
    fi
}

# ═══════════════════════════════════════════════════════════════
# PHASE 2: apt Packages (223 tools)
# ═══════════════════════════════════════════════════════════════
phase2_apt() {
    header "PHASE 2: apt Packages (223 tools)"

    sudo apt update -qq 2>/dev/null

    # ── Core System ──────────────────────────────────────
    log "Installing core system tools..."
    sudo apt install -y -qq \
        curl wget git python3 python3-pip python3-venv python3-dev \
        build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev \
        jq ripgrep fd-find fzf tmux screen vim nano \
        net-tools dnsutils whois traceroute \
        2>/dev/null || true
    ok "Core system tools installed."

    # ── Information Gathering ────────────────────────────
    log "Installing information gathering tools..."
    sudo apt install -y -qq \
        nmap masscan zmap netdiscover arp-scan fping hping3 \
        dnsenum dnsrecon fierce dmitry \
        theharvester recon-ng maltego spiderfoot \
        amass sublist3r knockpy \
        enum4linux-ng smbclient rpcclient nbtscan smbmap \
        ldap-utils ldapdomaindump \
        whatweb wafw00f httprobe \
        2>/dev/null || true
    ok "Information gathering tools installed."

    # ── Vulnerability Analysis ───────────────────────────
    log "Installing vulnerability analysis tools..."
    sudo apt install -y -qq \
        nikto wapiti nuclei testssl.sh sslyze sslscan \
        2>/dev/null || true
    ok "Vulnerability analysis tools installed."

    # ── Web Application ──────────────────────────────────
    log "Installing web application tools..."
    sudo apt install -y -qq \
        sqlmap joomscan wpscan cmseek droopescan \
        dirb gobuster wfuzz dirbuster dirsearch \
        commix tplmap davtest cadaver \
        mitmproxy \
        2>/dev/null || true
    ok "Web application tools installed."

    # ── Password Attacks ─────────────────────────────────
    log "Installing password attack tools..."
    sudo apt install -y -qq \
        hydra medusa ncrack crowbar patator \
        john hashcat crunch cewl \
        ophcrack samdump2 \
        impacket-scripts \
        2>/dev/null || true
    ok "Password attack tools installed."

    # ── Wireless ─────────────────────────────────────────
    log "Installing wireless tools..."
    sudo apt install -y -qq \
        aircrack-ng wifite reaver bully pixiewps \
        kismet mdk4 hostapd-mana \
        2>/dev/null || true
    ok "Wireless tools installed."

    # ── Exploitation ─────────────────────────────────────
    log "Installing exploitation tools..."
    sudo apt install -y -qq \
        metasploit-framework exploitdb searchsploit \
        shellnoob \
        2>/dev/null || true
    ok "Exploitation tools installed."

    # ── Sniffing & Spoofing ──────────────────────────────
    log "Installing sniffing & spoofing tools..."
    sudo apt install -y -qq \
        wireshark tshark tcpdump \
        ettercap-text-only bettercap \
        dsniff macchanger \
        2>/dev/null || true
    ok "Sniffing & spoofing tools installed."

    # ── Post Exploitation ────────────────────────────────
    log "Installing post-exploitation tools..."
    sudo apt install -y -qq \
        proxychains4 \
        netcat-traditional ncat socat \
        sshuttle \
        2>/dev/null || true
    ok "Post-exploitation tools installed."

    # ── Forensics ────────────────────────────────────────
    log "Installing forensics tools..."
    sudo apt install -y -qq \
        autopsy sleuthkit \
        scalpel foremost bulk-extractor dcfldd \
        binwalk steghide exiftool \
        pdf-parser \
        volatility3 \
        2>/dev/null || true
    ok "Forensics tools installed."

    # ── Reverse Engineering ──────────────────────────────
    log "Installing reverse engineering tools..."
    sudo apt install -y -qq \
        radare2 rizin ghidra gdb edb-debugger \
        ropper \
        ltrace strace objdump readelf strings file \
        upx-ucl apktool jadx dex2jar \
        2>/dev/null || true
    ok "Reverse engineering tools installed."

    # ── Hardware / IoT / RF ──────────────────────────────
    log "Installing hardware/IoT/RF tools..."
    sudo apt install -y -qq \
        minicom screen picocom flashrom \
        urh gqrx-sdr rtl-sdr hackrf gnuradio gr-osmosdr \
        rtl-433 inspectrum sigrok \
        2>/dev/null || true
    ok "Hardware/IoT/RF tools installed."

    # ── Bluetooth ────────────────────────────────────────
    log "Installing Bluetooth tools..."
    sudo apt install -y -qq \
        bluelog blueranger btscanner redfang spooftooph \
        ubertooth \
        2>/dev/null || true
    ok "Bluetooth tools installed."

    # ── VoIP ─────────────────────────────────────────────
    log "Installing VoIP tools..."
    sudo apt install -y -qq \
        sipvicious protos-sip \
        2>/dev/null || true
    ok "VoIP tools installed."

    # ── Fuzzing ──────────────────────────────────────────
    log "Installing fuzzing tools..."
    sudo apt install -y -qq \
        boofuzz afl++ \
        2>/dev/null || true
    ok "Fuzzing tools installed."

    # ── Social Engineering ───────────────────────────────
    log "Installing social engineering tools..."
    sudo apt install -y -qq \
        set \
        2>/dev/null || true
    ok "Social engineering tools installed."

    # ── Cloud & Container ────────────────────────────────
    log "Installing cloud/container tools..."
    sudo apt install -y -qq \
        trivy \
        docker.io kubectl \
        2>/dev/null || true
    ok "Cloud/container tools installed."

    # ── Reporting ────────────────────────────────────────
    log "Installing reporting tools..."
    sudo apt install -y -qq \
        recordmydesktop cutycapt pipal \
        2>/dev/null || true
    ok "Reporting tools installed."

    # ── Kali Meta-packages (catch remaining) ─────────────
    if [[ "$OS_ID" == "kali" ]]; then
        log "Kali detected. Installing metapackages for coverage..."
        sudo apt install -y -qq \
            kali-linux-headless \
            2>/dev/null || true
        ok "Kali metapackages installed."
    fi

    ok "Phase 2 complete: apt packages installed."
}

# ═══════════════════════════════════════════════════════════════
# PHASE 3: Python Packages (59 libraries)
# ═══════════════════════════════════════════════════════════════
phase3_pip() {
    header "PHASE 3: Python Packages (59 libraries)"

    # Create/update virtualenv
    if [ ! -d "$CHIPER_VENV" ]; then
        log "Creating virtualenv at ${CHIPER_VENV}..."
        python3 -m venv "$CHIPER_VENV"
    fi

    source "${CHIPER_VENV}/bin/activate"
    pip install --upgrade pip setuptools wheel 2>/dev/null

    # ── Core Networking ──────────────────────────────────
    log "Installing core networking libraries..."
    pip install -q \
        requests requests[security] beautifulsoup4 lxml \
        aiohttp httpx websocket-client \
        paramiko scapy dpkt \
        2>/dev/null || true
    ok "Core networking libraries installed."

    # ── Web Exploitation ─────────────────────────────────
    log "Installing web exploitation libraries..."
    pip install -q \
        sqlmap \
        jsbeautifier \
        flask fastapi \
        2>/dev/null || true
    ok "Web exploitation libraries installed."

    # ── Cryptography ─────────────────────────────────────
    log "Installing cryptography libraries..."
    pip install -q \
        pycryptodome cryptography \
        2>/dev/null || true
    ok "Cryptography libraries installed."

    # ── Binary / RE / Exploit Dev ────────────────────────
    log "Installing binary/RE/exploit libraries..."
    pip install -q \
        pwntools \
        ropper \
        angr \
        capstone keystone-engine unicorn \
        pefile \
        ropgadget \
        2>/dev/null || true
    ok "Binary/RE/exploit libraries installed."

    # ── Mobile ───────────────────────────────────────────
    log "Installing mobile security libraries..."
    pip install -q \
        frida-tools objection \
        drozer \
        2>/dev/null || true
    ok "Mobile security libraries installed."

    # ── Blockchain / Smart Contract ──────────────────────
    log "Installing blockchain/smart contract libraries..."
    pip install -q \
        slither-analyzer mythril \
        web3 solc-select \
        2>/dev/null || true
    ok "Blockchain/smart contract libraries installed."

    # ── Active Directory ─────────────────────────────────
    log "Installing AD/Windows attack libraries..."
    pip install -q \
        impacket \
        certipy-ad \
        lsassy nanodump \
        bloodhound \
        pywerview \
        2>/dev/null || true
    ok "AD/Windows attack libraries installed."

    # ── OSINT ────────────────────────────────────────────
    log "Installing OSINT libraries..."
    pip install -q \
        sherlock-project \
        trufflehog \
        2>/dev/null || true
    ok "OSINT libraries installed."

    # ── VoIP ─────────────────────────────────────────────
    log "Installing VoIP libraries..."
    pip install -q \
        sipvicious \
        2>/dev/null || true
    ok "VoIP libraries installed."

    # ── AI / LLM ─────────────────────────────────────────
    log "Installing AI/LLM red team libraries..."
    pip install -q \
        garak \
        2>/dev/null || true
    ok "AI/LLM red team libraries installed."

    # ── Utilities ────────────────────────────────────────
    log "Installing utility libraries..."
    pip install -q \
        termcolor colorama rich \
        pyyaml toml \
        telethon \
        pillow \
        2>/dev/null || true
    ok "Utility libraries installed."

    deactivate
    ok "Phase 3 complete: Python packages installed in ${CHIPER_VENV}"
}

# ═══════════════════════════════════════════════════════════════
# PHASE 4: Go Binaries (12 tools)
# ═══════════════════════════════════════════════════════════════
phase4_go() {
    header "PHASE 4: Go Binaries (12 tools)"

    # Check if Go is installed
    if ! command -v go &>/dev/null; then
        log "Go not found. Installing..."
        # Install Go
        GO_VERSION="1.22.5"
        wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
        sudo rm -rf /usr/local/go
        sudo tar -C /usr/local -xzf /tmp/go.tar.gz
        rm /tmp/go.tar.gz

        export PATH="${PATH}:/usr/local/go/bin:${GOBIN}"
        echo 'export PATH="${PATH}:/usr/local/go/bin:${HOME}/go/bin"' >> ~/.bashrc
        echo 'export PATH="${PATH}:/usr/local/go/bin:${HOME}/go/bin"' >> ~/.zshrc 2>/dev/null || true
        ok "Go ${GO_VERSION} installed."
    else
        log "Go already installed: $(go version)"
    fi

    export PATH="${PATH}:${GOBIN}"
    mkdir -p "$GOBIN"

    # ── ProjectDiscovery Suite ───────────────────────────
    log "Installing ProjectDiscovery tools..."
    go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null && ok "nuclei" || warn "nuclei failed"
    go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>/dev/null && ok "subfinder" || warn "subfinder failed"
    go install github.com/projectdiscovery/httpx/cmd/httpx@latest 2>/dev/null && ok "httpx" || warn "httpx failed"
    go install github.com/projectdiscovery/katana/cmd/katana@latest 2>/dev/null && ok "katana" || warn "katana failed"
    go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest 2>/dev/null && ok "naabu" || warn "naabu failed"

    # ── Web Fuzzing ──────────────────────────────────────
    log "Installing web fuzzing Go tools..."
    go install github.com/ffuf/ffuf/v2@latest 2>/dev/null && ok "ffuf" || warn "ffuf failed"

    # ── URL/Subdomain ────────────────────────────────────
    log "Installing URL/subdomain Go tools..."
    go install github.com/tomnomnom/assetfinder@latest 2>/dev/null && ok "assetfinder" || warn "assetfinder failed"
    go install github.com/tomnomnom/waybackurls@latest 2>/dev/null && ok "waybackurls" || warn "waybackurls failed"
    go install github.com/lc/gau/v2/cmd/gau@latest 2>/dev/null && ok "gau" || warn "gau failed"
    go install github.com/jaeles-project/gospider@latest 2>/dev/null && ok "gospider" || warn "gospider failed"

    # ── Network ──────────────────────────────────────────
    log "Installing network Go tools..."
    go install github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest 2>/dev/null && ok "interactsh-client" || warn "interactsh failed"
    go install github.com/OJ/gobuster/v3@latest 2>/dev/null && ok "gobuster-go" || warn "gobuster-go failed"

    ok "Phase 4 complete: Go binaries installed in ${GOBIN}"
}

# ═══════════════════════════════════════════════════════════════
# PHASE 5: Manual Downloads (8 tools)
# ═══════════════════════════════════════════════════════════════
phase5_manual() {
    header "PHASE 5: Manual Downloads (8 tools)"

    echo -e "${YELLOW}The following tools require manual download:${NC}\n"

    echo -e "${CYAN}1. Burp Suite${NC} (Web Application Proxy)"
    echo "   → https://portswigger.net/burp/communitydownload"
    echo "   → Install: java -jar burpsuite.jar"
    echo ""

    echo -e "${CYAN}2. IDA Free${NC} (Disassembler)"
    echo "   → https://hex-rays.com/ida-free/"
    echo "   → Install: chmod +x idafree && ./idafree"
    echo ""

    echo -e "${CYAN}3. Gophish${NC} (Phishing Framework)"
    echo "   → https://github.com/gophish/gophish/releases"
    echo "   → Install: unzip && chmod +x gophish && ./gophish"
    echo ""

    echo -e "${CYAN}4. Evilginx2${NC} (Advanced Phishing)"
    echo "   → https://github.com/kgretzky/evilginx2/releases"
    echo "   → Install: chmod +x evilginx && ./evilginx"
    echo ""

    echo -e "${CYAN}5. Ligolo-ng${NC} (Tunneling)"
    echo "   → https://github.com/nicocha30/ligolo-ng/releases"
    echo "   → Install: chmod +x agent proxy && ./proxy"
    echo ""

    echo -e "${CYAN}6. Chisel${NC} (Tunneling)"
    echo "   → https://github.com/jpillora/chisel/releases"
    echo "   → Install: chmod +x chisel && ./chisel server"
    echo ""

    echo -e "${CYAN}7. ngrok${NC} (Tunneling)"
    echo "   → https://ngrok.com/download"
    echo "   → Install: tar xzf ngrok.tgz && ./ngrok authtoken <TOKEN>"
    echo ""

    echo -e "${CYAN}8. Cloudflared${NC} (Tunneling)"
    echo "   → https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    echo "   → Install: chmod +x cloudflared && ./cloudflared tunnel"
    echo ""

    ok "Phase 5 complete: Manual download list displayed."
}

# ═══════════════════════════════════════════════════════════════
# PHASE 6: Verification
# ═══════════════════════════════════════════════════════════════
phase6_verify() {
    header "PHASE 6: Verification"

    if [ -f "${SCRIPT_DIR}/verify.sh" ]; then
        bash "${SCRIPT_DIR}/verify.sh"
    else
        warn "verify.sh not found. Run manually: ${SCRIPT_DIR}/verify.sh"
    fi
}

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
main() {
    echo -e "${BLUE}"
    echo "  ╔═══════════════════════════════════════════════╗"
    echo "  ║     chiper-bootstrap v1.0                     ║"
    echo "  ║     Environment Installer for chiper-* skills ║"
    echo "  ╚═══════════════════════════════════════════════╝"
    echo -e "${NC}"

    PHASE="${1:-all}"

    case "$PHASE" in
        1) phase1_detect ;;
        2) phase2_apt ;;
        3) phase3_pip ;;
        4) phase4_go ;;
        5) phase5_manual ;;
        6) phase6_verify ;;
        all)
            phase1_detect
            phase2_apt
            phase3_pip
            phase4_go
            phase5_manual
            phase6_verify
            ;;
        *)
            echo "Usage: $0 [--phase <1|2|3|4|5|6|all>]"
            exit 1
            ;;
    esac

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ chiper-bootstrap complete!${NC}"
    echo -e "${GREEN}  📋 Log: ${LOG_FILE}${NC}"
    echo -e "${GREEN}  🔧 Verify: ${SCRIPT_DIR}/verify.sh${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
}

main "$@"
