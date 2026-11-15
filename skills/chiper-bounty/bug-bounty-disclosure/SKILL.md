---
name: bug-bounty-disclosure
author: RESEARCHER_NAME
description: Skill end-to-end buat authorized/good-faith bug bounty & coordinated vulnerability disclosure ke developer atau pemilik projek — untuk SEMUA jenis bug (web, API, infra, mobile, cloud, smart contract/web3, agent/LLM), crypto maupun non-crypto. Pakai skill ini setiap kali user mau triase & verifikasi temuan, bikin PoC, NYARI kontak dev/owner (security.txt, SECURITY.md, GitHub, WHOIS, on-chain, sosmed), dan KIRIM laporan via email — baik target punya program bug bounty terdaftar (HackerOne/Immunefi/dll) maupun proyek tanpa program resmi. Trigger juga kalau user nyebut "report bug ke dev", "disclosure", "lapor kerentanan", "cari kontak owner projek", "kirim report email", "responsible disclosure", "bug bounty" — walau ga eksplisit bilang "skill". Sisi disclosure jalan buat proyek apapun; dasar pengetesan harus sah/good-faith.
metadata:
  hermes:
    tags: [bug-bounty-disclosure]
---

# Bug Bounty & Coordinated Disclosure

Skill buat ngerapihin seluruh alur dari **temuan → verifikasi → cari kontak → lapor ke dev via email → koordinasi fix**. Serba-guna: crypto & non-crypto, target dengan program resmi maupun tanpa program. Fokusnya bikin laporan yang **valid, reproducible, dan diterima dev** — bukan AI-slop yang di-ignore.

## ⚠️ Dasar good-faith (baca dulu, singkat)

Skill ini buat **good-faith security research + coordinated disclosure**. Lapor kerentanan ke pemilik projek itu sah & etis **entah mereka punya program resmi atau enggak** — justru itu tujuannya.

Yang harus dijaga: **dasar pengetesan harus sah.** Bug ditemukan lewat cara legit:
- Sistem/infra milik sendiri, akun sendiri, atau testnet.
- Review kode open-source / artefak publik (repo, package, image).
- Analisis smart contract on-chain (bytecode/source publik).
- Target yang punya program bug bounty / VDP / `security.txt` yang mengundang laporan.
- Ada izin tertulis dari owner.

Jangan pakai skill ini buat **membenarkan intrusi tanpa izin** ke sistem produksi pihak ketiga (mancing kredensial, nembus akses yang bukan hak lo, lanjut nge-drill setelah dapat akses). Kalau ragu apakah suatu langkah pengetesan sah: **stop, jangan eskalasi akses**, laporkan hanya yang lo temukan lewat cara legit. Untuk bug crypto yang dananya live & exploitable: **jangan exploit, jangan publikasikan dulu** — disclosure privat ke tim adalah langkah yang benar.

## Prinsip inti

Sebuah temuan layak dikirim ke dev kalau: **(1) valid & reproducible dengan PoC**, **(2) impact-nya nyata**, **(3) dikirim ke pihak yang benar lewat kanal yang tepat**, dengan **(4) nada good-faith, tanpa ancaman/ransom.**

## Alur pakai skill

1. **Jalanin `workflow.md`** — pipeline 6 fase: Triase → Verifikasi/PoC → Impact → Cari Kontak → Kirim Email → Koordinasi & Follow-up.
   → **PoC wajib mencetak nilai yang dieksploitasi, bukan cuma lulus.** Tes hijau tanpa output bukan
   bukti bagi dev. Cara per-stack (Rust/Soroban: `extern crate std;` + `{:?}` untuk `Address`;
   Node/vitest: ANSI di output + capture per-file): `references/poc-runtime-evidence.md`.
   → **Triase/Verifikasi & Impact: wajib lewat gate mekanis dulu** (bukan cuma diklaim lolos):
   ```bash
   python $TOOLKIT/shared/finding_gate.py findings.json --report REPORT-survivors.md
   python $TOOLKIT/shared/chain_builder.py findings.json --goal <impact>
   ```
   `finding_gate.py` buang temuan info-only / by-design / **rantai exploit mati — walau skornya tinggi**.
   Yang di-drop gate = informational; jangan dikirim. Kalau semua di-drop, lapor jujur "tidak ada temuan
   yang layak" — itu hasil yang sah, bukan alasan buat padding laporan.
   ⛔ **TAPI `finding_gate.py` DROP ≠ temuan itu sampah — diperiksa dulu (koreksi 2026-10-12, Vana).**
   Gate-nya menilai dari teks temuan, dan ia bisa salah buang temuan nyata karena dua hal:
   (a) **kosakata impact-nya web2/PII-sentris** (pii-exposure / fund-loss), jadi SSRF, consent-integrity,
   registry/identity-spoofing, missing-auth, privileged-fund-movement sering skor 0 → DOWNGRADE;
   (b) **frasa jujur wajib kita sendiri** — "What I did NOT demonstrate", "not a live exploit", "by design",
   "information only", dan kata **"documented"** polos — dibaca sebagai penanda by-design/info-only dan
   men-DROP temuan. Hitungan nyata pada 8 temuan asli: sebelum diperbaiki `REPORT 1 / DOWNGRADE 2 / DROP 5`
   (dua temuan terkuat — webhook SSRF & celah trust kontrak — ikut terbuang); sesudah patch
   `REPORT 5 / DOWNGRADE 2 / DROP 1`. **Jadi: baca alasan DROP-nya, dan kalau alasannya "marked by-design"
   atau "info-only: info:version-disclosure" padahal temuanmu bukan itu, itu bug gate, bukan verdict.**
   Perbaikannya (additive, ada backup): strip section keterbatasan sebelum klasifikasi, persempit regex
   by-design/open-redirect/version-disclosure, dan tambah kelas impact web3/SSRF. Detail patch + rasionalnya
   ada di skill `bb-audit-launcher` (§ 0D/0E/0F GATE PITFALLS).
   ⛔ Dan **jangan pernah kirim artefak `AUDIT-REPORT.md` / `AUDIT-REPORT.pdf` hasil pipeline otomatis.**
   Pada run yang sama, dengan 0 temuan tervalidasi, report-agent menulis laporan yang section Findings-nya
   KOSONG tapi prosanya mengklaim "Findings Count: 1", "All findings passed impact verification",
   "37/37 hackskills loaded", dan "1 high-impact vulnerabilities → Fund/data theft / Account takeover",
   plus PDF **0 byte** sambil mencetak "READY FOR SUBMISSION". Deliverable yang dikirim tetap PDF per-temuan
   yang kita bangun sendiri dari bukti mentah.
   → **Sebelum nulis draft, cek dulu: ini temuan BARU atau sudah publik?** `references/known-issue-and-deployment-gap.md`.
   Cek repo publik + riwayat commit file-nya, tanggal PR fix, dan **tanggal DEPLOY kontrak**
   (Sourcify `deployment.blockNumber` → `eth_getBlockByNumber`). Fix yang sudah di-merge TAPI belum
   sampai ke kontrak live = **deployment gap** — tetap lapor, dan sebutkan duplikasinya terbuka
   di section sendiri. Aturan user 2026-10-08: *"duplikat gpp ttp lapor, ktnya ad reward duplikat"*.
   ⛔ **Dan temuan lemah di aset yang sama JANGAN ditempel jadi "secondary observation" di laporan
   yang kuat — pisahkan atau buang.**
   ⛔ **Cek daftar None/out-of-scope PROGRAM sebelum mendraft — bug nyata yang dikecualikan eksplisit
   tetap BUKAN laporan.** Gate internal membuang yang info-only; policy program membuang yang lain
   lagi. Kasus nyata (CoderPad 2026-10-17): 4 temuan nyata & reproducible (alias-overloading GraphQL,
   urlencoded POST, token analytics di halaman publik, Turnstile tak divalidasi server) — SEMUA
   jatuh ke None-list mereka ("all rate limiting / missing throttling", "CSRF with no or low impact",
   "data injection from clients to analytics tools", "manipulation client-side faking", web-archive
   links). Menyetel draft untuk semuanya = melanggar aturan program ("analysts not following the
   rules will not be eligible" / ban). Yang benar: tulis analisa scope-nya ke user, rekomendasikan
   JANGAN kirim, dan stage draft HANYA untuk yang lolos filter — kalau nol yang lolos, nol draft.
   ⛔ **Cek juga STATUS programnya, bukan cuma eksistensinya.** Halaman /bug-bounty vendor bisa
   menyatakan program "temporarily suspended" sementara security.txt + mailbox bugbounty@ masih
   aktif (CDN77, 2026-10-23: "due to an increased volume of invalid reports"; laporan sebelum
   30 Juni 2026 tetap diproses). Suspension ≠ kanal mati: draft TETAP distage kalau user minta,
   tapi flag ke user bahwa reward outlook tidak pasti dan keputusan kirim ada di user. Jangan
   auto-send ke program suspended; jangan juga skip staging hanya karena suspend.
   ⛔ **Dan sebelum "memperbaiki" deliverable lama, BUKTIKAN dulu deliverable-nya ada.** User bilang
   "perbaiki draftnya" (CoderPad 2026-10-17) — verifikasi menyeluruh (enumerasi SEMUA draft via
   `users/me/drafts?maxResults=500`, pencarian mailbox penuh incl. spam/trash, sweep disk engagement,
   session DB, agent log) menunjukkan NOL artefak target ada di mana pun: sesi sebelumnya tidak
   pernah persist apa pun. Menambal "draft lama" yang tidak ada = mengarang; hasil yang benar adalah
   bangun ulang dari nol dan katakan terus terang bahwa tidak ada yang bisa diperbaiki.
2. **Fase Cari Kontak** → buka `references/contact-discovery.md` (metode nyari dev/owner, crypto & non-crypto, + verifikasi pihak & enkripsi).
   Kalau permintaannya justru *mengaudit* `security.txt` sendiri → `references/security-txt-rfc9116-audit.md`
   (checklist RFC 9116 + mail-auth alamat kontak + review permukaan publik yang policy-nya izinkan).
   ⛔ **Alamat yang ditulis di SECURITY.md BELUM tentu hidup — verifikasi dulu sebelum percaya.**
   Cek `nslookup -type=MX <domain>` (MX `(root)` = null MX = domain tidak bisa terima email),
   `curl https://<domain>/.well-known/security.txt` (kalau redirect ke `/lander` = domain parkir),
   dan apakah domain lain yang disebut di repo (`.xyz/.app/.finance/.org`) malah NXDOMAIN.
   Kalau alamatnya mati → jangan stop, lanjut ke `references/github-pvr-submission.md`
   (jalur GitHub PVR + email maintainer dari commit author / situs pribadi owner).
   ⛔ **Dan kalau vendor menerbitkan DUA alamat berbeda (beda TLD!) di dua policy berbeda — pakai yang
   menaungi aset yang lo uji.** Kasus Vana 2026-10-12: `docs.vana.org/security/overview` → `dev@vana.org`
   (contracts + infrastructure), sementara `personal-server-ts/SECURITY.md` → `dev@vana.com` + subjek
   `[SECURITY] personal-server-ts - <desc>` (repo itu saja). Dua-duanya MX hidup, jadi yang menentukan
   bukan \"mana yang hidup\" tapi \"policy mana yang meng-cover aset ini\". Sebelum draft pertama:
   fetch policy-nya (docs Mintlify: tambahkan `.md` ke URL-nya untuk teks bersih), cek SEMUA `SECURITY.md`
   di estate, `nslookup -type=MX <domain>`, dan pastikan tidak ada program di HackerOne/Immunefi/Bugcrowd.
   Lalu pakai prefiks subjek `[SECURITY]` di semua draft (bahkan kalau policy yang satu tidak memintanya),
   kutip URL policy yang jadi dasar di badan email, dan tulis keputusannya ke `SUBMISSION-CHANNEL.md`
   di folder engagement. Prosedur + checklist: `references/submission-channel-verification.md`.
3. **Fase Kirim Email** → buka `references/report-templates.md` (template email disclosure + laporan teknis, ID/EN)
   Target punya **VDP sendiri** (bukan platform HackerOne/Bugcrowd)? → `references/vendor-vdp-submission.md`:
   cara nemuin kanal asli dari halaman policy-nya sendiri, enkripsi PGP ke key vendor, dan bikin
   **draft Gmail berkepala PDF (JANGAN kirim)** + verifikasi balik + prosedur re-auth OAuth kalau token mati.
   Mekanisme bikin draft-nya via REST API langsung (wrapper `google_api.py` nggak punya subcommand `draft`):
   `references/gmail-draft-via-api.md` — refresh token dari `google_token.json`, POST ke
   `users/me/drafts` dengan raw RFC822 base64url, lalu verifikasi dengan `gmail search in:draft`.
   Shortcut lokal yang hasilnya sama: `python gmail_ops.py draft --to X --subject Y --body Z
   --account <bounty_acct>` (`encode_mime` + `drafts().create`; body plain-text di-escape otomatis
   jadi `<pre>`). ⚠️ **`encode_mime` (dan shortcut `gmail_ops.py draft`) TIDAK dukung lampiran** — cuma
   text/plain + text/html). Buat draft DENGAN lampiran (.md/.txt/PDF): bangun `MIMEMultipart("mixed")`
      manual — ⛔ **set `m["To"]` + `m["Subject"]` DULU di MIMEMultipart sebelum attach apa pun** (From
      diisi otomatis Gmail dari akun). Lupa set To/Subject → `drafts().update(userId,draft,body=raw)`
      (atau `create`) menimpa draft jadi subjek+penerima KOSONG, dan user lihat email tanpa subjek/tujuan
      (bug nyata 2026-11-05, attach PDF ke draft webhook). Order aman: `m["To"] = to; m["Subject"] = subj`
      → bangun alt → attach lampiran. Lalu `alt = MIMEMultipart("alternative")` (attach `MIMEText(body,"plain")` + `MIMEText(html_pre(body),"html")`),
   lalu lampiran via `MIMEBase("text","markdown")` (atau `"application","pdf"`) → `set_payload(bytes)` →
   `encoders.encode_base64(att)` → `att.add_header("Content-Disposition","attachment",filename=...)` →
   `m.attach(alt); m.attach(att)`, terakhir `raw = base64.urlsafe_b64encode(m.as_bytes())` +
   `drafts().create(body={"message":{"raw":raw}})`. Verifikasi lampiran benar masuk: `references/gmail-draft-rest-verification.md`.
   ⚠️ `--account` WAJIB eksplisit ke akun bounty (mis. `RESEARCHER_USERNAME`) — tanpa flag,
   `pick_service()` default ke `accts[0]` yang bisa akun SALAH. Dan ingat: `DRAFT_EMAIL.txt` di disk
   BUKAN deliverable — user mengecek folder **Drafts di Gmail**, jadi "draft siap" = draft Gmail
   nyata yang dibuat, lalu konfirmasi draftId + To + Subject (bukan cuma path file lokal).
   **dan `references/gmail-draft-rest-verification.md`** — cara MEMBUKTIKAN lampiran PDF-nya benar-benar
   masuk: part `application/pdf` pakai `body.attachmentId` (BUKAN `body.data`, jadi loop yang cuma cek
   `data` akan bilang "lampiran hilang" dan bikin draft kembar), download via
   `messages/{msgId}/attachments/{aid}` + banding **sha256** dengan file lokal, pastikan **1 draft per
   temuan** per-subjek, dan staging per-batch (`stage_drafts.py`, `stage_drafts2.py`, …) supaya re-run
   tidak menduplikasi temuan yang sudah di-stage.
   **dan `references/first-contact-email-structure.md`** — bentuk wajib email KONTAK PERTAMA: 4 blok
   (perkenalan → isi teknis → lampiran non-temuan → penutup) + pitfall nyata.
   ⛔ **Email tidak boleh mulai dari "Summary".** Harus ada perkenalan: nama, peran, alamat + URL policy yang
   jadi dasar, apa yang direview dan bagaimana, temuan inti dalam satu kalimat, dan pernyataan eksplisit
   "tidak mengambil data / tidak mengubah state / berhenti ketika sudah jelas". Penutupnya wajib memuat
   penawaran konkret (kirim tangkapan mentah / uji ulang setelah fix), pilihan jaga-terbuka atau tutup, dan
   pernyataan tidak meminta kompensasi bila policy-nya tanpa reward. Koreksi user 2026-10-01:
   *"perbaiki dl draftnya, masa gkad perkenalan sama sekali"*.
4. **Butuh klasifikasi bug** (fase Triase/Impact) → `references/vuln-classes.md` (recognition cepat: web/API/infra/cloud, smart contract/web3, agent/LLM info-flow).

## Aturan anti-slop (non-negotiable)

1. **No PoC, no report.** Tiap klaim reproducible dengan bukti (log/screenshot/tx hash).
2. **Impact ditunjukin, bukan diklaim.** Demokan minimal & non-destruktif; jangan bikin kerusakan buat "ngebuktiin".
3. **Ulang ≥3×**, isolasi variabel, minimize payload/PoC.
4. **Ga bisa reproduce → buang.** Jangan overclaim severity, jangan filler.
   **Feasibility brute-force/ATO JANGAN diklaim "guaranteed/X jam" dari "unlimited attempts" doang.**
   Sebelum bilang ATO feasible, UKUR tiga hal (user menolak klaim teoritis 2026-11-01, conferencebadge):
   (a) **perilaku lockout** — hitung blokir per N percobaan: "too many attempts" yang nyala cuma
   ~1/200–4000 = kontrol rusak (pola `== max` bukan `>= max`, plus counter reset saat OTP baru);
   (b) **TTL OTP** — probe `INVALID_OTP` vs `OTP_EXPIRED` tiap interval ≥30 menit (OTP yang tidak
   expire = brute kontinu; yang expire singkat = brute per-window = probabilitas, bukan jaminan);
   (c) **ceiling rate sustained** — tes concurrency (hash lambat server bisa membatasi ~50 req/s,
   bukan 500). Baru hitung: jaminan 100% hanya kalau bisa exhaust 10^N sebelum TTL habis di rate
   itu. Tanpa ketiganya terukur, tulis "probabilitas tinggi, belum terbukti end-to-end" — bukan "pasti".
5. **Satu report = satu bug** yang jelas. Jangan gabung 10 "temuan" variasi teks.
   **N temuan berbeda = N draft terpisah + N PDF + N PoC — satu email hanya satu temuan.**
   Jangan pernah naruh semua temuan dalam satu draft "biar ringkas".
   ⛔ **N draft ke SATU vendor = N SUBJECT yang BERBEDA — jangan semua pakai subject generik identik.**
   Vendor sering menetapkan format subject generik ("Bug Bounty: P4", "[SECURITY]"). Kalau lo kirim
   beberapa temuan (semua P4 misalnya) dengan subject IDENTIK, Gmail & ticketing vendor (HelpScout/Zendesk)
   MERGE mereka jadi satu thread → vendor cuma baca & balas SATU, sisanya "hilang". Bukti nyata Porkbun
   2026-11-01: dua email subject persis "Bug Bounty: P4" → digabung satu thread → yang dibalas cuma
   returnUrl (ditolak "no demonstrated security impact"), temuan captcha ikut terlipat tak direview.
   FIX: tambah deskriptor unik ke tiap subject TANPA merusak prefix wajib — "Bug Bounty: P4 - PoW CAPTCHA
   bypass (email bombing)" vs "Bug Bounty: P4 - returnUrl open redirect". Prefix wajib vendor tetap di
   depan; deskriptor pendek (≤8 kata) di belakang membedakan satu-sama-lain. Kalau dua temuan sudah
   terlanjur ter-kirim subject sama & ter-merge → kirim ulang temuan yang "hilang" sebagai email BARU
   (thread terpisah), jangan reply thread lama. **KECUALI user minta eksplisit gabung** (2026-11-01 conferencebadge: "buat aja semua jadi satu draft email, gabungkan termasuk otp lockout" — untuk VDP email kecil, temuan satu-keluarga auth: OTP lockout→ATO + enumeration + health-leak digabung jadi satu email). Ikuti instruksi eksplisit itu; JANGAN menolak pakai aturan split. Default tetap split per-temuan untuk platform bounty (H1/Bugcrowd/Intigriti). Koreksi user 2026-10-04:
   *"perbaiki draftnya dulu, kan sy udh blg 1 draft 1 email 1 poc"*. Hanya rangkaian exploit
   nyata (chain attack) yang boleh digabung jadi satu report. Nama file lampiran harus
   mengandung ID temuan (`TrustLend-TL-07-Medium.pdf`) supaya tidak tertukar saat ada 12 draft.
   **Sisi sebaliknya: dua catatan temuan yang satu akar masalah = SATU draft, dan jumlahnya harus
   konsisten.** Kalau dua entri di `findings.json` punya host + alur request + file bukti yang sama,
   itu satu isu yang dipotong dua (Vana 2026-10-12: 8 temuan di record, 7 isu berbeda → VANA-05 adalah
   belahan kedua VANA-02 di `session-relay.vana.org`, bukti sama `session_webhook_ssrf.json`). Jangan
   bikin email kedelapan: triager membacanya sebagai duplikat. Yang wajib dilakukan: (a) tandai di
   `status`/`note` entri itu (“duplicate framing of <ID>'s second half”), (b) **verifikasi isinya benar
   ada di draft yang menaunginya** sebelum bilang ke user “cakupan lengkap” — grep artefak kirimannya
   (`Consent-integrity`, `fabricated`, `grant that does not exist` ada di email DAN PDF VANA-02), dan
   (c) kalau user tanya “kenapa kirim 7 padahal temuan 8”, jawab dengan tabel pemetaan draft→temuan.
   Sebutkan juga opsi memisahkannya, tapi rekomendasikan tetap tergabung.
7. **Kalau subjek draft harus berubah (mis. menambah prefiks `[SECURITY]`) → hapus lalu stage ulang,
   bukan menumpuk.** Cari draft lama per-subjek, `DELETE users/me/drafts/<id>` (respons Gmail = body
   KOSONG, jadi jangan `json.loads` tanpa guard — di sini `json.load` melempar JSONDecodeError dan
   membunuh script di iterasi pertama), lalu buat ulang dari `stage_drafts*.py` baru, dan tutup dengan
   verifikasi: **1 draft per temuan, To benar, dan attachment sha256 == file lokal**.
6. **Kirim ke pihak & kanal yang benar.** Verifikasi dulu, pakai kanal security khusus, enkripsi detail sensitif.
8. **Ditanya "sudah deepdive semua sisi pakai all tools? / semua fase lancar?" → jawab dengan LEDGER, bukan penenangan.**
   Aturan user 2026-10-12 (dua kali ditanya berturut-turut setelah laporan terkirim). Bentuk jawaban yang benar:   **(a) status gate apa adanya** (`audit-checkpoint <target> --phase all` → `33/33`, `verify-tool-usage` → `13/13`,
   `deep-audit guard` → OK, plus ledger `USED/N-A/NOT_RUN`); **(b) tool yang benar-benar jalan + jumlahnya**
   (entri `status:EXECUTED` di `tools-usage.json`, plus tool yang dijalankan manual dengan bukti di disk);
   **(c) angka coverage nyata** (host yang diprobe, URL crawl, request nuclei + **jumlah template error** sebagai
   caveat, jumlah subdomain, jumlah kontrak, dsb); **(d) daftar "BELUM diuji" yang eksplisit** — dan ini bagian
   terpenting. Jangan pernah bilang "semua sisi/all tools" kalau ada tool N/A dan permukaan yang belum disentuh;
   sebutkan juga fase yang **tidak mulus** (mis. gate gagal 3× lalu lolos setelah intervensi manual + patch script)
   kalau itu faktanya. Gap yang wajib disebut contohnya: **tidak ada sesi login apa pun** (jadi seluruh permukaan
   authenticated: IDOR/BOLA lintas-tenant, endpoint user/transactions/storages/files/settings, route admin via POST
   — bukan cuma penolakan GET), tidak ada operasi tulis/on-chain, tool web3 yang tidak jalan (aderyn/mythril/echidna/
   medusa), pemegang role on-chain belum dicek, jaringan lain (Moksha) belum diverifikasi, mobile/desktop belum di-RE,
   SSRF cuma terbukti buta, bot-protection yang membatasi tes otomatis di satu host.
   Tutup dengan penawaran prioritas untuk menutup gap terbesar (mis. sediakan satu akun tes → suite authenticated
   bisa jalan otomatis). Ini persis lawan dari "aman/matang" tanpa bukti yang dilarang di memory operator.
9. **Laporan progres PROAKTIF tiap chunk kerja — jangan diam beberapa turn (user, 2026-10-17).**
   *"tp kasih info progressnya, jgn diam aja"* — saat sebuah engagement berjalan lintas banyak turn
   (recon → scan → deep-dive), kirim update singkat setelah SETIAP chunk yang diselesaikan: apa yang
   baru diperiksa, artefak mana yang bertambah, apa temuan sementara, apa langkah berikutnya. Ledger
   lengkap tetap dikirim saat diminta; yang dilarang adalah turn panjang tanpa kabar.
   ⛔ **Dan jangan pernah menyajikan modul yang sudah direview sebagai "clean" sebagai kesimpulan.**
   Framing user (2026-10-17): *"tidak ada namanya clean code clean project, pasti ada celah"* —
   dan *"kerjakan perlahan2, pakai semua tools secara maksimal, jgn terburu2 mengambil keputusan"*.
   Bentuk aman: "modul X direview & verified sound pada ronde ini; sisa antrian: Y, Z" — selalu
   dengan daftar yang BELUM diperiksa. "Bersih" adalah klaim yang tidak bisa dibuktikan; antrian
   yang jujur bisa.

## Fase Koordinasi — balasan vendor, "sudah diperbaiki", dan minta akses

Setelah laporan terkirim, vendor biasanya balas. Tiga pola yang sering muncul, plus cara
menanganinya:

**1. Vendor bilang "confirmed and fixed" → uji ulang, dan uji SAMPAI SEMUA jalur tulis.**
Perbaikan biasanya dipasang di jalur yang mereka sebut (biasanya form create), sementara
jalur lain ke data yang sama (edit, delete, import, API) tetap terbuka. Selalu uji invarian
yang sama di create + edit + delete + import. Contoh nyata (Quarterwise, 2026-09): cek
kategori bertahan di add DAN edit, pengecekan relasi jumlah (`withheld < rent`) hanya di
create — lewat edit jumlahnya diterima, dan menghapus entri induk meninggalkan entri
turunan sebagai yatim (orphan) yang masih dihitung. Ini kelas temuan yang **paling dihargai
vendor** karena menutup perbaikan yang baru mereka rilis — dan tetap lacak sebagai Low kalau
memang self-scoped. Detail teknis Server Action ada di `nextjs-server-actions-audit`
(§ "Verifying a vendor's fix — and where fixes leak").

**2. Kalau framing kita yang salah → terima koreksinya secara eksplisit dan tulis itu di
balasan.** Jangan diam-diam diam atau membela klaim yang keliru; sebut bagian yang salah,
sebut yang benar menurut mereka, dan lanjut. Ini yang bikin vendor merekam temuan kita
sebagai kredit, bukan sebagai noise.

**3. Draft balasan = reply, bukan email baru. Threading porte-parole gampang salah.**
Jangan pilih pesan thread hanya dari "pesan terbaru dari domain program" — email
transaksional dari domain yang sama (contoh nyata: *"Security alert: Your password was
changed"*, *"Your <produk> code is 123456"*) akan membajak `In-Reply-To` dan draft kita
nyempil di thread yang salah. Pilih dengan **subject/kata kunci topik laporan**
(mis. cocokkan "validation gap" / judul laporan), lalu ambil Message-ID dari pesan itu
untuk `In-Reply-To` + `References`.

Aturan teknis saat menyiapkan draft via IMAP (append ke folder Draf, flag DRAFT, `X-Unsent: 1`):

```
[ ] Idempotent — script boleh dijalankan berkali-kali: hapus dulu draft yang KITA buat
    sebelumnya (kenali dari subject 'Re: <topik laporan>' yang kita generate), baru append
    yang baru. Jangan sampai mailbox numpuk draft kembar.
[ ] JANGAN hapus draft lain yang bukan buatan kita (mis. draft laporan awal yang user
    simpan sendiri) — cukup sebutkan keberadaannya ke user.
[ ] Verifikasi setelah append: ambil kembali draft-nya, cek To, Subject, In-Reply-To,
    daftar lampiran, dan panjang body. Jangan lapor "draft siap" tanpa verifikasi ini.
[ ] Isi klaim yang benar-benar faktual. Kalau di draft kita menulis "akun sudah terdaftar"
    padahal belum, ubah jadi kalimat yang benar di dua kondisi ("saya sedang membuat
    akunnya saat mengirim ini").
```

**4. Kalau vendor menawarkan akses (plan Pro / akun uji / 30 hari), jawab dengan alamat
akun yang tepat + daftar area yang akan diuji + patuhi batasannya secara tertulis.**
Contoh batasan yang harus dikutip balik di email: "jangan sambungkan akun pajak/pihak
ketiga, jangan submit apa pun ke sana". Catat juga apa yang jadi gate: kalau fitur
tambahan itu satu-satunya cara menembus permukaan yang belum diuji, siapkan harness uji
DULU supaya begitu akses turun tinggal dijalankan.

**5. Kalau triager menunjuk satu endpoint dan bilang "bikin report terpisah + demonstrasi
konkret, mungkin eligible" → bikin dokumen STANDALONE yang menjawab persis pertanyaannya.**
Jangan kirim versi tambahan dari laporan lama. Yang mereka minta:

```
[ ] Berdiri sendiri — bukan "addendum v4", bukan "updated version". Judul & isi fokus 1 endpoint.
[ ] BAGIAN 2 = demonstrasi konkret itu sendiri: tabel beberapa tenant BERBEDA, menampilkan
    nilai yang benar-benar dikembalikan ke pemanggil TANPA auth (secret ditulis prefix+length,
    respons mentah masuk evidence bundle).
[ ] Jawab istilah yang MEREKA pakai, secara eksplisit. Kalau mereka bilang "across tenants",
    bedakan dua tafsirnya: (a) data milik SEMUA tenant bisa dibaca = biasanya BENAR &
    terbukti; (b) tenant A bisa baca config tenant B = biasanya SALAH. Laporkan (a),
    nyatakan (b) sudah diuji dan gagal, dan minta mereka menilai atas dasar itu.
[ ] Tambahkan kalimat biaya-panen ("1 GET per hostname, dari daftar yang sudah publik di
    certificate transparency") — itu pembeda antara "config satu tenant bocor" dan
    "config SEMUA tenant bocor".
[ ] Bab "yang TIDAK bisa saya lakukan" ditulis terang-terangan. Ini yang mencegah triager
    menutup laporan sebagai "tidak reproducible" saat tes cross-tenant mereka sendiri gagal.
[ ] Sebutkan kelas mereka sendiri di badan email (mis. "CWE-200 + CWE-306, sesuai kelas
    information-exposure / missing-authentication").
```

**6. Draft email baru dibuat SETELAH ada temuan yang dikonfirmasi — bukan sebelumnya.**
Aturan user (2026-09-30): *"draft kalau ada temuan aja, kl gkad deepdive lagi, pastikan bukan
cm curl tp semua tools dipakai."* Terjemahannya:

- Belum ada temuan untuk kelas yang diminta → **jangan siapkan deliverable apa pun**; lanjut
  gali dengan toolset penuh (bukan cuma curl), dan tutup gap yang belum jalan.
- Sudah ada temuan → baru siapkan draft, dan **ganti** draft lama kalau ada (jangan menumpuk).
- Kalau ternyata dokumennya berubah lagi setelah gali lebih dalam, **perbarui draft yang sama**
  (hapus yang lama, append yang baru) — jangan tinggalkan dua draft dengan subjek mirip.
- Selalu tutup dengan pernyataan eksplisit: belum dikirim, folder + uid, lampiran + ukurannya.

---

## Output

Deliverable: temuan tervalidasi → kontak dev/owner terverifikasi → email disclosure + laporan teknis (bahasa ngikutin target, ID/EN, nada natural & teknis) → catatan koordinasi/timeline.
