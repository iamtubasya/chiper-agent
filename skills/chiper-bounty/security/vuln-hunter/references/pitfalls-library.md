# Pitfalls Library — Common Audit Mistakes & How to Avoid Them

## Overclaiming Patterns (DON'T DO)
```
❌ "Critical RCE" → command injection is blocked
❌ "Account Takeover" → only read access, no write
❌ "Full data exfiltration" → only 1 field accessible
❌ "Privilege escalation" → only see role, can't change
❌ "SQL injection" → only boolean blind, no data extract
❌ "SSRF" → only internal scan, no data exfil
❌ "Business logic flaw" → only quantity 1-2 manipulation
❌ "Mass assignment" → only add empty field
❌ "Authentication bypass" → only bypass rate limit
❌ "Session fixation" → only fix own session
```

## False Positive Triggers
```
- CORS without credentials → NOT exploitable for token theft
- Self-XSS → only affects the user who finds it
- Clickjacking on non-sensitive pages → no impact
- Missing headers → informational only
- Version disclosure → no known CVE
- robots.txt disclosure → by design
- Open redirect without chaining → P4 max
```

## Context Budget Pitfalls
```
- Loading all skills at once → context overflow → compression → lose rules
- Running nuclei in foreground → blocks other work for hours
- Not writing output to FILE → context fills with tool output
- Forgetting to evict skills between phases → redundant context usage
- Reloading skills "to check" → wastes context budget
```

## Common Testing Mistakes
```
- Testing CORS before vectors 1-13 → pipeline violation
- Spending >5 min on account creation → loop block
- Running sqlmap without authentication → usually blocked by WAF
- Not testing on ALL subdomains → miss findings on api2.target.com
- Ignoring rate limiting → get banned, can't continue
- Not checking Content-Type on SPA → false positives from 200 status
```

## Report Writing Mistakes
```
- Claiming severity without proven chain → overclaim
- Submitting partial report → must include ALL findings
- Not including Steps to Reproduce → rejected
- Missing impact demonstration → informational, no bounty
- Wrong VRT mapping → wrong severity, delayed payout
```

## Anti-Patterns for DeFi/Web3
```
- Claiming CRITICAL on dormant contract → INFORMATIONAL
- Not checking on-chain balance before severity claim
- Assuming "on-chain" means decentralized → could be CEX API
- Not verifying upgrade authority type (EOA vs multisig)
- Claiming flash loan attack without cost analysis
```
