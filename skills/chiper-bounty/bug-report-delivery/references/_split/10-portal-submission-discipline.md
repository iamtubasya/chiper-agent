# Portal / web-form submission discipline (terukur 2026-10-31, Scribble Maps)

Berlaku setiap kali laporan dikirim lewat **form portal vendor** (bukan email draft).
Sumber: `api.scribblemaps.com/vulnerabilities` — form multipart + Cloudflare Turnstile,
login wajib, batas **1 laporan per akun per hari**.

---

## 1. ⛔ JANGAN pernah dry-run probe endpoint submit

Ini kesalahan yang benar-benar memakan waktu di sesi 2026-10-31 dan **memblokir submit asli**:

| yang dilakukan | hasil |
|---|---|
| 6× `POST /api/vulnerability/submit` dengan payload sengaja tidak lengkap (title saja, desc saja, dll.) untuk "mengenali field" | 3 balasan `400 {"error":"Description is required"}` lalu **`429 {"error":"You've submitted too many reports recently"}`** |
| probe ulang 20 menit kemudian | masih `429` |
| endpoint AI (`/api/vulnerability/aisubmit`) | tidak kena throttle (400 validasi) — throttle spesifik per-endpoint |

**Aturan:** endpoint submit itu **one-shot**. Satu request gagal validasi pun sudah cukup
membakar jatah throttle. Pelajari nama field dari **HTML form + JS**, bukan dari probing:

```python
# 1) nama/id field + enctype dari HTML
re.findall(r'<(input|textarea|select)[^>]*>', html)      # id, type, placeholder, maxlength
re.findall(r'<form[^>]*>', html)                          # enctype="multipart/form-data"
# 2) endpoint mana yang dipakai form itu, dari JS halaman yang sama
re.findall(r'["\'`](/api/[^"\'`\s]+)', html)
# 3) field wajib = atribut `required` + label di atasnya
```

Kalau tetap butuh konfirmasi bentuk payload, pakai **satu** request dengan field yang
pasti gagal validasi (mis. hanya `title`), lalu **berhenti** — jangan ulangi 3×.

## 2. Isi form di browser headed, tunjukkan ke operator, baru submit

Operator meminta melihat tampilan submit sebelum dikirim ("sy jg mau lihat"). Pola yang benar:

1. Playwright persistent context `channel="chrome"`, `headless=False` (Turnstile butuh browser asli).
2. Isi field via `page.fill("#vuln-title", ...)`, `page.fill("#vuln-description", ...)`,
   `page.fill("#vuln-date", ...)`, lampiran via `page.set_input_files("#vuln-attachments", pdf)`.
3. **Verifikasi 3× sebelum submit** — baca balik nilai dari DOM, bandingkan dengan payload di disk:
   ```python
   v = page.evaluate("""()=>({title:document.getElementById('vuln-title').value,
     desc:document.getElementById('vuln-description').value,
     date:document.getElementById('vuln-date').value,
     paypal:document.getElementById('vuln-payment-email').value,
     files:[...(document.getElementById('vuln-attachments').files||[])].map(f=>[f.name,f.size,f.type])})""")
   assert v["title"]==payload["title"] and v["desc"]==payload["description"]
   assert v["files"][0][1]==os.path.getsize(pdf)      # ukuran file = bukti lampiran benar
   ```
4. **Cek field readonly/prefill** (mis. PayPal email diisi dari email akun) — kalau sesi bukan
   akun yang diminta operator, nilainya akan salah dan baru kelihatan di sini.
5. Tunggu token Turnstile: `window.turnstile.getResponse()` (sitekey portal **berbeda** dari
   sitekey register — ambil dari `data-sitekey` di HTML, jangan hardcode).
   **Kalau token tidak muncul, widget-nya harus DIKLIK** — lihat §7 di bawah.
6. Biarkan jendela terbuka (`terminal background=true`, proses tidur panjang di akhir script),
   beri operator URL + status throttle, dan **jangan klik Submit** sampai dia bilang.

## 3. Batas 1 laporan/hari → prioritas, jangan submit semua

Program dengan kuota harian memaksa pemilihan. Urutan:
1. Kirim temuan **paling kuat** (severity + impact paling jelas) lewat portal hari itu.
2. Temuan sisanya: **tahan** untuk besok, atau lewat kanal email kalau program punya alamat
   keamanan. Jangan gabungkan dua temuan jadi satu laporan (RULE 0: 1 temuan = 1 laporan).
3. Sebutkan kuota ini ke operator supaya dia bisa memutuskan, jangan diam-diam memilih.

## 4. Identitas pengirim ≠ identitas akun uji → klarifikasi, jangan tulis ulang bukti

Kalau laporan dikirim dari akun utama operator sementara PoC memakai akun uji
(plus-alias), **jangan** ubah isi PoC. Tambahkan satu kalimat kepemilikan:

> "RESEARCHER_USERNAME+sm1@gmail.com dan RESEARCHER_USERNAME+sm2@gmail.com adalah plus-alias dari
> RESEARCHER_EMAIL, mailbox tempat laporan ini dikirim; semua identitas di laporan ini
> milik reporter sendiri."

Alasannya: plus-address masuk ke inbox yang sama, jadi klaim "kedua identitas milik reporter"
tetap benar, dan triager tidak salah paham bahwa ada pihak ketiga sebagai "korban".
Kalau identitas uji **bukan** alias (mailbox benar-benar berbeda), itu harus dinyatakan eksplisit.

## 5. Setelah submit — verifikasi, jangan berhenti di HTTP 200

- Baca balasan: bisa `pendingConfirmation` + kirim email approval ke pemilik mailbox
  (laporan belum masuk triage sampai link diklik). Laporkan ini ke operator.
- Cek daftar "Your Submissions" di portal: judul, tanggal, status harus muncul.
- Kalau `429`: throttle aktif, tunggu (window-nya tidak diketahui — cek berkala), dan
  **jangan** spam probe untuk mengetesnya.

## 6. Efek samping provisioning yang harus dibuka ke vendor

Meng-probe endpoint seller/billing (`market/create-account`) bisa **benar-benar membuat**
objek di sisi vendor (terukur: Stripe Connect Express `acct_...` tercipta). Kalau itu terjadi:
catat sebagai side effect di laporan/coverage, jangan lanjutkan onboarding/KYC, dan siapkan
kalimat pengakuan untuk vendor.

## 7. ⛔ Turnstile menolak? Pakai jalur AI yang DIDOKUMENTASIKAN portal sendiri

Terukur 2026-10-31: form manusia (`POST /api/vulnerability/submit`) tidak bisa dipakai karena
Turnstile berhenti mengeluarkan token — widget muncul dengan bounding box normal, tetapi
`window.turnstile.getResponse()` tetap `null` setelah 90 s polling **dan** setelah 3× klik.

**Jangan lawan captcha-nya.** Baca dulu apakah halaman portal itu sendiri mendokumentasikan
jalur submit terprogram. Di Scribble Maps, halaman yang sama memuat blok
"AI Submission Instructions" berisi endpoint bebas-captcha:

```
POST https://api.scribblemaps.com/api/vulnerability/aisubmit?userId=<userId>
Content-Type: multipart/form-data
title / description / attachments
```

Cara pakainya dengan aman:

```python
acc = S.get("https://www.scribblemaps.com/api/account", timeout=20).json()
assert acc["userId"] == OWN_USER_ID          # WAJIB: userId harus milik sesi sendiri
r = S.post(f"{A}/api/vulnerability/aisubmit?userId={OWN_USER_ID}",
           files={"attachments": (name, pdf_bytes, "application/pdf")},
           data={"title": title, "description": desc, "date": "2026-10-31"}, timeout=60)
# -> 200 {"success":true,"pendingConfirmation":true,"referenceId":"FF3179", ...}
```

Aturan pakai jalur ini:
1. **`userId` WAJIB sama dengan userId sesi.** Verifikasi lewat `/api/account` dulu — ini juga
   persis celah yang dilaporkan sebagai temuan #2 di engagement yang sama, jadi jangan sampai
   kita sendiri mengulanginya.
2. **Isi laporan identik** dengan yang sudah diverifikasi 3× (title, description, tanggal,
   lampiran) — jangan buat versi ringkas "karena lewat API".
3. Jalur ini **tetap memakan kuota 1 laporan/hari** — bukan jalan pintas kuota.
4. Balasannya `pendingConfirmation`: laporan belum masuk review sampai link approval di email
   pemilik mailbox diklik (**expired 48 jam**). Cek inbox lewat Gmail API; kalau email tidak
   datang dalam ~15 menit, laporkan ke operator sebagai open item — jangan klik ulang submit
   karena itu membakar kuota.
5. Sebutkan ke operator **kenapa** form manual tidak dipakai (captcha) supaya dia bisa putuskan;
   kalau dia tetap mau submit sendiri, serahkan jendela browser yang sudah terisi.

Teknik klik widget Turnstile (dipakai sebelum fallback di atas, dan berguna untuk signup umum):
`saas-test-account-provisioning` → **Step 3j**.
