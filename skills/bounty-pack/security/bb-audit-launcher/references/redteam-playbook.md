# Red Team Playbook — Curated from 17 Repos
> C2 frameworks, post-exploitation, lateral movement, privilege escalation.
> This is a REFERENCE file — methodology only, not executable tools.

## C2 Frameworks (Methodology)

### 1. pupy ⭐9K — Python C2
- Cross-platform: Windows, Linux, OSX, Android
- Features: keylogger, screenshot, file manager, SOCKS proxy
- URL: https://github.com/n1nj4sec/pupy

### 2. Covenant ⭐4.7K — .NET C2
- Collaborative red team framework
- Features: tasking, agents, grunts, social engineering
- URL: https://github.com/cobbr/Covenant

### 3. Villain ⭐4.5K — Stage 0/1 C2
- Multiple reverse TCP + HoaxShell shells
- Features: payload generation, session management
- URL: https://github.com/t3l3machus/Villain

### 4. PoshC2 ⭐2.1K — PowerShell C2
- Proxy-aware, multi-protocol
- Features: lateral movement, persistence, credential theft
- URL: https://github.com/nettitude/PoshC2

### 5. phpsploit ⭐2.5K — Webshell C2
- Single-line PHP backdoor persistence
- Features: file upload, cmd exec, reverse shell
- URL: https://github.com/nil0x42/phpsploit

---

## Post-Exploitation Methodology

### Privilege Escalation (Linux)
```bash
# Enumerate SUID binaries
find / -perm -u=s -type f 2>/dev/null
# Kernel exploit check
uname -r
# Search for exploit: searchsploit linux kernel <version>
# Sudo abuse
sudo -l
# Capabilities
getcap -r / 2>/dev/null
```
**Repos:** k8gege/K8tools (6.2K)

### Privilege Escalation (Windows)
```bash
# Whoami /priv
# Token impersonation
# Service misconfiguration
# Unquoted service paths
# DLL hijacking
# AlwaysInstallElevated
```

### Lateral Movement
- Pass-the-Hash
- Pass-the-Ticket
- Overpass-the-Hash
- Remote service exploitation
- PsExec/WMI/WinRM

### Persistence
- Registry run keys
- Scheduled tasks
- Service creation
- DLL side-loading
- Startup folder

---

## Offense Frameworks

### TIDoS ⭐1.9K — Manual Web Pentest
- 5 phases: recon, footprint, vuln analysis, exploitation, post-exploitation
- URL: https://github.com/0xInfection/TIDoS-Framework

### NeuroSploit ⭐1.4K — AI-Powered Pentest
- Automated scanning + exploitation
- URL: https://github.com/JoasASantos/NeuroSploit

### offensive-claude ⭐367 — AI Offensive Toolkit
- Red team, exploit dev, AD attacks, EDR bypass
- URL: https://github.com/hypnguyen1209/offensive-claude

---

## Tool Index

| Category | Tools |
|----------|-------|
| C2 Frameworks | pupy, Covenant, Villain, PoshC2, phpsploit, Rshell |
| Post-Exploitation | shad0w, Mongoose, TIDoS |
| Hardware Red Team | The-Hackers-Hardware-Toolkit |
| AI Red Team | NeuroSploit, offensive-claude, AI-penetration-testing |
| Frameworks | RedTeam_toolkit (Django UI) |

---

## Integrated Repos (17)

| Repo | Stars | Category |
|------|-------|----------|
| n1nj4sec/pupy | 9K | C2 (Python) |
| cobbr/Covenant | 4.7K | C2 (.NET) |
| t3l3machus/Villain | 4.5K | C2 (TCP) |
| nil0x42/phpsploit | 2.5K | C2 (Webshell) |
| yadox666/The-Hackers-Hardware-Toolkit | 2.2K | Hardware |
| nettitude/PoshC2 | 2.1K | C2 (PowerShell) |
| 0xInfection/TIDoS-Framework | 1.9K | Web pentest |
| JoasASantos/NeuroSploit | 1.4K | AI pentest |
| tcostam/awesome-command-control | 980 | C2 index |
| DavidProbinsky/RedTeam-Physical-Tools | 606 | Physical |
| signorrayan/RedTeam_toolkit | 573 | Toolkit UI |
| Rubby2001/Rshell | 542 | C2 (Go) |
| hypnguyen1209/offensive-claude | 367 | AI offensive |
| Mr-Infect/AI-penetration-testing | 285 | AI/LLM pentest |
| zux0x3a/0xsp-Mongoose | 533 | Windows audit |
| bats3c/shad0w | 2.2K | Covert post-exploit |
| k8gege/K8tools | 6.2K | Intranet pentest |

---

## Cross-References
- Exploit playbooks → `exploit-cookbook`
- Attack vectors → `security-web-attacks`
- Cloud targets → `security-cloud`
- Report → `bug-report-delivery` (Phase 0F, ABSOLUTE LAST)
