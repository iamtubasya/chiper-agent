# Reference Files Loader — Phase 0C

**⚠️ MANDATORY: Load reference files BEFORE starting each test type.**

## Load Procedure

When starting a test section, load the FIRST 3-5 relevant reference files. Don't load all at once — load per test type.

## XSS Testing
```
read_file('skills/security/bug-bounty/references/xss-testing-playbook.md')
read_file('skills/security/bug-bounty/references/articles-xss-vectors-playbook.md')
read_file('skills/security/bug-bounty/references/dom-based-vulnerabilities-playbook.md')
```

## SQL Injection
```
read_file('skills/security/bug-bounty/references/sql-injection-complete.md')
```

## SSRF Testing
```
read_file('skills/security/bug-bounty/references/advanced-vuln-vectors-2026.md')
```

## CORS Testing
```
read_file('skills/security/bug-bounty/references/cors-findings.md')
read_file('skills/security/bug-bounty/references/cors-testing-playbook.md')
```

## Authentication Testing
```
read_file('skills/security/bug-bounty/references/authentication-complete.md')
read_file('skills/security/bug-bounty/references/account-first-exploitation.md')
read_file('skills/security/bug-bounty/references/jwt-playbook.md')
read_file('skills/security/bug-bounty/references/oauth-playbook.md')
```

## GraphQL Testing
```
read_file('skills/security/bug-bounty/references/graphql-attack-patterns.md')
read_file('skills/security/bug-bounty/references/graphql-playbook.md')
```

## API Testing
```
read_file('skills/security/bug-bounty/references/api-testing-complete.md')
read_file('skills/security/bug-bounty/references/api-webapp-testing.md')
```

## Access Control
```
read_file('skills/security/bug-bounty/references/access-control-complete.md')
read_file('skills/security/bug-bounty/references/logic-flaws-complete.md')
```

## File Upload / Path Traversal
```
read_file('skills/security/bug-bounty/references/file-path-traversal-complete.md')
```

## Request Smuggling
```
read_file('skills/security/bug-bounty/references/request-smuggling-playbook.md')
```

## XXE
```
read_file('skills/security/bug-bounty/references/xxe-complete.md')
```

## Race Conditions
```
read_file('skills/security/bug-bounty/references/race-conditions-complete.md')
```

## Prototype Pollution
```
read_file('skills/security/bug-bounty/references/prototype-pollution-playbook.md')
```

## SSTI
```
read_file('skills/security/bug-bounty/references/ssti-playbook.md')
```

## OS Command Injection
```
read_file('skills/security/bug-bounty/references/os-command-injection-complete.md')
```

## CSRF
```
read_file('skills/security/bug-bounty/references/csrf-testing-playbook.md')
```

## Host Header
```
read_file('skills/security/bug-bounty/references/host-header-playbook.md')
```

## Web Cache Poisoning
```
read_file('skills/security/bug-bounty/references/web-cache-poisoning-playbook.md')
read_file('skills/security/bug-bounty/references/web-cache-deception-complete.md')
```

## Deserialization
```
read_file('skills/security/bug-bounty/references/deserialization-playbook.md')
```

## SAML
```
read_file('skills/security/bug-bounty/references/saml-exploitation-patterns.md')
```

## LLM / AI Attacks
```
read_file('skills/security/bug-bounty/references/llm-attacks-playbook.md')
read_file('skills/security/bug-bounty/references/ai-agents.md')
```

## Info Disclosure
```
read_file('skills/security/bug-bounty/references/info-disclosure-complete.md')
```

## CMS (WordPress/Payload)
```
read_file('skills/security/bug-bounty/references/wordpress-admin-attack-surface.md')
read_file('skills/security/bug-bounty/references/payload-cms-graphql-attack-patterns.md')
```

## Credential Attacks
```
read_file('skills/security/bug-bounty/references/credential-attack-pipeline.md')
```

## WebSockets
```
read_file('skills/security/bug-bounty/references/websockets-testing-playbook.md')
```

## DeFi / Web3
```
read_file('skills/security/bug-bounty/references/web3.md')
read_file('skills/security/bug-bounty/references/web3-vuln-patterns.md')
read_file('skills/security/bug-bounty/references/web3-tools.md')
```

## Immunefi Programs
```
read_file('skills/security/bug-bounty/references/immunefi-rules.md')
read_file('skills/security/bug-bounty/references/immunefi-severity.md')
read_file('skills/security/bug-bounty/references/immunefi-poc.md')
```

## Smart Contract (Solana)
```
read_file('skills/security/bug-bounty/references/rust-solana-audit--blackbox-onchain-analysis.md')
```

## Keycloak
```
read_file('skills/security/bug-bounty/references/keycloak-attack-patterns.md')
```

## Clickjacking
```
read_file('skills/security/bug-bounty/references/clickjacking-testing-playbook.md')
```

## Subdomain Takeover
```
read_file('skills/security/bug-bounty/references/dns-subdomain-takeover-and-recon-pitfalls.md')
```

## Infrastructure Pivot
```
read_file('skills/security/bug-bounty/references/infrastructure-pivot-patterns.md')
```

## Next.js / Framework
```
read_file('skills/security/bug-bounty/references/nextjs-nextdata-disclosure.md')
```

## Segment / Analytics Key Extraction
```
read_file('skills/security/bug-bounty/references/segment-write-key-escalation.md')
read_file('skills/security/bug-bounty/references/analytics-data-injection.md')
```

## Recaptcha / Signup Probes
```
read_file('skills/security/bug-bounty/references/recaptcha-signup-probes.md')
```

## Verification Labs (Real CVEs — load before testing related vuln class)
```
read_file('skills/security/bug-bounty/references/cbh-verification-labs/apache-cve-2021-41773.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/jenkins-cve-2024-23897.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/spring-cve-2022-22963.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/juice-shop-2026-05-15.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/recon-hackerone-vdp.md')
```

## Verification Phases (Advanced — JWT/SSTI/SAML/Smuggling/LLM/Cloud)
```
read_file('skills/security/bug-bounty/references/cbh-verification-labs/phase2e-jwt-graphql-race.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/phase2f-ssti-oauth-fileupload.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/phase2g-saml-mfa-xxe.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/phase2h-smuggling-cachepoison.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/phase2i-llm-ato.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/phase2j-cloud-localstack.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/phase3-playwright-browser-execution.md')
read_file('skills/security/bug-bounty/references/cbh-verification-labs/hardened-lab-discipline-rules.md')
```

## Crypto Node/RPC Exploits (load when target has blockchain/crypto component)
```
read_file('skills/security/exploit-cookbook/references/theo-guide.md')
read_file('skills/security/exploit-cookbook/references/scrooge-guide.md')
read_file('skills/security/exploit-cookbook/references/bridge-exploits.md')
read_file('skills/security/exploit-cookbook/references/flashloan-mev.md')
read_file('skills/security/exploit-cookbook/references/key-vulns.md')
read_file('skills/security/exploit-cookbook/references/web3bugs-patterns.md')
read_file('skills/security/smart-contract-audit/references/slowmist-vulns.md')
read_file('skills/security/smart-contract-audit/references/solana-security.md')
read_file('skills/security/security-web-attacks/references/rpc-fingerprint.md')
read_file('skills/security/onchain-finding-verification/references/forensics-trace.md')
read_file('skills/security/bb-audit-launcher/references/crypto-knowledge-index.md')
```

## SQL Injection & Data Extraction (load when SQLi found or testing web2)
```
read_file('skills/security/exploit-cookbook/references/sqlmap-advanced.md')
read_file('skills/security/exploit-cookbook/references/nosqli-guide.md')
read_file('skills/security/exploit-cookbook/references/waf-bypass-tamper.md')
read_file('skills/security/exploit-cookbook/references/blind-sqli-headers.md')
read_file('skills/security/exploit-cookbook/references/sqli-payloads.md')
read_file('skills/security/exploit-cookbook/references/sqli-exfiltration-lab.md')
read_file('skills/security/exploit-cookbook/references/bbqsql-guide.md')
```

## Exploit Playbooks (load when in Phase 0C testing)
```
read_file('skills/security/exploit-cookbook/references/proven-exploits.md')
read_file('skills/security/exploit-cookbook/references/writeup-playbooks.md')
read_file('skills/security/exploit-cookbook/references/403-bypass.md')
read_file('skills/security/exploit-cookbook/references/graphql-attacks.md')
read_file('skills/security/exploit-cookbook/references/vuln-chaining.md')
read_file('skills/security/exploit-cookbook/references/web3-exploit-playbooks.md')
read_file('skills/security/exploit-cookbook/references/post-recon-decision-tree.md')
read_file('skills/security/exploit-cookbook/references/tool-install.md')
```

## Web2 Attack References (load when testing web2 targets)
```
read_file('skills/security/security-web-attacks/references/web-attack-playbooks.md')
read_file('skills/security/security-web-attacks/references/nosqli-guide.md')
read_file('skills/security/security-web-attacks/references/rpc-fingerprint.md')
```

## 2026 Public Disclosures & Testing Methods (MANDATORY — load in Phase 0C BEFORE testing any vector)
```
read_file('skills/security/exploit-cookbook/references/cve-2026-disclosures.md')
read_file('skills/security/exploit-cookbook/references/bb-writeup-techniques.md')
read_file('skills/security/exploit-cookbook/references/hackerone-disclosed-patterns.md')
read_file('skills/security/exploit-cookbook/references/poc-sources-2026.md')
read_file('skills/security/exploit-cookbook/references/pocindex-execution-workflow.md')
read_file('skills/security/exploit-cookbook/references/disclosure-testing-methodology.md')
```
> **⛔ RULE: These 6 files MUST be loaded before testing begins. They contain real-world patterns from 82K+ PoCs and 2026 disclosures. Use them to guide which vectors to test and how.**

## Wordlists & Payloads (load per test type during Phase 0C)
```
# SQLi payloads
read_file('skills/security/exploit-cookbook/references/sqli-auth-bypass-payloads.txt')

# XSS payloads
read_file('skills/security/exploit-cookbook/references/xss-payloads.txt')

# SSRF payloads
read_file('skills/security/exploit-cookbook/references/ssrf-payloads.txt')

# NoSQLi payloads
read_file('skills/security/exploit-cookbook/references/nosqli-payloads.txt')

# CMDi payloads
read_file('skills/security/exploit-cookbook/references/cmdi-payloads.txt')

# Path Traversal payloads
read_file('skills/security/exploit-cookbook/references/path-traversal-payloads.txt')

# XXE payloads
read_file('skills/security/exploit-cookbook/references/xxe-payloads.txt')

# JWT attack payloads
read_file('skills/security/exploit-cookbook/references/jwt-attack-payloads.txt')

# GraphQL payloads
read_file('skills/security/exploit-cookbook/references/graphql-payloads.txt')

# WAF bypass payloads
read_file('skills/security/exploit-cookbook/references/waf-bypass-payloads.txt')

# Sensitive files wordlist
read_file('skills/security/exploit-cookbook/references/sensitive-files-wordlist.txt')

# Web3 attack patterns
read_file('skills/security/exploit-cookbook/references/web3-attack-patterns.txt')

# Common passwords
read_file('skills/security/exploit-cookbook/references/common-passwords.txt')
```
> **⛔ RULE: Load ONLY the payload file matching the current test type. Do NOT load all 13 at once.**
> Wordlists also at: D:/data hermes/wordlists/ (organized by phase)

## HTML Injection Rules (MANDATORY — load when testing HTML injection)
```
read_file('skills/security/exploit-cookbook/references/html-injection-rules.md')
```
> **⛔ RULE: HTML injection MUST chain to XSS or real impact. Basic payloads = OUT OF SCOPE. Always provide complete PoC.**

## Execution Discipline (MANDATORY — load at audit start)
```
read_file('skills/security/exploit-cookbook/references/execution-discipline-protocol.md')
```
> **⛔ 6 RULES enforcement. Violations = STOP. No claim COMPLETE without verification log.**

## Config & Timeout Settings (load at audit start)
```
read_file('skills/security/exploit-cookbook/references/config-and-timeout-settings.md')
```
> **Wordlist paths, timeout values, retry strategy — reference before every tool execution.**

## Hack-Skills Reference (102 Vulnerability Classes)
```
# Core Web Vulns
read_file('skills/security/exploit-cookbook/references/hackskill-xss-cross-site-scripting.md')
read_file('skills/security/exploit-cookbook/references/hackskill-sqli-sql-injection.md')
read_file('skills/security/exploit-cookbook/references/hackskill-ssrf-server-side-request-forgery.md')
read_file('skills/security/exploit-cookbook/references/hackskill-idor-broken-object-authorization.md')
read_file('skills/security/exploit-cookbook/references/hackskill-cors-cross-origin-misconfiguration.md')
read_file('skills/security/exploit-cookbook/references/hackskill-authbypass-authentication-flaws.md')
read_file('skills/security/exploit-cookbook/references/hackskill-business-logic-vulnerabilities.md')
read_file('skills/security/exploit-cookbook/references/hackskill-race-condition.md')
read_file('skills/security/exploit-cookbook/references/hackskill-path-traversal-lfi.md')
read_file('skills/security/exploit-cookbook/references/hackskill-jwt-oauth-token-attacks.md')

# Advanced Attacks
read_file('skills/security/exploit-cookbook/references/hackskill-open-redirect.md')
read_file('skills/security/exploit-cookbook/references/hackskill-cmdi-command-injection.md')
read_file('skills/security/exploit-cookbook/references/hackskill-ssti-server-side-template-injection.md')
read_file('skills/security/exploit-cookbook/references/hackskill-xxe-xml-external-entity.md')
read_file('skills/security/exploit-cookbook/references/hackskill-nosql-injection.md')
read_file('skills/security/exploit-cookbook/references/hackskill-waf-bypass-techniques.md')
read_file('skills/security/exploit-cookbook/references/hackskill-401-403-bypass-techniques.md')
read_file('skills/security/exploit-cookbook/references/hackskill-csp-bypass-advanced.md')
read_file('skills/security/exploit-cookbook/references/hackskill-request-smuggling.md')
read_file('skills/security/exploit-cookbook/references/hackskill-web-cache-deception.md')

# Auth & Session
read_file('skills/security/exploit-cookbook/references/hackskill-csrf-cross-site-request-forgery.md')
read_file('skills/security/exploit-cookbook/references/hackskill-saml-sso-assertion-attacks.md')
read_file('skills/security/exploit-cookbook/references/hackskill-oauth-oidc-misconfiguration.md')
read_file('skills/security/exploit-cookbook/references/hackskill-http-host-header-attacks.md')

# Infrastructure
read_file('skills/security/exploit-cookbook/references/hackskill-dns-rebinding-attacks.md')
read_file('skills/security/exploit-cookbook/references/hackskill-subdomain-takeover.md')
read_file('skills/security/exploit-cookbook/references/hackskill-crlf-injection.md')
read_file('skills/security/exploit-cookbook/references/hackskill-clickjacking.md')

# Advanced
read_file('skills/security/exploit-cookbook/references/hackskill-prototype-pollution.md')
read_file('skills/security/exploit-cookbook/references/hackskill-deserialization-insecure.md')
read_file('skills/security/exploit-cookbook/references/hackskill-graphql-and-hidden-parameters.md')
read_file('skills/security/exploit-cookbook/references/hackskill-llm-prompt-injection.md')

# Web3
read_file('skills/security/exploit-cookbook/references/hackskill-smart-contract-vulnerabilities.md')
read_file('skills/security/exploit-cookbook/references/hackskill-defi-attack-patterns.md')

# Bug Bounty Meta
read_file('skills/security/exploit-cookbook/references/skill-bug-bounty-pitfalls.md')
read_file('skills/security/exploit-cookbook/references/skill-bug-bounty-qc.md')
read_file('skills/security/exploit-cookbook/references/skill-bug-bounty-evidence.md')
read_file('skills/security/exploit-cookbook/references/skill-bug-bounty-collective-wisdom.md')
read_file('skills/security/exploit-cookbook/references/skill-bug-bounty-recon-patterns.md')
read_file('skills/security/exploit-cookbook/references/skill-oauth-oidc-audit.md')
read_file('skills/security/exploit-cookbook/references/skill-ip-and-session-hijacking.md')
```
> **⛔ Load per test type. Do NOT load all at once.**

## Red Team
```
read_file('skills/security/exploit-cookbook/references/redteam-playbook.md')
```

## FOCUSED WORDLISTS (for ffuf/nuclei — <2000 lines)
```
# Directories (2000 lines)
read_file('D:/data hermes/wordlists/0B-recon/focused/directories/common-focused.txt')

# Files (2000 lines)
read_file('D:/data hermes/wordlists/0B-recon/focused/files/common-focused.txt')

# Subdomains (1000 lines)
read_file('D:/data hermes/wordlists/0B-recon/focused/subdomains/subdomains-focused.txt')

# Sensitive files (169 lines)
read_file('D:/data hermes/wordlists/0C-sensitive-files/sensitive-files-wordlist.txt')
```
> **RULE: Use focused wordlists first. Only use full wordlists if focused returns good results.**

## Phase Execution Enforcement (MANDATORY — load at audit start)
```
read_file('skills/security/exploit-cookbook/references/phase-execution-enforcement.md')
```
> **⛔ ZERO SKIP PROTOCOL: Every file MUST be loaded, executed, documented, verified. Timeout = retry, NOT skip. Context full = evict recon, NOT references. Claim COMPLETE = ALL files executed.**
