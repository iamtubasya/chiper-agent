# Chiper-Cyber

**144 security skill domains** untuk Chiper Agent — 302 tools, cross-platform.

## Install

```bash
cp -r chiper-cyber ~/.Chiper/skills/
bash ~/.chiper/skills/chiper-cyber/chiper-bootstrap/scripts/install.sh
```

## Update

```bash
cd ~/.chiper/skills/chiper-cyber && git pull
```

## Skills (144 total)

### Web Exploitation
- chiper-web-sqli, chiper-web-xss, chiper-web-ssrf, chiper-web-xxe
- chiper-web-auth-bypass, chiper-web-access-control, chiper-web-deserialization
- chiper-file-inclusion, chiper-command-injection-advanced, chiper-api-security

### Network & Infrastructure
- chiper-network-pentest, chiper-network-sniffing-mitm, chiper-network-tunneling-proxy
- chiper-dns-attacks, chiper-vpn-attack, chiper-voip-sip-attack
- chiper-wifi-pentest, chiper-bluetooth-rfid-nfc

### Cloud & Container
- chiper-cloud-security, chiper-cloud-identity-attack, chiper-cloud-native-vuln-research
- chiper-kubernetes-attack, chiper-container-security, chiper-gitops-security
- chiper-cspm-casb-attack

### Active Directory & Enterprise
- chiper-ad-ldap-attack, chiper-ad-cs-abuse, chiper-pam-privilege-attack
- chiper-identity-provider-attack, chiper-email-protocol-attack

### AI & LLM Security
- chiper-ai-security, chiper-ai-agent-security, chiper-ai-fuzzing
- chiper-ai-safety-redteam-advanced, chiper-llm-red-team
- chiper-ai-agent-framework-attack, chiper-mcp-server-patterns

### Blockchain & Web3
- chiper-blockchain-web3, chiper-blockchain-l2-attack

### IoT, OT & SCADA
- chiper-iot-pentest, chiper-scada-ics-security, chiper-ics-fieldbus-attack
- chiper-cps-attack, chiper-embedded-rtos-security

### Telecom (4G/5G/6G)
- chiper-5g-telecom-attack, chiper-5g-6g-telecom-attack-advanced

### Wireless & RF
- chiper-sdr-rf-attack, chiper-hf-vhf-radio-attack

### Reverse Engineering & Exploit Dev
- chiper-exploit-development, chiper-binary-reverse, chiper-reverse-engineering-advanced
- chiper-firmware-reverse, chiper-malware-analysis-advanced

### OSINT & Recon
- chiper-osint, chiper-recon-osint, chiper-username-profiling
- chiper-social-intelligence, chiper-darkweb-intel, chiper-deep-research

### Post-Exploitation
- chiper-post-exploitation, chiper-privilege-escalation, chiper-data-exfiltration-attack
- chiper-red-team-infrastructure, chiper-av-edr-evasion, chiper-anti-forensics

### Defense & Blue Team
- chiper-detection-engineering, chiper-threat-hunting, chiper-digital-forensics
- chiper-deception-honeypot, chiper-security-review

### Cryptography
- chiper-crypto-attacks, chiper-quantum-crypto-attack, chiper-hsm-attack
- chiper-post-quantum-migration-attack, chiper-quantum-cryptography-transition

### Mobile
- chiper-mobile-security, chiper-mobile-app-instrumentation, chiper-macos-security

### Payment & Banking
- chiper-payment-security, chiper-open-banking-attack

### And 40+ more domains...

## Structure

```
chiper-cyber/
├── SKILL.md                    ← Entry point
├── README.md                   ← This file
├── chiper-bootstrap/           ← MUST RUN FIRST
│   ├── scripts/install.sh      ← Install 302 tools
│   └── scripts/verify.sh       ← Verify installation
├── chiper-kali-tools/          ← Tool selection reference
├── chiper-kali-identity/       ← 12 Hacker Laws
├── chiper-web-sqli/            ← SQL injection
└── ... (144 skills)
```

## Author

**Chiper** (Chiper-Cyber)

## Source

Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
