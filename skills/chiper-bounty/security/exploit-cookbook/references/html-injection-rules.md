# HTML Injection Submission Rules — STRICT

## ⛔ OUT OF SCOPE (REJECT IMMEDIATELY)
- Reports suggesting "could lead to" or "has the potential to cause" impact
- Basic HTML payloads with no demonstrated exploit:
  - `<h1>Test</h1>`
  - `<form action="https://evil.com">`
  - `<a href="https://target.com">test</a>`
  - `<img src=x onerror=alert(1)>` (without proven context)

## ✅ IN SCOPE (MANDATORY)
- Complete PoC demonstrating the FULL attack chain
- HTML injection MUST chain to XSS or real data exfil
- Proven impact: cookie theft, credential harvesting, session hijack

## Valid Finding Format
```
1. Inject point: [field/URL param]
2. Payload: [actual payload that fires in browser]
3. Impact: [what attacker achieves — cookie steal, redirect to phishing, etc.]
4. PoC: [curl command OR steps to reproduce]
5. Screenshot/Video: showing payload executing in target's browser
```

## If HTML → XSS Bypass
- Test DOMPurify version → apply version-specific bypass
- Test CSP headers → find bypass or missing policy
- Test input sanitization → try mutation XSS (mXSS)
- Test context → attribute, tag, event handler variations
- If NO XSS possible → HTML injection alone = likely OUT OF SCOPE

## Severity Guide
| Scenario | Severity | Verdict |
|----------|----------|---------|
| HTML only, no XSS chain | Out of scope | REJECT |
| HTML → XSS (self-XSS) | Low | SUBMIT with PoC |
| HTML → XSS (stored, other users) | High | SUBMIT |
| HTML → credential phishing form | Medium | SUBMIT with real PoC |
| HTML → open redirect to evil.com | Medium | SUBMIT |
| HTML → JS execution via on* handlers | High | SUBMIT |
| HTML → CSP bypass + script load | Critical | SUBMIT |

## Key Principle
> "Demonstrate REAL security risk and impact. Not potential. Not theoretical. PROVE IT."
