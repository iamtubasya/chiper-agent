## ⛔ RULE 0C: Impact-First — Not Volume

**The goal is NOT to find 30 bugs. The goal is to find 1 BUG that matters.**

When auditing:
1. FIRST understand the app flow (read JS bundles, API, auth model)
2. THEN ask: "Where is the money? Where is the user data?"
3. THEN test specifically those areas with deep exploits
4. THEN chain findings for maximum impact
5. THEN report only with proof of impact (data, funds, accounts)

**Do NOT:** Run 30 generic scans → report everything → hope something sticks
**DO:** Understand target → targeted deep test → chain → report with impact proof

**DO NOT report:**
- By-design features (CORS *, server headers, informational)
- Findings without chain analysis (XSS alone ≠ bug, XSS + CSRF = takeover)
- "Zero findings" without proving app is actually secure

**DO report:**
- IDOR → data access proof
- Business logic → price/transfer manipulation proof
- Auth bypass → account takeover proof
- Race condition → double-spend proof

