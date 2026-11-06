# Authz & crypto surfaces: cara membuktikan negatif (dan cara tidak membodohi diri)

Ringkasan dari satu engagement penuh (Proton, 2026-10-25) — 15+ endpoint authz diuji, semuanya
bersih. Yang membuat hasilnya bisa dipercaya bukan jumlahnya, tapi **kualitas diferensialnya**.

## 1. Uji dengan OBJEK NYATA, bukan endpoint kosong

Endpoint yang kamu panggil tanpa objek akan balas `[]` / `Total: 0` dan kamu tidak menguji apa pun.

Yang dilakukan dan wajib diulang:
- **upload file betulan** ke drive target → dapat `Volume/Share/LinkID` nyata, baru uji authz
- **buat alias/record betulan** → dapat integer ID nyata, baru uji ID tetangga
- **buat subdomain/vault/page betulan** → baru uji kuota, duplikat, dan kepemilikan

Kalau tidak punya objek: tulis `UNTESTED – no object created`, **jangan** tulis NEGATIVE.

## 2. Diferensial 2-identitas-minimum: pakai ID tetangga

Dengan satu akun pun kamu bisa uji banyak hal — bandingkan **ID sendiri vs ID yang bukan milikmu**:

```
mine = 51708360    other = mine-1, mine+1, 1, 100, 1000000
```

Pola hasil yang harus dibaca benar:

| pola | arti | keputusan |
|---|---|---|
| `200` untuk milik sendiri, `403 Forbidden` untuk orang lain | authz **benar** | NEGATIVE, tulis apa adanya |
| `200` untuk milik sendiri, redirect ke `/dashboard/` untuk orang lain | authz benar (deny via redirect) | NEGATIVE |
| **seragam** `422 "not found"` untuk semua ID acak | tidak ada oracle | NEGATIVE (bagus) |
| `403` (ada, bukan milikmu) vs `400 "Unknown error"` (tidak ada) | **oracle keberadaan** | info-only → hampir selalu DROP, sebut di negatif |

Aturan: authz yang deny lewat redirect **tetap deny**. Jangan salah baca "200 di halaman redirect"
sebagai bypass — cek `page.url` finalnya.

## 3. Oracle keberadaan = info-only, jangan dinaikkan

Banyak program mengecualikan "information disclosure tanpa dampak". Contoh yang muncul dan
sebaiknya **tidak** dilaporkan:
- `GET /api/aliases/{id}`: 403 vs 400 → hanya bilang "integer ini alias hidup"
- `?Username=` pre-auth mengembalikan modulus SRP untuk nama ada maupun tidak → bukan enumerasi
- field `Suggestions` pada endpoint availability: **verifikasi dulu** apakah nama yang disarankan
  itu benar-benar terpakai. Pada kasus ini semuanya masih bebas → array-nya sintetis, bukan bocoran.
  Selalu uji klaim "bocor username lain" dengan mengecek 3–4 nilai yang disarankan.

## 4. Permukaan kripto sisi-server (SRP, share-link)

Yang diuji pada `POST /drive/urls/{token}/auth` (dan analoginya): kirim matriks input rusak dan
pastikan **tidak ada token terbit**.

| payload | jawaban yang benar |
|---|---|
| `null` / integer untuk field string | `400` type error |
| string kosong | `422 Invalid parameter` |
| base64 sampah | `422 Invalid parameter` |
| field wajib dihilangkan | `400 Missing required attribute` |
| server ephemeral diputar jadi client ephemeral | `422` |

Kalau semuanya ditolak → tulis **NEGATIVE (input handling)**, bukan "tidak bisa diuji".

**Jebakan besar:** 30 request cepat yang semuanya `422` **bukan** bukti "tidak ada rate limit".
Kalau payload gagal di **validasi parameter** (mis. ephemeral acak bukan elemen grup SRP), itu belum
pernah jadi tebakan password. Statusnya `UNTESTED`, bukan NEGATIVE, bukan temuan. Uji brute-force
yang sah butuh `A = g^x mod N` + proof yang benar.

## 5. Jangan buat link berpassword sendiri kalau butuh crypto klien

`POST /shares/{id}/urls` menuntut `SRPVerifier`, `SharePassphraseKeyPacket`, `UrlPasswordSalt`, dsb.
Artinya implementasi SRP verifier + re-enkripsi passphrase di sisi klien. Kalau UI-nya terhalang
modal/upsell, tandai `UNTESTED – needs client-side crypto`, jangan diakali dengan payload setengah.

## 6. Kuota / limit: baca teks UI dengan curiga

"Currently you can create up to 4 subdomains" ternyata = **sisa izin**, bukan total (1 dipakai →
"up to 4"; 5 dipakai → "up to 0", tombol Create hilang). Total sebenarnya 5. Salah baca satu kali →
hampir melaporkan "quota bypass" yang tidak ada. Selalu verifikasi dengan **menghitung objek nyata**
yang kamu miliki, bukan dengan teks bantuan.

## 7. Kerangka pelaporan negatif

```
Bersih (dengan bukti): <daftar endpoint/kelas + pola respons>
UNTESTED (bukan negatif): <daftar + alasan teknis spesifik>
```
Jangan pernah gabungkan keduanya jadi "0 temuan, aman". Program yang matang menghargai coverage
yang jujur; triager akan menghukum klaim "secure" tanpa cakupan.
