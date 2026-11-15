# PoC Sources & Exploit Databases — 2026
> Use this to find latest PoC for any CVE during audit

## Primary PoC Aggregators
| Source | URL | Content | Update |
|--------|-----|---------|--------|
| **pocindex** | github.com/0xMarcio/pocindex | 82,000+ PoCs (GitHub, Nuclei, ExploitDB, Metasploit, Vulhub) | Daily |
| **trickest/CVE** | github.com/trickest/CVE | Auto-generated PoC per CVE | Daily |
| **CVE-2026-PoCs** | github.com/SecureWithUmer/CVE-2026-PoCs | Verified 2026 CVE PoCs with metadata | Active |
| **eip-pocs** | github.com/exploitintel/eip-pocs-and-cves | Exploit Intelligence Platform | Active |
| **VulnCheck XDB** | vulncheck.com/xdb | Validated exploit database | Active |
| **cve.imfht.com** | cve.imfht.com/poc | AI-generated PoC walkthroughs | Daily |
| **bugbountyhunt.com/cve** | bugbountyhunt.com/cve | CVE+PoC for BB hunters | Daily |
| **securityvulnerability.io** | securityvulnerability.io/exploits/latest | Latest exploit PoCs | Daily |

## Advisory Databases
| Source | URL | Content |
|--------|-----|---------|
| **GitHub Advisory DB** | github.com/advisories | CVEs + GHSA, 150M+ users |
| **GHSL** | securitylab.github.com/advisories | GitHub Security Lab advisories |
| **CISA KEV** | cisa.gov/known-exploited-vulnerabilities | Actively exploited vulns |
| **NVD** | nvd.nist.gov | Official NIST CVE database |
| **Vulners** | vulners.com | CVE + HackerOne + Exploit search |
| **GCVE** | db.gcve.eu | Vulnerability-Lookup |

## How to Find PoC for a CVE
```bash
# 1. Search pocindex
curl -sL "https://raw.githubusercontent.com/0xMarcio/pocindex/main/pocs.json" | grep "CVE-2026-XXXX"

# 2. Search GitHub
curl -sL "https://api.github.com/search/repositories?q=CVE-2026-XXXX+exploit&sort=updated&per_page=5"

# 3. Search ExploitDB
curl -sL "https://www.exploit-db.com/search?cve=CVE-2026-XXXX"

# 4. Search nuclei templates
nuclei -t cves/ -id CVE-2026-XXXX -target https://target.com
```

## BB Automation Tools
| Tool | URL | Content |
|------|-----|---------|
| **dark_wxlf** | github.com/ibdtech/dark_wxlf | 4-phase BB automation: OSINT → recon → analysis → vuln testing (XSS, SQLi, IDOR, SSRF). Auto-generates PoCs. |

## How to Execute PoCs During Audit
```
read_file('skills/security/exploit-cookbook/references/pocindex-execution-workflow.md')
```

## Program Lists
| Source | URL | Content |
|--------|-----|---------|
| **Bug-Bounty-Programs** | github.com/SecAnalysts/Bug-Bounty-Programs | Structured BB program list, discovery + tracking |
| **public-bugbounty-programs** | github.com/projectdiscovery/public-bugbounty-programs | Community-curated public BB programs, Chaos integration |

## Key 2026 CVEs with PoC
| CVE | Target | PoC Location |
|-----|--------|-------------|
| CVE-2026-3854 | GitHub RCE | Wiz blog + GitHub |
| CVE-2026-42945 | NGINX RCE | GitHub public |
| CVE-2026-24061 | Telnetd RCE | SafeBreach Labs |
| CVE-2026-20230 | Cisco SSRF | HawkTrace GitHub |
| CVE-2026-61797 | GLPI SQLi | Research blog |
| CVE-2026-76851 | GHES SSRF→RCE | SentinelOne |
| CVE-2026-69192 | IPv4 SSRF Bypass | GitHub Gist |
