---
name: signup-block-ops
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  What to do when signup is blocked during authorized testing: email verification,
  phone/SMS, CAPTCHA, invite-only, IP/rate blocks, and disposable-email walls.
  Ordered ladder, each step naming the tool already installed.
metadata:
  hermes:
    tags: [security, signup, blocked, captcha, sms, disposable-email, bug-bounty]
---

# Signup Block Ops — saat pembuatan akun uji terblokir

**Prinsip:** blokir pendaftaran adalah **penghalang operasional**, bukan temuan. Tugasmu
melewatinya secara sah — tapi kalau policy target melarang, tandai `not-tested` dan lanjut.
Ini tangga eskalasi, bukan daftar trik.

---

## Tangga eskalasi (urut, jangan lompat)

### 0. SEBELUM tangga: pastikan form yang kamu isi itu form ASLI

Banyak vendor modern menaruh **honeypot off-screen** di dokumen utama dan memindahkan input
sungguhan ke **iframe cross-origin**. Kalau tidak dicek dulu, kamu akan berjam-jam mengisi field
palsu lalu menyimpulkan "signup diblokir" padahal gate-nya belum pernah tersentuh.

**Cek 30 detik — dump semua input dengan geometri + visibility:**
```python
pg.evaluate("""() => Array.from(document.querySelectorAll('input')).map(e => {
  const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
  return {id:e.id, type:e.type, x:Math.round(r.x), y:Math.round(r.y),
          w:Math.round(r.width), vis:s.visibility, ariaHidden:e.closest('[aria-hidden="true"]')!==null};
})""")
print(pg.evaluate("()=>Array.from(document.querySelectorAll('iframe')).map(f=>f.src)"))
```
**Tanda honeypot** (semua harus dianggap red flag):
- bounding box nyata (`w > 0`) tapi koordinat **negatif** — `x = -956`, atau CSS
  `--left-custom: -1000px; --top-custom: -1000px`
- induk ber-`aria-hidden="true"` dan/atau `visibility: hidden`
- nama field terlalu menggoda (`email`, `username`) sementara label yang terlihat tidak cocok
- ada `<iframe src=".../challenge/v4/html?Type=0&Name=email" sandbox="allow-scripts allow-same-origin allow-popups">`

**Kalau input asli ada di iframe:** isi lewat `frame.fill()` / `frame.locator().type()` memang bisa
masuk ke DOM frame, **tapi biasanya tidak mem-propagate ke state React induk** — parent tetap bilang
"This field is required" walau `frame.evaluate(()=>input.value)` berisi. Itu **bukti gate bekerja**,
bukan petunjuk cara bypass. Berhenti di sini dan catat sebagai kontrol yang berfungsi.

### 0b. Jangan menyimpulkan "tidak bisa" sebelum tabel pendekatan
Aturan yang diminta operator: **enumerasi pendekatan dalam tabel sebelum menyatakan BLOCKED.**
Satu percobaan gagal ≠ blocked. Format yang diterima:
```
| # | Pendekatan | Hasil |
| 1 | playwright klik plan + isi #username | state plan tak berubah (payment check tetap bundle2022) |
| 2 | mouse fisik di koordinat kartu       | aria-pressed=true, form tetap tersembunyi |
...
```
Tanpa tabel + akar masalah, jawaban "tidak bisa bikin akun sendiri" akan (dan pernah) ditolak balik
oleh operator. Kalau ragu, baca ulang: dia minta **dikerjakan**, bukan dijelaskan kenapa sulit.

### 1. Email verifikasi — paling umum
| situasi | solusi |
|---|---|
| Butuh email korporat (`@perusahaan`) | cari domain yang menerima semua email (catch-all), atau cari form invite |
| Email sekali-pakai diblokir | gandi provider: `mail.tm` → `temp-mail` → Gmail alias (`+tag`) |
| Link verifikasi tak datang | cek spam; cek MX domain; coba lagi dgn delay 60s; cek apakah domain diblokir (Spamhaus) |
| **Yang datang KODE 6 digit, bukan link** | jangan tunggu `<a href>`; baca isi `m.text` dan kirim kode ke endpoint aktivasi (lihat di bawah) |

**Alat:** `mail.tm` API (gratis, tanpa akun) · Gmail `+tag` (`RESEARCHER_USERNAME+test1@gmail.com`)

**Kode ≠ link — cek bentuk pesannya dulu.** Banyak flow modern mengirim **kode** di dalam body, dan
menggrep `href` pada email itu hanya menghasilkan link logo/support. Gejalanya: "link tidak ditemukan"
padahal email sudah masuk. Baca `m.text` (bukan hanya `m.html`) — kodenya biasanya berdiri sendiri di
barisnya sendiri.

Contoh nyata (SimpleLogin, 2026-10-25 — subjek "Just one more step to join SimpleLogin"):

1. Baca kode dari IMAP: `m.text` -> `765128`.
2. Temukan bentuk endpoint dengan **diferensial**, bukan tebakan. `POST /api/auth/activate`:
   | body | hasil |
   |---|---|
   | `{"code":"765128"}` | `500 Internal error` |
   | `{"activation_code":"765128"}` | `500 Internal error` |
   | `{"email":"...","code":"765128"}` | `200 {"msg":"Account is activated..."}` |
3. **`500` di sini bukan berarti endpoint rusak** — itu body yang salah bentuk. Jangan coret endpoint
   karena 500; coret setelah ≥2 bentuk berbeda gagal. Bandingkan juga dengan `404 No such endpoint`
   (path salah) dan `400 request body cannot be empty` (content-type salah): tiga kode berbeda =
   tiga kegagalan berbeda, dan hanya satu yang berarti "endpoint tidak ada".

**Jangan percaya kredensial yang tampil teredaksi.** File yang di-`cat` tampil sebagai
`APP_PASSWORD=***` itu **redaksi lapisan tampilan**, bukan isi file. Membaca balik string literal `***`
lalu gagal login adalah kesalahan sendiri, bukan kredensial mati. Baca nilainya dengan regex dari file
mentah dan cetak **hanya panjangnya**: kalau butuh 16 karakter alfanumerik untuk app password Gmail,
panjang 16 = kredensial ada; login gagal baru berarti benar-benar mati.

**Alat:** `mail.tm` API (gratis, tanpa akun) · Gmail `+tag` (`RESEARCHER_USERNAME+test1@gmail.com`)

### 1b. Domain-keyed blocklists vs address-keyed uniqueness — the winning variant is an ALTERNATE DOMAIN

Measured 2026-10-28 (binobi.com, casino platform with `error_auth_register_disposable_email`).
`+tag` alone is **not** the answer, and assuming it is wastes a round:

| variant of the same mailbox | result | why |
|---|---|---|
| `user+tag1@gmail.com` on an address already used | `409 duplicate_register_email` | uniqueness is on the **literal address string**, plus-address is not normalised |
| `usertag2@gmail.com`, `us.er3@gmail.com` | `409 duplicate` / `500` | dot-removal collides back to the base mailbox; some shapes crash the unique check |
| `user@googlemail.com` (alternate domain, same inbox) | **`201` + full session** | different **domain string**, so both the disposable filter and the uniqueness check pass |

Rule: when the signup rejects `@gmail.com`, stop iterating on `+tag`/dots of the same address and
switch the **domain** to another name that routes into the same mailbox you can already read —
`gmail.com` ↔ `googlemail.com` is the classic pair (also: any custom-domain alias you own,
`outlook.com` ↔ `hotmail.com`). The account is still yours, the inbox is still IMAP-readable, and it
survives both checks.

**Ordering you must know before probing the blocklist:** the captcha gate is evaluated **before** the
disposable-domain check. With a dummy token *every* domain — including ones that would be rejected —
returns `401 error_auth_captcha_failed`. So you cannot map the blocklist cheaply with a fake token;
you need one real Turnstile solve per candidate. Budget for that, and do not read the uniform 401 as
"domain accepted".

**A `500` on the register endpoint for some address shapes is a finding, not noise.** `fz.susanto13@…`
and `user+tag@…` produced `500 Internal server error` while the sibling shape returned `201` — an
unhandled unique-constraint path. Capture it as an Informational/quality finding in the same report
(the payload is the exact address that crashes it); do not discard it because registration
"otherwise worked".

### 1c. Business-email gate yang ASYNC ("pending → failed"), bukan synchronous /error

Terukur 2026-11-02 (scoro.com). Ada DUA mode tolak email; cara mendeteksinya beda dan
salah baca = 5 percobaan sia-sia. Bedakan dulu:

| bentuk respons | artinya |
|---|---|
| `303 → /error` seketika | domain invalid / tak ada MX — **synchronous**, ketahuan langsung |
| `303 → root` + `Set-Cookie` session, lalu `GET /api/status` → `pending` → `failed` (beberapa menit) | domain valid & lolos cek awal, tapi provider email gratis (gmail/outlook/dll) **ditolak ASYNC** di background job |

Implikasi penting: `+tag` / dot-variant (§1b) **tidak menolong** di sini — ini denylist lebar
di level *provider*, bukan uniqueness per-address. Butuh domain bisnis sungguhan, atau jalur SSO
(Google/Microsoft) dengan account work. Jangan buang 5 percobaan memutar-mutar alias gmail.

**Decode state-machine dari cookie session-nya sendiri (tanpa terima email):** banyak flow
lama/email mengeluarkan cookie `X_session` = `payload.signature` (base64url). Payload sering
sudah memuat token magic-link — jadi kamu bisa lihat state account tanpa menunggu inbox.
Contoh nyata: `scoro_create_site__session` → `{email, firstName, lastName, provider, createSiteHash, expiresAt, issuedAt}`. `createSiteHash` adalah token link verifikasi yang **tertanam di cookie-mu sendiri**:

```python
import base64, json
seg = cookie.split(".")[0]
payload = json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))
print(payload)  # -> {'email': ..., 'provider': 'email', 'createSiteHash': '41tskm2...', ...}
```

Dari situ: (a) `provider` menandakan jalur daftar (email vs oauth), (b) `status` polling
(`pending`→`ready`/`failed`) mengungkap hasil provisioning tanpa inbox, (c) hash magic-link
bisa dipakai untuk probe endpoint verifikasi (`/verify?hash=`, `/api/verify`, dst). Ganti
buta menunggu email dengan baca state server langsung.

**Jebakan yang paling sering membuang waktu (2026-10-25):** verifikasi email bukan soal "punya
alamat", tapi soal **"bisa membaca inbox-nya"**. Sebelum menaiki tangga, pastikan ada satu jalur baca
yang hidup dan uji dengan satu pesan nyata. Kalau jalur baca mati (mis. app-password Gmail sudah
di-revoke, OAuth refresh token mati), SEMUA langkah di bawah akan gagal dan terlihat seperti "target
memblokir pendaftaran" padahal masalahnya di sisi kita.

**Aturan eskalasi dini:** begitu ketahuan tidak ada mailbox yang bisa dibaca, **lapor operator di
giliran itu juga** (minta app-password baru / kerjakan signup manual di browser headed) — jangan
habiskan 3 percobaan tangga dulu. Blocker ini mematikan seluruh kelas BOLA/IDOR lintas-tenant, jadi
harganya jauh lebih mahal daripada satu pesan minta bantuan.

### 2. CAPTCHA
| tipe | alat |
|---|---|
| reCAPTCHA v2 / v3 | **Camoufox** (terbukti tembus v2 invisible tanpa interaksi) |
| Cloudflare Turnstile | **SeleniumBase MCP** `mcp__seleniumbase__solve_captcha`, ATAU §2b (Playwright + Chrome asli headed) |
| hCaptcha / DataDome | SeleniumBase `solve_captcha` |
| Image CAPTCHA | Camoufox + delay + perilaku manusia |
| **PoW / computational** (custom sha256 proof-of-work, e.g. "Pork Captcha") | jangan dipaksa lewat browser — reverse client JS, mine nonce, POST ke endpoint challenge (lihat §2d) |

**Urutan:** Camoufox dulu (gratis, stealth) → SeleniumBase `solve_captcha` (butuh gateway restart, sudah aktif)
→ §2b kalau jalur browser-MCP tidak terpasang/ter-attach di host itu.

### 2d. PoW / computational CAPTCHA — mine it, don't click it

Sebagian target menaruh **proof-of-work buatan sendiri** sebagai captcha (bukan Turnstile/reCAPTCHA).
Contoh nyata: Porkbun "Pork Captcha V1.3.1" — SHA-256 PoW dengan target **12-bit** (`minDifficulty:12`),
~4096 hash, terpecahkan 6–23 ms di Python stdlib. Ini golongan captcha yang **bukan** soal stealth/browser;
ia soal baca JS-nya lalu tiru alurnya lewat HTTP langsung. Literal klik-widget di sini buang waktu.

Cara mengenalinya sebelum buang 30 menit:
- widget "captcha" custom (`data-role="pork-checkbox"`, teks "Pork Captcha Vx.y") bukan `challenges.cloudflare.com`
- ada endpoint `*/captchaIssue` + `*/captchaChallenge` (atau sejenis) yang bolak-balik `{challenge, challengeToken, difficulty}`
- client JS berisi loop `sha256(challenge + nonce)` yang mencari prefix hash tertentu (`makeTarget`, `targetHexPrefix`)

Resep minim (stdlib saja, tanpa browser):
1. `POST /tools/<x>Issue {"sitekey":"..."}` → `{challenge, challengeToken, difficulty}`.
2. Mine nonce N: `sha256("<challenge>"+str(N))` diawali `"0"*(difficulty//4)` (untuk sisa bit pakai nibble `< 1<<(4-remainder)`).
3. `POST /tools/<x>Challenge {challengeToken, nonce, difficulty, action, ...}` → `{token}` (biasanya JWT).
4. Pakai token itu sebagai field form / `pcaptcharesponse` di POST pendaftaran.

Kalau `difficulty` kecil (≤16 bit) ini **sekaligus temuan** (insufficient anti-automation → P4): captcha
itu tidak menghalangi bot sama sekali, dan sering membuka vektor email-bombing — endpoint "kirim kode
verifikasi" yang cuma dijaga captcha tak berguna bisa dipakai spam alamat arbitrer. Catat sebagai temuan
sendiri, jangan cuma dipakai diam-diam untuk daftar. Flow penuh + script solver: skill `porkbun-audit`
(`scripts/porkbun_pow_solver.py`).

**Gate lain yang muncul SETELAH captcha lolos:** beberapa target kini nempel **ID/KYC verification**
(foto KTP) untuk akun baru — terutama dari IP datacenter/Cloudflare. Itu anti-fraud sah, **bukan** pintu
yang boleh dibuka dengan data palsu (lihat tabel "Yang TIDAK boleh dilakukan"). Kalau ini yang memblokir,
berhenti daftar otomatis → pakai sandbox/test-API kalau ada, atau serah-terima ke operator (§9).

### 2b. Turnstile di signup SPA — resep yang benar-benar bekerja (terukur 2026-10-31)

Gejala khas: field terisi, tapi submit tidak mengirim request apa pun dan halaman diam di
"Complete verification to register". Sebelum menyebut ini blokir, lakukan empat hal ini:

1. **Jangan tebak selektor tombol submit.** Dump dulu — satu klik salah = timeout berulang yang
   terbaca seperti "diblokir":
   ```js
   [...document.querySelectorAll('input')].map(i=>i.id+'|'+i.name+'|'+i.type)
   [...document.querySelectorAll('button')].map(b=>b.textContent.trim()+'|'+b.id+'|'+b.className)
   ```
   Terukur: tombol yang benar `button#registerNow` (class `btn btn-blue`); `button.btn-orange` justru
   tombol *pembuka* panel register — klik itu sukses membuka panel, lalu klik kedua ke selektor sama
   timeout 10 s dan tes terlihat mati.
2. **Ambil sitekey dari global**, jangan dari HTML: `window.turnstileSiteKey` (widget container
   biasanya `#registerTurnstile`, script `challenges.cloudflare.com/turnstile/v0/api.js?...render=explicit`).
3. **Jalankan Chrome asli headed** lewat Playwright persistent context — Turnstile *appearance:always*
   selesai sendiri di sana:
   ```python
   ctx = pw.chromium.launch_persistent_context(profile_dir, channel="chrome", headless=False,
       args=["--disable-blink-features=AutomationControlled"], locale="en-US", timezone_id="Asia/Jakarta")
   ```
   Submit sungguhan (klik tombol asli) → tunggu token.
4. **Poll token, jangan pakai `sleep` buta:** `window.turnstile.getResponse()`; berhenti begitu string
   token keluar (≈5–10 s). Setelah akun jadi: `ctx.storage_state()` lalu replay cookie ke
   `requests.Session` — seluruh matriks API lanjut tanpa browser.

Pitfall yang sudah memakan waktu:
- `getResponse()` melempar `Could not find widget` **sebelum** widget di-`execute` (mode eksplisit) —
  normal, bukan blocker; panggil setelah submit.
- **Token bisa tidak pernah terbaca padahal pendaftaran SUKSES.** Terukur 2026-10-31 (Scribble Maps,
  akun kedua + akun utama): `#registerTurnstile` punya rect 300×69, `document.querySelectorAll('iframe')`
  kosong (widget hidup di shadow DOM), `getResponse()` tetap `null` setelah 90 s — tapi akun terbuat dan
  `/api/account` balas 200. **Jangan simpulkan "Turnstile gagal" dari token yang tidak muncul**; verifikasi
  lewat API akun (`GET /api/account` → email/userId), dan kalau 200 maka signup berhasil.
- Kalau login gagal (`Login Failed`) itu justru sinyal akun **belum ada** → lanjut ke jalur register
  dengan kredensial yang sama, jangan diulang login-nya.
- `page.screenshot()` bisa timeout menunggu font di app berat; jangan jadikan blocker, keluarkan
  screenshot dari alur otomatis.
- Endpoint register yang membalas `{"error":"Captcha required"}` untuk request tanpa token adalah
  **gate yang bekerja** — jangan dicatat sebagai endpoint rusak.
- Jangan `fill()` semua input membabi buta kalau ada honeypot (lihat §0/§8) — dump geometri dulu.

**Widget inline (bukan mode `execute`) butuh KLIK, bukan polling.** Terukur 2026-10-31 di portal
laporan Scribble Maps (`div.cf-turnstile#turnstile-widget`, `data-sitekey` beda dari signup): widget
punya rect nyata (1261×72), `getResponse()` `null` selamanya, dan **klik di dalam widget** menghasilkan
token dalam ~4 detik. Pola yang bekerja:

```python
rect = pg.evaluate("()=>{const el=document.getElementById('turnstile-widget');"
                   "if(!el)return null;const r=el.getBoundingClientRect();"
                   "return [r.x,r.y,r.width,r.height]}")
if rect and rect[2] > 20:
    pg.mouse.click(rect[0]+36, rect[1]+rect[3]/2)   # checkbox ada di kiri, tengah vertikal
    for _ in range(45):
        time.sleep(1)
        if pg.evaluate("()=>{try{return window.turnstile.getResponse('#turnstile-widget')}catch(e){return null}}"):
            break
```
Klik berulang (3×) di widget yang sama tidak menambah peluang — kalau attempt pertama tidak
menghasilkan token, Cloudflare sedang menantang; tunggu cooldown, jangan spam klik.

### 2c. Sesi kedaluwarsa & dialog "logged in elsewhere" (refresh sebelum kerja API)

Sesi cookie di target multi-app (www / api / team subdomain) **akan** kedaluwarsa di tengah
engagement — gejalanya `401` mendadak pada endpoint yang baru saja berhasil. Jangan salah baca
sebagai "authz berubah" atau "endpoint mati":

1. **Refresh dulu, baru simpulkan.** Buka ulang profil persisten di Chrome headed, biarkan app
   memuat, lalu `ctx.storage_state(path=...)` dan replay cookie ke `requests.Session`.
2. **Dialog "You are logged in elsewhere. Logout other location?"** muncul kalau sesi lama masih
   dianggap aktif (mis. browser sebelumnya belum ditutup). Klik **YES** — kalau tidak, login
   "berhasil" tapi `/api/account` tetap 401:
   ```python
   if "logged in elsewhere" in pg.inner_text("body").lower():
       pg.evaluate("""()=>{const b=[...document.querySelectorAll('button,a,div')]
         .filter(e=>e.children.length===0&&/^\\s*YES\\s*$/i.test(e.textContent));
         const v=b.find(e=>e.offsetParent!==null); if(v) v.click();}""")
   ```
3. **Verifikasi identitas sesi sebelum dipakai** (`GET /api/account` → email + userId), karena
   beberapa matriks authz bergantung pada userId yang tepat.

Script lengkap (signup → token → `storage_state` → validasi `/api/account`): 
`references/turnstile-signup-playwright.md`.

### 3. Nomor telepon / SMS
| situasi | solusi |
|---|---|
| Butuh SMS verifikasi | layanan SMS sekali-pakai (mis. `5sim`, `sms-activate`) — **pakai nomor milikmu kalau bisa** |
| Nomor asing diblokir | ganti negara (lihat `geo-block-proxy-ops`) |
| Ada opsi "verifikasi nanti" | pakai itu — banyak aplikasi izinkan akses terbatas sebelum verifikasi |

**Aturan etika:** jangan pakai nomor orang lain. Kalau tak ada opsi sah, tandai `not-tested`.

### 4. Invite-only / waitlist
| situasi | solusi |
|---|---|
| Butuh undangan | cari halaman publik yang tak butuh akun; cek API mobile (sering tanpa gate) |
| Ada program referral | **jangan** bikin akun massal — langgar ToS |
| Trial tanpa kartu | pakai itu |

**Alternatif yang sering berhasil:** **API mobile / endpoint lama** sering tak punya gate
pendaftaran sama sekali. Itu surface yang sah diuji (lihat `hunt-shadow-api`).

### 5. IP / rate block saat mendaftar
| situasi | solusi |
|---|---|
| Terblokir setelah 1× daftar | `proxy_run.py` ganti IP |
| WAF blokir datacenter IP | proxy residensial |
| Blokir negara | `geo_session.py` (fingerprint konsisten) |

### 6. Approval manual (admin setuju)
| situasi | solusi |
|---|---|
| Butuh persetujuan admin | cari tenant/organisasi yang izinkan self-signup |
| Workspace butuh domain email | daftar dgn email samaran di domain milikmu sendiri |

### 7. Registration API sebagai attack surface (walau pendaftaran gagal total)

Bahkan kalau akun **tidak pernah selesai dibuat**, flow pendaftaran yang sudah ter-map adalah
surface yang sah diuji — dan sering memuat temuan kelas sendiri (hit live 2026-10-25, mail.com/
GMX shared flexreg backend):

- **Map API-nya dari network capture**, bukan dari tebak-tebakan path. Jalankan wizard pendaftaran
  di Camoufox/Playwright sampai mentok, tangkap setiap `fetch`/XHR (method, URL, content-type,
  body, response). Endpoint khas: `/config` (minta `registrationFlowId`), `/captcha-verification`,
  `/personal-info`, `/aliases`, `/address-details`, `/password-check`, `/mtan`. Header
  identitas app (`x-ui-app: flexreg/2.14.1`) biasanya wajib.
- **Alias/email availability = account-enumeration oracle.** `POST .../aliases` dengan
  `wishAlias` balik `{"available":true|false}` — cek role addresses yang pasti ada
  (postmaster@, admin@, abuse@) vs string random; 100% diskriminasi = oracle valid. Ini temuan
  kelas CWE-204 terpisah, bukan bagian dari "gagal daftar".
- **Flow-ID/cookie binding harus diuji, jangan diasumsikan.** Cookie flow (`reg-flow-data0/1`)
  biasanya terenkripsi → tidak forgedable (negative result yang baik untuk dilaporkan). Random
  flow-ID + cookie asli → harus ditolak (`cookie-validation-error`).
- **Kalau UI bail-out ke halaman help/error (anti-automation), API-nya sering MASIH hidup.**
  Jangan berhenti di "wizard-nya redirect" — blokir navigasi bail-out (`page.route('**hilfe...**', abort)`)
  biar JS context tetap hidup, lalu panggil endpoint via `page.evaluate(fetch)` dengan
  `credentials:'include'` (tanpa itu cookie tidak ikut → 401 palsu). Detail: skill
  `bot-protected-target-testing`.
- **Anti-enumeration mereka bisa nyala setelah probing berulang** (`denial-error` pada endpoint
  availability). Itu bukan alasan stop — itu bukti endpoint sensitif; catat sebagai honest
  limitation di laporan ("oracle deterministik; platform menambahkan throttling setelah probing
  sustained").
- **Rate-limit window-nya per-flow, bukan per-IP-selamanya.** Kalau attempt ke-N ke-blok, tunggu
  cooldown (~20–60 menit) dan pakai flow baru; loop retry yang bail terlalu awal (cek "UI redirect")
  akan salah simpulkan "blocked permanen" — cek state API-nya langsung, jangan percaya state UI.

### 7b. Pola yang BERHASIL: IMAP + activation-code endpoint (bukan magic link)

Terbukti 2026-10-25 (SimpleLogin, produk in-scope Proton): akun uji bisa diprovision sendiri
end-to-end tanpa interaksi operator, walau email aktivasi berisi **kode 6 digit**, bukan link.

1. Daftar via API: `POST /api/auth/register {email, password, password_confirm}` → `200 {"msg":"User needs to confirm their account"}`
   (pakai app-password Gmail yang benar-benar bisa di-IMAP; disposable domain biasanya ditolak balik)
2. Ambil kode dari inbox sendiri: `imap_tools` + filter `subject`/`from`, baca **`m.text`** —
   link di `m.html` sering cuma logo/support, kodenya ada di teks.
3. **Temukan bentuk endpoint aktivasi dengan diferensial**, jangan menebak-nebak:
   | body | hasil |
   |---|---|
   | `{"code": "..."}` | `500 Internal error` (endpoint ADA, body salah) |
   | `{"Code": "..."}` | `500` |
   | `{"email": ..., "code": ...}` | `200 {"msg":"Account is activated..."}` |
   `500` pada satu bentuk + `200` pada bentuk lain = endpoint ketemu; `404 "No such endpoint"` = path salah.
4. Login: `POST /api/auth/login {email, password}` → **`api_key`** (bukan cookie sesi — dipakai sebagai
   header `Authentication: <api_key>`, bukan `Authorization: Bearer`).

Catatan: banyak layanan menormalkan plus-address (`user+tag@gmail.com` → `user@gmail.com`) saat login;
tetap satu identitas, dan itu harus disebut di laporan kalau dipakai untuk uji diferensial.

### 7c. Kalau produk punya CLI/alternatif mobile
Endpoint mobile/lama sering tanpa gate pendaftaran (lihat `hunt-shadow-api`). Cek `api.<domain>`
versi lama dan header `x-pm-appversion`-style sebelum menyerah.

### 8. Form-level decoys — "the field is in the DOM" ≠ "the field is usable"

Measured 2026-10-25 (Proton signup). Before concluding a form is broken or that automation "should"
work, classify **every** input by geometry, not by selector existence:

```js
Array.from(document.querySelectorAll('input')).map(e => {
  const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  return {id: e.id, type: e.type, x: Math.round(r.x), y: Math.round(r.y),
          w: Math.round(r.width), h: Math.round(r.height),
          vis: s.visibility, disp: s.display};
})
```

The tell: `#username` had a **real 222×34 box but `visibility:hidden` with `x = -956`** — an
off-screen decoy. `#password` was the only genuinely visible input. Proton's wizard ships that decoy
specifically to swallow "fill every input" automation.

- **Never force it.** Setting `style.visibility='visible'` then clicking yields
  `Element is outside of the viewport` and **zero POST** — a wasted round that reads like a block.
  Same for JS `.click()` on a hidden field.
- **`aria-pressed` / `aria-checked` flipping is not progress.** The plan card went to
  `aria-pressed=true` while the account fields stayed hidden. Verify the *field* became usable.
- **Keyboard path is a real test, not a workaround.** 40 `Tab` presses that never land on a visible
  text input *is* evidence the visible form has no such input — that belongs in the N/A reason.
- **Telemetry leak tells you where you are**: Proton emitted `random_uid_created` (address
  pre-generated) before any submit. If a hidden flow says "created", a submit path exists that you
  are not reaching — say that, don't call the flow dead.
- **Verdict wording:** an anti-automation gate that holds is a **working control** = coverage limit
  with a named unlock (manual signup / different egress / sibling product). Never "target bersih",
  never a bug report.

### 9. When the flagship signup is gated, try the SIBLING product in the same scope

Same session, same IP, same browser: Proton signup was unpassable (decoy + HV gate), but
**SimpleLogin** — another in-scope product of the same vendor — self-provisioned on the first try.
Before writing "no test account possible", enumerate every in-scope *product* (not just the main app)
and try each signup: subsidiary SaaS, alias/mailbox services, docs/sheets suites and freshly-acquired
products usually run their own registration stack with their own (weaker) gates. One working sibling
identity is often enough to unblock the flagship's authenticated surface.

### 7b. Langkah AKTIVASI setelah daftar (jangan berhenti di "signup sukses")

Banyak produk menerima `POST /register` → `200 {"msg":"needs confirmation"}`, lalu mengirim **kode 6
digit** (bukan link) yang harus dimasukkan ke endpoint aktivasi. Tanpa langkah ini akun tetap
`Account not activated` (`422`) dan seluruh surface produk tidak bisa diuji. Terukur 2026-10-25
(SimpleLogin): signup sukses tapi login `422 Account not activated` sampai kode dimasukkan.

1. **Ambil kode/ link dari inbox**: `imap_tools` ke Gmail — cari `from`/`subject` brand, lalu regex
   `\b\d{6}\b` dari `m.text` (kirimannya sering hanya teks, tanpa link sama sekali).
2. **Kalau nama endpoint aktivasi tidak ada di bundle** (app server-rendered / Flask / htmx — bundle
   hanya berisi jQuery + vendor, nol string `/api/`), **jangan menyerah**: probe kandidat
   `POST /api/auth/activate|activation|confirm`, lalu pakai **diferensial bentuk payload** untuk
   menemukan field yang wajib. Ini pola yang berulang:
   | payload | hasil | artinya |
   |---|---|---|
   | `{"code":"123456"}` | `500 Internal error` | endpoint ADA, field kurang / salah nama |
   | `{"Code":"123456"}` | `500` | nama field case-sensitive |
   | form-urlencoded | `400 request body cannot be empty` | endpoint **hanya** menerima JSON |
   | `{"email":…,"code":"…"}` | `200 {"msg":"Account is activated…"}` | bentuk benar |
   Pelajaran umum: **generik 500 dari endpoint ber-auth = payload salah, bukan endpoint tidak ada.**
   `400/422 "cannot be empty"` = bentuk transport salah. `404 No such endpoint` baru berarti tidak ada.
3. Login ulang setelah aktivasi; kalau sukses, simpan **API key / token** yang dikembalikan — di
   SimpleLogin `POST /api/auth/login` mengembalikan `api_key` 60 char yang dipakai sebagai header
   `Authentication: <key>` (bukan `Authorization: Bearer`, bukan cookie). Cek cara auth-nya dengan
   memanggil satu endpoint yang sudah pasti ada: `401/403` dengan cookie saja → ganti ke header key.

```


```
Coba 3 pendekatan BERBEDA  ->  kalau semua gagal  ->  tandai N/A + alasan
```

**N/A yang sah:**
```
"signup blocked: email verification requires corporate domain; mobile API also
gated; tried mail.tm + Gmail alias + invite page (3 approaches) — not-tested"
```

**N/A yang DITOLAK gate:**
```
"signup blocked, skip"          -> penyerahan
"captcha susah, skip"           -> penyerahan
"butuh SMS, skip"               -> penyerahan
```

**Kenapa:** kegagalan teknis = rework, bukan N/A (lihat `redteam-mindset` +
`N/A discipline`). Gate 0F-pre akan **memblokir laporan** kalau N/A-nya penyerahan.

---

## Yang TIDAK boleh dilakukan

| jangan | kenapa |
|---|---|
| Bikin banyak akun (mass registration) | langgar ToS hampir semua target |
| Pakai identitas/nomor orang lain | masalah hukum |
| Bypass KYC dgn data palsu | bisa ban + masalah regulasi |
| Pakai kartu kredit orang lain | penipuan |
| Abusi layanan SMS sekali-pakai | langgar ToS penyedia |

### 8. Decoy input + cross-origin HV challenge iframe (terukur 2026-10, Proton)

Kalau field "ada di DOM" tapi `visibility:hidden` / koordinat negatif, **jangan** simpulkan
"form-nya rusak" atau "anti-bot mustahil". Cek dua hal ini dulu:

```js
// 1. setiap input: bounding box + visibility + apakah off-screen
Array.from(document.querySelectorAll('input')).map(e=>{const r=e.getBoundingClientRect();
  const s=getComputedStyle(e);
  return {id:e.id, type:e.type, vis:s.visibility, x:Math.round(r.x), y:Math.round(r.y),
          w:Math.round(r.width), offscreen:(r.x+r.width<0||r.y+r.height<0)};});
// 2. semua FRAME — field asli sering ada di iframe
pg.frames.map(f => f.url)        # python
```

| Gejala | Artinya |
|---|---|
| input punya w/h wajar tapi `visibility:hidden` + `x≈-1000` | **honeypot** — umpan untuk bot yang "isi semua input" |
| parent `aria-hidden="true"` | sama: umpan, bukan field |
| `<iframe src="https://<api-host>/challenge/v4/html?Type=0&Name=email">` | **field ASLI ada di dalam iframe cross-origin** |
| `pg.frames` memuat `.../challenge/v4/html` | isi lewat frame itu, bukan dokumen induk |

**Aturan kerja:**
1. **Jangan `fill()` semua input membabi buta** — itu mengisi honeypot dan menandai sesi sebagai bot.
2. Field asli: `[f for f in pg.frames if 'Name=email' in f.url][0].fill('#email', val)`.
3. **Nilai di dalam frame TIDAK otomatis sinkron ke state React induk.** Terukur: `value` benar di
   frame, tapi parent tetap `This field is required` dan **nol request keluar**. Itu sinyal gate-nya
   bukan sekadar iframe — ada verifikasi manusia di dalamnya.
4. Kalau begitu: **berhenti mengotomasi** lalu pakai §9 di bawah. Jangan `dispatchEvent` paksa dan
   jangan JS-force klik elemen off-screen; keduanya tidak menghasilkan request, hanya membakar waktu.

**Bukti cepat di sisi API** (kalau ada endpoint signup langsung) — kirim body lengkap, lalu uji
header HV dengan nilai **kosong** untuk membuktikan header itu benar-benar dibaca:
```
tanpa header HV                         -> 400 {"Code":2001,"Error":"Invalid input"}
x-pm-human-verification-token: ""       -> 422 "Invalid token type"   <- diparse!
x-pm-human-verification-token: <palsu>  -> 400 "Invalid input"
```
`422 Invalid token type` membuktikan gate-nya nyata dan wajib, bukan opsional. Ini juga yang
membedakan "API salah bentuk" dari "API dijaga HV" — penting supaya tidak menulis "signup diblokir"
padahal cuma payload kita yang kurang.

DOM dump lengkap, 6 pendekatan yang gagal, dan panen-sesi setelah serah-terima:
`references/cross-origin-challenge-iframe-signup.md`.

### 9. Serah-terima ke operator — kalau HV memang tidak bisa diotomasi

Ini **bukan kegagalan** dan **bukan** alasan menulis `N/A`. Aturannya: identitas kedua tetap harus
didapat, hanya pemilik langkahnya yang berganti.

**Urutannya penting: JANGAN langsung minta operator.** Jalankan tangga §1–§7 dulu (provider email →
alias → captcha/stealth → proxy → surface tanpa gate → API mobile), baru §9. Operator memang yang
terakhir, bukan yang pertama — tapi kalau HV-nya terbukti tidak bisa diotomasi, minta lebih baik
daripada menulis `N/A`.

1. Buka Chromium **headed** dengan profil persisten khusus target, biarkan proses hidup:
   ```python
   ctx = pw.chromium.launch_persistent_context(
       r"/home/agentuser/<target>-manual-profile", headless=False,
       args=["--disable-blink-features=AutomationControlled","--start-maximized"],
       no_viewport=True, locale="en-US", timezone_id="Asia/Jakarta")
   ```
   Jalankan via `terminal background=true` + `notify_on_complete=true`. **Jangan foreground** —
   timeout akan membunuh browser yang sedang dipakai operator.
2. **Pilih URL signup dengan gerbang paling sedikit.** Nyata: `/signup` (wizard baru: kartu plan +
   langkah payment) jauh lebih berliku daripada `/<product>/signup?plan=free` yang cuma
   password + submit. Bandingkan dulu sebelum menyuruh operator.
3. Beri operator: URL, path profil, password yang disarankan, dan "jangan tutup jendela sampai selesai".
4. Setelah selesai, **panen sesi dari profil yang sama** (buka lagi persistent context, baca
   `ctx.cookies()`), lalu **verifikasi identitas sebelum dipakai**: `GET /users` `/users/me` harus
   mengembalikan email yang benar. Jangan langsung tembak matriks authz.
5. **Satu profil = satu proses.** Profil yang masih dipakai proses lain menolak dibuka
   (`Opening in existing browser session`). Matikan dulu proses pemakai profil itu, atau baca cookie
   lewat proses yang sudah berjalan — jangan bikin instance kedua.

**Wajib dicatat di ledger:** "account B dibuat manual oleh operator, <tanggal>" — supaya laporan
tidak menyiratkan self-provisioning yang tidak terjadi.

**Kalau policy target melarang pendaftaran dari wilayahmu atau dengan data samaran:**
tandai `not-tested`, sebutkan alasannya, lanjut ke surface lain. Itu **kepatutan**, bukan kegagalan.

---

## Alur praktis (ringkas)

```
1. Coba daftar normal (email milikmu / alias)
        ↓ gagal
2. Ganti email provider (mail.tm / alias / domain sendiri)
        ↓ gagal
3. Camoufox (CAPTCHA stealth) atau SeleniumBase solve_captcha
        ↓ gagal
4. proxy_run.py ganti IP (kalau terblokir IP/rate)
        ↓ gagal
5. geo_session.py (kalau terblokir negara)
        ↓ gagal
6. Cari surface tanpa gate: API mobile, endpoint lama, halaman publik
        ↓ gagal
7. Tandai N/A + sebut 3+ pendekatan yang sudah dicoba
```

---

## Sambungan ke pipeline

```
0A  baca policy — boleh daftar akun uji?
0B  recon — cek apakah ada surface tanpa gate (API mobile, endpoint lama)
0C  daftar via tangga di atas → identity_harness capture → audit normal
0D  gate: N/A harus sebut pendekatan apa yang sudah dicoba
```

Skill terkait: `geo-block-proxy-ops` · `disposable-auth-identity` ·
`identity_harness.py` · `bot-protected-target-testing` · `redteam-mindset` ·
`exploit-depth` (L0–L5).
