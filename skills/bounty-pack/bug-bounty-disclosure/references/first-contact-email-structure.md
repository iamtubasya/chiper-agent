# Struktur email disclosure KONTAK PERTAMA (wajib ikut bentuk ini)

Sumber: koreksi user 2026-10-01 — *"perbaiki dl draftnya, masa gkad perkenalan sama sekali"*.
Draft sebelumnya cuma `"Hi <vendor> security team,"` lalu langsung `Summary`. Secara teknis isinya benar,
tapi **penerima tidak tahu siapa yang menulis dan atas dasar apa** — dan itu yang pertama kali dibaca triager.

Aturan: email kontak pertama punya **4 blok wajib** dan satu **blok penutup**. Bahasa: INGGRIS
(artefak eksternal selalu Inggris; catatan internal boleh ID).

---

## Blok 1 — PEMBUKA (jangan pernah dihapus)

```
Hi <Product> security team,

My name is <Nama>, an independent security researcher. I am contacting you at <alamat security> under
the responsible disclosure policy published at <URL policy> (safe harbour), and I would like to be
upfront about what this report is and what it is not.

While reviewing <permukaan yang diperiksa — docs site / API spec / repo publik / kontrak on-chain>
as part of good-faith, <unauthenticated> and strictly read-only research, I noticed <inti temuan dalam
satu kalimat>.

I want to state clearly up front that I did not obtain any <data kategori: investor / personal /
credential> data, I did not alter any state, and I stopped as soon as the issue was established.
Everything below is reproducible with plain <GET requests / commands> and the raw responses are quoted
so you can verify each step yourself. I have also labelled exactly what I did NOT prove, so this does
not read as a stronger claim than the evidence supports.
```

Yang wajib ada di blok ini, satu per satu:
- [ ] nama + peran
- [ ] alamat tujuan + **URL policy** yang jadi dasar + safe harbour
- [ ] **apa yang sedang direview dan bagaimana caranya** (bukan cuma "saya menemukan bug")
- [ ] temuan inti dalam SATU kalimat
- [ ] pernyataan eksplisit: tidak mengambil data, tidak mengubah state, berhenti ketika sudah jelas
- [ ] pernyataan bahwa semuanya bisa direproduksi + tangkapan mentah dikutip
- [ ] pernyataan bahwa yang TIDAK terbukti juga dilabeli

## Blok 2 — ISI TEKNIS

`Summary` → `Steps to reproduce` (perintah nyata + hasil) → `Impact (stated conservatively)` →
`Suggested remediation` → `Conduct notes`.
Sertakan juga bagian `What I did NOT demonstrate` — daftar eksplisit apa yang tidak terbukti.
Lihat `report-templates.md` untuk badan teknisnya.

## Blok 3 — LAMPIRAN untuk hal yang BUKAN kerentanan

Kalau ada lead/QA nit yang layak disampaikan tapi belum terbukti, jangan campur ke temuan utama dan
jangan dibuang. Taruh di bagian terpisah berjudul persis:

```
Additional observations (NOT vulnerabilities)
```

Tiap item: label `LEAD (unconfirmed)` atau `QA NOTE`, apa yang terbukti, apa yang TIDAK terbukti,
saran tindakan, dan penutup "please treat this as a non-issue" bila memang begitu.
Tambahkan satu paragraf "Context on the rest of my testing" yang menyebut tool/negatif — supaya vendor
tahu cakupannya dan tidak mengira cuma satu request yang dilakukan.

## Blok 4 — PENUTUP

```
Thank you for reading this, and for running a public disclosure channel at all - it is genuinely appreciated.
If it is useful, I can send the raw response captures for every command quoted here, walk through any step, or
re-test once you have changed something. I am happy to keep this open until you have had a chance to look at it,
and I am happy to close it immediately if you would rather not have it tracked.

I am not requesting any compensation, and I understand from your policy that none is offered; I would only be
glad to see <perbaikan yang diharapkan> and the appendix items checked by whoever owns those code paths.

Regards,
<Nama>
<email>
```

- [ ] ucapan terima kasih yang tulus (bukan formalitas kosong)
- [ ] **penawaran konkret**: kirim tangkapan mentah / jelaskan langkah / uji ulang setelah fix
- [ ] **pilihan jelas**: jaga terbuka atau tutup atas permintaan mereka
- [ ] pernyataan eksplisit tidak meminta kompensasi bila policy-nya tidak menawarkan reward
- [ ] satu tanda tangan, di akhir

---

## Pitfall yang sudah benar-benar kejadian

1. **Tanpa perkenalan = koreksi user.** Jangan pernah mulai dari "Summary" walaupun temuan sudah jelas.
   Triager butuh tahu penulisnya siapa dan dasar pengirimannya apa.
2. **Skrip pembersih sendiri bisa memotong badan email.** Untuk membuang tanda tangan ganda, saya pakai
   `s.split(sig)[0]` — dan itu **menghapus seluruh lampiran** karena lampiran berada setelah tanda tangan
   pertama. Hasilnya file kembali ke ukuran semula tanpa saya sadari.
   → Setelah operasi teks apa pun, **cetak panjang + jumlah marker** dan bandingkan dengan sebelum:
   ```python
   print(len(out), out.count("Additional observations"), out.count("Regards,"))
   ```
   Kalau panjangnya tidak bertambah padahal baru menambah teks → edit-nya gagal/memotong. Jangan lapor "sudah".
3. **Drift faktual di kalimat yang baru ditulis.** Saya menulis "the four non-production API hosts" padahal
   jumlahnya tiga, dan satu frasa canggung. Baca ulang kalimat baru itu **kata per kata** sebelum menyerahkan;
   hitungan, angka, dan nama host adalah yang paling sering salah.
4. **Verifikasi draft dari server, bukan dari naskah lokal.** Setelah append ke `[Gmail]/Draf`, ambil kembali
   header-nya (To/Subject/Date/size) dan cetak. Laporkan uid + ukuran + jumlah draft yang cocok.
5. **Subjek harus menyebut temuan, bukan "Security report".** Pola yang diterima:
   `[<Severity>] <apa yang salah> on <host> while <pembanding>`. Kalau environment-nya banyak, sebut semuanya
   di subjek (`api.dev / api.staging / api.devddx`) — itu yang bikin triager langsung paham cakupannya.
6. **Draft hanya setelah ada temuan** (aturan user sebelumnya). Kalau belum ada temuan, gali dulu dengan
   toolset penuh; jangan siapkan deliverable kosong.
