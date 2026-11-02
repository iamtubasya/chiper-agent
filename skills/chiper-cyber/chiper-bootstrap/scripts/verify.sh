#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# chiper-bootstrap: Verify all tools are installed
# ═══════════════════════════════════════════════════════════════

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CHIPER_VENV="${HOME}/.Chiper/venv"
GOBIN="${HOME}/go/bin"

found=0
missing=0
total=0

check() {
    local name="$1"
    local cmd="$2"
    total=$((total + 1))
    if eval "$cmd" &>/dev/null; then
        found=$((found + 1))
    else
        echo -e "${RED}  ❌ $name${NC}"
        missing=$((missing + 1))
    fi
}

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  chiper-bootstrap: Tool Verification${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""

# ── apt / system tools ──────────────────────────────────
echo -e "${YELLOW}[Phase 2: apt packages]${NC}"
check "nmap" "command -v nmap"
check "masscan" "command -v masscan"
check "nikto" "command -v nikto"
check "sqlmap" "command -v sqlmap"
check "hydra" "command -v hydra"
check "john" "command -v john"
check "hashcat" "command -v hashcat"
check "gobuster" "command -v gobuster"
check "wfuzz" "command -v wfuzz"
check "dirb" "command -v dirb"
check "wpscan" "command -v wpscan"
check "metasploit" "command -v msfconsole"
check "searchsploit" "command -v searchsploit"
check "wireshark" "command -v wireshark || command -v tshark"
check "tcpdump" "command -v tcpdump"
check "bettercap" "command -v bettercap"
check "mitmproxy" "command -v mitmproxy"
check "aircrack-ng" "command -v aircrack-ng"
check "wifite" "command -v wifite"
check "responder" "command -v responder"
check "radare2" "command -v radare2"
check "gdb" "command -v gdb"
check "ghidra" "command -v ghidra || ls /usr/share/ghidra 2>/dev/null"
check "binwalk" "command -v binwalk"
check "steghide" "command -v steghide"
check "exiftool" "command -v exiftool"
check "enum4linux" "command -v enum4linux || command -v enum4linux-ng"
check "smbclient" "command -v smbclient"
check "rpcclient" "command -v rpcclient"
check "ldapsearch" "command -v ldapsearch"
check "theharvester" "command -v theHarvester || command -v theharvester"
check "recon-ng" "command -v recon-ng"
check "amass" "command -v amass"
check "sublist3r" "command -v sublist3r || python3 -c 'import sublist3r' 2>/dev/null"
check "dig" "command -v dig"
check "whois" "command -v whois"
check "whatweb" "command -v whatweb"
check "wafw00f" "command -v wafw00f"
check "crunch" "command -v crunch"
check "cewl" "command -v cewl"
check "medusa" "command -v medusa"
check "ncrack" "command -v ncrack"
check "ettercap" "command -v ettercap"
check "dsniff" "command -v dsniff"
check "macchanger" "command -v macchanger"
check "proxychains" "command -v proxychains4 || command -v proxychains"
check "netcat" "command -v nc || command -v ncat"
check "socat" "command -v socat"
check "autopsy" "command -v autopsy"
check "sleuthkit" "command -v fls"
check "scalpel" "command -v scalpel"
check "foremost" "command -v foremost"
check "bulk-extractor" "command -v bulk_extractor"
check "strings" "command -v strings"
check "objdump" "command -v objdump"
check "readelf" "command -v readelf"
check "file" "command -v file"
check "upx" "command -v upx"
check "apktool" "command -v apktool"
check "jadx" "command -v jadx"
check "ltrace" "command -v ltrace"
check "strace" "command -v strace"
check "hackrf" "command -v hackrf_info"
check "rtl_sdr" "command -v rtl_sdr"
check "gnuradio" "command -v gnuradio-companion || command -v gnuradio-config-info"
check "bluelog" "command -v bluelog"
check "sipvicious" "command -v svmap || command -v svwar"
check "boofuzz" "command -v boofuzz || python3 -c 'import boofuzz' 2>/dev/null"
check "set" "command -v setoolkit"
check "trivy" "command -v trivy"
check "docker" "command -v docker"
check "kubectl" "command -v kubectl"
check "curl" "command -v curl"
check "wget" "command -v wget"
check "git" "command -v git"
check "python3" "command -v python3"
check "jq" "command -v jq"
check "tmux" "command -v tmux"

echo ""

# ── pip packages ────────────────────────────────────────
echo -e "${YELLOW}[Phase 3: pip packages]${NC}"
if [ -d "$CHIPER_VENV" ]; then
    PIP="${CHIPER_VENV}/bin/pip"
    PY="${CHIPER_VENV}/bin/python3"
else
    PIP="pip3"
    PY="python3"
fi

check "requests" "$PY -c 'import requests'"
check "beautifulsoup4" "$PY -c 'import bs4'"
check "lxml" "$PY -c 'import lxml'"
check "aiohttp" "$PY -c 'import aiohttp'"
check "httpx" "$PY -c 'import httpx'"
check "paramiko" "$PY -c 'import paramiko'"
check "scapy" "$PY -c 'import scapy'"
check "pycryptodome" "$PY -c 'import Crypto'"
check "cryptography" "$PY -c 'import cryptography'"
check "pwntools" "$PY -c 'import pwn'"
check "ropper" "$PY -c 'import ropper'"
check "angr" "$PY -c 'import angr'"
check "capstone" "$PY -c 'import capstone'"
check "keystone" "$PY -c 'import keystone'"
check "unicorn" "$PY -c 'import unicorn'"
check "pefile" "$PY -c 'import pefile'"
check "frida-tools" "command -v frida || $PY -c 'import frida'"
check "objection" "command -v objection"
check "slither" "command -v slither"
check "mythril" "command -v mythril"
check "web3" "$PY -c 'import web3'"
check "impacket" "$PY -c 'import impacket'"
check "certipy" "command -v certipy || $PY -c 'import certipy'"
check "bloodhound" "$PY -c 'import bloodhound'"
check "sherlock" "command -v sherlock || $PY -c 'import sherlock'"
check "trufflehog" "command -v trufflehog"
check "termcolor" "$PY -c 'import termcolor'"
check "rich" "$PY -c 'import rich'"
check "telethon" "$PY -c 'import telethon'"
check "pillow" "$PY -c 'import PIL'"

echo ""

# ── Go binaries ─────────────────────────────────────────
echo -e "${YELLOW}[Phase 4: Go binaries]${NC}"
check "nuclei" "command -v nuclei"
check "subfinder" "command -v subfinder"
check "httpx" "command -v httpx"
check "katana" "command -v katana"
check "naabu" "command -v naabu"
check "ffuf" "command -v ffuf"
check "assetfinder" "command -v assetfinder"
check "waybackurls" "command -v waybackurls"
check "gau" "command -v gau"
check "gospider" "command -v gospider"
check "interactsh" "command -v interactsh-client"
check "gobuster-go" "command -v gobuster"

echo ""

# ── Summary ─────────────────────────────────────────────
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
pct=$((found * 100 / total))
if [ "$pct" -ge 90 ]; then
    COLOR=$GREEN
elif [ "$pct" -ge 70 ]; then
    COLOR=$YELLOW
else
    COLOR=$RED
fi

echo -e "  ${COLOR}📊 Results: ${found}/${total} tools installed (${pct}%)${NC}"
echo -e "  ${GREEN}✅ Found:   ${found}${NC}"
echo -e "  ${RED}❌ Missing: ${missing}${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"

if [ "$missing" -gt 0 ]; then
    echo -e "\n${YELLOW}💡 Run the installer to fix missing tools:${NC}"
    echo "   bash ~/.Chiper/skills/chiper-bootstrap/scripts/install.sh"
fi
