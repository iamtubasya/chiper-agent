## ⛔ RULE 25: References MUST Be USED — Not Just Loaded (C6)

**User correction (2026-09-26): "Ini semua Pipeline dan file, bukan cm d load dan dbaca aja ya, tapi pakai secara maksimal, termasuk all tools, jgn hanya curl aja"**

Loading/reading reference files is NOT enough — the pipeline must make real requests from them. Lesson learned: `load_all_references()` wrote `references-index.json` (88 refs, ~3,884 clues) but NOTHING read that index → it was a dead dump. The user caught this.

**The contract (enforced by Gate CHECK 10):**
1. `force-full-execution.py` → `load_all_references()`: reads ALL 88 refs' CONTENT (not just existence), extracts attack clues (endpoint/header/payload lines), writes `references-index.json`.
2. `execute-references.py` (C6, called by orchestrator after C5): reads `references-index.json`, classifies each clue:
   - `HEADER_ATTACK` → real request with special headers (X-Forwarded-For, X-Original-URL, Host, CRLF)
   - `ENDPOINT_PROBE` → GET/POST to extracted path (strip foreign host: `https://target.com/admin` → `root + /admin`, NOT `//target.com/admin`)
   - `PAYLOAD_INJECT` → inject payload into target param via urllib
   - Fires to target with rate limit + timeout 120s → `references-evidence/clue-NNNN.txt` + `reference-usage.json`
3. `verify-tool-usage.py` **CHECK 10**: `reference-usage.json` must exist, non-empty, ≥30% evidence files on disk. Missing → Gate FAIL → rework runs execute-references.py → HARD BLOCK if still missing.

**Pitfalls:**
- A clues file that is ONLY written and never read is a dead dump — same class of bug as dual-runner drift. Audit who READS each artifact.
- Refs are guides, not payloads: from ~60 classified clues only ~16-20 produce executable requests (methods/pseudocode don't fire). That's normal; what matters is the actionable ones are fired with real evidence.
- Full URLs in clues must be reduced to their PATH against the target root.

**Script:** `execute-references.py` (Global scripts dir). Gate CHECK 10 = "refs used, not just read".

