# Dangling Social Link (Dead Handle) — recon → klaim → eskalasi

Sister-class dari subdomain takeover (`hunt-subdomain`). Keduanya "klaim resource nganggur atas
nama brand". Bedanya: subdomain takeover = DNS CNAME nganggur → serve konten; dangling social link
= **handle media sosial mati** yang di-link dari situs resmi → attacker daftar handle → nyamar
jadi brand. Additive-only.

---

## Definisi & kenapa diakui

Website resmi nge-link ke handle X / Facebook / Instagram / YouTube / TikTok / LinkedIn yang
**belum didaftarkan** atau **sudah dihapus/suspended**. Attacker mendaftarkan handle itu, lalu
`https://x.com/<brand>` yang ter-link dari footer/help-center kini menunjuk ke akun penyerang —
penyamaran brand penuh.

Contoh konkret yang diterima industri: subdomain `aiaa-dpw.larc.nasa.gov` CNAME → GitHub Pages
mati → di-takeover → diterima NASA sebagai **P3**, researcher dapat Letter of Appreciation +
Hall of Fame.

**Catatan program NASA (jangan salah target):**
- NASA = **VDP tanpa hadiah uang** (hanya pengakuan + surat).
- Laporan lewat **Bugcrowd** → ini bentrok dengan aturan no-platform kita (hindari platform).
- Kelas bug-nya sendiri tetap valid di banyak program berbayar, bukan cuma NASA — jadi jaruh
  tekniknya, cari target berbayar yang nerima.

---

## Severity & eskalasi

| Level | Kondisi |
|---|---|
| **Low** | handle mati di tempat sepi (satu footer item kecil, brand kecil) |
| **Medium** | handle mati di-link dari tempat prominent (footer resmi, help center, halaman kontak) |
| **High (rare)** | brand BESAR + link prominent → dampak phishing / pengumuman palsu / scam support |

**Prinsip eskalasi:** makin dipercaya lokasi link-nya, makin tinggi severity. Footer + help center
= tempat yang user anggap otoritatif, jadi penyamaran di sana berdampak nyata.

**Jalur naik ke High (sama seperti subdomain takeover — lihat `hunt-subdomain` 5 chain):**
- Cookie parent-domain `Domain=.target.com` → takeover baca session cookie user lain
- CSP `script-src *.target.com` → JS dari subdomain hasil takeover jalan di origin utama = XSS
- CORS allow `*.target.com` → credentialed cross-origin read
- OAuth redirect URI wildcard → auth-code theft
- Email (SPF/DKIM) → spoofing atas nama subdomain terpercaya
- Halaman login phishing di subdomain yang dipercaya user

---

## Eksekusi — disiplin wajib (beda dari subdomain takeover)

1. **JANGAN beneran posting nyamar jadi brand.** Itu melanggar hampir semua program dan bisa
   dianggap abuse/impersonation, bukan research.
2. Cukup **buktikan handle TERSEDIA dan BISA didaftarkan**, ATAU daftar lalu **langsung
   serahkan/dipake untuk verifikasi ke vendor** (bukan diposting).
3. **Cek program rules dulu.** Ada program yang eksplisit melarang "takeover akun beneran" /
   meregistrasi handle brand. Kalau ada klausa itu, jangan daftar — cukup laporkan sebagai
   "handle tersedia untuk didaftarkan" (availability proof) dan serahkan keputusan daftar ke vendor.

---

## Validasi ikut aturan main (anti over-claim)

Klaim harus **dibuktikan, bukan ditunjuk**:
- **"Saya bisa serve konten di subdomain ini"** = klaim BENERAN dengan PoC jinak (mis. file teks /
  halaman HTML kosong). DNS CNAME nganggur doang **BELUM cukup** — itu cuma signal, bukan finding.
- Untuk dangling social: bukti = halaman pendaftaran handle menampilkan "username tersedia" (atau
  status 404/not-found di URL `https://x.com/<brand>` sementara situs resmi masih link ke sana),
  ditambah screenshot bahwa link tersebut ada di footer/help-center situs resmi.
- **Cek program rules** — ada program yang eksplisit exclude subdomain takeover / social takeover.
  Kalau exclude, jangan laporkan (atau laporkan sebagai info internal, bukan temuan bounty).

---

## Deteksi cepat (recon-friendly)

```bash
# 1) kumpulkan semua URL situs resmi (footer, help center, halaman kontak)
grep -rhoE "https?://(x\.com|twitter\.com|facebook\.com|instagram\.com|youtube\.com|linkedin\.com|tiktok\.com)/[A-Za-z0-9_.]+" \
  index.html footer.html help.html 2>/dev/null | sort -u

# 2) untuk tiap handle, cek status: 404 / "username tidak tersedia" / "Account suspended"
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://x.com/<handle>"
# 404/302-ke-login (handle tak ada) + situs masih link = dangling candidate

# 3) ulangi untuk tiap channel yang di-link situs (footer biasanya punya 3-6)
```

**Proof yang diterima triager:**
- Screenshot situs resmi yang menampilkan link ke `<brand>` di footer/help-center (konteks: lokasi
  linknya prominent).
- Screenshot halaman pendaftaran / response yang menampilkan handle `TERSEDIA` / account-not-found.
- (Opsional) setelah approve: akun placeholder diserahkan ke vendor, bukan posting konten.

---

## Refusal-pattern

- Handle mati di situs **milik operator pihak ketiga** (bukan target bounty) → jangan sentuh.
- Program **eksplisit exclude** social/takeover → jangan laporkan sebagai bounty.
- Cuma "CNAME nganggur" tanpa PoC serve konten → bukan finding (candidate).
- NASA / platform-hosted (Bugcrowd) → bukan target kita (no-platform + VDP no-money).

## Cross-reference

- Subdomain takeover + 5 chain eskalasi → `hunt-subdomain/SKILL.md` (Chains & Compositions).
- Recon CNAME dangling + subjack → `security-recon` Step 5 + `dnsReaper`.
- OSINT handle brand → `offensive-osint` (social profile enumeration).