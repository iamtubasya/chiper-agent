---
name: autopilot-bounty
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Nonstop bounty loop: pick target from pool, run 0A-0F, validate 3x, draft Gmail
  with PDF PoC, deep-dive 3x, move to next target. Use when the operator says
  "jalankan nonstop sampai saya suruh berhenti".
metadata:
  hermes:
    tags: [security, autopilot, loop, pipeline, bounty, nonstop]
---

# Autopilot Bounty — loop nonstop

**Yang operator minta:** tarik pool → jalankan pipeline → kalau dapat bug, validasi 3× →
simpan draft Gmail + PDF PoC + evidence → deep-dive minimal 3× → kalau ada bug baru,
draft lagi → kalau tidak ada, pindah target baru → **nonstop sampai disuruh berhenti**.

---

## 1. Yang BISA diatur sekarang

| kemampuan | status | alat |
|---|---|---|
| Tarik target dari pool (35.550 domain) | ✅ | `pool_pick.py --web2/--web3 --monetary/--vdp --geo-preferred --safe-harbor --exclude-audited` |
| Tandai domain sudah diaudit | ✅ | `pool_pick.py --mark` |
| Jalankan pipeline 0A–0F | ✅ | `audit-pipeline-orchestrator.py <url> --scope <domain>` |
| Gate fail-closed (N/A + depth + eskalasi) | ✅ | sudah terpasang |
| Validasi 3× | ✅ | `reverify.py` + `0E-REVIEW` (3× cek) |
| Draft Gmail + PDF PoC + evidence | ✅ | `bug-bounty-disclosure` + `report-writing` (1 temuan = 1 draft = 1 PDF) |
| Deep-dive berulang | ✅ | `exploit-depth` L0–L5 + `attack-flows` (5 alur) |
| Pindah target otomatis | ✅ | `pool_pick.py --exclude-audited` |
| Loop nonstop | ✅ | `cronjob` (setiap N menit, `attach_to_session`) |

---

## 2. Yang TIDAK bisa diotomatis penuh (jujur)

| hal | kenapa | mitigasi |
|---|---|---|
| **Kirim email draft** | butuh keputusan kamu (kirim / jangan) | draft **tersimpan**, kamu review lalu suruh kirim |
| **Keputusan "ini bug nyata"** | butuh judgement manusia | gate 0E (3× cek) + kamu review sebelum kirim |
| **Register akun** | kadang butuh CAPTCHA/email/SMS | `geo_session.py` + SeleniumBase `solve_captcha` + mail disposable |
| **Audit paralel** | RAM 1.3G — sub-agent DITOLAK | **satu target pada satu waktu**, berurutan |
| **Target yang butuh KYC/berbayar** | TARGET RULES: SKIP | otomatis dilewati, dicatat N/A |

**Kesimpulan:** loop **teknis** bisa nonstop. Yang butuh **keputusan** (kirim laporan)
berhenti di draft — dan itu memang seharusnya.

---

## 3. Cara menjalankan

### Mode A — satu perintah (audit 1 target sampai selesai)
```bash
# tarik 1 target terbaik
python pool_pick.py --web2 --monetary --geo-preferred --safe-harbor \
  --exclude-audited --count 1 --mark --out next.txt

# jalankan pipeline penuh
python audit-pipeline-orchestrator.py https://$(cat next.txt) \
  --scope $(cat next.txt)
```

### Mode B — loop nonstop (cron, tiap 30 menit)
```bash
# aku buatkan cron job yg:
#   1. tarik target baru (exclude yg sudah diaudit)
#   2. jalankan pipeline 0A-0F
#   3. kalau ada temuan lolos 0E -> siapkan draft + PDF PoC (TIDAK dikirim)
#   4. deep-dive 3x pada temuan tsb
#   5. tandai domain diaudit, lanjut target berikutnya
#   6. berhenti hanya kalau kamu bilang berhenti
```

### Mode C — batch (kamu yang jalankan bertahap)
```bash
python pool_pick.py --web2 --monetary --geo-preferred --safe-harbor \
  --exclude-audited --count 10 --out batch.txt --mark
# lalu satu-satu:
while read d; do
  python audit-pipeline-orchestrator.py "https://$d" --scope "$d"
done < batch.txt
```

---

## 4. Aturan loop (mengikat)

1. **Satu target pada satu waktu** — RAM 1.3G, jangan paralel.
2. **Gate wajib lolos** — N/A discipline + depth gate + eskalasi gate. Kalau gate
   memblokir, perbaiki dulu, jangan paksa.
3. **Draft TIDAK dikirim** — tersimpan, kamu review, baru suruh kirim.
4. **Deep-dive 3×** — tiap temuan dieksplorasi minimal 3 putaran (L2→L3→L4→L5).
5. **Tandai diaudit** — supaya tak diulang.
6. **Target no-pay / KYC / berbayar** — dilewati otomatis, dicatat alasan.
7. **Berhenti kalau kamu bilang berhenti** — atau kalau gate memblokir 3× berturut-turut
   (tanda ada yang salah dengan konfigurasi, bukan target).

---

## 5. Yang akan kamu terima tiap siklus

```
[TARGET] arcanitegames.ca  (web2 monetary, up to $25,000, safe harbor full)
  [0A] scope OK — policy: bugcrowd.com/engagements/hypixel-studios-mbb-og
  [0B] recon: 142 subdomain, 38 live, 12 endpoint
  [0C] C1..C7 — 3 sinyal positif
  [0D] gate: PASS (76 tool terbukti)
  [0E] review: 1 kandidat lolos 3x cek
  [0F] DRAFT SIAP (TIDAK DIKIRIM):
       - draft email  : drafts/<target>-<finding>.txt
       - PDF PoC      : drafts/<target>-<finding>.pdf
       - evidence     : drafts/<target>-<finding>/ (req-resp, sha256, marker)
  [DEEP-DIVE] 3 putaran: L2 mekanisme -> L3 primitif -> L4 chain -> L5 impact
  [NEXT] pindah ke target berikutnya
```

---

## 6. Prasyarat sebelum mulai

- [ ] **Yolo/GO** — kamu sudah kasih (jangan tanya izin tiap langkah)
- [ ] **Pool** — 35.550 domain siap (`pool.json` 18.2MB)
- [ ] **Tool** — 76 terdeteksi, 0 syntax error
- [ ] **Gate** — 3 lapis fail-closed aktif
- [ ] **Gmail** — token terpasang (draf bisa dibuat)
- [ ] **RAM** — tutup Chrome yang tak dipakai (413MB)
