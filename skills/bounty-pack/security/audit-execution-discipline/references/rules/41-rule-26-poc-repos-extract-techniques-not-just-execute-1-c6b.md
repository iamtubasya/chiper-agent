## ⛔ RULE 26: PoC Repos → Extract TECHNIQUES, Not Just Execute 1% (C6b)

**User correction (2026-09-26): "Bagaimana dgn POC varian attack yg udh ad? Ribuan file itu, udh kamu jadikan sumber cara attack exploit blm?"**

Executing matched PoC repos by NAME uses only ~1% of the library: 2,223 repos, 70% are CVE-specific (require identical product/version, never match a generic target), old name-matching + cap 25-50 left 26 repos `PLANNED_BEYOND_CAP` and only ~21 actually executed. The user called this out. The fix is NOT to execute all 2,223 — it's to EXTRACT the attack techniques from ALL of them and fire those at any target.

**The technique-extraction pattern (proven on 2,223 repos → 3,014 unique techniques):**

1. `poc-techniques-index.py` (build once, ~8 min for 2,223 repos): scan EVERY repo's file content (.py/.sh/.md/.txt/.php), extract per file (cap 120 files/repo, 30KB/file):
   - `ENDPOINT` — URL/path with params (classify into sqli/xss/xxe/lfi/ssrf/ssti/cmdi/auth/upload/admin-config/generic)
   - `CURL_TEMPLATE` — `curl ...` command lines (with `-X METHOD`, `-H header`)
   - Dedupe by (type, endpoint|curl) → `poc-techniques-index.json` (3,014 unique)
2. `execute-poc-techniques.py` (C6b, called by orchestrator after C6 refs):
   - Read index → fire technique to target root (relativize endpoints: keep path only)
   - Apply method/headers from curl template → real request via urllib (never shell curl)
   - Rate-limit 0.3s, timeout 120s → `poc-techniques-evidence/tech-NNNN.txt` + `poc-techniques-usage.json`
3. **GATE CHECK 11**: `poc-techniques-usage.json` must exist, non-empty, ≥30% evidence on-disk → else HARD BLOCK.

**Pitfalls:**
- Don't judge the repo library by "how many repos I executed" — judge by "how many TECHNIQUES I extracted and fired". 3,014 unique techniques from 2,223 repos is the real coverage number.
- CVE-specific repos DO contribute: their exploit.py/README contains endpoint+payload patterns reusable on other targets.
- Fire cap per run (~150-300) is fine — the index persists; more techniques = more coverage each run.
- Keep caps growing: track-poc MAX_EXEC 25→50, execute-poc-variants cap 50→100.

**Scripts:** `poc-techniques-index.py` (build) + `execute-poc-techniques.py` (fire). Gate CHECK 11 enforces usage.

**Cap updates (2026-09-26):** track-poc `MAX_EXEC = 150` (was 25→50), execute-poc-variants `matched_names[:150]` (was 50→100). Cap = max repos EXECUTED/extracted per audit to bound runtime — NOT a limit on which repos contribute techniques (the technique index always scans ALL 2,223).

