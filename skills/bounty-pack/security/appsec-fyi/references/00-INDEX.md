# appsec.fyi — Technique Reference Index

> Mirror of https://appsec.fyi/ — a curated AppSec resource library by Carl Sampson.
> 25 practical-guide classes, each synthesized from 1,000+ cited resources.
> **Web2 + adjacent (AI/LLM, mobile, OSINT, fuzzing, supply-chain, recon).**
> **No dedicated web3/smart-contract class** — see `references/00-INDEX.md` bottom note.

## Class → techniques overview

| Class | File | Techniques (attack patterns) |
|---|---|---|
| RCE | `references/rce.md` | PHP2Shell (CVE-2026-109618 & CVE-2026-109619), Spring4Shell (CVE-2022-22965), Server-Side Template Injection (SSTI) Variants, Deserialization Exploitation in Enterprise Java Platforms, Container Escapes and Cloud Native Exploitation, AI-Assisted Exploit Development and AI Infrastructure Targeting, Kernel Exploitation, Supply Chain Attacks |
| SSRF | `references/ssrf.md` | Cloud Metadata Services Abuse, Bypassing IP Address and Host Restrictions, Exploiting Specific Application Features, SSRF Chaining for RCE, Blind SSRF Exploitation, Cloud Metadata Exfiltration Beyond IMDSv1, HTTP/2 Request Smuggling, PDF Generation and HTML/JavaScript Injection, AI Agent and LLM Pipeline Exploitation, XXE Beyond Basic XML Parsing, Leveraging URL Parsing and Protocol Handlers, Portainer SSRF via URL Validation Bypass, MLflow Webhook SSRF Leading to Cloud Credential Theft, SonicWall SMA1000 SSRF Chains, Next, Axios Vulnerabilities (Header Injection, NO_PROXY Bypass), Craft CMS GraphQL SSRF Bypass |
| SQLi | `references/sqli.md` | In-Band SQLi (Error-Based and UNION-Based), Inferential (Blind) SQLi, Out-of-Band (OOB) SQLi, Second-Order SQLi, Advanced and Context-Specific Techniques |
| XSS | `references/xss.md` | SVG and XML Exploitation, DOM Clobbering and Parser Manipulations, WAF and Filter Bypass Techniques, DOM-Based XSS in Modern Frameworks, POST-Based XSS and Account Takeover, Exploiting Browser Extensions and WebExtensions, CSS Weaponization, Other Notable Techniques |
| XXE | `references/xxe.md` | Entities & DTDs; Parameter vs General Entities; File Disclosure & Data Exfiltration; SSRF via XXE; Blind XXE & OOB Exfiltration; Exploiting File Uploads; Other Protocols & Wrappers; Local DTD Reuse |
| IDOR/BOLA | `references/idor.md` | Sequential and Predictable Identifiers, Exploiting Object References in Various Request Components, Second-Order and Multi-Step IDORs, Mass Assignment and Parameter Pollution, Blind IDORs, IDORs in Account Recovery and Password Reset Flows, IDORs in Role/Permission Management |
| JWT | `references/jwt.md` | Signature Verification Failures (decode-vs-verify, alg:none, null signature); Algorithm Confusion (RS/EC→HS); Weak Secrets & Key Management; Header Parameter Injection; Claim Tampering; Client-Side Storage; Other |
| CSRF | `references/csrf.md` | GET-Based CSRF, POST-Based CSRF, JSON-Based CSRF, Referrer Header Bypass, Method Override Bypass, SameSite Cookie Bypass, CSRF Token Validation Bypass |
| SSTI | `references/ssti.md` | Detection & Identification Payloads; Object Chaining for RCE; Engine-Specific Execution Primitives; Filter Bypasses |
| Deserialization | `references/deser.md` | Gadget Chains, Specific Exploitation Vectors |
| GraphQL | `references/graphql.md` | Introspection Abuse, Injection Attacks, Authorization and Access Control Flaws, Denial of Service (DoS) and Resource Exhaustion, Supply Chain and Code Injection Risks, Broken Authentication |
| API Security | `references/apisec.md` | Authentication and Authorization Weaknesses, Data Exposure and Leakage, Injection and Input Validation Flaws, Business Logic and Flow Vulnerabilities, Server-Side Request Forgery (SSRF), HTTP Smuggling and Desync Attacks, AI-Specific Vulnerabilities, SVG Sanitizer Bypasses, Weak JWT Signature Validation, Loopjacking, Exploiting Custom URL Schemes and PWAs, CRLF Injection for HTTP Desync Attacks, Arbitrary File Read (Path Traversal), Insecure Deserialization, Uncontrolled Resource Consumption (Denial of Service), API Key Theft and Credit Consumption, Exposure of OTPs in API Responses, Unauthenticated API Endpoint Exposing Sensitive Data, Exploiting Agent Harnesses for Forged Instructions |
| Authentication | `references/authn.md` | Authentication Bypass, Account Takeover (ATO) and Credential Compromise, Token Abuse, Cloud and API Security, AI Agent Security |
| Authorization | `references/authz.md` | BOLA/IDOR, Broken Function-Level AuthZ, Privilege Escalation, Object vs Function Level |
| AI / LLM | `references/ai.md` | Agent Swarms & Autonomy, LLMJacking, Credential Exfiltration via LLM, Sandbox/Container Escapes, AI-Generated Package Slopsquatting, Prompt Injection (indirect), Adversarial Probing / AI Fuzzing, Agent Impersonation/Cloaking, AI-Assisted Offensive (discovery/exploit/post-exploit) |
| Mobile | `references/mobile.md` | Arbitrary File Overwrite (AFO) via Libraries, Intent Redirection and Hijacking, URL Scheme Hijacking and Universal Links, WebView Exploitation, Root/Jailbreak Detection Bypass, SSL Pinning Bypass, Exploiting Third-Party SDKs, iOS Exploit Chains and Zero-Days, Memory Corruption and Kernel Exploitation |
| OSINT | `references/osint.md` | Google Dorking, Social Media Intelligence (SOCMINT), Publicly Exposed Files and Metadata Analysis, Certificate Transparency (CT) Logs, Internet-Connected Device Discovery, Username Enumeration, Dark Web Intelligence (DARKInt), Typing Style as a Digital Fingerprint |
| Recon | `references/recon.md` | Subdomain Enumeration, JavaScript Reconnaissance, Cloud Asset Discovery and Misconfigurations, Exploiting Embedded Systems and IoT Devices, GitHub Reconnaissance, AI-Assisted Reconnaissance, Certificate Transparency (CT) Log Analysis, Favicon Fingerprinting, Analyzing Reverse DNS Records, Exploiting Vulnerabilities in Networking Equipment, Container and Kubernetes Security Reconnaissance |
| Secrets | `references/secrets.md` | Secret Scanning & Detection, Exposed, History rewriting, CI/CD secret leakage, Non-Human Identity (NHI) abuse, Runtime secret exfiltration |
| Supply Chain | `references/supplychain.md` | Self-Propagating Worms, Credential Harvesting Sophistication, Exploiting Build and Runtime Behaviors, Code Signing and Provenance Forgery, AI Ecosystem Attacks |
| Fuzzing | `references/fuzzing.md` | Structure-Aware and Grammar-Based Fuzzing, AI-Assisted Fuzzing and Harness Synthesis, Binary-Only Fuzzing, Protocol Fuzzing, Targeted Fuzzing and Sanitizers |
| Burp Suite | `references/burp.md` | XML External Entity (XXE) Injection, HTTP Host Header Attacks, Path Traversal for File Upload, API Security Testing, Race Conditions and High-Speed Attacks, AI-Assisted Security Testing, Session Management and Authorization Testing, JavaScript Analysis, Customization with Bambda and BCheck Scripts |
| Python | `references/python.md` | SSTI (Jinja2/Mako), Deserialization (pickle/yaml), Eval/Exec sinks, Path/Module injection, Dependency confusion |
| Bug Bounty methodology | `references/bugbounty.md` | Vulnerability Classes and Exploitation Chains, AI-Assisted Techniques |
| Talks (attack surface) | `references/talks.md` | Injection Attacks: An Enduring Threat, Chain Reactions and Amplification, Exploiting Trust and Authentication Mechanisms, Kernel-Level Exploitation and Evasion, Supply Chain Compromise, AI-Driven Vulnerability Discovery and Exploitation, Weaponizing AI Agents and Chatbots, Exploiting Browser and Web Technologies, Arbitrary File Write Escalation in Modern Environments, Exploiting Connected Systems and IoT |

## Web3 honesty note

appsec.fyi **has no dedicated smart-contract / web3 vulnerability class.**
The only web3-adjacent material is tangential and lives inside these classes:
- `supplychain.md` — Web3 C2 infrastructure (smart contracts as botnet C2, dynamic dead-drop)
- `fuzzing.md` — smart-contract fuzzing (Medusa/Echidna mention)
- `deser.md`, `secrets.md`, `recon.md` — occasional `defi`/`blockchain` passing references (mostly "define/defined")
For actual web3 attack classes, use the existing `hunt-*` web3 family + `web3-audit/references/web3-hunt-dispatcher.md`.
