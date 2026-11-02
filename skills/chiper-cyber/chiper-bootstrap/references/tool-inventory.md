# chiper-bootstrap: Complete Tool Inventory
# 302 tools across 145 chiper-* skills

## Summary

| Category | Count | Install Method |
|----------|-------|----------------|
| apt packages | 223 | `sudo apt install <pkg>` |
| pip packages | 59 | `pip install <pkg>` |
| go binaries | 12 | `go install <pkg>@latest` |
| manual downloads | 8 | Download from website |
| **TOTAL** | **302** | |

## apt Packages (223)

### Core System
curl, wget, git, python3, python3-pip, python3-venv, python3-dev,
build-essential, libssl-dev, libffi-dev, libxml2-dev, libxslt1-dev,
jq, ripgrep, fd-find, fzf, tmux, screen, vim, nano,
net-tools, dnsutils, whois, traceroute

### Information Gathering
nmap, masscan, zmap, netdiscover, arp-scan, fping, hping3,
dnsenum, dnsrecon, fierce, dmitry,
theharvester, recon-ng, maltego, spiderfoot,
amass, sublist3r, knockpy,
enum4linux-ng, smbclient, rpcclient, nbtscan, smbmap,
ldap-utils, ldapdomaindump,
whatweb, wafw00f, httprobe

### Vulnerability Analysis
nikto, wapiti, nuclei, testssl.sh, sslyze, sslscan

### Web Application
sqlmap, joomscan, wpscan, cmseek, droopescan,
dirb, gobuster, wfuzz, dirbuster, dirsearch,
commix, tplmap, davtest, cadaver,
mitmproxy

### Password Attacks
hydra, medusa, ncrack, crowbar, patator,
john, hashcat, crunch, cewl,
ophcrack, samdump2,
impacket-scripts

### Wireless
aircrack-ng, wifite, reaver, bully, pixiewps,
kismet, mdk4, hostapd-mana

### Exploitation
metasploit-framework, exploitdb, searchsploit, shellnoob

### Sniffing & Spoofing
wireshark, tshark, tcpdump,
ettercap-text-only, bettercap,
dsniff, macchanger

### Post Exploitation
proxychains4, netcat-traditional, ncat, socat, sshuttle

### Forensics
autopsy, sleuthkit, scalpel, foremost, bulk-extractor, dcfldd,
binwalk, steghide, exiftool, pdf-parser, volatility3

### Reverse Engineering
radare2, rizin, ghidra, gdb, edb-debugger, ropper,
ltrace, strace, objdump, readelf, strings, file,
upx-ucl, apktool, jadx, dex2jar

### Hardware / IoT / RF
minicom, screen, picocom, flashrom,
urh, gqrx-sdr, rtl-sdr, hackrf, gnuradio, gr-osmosdr,
rtl-433, inspectrum, sigrok

### Bluetooth
bluelog, blueranger, btscanner, redfang, spooftooph, ubertooth

### VoIP
sipvicious, protos-sip

### Fuzzing
boofuzz, afl++

### Social Engineering
set

### Cloud & Container
trivy, docker.io, kubectl

### Reporting
recordmydesktop, cutycapt, pipal

---

## pip Packages (59)

### Core Networking
requests, requests[security], beautifulsoup4, lxml,
aiohttp, httpx, websocket-client,
paramiko, scapy, dpkt

### Web Exploitation
sqlmap, jsbeautifier, flask, fastapi

### Cryptography
pycryptodome, cryptography

### Binary / RE / Exploit Dev
pwntools, ropper, angr,
capstone, keystone-engine, unicorn,
pefile, ropgadget

### Mobile
frida-tools, objection, drozer

### Blockchain / Smart Contract
slither-analyzer, mythril, web3, solc-select

### Active Directory
impacket, certipy-ad, lsassy, nanodump, bloodhound, pywerview

### OSINT
sherlock-project, trufflehog

### VoIP
sipvicious

### AI / LLM Red Team
garak

### Utilities
termcolor, colorama, rich,
pyyaml, toml,
telethon, pillow

---

## Go Binaries (12)

### ProjectDiscovery Suite
nuclei, subfinder, httpx, katana, naabu

### Web Fuzzing
ffuf

### URL/Subdomain
assetfinder, waybackurls, gau, gospider

### Network
interactsh-client, gobuster-go

---

## Manual Downloads (8)

| Tool | URL | Purpose |
|------|-----|---------|
| Burp Suite | portswigger.net/burp/communitydownload | Web proxy/scanner |
| IDA Free | hex-rays.com/ida-free/ | Disassembler |
| Gophish | github.com/gophish/gophish/releases | Phishing framework |
| Evilginx2 | github.com/kgretzky/evilginx2/releases | Advanced phishing |
| Ligolo-ng | github.com/nicocha30/ligolo-ng/releases | Tunneling |
| Chisel | github.com/jpillora/chisel/releases | Tunneling |
| ngrok | ngrok.com/download | Tunneling |
| Cloudflared | developers.cloudflare.com | Tunneling
