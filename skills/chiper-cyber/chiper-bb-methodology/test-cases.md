# Test Cases — chiper-bb-methodology

Karena skill ini workflow (bukan kelas), test case terstruktur diambil dari:

1. **Pra-jual (Phase 3):** `../chiper-security-bounty-hunter/test-cases.md` — cek surface
   kelas yang mau dihunt ADA di target; tidak ada → catat N/A + alasan.
2. **Per kelas:** setiap `test-cases.md` di dir sub-skill kelas terkait (`~/.chiper/skills/chiper-cyber/chiper-<kelas>/`) (sqli, xss, ssrf, xxe,
   access-control, auth-bypass, deserialization, api-security, dst).
3. **Validasi temuan (Phase 5):** 7-Question Gate →
   `../chiper-verification-loop/guides/false-positive-triage-guide.md` + `../chiper-verification-loop/test-cases.md`.
4. **Kualitas laporan:** `../chiper-security-bounty-hunter/guides/bug-bounty-report-writing-guide.md`.

Urutan penerapan: workflow (file SKILL.md utama) → test-case kelas → gate verifikasi.
