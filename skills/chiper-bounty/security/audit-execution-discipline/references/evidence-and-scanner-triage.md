# Bukti & triase scanner: 0-byte file, falsifikasi fuzzer, atribusi bytecode

Sumber: engagement Superstate 2026-10-01 (slither + aderyn + mythril + echidna + nuclei/trufflehog).

---

## 1. File bukti 0 byte BUKAN negatif

RULE 2c sudah menutup arah positif-palsu (file >100 B yang isinya cuma banner error). Arah sebaliknya
kena di Superstate: `nuclei -silent ... > out.txt` dengan **nol temuan menghasilkan file 0 byte**. Sapuan
16 artefak menemukan satu file 0 B, jadi kesimpulan "tidak ada subdomain takeover" saat itu **tidak
berbukti** — tidak bisa dibedakan dari "scan-nya tidak pernah jalan".

Untuk setiap scanner yang diperkirakan tidak menemukan apa-apa, bungkus dengan banner + marker selesai:

```bash
{ echo "=== <tool> : $(date -u +%FT%TZ) ==="
  echo "=== command: <perintah persisnya> ==="
  echo "=== template/target count: $(ls <templates>/*.yaml | wc -l) / $(wc -l < targets.txt) ==="
  timeout 900 <tool> <args> 2>&1          # TANPA -silent, supaya banner run ikut tertangkap
  echo "=== exit=$? ==="
  echo "=== SELESAI: 0 baris hasil di atas berarti TIDAK ADA temuan ==="
} > out.txt
```

Baca balik marker-nya sebelum mengutip negatif:
`grep -E "Scan completed|No results found|HTTP connections|finished scanning" out.txt`.
Negatif yang sah sekarang terlihat seperti: `[INF] Scan completed in 50.69s. No results found.` +
`HTTP connections: 203 total` — bukti scan jalan, sekaligus negatifnya.

### Cari pendamping yang membuktikan run-nya
- `trufflehog --json > x.json` menghasilkan 0 B saat bersih — **stderr-nya** yang menentukan:
  `{"msg":"finished scanning","chunks":2001,"bytes":1089043,"verified_secrets":0,"unverified_secrets":0}`.
  Kutip stderr, bukan json kosongnya. (Ini bukti sah untuk klaim "3 repo, seluruh history, 0 kredensial".)
- `subfinder` / `httpx` menulis **stderr kosong** saat sukses; stdout-nya yang berisi hasil. Pasangkan keduanya.
- `*-noresp.txt` / `*-https.txt` yang kosong biasanya isi sebenarnya ada di saudaranya `*-list.txt`.

### Close-out mekanis sebelum bilang "semua tool selesai"
```python
import os
for root,_,files in os.walk('tool-evidence'):
    for f in files:
        p=os.path.join(root,f)
        if os.path.getsize(p)==0: print("EMPTY ->", p)
```
Setiap hasil wajib: (a) dijalankan ulang dengan pembungkus di atas, atau (b) dijelaskan oleh pendamping
non-kosong yang bisa disebut namanya. "Kosong karena memang tidak ada yang dilaporkan" tidak cukup sendirian.

---

## 2. Falsifikasi fuzzer = hipotesis, bukan temuan

Echidna/medusa yang memfalsifikasi properti bisa berarti: (1) bug nyata, (2) bug yang hanya bisa dicapai lewat
satu jalur, atau (3) **invarian kita sendiri yang salah**. Pisahkan secara mekanis:

1. **Harness varian.** Salin harness jadi `<Name>NoX.sol`, hapus HANYA aksi `X`, ganti nama kontraknya,
   jalankan ulang dengan limit lebih kecil.
2. **Baca deltanya.** Properti yang berubah `failed` → `passing` penyebabnya `X` — kaitkan ke jalur kode
   yang dicapai `X` dan hanya itu. Yang tetap gagal berarti nyata ATAU harness yang salah.
3. **Curigai invarian sendiri lebih dulu untuk yang tersisa.**

Contoh nyata: `capacity_never_exceeds_balance` gagal di DUA run. Penyebabnya invarian saya membandingkan
`maxUstbRedemptionAmount()` dengan saldo USDC mentah — padahal fungsi itu **sengaja meng-gross up** nominal
dengan fee (`* FEE_DENOMINATOR / (FEE_DENOMINATOR - redemptionFee)`), sehingga untuk fee > 0 kapasitasnya
memang melebihi saldo by design. Artefak harness → tidak dilaporkan.

→ **Saat menulis invarian atas aritmatika uang, tulis ulang semantik pembulatan dan gross-up kontraknya di
dalam invarian itu sendiri.** Baca komentar di sebelah rumusnya sebelum menulis assertion.

4. Catat falsifikasi DAN adjudikasinya di log, termasuk properti mana yang benar-benar lulus (mis. di
   Superstate: `out_never_exceeds_value` lulus = tidak ada uang gratis di fee mana pun yang bisa di-set owner).

---

## 3. Atribusikan temuan bytecode ke fungsinya sebelum menilai severity

Symbolic executor dalam mode bytecode tidak bisa menamai fungsi — mythril mencetak
`Function name: constructor` untuk temuan APA PUN dan hanya memberi blob `calldata:`. Label itu tidak berarti;
jangan menilai temuan dari label itu. Identifikasi entry point-nya sendiri:

```bash
# ambil selector 4-byte dari field `calldata:` mythril, mis. e24df754, lalu cocokkan:
cast sig "initialize(address,uint256,address,uint256)"   # -> 0xe24df754
cast sig "redeem(uint256)"                               # -> 0xdb006a75
```

Contoh nyata: temuan severity **High** SWC-101 dilaporkan sebagai `constructor`; setelah dilacak, calldata-nya
menunjuk `initialize(...)`, bukan aritmatika uang redemption — rating berubah dari High menjadi QA/Informational.
Melaporkan temuan bytecode tanpa langkah ini = cara label scanner menjadi overclaim.

### Menjalankan mythril atas bytecode TER-DEPLOY
Teknik yang dipakai: analisis bytecode runtime yang benar-benar ada di mainnet, bukan cuma hasil kompilasi.

```bash
# 1. dapatkan implementasi di balik proxy (slot ERC-1967)
cast storage <PROXY> 0xREDACTED_******** --rpc-url <RPC>
# 2. ambil bytecode runtime-nya (dan bytecode kontrak langsung untuk non-proxy)
cast code <IMPL_ATAU_KONTRAK> --rpc-url <RPC> > deployed.hex
# 3. analisis
myth analyze -f deployed.hex --execution-timeout 240 --solver-timeout 20000 -t 1 --no-onchain-data
```
Bound ketat (`--execution-timeout`, `-t 1`) itu wajib: bytecode 7–10 KB bikin solver lambat.
Kalau `myth --solv <versi>` gagal karena tidak bisa mengunduh solc, pakai binary lokal:
`SOLC=/home/<user>/.local/bin/solc myth analyze -f deployed.hex ...` (dan hilangkan `--solv`).
Kalau `--solc-json` remapping tidak dihormati untuk analisis source, pivot ke jalur bytecode ini — hasilnya tetap
analisis nyata atas kode yang ter-deploy, dan sering lebih relevan daripada source repo yang bisa lebih baru.

---

## 4. Jalur kontrak yang lebih baru dari yang ter-deploy

Kalau `VERSION()` on-chain berbeda dari versi di repo (Superstate: mainnet "1.3.0" vs repo "4"), maka repo
main itu **kode belum rilis**. Konsekuensi urutan: temuan di repo hanya layak dilaporkan kalau (a) direproduksi
pada alamat yang ter-deploy, atau (b) jelas memengaruhi rencana rilis vendor. Sebutkan status ini eksplisit
di laporan; jangan diam-diam menyiratkan mainnet terpengaruh.

---

## 5. Adjudikasi route SPA: mana yang benar-benar ADA

RULE 35.2 sudah memperingatkan soal catch-all route yang memalsukan "panel terekspos". Ini resep pembedanya —
dipakai di Superstate dan mencegah 7 laporan palsu (`.well-known/security.txt`, `openid-configuration`,
`ai-plugin.json`, `assetlinks.json`, `trust.txt`, `gpc.json`, `nodeinfo` semuanya 200).

### Uji catch-all: bandingkan dengan path acak
```bash
curl -s -m 15 -o wk1.html "https://target/.well-known/security.txt"
curl -s -m 15 -o wk2.html "https://target/zzz-not-a-real-path-98765"
ls -la wk1.html wk2.html            # ukuran hampir sama = curiga catch-all
md5sum wk1.html wk2.html            # beda hash itu NORMAL (nonce/hydration) - jangan jadi patokan tunggal
grep -oE "<title>[^<]*</title>" wk1.html wk2.html
```
Kalau judul + ukuran ± sama, itu **shell SPA**, bukan file. Semua path yang "200" harus diuji begini sebelum
masuk laporan. Tanda lain: banyak path berbeda dengan ukuran identik (31.471 / 31.474 / 31.479) = artefak.

### Uji keberadaan route: OPTIONS, bukan GET
GET pada SPA hampir selalu 200 (shell), jadi tidak informatif. Yang membedakan:

```bash
curl -s -X OPTIONS -o /dev/null -w "code=%{http_code} allow=%header{allow}\n" "https://target/api/<path>"
```
- `405` + `allow: GET, HEAD` → **route itu NYATA** dan melayani method tersebut.
- `200` dengan `allow` kosong → ambigu (banyak framework membalas 200 untuk OPTIONS yang tak ditangani);
  **jangan** dijadikan bukti route ada.

Verifikasi lanjutan yang aman: `GET` route yang sudah terbukti ada. Kalau balasannya `401/403` → terlindungi.
Kalau `500 {"message":"Internal Error"}` tanpa kredensial → catat sebagai **LEAD**, bukan temuan: itu bisa
berarti pemeriksaan kredensial ada setelah logika bisnis, tapi tidak ada data/aksi yang terbukti. Jangan pernah
kirim method pengubah state (PUT/PATCH/POST/DELETE) untuk "memastikan" — itu melanggar aturan vendor.

### Menemukan route tersembunyi dari bundle JS
```bash
katana -u https://target -d 2 -jc -silent > katana.txt
grep -iE "\.js(\?|$)" katana.txt | sed 's/?.*//' | sort -u > js-urls.txt   # dedupe + buang cache-buster
```
Unduh sampel bundel, lalu cari pola yang menghasilkan route nyata:
- template path: `` /api/${...}/entity_application/${...} ``, `` /api/admin/funds/${id}/gas-costs/invoice ``
- route app: `/admin`, `/admin/entities/${id}`, `/dashboard`
- petunjuk stack dari header CSP (daftar host `connect-src` / `img-src` sering membocorkan environment dan RPC)

Catatan penting pada loop unduhan di shell: `while read ... | ...` berjalan di subshell sehingga counter tidak
naik dan `$f` bisa kosong → 0 file terunduh tanpa error. Pakai Python (`urllib.request`) atau `xargs` untuk
mengunduh banyak URL; jangan percaya "selesai" dari loop bash tanpa mengecek jumlah file hasilnya.

