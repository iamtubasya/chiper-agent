# Bug Bounty Mission Workflow — Operator's Standard

## 7-Stage Pipeline

```
Stage 1: Recon & Codebase Mapping
    ↓
Stage 2: Attack Surface Discovery
    ↓
Stage 3: Bug Discovery (temukan sebanyak mungkin kandidat)
    ↓
Stage 4: Deep Verification (PoC, exploit, impact)
    ↓
Stage 5: Duplicate & Scope Check
    ↓
Stage 6: Report Generator
    ↓
Stage 7: Final Submission Review (MANDATORY GATE)
    ↓
✅ READY TO SUBMIT
```

## Communication during long runs (operator rule, 2026-10-17)

Operator: *"ttp kasih info progressnya, jgn diam aja"* — during multi-step engagements
(recon → scan → deep-dive), **report progress incrementally, never go silent for a whole
phase**. Shape he accepts: a short "Progress:" block after each meaningful step (what was just
extracted/found, what is running, what is next), artifacts referenced by absolute path. This is
not the same as the final report — it is a running commentary so he can course-correct (he used
it live to abort Abhieo mid-engagement and redirect to Australia). Corollary: when a background
job is running, say so and what it will produce; when a step dead-ends, say that too — silence
reads as a stalled agent.

**MISSION:** Tidak ada report yang boleh dibuat atau dikirim sebelum melewati Stage 7 review.

---

## Stage 7: Final Submission Review — COMPLETE CHECKLIST

**OBJECTIVE:** Verifikasi bahwa finding benar-benar layak disubmit, bukan false positive, duplicate, intended behavior, atau sekadar design issue.

### 1. VALIDASI
- Reproduce minimal **5x**.
- Jalankan pada **commit terbaru**.
- Jalankan pada **fork/mainnet-equivalent** jika memungkinkan.
- Pastikan hasil **konsisten**.

### 2. IMPACT
Buktikan impact nyata. Jangan hanya menunjukkan code flaw.

Harus bisa menjawab:
- Apa yang dicuri?
- Apa yang rusak?
- Siapa yang dirugikan?
- Berapa maximum loss?
- Apakah exploit realistis?

### 3. POC
PoC harus:
- **Repeatable**
- **End-to-end**
- Tanpa asumsi tidak realistis
- Tidak membutuhkan privileged access kecuali memang bagian threat model

### 4. ROOT CAUSE
Jelaskan:
- Mengapa bug terjadi
- Mengapa validasi gagal
- Fungsi yang terlibat
- Call flow
- State transition

### 5. SCOPE
Pastikan:
- Asset in-scope
- Commit in-scope
- Contract in-scope
- Bukan third-party issue

### 6. EXCLUSION CHECK
Pastikan bukan:
- ❌ Intended behavior
- ❌ Governance decision
- ❌ Admin risk
- ❌ Centralization
- ❌ Missing best practice
- ❌ Informational
- ❌ Gas optimization
- ❌ Code style
- ❌ Dead code tanpa impact

### 7. DUPLICATE CHECK
Cari pada:
- GitHub Issues & Pull Requests
- Audit reports
- Known issues
- Previous disclosures
- Public writeups

### 8. PATCH CHECK
Pastikan bug **belum diperbaiki**.

### 9. REPORT QUALITY
Report wajib memiliki:
- Title
- Summary
- Root Cause
- Technical Details
- Impact
- PoC
- Reproduction Steps
- Evidence
- Recommended Fix
- References

### 10. SEVERITY
Hitung:
- CVSS (dengan vector string)
- CWE
- Likelihood
- Exploitability
- Business Impact

### 11. CONFIDENCE SCORE
Nilai:
- Validity
- Exploitability
- Impact
- Duplicate Risk
- Report Quality

### 12. FINAL DECISION

Output **hanya salah satu:**

✅ `READY TO SUBMIT`
⚠ `NEED MORE EVIDENCE`
⚠ `POSSIBLE DUPLICATE`
⚠ `OUT OF SCOPE`
⚠ `DESIGN DECISION`
⚠ `FALSE POSITIVE`

### 13. SUBMISSION RULE

Jangan pernah:
- Melebih-lebihkan severity
- Mengarang impact
- Mengarang estimasi bounty
- Mengklaim Critical tanpa PoC yang membuktikan kerugian nyata
- Mengirim submission otomatis

### 14. SELF-CRITIQUE

Sebelum memberikan status READY TO SUBMIT, lakukan review sebagai triager bug bounty dan jawab:

- Mengapa saya mungkin akan menolak report ini?
- Bukti apa yang masih kurang?
- Apakah ada interpretasi lain yang membuat ini intended behavior?
- Seberapa yakin saya (0–100%) bahwa report ini akan diterima?

**READY TO SUBMIT hanya boleh diberikan jika seluruh checklist di atas lolos.**
