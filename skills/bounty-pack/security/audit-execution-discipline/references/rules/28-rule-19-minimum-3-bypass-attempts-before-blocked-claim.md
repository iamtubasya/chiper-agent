## ⛔ RULE 19: Minimum 3 Bypass Attempts Before "Blocked" Claim

Before declaring any attack vector "blocked by WAF":
1. Try the direct payload
2. Try with encoding bypass (URL encode, double encode, Unicode)
3. Try with protocol trick (Content-Type switch, chunked, HTTP method change)
4. Try with path manipulation (normalization, backslash, semicolon)
5. Try with header manipulation (Host, X-Forwarded-For, True-Client-IP)

If ALL 5 fail → THEN you may claim "blocked" — but document each attempt.

