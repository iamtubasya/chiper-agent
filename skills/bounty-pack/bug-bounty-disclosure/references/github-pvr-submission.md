# GitHub Private Vulnerability Reporting (PVR) — kanal disclosure + submit via API

Dipakai kalau: repo target punya GitHub PVR aktif, atau alamat di SECURITY.md mati/bounce.
Referensi ini dari engagement nyata (TrustLend, `thisisouvik/trustlend-stellar`, 2026-10-04).

## 1. Alamat di SECURITY.md bisa MATI — selalu verifikasi

Kasus nyata: SECURITY.md bilang `security@trustlend.io`, tetapi:
- `nslookup -type=MX trustlend.io` → `MX preference = 0, mail exchanger = (root)` = **null MX**
  (domain secara eksplisit TIDAK menerima email),
- A-record ke IP parkir, `/.well-known/security.txt` → redirect ke `/lander` (halaman parkir),
- domain lain di repo (`trustlend.xyz`) sama; `.app` / `.finance` / `.org` → **NXDOMAIN**.

Semua itu = alamat itu fiktif. Jangan kirim ke sana, dan jangan lapor "sudah kirim".

## 2. Cari kanal yang benar-benar hidup

Urutan yang terbukti berhasil:

```bash
gh login? -> skip kalau gh tidak terpasang
# identitas & kanal owner
curl -s https://api.github.com/users/<owner>            # name, blog, twitter_username
curl -s https://api.github.com/repos/<o>/<r>            # homepage, has_discussions
curl -s https://api.github.com/repos/<o>/<r>/private-vulnerability-reporting   # {"enabled": true}
# email maintainer: commit author (TIDAK bisa dipalsukan, dan biasanya hidup)
git log --format='%an <%ae>' | sort -u
# konfirmasi kedua: situs pribadi owner (mailto di halaman)
curl -s https://<owner-blog> | grep -oiE 'mailto:[^"]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
```

Email maintainer yang terverifikasi dari **dua sumber independen** (commit author + situs
pribadi) jauh lebih dapat dipercaya daripada alamat generik di SECURITY.md.

`.well-known/security.txt` pada app live (mis. `*.vercel.app`): 404 semua → memang tidak ada.

## 3. Submit via API (PVR)

```http
POST https://api.github.com/repos/{owner}/{repo}/security-advisories/reports
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
Authorization: Bearer <token>
Content-Type: application/json

{"summary":"...","description":"<markdown lengkap>",
 "severity":"critical|high|medium|low",
 "vulnerabilities":[{"package":{"ecosystem":"other","name":"<repo>"},
                     "vulnerable_version_range":"all versions (rev <sha>)"}]}
```

- `vulnerabilities[]` opsional → kalau `422`, retry tanpa blok itu.
- Endpoint ini memang untuk **pelapor eksternal**. Jangan tertukar dengan
  `POST /repos/{o}/{r}/security-advisories` (bikin advisory sendiri) — itu butuh
  **security manager / admin repo**, pelapor luar tidak bisa.
- Cek cepat endpoint ada: POST tanpa auth → **401** (bukan 404).

### Permission yang dibutuhkan (dan cara tahu kurangnya)

| Token | Syarat | Symptom kalau kurang |
|---|---|---|
| Fine-grained PAT | Repository permissions → **Repository security advisories: Read and write** (+ Repository access = **All repositories**) | `403` + header `x-accepted-github-permissions: repository_advisories=write` |
| Classic PAT | scope **`public_repo`** | `403` / `404` |

Header respons `x-accepted-github-permissions` / `X-OAuth-Scopes` adalah cara tercepat
mendiagnosa **sebelum** menyalahkan endpoint. Cek dengan GET `/user` sambil lihat header.

### Blokir yang sering muncul untuk akun baru

```
403 {"message":"You have exceeded a secondary rate limit and have been temporarily
     blocked from content creation."}
```

Ini **content-creation secondary limit** khas akun GitHub muda/kurang riwayat. Artinya token
BENAR dan auth lolos — yang ditolak adalah *membuat konten*. **0 laporan terkirim, tidak ada
efek samping.** Opsi: tunggu (biasanya pulih dalam 1–2 jam) lalu ulang dengan pacing lambat,
pakai akun yang lebih matang, atau submit manual lewat form web
(`https://github.com/{o}/{r}/security/advisories/new`) yang kadang lolos.

## 4. Pola script yang aman (dari engagement ini)

```
[ ] GATE ganda: butuh token + env I_CONFIRM_USER_FINISHED_READING=yes.
    Tanpa keduanya → exit, tidak kirim apa pun. Default = DRY-RUN.
    (Hard-rule user: kirim hanya setelah user konfirmasi selesai baca.)
[ ] RESUMABLE: catat hasil per temuan ke evidence/pvr-submitted.json
    (id → {result, url, at}); re-run hanya mengirim yang belum OK. Aman diulang.
[ ] PACING + backoff pada 403 secondary limit (60s,120s,240s,...), bukan retry rapat.
[ ] 1 temuan = 1 report. Jangan gabung.
[ ] Jangan pernah inline token di shell command — lihat §5.
```

## 5. Token: jangan taruh di command line

Sistem bisa meredaksi pola token di dalam perintah yang ditulis agent, sehingga
`export GITHUB_TOKEN='ghp_...'` berubah jadi `***` dan hasilnya `401 Bad credentials`
(walaupun tokennya benar). Jangan melawan kontrol itu — pakai jalur file:

```
[ ] Minta user menaruh token di file, mis. <engagement>/.gh_token (satu baris).
[ ] Script membaca: env GITHUB_TOKEN/GH_TOKEN, kalau kosong → file .gh_token (strip()).
[ ] Token tidak pernah ditulis oleh agent, tidak pernah masuk log.
[ ] Setelah selesai: minta user REVOKE token (sudah terekspos di chat).
```

Gejala diagnostik: `echo "len=${#GITHUB_TOKEN}"` → `3` artinya yang masuk cuma `***`.
Bedakan dari `401` yang datang dari token yang memang salah/belum diberi permission.

## 6. Kalau API tetap gagal → form web

Siapkan teks **siap-paste per temuan**: satu file `PVR_SUBMIT.md`, tiap blok berisi
`TITLE:` / `SEVERITY:` / `CWE:` / `ASSET:` / `POC:` + deskripsi markdown lengkap di antara
penanda `<<<DESC` … `DESC>>>`. Field form: Title, Description, Severity (dropdown),
Weaknesses/CWE, Affected products. Email tetap jadi kanal cadangan.
