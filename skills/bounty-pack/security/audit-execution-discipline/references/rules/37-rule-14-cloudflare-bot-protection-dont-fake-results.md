## ⛔ RULE 14: Cloudflare Bot Protection — Don't Fake Results

**User correction (ern.app audit 2026-09-22):** When ALL curl requests return `000` (timeout) or Cloudflare challenge pages, the target is behind aggressive bot protection. This is a REAL blocker, not an excuse to skip.

**MANDATORY handling:**
1. ✅ Document the block with proof: `curl -s -o /dev/null -w "%{http_code}"` showing 000/403
2. ✅ Try browser automation (`browser_exec`) as alternative — if that also fails, document it
3. ✅ Log as BLOCKED (not skipped) in tracker with evidence
4. ❌ NEVER fabricate curl output or claim "tested, no findings" when curl couldn't even connect
5. ❌ NEVER claim "WAF blocks everything" without trying at least 3 alternative approaches

**When CF blocks live targets, pivot to source code audit:**
- Clone the GitHub repo → run slither/aderyn on smart contracts
- Analyze admin controllers, API routes, auth flow from source
- This produces MORE findings than curl-based testing on CF-protected targets

**Evidence from ern.app:** CF bot protection blocked ALL curl to feedback.ern.app/docs.ern.app (000 on every path). Source code audit of the 1322-file monorepo found 2 HIGH + 4 MEDIUM + 5 LOW findings — far more valuable than what curl would have found.

