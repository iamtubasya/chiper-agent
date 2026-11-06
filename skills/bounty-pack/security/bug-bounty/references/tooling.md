# Reference: Tooling — Standard, Production-Ready (v3)

> Industry-standard security research tools. Power is not in the tool — it's in how you
> wield it with discipline and depth. Every tool here is publicly available.
> Curated from: vavkamil/awesome-bugbounty-tools, nahamsec/Resources, projectdiscovery, swisskyrepo, danielmiessler/SecLists.

---

## 🤖 AI-Powered Agents (Tier 0 — Always try first)

| Agent | Type | Best For | Link |
|---|---|---|---|
| **Shannon** | Autonomous white-box + black-box | Source code + live exploit → proof-by-exploitation reports | KeygraphHQ/shannon |
| **Dark-Moon** | Autonomous full-stack | Web, cloud, AD, K8s, IoT, CI/CD, IaC — 80+ tools via MCP | ASCIT31/Dark-Moon |
| **PentestGPT** | Multi-stage agent | CTF + pentest, recon→exploit→report pipeline | GreyDGL/PentestGPT |
| **bbot** | Recursive internet scanner | Subdomain enum (20-50% more than alternatives), spider, email enum | blacklanternsecurity/bbot |

### Shannon Workflow (proof-by-exploitation)
```
Pre-Recon (source code scan) → Recon (attack surface mapping) →
[Vuln: Injection | XSS | SSRF | Auth | ...] → Exploit (real PoC) → Report
```
- White-box: reads source code to plan attacks
- Black-box: live exploitation against running app
- Only reports findings with working PoC
- Config: login flows, 2FA, TOTP, email-based auth

### bbot Quick Commands
```bash
# Subdomain enum (passive + recursive DNS brute)
bbot -t target.com -p subdomain-enum
# Web spider
bbot -t target.com -p spider
# Email gatherer
bbot -t target.com -p email-enum
# Full web scan (light)
bbot -t www.target.com -p web
# Full web scan (heavy)
bbot -t www.target.com -p web-heavy
# Everything
bbot -t target.com -p subdomain-enum spider email-enum web
```

### PentestGPT Commands
```bash
# CTF mode
pentestgpt --target 10.10.11.234
# Pentest mode (asset discovery → vulns → report)
pentestgpt --target 10.10.11.234 --mode pentest
# With instruction
pentestgpt --target IP --instruction "WordPress site, focus on plugin vulns"
```

---

## Recon & Enumeration

| Category | Tools |
|---|---|
| Subdomain/asset | **bbot** (preferred), subfinder, amass, assetfinder, crt.sh, censys, dnsx, chaos-client, hakrevdns, csp-recon |
| Port/service | nmap, masscan, naabu, rustscan |
| Content/param discovery | **ffuf** (preferred), feroxbuster, gobuster, dirsearch, arjun, x8, ParamSpider |
| Crawling/JS analysis | **katana** (preferred), gospider, hakrawler, gau, waybackurls, waymore, linkfinder, jsluice, xnLinkFinder |
| JS secrets | truffleHog, gitleaks, jsleak, jsluice, getJS |
| Fingerprint | httpx, whatweb, wappalyzer, wafw00f, cdncheck, fingerprintx |
| Screenshots | gowitness, aquatone, EyeWitness, invisible-playwright (anti-bot bypass) |
| **Stealth browser** | **CloakBrowser** (`pip install cloakbrowser` — source-level C++ Chromium patches, passes Turnstile/FingerprintJS/reCAPTCHA v3; see `cloakbrowser-stealth-browser.md`), Camofox (light scraping) |
| Search dorking | Google/Bing advanced operators, GitHub dorking, github-subdomains, gitlab-subdomains |
| WAF evasion | Hacker-Scoper (scope filter), custom payloads from PayloadsAllTheThings |

## Analysis & Interception

| Category | Tools |
|---|---|
| Intercepting proxy | Burp Suite (Community/Pro), OWASP ZAP |
| Out-of-band | interactsh, Burp Collaborator, dnslog.cn |
| **Template scanning** | **nuclei** (primary scanner) + nuclei-templates (community) |
| API analysis | Postman, Insomnia, GraphQL voyager, graphw00f (GraphQL fingerprint) |
| **Wordlists** | **SecLists** (danielmiessler), fuzz.txt, FuzzDB, Assetnote wordlists |
| **Payloads** | **PayloadsAllTheThings** (swisskyrepo) — every vuln type + bypass |

## Exploitation

| Category | Tools |
|---|---|
| SQL injection | sqlmap, ghauri |
| SSTI | tplmap, SSTImap |
| Command injection | commix |
| XXE | XXEinjector, custom DTD |
| Deserialization | ysoserial (Java), PHPGGC (PHP), ysoserial.net (.NET) |
| WebSocket | wscat, custom scripts |
| Race condition | turbo intruder (Burp), custom threading scripts |
| **General web** | curl, httpie, Python requests |

## Web3 / Smart Contract

| Category | Tools |
|---|---|
| Development | Foundry (forge/cast/anvil) — primary, Hardhat — alternative |
| Static analysis | **Mythril** (symbolic exec), **Slither** (dataflow), **Aderyn** (static), Semgrep |
| Fuzzing | **Echidna** (property-based), **Medusa** (state machine), Foundry invariant fuzz |
| Formal verification | **Halmos** (symbolic testing), **Z3** (SMT solver) |
| Custom detectors | FeeCapInconsistency, MissingHealthCheck, RoundingDirectionMismatch (Slither plugins) |
| Explorer | Etherscan/Snowtrace/Polygonscan, Blockscout |
| Simulation | Tenderly, Phalcon, anvil fork |
| Storage | cast storage, sload, slot-by-slot analysis |
| Disassembly | evm.codes, solc --asm, Dedaub, Heimdall |

## Network / Infra

| Category | Tools |
|---|---|
| Cloud recon | cloud_enum, S3Scanner, GCPBucketBrute |
| CI/CD | truffleHog, git-secrets, gitleaks |
| DNS recon | dnsrecon, dnsdumpster, fierce |
| Container | Docker enumeration scripts, kube-hunter |
| CMS | wpscan (WordPress), Droopescan (Drupal/SilverStripe) |

## Payloads & Bypass Reference (from PayloadsAllTheThings)

| Vuln Type | Key Payloads |
|---|---|
| XSS | `<script>alert(1)</script>`, `<img onerror=alert(1)>`, polyglots, event handlers |
| SQLi | `' OR 1=1--`, `UNION SELECT`, time-based blind, stacked queries |
| SSRF | `http://169.254.169.254/`, `http://localhost:8080`, Gopher protocol, DNS rebinding |
| XXE | `<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>`, parameter entities |
| Path Traversal | `../../../etc/passwd`, URL encoding, null bytes, double encoding |
| Command Injection | `; ls`, `| cat /etc/passwd`, backticks, `$()` |
| Deserialization | Java gadget chains, PHP object injection, Pickle payloads |
| Open Redirect | `//evil.com`, `///evil.com`, `\/evil.com`, protocol-relative |
| CRLF | `%0d%0a`, `%5Cr%5Cn`, double encoding |

## Wordlist Locations (SecLists)

```
~/seclists/Discovery/Web-Content/           — dirbusting
~/seclists/Discovery/DNS/                   — subdomain brute
~/seclists/Fuzzing/                         — general fuzzing
~/seclists/Passwords/                       — password lists
~/seclists/Discovery/Infrastructure/        — infrastructure keywords
```

## Nuclei Templates (key categories)

```bash
# Update templates
nuclei -update-templates
# Scan with severity filter
nuclei -l urls.txt -severity medium,high,critical -json
# Auto-detect tech + scan
nuclei -l urls.txt -as
# Specific template
nuclei -l urls.txt -t cves/ -json
# Custom templates
nuclei -l urls.txt -t custom-templates/ -json
```

---

## Healthy Workflow

1. **bbot** → subdomain + spider + email (passive first).
2. **nuclei** → template-based vuln scan.
3. **ffuf/katana** → targeted content/API discovery.
4. **Shannon/Dark-Moon** → AI-powered exploitation (if source code available).
5. **Manual analysis** of candidates (tools assist, brain decides).
6. **Manual verification** + PoC (code proves).
7. **Report.**

## What NOT To Do

- Submit findings directly from scanner output without manual verification.
- Run destructive/DoS scanners against production.
- Trust any tool's output blindly — always verify.
- Skip nuclei update — stale templates = missed vulns.
