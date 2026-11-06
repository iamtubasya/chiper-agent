# Reference: AI-Powered Pentest Agents

> AI agents that automate recon → analysis → exploitation → reporting.
> Source: Shannon (Keygraph), Dark-Moon (ASCIT31), PentestGPT (GreyDGL), bbot (BLS).

---

## Agent Comparison Matrix

| Agent | Stars | Mode | Source Code | Live Exploit | Autonomy | Best Target |
|---|---|---|---|---|---|---|
| **Shannon** | 4k+ | White+Black box | ✅ Read source | ✅ Real PoC | Full | Web apps with source |
| **Dark-Moon** | 859 | Full-stack | ✅ | ✅ | Full | Cloud, AD, K8s, IoT |
| **PentestGPT** | 4k+ | Multi-stage | ✅ | ✅ | Full | CTF + pentest |
| **bbot** | 5k+ | Recon+Spider | ❌ | Partial | Semi | Asset discovery |

---

## Shannon (KeygraphHQ/shannon)

### Architecture
```
Pre-Recon (source scan) → Recon (attack surface) →
Parallel Vuln Agents [Injection, XSS, SSRF, Auth, ...] →
Exploit (real PoC) → Report (proof-by-exploitation)
```

### Key Concepts
- **Proof-by-exploitation**: Only reports findings with working PoC
- **White-box**: Source code analysis guides dynamic testing
- **Authenticated testing**: Config for login flows, 2FA, TOTP
- **OWASP-focused**: Injection, XSS, SSRF, Broken Auth, Broken AuthZ
- **Resumable workspaces**: Can resume interrupted scans

### Run Command
```bash
npx @keygraph/shannon setup          # configure
npx @keygraph/shannon start -u URL -r /path/to/repo
```

### Provider Support
Anthropic, OpenAI, xAI, AWS Bedrock, custom endpoints (Ollama, vLLM, LM Studio)

### Report Sample Targets
- OWASP Juice Shop: 20+ vulns (auth bypass, SQLi, IDOR, SSRF)
- c{api}tal API: 15 critical/high (command injection, auth bypass, mass assignment)
- OWASP crAPI: 15+ critical/high (JWT, injection, SSRF, API authZ)

---

## Dark-Moon (ASCIT31/Dark-Moon)

### Scope
Web, Cloud (AWS/GCP/Azure), Identity/AD, CI/CD, IaC, Databases, Kubernetes, IoT firmware

### Key Features
- **80+ tools orchestrated via MCP**
- **Privacy gateway**: LLM never sees real IPs/hosts/creds
- **Agentic reasoning** + real exploit execution
- **Proof-based vulnerabilities**

### Architecture
MCP-based tool orchestration → LLM reasoning → exploit execution → proof generation

---

## PentestGPT (GreyDGL/PentestGPT)

### Modes
1. **CTF mode**: recon → exploit → walkthrough
2. **Pentest mode**: asset discovery → vulnerability identification → report

### Pipeline
Multi-stage: each stage feeds findings into the next

### Backends
Claude Code CLI, Codex CLI

### Command
```bash
pentestgpt --target IP --mode pentest --instruction "focus on X"
```

---

## bbot (blacklanternsecurity/bbot)

### Why bbot?
- Finds 20-50% more subdomains than any other tool
- Recursive internet scanner with modules
- Presets: subdomain-enum, spider, email-enum, web, web-heavy

### Key Presets
```bash
bbot -t domain.com -p subdomain-enum    # subdomains
bbot -t domain.com -p spider            # web crawl
bbot -t domain.com -p email-enum        # emails
bbot -t domain.com -p web               # light scan
bbot -t domain.com -p web-heavy         # aggressive scan
```

### Module System
Python-based modules: dns, http, ssl, social, etc.
Custom modules via YAML config.

---

## When to Use What

| Scenario | Agent |
|---|---|
| Have source code + want exploit proof | **Shannon** |
| Full infrastructure audit (cloud+AD+K8s) | **Dark-Moon** |
| CTF challenge solving | **PentestGPT** |
| Fast subdomain + asset discovery | **bbot** |
| No source code, web-only | **bbot + nuclei** |
| Smart contract | **Foundry + Slither + Mythril + Echidna** |

---

## Integration with IRONCLAW Pipeline

```
Phase 1: bbot → subdomain + spider + assets
Phase 2: nuclei → template scan
Phase 3: Shannon/Dark-Moon → AI exploitation (if source available)
Phase 4: Manual verification + PoC
Phase 5: Report
```
