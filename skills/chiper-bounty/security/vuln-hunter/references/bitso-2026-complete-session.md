# Bitso 2026 Complete Session — Exhausted Target Case Study

## Target Profile
```
Platform: Bitso (crypto exchange, Mexico-based)
Program: Bugcrowd (private)
Scope: Web application, API, mobile app
Auth: Email + password + 2FA
Test accounts: 1 available
```

## Recon Results
```
Subdomains: 50+ found
Live hosts: 30+ confirmed
API endpoints: 100+ discovered
Tech stack: React, Node.js, PostgreSQL
WAF: Cloudflare
```

## Testing Results (30 vectors)

| Vector | Result | Notes |
|--------|--------|-------|
| IDOR/BOLA | BLOCKED | Needs 2 accounts, only 1 available |
| Auth bypass | NEGATIVE | Strong auth, no bypass found |
| Privilege escalation | NEGATIVE | Role checks enforced |
| RCE/SSRF | NEGATIVE | No URL-accepting endpoints |
| SQLi | NEGATIVE | Parameterized queries |
| Race condition | NEGATIVE | Proper locking |
| Business logic | NEGATIVE | Price/quantity manipulation blocked |
| Mass assignment | NEGATIVE | Whitelist validation |
| Info disclosure | LOW | Version in headers, stack traces |
| XSS reflected | NEGATIVE | Output encoding |
| XSS stored | NEGATIVE | Input sanitization |
| XSS DOM | NEGATIVE | No dangerous sinks |
| GraphQL | N/A | No GraphQL endpoint |
| CORS | NEGATIVE | Properly configured |
| CSRF | NEGATIVE | Token-based protection |
| File upload | N/A | No upload endpoint |
| Cache poisoning | NEGATIVE | Proper cache headers |
| 403 bypass | NEGATIVE | All paths protected |
| Password reset | NEGATIVE | Token-based, no predictability |
| Open redirect | NEGATIVE | No redirect endpoints |
| WebSocket | N/A | No WebSocket endpoint |
| API versioning | NEGATIVE | Only one version |
| Rate limiting | NEGATIVE | Proper rate limiting |
| Third-party | LOW | Analytics endpoints exposed |
| Source maps | NEGATIVE | No source maps found |
| Template injection | NEGATIVE | No template engine |
| Command injection | NEGATIVE | No OS commands |
| XXE | NEGATIVE | JSON-only API |
| Subdomain takeover | NEGATIVE | All CNAMEs verified |
| HTTP smuggling | NEGATIVE | Proper parsing |

## Finding Gate Results
```
73 candidates → 4 REPORT / 65 DOWNGRADE / 4 DROP
All REPORT findings = informational, no bounty
Conclusion: Exhausted — no bounty-worthy findings
```

## Lessons Learned
```
1. Well-hardened targets exist — respect the engineering
2. Account limitation = P3 ceiling for auth-dependent vectors
3. Cloudflare WAF blocks most automated testing
4. 1 test account = cannot test IDOR (needs 2)
5. Recon-only findings (version, headers) = no bounty
6. Exhausted ≠ "tried one tool and gave up"
7. Document EVERYTHING — honest report > padded report
```
