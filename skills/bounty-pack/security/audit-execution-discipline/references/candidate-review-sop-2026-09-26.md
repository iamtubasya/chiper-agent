# Candidate Review SOP — Implementation Detail (2026-09-26)

User mandate: "Setiap temuan adalah candidate ... minimal 3x cek per candidate,
jgn kerjakan sekaligus, tp satu persatu ... tidak apa2 kalau prosesnya lama."

## Script: review-candidates.py

Location: `~/.chiper/skills/bounty-pack/review-candidates.py`

Usage:
```
python review-candidates.py <target_dir> [--findings findings.json] [--out review-candidates.json]
```
Defaults: reads `findings.json` from target_dir, writes `review-candidates.json`.

Called from orchestrator (`run_review_candidates()`) after validate-findings (0E),
before generate_report (0F). Report source = `ready-candidates.json` (verdict==READY only).

## The 3 Checks (per candidate, one at a time)

### CEK-1 VALID (`cek1_valid`)
Rejects:
- by-design / intended / expected / documented behavior / works as intended
- phishing / social engineering / credential harvest / lure / trick user / email spoof / impersonation
- speculative: "could be", "may be", "possibly", "potential", "might", "recommend",
  "best practice", "consider", "hardening"
- hardening-context ONLY (required pair):
  - `missing|absent|no` + `x-frame-options|hsts|security header`
  - `missing|absent` + `httponly|secure|samesite`

Do NOT blanket-reject on the word "cookie" — XSS payloads legitimately contain `document.cookie`.

### CEK-2 REPRODUCIBLE (`cek2_reproducible`)
Requires:
- evidence file exists on disk (`find_evidence()` maps `source_file` → file, tries
  backslash/forward-slash variants + rglob by name)
- evidence file ≥ 100 bytes
- evidence contains `http/|response|status :? 3-digit` OR payload markers
  (`payload|curl|sqlmap|dalfox|[?&]param=`)

Empty/missing source_file → REJECTED. Correct: can't reproduce = don't report.

### CEK-3 IMPACT (`cek3_impact`)
Impact signals (regex on evidence+text):
- data exposure: ssn|balance|db_password|api_key|secret|token|credential|pii|email|phone
- template injection: `ssti|template injection|{{\*|${7*7}}` (added 2026-09-26 — was missing, caused false REJECT of real SSTI)
- privilege: admin|role|privilege|isadmin|escalat
- account takeover: account takeover|ato|password reset|session
- code exec: sql injection|sqli|rce|code exec|command injection
- ssrf: ssrf|server side request
- financial: balance|funds|withdraw|transfer|order|price|payment
- xss: `<script|xss|alert(|onerror=`

Also extracts up to 6 actionable step lines (curl/GET/POST/http/payload/`?param=`) from evidence.
Both impact signal AND steps required → else REJECT.

## Output schemas

`review-candidates.json` per candidate:
```json
{
  "title": "...", "severity": "high", "source_file": "variants\\ssti.txt",
  "cek1_valid": true, "why1": "valid signal",
  "cek2_reproducible": true, "why2": "evidence di disk + status/payload tercatat",
  "cek3_impact": true, "why3": "impact nyata + step-by-step tersedia",
  "impacts": ["template injection (ssti)"],
  "steps": ["[200] http://localhost:4310/search?q=%3C%3Fxml..."],
  "verdict": "READY", "rationale": "PASS cek1+cek2+cek3",
  "reviewed_at": "..."
}
```
`review-candidates.md` — same content human-readable, sorted low→high, with `## READY (lolos 3x cek): N` footer.

## Orchestrator wiring
- `run_review_candidates()` (new method) — subprocess call, timeout 1800, reads
  review-candidates.json, counts READY, raises RuntimeError (BLOCK report) if it failed.
- `_get_ready_candidates()` — loads review-candidates.json, returns verdict==READY list.
- `generate_report()` — first writes `ready-candidates.json`, then proceeds.

## Test evidence (2026-09-26, vulnerable express app on :4310)
- 20-candidate sample: 12 READY (real bugs: IDOR sqli nosqli xxe ssti xss-dom/reflected/stored
  ssrf open-redirect business-logic waf-bypass) + 8 REJECTED (no evidence file → not reproducible).
- XSS dom/reflected/stored wrongly rejected first (evidence mentions "cookie" via document.cookie payloads)
  → fixed CEK-1 to context-sensitive rejection only.
- SSTI wrongly rejected at CEK-3 (no impact keyword) → added ssti/template-injection pattern.