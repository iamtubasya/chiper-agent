# Reference Loader — On-Demand Reference File Loading

## Purpose
Load reference files ON-DEMAND during testing, not all at once. This prevents context overflow.

## Loading Rules
```
1. Load ONLY the reference for the CURRENT vector being tested
2. After reading, apply the technique to the target
3. Move to next vector, load its reference
4. NEVER load all references at once
5. NEVER reload a reference "to check" — use read_file instead
```

## Per-Vector Reference Map
```
Vector 1 (IDOR):     → hackskill-idor-broken-object-authorization.md
Vector 2 (Auth):     → hackskill-authbypass-authentication-flaws.md + jwt-attack-payloads.txt
Vector 3 (PrivEsc):  → hackskill-authbypass-authentication-flaws.md
Vector 4 (SSRF):     → hackskill-ssrf-server-side-request-forgery.md + ssrf-payloads.txt
Vector 5 (SQLi):     → hackskill-sqli-sql-injection.md + sqli-auth-bypass-payloads.txt
Vector 6 (Race):     → hackskill-race-condition.md
Vector 7 (BizLogic): → hackskill-business-logic-vulnerabilities.md
Vector 8 (MassAss):  → hackskill-idor-broken-object-authorization.md
Vector 9 (InfoDisc): → proven-exploits.md + sensitive-files-wordlist.txt
Vector 10 (XSS):     → hackskill-xss-cross-site-scripting.md + xss-payloads.txt
Vector 11 (XSS):     → hackskill-xss-cross-site-scripting.md + xss-payloads.txt
Vector 12 (DOM XSS): → hackskill-xss-cross-site-scripting.md
Vector 13 (GraphQL): → hackskill-graphql-and-hidden-parameters.md + graphql-payloads.txt
Vector 14 (CORS):    → hackskill-cors-cross-origin-misconfiguration.md
Vector 15 (CSRF):    → hackskill-csrf-cross-site-request-forgery.md
Vector 16 (Upload):  → proven-exploits.md
Vector 17 (Cache):   → hackskill-web-cache-deception.md
Vector 18 (403):     → hackskill-401-403-bypass-techniques.md
Vector 19 (Reset):   → hackskill-oauth-oidc-misconfiguration.md
Vector 20 (Redirect):→ hackskill-open-redirect.md
Vector 21 (WS):      → hackskill-graphql-and-hidden-parameters.md
Vector 22 (API ver): → proven-exploits.md
Vector 23 (Rate):    → hackskill-business-logic-vulnerabilities.md
Vector 24 (3rd):     → proven-exploits.md
Vector 25 (JS):      → proven-exploits.md
Vector 26 (SSTI):    → hackskill-ssti-server-side-template-injection.md
Vector 27 (CMDi):    → hackskill-cmdi-command-injection.md + cmdi-payloads.txt
Vector 28 (XXE):     → hackskill-xxe-xml-external-entity.md
Vector 29 (Takeover):→ hackskill-subdomain-takeover.md
Vector 30 (Smuggle): → hackskill-request-smuggling.md
```

## Loading Pattern
```python
# PSEUDO — load reference before testing
ref_file = get_ref_for_vector(vector_name)
read_file(f"exploit-cookbook/references/{ref_file}")
# Now test the vector using the loaded reference
test_vector(target, vector_name)
```
