# BugBounty Playbook — Full Index (186 pages)

Auto-mirrored from https://bugbounty.info/ (Quartz content index). Every page below is a
reference file in this skill. Paths are relative to `references/`.

| Top-level | Pages | What it covers |
|---|---|---|
| `index.md` | 1 | Site landing page. |
| `recon/` | 24 | Asset discovery: subdomains, ASN, ASM, CT logs, cloud ranges, JS, GitHub dorking, OSINT on employees, wayback, params, ports, SaaS enum, robots/security.txt, monitoring, data management. |
| `methodology/` | 10 | Hunting discipline: target selection, scoping, time-boxing, recon-driven hunting, specialising, chain thinking, post-submission, disputes, legal protections. |
| `chains/` | 20 | Pre-built multi-step exploit chains (XSS→ATO, SSRF→cloud RCE, IDOR→ATO, OAuth→ATO, race→financial, SSTI→RCE, XXE→SSRF→RCE, prototype pollution, request smuggling, file upload→RCE, GraphQL BFLA→extraction, prompt-injection→exfil, and more) with flow diagrams + step-by-step + public reports. |
| `attack-surface/` | 91 | Per-surface TTPs: Web (auth, authorization, injection, client-side, file ops, infra, business logic), API (REST/GraphQL/gRPC/gateway bypass), Cloud (AWS/Azure/GCP/multi-cloud), CI/CD (Actions/GitLab/Jenkins/secrets/supply-chain), AI-LLM (prompt injection, agent abuse, MCP, RAG, output handling, DoS, training-data leaks), Mobile, Web3. |
| `reporting/` | 6 | Report writing, templates, impact statements, severity escalation, responsible disclosure. |
| `tooling/` | 7 | AI-assisted workflow, automation, Browser DevTools, Burp Suite, Nuclei, ffuf. |
| `programs/` | 14 | Platform selection + per-platform notes (HackerOne, Bugcrowd, Intigriti, Immunefi, YesWeHack, etc.). |
| `business-of-bounties/` | 12 | Career strategy, financials, running a program, for-organisations guides, mental health. |
| `resources/` | 1 | Curated resources. |

---
## All pages by section

### index.md
- `index.md` — The Bug Bounty Playbook
### recon/
- `recon/API-Discovery.md` — API Discovery
- `recon/API-Documentation-Discovery.md` — API Documentation Discovery
- `recon/ASN-Mapping.md` — ASN Mapping
- `recon/Acquisitions.md` — Acquisitions
- `recon/Certificate-Transparency.md` — Certificate Transparency
- `recon/Cloud-Range-Discovery.md` — Cloud Range Discovery
- `recon/Content-Discovery.md` — Content Discovery
- `recon/Data-Management.md` — Data Management
- `recon/Exposed-Git.md` — Exposed Git Repositories
- `recon/GitHub-Dorking.md` — GitHub Dorking
- `recon/JavaScript-Analysis.md` — JavaScript Analysis
- `recon/Mobile-App-Recon.md` — Mobile App Recon
- `recon/Monitoring.md` — Monitoring
- `recon/OSINT-on-Employees.md` — OSINT on Employees
- `recon/Parameter-Discovery.md` — Parameter Discovery
- `recon/Pipeline.md` — Pipeline
- `recon/Port-Scanning.md` — Port Scanning
- `recon/SaaS-Enumeration.md` — SaaS Enumeration
- `recon/Shodan-Censys-Fofa.md` — Shodan, Censys & FOFA
- `recon/Subdomain-Enumeration.md` — Subdomain Enumeration
- `recon/Tech-Fingerprinting.md` — Tech Fingerprinting
- `recon/Wayback-Mining.md` — Wayback Mining
- `recon/index.md` — Recon
- `recon/robots-and-security.txt.md` — robots.txt, security.txt & sitemap.xml

### methodology/
- `methodology/Chain-Thinking.md` — Chain Thinking
- `methodology/Dispute-Handling.md` — Dispute Handling
- `methodology/Legal-Protections.md` — Legal Protections
- `methodology/Post-Submission.md` — Post-Submission Workflow
- `methodology/Recon-Driven-Hunting.md` — Recon-Driven Hunting
- `methodology/Scoping.md` — Scoping & Rules of Engagement
- `methodology/Specializing.md` — Specialising
- `methodology/Target-Selection.md` — Target Selection
- `methodology/Time-Boxing.md` — Time-Boxed Hunting
- `methodology/index.md` — Methodology

### chains/
- `chains/CSRF-to-ATO.md` — CSRF to Account Takeover
- `chains/File-Upload-to-RCE.md` — File Upload to RCE
- `chains/GraphQL-BFLA-to-Extraction.md` — GraphQL BFLA to Mass Data Extraction
- `chains/IDOR-and-Mass-Assignment.md` — IDOR and Mass Assignment to Privilege Escalation
- `chains/IDOR-to-ATO.md` — IDOR to PII Leak to Account Takeover
- `chains/Info-Disclosure-to-Full-Exploit.md` — Info Disclosure to Full Exploitation
- `chains/OAuth-Misconfig-to-ATO.md` — OAuth Misconfiguration to Account Takeover
- `chains/Open-Redirect-to-ATO.md` — Open Redirect to OAuth Account Takeover
- `chains/Prompt-Injection-to-Data-Exfil.md` — Prompt Injection to Data Exfiltration
- `chains/Prototype-Pollution-to-Exploit.md` — Prototype Pollution to Exploit
- `chains/Race-Condition-to-Financial.md` — Race Condition to Financial Impact
- `chains/SSRF-to-Cloud-RCE.md` — SSRF to Cloud Metadata to RCE
- `chains/SSTI-to-RCE.md` — SSTI to RCE
- `chains/Self-XSS-to-Exploitable.md` — Self-XSS to Exploitable Chain
- `chains/Subdomain-Takeover-to-OAuth.md` — Subdomain Takeover to OAuth Account Takeover
- `chains/Subdomain-Takeover-to-Session.md` — Subdomain Takeover to Cookie Theft
- `chains/XSS-to-Account-Takeover.md` — XSS to Account Takeover
- `chains/XSS-to-Privilege-Escalation.md` — XSS to Admin Action to Privilege Escalation
- `chains/XXE-to-SSRF-to-RCE.md` — XXE to SSRF to Cloud RCE
- `chains/index.md` — Chains

### attack-surface/
- `attack-surface/AI-LLM/Agent-Abuse.md` — Agent Abuse
- `attack-surface/AI-LLM/Direct-Prompt-Injection.md` — Direct Prompt Injection
- `attack-surface/AI-LLM/Indirect-Prompt-Injection.md` — Indirect Prompt Injection
- `attack-surface/AI-LLM/MCP-Vulnerabilities.md` — MCP Vulnerabilities
- `attack-surface/AI-LLM/Model-DoS-and-Resource-Abuse.md` — Model DoS & Resource Abuse
- `attack-surface/AI-LLM/Output-Handling-Flaws.md` — Output Handling Flaws
- `attack-surface/AI-LLM/RAG-and-Vector-DB-Attacks.md` — RAG & Vector DB Attacks
- `attack-surface/AI-LLM/Training-Data-and-Memory-Leaks.md` — Training Data & Memory Leaks
- `attack-surface/AI-LLM/index.md` — AI & LLM Applications
- `attack-surface/API/API-Gateway-Bypass.md` — API Gateway Bypass
- `attack-surface/API/GraphQL.md` — GraphQL
- `attack-surface/API/REST.md` — REST
- `attack-surface/API/gRPC.md` — gRPC
- `attack-surface/API/index.md` — API Attack Surface
- `attack-surface/CI-CD/GitHub-Actions.md` — GitHub Actions
- `attack-surface/CI-CD/GitLab-CI.md` — GitLab CI
- `attack-surface/CI-CD/Jenkins.md` — Jenkins
- `attack-surface/CI-CD/Secret-Leakage.md` — Secret Leakage
- `attack-surface/CI-CD/Supply-Chain.md` — Supply Chain
- `attack-surface/CI-CD/index.md` — CI/CD Attack Surface
- `attack-surface/Cloud/AWS/Cognito.md` — Cognito
- `attack-surface/Cloud/AWS/IAM-Privilege-Escalation.md` — IAM Privilege Escalation
- `attack-surface/Cloud/AWS/Lambda.md` — Lambda
- `attack-surface/Cloud/AWS/S3-Misconfiguration.md` — S3 Misconfiguration
- `attack-surface/Cloud/AWS/index.md` — AWS Attack Surface
- `attack-surface/Cloud/Azure/index.md` — Azure Attack Surface
- `attack-surface/Cloud/GCP/index.md` — GCP Attack Surface
- `attack-surface/Cloud/Multi-Cloud/index.md` — Multi-Cloud Attack Patterns
- `attack-surface/Cloud/index.md` — Cloud Attack Surface
- `attack-surface/Mobile/Android/index.md` — Android Testing
- `attack-surface/Mobile/Shared/index.md` — Shared Mobile Concerns
- `attack-surface/Mobile/iOS/index.md` — iOS Testing
- `attack-surface/Mobile/index.md` — Mobile Attack Surface
- `attack-surface/Web/Authentication/JWT.md` — JWT Attacks
- `attack-surface/Web/Authentication/Login-Bypass.md` — Login Bypass
- `attack-surface/Web/Authentication/MFA-Bypass.md` — MFA Bypass
- `attack-surface/Web/Authentication/OAuth.md` — OAuth
- `attack-surface/Web/Authentication/Password-Reset.md` — Password Reset
- `attack-surface/Web/Authentication/SSO.md` — SSO
- `attack-surface/Web/Authentication/Session-Management.md` — Session Management
- `attack-surface/Web/Authorization/BOLA.md` — BOLA
- `attack-surface/Web/Authorization/IDOR.md` — IDOR
- `attack-surface/Web/Authorization/Multi-Tenancy.md` — Multi-Tenancy
- `attack-surface/Web/Authorization/Privilege-Escalation.md` — Privilege Escalation
- `attack-surface/Web/Business-Logic/Mass-Assignment.md` — Mass Assignment
- `attack-surface/Web/Business-Logic/Price-Manipulation.md` — Price Manipulation
- `attack-surface/Web/Business-Logic/Race-Conditions.md` — Race Conditions
- `attack-surface/Web/Business-Logic/State-Machine.md` — State Machine Bugs
- `attack-surface/Web/Client-Side/CORS.md` — CORS Misconfigurations
- `attack-surface/Web/Client-Side/CSRF.md` — CSRF
- `attack-surface/Web/Client-Side/Clickjacking.md` — Clickjacking
- `attack-surface/Web/Client-Side/Prototype-Pollution.md` — Prototype Pollution
- `attack-surface/Web/Client-Side/Subdomain-Takeover.md` — Subdomain Takeover
- `attack-surface/Web/Client-Side/WebSocket.md` — WebSocket Security
- `attack-surface/Web/Client-Side/postMessage-Vulnerabilities.md` — postMessage Vulnerabilities
- `attack-surface/Web/File-Operations/File-Upload.md` — File Upload
- `attack-surface/Web/File-Operations/Path-Traversal.md` — Path Traversal
- `attack-surface/Web/File-Operations/XXE.md` — XXE (XML External Entities)
- `attack-surface/Web/Infrastructure/Cache-Poisoning.md` — Cache Poisoning
- `attack-surface/Web/Infrastructure/HTTP2-Attacks.md` — HTTP/2 Attacks
- `attack-surface/Web/Infrastructure/Open-Redirect.md` — Open Redirect
- `attack-surface/Web/Infrastructure/Request-Smuggling.md` — HTTP Request Smuggling
- `attack-surface/Web/Infrastructure/Web-Cache-Deception.md` — Web Cache Deception
- `attack-surface/Web/Injection/Command-Injection.md` — Command Injection
- `attack-surface/Web/Injection/Deserialization.md` — Deserialization
- `attack-surface/Web/Injection/Host-Header.md` — Host Header
- `attack-surface/Web/Injection/NoSQLi.md` — NoSQLi
- `attack-surface/Web/Injection/SQLi/Blind.md` — Blind
- `attack-surface/Web/Injection/SQLi/Error-Based.md` — Error-Based
- `attack-surface/Web/Injection/SQLi/Second-Order.md` — Second-Order
- `attack-surface/Web/Injection/SQLi/index.md` — SQL Injection  -  Overview
- `attack-surface/Web/Injection/SSTI.md` — SSTI
- `attack-surface/Web/Injection/XSS/DOM-XSS.md` — DOM XSS
- `attack-surface/Web/Injection/XSS/Framework-XSS.md` — Framework XSS
- `attack-surface/Web/Injection/XSS/Reflected-XSS.md` — Reflected XSS
- `attack-surface/Web/Injection/XSS/Stored-XSS.md` — Stored XSS
- `attack-surface/Web/Injection/XSS/WAF-Bypass.md` — WAF Bypass
- `attack-surface/Web/Injection/XSS/index.md` — XSS  -  Overview
- `attack-surface/Web/SSRF/index.md` — SSRF
- `attack-surface/Web/index.md` — Web Applications
- `attack-surface/Web3/Access-Control.md` — Access Control
- `attack-surface/Web3/Cross-Chain-Bridge.md` — Cross-Chain Bridge
- `attack-surface/Web3/Integer-and-Precision.md` — Integer and Precision
- `attack-surface/Web3/MEV-and-Frontrunning.md` — MEV and Frontrunning
- `attack-surface/Web3/Oracle-Manipulation.md` — Oracle Manipulation
- `attack-surface/Web3/Reentrancy.md` — Reentrancy
- `attack-surface/Web3/Signature-and-Replay.md` — Signature and Replay
- `attack-surface/Web3/Smart-Contract-Basics.md` — Smart Contract Basics
- `attack-surface/Web3/Tooling.md` — Web3 Tooling
- `attack-surface/Web3/index.md` — Web3 & Smart Contracts
- `attack-surface/index.md` — Attack Surface

### reporting/
- `reporting/Impact-Statements.md` — Impact Statements
- `reporting/Report-Templates.md` — Report Templates
- `reporting/Report-Writing.md` — Report Writing
- `reporting/Responsible-Disclosure.md` — Responsible Disclosure
- `reporting/Severity-Escalation.md` — Severity Escalation
- `reporting/index.md` — Reporting

### tooling/
- `tooling/AI-Assisted/index.md` — AI-Assisted Hunting
- `tooling/Automation/index.md` — Automation
- `tooling/Browser-DevTools/index.md` — Browser DevTools
- `tooling/Burp-Suite/index.md` — Burp Suite
- `tooling/Nuclei/index.md` — Nuclei
- `tooling/ffuf/index.md` — ffuf
- `tooling/index.md` — Tooling

### programs/
- `programs/Platforms/Bugcrowd.md` — Bugcrowd
- `programs/Platforms/Chaos-Project.md` — Chaos Project
- `programs/Platforms/Cobalt.md` — Cobalt
- `programs/Platforms/Direct-Programs.md` — Direct Programs
- `programs/Platforms/HackerOne.md` — HackerOne
- `programs/Platforms/Immunefi.md` — Immunefi
- `programs/Platforms/Intigriti.md` — Intigriti
- `programs/Platforms/Synack.md` — Synack
- `programs/Platforms/YesWeHack.md` — YesWeHack
- `programs/Selection/Competition-Assessment.md` — Competition Assessment
- `programs/Selection/New-Programs.md` — New Programs
- `programs/Selection/Payout-Analysis.md` — Payout Analysis
- `programs/Selection/Reading-Scope.md` — Reading Scope
- `programs/index.md` — Programs

### business-of-bounties/
- `business-of-bounties/Career-Strategy.md` — Career Strategy
- `business-of-bounties/Financial.md` — Financial
- `business-of-bounties/For-Organisations/1-Starting-a-Program.md` — Starting a Program
- `business-of-bounties/For-Organisations/2-Scoping-a-Program.md` — Scoping a Program
- `business-of-bounties/For-Organisations/3-Choosing-a-Platform.md` — Choosing a Platform
- `business-of-bounties/For-Organisations/4-Setting-Bounty-Tables.md` — Setting Bounty Tables
- `business-of-bounties/For-Organisations/5-Researcher-Relationships.md` — Researcher Relationships
- `business-of-bounties/For-Organisations/6-The-Business-Case.md` — The Business Case
- `business-of-bounties/For-Organisations/index.md` — For Organisations
- `business-of-bounties/Mental-Health.md` — Mental Health
- `business-of-bounties/Running-a-Program.md` — Running a Program
- `business-of-bounties/index.md` — Business of Bounties

### resources/
- `resources/index.md` — Resources
