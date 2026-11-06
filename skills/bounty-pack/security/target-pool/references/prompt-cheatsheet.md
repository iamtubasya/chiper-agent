# Prompt & Instruksi — Target Pool

## A. Cara panggil dari chat (natural language)

| the operator bilang | Agent jalankan |
|---|---|
| "kasih target dari pool" | `pool.py pick --limit 5` → kasih kandidat + alasan |
| "ambil 1 target eropa monetary belum dikerjakan" | `pool.py pick --region eu --reward monetary` |
| "ambil 3 target dari eropa" | `pool.py pick --region eu --limit 3` |
| "yang country de" | `--country de` (alias: "jerman"→de, "inggris"→uk) |
| "yg no platform" / "self-hosted aja" | filter `hosting == self_hosted` (via python: `str(r.get("hosting")).lower()!="platform"`) |
| "1 random target terbaru eropa monetary" | sort kandidat by `first_seen` desc → random pick dari tanggal paling baru |
| "pilih 1 random eropa/australia, **yang benar membayar**, hindari platform" (2026-10-15) | filter `eu ∪ {au}` + `monetary` + `hosting != platform` + `untouched` → random 1 → **wajib fetch policy_url dan cari pernyataan reward sebelum propose** (tag sheet ≠ bayar). Kalau reward ternyata swag/CVD-simbolik → `set <dom> no-reward --note "<kutipan policy>"` DAN re-pick sampai ketemu yang ada nominal. Kasih summary: domain, negara, channel submit, tabel reward, scope, exclusion, SLA |
| "yang ini tandain aja spy gk kebaca lagi" | `pool.py set <dom> no-reward|policy-dead|skipped --note "<alasan>"` — state non-`untouched` tidak akan muncul lagi di `pick`/`pending` |
| "kategori master-list" | `--cat master-list` |
| "pool cari venice" | `pool.py search venice` |
| "<domain> udah digarap?" | `pool.py why <domain>` |
| "sync pool dari MyGroupBot" | ekstrak attachment baru → re-run pool_step1..3 |

Wilayah yang didukung: `eu` / `europe` · `asia` · `americas` · `apac`

## B. Cara panggil dari terminal (langsung, tanpa agent)

```bash
PY314="C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe"
cd ~/AppData/Local/hermes/scripts

# lihat isi
pool.py stats                                   # jumlah per kategori + per state
pool.py body eu                                 # TLD apa saja yang masuk "eu"

# cari target
pool.py pick  --region eu --limit 10            # kandidat siap kerja (skor + alasan)
pool.py pick  --country de --reward monetary    # 1 negara
pool.py pending --limit 80                      # monetary+live+untouched
pool.py list  --reward monetary --limit 60      # semua yang bayar (termasuk yg udah dikerjakan)
pool.py list  --state finding-pending           # yang lagi nunggu dilaporkan
pool.py get   xora.finance                      # record mentah 1 domain
pool.py why   xora.finance                      # record + state + catatan

# tandai hasil kerja
pool.py set  <domain> audited          --note "0 temuan"
pool.py set  <domain> policy-dead      --note "halaman 404"
pool.py set  <domain> no-reward        --note "credit-only"
pool.py skip <domain>                  --note "terlalu susah, skip"
pool.py set  <domain> submitted        --note "F1 dikirim via Bugcrowd"
```

## C. State (audit_status) — ini jawaban "apa nanti ada keterangannya?"

| state | arti | siapa yang set |
|---|---|---|
| `untouched` | belum pernah digarap (default) | otomatis |
| `recon-done` | recon selesai, belum ada temuan | agent |
| `audited` | pipeline 0A–0F sudah dijalankan | agent |
| `finding-pending` | ada temuan, belum dilaporkan | agent |
| `submitted` | laporan sudah dikirim ke vendor | agent |
| `paid` | bounty diterima | the operator |
| `rejected` | vendor tolak / duplikat | the operator |
| `policy-dead` | halaman policy 404/410/redirect | agent (auto-flag) |
| `no-reward` | credit-only / swag / tanpa uang | agent (auto-flag) |
| `skipped` | the operator suruh lompati (alasan di note) | the operator |

**`--note "..."`** disimpan permanen dan muncul di `pool.py list` + `pool.py why`.

## D. Aturan agent (WAJIB)

1. **Query pool SEBELUM minta target ke the operator.**
2. **`untouched` filter mengecualikan SEMUA state lain** — target yang sudah `policy-dead`,
   `no-reward`, `skipped`, `audited` tidak akan muncul lagi di `pick`/`pending`.
3. **Auto-flag saat recon** — kalau policy URL 404/redirect → `set <dom> policy-dead --note "<bukti>"`.
   Kalau program cuma kasih credit/swag → `set <dom> no-reward --note "<kutipan>"`.
   Jangan diamkan; catat supaya tidak diambil ulang.
4. **the operator bilang skip** → `skip <dom> --note "<alasan>"`. Jangan lupa, jangan audit ulang.
5. **Tandai status otomatis** tiap tahap selesai. Jangan biarkan `untouched` setelah dikerjakan.
6. **Pool ≠ otorisasi.** Baca `policy_url` + `safe_harbour` target sebelum testing aktif.
   `safe_harbour: not_stated` = hati-hati, konfirmasi dulu.
7. `BB 10K.txt` (10k `sk-` keys) **JANGAN** masuk pool / jangan dipakai.
8. **Deep-check policy SEBELUM propose target** kalau the operator nanya reward/bayar:
   resolve shortlink → halaman rules (biasanya tanpa angka) → cari halaman reward/scope
   (`/i/main-scope` dsb). Sekaligus cek domain pool ADA di scope program — entry pool bisa
   cuma mirror locale (`yandex.fr` → scope `*.yandex.com`). Resep lengkap:
   `references/policy-amount-check.md`.

## E. Kalau data target ternyata salah

`pool.py set <dom> <state> --note "<koreksi>"` — note-nya nyimpen alasan, jadi lain kali
kelihatan kenapa target itu di-skip. Contoh: `expires 2026-02-11 → program ditutup`.
