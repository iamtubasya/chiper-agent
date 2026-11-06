## ⛔ RULE 24: Candidate Review SOP — Temuan = CANDIDATE, 3x Cek, Low→High, Satu-Persatu (MANDATORY)

**User correction (2026-09-26): "Setiap temuan adalah candidate, dan candidate di list setelah semua proses dan tools selesai, setelah dilist, kamu cek kembali mulai dari severity plg rendah sampai tertinggi, apakah temuan candidate tersebut valid, bisa diduplikasi, menimbulkan impact apa, dan step by step yg jelas, minimal 3x cek per candidate, jgn kerjakan sekaligus, tp satu persatu Candidate, tidak apa2 kalau proses nya lama, yg pngt dilakukan secara hati2"**

Every finding is a CANDIDATE. Nothing is a finding until it survives review. The reviewer runs `scripts/review-candidates.py`:

1. **LIST** — all candidates AFTER every tool/phase is done (input = findings.json).
2. **SORT** — severity lowest → highest (Low → Medium → High → Critical). Review order is deliberate.
3. **PER CANDIDATE, ONE AT A TIME, 3x CHECK**:
   - **CEK-1 VALID**: benar bug? Reject by-design / intended-behavior / phishing-social / speculative-info ("could be/may be/missing header/cookie-flags-harding").
   - **CEK-2 REPRODUCIBLE**: evidence file on-disk ≥100B + status HTTP / payload / tool output tercatat. No evidence file = REJECT ("tidak ada evidence di disk").
   - **CEK-3 IMPACT**: impact nyata (data/dana/user/sistem: ssn/balance/admin/ssrf/sqli/xss/ssti/etc) + step-by-step yang jelas. No impact signal or no steps = REJECT.
4. **ONLY candidates that pass ALL 3 checks → verdict READY → masuk ready-candidates.json → report 0F.**

Outputs: `review-candidates.json` (per-candidate cek1/cek2/cek3 + why + verdict + rationale), `review-candidates.md` (human-readable low→high).

**Wiring:** orchestrator 0E → `run_review_candidates()` → 0F `generate_report()` reads ready-candidates.json. If review-candidates fails/never runs → report BLOCKED.

**Pitfalls fixed in dev (2026-09-26):**
- CEK-1 "cookie" blanket-reject was WRONG — payload XSS legitimately contains `document.cookie`. Use context: only reject "missing/absent cookie flags" / "missing security header" patterns, not bare keyword "cookie".
- CEK-3 must recognize SSTI/template-injection (`{{7*7}}`, `${7*7}`) as an impact signal — else real SSTI findings get REJECTED.
- Candidates with empty `source_file` → no evidence file → REJECTED at CEK-2. That is correct (can't reproduce = don't report), not a bug.
- Slow = by design. Do not sprint the review; one candidate fully reviewed before the next.

