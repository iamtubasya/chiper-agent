---
name: twitter-x
description: "X/Twitter via cookie auth: post, search, DM, media, follow — tanpa Developer account. Auto-login jika cookie expired."
version: 1.2.0
author: Chiper
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  commands: [curl, jq, node]
metadata:
  chiper:
    tags: [twitter, x, social-media, cookie, free, no-developer-account]
    homepage: https://github.com/iamtubasya/chiper-agent
---

# Twitter-X — X (Twitter) via Cookie Authentication

Akses X/Twitter tanpa Developer account, tanpa bayar, tanpa OAuth. Cukup pakai cookie dari browser.

---

## Struktur Skill (Self-Contained)

Semua file di dalam folder skill ini:

```
Twitter-X/
├── SKILL.md              # Dokumentasi
├── twitter-x.sh          # CLI tool (chmod +x)
├── cookie.json           # Auto-generated (JANGAN edit manual)
├── account.txt           # Credential (auto-generated saat login)
├── gmail-app.txt         # Gmail credential untuk verifikasi
├── script/
│   ├── x-login.js        # Opsi 1: Login default (tanpa proxy)
│   └── x-login-tor-ip.js # Opsi 2: Login via Tor + auto-verifikasi
├── browser-profile/      # Firefox persistent profile (auto-generated)
└── screenshots/          # Screenshot login (auto-generated)
```

**Skill ini SELF-CONTAINED** — bisa dipindah ke server lain tanpa ubah path.

---

## Install di Server Lain

```bash
# 1. Copy folder skill ke server lain
scp -r Twitter-X/ user@server:~/skills/

# 2. Install dependency di server baru
npm install playwright
npx playwright install firefox
sudo apt install tor jq curl

# 3. Buat symlink agar bisa dipanggil dari mana saja
sudo ln -s ~/skills/Twitter-X/twitter-x.sh /usr/local/bin/twitter-x
chmod +x ~/skills/Twitter-X/twitter-x.sh

# 4. Jalankan
twitter-x post "Hello from new server!"
```

---

## Secret Safety (MANDATORY)

- **Never** read, print, parse, summarize, upload, atau send cookie/credential ke LLM context.
- **Never** minta user paste credential di chat.
- Cookie hanya di `Twitter-X/cookie.json` (auto-generated).
- Credential di `Twitter-X/account.txt` dan `Twitter-X/gmail-app.txt` (user buat manual).

---

## Cara Pakai

### Pertama Kali (Auto-Login)

```bash
twitter-x post "Hello!"
```

Script otomatis:
1. Cek cookie → tidak ada → auto-login
2. Opsi 1: Login default (tanpa proxy)
3. Jika gagal (verifikasi/rate limit) → Opsi 2: Tor + auto-verifikasi email
4. Simpan cookie → jalankan command

### Cookie Expired

Sama — script auto-detect expired dan login ulang.

### Manual Login

```bash
twitter-x login
```

### Cek Status

```bash
twitter-x auth status
```

---

## Auto-Login Flow

```
twitter-x <command>
    ↓
Cek cookie.json
    ├─ Valid → Pakai cookie, jalankan command
    └─ Expired/tidak ada → Auto-login
         ↓
    Opsi 1: x-login.js (default, tanpa proxy)
         ├─ Berhasil → simpan cookie → selesai
         ├─ Verifikasi diperlukan → fallback ke opsi 2
         └─ Rate limited → fallback ke opsi 2
              ↓
    Opsi 2: x-login-tor-ip.js (Tor proxy)
         ├─ Berhasil langsung → simpan cookie → selesai
         └─ Verifikasi diperlukan:
              ├─ Ambil kode dari email (Himalaya)
              ├─ Submit kode ke X
              └─ Berhasil → simpan cookie → selesai
```

---

## Command Reference

```bash
# Posting
twitter-x post "Hello world!"
twitter-x reply POST_ID "Nice post!"
twitter-x quote POST_ID "My take"
twitter-x delete POST_ID

# Search & Read
twitter-x search "query" --limit 10
twitter-x timeline --limit 20
twitter-x mentions --limit 10

# Engagement
twitter-x like POST_ID
twitter-x unlike POST_ID
twitter-x repost POST_ID
twitter-x follow @handle
twitter-x unfollow @handle

# DM
twitter-x dm @handle "message"

# Info
twitter-x whoami
twitter-x user @handle

# Raw API
twitter-x raw GET /2/users/me
```

---

## File: gmail-app.txt

Untuk auto-verifikasi email. Isi:

```
Email : anda@gmail.com
Password-app : xxxx xxxx xxxx xxxx
```

**Wajib App Password** (bukan password Gmail):
1. Buka https://myaccount.google.com/apppasswords
2. Pilih "Mail" → "Other" → "Twitter-X"
3. Copy 16 karakter

---

## File: account.txt

Auto-generated saat login pertama. Isi:

```
username: @handle
password: password_anda
```

---

## Error Handling

| Error | Solusi |
| --- | --- |
| Rate limited | Tunggu 15-30 menit, ganti IP |
| Wrong password | Script minta ulang credential |
| Account suspended | Appeal di x.com/account/access |
| Verification required | Auto-ambil kode dari email |
| Playwright not found | npm install playwright && npx playwright install firefox |

---

## Troubleshooting

### "Cookie expired"
- Script auto-login ulang

### "Playwright not found"
```bash
npm install playwright
npx playwright install firefox
```

### "Tor not available"
```bash
sudo apt install tor
sudo systemctl start tor
```

### "Himalaya not found"
```bash
curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh
```

### "Account suspended"
- Buka https://x.com/account/access
- Appeal/unlock
- Setelah aktif, jalankan `twitter-x login`
