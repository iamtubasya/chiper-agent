## ⛔ RULE 3: Timeout = Retry, Not Skip

Tool timeout MUST use 4-method retry chain before skip:
1. Run as-is with 2x timeout
2. Background + timeout 2x + rate limit
3. Subset (critical,high only)
4. Lightweight alternative
Skip ONLY after all 4 methods documented.

