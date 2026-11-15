# Disclosure-Driven Testing Methodology
> How to use public disclosures to find similar bugs on your target

## Concept
Public disclosures reveal PATTERNS. Attackers find the same pattern across targets. Your target likely has the same class of bug.

## Step-by-Step Process

### Phase 1: Recon (5 min)
1. Identify target technology stack (CMS, framework, language, cloud provider)
2. Search disclosure repos for matching tech:
   ```
   # Check HackerOne disclosures for same tech
   curl -sL "https://raw.githubusercontent.com/reddelexc/hackerone-reports/main/data.csv" | grep -i "TARGET_TECH"
   
   # Check CVE databases
   curl -sL "https://api.github.com/search/repositories?q=TARGET_TECH+exploit+2026&sort=updated"
   ```
3. Map disclosure patterns to target attack surface

### Phase 2: Pattern Matching (10 min)
| If target uses... | Check disclosures for... | Test for... |
|-------------------|-------------------------|-------------|
| OAuth/SAML | Auth bypass patterns | Token manipulation, callback hijack |
| GraphQL | Introspection abuse | Hidden queries, batch abuse |
| File upload | Upload race conditions | TOCTOU, extension bypass |
| PDF generation | PDF plugin vulns | SQLi in PDF params, SSRF |
| Redirect handling | SSRF via redirect | Open redirect → SSRF chain |
| JSON processing | Prototype pollution | `__proto__` injection |
| JWT | JWT injection | `kid` SQLi, `none` alg, weak secret |
| WAF/CDN | WAF bypass techniques | Encoding tricks, chunked transfer |

### Phase 3: Targeted Testing (20 min)
1. For each matched pattern:
   - Reproduce the disclosure PoC on target
   - Adapt payload to target's specific implementation
   - Test WAF/CDN bypass if blocked
2. Check for the IPv4 parser bypass:
   ```
   # Test SSRF filters with octal notation
   curl -v "https://target.com/fetch?url=http://0177.0.0.1/"  # octal = 127.0.0.1
   curl -v "https://target.com/fetch?url=http://0x7f.0.0.1/"   # hex = 127.0.0.1
   curl -v "https://target.com/fetch?url=http://127.1/"          # shorthand
   ```
3. Test redirect handling:
   ```
   # Check if target follows redirects to internal IPs
   curl -v "https://target.com/redirect?url=http://169.254.169.254/"
   ```

### Phase 4: Chain & Escalate (10 min)
1. Combine findings for higher severity
2. SSRF → internal service → RCE
3. XSS → cookie theft → account takeover
4. IDOR → admin endpoint → privilege escalation

## Disclosure Sources Quick Access
```
# Load during audit:
read_file('skills/security/exploit-cookbook/references/cve-2026-disclosures.md')
read_file('skills/security/exploit-cookbook/references/hackerone-disclosed-patterns.md')
read_file('skills/security/exploit-cookbook/references/poc-sources-2026.md')
read_file('skills/security/exploit-cookbook/references/bb-writeup-techniques.md')
```
