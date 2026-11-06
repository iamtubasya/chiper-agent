# ATO / IDOR / SSRF — Surface Atlas (31 trigger surfaces)

**Kenapa file ini ada.** `web2-high-yield-tables.md` mengajarkan *cara* menembus (bypass set,
impact ladder). File ini mengajarkan *di mana harus melihat* — daftar permukaan konkret yang
paling sering jadi pintu masuk. Dua sumbu berbeda, dua-duanya wajib.

Aturan pakai: **satu kelas belum dianggap tercakup sampai setiap permukaan di bawah dicoba atau
dinyatakan N/A dengan alasan teknis** (bukan "kelihatannya tidak ada").

Severity mengikuti impact terminal, bukan nama kelas.

---

## A. ACCOUNT TAKEOVER — 10 permukaan

| # | Permukaan | Probe pertama | Yang membuktikan | Sev | Depth |
|---|---|---|---|---|---|
| A1 | Reset token predictable / tak expire / tak terikat user | minta 3 reset berurutan, bandingkan token; pakai ulang token lama; pakai setelah ganti password | token bisa ditebak/dipakai ulang, ATAU token akun A berlaku untuk akun B | High | `hunt-forgot-password` |
| A2 | Host header injection di link reset | kirim reset dengan `X-Forwarded-Host`, `X-Host`, `Forwarded: host=`, `Host:` ganda | link di email mengarah ke domain penyerang (bukan cuma header ter-refleksi) | High | `hunt-host-header` |
| A3 | Rate limit absen di login / OTP | 30 percobaan lambat (`-rl`), ukur respons ke-1 vs ke-30; cek `Retry-After` | tidak ada lockout/backoff → kredensial atau OTP bisa di-spray | Medium→High | `hunt-brute-force` |
| A4 | Session fixation | set cookie sesi sebelum login, login, bandingkan ID | session ID **tidak** di-regenerate setelah login | High | `hunt-session` |
| A5 | OAuth/SSO misconfig | ubah `redirect_uri` (prefix, `@`, path traversal, subdomain), hapus `state`, cek secret di JS/APK | code/token mendarat di host penyerang, atau `state` absen → CSRF flow | High→Critical | `hunt-oauth` |
| A6 | JWT lemah | `alg:none`, `alg:HS256` dengan public key sebagai secret, brute secret lemah, hapus signature | server menerima token yang tanda tangannya tidak sah | High→Critical | `hunt-jwt-crypto` |
| A7 | Email/profile change tanpa re-auth | ubah email **tanpa** password saat ini; cek apakah notifikasi ke alamat LAMA bisa ditekan | email berpindah tanpa verifikasi alamat lama → reset password ke email penyerang | High | `hunt-ato` |
| A8 | 2FA bypass | coba endpoint alternatif yang skip 2FA (`/api/v1/` vs `/api/v2/`), manipulasi respons client-side, hapus field `otp` | akses penuh tanpa melewati langkah 2FA | Critical | `hunt-mfa-bypass` |
| A9 | Username enumeration | bandingkan pesan/status/waktu respons: login, register, forgot-password | beda respons antara user ada vs tidak → daftar akun valid | Low→Medium | `hunt-ato` |
| A10 | Cookie/token tanpa flag aman | baca `Set-Cookie`: `HttpOnly`, `Secure`, `SameSite` | cookie sesi bisa dicuri via XSS atau sniffing | Low (naik bila digabung XSS) | `hunt-session` |

**Urutan kerja yang benar:** A9 → A3 → A10 (murah, cepat) sebelum A1/A5/A6 (butuh akun kedua).

**Jebakan:** A1/A2 hanya jadi temuan kalau link yang **benar-benar dikirim** bisa dibuktikan.
Header yang ter-refleksi di respons bukan bukti — bukti adalah isi email/link.

---

## B. IDOR / BOLA — 10 permukaan

| # | Permukaan | Probe pertama | Yang membuktikan | Sev | Depth |
|---|---|---|---|---|---|
| B1 | ID sekuensial di URL/API | `/api/user/1234` → `1235`, `1233`, `0`, `-1` | respons berisi data milik akun lain | Medium→Critical | `hunt-idor` |
| B2 | Parameter tersembunyi di body/header | tambah `user_id`, `orgId`, `account_id`, `X-User-ID`, `X-Org-ID` | server memakai nilai itu tanpa cek kepemilikan | Medium→High | `hunt-idor` |
| B3 | GraphQL per-field/per-node | `node(id: base64("User:456"))`, alias ganda, fragment pada objek lain | field/node milik user lain terbaca lewat query yang sah | High | `hunt-graphql`, `hunt-fintech-graphql` |
| B4 | Export/download by ID | invoice/report/PDF/CSV: ganti ID, ganti `?id=` | file milik akun lain terunduh | High | `hunt-idor` |
| B5 | Mobile app API | ambil endpoint dari APK (`strings`, jadx), panggil langsung dengan token web | endpoint mobile kurang hardening: tanpa cek owner, tanpa rate limit | High | `mobile-pentest`, `apk-redteam-pipeline` |
| B6 | Batch/bulk operation | `{"ids":[own, victim]}`, `?ids=1,2,3`, array campuran | operasi massal memproses ID yang bukan milik pemanggil | High→Critical | `hunt-idor` |
| B7 | WebSocket / real-time channel | subscribe ke room/channel/user ID lain; ganti `room_id` di frame join | menerima pesan/event milik user lain | High | `hunt-websocket` |
| B8 | Versi API lama | `/api/v2/` 403 → `/api/v1/`, `/api/internal/`, `/api/beta/`, `/api/legacy/` | versi lama masih hidup dan otorisasinya lebih lemah | High | `hunt-shadow-api` |
| B9 | UUID predictable | UUID v1 (time-based), base64 dari integer, ID generator kustom | pola bisa ditebak → objek lain terambil | Medium→High | `hunt-idor` |
| B10 | Referensi objek nested | `/orgs/{org}/users/{user}`, `/posts/{p}/comments/{c}`, attachment | objek anak diakses tanpa validasi relasi ke parent yang diotorisasi | Medium→High | `hunt-idor` |

**Aturan bukti (wajib):** dua akun — penyerang + korban. Respons harus memuat **data korban yang
nyata**. `200` dengan body kosong **bukan** IDOR. Selalu sertakan respons akun sendiri sebagai kontrol.

**Prioritas:** B2 dan B8 paling sering terlewat di manual testing, dan paling sering dibayar.

---

## C. SSRF — 10 permukaan pemicu

| # | Permukaan | Probe pertama | Yang membuktikan | Sev | Depth |
|---|---|---|---|---|---|
| C1 | "Import from URL" / preview / webhook | masukkan URL kolaborator (interactsh), lalu `http://127.0.0.1:80` | callback OOB masuk **dan** ada fetch server-side | Medium→High | `hunt-ssrf` |
| C2 | PDF / HTML-to-image renderer | HTML berisi `<img src=http://127.0.0.1/>`, `<iframe>`, CSS `url()` | renderer mengambil resource internal saat membuat PDF/screenshot | High | `hunt-ssrf` |
| C3 | Cloud metadata | `169.254.169.254/latest/meta-data/iam/security-credentials/`, GCP `metadata.google.internal`, Azure `169.254.169.254/metadata/instance?api-version=` | body respons memuat kredensial/token (redaksi sebelum lapor) | High→Critical | `hunt-cloud-misconfig` |
| C4 | URL validator bypass | desimal `2130706433`, oktal `0177.0.0.1`, `127.1`, `[::1]`, redirect 302, DNS rebinding, `@` authority | blocklist terlewati dan request internal benar-benar terjadi | High | `hunt-ssrf` |
| C5 | OAuth "fetch avatar" / profile sync | daftarkan URL avatar/profil milik sendiri → arahkan ke internal | server fetch URL yang dikontrol user | Medium→High | `hunt-oauth` |
| C6 | Health check / monitoring endpoint | cari endpoint status/metrics yang menerima parameter URL atau host | endpoint mem-fetch tujuan arbitrer, atau membocorkan topologi internal sebagai pivot | Low→High | `hunt-ssrf` |
| C7 | File parser dengan external reference | XXE (`<!ENTITY x SYSTEM "http://...">`), SVG dengan `<image href>`, OOXML dengan rel eksternal | parser menyelesaikan referensi eksternal → SSRF/XXE | High | `hunt-xxe` |
| C8 | Proxy / gateway internal | parameter tujuan (`url=`, `target=`, `dest=`, `endpoint=`, `host=`) pada gateway | gateway meneruskan request ke backend sesuai input user | High→Critical | `hunt-ssrf` |
| C9 | Image/file library fetch remote | upload SVG/PDF berisi referensi remote; cek versi ImageMagick/Ghostscript | library mengambil resource remote (kelas ImageTragick) | High→Critical | `hunt-file-upload` |
| C10 | Webhook subscription tanpa validasi ownership | daftarkan webhook ke host sendiri, lalu ke internal; cek validasi domain | server melakukan request ke URL yang tidak diverifikasi kepemilikannya | Medium→High | `hunt-ssrf` |

**Impact ladder — jangan submit di bawah rung 3:**

```
1 callback DNS saja                          → Informational, BUKAN temuan
2 port internal terbuka / banner             → Low, biasanya ditolak standalone
3 cloud metadata terbaca (IAM creds/user-data) → High
4 metadata + kredensial DIPAKAI (S3/API call sukses) → Critical
```

Untuk metadata, buktikan **keterbacaan**, bukan sekadar keterjangkauan: kutip body respons
(ter-redaksi) di file evidence.

---

## D. Matriks silang — permukaan × teknik

Permukaan menentukan **di mana** menusuk; teknik menentukan **apakah tusukan masuk**.
Kombinasi yang paling sering membayar:

| Permukaan | Teknik yang dipakai | Kelas |
|---|---|---|
| C1/C10 webhook | redirect 302 → metadata | SSRF |
| C2 renderer | `<iframe src=file:///etc/passwd>` | SSRF/LFI |
| C4 validator | desimal/oktal + DNS rebinding | SSRF bypass |
| A2 reset link | `X-Forwarded-Host` + host ganda | ATO |
| A5 redirect_uri | prefix match (`evil.com` vs `target.com.evil.com`) | ATO |
| B2 hidden param | `X-Org-ID` di header, bukan body | BOLA |
| B6 batch | array campuran own+victim | BOLA |
| B8 versi lama | `/v1/` tanpa cek owner | BOLA |

---

## E. Gate sebelum submit (per kelas)

**ATO**
- [ ] Bukti adalah link/email nyata, bukan header ter-refleksi
- [ ] Dua akun; korban benar-benar terambil alih (bukan cuma "seharusnya bisa")
- [ ] Kontrol: alur normal dengan akun sendiri

**IDOR/BOLA**
- [ ] Dua akun; respons memuat data korban yang nyata
- [ ] Kontrol: objek milik sendiri, respons berbeda
- [ ] Bukan public-by-design (cek OpenAPI `security`, cek route yang dipakai front-end resmi)

**SSRF**
- [ ] Callback OOB atau body internal tersimpan sebagai artefak
- [ ] Impact ≥ rung 3 (metadata terbaca), bukan cuma DNS callback
- [ ] Kontrol: URL eksternal biasa → perilaku berbeda

---

## F. Hubungan dengan file lain

| Butuh | Buka |
|---|---|
| Teknik bypass & payload | `web2-high-yield-tables.md` §3–§6 |
| Kedalaman per kelas | skill `hunt-ato`, `hunt-idor`, `hunt-ssrf` |
| Menyusun Low jadi impact | `chain-to-impact`, `redteam-mindset` §3.5 |
| Bentuk bukti yang lolos gate | `evidence-state-ladder-and-reachability-gate.md` |
| Cek sebelum lapor | `category-pre-submission-checklists.md` |

---

*31 permukaan. Satu kelas belum tercakup sampai semuanya dicoba atau N/A dengan alasan teknis.*
