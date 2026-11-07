# Gate-block repair recipes — 0D HARD BLOCK & 0F final-gate (terukur 2026-10-17, 2 run penuh: energiekoers + dataport)

Kedua kasus ini mengulang **3× sampai HARD BLOCK / FINAL GATE FAILED** di run yang sebenarnya BENAR.
Keduanya kontrak producer↔gate (kelas yang sama dengan `gate-design-and-track-awareness.md` §6b),
dengan satu kuncinya: **perbaiki producer / regenerasi artefak — jangan edit `asset-coverage.py`
dan jangan klaim run-nya gagal.**

## Kasus 1 — 0D: `asset-coverage FAIL ... poc-execution.json` loop → HARD BLOCK

**Gejala (identik di 3 attempt):**
```
❌ GATE FAILED (attempt N) — analyzing failures...
   ✅ References dipakai: 52 requests nyata ... ✅ skill-usage: 7 skills all applied
   ❌ asset-coverage FAIL for phase(s): ['0C'] — some asset was READ not USED / skipped-timeout
🔁 REWORK (generic): re-running full force execution   ← rework tak memperbaiki apa pun
⇒ ❌ GATE FAILED after 3 attempts — HARD BLOCK ... jalankan ulang utk RESUME dari 0D
```

**Akar (baca dua file ini berdampingan, jangan menebak):**
- `asset-coverage.py` (skill ini, `scripts/asset-coverage.py`) baris ~470:
  `_no_poc = (pce is not None and pce and not any_exec(pce))` — syarat menerima ledger kosong
  adalah ledger **truthy** berisi entri berstatus non-EXECUTED (mis. `NO_POC_MATCHED`).
- `scripts/track-poc-execution.py`: cabang `if not plan:` menulis `NO_POC_MATCHED`, tapi cabang
  itu **tidak menangani plan yang ter-generate dengan `repos_matched=0`** → jatuh ke loop biasa →
  `execution_log = []` → file 2 byte `[]` → **falsy** → `_no_poc = False` → C4/C5/C6b/shelf
  semuanya `NOT_RUN "no evidence: poc-execution.json"`.

**Discriminator (1 menit):**
```bash
D=<target-dir>
cat "$D/poc-plan.json"      # kalau "repos_matched": 0 + "plan": [] → ini penyebabnya
wc -c "$D/poc-execution.json"   # 2 byte = [] (bukan ledger)
```

**Fix — di PRODUCER (permukaan sudah di-patch 2026-10-17, jangan duplikasi):**
`track-poc-execution.py` kini menulis `NO_POC_MATCHED` kalau `not plan` **ATAU**
`plan.get("repos_matched",0)==0 and not plan.get("plan")`. Kalau run kamu memakai salinan lama
(lagi-lagi HARD BLOCK), jalankan **satu** dari dua ini lalu RESUME (bukan restart 0A):
1. Jalankan ulang sub-step-nya sendiri (biarkan patch menulis ledger), atau
2. Tulis ledger jujur yang mencerminkan bukti yang SUDAH ada — **bukan fabrikasi**:
```python
# hanya bila poc-plan.json benar-benar bilang 0 match (bukti = file itu sendiri)
json.dump([{"repo":"NONE","status":"NO_POC_MATCHED","reason":"NO_POC_MATCHED",
            "tech":"<tech dari run-meta>",
            "evidence":"poc-plan.json repos_matched=0 nuclei_matched=0",
            "ts": datetime.now().isoformat()}], open(f"{D}/poc-execution.json","w"), indent=2)
```
`poc-variant-usage.json` / `poc-techniques-usage.json` boleh tetap `[]` — begitu `_no_poc` True
keduanya diterima otomatis (`(_no_poc and not pvc)`).

**Jebakan resume:** resume **me-SKIP 0C**, jadi producer tidak jalan ulang → kalau ledger lama
masih `[]`, tulis dulu (cara 2) SEBELUM resume, kalau tidak attempt-1 tetap gagal.
`--init` pada resume mencetak `seeded 0 assets` lalu `--derive` ulang — itu normal.

## Kasus 2 — 0F: `REPORT-survivors.md [NOT_RUN]` → FINAL GATE FAILED padahal 0F selesai

**Gejala:**
```
⛔ passed-findings.json is EMPTY → NEGATIVE report (0 passed triage)
📄 NEGATIVE audit report written: AUDIT-REPORT.md
❌ coverage 0E-REVIEW FAIL (1): FAIL 0E-REVIEW:review:REPORT-survivors.md [NOT_RUN]
audit-checkpoint: TOTAL: 32/33 checks   ❌ REPORT-survivors.md exists (finding_gate)
❌ PIPELINE FAILED: FINAL GATE FAILED — jalankan ulang utk RESUME dari DONE
```

**Akar:** `finding_gate.py` hanya menulis `REPORT-survivors.md` bila di-*invoke* dengan flag
`--report`. Pipeline 0E memanggilnya (atau menulis `gated.json`/`survivors.json`) **tanpa**
flag itu saat nol temuan lolos → `gated.json` = `[]`, `survivors.json` = `[]`, tapi file laporan
tak pernah dibuat; `audit-checkpoint` tetap menuntutnya (check `REPORT-survivors.md exists (finding_gate)`).

**Fix (read-only terhadap hasil, tidak mengubah verdict):**
```bash
cd <target-dir>
python "~/.chiper/skills/bounty-pack/finding_gate.py" findings.json \
       --out gated.json --report REPORT-survivors.md --survivors survivors.json
# rc=0 walau 0 survivor → file tetap ditulis berisi "Survivors: N of M"
```
Lalu RESUME (same command) → coverage 0E-REVIEW PASS → `audit-checkpoint` 33/33 →
`🎯 FINAL GATE PASSED` → baru jalankan `deep-audit-mode.py guard <dir>` (wajib HIJAU).

**Penting untuk interpretasi isinya:** survivor `finding_gate` BUKAN temuan. Di kedua run,
survivor pertama selalu kandidat varian **SSRF** berisi path `https://<host>/http://127.0.0.1/`
dengan body **byte-identik ke homepage** (SPA catch-all) — lolos impact-gate karena regex
`proof markers` mencocokkan teks, lalu **triage 7-Question membatalkannya** (`impact_score=None`).
Selalu baca `passed-findings.json` (bukan `survivors.json`) untuk menentukan "ada temuan / 0 temuan".

## Checklist penutup (kedua kasus)
1. `audit-checkpoint.py <dir> --phase all` → target **33/33**.
2. `deep-audit-mode.py guard <dir>` → `DEEP-AUDIT GATE: ... OK` (exit 0) — tanpa ini
   "0 temuan" belum boleh diucapkan (HARD RULE).
3. Perbarui catatan status produk (state pool / `CANDIDATES.md`) — termasuk koreksi state lama
   yang basi (lihat Account Factory item 8 di `audit-runbook` — Gmail-first).
