# Vulnerability Methodology — From Finding to Exploit

## 5-Step Exploit Development

### Step 1: Identify Vulnerability Class
```
Ask: What TYPE of bug is this?
- Injection (SQL, NoSQL, Command, Template)
- Broken Auth (bypass, escalation, session)
- Sensitive Data Exposure
- XXE / SSRF
- Broken Access Control (IDOR, BOLA)
- Security Misconfiguration
- XSS (Reflected, Stored, DOM)
- Insecure Deserialization
- Using Components with Known Vulnerabilities
- Insufficient Logging
```

### Step 2: Determine Entry Point
```
Ask: WHERE does attacker input enter the system?
- URL parameters
- POST body (JSON, form, XML)
- HTTP headers (Cookie, Authorization, X-Forwarded-For)
- File uploads
- WebSocket messages
- API keys in JS bundles
- Subdomain DNS records
```

### Step 3: Test Exploitation
```
Ask: Can I actually exploit this?
- Minimum: demonstrate the vulnerability exists
- Better: show impact (data access, fund loss)
- Best: full exploit chain with PoC

Test method:
1. Craft minimal payload
2. Send to target
3. Observe response
4. If blocked → try bypass techniques
5. If works → document exact steps
```

### Step 4: Assess Impact
```
Ask: What can attacker DO with this?
- Read other users' data? → P2
- Modify other users' data? → P1
- Take over accounts? → P1
- Execute code on server? → P1
- Steal funds? → P1
- Just see errors? → P4
```

### Step 5: Chain for Severity
```
Ask: Can I combine this with other findings?
- CORS + CSRF → Account takeover = P1
- XSS + Cookie theft → Session hijack = P2
- IDOR + Write access → Data tampering = P1
- SSRF + Internal service → RCE = P1
- Open redirect + OAuth → Token theft = P1
```

## PoC Template
```
TITLE: [Vulnerability Type] in [Endpoint]
SEVERITY: P[1-5]
ENDPOINT: [URL]
METHOD: [HTTP Method]

STEPS TO REPRODUCE:
1. [Step 1]
2. [Step 2]
3. [Step 3]

EXPECTED: [What should happen]
ACTUAL: [What actually happens]

IMPACT: [What attacker gains]
```
