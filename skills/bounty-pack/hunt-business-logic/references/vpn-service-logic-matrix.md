# VPN Service — Business Logic Matrix (consumer VPN: quota/connection/region)

Checklist 2026 untuk VPN consumer berbayar (Mullvad/Proton/Nord-style), BUKAN `enterprise-vpn-attack`
(yang itu SSL VPN appliance/Ivanti/Forti). Di sini targetnya billing + entitlement + client-logic.

## Surface yang diuji

1. **Bandwidth / data quota bypass** — plan berbasis kuota. Uji reset counter:
   - logout→login cepat (apakah counter persist atau reset?)
   - ganti device ID / fingerprint / session ID
   - race pada endpoint cek-kuota (parallel request sebelum counter commit)
   - manipulasi counter yang terpapar di respons (kalau UI baca kuota dari token/body)
   Bukti: kuota melebihi cap tanpa upgrade = entitlement/accounting bug.

2. **Simultaneous connection limit bypass** — buka sesi > limit diklaim:
   - request paralel ke endpoint connect/session-create (race pada slot count)
   - manipulasi device fingerprint/session ID agar dihitung device baru
   - token reuse di banyak socket bersamaan
   Bukti: N sesi aktif > limit di pricing/TOS.

3. **Server / region access control** — akun free/tier-rendah akses server premium:
   - langsung via config file `.ovpn`/WireGuard peer yang di-list API
   - call endpoint server-list API langsung (bukan lewat app resmi yang menyembunyikan region premium)
   Bukti: dapat credential/key server premium tanpa entitlement.

4. **Subscription sharing / token reuse** — satu kredensial dipakai melebihi lisensi device.

5. **Protocol downgrade** — paksa client fallback ke protokol lemah (blokir port utama).
   Cek apakah ada peringatan atau silent downgrade (bug fungsional, relevan untuk klaim keamanan).

6. **Kill-switch / DNS leak** — matikan paksa interface, cek apakah traffic benar-benar diblokir
   sesuai klaim marketing. Ini bug fungsional yang jadi laporan privacy/false-advertising.

7. **Log policy / no-log claim** — cek endpoint internal/admin apakah benar tidak menyimpan metadata
   konkret. (lebih ke audit konfigurasi daripada blackbox murni).

## Aturan triase

- Race pada slot/quota = bukti saldo/kuota AKHIR, bukan 2× 200 (pakai `hunt-race-condition`).
- Region/server access = bukti credential/key premium bisa DIPAKAI, bukan cuma list nama server.
- Kill-switch/DNS leak = butuh PoC traffic (packet capture) yang membuktikan kebocoran, bukan klaim.
- "No-log" claim = audit konfigurasi; rendah kalau cuma blackbox tanpa bukti data tersimpan.