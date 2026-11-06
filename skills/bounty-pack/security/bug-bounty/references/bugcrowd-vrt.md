# Bugcrowd Vulnerability Rating Taxonomy (VRT) — Quick Reference

## Severity Levels
```
P1 Critical   → Full account takeover, RCE, SQL injection, authentication bypass
P2 High       → IDOR with sensitive data, SSRF with internal access, stored XSS
P3 Medium     → CSRF with impact, open redirect with chaining, reflected XSS
P4 Low        → Missing security headers, verbose errors, info disclosure
P5 Informational → Best practice violations, version disclosure, clickjacking
```

## Top Payout Classes (Focus Here First)

### P1 Critical (>$5,000)
- Authentication bypass
- Remote code execution
- SQL injection with data access
- Full account takeover
- Cryptographic private key exposure
- Business logic allowing fund theft

### P2 High ($1,000-$5,000)
- IDOR with sensitive data exposure
- SSRF leading to internal service access
- Stored XSS with session hijacking
- CSRF on sensitive actions (password change, email change)
- Path traversal with file read
- Insecure direct object reference on financial data

### P3 Medium ($500-$1,000)
- Open redirect with chaining potential
- Reflected XSS
- CSRF with limited impact
- Missing rate limiting on sensitive endpoints
- Business logic flaws (quantity manipulation, price bypass)
- Information disclosure (API keys, internal IPs)

### P4 Low ($200-$500)
- Missing security headers (CSP, HSTS, X-Frame-Options)
- Verbose error messages
- Version disclosure
- Cookie without Secure/HttpOnly flags
- SSL/TLS weak configuration

### P5 Informational (<$200)
- Clickjacking (no chaining)
- Open redirect (no chaining)
- Self-XSS
- Missing CSRF token (no impact)
-robots.txt disclosure

## Severity Escalation Chains
```
CORS misconfig → CSRF → Account takeover = P1
Open redirect → OAuth token theft → Account takeover = P1
IDOR (read) → IDOR (write) → Data tampering = P2
Reflected XSS → Cookie theft → Session hijack = P2
SSRF → Cloud metadata → Credential theft = P1
Business logic → Price manipulation → Fund loss = P1
```

## Common False Positives (Don't Report These)
```
- CORS without credentials (can't steal tokens)
- Self-XSS (only affects the user who finds it)
- Clickjacking on non-sensitive pages
- Missing headers on error pages
- Version disclosure without known CVE
- robots.txt revealing paths (by design)
- SSL certificate issues on non-production
```

## VRT Categories (Simplified)
```
P1: Authentication, Authorization, RCE, SQLi, Crypto
P2: IDOR, SSRF, Stored XSS, CSRF, Path Traversal
P3: Reflected XSS, Open Redirect, Business Logic, Rate Limiting
P4: Headers, Cookies, SSL, Information Disclosure
P5: Clickjacking, Self-XSS, Best Practices
```

## Program-Specific Notes
- Always check program's scope BEFORE testing
- Some programs exclude specific vuln classes
- Some programs have custom severity overrides
- Check "safe harbor" language for legal protection
- Follow program's disclosure timeline

## Severity Calibration Checklist
Before assigning severity, ask:
1. Can this be exploited WITHOUT chaining? (If no → lower severity)
2. Does it affect OTHER users? (If no → lower severity)
3. Is the data SENSITIVE? (If no → lower severity)
4. Is there a PROVEN attack chain? (If no → informational)
5. Would a triager accept this as the claimed severity?
