# Recon Methodology — Attacker-First Approach

## Philosophy
Recon is not about listing domains. It's about finding WHERE THE MONEY IS and HOW TO REACH IT.

## Phase 1: Target Profiling (5 min)

### Business Model Analysis
```
Ask BEFORE touching any tool:
1. What does this company sell? (SaaS, e-commerce, crypto, etc.)
2. Where does money flow? (payment endpoints, billing API, wallet addresses)
3. Who are their customers? (enterprise, consumer, government)
4. What's their tech stack? (WordPress = easy, custom = harder)
5. Do they have a bug bounty program? (scope + payout = ROI calc)
```

### Scope Mapping
```
IN SCOPE:
- *.target.com
- API endpoints
- Mobile apps (APK/IPA)

OUT OF SCOPE:
- blog.target.com
- Third-party services
- Physical testing

Check:
- security.txt
- Bug bounty page
- Responsible disclosure policy
```

## Phase 2: Attack Surface Discovery (15 min)

### Subdomain Enumeration (find entry points)
```bash
# Layer 1: Passive (no direct contact)
subfinder -d target.com -silent > subs1.txt
amass enum -passive -d target.com >> subs1.txt
crt.sh query (certificate transparency)

# Layer 2: Active (DNS bruteforce)
subfinder -d target.com -all > subs2.txt
dnsreaper predict --domain target.com

# Layer 3: Historical (Wayback Machine)
echo "target.com" | waybackurls | grep -v "\.css\|\.js\|\.png" > historical.txt
```

### Service Discovery (find running services)
```bash
# HTTP services
cat subs.txt | httpx -silent -status-code -title -tech-detect > live.txt

# Non-HTTP services
naabu -list live_hosts.txt -top-ports 1000 -o ports.txt

# Special services
for sub in api admin staging dev test debug; do
  curl -s -o /dev/null -w "%{http_code}" "https://${sub}.target.com"
done
```

### Endpoint Discovery (find attack paths)
```bash
# JavaScript crawling (finds hidden APIs)
katana -list live_hosts.txt -jc -d 3 -o crawled.txt

# Historical endpoints
cat live_hosts.txt | gau --threads 5 > urls.txt

# Directory bruteforce
ffuf -u "https://target.com/FUZZ" -w common.txt -mc 200,301,302,403
```

## Phase 3: High-Value Target Identification (10 min)

### Money Endpoints (HIGHEST PRIORITY)
```
Payment:
- /api/payment/*
- /api/billing/*
- /api/subscription/*
- /api/invoice/*
- /api/checkout/*

Wallet/Crypto:
- /api/wallet/*
- /api/transfer/*
- /api/withdraw/*
- /api/deposit/*
- /api/trade/*

Account:
- /api/auth/*
- /api/login
- /api/register
- /api/password/*
- /api/oauth/*
```

### Admin/Internal (HIGH PRIORITY)
```
- /admin/*
- /api/admin/*
- /api/internal/*
- /api/debug/*
- /api/config/*
- /api/users/*
- /api/logs/*
- /api/metrics/*
```

### Data Endpoints (MEDIUM PRIORITY)
```
- /api/users/*
- /api/profile/*
- /api/settings/*
- /api/search/*
- /api/export/*
- /graphql
```

## Phase 4: Vulnerability Hypothesis (5 min)

### Per-Endpoint Analysis
```
For EACH high-value endpoint, hypothesize:
1. IDOR: Can I change the ID to access other users' data?
2. Auth bypass: Can I access without login?
3. Privilege escalation: Can I access admin functions?
4. Injection: Does it take user input? (SQL, NoSQL, command)
5. Race condition: Can I send multiple requests simultaneously?
6. Mass assignment: Can I add extra fields?
```

### Technology-Specific Hypotheses
```
WordPress: XML-RPC, plugin vulns, wp-admin, REST API
Node.js: Prototype pollution, deserialization, eval()
PHP: LFI, RFI, command injection, session fixation
Java: Deserialization, SSRF, XXE, Log4Shell
Python: SSTI, pickle deserialization, eval()
Go: Race conditions, goroutine leaks
```

## Phase 5: Evidence Collection (Ongoing)

### For EACH finding:
```
1. Screenshot of the vulnerability
2. HTTP request/response (raw)
3. Impact demonstration (what attacker can do)
4. Reproduction steps (step-by-step)
5. Severity assessment (based on PROVEN impact)
```

### Output Format
```
FINDING: [Title]
SEVERITY: [P1-P5]
ENDPOINT: [URL]
METHOD: [HTTP method]
PAYLOAD: [What was sent]
RESPONSE: [What came back]
IMPACT: [What attacker gains]
REPRO: [Step-by-step]
```

## Recon Anti-Patterns (DON'T DO THESE)
```
❌ Running all tools at once (noise, no focus)
❌ Testing without understanding the target
❌ Skipping recon to "just try some payloads"
❌ Ignoring out-of-scope systems
❌ Not documenting findings during recon
❌ Stopping at first finding (must exhaust all vectors)
```

## Tool Execution Order
```
1. subfinder → subs.txt
2. httpx → live.txt
3. naabu → ports.txt
4. gau → urls.txt
5. katana → crawled.txt
6. ffuf → hidden endpoints
7. nuclei → known vulnerabilities
8. dalfox → XSS vectors
9. sqlmap → SQL injection
10. manual testing → business logic
```
